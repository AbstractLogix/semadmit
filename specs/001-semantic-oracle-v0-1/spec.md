# Feature Specification: Semadmit Reusable Core v0.1

**Feature Branch**: main (specification work only)

**Created**: 2026-09-29

**Status**: M0 contract approved on 2026-09-30. Implementation and release gates remain open.

**Input**: A proposed semantic-oracle contract and the user's clarified product goal: capture the evidence-bound decision mechanism developed in Isoprax as reusable open-source software for other projects.

## Overview

Build Semadmit as a reusable offline core for deterministic decisions based on evidence. Reuse the mechanism developed in Isoprax. The core uses closed, versioned requests. It binds exact content and policy. It records each obligation as pass, fail, or missing. It verifies decisions locally. It uses the same immutable snapshot that it checked.

Closed, versioned packs define domain meaning. Isoprax prediction pooling is the founding pack. A narrow measurement pack checks that the core serves another domain without Isoprax concepts. A separately authored MTG Ducky sideboard-evidence pack will test downstream use. It must use the public pack interface and shared identity/result behavior. It must not copy or change Core. Ducky keeps its source data, ingestion, storage, and product behavior.

The intended deliverable is open-source software. A Python-hosted application can install it and add packs through a documented typed interface. A host registers packs. Callers use the language-neutral JSONL protocol to call registered packs. The protocol does not load packs across languages.

Shared identity, verification, and evidence-state handling may reduce duplicated correctness logic for adopters. The Ducky-style example will record whether this reuse works and where the interface creates friction. The example does not prove broader demand. The decision path stays local/offline. Packs are trusted application code that the host registers. Caller-supplied policies are data; the core never executes them. Version 0.1 does not include a server, dynamic plugin ABI, general rule language, or production Isoprax behavior.

This repository contains the approved M0 contract and fixtures, partial M1 Core evaluators, a shared positive/negative registered-pack slice, and a fixture-tested registry-injected Haskell `Core.CLI` runner. It has no maintained first-party packs or wired Haskell CLI executable, complete domain evaluator, package release, or downstream integration.

## User Scenarios & Testing

### M0 Contract Gate (Prerequisite)

Before implementation, M0 must close and independently review these items: shared request/result/error envelopes; generic subject and artifact bindings; the Python-hosted pack interface; pack registration and version rules; identity vectors; Isoprax and measurement decision tables; obligation and diagnostic vocabularies; resource limits; the threat model; and the ownership/license assumptions for an open-source release. A neutral extension-pack fixture must test registration and shared result behavior without Ducky-specific rules. M4 defines the Ducky domain contract against the frozen interface. M0 closes only when each blocker has a documented resolution and normative fixture.

### User Story 1 — Reuse the offline decision core (Priority: P1, M1)

As an application maintainer, I need to submit a bounded request to a reusable local evaluator and receive a deterministic result, so I can reuse Semadmit's identity, verification, and decision-envelope behavior instead of rebuilding it in my application.

**Why this priority**: The shared core and usable interface are the product; domain packs demonstrate its semantics.

**Independent Test**: An offline caller sends positive and negative requests through the supported public interface. Independent evaluators agree on canonical bytes, digests, states, generic bindings, obligations, diagnostics, and errors for built-in packs.

**Acceptance Scenarios**:

1. **Given** a valid request for a registered pack, **When** evaluated offline, **Then** the result is deterministic and binds the exact request, policy, subjects, component artifacts, and evidence.
2. **Given** malformed input or an unregistered pack, **When** evaluated, **Then** a stable protocol error is returned with no admission value.
3. **Given** an inadmissible or indeterminate request, **When** evaluated, **Then** all applicable obligations are returned and no admission value is present.
4. **Given** a candidate result artifact, **When** a trusted local verifier checks it, **Then** the verifier reevaluates the exact request and constructs admission only from its own matching result.

### User Story 2 — Preserve the Isoprax founding semantics (Priority: P1, M2)

As an Isoprax reporting consumer, I need pooling to require compatible complete outcome definitions and locally recomputed calibration for both exact samples under one supported policy, so a label, assertion, or stale report cannot authorize pooling.

**Why this priority**: Isoprax is where the reusable mechanism was discovered and remains the first end-to-end semantic pack.

**Independent Test**: Exercise positive and negative Isoprax requests with definition, policy, calibration, digest, and mutation cases; verify the guarded operation consumes the exact snapshot whose bindings were evaluated.

**Acceptance Scenarios**:

