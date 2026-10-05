"""Strict byte-framed JSON parser for Semadmit's shared input profile."""

from __future__ import annotations

import re

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)
_HEX = frozenset("0123456789abcdefABCDEF")
_SAFE_INTEGER = (1 << 53) - 1
_MAX_BYTES = 10 * 1024 * 1024
_MAX_DEPTH = 64
_MAX_EVIDENCE = 256
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class InputProblem(Exception):
    def __init__(self, code: str, pointer: str = "") -> None:
        self.code = code
        self.pointer = pointer
        super().__init__(f"{code} at {pointer}")

    def envelope(self) -> dict[str, str]:
        return {"kind": "error", "code": self.code, "pointer": self.pointer}


def _pointer(parent: str, segment: str | int) -> str:
    escaped = str(segment).replace("~", "~0").replace("/", "~1")
    return parent + "/" + escaped


class _Parser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0

    def parse(self) -> object:
        self._space()
        result = self._value("", 0)
        self._space()
        if self.index != len(self.source):
            raise InputProblem("input.invalid_json")
        return result

    def _space(self) -> None:
        while self.index < len(self.source) and self.source[self.index] in " \t\r\n":
            self.index += 1

    def _value(self, pointer: str, depth: int) -> object:
        if self.index == len(self.source):
            raise InputProblem("input.invalid_json")
        char = self.source[self.index]
        if char == "{":
            if depth >= _MAX_DEPTH:
                raise InputProblem("limit.exceeded", pointer)
            return self._object(pointer, depth + 1)
        if char == "[":
            if depth >= _MAX_DEPTH:
                raise InputProblem("limit.exceeded", pointer)
            return self._array(pointer, depth + 1)
        if char == '"':
            return self._string()
        for literal, value in (("true", True), ("false", False), ("null", None)):
            if self.source.startswith(literal, self.index):
                self.index += len(literal)
                return value
        if char == "-" or "0" <= char <= "9":
            return self._number(pointer)
        raise InputProblem("input.invalid_json")

    def _object(self, pointer: str, depth: int) -> dict[str, object]:
        self.index += 1
        result: dict[str, object] = {}
        self._space()
        if self._consume("}"):
            return result
        while True:
            if not self._at('"'):
                raise InputProblem("input.invalid_json")
            key = self._string()
            member_pointer = _pointer(pointer, key)
            if key in result:
                raise InputProblem("input.duplicate_key", member_pointer)
            self._space()
            if not self._consume(":"):
                raise InputProblem("input.invalid_json")
            self._space()
            result[key] = self._value(member_pointer, depth)
            self._space()
            if self._consume("}"):
                return result
            if not self._consume(","):
                raise InputProblem("input.invalid_json")
            self._space()

    def _array(self, pointer: str, depth: int) -> list[object]:
        self.index += 1
        result: list[object] = []
        self._space()
        if self._consume("]"):
            return result
        while True:
            member_pointer = _pointer(pointer, len(result))
            if pointer == "/evidence" and len(result) >= _MAX_EVIDENCE:
                raise InputProblem("limit.exceeded", member_pointer)
            result.append(self._value(member_pointer, depth))
            self._space()
            if self._consume("]"):
                return result
            if not self._consume(","):
                raise InputProblem("input.invalid_json")
            self._space()

    def _string(self) -> str:
        self.index += 1
        result: list[str] = []
        while self.index < len(self.source):
            char = self.source[self.index]
            self.index += 1
            if char == '"':
                return "".join(result)
            if ord(char) < 0x20:
                raise InputProblem("input.invalid_json")
            if char != "\\":
                if 0xD800 <= ord(char) <= 0xDFFF:
                    raise InputProblem("input.invalid_unicode")
                result.append(char)
                continue
            if self.index == len(self.source):
                raise InputProblem("input.invalid_json")
            escape = self.source[self.index]
            self.index += 1
            if escape in _ESCAPES:
                result.append(_ESCAPES[escape])
                continue
            if escape != "u":
                raise InputProblem("input.invalid_json")
            codepoint = self._hex_quad()
            if 0xDC00 <= codepoint <= 0xDFFF:
                raise InputProblem("input.invalid_unicode")
            if 0xD800 <= codepoint <= 0xDBFF:
                if self.source[self.index:self.index + 2] != "\\u":
                    raise InputProblem("input.invalid_unicode")
                self.index += 2
                lower = self._hex_quad()
                if not 0xDC00 <= lower <= 0xDFFF:
                    raise InputProblem("input.invalid_unicode")
                codepoint = 0x10000 + ((codepoint - 0xD800) << 10) + lower - 0xDC00
            result.append(chr(codepoint))
        raise InputProblem("input.invalid_json")

    def _hex_quad(self) -> int:
        digits = self.source[self.index:self.index + 4]
        if len(digits) != 4 or any(char not in _HEX for char in digits):
            raise InputProblem("input.invalid_json")
        self.index += 4
        return int(digits, 16)

    def _number(self, pointer: str) -> int:
        match = _NUMBER.match(self.source, self.index)
        if match is None:
            raise InputProblem("input.invalid_json")
        token = match.group()
        self.index = match.end()
        if self.index < len(self.source) and self.source[self.index] not in " \t\r\n,]}":
            raise InputProblem("input.invalid_json")
        if any(char in token for char in ".eE") or token == "-0":
            raise InputProblem("input.number_profile", pointer)
        digits = token.lstrip("-")
        if len(digits) > 16 or (len(digits) == 16 and digits > str(_SAFE_INTEGER)):
            raise InputProblem("input.number_profile", pointer)
        return int(token)

    def _at(self, char: str) -> bool:
        return self.index < len(self.source) and self.source[self.index] == char

    def _consume(self, char: str) -> bool:
        if self._at(char):
            self.index += 1
            return True
        return False


