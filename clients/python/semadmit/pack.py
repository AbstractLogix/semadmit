"""Trusted, explicitly registered Python pack boundary for v0.1."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from semadmit.identity import artifact_digest

_PACK_ID = re.compile(r"[a-z][a-z0-9-]{0,62}/(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", re.ASCII)
_OUTCOMES = frozenset(("pass", "fail", "missing"))


def _valid_pointer(pointer: str) -> bool:
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False
    index = 0
    while index < len(pointer):
        if pointer[index] == "~":
            if index + 1 == len(pointer) or pointer[index + 1] not in "01":
                return False
            index += 2
        else:
            index += 1
    return True


def _freeze_schema(value: object) -> object:
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("descriptor schema keys must be strings")
        return MappingProxyType({key: _freeze_schema(member) for key, member in value.items()})
    if type(value) in (list, tuple):
        return tuple(_freeze_schema(member) for member in value)
    if type(value) in (str, int, bool) or value is None:
        return value
    raise TypeError("descriptor schemas must be JSON-shaped data")


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    kind: str
    schema: str
    projection: str


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    subject_role: str
    name: str
    artifact: ArtifactSpec
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class OperationDescriptor:
    subject_roles: tuple[str, ...]
    policy_artifact: ArtifactSpec
    subject_artifacts: Mapping[str, ArtifactSpec]
    evidence_artifact: ArtifactSpec | None
    components: tuple[ComponentSpec, ...]
    obligations: tuple[str, ...]
    diagnostic_pointers: Mapping[str, tuple[str, ...]]
    input_schemas: Mapping[str, object]
    validation_order: Mapping[str, tuple[str, ...]]
    array_order: Mapping[str, str]
    resource_limits: Mapping[str, int]
    allowed_outcomes: frozenset[str] = _OUTCOMES

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_roles", tuple(self.subject_roles))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "obligations", tuple(self.obligations))
        object.__setattr__(self, "allowed_outcomes", frozenset(self.allowed_outcomes))
        object.__setattr__(self, "subject_artifacts", MappingProxyType(dict(self.subject_artifacts)))
        object.__setattr__(self, "input_schemas", _freeze_schema(dict(self.input_schemas)))
        for name in ("diagnostic_pointers", "validation_order"):
            values = {key: tuple(items) for key, items in getattr(self, name).items()}
            object.__setattr__(self, name, MappingProxyType(values))
        for name in ("array_order", "resource_limits"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True, slots=True)
class PackDescriptor:
    pack_id: str
    protocol_versions: tuple[str, ...]
    operations: Mapping[str, OperationDescriptor]

    def __post_init__(self) -> None:
        object.__setattr__(self, "protocol_versions", tuple(self.protocol_versions))
        object.__setattr__(self, "operations", MappingProxyType(dict(self.operations)))


@dataclass(frozen=True, slots=True)
class NormalizedPackRequest:
    policy: object
    subjects: object
    evidence: object


@dataclass(frozen=True, slots=True)
class ComponentPayload:
    subject_role: str
    name: str
    kind: str
    schema: str
    payload: object


@dataclass(frozen=True, slots=True)
class ObligationOutcome:
    id: str
    outcome: str


@dataclass(frozen=True, slots=True)
class Diagnostic:
    obligation_id: str
    pointer: str
    code: str


@dataclass(frozen=True, slots=True)
class PackEvaluation:
    obligations: tuple[ObligationOutcome, ...]
    diagnostics: tuple[Diagnostic, ...]


class PackInputError(Exception):
    def __init__(self, code: str, pointer: str) -> None:
        self.code = code
        self.pointer = pointer
        super().__init__(f"{code} at {pointer}")


class Pack[InputT](Protocol):
    descriptor: PackDescriptor

    def validate(
        self, operation: str, policy: object, subjects: object, evidence: object
    ) -> NormalizedPackRequest: ...

    def decode(self, request: NormalizedPackRequest) -> InputT: ...

    def component_payloads(
        self, request: InputT, identities: PackIdentity
    ) -> Sequence[ComponentPayload]: ...

    def evaluate(self, operation: str, request: InputT) -> PackEvaluation: ...


class PackIdentity:
    """Core-owned digest service limited to the selected operation's artifacts."""

    def __init__(self, operation: OperationDescriptor) -> None:
        specs = [operation.policy_artifact, *operation.subject_artifacts.values()]
        if operation.evidence_artifact is not None:
            specs.append(operation.evidence_artifact)
        specs.extend(component.artifact for component in operation.components)
        self._allowed = frozenset(
            {("request", "semantic-oracle/0.1/request")}
            | {(spec.kind, spec.schema) for spec in specs}
        )

    def digest(self, kind: str, schema: str, payload: object) -> str:
        if (kind, schema) not in self._allowed:
            raise ValueError("undeclared artifact kind/schema pair")
        return artifact_digest(kind, schema, payload)


@dataclass(frozen=True, slots=True)
class RegisteredPack:
    pack: Pack[Any]
    descriptor: PackDescriptor


