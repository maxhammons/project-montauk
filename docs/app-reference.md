# Montauk App Reference

> A per-button, per-view reference for the local Mac app at `app/`.
>
> Descriptive, not normative — see `docs/app-charter.md` for trust boundaries
> and product principles. When you change a button label, tooltip, command, or
> artifact path in code, update this file too.

---

## Operating philosophy

The app exists for two tasks:

- **Today**: 15-second glance at the dashboard. What do I do today? How sure are we?
- **Deep dive**: 30-minute trend exploration in the Viz tab.

Everything else (data refresh, validation, doctor checks, research drain) is
folded behind **one button**: `Run Maintenance`. Maintenance also runs
automatically on every app launch. No scheduler, no per-job toggles, no manual
ordering — if you want fresh state, click the button.

The intelligence is in versioned Python code under `scripts/`. The app
*invokes* it through a Tauri bridge; it does not implement strategy logic.

---

## Architecture at a glance

- Shell: Tauri 2.x (`app/src-tauri/`), Vite dev server (`app/`), vanilla JS frontend (`app/src/main.js`, `app/index.html`).
- Bridge: Rust `tauri::command` functions in `app/src-tauri/src/main.rs` spawn Python scripts under `scripts/ops/` and read JSON from `runs/`, `signals/`, `spike/`, and `viz/`.
- Static assets: `app/public/lib/lightweight-charts.js`, `app/public/lib/viz-engine.js`.
- Project root resolution: `MONTAUK_PROJECT_ROOT` env var if set; otherwise inferred from the Tauri manifest dir.

---

## Sidebar (every view)

- **PROJECT MONTAUK** wordmark — animated magenta→violet→cyan gradient text.
- **Today** nav button — dashboard.
- **Doctor** nav button — confidence ledger + research queue + collapsed advanced sections.
- **Viz** nav button — deep-dive chart workspace. Triggers a full-window takeover; the sidebar collapses to a 56 px icon rail while Viz is active.
- **Now** readout — current position state and active family from the latest signal snapshot.

---

## Top bar (Today + Doctor views)

| Button | What it does | Bridge |
|---|---|---|
| **Run Maintenance** | Runs `scripts/ops/maintenance.py`. Refreshes data, recomputes signal, rebuilds viz bundle, runs health checks, drains ONE approved research idea. Modal shows live phase progress. Also runs automatically on app launch. | `start_maintenance` + `read_maintenance_status` (polled every 350 ms) |

No Reload, no Update Data, no Run Checkup, no Run Next Strategy. One button.

If the research queue is empty, the modal's research phase shows status
`empty` with a "Queue empty — ask AI to top up runs/research_queue/queue.json
(see docs/ai-research-playbook.md)" message. Click again later once an AI
session has populated the queue.

### Maintenance modal

Full-window translucent overlay over animated magenta/cyan gradient. Shows:

- The current phase title and its subtitle.
- A neon progress bar (magenta → violet → cyan).
- A vertical step list:
  - **Refresh data & recompute signal** (`scripts/ops/daily.py`)
  - **Run health checks** (`scripts/ops/doctor.py`)
  - **Drain one approved research idea** (`scripts/ops/research_runner.py` — only if a `status: "approved"` idea exists)

When a phase is running it gets a pulsing neon outline. When complete the
modal shows `Close` and (on failure) `Copy Debug`.

---

## Today (dashboard)

Single screen. 15-second read.

### Command panel

- **TECL** action label — Buy / Hold / Sell / Stay in Cash / Entering / Leaving / No Call.
- **One-line reason** — never restates the action. Example: "Trend remains intact and no exit fired today."
- **Confidence** meter (0–100%) — composite confidence of the active certified strategy.
- **Flip pressure · 60d** — neon sparkline replayed from `signals/YYYY-MM-DD.json`. Magenta line on a violet→cyan gradient fill; cyan dot marks today. Hover the meter block for the tooltip.

### Family card

