# Operation-Aware Admission Design Note

**Status:** Design draft. No new wire protocol or universal evidence-combination engine is implemented here.

Semadmit should answer a bounded question: may identified evidence be used for one named operation on one target under one declared context and policy? The result grants no general permission to reuse that evidence for other operations.

## IsoPrax Direction

The public IsoPrax research direction treats measurement validity, calibration, outcome semantics, and supported operations as separate questions. Calibration alone does not show that two predictions describe the same event or support the same operation. Its README also describes outcome definitions that are not commensurable. See the [IsoPrax research mission](https://github.com/AbstractLogix/isoprax#research-mission).

Semadmit should therefore require an operation-specific compatibility rule where an operation needs one. It must keep unknown compatibility distinct from permission. For example, a rule may allow pooling only when outcome definitions and measurement contexts match; passing calibration checks alone must not imply that pooling is allowed.

## Draft Request Shape

This is a schema sketch, not a protocol commitment:

```json
{
  "operation": "pool_predictions",
  "target": {"kind": "hypothesis", "id": "H", "digest": "sha256:..."},
  "evidence": [
    {
      "id": "E",
      "digest": "sha256:...",
      "family": "forecast/0.1",
      "provenance": {"source": "...", "captured_version": "..."},
      "dependence": {"correlation_group": "...", "upstream_dependencies": []}
    }
  ],
  "assumptions": [],
  "context": {"id": "C", "policy": "..."},
  "rule": {"system": "IsoPrax", "id": "...", "version": "...", "digest": "sha256:..."}
}
```

The operation vocabulary starts with `support_claim`, `contradict_claim`, `aggregate_evidence`, `compare_scores`, `pool_predictions`, and `calibration_transfer`. A first implementation should support only operations with a reviewed rule and explicit required fields. The rule reference may be absent when no external rule applies. An absent rule must not be treated as an affirmative rule.

## Draft Result Shape

The result should bind to the full request and preserve the requested operation, target, evidence identities, assumptions, provenance, evidence families, dependence/correlation data, and the applicable rule reference. Its operation outcome should be one of:

- `admissible`;
- `inadmissible`;
- `separate-treatment`;
- `unknown`.

It should include a stable rationale code and any human-readable detail. `unknown` means the rule cannot decide from the supplied declarations. `separate-treatment` means the evidence may remain available for separate handling but must not take part in the requested combined operation. Neither is a positive admission.

If the implementation reports verification, it must use a separate field with a separate vocabulary. Verification of Semadmit's result structure does not establish an evidence-use outcome, and an admissible outcome does not establish truth. An admissibility result says only whether the evidence may participate in the named operation under the declared policy.

## First Bounded Slice

Start with one operation and a small closed rule table. Include cases for matching inputs, mismatched outcome definitions, shared dependence, missing provenance, and unavailable rule versions. Keep evidence identities and the rule digest in the result binding. Add operation-specific conformance vectors before adding another operation. Do not add pooling algorithms or cross-operation reuse as part of this schema work.
