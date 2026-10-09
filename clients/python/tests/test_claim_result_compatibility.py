"""Compatibility and fail-closed checks for the claim result boundary."""

import json
import unittest
from io import BytesIO
from pathlib import Path

from semadmit import ClaimEngine, claim_jsonl_runner

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _ROOT / "conformance/fixtures/claim-verification-cases.json"
_COMPATIBILITY = _ROOT / "conformance/fixtures/bouleusis-compatibility.json"
_MATRIX = _ROOT / "conformance/fixtures/claim-consumer-compatibility-matrix.json"


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
            (("verification_digest",), "sha256:bad"),
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

        unexpected = json.loads(json.dumps(result))
        unexpected["unexpected"] = True
        self.assertFalse(self.engine.verify_result(request, unexpected))

        changed_request = json.loads(json.dumps(request))
        changed_request["claim"]["id"] = "different-claim"
        self.assertFalse(self.engine.verify_result(changed_request, result))

        changed_evidence = json.loads(json.dumps(request))
        changed_evidence["evidence"][0]["id"] = "substituted-evidence"
        self.assertFalse(self.engine.verify_result(changed_evidence, result))

        changed_policy = json.loads(json.dumps(request))
        changed_policy["policy"]["admission_profile"] = "strict/0.2"
        self.assertFalse(self.engine.verify_result(changed_policy, result))

    def test_result_verification_uses_strict_canonical_json_types(self) -> None:
        request = cases()[1]["request"]
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification"]["counterexample"]["input"], 1)
        candidate = json.loads(json.dumps(result))
        candidate["verification"]["counterexample"]["input"] = True
        self.assertFalse(self.engine.verify_result(request, candidate))

        self.assertEqual(result["verification"]["counterexample"]["required_lower_bound"], 0)
        candidate = json.loads(json.dumps(result))
        candidate["verification"]["counterexample"]["required_lower_bound"] = False
        self.assertFalse(self.engine.verify_result(request, candidate))

        candidate = json.loads(json.dumps(result))
        candidate["verification"]["counterexample"]["claim_id"] = "\ud800"
        self.assertFalse(self.engine.verify_result(request, candidate))

    def test_claim_jsonl_rejects_ambiguous_json(self) -> None:
        source = BytesIO(
            b'{"protocol":"semadmit/claim/0.1","protocol":"semadmit/claim/0.1"}\n'
            b'{"value":"\\ud800"}\n'
        )
        sink = BytesIO()
        self.assertEqual(claim_jsonl_runner(self.engine).run(source, sink), 3)
        results = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(
            [(item["code"], item["pointer"]) for item in results],
            [("input.duplicate_key", "/protocol"), ("input.invalid_unicode", "")],
        )

    def test_bouleusis_compatibility_record_matches_verified_fixture(self) -> None:
        record = json.loads(_COMPATIBILITY.read_text(encoding="utf-8"))
        matrix = json.loads(_MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "semadmit-bouleusis-compatibility/0.1")
        self.assertEqual(record["semadmit_commit"], "de61aa87a5f4470fd64de33c926cff7f92cf8bd6")
        self.assertEqual(record["protocol"], "semadmit/claim/0.1")
        self.assertEqual(record["core_protocol"], "semantic-oracle/0.1")
        self.assertEqual(record["compatible_bouleusis_contract"], "semadmit/claim-result-consumer/0.1")
        self.assertEqual(record["result_verification"], "PASS")
        self.assertEqual(matrix["minimum_reviewed_semadmit_commit"], record["semadmit_commit"])
        self.assertEqual(matrix["protocols"]["claim_request"], record["protocol"])
        self.assertEqual(matrix["protocols"]["core_request_and_decision"], record["core_protocol"])
        self.assertEqual(matrix["compatible_bouleusis_contract"], record["compatible_bouleusis_contract"])
        self.assertEqual(matrix["verification_api"]["call"], record["verification_api"])
        self.assertEqual(matrix["python_runtime"], ">=3.13,<3.14")
        self.assertEqual(matrix["normative_claim_cases"], [case["id"] for case in cases()])
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

        unsupported = json.loads(json.dumps(request))
        unsupported["protocol"] = "semadmit/claim/0.0"
        error = self.engine.evaluate(unsupported)
        self.assertEqual(set(error), {"kind", "code", "pointer"})
        self.assertEqual(error["kind"], "error")
        self.assertEqual(error["pointer"], "/protocol")
