# Data Model: Semadmit Reusable Core v0.1

This is the normative v0.1 M0 logical model approved by independent review on 2026-09-30. Implementation conformance remains unproven.

## Core Request and Pack Registry

### Request

The core request envelope contains protocol, pack, operation, policy_digest, policy, subjects, and evidence. Those top-level fields are fixed. The selected registered pack defines the closed nested schemas, subject roles/cardinality, normalization, and ordering for policy, subjects, and evidence. Unknown fields are rejected by the core envelope or pack schema. The request digest covers the exact normalized common request projection defined in contracts/pack-interface.md. It includes protocol, exact pack/version ID, operation, recomputed and verified policy_digest, normalized policy, normalized subjects, and normalized evidence. The policy_digest is included even though it is recomputable.

### Pack

A pack is trusted typed application code with a namespaced versioned ID, a closed set of operations, input schemas, identity projections, resource limits, deterministic evaluator, stable obligations/diagnostics, and binding declarations. A host explicitly registers pack modules. Request data may select a registered pack but cannot load or execute code. Unknown packs and versions are protocol errors.

The Python API is the v0.1 in-process pack-author and consumer interface. The language-neutral JSONL contract lets callers use packs already registered by a running implementation; it is not a foreign-language pack-loading ABI. The Haskell reference evaluator and Python package independently implement shared Core and maintained first-party packs. A downstream pack must provide its own fixtures; cross-implementation conformance is claimed only when a second evaluator for that pack is checked.

### Policy manifest

A policy is fixed-schema bounded data supported by the selected pack. Caller-supplied expressions are never executed. Its content digest binds every parameter. The Isoprax policy has min_events in 1–100,000, n_bins in 1–1,000, max_ece in [0,1], definition_comparison=normalized-key/0.1, and numeric_profile=decimal-rational-12/0.1. Requiring both outcome classes and nonzero score variance are fixed isoprax/0.1 rules, not caller-selectable fields. Every non-integer policy and domain quantity uses a canonical decimal string; JSON numbers are safe integers only. Each pack publishes its own constraints and fixtures.

## Subjects, Components, and Evidence

### Generic subject

A subject is one pack-defined exact input with a pack-defined role. The common result binding carries role, kind, schema, and the digest recomputed from the complete validated subject. Core does not require the names `left` and `right` or a fixed number of subjects. Built-in Isoprax and measurement packs currently use two roles; additional packs declare their own role set.

### Component artifact

A pack may expose separately addressable child identities through generic component bindings `(subject_role, name, kind, schema, digest)`. The operation descriptor declares each component's schema and per-role cardinality; Core enforces those counts before issuing a decision. The Isoprax pack uses components for a definition and a present sample nested in a role. A measurement pack can have no components. A downstream pack can bind a deck revision, target, or meta snapshot without adding product-specific fields to Core. All component contents are also covered by the complete subject and request identities.

### Isoprax definition and sample

The Isoprax schemas, nullability, normalized key, and diagnostic pointers are specified in `contracts/wire-protocol.md` and `contracts/decision-tables.md`. A definition's identity binds its declared ID and complete validated content. IDs are labels, not proof of semantic equality: direct compatibility compares normalized semantic keys, while IDs and definition digests remain separately bound as components. A sample binds ordered score/outcome pairs to a definition digest. Absent and empty samples remain distinct.

Scores are canonical decimal strings in [0,1], with at most 12 fractional digits; exponents, leading plus signs, leading zeros, trailing fractional zeros, negative zero, and values outside the numeric profile are rejected. Outcomes are JSON integers 0 or 1; booleans are rejected. Pair-array lengths must match. Sample row order is preserved in identity.

### Evidence

Evidence has a pack-defined stable ID, kind, schema, subject/policy bindings, and payload. Duplicate IDs are rejected. Evidence identity binds complete validated content. The common top-level evidence collection is a set sorted by ID after validation; nested evidence arrays are sorted only where the selected pack declares set semantics. The common result binds each evidence item with ID, kind, schema, and recomputed digest.

