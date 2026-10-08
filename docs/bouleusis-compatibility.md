# Bouleusis Compatibility

This note freezes the Semadmit claim and Core interfaces for consumers. It does not describe or depend on Bouleusis internals.

## Pin

The exact merged Semadmit commit recorded for this compatibility baseline is:

`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`

The machine-readable record is [bouleusis-compatibility.json](../conformance/fixtures/bouleusis-compatibility.json). It identifies the latest merged `main` commit when this record was created. A later Semadmit change needs a new reviewed pin record before a consumer moves to it.

## Frozen Protocols

The claim request protocol is `semadmit/claim/0.1`. This version accepts the existing closed request shape: `protocol`, `policy`, `claim`, `context`, and `evidence`. This compatibility work does not change that shape or the claim-result wrapper.

The generic Core protocol remains `semantic-oracle/0.1`. A successful Core decision has exactly these outer fields:

- `kind`, with value `decision`;
- `payload`;
- `decision_digest`.

The payload has exactly `protocol`, `pack`, `operation`, `request_digest`, `policy_digest`, `state`, `bindings`, `obligations`, and `diagnostics`. Its state is `admissible`, `inadmissible`, or `indeterminate`. The digest covers the canonical payload only. A Core protocol change requires a new version under the existing Core contract.

A protocol error has exactly `kind`, `code`, and `pointer`. `kind` is `error`; `pointer` is always present and uses RFC 6901 syntax. The empty pointer denotes the whole request. Error codes and pointer rules remain those in the [Core wire protocol](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md#protocol-error-envelope).

The claim-result wrapper has exactly these fields: `kind`, `protocol`, `result_id`, `claim_id`, `evidence_ids`, `verification_status`, `admission_status`, `verification_digest`, `verification`, and `core_decision`. The result ID equals the Core decision digest. The verification artifact digest equals its Core component binding. The claim ID and evidence IDs bind to the request.

The compatibility label `semadmit/claim-result-consumer/0.1` describes the Semadmit-side consumer contract: keep the request protocol pinned, verify the result against that request with `ClaimEngine.verify_result`, keep verification and admission statuses separate, and treat admission only as permission for the named operation under the declared policy. This label does not claim that Bouleusis has implemented or tested a particular integration.

## Result Verification

Use the Semadmit-owned Python boundary:

```python
from semadmit import ClaimEngine

engine = ClaimEngine()
result = engine.evaluate(request)
if not engine.verify_result(request, result):
    raise ValueError("Semadmit result verification failed")
```

`verify_result` recomputes the result from the supplied request and compares the canonical JSON bytes. It checks request/result binding, claim and evidence identities, the verification artifact digest, the Core decision digest and bindings, the supported status pair, and the protocol. It returns `False` for malformed candidates and for any mismatch. Callers do not need to reproduce Semadmit canonicalization rules.

`VerificationStatus` and `AdmissionStatus` remain separate values. The supported pairs are:

| Verification | Admission | Core state |
| --- | --- | --- |
| `VALID` | `ADMISSIBLE` | `admissible` |
| `INVALID` | `INADMISSIBLE` | `inadmissible` |
| `UNKNOWN` | `REQUIRES_SEPARATE_TREATMENT` | `indeterminate` |

Admission states whether evidence may take part in the operation under the declared policy. It does not tell a consumer what to believe. Verification checks Semadmit's deterministic result structure and bindings. It does not authenticate evidence sources, provenance declarations, or collectors.

The compatibility fixture records `Result verification: PASS` for the `complete-valid` normative claim fixture. The automated Semadmit test evaluates the fixture and calls this verification boundary. This is a Semadmit conformance result. It does not claim an independent Bouleusis integration run.
