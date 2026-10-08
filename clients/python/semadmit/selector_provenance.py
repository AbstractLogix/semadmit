"""Bounded selector-provenance admission pack for independent corroboration."""

from __future__ import annotations

import re
from collections.abc import Sequence

from semadmit.pack import (
    ArtifactSpec,
    ComponentPayload,
    Diagnostic,
    NormalizedPackRequest,
    ObligationOutcome,
    OperationDescriptor,
    PackDescriptor,
    PackEvaluation,
    PackInputError,
    PackIdentity,
)

PACK_ID = "selector-provenance/0.1"
RULE_VERSION = "selector-independence/0.1"
OPERATION = "independent_corroboration"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
_SCORE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?", re.ASCII)
_RELATIONS = frozenset(
    (
        "independent",
        "shared_model",
        "shared_encoder",
        "shared_training_lineage",
        "shared_source",
        "unknown",
    )
)
_SHARED_RELATIONS = (
    "shared_model",
    "shared_encoder",
    "shared_training_lineage",
    "shared_source",
)
_DIAGNOSTIC_CODES = {
    "provenance.missing": ("/evidence",),
    "independence.unestablished": ("/evidence",),
    "dependence.unknown": ("/evidence",),
    "dependence.shared_model": ("/evidence",),
    "dependence.shared_encoder": ("/evidence",),
    "dependence.shared_training_lineage": ("/evidence",),
    "dependence.shared_source": ("/evidence",),
}


def _object(
    value: object, required: set[str], optional: set[str], pointer: str
) -> dict[str, object]:
    if type(value) is not dict or not required <= set(value) or not set(value) <= required | optional:
        raise PackInputError("input.invalid_shape", pointer)
    return value


def _text(value: object, pointer: str) -> str:
    if type(value) is not str or not value:
        raise PackInputError("input.invalid_type", pointer)
    return value


def _optional_text(value: object, pointer: str) -> str | None:
    if value is None:
        return None
    return _text(value, pointer)


