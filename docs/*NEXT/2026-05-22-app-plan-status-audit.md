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
- Phase 7: research queue and bounded research-run artifacts exist.

## Still Outstanding

- Phase 8: strategy ideation loop is only partially present. The queue can
  generate proposals from existing artifacts, but there is not yet a broader
  controlled ideation layer that reads the full diagnostic set and proposes
  reviewable strategy tests as a normal app workflow.
- Phase 9: packaging is partial. A local macOS bundle exists, but the update
  path, version stamping into operations artifacts, and clean-install/runtime
  dependency strategy still need to be finished and documented.
- Phase 10: hardening is partial. Job locks, stale-lock recovery, immutable
  signal snapshots, Doctor checks, and maintenance flow exist, but app smoke
  tests, operations fixtures, fresh-shell verification, no-network/partial-
  network behavior, DST handling, and market-holiday behavior are not complete.

## Disposition

Keep the app plan active in `docs/*NEXT/`. Do not move it to
`docs/*NEXT/archive/` until phases 8-10 are either implemented or split into
new active follow-up plans.
