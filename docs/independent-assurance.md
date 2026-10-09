# Independent Core Assurance

This record adds an independent reference for a bounded part of
`semantic-oracle/0.1`. It does not change the wire protocol, the
`semadmit/claim/0.1` contract, or `selector-provenance/0.1`.

The stable Bouleusis claim pin remains
`de61aa87a5f4470fd64de33c926cff7f92cf8bd6`. Claim qualification, Core
cross-language conformance, and release approval are separate results.

## Guarantee Matrix

| Property | Normative source | Executable evidence | Limit |
| --- | --- | --- | --- |
| Input validity | [Wire protocol](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md), request envelope and error precedence | Python and Haskell run the same 68 raw parser cases, including 65 error envelopes: 17 reviewed errors plus 48 seeded mutations. Python also checks bounded direct-object copying. | The raw mutations cover trailing data, number-profile failures, and duplicate keys. They do not qualify every parser precedence pair, pointer, CLI frame, or resource boundary. |
| Artifact identity | [Pack interface](../specs/001-semantic-oracle-v0-1/contracts/pack-interface.md), request identity; [wire protocol](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md), decision digest | Independent safe-integer JCS encoder; 9 reviewed M0 identity vectors; one selected RFC 8785 property-order vector; 57 exact Core result vectors. | The oracle supports only the common safe-integer JSON profile and the test-only `fixture/0.1/check` pack. |
| Canonical serialization | [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) and the Semadmit number profile | Hand-derived UTF-8 and digest example, reviewed M0 bytes, and the selected RFC 8785 vector. The reference uses only Python's standard library and does not import Semadmit production identity code. | The oracle rejects floating-point values. It is not a general-purpose RFC 8785 library. |
| Deterministic result verification | [Wire protocol](../specs/001-semantic-oracle-v0-1/contracts/wire-protocol.md), decision verification | Reference reevaluation and exact canonical-result comparison; Python `Evaluator.verify_result`; request, content, policy, operation, and digest substitutions. | This verifies result consistency for the supplied request. It does not verify the executing binary or source evidence. |
| Operation-specific admission | [Decision tables](../specs/001-semantic-oracle-v0-1/contracts/decision-tables.md), state resolution | The test-only fixture pack exercises all three states and failure-over-missing reduction. Claim results remain separately checked by Python tests. | The reference does not implement claim, Isoprax, selector, or Measurement semantics. No universal evidence-combination engine is present. |
| Evidence authenticity | [Threat model](../specs/001-semantic-oracle-v0-1/contracts/threat-model.md) | No authenticity guarantee is claimed. | A digest binds content to an identity declaration. It does not authenticate a source or collector. |
| Evidence reliability | Threat model and operation-specific contract | No reliability guarantee is claimed. | A passing admission result does not prove that evidence is reliable. |
| Claim truth | Claim and operation contracts | No truth guarantee is claimed. | Admission only says whether evidence may participate in the named operation under the declared policy. It does not determine what Bouleusis must believe. |

## Test Corpus

The shared Core corpus keeps the original nine reviewed examples and adds 48
valid requests generated with seed `20261009`. The independent reference
creates their expected results. The production Python evaluator does not
create oracles. Both Python and Haskell compare complete results and error
envelopes with the committed values.

The generated requests vary the five supported fixture states, Unicode subject
text, evidence identity, evidence content, and evidence order. The test
`assurance.test_reference_core` also runs 96 fixed-seed Python differential
cases. Metamorphic checks cover object-key order, evidence-set order, composed
and decomposed Unicode, content changes, repeated evaluation, operation
substitution, request/result substitution, and result-digest changes.
The Python-only claim suite also changes evidence IDs and assumptions inside a
valid `VALID`/`ADMISSIBLE` result and confirms that verification fails. The
selector suite confirms all four independence examples remain `indeterminate`
without adding an independence permission rule.

