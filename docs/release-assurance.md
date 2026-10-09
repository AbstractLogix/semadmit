# Release Assurance

**Claim contract: qualified. Release: not ready.** The claim contract qualification covers the Semadmit verifier and its bounded conformance cases. It does not claim a Bouleusis integration run. The stable compatibility pin remains `de61aa87a5f4470fd64de33c926cff7f92cf8bd6` for `semadmit/claim/0.1`. The separate `selector-provenance/0.1` pack remains experimental.

This record separates evidence for the current merged baseline from older validation. It does not treat a documentation entry as proof that an open gate is complete.

## Clean Baseline

Validation ran from a clean checkout of `origin/main` at `46b81c7d1429dc645efafdafcfac35b584ef38b9` on 2026-10-08. Host: Linux x86_64 under WSL2. Toolchain: CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, and uv 0.11.31.

| Check | Result | Evidence |
| --- | --- | --- |
| Python tests and coverage | PASS | `python3 scripts/check_coverage.py`: 58 tests; all 9 package modules at 100% executable-line coverage (1,673/1,673). The gate does not measure Python branch coverage. |
| Haskell tests and coverage | PASS | All 7 declared suites passed. HPC: 5,315/5,859 expressions (90.72%, floor 89%) and 89/193 booleans (46.11%, floor 34%). |
| Shared Python/Haskell Core corpus | PASS for stated scope | All 9 exact-output vectors passed in both implementations. This is not claim-pack or selector-pack parity. |
| Haskell executable | PASS | `cabal build exe:semantic-oracle` completed. |
| CLI smoke | PASS | The `admissible-ece-equality` request returned `admissible` and the fixture decision digest `sha256:90e4c7d10296fe508ecd250904139d8b8c0c492b361b1f59940afdf7b4faa0f5`. |
| Python sdist and wheel | PASS | `uv build --out-dir /tmp/semadmit-release-assurance-46b81c7 clients/python` completed. The wheel has 9 runtime modules, no test package, and the Apache-2.0 license. The sdist includes the license and tests. |
| Wheel metadata | PASS | `License-Expression: Apache-2.0`; `Requires-Python: >=3.13,<3.14`; no Python runtime dependencies. |
| Claim compatibility matrix | PASS | `ClaimEngine.verify_result` accepted the normative valid fixture. Tests reject candidate mutation, request substitution, status changes, digest changes, duplicate keys, and invalid Unicode. |

The claim pin and the validation commit are separate values. The pin remains `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`; this run validated the current merged source at `46b81c7d1429dc645efafdafcfac35b584ef38b9`.

## Assurance Test Commit

The focused regression-test commit is `03751e4a3a234c00360c9e6ddf36b6f742b0e3b3`. It changes tests only; it does not change Python or Haskell runtime code. The full coverage hook passed on this exact commit: 58 Python tests; all 9 modules at 100% executable-line coverage (1,674/1,674); all 7 Haskell suites; 5,315/5,859 expressions (90.72%) and 89/193 booleans (46.11%).

Two clean builds from this exact source commit produced identical Python wheels with SHA-256 `086a9911558f539fa892857403282c1838b40722dfa504105e4aabcf5c224339` and identical Haskell executables with SHA-256 `08a314a7dddd3ed49018740f3d5ac6edda80b97deea10d5e449854f521c2b700`. The Python sdist hashes differed: `263580b032f2b8fb09ee70b39422d3436cd9fc48394ba14ed8df9cb8c069799c` and `eef5869b31101add915f97967fd238832fb55a250d6c4a0b3c372786ab4b1712`. The sdist member contents matched; generated timestamps differed.

### Clean Build Repeatability

Two clean source snapshots were built with `SOURCE_DATE_EPOCH` set to the baseline commit time. The Python wheel was byte-identical in both builds: SHA-256 `5e08e6ec31a9f6904c360b858380b9604aaade29e0e2ee4550a19dbfa0f759a3`. The Haskell executable was byte-identical in both builds: SHA-256 `08a314a7dddd3ed49018740f3d5ac6edda80b97deea10d5e449854f521c2b700`.

The Python source archives were not byte-identical. Their SHA-256 values were `ab83a6821dc7fc9aaa180800d8400488a6ee282a35cb648ca0546029edebf1fc` and `e59e6d068723bb9e0ca567f1c1466f46d694e1ec245191d7c25a92fb0a9f7b6f`. The file contents matched; generated directory and metadata times and the gzip time differed. Source-archive reproducibility remains open.

### Dependency Lock and Platform

The frozen Haskell graph has 71 exact package versions. `cabal.project.freeze` SHA-256 is `9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`; its Hackage index state is `2026-09-16T00:00:00Z`. The full package and license metadata list is in the [dependency license inventory](dependency-license-inventory.md).

The package declares Python `>=3.13,<3.14`. This run qualifies only CPython 3.13.14 on Linux x86_64 under WSL2. Windows, macOS, other Python minor versions, and other architectures are untested and are not release-qualified.

## Adversarial Boundary Evidence

The Python claim verifier recomputes the result from the supplied request and compares canonical JSON bytes. Its tests cover:

