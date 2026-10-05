"""Focused checks against the approved M0 canonical identity vectors."""

import json
import unittest
from pathlib import Path

from semadmit.identity import artifact_digest, canonical_bytes, decision_digest


_VECTORS = Path(__file__).resolve().parents[3] / "conformance/fixtures/m0-identity-vectors.json"
_RFC_VECTORS = Path(__file__).resolve().parents[3] / "conformance/fixtures/rfc8785-vectors.json"


class IdentityVectors(unittest.TestCase):
    def test_canonical_bytes_and_digests(self) -> None:
        vectors = json.loads(_VECTORS.read_text(encoding="utf-8"))["vectors"]
        for vector in vectors:
            with self.subTest(vector=vector["id"]):
                value = vector["value"]
                self.assertEqual(canonical_bytes(value), vector["canonical_utf8"].encode("utf-8"))
                if vector.get("kind"):
                    self.assertEqual(
                        artifact_digest(value["kind"], value["schema"], value["payload"]),
                        vector["sha256"],
                    )
                elif vector["id"] == "measurement-admissible-decision":
                    self.assertEqual(decision_digest(value), vector["sha256"])

    def test_rejects_unsupported_values(self) -> None:
        for value in (0.5, 1 << 53, "\ud800", {1: "not a string key"}):
            with self.subTest(value=repr(value)), self.assertRaises((TypeError, ValueError)):
                canonical_bytes(value)

    def test_published_jcs_property_order(self) -> None:
        cases = json.loads(_RFC_VECTORS.read_text(encoding="utf-8"))["cases"]
        case = next(item for item in cases if item["id"] == "section-3-2-3-property-order-and-utf8")
        value = json.loads(case["input_json_utf8"])
        self.assertEqual(canonical_bytes(value), case["expected_canonical_utf8"].encode("utf-8"))

    def test_boolean_is_not_encoded_as_integer(self) -> None:
        self.assertEqual(canonical_bytes([True, False, 0, 1]), b"[true,false,0,1]")

    def test_depth_is_bounded(self) -> None:
        value: object = None
        for _ in range(65):
            value = [value]
        with self.assertRaises(ValueError):
            canonical_bytes(value)


if __name__ == "__main__":
    unittest.main()
