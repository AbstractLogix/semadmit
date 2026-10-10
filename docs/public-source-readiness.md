# Public-source readiness audit

**Audit baseline:** `e8f923ee909bcc527675cb89fc578e7da8c258f4` (`origin/main`). The supplied baseline `4717f5d1cc202d57fcdc8f61da5de3dc6c7839c8` is an ancestor. This review covers public source access only. It does not approve a package or binary release.

## Decision matrix

| Area | Result | Scope and open action |
| --- | --- | --- |
| History and secret audit | **BLOCKED pending owner decisions** | No credential candidate was found. A personal author email is present in reachable commit metadata. A detailed downstream eligibility specification also needs owner classification before public disclosure. Neither item was rewritten. |
| Source licensing | **READY** | Semadmit source declares Apache-2.0. This change adds the MIT notice for adapted Spec Kit material. Haskell binary notice work remains a separate distribution gate. |
| Public documentation | **READY** | README, contributor guidance, security guidance, and this report describe current scope and limits. The quickstart passed from a clean checkout. |
| Clean checkout | **PASS** | The full test gate, independent reference, mutation check, quickstart, and source builds passed from a clean checkout at `6db5f2e85b1666a57f851388c2e2ff97b3b413a9`. |
| Public source release | **NO-GO pending owner decisions** | The owner must accept or remediate the author-email disclosure and decide whether the downstream contract detail may be public. No repository visibility change is made here. |
| Python package publication | **Separate decision** | No package is published or approved by this report. |
| Haskell binary publication | **Separate decision; blocked** | The existing dependency provenance and `rts` notice gates remain open. This does not block source-only access. |

## Exposure audit

The audit used Gitleaks 8.30.1 and TruffleHog 3.99.2. The release archives for both scanner binaries were checked against their published checksums. TruffleHog ran with `--no-verification`; this prevented it from sending candidate values to external verification services. Scanner output and downloaded records remain in a local temporary audit directory and are not included in this repository.

The scan covered 60 reachable Git commits, 25 ref names in this checkout that point to commits, 10 remote branch refs, 2 local Codex snapshot refs, 142 tracked paths, 12 pull requests and their 47 commit records, and all 67 available Actions log archives. The ten remote branches have no commits ahead of `main`; the repository has no remote tags. GitHub reports zero Actions artifacts. All 67 runs had completed when the audit closed: 45 succeeded, 18 were cancelled, and 4 failed. The latest `main` Coverage run, `38027864768`, succeeded. The 4 older failures and 18 cancellations do not change this current result.

Gitleaks reported no findings in the reachable Git history, the two local snapshots, pull-request records, or Actions logs. TruffleHog reported zero verified and zero unverified secret findings for those sources. No credential value is included in this report. No credential rotation is indicated by these scans. These tools do not prove that every possible secret or sensitive record has been found.

The GitHub secret-scanning alerts API reported that secret scanning is disabled while the repository is private. This audit therefore does not include GitHub-hosted secret-scanning alerts. After the owner makes the repository public, enable secret scanning and push protection.

### Owner review: commit metadata

Two distinct email addresses and two author display names appear in the reachable commit metadata. The values and names are redacted here. One address uses an individual email-provider domain and appears in 12 commits. The second uses a project-associated domain and appears in 48 commits. Repository evidence does not establish whether the second address is a shared role account or a person's address. A public clone exposes both commit addresses and author names. Treat both addresses as personal-data disclosure items until the owner confirms their intended publication or authorizes history remediation.

Affected commit objects:

```text
e8f923ee909bcc527675cb89fc578e7da8c258f4
e042aded9fd98d22aeb708337a26e9bbc9f2b7b8
35e03fdf4714e792a53ec292f6521de96f787851
e82c459c3de95f8a1adb0475feea70ba29aa77c0
b4e1f85ccc8bc56de8f4b12529cfc4e110ee21c7
46b81c7d1429dc645efafdafcfac35b584ef38b9
79dc40a74dfb6aa6469534ecde14bc80903cb685
49a772eed2591747c99b3af29c6992fda14f120d
7556734a996ef3b1686e224a906781ddb9eb6e20
de61aa87a5f4470fd64de33c926cff7f92cf8bd6
6ba07d119a62fa99cfb9ec875321bff7b4bd57d1
fda9ddb3636f7c8488d5867256f007b1510b67db
```

The other 48 affected commit objects are:

