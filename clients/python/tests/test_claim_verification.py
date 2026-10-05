"""Claim-pack contract, evidence boundaries, and local adapter checks."""

import itertools
import json
import unittest
from io import BytesIO
from pathlib import Path

from semadmit import ClaimEngine, FiniteInvariantPack, claim_jsonl_runner
from semadmit.pack import PackInputError

_FIXTURE = Path(__file__).resolve().parents[3] / "conformance/fixtures/claim-verification-cases.json"


def cases() -> list[dict[str, object]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]


def valid_request() -> dict[str, object]:
    return json.loads(json.dumps(cases()[0]["request"]))


class ClaimVerificationChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ClaimEngine()

    def test_normative_cases_include_status_provenance_and_bound_artifact(self) -> None:
        for case in cases():
            with self.subTest(case=case["id"]):
                request = case["request"]
                expected = case["expected"]
                result = self.engine.evaluate(request)
                self.assertEqual(result["kind"], "claim-result")
                self.assertEqual(result["verification_status"], expected["verification_status"])
                self.assertEqual(result["admission_status"], expected["admission_status"])
                self.assertEqual(result["verification"]["commensurability_result"], expected["commensurability_result"])
                self.assertEqual(result["verification"]["counterexample"], expected["counterexample"])
                self.assertEqual(result["core_decision"]["payload"]["state"], expected["core_state"])
                self.assertEqual(
                    sorted(item["code"] for item in result["verification"]["diagnostics"]),
                    expected["diagnostic_codes"],
                )
                self.assertEqual(result["result_id"], result["core_decision"]["decision_digest"])
                self.assertEqual(
                    result["verification_digest"],
                    result["core_decision"]["payload"]["bindings"]["components"][0]["digest"],
                )
                self.assertEqual(result["verification"]["evidence_ids"], result["evidence_ids"])
                self.assertTrue(self.engine.verify_result(request, result))

    def test_provenance_is_preserved_and_evidence_order_is_canonical(self) -> None:
        request = valid_request()
        evidence = request["evidence"][0]
        result = self.engine.evaluate(request)
        provenance = result["verification"]["provenance"][0]
        for field in (
            "source", "collection_method", "captured_version", "family", "subject_digest",
            "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group",
        ):
            self.assertEqual(provenance[field], evidence[field])

        reversed_request = valid_request()
        reversed_request["claim"]["domain"]["inputs"] = [1, 0, -1]
        reversed_request["evidence"][0]["observations"].reverse()
        self.assertEqual(result, self.engine.evaluate(reversed_request))

    def test_unknown_never_becomes_valid_and_candidate_binding_is_exact(self) -> None:
        unknown = cases()[2]["request"]
        result = self.engine.evaluate(unknown)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertEqual(result["admission_status"], "REQUIRES_SEPARATE_TREATMENT")
        self.assertEqual(result["core_decision"]["payload"]["state"], "indeterminate")
        altered = json.loads(json.dumps(result))
        altered["verification"]["verification_status"] = "VALID"
        self.assertFalse(self.engine.verify_result(unknown, altered))
        self.assertFalse(self.engine.verify_result(unknown, {"kind": "claim-result"}))
        self.assertFalse(self.engine.verify_result(unknown, object()))

    def test_exhaustive_small_domain_oracle(self) -> None:
        base = valid_request()
        domain = [0, 1]
        for outputs in itertools.product((-1, 0, 1), repeat=len(domain)):
            for mask in range(1 << len(domain)):
                observations = [
                    {"input": item, "output": outputs[index]}
                    for index, item in enumerate(domain)
                    if mask & (1 << index)
                ]
                request = json.loads(json.dumps(base))
                request["claim"]["domain"]["inputs"] = domain
                request["evidence"][0]["observations"] = observations
                result = self.engine.evaluate(request)
                has_counterexample = any(output < 0 for output, index in zip(outputs, domain) if mask & (1 << index))
                complete = mask == (1 << len(domain)) - 1
                expected = "INVALID" if has_counterexample else "VALID" if complete else "UNKNOWN"
                self.assertEqual(result["verification_status"], expected)
                self.assertEqual(result, self.engine.evaluate(request))

    def test_closed_schema_rejects_malformed_and_unsupported_inputs(self) -> None:
        request = valid_request()
        request["claim"]["domain"]["inputs"][0] = True
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/claim/domain/inputs/0")

        request = valid_request()
        request["claim"]["id"] = True
        del request["claim"]["subject"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/claim/id")

        request = valid_request()
        request["claim"]["subject"]["function_id"] = 7
        request["claim"]["domain"]["inputs"] = "bad"
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/claim/subject/function_id")

        request = valid_request()
        request["claim"]["subject"]["function_id"] = None
        del request["claim"]["subject"]["version"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/claim/subject/function_id")

        request = valid_request()
        del request["claim"]["subject"]["version"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.missing_field")
        self.assertEqual(error["pointer"], "/claim/subject/version")

        request = valid_request()
        request["claim"]["id"] = False
        with self.assertRaises(PackInputError) as caught:
            FiniteInvariantPack().validate(
                "verify",
                {"admission_profile": "strict/0.1"},
                {"claim": request["claim"]},
                request["evidence"],
            )
        self.assertEqual(caught.exception.code, "input.invalid_type")
        self.assertEqual(caught.exception.pointer, "/subjects/claim/id")

        request = valid_request()
        request["context"]["contract_id"] = None
        del request["context"]["scope"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/context/contract_id")

        request = valid_request()
        request["evidence"][0]["id"] = True
        del request["evidence"][0]["source"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/evidence/0/id")

        request = valid_request()
        request["evidence"][0]["observations"][0]["input"] = None
        del request["evidence"][0]["observations"][0]["output"]
        error = self.engine.evaluate(request)
        self.assertEqual(error["code"], "input.invalid_type")
        self.assertEqual(error["pointer"], "/evidence/0/observations/0/input")

        request = valid_request()
        request["claim"]["extra"] = "rejected"
        self.assertEqual(self.engine.evaluate(request)["code"], "input.unknown_field")

        request = valid_request()
        request["claim"]["domain"]["inputs"] = [0, 0]
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_value")

        request = valid_request()
        request["claim"]["domain"]["inputs"] = [2**53]
        self.assertEqual(self.engine.evaluate(request)["code"], "input.number_profile")

        with self.assertRaises(PackInputError) as caught:
            FiniteInvariantPack().validate(
                "verify",
                {"admission_profile": "strict/0.1"},
                {"claim": request["claim"], "context": request["context"]},
                request["evidence"],
            )
        self.assertEqual(caught.exception.code, "input.invalid_value")

        request = valid_request()
        request["evidence"].append(request["evidence"][0])
        self.assertEqual(self.engine.evaluate(request)["code"], "limit.exceeded")

        request = valid_request()
        request["policy"]["admission_profile"] = "unknown/0.1"
        self.assertEqual(self.engine.evaluate(request)["code"], "policy.unsupported")

        request = valid_request()
        request["claim"]["subject"]["artifact_digest"] = "not-a-digest"
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_value")

        request = valid_request()
        request["claim"]["subject"]["function_id"] = "x" * 1025
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_value")

        request = valid_request()
        request["evidence"][0]["observations"][1]["output"] = True
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_type")

        request = valid_request()
        request["evidence"][0]["observations"].append(request["evidence"][0]["observations"][0])
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_value")

        request = valid_request()
        request["evidence"][0]["observations"][0]["input"] = 99
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_value")

        request = valid_request()
        request["protocol"] = "semadmit/claim/9.9"
        self.assertEqual(self.engine.evaluate(request)["code"], "protocol.unsupported_version")

        request = valid_request()
        request["protocol"] = 1
        self.assertEqual(self.engine.evaluate(request)["code"], "input.invalid_type")

        request = valid_request()
        del request["context"]
        self.assertEqual(self.engine.evaluate(request)["pointer"], "/context")

    def test_descriptor_declares_closed_input_schemas_and_field_order(self) -> None:
        operation = FiniteInvariantPack().descriptor.operations["verify"]
        self.assertEqual(set(operation.input_schemas), {"policy", "subjects", "evidence"})
        self.assertFalse(operation.input_schemas["policy"]["additionalProperties"])
        claim_schema = operation.input_schemas["subjects"]["properties"]["claim"]
        self.assertFalse(claim_schema["additionalProperties"])
        self.assertEqual(
            tuple(claim_schema["required"]),
            ("id", "subject", "predicate", "domain", "assumptions", "expected_evidence_family", "required_verifier"),
        )
        self.assertEqual(
            operation.validation_order["/evidence/*"],
            (
                "id", "source", "collection_method", "captured_version", "family", "subject_digest",
                "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group", "observations",
            ),
        )

    def test_unsupported_and_open_domain_results_stay_unknown(self) -> None:
        request = valid_request()
        request["claim"]["required_verifier"] = "model-checker/0.1"
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertIn("verifier.unsupported", [item["code"] for item in result["verification"]["diagnostics"]])

        request = valid_request()
        request["claim"]["predicate"]["id"] = "integer.output.eq/0.1"
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertIn("verifier.unsupported", [item["code"] for item in result["verification"]["diagnostics"]])

        request = valid_request()
        request["context"]["contract_id"] = "other-contract/0.1"
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertIn("contract.unsupported", [item["code"] for item in result["verification"]["diagnostics"]])

        request = valid_request()
        request["claim"]["domain"]["complete"] = False
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertEqual(
            [item["pointer"] for item in result["core_decision"]["payload"]["diagnostics"]],
            ["/evidence/0/observations", "/subjects/claim/domain/complete"],
        )

        request = valid_request()
        request["claim"]["expected_evidence_family"] = "future-observation/0.1"
        request["evidence"][0]["family"] = "future-observation/0.1"
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertEqual(result["admission_status"], "REQUIRES_SEPARATE_TREATMENT")
        self.assertEqual(result["verification"]["commensurability_result"], "NON_COMMENSURABLE")
        self.assertEqual(
            [item["pointer"] for item in result["verification"]["diagnostics"]],
            ["/subjects/claim/expected_evidence_family"],
        )

    def test_subject_binding_mismatch_is_not_used_as_a_counterexample(self) -> None:
        request = valid_request()
        request["evidence"][0]["subject_digest"] = "sha256:" + "1" * 64
        result = self.engine.evaluate(request)
        self.assertEqual(result["verification_status"], "UNKNOWN")
        self.assertEqual(result["verification"]["commensurability_result"], "NON_COMMENSURABLE")
        self.assertIsNone(result["verification"]["counterexample"])

    def test_missing_and_incompatible_evidence_are_distinct_unknowns(self) -> None:
        by_id = {case["id"]: case["request"] for case in cases()}
        missing = self.engine.evaluate(by_id["missing-evidence-unknown"])
        incompatible = self.engine.evaluate(by_id["family-mismatch-unknown"])
        self.assertEqual(missing["verification_status"], "UNKNOWN")
        self.assertEqual(missing["verification"]["commensurability_result"], "UNKNOWN")
        self.assertEqual(incompatible["verification_status"], "UNKNOWN")
        self.assertEqual(incompatible["verification"]["commensurability_result"], "NON_COMMENSURABLE")
        self.assertIsNone(incompatible["verification"]["counterexample"])

    def test_jsonl_adapter_accepts_the_bouleusis_library_boundary(self) -> None:
        request = valid_request()
        source = BytesIO((json.dumps(request) + "\n{" ).encode("utf-8"))
        sink = BytesIO()
        self.assertEqual(claim_jsonl_runner(self.engine).run(source, sink), 3)
        results = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(results[0]["verification_status"], "VALID")
        self.assertEqual(results[1]["code"], "input.invalid_json")


if __name__ == "__main__":
    unittest.main()
