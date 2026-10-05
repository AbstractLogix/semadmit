# Threat Model — v0.1

## Protected Property

The evaluator must not admit a request whose validated, content-bound inputs fail the reviewed domain contract. A consumer must use the same immutable values that were verified.

The trust roots are the host's Core implementation, its explicitly constructed registry, the selected installed pack implementation and descriptor, and the local verifier. Request data, a received decision artifact, and external files or database rows are outside that trust boundary. A pack is trusted application code with host-process privileges; registration is a host decision, not an authentication check performed by Semadmit.

## Inputs Treated as Untrusted

Requests, policies, definitions, samples, evidence, supplied digests, caller-owned arrays, files, and any report presented for verification may be malformed, contradictory, substituted, stale, or fabricated. Human-readable messages are not normative.

## Threats and Required Controls

| Threat | Required control | Limit |
|---|---|---|
| Duplicate keys or parser ambiguity | Reject duplicate JSON keys before ordinary object decoding; close schemas and number profile. | Does not make an upstream data producer trustworthy. |
| Same label hides changed semantics | Include both declared ID and validated content in identity; compare compatibility explicitly. | A definition may still misdescribe reality. |
| Caller forges a digest or pass assertion | Recompute all digests and calibration from bound data; never trust a passes flag. | Hashes do not authenticate the issuer. |
| Missing evidence masks a known failure | Evaluate independent obligations; failure takes precedence over missing. | The obligation model still needs independent review. |
| Pack omits an obligation or required component | Check the descriptor's exact obligation set and per-role component cardinalities before deriving state or bindings; emit only `internal.failure` for invalid pack output. | A consistently wrong but structurally complete trusted pack still requires independent domain review. |
| Request, evidence order, or pack version is substituted | Bind exact protocol, pack/version, operation, verified policy digest, normalized subjects, and ID-sorted evidence in request identity; reject unknown versions and duplicate evidence IDs. | Content identity does not authenticate who supplied the request. |
| Verification/use race | Copy and validate inputs once; retain immutable snapshot; guarded use consumes that snapshot or rejects. | A caller can bypass the guarded API. |
| File or database contents change after verification | Use an immutable content-addressed snapshot or one atomic read/verify/use transaction; do not reopen a mutable path by name after admission. | External stores must provide the promised snapshot or transaction semantics. |
| Request selects untrusted pack code | The host resolves requests only against explicitly registered trusted pack implementations; request data cannot import code or expressions. | Registered pack code is trusted application code and is not sandboxed from its host. |
| Pack result varies with hidden host state | Require Core and registered packs to be pure functions of normalized request and exact pack version; forbid random sources, mutable process history, network, environment, files, and wall clock. Verify repeated and reordered evaluations against pack fixtures. | The contract is not a runtime isolation or sandbox guarantee. |
| Cross-language canonicalization drift | Use JCS, a bounded decimal-string profile, explicit ASCII-only Isoprax key normalization, and normative byte/digest vectors. | Shared specification or fixture errors can affect both implementations. |
| Resource exhaustion | Bound request and candidate-decision size and nesting during direct-object copy or byte parsing; bound evidence count and prediction pairs. | No general availability or hostile-network guarantee is made. |
| Unsigned decision is forged, replayed, or edited | Treat every candidate decision as untrusted; the local verifier revalidates the exact request, reevaluates the same registered pack/version, and compares every normative field and decision digest before constructing Admission. | Authenticity, issuer identity, freshness, authorization, and downstream enforcement are out of scope. |

## Input and Identity Boundaries

All request bytes and nested records are untrusted. The parser rejects invalid UTF-8, unpaired surrogate escapes, duplicate keys, unsupported number spellings, out-of-range integers, unknown fields, and limit violations before domain evaluation. Content hashes identify normalized validated records; they do not prove who supplied them. Isoprax comparison normalizes only ASCII whitespace and ASCII A-Z, while measurement identifiers remain exact Unicode scalar sequences. These rules avoid runtime Unicode-version dependence in the decision path. A pack's declared schemas, roles, and rules are versioned, but a new pack does not add fields or executable policies to generic Core.

The Python object API copies caller-owned request and candidate-result trees with independent size and depth budgets before validation; the CLI and JSONL paths parse bounded bytes into the same internal form. The direct object path cannot recover duplicate JSON keys or numeric token spelling from an already constructed dict, so callers needing byte-level rejection must use the byte-framed path. Core verifies supplied digests only after the corresponding validated identity projections are available. A well-formed but contradictory measurement coverage binding is a failed obligation, while a malformed digest is an input error. No error or non-admissible state yields Admission.

## Verification and Consumption Boundary

An unsigned artifact may be stored or transmitted, but its digest only detects changes to its canonical content. Verification requires the exact request snapshot and the registered pack/version that defines its meaning. A self-consistent forged `state=admissible` payload, matching forged digest, or report from another pack/version does not create Admission. If the pack is unavailable, reevaluation fails, any normative field differs, or the request snapshot cannot be retained immutably, the verifier produces no Admission. An admissible decision gives no authority to a consumer that bypasses the guarded operation.

For caller-owned arrays, Core retains its own immutable validated copy. For file or database consumers, the consumer must prove that the bytes used after verification are the same content-addressed snapshot, or perform reading, verification, and use in one atomic transaction. Reopening a mutable path or requerying a mutable row after verification is outside the guarded contract. Packs without a guarded consumer return eligibility only and make no claim that downstream use occurred.

## Evidence and Review Limits

M0 fixtures cover parser rejection, digest and evidence substitution, all three decision states, evidence-order normalization, incomplete pack output, and canonical identities. They establish expected contract examples, not implementation resistance. T011 independently reviewed this threat model and contract; M1 and M5 must later exercise the parser, verifier, and mutable-input substitution paths in running implementations. A trusted pack can still be buggy or read hidden host state, and a fabricated but well-formed observation can still satisfy its declared rules. Neither case is prevented by SHA-256 or by a passing fixture.

## Explicitly Out of Scope

Network attacker defense, credentials, issuer identity, signatures, revocation, expiry, authorization, ontology inference, automatic unit conversion, observation truth, and scientific efficacy are not v0.1 claims.
