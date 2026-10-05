# Wire Protocol: semantic-oracle/0.1

**Status**: Normative v0.1 M0 contract and fixtures, approved by independent review on 2026-09-30. Implementation conformance remains unproven.

## Request Envelope

A request line is one UTF-8 JSON object with exactly these fields. Trailing non-whitespace data, a second root value, or a byte-order mark is invalid JSON.

| Field | Type | Rule |
|---|---|---|
| protocol | string | Exactly semantic-oracle/0.1 |
| pack | string | Exact namespaced versioned ID of a pack registered by the host, using the grammar in `contracts/pack-interface.md` |
| operation | string | Exact operation declared by the selected registered pack |
| policy_digest | string | Recomputed SHA-256 identity of the validated policy; lowercase 64-digit hex after sha256: |
| policy | object | Closed pack-specific policy schema |
| subjects | object | Closed pack-specific subject schema |
| evidence | array | Closed pack-specific evidence schema |

Every field is mandatory. Core validates UTF-8/JSON framing, duplicate keys, the shared number profile, request-wide limits, the exact common field set, and common field types before dispatch. The selected pack then validates its closed nested schemas in the deterministic field order declared by its descriptor and applies pack-specific limits. Pack validation errors use only the shared closed error vocabulary and RFC 6901 request pointers. The policy digest is recomputed from the validated normalized policy and checked against the supplied value; it is never caller-authoritative. The implementation does not execute policy expressions. An unregistered pack or unsupported pack version is `protocol.unsupported_pack`.

Byte framing and token-spelling checks apply to CLI and JSONL input. The direct Python API makes bounded copies of JSON-shaped request and candidate-decision trees and applies the same structural, number-value, depth, evidence, pack, identity, and domain rules. It rejects Python floats as `input.number_profile` and non-JSON values as `input.invalid_type`; byte-only errors such as duplicate JSON keys and exponent-form tokens cannot be reconstructed from an already built object. The direct API caps each copied tree's JCS UTF-8 bytes at 10 MiB and nesting depth at 64 during traversal; an over-limit candidate fails verification without Admission. `contracts/pack-interface.md` defines this entry boundary and the immutable snapshot rule.

The `subjects` object has exactly the roles declared by the selected pack and operation. Each role's closed schema, cardinality, ordering, and component artifacts are pack-defined. The Isoprax pack declares `left` and `right` roles with `definition` and `sample`; the measurement pack declares `left` and `right` roles with its identifiers and `window`. These are built-in pack rules, not shared-core assumptions. Every subject and nested component identity is derived from validated content, never trusted from caller-supplied digest fields. Evidence shape and limits are defined by the selected pack.

Each host evaluates only trusted pack modules explicitly present in its registry. The Python API provides downstream pack registration; the Haskell reference CLI registers maintained first-party packs. Request data can select a registered pack but cannot load code. The language-neutral JSONL envelope is an interoperability path to packs already registered by that host; it is not a cross-language pack-loading ABI. See `contracts/pack-interface.md`; there is no runtime rule language or dynamic plugin ABI.

### Isoprax Subject and Sample

An Isoprax subject contains exactly `definition` and `sample`. The `definition` object accepts exactly `id`, `event`, `observation_process`, `window`, `thresholds`, and `description`. `id`, `event`, `observation_process`, and `window` are required. `thresholds` defaults to an empty array; `description` is optional text or null and is display metadata. Unknown members are input errors. A required non-empty string is rejected if it is empty after trimming ASCII whitespace U+0009 through U+000D and U+0020. The original string is retained unless a normalization rule below says otherwise.

`id` and `event` are non-empty strings after the validation trim. The ID is preserved exactly and is not part of the semantic comparison key. `event` is ASCII-trimmed and ASCII-lowercased for that key: only U+0041 through U+005A map to U+0061 through U+007A; other Unicode scalar values are unchanged. `observation_process` is an object with exactly `kind`, `parameters`, and `raw`: `kind` is required non-empty text and uses the same ASCII trim/lowercase rule; `parameters` is an optional object whose values are strings, defaults to `{}`, preserves key/value text, and compares in Unicode-scalar-sorted key order; `raw` is optional text or null, defaults to empty text, and uses the ASCII trim/lowercase rule in the key.