### Measurement subject and coverage

A measurement subject carries quantity ID, unit ID, method ID, reference-frame ID, context/population ID, and one declared window. A window has bounded integer start/end ticks in the POSIX-millisecond timescale `unix-ms-utc-v1` and uses half-open endpoints with start < end. Its identity uses kind `subject` and schema `measurement/0.1/subject`. v0.1 requires identical declared windows; no disjoint-window merge or unit conversion is inferred.

Coverage binds the exact measurement subject, current policy digest, and declared window and carries a supplied count greater than zero. Missing coverage is missing evidence; a contradictory subject, policy, or window is a failed obligation; malformed supplied data is an input error. A positive count is a supplied fact, not verified real-world coverage. The measurement pack emits only an eligibility decision; it carries no measurement values and computes no aggregate.

## Identity and Results

### Content identity

Artifact identity is SHA-256 of RFC 8785 JCS bytes for a structured envelope containing kind, schema, and payload. Core and each registered pack declare accepted kind/schema pairs. Pack artifact schemas are namespaced by pack and version. M0 fixtures specify exact bytes and digests. No Unicode normalization is applied unless an explicit pack contract requires it.

### Decision state

- **admissible**: every operation-declared obligation is present exactly once and passes.
- **inadmissible**: one or more evaluated obligations fail.
- **indeterminate**: no obligation fails and at least one declared requirement is missing or explicitly unknown.

Every operation declares a fixed complete obligation set and Core requires exactly one outcome per ID before state reduction. Omission, duplication, or undeclared output is `internal.failure`. Missing evidence is represented by a `missing` outcome; it is never represented by omitting the obligation.

Malformed data and unsupported protocol, pack, operation, or policy are errors, not decision states. Failure takes precedence over missing evidence.

### Decision artifact

A valid-result envelope contains exactly kind, payload, and decision_digest. Kind is decision. Payload contains exactly protocol, pack, operation, request_digest, policy_digest, state, bindings, obligations, and diagnostics.

Bindings contain subjects, components, and evidence. Subject entries bind role/kind/schema/digest; component entries bind subject role/name/kind/schema/digest; evidence entries bind ID/kind/schema/digest. Each list is sorted by its generic keys. Empty collections are empty arrays. Obligations contain ID and pass/fail/missing outcome, sorted by ID. Diagnostics contain obligation_id, JSON Pointer, and code; they are sorted by obligation_id, pointer, and code and deduplicated. The decision digest hashes the canonical payload without the digest field.

Execution metadata, build identity, telemetry, and human-readable messages are outside the normative payload. Inadmissible and indeterminate outputs have no admission value.

### Admission snapshot

Admission is opaque and created only after a trusted local evaluator validates the exact request, recomputes request and policy identities, evaluates the registered pack/version, and compares every normative field and decision digest with the candidate artifact. A deserialized admissible flag or self-consistent supplied digest cannot create admission. Admission retains the validated immutable request and pack snapshot; guarded operations consume it or reject changed inputs. Mutable file/database consumers require an immutable content-addressed snapshot or one atomic read/verify/use transaction.

## Calibration Calculation

For n_bins equal-width bins, the bin index is min(floor(score × n_bins), n_bins − 1). Empty bins contribute zero. ECE is the sum over nonempty bins of (bin count / total count) times the absolute difference between mean score and mean outcome. Arithmetic is exact rational arithmetic; fixture sidecars record defined ECE values as reduced numerator and denominator strings. ECE remains internal and is not a field in the v0.1 decision envelope. A sample passes only when its count is at least min_events, contains both outcomes, has nonzero score variance, and ECE is no greater than max_ece. M0 fixtures must cover equality boundaries and the explicit RFC 8785 binary64-to-decimal adapter mapping.
