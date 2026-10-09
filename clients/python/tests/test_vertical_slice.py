"""Shared registered-pack vectors for the cross-language evaluator slice."""

import json
import unittest
from pathlib import Path

from semadmit.evaluator import Evaluator
from semadmit.pack import PackRegistry
from test_evaluator import FixturePack


_ROOT = Path(__file__).resolve().parents[3]
_VECTORS = _ROOT / "test" / "integration" / "vertical_slice" / "vectors.json"


class VerticalSliceChecks(unittest.TestCase):
    def test_shared_core_parity_corpus(self) -> None:
        vectors = json.loads(_VECTORS.read_text(encoding="utf-8"))
        evaluator = Evaluator(PackRegistry((FixturePack(),)))
        self.assertEqual(vectors["format"], "semadmit-core-parity-cases/0.1")
        self.assertEqual(vectors["implementations"], ["python", "haskell"])
        self.assertEqual(
            vectors["scope"],
            [
                "Core request normalization",
                "generic subject, evidence, and component bindings",
                "obligation reduction",
                "decision payload and digest",
            ],
        )
        self.assertEqual(vectors["excludes"], ["semadmit/claim/0.1", "isoprax/0.1 domain semantics"])
        self.assertEqual(
            [case["id"] for case in vectors["cases"]],
            [
                "admissible",
                "inadmissible",
                "indeterminate",
                "pass-with-missing",
                "failure-dominates-missing",
                "duplicate-evidence",
                "unsupported-protocol",
                "policy-digest-mismatch",
                "unexpected-field",
            ],
        )

        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    evaluator.evaluate(case["request"]),
                    case["expected"],
                    f"Python Core result differs from the shared corpus case {case['id']}",
                )
