"""Closed common-envelope checks before pack-specific validation."""

import unittest

from semadmit.json_input import InputProblem, parse_json_bytes
from semadmit.pack import PackRegistry
from semadmit.protocol import validate_common
from test_pack_registry import DummyPack


def request() -> dict[str, object]:
    return {
        "protocol": "semantic-oracle/0.1",
        "pack": "example/0.1",
        "operation": "check",
        "policy_digest": "sha256:" + "0" * 64,
        "policy": {},
        "subjects": {"item": {}},
        "evidence": [],
    }


class CommonEnvelopeChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PackRegistry((DummyPack(),))

    def test_accepts_closed_common_envelope(self) -> None:
        value = parse_json_bytes(b'{"protocol":"semantic-oracle/0.1","pack":"example/0.1",'
                                 b'"operation":"check","policy_digest":"sha256:' + b'0' * 64 +
                                 b'","policy":{},"subjects":{"item":{}},"evidence":[]}')
        common = validate_common(value, self.registry)
        self.assertEqual(common.pack.descriptor.pack_id, "example/0.1")
        self.assertEqual(common.operation, "check")

    def test_unknown_and_missing_common_fields(self) -> None:
        value = request()
        value["a/b"] = 1
        with self.assertRaises(InputProblem) as caught:
            validate_common(value, self.registry)
        self.assertEqual(caught.exception.envelope(),
                         {"kind": "error", "code": "input.unknown_field", "pointer": "/a~1b"})
        del value["a/b"]
        del value["operation"]
        with self.assertRaises(InputProblem) as caught:
            validate_common(value, self.registry)
        self.assertEqual(caught.exception.envelope(),
                         {"kind": "error", "code": "input.missing_field", "pointer": "/operation"})

    def test_exact_dispatch_and_digest_shape(self) -> None:
        for field, member, code in (
            ("protocol", "semantic-oracle/0.2", "protocol.unsupported_version"),
            ("pack", "example/0.2", "protocol.unsupported_pack"),
            ("operation", "other", "protocol.unsupported_operation"),
            ("policy_digest", "SHA256:bad", "input.invalid_value"),
        ):
            value = request()
            value[field] = member
            with self.subTest(field=field), self.assertRaises(InputProblem) as caught:
                validate_common(value, self.registry)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(caught.exception.pointer, "/" + field)


if __name__ == "__main__":
    unittest.main()
