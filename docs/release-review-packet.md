# Independent Release Review Packet

**Implementation baseline SHA:** `46b81c7d1429dc645efafdafcfac35b584ef38b9`.

**Exact test source SHA:** `03751e4a3a234c00360c9e6ddf36b6f742b0e3b3`.

The baseline is the exact merged Semadmit source used for fresh validation. The test source SHA adds regression assertions. The remaining PR changes are evidence documents. No assurance change alters runtime semantics or the frozen claim contract. Review the PR diff as well as these exact source commits.

## Review Scope

Review Semadmit's claim result boundary, generic Core behavior, package contents, and evidence. Do not infer a Bouleusis integration result from the compatibility fixture. Do not treat this packet or automated review as human independent approval.

Read these files in order:

1. [Claim admission specification](../specs/002-structured-claim-admission/spec.md)
2. [Core wire contract](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md)
3. [Trust boundary review](trust-boundary-review.md)
4. [Bouleusis compatibility record](bouleusis-compatibility.md)
5. [Machine-readable compatibility matrix](../conformance/fixtures/claim-consumer-compatibility-matrix.json)
6. [Release assurance and remaining gates](release-assurance.md)
7. [Dependency and license inventory](dependency-license-inventory.md)

## Threat Model

An untrusted caller may provide a malformed request or a candidate result whose claim, evidence, policy, operation, components, status, or digests were changed. The verifier must reject a candidate that does not match a fresh evaluation for the supplied request. JSONL input must reject ambiguous or out-of-profile JSON. Missing provenance or unknown dependence must not create an independence decision.

The boundary does not authenticate sources or collectors. It does not measure evidence reliability. It does not establish claim truth. It does not bind a result to an immutable executable. Those limits must remain visible.

## Frozen Contract and Invariants

- Claim request protocol: `semadmit/claim/0.1`.
- Core request and decision protocol: `semantic-oracle/0.1`.
- Consumer contract label: `semadmit/claim-result-consumer/0.1`.
- Minimum reviewed compatibility pin: `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`.
- Verification status and admission status are separate values.
- `VALID` maps to `ADMISSIBLE`; `INVALID` maps to `INADMISSIBLE`; `UNKNOWN` maps to `REQUIRES_SEPARATE_TREATMENT` and Core `indeterminate`.
- Admission permits evidence to participate only in the named operation under the declared policy. It does not say what a consumer must believe.
- Digests bind supplied content to an identity declaration. They do not authenticate a source.
- `selector-provenance/0.1` is a separate experimental Python pack. It remains `indeterminate` for its four bounded independence cases. No positive independence rule is supported by the current IsoPrax evidence.

## Validation Commands

Run from a clean checkout at the source SHA above, with CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, and uv 0.11.31:

```sh
python3 scripts/check_coverage.py
cabal build exe:semantic-oracle
cabal sdist --output-directory=/tmp/semadmit-review-haskell
uv build --out-dir /tmp/semadmit-review-python clients/python
jq -c '.cases[] | select(.id == "admissible-ece-equality") | .request' \
  conformance/fixtures/isoprax-cases.json \
  | cabal run exe:semantic-oracle --
```

The coverage command checks the pinned Python/GHC/Cabal versions, 58 Python tests, all 7 Haskell suites, and the coverage floors. The exact results and artifact hashes are in the [release assurance record](release-assurance.md). The compatibility fixture tests the Semadmit verifier; it is not a downstream integration test.

## Known Limits and Open Defects

- Verification uses the implementation available in the caller's process. There is no immutable implementation or build identity in the claim result.
- The claim verifier returns a boolean. There is no claim-specific checked-use capability.
- The shared exact-output corpus covers nine Core cases. It does not cover every parser error, error pointer, resource limit, or CLI frame across languages.
- Claim and selector packs do not have Haskell parity. Measurement is not qualified.
- Two clean Python wheels matched. Two clean Python source archives did not; generated timestamps differ.
- The dependency inventory records the lock and Hackage index state but has no per-archive hashes or retrieval manifest.
- `ghc-prim` and `rts` have license identifiers in the GHC package database, but their source license and notice files were not audited.
- Only Linux x86_64 under WSL2 with the pinned toolchain was tested. Other operating systems, architectures, and Python minor versions are unqualified.
- Branch protection is unknown because GitHub returned HTTP 403 to the private repository protection query.
- A separate human reviewer has not approved the implementation, package, and license evidence. This gate remains open.

## Reviewer Checklist

- [ ] Confirm result verification rejects the changed request and candidate cases.
- [ ] Confirm canonical JSON comparison preserves strict JSON type distinctions.
- [ ] Confirm supported status pairs remain separate from belief or truth.
- [ ] Confirm the Core parity claim is limited to the nine committed vectors.
- [ ] Confirm selector metadata and relevance scores do not grant independence.
- [ ] Confirm package files include the project license and do not overstate dependency notice coverage.
- [ ] Review the sdist reproducibility failure and the two compiler-only license entries.
- [ ] Record findings against the exact source SHA and the PR head.
- [ ] Do not approve release until the open gates are closed or explicitly accepted by the owner.
