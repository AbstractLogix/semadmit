# Independent Release Review Packet

**Exact implementation and validation commit:**
`cad6943ce19bc4b0439cd85332ed632ee17f3a9f`.

**Latest merged Semadmit baseline:**
`b4e1f85ccc8bc56de8f4b12529cfc4e110ee21c7`.

The implementation commit contains the assurance corrections and tests. The
release assurance documents in the pull request record results from that exact
commit. Review the implementation commit and the full pull request diff. This
packet is not human approval.

## Review Scope

Review Semadmit's `semadmit/claim/0.1` result boundary, bounded Core parity,
archive provenance, package contents, and reproducible Python source archive
procedure. Do not infer a Bouleusis integration run from the compatibility
fixture. Do not treat automated checks as independent release approval.

Read these files:

1. [Claim admission specification](../specs/002-structured-claim-admission/spec.md)
2. [Core wire contract](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md)
3. [Trust boundary review](trust-boundary-review.md)
4. [Bouleusis compatibility record](bouleusis-compatibility.md)
5. [Claim compatibility matrix](../conformance/fixtures/claim-consumer-compatibility-matrix.json)
6. [Release assurance and open gates](release-assurance.md)
7. [Dependency license inventory](dependency-license-inventory.md)
8. [Per-artifact provenance data](dependency-provenance.json)

## Supported Contract and Scope

- Claim request protocol: `semadmit/claim/0.1`.
- Core request and decision protocol: `semantic-oracle/0.1`.
- Consumer contract label: `semadmit/claim-result-consumer/0.1`.
- Stable Bouleusis pin: `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`.
- Claim semantics are implemented and tested in Python only. Haskell does not
  implement the claim pack, so no claim-pack parity is asserted.
- Core parity is limited to the 9 shared decision vectors, 9 M0 identity
  vectors, the selected RFC 8785 property-order vector, and the 8 raw parser
  error cases. Other parser recipes and full CLI framing remain partial.
- `selector-provenance/0.1` is experimental and Python-only. Its four bounded
  independence cases remain `indeterminate`. No positive independence rule is
  supported by current IsoPrax evidence.
- `VerificationStatus` and `AdmissionStatus` are separate. Admission says only
  whether evidence may take part in a named operation under a declared policy.
  It does not say what Bouleusis must believe.

## Threat Model

An untrusted caller may submit malformed JSON or a candidate result whose
request, claim, evidence, policy, operation, bindings, status, or digests have
changed. The Semadmit verifier recomputes the result for the supplied request
and rejects a candidate that does not match.

The boundary does not authenticate evidence sources or collectors. A digest
binds content to an identity declaration; it does not prove where the content
came from. The verifier does not prove claim truth or evidence reliability. It
uses the implementation available in the caller's process and does not bind
the result to an immutable executable. The in-memory API cannot detect
duplicate JSON keys after a caller has parsed and discarded them.

## Positive and Negative Conformance Evidence

The shared Core decision cases include:

- Positive: `admissible` and `pass-with-missing`.
- Negative: `inadmissible` and `failure-dominates-missing`.
- Unknown: `indeterminate`.
- Identity, binding, and error cases: `duplicate-evidence`,
  `unsupported-protocol`, `policy-digest-mismatch`, and `unexpected-field`.

Both language suites compare complete Core decisions and error results with
the same expected vectors. The Haskell and Python identity suites consume the
same M0 canonical byte and digest vectors. The parser suites now consume the
same eight raw error cases and compare the full error object. The full test
record and known limits are in [release-assurance.md](release-assurance.md).

Claim-verification tests reject changed requests, claim and evidence identity
substitution, result-envelope changes, status changes, artifact/Core binding
changes, and decision or verification digest changes. These tests are
Python-only because Haskell does not implement the claim semantics.

## Reproduction Commands

Use Linux x86_64, CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, and uv 0.11.31.
Run from a clean checkout of the exact implementation commit above.

```bash
set -euo pipefail
scratch="$(mktemp -d /tmp/semadmit-review-build.XXXXXX)"
mkdir -p "$scratch/haskell" "$scratch/python"
python3 scripts/check_coverage.py
cabal build exe:semantic-oracle
cabal sdist --output-directory="$scratch/haskell"
uv build --out-dir "$scratch/python" clients/python
printf 'Build artifacts: %s\n' "$scratch"
```

