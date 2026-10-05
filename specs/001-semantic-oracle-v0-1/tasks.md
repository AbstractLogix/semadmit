# Tasks: Semadmit Reusable Core v0.1

**Input**: Design documents in specs/001-semantic-oracle-v0-1/

**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md

**Status**: M0 written contract and fixtures were approved after independent review on 2026-09-30. T012–T019, T021–T025, and T046 are complete. The Haskell/Python Core evaluators, Python verification/JSONL APIs, generic bindings, shared positive/negative vectors, Isoprax subject types, identities, calibration, pooling evaluator, and first-party Haskell executable are implemented. Feature 002 adds structured claim verification. Guarded consumption, independent Python Isoprax parity, Measurement packs, the downstream extension, and broader generated and mutation conformance remain open.

## Format

Tasks use a checkbox, sequential ID, optional parallel marker, optional user-story marker, action, and concrete target path. Test tasks are included because the accepted specification requires conformance evidence; this specification-only change does not run them.

## Phase 1: Setup (Specification Baseline)

**Purpose**: Establish the Spec Kit feature and document the product baseline.

- [x] T001 Initialize the official Spec Kit generic integration and command templates in .specify/init-options.json and .agents/commands/
- [x] T002 Create the active feature specification, plan, and index in specs/001-semantic-oracle-v0-1/ and specs/README.md
- [x] T003 Draft the data model, wire protocol, decision tables, threat model, research, fixtures, and validation guide under specs/001-semantic-oracle-v0-1/ and conformance/fixtures/

---

## Phase 2: Foundational (M0 Contract Gate)

**Purpose**: Approve a domain-neutral core contract and a usable public pack interface before implementation.

- [x] T004 Record the historical Isoprax source references and map Haskell/Python definition, calibration, pooling, identity, CLI, and evidence behavior plus contract gaps in specs/001-semantic-oracle-v0-1/contracts/isoprax-mapping.md
- [x] T005 Freeze the registered-pack request dispatch, pack-specific subject roles, generic subject/component/evidence bindings, and result/error envelopes in specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md
- [x] T006 Define the public typed pack interface, pack-ID grammar/versioning rules, host registration boundary, and pack-author conformance obligations in specs/001-semantic-oracle-v0-1/contracts/pack-interface.md
- [x] T007 Freeze the exact request identity preimage, evidence set ordering, pack-declared artifact kinds/schemas, canonicalization, and policy binding rules in specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md and specs/001-semantic-oracle-v0-1/data-model.md
- [x] T008 Assign the complete per-operation obligation set, component cardinalities, diagnostic code, JSON Pointer, and parser error code for every built-in pack in specs/001-semantic-oracle-v0-1/contracts/decision-tables.md
- [x] T009 Add complete positive, negative, missing, malformed, boundary, and incomplete-pack-output fixtures plus independently recomputed canonical bytes/digests for both built-in packs and a neutral generic extension pack; include passing and failing evidence-permutation pairs with normalized diagnostic pointers and published RFC 8785 vectors in conformance/fixtures/
- [x] T010 Complete the threat model for untrusted request data, trusted registered pack code, snapshot substitution, and unsigned results in specs/001-semantic-oracle-v0-1/contracts/threat-model.md
- [x] T011 Obtain independent M0 review of the shared Core, Python pack interface, built-in pack contracts, neutral extension fixture, vectors, and threat model in specs/001-semantic-oracle-v0-1/contracts/review.md

**Checkpoint**: M0 was approved after the generic envelopes, Python pack interface, Isoprax and measurement schemas/tables, neutral extension fixture, vocabularies, vectors, limits, threat model, and independent review were complete. T005–T011 record that completed gate. Ducky-specific schemas and evidence rules are an M4 gate.

### Runtime Setup (After M0)

- [x] T012 Pin the supported Haskell and Python toolchains, platforms, and package versions in cabal.project and clients/python/pyproject.toml
- [x] T013 Select and license-review JSON, JCS, CLI, exact-arithmetic, and Python package dependencies plus the reproducible Isoprax source-integration method in semantic-oracle.cabal and clients/python/pyproject.toml
- [x] T014 Create the Haskell and Python Core/Pack API skeletons and registry in src/Core/Pack.hs and clients/python/semadmit/

---

## Phase 3: User Story 1 — Reuse the Offline Decision Core (M1, Priority: P1)

**Goal**: Let a local caller reuse canonical identity, strict protocol handling, deterministic results, and verification through the public API and language-neutral CLI.

**Independent Test**: Run one positive and one negative registered-pack request through Haskell and Python. Compare canonical bytes, request and decision digests, generic bindings, state, obligations, diagnostics, errors, and exit status.

### Contract and Parser Checks

- [x] T015 [P] [US1] Add generic request/result/error, registered-pack, and unknown-pack contract checks in test/contract/protocol/
- [x] T016 [P] [US1] Add published RFC 8785 vectors and generic kind/schema/payload identity checks in conformance/fixtures/, test/identity/, and clients/python/tests/test_identity.py

### Implementation

