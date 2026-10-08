"""Compatibility and fail-closed checks for the claim result boundary."""

import json
import unittest
from pathlib import Path

from semadmit import ClaimEngine

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _ROOT / "conformance/fixtures/claim-verification-cases.json"
_COMPATIBILITY = _ROOT / "conformance/fixtures/bouleusis-compatibility.json"


def cases() -> list[dict[str, object]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]


class ClaimResultCompatibilityChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ClaimEngine()

    def test_result_verification_rejects_changed_bindings_and_status(self) -> None:
        request = cases()[0]["request"]
        result = self.engine.evaluate(request)
        mutations = (
            (("protocol",), "semadmit/claim/0.0"),
            (("result_id",), "sha256:" + "0" * 64),
            (("claim_id",), "different-claim"),
            (("evidence_ids",), []),
            (("verification_status",), "INVALID"),
            (("admission_status",), "INADMISSIBLE"),
            (("verification_digest",), "sha256:" + "0" * 64),
            (("verification", "evidence_ids"), []),
            (("core_decision", "decision_digest"), "sha256:" + "0" * 64),
            (("core_decision", "payload", "bindings", "components", 0, "digest"), "sha256:" + "0" * 64),
        )
        for path, replacement in mutations:
            candidate = json.loads(json.dumps(result))
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(path=path):
                self.assertFalse(self.engine.verify_result(request, candidate))

        changed_request = json.loads(json.dumps(request))
        changed_request["claim"]["id"] = "different-claim"
        self.assertFalse(self.engine.verify_result(changed_request, result))

    def test_result_verification_uses_strict_canonical_json_types(self) -> None:
        request = cases()[1]["request"]
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification"]["counterexample"]["input"], 1)
        candidate = json.loads(json.dumps(result))
        candidate["verification"]["counterexample"]["input"] = True
        self.assertFalse(self.engine.verify_result(request, candidate))

    def test_bouleusis_compatibility_record_matches_verified_fixture(self) -> None:
        record = json.loads(_COMPATIBILITY.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "semadmit-bouleusis-compatibility/0.1")
        self.assertEqual(record["semadmit_commit"], "6ba07d119a62fa99cfb9ec875321bff7b4bd57d1")
        self.assertEqual(record["protocol"], "semadmit/claim/0.1")
        self.assertEqual(record["core_protocol"], "semantic-oracle/0.1")
        self.assertEqual(record["compatible_bouleusis_contract"], "semadmit/claim-result-consumer/0.1")
        self.assertEqual(record["result_verification"], "PASS")
        request = cases()[0]["request"]
        result = self.engine.evaluate(request)
        self.assertEqual(
            set(result),
            {
                "kind",
                "protocol",
                "result_id",
                "claim_id",
                "evidence_ids",
                "verification_status",
                "admission_status",
                "verification_digest",
                "verification",
                "core_decision",
            },
        )
        self.assertEqual(result["protocol"], record["protocol"])
        core = result["core_decision"]
        self.assertEqual(set(core), {"kind", "payload", "decision_digest"})
        self.assertEqual(
            set(core["payload"]),
            {
                "protocol",
                "pack",
                "operation",
                "request_digest",
                "policy_digest",
                "state",
                "bindings",
                "obligations",
                "diagnostics",
            },
        )
        self.assertTrue(self.engine.verify_result(request, result))
