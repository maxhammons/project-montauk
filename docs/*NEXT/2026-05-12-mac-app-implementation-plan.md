# Montauk Mac App Implementation Plan

> Status: implementation plan, 2026-05-12

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

- chose the Tauri direction for the first app shell
- scaffolded `app/`
- added static dashboard assets under `app/src/`
- added Tauri bridge commands under `app/src-tauri/`
- installed app dependencies locally
- verified the Vite app build and native Tauri bundle build

Reason:

- the existing visualization is already HTML/JS
- the Python engine can remain untouched
- Tauri can package a small macOS app without bringing in a heavy runtime
- native notifications, menu bar, and background command execution are reachable

Fallback: SwiftUI if deeper native macOS integration becomes more important
than reuse of the current web visualization.

Deliverables:

- create `app/` for the desktop shell
- document chosen app-shell tradeoffs in `docs/*NEXT/`
- add a minimal app window that can read a JSON status artifact
- add a menu bar item showing `risk_on`, `risk_off`, or `stale`

Acceptance criteria:

- app launches locally
- app can read from the Project Montauk directory
- app does not need to understand strategy code
- no engine behavior changes

---

## Phase 1 — Operations Artifacts

Create a stable operations layer before building much UI.

2026-05-12 implementation slice:

- added `scripts/ops/daily.py`
- added `scripts/ops/status.py`
- added `scripts/ops/events.py`
- added `scripts/ops/paths.py`
- added `tests/test_ops.py`
- created initial `signals/2026-05-08.json`
- created initial `runs/operations/latest.json`
- verified local data quality at 41 PASS / 0 WARN / 0 FAIL with refresh disabled
- current app-facing status reports `risk_on` through `2026-05-08`

2026-05-12 follow-up slice:

- `daily.py` now builds live holdout, governance, and notification artifacts
  after the core daily snapshot unless `--skip-followups` is passed
- latest hardened local run produced live holdout `ok`, governance
  `active_watch`, and notification pending count `0`

New folders:

- `signals/`
- `runs/operations/`
- `runs/scheduler/`
- `runs/research_queue/`

New command surface:

- `scripts/ops/daily.py`
- `scripts/ops/status.py`
- `scripts/ops/events.py`

`daily.py` should run the daily operating sequence:

1. refresh market and macro data
2. rebuild or verify the data manifest
3. run consolidated data quality
4. recompute the active champion signal
5. write `signals/YYYY-MM-DD.json`
6. compare against the prior signal snapshot
7. write `runs/operations/latest.json`
8. append notable events to `runs/operations/events.jsonl`
9. rebuild `viz/montauk-viz.html`

`signals/YYYY-MM-DD.json` should include:

- generated timestamp
- data end date
- active champion identity
- strategy params hash
- risk state
- entry/exit/buy/sell event flags
- close price used
- data quality summary
- certification summary
- warnings and blockers

Acceptance criteria:

- daily command is idempotent for the same date
- historical signal snapshots are not overwritten without an explicit repair mode
- app can display `latest.json` without parsing logs
- tests cover signal snapshot shape and signal-change detection

---

## Phase 2 — Background Scheduler

Use macOS `launchd` for the first background implementation. The app should
install, inspect, pause, and remove the LaunchAgent rather than invent its own
daemon first.

2026-05-12 implementation slice:

- added `scripts/ops/run_job.py`
- added `scripts/ops/scheduler.py`
- added `scripts/ops/install_launch_agent.py`
- created default scheduler config at `runs/scheduler/config.json`
- created first lightweight job record under `runs/scheduler/jobs/`
- verified LaunchAgent plist generation for the `daily` job
- later implementation installed and loaded the enabled LaunchAgents

2026-05-12 hardening slice:

- `scripts/ops/run_job.py` now uses per-job lock files under
  `runs/scheduler/locks/`
- stale locks can be recovered after the configured timeout
- overlapping jobs are recorded as `locked` instead of running concurrently
- `scripts/ops/install_launch_agent.py` can now generate, install, load,
  unload, and uninstall LaunchAgent plists
- LaunchAgent load/unload support is implemented and has been exercised for
  enabled jobs
- the Mac app Settings view can inspect, install, load, unload, and uninstall
  the `daily` LaunchAgent through explicit user actions
- the Mac app Settings view can now install/load/unload/uninstall all enabled
  scheduler job LaunchAgents
- enabled LaunchAgents were installed and loaded on 2026-05-12
- daily schedule corrected on 2026-05-12 to run the main block at 13:30 local
  time, followed by governance at 13:45, notifications at 13:50, and approved
  research planning at 14:10
- `scripts/ops/scheduler.py status --json` now returns app-ready scheduler
  status with next local run time and latest job result
- the app Jobs view can enable or disable configured scheduler jobs
- scheduler config loading merges in newly introduced default jobs without
  clobbering local job settings
- `daily-research-supervisor` creates bounded run artifacts for approved
  research ideas
- `scripts/ops/doctor.py` verifies app bundle, core ops artifacts, scheduler,
  and enabled LaunchAgent install/load state from one command

Schedules:

- daily operations after market data is expected to settle
- weekly Gold recertification and family leaderboard refresh
- monthly Confidence v2 calibration diagnostics
- optional bounded research windows

New command surface:

- `scripts/ops/install_launch_agent.py`
- `scripts/ops/scheduler.py`
- `scripts/ops/run_job.py`

Job records should live under `runs/scheduler/` and include:

- job id
- schedule
- command
- started timestamp
- finished timestamp
- status
- output artifact paths
- failure summary

Acceptance criteria:

- scheduled daily job runs when the app is closed
- app shows next run time and last run result
- failed jobs create a structured event
- user can pause background jobs from the app

---

## Phase 3 — Notifications

Add notification rules after the operations artifacts exist.

2026-05-12 implementation slice:

- added `scripts/ops/notifications.py`
- added `runs/operations/notifications.json`
- notification scan reads `events.jsonl` and writes a pending outbox
- the app can scan and send pending macOS notifications
- sent notification status is persisted back to `notifications.json`
- routine `job_succeeded` info events are filtered out
- signal changes, data quality failures, job failures, snapshot conflicts,
  viz build failures, champion blockers, replacement candidates, and live drift
  are notifiable
- explicit `--send` exists for CLI/manual use, but the app should eventually
  own native notification delivery

Notification events:

- risk state changed
- data is stale
- data quality failed
- active champion lost Gold Status
- current signal has blockers
- scheduled job failed
- new review-worthy candidate exists
- live holdout drift crossed threshold

Notification data should come from `events.jsonl`, not from ad hoc app logic.

Acceptance criteria:

- app sends a macOS notification for a simulated signal change
- routine successful daily runs do not notify
- notification preferences are persisted
- every notification links back to the relevant app view or artifact

---

## Phase 4 — App Dashboard

Build the first useful app surface.

2026-05-12 implementation slice:

- added dashboard shell with Current Signal, Data Status, Active Champion,
  Notifications, Jobs, Events, and Settings views
- app reads live status through Tauri command `read_status`
- app can invoke `run_job`, `scan_notifications`, and `open_viz` once running
  through Tauri
- app can manage the daily LaunchAgent from Settings without terminal commands
- app can show Doctor readiness, including launchd loaded/runs/last-exit state
- app auto-refreshes status and shows scheduler next-run/last-run details
- app main view now focuses on a premium, stripped-down Current Signal and a
  strategy-selection matrix instead of question-style copy
- app Today view now answers buy/sell/hold, risk on/off, consensus, and which
  strategy lenses support the current stance
- app current signal now includes freshness and automation state so stale data
  or a stopped daily LaunchAgent is visible in the primary view
- app removed backend-facing alert scan/send controls from the main view; issues
  that could reduce confidence now live under Checkup
- app includes a sidebar Viz tab that embeds the existing Montauk visualization
- app can show risk on/off and best certified strategy at a glance under the
  main selection metrics: confidence, full history, real era, and modern era
- app-side metric comparisons are read-only and do not overwrite the official
  daily strategy review artifact or create replacement-candidate notifications
- static browser fallback renders a preview status object for design iteration
- JavaScript and Rust formatting checks pass without installing dependencies

Views:

- Current Signal
- Data Status
- Active Champion
- Gold Leaderboard
- Family Leaders
- Operations Log
- Scheduled Jobs
- Settings

The dashboard should be dense and operational. It should show what changed,
what is stale, and what needs attention.

Acceptance criteria:

- no terminal is needed to answer the daily status questions
- stale data and failed jobs are visually obvious
- leaderboard rows link to their run artifacts
- existing `viz/montauk-viz.html` can be opened or embedded

---

## Phase 5 — Live Holdout And Drift Tracking

Turn the daily snapshots into forward evidence.

2026-05-12 implementation slice:

- added `scripts/ops/live_holdout.py`
- added `runs/operations/live_holdout.json`
- current point-in-time snapshot replays cleanly against the current engine
- report currently tracks latest-date replay; fuller historical replay can be
  added after more live snapshots accumulate

New command surface:

- `scripts/ops/live_holdout.py`
- `scripts/ops/reconcile_signals.py`

Track:

- daily point-in-time signal
- later replay signal for the same date
- signal divergence
- expected next-open execution proxy
- active champion performance since live tracking began
- backtest-vs-live degradation
- confidence drift after data refreshes

Acceptance criteria:

- app shows live holdout start date
- app shows whether replay still matches the original daily signal
- app flags material drift
- historical snapshots remain immutable

---

## Phase 6 — Recertification And Champion Governance

Add explicit rules for whether the active champion is still deployable.

2026-05-12 implementation slice:

- added `scripts/ops/governance.py`
- added `runs/operations/governance.json`
- current governance state is `active_watch`
- reason: current champion remains Gold, but 7 validation warnings are active
- live holdout status is included in governance and currently has 0 divergences

Governance states:

- `active_ok`
- `active_watch`
- `active_blocked`
- `replacement_candidate`
- `manual_review_required`

Triggers:

- champion lost Gold Status
- data quality failed
- live holdout drift exceeded threshold
- Future Confidence or Trust deteriorated materially
- a new family leader materially improves trust
- validation warnings crossed a configured threshold

Acceptance criteria:

- app can explain why the active champion is ok, watch, or blocked
- no raw research result can become active without Gold Status
- champion changes are logged as governance events
- user can see old champion, new candidate, and reason for review

---

## Phase 7 — Research Queue

Create an app-visible queue for strategy testing.

2026-05-12 implementation slice:

- added `scripts/ops/research_queue.py`
- added `runs/research_queue/queue.json`
- added four proposed research lanes from current warnings:
  rebound capture repair, drawdown resilience probe, parsimony challenger, and
  portability repair
- proposals are reviewable artifacts; none can mutate the authority leaderboard
  outside the existing certification path
- research ideas can now be marked approved, dismissed, or reset from the app
- review actions update both `queue.json` and the individual idea artifact
- approved ideas can now be converted into bounded research run artifacts under
  `runs/research_queue/runs/`
- a daily approved-research supervisor is included in scheduler status

Research job types:

- recertify existing Gold rows
- focused grid search
- hybrid lab
- diversity prefilter
- near-miss autopsy
- confidence calibration
- generated hypothesis test

Each queued job should include:

- rationale
- input diagnostics
- strategy family or idea
- validation tier
- time budget
- expected artifact paths
- stop conditions

Acceptance criteria:

- app can enqueue, start, pause, and inspect jobs
- long-running research is bounded by budget
- results are archived as artifacts
- no research job can directly mutate the authority leaderboard except through
  the existing certification path

---

## Phase 8 — Strategy Ideation Loop

Add a controlled idea-generation layer.

The ideation loop should read diagnostics and propose tests, not directly write
authority strategies.

Inputs:

- recent market movement
- marker timing misses
- named-window failures
- near-Gold autopsies
- live holdout drift
- family concentration
- Confidence v2 weak planks

Outputs:

- proposal JSON under `runs/research_queue/ideas/`
- short rationale
- candidate family
- suggested tests
- expected failure mode
- validation tier
- compute budget

Acceptance criteria:

- generated ideas are reviewable before expensive runs
- app can approve or dismiss ideas
- accepted ideas become bounded research jobs
- rejected ideas remain logged

---

## Phase 9 — Packaging And Auto-Update

Package the app as a local standalone macOS application.

2026-05-12 implementation slice:

- native app build completed successfully
- local bundle path:
  `app/src-tauri/target/release/bundle/macos/Montauk.app`
- local binary path:
  `app/src-tauri/target/release/montauk-app`
- app-side LaunchAgent controls are present, but persistent background
  activation is explicit and has now been performed for enabled jobs
- `.gitignore` excludes local app build products and dependency folders

Packaging requirements:

- app bundle can be opened from Finder
- app can locate or configure the Project Montauk path
- Python runtime/dependency strategy is documented
- LaunchAgent is installed through the app
- app update path is defined

Auto-update should mean:

- the app can update its own app shell when a new signed build exists
- the app can keep Montauk data current through scheduled refreshes
- the app does not silently change strategy code or validation rules without
  recording the version change

Acceptance criteria:

- clean install works on the local machine
- app survives reboot and runs scheduled jobs
- app can be updated without losing settings or signal history
- version is stamped into operations artifacts

---

## Phase 10 — Hardening

Before treating the app as the normal daily surface:

- add crash-safe job locking
- add stale-lock recovery
- protect immutable signal snapshots
- add structured error codes
- add app-level smoke tests
- add operations fixtures
- verify all scheduled jobs can run from a fresh shell environment
- test with no network, partial network failure, and stale market data
- test daylight-saving and market-holiday behavior

Acceptance criteria:

- failed background jobs do not corrupt artifacts
- app explains failures without terminal output
- daily job is repeatable
- market holidays do not create false alarms
- stale data creates a clear warning

---

## Suggested Build Order

1. Operations artifacts and `scripts/ops/daily.py`
2. Signal journal and event log
3. Minimal app shell reading `latest.json`
4. LaunchAgent scheduler
5. Notifications
6. Dashboard views
7. Live holdout tracking
8. Governance states
9. Research queue
10. Ideation loop
11. Packaging and auto-update
12. Hardening

This order keeps the engine trustworthy before making the app feel automatic.
