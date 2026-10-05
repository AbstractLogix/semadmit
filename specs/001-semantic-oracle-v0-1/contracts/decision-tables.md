# Decision Tables

**Status**: Normative v0.1 M0 tables and fixtures, approved by independent review on 2026-09-30. Implementation conformance remains unproven.

The domain rules below cover the Isoprax and measurement first-party packs only. The common state and binding rules are pack-neutral; each additional pack must declare its own roles, schemas, obligations, diagnostics, and decision table. M0 includes a neutral extension fixture for the public interface; the Ducky-specific table and fixtures are an M4 gate after the interface is frozen.

## State Resolution

| Evaluated obligations | Decision state |
|---|---|
| One or more fail, with or without missing | inadmissible |
| No fail and at least one missing | indeterminate |
| All operation-declared obligations are present exactly once and pass | admissible |

Every well-formed evaluation returns exactly one outcome for each obligation declared for the selected operation; this set is fixed and cannot shrink based on request contents. A pack that needs conditional behavior must encode a deterministic pass/fail/missing outcome or declare a separate operation. Omission, duplication, or an undeclared obligation is an invalid pack result and produces `internal.failure`, never an admissible partial result. A missing outcome means a declared requirement could not be established from supplied evidence. Return all applicable diagnostics. A malformed supplied value is a protocol/input error, not an obligation outcome. Unsupported protocol, pack, operation, or policy is a protocol error. Neither error path produces admission. Diagnostics are sorted by obligation_id, pointer, code and deduplicated. Pointers address the normalized validated request defined in wire-protocol.md. Braced names in pointer templates below are placeholders; substitute each listed role, field, or canonical index before emitting an RFC 6901 pointer.

## Built-in Operation Declarations

Both operations require exactly one `left` and one `right` subject and reject any other role. A present subject binds the complete validated subject using kind `subject`; the role is the generic binding key, not part of its artifact preimage. The declared outputs are fixed:

| Pack / operation | Policy artifact | Subject artifact per role | Component output per role | Evidence input and artifact | Complete obligation IDs |
|---|---|---|---|---|---|
| `isoprax/0.1` / `pool_predictions` | `policy`, `isoprax/0.1/policy` | `subject`, `isoprax/0.1/subject` | Exactly one `definition` (`definition`, `isoprax/0.1/definition`); zero or one `sample` (`sample`, `isoprax/0.1/sample`), present exactly when the input sample is an object | Exactly empty array; no evidence artifacts | `definition.compatibility`, `calibration.left`, `calibration.right` |
| `measurement/0.1` / `aggregate_measurements` | `policy`, `measurement/0.1/policy` | `subject`, `measurement/0.1/subject` | None | Zero to two coverage records, at most one per role; each uses kind `evidence`, schema `measurement/0.1/coverage` | `measurement.compatibility`, `coverage.left`, `coverage.right` |

These counts apply before state reduction. A missing or extra subject role is an input error; a missing, duplicate, or extra component produced by a trusted pack is `internal.failure`. A null Isoprax sample emits no sample component; a supplied empty sample emits one. A missing measurement coverage item creates a `missing` coverage obligation, while a duplicate coverage role is an input error.

## Isoprax: pool_predictions

The two required roles are left and right. Each has a definition and either a sample or explicit null absence. The supported policy has exactly min_events, n_bins, max_ece, definition_comparison, and numeric_profile. min_events is an integer in [1, 100000], n_bins is an integer in [1,1000], and max_ece is a canonical decimal string in [0,1]. definition_comparison is exactly normalized-key/0.1; numeric_profile is exactly decimal-rational-12/0.1. The policy digest covers all five fields. v0.1 additionally requires both outcome classes and nonzero score variance; these fixed rules are bound by the pack version and cannot be disabled through policy fields.

| Obligation ID | Pass | Fail | Missing |
|---|---|---|---|
| definition.compatibility | Both definitions are complete and their normalized semantic comparison keys match. IDs may differ; each exact ID and full definition digest remains separately bound to its subject and sample. | A known semantic field differs. | No known mismatch exists, but an allowed explicit unknown prevents a complete comparison. |
| calibration.left | Left sample is present and satisfies every calibration rule below. | A supplied sample violates one or more calibration rules. | Left sample is null. |
| calibration.right | Right sample is present and satisfies every calibration rule below. | A supplied sample violates one or more calibration rules. | Right sample is null. |

