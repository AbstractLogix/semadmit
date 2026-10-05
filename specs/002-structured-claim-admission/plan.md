# Implementation Plan: Structured Claim Verification v0.1

## Summary

Add a Python first-party pack for a finite integer output-bound claim. Use the public pack interface and existing Core evaluator. Add a high-level result wrapper so callers receive explicit verification states and the full pack artifact without changing the approved v0.1 decision envelope.

## Design

1. Keep the `semantic-oracle/0.1` request, decision, identity, and admission contracts unchanged.
2. Register `claim/0.1` in a local `ClaimEngine` registry. The pack accepts one observation trace at most.
3. Normalize domain inputs and observations into ascending integer order.
4. Compare the claim's expected evidence family and function digest with the trace before using its observations.
5. Return `INVALID` for a compatible counterexample. Return `VALID` only for full compatible coverage of a declared complete finite domain. Return `UNKNOWN` in every other well-formed case.
6. Map those states to pass, fail, and missing obligations. Keep the Core admission result fail-closed.
7. Return the full verification artifact in an outer `semadmit/claim/0.1` result. Verify that its digest matches the declared Core component binding.
8. Use the existing JSONL runner for local host integration. Keep the existing Isoprax pooling operation as a separate pack and request.

## Data and Trust Boundaries

- Claim data declares the subject digest, predicate, finite domain, assumptions, expected evidence family, and required verifier.
- Context data declares the contract and scope.
- Evidence data declares source, collection method, captured version, family, subject digest, uncertainty, dependencies, artifact references, correlation group, and observations.
- Core binds normalized claim, context, policy, evidence, verification component, and decision.
- The pack never executes supplied code, retrieves evidence, reads ambient files, or uses wall-clock time.
- Provenance remains caller-supplied metadata. The result does not authenticate it.

## Validation Strategy

- Use normative fixtures for valid, invalid, partial, missing, and non-commensurable cases.
- Exhaustively enumerate small two-input domains and output combinations. Check that any compatible violation is invalid, complete safe coverage is valid, and all other combinations remain unknown.
- Check canonical normalization, artifact digest binding, local verification, and JSONL behavior.
- Run the repository coverage gate after focused tests. Report local and hosted evidence separately.

## Complexity

At most 256 domain inputs, 256 observations, and one evidence artifact are accepted. Normalization is `O(n log n)` and verification is `O(n)`. The implementation adds one Python pack and one wrapper API. It adds no service or runtime dependency.

## Risks and Limits

- One evidence trace is intentionally narrow. The pack does not combine evidence sources or infer independence.
- A complete finite test set does not prove behavior outside the declared finite domain.
- The artifact preserves declared provenance but does not authenticate sources.
- The claim pack is Python-only in this feature. Do not claim independent Haskell conformance for its domain rule.
- The wrapper must keep its status, artifact digest, and Core decision consistent. Tests check that binding.
