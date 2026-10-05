# Feature Specification: Structured Claim Verification v0.1

**Feature Branch**: main
**Created**: 2026-10-05
**Status**: Implemented locally; release and hosted checks remain open.

## Purpose

Add one end-to-end claim verification path to Semadmit. The path accepts a structured claim, context, policy, and evidence. It returns separate verification and admission statuses. It keeps the approved `semantic-oracle/0.1` Core envelope unchanged.

This feature adds one Python pack, `claim/0.1`. A host must register it. The pack checks finite integer observations against a lower-bound invariant. It does not run caller code. It does not prove claims about inputs outside the complete finite domain in the request.

## Scope

- Accept closed, versioned claim, context, policy, and evidence schemas.
- Verify one deterministic execution trace with the finite-observation verifier.
- Return `VALID`, `INVALID`, or `UNKNOWN` separately from the Core decision state.
- Keep source, method, version, uncertainty, upstream dependencies, artifact references, and correlation group in a reproducible verification artifact.
- Bind the artifact to the generic Core decision by its declared component digest.
- Provide a bounded local JSONL adapter for a Bouleusis-style host.
- Document and exercise the existing Isoprax pooling rule as the commensurability example.

This feature does not add a server, dynamic pack loader, arbitrary function execution, a general rule language, or cross-pack evidence pooling. It does not change Isoprax production behavior.

## User Story and Acceptance

As a reasoning-system maintainer, I need an explicit result for a structured finite-domain claim, so I can admit only evidence that satisfies a declared contract and keep uncertainty visible.

Acceptance scenarios:

1. Complete, compatible observations that meet the invariant produce `VALID` and `ADMISSIBLE`.
2. A compatible observation that breaks the invariant produces `INVALID`, `INADMISSIBLE`, and a counterexample linked to the claim and source evidence.
3. Missing, partial, unsupported, or non-commensurable evidence produces `UNKNOWN` and `REQUIRES_SEPARATE_TREATMENT`.
4. The result includes the exact Core decision, result digest, verification artifact, and artifact digest. The component digest in the Core result matches the returned artifact.
5. Identical normalized requests produce identical results. Reordered domain and observation arrays produce the same result.
6. Malformed fields, duplicate observations, unsupported policy, and resource-limit violations return stable errors with no admission status.
7. A local JSONL caller can pass requests through `ClaimEngine` and receive one machine-readable result per line.
8. The Isoprax example refuses prediction pooling unless the complete outcome definitions are compatible and both samples pass calibration under the bound policy.

## Request Schema

The public request uses protocol `semadmit/claim/0.1`:

```json
{
  "protocol": "semadmit/claim/0.1",
  "policy": {"admission_profile": "strict/0.1"},
  "claim": {
    "id": "claim-1",
    "subject": {
      "function_id": "example.abs",
      "version": "1",
      "artifact_digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    },
    "predicate": {"id": "integer.output.gte/0.1", "lower_bound": 0},
    "domain": {"inputs": [-1, 0, 1], "complete": true},
    "assumptions": ["The digest identifies the tested function."],
    "expected_evidence_family": "deterministic-execution/0.1",
    "required_verifier": "finite-observation/0.1"
  },
  "context": {
    "contract_id": "integer-output-lower-bound/0.1",
    "scope": "finite-closed-domain",
    "assumptions": ["The input list is the full domain."]
  },
  "evidence": []
}
```

The evidence list accepts zero or one trace. A trace has `id`, `source`, `collection_method`, `captured_version`, `family`, `subject_digest`, `uncertainty`, `upstream_dependencies`, `artifact_references`, `correlation_group`, and `observations`. Each observation has a safe JSON integer `input` and `output` in the RFC 8785 range, `-(2^53-1)` through `2^53-1`. Booleans are not integers in this contract. Both subject digest fields must use the SHA-256 syntax. A mismatch makes the evidence non-commensurable and the status `UNKNOWN`. The pack binds the digest; it does not authenticate the function source.

The policy schema accepts only `{"admission_profile":"strict/0.1"}`. The claim domain and trace are bounded to 256 integer values. Duplicate domain values, duplicate observation inputs, and observations outside the declared domain are input errors.

## Verification and Admission Semantics

| Evidence and check | Verification | Admission | Core obligation | Core state |
|---|---|---|---|---|
| Compatible trace covers the complete domain; all outputs meet the bound | `VALID` | `ADMISSIBLE` | pass | admissible |
| Compatible trace contains an output below the bound | `INVALID` | `INADMISSIBLE` | fail | inadmissible |
| Evidence is absent, partial, unsupported, or non-commensurable | `UNKNOWN` | `REQUIRES_SEPARATE_TREATMENT` | missing | indeterminate |

The verifier checks known counterexamples before checking trace completeness. A compatible violation is `INVALID`, even when other inputs are missing. A family or subject-digest mismatch is not used to verify or falsify the claim; it yields `UNKNOWN`.

`VALID` means only that every input in the request's declared complete finite domain has a compatible supplied observation and each output meets the bound. It does not mean the function is correct for any larger or different domain. `UNKNOWN` is not a failure.

## Result and Artifact

`ClaimEngine.evaluate` returns a `claim-result` wrapper with:

