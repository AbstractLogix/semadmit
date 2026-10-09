"""Independent reference for the shared Core test pack, not a production evaluator.

This module uses only Python's standard library. It supports the fixture/0.1
check operation used by the cross-language Core corpus. Pack-specific claim,
Isoprax, selector, and Measurement rules are outside its scope.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


_PROTOCOL = "semantic-oracle/0.1"
_PACK = "fixture/0.1"
_OPERATION = "check"
_REQUEST_SCHEMA = "semantic-oracle/0.1/request"
_REQUEST_FIELDS = (
    "protocol",
    "pack",
    "operation",
    "policy_digest",
    "policy",
    "subjects",
    "evidence",
)
_MODES = {
    "pass": ("pass", "pass"),
    "fail": ("pass", "fail"),
    "missing": ("missing", "missing"),
    "partial": ("missing", "pass"),
    "mixed": ("fail", "missing"),
}
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class ReferenceError(ValueError):
    """A bounded Core error with the normative result envelope fields."""

    def __init__(self, code: str, pointer: str = "") -> None:
        super().__init__(f"{code} at {pointer}")
        self.code = code
        self.pointer = pointer

    def envelope(self) -> dict[str, str]:
        return {"kind": "error", "code": self.code, "pointer": self.pointer}


def _string(value: str) -> str:
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("JCS input must contain Unicode scalar values")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _pieces(value: object, depth: int = 0) -> list[str]:
    if value is None:
        return ["null"]
    if value is True:
        return ["true"]
    if value is False:
        return ["false"]
    if type(value) is int:
        if abs(value) > 9007199254740991:
            raise ValueError("integer is outside the safe JSON profile")
        return [str(value)]
    if type(value) is str:
        return [_string(value)]
    if type(value) is list:
        if depth >= 64:
            raise ValueError("JSON nesting exceeds the Core limit")
        parts = ["["]
        for index, item in enumerate(value):
            if index:
                parts.append(",")
            parts.extend(_pieces(item, depth + 1))
        parts.append("]")
        return parts
    if type(value) is dict:
        if depth >= 64:
            raise ValueError("JSON nesting exceeds the Core limit")
        if any(type(key) is not str for key in value):
            raise ValueError("JSON object keys must be strings")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        parts = ["{"]
        for index, key in enumerate(keys):
            if index:
                parts.append(",")
            parts.extend((_string(key), ":"))
            parts.extend(_pieces(value[key], depth + 1))
        parts.append("}")
        return parts
    raise ValueError(f"unsupported JSON value: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Encode the Core safe-integer JSON profile with RFC 8785 key ordering."""
    return "".join(_pieces(value)).encode("utf-8")


def artifact_digest(kind: str, schema: str, payload: object) -> str:
    envelope = {"kind": kind, "schema": schema, "payload": payload}
    return "sha256:" + hashlib.sha256(canonical_bytes(envelope)).hexdigest()


def _require(condition: bool, code: str, pointer: str) -> None:
    if not condition:
        raise ReferenceError(code, pointer)


def _preflight(value: object, pointer: str = "", depth: int = 1) -> None:
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        _require(abs(value) <= 9007199254740991, "input.number_profile", pointer)
        return
    if type(value) is float:
        raise ReferenceError("input.number_profile", pointer)
    if type(value) is str:
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ReferenceError("input.invalid_unicode", "")
        return
    if type(value) is list:
        _require(depth <= 64, "limit.exceeded", pointer)
        for index, item in enumerate(value):
            _preflight(item, f"{pointer}/{index}", depth + 1)
        return
    if type(value) is dict:
        _require(depth <= 64, "limit.exceeded", pointer)
        for key, item in value.items():
            _require(type(key) is str, "input.invalid_type", pointer)
            if any(0xD800 <= ord(char) <= 0xDFFF for char in key):
                raise ReferenceError("input.invalid_unicode", "")
            escaped = key.replace("~", "~0").replace("/", "~1")
            _preflight(item, f"{pointer}/{escaped}", depth + 1)
        return
    raise ReferenceError("input.invalid_type", pointer)