`window` is an object with exactly `duration`, `unit`, `anchor`, and `raw`. `duration` is an optional canonical decimal string or null and cannot be negative; `unit` and `anchor` are required non-empty strings and use the ASCII trim/lowercase rule. `raw` is optional text or null and does not affect comparison. Each `thresholds` item is an object with exactly `metric`, `operator`, `value`, `sustain`, `sustain_unit`, and `raw`. `metric` and `operator` are required non-empty strings; metric uses the ASCII trim/lowercase rule and operator is ASCII-trimmed without case folding. `value` is absent/null, or exactly `{"type":"text","value":string}` or `{"type":"decimal","value":canonical-decimal-string}`. Text and decimal values remain different semantic types. `sustain` is absent/null or a canonical non-negative decimal string. `sustain_unit` is absent/null or text and defaults to empty text after applying the ASCII trim/lowercase rule. `raw` is absent/null or text and is excluded from comparison. Thresholds compare as an unordered multiset after sorting their normalized tuples; duplicate entries are retained. Missing and null `window.duration` and threshold `value` normalize to an explicit unknown. Missing and null optional `sustain`, `sustain_unit`, and raw fields normalize to their defined absent/default values and do not by themselves make a definition unknown. A supplied value of the wrong type is an input error.

The normalized threshold tuple is `(metric, operator, value-kind, value, sustain, sustain-unit)`. Compare strings by Unicode scalar value, decimals by exact rational value, and optional values with absent before present. For threshold ordering only, value kinds sort as unknown, text, decimal. Equal tuples retain multiplicity. For the identity projection and diagnostic index, ties are ordered by the JCS bytes of the complete normalized threshold row, including raw metadata; identical rows remain repeated. This ordering defines the canonical threshold index used by semantic diagnostic pointers.

These accepted shapes and validations are mapped from the completed Isoprax Haskell kernel at `origin/codex/042-haskell-semantics-kernel` commit `223187c319d6b50fb05cc2d55ffc5b465556a660`; exact source locations and intentional v0.1 differences are recorded in `contracts/isoprax-mapping.md`. Semadmit adds stable RFC 6901 pointers and input codes; the Haskell kernel reports a categorized error without a field pointer.

`sample` is either null, meaning absent evidence, or an object with exactly `scores` and `outcomes`. Both are arrays of equal length. Scores are canonical non-negative decimal strings in [0,1] with at most 12 fractional digits. Outcomes are JSON integers 0 or 1; booleans are rejected. Array order is preserved. Two empty arrays mean a supplied empty sample and fail minimum-event eligibility; null means the sample is missing. Each sample is limited to 100,000 pairs.

Isoprax v0.1 derives definition compatibility and calibration from the two definitions, samples, and policy. Its evidence array is empty; caller-provided pass flags or evidence cannot replace those computations. Definition IDs are independently bound to each subject and its sample, but different IDs do not prevent direct compatibility when normalized semantic keys match. Semadmit v0.1 supports direct compatibility only; it does not import the Haskell kernel's attestation or bridge paths.

The Isoprax policy object has exactly `min_events`, `n_bins`, `max_ece`, `definition_comparison`, and `numeric_profile`. `min_events` is a safe JSON integer from 1 through 100,000, matching the per-subject sample row limit; `n_bins` is a safe JSON integer from 1 through 1,000; `max_ece` is a canonical decimal string in [0,1]. `definition_comparison` is exactly `normalized-key/0.1` and `numeric_profile` is exactly `decimal-rational-12/0.1`. All five fields participate in policy identity. Other enum values are unsupported policies. Both outcome classes and nonzero score variance are fixed eligibility rules of the `isoprax/0.1` pack, not caller-selectable policy fields; changing those rules requires a pack-version change.

### Measurement Subject, Policy, and Coverage

