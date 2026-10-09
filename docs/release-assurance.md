# Release Assurance

**Claim contract: qualified. Release: not ready.** The qualified contract is
`semadmit/claim/0.1`. The stable Bouleusis compatibility pin remains
`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. The separate
`selector-provenance/0.1` pack remains experimental. These are separate
qualification results.

The [final assurance integrity and distribution assessment](assurance-integrity-assessment.md)
adds the adversarial certificate results and current artifact build hashes.

## PR #8 Baseline and Validation (Historical)

- Pre-assurance main baseline: `b4e1f85ccc8bc56de8f4b12529cfc4e110ee21c7`.
- Assurance PR #8 merge commit: `e82c459c3de95f8a1adb0475feea70ba29aa77c0`.
- Assurance implementation and test commit:
  `cad6943ce19bc4b0439cd85332ed632ee17f3a9f`.
- Scope: dependency provenance evidence, Python source archive metadata
  normalization, and exact shared parser-error comparisons. No claim, Core,
  or selector runtime semantics changed.
- Host: Linux x86_64 under WSL2; CPython 3.13.14; GHC 9.14.1; Cabal 3.18.1.0;
  uv 0.11.31.

The full validation command was `python3 scripts/check_coverage.py`.

| Check | Result | Evidence |
| --- | --- | --- |
| Python tests and line coverage | PASS | 58 tests; all 9 package modules at 100% executable-line coverage (1,678/1,678). Python branch coverage is not measured. |
| Haskell tests and coverage | PASS | All 7 suites; 5,315/5,859 expressions (90.72%, floor 89%); 89/193 booleans (46.11%, floor 34%). |
| Haskell executable build | PASS | `cabal build exe:semantic-oracle`; SHA-256 `08a314a7dddd3ed49018740f3d5ac6edda80b97deea10d5e449854f521c2b700`. This matches the earlier two-clean-build result; Haskell runtime code did not change. |
| Haskell CLI smoke | PASS | The `admissible-ece-equality` request returned `admissible` and decision digest `sha256:90e4c7d10296fe508ecd250904139d8b8c0c492b361b1f59940afdf7b4faa0f5`. |
| Haskell source archive | PASS | `cabal sdist --output-directory=/tmp/semadmit-final-cad6943-haskell`; SHA-256 `b79b145abfa4fd2f138c1cd17a46926f29acc9485cd9bcce1ca42925f4bbeac5`. It contains Semadmit's `LICENSE`; it does not bundle dependencies. |
| Python source archive and wheel | PASS | `uv build --out-dir /tmp/semadmit-final-cad6943-python clients/python`; raw sdist SHA-256 `fb019e472d95702487c07d29f06b3268b7524b121b5c1b27689a9d528eaacd86`; wheel SHA-256 `3bd2eefbad3348401ac1d1a9155f597c2b58ca7941eb71a5970d903f43659871`. |
| Python package contents | PASS | Wheel has 9 modules, no tests, no runtime dependencies, the Semadmit license, and `License-Expression: Apache-2.0`. The sdist includes the license and tests. |
| Dependency archives | PASS for recorded artifacts | All 69 locked Hackage archive hashes and sizes match the current Cabal-managed Hackage index target metadata. A fresh download check also matched `aeson-2.2.5.1`. GHC source signatures and the remaining notice limits are recorded below. |

The Cabal lock file hash is
`9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`.
The effective index state is `2026-09-15T22:55:42Z`, recorded in
`cabal.project.freeze`. `cabal.project` says `2026-09-16T00:00:00Z`, but Cabal
applies the freeze file after the project file. See the [Cabal configuration
order](https://github.com/haskell/cabal/blob/master/doc/cabal-project-description-file.rst#L204-L210).

## Independent Core Assurance Extension

The new bounded reference and corpus are described in
[independent-assurance.md](independent-assurance.md). The exact assurance
implementation commit, source hashes, build artifact hashes, and hosted CI
evidence are recorded in
[`assurance-certificate.json`](../assurance/assurance-certificate.json).

The implementation commit is
`47d55e1e7fa10348d4a39679add3590edfe8233b`. The refreshed certificate was
generated from clean validation commit
`dcf3d1070186a3f936e17f5975622023c812fc2b`. The writer reran the seeded-corpus,
source-mutation, and full test/coverage gates. It recorded 59 Python package
tests, 7 independent-reference tests, 10 certificate-integrity tests, and all
7 Haskell suites. Python line coverage was 1,679/1,679 executable lines.
Haskell coverage was 5,318/5,859 expressions (90.77%) and 90/193 booleans
(46.63%). Hosted Coverage passed on the same validation commit:
<https://github.com/AbstractLogix/semadmit/actions/runs/38000152994>. The
certificate stores stdout, byte counts, and digests for all three local gates.
Its artifact hashes match the assessed artifact bytes, but do not prove source
binding. The certificate is not a signed build attestation.

The shared Core suite now compares 57 complete decisions or error results in
both languages. The 48 generated decisions come from a fixed seed and have
expected values from the independent reference, not the production evaluator.
Both parser suites compare 68 complete raw-input cases, including 65 error
envelopes: 17 reviewed errors and 48 bounded generated mutations. The
reference supports only the test-only `fixture/0.1/check` operation. It does
not implement Semadmit claim, Isoprax, selector, or Measurement semantics.

Seven controlled Python Core source mutants were killed (7/7) across exact
result comparison, request and policy identity, policy-digest verification,
state reduction, protocol rejection, and error envelopes. No Haskell source
mutations were run. This result applies only to the selected mutation set.
The Core contract remains only partially qualified because broader parser
precedence, error-pointer, resource-boundary, and CLI parity remain open.

The Python claim suite also tampers with evidence IDs and assumptions in a
valid `VALID`/`ADMISSIBLE` result and confirms `verify_result` rejects both
changes. The existing selector-provenance suite still confirms all four
independence cases are `indeterminate`.

## Qualification Matrix

| Area | Status | Evidence and limit |
| --- | --- | --- |
| Claim protocol | Qualified | Python Semadmit verifier checks request/result binding, identities, digests, Core bindings, status pairs, and protocol version. This is not a truth or source-authentication claim. |
| Core cross-language conformance | Partially qualified | Python and Haskell compare 57 exact decision vectors and 9 M0 identity vectors. Both also run the selected RFC 8785 property-order vector and 68 raw parser cases, including 65 error envelopes. The independent reference is bounded to the test-only fixture pack. Parser precedence, limits, and CLI framing remain open. |
| Claim semantics | Python-only | `semadmit/claim/0.1` is implemented and tested in Python. Haskell does not implement this claim pack. No claim-pack parity is asserted. |
| Selector provenance | Experimental | `selector-provenance/0.1` remains Python-only. All 4 bounded independence cases remain `indeterminate`. No positive independence rule is supported by the current IsoPrax evidence. |
| Python distribution | Ready for owner decision | The exact Python artifacts are reproducible on the tested host. An independent review and separate owner decision remain open. |
| Haskell executable distribution | Blocked | A complete notice and provenance bundle for the linked dependencies and GHC runtime is not prepared or approved. Other hosts are not qualified. |
| Certificate integrity | Blocked | Adversarial tests now reject missing logs, false counts, wrong workflow runs, and other tested failures. Artifact-to-source binding and offline certificate verification remain absent. |
| Independent release approval | Open | No independent human has reviewed and approved the exact source, dependency notices, and distribution artifacts. Automated checks do not close this gate. |

`VerificationStatus` remains separate from `AdmissionStatus`. An admissibility
result only says whether evidence may participate in the named operation under
the declared policy. It does not tell Bouleusis what to believe.

## Cross-Language Conformance Review

The nine original reviewed Core decision vectors are:
`admissible`, `inadmissible`, `indeterminate`, `pass-with-missing`,
`failure-dominates-missing`, `duplicate-evidence`, `unsupported-protocol`,
`policy-digest-mismatch`, and `unexpected-field`. They compare full decisions
and error results. They cover generic request normalization, identity and
component bindings, digest equality, and operation-state reduction. The shared
corpus also has 48 fixed-seed valid requests with expected results computed by
the independent `assurance/reference_core.py` implementation. Each language
compares all 57 full results against the committed expected values.

The two language suites consume the 9 M0 identity vectors. They check canonical
bytes and identity digests, including a decision digest. Both consume the
selected RFC 8785 property-order and UTF-8 vector. Both consume the same 68 raw
parser cases, including 65 error envelopes: 17 reviewed errors plus 48
fixed-seed mutations of trailing data, number profiles, and duplicate keys.
They compare each complete output. Invalid UTF-8, unpaired surrogate, and
negative zero remain in the reviewed cases. The loader fails if the expected
raw case set changes without a test update.

The remaining `protocol-cases.json` entries describe request mutations,
resource recipes, or JSONL framing. They are not all run as exact shared
Python/Haskell cases. The claim substitution tests are Python-only because
Haskell does not implement the claim pack. Parser precedence, every error
pointer, resource-limit boundaries, and CLI framing remain partial; see the
open gate matrix.

## Dependency and Notice Findings

The complete per-artifact record is [dependency-provenance.json](dependency-provenance.json).

- The 69 locked Hackage archives match their `package.json` target hash and size
  in the current Cabal-managed local index. The `01-index.tar` SHA-256 is
  `63acf6536e0cdfe6aca24f8b018006dafd32e1df45f1d82c817260f2dd8f28da`.
  A fresh `aeson-2.2.5.1` download also matched. Hackage stores the archive hash
  and size in the package target metadata; see its [security design](https://github.com/haskell/hackage-security/blob/master/README.md#targets).
- Each of the 69 source archives has its declared Cabal license file. No
  separate `NOTICE` file was found. This scan does not assess every source file
  for additional attribution requirements.
- `base-4.22.0.0`, `colour-2.3.7`, and `strict-0.5.1` do not declare a source
  repository in their package descriptions. Their source repositories are not
  established here.
- `ghc-prim-0.13.1` and `rts-1.0.3` come from the official GHC 9.14.1 source
  archive at `https://downloads.haskell.org/ghc/9.14.1/ghc-9.14.1-src.tar.xz`.
  Its SHA-256 is
  `2a83779c9af86554a3289f2787a38d6aa83d00d136aa9f920361dd693c101e77`.
  The checksum-list and source-archive GPG signatures verify with fingerprint
  `88B5 7FCF 7DB5 3B4D B3BF A4B1 5887 64FB E22D 19C4`. The GHC 9.14.1 download
  page lists this signing key. The local GPG trust database reports the key as
  unknown, so signer identity is not independently certified here. See the
  [GHC source release page](https://ghc.gitlab.haskell.org/homepage/download_ghc_9_14_1.html).
- `ghc-prim` declares BSD-3-Clause and includes its license with the GHC and
  Haskell 98 notices. `rts` declares BSD-3-Clause but has no `license-file`
  field. The source archive includes GHC's root license, inline xxHash
  BSD-2-Clause terms, LLVM license text, and the generated `configure` script's
  Free Software Foundation unlimited-permission notice. `rts/js/md5.js`
  identifies vendored Closure Library code under Apache-2.0, but no separate
  Apache license copy or `NOTICE` file was found under `rts`. The assessed
  native Linux executable and Semadmit Cabal source archive do not contain
  this JavaScript file. The Apache license-copy issue applies if a distribution
  includes that Closure work. The Haskell executable remains blocked because
  no complete, reviewed notice bundle exists for its linked dependencies and
  runtime. This inventory is not legal approval.
- Setuptools 84.0.0 is a build-only backend. Its exact wheel hash and MIT
  license file are recorded in the inventory. It is not bundled in Semadmit's
  Python wheel or source archive.

The Hackage target hashes come from the current Cabal-managed index cache, not
from a separately recreated historical index snapshot at the freeze time. The
report does not independently verify the full Hackage signing-key chain. These
limits are recorded in the provenance data.

## Source Archive Reproducibility

Two clean source trees at
`cad6943ce19bc4b0439cd85332ed632ee17f3a9f` were built with `SOURCE_DATE_EPOCH`
set to the commit time. The raw sdist hashes differed:

- `487f195463deedf0da6c705c460e30716b189c488bb568cab23b5e9731f1a44c`
- `f53a465f55fd6bc8cb39a8cf92fe07ecc6b0b92852e33bb6d3f5b2b3f7fe1964`

All 32 archive member names, types, and file bytes matched. PAX fractional
`mtime` fields differed for the generated top-level directory, `PKG-INFO`,
`semadmit/`, `semadmit.egg-info/`, its generated metadata files, `setup.cfg`,
and `tests/`. The gzip timestamp happened to match because both builds ran in
the same second. Earlier clean builds also showed the gzip header timestamp
changing with build time.

`scripts/normalize_python_sdist.py` removes variable time and owner metadata,
keeps member order, modes, names, and file bytes, and writes a fixed gzip
header. Both normalized archives are byte-identical with SHA-256
`940ed9931fbcbfbdeaf0a05b374af7a0226662635dcff69ddda1567d8701b13c`.
The normalized archive has the same 32 members. Its `LICENSE`,
`License-Expression: Apache-2.0`, and `License-File: LICENSE` are present.
The two clean wheels also match byte for byte at SHA-256
`48cfb2aa836e5313e00239bac61118f7ff8209b4fb624b9c36efa40273cb4423`.

This procedure makes the normalized sdist reproducible on the tested pinned
toolchain. The unmodified `uv build` sdist is not byte-reproducible. Repeatable
release builds on CI and other supported hosts remain open.

## Outstanding Gate Matrix

| Gate | Current evidence | Remaining action | Status |
| --- | --- | --- | --- |
| Snapshot-bound verification | Verifier uses the implementation in the current process. | Bind verification to an immutable implementation or build identity without changing the frozen claim protocol. | Open |
| Guarded claim consumption | Result verification returns a boolean. | Add and qualify a claim-specific checked-use capability before claiming guarded consumption. | Open |
| Broad Core conformance | 57 exact decision vectors, 9 identity vectors, one shared RFC vector, 68 raw parser cases (65 errors), and 7/7 selected Python mutation kills pass. | Qualify remaining parser precedence, error pointers, resource boundaries, and CLI behavior where they expose a real compatibility risk. | Partial |
| Measurement | Existing tests pass. | Qualify a narrow contract and matching Python/Haskell behavior. | Open |
| Downstream extension example | Neutral Core fixture exists. | Add and test an example after guarded consumption is available. | Open |
| Certificate integrity | Executed gate logs and their hashes are recorded; tested fail-closed cases pass. | Add source-bound artifact verification and an offline certificate verifier. | Partial |
| Dependency redistribution notices | Hackage archive digests and declared licenses are recorded. The native ELF does not include `rts/js/md5.js`; the full linked-dependency notice bundle is not prepared. | Review the exact artifact notice bundle, GHC provenance limits, and any Closure-containing distribution separately. | Partial |
| Reproducible builds | Python wheel and normalized sdist match across two clean trees with fixed `SOURCE_DATE_EPOCH`; Haskell executable and source archive also match across two clean trees. | Repeat release builds on any additional claimed target platforms. | Partial |
| Independent release review | Reviewer packet is prepared. | A human who did not author the implementation must record findings against the exact source commit and artifacts. | Open |
| Repository protection | Prior read-only query returned HTTP 403 for private repository settings. | Owner confirms required Coverage and independent review rules. | Unknown |
| Package release decision | No package has been published. | Obtain a separate owner release decision after the other gates close. | Open |

Do not publish a package until the open release gates are closed or the owner
records an explicit release decision. This assurance work does not itself
authorize publication.

## Independent Review Packet

See the [review packet](release-review-packet.md). It identifies the exact
source commit, scope, threats, reproduction steps, limitations, and open
release gates. The current [assurance assessment](assurance-integrity-assessment.md)
records the certificate, parity, distribution, and owner-review gates. Neither
document claims human approval.