def parse_json_bytes(source: bytes) -> object:
    """Parse one bounded UTF-8 JSON value, preserving protocol error codes."""
    if len(source) > _MAX_BYTES:
        raise InputProblem("limit.exceeded")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputProblem("input.invalid_utf8") from exc
    if text.startswith("\ufeff"):
        raise InputProblem("input.invalid_json")
    return _Parser(text).parse()


def copy_json_tree(value: object) -> object:
    """Make a bounded JSON-shaped copy for direct Python API calls."""
    encoded_size = 0

    def charge(amount: int) -> None:
        nonlocal encoded_size
        encoded_size += amount
        if encoded_size > _MAX_BYTES:
            raise InputProblem("limit.exceeded")

    def string_size(text: str, pointer: str) -> int:
        size = 2
        for char in text:
            codepoint = ord(char)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise InputProblem("input.invalid_unicode", pointer)
            if char in ('"', "\\", "\b", "\f", "\n", "\r", "\t"):
                size += 2
            elif codepoint < 0x20:
                size += 6
            else:
                size += len(char.encode("utf-8"))
            if size + encoded_size > _MAX_BYTES:
                raise InputProblem("limit.exceeded")
        return size

    def visit(member: object, pointer: str, depth: int) -> object:
        if member is None:
            charge(4)
            return None
        if type(member) is bool:
            charge(4 if member else 5)
            return member
        if type(member) is int:
            if not -_SAFE_INTEGER <= member <= _SAFE_INTEGER:
                raise InputProblem("input.number_profile", pointer)
            charge(len(str(member)))
            return member
        if type(member) is float:
            raise InputProblem("input.number_profile", pointer)
        if type(member) is str:
            charge(string_size(member, pointer))
            return member
        if type(member) is list:
            if depth >= _MAX_DEPTH:
                raise InputProblem("limit.exceeded", pointer)
            if pointer == "/evidence" and len(member) > _MAX_EVIDENCE:
                raise InputProblem("limit.exceeded", "/evidence/256")
            charge(2 + max(0, len(member) - 1))
            return [visit(item, _pointer(pointer, index), depth + 1) for index, item in enumerate(member)]
        if type(member) is dict:
            if depth >= _MAX_DEPTH:
                raise InputProblem("limit.exceeded", pointer)
            charge(2 + max(0, len(member) - 1))
            copied: dict[str, object] = {}
            for index, (key, item) in enumerate(member.items()):
                if type(key) is not str:
                    raise InputProblem("input.invalid_type", pointer)
                child_pointer = _pointer(pointer, key)
                charge(string_size(key, child_pointer) + 1)
                copied[key] = visit(item, child_pointer, depth + 1)
            return copied
        raise InputProblem("input.invalid_type", pointer)

    return visit(value, "", 0)
