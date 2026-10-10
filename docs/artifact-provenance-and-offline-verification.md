# Artifact Provenance and Offline Verification

This record defines the scope of assurance certificate format
`semadmit-assurance-certificate/0.2`. It does not change
`semantic-oracle/0.1`, `semadmit/claim/0.1`, or any admission rule.

## Trust model

| Property | What the check establishes | What it does not establish |
| --- | --- | --- |
| Artifact byte identity | SHA-256 and size identify the supplied bytes. | A hash written by a caller does not prove who built the file. |
| Source-to-artifact reproducibility | The offline verifier builds each artifact again from the externally selected Git commit and compares exact bytes under the recorded toolchain and locks. | It does not prove that another toolchain or platform produces the same output. |
| Authenticated build provenance | Not established by this certificate. The CI run identity is recorded and checked while the certificate is written, then labelled `recorded-unverified`. | Offline checking cannot authenticate the CI provider, workflow identity, or build worker. |
| Functional or scientific correctness | The named test and mutation gates ran and their structured results match a rerun. | This does not prove general correctness, evidence authenticity, scientific validity, or claim truth. |

The trusted inputs are the full source revision supplied separately to the
verifier, the matching local Git commit and tree, the installed verifier, the
recorded Python/GHC/Cabal/uv versions, the pinned dependency inputs, and the
offline dependency caches. The repository certificate is not a signing key.
Its declarations are checked against those external inputs and a new build.

The builder exports the requested commit into a new temporary source tree. It
runs the coverage, corpus, and mutation gates there. It then builds the Python
wheel and normalized source archive and the Haskell executable and source
archive. Cabal and uv run in offline mode. The build uses the host's installed
toolchains and dependency caches. It is a clean-source rebuild, not a
hermetic container build.

## GitHub attestations

GitHub documents offline verification for artifact attestations, but this
repository's current local GitHub CLI is version 2.4.0 and has no
`attestation` command. The organization plan could not be queried with the
available credentials. GitHub documents attestation support for private
repositories on Enterprise Cloud; public-repository support is broader. The
current certificate therefore uses the reproducible-build fallback and does
not claim an authenticated attestation. See the [GitHub attestation
availability](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
and [offline verification instructions](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline).

The recorded Coverage run must be successful and match the exact source
revision when the certificate is written. The offline verifier checks its
recorded shape, workflow, and source SHA. It cannot independently authenticate
that record. A future authenticated-attestation path needs a supported GitHub
plan, a trusted attestation bundle, and a verifier that checks that bundle
against a trusted root.

## Commands

Create a certificate from a clean checkout at the exact source revision and a
completed Coverage run:

```sh
python3 -m assurance.write_certificate \
  --source-revision <full-git-sha> \
  --ci-run-url https://github.com/AbstractLogix/semadmit/actions/runs/<run-id> \
  --artifacts-dir /tmp/semadmit-build-artifacts
```

The writer hashes the lock files, build scripts, normalizer, Coverage workflow,
and dependency inventory. It creates all four artifacts. It does not accept
artifact paths from the caller.

Verify the certificate without network access. The verifier reads the source
commit from the local Git object store, rebuilds into a new temporary
directory, reruns the gates, validates archive structure, and compares each
supplied file with the rebuild:

```sh
python3 -m assurance.verify_certificate \
  --certificate assurance/assurance-certificate.json \
  --source-revision <full-git-sha> \
  --haskell-executable /path/to/semantic-oracle \
  --haskell-source-archive /path/to/semantic-oracle-0.1.0.0.tar.gz \
  --python-wheel /path/to/semadmit-0.1.0.dev0-py3-none-any.whl \
  --python-source-archive /path/to/semadmit-0.1.0.dev0.tar.gz
```

The source SHA is an external input. The verifier rejects a certificate that
names another revision, a different Git tree or lock input, altered
validation results, an invalid provenance label, a missing artifact, or any
artifact whose structure, size, or bytes differ from the rebuild. Duplicate
JSON keys and truncated JSON also fail.

## Tested attack cases

The assurance test suite checks these cases:

| Attack | Result |
| --- | --- |
| Replace a generated wheel with arbitrary caller bytes | Rejected by wheel structure and byte comparison. |
| Replay a certificate against another expected revision | Rejected before rebuilding. |
| Truncate the certificate JSON | Rejected during parsing. |
| Omit an artifact path | Rejected. |
| Change the declared source tree or locked input digest | Rejected against the Git revision. |
| Change a recorded test result or remove a mandatory gate | Rejected against rerun results. |
| Mark provenance authenticated or change the CI source SHA | Rejected. |
| Change a certificate artifact digest | Rejected against the clean-source output. |

These are tested cases, not a claim that every certificate attack is
prevented. In particular, unauthenticated CI metadata can only be checked for
internal consistency offline. A trusted signature or authenticated
attestation is required to establish who ran the CI workflow.

## Separate distribution assessment

| Distribution | Assessment | Open gates |
| --- | --- | --- |
| Python | Ready for owner review, not approved for release. | Independent human review and the owner's release decision. The supported build target is CPython 3.13 on the tested Linux x86_64 toolchain. |
| Haskell | Blocked. | The `rts` Apache-2.0 notice bundle and remaining dependency provenance still need review. The qualified binary target is Linux x86_64 only. |

The Python-only qualification for `semadmit/claim/0.1` remains in force.
`selector-provenance/0.1` remains experimental. Bouleusis remains pinned to
`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. No package is published or
approved by this record. Independent release approval is absent.
