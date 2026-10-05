# Research: Semadmit Reusable Core v0.1

**Status**: M0 contract and fixtures approved on 2026-09-30. The product goal is a reusable open-source core with typed domain packs. Runtime implementation and first-party conformance remain open; the Ducky-specific downstream proof is scheduled for M4 against the approved public interface.

## Product Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Reusable offline Core with versioned typed packs | Preserves the mechanism found in Isoprax while letting other applications add domain semantics without copying identity, verification, or result handling. | An Isoprax-only oracle or a generic domain-rule language would either narrow reuse or make semantics opaque. |
| Pack code is trusted and registered by the host | The evaluator can safely remain offline and deterministic while supporting application-owned semantics. | Loading executable code or policy from a request is unsafe and out of scope. |
| Python-hosted pack API plus language-neutral JSONL protocol | Gives Python applications such as MTG Ducky an in-process extension path. JSONL supports callers of already-registered packs but is not a cross-language pack-loading ABI. | A Haskell-only library would force the Python adopter to duplicate or wrap more behavior; a foreign-language plugin ABI or server is not required for v0.1. |
| Haskell reference plus independent Python implementation for Core and maintained packs | Provides a differential check of the shared contract and first-party semantics. | Sharing one evaluator implementation would weaken that evidence. A downstream pack can start in one language and must not claim two-implementation parity without a second evaluator. |
| The Ducky example is an M4 extension-path assessment, not an M0 prerequisite or market-demand proof | It will model Ducky's actual sideboard-evidence gate after the generic interface is frozen, and it must show reuse without Core edits/copying. | Pulling Ducky-specific freshness, provenance, and card rules into M0 would couple the Core gate to one adopter; a toy example would not test the stated use case. |
| RFC 8785 JCS and SHA-256 identities | Defines canonical bytes and binds identity to artifact kind, schema, and payload across languages. | Sorted-key JSON alone is insufficient. |
| Canonical decimal strings with exact rational calculations where required | Avoids cross-language floating-point drift in score and calibration rules. | Tolerance-based equality and silent rounding are prohibited. |
| Snapshot-bound verification and use | Prevents a caller from changing data after checking and before consuming it. | Re-reading mutable arrays or paths after verification is unsafe for the contract. |
| No signing or authenticity claims | v0.1 hashes content but does not authenticate its issuer. | Calling an unsigned record an attestation is out of scope. |

## M0 Decisions Approved by Independent Review

The decisions below are normative for v0.1 following the independent recheck recorded in contracts/review.md. They authorize implementation within the frozen behavior and versioning rules.

- The common request envelope is closed. The host resolves the exact namespaced pack/version ID through an explicit trusted registry; pack-specific policy, subject-role, evidence, component, and operation schemas remain closed under the selected pack.
- Subject roles and cardinality belong to the pack. The current Isoprax and measurement packs use left/right; this pair is not a Core rule.
- The shared result contains generic subject, component, and evidence bindings with kind/schema/digest references. Isoprax definition and sample hashes appear as generic components rather than special Core fields.
- Core owns envelope parsing, JCS identity framing, complete obligation/component-output validation, generic state reduction, result/error ordering, local artifact reevaluation, and opaque snapshot creation. Pack code owns only typed domain validation and evaluation.
- The in-process extension API is Python for v0.1; JSONL is language-neutral for calling registered packs, not registering foreign-language pack code. Haskell and Python independently implement maintained Core/first-party semantics. Downstream Python packs provide fixtures and use the common harness.
- M0 reviews a neutral extension-pack fixture that exercises registration, generic artifacts, result ordering, error mapping, and verification. Ducky's exact domain requirements and evidence fields are set at M4 against the frozen Python interface.
- Pack modules are trusted code registered by the host. Requests cannot load code or expressions. No server, dynamic plugin ABI, or generic runtime rule language is introduced.
- Isoprax uses exactly left/right subjects, an explicit null for absent samples, ordered score/outcome arrays, and an empty caller-evidence array. Its policy has bounded min_events, n_bins, and max_ece plus explicit definition-comparison and numeric-profile IDs; the digest covers all five fields.
- Definition compatibility follows the completed Haskell kernel's direct rule: normalized semantic comparison keys must match, but declared IDs need not. Both IDs and full definition identities remain separately bound. Both outcome classes and nonzero score variance are fixed pack rules, alongside minimum-event and exact ECE checks.
- All non-integer quantities in the Isoprax request use bounded canonical decimal strings; threshold values use an explicit text/decimal tagged form. Legacy numeric adapter inputs use the RFC 8785 number spelling, exponent expansion, and exact rational parsing; inputs outside the profile are rejected without rounding. ASCII-only normalization avoids cross-runtime Unicode-version drift.
- Evidence is a set sorted by stable ID for identity and evaluation. Sample rows preserve order. Result diagnostics use pointers into the normalized request so evidence permutation cannot change semantic diagnostics.
- Measurement is a two-subject eligibility decision over exact metadata identifiers, an identical half-open POSIX-millisecond window, and one coverage record per role bound to subject and policy digests. It returns no measurement values or aggregate; zero coverage is a domain failure, and negative count is malformed input.
- Shared request limits are 10 MiB per line excluding LF, depth 64, and 256 evidence records. Packs declare additional bounded domain limits; Isoprax allows at most 100,000 prediction rows per subject.