A measurement subject has exactly `quantity_id`, `unit_id`, `method_id`, `reference_frame_id`, `context_population_id`, and `window`. Each identifier is either a non-empty Unicode-scalar string or null. Null is an explicit unknown; omitted fields and empty strings are malformed. Identifiers are compared as exact Unicode scalar sequences without normalization.

A window has exactly timescale, start, and end. Timescale is exactly unix-ms-utc-v1: integer ticks are POSIX milliseconds since 1970-01-01T00:00:00Z, with leap seconds not represented. Start and end are safe JSON integers in [-9007199254740991, 9007199254740991], and start must be less than end. Windows are half-open [start,end). Both subjects must declare the same timescale and endpoints.

The measurement policy is exactly `{"mode":"identical_window_positive_coverage"}`. Its digest uses the `measurement/0.1/policy` identity schema. No other measurement policy is supported in v0.1.

Each measurement coverage evidence item has exactly id, kind, schema, subject_role, subject_digest, policy_digest, window, and count:

- id is a non-empty unique string.
- kind is coverage and schema is measurement/0.1/coverage.
- subject_role is left or right.
- subject_digest is recomputed from the complete validated subject.
- policy_digest must equal the recomputed top-level policy digest. A different well-formed digest is contradictory evidence and fails that role's coverage obligation.
- window repeats the exact declared window for that subject.
- count is a safe JSON integer from 0 through 9007199254740991. Zero is well-formed but fails coverage; a negative count is malformed.

At most one coverage item may name each role. A second item for the same role is `evidence.duplicate_role`; the error points to the later item's `subject_role` field in input order. No item for a role means missing coverage. A malformed subject_digest or policy_digest is an input error; a well-formed digest that contradicts the subject or policy is a failed obligation. A contradictory window is also a failed obligation. Coverage counts are supplied facts and do not prove observations occurred.

aggregate_measurements returns a decision only. It does not carry measurement values, calculate an aggregate, or claim that one was performed. Actual aggregation is the downstream caller's responsibility and is outside the v0.1 Semadmit consumer API; an admissible result is not evidence that a caller honored it.

## Canonical Values and Identity

Use RFC 8785 JCS for canonical bytes and object-property ordering by UTF-16 code units. Published JCS vectors are required in addition to project vectors. Reject invalid UTF-8, escaped unpaired surrogates, duplicate object keys, unknown fields, and JSON number tokens that are fractional, exponent-form, negative zero, or outside the safe-integer range. JSON numeric values are safe integers only; booleans are never integers. Every non-integer domain quantity, including definition duration, numeric threshold value, sustain, prediction score, and max ECE, is represented as a string. A threshold numeric value uses the tagged decimal form above so it cannot be confused with threshold text. Canonical decimal strings match `-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?`, with at most 12 digits after the decimal point and exact absolute value at most 9,007,199,254,740,991. The spelling `-0` is forbidden. Signed values are allowed only for threshold numeric values. All other decimal fields are non-negative and retain their field-specific bounds. No Unicode normalization is performed. Isoprax key normalization uses the ASCII trim/lowercase rule defined above; other Unicode scalar values are preserved.

Artifact identity is lowercase `sha256:` plus the hex encoding of JCS bytes for `{"kind":K,"schema":V,"payload":P}`. Every digest-valued field uses exactly `sha256:` followed by 64 lowercase hexadecimal digits. Core fixes the `request` identity kind and `semantic-oracle/0.1/request` schema. For each operation, the selected pack explicitly declares the `policy`, `subject`, `evidence`, and component kind/schema pairs and their identity projections; component kinds include `definition` and `sample` for Isoprax. Schema IDs are namespaced by pack and version. The shared identity helper accepts only the Core request pair or a pair declared by the selected pack.

