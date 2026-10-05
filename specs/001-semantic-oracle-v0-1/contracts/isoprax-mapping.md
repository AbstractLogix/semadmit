# Isoprax Haskell Oracle Mapping and Reuse Boundary

**Status**: Source inspection complete; contract equivalence is not established.

## Source Pin and Verification Record

- The completed Haskell reference kernel is available in `origin/codex/042-haskell-semantics-kernel` at `223187c319d6b50fb05cc2d55ffc5b465556a660`; its package path on that ref is `haskell/isoprax-kernel/`.
- That work was merged to the Isoprax default line, then deliberately refactored to Python by `c5a11f1` (`refactor(semantics)!: commit kernel to Python`). The current Isoprax checkout at `2d66659` no longer contains `haskell/isoprax-kernel/`; it retains a separate, older fixture oracle at `haskell/semantic-oracle/` from the 044 line. This mapping uses the completed 042 kernel as the Haskell baseline and does not confuse the two CLIs.
- The 042 package metadata declares Apache-2.0 and pins GHC/Cabal dependencies. Recheck repository license compatibility and provenance before copying or depending on either package.
- The 042 convergence record reports a clean Cabal build/test and compile-fail run, ten QuickCheck properties at 1,000 examples each, and 34 shared Python/Haskell fixtures. This is recorded repository evidence; Semadmit has not independently rerun those checks.
- All inspection was read-only. No Isoprax file or checkout state was changed.

## Existing Semantics

The completed kernel exposes opaque validated outcome definitions, attestation/bridge evidence, pooling evidence, and calibration values. Its JSON Lines CLI supports identity, commensurability, calibration, admission, and conformance operations. Semadmit uses only the direct-comparison and calibration semantics as a candidate baseline; it does not adopt the kernel's attestation/bridge paths or its transport.

### Completed Haskell Kernel Definition Schema

The Haskell reference accepts exactly these top-level definition fields: `id`, `event`, `observation_process`, `window`, `thresholds`, and `description`. `id`, `event`, `observation_process`, and `window` are required; `thresholds` defaults to `[]`; `description` is optional text or null and is excluded from semantic equality. Unknown fields and malformed types fail with the stable `invalid_outcome_definition` category.

| Object | Accepted fields and validation | Normalized semantic key |
|---|---|---|
| Definition | `id`, `event` are non-empty text; `id` is preserved exactly. | Candidate v0.1 keeps ID exact and uses ASCII trim/lowercase for event. Non-ASCII scalar values remain exact. |
| `observation_process` | Object exactly `{kind, parameters, raw}`. `kind` is required non-empty text. `parameters` is optional object of string values (default `{}`). `raw` is optional text/null (default empty). | Candidate v0.1 applies ASCII trim/lowercase to kind and raw. Parameter keys and values remain exact and keys sort by Unicode scalar values. |
| `window` | Object exactly `{duration, unit, anchor, raw}`. Duration is optional finite number/null and non-negative when present. Unit and anchor are required non-empty text. Raw is optional text/null. | Candidate v0.1 represents duration as a bounded canonical decimal string or null, and applies ASCII trim/lowercase to unit and anchor. Raw is excluded. |
| Each `thresholds` item | Object exactly `{metric, operator, value, sustain, sustain_unit, raw}`. Metric/operator are required non-empty text. Value is absent/null, text, or JSON number. Sustain is optional finite number/null and non-negative when present. Sustain unit and raw are optional text/null. | Candidate v0.1 uses tagged text/decimal values, bounded canonical decimal strings for numeric values and sustain, ASCII trim/lowercase for metric and sustain unit, and ASCII trim for the case-sensitive operator. Raw is excluded. Thresholds are an unordered multiset with deterministic canonical ordering. |