1. **Given** matching complete definitions and both samples meeting the bound calibration policy, **When** the consumer verifies and pools, **Then** it consumes the verified immutable snapshot.
2. **Given** the same definition ID with changed semantic content, a failed calibration threshold, or a changed policy, **When** verification is attempted, **Then** pooling is rejected and all applicable diagnostics are reported.
3. **Given** an absent sample, **When** evaluated, **Then** the relevant obligation is missing; given a supplied empty sample, it fails the minimum-event rule.
4. **Given** caller-owned arrays or files change after verification, **When** the guarded operation runs, **Then** it uses the original verified snapshot or rejects the operation.
5. **Given** two complete definitions have different IDs but equal normalized semantic keys, **When** evaluated under the direct-comparison policy, **Then** compatibility passes while both definitions and samples remain bound to the request and result.

### User Story 3 — Check measurement eligibility with the shared core (Priority: P2, M3)

As a measurement consumer, I need an eligibility decision only when all required semantic identifiers and the declared window match and each subject has matching positive-count coverage evidence. Semadmit does not receive measurement values or calculate an aggregate; downstream aggregation is outside the v0.1 consumer API.

**Why this priority**: A second first-party pack checks that the reusable core is not tied to Isoprax calibration.

**Independent Test**: Evaluate positive, metadata mismatch, missing coverage, malformed coverage digest, policy-digest mismatch, contradictory-window, and substituted-subject fixtures through the shared implementations.

**Acceptance Scenarios**:

1. **Given** matching complete measurement metadata, identical windows, and valid coverage for every subject, **When** evaluated, **Then** the decision is admissible and no aggregate value is produced.
2. **Given** a known metadata or window mismatch, **When** evaluated, **Then** the result is inadmissible even if other evidence is missing.
3. **Given** absent coverage, **When** evaluated, **Then** the result is indeterminate; a well-formed policy-digest mismatch or other contradictory coverage fails its obligation; malformed supplied digest syntax is an input error.

### User Story 4 — Add a downstream domain pack (Priority: P1, M4)

As a Python-hosted downstream project maintainer, I need to define and register a typed pack through Semadmit's public interface, so my project can reuse the core protocol, identity, verification, and result behavior without copying or editing those core mechanisms.

**Why this priority**: A reusable-library claim needs a demonstrated adoption path beyond Semadmit's built-in packs.

**Independent Test**: Add a separately packaged Python example based on MTG Ducky's existing sideboard-evidence eligibility contract. It binds one exact deck revision and selected meta snapshot; covers observed target coverage, sideboard-card availability, local format legality, color compatibility, Oracle-text-backed role evidence, and source/coverage/recency/limitation metadata; and passes the shared conformance harness without edits to generic Core or result-protocol code. Evaluate freshness only against explicit request/policy time or window values, never the wall clock. Record which shared mechanics it reused, which responsibilities remain in Ducky, and any adapter friction or unmet need.

**Acceptance Scenarios**:

1. **Given** a pack module with a namespaced versioned identity and closed schemas, **When** a host registers it, **Then** the shared evaluator handles its envelope, identity, result ordering, and verification through the public API.
2. **Given** an unknown or unregistered pack identifier, **When** evaluated, **Then** the evaluator returns a stable unsupported-pack error.
3. **Given** a Ducky-style request bound to one immutable deck revision and selected meta snapshot, with qualifying observed target coverage, available sideboard cards, local format legality, exact color compatibility, Oracle-text-backed role evidence, source URLs, coverage kind, recency/window metadata, and explicit limitations, **When** its pack evaluates, **Then** the result states only whether the sideboard-guide evidence requirements pass; Ducky retains the source-attributed snapshot and remains responsible for selecting, generating, and displaying the guide.
4. **Given** a supported pack's semantics change, **When** released, **Then** the pack version changes and prior fixture identities remain reproducible.
5. **Given** the example pack is complete, **When** its adoption is reviewed, **Then** it passes only if it uses the installed public API without changing generic Core/result behavior or copying Core identity, binding, state-reduction, or verification logic; the record lists reused behavior, Ducky-owned behavior, and any friction. Otherwise M4 is a failed extension proof and the reusable-pack claim must be revised.

### User Story 5 — Qualify conformance and an open-source release candidate (Priority: P2, M5–M6)

As a maintainer, I need reproducible fixtures, generated cases, mutation checks, parser limits, package and license records, and independent review, so adopters can judge what the implementation guarantees and how to consume it.

**Independent Test**: Reproduce the recorded release run from a clean checkout, account for every differential mismatch, and verify all acceptance gates before proposing publication.

**Acceptance Scenarios**:

1. **Given** the pinned toolchains and fixed generator seeds, **When** the release run is repeated, **Then** all maintained implementation results agree and no unexplained difference remains.
2. **Given** a selected mutation that removes a binding or changes a threshold comparison, **When** the conformance suite runs, **Then** the corresponding check detects it.
3. **Given** a completed candidate, **When** reviewed, **Then** the report lists exact SHAs, commands actually run, package and license status, discrepancies, intentional differences, limitations, and gate status; publication remains a separate decision.