```text
45f5d897d43db5e5e5a66c2dd681252e5a2bbdab
b904752a7ef2225f5333391acd1fb03604054528
c801b42e954b1ac583a18b81c7f2a12189e12400
442df5ecb7572ccf27fffd9fd7fd6a1e7ae0eb27
765228bc00d7f782f80c88cdc2e452b61db8771e
c0f1e01af9f37b75655849ce41a0ea50e67fe2ae
ca72ff036ae6c6a3a6a8001a541611365185a45a
82ed0559d00a84f9970174e7d4c7610877dd10a7
93b2f1d5eeafec5578a2fdc632338f0f6acb0f5e
28204f378f4ccefd5e85a00ef87b396d7f407e11
d2068e662a91ceafe9a99931857f4ae6f2bf120b
fbbc432ab57e07d34b8d6a828a1d977506010ae0
29114fc16171a120f3bc85f646aee37eb869e659
4717f5d1cc202d57fcdc8f61da5de3dc6c7839c8
921219ba59fa6018d6d26ca54ae2115818fcab7b
dcf3d1070186a3f936e17f5975622023c812fc2b
65bc3c3a4d5bbb5d4749957567c4ca4eb483fd46
40528b3ea6989cb9487c9c558fdb278b1567e9d9
83116211c905394e4923c710ce39cd7c4727bca1
8879272624257c9dbd1ec5713aa6874bb29f5530
ec3b1066201a2b54c1f392eee356b97bfd28a943
25117c65f2e0583318292c90eeefdbc37aaf0f86
47d55e1e7fa10348d4a39679add3590edfe8233b
ce89042b84f2d39cb9bebf296eaa9d66622281d9
69f2c87ed6e98c181b3afcac976e70637d7d113b
6b48f6c45900077b5c2bb79586d8297fb541d3a0
e0533232e05bf4974d63a5517b2cb82b3a29a7ef
cad6943ce19bc4b0439cd85332ed632ee17f3a9f
a97201d2a3b5db6ba0e4514da3d2b63696bf9bf7
f5733d5ab61f4710756d3f6f178833fd501bbb76
03751e4a3a234c00360c9e6ddf36b6f742b0e3b3
f98200cb4e0ae3f93bf04b9b0ee163b80604636f
3b802a33acbb501ec4a4bcc3874e202322c41a8f
0d4aea76e1cc80dc663ecf8471e232a5c57ed921
67bdf5cbddf34b87433dfda9da34e1bb952dd0f4
2f01fb4da53b4e17483c6f0f792ce9fc6e1c10fc
8e4d88f4311a637281711501837438ae2ef0cdef
26c0132ec709d3bfd2bb43c42818dc2458e7fed0
ab5185dfd70d2ae18f5b5e266682830eb9454064
fb9161300f3671536caf55e3cafad7bd849b9b23
af0d9cf855ff344554cd90ecf3a2f5f3bc0d9f58
02f514be3b5580ba6d264995b306cf1c2f1fa690
7a36e2a43a5fa59d6647804f68157b3e1ec21aec
d79003d42637517934c90678ba21ab4e82768544
4171059f185bed6ea1b637c939c5fd135c1a9ad7
facebfa324b6f6d79a8636744c89694d47b866bc
fc716c3da3437d638a3f89a8480758358e67f38d
683c17ecab794e64d52097dbc028fedd3dc28b02
```

All 47 commits returned by the pull-request API use the second address. No email address was found in reachable file contents or in pull-request descriptions, comments, or Actions logs. GitHub Actions logs contain standard `/home/runner/...` paths; these are runner paths, not local machine paths.

### Owner review: downstream contract detail

The tracked plan contains a detailed, project-specific downstream eligibility contract. The exact criteria are not repeated here. The text is in [`specs/001-semantic-oracle-v0-1/plan.md`](../specs/001-semantic-oracle-v0-1/plan.md), introduced in commit `683c17ecab794e64d52097dbc028fedd3dc28b02`. The README in commit `fda9ddb3636f7c8488d5867256f007b1510b67db` also names the downstream project; that name alone is a reference, not a secret. No credentials, private data, or copied executable source from that project were found.

The owner must decide whether the detailed plan may be public. If it is private, a normal documentation edit will not remove it from earlier commits. No history rewrite was done. The owner must approve any history-remediation plan.

### Harmless development references

`assurance/assurance-certificate.json` contains an absolute local build path in several historical versions. The username and full path are omitted here. The affected file revisions include commits `ca72ff036ae6c6a3a6a8001a541611365185a45a`, `4717f5d1cc202d57fcdc8f61da5de3dc6c7839c8`, `921219ba59fa6018d6d26ca54ae2115818fcab7b`, and `65bc3c3a4d5bbb5d4749957567c4ca4eb483fd46`. This is local build metadata, not a credential or private configuration. It does not require credential rotation. The path is retained in the historical assurance record; this report does not rewrite that evidence.

The old `codex/...` remote branch names are internal development labels. Every remote branch is merged into `main`, and none contains extra commits. They do not contain branch-only source. The owner may remove these refs as repository housekeeping before changing visibility.

## Licensing and source contents

