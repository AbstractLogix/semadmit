"""Finite-domain claim verification as an explicitly registered Python pack."""

from __future__ import annotations

from dataclasses import dataclass
from semadmit.evaluator import Evaluator, JsonlRunner, _result_exit_status
from semadmit.json_input import InputProblem, copy_json_tree
from semadmit.pack import (
    ArtifactSpec,
    ComponentPayload,
    ComponentSpec,
    Diagnostic,
    NormalizedPackRequest,
    ObligationOutcome,
    OperationDescriptor,
    PackDescriptor,
    PackEvaluation,
    PackIdentity,
    PackInputError,
    PackRegistry,
)

_PACK_ID = "claim/0.1"
_PROTOCOL = "semantic-oracle/0.1"
_CLAIM_PROTOCOL = "semadmit/claim/0.1"
_POLICY_SCHEMA = "claim/0.1/policy"
_CLAIM_SCHEMA = "claim/0.1/claim"
_CONTEXT_SCHEMA = "claim/0.1/context"
_EVIDENCE_SCHEMA = "claim/0.1/evidence"
_RESULT_SCHEMA = "claim/0.1/verification"
_MAX_DOMAIN = 256
_MAX_INTEGER = 2**53 - 1
_MIN_INTEGER = -_MAX_INTEGER
_DIGEST_PREFIX = "sha256:"
_HEX = frozenset("0123456789abcdef")
_SUPPORTED_EVIDENCE_FAMILIES = frozenset(("deterministic-execution/0.1",))