def _digest(value: object, pointer: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise PackInputError("input.invalid_digest", pointer)
    return value


def _optional_positive_int(value: object, pointer: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 1:
        raise PackInputError("input.invalid_type", pointer)
    return value


def _optional_score(value: object, pointer: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or _SCORE.fullmatch(value) is None or value == "-0":
        raise PackInputError("input.invalid_type", pointer)
    return value


def _dependencies(value: object, pointer: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if type(value) is not list:
        raise PackInputError("input.invalid_type", pointer)
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        dependency_pointer = f"{pointer}/{index}"
        dependency = _object(raw, {"id", "relation"}, set(), dependency_pointer)
        identifier = _text(dependency["id"], f"{dependency_pointer}/id")
        relation = _text(dependency["relation"], f"{dependency_pointer}/relation")
        if relation not in _SHARED_RELATIONS and relation != "unknown":
            raise PackInputError("input.invalid_relation", f"{dependency_pointer}/relation")
        normalized.append({"id": identifier, "relation": relation})
    return normalized


def _identity(value: object, pointer: str) -> dict[str, str | None] | None:
    if value is None:
        return None
    identity = _object(value, set(), {"id", "version"}, pointer)
    return {
        "id": _optional_text(identity.get("id"), f"{pointer}/id"),
        "version": _optional_text(identity.get("version"), f"{pointer}/version"),
    }


def _selector(value: object, pointer: str) -> dict[str, object] | None:
    if value is None:
        return None
    fields = {
        "id",
        "type",
        "version",
        "model_id",
        "model_version",
        "query_identity",
        "corpus_identity",
        "ranking_score",
        "rank",
        "retrieval_method",
        "budget",
        "consumer_relation",
        "upstream_dependencies",
    }
    selector = _object(value, set(), fields, pointer)
    consumer_relation = _optional_text(
        selector.get("consumer_relation"), f"{pointer}/consumer_relation"
    )
    if consumer_relation is not None and consumer_relation not in _RELATIONS:
        raise PackInputError("input.invalid_relation", f"{pointer}/consumer_relation")
    return {
        "id": _optional_text(selector.get("id"), f"{pointer}/id"),
        "type": _optional_text(selector.get("type"), f"{pointer}/type"),
        "version": _optional_text(selector.get("version"), f"{pointer}/version"),
        "model_id": _optional_text(selector.get("model_id"), f"{pointer}/model_id"),
        "model_version": _optional_text(
            selector.get("model_version"), f"{pointer}/model_version"
        ),
        "query_identity": _optional_text(
            selector.get("query_identity"), f"{pointer}/query_identity"
        ),
        "corpus_identity": _optional_text(
            selector.get("corpus_identity"), f"{pointer}/corpus_identity"
        ),
        "ranking_score": _optional_score(
            selector.get("ranking_score"), f"{pointer}/ranking_score"
        ),
        "rank": _optional_positive_int(selector.get("rank"), f"{pointer}/rank"),
        "retrieval_method": _optional_text(
            selector.get("retrieval_method"), f"{pointer}/retrieval_method"
        ),
        "budget": _optional_positive_int(selector.get("budget"), f"{pointer}/budget"),
        "consumer_relation": consumer_relation,
        "upstream_dependencies": _dependencies(
            selector.get("upstream_dependencies"), f"{pointer}/upstream_dependencies"
        ),
    }


def _normalize_policy(value: object) -> dict[str, object]:
    pointer = "/policy"
    policy = _object(
        value,
        {"rule_version", "context", "consumer", "assumptions"},
        {"isoprax_rule"},
        pointer,
    )
    version = _text(policy["rule_version"], f"{pointer}/rule_version")
    if version != RULE_VERSION:
        raise PackInputError("policy.unsupported_rule", f"{pointer}/rule_version")
    context = _identity(policy["context"], f"{pointer}/context")
    if context is None or context["id"] is None:
        raise PackInputError("input.invalid_type", f"{pointer}/context/id")
    consumer = _object(
        policy["consumer"],
        set(),
        {"model_id", "model_version", "upstream_dependencies"},
        f"{pointer}/consumer",
    )
    assumptions = policy["assumptions"]
    if type(assumptions) is not list:
        raise PackInputError("input.invalid_type", f"{pointer}/assumptions")
    normalized_assumptions = [
        _text(item, f"{pointer}/assumptions/{index}")
        for index, item in enumerate(assumptions)
    ]
    isoprax_rule = policy.get("isoprax_rule")
    if isoprax_rule is not None:
        rule = _object(
            isoprax_rule,
            {"id", "version", "digest"},
            set(),
            f"{pointer}/isoprax_rule",
        )
        isoprax_rule = {
            "id": _text(rule["id"], f"{pointer}/isoprax_rule/id"),
            "version": _text(rule["version"], f"{pointer}/isoprax_rule/version"),
            "digest": _digest(rule["digest"], f"{pointer}/isoprax_rule/digest"),
        }
    return {
        "rule_version": version,
        "context": context,
        "consumer": {
            "model_id": _optional_text(
                consumer.get("model_id"), f"{pointer}/consumer/model_id"
            ),
            "model_version": _optional_text(
                consumer.get("model_version"), f"{pointer}/consumer/model_version"
            ),
            "upstream_dependencies": _dependencies(
                consumer.get("upstream_dependencies"),
                f"{pointer}/consumer/upstream_dependencies",
            ),
        },
        "assumptions": normalized_assumptions,
        "isoprax_rule": isoprax_rule,
    }


def _normalize_subjects(value: object) -> dict[str, object]:
    subjects = _object(value, {"target"}, set(), "/subjects")
    target = _object(
        subjects["target"], {"kind", "id", "digest"}, set(), "/subjects/target"
    )
    kind = _text(target["kind"], "/subjects/target/kind")
    if kind not in {"claim", "hypothesis"}:
        raise PackInputError("input.invalid_type", "/subjects/target/kind")
    return {
        "target": {
            "kind": kind,
            "id": _text(target["id"], "/subjects/target/id"),
            "digest": _digest(target["digest"], "/subjects/target/digest"),
        }
    }


def _normalize_evidence(value: object) -> list[dict[str, object]]:
    if type(value) is not list:
        raise PackInputError("input.invalid_type", "/evidence")
    if not 2 <= len(value) <= 8:
        raise PackInputError("evidence.invalid_count", "/evidence")
    normalized: list[dict[str, object]] = []
    for index, raw in enumerate(value):
        pointer = f"/evidence/{index}"
        evidence = _object(
            raw,
            {"id", "digest", "family"},
            {"source", "collector", "selector"},
            pointer,
        )
        normalized.append(
            {
                "id": _text(evidence["id"], f"{pointer}/id"),
                "digest": _digest(evidence["digest"], f"{pointer}/digest"),
                "family": _text(evidence["family"], f"{pointer}/family"),
                "source": _identity(evidence.get("source"), f"{pointer}/source"),
                "collector": _identity(evidence.get("collector"), f"{pointer}/collector"),
                "selector": _selector(evidence.get("selector"), f"{pointer}/selector"),
            }
        )
    return normalized


def _relations(request: NormalizedPackRequest) -> tuple[str, ...]:
    policy = request.policy
    evidence = request.evidence
    if type(policy) is not dict or type(evidence) is not list:
        return ("provenance.missing",)
    consumer = policy["consumer"]
    consumer_model_id = consumer["model_id"] if type(consumer) is dict else None
    consumer_dependencies = (
        consumer.get("upstream_dependencies", []) if type(consumer) is dict else []
    )
    missing = consumer_model_id is None
    selectors: list[dict[str, object] | None] = []
    sources: list[dict[str, str | None]] = []
    for item in evidence:
        if type(item) is not dict:
            missing = True
            continue
        source = item["source"]
        collector = item["collector"]
        selector = item["selector"]
        if type(source) is dict and source["id"] is not None:
            sources.append(source)
        else:
            missing = True
        if type(collector) is not dict or collector["id"] is None:
            missing = True
        if type(selector) is not dict:
            selectors.append(None)
            missing = True
            continue
        if (
            selector["id"] is None
            or selector["type"] is None
            or selector["type"] == "unknown"
            or (selector["type"] == "model" and selector["model_id"] is None)
        ):
            missing = True
        selectors.append(selector)

    found: set[str] = set()
    found_unknown = False
    for selector in selectors:
        if type(selector) is not dict:
            continue
        model_id = selector["model_id"]
        if model_id is not None and model_id == consumer_model_id:
            found.add("shared_model")
        relation = selector["consumer_relation"]
        if relation in _SHARED_RELATIONS:
            found.add(relation)
        elif relation == "unknown":
            found_unknown = True
        if any(
            dependency["relation"] == "unknown"
            for dependency in selector["upstream_dependencies"]
        ):
            found_unknown = True
    for index, left in enumerate(selectors):
        if type(left) is not dict:
            continue
        left_dependencies = left["upstream_dependencies"]
        for right in selectors[index + 1 :]:
            if type(right) is not dict:
                continue
            if left["model_id"] is not None and left["model_id"] == right["model_id"]:
                found.add("shared_model")
            if (
                left["corpus_identity"] is not None
                and left["corpus_identity"] == right["corpus_identity"]
            ):
                found.add("shared_source")
            right_dependencies = right["upstream_dependencies"]
            found.update(_shared_dependency_relations(left_dependencies, right_dependencies))
        found.update(
            _shared_dependency_relations(left_dependencies, consumer_dependencies)
        )
    for index, left in enumerate(sources):
        if any(left["id"] == right["id"] for right in sources[index + 1 :]):
            found.add("shared_source")
    codes: list[str] = []
    if missing:
        codes.append("provenance.missing")
    codes.extend(f"dependence.{item}" for item in _SHARED_RELATIONS if item in found)
    if found_unknown:
        codes.append("dependence.unknown")
    if not codes and not found:
        return ("independence.unestablished",)
    return tuple(codes)


def _shared_dependency_relations(left: object, right: object) -> set[str]:
    if type(left) is not list or type(right) is not list:
        return set()
    return {
        item["relation"]
        for item in left
        if type(item) is dict
        and item["relation"] in _SHARED_RELATIONS
        and any(
            type(other) is dict
            and item["id"] == other["id"]
            and item["relation"] == other["relation"]
            for other in right
        )
    }


def _descriptor() -> OperationDescriptor:
    return OperationDescriptor(
        subject_roles=("target",),
        policy_artifact=ArtifactSpec(
            "policy", f"{PACK_ID}/policy", "normalized-policy"
        ),
        subject_artifacts={
            "target": ArtifactSpec("subject", f"{PACK_ID}/target", "normalized-subject")
        },
        evidence_artifact=ArtifactSpec(
            "evidence", f"{PACK_ID}/evidence", "normalized-evidence"
        ),
        components=(),
        obligations=("independence",),
        diagnostic_pointers=_DIAGNOSTIC_CODES,
        input_schemas={
            "policy": {"schema": f"{PACK_ID}/policy"},
            "subjects": {"schema": f"{PACK_ID}/target"},
            "evidence": {"schema": f"{PACK_ID}/evidence"},
        },
        validation_order={
            "policy": ("rule_version", "context", "consumer", "assumptions"),
            "subjects": ("target",),
            "evidence": ("id", "digest", "family", "source", "collector", "selector"),
        },
        array_order={"/evidence": "set:id", "/policy/assumptions": "declared"},
        resource_limits={"evidence_items": 8},
    )


class SelectorProvenancePack:
    """Experimental, fail-closed selector independence assessment."""

    descriptor = PackDescriptor(
        PACK_ID, ("semantic-oracle/0.1",), {OPERATION: _descriptor()}
    )

    def validate(
        self, operation: str, policy: object, subjects: object, evidence: object
    ) -> NormalizedPackRequest:
        if operation != OPERATION:
            raise PackInputError("protocol.unsupported_operation", "/operation")
        return NormalizedPackRequest(
            _normalize_policy(policy),
            _normalize_subjects(subjects),
            _normalize_evidence(evidence),
        )

    def decode(self, request: NormalizedPackRequest) -> NormalizedPackRequest:
        return request

    def component_payloads(
        self, request: NormalizedPackRequest, identities: PackIdentity
    ) -> Sequence[ComponentPayload]:
        del request, identities
        return ()

    def evaluate(self, operation: str, request: NormalizedPackRequest) -> PackEvaluation:
        if operation != OPERATION:
            raise PackInputError("protocol.unsupported_operation", "/operation")
        return PackEvaluation(
            (ObligationOutcome("independence", "missing"),),
            tuple(
                Diagnostic("independence", "/evidence", code)
                for code in _relations(request)
            ),
        )
