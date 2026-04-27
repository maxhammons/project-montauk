# /gojo task — argus-remediation: Fused memory and authority surface

## Context
Source: Argus Deep Mode — Apr-22
Severity: High
Specialist: Futurist
Adversarial status: confirmed
Finding: `spike/leaderboard.json` is acting as durable memory, ranking surface, and downstream authority source at the same time, even though the stored rows do not all carry the same trust level.

## Files
- Modify: `scripts/search/evolve.py`
- Modify: `scripts/certify/backfill_artifacts.py`
- Modify: `scripts/certify/full_sweep.py`
- Modify: `scripts/certify/recertify_leaderboard.py`
- Modify: `viz/build_viz.py`

## Do
Split durable evidence from authority-bearing state.
Keep the canonical certification evidence immutable, derive leaderboard and watchlist views from that evidence, and make the viz and maintenance surfaces consume derived views rather than treating the leaderboard file as both ledger and contract.

## Do Not Touch
- Do not change unrelated UI layout or chart behavior.
- Do not mutate legacy data outside the existing derivation and backfill paths.
- Only modify the files listed in `## Files`.

## Acceptance
- [ ] Authority-bearing writes come from a single evidence-backed path.
- [ ] Derived views render without implicitly re-certifying legacy rows.
- [ ] The viz surface no longer depends on mutable trust semantics in the leaderboard file.
- [ ] Tests pass.

## Risk
High

## Argus Reference
Report: `.argus/runs/argus-2026-04-22T21-14-17Z/argus-elevation.md` — Blocker #3
Evidence: `.argus/runs/argus-2026-04-22T21-14-17Z/execution-verdicts.md`, `.argus/runs/argus-2026-04-22T21-14-17Z/poc-maintenance-backfill.py`
