# Final Assurance Integrity and Distribution Assessment

**Assessment baseline:** PR #10 merge `e042aded9fd98d22aeb708337a26e9bbc9f2b7b8`.
Its tree is `c84d326ab07eacec88786df12081cf6442175982`.
The assurance-integrity implementation commit is
`dcf3d1070186a3f936e17f5975622023c812fc2b`. The refreshed certificate records
that validation commit and the successful
[hosted Coverage run](https://github.com/AbstractLogix/semadmit/actions/runs/38000152994).

The stable Bouleusis compatibility pin remains
`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. `semadmit/claim/0.1` remains
qualified in Python only. `selector-provenance/0.1` remains experimental. No
admission rule or positive independence result changed.

## Adversarial Certificate Results

The certificate writer now requires a completed successful Coverage workflow
with the expected GitHub workflow ID and the exact validation commit. It
records each mandatory local gate's output, byte count, and SHA-256. It rejects
empty logs, truncated corpus or coverage output, incomplete mutation output,
fabricated Python test counts, and nonzero gate exits. The coverage command
also runs the certificate-integrity tests.

| Adversarial case | Result | Evidence and limit |
| --- | --- | --- |
| Missing local execution output | Rejected | A successful command with empty output fails. A written certificate includes non-empty gate output and its byte count and digest. |
| Fabricated Python test counts | Rejected | The three reported counts must match test cases discovered from the checked-out source. A count one higher than discovery fails. |
| Truncated output | Rejected in tested cases | Corpus output must match its complete success line. Coverage output must end with its success marker and contain all three test summaries. Mutation output must list every configured mutant and the full score. |
| Nonzero test or gate exit | Rejected | Any nonzero local gate exit stops certificate generation. |
| Incorrect validation commit | Rejected during generation | The requested commit must equal `HEAD`; the checkout must be clean; and the implementation commit must be its ancestor. |
| Stale CI on another commit | Rejected | The run's head SHA and URL must match the requested validation commit and URL. |
| Wrong or unrelated CI workflow | Rejected | The run must be `Coverage` with workflow database ID `375788046`. The ID must be updated if the repository replaces that workflow. |
| Pending or failed CI | Rejected | The run must be completed with conclusion `success`. Missing CI evidence also fails. |
| Incorrect mutation result | Rejected | Missing or reordered mutation kills and an incomplete score fail. The selected set remains seven Python mutations; no Haskell mutations were run. |
| Skipped mandatory local gate | Rejected by the tested path | The writer records and checks the three required gates: seeded corpus, source mutation, and test/coverage. |
| Mismatched or unrelated build artifacts | **Not prevented** | An adversarial run supplied four non-empty text files as the build artifacts. The writer exited `0` and recorded their hashes. The hashes identify bytes; they do not prove that those bytes came from the validation source. |
| Reused certificate from another revision | **No offline check** | New generation rejects a wrong validation commit. The repository has no certificate-verification command to reject a copied old certificate against a caller's expected revision or artifacts. The certificate is not signed. |

The new failure checks pass in the tested cases. Certificate integrity is still
blocked because artifact-to-source binding and offline certificate reuse are
not checked. Do not treat the certificate as a signed build attestation.

## Core Parity Gaps, in Priority Order

The current shared corpus checks 57 complete Core results, 9 M0 identity
vectors, one selected RFC 8785 property-order vector, and 68 raw parser cases
(65 error envelopes). These results qualify only the named cases.

1. **Parser precedence.** Add a small set of inputs with two independent
   defects, such as an invalid number plus trailing data or a duplicate key
   before an invalid member. Compare the first error code and pointer. This is
   the most direct way to reveal different validation order.
2. **Resource boundaries.** The Core limits are 10 MiB per request, depth 64,
   and 256 evidence items. Compare below, at, and above each limit. Compare
   exact error pointers and behavior for raw bytes and direct-object input.
3. **CLI framing.** Compare JSONL behavior for blank lines, CRLF, a final line
   without a newline, malformed records followed by valid records, and an
   over-limit line followed by another record. Compare every output line,
   standard error, and exit status.
4. **Cross-language errors.** Extend exact-envelope cases only where they test
   uncovered precedence, pointer, or framing behavior. Number profile,
   Unicode, duplicate keys, and the current error set already have named
   vectors; do not duplicate them for count.

Canonical identity, digest equality, component binding, and state reduction
already have shared vectors. Claim verification remains Python-only. The
independent oracle implements only test-only `fixture/0.1/check`. It does not
provide Haskell claim-pack parity.

## Python Distribution Assessment

**Status: ready for an owner decision; not approved or published.**

- **Exact source input:** commit `e042aded9fd98d22aeb708337a26e9bbc9f2b7b8`,
  tree `c84d326ab07eacec88786df12081cf6442175982`, Python subtree
  `7cc3ada3e5adfc62ad2c1fb4c420eb3a9c345a03`.
- **Build inputs:** CPython 3.13.14, uv 0.11.31, setuptools 84.0.0. The
  `pyproject.toml` SHA-256 is
  `953e3fac5f9ad27e250948432db4d5b7e7b0f6da885b8d70aea3d5f6c510e83f`.
  Setuptools is a build-only input, not a runtime dependency and not part of
  the Semadmit artifacts. Its source is [setuptools on GitHub](https://github.com/pypa/setuptools),
  and its wheel hash is
  `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670`.
- **Clean artifact builds:** two clean source trees, with
  `SOURCE_DATE_EPOCH=1791569362` (the PR #10 merge commit time), produced the
  same wheel SHA-256
  `d93f079d885674ccef9aa482d628675a90387749d7380559d0aa82dbec286740`
  (29,770 bytes). The wheel contains nine modules and the Apache-2.0 license.
  Its metadata says `License-Expression: Apache-2.0` and `License-File: LICENSE`.
- **Source archive:** the two raw builds differ. Their hashes are
  `db2a5fba968e2552bcd09e20034975ae482748022a1f1080c7590de0a22606aa` and
  `e5601384efe1ce417a6041fa643a79548a381a35181db2c2d0247dfe7996d89c`.
  All 32 member names and file bytes match. Ten generated directory or
  metadata entries have different PAX fractional `mtime` values. The gzip
  timestamp matches. `scripts/normalize_python_sdist.py` produces identical
  37,279-byte archives with SHA-256
  `1f7c06e3e96b6e9fc769e6c97fb9ebf380e81c6875fff8b719d18de7d7093bfa`.
  The normalizer changes archive metadata only; it preserves member contents
  and package licensing metadata.
- **Qualified platform:** the build and tests ran on Linux x86_64 under WSL2
  with CPython 3.13.14. The wheel is pure Python and tagged `py3-none-any`, but
  other interpreters and host platforms were not tested here.
- **Release blockers:** separate owner release decision and independent human
  review. No runtime dependency license bundle is needed for the Python
  wheel. Build repeatability outside this recorded toolchain is not established.

Reproduction commands:

```bash
python3 scripts/check_coverage.py
SOURCE_DATE_EPOCH=1791569362 uv build --out-dir <output-dir> clients/python
SOURCE_DATE_EPOCH=1791569362 python3 scripts/normalize_python_sdist.py <raw-sdist> <normalized-sdist>
```

## Haskell Distribution Assessment

**Status: blocked for a Haskell executable distribution.** The source archive
can be reviewed separately because it does not bundle dependencies.

- **Exact source input:** the same Semadmit commit and tree listed above.
  Haskell subtrees: `src` `3143dcb1b33d94e839d9c7cd4f1d275af52643ed`, `app`
  `93de546a980f336e075d613567182961875f10fd`, and `test`
  `566ba2ece7579dba32d6e2c44bd5621dfb97df97`.
- **Build inputs:** GHC 9.14.1, Cabal 3.18.1.0, and the exact 71-package lock.
  `cabal.project.freeze` SHA-256 is
  `9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`;
  `semantic-oracle.cabal` SHA-256 is
  `b75f131beced23ab493ba1df76f7edfe3aee86475a9d7b33982db0d0aa292f70`.
  The 69 Hackage archives match recorded index target hashes and sizes. Three
  packages still lack declared source repositories: `base`, `colour`, and
  `strict`. Per-archive URLs, hashes, sizes, license fields, and license-file
  evidence are in [dependency-provenance.json](dependency-provenance.json) and
  [dependency-license-inventory.md](dependency-license-inventory.md).
- **GHC compiler source:** `ghc-9.14.1-src.tar.xz` from the official GHC
  download site has SHA-256
  `2a83779c9af86554a3289f2787a38d6aa83d00d136aa9f920361dd693c101e77`.
  Both archive signatures verified with key fingerprint
  `88B5 7FCF 7DB5 3B4D B3BF A4B1 5887 64FB E22D 19C4`; the local GPG trust
  store does not certify that key.
- **Clean artifact builds:** two clean source trees produced byte-identical
  Linux x86_64 ELF executables with SHA-256
  `08a314a7dddd3ed49018740f3d5ac6edda80b97deea10d5e449854f521c2b700`
  (20,763,832 bytes), and byte-identical Cabal source archives with SHA-256
  `f8b7307e484d0be76f854a598c0c7c1f69652d21cd04aaf00652e48f328b38f4`
  (46,556 bytes). The executable needs the host's `libm`, `libgmp`, and `libc`;
  the tested host uses glibc 2.35. Other platforms are not qualified.
- **Source archive contents:** the Cabal archive contains Semadmit's Apache-2.0
  `LICENSE` and source. It does not bundle Hackage dependencies or the GHC
  source tree.
- **`rts` and Closure notice:** GHC 9.14.1 `rts-1.0.3` declares BSD-3-Clause.
  Its `rts/js/md5.js` has a Closure Library Apache-2.0 source header, but the
  inspected GHC source archive has no separate Apache license copy and no
  `rts/NOTICE`. The built Semadmit artifact is a native Linux ELF; the JS file
  is not in the Semadmit source archive or executable. This makes the missing
  Closure license copy an unresolved issue for a distribution that includes
  that JS work, not evidence of a missing notice in this native artifact.
  Apache 2.0 section 4(a) requires a license copy when distributing the
  licensed work. Section 4(d) applies NOTICE-file attribution when the source
  work includes a NOTICE file. This inventory is not legal approval. See the
  [official GHC 9.14.1 source page](https://ghc.gitlab.haskell.org/homepage/download_ghc_9_14_1.html),
  [GHC source archive](https://downloads.haskell.org/ghc/9.14.1/ghc-9.14.1-src.tar.xz),
  [Closure Library license](https://github.com/google/closure-library/blob/master/LICENSE),
  and [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).
- **Release blockers:** no redistributable third-party notice bundle exists for
  the executable's linked Haskell dependencies and GHC runtime. The GHC
  signature key trust and three missing package source repositories also need
  review. The source archive may be assessed as a separate artifact. No
  Haskell binary release is authorized.

Reproduction commands:

```bash
cabal build exe:semantic-oracle --offline
cabal sdist --output-directory=<output-dir>
```

## Research Artifact Summary

**Title:** *Semadmit Core Conformance Oracle and Assurance Corpus*, version
0.1. The immutable baseline is
[`e042aded9fd98d22aeb708337a26e9bbc9f2b7b8`](https://github.com/AbstractLogix/semadmit/tree/e042aded9fd98d22aeb708337a26e9bbc9f2b7b8).
The source and executed record are in
[`assurance/assurance-certificate.json`](../assurance/assurance-certificate.json).

The oracle is an independent Python implementation for the test-only
`fixture/0.1/check` operation. It derives expected results for a bounded shared
Core corpus. Python and Haskell compare complete outputs for the named vectors.
The executed certificate records the selected local tests, mutation outcomes,
toolchain, build hashes, and a matching hosted Coverage run.

These results do not authenticate evidence or its collector. They do not show
that a claim is true, that evidence is reliable, or that the operation has
general empirical validity. They do not prove full Core parity, Haskell claim
semantics, formal correctness, or independent release approval. No claim of
scientific novelty is made; no related-work comparison was performed. The
artifact has no DOI and is not peer reviewed.

## Decision State

`semadmit/claim/0.1` is qualified in Python only. Core parity is partial. The
Python artifacts are ready for an owner decision after independent review. A
Haskell executable distribution is blocked on a complete reviewed notice and
provenance bundle. No package is published or authorized for distribution.

CERTIFICATE INTEGRITY: BLOCKED

CORE CONTRACT: PARTIALLY QUALIFIED

PYTHON DISTRIBUTION: READY FOR OWNER DECISION

HASKELL DISTRIBUTION: BLOCKED

INDEPENDENT RELEASE APPROVAL: ABSENT
