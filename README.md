# Semadmit

**Semadmit — A deterministic, verifiable evidence-admission engine for software agents and research systems.**

Semadmit checks whether identified evidence may take part in one named operation under a declared policy. It binds the request, policy, evidence identities, obligations, and result. A caller can verify the returned result against the original request.

An **evidence obligation** is a policy requirement for an operation. The request names the operation and policy. The registered pack defines the required checks. Each obligation has a recorded outcome. Missing or incomplete evidence stays visible in the result.

Semadmit returns one of three admission outcomes:

- `admissible`: evidence may take part in the requested operation under the policy.
- `inadmissible`: the evidence fails a required check.
- `indeterminate`: the request does not support a decision. The caller must treat it separately.

Admission is not a truth judgment. It does not prove that a claim is true, that an evidence source is authentic, or that two sources are independent. The consumer remains responsible for interpretation and belief.

## Quickstart

Use Python 3.13. This example uses only the checked-out source and the Python standard library. It does not execute the described function. It checks a small, declared observation set.

The request, digest, and observations are synthetic examples. They do not describe a real build or establish a claim about real software.

From the repository root, run:

```sh
PYTHONPATH=clients/python python3 examples/claim_quickstart.py
```

The example prints valid, invalid, and indeterminate decisions. It also changes a result and shows that Semadmit rejects the changed result during verification.

## Verify results

Use the Semadmit verifier with the same request that produced the result:

```python
from semadmit import ClaimEngine

engine = ClaimEngine()
result = engine.evaluate(request)
if not engine.verify_result(request, result):
    raise ValueError("Semadmit result verification failed")
```

`verify_result` recomputes the deterministic result and checks its request binding, identities, digests, Core binding, supported status pair, and protocol version. It does not authenticate evidence or prove the evidence is correct.

Named operations and policies bind to their inputs through the versioned protocol. The result records the operation, policy, request identity, obligations, and decision digest. A different request or policy produces a different binding.

## Current support

- **Python:** `semadmit/claim/0.1` and its result-verification boundary are qualified within the declared finite-invariant scope. Claim semantics are Python-only. The `selector-provenance/0.1` pack is experimental and does not grant independent-corroboration admission.
- **Haskell:** the `semantic-oracle/0.1` Core library and command-line interface support selected Core semantics and the Isoprax calibration and prediction-pooling packs. Haskell does not implement the claim pack. Claim-pack parity is not claimed.
- **Platforms:** the maintained toolchain is CPython 3.13, GHC 9.14.1, and Cabal 3.18.1.0 on Linux x86_64. Other platforms and compiled-artifact guarantees are not qualified.

The Core and claim protocols are stable only within these declared scopes. The selector-provenance pack is experimental.

These are bounded implementation claims. Tests do not establish general correctness, scientific validity, evidence authenticity, or claim truth. See the assurance records for the tested scope and known limits.

## Protocols and assurance

- [Core protocol and specification](specs/001-semantic-oracle-v0-1/spec.md)
- [Core wire protocol](specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md)
- [Claim protocol](specs/002-structured-claim-admission/spec.md)
- [Claim verification guide](specs/002-structured-claim-admission/quickstart.md)
- [Release readiness and limits](docs/release-readiness.md)
- [Artifact provenance and offline verification](docs/artifact-provenance-and-offline-verification.md)
- [Public-source readiness audit](docs/public-source-readiness.md)
- [Apache-2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html)

The stable Bouleusis compatibility pin remains `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. This documentation does not ask a consumer to change its pin.

## Development

Run the maintained local test and coverage gate:

```sh
python3 scripts/check_coverage.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing a protocol or adding a conformance vector. See [SECURITY.md](SECURITY.md) to report a security issue.

Semadmit source is licensed under [Apache-2.0](LICENSE). Third-party material keeps its own license; see [third-party notices](THIRD-PARTY-NOTICES.md).
