"""Core evaluation and JSONL checks using an explicitly registered test pack."""

import json
import unittest
from io import BytesIO

from semadmit.evaluator import Admission, Evaluator, JsonlRunner
from semadmit.identity import decision_digest
from semadmit.pack import (
    ArtifactSpec,
    ComponentPayload,
    ComponentSpec,
    Diagnostic,
    NormalizedPackRequest,
    ObligationOutcome,
    OperationDescriptor,
    PackDescriptor,
    PackEvaluation,
    PackIdentity,
    PackInputError,
    PackRegistry,
)


def operation() -> OperationDescriptor:
    return OperationDescriptor(
        subject_roles=("item",),
        policy_artifact=ArtifactSpec("policy", "fixture/0.1/policy", "normalized-policy"),
        subject_artifacts={
            "item": ArtifactSpec("subject", "fixture/0.1/subject", "normalized-subject")
        },
        evidence_artifact=ArtifactSpec("assertion", "fixture/0.1/assertion", "normalized-evidence"),
        components=(
            ComponentSpec(
                "item",
                "name",
                ArtifactSpec("component", "fixture/0.1/component", "component-payload"),
                1,
                1,
            ),
        ),
        obligations=("present",),
        diagnostic_pointers={"domain.mismatch": ("/subjects/item/name",)},
        input_schemas={"policy": {}, "subjects": {}, "evidence": {}},
        validation_order={"policy": ("mode",), "subjects": ("item",), "evidence": ("id",)},
        array_order={"/evidence": "set:id"},
        resource_limits={"evidence_items": 256},
    )


class FixturePack:
    descriptor = PackDescriptor(
        "fixture/0.1", ("semantic-oracle/0.1",), {"check": operation()}
    )

    def validate(
        self, operation_name: str, policy: object, subjects: object, evidence: object
    ) -> NormalizedPackRequest:
        if operation_name != "check":
            raise PackInputError("protocol.unsupported_operation", "/operation")
        if type(policy) is not dict or set(policy) != {"mode"} or policy["mode"] not in {
            "pass",
            "fail",
            "missing",
        }:
            raise PackInputError("policy.unsupported", "/policy")
        if (
            type(subjects) is not dict
            or set(subjects) != {"item"}
            or type(subjects["item"]) is not dict
            or set(subjects["item"]) != {"name"}
            or type(subjects["item"]["name"]) is not str
        ):
            raise PackInputError("input.invalid_type", "/subjects")
        if type(evidence) is not list:
            raise PackInputError("input.invalid_type", "/evidence")
        normalized_evidence: list[object] = []
        seen: set[str] = set()
        for index, item in enumerate(evidence):
            if (
                type(item) is not dict
                or set(item) != {"id", "present"}
                or type(item["id"]) is not str
                or type(item["present"]) is not bool
            ):
                raise PackInputError("input.invalid_type", f"/evidence/{index}")
            if item["id"] in seen:
                raise PackInputError("evidence.duplicate_id", f"/evidence/{index}/id")
            seen.add(item["id"])
            normalized_evidence.append(dict(item))
        return NormalizedPackRequest(dict(policy), {"item": dict(subjects["item"])}, normalized_evidence)

    def decode(self, request: NormalizedPackRequest) -> NormalizedPackRequest:
        return request

    def component_payloads(
        self, request: NormalizedPackRequest, identities: PackIdentity
    ) -> tuple[ComponentPayload, ...]:
        name = request.subjects["item"]["name"]
        return (
            ComponentPayload(
                "item", "name", "component", "fixture/0.1/component", {"name": name}
            ),
        )

    def evaluate(self, operation_name: str, request: NormalizedPackRequest) -> PackEvaluation:
        outcome = request.policy["mode"]
        diagnostics = (
            (Diagnostic("present", "/subjects/item/name", "domain.mismatch"),)
            if outcome == "fail"
            else ()
        )
        return PackEvaluation((ObligationOutcome("present", outcome),), diagnostics)


def request(mode: str = "pass", evidence: list[object] | None = None) -> dict[str, object]:
    operation_descriptor = FixturePack.descriptor.operations["check"]
    policy = {"mode": mode}
    digest = PackIdentity(operation_descriptor).digest("policy", "fixture/0.1/policy", policy)
    return {
        "protocol": "semantic-oracle/0.1",
        "pack": "fixture/0.1",
        "operation": "check",
        "policy_digest": digest,
        "policy": policy,
        "subjects": {"item": {"name": "example"}},
        "evidence": evidence if evidence is not None else [{"id": "z", "present": True}, {"id": "a", "present": False}],
    }


class EvaluatorChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = Evaluator(PackRegistry((FixturePack(),)))

    def test_evaluates_bound_and_sorted_decision(self) -> None:
        result = self.evaluator.evaluate(request())
        self.assertEqual(result["kind"], "decision")
        payload = result["payload"]
        self.assertEqual(payload["state"], "admissible")
        self.assertEqual([entry["id"] for entry in payload["bindings"]["evidence"]], ["a", "z"])
        self.assertEqual(
            result["decision_digest"], decision_digest(payload)
        )
        reversed_result = self.evaluator.evaluate(
            request(evidence=[{"id": "a", "present": False}, {"id": "z", "present": True}])
        )
        self.assertEqual(result, reversed_result)

    def test_fail_and_missing_states_and_policy_digest_mismatch(self) -> None:
        failed = self.evaluator.evaluate(request("fail", []))
        missing = self.evaluator.evaluate(request("missing", []))
        self.assertEqual(failed["payload"]["state"], "inadmissible")
        self.assertEqual(missing["payload"]["state"], "indeterminate")
        self.assertTrue(self.evaluator.verify_result(request("fail", []), failed))
        self.assertTrue(self.evaluator.verify_result(request("missing", []), missing))
        self.assertEqual(len(failed["payload"]["diagnostics"]), 1)
        invalid = request()
        invalid["policy_digest"] = "sha256:" + "0" * 64
        self.assertEqual(
            self.evaluator.evaluate(invalid),
            {"kind": "error", "code": "identity.digest_mismatch", "pointer": "/policy_digest"},
        )

    def test_pack_errors_and_verification_fail_closed(self) -> None:
        unsupported = request()
        unsupported["policy"] = {"mode": "other"}
        self.assertEqual(
            self.evaluator.evaluate(unsupported),
            {"kind": "error", "code": "policy.unsupported", "pointer": "/policy"},
        )
        candidate = self.evaluator.evaluate(request())
        self.assertIsInstance(self.evaluator.verify(request(), candidate), Admission)
        self.assertIsNone(self.evaluator.verify(request("fail", []), candidate))
        altered = dict(candidate)
        altered["decision_digest"] = "sha256:" + "0" * 64
        self.assertIsNone(self.evaluator.verify(request(), altered))

    def test_jsonl_runner_recovers_per_line_and_after_oversize(self) -> None:
        valid_line = json.dumps(request(), separators=(",", ":")).encode("utf-8")
        sink = BytesIO()
        status = JsonlRunner(self.evaluator).run(BytesIO(valid_line + b"\n{"), sink)
        self.assertEqual(status, 3)
        records = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["kind"], "decision")
        self.assertEqual(records[1]["code"], "input.invalid_json")

        sink = BytesIO()
        oversized = b"x" * (10 * 1024 * 1024 + 2) + b"\n"
        status = JsonlRunner(self.evaluator).run(BytesIO(oversized + valid_line + b"\n"), sink)
        self.assertEqual(status, 3)
        records = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["code"], "limit.exceeded")
        self.assertEqual(records[1]["kind"], "decision")

    def test_jsonl_runner_returns_highest_decision_severity(self) -> None:
        requests = [request("pass"), request("fail"), request("missing")]
        source = b"\n".join(
            json.dumps(item, separators=(",", ":")).encode("utf-8") for item in requests
        )
        sink = BytesIO()
        status = JsonlRunner(self.evaluator).run(BytesIO(source), sink)
        self.assertEqual(status, 2)
        records = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(
            [record["payload"]["state"] for record in records],
            ["admissible", "inadmissible", "indeterminate"],
        )

    def test_jsonl_runner_fails_closed_on_invalid_status_resolver(self) -> None:
        valid_line = json.dumps(request(), separators=(",", ":")).encode("utf-8")
        sink = BytesIO()
        runner = JsonlRunner(self.evaluator, lambda _result: 5)
        self.assertEqual(runner.run(BytesIO(valid_line + b"\n" + valid_line), sink), 4)
        records = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["code"], "internal.failure")


if __name__ == "__main__":
    unittest.main()