- Active family name (large), strategy display name (small).
- Three meta tiles:
  - **Data** — latest snapshot date + fresh/stale pill.
  - **Universe** — number of Gold rows currently certified.
  - **Routes** — how many of the four route lenses (confidence, full, real, modern) agree with the displayed position.

That's it. No stat strip. No status grid. If you want more, switch to Doctor.

---

## Doctor (confidence ledger + research queue)

### Hero — "How sure are we?"

One big animated gradient number (0–100) plus a one-line narrative
("Position is supported by the active checks" / "Some checks are soft" /
"Multiple checks are failing"). Score is the average of the per-pill levels
(ok = 1.0, warn = 0.5, fail = 0.0).

### Ledger pills

Each pill is a single fact about why we are or aren't sure:

| Pill | Source | What ok/warn/fail means |
|---|---|---|
| Data integrity | `signal.data_quality` | ok if all checks pass; fail if any fail |
| Live replay | `runs/operations/live_holdout.json` | ok if 0 drift; warn if drift or no snapshots yet |
| Validation composite | `strategy_review.best_certified.confidence` | ok ≥ 70% / warn ≥ 40% / fail otherwise |
| Governance | `runs/operations/governance.json` state | ok = `active_ok`, fail = `active_blocked`, warn otherwise |
| Family leader | `runs/family_confidence_leaderboard.json` top row | ok if future_confidence ≥ 60% |
| Active warnings | `signal.warnings[]` (only shown if non-empty) | always warn — surfaces a one-line excerpt |

Hover any pill for the underlying detail.

### Research queue

Reads `runs/research_queue/queue.json`. Each row shows status, kind, validation
tier, rationale, suggested tests, action buttons:

| Idea status | Buttons | Effect |
|---|---|---|
| proposed | **Approve** / **Dismiss** | `research_queue_action(id, approve|dismiss)` |
| approved | **Dismiss** | Re-flips to dismissed |
| dismissed | **Reopen** | Resets to proposed |

The Maintenance button drains the first `status: "approved"` idea each run.
See `docs/ai-research-playbook.md` for how to populate the queue from an AI
session.

### Collapsed accordions (advanced)

- **Strategy board** — top 10 Gold leaderboard rows from `spike/leaderboard.json`. Now joined with Edge (Future Confidence) and Trust columns from `runs/family_confidence_leaderboard.json`.
- **Route votes** — what position each of the four route lenses (main confidence / long-run share / live-era share / modern share) would call.
- **Readiness detail** — full `scripts/ops/doctor.py` output.

No scheduler panel. No LaunchAgent install/load controls in the UI.

---

## Viz (deep dive)

Activating Viz collapses the app sidebar to a 56 px glyph rail and lets the
viz absorb the full window (no border, no radius, no surrounding box).

### Topbar

Built into the viz shell, not the app shell. Provenance badge, generated
timestamp, Index-to-viewport toggle, North-star markers toggle, 1Y/5Y/ALL
range, **Pop out** (opens `viz/montauk-viz.html` in a separate window).

### Left rail — leaderboard

Tabs (Full / Family), sort selector with direction toggle, Real/Modern share
toggle, scrollable list of strategies. Click a row to load it into the chart.

### Center — three chart panes

| Pane | What |
|---|---|
| Price + trades | TECL close (cyan crosshair), violet tint on the synthetic pre-2008 era, "Real data starts" seam label, entry/exit trade arrows, optional north-star markers. |
| Equity vs B&H | Strategy equity (cyan) vs buy-and-hold (muted dashed). Renormalizes on viewport when Index-to-viewport is on. |
| TECL Health | Diagnostic-only baseline series (green above 50, red below) + fast/slow EMAs. Never affects buy/sell. |

Cross-chart crosshair and time-scale sync across all three panes.

### Right panel — active strategy detail

Name + meta badges, TECL Health snapshot, 5Y scorecard, primary metrics, era
breakdown, regime scoring, validation gates, parameters.

