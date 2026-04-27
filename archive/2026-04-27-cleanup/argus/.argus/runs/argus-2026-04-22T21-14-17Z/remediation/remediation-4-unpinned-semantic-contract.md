# /gojo task — argus-remediation: Unpinned semantic contract

## Context
Source: Argus Deep Mode — Apr-22
Severity: High
Specialist: Craftsman
Adversarial status: moderate
Finding: The repo lacks fixture-level tests and explicit exported language that pin the allowed relationship between leaderboard eligibility, `promotion_ready`, `backtest_certified`, and champion finalization.

## Files
- Modify: `tests/test_regression.py`
- Modify: `scripts/search/evolve.py`
- Modify: `scripts/certify/certify_champion.py`
- Modify: `scripts/certify/recertify_leaderboard.py`
- Modify: `scripts/README.md`
- Modify: `docs/pipeline.md`

## Do
Add fixture-level semantic tests that lock the allowed relationship between `promotion_ready`, `backtest_certified`, leaderboard eligibility, and champion finalization.
Export the contract in one documented place and make both promotion and recertification code import it instead of duplicating assumptions.

## Do Not Touch
- Do not expand the test suite into unrelated strategy behavior.
- Do not rewrite docs beyond the contract language needed to pin the semantics.
- Only modify the files listed in `## Files`.

## Acceptance
- [ ] A WARN-row certification or eligibility mismatch fails tests.
- [ ] The contract appears in one documented location and is reused by code paths that enforce it.
- [ ] Promotion and recertification paths agree on the same rule text and behavior.
- [ ] Tests pass.

## Risk
High

## Argus Reference
Report: `.argus/runs/argus-2026-04-22T21-14-17Z/argus-elevation.md` — Blocker #4
Evidence: `.argus/runs/argus-2026-04-22T21-14-17Z/execution-verdicts.md`