The semantic comparison key contains ASCII-trimmed/lowercased event, observation-process kind, observation-process raw value, window unit/anchor, and metric/sustain-unit fields; exact parameter key/value pairs; canonical decimal duration, threshold values, and sustain; and the multiset of normalized thresholds. ASCII lowercase changes only A-Z; other Unicode scalars remain exact. Definition ID, description, window raw, and threshold raw are excluded. Different IDs with equal complete keys pass compatibility; IDs and full definition digests remain separately bound. A changed known semantic field fails compatibility even when IDs match. Missing/null window duration and threshold value are unknown, not equal-known values. Emit an unknown diagnostic for each such leaf on either side; if any known mismatch also exists, the obligation fails and unknown diagnostics remain. With unknowns and no known mismatch, compatibility is missing.

Calibration uses the ordered scores and binary outcomes in the exact supplied sample. It fails minimum-event eligibility when count < min_events, when either outcome class is absent, when score variance is zero, or when exact ECE > max_ece. Comparisons are inclusive at the passing boundaries: count >= min_events and ECE <= max_ece. For an empty supplied sample, emit only minimum-events failure; there is no defined class, variance, or ECE calculation. For nonempty samples, evaluate every applicable criterion and return every corresponding diagnostic.

For n_bins equal-width bins, bin index is min(floor(score × n_bins), n_bins − 1). Empty bins contribute zero. ECE is the exact rational sum over nonempty bins of (bin count / total count) × abs(mean score − mean outcome). Score variance is nonzero exactly when at least two distinct canonical score values occur. No floating tolerance is used. M0 fixture sidecars record the reduced numerator and denominator for each defined ECE; ECE is an internal calculation and is not a field in the v0.1 decision envelope.

Canonical v0.1 decimal quantities arrive as strings. For a finite legacy IEEE-754 binary64 value, an adapter first obtains its RFC 8785 JCS number spelling, expands any exponent to plain decimal without further rounding, and validates the canonical decimal profile and target field bounds. Non-finite values are rejected. A legacy Scientific value must be explicitly converted to binary64 with any loss recorded, or rejected; this adapter does not silently claim to preserve its original precision. A binary64 negative zero serializes as `0` through this adapter, while a raw Semadmit request number token `-0` is rejected. The mapping and precision/range boundaries are recorded in `conformance/fixtures/isoprax-legacy-number-adapter.json`. This is a representation mapping, not a claim that the old floating-point calculation equals exact rational arithmetic. Any ECE difference is recorded as an intentional numeric-profile difference or a reproduced defect.

| Diagnostic code | Pointer | Condition |
|---|---|---|
| definition.event_mismatch | /subjects/right/definition/event | Normalized events differ. |
| definition.observation_process_mismatch | /subjects/right/definition/observation_process | Normalized process kind, parameter set, or process raw value differs. |
| definition.window_mismatch | /subjects/right/definition/window | Normalized duration, unit, or anchor differs. |
| definition.thresholds_mismatch | /subjects/right/definition/thresholds | Sorted normalized threshold sets differ. |
| definition.unknown | `/subjects/{left,right}/definition/window/duration` or `/subjects/{left,right}/definition/thresholds/{canonical-index}/value` | Missing/null duration or threshold value prevents complete comparison. Emit one per unknown leaf, including alongside a known mismatch. |
| calibration.sample_missing | /subjects/left/sample or /subjects/right/sample | The sample is null. |
| calibration.min_events | /subjects/left/sample or /subjects/right/sample | A supplied sample count is below min_events. |
| calibration.outcome_class_missing | /subjects/left/sample or /subjects/right/sample | A nonempty sample lacks outcome 0 or outcome 1. |
| calibration.zero_score_variance | /subjects/left/sample or /subjects/right/sample | A nonempty sample has only one distinct score. |
| calibration.ece_exceeded | /subjects/left/sample or /subjects/right/sample | Exact ECE is greater than max_ece. |

Malformed or unequal-length samples, malformed definitions, invalid policy values, and noncanonical decimals are protocol/input errors. A caller-supplied pass flag, human attestation, or retained observation cannot override computed results.

## Measurement: aggregate_measurements

The two required roles are left and right. Each subject has quantity_id, unit_id, method_id, reference_frame_id, context_population_id, and window. Known identifiers must match exactly; explicit null is unknown. The window is a half-open POSIX-millisecond interval under the single timescale defined in wire-protocol.md. The policy is the fixed identical-window-positive-coverage mode.

| Obligation ID | Pass | Fail | Missing |
|---|---|---|---|
| measurement.compatibility | All five identifiers are known and match, and the complete windows match. | At least one known identifier differs or the valid windows differ. | No known mismatch exists, but at least one required identifier is null. |
| coverage.left | Exactly one evidence item binds the left subject digest, current policy digest, and exact declared window, with count > 0. | Supplied coverage contradicts the subject, policy, or window, or has count 0. | No coverage item names left. |
| coverage.right | Exactly one evidence item binds the right subject digest, current policy digest, and exact declared window, with count > 0. | Supplied coverage contradicts the subject, policy, or window, or has count 0. | No coverage item names right. |

