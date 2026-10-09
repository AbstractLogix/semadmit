"""Regenerate committed assurance vectors without calling production evaluators."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from assurance.reference_core import artifact_digest, evaluate


ROOT = Path(__file__).resolve().parents[1]
SEED = 20261009
CORE_COUNT = 48
PARSER_COUNT_PER_CLASS = 16
CORE_PATH = ROOT / "test/integration/vertical_slice/vectors.json"
PARSER_PATH = ROOT / "conformance/fixtures/protocol-cases.json"
CORE_ID_PREFIX = f"assurance-seed-{SEED}-"
PARSER_ID_PREFIX = f"assurance-parser-seed-{SEED}-"


def generated_core_cases() -> list[dict[str, object]]:
    rng = random.Random(SEED)
    names = ["plain", "café", "cafe\u0301", "λ", "𐐷", "東京"]
    identifiers = ["a", "é", "e\u0301", "β", "𐐷"]
    modes = ["pass", "fail", "missing", "partial", "mixed"]
    cases: list[dict[str, object]] = []
    for case_index in range(CORE_COUNT):
        policy = {"mode": rng.choice(modes)}
        evidence = [
            {"id": identifier, "present": bool(rng.getrandbits(1))}
            for identifier in rng.sample(identifiers, rng.randrange(len(identifiers) + 1))
        ]
        rng.shuffle(evidence)
        request = {
            "protocol": "semantic-oracle/0.1",
            "pack": "fixture/0.1",
            "operation": "check",
            "policy_digest": artifact_digest("policy", "fixture/0.1/policy", policy),
            "policy": policy,
            "subjects": {"item": {"name": rng.choice(names)}},
            "evidence": evidence,
        }
        cases.append(
            {
                "id": f"{CORE_ID_PREFIX}{case_index:03d}",
                "request": request,
                "expected": evaluate(request),
            }
        )
    return cases


def generated_parser_cases() -> list[dict[str, object]]:
    rng = random.Random(SEED ^ 0x5EED)
    cases: list[dict[str, object]] = []

    def append(identifier: str, raw: str, code: str, pointer: str) -> None:
        cases.append(
            {
                "id": identifier,
                "input": {"kind": "raw-json-utf8", "text": raw},
                "expected": {
                    "error": {"kind": "error", "code": code, "pointer": pointer}
                },
            }
        )

    for index in range(PARSER_COUNT_PER_CLASS):
        suffix = chr(rng.randrange(33, 127))
        append(
            f"{PARSER_ID_PREFIX}trailing-{index:02d}",
            "{}" + suffix,
            "input.invalid_json",
            "",
        )
    for index in range(PARSER_COUNT_PER_CLASS):
        variant = rng.randrange(3)
        if variant == 0:
            token = f"0.{rng.randrange(1, 10)}"
        elif variant == 1:
            token = f"1e{rng.randrange(1, 10)}"
        else:
            token = f"900719925474099{rng.randrange(2, 10)}"
        append(
            f"{PARSER_ID_PREFIX}number-{index:02d}",
            '{"n":' + token + "}",
            "input.number_profile",
            "/n",
        )
    for index in range(PARSER_COUNT_PER_CLASS):
        field = f"key{rng.randrange(32):02d}"
        append(
            f"{PARSER_ID_PREFIX}duplicate-{index:02d}",
            json.dumps({field: 0}, separators=(",", ":"))[:-1]
            + f',"{field}":1}}',
            "input.duplicate_key",
            "/" + field,
        )
    return cases


def update_core_corpus() -> None:
    corpus = json.loads(CORE_PATH.read_text(encoding="utf-8"))
    corpus["cases"] = [
        case for case in corpus["cases"] if not case["id"].startswith(CORE_ID_PREFIX)
    ]
    corpus["cases"].extend(generated_core_cases())
    corpus["generated"] = {
        "seed": SEED,
        "count": CORE_COUNT,
        "method": "stdlib random.Random; expected values from assurance.reference_core only",
    }
    CORE_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def update_parser_corpus() -> None:
    corpus = json.loads(PARSER_PATH.read_text(encoding="utf-8"))
    corpus["cases"] = [
        case for case in corpus["cases"] if not case["id"].startswith(PARSER_ID_PREFIX)
    ]
    corpus["cases"].extend(generated_parser_cases())
    corpus["assurance_parser_fuzz"] = {
        "seed": SEED,
        "count": 3 * PARSER_COUNT_PER_CLASS,
        "classes": [
            "non-whitespace trailing byte after valid JSON",
            "fractional, exponent-form, and unsafe integer tokens",
            "duplicate object keys",
        ],
        "generator": "assurance.generate_corpus",
    }
    PARSER_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def check_corpora() -> bool:
    core = json.loads(CORE_PATH.read_text(encoding="utf-8"))
    core_generated = [
        case for case in core["cases"] if case["id"].startswith(CORE_ID_PREFIX)
    ]
    expected_core_metadata = {
        "seed": SEED,
        "count": CORE_COUNT,
        "method": "stdlib random.Random; expected values from assurance.reference_core only",
    }
    if core_generated != generated_core_cases() or core.get("generated") != expected_core_metadata:
        return False

    parser = json.loads(PARSER_PATH.read_text(encoding="utf-8"))
    parser_generated = [
        case for case in parser["cases"] if case["id"].startswith(PARSER_ID_PREFIX)
    ]
    expected_parser_metadata = {
        "seed": SEED,
        "count": 3 * PARSER_COUNT_PER_CLASS,
        "classes": [
            "non-whitespace trailing byte after valid JSON",
            "fractional, exponent-form, and unsafe integer tokens",
            "duplicate object keys",
        ],
        "generator": "assurance.generate_corpus",
    }
    return (
        parser_generated == generated_parser_cases()
        and parser.get("assurance_parser_fuzz") == expected_parser_metadata
    )


def main() -> None:
    if sys.argv[1:] == ["--check"]:
        if not check_corpora():
            raise SystemExit("committed assurance corpora do not match their recorded seed")
        print("seeded assurance corpus matches its generator")
        return
    if sys.argv[1:]:
        raise SystemExit("usage: python3 -m assurance.generate_corpus [--check]")
    update_core_corpus()
    update_parser_corpus()
    print(f"wrote {CORE_COUNT} independent Core vectors and {3 * PARSER_COUNT_PER_CLASS} parser cases")


if __name__ == "__main__":
    main()