- [x] T017 [US1] Implement strict UTF-8 JSON parsing, duplicate-key rejection, core limits, and envelope validation in src/Core/Protocol.hs
- [x] T018 [US1] Implement JCS canonical bytes and pack-declared kind/schema/payload SHA-256 identities in src/Core/Identity.hs
- [x] T019 [US1] Implement the shared pack registry, generic bindings, complete obligation/component-output validation, deterministic states, diagnostics, and decision digest in src/Core/Decision.hs
- [x] T020 [US1] Wire the tested registry-injected Core.CLI runner to app/Main.hs and add request/output/exit-code acceptance tests for maintained first-party packs when available
- [x] T021 [US1] Implement the public Python API, pack registration, independent core evaluator, and JsonlRunner over an explicitly supplied evaluator in clients/python/semadmit/
- [x] T022 [US1] Run a complete positive and negative registered-pack vertical slice through both implementations in test/integration/vertical_slice/

---

## Phase 4: User Story 2 — Preserve Isoprax Founding Semantics (M2, Priority: P1)

**Goal**: Implement Isoprax prediction pooling behind the pack interface and consume the exact verified snapshot.

**Independent Test**: Exercise positive and negative pool requests through both evaluators and prove changed definitions, policies, samples, or evidence cannot reuse an admission.

- [x] T023 [P] [US2] Adapt mapped Isoprax definitions and component identities to the public pack interface in src/Pack/Isoprax/Types.hs
- [x] T024 [P] [US2] Implement the approved numeric conversion and exact calibration policy in src/Pack/Isoprax/Calibration.hs
- [x] T025 [US2] Implement direct definition compatibility, calibration obligations, and stable diagnostics in src/Pack/Isoprax/PoolPredictions.hs
- [ ] T026 [US2] Implement snapshot-bound verification and guarded consumption in src/Pack/Isoprax/Admission.hs
- [ ] T027 [US2] Implement the independent Python Isoprax pack evaluator in clients/python/semadmit/packs/isoprax.py
- [ ] T028 [US2] Add the Isoprax baseline adapter and compare every mapped field in clients/python/isoprax_adapter.py
- [ ] T029 [US2] Add digest substitution, threshold equality, empty/absent sample, and post-verification mutation cases through both evaluators in test/integration/isoprax/

---

## Phase 5: User Story 3 — Check Measurement Eligibility (M3, Priority: P2)

**Goal**: Add a second first-party pack without importing Isoprax types into Core.

**Independent Test**: Evaluate positive, mismatch, missing, malformed, contradictory-window, and substituted-subject measurement fixtures through both evaluators.

- [ ] T030 [P] [US3] Implement measurement subject, window, and coverage validation behind the pack API in src/Pack/Measurement/Types.hs
- [ ] T031 [P] [US3] Implement measurement compatibility and coverage obligations in src/Pack/Measurement/AggregateMeasurements.hs
- [ ] T032 [US3] Implement the independent Python measurement pack, compare it with the Haskell evaluator on pack fixtures, and assert there are no Isoprax/calibration imports in clients/python/semadmit/packs/measurement.py, conformance/fixtures/measurement/, and test/integration/measurement/

---

## Phase 6: User Story 4 — Add a Downstream Domain Pack (M4, Priority: P1)

**Goal**: Demonstrate that a downstream Python application can add a typed pack and reuse Core without copying or changing it.

**Independent Test**: Build the separately packaged Ducky-style pack through the public Python API. Exercise admissible, inadmissible, indeterminate, and input-error cases for one exact deck revision and meta snapshot; verify generic Core and the shared result schema require no edits.

- [ ] T033 [P] [US4] Document pack identity, schemas, evaluation, binding, diagnostics, limits, and registration in docs/pack-author-guide.md
- [ ] T034 [US4] Define the Ducky-style sideboard-evidence example contract and evidence-boundary fixtures in examples/mtg_ducky_pack/spec.md and examples/mtg_ducky_pack/fixtures/
- [ ] T035 [US4] Implement the separately packaged sideboard-evidence pack through the public API in examples/mtg_ducky_pack/
- [ ] T036 [US4] Add integration cases binding the same immutable deck revision and meta snapshot at verification and guarded use in examples/mtg_ducky_pack/tests/
- [ ] T037 [US4] Verify unknown-pack rejection, pack-version changes, and unchanged generic Core conformance in test/integration/pack_extension/; record reused Core behavior, retained Ducky responsibilities, and interface friction in docs/adoption-evaluation.md

---

## Phase 7: User Story 5 — Qualify Conformance and Release Candidate (M5–M6, Priority: P2)

**Goal**: Record reproducible implementation evidence, pack-author instructions, license status, and limitations for a reviewable open-source release candidate.

**Independent Test**: Repeat the full recorded run from a clean checkout, account for every differential mismatch, and verify that every selected mutation is detected.

