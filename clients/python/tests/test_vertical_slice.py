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
    def test_shared_positive_and_negative_vectors(self) -> None:
        vectors = json.loads(_VECTORS.read_text(encoding="utf-8"))
        evaluator = Evaluator(PackRegistry((FixturePack(),)))
        self.assertEqual(len(vectors["cases"]), 2)

        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(evaluator.evaluate(case["request"]), case["expected"])