The shared parser corpus adds 48 fixed-seed raw inputs: 16 trailing-data cases,
16 fractional/exponent/unsafe-integer cases, and 16 duplicate-key cases. Both
language parsers return the exact expected error envelope. Existing reviewed
cases continue to cover invalid UTF-8, unpaired surrogates, negative zero, and
the principal safe-integer boundary.

The mutation check applies seven controlled source changes to the Python Core:

- Weaken exact result comparison.
- Remove request binding from the digest.
- Skip policy-digest verification.
- Remove policy content from request identity.
- Remove failure priority from state reduction.
- Accept an unsupported protocol.
- Weaken the closed internal-error envelope.

All seven mutants are killed by the named Core assurance tests. This is a
100% score for this selected set only. Haskell source mutations are not run.
This score is not a measure of formal correctness or total defect coverage.

## Reproduction

Use CPython 3.13.14, GHC 9.14.1, and Cabal 3.18.1.0 on the recorded Linux
x86_64 host.

```bash
python3 -m assurance.generate_corpus --check
PYTHONPATH=clients/python:clients/python/tests python3 -m unittest \
  test_vertical_slice test_json_input test_claim_verification \
  assurance.test_reference_core -v
python3 -m assurance.mutation_check
cabal test vertical-slice protocol-contract --test-show-details=direct
python3 scripts/check_coverage.py
```

The machine-readable evidence is in
[`assurance-certificate.json`](../assurance/assurance-certificate.json). It
records the implementation commit, corpus digests, toolchain, test counts,
mutation results, local build hashes, CI evidence, and unsupported guarantees.
The certificate writer reruns the corpus, mutation, test, and coverage gates;
it derives test counts and mutation outcomes from those runs. A hosted pass is
read from GitHub Actions and bound to the validation commit. The certificate
is a reproducible report, not a signature or independent approval.

## Research Artifact Description

**Title:** Semadmit Core Conformance Oracle and Assurance Corpus, version 0.1.

**Scope:** An independent Python reference for the shared Core identity,
binding, deterministic result, and error behavior used by the test-only
`fixture/0.1/check` operation; plus fixed-seed exact-output vectors consumed
by Semadmit's Python and Haskell Core implementations.

**Method:** The reference follows the frozen Core wire contract and decision
tables. It uses hand-derived examples, reviewed RFC and M0 canonical-byte
vectors, deterministic generated requests, parser mutations, metamorphic
checks, and seven controlled Python source mutants. Expected Core results are
computed by the reference implementation, never by the production evaluator.

**Limits:** The artifact does not qualify every Core input or every error
precedence rule. It does not implement claim, Isoprax, selector, or Measurement
semantics. It does not prove evidence authenticity, evidence reliability, claim
truth, or release readiness. Independent human review remains open.

**Suggested citation:** Semadmit Project. (2026). *Semadmit Core Conformance
Oracle and Assurance Corpus* (v0.1), source commit recorded in
`assurance/assurance-certificate.json`, AbstractLogix/semadmit. Use the
immutable GitHub commit permalink in that certificate. No DOI or peer-review
status is claimed.

## Remaining Gates

| Area | Current state | Open work |
| --- | --- | --- |
| `semadmit/claim/0.1` | Qualified, Python-only | No Haskell claim-pack parity is claimed. |
| Core parity | Qualified only for named, bounded semantics | Complete parser precedence, broader errors, resource limits, CLI parity, and all-pack conformance remain open. |
| `selector-provenance/0.1` | Experimental; independence outcomes remain indeterminate | Do not add positive independence permission without qualifying Isoprax evidence. |
| Python package distribution | Not approved | Review the exact Python artifacts and obtain a separate owner release decision. |
| Haskell distribution | Not ready | Resolve and approve the `rts` Apache-2.0 notice obligations and full distribution notice set. |
| Dependency provenance | Partial | Establish remaining source-repository provenance and independent archive/source review. |
| Independent release review | Open | A human who did not author the change must review exact source and distribution evidence. |
| Release decision | Open | The owner must approve each proposed distribution separately. No package is published by this work. |
