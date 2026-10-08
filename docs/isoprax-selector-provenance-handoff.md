# Isoprax Handoff: Selector Dependence and Operation Rules

Semadmit records selector, collector, source, consumer, and shared-lineage declarations. Its current `selector-independence/0.1` rule returns `indeterminate` for the four bounded cases. It does not infer a correlation result from model identity, corpus identity, selector score, or different component names.

Please research whether shared selector/consumer or upstream lineage is material to each named operation, and identify the evidence and assumptions that support any rule. In particular, distinguish a shared-model relation from measured error dependence. Test support use and independent corroboration separately; do not imply that a result for one operation transfers to pooling, score comparison, or calibration transfer.

The cited UNREAL paper describes model-native evidence selection and reports retrieval scores. It does not establish selector-consumer error independence or dependence for Semadmit's operations. See [arXiv:2610.08463v1](https://arxiv.org/abs/2610.08463v1).

Any proposed executable rule should name its operation, target/context assumptions, evidence family, dependence relation, rationale, rule version, and evidence digest. Until that work establishes a bounded rule, Semadmit preserves the relation and returns `indeterminate`.