## M0 Review Disposition

The independent recheck approved the shared Core contract, public Python pack interface, built-in pack tables, neutral extension fixture, vectors, limits, and threat model on 2026-09-30. The earlier blocker list was resolved and superseded by the current disposition in contracts/review.md. No M0 blocker remains; M1 implementation is authorized against the frozen contract. Ducky-specific rules are an M4 gate.

## Runtime Setup and Conformance Gates After M0

- Toolchain pins, direct dependencies, and the independent Isoprax implementation boundary are recorded in docs/release-readiness.md, cabal.project, semantic-oracle.cabal, and clients/python/pyproject.toml. Setup builds and focused identity/parser/registry checks are recorded there.
- Apache-2.0 was selected by the owner on 2026-09-30 and applied in `LICENSE` and package metadata. Before release, complete the direct and transitive dependency redistribution and notice inventory in `docs/release-readiness.md`.
- Define a pack-author guide, registration example, and shared fixture harness. At M4, verify the full Ducky sideboard-evidence example as a separate package against the public Python API and record the extension-path stop/go result.
- Define at least 10,000 generated valid/invalid cases per maintained first-party pack, classified by obligation, state, and boundary. This is a conformance-run gate, not a documentation-only completion claim.

## Repository Evidence and Limits

The completed Haskell reference kernel was inspected read-only from `origin/codex/042-haskell-semantics-kernel` at `223187c319d6b50fb05cc2d55ffc5b465556a660`. The later Isoprax history refactored it to Python in `c5a11f1`; the current Isoprax checkout also retains the separate older 044 fixture oracle. Semadmit uses the 042 source as a candidate semantic baseline, not as proof that Semadmit implements the broader core or pack API. No Isoprax files were modified.

Isoprax's convergence record at the time of inspection reported hosted validation for ff0b279 (pinned Haskell build, QuickCheck, compile-fail API checks, and five Python/Haskell fixtures). This is existing repository evidence, not an independent Semadmit run or proof that the v0.1 contract is implemented. Semadmit implements the reviewed behavior independently; release still requires transitive dependency notice review and final package evidence.

## Threat Model Boundaries

The evaluator accepts caller-supplied data that may be malformed, contradictory, substituted, or fabricated. It rejects malformed/unsupported inputs, binds exact content and policy, and preserves failure/missing distinctions. Registered pack modules are trusted installed code; they are not loaded from request data and must obey the offline determinism boundary. The core cannot establish issuer identity, real-world truth, source authenticity, actual evidence freshness beyond supplied metadata and an explicit bound time/window, authorization, or downstream enforcement. Denial-of-service controls are request and collection limits; operational hardening beyond these local limits is not claimed.
