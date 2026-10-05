# Public Python Pack Interface

**Status**: Normative v0.1 M0 contract, approved by independent review on 2026-09-30.

## Scope

The v0.1 downstream extension interface is an in-process Python API. The Haskell reference CLI registers the maintained first-party packs only. A Python host may use the language-neutral JSONL protocol through `JsonlRunner`, constructed with an explicit `Evaluator` and registry, or call the evaluator directly. JSONL is not a mechanism for loading or registering code from another language. Haskell and Python independently implement Core and the maintained first-party packs. A downstream pack written in another language requires a separately reviewed embedding contract.

A pack supplies versioned domain validation and decision rules while reusing Core's request framing, canonical identity, binding generation, result/error envelope, obligation-state reduction, verification, and snapshot handling. Adding a pack must not require copying or adding domain-specific fields to generic Core.

## Python API Shape

A host constructs a registry from installed, trusted pack instances. A `pack_id` has the exact form `<namespace>/<major>.<minor>`: an ASCII lowercase namespace starting with a letter and followed by up to 62 lowercase letters, digits, or hyphens, then canonical nonnegative decimal version components with no leading zeroes except `0`. The founding IDs are `isoprax/0.1` and `measurement/0.1`. A downstream author chooses a stable namespace associated with its project; global namespace ownership is not centrally enforced. Registration validates each descriptor and rejects duplicate exact `pack_id` values. Request data can select only an already registered ID; it cannot import code.

The v0.1 public call shapes are:

```python
registry = PackRegistry((isoprax_pack, measurement_pack))
evaluator = Evaluator(registry)
result = evaluator.evaluate(request_object)
admission = evaluator.verify(request_object, candidate_result)
runner = JsonlRunner(evaluator)
exit_status = runner.run(input_stream, output_stream)
```

The pack protocol is conceptually generic over an immutable pack-specific input type:

```python
class Pack[InputT](Protocol):
    descriptor: PackDescriptor

    def validate(self, operation: str, policy: JsonObject,
                 subjects: JsonObject, evidence: JsonArray
                 ) -> NormalizedPackRequest: ...

    def decode(self, request: NormalizedPackRequest
               ) -> InputT: ...

    def component_payloads(self, request: InputT, identities: PackIdentity
                           ) -> Sequence[ComponentPayload]: ...

    def evaluate(self, operation: str, request: InputT
                 ) -> PackEvaluation: ...
```

`NormalizedPackRequest` contains the pack's normalized JSON projections for `policy`, `subjects`, and `evidence`. The pack validates supplied values in source order and returns errors with pointers into that source request. After successful validation, Core sorts the common top-level evidence set by ID and uses the resulting normalized projections for identity and snapshot retention. Core then calls the pack's pure, deterministic `decode` method with those exact projections. The resulting immutable `InputT` MUST be a lossless typed view of them; a pack MUST NOT reintroduce source positions or raw array order. Only this decoded value may be used for component generation or evaluation. A decode failure for a previously validated normalized request is `internal.failure`. Domain diagnostic pointers refer to the normalized request. The exact Python aliases and error classes are implementation details, but the ownership and behavior below are contract requirements.

`Evaluator.evaluate` accepts a JSON-shaped Python request tree; `Evaluator.verify` accepts that tree and a JSON-shaped candidate decision tree. These trees contain only dicts with string keys, lists, strings containing Unicode scalar values, safe JSON integers, booleans, and null. Core makes bounded immutable copies before validation and never rereads caller-owned objects. The copy traversal enforces depth 64 and a 10 MiB JCS UTF-8 size budget independently for the request and candidate; it stops when either bound is exceeded, before materializing the rest of that tree. An oversized or over-deep candidate fails verification without Admission. Floats are rejected as `input.number_profile`; other non-JSON Python values are `input.invalid_type`. Byte-only errors such as invalid UTF-8, duplicate JSON keys, a byte-order mark, or the original numeric token spelling cannot occur after an object has been constructed. `JsonlRunner` and the Haskell CLI enforce those byte and token rules before constructing the same internal tree. Structural and domain validation, identity, decision, and verification rules are otherwise identical. The 10 MiB raw-line limit applies to JSONL/CLI input; direct Python calls apply the same cap to each copied tree's JCS UTF-8 bytes before domain evaluation. The evidence-count and pack limits apply on both paths.

`PackIdentity` is a Core-owned service scoped to the selected registered descriptor. Its `digest(kind, schema, payload)` operation accepts only a declared kind/schema pair and returns the `sha256:` digest of Core's RFC 8785 kind/schema/payload envelope. It lets a pack build a component payload that refers to another component without implementing canonicalization or hashing. For Isoprax, `component_payloads` obtains the definition digest through this service and places it in the sample payload's `definition_digest`. Core still computes the final component bindings from the emitted payloads and enforces their declared cardinalities. The service does not accept a caller-supplied digest as authority.

## Pack Descriptor and Validation Ownership

Each `PackDescriptor` MUST declare:

- an exact namespaced, versioned `pack_id` and supported common protocol versions;
- the closed operation set;
- for each operation, subject roles/cardinality and the closed policy, subject, evidence, and component schemas;
- schema field-validation order, required/optional fields, and normalization rules;
- which arrays are sequences and which are sets, including stable set keys and ordering;
- for every top-level evidence record, `id` as the first validated field and, when a per-role uniqueness rule exists, `subject_role` as a later declared field;
- policy, subject, evidence, and component artifact kinds/schemas and identity projections for each operation; no kind/schema pair or projection is inferred from a field name or a fixture sidecar;
- each component name, kind, schema, and per-role cardinality (including whether it is optional);
- pack-specific resource limits bounded by Core's shared limits;
- the complete obligation ID set for each operation, diagnostic codes/pointers, and allowed pass/fail/missing outcomes.

