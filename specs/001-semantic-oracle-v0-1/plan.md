# Implementation Plan: Semadmit Reusable Core v0.1

**Branch**: main (feature branch not created) | **Date**: 2026-09-30 | **Spec**: spec.md

**Input**: Feature specification from specs/001-semantic-oracle-v0-1/spec.md

## Summary

Build Semadmit as an open-source, offline core. Provide a stable, typed Python interface for pack authors. Core handles strict envelope parsing, canonical identities, generic artifact bindings, deterministic results and errors, local reevaluation, and admission from the same snapshot.

Explicitly registered, versioned packs define domain semantics. Isoprax is the founding pack. The measurement pack proves a second first-party domain. A separately packaged MTG Ducky example tests whether a Python adopter can add its sideboard-evidence rules without copying or changing Core.

Maintain independent Haskell and Python implementations of the shared core and first-party packs. The public JSONL protocol is language-neutral. It serves callers of packs that a host has registered. It does not let non-Python callers load or register pack code. The Python API is the v0.1 interface for in-process pack authoring and use. A downstream pack is trusted application code that its host registers. A request never loads code. This plan does not add a hosted service, dynamic plugin ABI, or caller-supplied rule language.

The checkout has partial Core evaluators, package manifests, and an Apache-2.0 license. A shared positive/negative registered-pack slice passes through both implementations. The injected Haskell `Core.CLI` runner has fixture-backed protocol tests; the maintained-pack executable, first-party packs, complete domain evaluation, and release remain open. M0 approved the normative contract and fixture corpus on 2026-09-30. Implementation conformance remains an M1–M5 gate. Dependency redistribution and package review remain open before release.

## Technical Context

**Language/Version**: Haskell reference evaluator and CLI for maintained first-party packs; Python package/API, JSONL runner, and independent evaluator. Pin supported toolchains after M0.

**Primary Dependencies**: RFC 8785 JCS implementation(s), SHA-256, exact-rational arithmetic, JSON parsers with duplicate-key rejection, and the package tooling selected for the Python API. Reuse/copy decisions for Isoprax code require source, provenance, and license review.

**Storage**: None in Core. Consumer adapters supply exact immutable content-addressed snapshots or keep one atomic read/verify/use transaction.

**Testing**: Normative fixtures, focused unit and contract checks, property generators, differential runner, shrinking, selected mutation checks, parser/resource-boundary cases, and a separately packaged downstream pack example. This specification-only change does not add or run implementation tests.

**Target Platform**: Local/offline CI and application use. Supported OS/toolchain matrix remains to be pinned.

**Project Type**: Reusable offline library/API, reference CLI, typed domain packs, and conformance toolkit.

**Performance Goals**: No throughput SLA is stated. Enforce the M0 limits: 10 MiB per JSONL request, 10 MiB per direct-object request or candidate decision, depth 64, 256 evidence records, and 100,000 Isoprax prediction rows per subject.

**Constraints**: Decisions are pure functions of normalized request and exact pack version; network, ambient environment, working-directory files, wall clock, random sources, and mutable process history cannot affect them. Reject duplicate JSON object keys before ordinary object parsing loses them. Register only trusted pack code. No server, dynamic plugin ABI, runtime policy expressions, signing, or production Isoprax behavior in v0.1.

**Scale/Scope**: One offline request and bounded JSONL stream; shared core; two first-party packs; a separately packaged Ducky-style pack example; no multi-tenant hosting.

## Constitution Check

| Principle | Plan assessment |
|---|---|
| Evidence boundaries | Pass. Decisions cover supplied inputs and tested cases only; they do not prove truth, efficacy, or consumer enforcement. |
| Deterministic, reusable contracts | Contract pass. M0 approved the generic envelopes and public pack interface; running implementation evidence remains open. |
| Independent conformance evidence | Pass as a requirement for Core and maintained packs. An external pack does not claim two-implementation parity unless that check exists. |
| Fail-closed, snapshot-bound admission | Pass as a requirement for every pack that exposes guarded consumer use. |
| Open-source reusable offline core | Conditional pass. Apache-2.0 is selected; the complete Python API, language-neutral CLI, downstream pack proof, and redistribution review remain gates. |

**Implementation gate**: M0 passed on 2026-09-30, and T012–T013 recorded toolchains, direct dependencies, and the Isoprax source-integration boundary. M1 is in progress. T043 remains a redistribution and package review gate before release.

## Delivery Phases

### Phase 0 — M0 shared contract and pack interface

