# /gojo task — argus-remediation: Broken certification invariant

## Context
Source: Argus Deep Mode — Apr-22
Severity: Critical
Specialist: Exploiter
Adversarial status: proven
Finding: Post-hoc finalization can set `backtest_certified=True` on a `WARN` row without preserving Gate 7's intended invariant.

## Files
- Modify: `scripts/search/spike_runner.py`
- Modify: `scripts/certify/backfill_artifacts.py`
- Modify: `scripts/certify/certify_champion.py`

## Do
Make `_finalize_champion_certification()` preserve the Gate 7 contract instead of recomputing `backtest_certified` from artifact checks alone.
Require `promotion_ready` and the required certification checks to be consistent before any path can mint `backtest_certified=True`.
Keep `validation`, `gate7`, and the champion summary synchronized from one authoritative contract.

## Do Not Touch
- Do not change unrelated search, certification, or viz logic outside the files listed in `## Files`.
- Do not broaden the fix into leaderboard redesign work.

## Acceptance
- [ ] A `WARN` champion cannot end with `backtest_certified=True`.
- [ ] `gate7`, `validation`, and `validation_summary` agree on `promotion_ready` and `backtest_certified`.
- [ ] The backfill and champion certification paths both preserve the same invariant.
- [ ] Tests pass.

## Risk
High

## Argus Reference
Report: `.argus/runs/argus-2026-04-22T21-14-17Z/argus-elevation.md` — Blocker #1
Evidence: `.argus/runs/argus-2026-04-22T21-14-17Z/execution-verdicts.md`, `.argus/runs/argus-2026-04-22T21-14-17Z/poc-broken-invariant.py`
