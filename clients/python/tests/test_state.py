"""Independent obligation-state checks for the generic Core rule."""

import unittest
from dataclasses import replace

from semadmit.pack import ObligationOutcome
from semadmit.state import InvalidPackOutput, reduce_obligations
from test_pack_registry import descriptor


class StateReductionChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.operation = replace(descriptor().operations["check"], obligations=("a", "b"))

    def test_all_states_and_fail_over_missing(self) -> None:
        for outcomes, expected in (
            (("pass", "pass"), "admissible"),
            (("pass", "missing"), "indeterminate"),
            (("fail", "missing"), "inadmissible"),
        ):
            with self.subTest(outcomes=outcomes):
                state, ordered = reduce_obligations(
                    self.operation,
                    (ObligationOutcome("b", outcomes[1]), ObligationOutcome("a", outcomes[0])),
                )
                self.assertEqual(state, expected)
                self.assertEqual(tuple(item.id for item in ordered), ("a", "b"))

    def test_missing_duplicate_extra_and_bad_outcome_fail_closed(self) -> None:
        for outcomes in (
            (ObligationOutcome("a", "pass"),),
            (ObligationOutcome("a", "pass"), ObligationOutcome("a", "pass")),
            (ObligationOutcome("a", "pass"), ObligationOutcome("c", "pass")),
            (ObligationOutcome("a", "pass"), ObligationOutcome("b", "unknown")),
        ):
            with self.subTest(outcomes=outcomes), self.assertRaises(InvalidPackOutput):
                reduce_obligations(self.operation, outcomes)


if __name__ == "__main__":
    unittest.main()
