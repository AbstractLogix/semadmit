"""Registration checks for the public trusted-pack boundary."""

import unittest
from dataclasses import replace

from semadmit.pack import (
    ArtifactSpec,
    OperationDescriptor,
    PackDescriptor,
    PackIdentity,
    PackRegistry,
)
from semadmit import PackRegistry as PublicPackRegistry


def descriptor(pack_id: str = "example/0.1") -> PackDescriptor:
    operation = OperationDescriptor(
        subject_roles=("item",),
        policy_artifact=ArtifactSpec("policy", f"{pack_id}/policy", "normalized-policy"),
        subject_artifacts={"item": ArtifactSpec("subject", f"{pack_id}/subject", "normalized-subject")},
        evidence_artifact=None,
        components=(),
        obligations=("example.present",),
        diagnostic_pointers={"example.missing": ("/subjects/item",)},
        input_schemas={"policy": {}, "subjects": {}, "evidence": {}},
        validation_order={"policy": ("mode",)},
        array_order={"/evidence": "set:id"},
        resource_limits={"evidence_items": 0},
    )
    return PackDescriptor(pack_id, ("semantic-oracle/0.1",), {"check": operation})


class DummyPack:
    def __init__(self, pack_id: str = "example/0.1") -> None:
        self.descriptor = descriptor(pack_id)

    def validate(self, operation: str, policy: object, subjects: object, evidence: object) -> object:
        raise NotImplementedError

    def decode(self, request: object) -> object:
        raise NotImplementedError

    def component_payloads(self, request: object, identities: object) -> object:
        raise NotImplementedError

    def evaluate(self, operation: str, request: object) -> object:
        raise NotImplementedError


class PackRegistryChecks(unittest.TestCase):
    def test_pack_registration_types_are_exported(self) -> None:
        self.assertIs(PublicPackRegistry, PackRegistry)

    def test_exact_registration_and_scoped_identity(self) -> None:
        pack = DummyPack()
        registry = PackRegistry((pack,))
        registered = registry.get("example/0.1")
        self.assertIsNotNone(registered)
        self.assertIsNone(registry.get("example/0.2"))
        assert registered is not None
        identities = PackIdentity(registered.descriptor.operations["check"])
        self.assertTrue(identities.digest("policy", "example/0.1/policy", {}).startswith("sha256:"))
        self.assertTrue(identities.digest("request", "semantic-oracle/0.1/request", {}).startswith("sha256:"))
        with self.assertRaises(ValueError):
            identities.digest("policy", "another/0.1/policy", {})

    def test_rejects_invalid_and_duplicate_ids(self) -> None:
        for pack_id in ("Example/0.1", "example/00.1", "example/0.01", "example/0.1/extra"):
            with self.subTest(pack_id=pack_id), self.assertRaises(ValueError):
                PackRegistry((DummyPack(pack_id),))
        with self.assertRaises(ValueError):
            PackRegistry((DummyPack(), DummyPack()))

    def test_rejects_incomplete_descriptor(self) -> None:
        pack = DummyPack()
        operation = pack.descriptor.operations["check"]
        pack.descriptor = replace(pack.descriptor, operations={"check": replace(operation, obligations=())})
        with self.assertRaises(ValueError):
            PackRegistry((pack,))

    def test_rejects_undeclared_identity_projection(self) -> None:
        pack = DummyPack()
        operation = pack.descriptor.operations["check"]
        altered = replace(operation, policy_artifact=replace(operation.policy_artifact, projection=""))
        pack.descriptor = replace(pack.descriptor, operations={"check": altered})
        with self.assertRaises(ValueError):
            PackRegistry((pack,))

    def test_rejects_invalid_diagnostic_pointer_declaration(self) -> None:
        pack = DummyPack()
        operation = pack.descriptor.operations["check"]
        pack.descriptor = replace(
            pack.descriptor,
            operations={"check": replace(operation, diagnostic_pointers={"bad": ("/item~2",)})},
        )
        with self.assertRaises(ValueError):
            PackRegistry((pack,))


if __name__ == "__main__":
    unittest.main()
