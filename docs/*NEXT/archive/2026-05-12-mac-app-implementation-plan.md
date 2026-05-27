# Montauk Mac App Implementation Plan

> Status: active mixed-status plan, 2026-05-12. Audited 2026-05-22:
> phases 0-9 are implemented or mostly implemented; phase 10 remains
> outstanding or partial. See
> [`2026-05-22-app-plan-status-audit.md`](./2026-05-22-app-plan-status-audit.md).
>
> Checklist audit: 2026-05-23. Checked items were verified from repository
> files, current artifacts, Doctor/scheduler status, LaunchAgent status, and
> `tests/test_ops.py`. Unchecked items are missing, superseded, or not
> verifiably complete.

This plan turns the app charter into buildable work. The target is a standalone
macOS app that runs the Montauk Engine in the background, keeps data and signals
current, schedules validation and research, and notifies the user when the
system state changes.

The app should wrap the existing Python engine. It should not rewrite strategy
logic.

---

## Phase 0 — Decide The App Shell

Default recommendation: use a Tauri desktop shell with a lightweight frontend
and Python sidecar commands.

2026-05-12 implementation slice:

- [x] chose the Tauri direction for the first app shell
- [x] scaffolded `app/`
- [x] added static dashboard assets under `app/src/`
- [x] added Tauri bridge commands under `app/src-tauri/`
- [x] installed app dependencies locally
- [x] verified the Vite app build and native Tauri bundle build

Reason:

- the existing visualization is already HTML/JS
- the Python engine can remain untouched
- Tauri can package a small macOS app without bringing in a heavy runtime
- native notifications, menu bar, and background command execution are reachable

Fallback: SwiftUI if deeper native macOS integration becomes more important
than reuse of the current web visualization.

Deliverables:

- [x] create `app/` for the desktop shell
- [x] document chosen app-shell tradeoffs in `docs/*NEXT/`
- [x] add a minimal app window that can read a JSON status artifact
- [x] add a menu bar item showing `risk_on`, `risk_off`, or `stale`

Acceptance criteria:

- [x] app launches locally
- [x] app can read from the Project Montauk directory
- [x] app does not need to understand strategy code
- [x] no engine behavior changes

---

## Phase 1 — Operations Artifacts

Create a stable operations layer before building much UI.

2026-05-12 implementation slice:

- [x] added `scripts/ops/daily.py`
- [x] added `scripts/ops/status.py`
- [x] added `scripts/ops/events.py`
- [x] added `scripts/ops/paths.py`
- [x] added `tests/test_ops.py`
- [x] created initial `signals/2026-05-08.json`
- [x] created initial `runs/operations/latest.json`
- [x] verified local data quality at 41 PASS / 0 WARN / 0 FAIL with refresh disabled
- [x] current app-facing status reports `risk_on` through `2026-05-08`

2026-05-12 follow-up slice:

- [x] `daily.py` now builds live holdout, governance, and notification artifacts
  after the core daily snapshot unless `--skip-followups` is passed
- [x] latest hardened local run produced live holdout `ok`, governance
  `active_watch`, and notification pending count `0`

New folders:

- [x] `signals/`
- [x] `runs/operations/`
- [x] `runs/scheduler/`
- [x] `runs/research_queue/`

New command surface:

- [x] `scripts/ops/daily.py`
- [x] `scripts/ops/status.py`
- [x] `scripts/ops/events.py`

`daily.py` should run the daily operating sequence:

1. [x] refresh market and macro data
2. [x] rebuild or verify the data manifest
3. [x] run consolidated data quality
4. [x] recompute the active champion signal
5. [x] write `signals/YYYY-MM-DD.json`
6. [x] compare against the prior signal snapshot
7. [x] write `runs/operations/latest.json`
8. [x] append notable events to `runs/operations/events.jsonl`
9. [x] rebuild `viz/montauk-viz.html`

`signals/YYYY-MM-DD.json` should include:

- [x] generated timestamp
- [x] data end date
- [x] active champion identity
- [x] strategy params hash
- [x] risk state
- [x] entry/exit/buy/sell event flags
- [x] close price used
- [x] data quality summary
- [x] certification summary
- [x] warnings and blockers

Acceptance criteria:

- [x] daily command is idempotent for the same date
- [x] historical signal snapshots are not overwritten without an explicit repair mode
- [x] app can display `latest.json` without parsing logs
- [x] tests cover signal snapshot shape and signal-change detection

---

## Phase 2 — Background Scheduler

Use macOS `launchd` for the first background implementation. The app should
install, inspect, pause, and remove the LaunchAgent rather than invent its own
daemon first.

2026-05-12 implementation slice:

- [x] added `scripts/ops/run_job.py`
- [x] added `scripts/ops/scheduler.py`
- [x] added `scripts/ops/install_launch_agent.py`
- [x] created default scheduler config at `runs/scheduler/config.json`
- [x] created first lightweight job record under `runs/scheduler/jobs/`
- [x] verified LaunchAgent plist generation for the `daily` job
- [x] later implementation installed and loaded the enabled LaunchAgents

2026-05-12 hardening slice:

- [x] `scripts/ops/run_job.py` now uses per-job lock files under
  `runs/scheduler/locks/`
- [x] stale locks can be recovered after the configured timeout
- [x] overlapping jobs are recorded as `locked` instead of running concurrently
- [x] `scripts/ops/install_launch_agent.py` can now generate, install, load,
  unload, and uninstall LaunchAgent plists
- [x] LaunchAgent load/unload support is implemented and has been exercised for
  enabled jobs
- [x] the Mac app Settings view can inspect, install, load, unload, and uninstall
  the `daily` LaunchAgent through explicit user actions
- [x] the Mac app Settings view can now install/load/unload/uninstall all enabled
  scheduler job LaunchAgents
- [x] enabled LaunchAgents were installed and loaded on 2026-05-12
- [x] daily schedule corrected on 2026-05-12 to run the main block at 13:30 local
  time, followed by governance at 13:45, notifications at 13:50, and approved
  research planning at 14:10
- [x] `scripts/ops/scheduler.py status --json` now returns app-ready scheduler
  status with next local run time and latest job result
- [x] the app Jobs view can enable or disable configured scheduler jobs
- [x] scheduler config loading merges in newly introduced default jobs without
  clobbering local job settings
- [x] `daily-research-supervisor` creates bounded run artifacts for approved
  research ideas
- [x] `scripts/ops/doctor.py` verifies app bundle, core ops artifacts, scheduler,
  and enabled LaunchAgent install/load state from one command

Schedules:

- [x] daily operations after market data is expected to settle
- [x] weekly Gold recertification and family leaderboard refresh
- [x] monthly Confidence v2 calibration diagnostics
- [x] optional bounded research windows

New command surface:

- [x] `scripts/ops/install_launch_agent.py`
- [x] `scripts/ops/scheduler.py`
- [x] `scripts/ops/run_job.py`

Job records should live under `runs/scheduler/` and include:

- [x] job id
- [x] schedule
- [x] command
- [x] started timestamp
- [x] finished timestamp
- [x] status
- [x] output artifact paths
- [x] failure summary

Acceptance criteria:

- [x] scheduled daily job runs when the app is closed
- [x] app shows next run time and last run result
- [x] failed jobs create a structured event
- [x] user can pause background jobs from the app

---

## Phase 3 — Notifications

Add notification rules after the operations artifacts exist.

2026-05-12 implementation slice:

- [x] added `scripts/ops/notifications.py`
- [x] added `runs/operations/notifications.json`
- [x] notification scan reads `events.jsonl` and writes a pending outbox
- [x] the app can scan and send pending macOS notifications
- [x] sent notification status is persisted back to `notifications.json`
- [x] routine `job_succeeded` info events are filtered out
- [x] signal changes, data quality failures, job failures, snapshot conflicts,
  viz build failures, champion blockers, replacement candidates, and live drift
  are notifiable
- [x] explicit `--send` exists for CLI/manual use, but the app should eventually
  own native notification delivery

Notification events:

- [x] risk state changed
- [x] data is stale
- [x] data quality failed
- [x] active champion lost Gold Status
- [x] current signal has blockers
- [x] scheduled job failed
- [x] new review-worthy candidate exists
- [x] live holdout drift crossed threshold

Notification data should come from `events.jsonl`, not from ad hoc app logic.

Acceptance criteria:

- [x] app sends a macOS notification for a simulated signal change
- [x] routine successful daily runs do not notify
- [x] notification preferences are persisted
- [x] every notification links back to the relevant app view or artifact

---

## Phase 4 — App Dashboard

Build the first useful app surface.

2026-05-12 implementation slice:

- [x] added dashboard shell with Current Signal, Data Status, Active Champion,
  Notifications, Jobs, Events, and Settings views
- [x] app reads live status through Tauri command `read_status`
- [x] app can invoke `run_job`, `scan_notifications`, and `open_viz` once running
  through Tauri
- [x] app can manage the daily LaunchAgent from Settings without terminal commands
- [x] app can show Doctor readiness, including launchd loaded/runs/last-exit state
- [x] app auto-refreshes status and shows scheduler next-run/last-run details
- [x] app main view now focuses on a premium, stripped-down Current Signal and a
  strategy-selection matrix instead of question-style copy
- [x] app Today view now answers buy/sell/hold, risk on/off, consensus, and which
  strategy lenses support the current stance
- [x] app current signal now includes freshness and automation state so stale data
  or a stopped daily LaunchAgent is visible in the primary view
- [x] app removed backend-facing alert scan/send controls from the main view; issues
  that could reduce confidence now live under Checkup
- [x] app includes a sidebar Viz tab that embeds the existing Montauk visualization
- [x] app can show risk on/off and best certified strategy at a glance under the
  main selection metrics: confidence, full history, real era, and modern era
- [x] app-side metric comparisons are read-only and do not overwrite the official
  daily strategy review artifact or create replacement-candidate notifications
- [x] static browser fallback renders a preview status object for design iteration
- [x] JavaScript and Rust formatting checks pass without installing dependencies

Views:

- [x] Current Signal
- [x] Data Status
- [x] Active Champion
- [x] Gold Leaderboard
- [x] Family Leaders
- [x] Operations Log
- [x] Scheduled Jobs
- [x] Settings

The dashboard should be dense and operational. It should show what changed,
what is stale, and what needs attention.

Acceptance criteria:

- [x] no terminal is needed to answer the daily status questions
- [x] stale data and failed jobs are visually obvious
- [x] leaderboard rows link to their run artifacts
- [x] existing `viz/montauk-viz.html` can be opened or embedded

---

## Phase 5 — Live Holdout And Drift Tracking

Turn the daily snapshots into forward evidence.

2026-05-12 implementation slice:

- [x] added `scripts/ops/live_holdout.py`
- [x] added `runs/operations/live_holdout.json`
- [x] current point-in-time snapshot replays cleanly against the current engine
- [x] report currently tracks latest-date replay; fuller historical replay can be
  added after more live snapshots accumulate

New command surface:

- [x] `scripts/ops/live_holdout.py`
- [x] `scripts/ops/reconcile_signals.py`

Track:

- [x] daily point-in-time signal
- [x] later replay signal for the same date
- [x] signal divergence
- [x] expected next-open execution proxy
- [x] active champion performance since live tracking began
- [x] backtest-vs-live degradation
- [x] confidence drift after data refreshes

Acceptance criteria:

- [x] app shows live holdout start date
- [x] app shows whether replay still matches the original daily signal
- [x] app flags material drift
- [x] historical snapshots remain immutable

---

## Phase 6 — Recertification And Champion Governance

Add explicit rules for whether the active champion is still deployable.

2026-05-12 implementation slice:

- [x] added `scripts/ops/governance.py`
- [x] added `runs/operations/governance.json`
- [x] current governance state is `active_watch`
- [x] reason: current champion remains Gold, but 7 validation warnings are active
- [x] live holdout status is included in governance and currently has 0 divergences

Governance states:

- [x] `active_ok`
- [x] `active_watch`
- [x] `active_blocked`
- [x] `replacement_candidate`
- [x] `manual_review_required`

Triggers:

- [x] champion lost Gold Status
- [x] data quality failed
- [x] live holdout drift exceeded threshold
- [x] Future Confidence or Trust deteriorated materially
- [x] a new family leader materially improves trust
- [x] validation warnings crossed a configured threshold

Acceptance criteria:

- [x] app can explain why the active champion is ok, watch, or blocked
- [x] no raw research result can become active without Gold Status
- [x] champion changes are logged as governance events
- [x] user can see old champion, new candidate, and reason for review

---

## Phase 7 — Research Queue

Create an app-visible queue for strategy testing.

2026-05-12 implementation slice:

- [x] added `scripts/ops/research_queue.py`
- [x] added `runs/research_queue/queue.json`
- [x] added four proposed research lanes from current warnings:
  rebound capture repair, drawdown resilience probe, parsimony challenger, and
  portability repair
- [x] proposals are reviewable artifacts; none can mutate the authority leaderboard
  outside the existing certification path
- [x] research ideas can now be marked approved, dismissed, or reset from the app
- [x] review actions update both `queue.json` and the individual idea artifact
- [x] approved ideas can now be converted into bounded research run artifacts under
  `runs/research_queue/runs/`
- [x] a daily approved-research supervisor is included in scheduler status
- [x] queue artifacts now include input diagnostics, expected artifacts, and
  stop conditions
- [x] app controls can enqueue ideas, start approved runs, pause ideas, and
  inspect queue metadata plus recent run artifacts

Research job types:

- [x] recertify existing Gold rows
- [x] focused grid search
- [x] hybrid lab
- [x] diversity prefilter
- [x] near-miss autopsy
- [x] confidence calibration
- [x] generated hypothesis test

Each queued job should include:

- [x] rationale
- [x] input diagnostics
- [x] strategy family or idea
- [x] validation tier
- [x] time budget
- [x] expected artifact paths
- [x] stop conditions

Acceptance criteria:

- [x] app can enqueue, start, pause, and inspect jobs
- [x] long-running research is bounded by budget
- [x] results are archived as artifacts
- [x] no research job can directly mutate the authority leaderboard except through
  the existing certification path

---

## Phase 8 — Strategy Ideation Loop

Add a controlled idea-generation layer.

The ideation loop should read diagnostics and propose tests, not directly write
authority strategies.

Inputs:

- [x] recent market movement
- [x] marker timing misses
- [x] named-window failures
- [x] near-Gold autopsies
- [x] live holdout drift
- [x] family concentration
- [x] Confidence v2 weak planks

Outputs:

- [x] proposal JSON under `runs/research_queue/ideas/`
- [x] short rationale
- [x] candidate family
- [x] suggested tests
- [x] expected failure mode
- [x] validation tier
- [x] compute budget

Acceptance criteria:

- [x] generated ideas are reviewable before expensive runs
- [x] app can approve or dismiss ideas
- [x] accepted ideas become bounded research jobs
- [x] rejected ideas remain logged

---

## Phase 9 — Packaging And Auto-Update

Package the app as a local standalone macOS application.

2026-05-12 implementation slice:

- [x] native app build completed successfully
- [x] local bundle path:
  `app/src-tauri/target/release/bundle/macos/Montauk.app`
- [x] local binary path:
  `app/src-tauri/target/release/montauk-app`
- [x] app-side LaunchAgent controls are present, but persistent background
  activation is explicit and has now been performed for enabled jobs
- [x] `.gitignore` excludes local app build products and dependency folders
- [x] added packaging/runtime/update notes at `docs/app-packaging.md`
- [x] added signed-bundle update inspection/install command at
  `scripts/ops/app_update.py`
- [x] operations artifacts now stamp app and strategy-code version metadata
- [x] signed local candidate was installed to `/Applications/Montauk.app` via the
  update command and verified with `codesign --verify --deep --strict`

Packaging requirements:

- [x] app bundle can be opened from Finder
- [x] app can locate or configure the Project Montauk path
- [x] Python runtime/dependency strategy is documented
- [x] LaunchAgent is installed through the app
- [x] app update path is defined

Auto-update should mean:

- [x] the app can update its own app shell when a new signed build exists
- [x] the app can keep Montauk data current through scheduled refreshes
- [x] the app does not silently change strategy code or validation rules without
  recording the version change

Acceptance criteria:

- [x] clean install works on the local machine
- [x] app survives reboot and runs scheduled jobs
- [x] app can be updated without losing settings or signal history
- [x] version is stamped into operations artifacts

---

## Phase 10 — Hardening

Before treating the app as the normal daily surface:

- [x] add crash-safe job locking
- [x] add stale-lock recovery
- [x] protect immutable signal snapshots
- [x] add structured error codes
- [x] add app-level smoke tests
- [x] add operations fixtures
- [x] verify all scheduled jobs can run from a fresh shell environment
- [x] test with no network, partial network failure, and stale market data
- [x] test daylight-saving and market-holiday behavior

Acceptance criteria:

- [x] failed background jobs do not corrupt artifacts
- [x] app explains failures without terminal output
- [x] daily job is repeatable
- [x] market holidays do not create false alarms
- [x] stale data creates a clear warning

---

## Suggested Build Order

1. [x] Operations artifacts and `scripts/ops/daily.py`
2. [x] Signal journal and event log
3. [x] Minimal app shell reading `latest.json`
4. [x] LaunchAgent scheduler
5. [x] Notifications
6. [x] Dashboard views
7. [x] Live holdout tracking
8. [x] Governance states
9. [x] Research queue
10. [x] Ideation loop
11. [x] Packaging and auto-update
12. [x] Hardening

This order keeps the engine trustworthy before making the app feel automatic.
