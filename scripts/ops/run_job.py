from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.errors import ERROR_CODES, classify_process_failure
from ops.paths import EVENTS_PATH, JOB_RECORDS_DIR, LOCKS_DIR, PROJECT_ROOT, ensure_ops_dirs
from ops.scheduler import load_config

CommandRunner = Callable[[list[str]], subprocess.CompletedProcess]

# Fallback compute budget for the nightly spike drain when the scheduler
# config omits an "hours" key. Kept here (not in spike_runner) because the
# bound exists to protect the scheduler's slot, not the GA itself. (2026-06-09)
SPIKE_DRAIN_DEFAULT_HOURS = 2.0

# Jobs that must also hold other jobs' locks while running. The nightly spike
# drain reads the CSVs the daily refresh rewrites and publishes spike/
# leaderboard artifacts the daily surfaces consume, so it acquires the 'daily'
# lock too — acquiring (not merely probing) it closes the race where 'daily'
# starts mid-drain. A blocked acquisition skips the run; nothing queues.
# (2026-06-09)
CONFLICT_LOCK_JOBS: dict[str, tuple[str, ...]] = {
    "spike-drain": ("daily",),
}

# Long-running jobs emit an explicit job_started event so a quiet events log
# during a 2h GA run is distinguishable from a job that never launched.
# (2026-06-09)
START_EVENT_JOBS = frozenset({"spike-drain"})


