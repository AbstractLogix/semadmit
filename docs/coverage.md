# Source Coverage Gates

Run `python3 scripts/check_coverage.py` to use the coverage gate. Local pre-commit and GitHub Actions run this command. It runs the Python unit tests and all Cabal test suites with coverage. It fails if a test, measurement, or threshold fails.

## Thresholds

| Implementation | Measured metric | Minimum |
|---|---|---:|
| Python | Executable source lines in every `clients/python/semadmit` module | 100% |
| Haskell | HPC expression points across production modules | 89% |
| Haskell | HPC boolean outcomes across production modules | 34% |

## Recorded Baseline

The latest gate run was measured on 2026-10-04 with the pinned toolchain. All 29 Python tests passed. They covered 792 of 792 executable lines across 7 modules. All 7 Haskell test suites passed, including `Core.CLI` framing and exit-code cases, every Isoprax pool fixture through the first-party application runner, subject parsing and identity sidecars, exact calibration calculations, and legacy number conversion. HPC measured 5,312 of 5,861 expression points (90.63%) and 88 of 193 boolean outcomes (45.60%). Alternative coverage is reported for review but is not a gate.

Python uses the Python 3.13 standard-library `trace` module. This metric covers executable lines, not branches. Haskell uses GHC HPC expression and boolean coverage. It excludes test entrypoint modules and measures the first-party application entry module through the Isoprax CLI suite. These metrics are separate and are not comparable.

The gate requires a measurement for every Python source module, every production Haskell module under `src/` or `app/`, and a fresh HPC file for each maintained Haskell test suite. The gate fails closed if evidence is missing.

These floors preserve the first measured baseline for the current Core implementation. Raise thresholds when coverage improves. Do not lower a threshold without updating the requirement and recording the reason in the release-readiness review.

## Local Hook

Install the hook manager once. Then install the repository hook:

```sh
uv tool install pre-commit==4.6.2
pre-commit install
```

The hook runs the full test and coverage gate at each commit. To run the gate directly, use:

```sh
python3 scripts/check_coverage.py
```

## Hosted Gate

`.github/workflows/coverage.yml` runs the same command on pull requests and pushes to `main`. Configure the repository ruleset or branch protection to require the **Coverage** check before merge. The workflow file cannot set repository-host protection settings by itself.
