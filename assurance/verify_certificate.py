"""Independently verify a source-bound Semadmit assurance certificate offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from assurance.source_build import (
    ARTIFACT_KEYS,
    build_source_revision,
    validate_artifact_structure,
)


ROOT = Path(__file__).resolve().parents[1]
FORMAT = "semadmit-assurance-certificate/0.2"
CI_WORKFLOW_NAME = "Coverage"
CI_WORKFLOW_DATABASE_ID = 375788046
BOULEUSIS_PIN = "de61aa87a5f4470fd64de33c926cff7f92cf8bd6"
REQUIRED_ARTIFACT_ARGS = {
    "haskell_executable": "haskell_executable",
    "haskell_source_archive": "haskell_sdist",
    "python_wheel": "python_wheel",
    "python_source_archive": "python_sdist",
}
UNSUPPORTED_GUARANTEES = [
    "authenticated CI identity or authenticated build provenance",
    "evidence authenticity or collector identity",
    "evidence reliability or claim truth",
    "scientific validity or general functional correctness",
    "complete Core parity or Haskell claim-pack semantics",
    "independent human release approval or distribution authorization",
]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_certificate(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"certificate is missing, truncated, or invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("certificate root must be a JSON object")
    return value


def _require_keys(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} has missing or unexpected fields")
    return value


def _digest_file(path: Path) -> tuple[str, int]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"artifact is missing, empty, or not a regular file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _validate_ci_record(value: Any, source_revision: str) -> None:
    ci = _require_keys(
        value,
        {
            "authentication",
            "head_sha",
            "run_id",
            "run_url",
            "status",
            "workflow_database_id",
            "workflow_name",
        },
        "CI identity",
    )
    if ci["authentication"] != "recorded-unverified":
        raise ValueError("CI identity must be labelled recorded-unverified")
    if ci["head_sha"] != source_revision or ci["status"] != "passed":
        raise ValueError("CI identity is stale or does not match the expected source revision")
    if ci["workflow_name"] != CI_WORKFLOW_NAME or ci["workflow_database_id"] != CI_WORKFLOW_DATABASE_ID:
        raise ValueError("CI identity is not for the required Coverage workflow")
    run_id = ci["run_id"]
    run_url = ci["run_url"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("CI run id is invalid")
    if run_url != f"https://github.com/AbstractLogix/semadmit/actions/runs/{run_id}":
        raise ValueError("CI run URL does not match its recorded run id")


def validate_certificate_record(
    certificate: dict[str, Any],
    expected_revision: str,
    rebuilt: dict[str, Any],
    supplied_artifacts: dict[str, Path],
) -> None:
    """Compare every derivable certificate claim with external source and artifact evidence."""
    cert = _require_keys(
        certificate,
        {"build", "format", "protocol_scope", "source", "unsupported_guarantees", "validation"},
        "certificate",
    )
    if cert["format"] != FORMAT:
        raise ValueError("unsupported certificate format")
    source = _require_keys(
        cert["source"],
        {"commit", "tree", "source_date_epoch", "locked_inputs_sha256", "build_inputs_sha256"},
        "source",
    )
    if source.get("commit") != expected_revision or rebuilt["source"].get("commit") != expected_revision:
        raise ValueError("certificate source revision does not match the externally expected revision")
    expected_source = {
        **rebuilt["source"],
        "source_date_epoch": rebuilt["source_date_epoch"],
        "locked_inputs_sha256": rebuilt["locked_inputs_sha256"],
        "build_inputs_sha256": rebuilt["build_inputs_sha256"],
    }
    if source != expected_source:
        raise ValueError("certificate source tree or locked build inputs do not match the Git revision")

    scope = _require_keys(
        cert["protocol_scope"],
        {"claim_protocol", "claim_status", "bouleusis_pin", "core_protocol", "selector_protocol", "selector_status"},
        "protocol scope",
    )
    expected_scope = {
        "claim_protocol": "semadmit/claim/0.1",
        "claim_status": "qualified; Python-only semantics",
        "bouleusis_pin": BOULEUSIS_PIN,
        "core_protocol": "semantic-oracle/0.1",
        "selector_protocol": "selector-provenance/0.1",
        "selector_status": "experimental; bounded independence outcomes remain indeterminate",
    }
    if scope != expected_scope:
        raise ValueError("certificate protocol scope changed or does not match the qualified contract")
    if cert["unsupported_guarantees"] != UNSUPPORTED_GUARANTEES:
        raise ValueError("certificate guarantee limits changed or are incomplete")

    build = _require_keys(
        cert["build"],
        {"artifacts", "commands", "environment", "provenance", "toolchain"},
        "build",
    )
    if build["commands"] != rebuilt["commands"]:
        raise ValueError("certificate build or validation commands do not match the verifier")
    if build["environment"] != rebuilt["environment"]:
        raise ValueError("certificate build environment does not match the offline verifier")
    if build["toolchain"] != rebuilt["toolchain"]:
        raise ValueError("certificate toolchain does not match the offline verifier environment")
    provenance = _require_keys(
        build["provenance"],
        {"authenticated", "ci_execution_identity", "method"},
        "provenance",
    )
    if provenance != {
        "method": "clean-source-rebuild",
        "authenticated": False,
        "ci_execution_identity": provenance.get("ci_execution_identity"),
    }:
        raise ValueError("unsupported or overstated build provenance")
    _validate_ci_record(provenance["ci_execution_identity"], expected_revision)

    artifact_records = _require_keys(build["artifacts"], set(ARTIFACT_KEYS), "artifact records")
    if set(supplied_artifacts) != set(ARTIFACT_KEYS):
        raise ValueError("all four required artifact paths must be supplied")
    if set(rebuilt["artifacts"]) != set(ARTIFACT_KEYS):
        raise ValueError("source rebuild did not produce every required artifact")
    for name in ARTIFACT_KEYS:
        record = _require_keys(
            artifact_records[name], {"filename", "sha256", "size_bytes", "mode"}, name
        )
        expected = rebuilt["artifacts"][name]
        if record != expected:
            raise ValueError(f"certificate artifact record does not match the clean-source rebuild: {name}")
        if supplied_artifacts[name].name != expected["filename"]:
            raise ValueError(f"supplied artifact filename does not match the clean-source rebuild: {name}")
        actual_digest, actual_size = _digest_file(supplied_artifacts[name])
        actual_mode = stat.S_IMODE(supplied_artifacts[name].stat().st_mode)
        if (
            actual_digest != expected["sha256"]
            or actual_size != expected["size_bytes"]
            or actual_mode != expected["mode"]
        ):
            raise ValueError(f"supplied artifact does not match the clean-source rebuild: {name}")
        validate_artifact_structure(name, supplied_artifacts[name], rebuilt["toolchain"]["machine"])

    if cert["validation"] != rebuilt["validation"]:
        raise ValueError("certificate validation results do not match rerun gates")


def verify(
    certificate_path: Path,
    expected_revision: str,
    supplied_artifacts: dict[str, Path],
    repo: Path = ROOT,
) -> None:
    certificate = load_certificate(certificate_path)
    if certificate.get("format") != FORMAT:
        raise ValueError("unsupported certificate format")
    source = certificate.get("source")
    if not isinstance(source, dict) or source.get("commit") != expected_revision:
        raise ValueError("certificate source revision does not match the externally expected revision")
    with tempfile.TemporaryDirectory(prefix="semadmit-offline-verifier-") as temporary:
        rebuilt = build_source_revision(repo, expected_revision, Path(temporary) / "artifacts")
        validate_certificate_record(certificate, expected_revision, rebuilt, supplied_artifacts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    for option, destination in REQUIRED_ARTIFACT_ARGS.items():
        parser.add_argument(f"--{option.replace('_', '-')}", dest=destination, type=Path, required=True)
    args = parser.parse_args()
    artifacts = {name: getattr(args, destination) for name, destination in REQUIRED_ARTIFACT_ARGS.items()}
    try:
        verify(args.certificate, args.source_revision, artifacts)
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
        tarfile.TarError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"offline certificate verification failed: {error}", file=sys.stderr)
        return 1
    print("offline certificate verification passed within clean-source rebuild scope")
    print("CI identity is recorded but unauthenticated; artifact rebuilds and result fields were checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
