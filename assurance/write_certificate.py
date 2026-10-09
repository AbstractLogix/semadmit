"""Write the machine-readable report for a completed local assurance run."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import re
import subprocess
import sys
import unittest
from pathlib import Path

from assurance.mutation_check import MUTATIONS


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CI_WORKFLOW_NAME = "Coverage"
REQUIRED_CI_WORKFLOW_DATABASE_ID = 375788046
MANDATORY_LOCAL_GATES = ("seeded_corpus", "source_mutation", "test_and_coverage")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tool_version(*command: str) -> str | None:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        ).stdout.strip().splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def checked_gate(name: str, command: list[str]) -> tuple[str, dict[str, object]]:
    print(f"$ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    if not result.stdout.strip():
        raise RuntimeError(f"{name} produced no execution log")
    log = result.stdout.encode("utf-8")
    return result.stdout, {
        "name": name,
        "argv": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stdout_bytes": len(log),
        "stdout_sha256": sha256_bytes(log),
    }


def expected_python_test_counts() -> tuple[int, int, int]:
    package_tests = ROOT / "clients/python/tests"
    added_paths = [str(ROOT / "clients/python"), str(package_tests)]
    inserted_paths = []
    for path in reversed(added_paths):
        if path not in sys.path:
            sys.path.insert(0, path)
            inserted_paths.append(path)
    try:
        package_suite = unittest.defaultTestLoader.discover(
            str(package_tests), pattern="test*.py"
        )
        reference_suite = unittest.defaultTestLoader.loadTestsFromName(
            "assurance.test_reference_core"
        )
        certificate_suite = unittest.defaultTestLoader.loadTestsFromName(
            "assurance.test_certificate"
        )
        return (
            package_suite.countTestCases(),
            reference_suite.countTestCases(),
            certificate_suite.countTestCases(),
        )
    finally:
        for path in inserted_paths:
            if path in sys.path:
                sys.path.remove(path)


def parse_python_test_counts(coverage_output: str) -> list[int]:
    counts = [int(count) for count in re.findall(r"\bRan (\d+) tests? in ", coverage_output)]
    if len(counts) != 3:
        raise RuntimeError("coverage output did not report all three Python test counts")
    if tuple(counts) != expected_python_test_counts():
        raise RuntimeError("Python test counts do not match discovered test cases")
    return counts


def test_constant(name: str) -> object:
    source = ast.parse((ROOT / "assurance/test_reference_core.py").read_text(encoding="utf-8"))
    for statement in source.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise RuntimeError(f"test case count {name} is not declared")


def local_validation() -> tuple[dict[str, int], dict[str, object], list[dict[str, object]]]:
    corpus_command = [sys.executable, "-m", "assurance.generate_corpus", "--check"]
    mutation_command = [sys.executable, "-m", "assurance.mutation_check"]
    coverage_command = [sys.executable, "scripts/check_coverage.py"]
    corpus_output, corpus_log = checked_gate("seeded corpus check", corpus_command)
    if corpus_output.strip() != "seeded assurance corpus matches its generator":
        raise RuntimeError("seeded corpus output is missing or truncated")

    mutation_output, mutation_log = checked_gate("source mutation check", mutation_command)
    killed = re.findall(r"^KILLED: (.+)$", mutation_output, re.MULTILINE)
    expected_mutations = [mutation.name for mutation in MUTATIONS]
    score = re.search(r"^mutation score: (\d+)/(\d+) \((\d+)%\)$", mutation_output, re.MULTILINE)
    if killed != expected_mutations or score is None:
        raise RuntimeError("mutation output does not report every configured mutation as killed")
    if tuple(map(int, score.groups())) != (len(expected_mutations), len(expected_mutations), 100):
        raise RuntimeError("mutation score is not a complete pass")

    coverage_output, coverage_log = checked_gate("test and coverage gates", coverage_command)
    if not coverage_output.rstrip().endswith("All test and coverage gates passed."):
        raise RuntimeError("coverage command exited without its success marker")
    test_counts = parse_python_test_counts(coverage_output)

    core = json.loads((ROOT / "test/integration/vertical_slice/vectors.json").read_text(encoding="utf-8"))
    parser = json.loads((ROOT / "conformance/fixtures/protocol-cases.json").read_text(encoding="utf-8"))
    identities = json.loads((ROOT / "conformance/fixtures/m0-identity-vectors.json").read_text(encoding="utf-8"))
    rfc = json.loads((ROOT / "conformance/fixtures/rfc8785-vectors.json").read_text(encoding="utf-8"))
    differential_request_count = test_constant("SEEDED_DIFFERENTIAL_REQUEST_COUNT")
    selected_rfc_ids = test_constant("SELECTED_RFC8785_VECTOR_IDS")
    if not isinstance(differential_request_count, int) or not isinstance(selected_rfc_ids, tuple):
        raise RuntimeError("seeded test counts have an invalid declaration")
    rfc_ids = {case["id"] for case in rfc["cases"]}
    if not set(selected_rfc_ids).issubset(rfc_ids):
        raise RuntimeError("selected RFC 8785 vector is missing")
    haskell_suites = len(
        re.findall(
            r"^test-suite\s+[A-Za-z0-9_-]+\s*$",
            (ROOT / "semantic-oracle.cabal").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    if haskell_suites == 0:
        raise RuntimeError("no Haskell test suites are declared")

    tests = {
        "python_package_tests": test_counts[0],
        "independent_reference_tests": test_counts[1],
        "certificate_integrity_tests": test_counts[2],
        "haskell_suites": haskell_suites,
        "exact_core_vectors_in_each_language": len(core["cases"]),
        "raw_parser_cases_in_each_language": len(parser["cases"]),
        "raw_parser_errors_in_each_language": sum("error" in case["expected"] for case in parser["cases"]),
        "m0_identity_vectors_in_each_language": len(identities["vectors"]),
        "selected_rfc8785_vectors_in_each_language": len(selected_rfc_ids),
        "seeded_python_differential_requests": differential_request_count,
    }
    mutations = {
        "scope": "selected Python Core mutations only; no Haskell source mutations",
        "killed": len(killed),
        "total": len(expected_mutations),
        "score_percent": 100,
        "mutations": killed,
        "outcomes": {name: "killed" for name in killed},
    }
    gates = [
        {**corpus_log, "name": "seeded_corpus", "description": corpus_log["name"]},
        {**mutation_log, "name": "source_mutation", "description": mutation_log["name"]},
        {**coverage_log, "name": "test_and_coverage", "description": coverage_log["name"]},
    ]
    if tuple(gate["name"] for gate in gates) != MANDATORY_LOCAL_GATES:
        raise RuntimeError("a mandatory local assurance gate did not execute")
    return tests, mutations, gates


def hosted_ci(run_url: str | None, validation_commit: str) -> dict[str, object]:
    if run_url is None:
        raise RuntimeError("a completed hosted Coverage CI run is required")
    match = re.fullmatch(
        r"https://github\.com/AbstractLogix/semadmit/actions/runs/(\d+)(?:/.*)?", run_url
    )
    if match is None:
        raise RuntimeError("CI run URL must point to an AbstractLogix/semadmit GitHub Actions run")
    try:
        output = subprocess.run(
            [
                "gh",
                "run",
                "view",
                match.group(1),
                "--json",
                "url,status,conclusion,headSha,name,workflowDatabaseId",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        ).stdout
        run = json.loads(output)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise RuntimeError(f"hosted Coverage CI evidence is unavailable: {error}") from error
    if run.get("headSha") != validation_commit or run.get("url") != run_url:
        raise RuntimeError("CI run does not match the validation commit and supplied URL")
    if (
        run.get("name") != REQUIRED_CI_WORKFLOW_NAME
        or run.get("workflowDatabaseId") != REQUIRED_CI_WORKFLOW_DATABASE_ID
    ):
        raise RuntimeError("CI run is not the required Coverage workflow")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise RuntimeError("required Coverage CI run is not completed successfully")
    return {
        "status": "passed",
        "run_url": run_url,
        "head_sha": validation_commit,
        "workflow_name": REQUIRED_CI_WORKFLOW_NAME,
        "workflow_database_id": REQUIRED_CI_WORKFLOW_DATABASE_ID,
    }


def require_clean_validation_commit(validation_commit: str, implementation_commit: str) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", implementation_commit, validation_commit],
        cwd=ROOT,
        check=False,
    )
    if head != validation_commit or status or ancestor.returncode != 0:
        raise RuntimeError(
            "validation must run from a clean checkout at a commit descended from the implementation commit"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--validation-commit", required=True)
    parser.add_argument("--ci-run-url", required=True)
    parser.add_argument("--haskell-executable", type=Path, required=True)
    parser.add_argument("--haskell-sdist", type=Path, required=True)
    parser.add_argument("--python-wheel", type=Path, required=True)
    parser.add_argument("--python-sdist", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "assurance/assurance-certificate.json")
    args = parser.parse_args()

    try:
        require_clean_validation_commit(args.validation_commit, args.implementation_commit)
        executed_tests, mutation_results, gates = local_validation()
        ci = hosted_ci(args.ci_run_url, args.validation_commit)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"certificate not written: {error}", file=sys.stderr)
        return 1

    artifacts = {
        "haskell_executable": args.haskell_executable,
        "haskell_source_archive": args.haskell_sdist,
        "python_wheel": args.python_wheel,
        "python_source_archive": args.python_sdist,
    }
    if any(not path.is_file() or path.stat().st_size == 0 for path in artifacts.values()):
        print("every build artifact path must name a non-empty file", file=sys.stderr)
        return 1

    certificate = {
        "format": "semadmit-assurance-certificate/0.1",
        "implementation_commit": args.implementation_commit,
        "validation_commit": args.validation_commit,
        "research_artifact": {
            "title": "Semadmit Core Conformance Oracle and Assurance Corpus",
            "version": "0.1",
            "permalink": f"https://github.com/AbstractLogix/semadmit/tree/{args.implementation_commit}",
            "doi": None,
            "peer_reviewed": False,
        },
        "protocol": "semantic-oracle/0.1",
        "stable_claim_compatibility": {
            "protocol": "semadmit/claim/0.1",
            "bouleusis_pin": "de61aa87a5f4470fd64de33c926cff7f92cf8bd6",
            "claim_status": "qualified; Python-only semantics",
        },
        "selector_provenance": {
            "protocol": "selector-provenance/0.1",
            "status": "experimental",
            "independence_cases": "indeterminate",
        },
        "digests": {
            "reference_oracle_sha256": sha256(ROOT / "assurance/reference_core.py"),
            "corpus_generator_sha256": sha256(ROOT / "assurance/generate_corpus.py"),
            "core_result_corpus_sha256": sha256(ROOT / "test/integration/vertical_slice/vectors.json"),
            "parser_corpus_sha256": sha256(ROOT / "conformance/fixtures/protocol-cases.json"),
            "identity_vectors_sha256": sha256(ROOT / "conformance/fixtures/m0-identity-vectors.json"),
            "rfc8785_vectors_sha256": sha256(ROOT / "conformance/fixtures/rfc8785-vectors.json"),
        },
        "toolchain": {
            "python": platform.python_version(),
            "ghc": tool_version("ghc", "--numeric-version"),
            "cabal": tool_version("cabal", "--numeric-version"),
            "uv": tool_version("uv", "--version"),
            "platform": platform.platform(),
        },
        "executed_tests": executed_tests,
        "source_mutation_results": mutation_results,
        "language_parity": {
            "shared": [
                (
                    f"{executed_tests['exact_core_vectors_in_each_language']} complete "
                    "fixture/0.1/check result or error vectors"
                ),
                (
                    f"{executed_tests['raw_parser_cases_in_each_language']} raw parser cases, "
                    f"including {executed_tests['raw_parser_errors_in_each_language']} error envelopes"
                ),
                f"{executed_tests['m0_identity_vectors_in_each_language']} M0 canonical identity vectors",
                f"{executed_tests['selected_rfc8785_vectors_in_each_language']} selected RFC 8785 property-order vectors",
            ],
            "python_only": [
                "semadmit/claim/0.1 semantics",
                "selector-provenance/0.1 semantics",
                f"{executed_tests['seeded_python_differential_requests']} dynamic seeded differential requests",
            ],
            "reference_scope": "fixture/0.1/check and common safe-integer JSON profile",
        },
        "counterexamples": {
            "count": 0,
            "scope": "listed committed corpus and recorded test runs only",
            "details": [],
        },
        "build_artifact_hashes_sha256": {
            name: sha256(path.resolve()) for name, path in artifacts.items()
        },
        "build_artifact_sizes_bytes": {
            name: path.stat().st_size for name, path in artifacts.items()
        },
        "validation": {
            "local_full_validation": "passed",
            "local_gates": gates,
            "hosted_ci": ci,
        },
        "unsupported_guarantees": [
            "build provenance beyond the recorded artifact byte hashes and toolchain; artifact source binding is not verified",
            "evidence authenticity or collector identity",
            "evidence reliability",
            "claim truth",
            "all Core parser precedence and error-pointer combinations",
            "all Core resource limits and CLI framing in cross-language parity",
            "Haskell parity for claim, selector, Isoprax, or Measurement semantics",
            "formal correctness, exploit resistance, or total defect detection",
            "independent human release approval",
            "release readiness or package publication authorization",
        ],
        "reproduction_commands": [
            "python3 -m assurance.generate_corpus --check",
            "python3 -m assurance.mutation_check",
            "python3 scripts/check_coverage.py",
            "cabal build exe:semantic-oracle",
            "cabal sdist --output-directory=<output-dir>",
            "uv build --out-dir <output-dir> clients/python",
        ],
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(certificate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
