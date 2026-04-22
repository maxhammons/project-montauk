# /gojo task — argus-remediation: Duplicate authority-writing and replay paths

## Context
Source: Argus Deep Mode — Apr-22
Severity: High
Specialist: Pragmatist
Adversarial status: proven
Finding: Multiple scripts can admit, rewrite, rebuild, or replay trust-bearing state around `spike/leaderboard.json`, so authority does not have one owner.

## Files
- Modify: `scripts/search/evolve.py`
- Modify: `scripts/certify/recertify_leaderboard.py`
- Modify: `scripts/certify/backfill_artifacts.py`
- Modify: `scripts/certify/full_sweep.py`
- Modify: `scripts/certify/certify_champion.py`

## Do
Collapse all leaderboard admission and rewrite behavior behind one canonical authority path.
Make recertification, backfill, and sweep utilities consume that contract instead of independently mutating trust-bearing fields or re-deciding eligibility.
Preserve the existing maintenance behaviors, but force them to route through the same admission logic.

## Do Not Touch
- Do not edit unrelated strategy search heuristics or scoring code.
- Do not make side-path scripts invent new eligibility rules.
- Only modify the files listed in `## Files`.

## Acceptance
- [ ] One module owns all authority-bearing leaderboard writes.
- [ ] Maintenance and replay utilities no longer make independent eligibility decisions.
- [ ] The canonical admission contract is reused everywhere trust-bearing state changes.
- [ ] Tests pass.

## Risk
High

## Argus Reference
Report: `.argus/runs/argus-2026-04-22T21-14-17Z/argus-elevation.md` — Blocker #2
Evidence: `.argus/runs/argus-2026-04-22T21-14-17Z/execution-verdicts.md`, `.argus/runs/argus-2026-04-22T21-14-17Z/poc-soft-admission.py`, `.argus/runs/argus-2026-04-22T21-14-17Z/poc-maintenance-backfill.py`
