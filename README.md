# Semadmit

Semadmit is in design and implementation. It aims to provide a reusable, offline core for decisions based on declared evidence.

The approved design binds exact inputs and policy. It defines each obligation as pass, fail, or missing. It requires local decision verification. A consumer must use the same immutable snapshot that was checked.

The design defines shared request identity, decision verification, and evidence-state handling. It does not cover evidence collection or judge whether a domain rule is meaningful.

The project aims to provide an open-source implementation and a typed interface for Python-hosted domain packs. Its language-neutral JSONL protocol serves callers of packs that a host has registered. It does not load packs across languages. The Haskell reference CLI is scoped to maintained first-party packs. A Python host can register a pack and call the API or JSONL runner.

Isoprax is the founding domain. A small measurement domain checks that the core also works outside Isoprax. A separately authored MTG Ducky sideboard-evidence pack is planned as an adoption test. Ducky will keep its data, evidence collection, and guide generation. Semadmit will decide only whether the supplied evidence meets the pack's eligibility rules.

This repository contains the independently reviewed M0 contract and initial M1 Core modules. The Python API and Haskell Core evaluator can evaluate explicitly registered packs. Shared positive and negative vectors pass through both implementations. The Haskell `Core.CLI` runner has fixture-backed request, JSONL, output, and exit-code checks. The executable registers the Isoprax pack and passes its decision fixtures. Feature 002 adds a Python finite-domain claim pack with separate verification and admission statuses. The Measurement pack, guarded consumption, full conformance, and release remain open.

Semadmit uses the [Apache-2.0 license](LICENSE). The license and the pinned Isoprax baseline provenance are recorded in [release readiness](docs/release-readiness.md).

Start with the [current claim-verification feature](specs/002-structured-claim-admission/spec.md), then read the [v0.1 Core specification](specs/001-semantic-oracle-v0-1/spec.md), [implementation plan](specs/001-semantic-oracle-v0-1/plan.md), and [task list](specs/001-semantic-oracle-v0-1/tasks.md).
