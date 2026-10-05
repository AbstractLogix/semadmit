"""Fail-closed reduction of an operation's complete obligation set."""

from __future__ import annotations

from semadmit.pack import ObligationOutcome, OperationDescriptor


class InvalidPackOutput(Exception):
    """A trusted pack omitted, duplicated, or invented an obligation."""


def reduce_obligations(
    operation: OperationDescriptor,
    outcomes: tuple[ObligationOutcome, ...],
) -> tuple[str, tuple[ObligationOutcome, ...]]:
    """Return state and sorted outcomes only when the declared set is exact."""
    declared = set(operation.obligations)
    seen: set[str] = set()
    ordered: list[ObligationOutcome] = []
    for item in outcomes:
        if item.id not in declared or item.id in seen or item.outcome not in operation.allowed_outcomes:
            raise InvalidPackOutput("invalid obligation output")
        seen.add(item.id)
        ordered.append(item)
    if seen != declared:
        raise InvalidPackOutput("incomplete obligation output")
    if any(item.outcome == "fail" for item in ordered):
        state = "inadmissible"
    elif any(item.outcome == "missing" for item in ordered):
        state = "indeterminate"
    else:
        state = "admissible"
    return state, tuple(sorted(ordered, key=lambda item: item.id))
