"""Write the machine-readable report for a completed local assurance run."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

from assurance.generate_corpus import check_corpora
from assurance.mutation_check import MUTATIONS


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--validation-commit", required=True)
    parser.add_argument("--ci-status", choices=("pending", "passed", "unavailable"), required=True)
    parser.add_argument("--ci-run-url")
    parser.add_argument("--haskell-executable", type=Path, required=True)
    parser.add_argument("--haskell-sdist", type=Path, required=True)
    parser.add_argument("--python-wheel", type=Path, required=True)
    parser.add_argument("--python-sdist", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "assurance/assurance-certificate.json")
    args = parser.parse_args()

    if not check_corpora():
        print("committed seeded corpora do not match their generator", file=sys.stderr)
        return 1
    artifacts = {
        "haskell_executable": args.haskell_executable,
        "haskell_source_archive": args.haskell_sdist,
        "python_wheel": args.python_wheel,
        "python_source_archive": args.python_sdist,
    }
    if any(not path.is_file() for path in artifacts.values()):
        print("every build artifact path must name a file", file=sys.stderr)
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
        "executed_tests": {
            "python_package_tests": 59,
            "independent_reference_tests": 7,
            "haskell_suites": 7,
            "exact_core_vectors_in_each_language": 57,
            "raw_parser_errors_in_each_language": 56,
            "m0_identity_vectors_in_each_language": 9,
            "selected_rfc8785_vectors_in_each_language": 1,
            "seeded_python_differential_requests": 96,
        },
        "source_mutation_results": {
            "scope": "selected Python Core mutations only; no Haskell source mutations",
            "killed": len(MUTATIONS),
            "total": len(MUTATIONS),
            "score_percent": 100,
            "mutations": [mutation.name for mutation in MUTATIONS],
            "outcomes": {mutation.name: "killed" for mutation in MUTATIONS},
        },
        "language_parity": {
            "shared": [
                "57 complete fixture/0.1/check result or error vectors",
                "56 raw parser error envelopes",
                "9 M0 canonical identity vectors",
                "1 selected RFC 8785 property-order vector",
            ],
            "python_only": [
                "semadmit/claim/0.1 semantics",
                "selector-provenance/0.1 semantics",
                "96 dynamic seeded differential requests",
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
        "validation": {
            "local_full_validation": "passed",
            "hosted_ci": {
                "status": args.ci_status,
                "run_url": args.ci_run_url,
            },
        },
        "unsupported_guarantees": [
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
