"""Seeded conformance properties for the independent fixture-pack oracle."""

from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from assurance.reference_core import (
    ReferenceError,
    artifact_digest,
    canonical_bytes,
    evaluate,
    verify_result,
)
from semadmit.evaluator import Evaluator, JsonlRunner
from semadmit.pack import PackRegistry
from clients.python.tests.test_evaluator import FixturePack


_ROOT = Path(__file__).resolve().parents[1]
_VECTORS = _ROOT / "test/integration/vertical_slice/vectors.json"
_IDENTITIES = _ROOT / "conformance/fixtures/m0-identity-vectors.json"
_RFC = _ROOT / "conformance/fixtures/rfc8785-vectors.json"
_SEED = 20261009


def _request(mode: str, name: str, evidence: list[object]) -> dict[str, object]:
    policy = {"mode": mode}
    return {
        "protocol": "semantic-oracle/0.1",
        "pack": "fixture/0.1",
        "operation": "check",
        "policy_digest": artifact_digest("policy", "fixture/0.1/policy", policy),
        "policy": policy,
        "subjects": {"item": {"name": name}},
        "evidence": evidence,
    }


def _reverse_object_keys(value: object) -> object:
    if type(value) is dict:
        return {key: _reverse_object_keys(member) for key, member in reversed(list(value.items()))}
    if type(value) is list:
        return [_reverse_object_keys(member) for member in value]
    return value


