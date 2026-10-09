#!/usr/bin/env python3
"""Run the repository's test and source-coverage gates."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Sequence


PYTHON_MIN_LINE_PERCENT = 100
HASKELL_MIN_EXPRESSION_PERCENT = 89
HASKELL_MIN_BOOLEAN_PERCENT = 34
EXPECTED_PYTHON_VERSION = "3.13.14"
EXPECTED_GHC_VERSION = "9.14.1"
EXPECTED_CABAL_VERSION = "3.18.1.0"
HASKELL_SUITES = ("core-registry", "identity-vectors", "isoprax-calibration", "isoprax-pool", "isoprax-types", "protocol-contract", "vertical-slice")
TRACE_ROW = re.compile(
    r"^\s*(?P<lines>\d+)\s+(?P<percent>\d+)%\s+"
    r"(?P<module>semadmit(?:\.[A-Za-z_]\w*)*)\s+\((?P<path>.*)\)$"
)
HPC_METRIC = {
    "expressions": re.compile(r"^\s*\d+% expressions used \((\d+)/(\d+)\)$", re.MULTILINE),
    "boolean": re.compile(r"^\s*\d+% boolean coverage \((\d+)/(\d+)\)$", re.MULTILINE),
}


class GateFailure(RuntimeError):
    """A required tool, test, report, or threshold failed."""


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> str:
    rendered = " ".join(command)
    print(f"$ {rendered}", flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if result.returncode:
        if capture and result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        raise GateFailure(f"command exited {result.returncode}: {rendered}")
    if not capture:
        return ""
    return result.stdout or ""


def check_tool_version(root: Path, tool: str, expected: str) -> None:
    output = run([tool, "--numeric-version"], cwd=root, capture=True).strip()
    if output != expected:
        raise GateFailure(f"{tool} version is {output}; expected pinned version {expected}")
    print(f"{tool} version: {output}")


def python_source_modules(package_dir: Path) -> set[str]:
    modules: set[str] = set()
    for source in package_dir.rglob("*.py"):
        relative = source.relative_to(package_dir).with_suffix("")
        modules.add("semadmit." + ".".join(relative.parts))
    return modules


def check_python(root: Path, output_dir: Path) -> None:
    if sys.implementation.name != "cpython":
        raise GateFailure(f"Python gate requires CPython {EXPECTED_PYTHON_VERSION}")
    actual_python = ".".join(map(str, sys.version_info[:3]))
    if actual_python != EXPECTED_PYTHON_VERSION:
        raise GateFailure(
            f"Python version is {actual_python}; expected pinned version {EXPECTED_PYTHON_VERSION}"
        )
    print(f"Python version: {actual_python}")

    package_dir = root / "clients" / "python" / "semadmit"
    tests_dir = root / "clients" / "python" / "tests"
    if not package_dir.is_dir() or not tests_dir.is_dir():
        raise GateFailure("Python package or test directory is missing")

    env = os.environ.copy()
    package_parent = str(package_dir.parent)
    old_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = package_parent + (os.pathsep + old_pythonpath if old_pythonpath else "")
    command = [
        sys.executable,
        "-m",
        "trace",
        "--count",
        "--summary",
        f"--coverdir={output_dir}",
        f"--ignore-dir={tests_dir}",
        "--module",
        "unittest",
        "discover",
        "-s",
        str(tests_dir),
    ]
    output = run(command, cwd=root, env=env, capture=True)

    test_summary = re.search(r"^Ran \d+ tests? in .+$", output, re.MULTILINE)
    if not test_summary or not re.search(r"^OK$", output, re.MULTILINE):
        print(output, end="" if output.endswith("\n") else "\n")
        raise GateFailure("Python unittest discovery did not report a successful run")
    print(test_summary.group(0))
    print("OK")

    assurance_output = run(
        [sys.executable, "-m", "unittest", "assurance.test_reference_core"],
        cwd=root,
        env=env,
        capture=True,
    )
    assurance_summary = re.search(r"^Ran \d+ tests? in .+$", assurance_output, re.MULTILINE)
    if not assurance_summary or not re.search(r"^OK$", assurance_output, re.MULTILINE):
        print(assurance_output, end="" if assurance_output.endswith("\n") else "\n")
        raise GateFailure("independent Core assurance tests did not report a successful run")
    print("Independent assurance " + assurance_summary.group(0))
    print("OK")

    rows: dict[str, tuple[int, int, str]] = {}
    for line in output.splitlines():
        match = TRACE_ROW.match(line)
        if match:
            rows[match.group("module")] = (
                int(match.group("lines")),
                int(match.group("percent")),
                match.group("path"),
            )

    expected = python_source_modules(package_dir)
    missing = expected - rows.keys()
    extra = rows.keys() - expected
    if missing or extra:
        details = []
        if missing:
            details.append("unmeasured Python modules: " + ", ".join(sorted(missing)))
        if extra:
            details.append("unexpected Python modules: " + ", ".join(sorted(extra)))
        raise GateFailure("; ".join(details))

    failed: list[str] = []
    total_lines = 0
    for module in sorted(expected):
        executable_lines, percent, _ = rows[module]
        total_lines += executable_lines
        print(f"Python {module}: {percent}% ({executable_lines} executable lines)")
        if percent < PYTHON_MIN_LINE_PERCENT:
            failed.append(f"{module} is {percent}%; requires {PYTHON_MIN_LINE_PERCENT}%")
    if failed:
        raise GateFailure("Python coverage threshold failed: " + "; ".join(failed))
    print(
        f"Python line gate passed: all {len(expected)} modules, "
        f"{total_lines} executable lines at {PYTHON_MIN_LINE_PERCENT}% or higher."
    )
    print("Python branch coverage is not measured by this gate.")


def latest_fresh_tix(root: Path, suite: str, started_ns: int) -> Path:
    candidates = [
        path
        for path in (root / "dist-newstyle").rglob(f"{suite}.tix")
        if path.parent.name == "tix"
        and path.parent.parent.name == "vanilla"
        and len(path.parents) > 3
        and path.parents[3].name == suite
        and path.stat().st_mtime_ns >= started_ns
    ]
    if len(candidates) != 1:
        found = ", ".join(str(path) for path in candidates) or "none"
        raise GateFailure(f"expected one fresh {suite} HPC file; found {len(candidates)}: {found}")
    return candidates[0]


def declared_haskell_suites(root: Path) -> set[str]:
    cabal_file = root / "semantic-oracle.cabal"
    declared = set(re.findall(r"^test-suite\s+([A-Za-z0-9_-]+)\s*$", cabal_file.read_text(), re.MULTILINE))
    expected = set(HASKELL_SUITES)
    if declared != expected:
        raise GateFailure(
            "Haskell test suites declared in semantic-oracle.cabal do not match the gate; "
            f"missing from gate: {', '.join(sorted(declared - expected)) or 'none'}; "
            f"no longer declared: {', '.join(sorted(expected - declared)) or 'none'}"
        )
    return declared


def declared_haskell_modules(root: Path) -> set[str]:
    return {
        ".".join(source.relative_to(source_dir).with_suffix("").parts)
        for source_dir in (root / "src", root / "app")
        if source_dir.is_dir()
        for source in source_dir.rglob("*.hs")
    }


def haskell_test_exclusions(root: Path) -> list[str]:
    cabal_file = (root / "semantic-oracle.cabal").read_text()
    name = re.search(r"^name:\s+(\S+)\s*$", cabal_file, re.MULTILINE)
    version = re.search(r"^version:\s+(\S+)\s*$", cabal_file, re.MULTILINE)
    if not name or not version:
        raise GateFailure("cannot identify the Cabal package name and version for HPC filtering")
    package_id = f"{name.group(1)}-{version.group(1)}-inplace"
    test_main_modules = {suite: "Main" for suite in HASKELL_SUITES}
    test_main_modules["isoprax-pool"] = "IsopraxPoolTest"
    return [f"--exclude={package_id}-{suite}:{test_main_modules[suite]}" for suite in HASKELL_SUITES]


def hpc_mix_dirs(root: Path, suite_tix: dict[str, Path]) -> list[Path]:
    build_dir = root / "dist-newstyle" / "build"
    library_mix_dirs = {
        mix_file.parents[1]
        for mix_file in build_dir.rglob("Core.Protocol.mix")
        if mix_file.parent.name.endswith("-inplace")
        and mix_file.parents[1].name == "mix"
        and mix_file.parents[2].name == "vanilla"
        and "extra-compilation-artifacts" in mix_file.parts
    }
    if len(library_mix_dirs) != 1:
        raise GateFailure(
            "expected one Haskell library HPC mix directory; found "
            + (", ".join(map(str, sorted(library_mix_dirs))) or "none")
        )

    mix_dirs = [next(iter(library_mix_dirs))]
    for suite, tix in suite_tix.items():
        suite_dir = tix.parents[3]
        suite_mix_dirs = {
            mix_file.parents[1]
            for mix_file in suite_dir.rglob("Main.mix")
            if mix_file.parent.name.endswith(f"-inplace-{suite}")
            and mix_file.parents[1].name == "mix"
            and mix_file.parents[2].name == "vanilla"
        }
        if len(suite_mix_dirs) != 1:
            raise GateFailure(
                f"expected one {suite} HPC mix directory; found "
                + (", ".join(map(str, sorted(suite_mix_dirs))) or "none")
            )
        mix_dirs.extend(suite_mix_dirs)
    return mix_dirs


def check_haskell(root: Path, output_dir: Path) -> None:
    check_tool_version(root, "ghc", EXPECTED_GHC_VERSION)
    check_tool_version(root, "cabal", EXPECTED_CABAL_VERSION)
    declared_haskell_suites(root)
    test_exclusions = haskell_test_exclusions(root)
    started_ns = time.time_ns()
    run(
        ["cabal", "test", "all", "--enable-coverage", "--test-show-details=direct"],
        cwd=root,
    )

    suite_tix = {
        suite: latest_fresh_tix(root, suite, started_ns)
        for suite in HASKELL_SUITES
    }
    mix_dirs = hpc_mix_dirs(root, suite_tix)
    combined_tix = output_dir / "semadmit-combined.tix"
    run(
        [
            "hpc",
            "sum",
            "--union",
            f"--output={combined_tix}",
            *(str(suite_tix[suite]) for suite in HASKELL_SUITES),
        ],
        cwd=root,
    )
    report = run(
        [
            "hpc",
            "report",
            str(combined_tix),
            *test_exclusions,
            *(f"--hpcdir={mix_dir}" for mix_dir in mix_dirs),
        ],
        cwd=root,
        capture=True,
    )
    print(report, end="" if report.endswith("\n") else "\n")

    module_report = run(
        [
            "hpc",
            "report",
            str(combined_tix),
            "--per-module",
            *test_exclusions,
            *(f"--hpcdir={mix_dir}" for mix_dir in mix_dirs),
        ],
        cwd=root,
        capture=True,
    )
    print(module_report, end="" if module_report.endswith("\n") else "\n")
    measured_modules = set(
        re.findall(r"^-----<module [^/]+/([^>]+)>-----$", module_report, re.MULTILINE)
    )
    expected_modules = declared_haskell_modules(root)
    if measured_modules != expected_modules:
        raise GateFailure(
            "Haskell library modules do not match HPC measurements; "
            f"unmeasured: {', '.join(sorted(expected_modules - measured_modules)) or 'none'}; "
            f"unexpected: {', '.join(sorted(measured_modules - expected_modules)) or 'none'}"
        )

    failures: list[str] = []
    for metric, threshold in (
        ("expressions", HASKELL_MIN_EXPRESSION_PERCENT),
        ("boolean", HASKELL_MIN_BOOLEAN_PERCENT),
    ):
        match = HPC_METRIC[metric].search(report)
        if not match:
            raise GateFailure(f"HPC report is missing its {metric} metric")
        covered, total = map(int, match.groups())
        if total == 0:
            raise GateFailure(f"HPC report has no {metric} points to measure")
        passed = covered * 100 >= threshold * total
        print(
            f"Haskell {metric} gate: {covered}/{total} "
            f"({covered * 100 / total:.2f}%), minimum {threshold}%: "
            f"{'PASS' if passed else 'FAIL'}"
        )
        if not passed:
            failures.append(f"{metric} coverage is below {threshold}%")
    if failures:
        raise GateFailure("Haskell coverage threshold failed: " + "; ".join(failures))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        with tempfile.TemporaryDirectory(prefix="semadmit-coverage-") as temporary:
            output_dir = Path(temporary)
            check_python(root, output_dir / "python")
            check_haskell(root, output_dir)
    except (GateFailure, OSError, subprocess.SubprocessError) as error:
        print(f"Coverage gate failed: {error}", file=sys.stderr)
        return 1
    print("All test and coverage gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
