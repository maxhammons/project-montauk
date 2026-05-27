# Montauk App Packaging And Update Notes

Status: active local packaging notes, 2026-05-24.

2026-05-24 verification: a signed local candidate at `/private/tmp/Montauk.app`
was installed to `/Applications/Montauk.app` with
`scripts/ops/app_update.py --candidate /private/tmp/Montauk.app --install --json`.
`codesign --verify --deep --strict /Applications/Montauk.app` passed after the
install. `scripts/ops/doctor.py --json` reported enabled LaunchAgents installed,
loaded, and last exiting with code 0. `last reboot` reported the current boot
session began on May 14, 2026; scheduler job records from May 23, 2026 confirm
the enabled jobs have run during this boot session.

## Runtime Strategy

The macOS app is a Tauri shell around the existing repository. It does not embed
or rewrite the Python engine.

- Python commands resolve to `.venv/bin/python` under the configured Project
  Montauk root, falling back to `python3` only when the virtual environment is
  missing.
- Dependencies are installed into the project-local `.venv`; app commands run
  with the repository root as the working directory.
- `MONTAUK_PROJECT_ROOT` can override root discovery for installed app bundles.
- Local state stays in repository artifacts: `runs/`, `signals/`, `data/`,
  `spike/`, and `spirit-memory/`.

Clean local install checklist:

1. Install dependencies into `.venv`.
2. Run `.venv/bin/python scripts/ops/doctor.py --json`.
3. Build the shell with `npm run tauri:build` from `app/`.
4. Copy the signed `Montauk.app` bundle to `/Applications`.
5. Launch the app, set or verify `MONTAUK_PROJECT_ROOT`, and install/load
   enabled LaunchAgents from Settings.

## Update Path

App-shell updates are signed-bundle replacements. The update path is defined by
`scripts/ops/app_update.py`:

- `--json` inspects the current local build candidate and target bundle.
- `--install` replaces the target bundle only when the candidate exists and
  passes `codesign --verify --deep --strict`.
- `--allow-unsigned` is reserved for local development and should not be used
  for routine updates.

The update step replaces only the app shell. It must not delete repository
state, signal history, scheduler config, notification state, or research
artifacts.

## Version Records

Operations artifacts include `version_info` with:

- `app_version` from `app/package.json` / Tauri config
- git commit
- dirty-worktree flag
- strategy code version

This means a shell update, strategy-code change, or validation-rule change is
visible in the artifact history. The app should not silently change strategy
code or validation rules without a corresponding version record.

## Reboot Behavior

Scheduled jobs use user LaunchAgents under `~/Library/LaunchAgents`. A reboot
survival check is:

1. Load all enabled LaunchAgents from app Settings.
2. Reboot.
3. Confirm `scripts/ops/install_launch_agent.py --all-enabled --status --json`
   reports installed and loaded jobs.
4. Confirm scheduled records appear under `runs/scheduler/jobs/`.

Settings and signal history remain in the project tree, not inside the app
bundle, so replacing the bundle does not erase them.
