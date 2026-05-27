# App Plan Status Audit

> Status: active audit, 2026-05-22

The app-specific plan is
[`2026-05-12-mac-app-implementation-plan.md`](./2026-05-12-mac-app-implementation-plan.md).
It is not ready for archive because it still contains outstanding app work.

## Implemented Or Mostly Implemented

- Phase 0: Tauri app shell exists under `app/`.
- Phase 1: operations artifacts and daily status pipeline exist under
  `scripts/ops/`, `signals/`, and `runs/operations/`.
- Phase 2: scheduler, job records, LaunchAgent install/load/unload plumbing,
  and app controls exist.
- Phase 3: notification outbox and macOS send path exist.
- Phase 4: app dashboard exists, reads status, embeds the viz, and exposes
  operational controls.
- Phase 5: live holdout reporting exists.
- Phase 6: governance reporting exists.
- Phase 7: research queue, bounded research-run artifacts, richer queue
  metadata, generated hypothesis artifacts, and app enqueue/start/pause/inspect
  controls exist.
- Phase 8: strategy ideation now reads current signal warnings, recent movement,
  timing misses, near-Gold autopsies, live holdout drift, family concentration,
  and Confidence-related diagnostics into reviewable bounded proposals.
- Phase 9: packaging is implemented. A signed local app candidate was installed
  to `/Applications/Montauk.app`, runtime strategy is documented, update path is
  defined, and operations artifacts stamp app/strategy version metadata.
- Phase 10: hardening is implemented for the current app plan. Structured error
  codes, app smoke checks, operations fixtures, fresh-shell scheduler probes,
  stale/network/holiday/DST hardening probes, and failed-job record checks exist.

## Still Outstanding

- No unchecked items remain in the app-specific implementation plan. Future
  hardening should be opened as a new plan if it expands beyond the current
  acceptance criteria.

## Disposition

The app plan can be archived after final review, or split into a new follow-up
plan if additional production hardening is desired.
