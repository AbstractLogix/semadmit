"""The closed v0.1 common request envelope and registered-pack dispatch."""

from __future__ import annotations

import re
from dataclasses import dataclass

from semadmit.json_input import InputProblem
from semadmit.pack import OperationDescriptor, PackRegistry, RegisteredPack

PROTOCOL_VERSION = "semantic-oracle/0.1"
_FIELDS = ("protocol", "pack", "operation", "policy_digest", "policy", "subjects", "evidence")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)


@dataclass(frozen=True, slots=True)
class CommonRequest:
    protocol: str
    pack: RegisteredPack
    operation: str
    operation_descriptor: OperationDescriptor
    supplied_policy_digest: str
    policy: dict[str, object]
    subjects: dict[str, object]
    evidence: list[object]


def validate_common(value: object, registry: PackRegistry) -> CommonRequest:
    """Validate only Core's closed envelope; the selected pack validates nested data."""
    if not isinstance(value, dict):
        raise InputProblem("input.invalid_type")
    if any(type(key) is not str for key in value):
        raise InputProblem("input.invalid_type")
    registered: RegisteredPack | None = None
    operation_descriptor: OperationDescriptor | None = None
    extras = set(value) - set(_FIELDS)
    if extras:
        raise InputProblem("input.unknown_field", "/" + min(extras).replace("~", "~0").replace("/", "~1"))
    for field in _FIELDS:
        if field not in value:
            raise InputProblem("input.missing_field", "/" + field)
        member = value[field]
        pointer = "/" + field
        if field in ("protocol", "pack", "operation", "policy_digest"):
            if type(member) is not str:
                raise InputProblem("input.invalid_type", pointer)
        elif field in ("policy", "subjects"):
            if type(member) is not dict:
                raise InputProblem("input.invalid_type", pointer)
        elif type(member) is not list:
            raise InputProblem("input.invalid_type", pointer)
        if field == "evidence" and len(member) > 256:
            raise InputProblem("limit.exceeded", "/evidence/256")
        if field == "protocol" and member != PROTOCOL_VERSION:
            raise InputProblem("protocol.unsupported_version", pointer)
        if field == "pack":
            registered = registry.get(member)
            if registered is None:
                raise InputProblem("protocol.unsupported_pack", pointer)
        if field == "operation":
            assert registered is not None
            operation_descriptor = registered.descriptor.operations.get(member)
            if operation_descriptor is None:
                raise InputProblem("protocol.unsupported_operation", pointer)
        if field == "policy_digest" and _DIGEST.fullmatch(member) is None:
            raise InputProblem("input.invalid_value", pointer)
    assert registered is not None and operation_descriptor is not None
    return CommonRequest(
        protocol=value["protocol"],
        pack=registered,
        operation=value["operation"],
        operation_descriptor=operation_descriptor,
        supplied_policy_digest=value["policy_digest"],
        policy=value["policy"],
        subjects=value["subjects"],
        evidence=value["evidence"],
    )
