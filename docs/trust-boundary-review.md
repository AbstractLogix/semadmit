# Trust Boundary Review

**Scope:** Semadmit `main` from the reviewed claim pin `de61aa87a5f4470fd64de33c926cff7f92cf8bd6` through this qualification change. This review covers Semadmit. It does not inspect or change Bouleusis.

## Boundary

Semadmit checks whether supplied evidence may take part in a named operation under a declared policy. It does not decide what Bouleusis must believe.

These steps remain separate:

1. Request validation checks the protocol, schema, token profile, and resource limits.
2. Result verification checks that a candidate matches deterministic reevaluation for the supplied request and registered implementation.
3. Admission reports permission for the named operation and policy.
4. Source authenticity asks whether a source or collector really produced the supplied artifact.
5. Evidential reliability asks how much weight the evidence deserves.
6. Truth asks whether the underlying claim is correct.

Semadmit enforces the first three within its supported packs. A digest binds bytes to an identity declaration. It does not authenticate a source. Reevaluation verifies the result structure and bindings. It does not prove the evidence is truthful or reliable.

## Guarantee Review

| Guarantee | Classification | Evidence and limit |
| --- | --- | --- |
| Claim request uses `semadmit/claim/0.1` and the closed five-field envelope | Mechanically enforced and tested | `ClaimEngine.evaluate`; closed-schema and unsupported-version tests. This checks request shape, not source truth. |
| Duplicate keys, invalid Unicode, unsafe number forms, and resource-limit violations fail closed | Mechanically enforced and tested | Strict byte parser and parser tests in both implementations. Duplicate JSON keys cannot be recovered after a consumer has already parsed and discarded them. |
| Claim result binds to the supplied request, claim, evidence, policy, Core result, and supported status pair | Mechanically enforced and tested | `ClaimEngine.verify_result` recomputes and compares canonical JSON bytes. Compatibility cases and tampering tests cover binding changes. |
| Claim status pairs stay aligned with Core state | Mechanically enforced and tested | `VALID/ADMISSIBLE/admissible`, `INVALID/INADMISSIBLE/inadmissible`, and `UNKNOWN/REQUIRES_SEPARATE_TREATMENT/indeterminate` are checked by deterministic reevaluation. |
| Incomplete or unsupported evidence does not become a successful finite verification | Mechanically enforced and tested | Missing, incomplete, unsupported-family, and open-domain cases return `UNKNOWN` and `indeterminate`. This is bounded to the implemented finite-invariant pack. |
| Core decision identity covers the canonical decision payload | Mechanically enforced and tested | `decision_digest` and shared exact-output vectors. Cross-language results are qualified only for the listed Core corpus. |
| Core result comparison distinguishes JSON booleans from integers | Mechanically enforced and tested | Python Core verification now compares canonical bytes. Regression tests exercise both `true`/`1` and `false`/`0`. |
| Python and Haskell agree on all Core semantics | Tested but not structurally enforced | Both implementations match the nine committed vectors. This is evidence for those cases only, not proof for every Core input. |
| Selector relevance or model names prove independent corroboration | Not implemented; tested to remain unknown | All four bounded `selector-provenance/0.1` fixture cases remain `indeterminate`; score and model metadata change identity but do not grant admission. No IsoPrax synthetic-pilot rule is used. |
| A particular Bouleusis release implements this consumer contract | Documented only | The contract is published for consumers. Semadmit does not claim a Bouleusis integration run. |
| Provenance declarations are authentic | Out of scope | Semadmit preserves supplied provenance and dependence fields. It does not authenticate those declarations. |
| Evidence is reliable or the claim is true | Out of scope | Neither result verification nor admissibility establishes reliability or truth. |
| Result remains verifiable against a recorded implementation snapshot | Incomplete | The current verifier reevaluates with the implementation available to the caller. It does not bind the result to an immutable executable or signed build attestation. |
| Consumers can only use evidence after a guarded admission capability is issued | Incomplete | The generic Core API has a guarded `Admission` object. The claim wrapper exposes a result and boolean verification check; it does not yet provide a claim-specific guarded-use capability. |
| Python and Haskell implement the claim and selector packs identically | Out of scope | Haskell is an independent Core reference. It does not claim the Python claim or selector packs. |