## Edge Cases

- Missing samples versus supplied empty samples; absent evidence versus explicit unknown values.
- A known failed obligation alongside missing evidence: failure determines the overall state while both diagnostics remain visible.
- Malformed values, duplicate JSON keys, duplicate evidence IDs, unknown fields, invalid UTF-8, unpaired surrogates, excessive nesting or size, booleans used as integers, and unsupported protocol, pack, operation, or policy.
- Scores at 0 and 1, exact threshold equality, maximum decimal precision, negative zero, exponent notation, unequal score/outcome lengths, and sample row permutation.
- Same definition label with changed content; policy edits; altered operation; forged request, evidence, or decision digest.
- Mutable input arrays or files changed between verification and consumption.
- Measurement subject substitution, missing coverage, contradictory coverage window, zero count, and differing semantic identifiers.
- A pack registered by one host but absent from another host; pack-version mismatch; component artifacts with missing or substituted subject bindings.
- A pack omitting a declared obligation or required component; the host rejects the incomplete result instead of reducing the partial set to admissible.
- A Ducky sideboard guide with stale or partial meta evidence, unavailable observed sideboard cards, illegal cards, or missing role evidence.

## Requirements

### Functional Requirements

- **FR-001**: The v0.1 contract MUST define a local/offline request protocol for single requests and JSONL evaluation; the Haskell reference CLI MUST support maintained first-party packs and the Python `JsonlRunner` MUST use its explicitly registered evaluator. Stdout MUST contain machine results only and logs MUST go to stderr.
- **FR-002**: A valid decision MUST be exactly one of admissible, inadmissible, or indeterminate. Input/protocol errors MUST be separate and MUST carry no admission.
- **FR-003**: A known failed obligation MUST take precedence over missing evidence; malformed values MUST be errors, not missing evidence.
- **FR-004**: The shared result envelope MUST have closed, domain-neutral fields, deterministic ordering, stable obligation outcomes, and stable diagnostic identifiers. Pack-specific labels MUST NOT be hard-coded into Core result fields.
- **FR-005**: The contract MUST define canonical identity using RFC 8785 JCS and SHA-256 over a kind/schema/payload envelope. Every supplied digest MUST be checked against recomputation.
- **FR-006**: Domain decimals MUST use canonical decimal strings and exact rational arithmetic where required by a pack; collection ordering MUST be explicit and schema-specific.
- **FR-007**: Semadmit v0.1 MUST expose a versioned typed Python pack interface and a language-neutral request/result protocol. A pack MUST declare its identity, operations, closed policy/subject/evidence schemas, identity projections, role/cardinality rules, the complete obligation set for each operation, component cardinalities, diagnostics, bindings, validation order, and limits. Core MUST reject omitted or duplicate obligation output and component-cardinality violations before deriving state. Python hosts MUST explicitly register trusted pack code; unknown packs MUST fail closed. JSONL is an interoperability protocol, not a cross-language pack-loading ABI.
- **FR-008**: Prediction pooling MUST require complete compatible definitions and qualifying calibration recomputed for both exact samples under a supported policy; the policy identity MUST bind definition-comparison and numeric-profile IDs plus every threshold parameter; a declared ID or asserted pass value MUST NOT substitute for content or computation.
- **FR-009**: A usable Isoprax admission MUST bind definition, sample, policy, evidence, operation, and immutable input snapshot. A trusted verifier MUST reevaluate the exact request locally and compare every normative field and digest before creating opaque admission; verification and guarded use MUST consume the same snapshot.
- **FR-010**: Measurement admission MUST require identical declared windows, matching required semantic identifiers, and positive-count coverage bound to every exact measurement subject, policy digest, and window. The oracle MUST return an eligibility decision only; actual aggregation and measurement values are outside the v0.1 consumer API.
- **FR-011**: A Ducky-style Python pack MUST exercise the public pack API with an immutable deck revision and selected meta snapshot. It MUST evaluate supplied target-coverage, sideboard-card availability, local-legality, color-compatibility, card-text-backed role, source URL, coverage kind, recency/window, and limitation evidence. Freshness checks MUST use explicit request/policy time or window values, never the wall clock. It MUST express evidence eligibility only and MUST NOT claim matchup probability, win rate, deck quality, card legality beyond supplied evidence, or source truth.
- **FR-012**: The project MUST maintain independent evaluators against normative Core and first-party pack contracts and fixtures. A downstream pack MUST provide its own fixtures; independent cross-implementation conformance is claimed only when two evaluators are checked.
- **FR-013**: Conformance work MUST include published JCS vectors, complete normative fixtures, property checks, differential comparison, shrinking, selected mutation checks, parser/resource-boundary cases, and pack-extension checks.
- **FR-014**: Release readiness MUST include pinned toolchains and dependencies, a selected redistribution license, reproducible package/build/test commands, provenance, independent review, exact discrepancy records, and an explicit limitations report. Publishing requires a separate decision.
- **FR-015**: The v0.1 decision path MUST not retrieve network data, read ambient environment or working-directory files, use wall clock, execute supplied policies, authenticate issuers, or change Isoprax production behavior.
- **FR-016**: The repository MUST maintain explicit source-coverage thresholds separately for the Python and Haskell implementations. One deterministic gate MUST run their tests under coverage instrumentation, fail closed when expected modules or suites are not measured, and be invoked by hosted CI and the local pre-commit hook.