For Isoprax, a definition payload is the complete validated definition with `thresholds` defaulted to `[]`, `description` absent/null normalized to null, missing/null `observation_process.raw` and `window.raw` normalized to the empty string, missing `observation_process.parameters` normalized to `{}`, missing/null `window.duration` and threshold `value`/`sustain` normalized to null, and missing/null threshold `sustain_unit`/`raw` normalized to the empty string. All other original text is retained. Thresholds are sorted by normalized tuple and then by each full normalized threshold row’s JCS bytes, so permutations produce one identity even when rows differ only in excluded raw metadata. A sample payload is exactly `{"definition_digest":D,"scores":[...],"outcomes":[...]}`; pair order is preserved. A policy payload is the complete validated policy object. A measurement subject payload is the complete validated subject. An evidence payload is the complete validated evidence record, including its ID. Each pack defines identity projections for its declared artifacts and arrays; ordered arrays preserve their order and set-valued arrays use the declared stable sort key. The common request preimage and the rule that top-level evidence is a set sorted by unique ID are fixed in `contracts/pack-interface.md`. Subject roles and cardinalities are pack-declared. RFC 8785 object property ordering remains UTF-16 code-unit order and is distinct from collection sorting.

Every supplied digest is compared after recomputation. Evidence and result bindings sort by ID, subject bindings by role, and component bindings by `(subject_role, name)`, each using Unicode-scalar lexical order. Obligation IDs and diagnostic strings use the same comparator. Object-key order has no semantic effect. The decision digest is lowercase `sha256:` plus the hex encoding of JCS bytes for the exact normative decision payload; it does not hash the outer envelope or a `decision_digest` field. Any change to common hashed fields requires a protocol-version change; any pack-specific change requires a pack-version change.

## Decision Verification and Admission

A decision artifact is an unsigned content record, not an admission capability. A trusted local verifier accepts a candidate artifact only alongside the exact validated request, recomputes request and policy identities, evaluates the pack locally, and compares every normative payload field plus the decision digest with its own result. It must not create Admission by deserializing state=admissible or by trusting a supplied digest. If reevaluation or exact input binding is unavailable, verification fails and no Admission is produced.

Admission is opaque and retains the exact immutable validated request snapshot together with the selected registered pack/version. A guarded operation consumes only inputs from that retained snapshot; it must not reread caller-owned arrays or paths after verification. A file or database consumer must obtain an immutable content-addressed snapshot or keep one atomic read/verify/use transaction. Packs without a guarded operation return eligibility only and make no claim about downstream consumption.

## Valid Decision Envelope

A valid result has exactly kind, payload, and decision_digest. Kind is decision. Payload has exactly protocol, pack, operation, request_digest, policy_digest, state, bindings, obligations, and diagnostics. Every field is present; empty collections are empty arrays, never null or omitted. State is admissible, inadmissible, or indeterminate. All result arrays use their generic canonical keys and Unicode-scalar lexical order.

Bindings has exactly subjects, components, and evidence. Subject entries have exactly role, kind, schema, and digest, sorted by role. Component entries have exactly subject_role, name, kind, schema, and digest, sorted by subject_role then name; a pack may use these for separately addressable nested inputs such as an Isoprax definition and sample. Core enforces the selected operation's declared per-role component cardinalities before emitting the result. Evidence entries have exactly id, kind, schema, and digest, sorted by ID. Empty arrays are used when a pack has no components or evidence. Obligation entries have exactly id and outcome, sorted by ID; outcome is pass, fail, or missing. A valid result contains every obligation declared by the selected operation exactly once; omitted, duplicate, or undeclared obligation output is `internal.failure`, not a partial decision. Diagnostics have exactly obligation_id, pointer, and code; they are sorted by obligation_id, pointer, and code using Unicode-scalar lexical order, with duplicates removed.

Diagnostic pointers use RFC 6901 escaping and address the normalized validated request: evidence set arrays are ordered by ID before a semantic diagnostic is formed. Human-readable text, telemetry, and build identity are outside this payload. Inadmissible and indeterminate results have no admission value.

## Protocol Error Envelope

A protocol error has exactly kind, code, and pointer. Kind is error. Pointer is always present as an RFC 6901 string; the empty string denotes the whole request. UTF-8, JSON-syntax, unpaired-surrogate, and internal-failure errors use the empty pointer. A duplicate-key error points to the repeated member at its later occurrence; a number-profile error points to the offending number token. Missing and malformed fields point to the named field or item. Unsupported protocol, pack, and operation errors point to `/protocol`, `/pack`, and `/operation`, respectively. An unsupported policy enum points to its field; an unsupported policy shape points to `/policy`. A duplicate evidence-ID error points to the later item's `id`; a duplicate-role error points to the later item's role field. A line-size error uses the empty pointer; collection-limit errors point to the first item over the limit; a nesting-limit error points to the first object or array whose depth would exceed the limit. Error codes are closed:

