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


def _expand_command(command: list[str], replacements: dict[str, str]) -> list[str]:
    return [
        next((part.replace(marker, value) for marker, value in replacements.items() if marker in part), part)
        for part in command
    ]


def _run_sandboxed(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    work: Path,
    cabal_cache: Path,
    uv_cache: Path,
    capture: bool = False,
) -> str:
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise RuntimeError("bubblewrap is required for isolated offline builds")
    wrapped = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-net",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        str(work),
        str(work),
        "--bind",
        str(cabal_cache),
        str(cabal_cache),
        "--bind",
        str(uv_cache),
        str(uv_cache),
        "--chdir",
        str(cwd),
        "--",
        *command,
    ]
    result = subprocess.run(
        wrapped,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout or "").strip()
        raise RuntimeError(
            f"isolated command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{output}" if output else "")
        )
    return result.stdout or "" if capture else ""


def _record_command(command: list[str], work: Path) -> list[str]:
    return [part.replace(str(work), "<build-root>") for part in command]


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


def _toolchain(
    repo: Path, cabal_config_sha256: str, cabal_cache: Path, uv_cache: Path
) -> dict[str, str]:
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
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise RuntimeError("bubblewrap is required for isolated offline builds")
    versions["bwrap"] = subprocess.run(
        [bwrap, "--version"], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()
    versions["bwrap_path"] = str(Path(bwrap).resolve())
    versions["cabal_cache_root"] = str(cabal_cache)
    versions["uv_cache_root"] = str(uv_cache)
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


def _source_tree(
    repo: Path, revision: str, source_dir: Path, command_log: list[list[str]], work: Path
) -> tuple[str, str, int]:
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("source revision must be a full lowercase 40-character Git SHA")
    commit = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if commit != revision:
        raise ValueError("source revision does not resolve to the supplied full commit SHA")
    tree = _git(repo, "rev-parse", "--verify", f"{revision}^{{tree}}")
    epoch = int(_git(repo, "show", "-s", "--format=%ct", revision))
    archive_path = source_dir.parent / "source.tar"
    export_command = _expand_command(
        SOURCE_EXPORT_COMMAND,
        {"<temp>": str(source_dir.parent), "<source-revision>": revision},
    )
    _run(
        export_command,
        cwd=repo,
        env=os.environ.copy(),
    )
    command_log.append(_record_command(export_command, work))
    with tarfile.open(archive_path, mode="r:") as archive:
        archive.extractall(source_dir, filter="data")
    archive_path.unlink()
    return commit, tree, epoch


def _validation(
    source_root: Path,
    env: dict[str, str],
    *,
    work: Path,
    cabal_cache: Path,
    uv_cache: Path,
    command_log: list[list[str]],
) -> dict[str, Any]:
    command = VALIDATION_COMMAND
    output = _run_sandboxed(
        command,
        cwd=source_root,
        env=env,
        work=work,
        cabal_cache=cabal_cache,
        uv_cache=uv_cache,
        capture=True,
    )
    command_log.append(_record_command(command, work))
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
        work = work.resolve()
        source_root = work / "source"
        source_root.mkdir()
        source_commands: list[list[str]] = []
        commit, tree, epoch = _source_tree(repo, revision, source_root, source_commands, work)
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
        home = work / "home"
        home.mkdir()
        inherited_path = os.environ.get("PATH")
        if not inherited_path:
            raise RuntimeError("PATH is required to locate the pinned build tools")
        cabal_path_result = subprocess.run(
            [shutil.which("cabal") or "cabal", "path"],
            cwd=repo,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        cache_line = next(
            (line for line in cabal_path_result.splitlines() if line.startswith("cache-home:")),
            None,
        )
        if cache_line is None:
            raise RuntimeError("Cabal did not report its cache home")
        cabal_cache = Path(cache_line.split(":", 1)[1].strip()).expanduser().resolve()
        uv_cache_result = subprocess.run(
            [shutil.which("uv") or "uv", "cache", "dir"],
            cwd=repo,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        uv_cache = Path(uv_cache_result).expanduser().resolve()
        if not cabal_cache.is_dir() or not uv_cache.is_dir():
            raise RuntimeError("offline dependency caches must exist before isolated builds")
        env = {
            "PATH": inherited_path,
            "HOME": str(home),
            "CABAL_DIR": str(cabal_cache),
            "UV_CACHE_DIR": str(uv_cache),
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(epoch),
            "TMPDIR": str(temp_tmp),
            "UV_OFFLINE": "1",
        }
        cabal_config_sha256 = _offline_cabal_config(source_root, work, env)

        validation_command_log: list[list[str]] = []
        validation = _validation(
            source_root,
            env,
            work=work,
            cabal_cache=cabal_cache,
            uv_cache=uv_cache,
            command_log=validation_command_log,
        )
        build_commands: list[list[str]] = []

        def run_build(command: list[str], *, capture: bool = False) -> str:
            result = _run_sandboxed(
                command,
                cwd=source_root,
                env=env,
                work=work,
                cabal_cache=cabal_cache,
                uv_cache=uv_cache,
                capture=capture,
            )
            build_commands.append(_record_command(command, work))
            return result

        run_build(BUILD_COMMANDS[0])
        executable_path = Path(
            run_build(BUILD_COMMANDS[1], capture=True).strip()
        )
        executable_path = executable_path if executable_path.is_absolute() else source_root / executable_path
        if not executable_path.is_file():
            raise RuntimeError("Cabal did not produce the declared executable")
        run_build(
            _expand_command(BUILD_COMMANDS[2], {"<output>/haskell": str(temp_haskell)})
        )
        haskell_sdist = _find_one(temp_haskell, "*.tar.gz")

        run_build(
            _expand_command(BUILD_COMMANDS[3], {"<output>/python": str(temp_python)})
        )
        python_wheel = _find_one(temp_python, "*.whl")
        python_raw_sdist = _find_one(temp_python, "*.tar.gz")
        python_sdist = temp_normalized / python_raw_sdist.name
        run_build(
            _expand_command(
                BUILD_COMMANDS[4],
                {
                    "<raw-sdist>": str(python_raw_sdist),
                    "<output>/normalized/<sdist-name>": str(python_sdist),
                },
            )
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
            "toolchain": _toolchain(source_root, cabal_config_sha256, cabal_cache, uv_cache),
            "commands": {
                "source_export": source_commands,
                "validation": validation_command_log,
                "build": build_commands,
            },
            "environment": {
                "CABAL_CONFIG": "<build-root>/cabal-offline.config",
                "CABAL_DIR": str(cabal_cache),
                "HOME": "<build-root>/home",
                "LC_ALL": "C.UTF-8",
                "PATH": inherited_path,
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": str(epoch),
                "TMPDIR": "<build-root>/tmp",
                "TZ": "UTC",
                "UV_CACHE_DIR": str(uv_cache),
                "UV_OFFLINE": "1",
                "sandbox": "bubblewrap write and network isolation; host filesystem remains visible read-only except build root and declared Cabal/uv caches; network namespace disabled",
            },
            "validation": validation,
            "artifacts": records,
        }