Validation has two stages:

1. **Core** parses UTF-8/JSON, rejects duplicate keys and unsupported number tokens, applies shared byte/depth/evidence limits, validates the exact common envelope and common field types, and resolves an exact registered `pack_id` plus declared operation.
2. **Pack** validates its closed operation-specific policy, subjects, evidence, and nested component schemas; applies pack limits; normalizes values; and returns normalized JSON projections. Its descriptor's schema order governs deterministic field validation. Unknown object keys are considered in Unicode-scalar order; declared fields are then validated in descriptor order. Evidence items are validated in supplied array order: validate `id` and reject a repeated ID immediately, then validate remaining declared fields; a declared per-role uniqueness check runs when `subject_role` is validated. An error in an earlier item wins over any error in a later item, and a duplicate ID in one item wins over a duplicate role in that same item. Input-error pointers retain source-array indices. Only after successful validation does Core normalize the common evidence set by ID, then asks the pack to decode that exact normalized request before identity-based evaluation; domain diagnostics point into that normalized request.

A pack reports a malformed or unsupported input by raising `PackInputError(code, pointer)` using only the shared protocol error vocabulary and an RFC 6901 pointer into the request. A well-formed domain mismatch or absent evidence is returned as an obligation outcome, not an input error. Core rejects undeclared codes, pointers outside the request, undeclared obligations/diagnostics, duplicate components, or unexpected pack output. Every well-formed evaluation MUST return exactly one outcome for every obligation declared by the selected operation. An omitted or duplicate obligation is an invalid pack result and becomes `internal.failure`; it is never interpreted as missing evidence. Every component emitted by `component_payloads` MUST match a descriptor declaration, and Core MUST enforce each declared per-role cardinality before creating bindings. A missing required component, extra component, or cardinality mismatch is an invalid pack result and becomes `internal.failure`. An unexpected exception becomes the generic `internal.failure` envelope.

## Bindings and Core-Owned Results

The result envelope uses domain-neutral records:

- subject: `role`, `kind`, `schema`, `digest`;
- component: `subject_role`, `name`, `kind`, `schema`, `digest`;
- evidence: `id`, `kind`, `schema`, `digest`.

Core derives subject and evidence records from the normalized validated request and declared schemas. The pack returns only raw `ComponentPayload(subject_role, name, kind, schema, payload)` values, never hashes or complete binding records. A component payload may contain a digest derived through `PackIdentity` where its declared schema requires one; that value is content inside the payload, not a caller-authoritative binding. Core checks component names, schemas, and exact declared cardinalities, then computes every binding digest from exact normalized content. It requires the complete per-operation obligation set exactly once, derives overall state only after this check, enforces declared result vocabularies, orders records, hashes the result, locally reevaluates candidate artifacts, and retains the immutable request snapshot. A pack cannot supply state, decision digests, or caller-authoritative bindings.

For example, Isoprax declares exactly one `definition` component and zero or one `sample` component under each role; explicit null sample absence emits no sample component, while an empty sample emits one. Measurement declares no components. A Ducky pack may declare exactly one deck-revision and one meta-snapshot component. Domain names remain in the pack descriptor and payloads, not in Core result fields.

## Request Identity

The request identity payload is the complete normalized common request with exactly `protocol`, `pack`, `operation`, `policy_digest`, `policy`, `subjects`, and `evidence`. Core recomputes `policy_digest` from the normalized policy, checks the supplied value, and includes the verified value in the request preimage. Pack/version and operation are included. Execution/build metadata is excluded.

Core treats the top-level evidence array as a set keyed by unique `id` and sorts it by Unicode-scalar lexical order after validation, before request hashing, evaluation, and domain-diagnostic pointer creation. Every other array is ordered by default; the selected pack descriptor may declare a set-valued array and its stable sort key. Set permutations normalize to one identity; sequence permutations retain distinct identities. Object keys use RFC 8785 ordering. Malformed-input and duplicate-record errors retain pointers into the original supplied request. M0 fixtures MUST include a valid request pair and a domain-failing request pair with evidence in opposite input orders; each pair MUST yield the same normalized request bytes and digest, and the failing pair MUST yield identical decision fields, diagnostic codes, and normalized pointers.

The request digest is SHA-256 over RFC 8785 bytes for:

```json
{"kind":"request","schema":"semantic-oracle/0.1/request","payload":{"protocol":"semantic-oracle/0.1","pack":"<exact-pack-id>","operation":"<operation>","policy_digest":"<recomputed-digest>","policy":{},"subjects":{},"evidence":[]}}
```

The example shows the complete field set; pack payloads fill the closed objects and arrays. A supplied digest is never omitted from the preimage merely because its value was recomputed.

## Versioning and Trust Boundary

The selected pack ID includes its version and is matched exactly. The host does not silently substitute an older/newer version, apply aliases, or negotiate compatibility. A pack version changes when its schemas, normalization, policy meaning, obligations, identity projection, or decision semantics change. A common-envelope/identity/result/verification change increments the common protocol version.

Pack code is trusted installed application code, not request content. It obeys Core's offline determinism boundary: the result is a pure function of the normalized request and exact pack version. It cannot read network, environment, working-directory files, wall clock, random sources, or mutable process history; request order, thread scheduling, or prior evaluations cannot change a decision. A cache is allowed only when it is observationally transparent. It is not sandboxed. No dynamic loader, cross-process plugin ABI, server, or general rule language is defined.

M0 approved the callable contract, error mapping, request preimage, validation order, and fixtures before implementation. Concrete Python record classes remain M1 implementation choices within this behavioral contract.