_TEXT_SCHEMA = {"type": "string", "minLength": 1, "maxLength": 1024}
_INTEGER_SCHEMA = {"type": "integer", "minimum": _MIN_INTEGER, "maximum": _MAX_INTEGER}
_DIGEST_INPUT_SCHEMA = {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"}
_TEXT_LIST_SCHEMA = {
    "type": "array",
    "items": _TEXT_SCHEMA,
    "maxItems": 256,
    "uniqueItems": True,
}
_NULLABLE_TEXT_SCHEMA = {"type": ["string", "null"], "minLength": 1, "maxLength": 1024}


def _object_schema(properties: dict[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _input_error(code: str, pointer: str) -> PackInputError:
    return PackInputError(code, pointer)


def _object_with_known_fields(
    value: object, fields: tuple[str, ...], pointer: str
) -> dict[str, object]:
    if type(value) is not dict:
        raise _input_error("input.invalid_type", pointer)
    actual = set(value)
    extra = sorted(actual - set(fields))
    if extra:
        escaped = extra[0].replace("~", "~0").replace("/", "~1")
        raise _input_error("input.unknown_field", f"{pointer}/{escaped}")
    return value


def _required_field(fields: dict[str, object], name: str, pointer: str) -> object:
    if name not in fields:
        raise _input_error("input.missing_field", f"{pointer}/{name}")
    return fields[name]


def _closed_object(value: object, fields: tuple[str, ...], pointer: str) -> dict[str, object]:
    result = _object_with_known_fields(value, fields, pointer)
    missing = [field for field in fields if field not in result]
    if missing:
        raise _input_error("input.missing_field", f"{pointer}/{missing[0]}")
    return result


def _text(value: object, pointer: str) -> str:
    if type(value) is not str:
        raise _input_error("input.invalid_type", pointer)
    if not value or len(value) > 1024:
        raise _input_error("input.invalid_value", pointer)
    return value


def _text_list(value: object, pointer: str, limit: int = 256) -> list[str]:
    if type(value) is not list:
        raise _input_error("input.invalid_type", pointer)
    if len(value) > limit:
        raise _input_error("limit.exceeded", pointer)
    values = [_text(item, f"{pointer}/{index}") for index, item in enumerate(value)]
    if len(set(values)) != len(values):
        raise _input_error("input.invalid_value", pointer)
    return values


def _integer(value: object, pointer: str) -> int:
    if type(value) is not int:
        raise _input_error("input.invalid_type", pointer)
    if value < _MIN_INTEGER or value > _MAX_INTEGER:
        raise _input_error("input.invalid_value", pointer)
    return value


def _valid_digest(value: object, pointer: str) -> str:
    text = _text(value, pointer)
    hexadecimal = text.removeprefix(_DIGEST_PREFIX)
    if not text.startswith(_DIGEST_PREFIX) or len(hexadecimal) != 64 or any(char not in _HEX for char in hexadecimal):
        raise _input_error("input.invalid_value", pointer)
    return text


def _artifact_spec(kind: str, schema: str, projection: str) -> ArtifactSpec:
    return ArtifactSpec(kind, schema, projection)


_OPERATION = OperationDescriptor(
    subject_roles=("claim", "context"),
    policy_artifact=_artifact_spec("policy", _POLICY_SCHEMA, "normalized-policy"),
    subject_artifacts={
        "claim": _artifact_spec("claim", _CLAIM_SCHEMA, "normalized-subject"),
        "context": _artifact_spec("context", _CONTEXT_SCHEMA, "normalized-subject"),
    },
    evidence_artifact=_artifact_spec("observation", _EVIDENCE_SCHEMA, "normalized-evidence"),
    components=(
        ComponentSpec(
            "claim", "verification", _artifact_spec("verification", _RESULT_SCHEMA, "component-payload"), 1, 1
        ),
    ),
    obligations=("claim.verification",),
    diagnostic_pointers={
        "claim.invariant_violated": ("/evidence/0/observations",),
        "contract.unsupported": ("/subjects/context/contract_id",),
        "evidence.incomplete": ("/evidence/0/observations", "/subjects/claim/domain/complete"),
        "evidence.missing": ("/evidence",),
        "evidence.non_commensurable": (
            "/subjects/claim/expected_evidence_family",
            "/evidence/0/family",
            "/evidence/0/subject_digest",
        ),
        "verifier.unsupported": ("/subjects/claim/predicate/id", "/subjects/claim/required_verifier"),
    },
    input_schemas={
        "policy": _object_schema({
            "admission_profile": {"type": "string", "const": "strict/0.1"},
        }),
        "subjects": _object_schema({
            "claim": _object_schema({
                "id": _TEXT_SCHEMA,
                "subject": _object_schema({
                    "function_id": _TEXT_SCHEMA,
                    "version": _TEXT_SCHEMA,
                    "artifact_digest": _DIGEST_INPUT_SCHEMA,
                }),
                "predicate": _object_schema({
                    "id": _TEXT_SCHEMA,
                    "lower_bound": _INTEGER_SCHEMA,
                }),
                "domain": _object_schema({
                    "inputs": {
                        "type": "array",
                        "items": _INTEGER_SCHEMA,
                        "minItems": 1,
                        "maxItems": _MAX_DOMAIN,
                        "uniqueItems": True,
                    },
                    "complete": {"type": "boolean"},
                }),
                "assumptions": _TEXT_LIST_SCHEMA,
                "expected_evidence_family": _TEXT_SCHEMA,
                "required_verifier": _TEXT_SCHEMA,
            }),
            "context": _object_schema({
                "contract_id": _TEXT_SCHEMA,
                "scope": _TEXT_SCHEMA,
                "assumptions": _TEXT_LIST_SCHEMA,
            }),
        }),
        "evidence": {
            "type": "array",
            "maxItems": 1,
            "items": _object_schema({
                "id": _TEXT_SCHEMA,
                "source": _TEXT_SCHEMA,
                "collection_method": _TEXT_SCHEMA,
                "captured_version": _TEXT_SCHEMA,
                "family": _TEXT_SCHEMA,
                "subject_digest": _DIGEST_INPUT_SCHEMA,
                "uncertainty": _NULLABLE_TEXT_SCHEMA,
                "upstream_dependencies": _TEXT_LIST_SCHEMA,
                "artifact_references": _TEXT_LIST_SCHEMA,
                "correlation_group": _NULLABLE_TEXT_SCHEMA,
                "observations": {
                    "type": "array",
                    "maxItems": _MAX_DOMAIN,
                    "x-uniqueBy": "input",
                    "items": _object_schema({
                        "input": _INTEGER_SCHEMA,
                        "output": _INTEGER_SCHEMA,
                    }),
                },
            }),
        },
    },
    validation_order={
        "policy": ("admission_profile",),
        "/subjects": ("claim", "context"),
        "/subjects/claim": (
            "id", "subject", "predicate", "domain", "assumptions",
            "expected_evidence_family", "required_verifier",
        ),
        "/subjects/claim/subject": ("function_id", "version", "artifact_digest"),
        "/subjects/claim/predicate": ("id", "lower_bound"),
        "/subjects/claim/domain": ("inputs", "complete"),
        "/subjects/context": ("contract_id", "scope", "assumptions"),
        "/evidence/*": (
            "id", "source", "collection_method", "captured_version", "family", "subject_digest",
            "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group", "observations",
        ),
        "/evidence/*/observations/*": ("input", "output"),
    },
    array_order={
        "/evidence": "set:id",
        "/subjects/claim/assumptions": "sequence",
        "/subjects/claim/domain/inputs": "set:ascending-integer",
        "/subjects/context/assumptions": "sequence",
        "/evidence/*/upstream_dependencies": "sequence",
        "/evidence/*/artifact_references": "sequence",
        "/evidence/*/observations": "set:ascending-input",
    },
    resource_limits={"evidence_items": 1, "domain_inputs": _MAX_DOMAIN, "observations": _MAX_DOMAIN},
)


@dataclass(frozen=True, slots=True)
class _PreparedClaim:
    normalized: NormalizedPackRequest
    verification: dict[str, object]
    outcome: str
    diagnostics: tuple[Diagnostic, ...]


class FiniteInvariantPack:
    """Check supplied execution observations against one finite integer claim."""

    descriptor = PackDescriptor(_PACK_ID, (_PROTOCOL,), {"verify": _OPERATION})

    def validate(
        self, operation: str, policy: object, subjects: object, evidence: object
    ) -> NormalizedPackRequest:
        if operation != "verify":
            raise _input_error("input.invalid_value", "/operation")
        policy_fields = _closed_object(policy, ("admission_profile",), "/policy")
        if policy_fields["admission_profile"] != "strict/0.1":
            raise _input_error("policy.unsupported", "/policy/admission_profile")
        subject_fields = _object_with_known_fields(subjects, ("claim", "context"), "/subjects")
        claim = self._validate_claim(_required_field(subject_fields, "claim", "/subjects"))
        context = self._validate_context(_required_field(subject_fields, "context", "/subjects"))
        if type(evidence) is not list:
            raise _input_error("input.invalid_type", "/evidence")
        if len(evidence) > 1:
            raise _input_error("limit.exceeded", "/evidence/1")
        normalized_evidence = [self._validate_evidence(item, claim, index) for index, item in enumerate(evidence)]
        return NormalizedPackRequest(
            policy={"admission_profile": policy_fields["admission_profile"]},
            subjects={"claim": claim, "context": context},
            evidence=normalized_evidence,
        )

    def _validate_claim(self, value: object) -> dict[str, object]:
        base = "/subjects/claim"
        fields = _object_with_known_fields(
            value,
            ("id", "subject", "predicate", "domain", "assumptions", "expected_evidence_family", "required_verifier"),
            base,
        )
        claim_id = _text(_required_field(fields, "id", base), f"{base}/id")
        subject_path = f"{base}/subject"
        subject = _object_with_known_fields(
            _required_field(fields, "subject", base),
            ("function_id", "version", "artifact_digest"),
            subject_path,
        )
        normalized_subject = {
            "function_id": _text(_required_field(subject, "function_id", subject_path), f"{subject_path}/function_id"),
            "version": _text(_required_field(subject, "version", subject_path), f"{subject_path}/version"),
            "artifact_digest": _valid_digest(_required_field(subject, "artifact_digest", subject_path), f"{subject_path}/artifact_digest"),
        }
        predicate_path = f"{base}/predicate"
        predicate = _object_with_known_fields(
            _required_field(fields, "predicate", base),
            ("id", "lower_bound"),
            predicate_path,
        )
        normalized_predicate = {
            "id": _text(_required_field(predicate, "id", predicate_path), f"{predicate_path}/id"),
            "lower_bound": _integer(_required_field(predicate, "lower_bound", predicate_path), f"{predicate_path}/lower_bound"),
        }
        domain_path = f"{base}/domain"
        domain = _object_with_known_fields(
            _required_field(fields, "domain", base),
            ("inputs", "complete"),
            domain_path,
        )
        inputs = _required_field(domain, "inputs", domain_path)
        if type(inputs) is not list:
            raise _input_error("input.invalid_type", f"{domain_path}/inputs")
        if not inputs or len(inputs) > _MAX_DOMAIN:
            raise _input_error("limit.exceeded" if len(inputs) > _MAX_DOMAIN else "input.invalid_value", f"{domain_path}/inputs")
        normalized_inputs = sorted(_integer(item, f"{domain_path}/inputs/{index}") for index, item in enumerate(inputs))
        if len(set(normalized_inputs)) != len(normalized_inputs):
            raise _input_error("input.invalid_value", f"{domain_path}/inputs")
        complete = _required_field(domain, "complete", domain_path)
        if type(complete) is not bool:
            raise _input_error("input.invalid_type", f"{domain_path}/complete")
        assumptions = _text_list(_required_field(fields, "assumptions", base), f"{base}/assumptions")
        expected_family = _text(_required_field(fields, "expected_evidence_family", base), f"{base}/expected_evidence_family")
        required_verifier = _text(_required_field(fields, "required_verifier", base), f"{base}/required_verifier")
        return {
            "id": claim_id,
            "subject": normalized_subject,
            "predicate": normalized_predicate,
            "domain": {"inputs": normalized_inputs, "complete": complete},
            "assumptions": assumptions,
            "expected_evidence_family": expected_family,
            "required_verifier": required_verifier,
        }

    def _validate_context(self, value: object) -> dict[str, object]:
        base = "/subjects/context"
        fields = _object_with_known_fields(value, ("contract_id", "scope", "assumptions"), base)
        contract_id = _text(_required_field(fields, "contract_id", base), f"{base}/contract_id")
        scope = _text(_required_field(fields, "scope", base), f"{base}/scope")
        assumptions = _text_list(_required_field(fields, "assumptions", base), f"{base}/assumptions")
        return {
            "contract_id": contract_id,
            "scope": scope,
            "assumptions": assumptions,
        }

    def _validate_evidence(self, value: object, claim: dict[str, object], index: int) -> dict[str, object]:
        base = f"/evidence/{index}"
        fields = _object_with_known_fields(
            value,
            (
                "id", "source", "collection_method", "captured_version", "family", "subject_digest",
                "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group", "observations",
            ),
            base,
        )
        evidence_id = _text(_required_field(fields, "id", base), f"{base}/id")
        source = _text(_required_field(fields, "source", base), f"{base}/source")
        collection_method = _text(_required_field(fields, "collection_method", base), f"{base}/collection_method")
        captured_version = _text(_required_field(fields, "captured_version", base), f"{base}/captured_version")
        family = _text(_required_field(fields, "family", base), f"{base}/family")
        subject_digest = _valid_digest(_required_field(fields, "subject_digest", base), f"{base}/subject_digest")
        uncertainty = _required_field(fields, "uncertainty", base)
        if uncertainty is not None:
            uncertainty = _text(uncertainty, f"{base}/uncertainty")
        upstream_dependencies = _text_list(_required_field(fields, "upstream_dependencies", base), f"{base}/upstream_dependencies")
        artifact_references = _text_list(_required_field(fields, "artifact_references", base), f"{base}/artifact_references")
        correlation_group = _required_field(fields, "correlation_group", base)
        if correlation_group is not None:
            correlation_group = _text(correlation_group, f"{base}/correlation_group")
        observations = _required_field(fields, "observations", base)
        if type(observations) is not list:
            raise _input_error("input.invalid_type", f"{base}/observations")
        if len(observations) > _MAX_DOMAIN:
            raise _input_error("limit.exceeded", f"{base}/observations")
        normalized_observations: list[dict[str, int]] = []
        domain_inputs = set(claim["domain"]["inputs"])
        observed_inputs: set[int] = set()
        for item_index, item in enumerate(observations):
            pointer = f"{base}/observations/{item_index}"
            observation = _object_with_known_fields(item, ("input", "output"), pointer)
            input_value = _integer(_required_field(observation, "input", pointer), f"{pointer}/input")
            if input_value not in domain_inputs or input_value in observed_inputs:
                raise _input_error("input.invalid_value", f"{pointer}/input")
            observed_inputs.add(input_value)
            output_value = _integer(_required_field(observation, "output", pointer), f"{pointer}/output")
            normalized_observations.append({"input": input_value, "output": output_value})
        normalized_observations.sort(key=lambda item: item["input"])
        return {
            "id": evidence_id,
            "source": source,
            "collection_method": collection_method,
            "captured_version": captured_version,
            "family": family,
            "subject_digest": subject_digest,
            "uncertainty": uncertainty,
            "upstream_dependencies": upstream_dependencies,
            "artifact_references": artifact_references,
            "correlation_group": correlation_group,
            "observations": normalized_observations,
        }

    def decode(self, request: NormalizedPackRequest) -> _PreparedClaim:
        claim = request.subjects["claim"]
        context = request.subjects["context"]
        evidence = request.evidence
        verification, outcome, diagnostics = _verify(claim, context, evidence, request.policy["admission_profile"])
        return _PreparedClaim(request, verification, outcome, tuple(diagnostics))

    def component_payloads(self, request: _PreparedClaim, identities: PackIdentity) -> tuple[ComponentPayload, ...]:
        return (ComponentPayload("claim", "verification", "verification", _RESULT_SCHEMA, request.verification),)

    def evaluate(self, operation: str, request: _PreparedClaim) -> PackEvaluation:
        return PackEvaluation((ObligationOutcome("claim.verification", request.outcome),), request.diagnostics)


def _verify(
    claim: dict[str, object], context: dict[str, object], evidence: list[object], policy_version: object
) -> tuple[dict[str, object], str, list[Diagnostic]]:
    claim_id = claim["id"]
    expected_family = claim["expected_evidence_family"]
    required_verifier = claim["required_verifier"]
    predicate = claim["predicate"]
    domain = claim["domain"]
    evidence_item = evidence[0] if evidence else None
    evidence_id = evidence_item["id"] if isinstance(evidence_item, dict) else None
    diagnostics: list[Diagnostic] = []
    status = "UNKNOWN"
    admission = "REQUIRES_SEPARATE_TREATMENT"
    commensurability = "UNKNOWN"
    counterexample: dict[str, object] | None = None
    proof_artifact: dict[str, object] | None = None
    method = "finite-observation/0.1"
    supported = (
        context["contract_id"] == "integer-output-lower-bound/0.1"
        and context["scope"] == "finite-closed-domain"
        and predicate["id"] == "integer.output.gte/0.1"
        and required_verifier == method
    )
    contracts_evaluated: list[str] = []
    if not supported:
        if required_verifier != method:
            diagnostics.append(Diagnostic("claim.verification", "/subjects/claim/required_verifier", "verifier.unsupported"))
        if predicate["id"] != "integer.output.gte/0.1":
            diagnostics.append(Diagnostic("claim.verification", "/subjects/claim/predicate/id", "verifier.unsupported"))
        if context["contract_id"] != "integer-output-lower-bound/0.1" or context["scope"] != "finite-closed-domain":
            diagnostics.append(Diagnostic("claim.verification", "/subjects/context/contract_id", "contract.unsupported"))
    else:
        contracts_evaluated.append("integer-output-lower-bound/0.1")
    if supported and evidence_item is None:
        diagnostics.append(Diagnostic("claim.verification", "/evidence", "evidence.missing"))
    elif supported and evidence_item is not None:
        contracts_evaluated.extend(("evidence-subject-binding/0.1", "evidence-family-compatibility/0.1"))
        subject = claim["subject"]
        evidence_matches = (
            expected_family in _SUPPORTED_EVIDENCE_FAMILIES
            and evidence_item["family"] == expected_family
            and evidence_item["subject_digest"] == subject["artifact_digest"]
        )
        if not evidence_matches:
            commensurability = "NON_COMMENSURABLE"
            if expected_family not in _SUPPORTED_EVIDENCE_FAMILIES:
                pointer = "/subjects/claim/expected_evidence_family"
            elif evidence_item["family"] != expected_family:
                pointer = "/evidence/0/family"
            else:
                pointer = "/evidence/0/subject_digest"
            diagnostics.append(Diagnostic("claim.verification", pointer, "evidence.non_commensurable"))
        else:
            commensurability = "COMPARABLE"
            observations = evidence_item["observations"]
            lower_bound = predicate["lower_bound"]
            for observation_index, observation in enumerate(observations):
                if observation["output"] < lower_bound:
                    status = "INVALID"
                    admission = "INADMISSIBLE"
                    counterexample = {
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                        "input": observation["input"],
                        "observed_output": observation["output"],
                        "required_lower_bound": lower_bound,
                        "evidence_pointer": f"/evidence/0/observations/{observation_index}",
                    }
                    diagnostics.append(Diagnostic("claim.verification", "/evidence/0/observations", "claim.invariant_violated"))
                    break
            if status != "INVALID":
                observed_inputs = {observation["input"] for observation in observations}
                complete = domain["complete"] and observed_inputs == set(domain["inputs"])
                if complete:
                    status = "VALID"
                    admission = "ADMISSIBLE"
                    proof_artifact = {
                        "kind": "finite-observation-check/0.1",
                        "checked_inputs": domain["inputs"],
                        "observations": observations,
                    }
                else:
                    diagnostics.append(Diagnostic("claim.verification", "/evidence/0/observations", "evidence.incomplete"))
                    if not domain["complete"]:
                        diagnostics.append(Diagnostic("claim.verification", "/subjects/claim/domain/complete", "evidence.incomplete"))

    if status == "VALID":
        outcome = "pass"
    elif status == "INVALID":
        outcome = "fail"
    else:
        outcome = "missing"
    evidence_ids = [item["id"] for item in evidence if isinstance(item, dict)]
    provenance = [
        {
            key: item[key]
            for key in (
                "id", "source", "collection_method", "captured_version", "family", "subject_digest",
                "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group",
            )
        }
        for item in evidence
        if isinstance(item, dict)
    ]
    supplied_observations = [
        {"evidence_id": item["id"], **observation}
        for item in evidence
        if isinstance(item, dict)
        for observation in item["observations"]
    ]
    artifact = {
        "schema": "semadmit/verification-artifact/0.1",
        "claim_id": claim_id,
        "evidence_ids": evidence_ids,
        "verification_status": status,
        "admission_status": admission,
        "method": method,
        "assumptions": claim["assumptions"] + context["assumptions"],
        "provenance": provenance,
        "contracts_evaluated": contracts_evaluated,
        "outcome_family": expected_family,
        "commensurability_result": commensurability,
        "counterexample": counterexample,
        "proof_artifact": proof_artifact,
        "supplied_observations": supplied_observations,
        "diagnostics": [
            {"code": item.code, "pointer": item.pointer} for item in diagnostics
        ],
        "limitations": [
            "The verifier checks supplied observations only; it does not execute the function.",
            "VALID applies only to the complete finite input domain declared in this request.",
            "Provenance is preserved as supplied and is not independently authenticated.",
        ],
        "reliability_category": "deterministic-observation",
        "semadmit_version": "0.1.0",
        "pack_version": _PACK_ID,
        "policy_version": policy_version,
    }
    return artifact, outcome, diagnostics


class ClaimEngine:
    """Expose explicit claim and admission states over the shared Core evaluator."""

    def __init__(self) -> None:
        self.pack = FiniteInvariantPack()
        self.registry = PackRegistry((self.pack,))
        self.evaluator = Evaluator(self.registry)
        self.identity = PackIdentity(_OPERATION)

    def evaluate(self, request: object) -> dict[str, object]:
        try:
            copied = copy_json_tree(request)
        except InputProblem as problem:
            return problem.envelope()
        if type(copied) is not dict:
            return InputProblem("input.invalid_type").envelope()
        fields = {"protocol", "policy", "claim", "context", "evidence"}
        extras = sorted(set(copied) - fields)
        if extras:
            return InputProblem("input.unknown_field", f"/{extras[0]}").envelope()
        missing = sorted(fields - set(copied))
        if missing:
            return InputProblem("input.missing_field", f"/{missing[0]}").envelope()
        if type(copied["protocol"]) is not str:
            return InputProblem("input.invalid_type", "/protocol").envelope()
        if copied["protocol"] != _CLAIM_PROTOCOL:
            return InputProblem("protocol.unsupported_version", "/protocol").envelope()
        policy = copied["policy"]
        try:
            policy_digest = self.identity.digest("policy", _POLICY_SCHEMA, policy)
        except (TypeError, ValueError):
            return {"kind": "error", "code": "input.invalid_type", "pointer": "/policy"}
        core_request = {
            "protocol": _PROTOCOL,
            "pack": _PACK_ID,
            "operation": "verify",
            "policy_digest": policy_digest,
            "policy": policy,
            "subjects": {"claim": copied["claim"], "context": copied["context"]},
            "evidence": copied["evidence"],
        }
        core_result = self.evaluator.evaluate(core_request)
        if core_result.get("kind") != "decision":
            pointer = core_result.get("pointer")
            if type(pointer) is str:
                if pointer.startswith("/subjects/claim"):
                    core_result["pointer"] = "/claim" + pointer[len("/subjects/claim") :]
                elif pointer.startswith("/subjects/context"):
                    core_result["pointer"] = "/context" + pointer[len("/subjects/context") :]
            return core_result
        try:
            normalized = self.pack.validate("verify", policy, core_request["subjects"], copied["evidence"])
            prepared = self.pack.decode(normalized)
            verification_digest = self.identity.digest("verification", _RESULT_SCHEMA, prepared.verification)
            payload = core_result["payload"]
            if type(payload) is not dict:
                return {"kind": "error", "code": "internal.failure", "pointer": ""}
            components = payload["bindings"]["components"]
            if len(components) != 1 or components[0]["digest"] != verification_digest:
                return {"kind": "error", "code": "internal.failure", "pointer": ""}
            status = prepared.verification["verification_status"]
            expected_state = {"VALID": "admissible", "INVALID": "inadmissible", "UNKNOWN": "indeterminate"}[status]
            if payload["state"] != expected_state:
                return {"kind": "error", "code": "internal.failure", "pointer": ""}
            return {
                "kind": "claim-result",
                "protocol": _CLAIM_PROTOCOL,
                "result_id": core_result["decision_digest"],
                "claim_id": prepared.verification["claim_id"],
                "evidence_ids": prepared.verification["evidence_ids"],
                "verification_status": status,
                "admission_status": prepared.verification["admission_status"],
                "verification_digest": verification_digest,
                "verification": prepared.verification,
                "core_decision": core_result,
            }
        except PackInputError as problem:
            return {"kind": "error", "code": problem.code, "pointer": problem.pointer}
        except Exception:
            return {"kind": "error", "code": "internal.failure", "pointer": ""}

    def verify_result(self, request: object, candidate: object) -> bool:
        try:
            copied_candidate = copy_json_tree(candidate)
        except InputProblem:
            return False
        return (
            type(copied_candidate) is dict
            and copied_candidate.get("kind") == "claim-result"
            and copied_candidate == self.evaluate(request)
        )


def claim_jsonl_runner(engine: ClaimEngine | None = None) -> JsonlRunner:
    """Return the bounded local JSONL adapter used by Bouleusis-style hosts."""
    def claim_status(result: object) -> int:
        if type(result) is dict and result.get("kind") == "claim-result":
            return _result_exit_status(result.get("core_decision"))
        return _result_exit_status(result)

    return JsonlRunner(engine or ClaimEngine(), claim_status)
