# 2026-04-27 Cleanup Archive

This archive preserves files moved out of active Project Montauk surfaces during the
April 27 cleanup. Nothing was deleted.

## Contents

- `argus/.argus/` — completed Argus reports, PoCs, and remediation briefs.
- `root/argus-remediation-python.md` — implemented/obsolete root remediation note.
- `spike-backups/` — old leaderboard backups, sweep outputs, historical rescoring
  output, and the pre-cleanup active leaderboard.
- `stale-runs/` — run artifact bundles whose validation payloads contained the
  stale contradiction `promotion_ready=false` with `backtest_certified=true`.

## Active State After Cleanup

- `spike/leaderboard.json` was rebuilt from the archived original with only
  `certified_not_overfit=true` rows.
- The active `spike/runs/` folder no longer contains the known stale
  certification artifact bundles.