class JobLockedError(RuntimeError):
    def __init__(self, lock_path: Path, payload: dict[str, Any]):
        self.lock_path = lock_path
        self.payload = payload
        super().__init__(f"job lock exists: {lock_path}")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def acquire_lock(
    job: str,
    *,
    locks_dir: Path = LOCKS_DIR,
    stale_after_seconds: int = 6 * 60 * 60,
) -> tuple[Path, dict[str, Any]]:
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_path = locks_dir / f"{job}.lock"
    now = time.time()
    payload = {
        "schema_version": 1,
        "job": job,
        "pid": os.getpid(),
        "started_utc": utc_now_iso(),
        "started_epoch": now,
    }
    try:
        with lock_path.open("x", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        return lock_path, payload
    except FileExistsError:
        existing = _load_json(lock_path)
        started = float(existing.get("started_epoch") or 0.0)
        if started > 0 and now - started > stale_after_seconds:
            payload["recovered_stale_lock"] = existing
            _write_json(lock_path, payload)
            return lock_path, payload
        raise JobLockedError(lock_path, existing) from None


def release_lock(lock_path: Path, lock_payload: dict[str, Any]) -> None:
    if not lock_path.exists():
        return
    try:
        existing = _load_json(lock_path)
    except (OSError, json.JSONDecodeError):
        return
    if existing.get("pid") == lock_payload.get("pid") and existing.get("started_epoch") == lock_payload.get("started_epoch"):
        lock_path.unlink()


def default_python() -> str:
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def spike_drain_budget(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the nightly spike-drain compute budget from scheduler config.

    WHY: the drain budget must be tunable from runs/scheduler/config.json
    (job entry "spike_drain", keys "hours" / "pop_size") without code edits.
    pop_size is only included when explicitly configured so spike_runner keeps
    owning its own default. (2026-06-09)
    """

    entry: dict[str, Any] = {}
    loaded = config or load_config()
    for item in (loaded.get("jobs") or {}).values():
        if item.get("job") == "spike-drain":
            entry = item
            break
    budget: dict[str, Any] = {"hours": float(entry.get("hours", SPIKE_DRAIN_DEFAULT_HOURS))}
    pop_size = entry.get("pop_size")
    if pop_size is not None:
        budget["pop_size"] = int(pop_size)
    return budget


def _spike_drain_command(py: str, scripts: Path) -> list[str]:
    budget = spike_drain_budget()
    command = [
        py,
        str(scripts / "search" / "spike_runner.py"),
        "--hours",
        str(budget["hours"]),
    ]
    if "pop_size" in budget:
        command += ["--pop-size", str(budget["pop_size"])]
    return command


def job_command(job: str, *, python: str | None = None) -> list[str]:
    py = python or default_python()
    scripts = PROJECT_ROOT / "scripts"
    commands = {
        "daily": [py, str(scripts / "ops" / "daily.py")],
        "daily-local": [
            py,
            str(scripts / "ops" / "daily.py"),
            "--skip-refresh",
            "--skip-viz",
        ],
        "status": [py, str(scripts / "ops" / "status.py"), "--json"],
        "live-holdout": [py, str(scripts / "ops" / "live_holdout.py")],
        "reconcile-signals": [py, str(scripts / "ops" / "reconcile_signals.py")],
        "governance": [py, str(scripts / "ops" / "governance.py")],
        "strategy-review": [py, str(scripts / "ops" / "strategy_review.py"), "--json"],
        "research-propose": [py, str(scripts / "ops" / "research_queue.py"), "propose"],
        "research-approved": [py, str(scripts / "ops" / "research_runner.py"), "--json"],
        "notifications": [py, str(scripts / "ops" / "notifications.py"), "--scan"],
        "doctor": [py, str(scripts / "ops" / "doctor.py"), "--json"],
        "build-viz": [py, str(PROJECT_ROOT / "viz" / "build_viz.py")],
        "recertify-leaderboard": [
            py,
            str(scripts / "certify" / "recertify_leaderboard.py"),
        ],
        "family-confidence": [
            py,
            str(scripts / "diagnostics" / "family_confidence_leaderboard.py"),
        ],
        "confidence-archive": [
            py,
            str(scripts / "diagnostics" / "confidence_candidate_archive.py"),
        ],
        "confidence-vintage": [
            py,
            str(scripts / "diagnostics" / "confidence_vintage_harness.py"),
        ],
        # Headless GA run; budget comes from scheduler config, not code.
        "spike-drain": _spike_drain_command(py, scripts),
    }
    if job not in commands:
        known = ", ".join(sorted(commands))
        raise KeyError(f"unknown job '{job}'. Known jobs: {known}")
    return commands[job]


def job_schedule(job: str) -> dict[str, Any] | None:
    config = load_config()
    for key, item in (config.get("jobs") or {}).items():
        if item.get("job") == job:
            return {
                "key": key,
                "enabled": bool(item.get("enabled")),
                "schedule": item.get("schedule") or {},
            }
    return None


def output_artifact_paths(job: str) -> list[str]:
    paths = {
        "daily": [
            "runs/operations/latest.json",
            "signals/YYYY-MM-DD.json",
            "viz/montauk-viz.html",
            "viz/montauk-bundle.json",
        ],
        "daily-local": [
            "runs/operations/latest.json",
            "signals/YYYY-MM-DD.json",
        ],
        "status": ["runs/operations/latest.json"],
        "live-holdout": ["runs/operations/live_holdout.json"],
        "reconcile-signals": ["runs/operations/live_holdout.json"],
        "governance": ["runs/operations/governance.json"],
        "strategy-review": ["runs/operations/strategy_review.json"],
        "research-propose": ["runs/research_queue/queue.json", "runs/research_queue/ideas/*.json"],
        "research-approved": ["runs/research_queue/runs/*.json"],
        "notifications": ["runs/operations/notifications.json"],
        "doctor": ["runs/operations/latest.json"],
        "build-viz": ["viz/montauk-viz.html", "viz/montauk-bundle.json"],
        "recertify-leaderboard": ["spike/leaderboard.json"],
        "family-confidence": ["runs/family_confidence_leaderboard.json"],
        "confidence-archive": ["runs/confidence_v2/candidate_archive.json"],
        "confidence-vintage": ["runs/confidence_v2/vintage_trials.json"],
        # spike_runner creates spike/runs/NNN/ itself; the job record's
        # spike_run_dir field pins the exact run dir after completion.
        "spike-drain": [
            "spike/runs/NNN/",
            "spike/leaderboard.json",
            "spike/hash-index.json",
        ],
    }
    return paths.get(job, [])


def _default_runner(command: list[str]) -> subprocess.CompletedProcess:
    # stdin=DEVNULL keeps every scheduled job headless-safe: a child that
    # tries to read input gets immediate EOF instead of blocking a launchd
    # run forever on a TTY that does not exist. (2026-06-09)
    return subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def run_job(
    job: str,
    *,
    extra_args: list[str] | None = None,
    record_dir: Path = JOB_RECORDS_DIR,
    events_path: Path = EVENTS_PATH,
    runner: CommandRunner | None = None,
    python: str | None = None,
    no_lock: bool = False,
    locks_dir: Path = LOCKS_DIR,
) -> dict[str, Any]:
    """Run one named operations job and write a structured job record."""

    ensure_ops_dirs()
    started_utc = utc_now_iso()
    safe_started = started_utc.replace(":", "").replace("-", "")
    record_path = record_dir / f"{safe_started}-{job}.json"
    command = job_command(job, python=python)
    extras = list(extra_args or [])
    # Extra args override the job's configured flags rather than duplicating
    # them (2026-06-09): `--job spike-drain -- --hours 0.02` previously
    # produced `--hours 2.0 --hours 0.02`, working only via argparse
    # last-wins while the job record misreported the budget.
    override_flags = {a for a in extras if a.startswith("--")}
    if override_flags:
        cleaned: list[str] = []
        skip_value = False
        for token in command:
            if skip_value:
                skip_value = False
                continue
            if token in override_flags:
                skip_value = True
                continue
            cleaned.append(token)
        command = cleaned
    command += extras
    held_locks: list[tuple[Path, dict[str, Any]]] = []
    record: dict[str, Any] = {
        "schema_version": 1,
        "job": job,
        "status": "running",
        "started_utc": started_utc,
        "finished_utc": None,
        "command": command,
        "cwd": str(PROJECT_ROOT),
        "schedule": job_schedule(job),
        "output_artifact_paths": output_artifact_paths(job),
        "returncode": None,
        "error_code": None,
        "stdout_tail": "",
        "stderr_tail": "",
    }
    _write_json(record_path, record)

    if not no_lock:
        try:
            lock_path, lock_payload = acquire_lock(job, locks_dir=locks_dir)
            held_locks.append((lock_path, lock_payload))
            record["lock_path"] = str(lock_path)
            if lock_payload.get("recovered_stale_lock"):
                record["recovered_stale_lock"] = True
            # Conflict locks (e.g. spike-drain holding 'daily') are acquired
            # after the job's own lock; if any are busy the whole run is
            # skipped — scheduled runs never queue behind a live conflict.
            for conflict_job in CONFLICT_LOCK_JOBS.get(job, ()):
                conflict_path, conflict_payload = acquire_lock(conflict_job, locks_dir=locks_dir)
                held_locks.append((conflict_path, conflict_payload))
            if len(held_locks) > 1:
                record["conflict_lock_paths"] = [str(path) for path, _ in held_locks[1:]]
        except JobLockedError as exc:
            for held_path, held_payload in held_locks:
                release_lock(held_path, held_payload)
            record["finished_utc"] = utc_now_iso()
            record["status"] = "locked"
            record["error_code"] = ERROR_CODES["job_locked"]
            record["lock_path"] = str(exc.lock_path)
            record["lock"] = exc.payload
            record["record_path"] = str(record_path)
            _write_json(record_path, record)
            append_event(
                "job_locked",
                f"Scheduled job '{job}' skipped because another run is active.",
                severity="warning",
                payload={"job": job, "record_path": str(record_path), "lock_path": str(exc.lock_path)},
                events_path=events_path,
            )
            return record

    if job in START_EVENT_JOBS:
        append_event(
            "job_started",
            f"Scheduled job '{job}' started.",
            severity="info",
            payload={"job": job, "record_path": str(record_path), "command": command},
            events_path=events_path,
        )

    try:
        run = runner or _default_runner
        completed = run(command)
        record["finished_utc"] = utc_now_iso()
        record["returncode"] = completed.returncode
        record["stdout_tail"] = (completed.stdout or "")[-8000:]
        record["stderr_tail"] = (completed.stderr or "")[-8000:]
        record["status"] = "ok" if completed.returncode == 0 else "failed"
        record["error_code"] = None if completed.returncode == 0 else classify_process_failure(
            completed.returncode,
            completed.stderr or "",
            completed.stdout or "",
        )
        if job == "spike-drain":
            # Pin the exact spike/runs/NNN/ dir in the job record so the
            # nightly drain's output is findable without scanning stdout.
            match = re.search(r"^Run directory: (.+)$", completed.stdout or "", re.MULTILINE)
            if match:
                record["spike_run_dir"] = match.group(1).strip()
        record["record_path"] = str(record_path)
        _write_json(record_path, record)
    finally:
        for held_path, held_payload in held_locks:
            release_lock(held_path, held_payload)

    if completed.returncode == 0:
        append_event(
            "job_succeeded",
            f"Scheduled job '{job}' completed.",
            severity="info",
            payload={"job": job, "record_path": str(record_path)},
            events_path=events_path,
        )
    else:
        append_event(
            "job_failed",
            f"Scheduled job '{job}' failed.",
            severity="error",
            payload={
                "job": job,
                "record_path": str(record_path),
                "returncode": completed.returncode,
                "error_code": record.get("error_code"),
            },
            events_path=events_path,
        )
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Montauk scheduled job.")
    parser.add_argument("--job", required=True, help="Named job to run.")
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed to the underlying job after '--'.",
    )
    parser.add_argument("--json", action="store_true", help="Emit full job record.")
    parser.add_argument("--no-lock", action="store_true", help="Run without acquiring a scheduler lock.")
    args = parser.parse_args(argv)

    extra_args = list(args.extra_args or [])
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    record = run_job(args.job, extra_args=extra_args, no_lock=args.no_lock)
    if args.json:
        print(json.dumps(record, indent=2, default=str))
    else:
        print(f"{record['job']}: {record['status']} ({record['record_path']})")
    return 0 if record.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
