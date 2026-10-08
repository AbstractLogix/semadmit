"""Conformance and fail-closed checks for selector-provenance admission."""

from __future__ import annotations

import copy
import json
import unittest
from io import BytesIO
from pathlib import Path

from semadmit.evaluator import Evaluator, JsonlRunner
from semadmit.pack import NormalizedPackRequest, PackIdentity, PackInputError, PackRegistry
from semadmit.selector_provenance import (
    OPERATION,
    RULE_VERSION,
    SelectorProvenancePack,
)


_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _ROOT / "conformance/fixtures/selector-independence-cases.json"
_SHARED_RELATIONS = (
    "shared_model",
    "shared_encoder",
    "shared_training_lineage",
    "shared_source",
)


def cases() -> list[dict[str, object]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]


def with_policy_digest(request: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(request)
    pack = SelectorProvenancePack()
    normalized = pack.validate(
        result["operation"],
        result["policy"],
        result["subjects"],
        result["evidence"],
    )
    operation = pack.descriptor.operations[OPERATION]
    result["policy_digest"] = PackIdentity(operation).digest(
        operation.policy_artifact.kind,
        operation.policy_artifact.schema,
        normalized.policy,
    )
    return result


def rationale_codes(result: dict[str, object]) -> list[str]:
    payload = result["payload"]
    return [item["code"] for item in payload["diagnostics"]]


class SelectorProvenanceChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = SelectorProvenancePack()
        self.evaluator = Evaluator(PackRegistry((self.pack,)))

    def test_bounded_independence_fixture(self) -> None:
        fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["format"], "semadmit-selector-independence-cases/0.1")
        self.assertEqual(fixture["implementation"], "python")
        self.assertEqual(fixture["pack"], "selector-provenance/0.1")
        self.assertEqual(fixture["operation"], OPERATION)
        self.assertEqual(fixture["rule_version"], RULE_VERSION)
        self.assertEqual(len(fixture["cases"]), 4)

        for case in cases():
            request = with_policy_digest(case["request"])
            self.assertEqual(request["policy_digest"], case["request"]["policy_digest"])
            result = self.evaluator.evaluate(request)
            with self.subTest(case=case["id"]):
                self.assertEqual(result["kind"], "decision")
                payload = result["payload"]
                self.assertEqual(payload["state"], case["expected"]["state"])
                self.assertEqual(rationale_codes(result), case["expected"]["rationale_codes"])
                self.assertEqual(payload["operation"], OPERATION)
                self.assertTrue(self.evaluator.verify_result(request, result))
                self.assertIsNone(self.evaluator.verify(request, result))

    def test_result_verifier_binds_selector_request_and_result(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        result = self.evaluator.evaluate(request)
        changed_request = copy.deepcopy(request)
        changed_request["evidence"][0]["selector"]["version"] = "v2"
        self.assertFalse(self.evaluator.verify_result(changed_request, result))

        changed_result = copy.deepcopy(result)
        changed_result["decision_digest"] = "sha256:" + "0" * 64
        self.assertFalse(self.evaluator.verify_result(request, changed_result))
        self.assertFalse(self.evaluator.verify_result(request, None))
        self.assertFalse(self.evaluator.verify_result({"invalid": True}, result))

    def test_relevance_score_is_bound_but_does_not_grant_admission(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        result = self.evaluator.evaluate(request)
        higher_score_request = copy.deepcopy(request)
        higher_score_request["evidence"][0]["selector"]["ranking_score"] = "1000000"
        higher_score_result = self.evaluator.evaluate(higher_score_request)

        self.assertEqual(result["payload"]["state"], "indeterminate")
        self.assertEqual(higher_score_result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(result), rationale_codes(higher_score_result))
        self.assertNotEqual(
            result["payload"]["request_digest"],
            higher_score_result["payload"]["request_digest"],
        )
        self.assertNotEqual(
            result["payload"]["bindings"]["evidence"][0]["digest"],
            higher_score_result["payload"]["bindings"]["evidence"][0]["digest"],
        )

    def test_missing_and_unknown_selector_provenance_stays_unknown(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        missing = copy.deepcopy(request)
        del missing["evidence"][0]["selector"]
        missing_result = self.evaluator.evaluate(missing)
        self.assertEqual(missing_result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(missing_result), ["provenance.missing"])

        unknown = copy.deepcopy(request)
        unknown["evidence"][0]["selector"] = {"id": "unknown", "type": "unknown"}
        unknown_result = self.evaluator.evaluate(unknown)
        self.assertEqual(unknown_result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(unknown_result), ["provenance.missing"])

        no_consumer = copy.deepcopy(request)
        no_consumer["policy"]["consumer"]["model_id"] = None
        no_consumer["policy_digest"] = with_policy_digest(no_consumer)["policy_digest"]
        no_consumer_result = self.evaluator.evaluate(no_consumer)
        self.assertEqual(rationale_codes(no_consumer_result), ["provenance.missing"])

    def test_explicit_unknown_relation_is_preserved(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        for evidence in request["evidence"]:
            evidence["selector"]["consumer_relation"] = "unknown"
        result = self.evaluator.evaluate(request)
        self.assertEqual(result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(result), ["dependence.unknown"])

        unknown_dependency = with_policy_digest(cases()[0]["request"])
        for evidence in unknown_dependency["evidence"]:
            evidence["selector"]["upstream_dependencies"] = [
                {"id": "dependency-1", "relation": "unknown"}
            ]
        dependency_result = self.evaluator.evaluate(unknown_dependency)
        self.assertEqual(rationale_codes(dependency_result), ["dependence.unknown"])

    def test_shared_model_is_preserved_without_automatic_rejection(self) -> None:
        request = with_policy_digest(cases()[1]["request"])
        result = self.evaluator.evaluate(request)
        self.assertEqual(result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(result), ["dependence.shared_model"])
        self.assertEqual(
            request["evidence"][0]["selector"]["model_id"],
            request["policy"]["consumer"]["model_id"],
        )
        self.assertTrue(self.evaluator.verify_result(request, result))

        incomplete = with_policy_digest(cases()[3]["request"])
        del incomplete["evidence"][0]["source"]
        incomplete_result = self.evaluator.evaluate(incomplete)
        self.assertEqual(
            rationale_codes(incomplete_result),
            [
                "dependence.shared_model",
                "dependence.shared_source",
                "provenance.missing",
            ],
        )

    def test_shared_upstream_relations_are_reported_in_fixed_order(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        for relation in _SHARED_RELATIONS:
            candidate = copy.deepcopy(request)
            for item in candidate["evidence"]:
                item["selector"]["upstream_dependencies"] = [
                    {"id": f"shared-{relation}", "relation": relation}
                ]
            candidate["policy_digest"] = with_policy_digest(candidate)["policy_digest"]
            result = self.evaluator.evaluate(candidate)
            self.assertEqual(
                rationale_codes(result), [f"dependence.{relation}"], relation
            )
            self.assertEqual(result["payload"]["state"], "indeterminate")

        shared_corpus = with_policy_digest(cases()[0]["request"])
        for evidence in shared_corpus["evidence"]:
            evidence["selector"]["corpus_identity"] = "same-corpus"
        corpus_result = self.evaluator.evaluate(shared_corpus)
        self.assertEqual(rationale_codes(corpus_result), ["dependence.shared_source"])

    def test_independence_declaration_and_isoprax_rule_do_not_change_truth(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        declared = copy.deepcopy(request)
        for evidence in declared["evidence"]:
            evidence["selector"]["consumer_relation"] = "independent"
        declared_result = self.evaluator.evaluate(declared)
        self.assertEqual(declared_result["payload"]["state"], "indeterminate")
        self.assertEqual(rationale_codes(declared_result), ["independence.unestablished"])

        with_rule = copy.deepcopy(request)
        with_rule["policy"]["assumptions"] = ["assumption-1"]
        with_rule["policy"]["isoprax_rule"] = {
            "id": "isoprax/operation-rule",
            "version": "0.1",
            "digest": "sha256:" + "3" * 64,
        }
        with_rule["policy_digest"] = with_policy_digest(with_rule)["policy_digest"]
        result = self.evaluator.evaluate(with_rule)
        self.assertEqual(result["payload"]["state"], "indeterminate")
        self.assertTrue(self.evaluator.verify_result(with_rule, result))
        self.assertFalse(self.evaluator.verify_result(request, result))

    def test_closed_schema_and_invalid_values_fail_as_core_errors(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        mutations = (
            lambda value: value.update(operation="other"),
            lambda value: value["policy"].update(rule_version="selector-independence/9.9"),
            lambda value: value["policy"].update(extra=True),
            lambda value: value["policy"].update(context=None),
            lambda value: value["policy"].update(assumptions="not-an-array"),
            lambda value: value["policy"].update(
                isoprax_rule={"id": "rule", "version": "v1", "digest": "bad"}
            ),
            lambda value: value["subjects"]["target"].update(kind="fact"),
            lambda value: value["subjects"]["target"].update(digest="bad"),
            lambda value: value.update(evidence=value["evidence"][:1]),
            lambda value: value["evidence"][0].update(digest="bad"),
            lambda value: value["evidence"][0].update(extra=True),
            lambda value: value["evidence"][0].update(source=7),
            lambda value: value["evidence"][0]["selector"].update(ranking_score="00.99"),
            lambda value: value["evidence"][0]["selector"].update(rank=True),
            lambda value: value["evidence"][0]["selector"].update(consumer_relation="maybe"),
            lambda value: value["evidence"][0]["selector"].update(
                upstream_dependencies=[{"id": "x", "relation": "maybe"}]
            ),
        )
        for mutate in mutations:
            invalid = copy.deepcopy(request)
            mutate(invalid)
            result = self.evaluator.evaluate(invalid)
            self.assertEqual(result["kind"], "error")
            self.assertNotEqual(result["code"], "internal.failure")

        self.assertEqual(
            self.evaluator.evaluate(
                {
                    **request,
                    "evidence": "not-an-array",
                }
            )["kind"],
            "error",
        )

    def test_pack_validation_errors_are_stable_and_batch_continues(self) -> None:
        request = with_policy_digest(cases()[0]["request"])
        invalid_cases = (
            (
                "shape",
                lambda value: value["policy"].update(extra=True),
                "input.invalid_value",
                "/policy",
            ),
            (
                "digest",
                lambda value: value["subjects"]["target"].update(digest="bad"),
                "input.invalid_value",
                "/subjects/target/digest",
            ),
            (
                "relation",
                lambda value: value["evidence"][0]["selector"].update(
                    consumer_relation="maybe"
                ),
                "input.invalid_value",
                "/evidence/0/selector/consumer_relation",
            ),
            (
                "rule",
                lambda value: value["policy"].update(
                    rule_version="selector-independence/9.9"
                ),
                "policy.unsupported",
                "/policy/rule_version",
            ),
            (
                "count",
                lambda value: value.update(evidence=value["evidence"][:1]),
                "input.invalid_value",
                "/evidence",
            ),
            (
                "operation",
                lambda value: value.update(operation="other"),
                "protocol.unsupported_operation",
                "/operation",
            ),
        )
        for name, mutate, code, pointer in invalid_cases:
            with self.subTest(case=name):
                invalid = copy.deepcopy(request)
                mutate(invalid)
                self.assertEqual(
                    self.evaluator.evaluate(invalid),
                    {"kind": "error", "code": code, "pointer": pointer},
                )

        invalid = copy.deepcopy(request)
        invalid["evidence"][0]["selector"]["consumer_relation"] = "maybe"
        source = BytesIO(
            b"\n".join(
                json.dumps(item, separators=(",", ":")).encode("utf-8")
                for item in (invalid, request)
            )
            + b"\n"
        )
        sink = BytesIO()
        self.assertEqual(JsonlRunner(self.evaluator).run(source, sink), 3)
        records = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["code"], "input.invalid_value")
        self.assertEqual(records[1]["kind"], "decision")

    def test_pack_is_fail_closed_when_called_with_malformed_normalized_data(self) -> None:
        result = self.pack.evaluate(
            OPERATION,
            NormalizedPackRequest(policy=None, subjects=None, evidence=None),
        )
        self.assertEqual(result.diagnostics[0].code, "provenance.missing")
        with self.assertRaises(PackInputError) as error:
            self.pack.validate("unsupported", {}, {}, [])
        self.assertEqual(error.exception.code, "input.invalid_value")
        self.assertEqual(error.exception.pointer, "/operation")
        self.assertEqual(RULE_VERSION, "selector-independence/0.1")


if __name__ == "__main__":
    unittest.main()
