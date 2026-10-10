# Independent Release Review Packet

**Current PR:** [#12 — Bind assurance artifacts to source](https://github.com/AbstractLogix/semadmit/pull/12).

**Certificate source and validation commit:**
`765228bc00d7f782f80c88cdc2e452b61db8771e`.

**Source tree:** `2070b36ad2d43923b996621e4fd7f500bf0a897d`.

**Hosted Coverage run:** [38025681059](https://github.com/AbstractLogix/semadmit/actions/runs/38025681059), passed for the exact source commit above. The CI identity in the certificate remains unauthenticated.

Review the full PR #12 diff and the machine-readable certificate. This packet
is not human approval. The certificate is bound to source commit `765228b…`;
later documentation or certificate-record commits do not replace that build
source.

This packet also covers the independent Core assurance extension. Its exact
implementation commit, corpus digests, local build hashes, and CI evidence are
recorded in [`assurance-certificate.json`](../assurance/assurance-certificate.json).
That certificate identifies the source commit for the new assurance artifact.

## Current Final Assurance Assessment

The current artifact assurance uses certificate format
`semadmit-assurance-certificate/0.2`. Its exact source revision, Git tree,
locked inputs, toolchain, validation results, CI run record, and artifact
hashes are in [`assurance-certificate.json`](../assurance/assurance-certificate.json).
The [artifact provenance record](artifact-provenance-and-offline-verification.md)
defines the trust model and reproduction command. The verifier rebuilds the
artifacts from the externally supplied source revision and rejects mismatched
bytes or results. An actual end-to-end run rejected a Python wheel after
arbitrary bytes were appended while preserving its filename. The verifier
shares build code with the writer, and the CI identity remains unauthenticated.

## Current Artifact Digests

Two clean-source builds on the recorded Linux x86_64 WSL2 host matched byte for
byte. The toolchain is CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, uv 0.11.31,
and Bubblewrap 0.6.1.

| Artifact | SHA-256 |
| --- | --- |
| Haskell executable | `08a314a7dddd3ed49018740f3d5ac6edda80b97deea10d5e449854f521c2b700` |
| Haskell source archive | `f8b7307e484d0be76f854a598c0c7c1f69652d21cd04aaf00652e48f328b38f4` |
| Python wheel | `9a76d49c81713d1feb50c1dd91aa384e416ad305da1a0b3e62b71e8cce5742cf` |
| Python source archive | `0fcdd0fbe0cb30c25f2df6afc25da75e21360643f424a721ab9e938feae84612` |

The actual offline verifier passed for the four recorded artifacts. Its
reproduction command is in the [provenance record](artifact-provenance-and-offline-verification.md).
Negative tests cover replay, truncation, missing artifacts, changed source
identity, altered results, and invalid provenance. The real CLI substitution
test changed the Python wheel bytes and was rejected after rebuild. The packet
records the exact command and output; the substitution run is manual, while
committed negative tests exercise record validation with fixtures.

The stable Bouleusis pin remains
`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. The `semadmit/claim/0.1`
qualification stays Python-only, and `selector-provenance/0.1` stays
experimental. Core parity remains partial. Python is ready for owner review;
Haskell distribution remains blocked on notice and dependency provenance
review. Independent release approval is absent.

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
- Core parity is limited to 57 shared decision vectors, 9 M0 identity vectors,
  the selected RFC 8785 property-order vector, and 68 raw parser cases,
  including 65 error envelopes.
  The independent Python oracle supports only test-only
  `fixture/0.1/check`. Other parser recipes and full CLI framing remain partial.
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

Certificate format 0.2 records a clean-source rebuild, not a signed
attestation. The writer builds artifacts from a full Git commit in a fresh
temporary source tree. The offline verifier repeats the build, checks source
identity and lock inputs, reruns the gates, and compares structure, file mode,
size, and bytes. The CI run is recorded as `recorded-unverified`; offline
verification cannot authenticate the run or the worker. The verifier does not
prove scientific validity, general functional correctness, or claim truth.

The independent Core reference does not use the production evaluator to
compute expected results. The Haskell implementation consumes committed
expected outputs from that reference; this qualifies only the listed shared
vectors. The oracle does not implement claim semantics or authenticate source
evidence.

## Positive and Negative Conformance Evidence

The shared Core decision cases include:

- Positive: `admissible` and `pass-with-missing`.
- Negative: `inadmissible` and `failure-dominates-missing`.
- Unknown: `indeterminate`.
- Identity, binding, and error cases: `duplicate-evidence`,
  `unsupported-protocol`, `policy-digest-mismatch`, and `unexpected-field`.

Both language suites compare complete Core decisions and error results with
the same expected vectors. The Haskell and Python identity suites consume the
same M0 canonical byte and digest vectors. The parser suites consume the same
68 raw cases, including 65 errors. They compare the full output. The selected
source mutations killed all 7 Python Core mutants; this does not establish
Haskell mutation coverage. The test record and limits are in
[independent-assurance.md](independent-assurance.md) and
[release-assurance.md](release-assurance.md).

Claim-verification tests reject changed requests, claim and evidence identity
substitution, result-envelope changes, status changes, artifact/Core binding
changes, and decision or verification digest changes. These tests are
Python-only because Haskell does not implement the claim semantics.

## Reproduction Commands

Use Linux x86_64, CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, and uv 0.11.31.
Run from a clean checkout of the independent Core assurance implementation
commit above.

```bash
set -euo pipefail
scratch="$(mktemp -d /tmp/semadmit-review-build.XXXXXX)"
mkdir -p "$scratch/haskell" "$scratch/python"
python3 scripts/check_coverage.py
python3 -m assurance.generate_corpus --check
python3 -m assurance.mutation_check
PYTHONPATH=clients/python:clients/python/tests python3 -m unittest assurance.test_certificate -v
cabal build exe:semantic-oracle
cabal sdist --output-directory="$scratch/haskell"
uv build --out-dir "$scratch/python" clients/python
printf 'Build artifacts: %s\n' "$scratch"
```

To rebuild and compare the normalized Python source archives from two clean
copies of the exact source commit:

```bash
set -euo pipefail
source_sha=47d55e1e7fa10348d4a39679add3590edfe8233b
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

Two clean builds of source commit `47d55e1e7fa10348d4a39679add3590edfe8233b`
produced byte-identical normalized archives with SHA-256
`43c0fecf441ab49e2edf3e639825c14b037eab301898395c2cf84f4e3d205c9d`.
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
  license copy or `NOTICE` file was found under `rts`. The assessed native
  Linux executable does not contain the JavaScript file. The full notice bundle
  for linked Haskell libraries and the runtime is not approved.
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
- [ ] Inspect the independent reference, fixed-seed corpora, and seven-mutation
  scope. Confirm the reference does not import production identity or evaluator
  code and both language suites consume the same expected data.
- [ ] Confirm selector metadata does not grant independence and the outcomes
  remain `indeterminate`.
- [ ] Review the exact hashes, lock metadata, GHC signatures, and whether a
  proposed artifact includes the Closure JavaScript work from `rts`.
- [ ] Confirm no Haskell binary release proceeds without a complete approved
  notice bundle.
- [ ] Review snapshot binding, guarded consumption, Measurement, and the
  incomplete parser/CLI cross-language cases as open gates.
- [ ] Review the [artifact provenance and offline verification record](artifact-provenance-and-offline-verification.md),
  including exact artifacts, tested substitution, replay, truncation,
  result-tampering, and provenance cases.
- [ ] Record findings against the exact implementation commit in
  `assurance/assurance-certificate.json` and the pull request.
- [ ] Obtain independent human approval before any release decision.

**Independent reviewer status: not obtained.** The release gate remains open.
