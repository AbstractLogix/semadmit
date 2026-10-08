# Semadmit Context

This glossary defines the evidence-provenance terms used at Semadmit's admission boundary.

## Evidence provenance

**Evidence source**:
The origin that produced an evidence artifact or the record it describes.
_Avoid_: Selector, collector

**Collector**:
A process or system that obtains and records an evidence artifact from a source.
_Avoid_: Source, interpreter

**Selector**:
A component that chooses candidate evidence from a corpus for a query or task.
_Avoid_: Collector, relevance judge

**Consumer**:
The operation-specific component that receives evidence for interpretation or use.
_Avoid_: Selector, admission policy

**Evidence family**:
A versioned type that identifies the declared structure and meaning of an evidence item.
_Avoid_: Evidence source

**Relevance score**:
A selector's ranking value for a candidate under a query.
_Avoid_: Verification score, truth score

**Upstream dependency**:
A declared source, model, encoder, or training lineage shared by provenance components.
_Avoid_: Correlation measurement

**Dependence relation**:
A declared or structurally observed relation that may matter to a named evidence-use operation.
It does not, by itself, measure error correlation or determine truth.
_Avoid_: Independence result

**Operation-specific admissibility**:
Whether identified evidence may participate in one named operation for one target, context, and policy.
_Avoid_: Truth decision, general evidence approval