The parser compares direct compatibility by these normalized fields and does not require IDs to match. The ID pair is retained in opaque pooling evidence and calibration must target the corresponding IDs. `description`, window `raw`, and threshold `raw` do not affect compatibility; observation-process `raw` does. The Haskell parser collapses absent and null optional values to the same `Maybe`/empty-text value. Semadmit v0.1 makes only window duration and threshold value explicit unknowns; absent/null sustain means no sustain constraint. It uses ASCII trim/lowercase instead of the Haskell runtime Unicode tables, and tagged decimal strings instead of JSON numeric tokens. These deliberate contract differences now have M0 fixture coverage and independent review; implementation parity remains unproven.

Calibration uses IEEE-754 `Double` scores, integer binary outcomes, and a policy containing `min_events`, `n_bins`, and `max_ece`. The parser allows `min_events == 0`, requires positive bins, and bounds `max_ece` to `[0,1]`. A sample must have equal score/outcome lengths, finite scores in `[0,1]`, and binary outcomes. Passing also requires enough events, both outcome classes, ECE within the threshold, and nonzero score variance.

Definition, sample, and policy digests use SHA-256 over RFC 8785 canonical JSON. The sample digest covers ordered `scores` and `outcomes`; calibration evidence separately binds the definition ID and content digest. Policy identity includes a kind/version and all three policy values. Pool authorization requires matching definition ID/content bindings and equal policies. Pooled evaluation recomputes each supplied sample digest before calculating ECE with the authorized bin count.

The older `haskell/semantic-oracle/` CLI accepts one fixture JSON value and emits a compact projection (`commensurable`, digests, calibration pass flags, `authorized`, and pooled ECE). It is a CI oracle, not the completed 042 kernel CLI or the Semantic Oracle v0.1 protocol.

The Python implementation lives in `isoprax/commensurability.py`, `isoprax/semantic_types.py`, `isoprax/evaluation.py`, and `isoprax/identity.py`. Its normalized `OutcomeDefinition` comparison key contains event, observation process, window, and order-normalized thresholds; it excludes ID and description. Python distinguishes direct, bridgeable, and irreducible definition comparisons. Only direct comparisons create poolable typed evidence; bridgeable records do not authorize pooling until a future operation re-derives outcomes under a shared definition.

Python's sealed typed evidence binds definition IDs, definition-content digests, calibration sample digests, and the complete `CalibrationPolicy`. Runtime authorization checks those bindings and policy equality. `authorized_pooled_ece` rehashes the score/outcome sequences supplied to that call and uses the token's bin count. The separate `cross_family_report.pooled_ece` field is documented as a same-call diagnostic: it may be reported for directly commensurable inputs without calibration evidence and is withheld for non-commensurable inputs. It is not the typed admission operation. The Python policy defaults to 500 events, 10 bins, and 0.05 max ECE; its types accept zero minimum events, require positive bins, and bound finite max ECE to `[0,1]`. Its calibration gate also requires both outcome classes, nondegenerate score variance, and the configured count/ECE checks.

## Contract Differences That Remain Open

