# Selector Provenance and Independent Corroboration

**Status:** Experimental Python pack. It does not change `semadmit/claim/0.1`, `semantic-oracle/0.1`, or the Haskell parity scope.

## Scope

`selector-provenance/0.1` supports one operation: `independent_corroboration`. It asks whether at least two identified evidence items may count as independent corroboration for one claim or hypothesis in one context. It does not retrieve, rank, combine, or score evidence. It does not determine what a caller should believe.

The current rule is conservative. It returns Core state `indeterminate` for all cases because Semadmit has no validated rule that establishes independence. It reports missing provenance or known shared lineage as rationale. It does not reject evidence because two components share a model, and it does not treat different model names as proof of independence.

## Request fields

The request binds the policy, target, evidence, operation, and Core protocol version. The policy includes the Semadmit rule version, context, consumer model, assumptions, and an optional Isoprax rule reference. Each evidence item includes its identity digest, evidence family, source, collector, and selector declaration.

For this operation, `context.id`, `consumer.model_id`, each evidence `id`, `digest`, and `family`, plus each evidence `source.id`, `collector.id`, `selector.id`, and `selector.type` are required to establish complete provenance. If the selector type is `model`, `selector.model_id` is also required. Missing source, collector, or selector declarations are accepted as unknown provenance and produce an `indeterminate` result.

The following selector fields are optional and are normalized into the request binding: selector and model versions, query identity, corpus identity, ranking score, rank, retrieval method, budget, selector-to-consumer relation, and shared upstream dependencies. A ranking score is a canonical decimal string because Core JSON numbers use safe integers only. Rank and budget are positive safe integers when present. Source and collector versions, the consumer version, and consumer upstream dependencies are also optional. Optional metadata may improve traceability; it does not establish admission by itself. An absent Isoprax rule reference means no Isoprax-derived rule applies in this fixture. It does not mean a rule passed.

## Relation vocabulary

The relation vocabulary is provisional:

- `independent`: a declared relation. This version does not accept it as proof.
- `shared_model`: selector and consumer, or two selectors, name a shared model identity.
- `shared_encoder`: provenance declares a shared encoder dependency.
- `shared_training_lineage`: provenance declares shared training lineage.
- `shared_source`: provenance declares a shared source or corpus.
- `unknown`: provenance does not identify the relation; the result reports `dependence.unknown`.

Semadmit reports these as possible dependence metadata. It does not convert them into a statistical correlation estimate. Matching corpus identities report `shared_source`. If some provenance is missing, the result also reports any shared relation that can still be read from the supplied fields. A shared model is preserved as a relation and returns `indeterminate`; it is not an automatic rejection.

## Bounded cases

The conformance fixture in [`selector-independence-cases.json`](../conformance/fixtures/selector-independence-cases.json) covers:

| Case | Recorded relation | Result |
| --- | --- | --- |
| BM25 selectors, Model X consumer | No validated independence rule | `indeterminate` |
| Model X selector and Model X consumer | `shared_model` | `indeterminate` |
| Model X selector and Model Y consumer | Different names do not establish independence | `indeterminate` |
| Two selectors share a model and corpus | `shared_model`, `shared_source` | `indeterminate` |

A high ranking score does not affect the result state. It remains part of normalized evidence and therefore changes its Core evidence digest and request digest when changed.

## Result and verification

The operation record is the request and its Core decision together. The Core decision carries the operation, target/evidence identity bindings, request digest, decision digest, state, and rationale codes. The request carries normalized provenance, assumptions, evidence family, and any Isoprax rule reference. Callers must retain both; the decision alone does not reproduce the full provenance declaration.

`Evaluator.verify_result(request, result)` verifies a Core decision by deterministic reevaluation. `ClaimEngine.verify_result` remains the verifier for the separate claim-result wrapper. Verification confirms result integrity; it does not convert an indeterminate or admissible result into truth.

The new pack is Python-only. The Haskell implementation remains an independent reference for Core and the existing selected parity semantics. This pack makes no cross-language parity claim.
