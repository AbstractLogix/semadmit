"""Build and validate release artifacts from a named Git source revision."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


LOCK_INPUTS = (
    "cabal.project",
    "cabal.project.freeze",
    "semantic-oracle.cabal",
    "clients/python/pyproject.toml",
    "docs/dependency-provenance.json",
)
BUILD_INPUTS = LOCK_INPUTS + (
    ".github/workflows/coverage.yml",
    "assurance/source_build.py",
    "assurance/write_certificate.py",
    "scripts/check_coverage.py",
    "scripts/normalize_python_sdist.py",
)
ARTIFACT_KEYS = (
    "haskell_executable",
    "haskell_source_archive",
    "python_wheel",
    "python_source_archive",
)
BUILD_COMMANDS = [
    ["cabal", "build", "--offline", "exe:semantic-oracle"],
    ["cabal", "list-bin", "exe:semantic-oracle"],
    ["cabal", "sdist", "--output-directory=<output>/haskell"],
    ["uv", "build", "--offline", "--out-dir", "<output>/python", "clients/python"],
    [sys.executable, "scripts/normalize_python_sdist.py", "<raw-sdist>", "<output>/normalized/<sdist-name>"],
]
SOURCE_EXPORT_COMMAND = ["git", "archive", "--format=tar", "--output", "<temp>/source.tar", "<source-revision>"]
VALIDATION_COMMAND = [
    sys.executable,
    "-c",
    "from assurance.write_certificate import local_validation; import json; "
    "tests, mutations, gates = local_validation(); print(json.dumps("
    "{'tests': tests, 'mutations': mutations, 'gates': "
    "[{'name': gate['name'], 'exit_code': gate['exit_code']} for gate in gates]}, sort_keys=True))",
]


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str], capture: bool = False
) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if result.returncode != 0:
        output = result.stdout or "" if capture else ""
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{output[-4000:]}"
        )
    return result.stdout or "" if capture else ""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _toolchain(repo: Path, cabal_config_sha256: str) -> dict[str, str]:
    versions: dict[str, str] = {
        "python": platform.python_version(),
        "python_executable": sys.executable,
    }
    for name, command in (
        ("ghc", ["ghc", "--numeric-version"]),
        ("cabal", ["cabal", "--numeric-version"]),
        ("uv", ["uv", "--version"]),
    ):
        versions[name] = subprocess.run(
            command, cwd=repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        resolved = shutil.which(name)
        if resolved is None:
            raise RuntimeError(f"required build tool is not on PATH: {name}")
        versions[f"{name}_path"] = str(Path(resolved).resolve())
    versions["ghc_global_packages"] = subprocess.run(
        ["ghc-pkg", "list", "--simple-output"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    versions.update(
        {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cabal_config_sha256": cabal_config_sha256,
            "network": "offline",
        }
    )
    return versions


def _source_tree(repo: Path, revision: str, source_dir: Path) -> tuple[str, str, int]:
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("source revision must be a full lowercase 40-character Git SHA")
    commit = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if commit != revision:
        raise ValueError("source revision does not resolve to the supplied full commit SHA")
    tree = _git(repo, "rev-parse", "--verify", f"{revision}^{{tree}}")
    epoch = int(_git(repo, "show", "-s", "--format=%ct", revision))
    archive_path = source_dir.parent / "source.tar"
    _run(
        ["git", "archive", "--format=tar", "--output", str(archive_path), revision],
        cwd=repo,
        env=os.environ.copy(),
    )
    with tarfile.open(archive_path, mode="r:") as archive:
        archive.extractall(source_dir, filter="data")
    archive_path.unlink()
    return commit, tree, epoch


def _validation(source_root: Path, env: dict[str, str]) -> dict[str, Any]:
    command = [sys.executable, *VALIDATION_COMMAND[1:]]
    output = _run(command, cwd=source_root, env=env, capture=True)
    try:
        record = json.loads(output.rstrip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as error:
        raise RuntimeError("clean-source validation did not emit a result record") from error
    if record.get("gates") != [
        {"name": "seeded_corpus", "exit_code": 0},
        {"name": "source_mutation", "exit_code": 0},
        {"name": "test_and_coverage", "exit_code": 0},
    ]:
        raise RuntimeError("clean-source validation omitted a mandatory passing gate")
    if not isinstance(record.get("tests"), dict) or not isinstance(record.get("mutations"), dict):
        raise RuntimeError("clean-source validation result has an invalid structure")
    return record


def _offline_cabal_config(repo: Path, work: Path, env: dict[str, str]) -> str:
    paths = _run(["cabal", "path"], cwd=repo, env=env, capture=True)
    config_line = next((line for line in paths.splitlines() if line.startswith("config-file:")), None)
    if config_line is None:
        raise RuntimeError("Cabal did not report its configuration file")
    configured = Path(config_line.split(":", 1)[1].strip())
    if not configured.is_file():
        raise RuntimeError("the active Cabal configuration file is missing")
    content = configured.read_bytes().rstrip() + b"\noffline: True\n"
    offline_config = work / "cabal-offline.config"
    offline_config.write_bytes(content)
    env["CABAL_CONFIG"] = str(offline_config)
    return hashlib.sha256(content).hexdigest()


def _find_one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1 or not matches[0].is_file() or matches[0].stat().st_size == 0:
        raise RuntimeError(f"expected one non-empty build output matching {pattern!r}")
    return matches[0]


def validate_artifact_structure(name: str, path: Path, machine: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        raise ValueError(f"artifact is missing, empty, or not a regular file: {name}")
    if name == "haskell_executable":
        with path.open("rb") as stream:
            if stream.read(4) != b"\x7fELF" or machine != "x86_64":
                raise ValueError("Haskell executable is not a qualified Linux x86_64 ELF")
        if not path.stat().st_mode & 0o111:
            raise ValueError("Haskell executable is missing executable file permissions")
    elif name == "python_wheel":
        if not zipfile.is_zipfile(path):
            raise ValueError("Python wheel is not a ZIP archive")
        with zipfile.ZipFile(path) as archive:
            members = set(archive.namelist())
            if not any(member.endswith("/METADATA") and ".dist-info/" in member for member in members):
                raise ValueError("Python wheel is missing distribution metadata")
            if not any(
                member == "semadmit/__init__.py" or member.endswith("/semadmit/__init__.py")
                for member in members
            ):
                raise ValueError("Python wheel is missing the Semadmit package")
            if not any(member.endswith("/LICENSE") for member in members):
                raise ValueError("Python wheel is missing the project license")
    else:
        if not tarfile.is_tarfile(path):
            raise ValueError(f"{name} is not a tar archive")
        with tarfile.open(path, mode="r:gz") as archive:
            members = {member.name for member in archive.getmembers() if member.isfile()}
            if name == "python_source_archive":
                if not any(member.endswith("/pyproject.toml") for member in members):
                    raise ValueError("Python source archive is missing pyproject.toml")
                if not any(
                    member == "semadmit/__init__.py" or member.endswith("/semadmit/__init__.py")
                    for member in members
                ):
                    raise ValueError("Python source archive is missing the Semadmit package")
                if not any(member.endswith("/LICENSE") for member in members):
                    raise ValueError("Python source archive is missing the project license")
            elif not any(member.endswith(".cabal") for member in members) or not any(
                member.endswith("/LICENSE") for member in members
            ):
                raise ValueError("Haskell source archive is missing package metadata or license")


def build_source_revision(
    repo: Path, revision: str, output_dir: Path
) -> dict[str, Any]:
    """Rebuild artifacts and validation results from a clean Git archive."""
    repo = repo.resolve()
    output_dir = output_dir.resolve()
    if output_dir == repo or repo in output_dir.parents:
        raise ValueError("artifact output directory must be outside the repository")
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError("artifact output directory must be a new or empty directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="semadmit-source-build-") as temporary:
        work = Path(temporary)
        source_root = work / "source"
        source_root.mkdir()
        commit, tree, epoch = _source_tree(repo, revision, source_root)
        temp_output = work / "outputs"
        temp_output.mkdir()
        temp_python = temp_output / "python"
        temp_haskell = temp_output / "haskell"
        temp_normalized = temp_output / "normalized"
        temp_python.mkdir()
        temp_haskell.mkdir()
        temp_normalized.mkdir()
        temp_tmp = work / "tmp"
        temp_tmp.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "TZ": "UTC",
                "LC_ALL": "C.UTF-8",
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": str(epoch),
                "TMPDIR": str(temp_tmp),
                "UV_OFFLINE": "1",
            }
        )
        cabal_config_sha256 = _offline_cabal_config(source_root, work, env)

        validation = _validation(source_root, env)

        _run(["cabal", "build", "--offline", "exe:semantic-oracle"], cwd=source_root, env=env)
        executable_path = Path(
            _run(
                ["cabal", "list-bin", "exe:semantic-oracle"],
                cwd=source_root,
                env=env,
                capture=True,
            ).strip()
        )
        executable_path = executable_path if executable_path.is_absolute() else source_root / executable_path
        if not executable_path.is_file():
            raise RuntimeError("Cabal did not produce the declared executable")
        _run(
            ["cabal", "sdist", f"--output-directory={temp_haskell}"],
            cwd=source_root,
            env=env,
        )
        haskell_sdist = _find_one(temp_haskell, "*.tar.gz")

        _run(
            ["uv", "build", "--offline", "--out-dir", str(temp_python), "clients/python"],
            cwd=source_root,
            env=env,
        )
        python_wheel = _find_one(temp_python, "*.whl")
        python_raw_sdist = _find_one(temp_python, "*.tar.gz")
        python_sdist = temp_normalized / python_raw_sdist.name
        _run(
            [
                sys.executable,
                "scripts/normalize_python_sdist.py",
                str(python_raw_sdist),
                str(python_sdist),
            ],
            cwd=source_root,
            env=env,
        )

        generated = {
            "haskell_executable": executable_path,
            "haskell_source_archive": haskell_sdist,
            "python_wheel": python_wheel,
            "python_source_archive": python_sdist,
        }
        records: dict[str, dict[str, Any]] = {}
        for name, generated_path in generated.items():
            validate_artifact_structure(name, generated_path, platform.machine())
            destination = output_dir / generated_path.name
            shutil.copy2(generated_path, destination)
            records[name] = {
                "filename": destination.name,
                "sha256": _sha256(destination),
                "size_bytes": destination.stat().st_size,
                "mode": stat.S_IMODE(destination.stat().st_mode),
            }

        locks = {
            name: _sha256(source_root / name)
            for name in LOCK_INPUTS
            if (source_root / name).is_file()
        }
        missing_locks = set(LOCK_INPUTS) - set(locks)
        if missing_locks:
            raise RuntimeError("source revision is missing locked build inputs: " + ", ".join(sorted(missing_locks)))
        build_inputs = {
            name: _sha256(source_root / name)
            for name in BUILD_INPUTS
            if (source_root / name).is_file()
        }
        missing_build_inputs = set(BUILD_INPUTS) - set(build_inputs)
        if missing_build_inputs:
            raise RuntimeError("source revision is missing build inputs: " + ", ".join(sorted(missing_build_inputs)))

        return {
            "source": {"commit": commit, "tree": tree},
            "source_date_epoch": epoch,
            "locked_inputs_sha256": locks,
            "build_inputs_sha256": build_inputs,
            "toolchain": _toolchain(source_root, cabal_config_sha256),
            "commands": {
                "source_export": SOURCE_EXPORT_COMMAND,
                "validation": VALIDATION_COMMAND,
                "build": BUILD_COMMANDS,
            },
            "environment": {
                "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "SOURCE_DATE_EPOCH": "source commit time",
                "TZ": "UTC", "UV_OFFLINE": "1", "CABAL_OFFLINE": "true via temporary CABAL_CONFIG",
            },
            "validation": validation,
            "artifacts": records,
        }