## Core Conformance

The shared Core corpus at `test/integration/vertical_slice/vectors.json` has nine exact-output cases. Each Python and Haskell suite compares the full expected decision or error envelope. It covers all three decision states, partial and mixed obligation reduction, evidence order, duplicate evidence, unsupported protocol, policy digest mismatch, and an unexpected request field.

This corpus checks generic Core request, binding, reduction, identity, and decision behavior. It does not qualify every Core parser edge or every pack. The parser tests cover malformed UTF-8, duplicate keys, invalid Unicode, numeric profile limits, request size, nesting depth, and evidence count. Claim and selector semantics remain outside Haskell parity.

## Selector Provenance

`selector-provenance/0.1` is a separate, experimental Python pack. It preserves source, collector, selector, consumer, model revision, encoder, training lineage, upstream source, and unknown relationship fields when supplied. Missing relationships remain unknown. Matching model, shared encoder, training lineage, shared source, ranking score, or different model names do not establish statistical independence.

The operation `independent_corroboration` remains `indeterminate` for all four reviewed cases. A positive independence rule needs reproducible external evidence and a reviewed operation-specific rule from the IsoPrax direction. The synthetic pilot does not meet this requirement.

## Release Gap Matrix

| Gate | State | Exact remaining work |
| --- | --- | --- |
| Snapshot-bound verification | Open | Bind verification to an immutable implementation/build identity and define how consumers verify that identity. |
| Guarded claim consumption | Open | Add a claim-specific capability or equivalent checked-use API so verification and use cannot be confused. |
| Measurement pack | Open | Qualify matching Python and Haskell Measurement semantics and their shared decision cases. |
| Extension example | Open | Add a complete downstream pack example with guarded consumption and conformance checks. |
| Broad conformance | In progress | Nine shared Core evaluator cases, nine identity vectors, one selected RFC 8785 vector, and eight full raw parser-error envelopes pass. Broader request mutation, resource-limit, and CLI framing parity remains partial. See the [current assurance scope](release-assurance.md#cross-language-scope). |
| Dependency and license inventory | Partial | Archive provenance and review cover the 69-package Hackage graph. `ghc-prim` source and license review is complete. The `rts` review found Closure Library Apache-2.0 code without a separate license copy or `NOTICE`; the Haskell binary notice set is not approved. Three packages do not declare source repositories, and redistribution obligations still need owner approval. See the [dependency inventory](dependency-license-inventory.md). |
| Reproducible release builds | Partial | Clean Python wheels and Haskell executables matched. Raw Python source archives still differ in generated timestamps; the documented normalizer makes the resulting archives byte-identical while preserving package contents and licensing metadata. See the [release assurance record](release-assurance.md#clean-build-repeatability). |
| Independent final review | Open | A review packet is ready. Obtain a human reviewer for the final code, contract, package, and license evidence; automated review does not close this gate. |
| Repository protection | Unable to inspect | GitHub returned HTTP 403 because private-repository branch protection requires an upgrade. Proposed rule: require the `Coverage` check and one independent review. The owner must confirm or configure it; no settings changed. |
| Release decision | Open | Close required gates, record final evidence for one exact commit, and make a separate release decision. |

## Compatibility and Release Status

The frozen Bouleusis consumer pin remains `de61aa87a5f4470fd64de33c926cff7f92cf8bd6` with protocols `semadmit/claim/0.1`, `semantic-oracle/0.1`, and `semadmit/claim-result-consumer/0.1`. See `conformance/fixtures/claim-consumer-compatibility-matrix.json` for the machine-readable contract.

The claim consumer boundary can be qualified independently of overall Semadmit release readiness. Release remains not ready while the open gates above remain open. See the [release assurance record](release-assurance.md) for the exact baseline, validation results, and remaining actions.