To rebuild and compare the normalized Python source archives from two clean
copies of the exact source commit:

```bash
set -euo pipefail
source_sha=cad6943ce19bc4b0439cd85332ed632ee17f3a9f
source_epoch="$(git show -s --format=%ct "$source_sha")"
repository_root="$(git rev-parse --show-toplevel)"
scratch="$(mktemp -d /tmp/semadmit-source-repro.XXXXXX)"
mkdir -p "$scratch/source-a" "$scratch/source-b" "$scratch/build-a" "$scratch/build-b"
git archive "$source_sha" | tar -x -C "$scratch/source-a"
git archive "$source_sha" | tar -x -C "$scratch/source-b"
(cd "$scratch/source-a" && SOURCE_DATE_EPOCH="$source_epoch" uv build --out-dir "$scratch/build-a" clients/python)
(cd "$scratch/source-b" && SOURCE_DATE_EPOCH="$source_epoch" uv build --out-dir "$scratch/build-b" clients/python)
SOURCE_DATE_EPOCH="$source_epoch" python3 "$repository_root/scripts/normalize_python_sdist.py" "$scratch/build-a/semadmit-0.1.0.dev0.tar.gz" "$scratch/build-a/normalized.tar.gz"
SOURCE_DATE_EPOCH="$source_epoch" python3 "$repository_root/scripts/normalize_python_sdist.py" "$scratch/build-b/semadmit-0.1.0.dev0.tar.gz" "$scratch/build-b/normalized.tar.gz"
sha256sum "$scratch/build-a/normalized.tar.gz" "$scratch/build-b/normalized.tar.gz"
cmp "$scratch/build-a/normalized.tar.gz" "$scratch/build-b/normalized.tar.gz"
```

The recorded normalized archive SHA-256 is
`940ed9931fbcbfbdeaf0a05b374af7a0226662635dcff69ddda1567d8701b13c`.
The dependency archive URLs and hashes are in
[dependency-provenance.json](dependency-provenance.json).

## Dependency and Build Findings

- All 69 Hackage dependency archives match the target hash and size recorded in
  the current Cabal-managed index cache. All declared license files are
  present; no separate `NOTICE` file was found in those 69 archives.
- `base-4.22.0.0`, `colour-2.3.7`, and `strict-0.5.1` do not declare a source
  repository in their package descriptions.
- The verified GHC 9.14.1 source archive supplies `ghc-prim-0.13.1` and
  `rts-1.0.3`. `rts` contains inline xxHash terms, LLVM license text, and the
  generated `configure` script's Free Software Foundation permission notice.
  Closure Library code has an Apache-2.0 header, but no separate Apache
  license copy or `NOTICE` file was found under `rts`; a future Haskell binary
  notice bundle is not approved.
- The two raw Python source archives differed in PAX fractional timestamps on
  generated directories and metadata files. All member contents matched. The
  normalizer made both archives byte-identical without changing package files
  or licensing metadata. The wheels also matched byte for byte.
- No Semadmit package has been published. The Python wheel and source archive
  contain Semadmit's Apache-2.0 license. The Haskell source archive does not
  bundle its dependencies.

## Open Review Checklist

- [ ] Confirm claim result verification and status separation match the frozen
  contracts.
- [ ] Confirm the Core parity statement names only semantics and vectors both
  implementations test.
- [ ] Confirm selector metadata does not grant independence and the outcomes
  remain `indeterminate`.
- [ ] Review the exact hashes, lock metadata, GHC signatures, and missing
  `rts` Apache license copy.
- [ ] Confirm no Haskell binary release proceeds without a complete approved
  notice bundle.
- [ ] Review snapshot binding, guarded consumption, Measurement, and the
  incomplete parser/CLI cross-language cases as open gates.
- [ ] Record findings against implementation commit
  `cad6943ce19bc4b0439cd85332ed632ee17f3a9f` and the pull request.
- [ ] Obtain independent human approval before any release decision.

**Independent reviewer status: not obtained.** The release gate remains open.