- protocol, result ID, claim ID, and evidence IDs;
- explicit verification and admission statuses;
- verification artifact and its digest;
- the full generic Core decision.

The verification artifact contains the method, assumptions, provenance, evaluated contract IDs, evidence family, commensurability result, counterexample or finite observation proof artifact, diagnostics, limitations, reliability category, Semadmit version, pack version, and policy version. The generic Core component digest must equal the digest of this artifact. The result ID is the Core decision digest. `ClaimEngine.verify_result` checks that a candidate claim result matches a fresh local evaluation. It does not issue an admission token.

The counterexample links the claim ID, evidence ID, input, observed output, required bound, and JSON Pointer into that evidence. The proof artifact records the sorted checked inputs and observations. Neither artifact authenticates the source or the evidence collector.

## Policy and Mechanism

Core owns canonical identity, request validation, generic bindings, decision reduction, and result verification. The claim pack owns the closed claim schema, finite-observation verifier, stable diagnostics, and verification artifact. The fixed `strict/0.1` profile maps verification states to Core obligations. It is data; the pack does not execute a caller-supplied policy.

The verifier inspects supplied data only. It does not import or execute the function under test. Provenance fields preserve caller declarations and suspected dependencies. They do not establish source truth, independence, or issuer identity.

## Bouleusis Integration

A Python host registers `ClaimEngine` and can use the existing bounded `JsonlRunner`:

```python
from semadmit import ClaimEngine, claim_jsonl_runner

runner = claim_jsonl_runner(ClaimEngine())
runner.run(bouleusis_input, bouleusis_output)
```

The adapter stays local. It writes one canonical JSON result per input line. A host can store the returned verification artifact by `verification_digest` and record `result_id` in its own epistemic ledger. Semadmit does not change that ledger.

For an Isoprax decision, Bouleusis can send the `semantic-oracle/0.1` request to the local `semantic-oracle --jsonl` process. The process returns one decision line and uses its exit status to distinguish admission, rejection, indeterminate results, and input errors. The `isoprax-pool` integration suite checks the first-party application entry point against every Isoprax pool fixture.

## IsoPrax Integration and Commensurability

The existing `isoprax/0.1` `pool_predictions` operation is the second example. It compares normalized semantic outcome keys: event, observation process, window, and thresholds. Known incompatibility fails. Missing semantic detail remains missing. Pooling also requires each exact sample to pass the calibration policy bound to the request.

The local process call is:

```python
import json
import subprocess

result = subprocess.run(
    ["semantic-oracle", "--jsonl"],
    input=(json.dumps(request, separators=(",", ":")) + "\n").encode(),
    capture_output=True,
    check=False,
)
decision = json.loads(result.stdout)
```

The request shape and positive and negative cases are in `conformance/fixtures/isoprax-cases.json`.

This operation accepts two prediction subjects and no separate evidence items. A deterministic test result cannot enter its prediction samples or be averaged with prediction probabilities. A caller must keep non-commensurable evidence separate. The request and decision bind both subjects, policy, definitions, and samples.

This gate reports eligibility under the supplied definitions and calibration policy. It does not establish that either predictor is truthful or that pooling improves prediction quality.

## Failure Cases

- Malformed claim, context, policy, digest, or observation: stable input error.
- Boolean supplied as an integer, duplicate input, or observation outside the declared domain: input error.
- More than one evidence trace or more than 256 domain points: limit error.
- Missing evidence or missing input coverage: `UNKNOWN`.
- Unsupported predicate, verifier, context contract, evidence family, or function digest: `UNKNOWN`.
- Matching evidence with a violating output: `INVALID` with a linked counterexample.
- Evidence from another family or function digest: `UNKNOWN`; the evidence is preserved but not used.
- A caller changes the request after verification: a later verification returns a different result or rejects the candidate.

## Complexity and Language Assessment

The feature bounds domain points, observations, and evidence count. Normalization sorts at most 256 domain values and observations; evaluation then scans the trace once. The verifier has no network, filesystem, clock, or caller-code access.

For the new claim pack, use Python as the primary implementation because its supported pack API gives Bouleusis a direct in-process and JSONL boundary. Keep Haskell as the independent reference for the existing Core and Isoprax pack. This slice does not show that Haskell should be removed. It gives no reason to make Haskell primary for claim packs until Haskell has equivalent schemas and results, and the project has comparative maintenance data.

## Validation Record

The normative positive, negative, unknown, incompatible-family, and missing-evidence cases are in `conformance/fixtures/claim-verification-cases.json`. Python tests exhaustively check every two-input output combination in `{-1, 0, 1}` and each coverage mask. They also check determinism, canonical ordering, result/artifact binding, provenance retention, malformed input, and JSONL framing.

Focused claim tests passed: 9 tests. The repository coverage gate passed: 38 Python tests, 100% executable-line coverage in all 8 Python modules (1,183 lines), 5,312/5,861 Haskell expressions (90.63%), and 88/193 Haskell booleans (45.60%). The Python source and wheel build passed. A local `semantic-oracle --jsonl` process returned the expected `admissible` result for the `admissible-ece-equality` Isoprax fixture. Hosted CI was not run.
