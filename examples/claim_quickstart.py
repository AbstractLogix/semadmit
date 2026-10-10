"""Run a self-contained Semadmit claim-verification example."""

from __future__ import annotations

from copy import deepcopy

from semadmit import ClaimEngine


SUBJECT_DIGEST = "sha256:" + "0" * 64


def request(name: str, observations: list[dict[str, int]]) -> dict[str, object]:
    source = f"fixture://quickstart/{name}"
    return {
        "protocol": "semadmit/claim/0.1",
        "policy": {"admission_profile": "strict/0.1"},
        "claim": {
            "id": f"claim-{name}",
            "subject": {
                "function_id": "example.abs",
                "version": "1",
                # This placeholder and all observations are synthetic.
                "artifact_digest": SUBJECT_DIGEST,
            },
            "predicate": {"id": "integer.output.gte/0.1", "lower_bound": 0},
            "domain": {"complete": True, "inputs": [-1, 0, 1]},
            "expected_evidence_family": "deterministic-execution/0.1",
            "required_verifier": "finite-observation/0.1",
            "assumptions": ["The source digest identifies the tested function."],
        },
        "context": {
            "contract_id": "integer-output-lower-bound/0.1",
            "scope": "finite-closed-domain",
            "assumptions": ["The input list is the full domain."],
        },
        "evidence": [
            {
                "id": f"trace-{name}",
                "family": "deterministic-execution/0.1",
                "source": source,
                "subject_digest": SUBJECT_DIGEST,
                "captured_version": "build-1",
                "collection_method": "fixed-test-vector/0.1",
                "artifact_references": [f"{source}/trace"],
                "upstream_dependencies": ["build-1"],
                "correlation_group": "run-1",
                "uncertainty": None,
                "observations": observations,
            }
        ],
    }


def main() -> None:
    engine = ClaimEngine()
    cases = [
        (
            "valid",
            request(
                "valid",
                [
                    {"input": -1, "output": 1},
                    {"input": 0, "output": 0},
                    {"input": 1, "output": 1},
                ],
            ),
        ),
        (
            "invalid",
            request(
                "invalid",
                [
                    {"input": -1, "output": 1},
                    {"input": 0, "output": 0},
                    {"input": 1, "output": -1},
                ],
            ),
        ),
        (
            "indeterminate",
            request("incomplete", [{"input": -1, "output": 1}, {"input": 1, "output": 1}]),
        ),
    ]
    valid_request: dict[str, object] | None = None
    valid_result: dict[str, object] | None = None
    for label, claim_request in cases:
        result = engine.evaluate(claim_request)
        if not engine.verify_result(claim_request, result):
            raise RuntimeError(f"{label}: result verification failed")
        core = result["core_decision"]
        assert isinstance(core, dict) and isinstance(core["payload"], dict)
        print(
            f"{label}: verification={result['verification_status']} "
            f"admission={result['admission_status']} core={core['payload']['state']}"
        )
        if label == "valid":
            valid_request, valid_result = claim_request, result

    assert valid_request is not None and valid_result is not None
    changed = deepcopy(valid_result)
    core = changed["core_decision"]
    assert isinstance(core, dict)
    core["decision_digest"] = "0" * 64
    print("tampered result verification accepted:", engine.verify_result(valid_request, changed))


if __name__ == "__main__":
    main()
