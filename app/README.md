# Montauk App

Standalone macOS app shell for Project Montauk.

Status: local bundle builds and is installed as `/Applications/Montauk.app`.
The app is designed to read the operations artifacts created by `scripts/ops/`:

- `runs/operations/latest.json`
- `runs/operations/events.jsonl`
- `runs/operations/notifications.json`
- `signals/*.json`
- `runs/scheduler/config.json`

The Python engine remains the source of truth. The app displays artifacts and
invokes the ops commands; it does not implement strategy logic.

## Product Surface

- Dashboard: simple TECL stance, position state, confidence, flip pressure,
  active animal family, data freshness, local update state, and high-level
  health stats.
- Viz: embedded Montauk visualization.
- Doctor: leaderboard, route-level position checks, readiness, local schedule,
  and local macOS background-job controls.

Metric comparisons are read-only from the app. They do not overwrite the
official daily strategy review artifact or emit replacement-candidate events.
App operations are local-only; the app does not use GitHub Actions, remote
runners, or an AI backend as runtime decision authority.

## Development

Install frontend/Rust dependencies when ready:

```bash
npm install
npm run tauri:dev
```

Build a local macOS app bundle:

```bash
npm run tauri:build
```

The app bridge defaults to this local project path. To point the app elsewhere:

```bash
MONTAUK_PROJECT_ROOT="/path/to/Project Montauk" npm run tauri:dev
```

## Current Commands

The Tauri bridge exposes:

- `read_status`
- `run_job`
- `scan_notifications`
- `send_notifications`
- `scheduler_status`
- `doctor_report`
- `set_scheduler_job`
- `research_queue_action`
- `strategy_metric_signal`
- `start_research_run`
- `launch_agent_status`
- `manage_launch_agent`
- `open_viz`
- `read_viz_html`

The browser fallback renders from a sample status object so the dashboard can be
opened as static HTML during design work.