- [ ] T038 [P] [US5] Add seeded valid/invalid generators and shrinkers classified by first-party pack obligation, state, and boundary in conformance/generators/
- [ ] T039 [US5] Run at least 10,000 generated cases per first-party pack through both evaluators, compare all normative fields, and record fixed seeds and coverage counts in docs/conformance-run.md
- [ ] T040 [P] [US5] Add binding-removal, threshold, unknown-semantics, asserted-pass, and skipped-obligation mutations in test/mutation/
- [ ] T041 [US5] Add parser, size/depth, JSONL recovery, duplicate-key, surrogate, bool-as-int, and limit cases in test/contract/parser/
- [ ] T042 [US5] Add direct candidate-result size/depth bounds, repeated/reordered evaluation, exact consumer verification, and snapshot-substitution cases for every maintained pack in test/integration/verification/
- [ ] T043 [US5] Complete Apache-2.0 package/license-file checks, direct and transitive dependency redistribution notices, and provenance inventory in LICENSE and docs/release-readiness.md; the owner delegated license selection on 2026-09-30
- [ ] T044 [US5] Record clean build, package, test, and example-pack commands; SHAs; discrepancies; limitations; and gate status in docs/release-readiness.md
- [ ] T045 [US5] Obtain final independent contract and implementation review in docs/release-readiness.md
- [x] T046 [US5] Establish per-language source-coverage thresholds and a fail-closed gate shared by CI and local pre-commit in scripts/check_coverage.py, .github/workflows/coverage.yml, .pre-commit-config.yaml, and docs/coverage.md

---

## Requirement Traceability

Every functional requirement and success criterion in spec.md has planned task coverage. M0 tasks are closed; implementation and conformance tasks remain open until performed.

| Requirement | Task coverage |
|---|---|
| FR-001: offline request and JSONL protocol | T005, T015, T020–T021 |
| FR-002: decision states and protocol-error separation | T005, T015, T019–T020 |
| FR-003: fail/missing precedence and malformed input handling | T008, T019, T025, T031, T035 |
| FR-004: closed, domain-neutral result envelope | T005–T006, T019 |
| FR-005: canonical identity and digest recomputation | T007, T016, T018 |
| FR-006: exact decimal and collection-order rules | T007, T016, T018, T024 |
| FR-007: typed pack contract, schemas, registration, and fail-closed dispatch | T005–T006, T014, T019, T021, T033–T037 |
| FR-008: Isoprax compatibility and locally recomputed calibration | T008, T023–T025, T027, T029 |
| FR-009: Isoprax identity, verification, and snapshot-bound use | T008–T009, T026, T029, T042 |
| FR-010: measurement subjects, policy, and coverage eligibility | T008–T009, T030–T032 |
| FR-011: Ducky-style eligibility and evidence limits | T034–T037 |
| FR-012: independent evaluators and downstream-pack fixture limits | T014–T022, T027, T032, T037, T045 |
| FR-013: normative fixtures and conformance coverage | T009, T015–T016, T022, T029, T032, T037–T042 |
| FR-014: release, licensing, provenance, and review evidence | T012–T013, T038–T045 |
| FR-015: offline determinism and execution boundaries | T010, T017, T020–T021, T032, T035, T041–T042 |
| FR-016: maintained source-coverage thresholds and gates | T046 |
| SC-001: M0 contract closure | T005–T011 |
| SC-002: independent evaluator agreement | T015–T032 |
| SC-003: downstream pack acceptance | T033–T037 |
| SC-004: generated-case coverage | T038–T039 |
| SC-005: discrepancy, mutation, and parser limits | T039–T042 |
| SC-006: release-readiness evidence | T043–T045 |
| SC-007: enforced Python and Haskell source coverage | T046 |

---

## Dependencies and Execution Order

- T001–T004 record setup and historical mapping; they do not constitute Semadmit implementation evidence.
- T005–T011 closed M0 and were prerequisites for implementation.
- T012–T014 depend on M0 approval.
- T015–T022 implement M1 after runtime setup.
- T023–T029 depend on M1 and a clean Isoprax baseline.
- T030–T032 depend on M1 and can proceed in parallel with Isoprax work in separate pack files.
- T033–T034 define the pack-author guide and Ducky-specific contract after M0; T035–T037 require the stable M1 public API and can proceed alongside built-in pack work.
- T038–T045 depend on the first-party packs and the downstream pack proof.
- T046 establishes the ongoing reference-toolchain coverage gate independently of the unfinished pack and release tasks.

## Parallel Opportunities

After M0 and M1, Isoprax and measurement pack work use separate directories and may proceed in parallel. The Ducky-style contract can be drafted after M0; its implementation can proceed in a separate package once the public Python API is stable. Within conformance, generator, mutation, and parser work uses separate paths.

## Implementation Strategy

### MVP First (User Story 1 Only)

Complete M0 and runtime setup, then implement the reusable core vertical slice with one first-party request. Stop and validate the public API, JSONL contract, generic bindings, and cross-implementation agreement before implementing full domain packs.

### Incremental Delivery

Add the full Isoprax pack, then measurement eligibility, then the Ducky-style downstream pack proof. Finish with conformance and release readiness. Each pack uses the same registered interface; no pack may add domain-specific branches to generic Core.

Do not claim open-source availability before redistribution review and a reviewable package candidate exist.
