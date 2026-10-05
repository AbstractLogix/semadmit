# Quickstart and Validation Guide

**Status**: M0 is approved. The generic Python API and Haskell Core evaluator produce decisions for explicitly registered packs. Shared positive and negative vectors pass through both evaluators. The Haskell CLI registers the maintained Isoprax pack and passes its pool fixtures. Later pack, guarded-use, conformance, and release work remains open.

## Current Local Checks

From the repository root, run these checks for the current slice:

```sh
python3 scripts/check_coverage.py
uv build --out-dir /tmp/semadmit-build clients/python
```

The coverage gate runs all Python tests and declared Haskell suites, including shared evaluator vectors and Isoprax CLI fixture checks. It does not establish guarded-use or release conformance. See `docs/release-readiness.md` and the package manifests for exact toolchain and dependency pins.

## M0 Contract Review

1. Read `spec.md`, `data-model.md`, `contracts/pack-interface.md`, `contracts/wire-protocol.md`, `contracts/decision-tables.md`, and `contracts/threat-model.md`.
2. Read `contracts/isoprax-mapping.md`. Treat its implementations and reported checks as a candidate domain baseline only. They do not establish the shared envelope, Python pack interface, immutable snapshot consumer, or measurement pack.
3. Confirm that the Core, built-in pack schemas/tables, and Python registration interface resolve every open M0 decision. Check that the neutral extension fixture uses the frozen generic API and does not import Ducky rules.
4. For Core and built-in pack obligations/validators, inspect positive, negative, missing, malformed, and boundary fixtures. Inspect the neutral extension fixture for registration, generic bindings, result ordering, and verification.
5. Independently recompute canonical bytes and digests from expected fixture values. Include the regenerated generic decision vector and the reference-based valid evidence-permutation pair. Add and inspect a failing evidence-permutation pair. Both input orders must produce identical decision fields and normalized diagnostic pointers.
6. Record the reviewer, contract revision, resolved findings, and remaining blockers. Do not start implementation while an M0 blocker remains.

## M1 Shared Core Acceptance

The shared vertical-slice vectors show positive and negative offline requests through both evaluators. They compare complete decisions, including request and decision digests, bindings, obligations, and diagnostics. The Haskell CLI checks Isoprax decisions and exit codes through the first-party executable. Explicit CLI cases for duplicate keys and forged digests remain open.

## M2–M3 First-Party Packs

- **M2 Isoprax**: Show that the guarded pooling path uses the verified snapshot. Cover the mapped baseline and intentional contract differences with normative fixtures.
- **M3 measurement**: Show positive, mismatch, missing-coverage, malformed, policy-mismatch, and substituted-subject cases. Confirm that Semadmit returns eligibility only. It must not receive or aggregate measurement values.

## M4 Downstream Pack Adoption

Define the Ducky pack against its actual sideboard-evidence gate. The gate uses fresh observed coverage, a qualifying target, observed sideboard cards, local format legality, exact color compatibility, and Oracle-text-backed role evidence. It also uses source URLs, coverage kind, recency/window metadata, and explicit limitations. Bind one exact deck revision and selected target/meta snapshot. Evaluate freshness against explicit request/policy time or window values, never wall clock. Then use the public Python API to show admissible, inadmissible, indeterminate, and input-error outcomes. M4 passes only if the pack needs no generic Core/result changes and copies none of Core's identity, binding, state-reduction, or verification logic. Record Ducky's remaining responsibilities and any friction or workaround. This assesses one extension path. It does not show broader demand.

## M5 Conformance and M6 Release Candidate

The future guide must provide exact, repeatable commands for generated and property cases, differential comparison, shrinking, selected mutations, parser/resource limits, immutable-snapshot substitution, clean builds, package/license inventory, and the release-readiness report. Report only gates that ran. Apache-2.0 is selected. Complete redistribution review is required before a release candidate can claim readiness. Publication remains a separate decision.