- request substitution for claim, evidence, and policy;
- result-envelope changes, including claim/evidence IDs, status pairs, missing fields, unexpected fields, and a non-object candidate;
- verification-artifact and Core component-binding changes;
- operation substitution and decision, result, and verification digest changes;
- `true`/`1` and `false`/`0` substitutions;
- duplicate JSON keys, malformed Unicode, unsupported protocols, and bounded number/resource profiles.

The claim and selector fixtures include positive, negative, and unknown paths. Missing provenance and unknown dependence remain `indeterminate`. The selector score, model names, and shared model metadata do not grant an independence result. No positive independence rule is added from the IsoPrax synthetic study.

No tested mutation produced an incorrectly admissible result. This is bounded test evidence. It is not a formal proof or a security certification. A valid digest does not authenticate a source. The in-memory Python API cannot detect duplicate keys after a caller has parsed them and discarded them.

## Cross-Language Scope

| Contract | Python | Haskell | Exact shared comparison | Status |
| --- | --- | --- | --- | --- |
| Generic Core decisions | Implemented | Implemented | 9 full decision/error vectors, including bindings, digest, status reduction, and selected protocol errors | Qualified for those vectors only |
| Core parser and resource limits | Local parser tests | Local parser tests | No complete shared corpus for error precedence, all error pointers, and every size/depth boundary | Partial |
| Claim pack `semadmit/claim/0.1` | Implemented and tested | Not implemented | None | Python-only by design; no parity claim |
| Selector pack `selector-provenance/0.1` | Experimental and tested | Not implemented | None | Python-only; all four bounded cases remain `indeterminate` |
| Measurement pack | Not qualified | Not qualified | None | Open |
| CLI framing | Python JSONL tests | Haskell CLI tests and smoke | No complete cross-language byte/exit-code corpus | Partial |

The shared Core vectors cover request normalization, generic bindings, obligation reduction, decision payloads, and decision digests. They do not establish parity for the claim pack, selector pack, Measurement, or every parser and CLI boundary.

## Remaining Release Gates

| Requirement | Existing evidence | Missing evidence | Risk if omitted | Required action | Independent review | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Snapshot-bound verification | The verifier recomputes the result with the registered implementation in the current process. | An immutable implementation or build identity that the consumer can verify. | A changed verifier can produce a valid-looking result under different code. | Add a versioned snapshot identity and bind verification to it. Keep the frozen claim protocol unchanged. | Required | Open |
| Guarded claim consumption | Core exposes an `Admission`; claim results have a boolean verifier. | A claim-specific checked-use capability bound to request, operation, and policy. | A consumer can use a candidate without proving that the checked request was admitted. | Add the smallest claim-specific checked-use API and fail-closed tests. Do not make it a truth or belief update. | Required | Open |
| Cross-language conformance gaps | Nine shared Core vectors pass in Python and Haskell. | Shared exact-output cases for more parser errors, pointers, limits, and CLI framing. | Implementations can disagree at boundaries that callers depend on. | Add shared vectors only for semantics both implementations claim to support. Keep claim and selector semantics excluded. | Required | Partial |
| Measurement readiness | Existing Core and Isoprax tests pass. | A qualified Measurement contract and matching Python/Haskell semantics. | Callers may rely on a pack with no cross-language evidence. | Define the narrow Measurement contract, then add matching behavior and shared cases before qualification. | Required | Open |
| Downstream extension example | The repository has a neutral Core extension fixture. | A downstream example that uses the guarded claim boundary and checks conformance. | Consumers may copy the API incorrectly or skip verification. | Add a small example after the guarded-use API exists and test it against the public contract. | Required | Open |
| Dependency and licensing inventory | The 71 locked versions and Hackage license files are listed. Python wheel and sdist contain Semadmit's Apache-2.0 license. | Source and notice review for GHC-only `ghc-prim` and `rts`; owner confirmation of redistribution obligations. | A release may omit a required notice or attribution. | Complete source/notice review for those compiler components and approve the distribution inventory. | Required | Partial |
| Reproducible release builds | Two clean Haskell executable builds and Python wheel builds were byte-identical. | Reproducible Python sdist output and repeated release build evidence on the supported CI host. | The same source can produce different published source archives. | Normalize sdist metadata and timestamps in the release build path, then compare clean outputs. | Required | Partial |
| Independent final review | A focused review packet is prepared below. The prior automated code review was not a human review. | A reviewer who did not author the implementation must inspect the exact source and release evidence. | Defects or unsupported claims may remain unchallenged. | Obtain and record an independent human review of the final source, contract, package, and license evidence. | Required | Open |
| Repository protection | Hosted Coverage passed on PR #6. | Branch protection could not be read; GitHub returned HTTP 403 for private-repository protection settings. | A later change can merge without the intended checks or review. | Repository owner must confirm or configure Coverage and one independent review. | Owner action | Unknown |

The compatibility result remains separate from release readiness. Do not publish a package until the owner makes a separate release decision.

## Focused Review Packet

The [review packet](release-review-packet.md) gives the threat model, frozen contract, invariants, limitations, validation commands, and open defects for a reviewer who did not author the implementation.
