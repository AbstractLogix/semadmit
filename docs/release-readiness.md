# Release Readiness

**Release status: NOT READY FOR RELEASE.** The frozen Bouleusis claim pin remains `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. The separate `selector-provenance/0.1` pack remains experimental and indeterminate for every bounded independence case. This claim-contract qualification is separate from overall release readiness. See the [trust-boundary review](trust-boundary-review.md) for the guarantee matrix and the current [release assurance record](release-assurance.md) for fresh validation, detailed gates, and the reviewer packet.

## Current Gate Matrix

Previous assurance PR #8 merge commit: `e82c459c3de95f8a1adb0475feea70ba29aa77c0`.
Independent Core assurance implementation and validation commit:
`47d55e1e7fa10348d4a39679add3590edfe8233b`.
The independent Core assurance extension and its exact commits are recorded in
[independent-assurance.md](independent-assurance.md) and its machine-readable
certificate.

| Gate | Result | Scope |
| --- | --- | --- |
| Claim protocol | Qualified | Python verifier for `semadmit/claim/0.1`; this does not establish truth or source authenticity. |
| Core cross-language conformance | Qualified for named vectors only | 57 exact decision vectors, 9 identity vectors, one selected RFC 8785 vector, and 56 raw parser-error envelopes. Broader parser precedence, resource-boundary, and CLI parity remains partial. |
| Claim semantics | Python-only | Haskell does not implement the claim pack; no claim-pack parity is claimed. |
| Selector provenance | Experimental | Four bounded independence cases remain `indeterminate`; no positive independence rule is supported. |
| Distribution readiness | No distribution approved | Haskell binaries still lack an approved `rts` Apache-2.0 notice set. A Python-only release needs its own artifact review and owner decision. Other hosts are not qualified. |
| Independent release approval | Open | No independent human reviewer has approved the source and distribution evidence. |

Do not publish until the dependency notice gap, other open gates, and owner
release decision are addressed. Current open gates are listed in
[release-assurance.md](release-assurance.md).

## Historical Validation Record: 49a772e

Validation ran from a clean detached worktree at the exact `origin/main` commit `49a772eed2591747c99b3af29c6992fda14f120d` (PR #4 merge). Host: Linux x86_64; CPython 3.13.14; GHC 9.14.1; Cabal 3.18.1.0; uv 0.11.31.

- `python3 scripts/check_coverage.py`: **PASS**. All 55 Python tests passed. All 9 package modules passed the 100% executable-line floor (1,672 of 1,672 lines). All 7 declared Haskell suites passed. Haskell coverage was 5,310 of 5,859 expressions (90.63%, floor 89%) and 88 of 193 boolean outcomes (45.60%, floor 34%).
- `cabal build exe:semantic-oracle`: **PASS**.
- Haskell CLI smoke with fixture `admissible-ece-equality`: **PASS**. The executable returned status 0 and an admissible decision with matching request, policy, and decision digests.
- `uv build --out-dir /tmp/semadmit-build-49a772e clients/python`: **PASS**. It produced an sdist and wheel. The wheel declares `License-Expression: Apache-2.0`; both archives include the license, and the wheel includes `selector_provenance.py`.
- The claim compatibility fixture still pins `de61aa87a5f4470fd64de33c926cff7f92cf8bd6` and protocol `semadmit/claim/0.1`. That consumer pin is distinct from the validation snapshot `49a772e`.
- The separate Python pack `selector-provenance/0.1` is present at `49a772e`. Its bounded `independent_corroboration` cases remain `indeterminate`. Semadmit has no empirical Isoprax result that supports an independence admission rule, so this validation adds no such rule and does not interpret relevance scores or model identity as proof of independence.

This record establishes the listed build and test results for this commit. It does not establish release readiness, complete transitive license review, independent final review, or validation on other hosts.

## Qualification Validation Record: 3b802a33acbb501ec4a4bcc3874e202322c41a8f

Source commit: `3b802a33acbb501ec4a4bcc3874e202322c41a8f` (`fix(core): verify JSON results canonically`), based on clean `main` at `79dc40a74dfb6aa6469534ecde14bc80903cb685`. Host: Linux x86_64 under WSL2; CPython 3.13.14; GHC 9.14.1; Cabal 3.18.1.0; uv 0.11.31.

- `python3 scripts/check_coverage.py`: **PASS**. All 58 Python tests passed. All 9 package modules passed the 100% executable-line floor (1,673 of 1,673 lines). All 7 Haskell suites passed. HPC measured 5,315 of 5,859 expressions (90.72%, floor 89%) and 89 of 193 boolean outcomes (46.11%, floor 34%). The commit hook reran this gate and passed.
- The nine shared Core vectors passed in both Python and Haskell. They cover all three states, partial and mixed outcome reduction, duplicate evidence, unsupported protocol, policy digest mismatch, and an unexpected field. This does not claim claim-pack or selector-pack parity.
- `cabal build exe:semantic-oracle`: **PASS**. The CLI smoke returned an admissible `admissible-ece-equality` decision with a decision digest.
- `uv build --out-dir /tmp/semadmit-build-trust-boundary-79dc clients/python`: **PASS**. Wheel metadata declares `License-Expression: Apache-2.0`. The wheel has all 9 Python modules and the license, and it has no test package. The source archive has the license and selector module.
- Artifact SHA-256: sdist `f273d7efae337fdaa68afa6dfb87aaa96dfc7d9b9fd60239e6566c849ffae5e5`; wheel `14abe2fc3dbc5bb24479f2603290f25bb745d80781ffe8d5cbe297ba0f708707`.
- `cabal.project.freeze` pins 71 Haskell package versions; its effective index state is `2026-09-15T22:55:42Z`, and its SHA-256 is `9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`. `cabal.project` declares `2026-09-16T00:00:00Z`; Cabal applies the freeze file after the project file.
- The Python package has no third-party runtime dependencies. The setuptools 84.0.0 build backend is pinned and its wheel hash and license file are recorded in [dependency-provenance.json](dependency-provenance.json). The 69 Hackage archives and the GHC-only source packages are reviewed in the current [dependency inventory](dependency-license-inventory.md). The `rts` third-party Apache notice gap and owner approval remain open.
- A read-only GitHub protection query returned HTTP 403 with a message that private-repository branch protection needs an upgrade. Protection status is unknown. No repository settings changed. The proposed rule is to require the **Coverage** check and one independent review.

The package was built from the same source tree that was committed as `3b802a33acbb501ec4a4bcc3874e202322c41a8f`. The full test/coverage hook passed on that exact commit. Hosted pull-request status is reported separately from this local record.

## License and Provenance

- Project license: The owner selected Apache-2.0 on 2026-09-30. `LICENSE` contains the full Apache License 2.0 text. Package metadata must use the SPDX expression `Apache-2.0` and include this file.
- Founding source baseline: Isoprax Haskell kernel at commit `223187c319d6b50fb05cc2d55ffc5b465556a660`, path `haskell/isoprax-kernel/`. Its package declares `Apache-2.0`. Its root `LICENSE` SHA-256 is `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`. The commit has no root `NOTICE` file.
- Integration method: Implement the reviewed Semadmit v0.1 contract independently. Compare behavior with the pinned Isoprax source only where semantics overlap. Do not copy Isoprax source or make Semadmit depend on the Isoprax package. Record any later copied code and its attribution before distribution.
- The Python runtime uses the standard library for its restricted JSON/JCS number profile. The build backend and exact locked Haskell packages are listed below. See the current dependency inventory for archive hashes and unresolved notices.

## Pinned Setup for M1

- Reference host: Linux x86_64 under WSL2. The first supported toolchain uses GHC 9.14.1, Cabal 3.18.1.0, and CPython 3.13.14. Other hosts and Python minor versions are unqualified until clean checks are recorded.
- `cabal.project` declares Hackage index state `2026-09-16T00:00:00Z` and selects GHC 9.14.1. `cabal.project.freeze` overrides that setting with effective index state `2026-09-15T22:55:42Z` and records the solved graph.
- `clients/python/pyproject.toml` supports Python 3.13 and pins setuptools 84.0.0 as its build backend. Setuptools declares MIT on [PyPI](https://pypi.org/project/setuptools/). This setup has no third-party Python runtime dependencies. Python's standard library provides restricted JSON/JCS encoding, SHA-256, evaluation, and JSONL. The public API exports the explicit registry, evaluator, verification result, and JSONL runner.
- Direct Haskell dependencies are `base` 4.22.0.0 (BSD-3-Clause), `aeson` 2.2.5.1 (BSD-3-Clause), `bytestring` 0.12.2.0 (BSD-3-Clause), `containers` 0.8 (BSD-3-Clause), `cryptohash-sha256` 0.11.102.1 (BSD3), `directory` 1.3.10.0 (BSD-3-Clause, test only), `scientific` 0.3.8.1 (BSD3), `text` 2.1.3 (BSD-2-Clause), and `vector` 0.13.2.0 (BSD-3-Clause). The pinned Cabal package metadata supplies these license declarations. `aeson` provides JSON values and RFC 8785 encoding. The bounded byte parser enforces the v0.1 token profile. `cryptohash-sha256` provides digests. `base` provides exact `Ratio Integer`. `scientific` and `vector` support Aeson value validation. `Core.CLI` uses `base` and `bytestring` for handle-based framing and output.
- Direct license metadata permits the selected Apache-2.0 project license. Preserve each dependency's distribution notices. The exact archive and license-file inventory is in [dependency-provenance.json](dependency-provenance.json). The `rts` notice gap still blocks a Haskell binary release. This repository does not copy dependency code.

## Historical M1 Setup Checks

- `cabal build lib:semantic-oracle` completed with GHC 9.14.1. The library contains protocol parsing, bounded canonical identity, pack registration, and decision evaluation. A shared registered-pack vector suite checks positive and negative decisions through the Haskell evaluator.
- `cabal freeze` wrote the locked direct and transitive Haskell package graph.
- `uv build --out-dir /tmp/semadmit-build clients/python` produced an sdist and wheel with the pinned setuptools backend. The wheel metadata reports `License-Expression: Apache-2.0`. Both archives include the full license. This checks package shape, not runtime behavior.
- `cabal build exe:semantic-oracle` passed. The executable registers the first-party Isoprax pack and delegates request handling to the tested `Core.CLI` runner. A CLI smoke request returned the expected admissible decision and exit status.
- `cabal test all --enable-coverage --test-show-details=direct` passed seven suites through the coverage gate. They cover the nine approved identity vectors, the applicable published RFC 8785 property-order vector, parser fixtures and limits, registered-operation dispatch, exact error/result envelopes, descriptor validation, generic bindings, deterministic decision construction, shared positive/negative evaluator vectors, fixture-backed `Core.CLI` framing and status behavior, every Isoprax pool fixture through the first-party application runner, subject parsing and identity sidecars, exact calibration calculations, and legacy number conversion.
- The shared vectors compare complete positive and negative decisions across the Python and Haskell evaluators. Each language suite compares its full output with the same expected vector; a disagreement fails that suite. The Haskell CLI checks request bytes, full output, and exit codes for the available first-party Isoprax pack. The Measurement pack and guarded consumption remain open.
- The shared vector file declares `semadmit-core-parity-cases/0.1`. Its two exact-output cases qualify only the Core evaluator semantics named in the corpus; they do not claim Python/Haskell parity for the claim or Isoprax domain packs. See [Bouleusis compatibility](bouleusis-compatibility.md) for the frozen claim/Core protocols and result verification boundary.
- The coverage gate runs with `python3 scripts/check_coverage.py`. On 2026-10-04, all 29 Python tests passed with 792 of 792 executable lines. All 7 Haskell suites passed with 5,312 of 5,861 expressions (90.63%) and 88 of 193 boolean outcomes (45.60%). The floors are 100% Python executable lines per package module and 89%/34% Haskell expressions/booleans. Local pre-commit and GitHub Actions use this gate. Require the **Coverage** check in repository branch protection before using it to block merges. See `docs/coverage.md` for the method and thresholds.

Apache-2.0 permits reuse and redistribution under its conditions. It also includes a patent grant. Keep required notices and the license text with distributed artifacts. See the [Apache license text](https://www.apache.org/licenses/LICENSE-2.0.html) and [Python package license metadata specification](https://packaging.python.org/en/latest/specifications/license-expression/) for the license rules.

## Open Gates

- Snapshot-bound verification: bind verification to an immutable implementation or build identity.
- Guarded consumption: provide a claim-specific checked-use capability.
- Measurement pack: qualify matching Python and Haskell semantics.
- Extension example: add downstream guarded-use and conformance checks.
- Broad conformance: the named decision, identity, and raw parser cases pass in both languages. Request mutation, resource recipes, all parser boundaries, and full CLI framing are not a complete shared corpus.
- Dependency and license review: the 69 Hackage archive hashes and declared license files are recorded. Resolve the GHC `rts` Apache-2.0 copy and obtain owner review of the redistribution notice set.
- Independent final review: obtain a separate reviewer for the implementation, contracts, package, and license evidence.
- Repository protection: branch rules could not be inspected; the repository owner must confirm that Coverage and independent review are required.
- Publishing remains a separate decision.