class ReferenceCoreChecks(unittest.TestCase):
    def test_static_cross_language_vectors_are_independently_derived(self) -> None:
        vectors = json.loads(_VECTORS.read_text(encoding="utf-8"))
        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(evaluate(case["request"]), case["expected"])

    def test_identity_examples_match_reviewed_bytes_not_production_helpers(self) -> None:
        vectors = json.loads(_IDENTITIES.read_text(encoding="utf-8"))["vectors"]
        for vector in vectors:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(
                    canonical_bytes(vector["value"]),
                    vector["canonical_utf8"].encode("utf-8"),
                )

        rfc_cases = json.loads(_RFC.read_text(encoding="utf-8"))["cases"]
        property_order = next(
            case for case in rfc_cases if case["id"] == "section-3-2-3-property-order-and-utf8"
        )
        self.assertEqual(
            canonical_bytes(json.loads(property_order["input_json_utf8"])),
            property_order["expected_canonical_utf8"].encode("utf-8"),
        )

    def test_hand_derived_canonical_bytes_and_digest(self) -> None:
        value = {"a": 1, "b": True, "c": "é"}
        self.assertEqual(canonical_bytes(value), b'{"a":1,"b":true,"c":"\xc3\xa9"}')
        self.assertEqual(canonical_bytes([True, False, 0, 1]), b"[true,false,0,1]")
        self.assertEqual(canonical_bytes(9007199254740991), b"9007199254740991")
        with self.assertRaises(ValueError):
            canonical_bytes(9007199254740992)
        self.assertEqual(
            artifact_digest("test", "test/0.1", {"a": 1}),
            "sha256:0c53b83eb21f5e9251900337e7590241e4213721c9c0b306a5baaaa7dc06d321",
        )

    def test_seeded_valid_requests_differentially_match_python_core(self) -> None:
        rng = random.Random(_SEED)
        evaluator = Evaluator(PackRegistry((FixturePack(),)))
        names = ["plain", "café", "cafe\u0301", "λ", "𐐷", "東京"]
        modes = ["pass", "fail", "missing", "partial", "mixed"]
        for case_index in range(96):
            identifiers = [f"evidence-{case_index}-{offset}" for offset in range(rng.randrange(5))]
            evidence = [
                {"id": identifier, "present": bool(rng.getrandbits(1))}
                for identifier in identifiers
            ]
            rng.shuffle(evidence)
            request = _request(rng.choice(modes), rng.choice(names), evidence)
            with self.subTest(seed=_SEED, case=case_index):
                expected = evaluate(request)
                actual = evaluator.evaluate(request)
                self.assertEqual(actual, expected)
                self.assertEqual(evaluator.evaluate(request), actual)
                self.assertEqual(evaluate(request), expected)

    def test_metamorphic_identity_and_verification_properties(self) -> None:
        request = _request(
            "pass", "café", [{"id": "β", "present": True}, {"id": "a", "present": False}]
        )
        result = evaluate(request)
        production = Evaluator(PackRegistry((FixturePack(),)))
        self.assertTrue(production.verify_result(request, result))
        reordered = dict(reversed(list(request.items())))
        reordered["evidence"] = list(reversed(request["evidence"]))
        self.assertEqual(evaluate(reordered), result)
        self.assertTrue(verify_result(request, result))
        reordered_result = _reverse_object_keys(result)
        self.assertTrue(verify_result(request, reordered_result))
        self.assertTrue(production.verify_result(request, reordered_result))
        tampered = {**result, "decision_digest": "sha256:" + "0" * 64}
        self.assertFalse(verify_result(reordered, tampered))
        self.assertFalse(production.verify_result(request, tampered))

        changed = _request(
            "pass", "cafe\u0301", [{"id": "β", "present": True}, {"id": "a", "present": False}]
        )
        changed_result = evaluate(changed)
        self.assertNotEqual(result["payload"]["request_digest"], changed_result["payload"]["request_digest"])
        self.assertNotEqual(
            result["payload"]["bindings"]["components"],
            changed_result["payload"]["bindings"]["components"],
        )
        self.assertFalse(verify_result(changed, result))
        self.assertFalse(production.verify_result(changed, result))
        self.assertFalse(verify_result({**request, "operation": "other"}, result))

        altered = json.loads(json.dumps(result))
        altered["payload"]["policy_digest"] = "sha256:" + "0" * 64
        self.assertFalse(verify_result(request, altered))
        self.assertFalse(production.verify_result(request, altered))

    def test_internal_error_envelope_is_closed(self) -> None:
        evaluator = Evaluator(PackRegistry((FixturePack(),)))
        source = json.dumps(_request("pass", "x", []), separators=(",", ":")).encode()
        from io import BytesIO

        sink = BytesIO()
        runner = JsonlRunner(evaluator, lambda _result: 5)
        self.assertEqual(runner.run(BytesIO(source), sink), 4)
        self.assertEqual(
            json.loads(sink.getvalue()),
            {"kind": "error", "code": "internal.failure", "pointer": ""},
        )

    def test_supported_error_cases_fail_closed(self) -> None:
        base = _request("pass", "item", [])
        cases = []
        unsupported = dict(base)
        unsupported["protocol"] = "semantic-oracle/9.9"
        cases.append((unsupported, "protocol.unsupported_version", "/protocol"))
        duplicate = dict(base)
        duplicate["evidence"] = [{"id": "x", "present": True}, {"id": "x", "present": False}]
        cases.append((duplicate, "evidence.duplicate_id", "/evidence/1/id"))
        wrong_digest = dict(base)
        wrong_digest["policy_digest"] = "sha256:" + "0" * 64
        cases.append((wrong_digest, "identity.digest_mismatch", "/policy_digest"))
        extra = dict(base)
        extra["unexpected"] = None
        cases.append((extra, "input.unknown_field", "/unexpected"))
        bool_integer = dict(base)
        bool_integer["evidence"] = [{"id": "x", "present": 1}]
        cases.append((bool_integer, "input.invalid_type", "/evidence/0"))
        invalid_unicode = dict(base)
        invalid_unicode["subjects"] = {"item": {"name": "\ud800"}}
        cases.append((invalid_unicode, "input.invalid_unicode", ""))
        fractional = dict(base)
        fractional["evidence"] = [{"id": "x", "present": 0.5}]
        cases.append((fractional, "input.number_profile", "/evidence/0/present"))
        for request, code, pointer in cases:
            with self.subTest(code=code):
                self.assertEqual(evaluate(request), {"kind": "error", "code": code, "pointer": pointer})
        with self.assertRaises(ValueError):
            canonical_bytes({"bad": float("nan")})


if __name__ == "__main__":
    unittest.main()