### Key Entities

- **Core request**: Validated protocol, registered pack, operation, policy, pack-declared subjects, and evidence; source of request identity.
- **Pack**: Trusted typed code plus a closed versioned contract for domain inputs, identities, obligations, diagnostics, and limits.
- **Policy manifest**: Fixed-schema bounded data supported by a registered pack, content-addressed and bound to the decision.
- **Subject**: Pack-defined exact input; its complete validated content is bound by a generic role/schema/digest record.
- **Component artifact**: Optional pack-defined identity such as an Isoprax definition or sample, represented through generic kind/schema/digest fields.
- **Evidence**: Typed payload with stable ID and exact pack-defined subject/policy bindings.
- **Obligation**: Stable named condition with pass, fail, or missing outcome.
- **Diagnostic**: Stable obligation identifier, JSON Pointer, and code; prose is non-normative.
- **Decision artifact**: Exact normative result payload plus digest; execution/build identity is separate.
- **Admission snapshot**: Validated immutable inputs retained for a guarded consumer operation.
- **Pack registry**: Explicit host-owned set of trusted pack implementations; it is not dynamically populated from request data.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Before M1 implementation begins, M0 contains closed generic envelopes, a public pack contract, generic subject/component/evidence bindings, complete per-operation obligation and component-output requirements, core error vocabulary, canonical vectors, every first-party pack decision table, limits, and threat model, with no implementation-blocking question unresolved.
- **SC-002**: Independent evaluators produce identical canonical bytes, request and decision digests, state, generic bindings, obligations, and diagnostic identifiers for every normative Core and first-party pack fixture.
- **SC-003**: A separately packaged Ducky-style Python pack uses the public API and shared conformance harness without changes to generic Core/result behavior or copied Core identity, binding, state-reduction, or verification logic; it covers admissible, inadmissible, indeterminate, and input-error outcomes. Its adoption record identifies reused behavior, retained Ducky responsibilities, and friction. Failure of those conditions fails the M4 extension proof; passing it validates one extension path, not broader market demand.
- **SC-004**: Each maintained first-party pack has at least 10,000 generated cases covering valid and invalid inputs in its recorded release run, with fixed seeds and coverage classified by obligation, state, and boundary.
- **SC-005**: No unexplained differential mismatch remains; every selected mutation is caught; all required parser/resource cases and consumer substitution cases are represented.
- **SC-006**: A release-readiness report records exact source SHAs and commands actually run, package and license status, dependency inventory, discrepancies and resolutions, intentional Isoprax differences, remaining limitations, and each gate as passed or not passed.
- **SC-007**: The shared coverage gate passes only when every Python package module has at least 100% executable-line coverage, production Haskell modules have at least 89% HPC expression coverage and 34% boolean coverage, all expected test suites ran, and both hosted CI and the local pre-commit configuration invoke the same gate.

## Assumptions and Contract Gates

- The handoff is proposed input, not evidence that any review, implementation, or historical finding is complete.
- The Isoprax implementation mapping is a historical candidate baseline only. It does not establish Semadmit protocol, pack-interface, or measurement conformance.
- The Haskell reference CLI registers only maintained first-party packs. Python hosts register trusted Python packs explicitly and may expose them through `JsonlRunner` or call the evaluator directly. JSONL does not load code, and non-Python pack registration requires a separately reviewed interface.
- The current Semadmit checkout has an approved contract, package manifests, partial Core evaluators, shared generic positive/negative vectors, and a fixture-tested registry-injected Haskell `Core.CLI` runner. Maintained first-party packs and the wired Haskell CLI executable, complete domain evaluation, and release remain open. Apache-2.0 has been selected; package, dependency, provenance, and conformance checks remain release gates.
- The Ducky-style example tests the extension path against one realistic use case; it does not establish general adopter demand or that every project benefits from Semadmit.
- Isoprax production code remains independent; the adapter exercises the oracle only in tests/CI.
- Hashes provide content identity, not authenticity. Samples, coverage, and downstream Ducky evidence may be fabricated; v0.1 does not make real-world truth claims.
- No expiry, online retrieval, signing, runtime policy scripting, inferred semantic equivalence, automatic unit conversion, hosted service, or publication is in scope.