def _validate_request(request: object) -> tuple[dict[str, Any], str]:
    _require(type(request) is dict, "input.invalid_type", "")
    unknown = set(request) - set(_REQUEST_FIELDS)
    if unknown:
        field = min(unknown)
        raise ReferenceError("input.unknown_field", "/" + field.replace("~", "~0").replace("/", "~1"))
    for field in _REQUEST_FIELDS:
        _require(field in request, "input.missing_field", "/" + field)
        value = request[field]
        if field in ("protocol", "pack", "operation", "policy_digest"):
            _require(type(value) is str, "input.invalid_type", "/" + field)
        elif field in ("policy", "subjects"):
            _require(type(value) is dict, "input.invalid_type", "/" + field)
        else:
            _require(type(value) is list, "input.invalid_type", "/evidence")
    _require(request["protocol"] == _PROTOCOL, "protocol.unsupported_version", "/protocol")
    _require(request["pack"] == _PACK, "protocol.unsupported_pack", "/pack")
    _require(request["operation"] == _OPERATION, "protocol.unsupported_operation", "/operation")
    _require(_DIGEST.fullmatch(request["policy_digest"]) is not None, "input.invalid_value", "/policy_digest")

    policy = request["policy"]
    _require(type(policy) is dict and set(policy) == {"mode"}, "policy.unsupported", "/policy")
    mode = policy["mode"]
    _require(type(mode) is str and mode in _MODES, "policy.unsupported", "/policy")

    subjects = request["subjects"]
    _require(
        type(subjects) is dict
        and set(subjects) == {"item"}
        and type(subjects["item"]) is dict
        and set(subjects["item"]) == {"name"}
        and type(subjects["item"]["name"]) is str,
        "input.invalid_type",
        "/subjects",
    )

    evidence = request["evidence"]
    _require(len(evidence) <= 256, "limit.exceeded", "/evidence/256")
    seen: set[str] = set()
    normalized_evidence: list[dict[str, object]] = []
    for index, item in enumerate(evidence):
        pointer = f"/evidence/{index}"
        _require(
            type(item) is dict
            and set(item) == {"id", "present"}
            and type(item["id"]) is str
            and type(item["present"]) is bool,
            "input.invalid_type",
            pointer,
        )
        identifier = item["id"]
        _require(identifier not in seen, "evidence.duplicate_id", pointer + "/id")
        seen.add(identifier)
        normalized_evidence.append({"id": identifier, "present": item["present"]})
    normalized_evidence.sort(key=lambda item: item["id"])

    normalized_policy = {"mode": mode}
    policy_digest = artifact_digest("policy", "fixture/0.1/policy", normalized_policy)
    _require(policy_digest == request["policy_digest"], "identity.digest_mismatch", "/policy_digest")
    normalized_subjects = {"item": {"name": subjects["item"]["name"]}}
    request_payload = {
        "protocol": _PROTOCOL,
        "pack": _PACK,
        "operation": _OPERATION,
        "policy_digest": policy_digest,
        "policy": normalized_policy,
        "subjects": normalized_subjects,
        "evidence": normalized_evidence,
    }
    return request_payload, mode


def evaluate(request: object) -> dict[str, object]:
    """Derive the shared fixture-pack decision from the request and frozen table."""
    try:
        _preflight(request)
        normalized, mode = _validate_request(request)
    except ReferenceError as error:
        return error.envelope()

    subject = normalized["subjects"]["item"]
    request_digest = artifact_digest("request", _REQUEST_SCHEMA, normalized)
    subject_digest = artifact_digest("subject", "fixture/0.1/subject", subject)
    component_digest = artifact_digest(
        "component", "fixture/0.1/component", {"name": subject["name"]}
    )
    evidence_bindings = [
        {
            "id": item["id"],
            "kind": "assertion",
            "schema": "fixture/0.1/assertion",
            "digest": artifact_digest("assertion", "fixture/0.1/assertion", item),
        }
        for item in normalized["evidence"]
    ]

    present, complete = _MODES[mode]
    outcomes = {"complete": complete, "present": present}
    if "fail" in outcomes.values():
        state = "inadmissible"
    elif "missing" in outcomes.values():
        state = "indeterminate"
    else:
        state = "admissible"
    obligations = [{"id": identifier, "outcome": outcomes[identifier]} for identifier in sorted(outcomes)]
    diagnostics = [
        {
            "obligation_id": identifier,
            "pointer": "/subjects/item/name",
            "code": "domain.mismatch",
        }
        for identifier in sorted(outcomes)
        if outcomes[identifier] == "fail"
    ]
    payload: dict[str, object] = {
        "protocol": _PROTOCOL,
        "pack": _PACK,
        "operation": _OPERATION,
        "request_digest": request_digest,
        "policy_digest": normalized["policy_digest"],
        "state": state,
        "bindings": {
            "subjects": [
                {
                    "role": "item",
                    "kind": "subject",
                    "schema": "fixture/0.1/subject",
                    "digest": subject_digest,
                }
            ],
            "components": [
                {
                    "subject_role": "item",
                    "name": "name",
                    "kind": "component",
                    "schema": "fixture/0.1/component",
                    "digest": component_digest,
                }
            ],
            "evidence": evidence_bindings,
        },
        "obligations": obligations,
        "diagnostics": diagnostics,
    }
    return {
        "kind": "decision",
        "payload": payload,
        "decision_digest": "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest(),
    }


def verify_result(request: object, candidate: object) -> bool:
    """Check exact result bytes after independent reevaluation; this proves no source fact."""
    expected = evaluate(request)
    if expected.get("kind") != "decision":
        return False
    try:
        return canonical_bytes(candidate) == canonical_bytes(expected)
    except (TypeError, ValueError):
        return False