Return all known mismatch diagnostics. A known mismatch makes measurement.compatibility fail even when another field is unknown. Missing coverage is missing evidence; a substituted subject, a well-formed policy_digest mismatch, contradictory window, or zero count is a failed coverage obligation. Malformed digest syntax, negative counts, and malformed records are input errors. A duplicate role is an input error. Positive counts are supplied facts, not proof that observations occurred.

| Diagnostic code | Pointer | Condition |
|---|---|---|
| measurement.identifier_mismatch | `/subjects/right/{field}` for each differing field in `quantity_id`, `unit_id`, `method_id`, `reference_frame_id`, `context_population_id` | Emit one diagnostic for each known right-side identifier that differs from the left. |
| measurement.window_mismatch | /subjects/right/window | Valid declared windows differ. |
| measurement.unknown | `/subjects/{role}/{field}` for each null field in `quantity_id`, `unit_id`, `method_id`, `reference_frame_id`, `context_population_id` and role `left` or `right` | Emit one diagnostic at each null identifier, including alongside a known mismatch. |
| coverage.missing | /subjects/left or /subjects/right | No coverage item names the role. |
| coverage.subject_mismatch | /evidence/{canonical-index}/subject_digest | Evidence binds another subject digest. |
| coverage.policy_mismatch | /evidence/{canonical-index}/policy_digest | Evidence binds another policy digest. |
| coverage.window_mismatch | /evidence/{canonical-index}/window | Evidence window differs from the subject window. |
| coverage.zero_count | /evidence/{canonical-index}/count | Supplied count is zero. |

The canonical evidence index is the record's index after evidence has been sorted by ID. These diagnostics do not use human-readable prose as part of decision identity.

## Protocol Errors and Precedence

The shared error envelope, parser/profile errors, and precedence are closed in wire-protocol.md. For both built-in packs, an absent required field is `input.missing_field` at that field's pointer; an extra field or subject role is `input.unknown_field` at its pointer; a wrong JSON type is `input.invalid_type` at that value; and a well-typed value outside its declared range, grammar, or constant is `input.invalid_value` there. These rules apply to every field in the closed schemas above and in wire-protocol.md. A missing required role points to `/subjects/{role}`. Unknown members are selected before known-field validation as the wire protocol specifies. The following operation-specific rules resolve cases that the generic mapping does not distinguish:

| Operation | Condition | Error code | Pointer |
|---|---|---|---|
| Isoprax | Unsupported `definition_comparison` or `numeric_profile` enum | `policy.unsupported` | `/policy/definition_comparison` or `/policy/numeric_profile` |
| Isoprax | Nonempty evidence array | `input.invalid_value` | `/evidence/0` |
| Isoprax | Scores and outcomes have unequal lengths | `input.invalid_value` | `/subjects/{role}/sample/outcomes` |
| Isoprax | Sample array exceeds 100,000 entries | `limit.exceeded` | First over-limit element in the affected `/subjects/{role}/sample/scores` or `/outcomes` array |
| Isoprax | Malformed tagged threshold value or noncanonical decimal string | `input.invalid_type` for wrong type, otherwise `input.invalid_value` | Offending `/subjects/{role}/definition/thresholds/{source-index}/{field}` or nested `/value/type` or `/value/value` |
| Measurement | Unsupported policy `mode` | `policy.unsupported` | `/policy/mode` |
| Measurement | Invalid timescale or start greater than or equal to end in a subject or evidence window | `input.invalid_value` | Offending `/subjects/{role}/window/timescale` or `/subjects/{role}/window/end`; for evidence, `/evidence/{source-index}/window/timescale` or `/end` |
| Measurement | Malformed coverage digest, role, kind, schema, count, or ID | `input.invalid_type` for wrong type, otherwise `input.invalid_value` | Offending `/evidence/{source-index}/{field}` |
| Measurement | Repeated evidence ID or subject role | `evidence.duplicate_id` or `evidence.duplicate_role` | Later input record's `/evidence/{source-index}/id` or `/subject_role` |
| Both | Malformed supplied top-level policy digest or well-formed digest unequal to the recomputed policy identity | `input.invalid_value` or `identity.digest_mismatch` | `/policy_digest` |

`{source-index}` is the index in the supplied evidence or threshold array during input validation. Domain diagnostics instead use the canonical index after declared set normalization. A well-formed measurement coverage digest or window that contradicts a subject or policy is a failed obligation with the diagnostic above, not an input error. A request with several domain failures remains a valid decision and returns all applicable diagnostics.