| Area | Isoprax implementation | Semantic Oracle v0.1 proposal | Required disposition |
|---|---|---|---|
| Definition compatibility | The completed Haskell kernel excludes ID and description from semantic comparison; equal normalized semantic keys are direct even when IDs differ. It also has attestation/bridge behavior for selected window/threshold mismatches. | Direct normalized-key comparison only; IDs and full definition digests stay separately bound to subjects and samples. No attestation/bridge operation in v0.1. | Use `definition_comparison=normalized-key/0.1`; fixture different IDs with equal keys and same ID with changed semantics. |
| Protocol | The completed 042 kernel has its own versioned JSON Lines protocol and categorized errors; the older 044 oracle is fixture-oriented single JSON. Neither uses the Semadmit envelope or obligation pointers. | Versioned offline request and deterministic decision/error protocol. | Implement the Semadmit transport contract; do not label either existing CLI as v0.1. |
| Numeric profile | Haskell definition parsing retains Scientific values for some fields, while window/sustain and calibration use Double; both calibration implementations use binary floating point. | Bounded canonical decimal strings and exact rational arithmetic; numeric threshold values have an explicit tagged shape. | Adapters map supported legacy numbers through RFC 8785 number serialization and exponent expansion, then validate without rounding. Reject values outside bounds or over 12 fractional digits. Review fixtures must classify every boundary difference. |
| Calibration rules | The completed Haskell kernel uses optional defaults 500/10/0.05, requires both classes, nonzero score variance, and finite AUC; its qualified value records definition ID and sample count. The older oracle requires explicit values and binds sample hashes. | Candidate Semadmit policy requires explicit positive `min_events`, bins 1–1,000, count/ECE thresholds, both outcome classes, and nonzero score variance. | Keep thresholds explicit and bind definition digest, sample digest, and policy digest in Semadmit admission; the Haskell opaque value alone is not that binding. |
| Identities | Python and Haskell sample hashes cover ordered scores/outcomes; calibration evidence separately binds definition ID and digest. | Sample identity includes the definition digest; definition, policy, subject, evidence, request, and decision projections are closed separately. | Verify canonical payload projections, optional-field normalization, threshold set ordering, JCS bytes, and every digest with normative vectors. |
| Admission/use | Opaque authorization binds samples and policy; pooled ECE rehashes values passed to the operation. | Admission retains an immutable validated snapshot consumed by the guarded operation. | Specify the consumer snapshot seam separately; current authorization value is not proof of an external mutable-resource transaction. |
| Reporting | Python `cross_family_report.pooled_ece` is a same-call diagnostic and is not typed authorization; Haskell fixture output reports the authorization projection separately. | A v0.1 decision is the only admission result and returns all stable obligations/diagnostics. | Keep diagnostic report fields outside the admission boundary and hashed decision payload. |
| Domain coverage | Isoprax definition compatibility and calibration/pooling only. | Isoprax pool plus an independent measurement aggregation pack. | Measurement remains new work and must not import Isoprax concepts. |
| Evidence shape | Five shared fixtures; six QuickCheck properties, three compile-fail examples, and conditional hosted CI. | Broader per-obligation/state/boundary fixtures, generators, mutations, parser checks, and release gates. | Reuse relevant evidence as a baseline; it does not satisfy Semadmit's full conformance criteria. |

## Candidate v0.1 Mapping Decisions

The candidate wire contract preserves direct compatibility semantics while closing numeric and normalization behavior that differed across runtimes:

- JSON number tokens are safe integers only. Decimal definition fields use canonical strings; threshold values use a tagged `text` or `decimal` record so the source type distinction remains explicit. Legacy numeric input is converted through its RFC 8785 number spelling and is rejected when it exceeds the bounded profile.
- Isoprax text keys use ASCII-only trimming and lowercasing. Non-ASCII scalar values are preserved exactly, avoiding dependence on different Unicode database versions. This intentionally narrows the completed Haskell kernel's `Text.strip`/`Text.toLower` behavior.
- Definition identity retains the complete validated record and display/raw text while semantic compatibility excludes the documented metadata fields. Missing/null aliases and threshold collection order are canonicalized before identity. Exact projection and ordering rules are in `wire-protocol.md`.
- RFC 8785 object-key ordering uses UTF-16 code units. Evidence IDs and threshold collections use their separately stated collection comparators.

These are candidate choices, not approved equivalence claims. The historical source mapping and M0 review findings remain evidence of the baseline only.

## Reuse Boundary

Treat the Isoprax Haskell oracle and its corresponding Python semantic implementation as candidate, independently authored baselines for the Isoprax domain. Do not recreate their covered semantic operations without first showing a contract or integration gap. Do not claim either implementation already satisfies the v0.1 transport, exact-decimal, snapshot-consumption, measurement, or release requirements.

M0 froze each semantic difference above. Runtime setup after M0 must select a source-integration method and complete license/provenance review plus a reproducible build design. Options such as a source copy, CI checkout at a pinned commit, or a narrow adapter are not selected here. No source code was changed in Isoprax as part of this mapping.
