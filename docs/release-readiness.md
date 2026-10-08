# Release Readiness

**Status**: Not ready for release. The main merge at `49a772eed2591747c99b3af29c6992fda14f120d` passed the full automated test and coverage gate, the Python package build, and the Haskell executable smoke check recorded below. Release gates remain open for broader conformance, the full redistribution inventory, independent final review, and the separate release decision.

## Validation Record: 2026-10-08

Validation ran from a clean detached worktree at the exact `origin/main` commit `49a772eed2591747c99b3af29c6992fda14f120d` (PR #4 merge). Host: Linux x86_64; CPython 3.13.14; GHC 9.14.1; Cabal 3.18.1.0; uv 0.11.31.

- `python3 scripts/check_coverage.py`: **PASS**. All 55 Python tests passed. All 9 package modules passed the 100% executable-line floor (1,672 of 1,672 lines). All 7 declared Haskell suites passed. Haskell coverage was 5,310 of 5,859 expressions (90.63%, floor 89%) and 88 of 193 boolean outcomes (45.60%, floor 34%).
- `cabal build exe:semantic-oracle`: **PASS**.
- Haskell CLI smoke with fixture `admissible-ece-equality`: **PASS**. The executable returned status 0 and an admissible decision with matching request, policy, and decision digests.
- `uv build --out-dir /tmp/semadmit-build-49a772e clients/python`: **PASS**. It produced an sdist and wheel. The wheel declares `License-Expression: Apache-2.0`; both archives include the license, and the wheel includes `selector_provenance.py`.
- The claim compatibility fixture still pins `de61aa87a5f4470fd64de33c926cff7f92cf8bd6` and protocol `semadmit/claim/0.1`. That consumer pin is distinct from the validation snapshot `49a772e`.
- The separate Python pack `selector-provenance/0.1` is present at `49a772e`. Its bounded `independent_corroboration` cases remain `indeterminate`. Semadmit has no empirical IsoPrax result that supports an independence admission rule, so this validation adds no such rule and does not interpret relevance scores or model identity as proof of independence.

This record establishes the listed build and test results for this commit. It does not establish release readiness, complete transitive license review, independent final review, or validation on other hosts.

## License and Provenance

- Project license: The owner selected Apache-2.0 on 2026-09-30. `LICENSE` contains the full Apache License 2.0 text. Package metadata must use the SPDX expression `Apache-2.0` and include this file.
- Founding source baseline: Isoprax Haskell kernel at commit `223187c319d6b50fb05cc2d55ffc5b465556a660`, path `haskell/isoprax-kernel/`. Its package declares `Apache-2.0`. Its root `LICENSE` SHA-256 is `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`. The commit has no root `NOTICE` file.
- Integration method: Implement the reviewed Semadmit v0.1 contract independently. Compare behavior with the pinned Isoprax source only where semantics overlap. Do not copy Isoprax source or make Semadmit depend on the Isoprax package. Record any later copied code and its attribution before distribution.
- The planned Python runtime uses the standard library for its restricted JSON/JCS number profile. The build backend and direct Haskell dependencies are listed below. Review the transitive dependency graph for distribution notices before release.

## Pinned Setup for M1

- Reference host: Linux x86_64 under WSL2. The first supported toolchain uses GHC 9.14.1, Cabal 3.18.1.0, and CPython 3.13.14. Other hosts and Python minor versions are unqualified until clean checks are recorded.
- `cabal.project` fixes the Hackage index state to `2026-09-16T00:00:00Z` and selects GHC 9.14.1. `semantic-oracle.cabal` pins direct library versions. `cabal.project.freeze` records the solved transitive graph and its effective index state.
- `clients/python/pyproject.toml` supports Python 3.13 and pins setuptools 84.0.0 as its build backend. Setuptools declares MIT on [PyPI](https://pypi.org/project/setuptools/). This setup has no third-party Python runtime dependencies. Python's standard library provides restricted JSON/JCS encoding, SHA-256, evaluation, and JSONL. The public API exports the explicit registry, evaluator, verification result, and JSONL runner.
- Direct Haskell dependencies are `base` 4.22.0.0 (BSD-3-Clause), `aeson` 2.2.5.1 (BSD-3-Clause), `bytestring` 0.12.2.0 (BSD-3-Clause), `containers` 0.8 (BSD-3-Clause), `cryptohash-sha256` 0.11.102.1 (BSD3), `directory` 1.3.10.0 (BSD-3-Clause, test only), `scientific` 0.3.8.1 (BSD3), `text` 2.1.3 (BSD-2-Clause), and `vector` 0.13.2.0 (BSD-3-Clause). The pinned Cabal package metadata supplies these license declarations. `aeson` provides JSON values and RFC 8785 encoding. The bounded byte parser enforces the v0.1 token profile. `cryptohash-sha256` provides digests. `base` provides exact `Ratio Integer`. `scientific` and `vector` support Aeson value validation. `Core.CLI` uses `base` and `bytestring` for handle-based framing and output.
- Direct license metadata permits the selected Apache-2.0 project license. Preserve each dependency's distribution notices. Review the transitive graph before release. This repository does not copy dependency code.

## Setup Checks Run

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

- M2: Complete snapshot-bound verification, guarded consumption, independent Python Isoprax parity, and substitution checks.
- M3: Implement and check the Haskell and Python Measurement packs.
- M4: Complete the downstream extension example and its guarded-use checks.
- M5–M6: Add broader conformance tests, close license and dependency-provenance checks, record release evidence, and obtain independent final review.
- T043–T045: Inventory each redistributed direct and transitive dependency. Verify package license metadata and included notices. Record clean build/test commands and exact source SHAs. Obtain final independent review.
- Publishing remains a separate decision.