Freeze the generic request/result/error envelopes; registered-pack dispatch; role/schema/cardinality declarations; generic subject, component, and evidence bindings; complete per-operation obligation sets and component-output cardinalities; request identity preimage/array semantics; pack versioning and identity rules; Python pack API and validation boundary; JSONL behavior; built-in pack obligations/diagnostics; parser limits; threat model; and fixtures for the built-in packs plus a neutral extension pack. Independently review this scope. Ducky-specific fields and decision rules are reserved for M4, after the API is frozen. This phase changes documentation and fixtures only.

### Phase 1 — M1 reusable core vertical slice

Pin Haskell/Python toolchains and dependencies. Implement the generic parser, identity, result and error behavior, pack registry, Python public API and JSONL runner, and one reviewed first-party Isoprax request through both evaluators. The Haskell reference CLI registers built-in packs only; a Python host supplies its registered pack set to `JsonlRunner`. Prove that generic Core does not import Isoprax types.

### Phase 2 — M2 Isoprax founding pack

Adapt the mapped Isoprax semantics behind the public pack interface. Implement direct definition compatibility, exact calibration, pack-specific component bindings, immutable snapshot retention, and a guarded CI consumer. Record differences from the historical baseline without hidden tolerances.

### Phase 3 — M3 measurement pack

Implement the narrow identical-window eligibility pack independently of Isoprax concepts. It binds matching identifiers and supplied positive coverage to each exact subject and returns no values or aggregate.

### Phase 4 — M4 downstream pack adoption proof

Build a separately packaged Python example based on MTG Ducky's actual sideboard-evidence eligibility contract: fresh observed coverage, a qualifying target, observed sideboard cards, local format legality, exact color compatibility, Oracle-text-backed role evidence, source URLs, coverage kind, recency/window metadata, and explicit limitations. Bind an exact deck revision and selected meta snapshot; evaluate freshness only against explicit request/policy time or window values. The pack returns eligibility only; Ducky retains the attributed snapshot and generates the guide. Do not retrieve Ducky data or modify the Ducky repository. M4 passes only if the pack uses the public API without generic Core/result changes or copies of Core identity, binding, state-reduction, or verification logic. Record remaining Ducky responsibilities and interface friction. This is a stop/go test of one extension path, not broader market-demand evidence.

### Phase 5 — M5 conformance

Add normative fixtures, per-first-party-pack generators, properties, shrinking, differential reproduction, selected mutations, parser/resource tests, and consumer substitution cases. Add pack-author conformance checks and resolve every disagreement through a contract change or documented correction.

### Phase 6 — M6 open-source release candidate

Record clean build/package/test commands, pinned versions, approved license, dependency inventory, provenance, minimized discrepancies, independent review, pack-author documentation, and limitations. Assess a release candidate only; publishing remains a separate decision.

## Dependency Order

M1 depends on approved M0 and recorded T012–T013 setup, which are complete. M2 and M3 depend on M1 and may proceed independently after the shared interface is stable. M4's Ducky-specific contract and fixtures can proceed after M0; its separately packaged implementation depends on M1's public Python API and can proceed alongside M2/M3. M5 depends on M2, M3, and M4. M6 depends on M5 and redistribution review.

## Project Structure

Planned implementation layout under the approved M0 contract:

    app/                              Haskell CLI entry point
    src/Core/                         protocol, identity, registry, verifier, results
    src/Pack/Isoprax/                 prediction-pooling rules
    src/Pack/Measurement/             measurement-eligibility rules
    clients/python/semadmit/          public Python API and independent evaluator
    clients/python/semadmit/jsonl.py  JSONL runner over an explicitly registered Python evaluator
    examples/mtg_ducky_pack/          separately packaged downstream pack example
    conformance/schema/               shared protocol and pack schemas
    conformance/fixtures/             canonical inputs, bytes, digests, and outcomes
    conformance/generators/           seeded first-party case generation and shrinking
    docs/                             pack-author guide, usage, threat model, release evidence
    test/                             Haskell, Python, property, and integration checks

The package names and initial toolchain versions are pinned for M1; parser strategy, executable distribution, and the complete host registration behavior remain implementation work. Apache-2.0 is selected; T043 checks redistribution details. The host composition boundary is fixed: Haskell CLI for maintained first-party packs; Python `JsonlRunner` for the explicit registry supplied by its host. A pack author must use Core's public identity and result facilities; packs supply only typed domain validation and evaluation behavior. No runtime code loader is introduced.

## Complexity Tracking

The downstream pack example is required by the product goal, not speculative generality. Scope stays bounded by keeping pack code trusted and linked by the host, keeping caller policies as closed data, and excluding hosted multi-tenant operation. Generic binding records are required so new packs do not add Isoprax-specific fields to Core.
