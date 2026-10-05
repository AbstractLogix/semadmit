# Specification Index

## 001 — Semadmit Reusable Core v0.1

This feature has five user stories. M0 approved the contract and fixtures. M1 builds the shared offline core. M2 and M3 add the Isoprax and measurement packs. M4 evaluates a downstream MTG Ducky-style pack. M5 checks conformance. M6 prepares a release candidate.

M0 defines extension behavior with a neutral fixture. M4 defines the exact Ducky evidence contract against the approved interface. The example does not change Ducky's application or data sources. It checks the Python-hosted extension path, not pack loading across languages.

The project has an approved M0 contract and fixtures, partial M1 Core evaluators, and shared positive/negative registered-pack vectors. The feature's fixture guide and review record document independent canonicalization checks and adversarial contract review. The injectable Haskell `Core.CLI` runner has neutral-pack tests; its maintained-pack executable, maintained first-party packs, complete domain evaluation, and release remain open.

See the [feature specification](001-semantic-oracle-v0-1/spec.md), [plan](001-semantic-oracle-v0-1/plan.md), and [task list](001-semantic-oracle-v0-1/tasks.md).

## 002 — Structured Claim Verification v0.1

This feature adds a finite-domain claim verifier through the Python pack API. It preserves separate verification and admission statuses and keeps the approved Core v0.1 envelope unchanged. It uses the existing Isoprax pooling rule as its commensurability example.

See the [feature specification](002-structured-claim-admission/spec.md), [plan](002-structured-claim-admission/plan.md), [task list](002-structured-claim-admission/tasks.md), and [quickstart](002-structured-claim-admission/quickstart.md).
