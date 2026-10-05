# M0 Independent Review Record

**Current disposition (2026-09-30)**: M0 written contract and fixture package approved within the independent review scope below. This does not establish implementation resistance or release readiness.

**Review date**: 2026-09-29
**Reviewer**: Independent Codex sub-agent, read-only review
**Scope**: Candidate Semadmit M0 specifications and the handoff's product requirements
**Out of scope**: Isoprax worktree inspection, implementation, and product tests

## Disposition

The initial review and follow-ups confirmed the policy identity, measurement scope, artifact verification, and coverage-policy binding. A read-only audit of the completed Isoprax Haskell kernel has now supplied the exact nested definition mapping and exposed an ID-compatibility mismatch in the draft. Those candidate corrections are recorded below and require independent recheck. M0 is not approved; Semadmit-specific canonical vectors and complete fixtures remain open.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | Blocker | Isoprax definition fields, types, enums, nullability, unknown markers, and field-level diagnostic pointers were not fully specified. | Candidate fix: the schema and normalization are mapped from the completed Haskell kernel at `223187c`; stable leaf pointers are now enumerated in wire-protocol.md and decision-tables.md. Independent recheck remains required. |
| R2 | Blocker | Canonical byte/digest vectors and complete positive, negative, missing, malformed, and boundary fixtures are absent. | Open. Add fixtures after nested schemas and identity envelopes are finalized. |
| R3 | Major | The handoff requires policy identity to include definition-comparison semantics and numeric profile. | Candidate fix: the manifest has definition_comparison=normalized-key/0.1 and numeric_profile=decimal-rational-12/0.1; its digest covers these plus all threshold fields. This matches the Haskell kernel's ID-independent direct comparison. Fixtures and independent recheck remain open. |
| R4 | Major | aggregate_measurements could be read as calculating an aggregate even though no measurement values or aggregation function are specified. | Addressed in the draft: the pack returns an eligibility decision only; measurement values and actual aggregation are outside Semadmit's v0.1 consumer API. It does not claim the downstream caller performed aggregation. |
| R5 | Major | A consumer could mistake a self-consistent forged admissible artifact for an admission. | Addressed in the draft: a trusted verifier validates the exact request, recomputes identities and decision locally, compares every normative field and digest, and only then constructs opaque admission over the immutable snapshot. Substitution fixtures remain open. |
| R6 | Major | Measurement coverage evidence did not explicitly bind the request policy digest. | Addressed in the draft: each coverage item carries policy_digest; a well-formed mismatch fails with coverage.policy_mismatch, while malformed digest syntax is an input error. Normative fixtures remain open. |

## Implementer Audit Addendum (Not Independent Review)

A later implementer pass compared the candidate schema against the pinned Haskell source. It replaced fractional JSON number tokens with bounded decimal strings (and a tagged representation for text-versus-number thresholds), defined ASCII-only Isoprax normalization, and separated RFC 8785 object-key ordering from evidence/threshold collection ordering. These changes are candidate compatibility decisions and have not been independently rechecked. The pointer table uses composite group pointers for broad definition differences and concrete leaf pointers for unknown values and measurement identifiers; it does not claim a leaf pointer for every semantic difference.

The addendum does not close R1 or R2 and is not evidence for T010. Canonical Semadmit vectors, complete domain fixtures, and an independent review are still required before M0 approval.

## Review Limits

This review checked the written contract and handoff, not source behavior. It did not verify the mapped Isoprax API, reproduce historical checks, or validate candidate rules against an Isoprax checkout. No implementation or conformance evidence is implied by this record.

## Scope Change Addendum — 2026-09-30

The product goal was later clarified to make Semadmit a reusable core with a public typed pack interface and a downstream MTG Ducky-style adoption example. This review predates that scope. It does not assess the generic binding records, public pack interface, host registration/versioning rules, or the neutral extension fixture, and it does not satisfy independent review for the current M0 gate. Ducky-specific acceptance remains an M4 review item after the interface is frozen.

## Independent M0 Recheck — 2026-09-30

An independent read-only adversarial sub-agent reviewed the current shared Core contract, public Python pack interface, Isoprax and measurement tables, neutral extension descriptor and fixtures, canonical vectors and fixture consistency evidence from the preceding T009 pass, and threat model. The reviewer found no remaining material M0 blocker and approved the written contract and fixture package. The earlier findings above remain a history of the pre-recheck draft; this disposition supersedes their open M0 status.

The review exposed and drove closure of these contract gaps:

- The neutral pack descriptor now explicitly declares policy, subject, evidence, and component identity kinds, schemas, and projections, plus diagnostic pointer templates, field order, set key, outcomes, and resource limits.
- The built-in packs now have complete obligation/component declarations and a generic plus operation-specific parser error-code/pointer mapping.
- Direct Python evaluation and verification now bound request and candidate-decision copies independently by size and depth before full materialization.
- Core and trusted packs now require decisions to be pure functions of normalized request and exact pack version, excluding randomness and mutable process history.
- The plan records dependency and Isoprax provenance review as post-M0 setup work and owner license approval as a pre-release gate; later conformance tasks cover repeated/reordered evaluations and candidate bounds.

The published canonicalization vectors and candidate artifact bytes/digests were independently recomputed during T009 preparation; the current recheck found no remaining fixture/contract contradiction. This approval makes the M0 contract and fixture set normative for v0.1 implementation. It does not claim that a parser, evaluator, verifier, pack, guarded consumer, or open-source package has passed implementation checks. Those checks remain assigned to M1–M6. Concrete Python record class definitions are M1 choices within the frozen behavioral API; changing normative semantics requires the version rules in the pack contract.

After this review, the owner delegated license selection. Apache-2.0 was applied to the repository and package manifests; T043 still requires the dependency and redistribution inventory before release.