The root `LICENSE`, Python package license, Python project metadata, and Cabal metadata identify Semadmit as Apache-2.0. The root and Python license files are byte-identical. No separate Semadmit copyright header is present in the source files; this audit does not infer a legal copyright owner from contributor metadata. The owner selected Apache-2.0 for Semadmit source. The source tree does not vendor Haskell dependencies; the locked dependency graph is resolved by Cabal. The Python package has no runtime dependencies and pins Setuptools as a build dependency.

The `.agents/commands/` files closely follow Spec Kit `v1.0.13` command templates. `.specify/scripts/bash/`, `.specify/templates/`, `.specify/workflows/speckit/`, and `.specify/.gitignore` include exact or adapted upstream files. This PR adds the upstream MIT copyright and license notice in [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md). The notice applies to Spec Kit-derived portions only. The Semadmit source remains Apache-2.0. The RFC 8785 fixture records its source URL and contains published examples; the Isoprax integration record describes an independent implementation, not copied source. No other vendored third-party source or data requiring an added license notice was identified in the tracked tree. See the [Apache-2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html) and the [Spec Kit v1.0.13 license](https://github.com/github/spec-kit/blob/v1.0.13/LICENSE).

The existing Haskell dependency inventory still blocks Haskell executable distribution. Its `rts` notice obligations and some provenance work are not requirements for publishing this source repository, because this PR does not include those dependency sources or distribute a binary. The artifact certificate has an offline verifier that rebuilds from a selected source revision, but it does not establish signed or authenticated CI provenance. The writer and verifier also share build code. These gaps remain future assurance work; they do not by themselves prevent source disclosure.

## CI and repository settings

The Coverage workflow grants `contents: read`, uses external actions pinned to full commit SHAs, and runs on `pull_request`, `push` to `main`, and manual dispatch. It does not use `pull_request_target` or repository secrets. This PR also disables checkout credential persistence because the workflow does not push changes.

After the visibility change, the owner should:

- Protect `main`; require a pull request, the Coverage check, and at least one approving review.
- Dismiss stale approvals, require conversation resolution, and block force pushes and branch deletion.
- Enable private vulnerability reporting and publish `SECURITY.md` as the reporting policy.
- Confirm secret-scanning alerts are active, enable push protection and Dependabot alerts, and review alerts before and after the visibility change.
- Limit Actions permissions to the minimum required and keep external actions pinned to full commit SHAs.

GitHub documents [secret-scanning availability](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning), [private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository), and [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches). The current private-repository API could not show branch-protection settings because the account plan does not allow that query. This PR does not change repository settings.

## Validation record

Validation ran in a fresh detached checkout at `6db5f2e85b1666a57f851388c2e2ff97b3b413a9` with CPython 3.13.14, GHC 9.14.1, Cabal 3.18.1.0, and uv 0.11.31.

- `python3 scripts/check_coverage.py`: **PASS**. All 59 Python package tests, 7 independent-reference tests, and 20 certificate tests passed. All 9 Python modules met the 100% executable-line threshold (1,679/1,679). All 7 Haskell test suites passed. Haskell coverage was 5,318/5,859 expressions (90.77%) and 90/193 boolean outcomes (46.63%).
- `env PYTHONPATH=clients/python python3 -m unittest assurance.test_reference_core -v`: **PASS**, 7 tests.
- `python3 assurance/mutation_check.py`: **PASS**, 7/7 selected Python Core mutations killed. This mutation check does not mutate Haskell source.
- `env PYTHONPATH=clients/python python3 examples/claim_quickstart.py`: **PASS**. It showed the valid, invalid, and indeterminate outcomes; verification rejected the changed decision digest.
- `env PYTHONPATH=clients/python python3 -m unittest clients.python.tests.test_claim_result_compatibility -v`: **PASS**, 4 tests. The fixture still pins `de61aa87a5f4470fd64de33c926cff7f92cf8bd6`.
- `uv build --index-url https://pypi.org/simple --out-dir /tmp/semadmit-public-audit/python-dist clients/python`: **PASS**. It built a source archive and wheel using the public PyPI index. The artifacts remain in a temporary directory and were not published.
- `cabal test all --enable-coverage --test-show-details=direct --offline`: **PASS**, all 7 Haskell suites.
- `cabal build exe:semantic-oracle --offline`: **PASS**. The locked Haskell dependency graph resolved from the local public Hackage cache without network access. The Python package has no runtime dependencies; its build used the public PyPI index for its build backend.
- `git diff --check`: **PASS** before commit. The checkout was clean after validation.

The readiness report was updated after this validation. That follow-up changes documentation only; no evaluator, protocol, fixture, or build-workflow code changed after the tested commit.

These checks establish only the named local behavior. They do not establish general correctness, scientific validity, evidence authenticity, signed build provenance, cross-platform support, package approval, or binary approval.
