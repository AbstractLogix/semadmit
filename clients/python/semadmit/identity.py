"""RFC 8785 bytes and SHA-256 identities for Semadmit's restricted JSON profile."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator

_SAFE_INTEGER = (1 << 53) - 1
_MAX_DEPTH = 64


def _scalar_text(value: str) -> str:
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("JSON strings must contain Unicode scalar values")
    return value


def _pieces(value: object, depth: int) -> Iterator[str]:
    if value is None:
        yield "null"
    elif value is True:
        yield "true"
    elif value is False:
        yield "false"
    elif isinstance(value, str):
        yield json.dumps(_scalar_text(value), ensure_ascii=False, separators=(",", ":"))
    elif type(value) is int:
        if not -_SAFE_INTEGER <= value <= _SAFE_INTEGER:
            raise ValueError("JSON integer is outside the safe integer range")
        yield str(value)
    elif type(value) is list:
        if depth >= _MAX_DEPTH:
            raise ValueError("JSON container depth exceeds 64")
        yield "["
        for index, item in enumerate(value):
            if index:
                yield ","
            yield from _pieces(item, depth + 1)
        yield "]"
    elif type(value) is dict:
        if depth >= _MAX_DEPTH:
            raise ValueError("JSON container depth exceeds 64")
        keys = value.keys()
        if any(type(key) is not str for key in keys):
            raise TypeError("JSON object keys must be strings")
        yield "{"
        for index, key in enumerate(sorted(keys, key=lambda item: _scalar_text(item).encode("utf-16-be"))):
            if index:
                yield ","
            yield json.dumps(key, ensure_ascii=False, separators=(",", ":"))
            yield ":"
            yield from _pieces(value[key], depth + 1)
        yield "}"
    else:
        raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Encode a validated JSON tree using JCS's UTF-16 object-key order.

    Semadmit request JSON numbers are safe integers only; non-integer domain
    quantities are canonical decimal strings supplied by their packs.
    """
    return "".join(_pieces(value, 0)).encode("utf-8")


def artifact_digest(kind: str, schema: str, payload: object) -> str:
    """Hash Core's exact kind/schema/payload identity envelope."""
    envelope = {"kind": kind, "schema": schema, "payload": payload}
    return "sha256:" + hashlib.sha256(canonical_bytes(envelope)).hexdigest()


def decision_digest(payload: object) -> str:
    """Hash the normative decision payload without an outer envelope."""
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()
