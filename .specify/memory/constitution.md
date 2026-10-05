# Semadmit Constitution

## Core Principles

### I. Evidence boundaries

A decision states only whether supplied evidence satisfies a versioned domain contract. It does not establish that observations are truthful, that a definition describes reality, or that a consumer enforced the decision. Conformance evidence is limited to tested cases. Documentation and output MUST preserve these limits.

### II. Deterministic, reusable contracts

Every supported core request, result, obligation, diagnostic, and error shape MUST be explicit and versioned. Domain-specific fields and rules MUST live in typed, versioned packs behind the public pack interface. A pack MUST declare its closed input schemas and deterministic semantics. Unknown fields, malformed values, unregistered packs, unsupported versions, and unrecognized policies MUST fail as input or protocol errors; they MUST NOT be converted into missing evidence or admission.

### III. Independent conformance evidence

The maintained Haskell reference and Python implementation MUST independently implement the shared core contract and maintained first-party packs. Normative fixtures and canonicalization vectors define expected behavior. A downstream pack MUST provide fixtures for its declared contract; it MUST NOT claim independent cross-implementation conformance unless a second independent evaluator has been checked. Agreement is evidence over tested cases, not proof of correctness; independent contract review and targeted mutation checks remain required.

### IV. Fail-closed, snapshot-bound admission

A failed obligation takes precedence over missing evidence; missing evidence without failure yields indeterminate. Inadmissible and indeterminate results MUST NOT construct an admission value. Verification and a guarded consumer operation MUST use the same immutable snapshot and exact policy, subject, component, evidence, and operation bindings declared by the selected pack.

### V. Open-source reusable offline core

Semadmit exists to make evidence-bound claim verification and admission reusable in other projects. The core MUST remain domain-neutral; Isoprax is the founding pack, and additional packs demonstrate reuse. The public typed pack interface and language-neutral request/result protocol MUST allow a downstream project to add a pack without copying core identity, verification, or result logic. Packs are trusted application code explicitly linked or registered by the host. Do not add a server, dynamic plugin ABI, runtime policy language, custom signing, or production Isoprax behavior without a separately reviewed specification.

### VI. Verification and admission are distinct

A claim verification status and an admission status MUST remain separate. `VALID`, `INVALID`, and `UNKNOWN` describe verification. Admission describes whether the result may affect reasoning under a declared policy. A pack-specific result artifact MUST preserve this distinction and bind to the generic Core decision. New result shapes MUST be versioned and MUST NOT silently change an approved Core envelope.

## Additional Constraints

- Use [ASD-STE100 Simplified Technical English, Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) by default in user-facing text and documentation. Prefer short, direct sentences and approved words. Preserve necessary technical terms and exact quotations.
- Use RFC 8785 JSON Canonicalization Scheme for identity; exact decimal strings and rational arithmetic govern domain quantities where required by a pack.
- Keep protocol, identity, verification, and result mechanics separate from Isoprax calibration and measurement rules.
- Preserve provenance and suspected evidence dependencies during normalization. Do not claim source authenticity or statistical independence from caller-supplied metadata.
- Keep shared binding fields domain-neutral. Pack-specific component names and semantics MUST NOT become special cases in Core.
- Haskell remains outside Isoprax production runtime; its adapter is exercised in tests/CI only.
- Resource limits are execution safeguards, not domain policy.
- Release claims require recorded builds, tests, dependencies/licenses, provenance, discrepancies, and remaining limits. A local green check MUST NOT be presented as hosted, production, scientific, or formal-verification evidence.
- Do not claim open-source availability until an owner-approved license and redistribution path are recorded.

## Development Workflow

- Close and independently review M0 schemas, the public pack interface, canonical vectors, decision tables, error vocabulary, and threat model before implementing M1.
- Demonstrate one independently authored downstream pack through the public interface before calling the extension path reusable.
- Preserve the approved contract as fixtures; resolve disagreements through an explicit contract change, not by silently changing one implementation.
- Keep tasks dependency-ordered and changes small. Verify focused implementation checks after code work; do not claim a gate that was not run.
- Publication is a separate decision after release-readiness review and license approval.

## Governance

This constitution is authoritative for all specifications and implementation work in this repository. A change to a principle requires a documented amendment and an impact review against existing specs and fixtures. Feature specs may tighten these rules but may not weaken them without an explicit constitution amendment.

**Version**: 1.3.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-10-05

### Amendment 1.1.0

The product goal now explicitly includes a reusable open-source core and a supported typed pack interface. The impact is to generalize shared binding and dispatch contracts, keep maintained pack rules isolated, and add a downstream pack adoption proof. This does not authorize a server, dynamic plugin ABI, or generic policy language.

### Amendment 1.2.0

Set ASD-STE100 Simplified Technical English, Issue 9, as the default for user-facing text and documentation. This amendment changes writing style. It does not change Core contracts or runtime behavior. Keep required technical terms and exact quotations.

Impact: README and reader guides now use shorter sentences. Templates and document-writing commands carry this rule forward. Approved M0 requirements, contracts, and fixture values are unchanged.

### Amendment 1.3.0

Clarified Semadmit's product role as reusable claim verification and admission. Added the rule that verification and admission statuses remain distinct, and that new pack-specific results bind to the generic Core decision. The existing `semantic-oracle/0.1` envelope remains unchanged. Provenance and suspected dependencies remain data; they do not authenticate sources or establish independence.

Impact: Feature 002 adds an explicitly versioned Python claim pack and result wrapper. It does not alter the approved v0.1 request, decision, or identity contract. Haskell remains the independent reference for the existing shared Core and Isoprax pack; Feature 002 makes no Haskell conformance claim for the new domain rule.
