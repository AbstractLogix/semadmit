"""Write the machine-readable report for a completed local assurance run."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    from assurance.source_build import build_source_revision

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--ci-run-url", required=True)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "assurance/assurance-certificate.json"
    )
    args = parser.parse_args()

    try:
        require_clean_validation_commit(args.source_revision, args.source_revision)
        ci = hosted_ci(args.ci_run_url, args.source_revision)
        evidence = build_source_revision(ROOT, args.source_revision, args.artifacts_dir)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"certificate not written: {error}", file=sys.stderr)
        return 1

    run_id = re.search(r"/actions/runs/(\d+)", str(ci["run_url"]))
    if run_id is None:
        print("certificate not written: hosted CI run id is invalid", file=sys.stderr)
        return 1
    certificate = {
        "format": "semadmit-assurance-certificate/0.2",
        "protocol_scope": {
            "claim_protocol": "semadmit/claim/0.1",
            "claim_status": "qualified; Python-only semantics",
            "bouleusis_pin": "de61aa87a5f4470fd64de33c926cff7f92cf8bd6",
            "core_protocol": "semantic-oracle/0.1",
            "selector_protocol": "selector-provenance/0.1",
            "selector_status": "experimental; bounded independence outcomes remain indeterminate",
        },
        "source": {
            **evidence["source"],
            "source_date_epoch": evidence["source_date_epoch"],
            "locked_inputs_sha256": evidence["locked_inputs_sha256"],
            "build_inputs_sha256": evidence["build_inputs_sha256"],
        },
        "build": {
            "toolchain": evidence["toolchain"],
            "commands": evidence["commands"],
            "environment": evidence["environment"],
            "artifacts": evidence["artifacts"],
            "provenance": {
                "method": "clean-source-rebuild",
                "authenticated": False,
                "ci_execution_identity": {
                    "authentication": "recorded-unverified",
                    "run_id": run_id.group(1),
                    "run_url": f"https://github.com/AbstractLogix/semadmit/actions/runs/{run_id.group(1)}",
                    "head_sha": args.source_revision,
                    "workflow_name": ci["workflow_name"],
                    "workflow_database_id": ci["workflow_database_id"],
                    "status": ci["status"],
                },
            },
        },
        "validation": evidence["validation"],
        "unsupported_guarantees": [
            "authenticated CI identity or authenticated build provenance",
            "evidence authenticity or collector identity",
            "evidence reliability or claim truth",
            "scientific validity or general functional correctness",
            "complete Core parity or Haskell claim-pack semantics",
            "independent human release approval or distribution authorization",
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