### Hot reload

When Maintenance completes while you're on Viz, the engine resets and reboots
with the new bundle automatically — no app restart needed.

---

## Tauri command surface

Defined in `app/src-tauri/src/main.rs::main` and called from `app/src/main.js`.

| Command | Args | Purpose |
|---|---|---|
| `read_status` | — | Aggregate JSON read from latest operation, latest signal, governance, live holdout, strategy review, leaderboards, notifications, research queue, doctor. |
| `start_maintenance` | — | Spawn `scripts/ops/maintenance.py` in the background. Resets `runs/operations/maintenance_status.json` to `{status: "starting"}` first. |
| `read_maintenance_status` | — | Read `runs/operations/maintenance_status.json`. Polled every 350 ms while the modal is open. |
| `read_flip_pressure_history` | `{ days? }` | Walks `signals/*.json` and returns the flip-pressure series for the sparkline. Default 60 days. |
| `read_viz_bundle` | `{ rebuild? }` | Read `viz/montauk-bundle.json`. If missing or `rebuild=true`, runs `python viz/build_viz.py --bundle-only` first. |
| `run_next_research` | `{ timeout_seconds? }` | Manually drain one approved idea (used as a fallback; Maintenance covers this path normally). |
| `research_queue_action` | `{ ideaId, action }` | `approve / dismiss / reset` on a queue entry. |
| `strategy_metric_signal` | `{ metric }` | Per-route signal review. |
| `open_viz` | — | `open viz/montauk-viz.html`. |
| `read_viz_html` | — | Legacy: read the standalone HTML. |
| `doctor_report` | — | `scripts/ops/doctor.py --json` (the maintenance modal triggers this via the orchestrator). |

Scheduler / LaunchAgent commands (`scheduler_status`, `set_scheduler_job`,
`launch_agent_status`, `manage_launch_agent`) are still defined for advanced
CLI use but the app no longer surfaces them in the UI.

---

## Artifact map (read by the app)

- `runs/operations/latest.json` — last daily run summary
- `runs/operations/events.jsonl` — append-only event log
- `runs/operations/governance.json` — champion governance state
- `runs/operations/live_holdout.json` — replay drift snapshot
- `runs/operations/strategy_review.json` — official metric review
- `runs/operations/notifications.json` — outbox + sent log
- **`runs/operations/maintenance_status.json`** — live phase status of the current/last Maintenance run (new)
- `runs/family_confidence_leaderboard.json` — family leaders + Future Confidence + Trust (joined into the leaderboard row render)
- `spike/leaderboard.json` — Gold-status leaderboard
- `runs/research_queue/queue.json` — research ideas (proposed/approved/dismissed)
- `signals/YYYY-MM-DD.json` — daily signal snapshots (latest is read for the dashboard; the last 60 are read for the sparkline)
- `viz/montauk-bundle.json` — viz bundle
- `viz/montauk-viz.html` — standalone HTML (kept as fallback)

---

## Visual system

Designed against modern-software clichés. References: 1980s retro-futurism,
neon, synthwave / vaporwave / outrun.

- Palette is fixed: `#42d69a` green, `#63c7d6` cyan, `#ff5fd2` magenta, `#7c5cff` violet, `#d7a84a` amber, `#f06666` red on a `#080a0d` near-black.
- Animations:
  - Body has a 22 s drifting scanline pattern (CSS keyframes).
  - The wordmark and the primary button use a 9 s `sweep-gradient` to animate the magenta→violet→cyan fill.
  - The `Run Maintenance` button pulses with `neon-pulse` while running.
  - Active maintenance step gets a 1.6 s `neon-pulse` outline.
- The app icon is a single corner-to-corner magenta→cyan gradient on a rounded square. No glyph.
- Tooltips use the same neon outline + cyan border + magenta shadow.

When in doubt: bigger glow, fewer borders, no rounded buttons trying to look
like SaaS.
