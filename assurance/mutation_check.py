"""Run a small, bounded source-mutation check against Python Core assurance tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ("test_vertical_slice", "test_evaluator", "assurance.test_reference_core")


@dataclass(frozen=True)
class Mutation:
    name: str
    file: str
    before: str
    after: str


MUTATIONS = (
    Mutation(
        "canonical-result-comparison",
        "evaluator.py",
        "canonical_bytes(copied_candidate) == canonical_bytes(result)",
        "canonical_bytes(copied_candidate.get(\"payload\")) == canonical_bytes(result.get(\"payload\"))",
    ),
    Mutation(
        "request-binding",
        "evaluator.py",
        'request_digest = identities.digest("request", _REQUEST_SCHEMA, request_payload)',
        'request_digest = identities.digest("request", _REQUEST_SCHEMA, {"operation": operation})',
    ),
    Mutation(
        "policy-digest-verification",
        "evaluator.py",
        "if policy_digest != common.supplied_policy_digest:",
        "if False:",
    ),
    Mutation(
        "policy-identity-binding",
        "evaluator.py",
        '"policy": policy,\n                "subjects": subjects,',
        '"policy": {},\n                "subjects": subjects,',
    ),
    Mutation(
        "failure-state-priority",
        "state.py",
        'if any(item.outcome == "fail" for item in ordered):',
        "if False:",
    ),
    Mutation(
        "unsupported-protocol-rejection",
        "protocol.py",
        'if field == "protocol" and member != PROTOCOL_VERSION:',
        "if False:",
    ),
    Mutation(
        "internal-error-envelope",
        "evaluator.py",
        '_INTERNAL_FAILURE = {"kind": "error", "code": "internal.failure", "pointer": ""}',
        '_INTERNAL_FAILURE = {"kind": "error", "code": "internal.failure"}',
    ),
)


def run_tests(package_root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    import_paths = [str(package_root), str(ROOT / "clients/python/tests"), str(ROOT / "clients/python")]
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(import_paths + ([existing] if existing else []))
    return subprocess.run(
        [sys.executable, "-m", "unittest", *TESTS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    production_package = ROOT / "clients/python/semadmit"
    with tempfile.TemporaryDirectory(prefix="semadmit-mutants-") as temporary:
        root = Path(temporary)
        package = root / "semadmit"
        shutil.copytree(production_package, package)
        baseline = run_tests(root)
        if baseline.returncode != 0:
            print(baseline.stdout)
            print("mutation baseline failed; no kill results are valid")
            return 1

        killed: list[str] = []
        for mutation in MUTATIONS:
            source = package / mutation.file
            original = source.read_text(encoding="utf-8")
            if original.count(mutation.before) != 1:
                print(f"{mutation.name}: mutation anchor was not unique")
                return 1
            source.write_text(original.replace(mutation.before, mutation.after), encoding="utf-8")
            result = run_tests(root)
            source.write_text(original, encoding="utf-8")
            if result.returncode == 0:
                print(f"SURVIVED: {mutation.name}")
                return 1
            if "Ran " not in result.stdout or "FAILED (" not in result.stdout:
                print(f"invalid mutant run for {mutation.name}:\n{result.stdout}")
                return 1
            killed.append(mutation.name)
            print(f"KILLED: {mutation.name}")

        print(f"mutation score: {len(killed)}/{len(MUTATIONS)} ({100 * len(killed) // len(MUTATIONS)}%)")
        print("scope: seven selected Python Core mutations; no Haskell source mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
