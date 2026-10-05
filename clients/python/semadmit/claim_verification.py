"""Finite-domain claim verification as an explicitly registered Python pack."""

from __future__ import annotations

from dataclasses import dataclass
from semadmit.evaluator import Evaluator, JsonlRunner
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


def _input_error(code: str, pointer: str) -> PackInputError:
    return PackInputError(code, pointer)


def _closed_object(value: object, fields: tuple[str, ...], pointer: str) -> dict[str, object]:
    if type(value) is not dict:
        raise _input_error("input.invalid_type", pointer)
    actual = set(value)
    extra = sorted(actual - set(fields))
    if extra:
        escaped = extra[0].replace("~", "~0").replace("/", "~1")
        raise _input_error("input.unknown_field", f"{pointer}/{escaped}")
    missing = sorted(set(fields) - actual)
    if missing:
        raise _input_error("input.missing_field", f"{pointer}/{missing[0]}")
    return value


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
        "evidence.non_commensurable": ("/evidence/0/family", "/evidence/0/subject_digest"),
        "verifier.unsupported": ("/subjects/claim/predicate/id", "/subjects/claim/required_verifier"),
    },
    input_schemas={"policy": {}, "subjects": {}, "evidence": {}},
    validation_order={
        "policy": ("admission_profile",),
        "claim": ("id", "subject", "predicate", "domain", "assumptions"),
        "context": ("contract_id", "scope", "assumptions"),
        "evidence": ("id", "family", "subject_digest", "observations"),
    },
    array_order={"/subjects/claim/domain/inputs": "ascending-integer", "/evidence/0/observations": "input"},
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
        subject_fields = _closed_object(subjects, ("claim", "context"), "/subjects")
        claim = self._validate_claim(subject_fields["claim"])
        context = self._validate_context(subject_fields["context"])
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
        fields = _closed_object(
            value,
            ("id", "subject", "predicate", "domain", "assumptions", "expected_evidence_family", "required_verifier"),
            base,
        )
        subject = _closed_object(fields["subject"], ("function_id", "version", "artifact_digest"), f"{base}/subject")
        predicate = _closed_object(fields["predicate"], ("id", "lower_bound"), f"{base}/predicate")
        domain = _closed_object(fields["domain"], ("inputs", "complete"), f"{base}/domain")
        inputs = domain["inputs"]
        if type(inputs) is not list:
            raise _input_error("input.invalid_type", f"{base}/domain/inputs")
        if not inputs or len(inputs) > _MAX_DOMAIN:
            raise _input_error("limit.exceeded" if len(inputs) > _MAX_DOMAIN else "input.invalid_value", f"{base}/domain/inputs")
        normalized_inputs = sorted(_integer(item, f"{base}/domain/inputs/{index}") for index, item in enumerate(inputs))
        if len(set(normalized_inputs)) != len(normalized_inputs):
            raise _input_error("input.invalid_value", f"{base}/domain/inputs")
        if type(domain["complete"]) is not bool:
            raise _input_error("input.invalid_type", f"{base}/domain/complete")
        return {
            "id": _text(fields["id"], f"{base}/id"),
            "subject": {
                "function_id": _text(subject["function_id"], f"{base}/subject/function_id"),
                "version": _text(subject["version"], f"{base}/subject/version"),
                "artifact_digest": _valid_digest(subject["artifact_digest"], f"{base}/subject/artifact_digest"),
            },
            "predicate": {
                "id": _text(predicate["id"], f"{base}/predicate/id"),
                "lower_bound": _integer(predicate["lower_bound"], f"{base}/predicate/lower_bound"),
            },
            "domain": {"inputs": normalized_inputs, "complete": domain["complete"]},
            "assumptions": _text_list(fields["assumptions"], f"{base}/assumptions"),
            "expected_evidence_family": _text(fields["expected_evidence_family"], f"{base}/expected_evidence_family"),
            "required_verifier": _text(fields["required_verifier"], f"{base}/required_verifier"),
        }

    def _validate_context(self, value: object) -> dict[str, object]:
        base = "/subjects/context"
        fields = _closed_object(value, ("contract_id", "scope", "assumptions"), base)
        return {
            "contract_id": _text(fields["contract_id"], f"{base}/contract_id"),
            "scope": _text(fields["scope"], f"{base}/scope"),
            "assumptions": _text_list(fields["assumptions"], f"{base}/assumptions"),
        }

    def _validate_evidence(self, value: object, claim: dict[str, object], index: int) -> dict[str, object]:
        base = f"/evidence/{index}"
        fields = _closed_object(
            value,
            (
                "id", "source", "collection_method", "captured_version", "family", "subject_digest",
                "uncertainty", "upstream_dependencies", "artifact_references", "correlation_group", "observations",
            ),
            base,
        )
        observations = fields["observations"]
        if type(observations) is not list:
            raise _input_error("input.invalid_type", f"{base}/observations")
        if len(observations) > _MAX_DOMAIN:
            raise _input_error("limit.exceeded", f"{base}/observations")
        normalized_observations: list[dict[str, int]] = []
        domain_inputs = set(claim["domain"]["inputs"])
        observed_inputs: set[int] = set()
        for item_index, item in enumerate(observations):
            pointer = f"{base}/observations/{item_index}"
            observation = _closed_object(item, ("input", "output"), pointer)
            input_value = _integer(observation["input"], f"{pointer}/input")
            output_value = _integer(observation["output"], f"{pointer}/output")
            if input_value not in domain_inputs or input_value in observed_inputs:
                raise _input_error("input.invalid_value", f"{pointer}/input")
            observed_inputs.add(input_value)
            normalized_observations.append({"input": input_value, "output": output_value})
        normalized_observations.sort(key=lambda item: item["input"])
        uncertainty = fields["uncertainty"]
        if uncertainty is not None:
            uncertainty = _text(uncertainty, f"{base}/uncertainty")
        correlation_group = fields["correlation_group"]
        if correlation_group is not None:
            correlation_group = _text(correlation_group, f"{base}/correlation_group")
        return {
            "id": _text(fields["id"], f"{base}/id"),
            "source": _text(fields["source"], f"{base}/source"),
            "collection_method": _text(fields["collection_method"], f"{base}/collection_method"),
            "captured_version": _text(fields["captured_version"], f"{base}/captured_version"),
            "family": _text(fields["family"], f"{base}/family"),
            "subject_digest": _valid_digest(fields["subject_digest"], f"{base}/subject_digest"),
            "uncertainty": uncertainty,
            "upstream_dependencies": _text_list(fields["upstream_dependencies"], f"{base}/upstream_dependencies"),
            "artifact_references": _text_list(fields["artifact_references"], f"{base}/artifact_references"),
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
            evidence_item["family"] == expected_family
            and evidence_item["subject_digest"] == subject["artifact_digest"]
        )
        if not evidence_matches:
            commensurability = "NON_COMMENSURABLE"
            pointer = "/evidence/0/family" if evidence_item["family"] != expected_family else "/evidence/0/subject_digest"
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
    return JsonlRunner(engine or ClaimEngine())