- input.invalid_utf8
- input.invalid_json
- input.duplicate_key
- input.invalid_unicode
- input.number_profile
- input.unknown_field
- input.missing_field
- input.invalid_type
- input.invalid_value
- protocol.unsupported_version
- protocol.unsupported_pack
- protocol.unsupported_operation
- policy.unsupported
- identity.digest_mismatch
- evidence.duplicate_id
- evidence.duplicate_role
- limit.exceeded
- internal.failure

Errors contain no state, admission, or partial decision. Error precedence is deterministic. First apply framing and size limits, then report the earliest invalid UTF-8 byte if decoding fails. During parsing, report the parser or profile violation with the earliest offending byte offset; if two checks identify the same byte, use this order: invalid Unicode scalar, invalid JSON syntax, duplicate key, number profile. After parsing, validate objects and array elements in descriptor order. At each object, report the unknown field with the smallest Unicode-scalar sequence before validating declared fields in their schema order. Validate evidence items in supplied array order; after each item's `id` is validated, reject a repeated ID at that later input index, then continue its remaining fields. A per-role duplicate check runs when that item's `subject_role` is validated, so a duplicate ID wins over a duplicate role in the same record. An earlier item's error wins over a later item's error. Finally recompute the top-level policy digest before domain evaluation. Fractional, exponent-form, negative-zero, boolean-as-integer, or out-of-safe-range JSON numbers fail number-profile or type validation as applicable. A policy digest mismatch is `identity.digest_mismatch`. A well-formed subject or policy digest inside measurement coverage that differs from the request is instead a failed coverage obligation. Domain mismatches and missing evidence are decisions, not protocol errors.

## CLI and JSONL

The Haskell reference CLI registers the maintained first-party packs only. The Python library exposes `JsonlRunner(evaluator)`, where the evaluator is constructed from an explicit registry; a Python host can therefore process JSONL for any trusted Python packs it registered, including downstream packs. A host may instead call `Evaluator.evaluate` and `Evaluator.verify` directly. There is no pack auto-discovery or cross-language code loading.

The single-request command reads one JSON object from standard input. JSONL reads one request per LF-delimited line; an optional CR immediately before LF is JSON whitespace and remains within the line limit. A final unterminated line is processed. Blank lines are invalid JSON requests. A line over the byte limit is discarded through its LF, emits one limit.exceeded result, and processing continues. Both the Haskell CLI and Python `JsonlRunner` use this framing and output contract.

Stdout contains only one machine result per request. Logs go to stderr. Single-request exit codes are 0 admissible, 1 inadmissible, 2 indeterminate, 3 protocol/input error, and 4 internal failure. JSONL continues after line-local errors and returns the greatest severity encountered; a host process wrapper exits with that value. An internal failure emits only the generic internal.failure envelope, writes no supplied-data stack trace to stdout, and ends stream processing with status 4.

## Resource Limits

The shared v0.1 limits are fixed: 10 MiB per request line excluding LF; JSON container nesting depth 64 with the root object at depth 1; and at most 256 evidence items. Each registered pack declares additional domain limits; the Isoprax pack allows at most 100,000 prediction rows per subject. Exceeding a shared or pack limit is `limit.exceeded`. No caller runtime override is supported in v0.1.

## Determinism Boundary

The decision path and registered pack code are pure functions of the normalized request and exact pack version. They cannot read ambient environment, working-directory files, network responses, wall clock, random sources, or mutable process history. Request order, prior evaluations, thread scheduling, and cache state cannot change a decision. An explicit timestamp in validated request content may be used by a pack's declared rules. Pack build identity is separate non-normative execution metadata; the declared pack ID/version is normative. A common semantics change requires a protocol version change; a domain semantics change requires a pack version change.
