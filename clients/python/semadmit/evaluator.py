"""Core-owned evaluation, verification, and JSONL execution for registered packs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from types import MappingProxyType
from typing import BinaryIO, Protocol

from semadmit.identity import canonical_bytes, decision_digest
from semadmit.json_input import InputProblem, copy_json_tree, parse_json_bytes
from semadmit.pack import (
    ComponentPayload,
    Diagnostic,
    NormalizedPackRequest,
    PackEvaluation,
    PackIdentity,
    PackInputError,
    PackRegistry,
    RegisteredPack,
    OperationDescriptor,
)
from semadmit.protocol import validate_common
from semadmit.state import InvalidPackOutput, reduce_obligations

_MAX_LINE_BYTES = 10 * 1024 * 1024
_REQUEST_SCHEMA = "semantic-oracle/0.1/request"
_INPUT_CODES = frozenset(
    {
        "input.invalid_type",
        "input.missing_field",
        "input.unknown_field",
        "input.invalid_value",
        "input.number_profile",
        "input.invalid_unicode",
        "input.invalid_utf8",
        "input.invalid_json",
        "input.duplicate_key",
        "policy.unsupported",
        "identity.digest_mismatch",
        "evidence.duplicate_id",
        "evidence.duplicate_role",
        "limit.exceeded",
    }
)
_INTERNAL_FAILURE = {"kind": "error", "code": "internal.failure", "pointer": ""}
_ADMISSION_TOKEN = object()


class Admission:
    """Opaque proof that an admissible candidate matched a local reevaluation."""

    __slots__ = ("_request_snapshot", "_registered_pack", "_operation")

    def __init__(
        self,
        token: object,
        request_snapshot: dict[str, object],
        registered_pack: RegisteredPack,
        operation: str,
    ) -> None:
        if token is not _ADMISSION_TOKEN:
            raise TypeError("Admission values are created only by Evaluator.verify")
        self._request_snapshot = _freeze(request_snapshot)
        self._registered_pack = registered_pack
        self._operation = operation


class Evaluator:
    """Evaluate and verify requests using only an explicitly supplied registry."""

    def __init__(self, registry: PackRegistry) -> None:
        if not isinstance(registry, PackRegistry):
            raise TypeError("Evaluator requires an explicit PackRegistry")
        self._registry = registry

    def evaluate(self, request: object) -> dict[str, object]:
        result, _, _, _ = self._evaluate(request)
        return result

    def verify_result(self, request: object, candidate: object) -> bool:
        """Verify any successful Core decision by deterministic reevaluation."""
        try:
            copied_candidate = copy_json_tree(candidate)
        except InputProblem:
            return False
        if type(copied_candidate) is not dict:
            return False
        result, snapshot, registered, operation = self._evaluate(request)
        return (
            snapshot is not None
            and registered is not None
            and operation is not None
            and result.get("kind") == "decision"
            and canonical_bytes(copied_candidate) == canonical_bytes(result)
        )

    def verify(self, request: object, candidate: object) -> Admission | None:
        try:
            copied_candidate = copy_json_tree(candidate)
        except InputProblem:
            return None
        if type(copied_candidate) is not dict:
            return None
        result, snapshot, registered, operation = self._evaluate(request)
        if snapshot is None or registered is None or operation is None:
            return None
        payload = result.get("payload")
        if result.get("kind") != "decision" or type(payload) is not dict:
            return None
        if payload.get("state") != "admissible" or canonical_bytes(copied_candidate) != canonical_bytes(result):
            return None
        return Admission(_ADMISSION_TOKEN, snapshot, registered, operation)

    def _evaluate(
        self, request: object
    ) -> tuple[dict[str, object], dict[str, object] | None, RegisteredPack | None, str | None]:
        try:
            copied_request = copy_json_tree(request)
            common = validate_common(copied_request, self._registry)
        except InputProblem as problem:
            return problem.envelope(), None, None, None
        except Exception:
            return dict(_INTERNAL_FAILURE), None, None, None

        registered = common.pack
        operation = common.operation
        try:
            normalized = registered.pack.validate(
                operation, common.policy, common.subjects, common.evidence
            )
        except PackInputError as problem:
            if _valid_pack_error(problem):
                return {
                    "kind": "error",
                    "code": problem.code,
                    "pointer": problem.pointer,
                }, None, None, None
            return dict(_INTERNAL_FAILURE), None, None, None
        except Exception:
            return dict(_INTERNAL_FAILURE), None, None, None

        try:
            if not isinstance(normalized, NormalizedPackRequest):
                raise InvalidPackOutput("pack returned the wrong normalized request type")
            copied_normalized = copy_json_tree(
                {
                    "policy": normalized.policy,
                    "subjects": normalized.subjects,
                    "evidence": normalized.evidence,
                }
            )
            if type(copied_normalized) is not dict:
                raise InvalidPackOutput("pack returned an invalid normalized request")
            policy = copied_normalized.get("policy")
            subjects = copied_normalized.get("subjects")
            evidence = copied_normalized.get("evidence")
            if type(policy) is not dict or type(subjects) is not dict or type(evidence) is not list:
                raise InvalidPackOutput("pack returned invalid normalized field types")
            evidence = _sorted_evidence(evidence)

            descriptor = common.operation_descriptor
            identities = PackIdentity(descriptor)
            policy_digest = identities.digest(
                descriptor.policy_artifact.kind,
                descriptor.policy_artifact.schema,
                policy,
            )
            if policy_digest != common.supplied_policy_digest:
                return {
                    "kind": "error",
                    "code": "identity.digest_mismatch",
                    "pointer": "/policy_digest",
                }, None, None, None

            request_payload = {
                "protocol": common.protocol,
                "pack": registered.descriptor.pack_id,
                "operation": operation,
                "policy_digest": policy_digest,
                "policy": policy,
                "subjects": subjects,
                "evidence": evidence,
            }
            request_digest = identities.digest("request", _REQUEST_SCHEMA, request_payload)
            snapshot = dict(request_payload)

            pack_request = NormalizedPackRequest(
                policy=copy_json_tree(policy),
                subjects=copy_json_tree(subjects),
                evidence=copy_json_tree(evidence),
            )
            decoded = registered.pack.decode(pack_request)
            component_payloads = registered.pack.component_payloads(decoded, identities)
            components = _component_bindings(descriptor, identities, component_payloads)
            evaluation = registered.pack.evaluate(operation, decoded)
            if not isinstance(evaluation, PackEvaluation):
                raise InvalidPackOutput("pack returned the wrong evaluation type")
            state, outcomes = reduce_obligations(descriptor, tuple(evaluation.obligations))
            diagnostics = _normalize_diagnostics(descriptor, evaluation.diagnostics)
            bindings = _bindings(descriptor, identities, subjects, evidence, components)

            decision_payload: dict[str, object] = {
                "protocol": common.protocol,
                "pack": registered.descriptor.pack_id,
                "operation": operation,
                "request_digest": request_digest,
                "policy_digest": policy_digest,
                "state": state,
                "bindings": bindings,
                "obligations": [
                    {"id": outcome.id, "outcome": outcome.outcome} for outcome in outcomes
                ],
                "diagnostics": diagnostics,
            }
            result = {
                "kind": "decision",
                "payload": decision_payload,
                "decision_digest": decision_digest(decision_payload),
            }
            return result, snapshot, registered, operation
        except Exception:
            return dict(_INTERNAL_FAILURE), None, None, None


class RequestEvaluator(Protocol):
    def evaluate(self, request: object) -> dict[str, object]: ...


def _result_exit_status(result: object) -> int:
    if type(result) is not dict:
        return 4
    if result.get("kind") == "error":
        return 4 if result.get("code") == "internal.failure" else 3
    if result.get("kind") != "decision":
        return 4
    payload = result.get("payload")
    if type(payload) is not dict:
        return 4
    return {"admissible": 0, "inadmissible": 1, "indeterminate": 2}.get(
        payload.get("state"), 4
    )


class JsonlRunner:
    """Process one request per line with an evaluator supplied by the host."""

    def __init__(
        self,
        evaluator: RequestEvaluator,
        status_resolver: Callable[[object], int] | None = None,
    ) -> None:
        if not callable(getattr(evaluator, "evaluate", None)):
            raise TypeError("JsonlRunner requires an evaluator with evaluate(request)")
        if status_resolver is not None and not callable(status_resolver):
            raise TypeError("JsonlRunner status_resolver must be callable")
        self._evaluator = evaluator
        self._status_resolver = (
            _result_exit_status if status_resolver is None else status_resolver
        )

    def run(self, source: BinaryIO, sink: BinaryIO) -> int:
        maximum_status = 0
        while True:
            raw = source.readline(_MAX_LINE_BYTES + 2)
            if not raw:
                return maximum_status
            has_newline = raw.endswith(b"\n")
            line = raw[:-1] if has_newline else raw
            oversized = len(line) > _MAX_LINE_BYTES
            if not has_newline and len(raw) > _MAX_LINE_BYTES:
                oversized = True
                while raw and not raw.endswith(b"\n"):
                    raw = source.readline(_MAX_LINE_BYTES + 2)
            if oversized:
                result: object = {"kind": "error", "code": "limit.exceeded", "pointer": ""}
            else:
                try:
                    result = self._evaluator.evaluate(parse_json_bytes(line))
                except InputProblem as problem:
                    result = problem.envelope()
                except Exception:
                    result = dict(_INTERNAL_FAILURE)
            try:
                status = self._status_resolver(result)
                if type(status) is not int or status not in range(5):
                    raise ValueError("status_resolver returned an invalid exit status")
            except Exception:
                result = dict(_INTERNAL_FAILURE)
                status = 4
            if status == 4 and not (
                type(result) is dict
                and result.get("kind") == "error"
                and result.get("code") == "internal.failure"
            ):
                result = dict(_INTERNAL_FAILURE)
            try:
                encoded = canonical_bytes(result)
            except Exception:
                encoded = canonical_bytes(_INTERNAL_FAILURE)
                status = 4
            sink.write(encoded)
            sink.write(b"\n")
            maximum_status = max(maximum_status, status)
            if status == 4:
                return maximum_status


def _component_bindings(
    operation: OperationDescriptor, identities: PackIdentity, outputs: object
) -> list[dict[str, str]]:
    if not isinstance(outputs, Sequence) or isinstance(outputs, (str, bytes, bytearray)):
        raise InvalidPackOutput("component_payloads must return a finite sequence")
    declarations = { (item.subject_role, item.name): item for item in operation.components }
    maximum = sum(item.maximum for item in operation.components)
    if len(outputs) > maximum:
        raise InvalidPackOutput("pack emitted too many components")
    counts: dict[tuple[str, str], int] = {}
    bindings: list[dict[str, str]] = []
    for payload in outputs:
        if not isinstance(payload, ComponentPayload):
            raise InvalidPackOutput("pack emitted an invalid component payload")
        key = (payload.subject_role, payload.name)
        declaration = declarations.get(key)
        if declaration is None or (payload.kind, payload.schema) != (
            declaration.artifact.kind,
            declaration.artifact.schema,
        ):
            raise InvalidPackOutput("pack emitted an undeclared component")
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > declaration.maximum:
            raise InvalidPackOutput("pack exceeded component cardinality")
        bindings.append(
            {
                "subject_role": payload.subject_role,
                "name": payload.name,
                "kind": payload.kind,
                "schema": payload.schema,
                "digest": identities.digest(payload.kind, payload.schema, payload.payload),
            }
        )
    for key, declaration in declarations.items():
        if counts.get(key, 0) < declaration.minimum:
            raise InvalidPackOutput("pack omitted a required component")
    return sorted(bindings, key=lambda item: (item["subject_role"], item["name"]))


def _bindings(
    operation: OperationDescriptor,
    identities: PackIdentity,
    subjects: dict[str, object],
    evidence: list[object],
    components: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    if set(subjects) != set(operation.subject_roles):
        raise InvalidPackOutput("normalized subject roles do not match the descriptor")
    subject_bindings: list[dict[str, str]] = []
    for role in sorted(operation.subject_roles):
        artifact = operation.subject_artifacts[role]
        subject_bindings.append(
            {
                "role": role,
                "kind": artifact.kind,
                "schema": artifact.schema,
                "digest": identities.digest(artifact.kind, artifact.schema, subjects[role]),
            }
        )

    evidence_bindings: list[dict[str, str]] = []
    artifact = operation.evidence_artifact
    if artifact is None and evidence:
        raise InvalidPackOutput("operation does not declare evidence")
    if artifact is not None:
        for item in evidence:
            if type(item) is not dict or type(item.get("id")) is not str:
                raise InvalidPackOutput("normalized evidence has no string ID")
            evidence_bindings.append(
                {
                    "id": item["id"],
                    "kind": artifact.kind,
                    "schema": artifact.schema,
                    "digest": identities.digest(artifact.kind, artifact.schema, item),
                }
            )
    return {
        "subjects": subject_bindings,
        "components": components,
        "evidence": evidence_bindings,
    }


def _sorted_evidence(evidence: list[object]) -> list[object]:
    identifiers: set[str] = set()
    for item in evidence:
        if type(item) is not dict or type(item.get("id")) is not str or not item["id"]:
            raise InvalidPackOutput("normalized evidence has no non-empty string ID")
        identifier = item["id"]
        if identifier in identifiers:
            raise InvalidPackOutput("normalized evidence IDs are not unique")
        identifiers.add(identifier)
    return sorted(evidence, key=lambda item: item["id"])


def _normalize_diagnostics(operation: OperationDescriptor, diagnostics: object) -> list[dict[str, str]]:
    if not isinstance(diagnostics, Sequence) or isinstance(diagnostics, (str, bytes, bytearray)):
        raise InvalidPackOutput("diagnostics must be a finite sequence")
    obligations = set(operation.obligations)
    allowed = operation.diagnostic_pointers
    normalized: set[tuple[str, str, str]] = set()
    for item in diagnostics:
        if not isinstance(item, Diagnostic):
            raise InvalidPackOutput("pack emitted an invalid diagnostic")
        if item.obligation_id not in obligations:
            raise InvalidPackOutput("diagnostic references an undeclared obligation")
        if item.pointer not in allowed.get(item.code, ()) or not _valid_pointer(item.pointer):
            raise InvalidPackOutput("pack emitted an undeclared diagnostic")
        normalized.add((item.obligation_id, item.pointer, item.code))
    return [
        {"obligation_id": obligation, "pointer": pointer, "code": code}
        for obligation, pointer, code in sorted(normalized)
    ]


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


def _valid_pack_error(problem: PackInputError) -> bool:
    if type(problem.code) is not str or problem.code not in _INPUT_CODES:
        return False
    if type(problem.pointer) is not str or not _valid_pointer(problem.pointer):
        return False
    if problem.pointer == "":
        return True
    root = problem.pointer[1:].split("/", 1)[0].replace("~1", "/").replace("~0", "~")
    return root in {"operation", "policy", "subjects", "evidence"}


def _freeze(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({key: _freeze(member) for key, member in value.items()})
    if type(value) is list:
        return tuple(_freeze(member) for member in value)
    return value
