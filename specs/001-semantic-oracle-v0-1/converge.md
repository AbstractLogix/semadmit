# Convergence Record: Semadmit Reusable Core v0.1

**Status**: M0 written contract and fixtures approved on 2026-09-30; implementation gates remain open

Initial Core identity, strict Python parsing/registry modules, and Haskell strict byte parsing/common-envelope validation are present with focused checks. T014 now includes the Haskell pack descriptor and exact-ID registry plus public Python registration exports; T017 adds strict JSON/profile checks and exact common dispatch. Both implementations evaluate registered packs and assemble digest-bound decisions. T022 checks shared positive and negative vectors, including digests, bindings, obligations, and diagnostics. The injectable Haskell `Core.CLI` runner checks single-request output, JSONL framing and recovery, and exit codes. T020 now wires `app/Main.hs` to the available first-party Isoprax pack and checks its full fixture output and status through the application runner. The Measurement pack, guarded consumption, and release remain open. The Isoprax mapping records a historical source snapshot at implementation commit `ff0b2797f43a12373eb07ab39eefbb8e91186051`, inspected at `c212c3485562c710ddcf77128dc6f92b9d2c6f29`. Isoprax's convergence record reported hosted validation for the implementation commit. This is baseline evidence only, not Semadmit protocol, reusable-pack, measurement-pack, or downstream-pack implementation conformance. M0 approved the Semadmit field shapes, numeric representation, normalization, identity projections, diagnostic pointers, measurement rules, generic bindings, typed pack interface, and fixture corpus after independent review on 2026-09-30.

## Scope Change — 2026-09-30

The product goal was clarified as an open-source reusable decision core for use beyond Isoprax. The spec now makes generic Core and its typed pack interface the product, uses the measurement pack as a second first-party domain, and adds an MTG Ducky-style sideboard-evidence pack as a downstream adoption proof. The revised public interface received independent M0 review; this scope change does not establish Ducky integration or implementation.

## Next Gate

T020 is complete: `app/Main.hs` registers the available first-party Isoprax pack and uses the tested `Core.CLI` runner. The pool suite checks every Isoprax fixture's request, full output, and exit code through the application runner. T022 is complete: shared neutral-pack vectors verify positive and negative full decisions through the Haskell and Python evaluators. T023 and T024 are complete: Isoprax subject and component identities match their normative sidecars, and exact calibration matches every M0 ECE trace and legacy binary64 vector. T025 is complete: the Haskell `pool_predictions` operation evaluates direct definition compatibility, calibration obligations, and stable diagnostics against every Isoprax decision fixture. T026–T029 remain open for snapshot-bound admission and independent Python Isoprax conformance. The Measurement pack and Ducky-specific acceptance rules also remain open.

The initial independent review, later implementer audit, and current adversarial recheck are recorded separately in contracts/review.md. The current recheck covers the revised generic bindings, public pack API, host registration/versioning, built-in contracts, neutral extension fixture, vectors, and threat model. Ducky-specific adoption proof remains an M4 gate; no implementation or downstream use is inferred from M0 approval.

## Later Evidence Required

- M2 verified Isoprax bindings consumed from one immutable snapshot, with the mapped baseline and any intentional contract differences covered by normative fixtures.
- M3 measurement fixtures covering all required states and validation classes.
- M4 a separately packaged Ducky-style Python pack against the actual sideboard-evidence gate, with an adoption stop/go report; no Core edits or copied Core logic.
- M5 generated/property/differential/mutation/parser and substitution results with no unexplained mismatch.
- M6 pinned builds, dependency/license inventory, provenance, independent review, discrepancy log, and release-readiness report.
