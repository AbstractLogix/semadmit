"""Focused byte-parser checks against approved M0 protocol examples."""

import json
import unittest
from pathlib import Path

from semadmit.json_input import InputProblem, copy_json_tree, parse_json_bytes


_CASES = Path(__file__).resolve().parents[3] / "conformance/fixtures/protocol-cases.json"
_RAW_ERROR_CASE_IDS = (
    "duplicate-json-key",
    "invalid-utf8",
    "unpaired-surrogate",
    "invalid-json-syntax",
    "unsupported-number-profile",
    "exponent-number-form",
    "negative-zero-number-form",
    "integer-outside-safe-range",
) + tuple(
    f"assurance-parser-seed-20261009-{kind}-{index:02d}"
    for kind in ("trailing", "number", "duplicate")
    for index in range(16)
)


class JsonInputChecks(unittest.TestCase):
    def test_published_parser_errors(self) -> None:
        cases = json.loads(_CASES.read_text(encoding="utf-8"))["cases"]
        selected = [
            case for case in cases
            if case["input"]["kind"] in {"raw-json-utf8", "raw-bytes-hex"}
        ]
        self.assertEqual(tuple(case["id"] for case in selected), _RAW_ERROR_CASE_IDS)
        for case in selected:
            data = case["input"]
            if data["kind"] == "raw-json-utf8":
                source = data["text"].encode("utf-8")
            elif data["kind"] == "raw-bytes-hex":
                source = bytes.fromhex(data["hex"])
            else:
                self.fail(f"unsupported raw parser fixture kind: {data['kind']}")
            with self.subTest(case=case["id"]), self.assertRaises(InputProblem) as caught:
                parse_json_bytes(source)
            self.assertEqual(caught.exception.envelope(), case["expected"]["error"])

    def test_valid_json_and_escaped_surrogate_pair(self) -> None:
        self.assertEqual(parse_json_bytes(b'{"x":"\\ud83d\\ude00","n":9007199254740991}'),
                         {"x": "😀", "n": 9007199254740991})

    def test_duplicate_pointer_escapes_rfc6901(self) -> None:
        with self.assertRaises(InputProblem) as caught:
            parse_json_bytes(b'{"a/b":{"~":1,"~":2}}')
        self.assertEqual(caught.exception.envelope(),
                         {"kind": "error", "code": "input.duplicate_key", "pointer": "/a~1b/~0"})

    def test_earliest_parser_violation_wins(self) -> None:
        for source, expected in (
            (b'{"a":1,"a":2,"n":0.5}', "input.duplicate_key"),
            (b'{"n":0.5,"a":1,"a":2}', "input.number_profile"),
        ):
            with self.subTest(source=source), self.assertRaises(InputProblem) as caught:
                parse_json_bytes(source)
            self.assertEqual(caught.exception.code, expected)

    def test_evidence_and_depth_limits(self) -> None:
        evidence = b'{"evidence":[' + b','.join([b'0'] * 257) + b']}'
        with self.assertRaises(InputProblem) as caught:
            parse_json_bytes(evidence)
        self.assertEqual(caught.exception.pointer, "/evidence/256")
        nested = b'[' * 65 + b'0' + b']' * 65
        with self.assertRaises(InputProblem) as caught:
            parse_json_bytes(nested)
        self.assertEqual(caught.exception.code, "limit.exceeded")
        self.assertEqual(caught.exception.pointer, "/0" * 64)

    def test_size_and_malformed_numbers(self) -> None:
        with self.assertRaises(InputProblem) as caught:
            parse_json_bytes(b' ' * (10 * 1024 * 1024 + 1))
        self.assertEqual(caught.exception.envelope(),
                         {"kind": "error", "code": "limit.exceeded", "pointer": ""})
        for source in (b'01', b'-00', b'1e', b'1.', b'-0x'):
            with self.subTest(source=source), self.assertRaises(InputProblem) as caught:
                parse_json_bytes(source)
            self.assertEqual(caught.exception.code, "input.invalid_json")

    def test_direct_api_copy_is_bounded_and_detached(self) -> None:
        source = {"subjects": {"item": {"id": "original"}}, "evidence": []}
        copied = copy_json_tree(source)
        source["subjects"]["item"]["id"] = "changed"
        self.assertEqual(copied["subjects"]["item"]["id"], "original")
        with self.assertRaises(InputProblem) as caught:
            copy_json_tree({"evidence": [None] * 257})
        self.assertEqual(caught.exception.envelope(),
                         {"kind": "error", "code": "limit.exceeded", "pointer": "/evidence/256"})
        with self.assertRaises(InputProblem) as caught:
            copy_json_tree({"value": "x" * (10 * 1024 * 1024)})
        self.assertEqual(caught.exception.code, "limit.exceeded")

    def test_direct_api_copy_rejects_non_json_values_and_depth(self) -> None:
        for value, code in ((0.5, "input.number_profile"), (1 << 53, "input.number_profile"),
                            ("\ud800", "input.invalid_unicode"), ({1: "bad key"}, "input.invalid_type")):
            with self.subTest(value=repr(value)), self.assertRaises(InputProblem) as caught:
                copy_json_tree(value)
            self.assertEqual(caught.exception.code, code)
        nested: object = None
        for _ in range(65):
            nested = [nested]
        with self.assertRaises(InputProblem) as caught:
            copy_json_tree(nested)
        self.assertEqual(caught.exception.code, "limit.exceeded")


if __name__ == "__main__":
    unittest.main()
