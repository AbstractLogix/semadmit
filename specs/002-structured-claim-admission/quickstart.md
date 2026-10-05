# Quickstart and Validation Guide

## Evaluate a Claim

Create `ClaimEngine` in a Python host and call `evaluate` with a `semadmit/claim/0.1` request. The result contains separate verification and admission statuses, a verification artifact and digest, and the generic Core decision.

Use `claim_jsonl_runner()` when the host needs one JSON request and result per line. The runner uses the existing input-size and JSONL framing limits.

The first verifier accepts one deterministic execution trace. It does not execute the function. `VALID` applies only to a complete finite domain named by the request.

## Local Validation

Run the focused claim checks:

```sh
PYTHONPATH=clients/python python3 -m unittest clients.python.tests.test_claim_verification -v
```

Run the repository's maintained gate:

```sh
python3 scripts/check_coverage.py
```

The claim fixtures are in `conformance/fixtures/claim-verification-cases.json`. A Bouleusis-style host can call the local `semantic-oracle --jsonl` process for the Isoprax pack. Its request fixtures and CLI checks are in `conformance/fixtures/isoprax-cases.json` and `test/integration/isoprax/`.

Local results do not establish hosted CI, source truth, statistical independence, formal proof, or production use.
