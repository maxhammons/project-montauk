from __future__ import annotations

import argparse
import json
import os
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
    }
    return paths.get(job, [])


def _default_runner(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
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
) -> dict[str, Any]:
    """Run one named operations job and write a structured job record."""

    ensure_ops_dirs()
    started_utc = utc_now_iso()
    safe_started = started_utc.replace(":", "").replace("-", "")
    record_path = record_dir / f"{safe_started}-{job}.json"
    command = job_command(job, python=python) + list(extra_args or [])
    lock_path = None
    lock_payload = None
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
            lock_path, lock_payload = acquire_lock(job)
            record["lock_path"] = str(lock_path)
            if lock_payload.get("recovered_stale_lock"):
                record["recovered_stale_lock"] = True
        except JobLockedError as exc:
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
        record["record_path"] = str(record_path)
        _write_json(record_path, record)
    finally:
        if lock_path is not None and lock_payload is not None:
            release_lock(lock_path, lock_payload)

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
