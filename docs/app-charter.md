# Montauk App Charter

> Status: draft product charter, 2026-05-12

---

## 1. Purpose

The Montauk app is the local operating surface for Project Montauk.

Its job is to keep the TECL signal factory current, observable, and honest while
preserving the core charter: Python remains the source of truth, strategies must
earn Gold Status before becoming authority, and brokerage execution remains a
manual human decision.

The app should feel like a cockpit for the Montauk Engine, not a separate
trading platform.

---

## 2. Product Identity

The app is a standalone macOS application that runs Montauk in the background
and shows the current state of the system at a glance:

- latest data refresh status
- current champion and risk state
- signal changes and recent signal history
- Gold Status leaderboard and family leaders
- validation warnings, confidence drift, and live holdout evidence
- scheduled research and testing activity
- strategy ideas proposed for future testing

The app may automate refresh, testing, reporting, and notifications. It must not
automate brokerage execution.

---

## 3. Operating Principles

### Local-first

The project remains local-first. Data, signals, validation artifacts, logs, and
the app state live in the project directory unless a later deployment decision
explicitly moves them.

App operations must run on the local machine. The app should not depend on
GitHub Actions, remote runners, hosted queues, or cloud services for daily
updates, scheduled checks, recertification, or strategy research.

### Python authority

The Python engine owns signal generation, backtests, validation, certification,
and artifact creation. The app invokes the engine and displays its artifacts.
The app does not reimplement strategy logic.

### Code-only intelligence

Montauk should not rely on an AI backend to decide trades, rank strategies, or
operate the daily process. The intelligence in the product should be versioned,
inspectable code: Python strategies, validators, schedulers, and structured
artifacts. AI can help during development, but it is not a runtime dependency
or decision authority inside the app.

### Immutable daily memory

Every trading day should produce a point-in-time signal snapshot. Future data
refreshes may explain or supersede an old signal, but they should not silently
rewrite what the system believed on that date.

### Continuous but governed research

The system may continuously propose and test strategies, including ideas derived
from recent market movement, regime shifts, failures, near misses, and live
degradation. Those ideas remain research until they pass the existing
tier-routed validation and Gold Status contract.

### Human-controlled promotion

The app may recommend a new champion. It should not silently replace the active
champion unless the governance rules explicitly allow that action and the event
is logged.

---

## 4. Core Capabilities

### Daily Operations

The app should automatically:

- refresh market and macro data when new bars are expected
- verify data quality and manifest integrity
- recompute the current champion signal
- write a dated signal snapshot
- detect signal changes
- rebuild the local visualization bundle
- notify when attention is needed

### Strategy Monitoring

The app should continuously evaluate whether the active strategy is still
eligible, trustworthy, and applicable:

- Gold Status recertification
- Confidence v2 drift
- live holdout comparison
- data refresh stability
- current-era degradation
- family crowding and duplicate-signal risk
- warnings that were once tolerable but are getting worse

### Scheduled Research

The app should maintain a background research calendar:

- short scheduled recertification jobs
- weekly or monthly strategy stress checks
- periodic calibration and confidence diagnostics
- occasional broader search jobs
- focused research runs based on current weaknesses

Research should be budgeted and observable. The user should be able to see what
is running, why it was scheduled, how long it is allowed to run, and what it
found.

### Strategy Ideation

The app may create strategy ideas from diagnostics rather than only running
static grids. Inputs may include:

- recent drawdown or rebound behavior
- missed marker transitions
- live-vs-backtest drift
- near-Gold failure reasons
- family concentration
- regime-specific underperformance
- current market state

Generated ideas should come from deterministic diagnostics and enter a proposal
queue with a plain-language rationale, expected failure mode, intended
validation tier, and test budget.

### Notifications

Notifications should be reserved for useful events:

- risk state changed
- data refresh failed or is stale
- active champion lost Gold Status
- validation warnings crossed a threshold
- a scheduled job failed
- a new candidate survived enough testing to review
- live holdout drift requires attention

The app should avoid noisy notifications for routine successful work.

---

## 5. Trust Boundaries

The app is allowed to automate:

- data refresh
- data audits
- signal snapshots
- local visualization rebuilds
- validation and recertification
- research queues
- strategy proposal drafting
- notifications
- logs and reports

The app is not allowed to automate:

- live brokerage orders
- unreviewed promotion of raw winners
- bypassing Gold Status
- editing historical signal snapshots
- hiding validation failures behind better-looking summary scores
- offloading app operations to GitHub Actions or other remote runners
- depending on an AI service for runtime strategy decisions

---

## 6. App Surfaces

The first version should prioritize utility over polish.

Expected surfaces:

- menu bar status item for current risk state and stale-data alerts
- main dashboard for signal, champion, data, and warnings
- leaderboard view for Gold and family leaders
- operations view for scheduled jobs and recent runs
- research queue for proposed and running strategy tests
- signal journal for point-in-time daily history
- settings for schedule, notification, and project-path configuration

The existing HTML visualization remains useful and may be embedded or opened
from the app.

---

## 7. Background Model

The app should have a background worker model independent of whether the window
is open. The worker should be able to run daily operations, scheduled checks,
and bounded research jobs using the same Python commands a user could run
manually.

The background system should prefer predictable schedules over constant churn:

- daily after market data is expected to settle
- weekly for leaderboard recertification
- monthly for broader confidence diagnostics
- explicit larger research windows when requested

---

## 8. Data And Artifact Contracts

The app should consume stable artifacts rather than scrape terminal output.

Likely app-facing contracts:

- `signals/YYYY-MM-DD.json`
- `runs/operations/latest.json`
- `runs/operations/events.jsonl`
- `runs/research_queue/*.json`
- `runs/scheduler/*.json`
- `spike/leaderboard.json`
- `runs/family_confidence_leaderboard.json`
- `runs/confidence_v2/leaderboard_scores.json`
- `viz/montauk-viz.html`

If an artifact is important enough for the app to display, it should be written
as structured JSON by the engine or operations layer.

---

## 9. Success Definition

The app succeeds when it can answer these questions without opening a terminal:

- Is Montauk current?
- What is the active signal?
- Did the signal change?
- Is the active champion still Gold?
- Are there warnings that affect deployment trust?
- What testing is scheduled or running?
- What did the latest research learn?
- Is the system improving or drifting?

The app is not successful merely because it displays charts. It is successful
when it turns Montauk into a dependable daily process.

---

## 10. Open Design Choices

These choices can be finalized during implementation:

- native SwiftUI shell vs Tauri shell
- exact notification severity levels
- exact promotion-review workflow
- how much strategy ideation is automated in v1
- whether the app embeds the HTML viewer or opens it externally
- how to budget long-running local research without making the app feel busy

The default bias should be simple, local, inspectable, and aligned with the
existing Python pipeline.
