# Contributing

Semadmit is an experimental project. Keep changes small and keep each claim within tested scope.

## Before you change a protocol

The Core protocol is `semantic-oracle/0.1`. The Python claim protocol is `semadmit/claim/0.1`. Treat both as versioned interfaces. Do not change a field, digest rule, result shape, or meaning under an existing version without a compatibility review. Propose an incompatible change as a new protocol version with a migration note and test vectors.

The claim protocol is supported by Python only. The Haskell implementation covers selected Core semantics. Do not claim claim-pack parity. The `selector-provenance/0.1` pack is experimental. It does not establish independence or allow positive independent-corroboration admission.

## Tests and conformance vectors

Run the maintained gate from the repository root:

```sh
python3 scripts/check_coverage.py
```

Add vectors when they test a distinct contract rule or a likely cross-language disagreement. Each vector must include its complete request and expected result. Include negative cases for invalid input and unsupported behavior. Keep Python and Haskell exact-output vectors limited to semantics both implementations claim to support. A mismatch is a failure; do not weaken expected results to hide it.

Run the [quickstart](README.md#quickstart) after changing the public API or claim protocol. Do not use test success as proof of claim truth, evidence authenticity, or scientific validity.

## Bugs and pull requests

For a bug report, include the Semadmit revision, runtime version, a minimal request with invented or public data, the command you ran, and the expected and actual result. Remove keys, tokens, private paths, personal data, and private downstream details.

For a pull request:

1. State the problem and the smallest change that fixes it.
2. Name each changed protocol or pack and say whether it is stable or experimental.
3. Add or update tests and conformance vectors for changed behavior.
4. Update the relevant protocol, contributor, or assurance documentation.
5. Run `python3 scripts/check_coverage.py` and include its result.

Do not include generated binaries, private evidence, credentials, or unrelated repository data. Do not change the Bouleusis compatibility pin as part of an unrelated change.

## Review policy

Submit changes through a pull request. Maintainers should review protocol changes and require the Coverage check before merge. A passing automated check does not replace review of protocol compatibility or release claims.