class PackRegistry:
    """An immutable registry of trusted pack instances selected by exact ID."""

    def __init__(self, packs: Iterable[Pack[Any]]) -> None:
        registered: dict[str, RegisteredPack] = {}
        for pack in packs:
            methods = ("validate", "decode", "component_payloads", "evaluate")
            if any(not callable(getattr(pack, method, None)) for method in methods):
                raise ValueError("pack does not implement the public call boundary")
            descriptor = pack.descriptor
            if not isinstance(descriptor, PackDescriptor):
                raise ValueError("pack descriptor has the wrong type")
            _validate_descriptor(descriptor)
            if descriptor.pack_id in registered:
                raise ValueError(f"duplicate pack ID: {descriptor.pack_id}")
            registered[descriptor.pack_id] = RegisteredPack(pack, descriptor)
        self._registered = MappingProxyType(registered)

    def get(self, pack_id: str) -> RegisteredPack | None:
        return self._registered.get(pack_id)


def _validate_descriptor(descriptor: PackDescriptor) -> None:
    if type(descriptor.pack_id) is not str or _PACK_ID.fullmatch(descriptor.pack_id) is None:
        raise ValueError("invalid pack ID")
    if not descriptor.protocol_versions or any(type(version) is not str for version in descriptor.protocol_versions):
        raise ValueError("invalid protocol versions")
    if len(set(descriptor.protocol_versions)) != len(descriptor.protocol_versions):
        raise ValueError("duplicate protocol version")
    if any(version != "semantic-oracle/0.1" for version in descriptor.protocol_versions):
        raise ValueError("unsupported protocol version in descriptor")
    if not descriptor.operations:
        raise ValueError("pack must declare an operation")
    for name, operation in descriptor.operations.items():
        if type(name) is not str or not name or not isinstance(operation, OperationDescriptor):
            raise ValueError("invalid operation declaration")
        if not operation.subject_roles or any(type(role) is not str or not role for role in operation.subject_roles):
            raise ValueError("invalid subject roles")
        if len(set(operation.subject_roles)) != len(operation.subject_roles):
            raise ValueError("duplicate subject role")
        if set(operation.subject_artifacts) != set(operation.subject_roles):
            raise ValueError("subject artifact roles do not match")
        if not operation.obligations or any(type(item) is not str or not item for item in operation.obligations):
            raise ValueError("invalid obligation set")
        if len(set(operation.obligations)) != len(operation.obligations):
            raise ValueError("duplicate obligation")
        if not operation.allowed_outcomes or not operation.allowed_outcomes <= _OUTCOMES:
            raise ValueError("invalid outcome set")
        if set(operation.input_schemas) != {"policy", "subjects", "evidence"} or not operation.validation_order:
            raise ValueError("closed schemas and validation order are required")
        if any(type(code) is not str or not code or not pointers for code, pointers in operation.diagnostic_pointers.items()):
            raise ValueError("invalid diagnostic declaration")
        if any(
            not isinstance(pointer, str) or not _valid_pointer(pointer)
            for pointers in operation.diagnostic_pointers.values()
            for pointer in pointers
        ):
            raise ValueError("invalid diagnostic pointer")
        if any(type(path) is not str or not path or type(order) is not str or not order
               for path, order in operation.array_order.items()):
            raise ValueError("invalid array ordering declaration")
        if any(not isinstance(component, ComponentSpec) for component in operation.components):
            raise ValueError("invalid component declaration")
        specs = [operation.policy_artifact, *operation.subject_artifacts.values()]
        if operation.evidence_artifact is not None:
            specs.append(operation.evidence_artifact)
        specs.extend(component.artifact for component in operation.components)
        if any(not isinstance(spec, ArtifactSpec) for spec in specs):
            raise ValueError("invalid artifact declaration")
        if any(type(spec.kind) is not str or not spec.kind or type(spec.schema) is not str
               or not spec.schema.startswith(descriptor.pack_id + "/") for spec in specs):
            raise ValueError("artifact schema must be namespaced by pack version")
        if operation.policy_artifact.projection != "normalized-policy":
            raise ValueError("policy identity projection is undeclared")
        if any(spec.projection != "normalized-subject" for spec in operation.subject_artifacts.values()):
            raise ValueError("subject identity projection is undeclared")
        if operation.evidence_artifact is not None and operation.evidence_artifact.projection != "normalized-evidence":
            raise ValueError("evidence identity projection is undeclared")
        if any(component.artifact.projection != "component-payload" for component in operation.components):
            raise ValueError("component identity projection is undeclared")
        seen_components: set[tuple[str, str]] = set()
        for component in operation.components:
            key = (component.subject_role, component.name)
            if component.subject_role not in operation.subject_roles or type(component.name) is not str or not component.name or key in seen_components:
                raise ValueError("invalid component declaration")
            if type(component.minimum) is not int or type(component.maximum) is not int:
                raise ValueError("invalid component cardinality")
            if component.minimum < 0 or component.maximum < component.minimum:
                raise ValueError("invalid component cardinality")
            seen_components.add(key)
        if any(type(key) is not str or not key or type(value) is not int or value < 0
               for key, value in operation.resource_limits.items()):
            raise ValueError("negative pack resource limit")
        if operation.resource_limits.get("evidence_items", 0) > 256:
            raise ValueError("pack evidence limit exceeds Core limit")
