from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.paths import JOB_RECORDS_DIR, SCHEDULER_CONFIG_PATH, ensure_ops_dirs


DEFAULT_SCHEDULE: dict[str, Any] = {
    "schema_version": 1,
    "jobs": {
        "daily": {
            "enabled": True,
            "job": "daily",
            "label": "Daily operations",
            "schedule": {"Hour": 13, "Minute": 30},
            "description": "Refresh data, verify quality, snapshot signal, and rebuild app-facing status.",
        },
        "daily-recertify": {
            "enabled": True,
            "job": "recertify-leaderboard",
            "label": "Daily best-strategy test",
            "schedule": {"Hour": 13, "Minute": 0},
            "description": "Retest the certified leaderboard and rank it by current confidence before the daily signal.",
        },
        "daily-governance": {
            "enabled": True,
            "job": "governance",
            "label": "Daily governance check",
            "schedule": {"Hour": 13, "Minute": 45},
            "description": "Evaluate whether the active champion is ok, watch, or blocked.",
        },
        "daily-notifications": {
            "enabled": True,
            "job": "notifications",
            "label": "Daily notification scan",
            "schedule": {"Hour": 13, "Minute": 50},
            "description": "Convert important operations events into notification outbox entries.",
        },
        "daily-research-supervisor": {
            "enabled": True,
            "job": "research-approved",
            "label": "Daily approved research planner",
            "schedule": {"Hour": 14, "Minute": 10},
            "description": "Create bounded run artifacts for approved strategy research ideas.",
        },
        "daily-strategy-review": {
            "enabled": True,
            "job": "strategy-review",
            "label": "Daily best-strategy check",
            "schedule": {"Hour": 13, "Minute": 40},
            "description": "Confirm the active strategy is the highest-confidence certified leaderboard strategy.",
        },
        "spike_drain": {
            "enabled": True,
            "job": "spike-drain",
            "label": "Nightly spike drain",
            "schedule": {"Hour": 2, "Minute": 0},
            # Compute budget read by run_job.job_command at launch time so the
            # nightly drain is tunable from runs/scheduler/config.json without
            # code edits (2026-06-09). "hours" bounds the GA wall clock; add an
            # optional "pop_size" key to override spike_runner's default (40).
            "hours": 2.0,
            "description": (
                "Drain idle overnight compute into the curated search roster via a "
                "headless spike_runner GA run. Budget keys: hours (default 2.0), "
                "optional pop_size (default: spike_runner's built-in 40)."
            ),
        },
        "weekly-recertify": {
            "enabled": False,
            "job": "recertify-leaderboard",
            "label": "Weekly Gold recertification",
            "schedule": {"Weekday": 1, "Hour": 18, "Minute": 0},
            "description": "Revalidate the current Gold leaderboard under current rules.",
        },
        "weekly-family-confidence": {
            "enabled": True,
            "job": "family-confidence",
            "label": "Weekly family confidence refresh",
            "schedule": {"Weekday": 1, "Hour": 18, "Minute": 30},
            "description": "Refresh the one-row-per-family confidence surface.",
        },
        "monthly-confidence-vintage": {
            "enabled": False,
            "job": "confidence-vintage",
            "label": "Monthly Confidence v2 calibration",
            "schedule": {"Day": 1, "Hour": 19, "Minute": 0},
            "description": "Run broader confidence calibration diagnostics when explicitly enabled.",
        },
    },
}


def load_config(path: Path = SCHEDULER_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_SCHEDULE))
    with path.open(encoding="utf-8") as f:
        config = json.load(f)
    return merge_defaults(config)


def merge_defaults(config: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_SCHEDULE))
    merged.update({key: value for key, value in config.items() if key != "jobs"})
    merged_jobs = merged.setdefault("jobs", {})
    for key, job in (config.get("jobs") or {}).items():
        if key in merged_jobs:
            hydrated = dict(merged_jobs[key])
            hydrated.update(job)
            merged_jobs[key] = hydrated
        else:
            merged_jobs[key] = job
    return merged


def write_config(config: dict[str, Any], path: Path = SCHEDULER_CONFIG_PATH) -> dict[str, Any]:
    ensure_ops_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, sort_keys=False)
        f.write("\n")
    return config


def init_config(path: Path = SCHEDULER_CONFIG_PATH, *, overwrite: bool = False) -> dict[str, Any]:
    if path.exists() and not overwrite:
        return load_config(path)
    return write_config(json.loads(json.dumps(DEFAULT_SCHEDULE)), path)


def set_enabled(
    job_key: str,
    enabled: bool,
    *,
    path: Path = SCHEDULER_CONFIG_PATH,
) -> dict[str, Any]:
    config = load_config(path)
    jobs = config.setdefault("jobs", {})
    if job_key not in jobs:
        raise KeyError(f"unknown scheduled job key '{job_key}'")
    jobs[job_key]["enabled"] = enabled
    return write_config(config, path)


def list_jobs(config: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key, job in sorted((config.get("jobs") or {}).items()):
        item = dict(job)
        item["key"] = key
        out.append(item)
    return out


def _job_datetime(day: datetime, schedule: dict[str, Any]) -> datetime:
    return day.replace(
        hour=int(schedule.get("Hour", 0)),
        minute=int(schedule.get("Minute", 0)),
        second=0,
        microsecond=0,
    )


def next_run_at(schedule: dict[str, Any], *, now: datetime | None = None) -> str | None:
    """Return the next local scheduled run as ISO text.

    Weekday uses ISO numbering: Monday=1 through Sunday=7. This keeps the
    config readable even though launchd's native numbering is less friendly.
    """

    if not schedule:
        return None
    now = now or datetime.now().astimezone()

    if "Day" in schedule:
        year = now.year
        month = now.month
        for _ in range(15):
            try:
                candidate = _job_datetime(now.replace(year=year, month=month, day=int(schedule["Day"])), schedule)
            except ValueError:
                pass
            else:
                if candidate > now:
                    return candidate.isoformat(timespec="minutes")
            month += 1
            if month == 13:
                month = 1
                year += 1
        return None

    if "Weekday" in schedule:
        weekday = int(schedule["Weekday"])
        for offset in range(14):
            day = now + timedelta(days=offset)
            if day.isoweekday() != weekday:
                continue
            candidate = _job_datetime(day, schedule)
            if candidate > now:
                return candidate.isoformat(timespec="minutes")
        return None

    for offset in range(2):
        candidate = _job_datetime(now + timedelta(days=offset), schedule)
        if candidate > now:
            return candidate.isoformat(timespec="minutes")
    return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def latest_job_records(record_dir: Path = JOB_RECORDS_DIR) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not record_dir.exists():
        return latest
    for path in sorted(record_dir.glob("*.json")):
        record = _read_json(path)
        if not record or not record.get("job"):
            continue
        slim = {
            "job": record.get("job"),
            "status": record.get("status"),
            "started_utc": record.get("started_utc"),
            "finished_utc": record.get("finished_utc"),
            "returncode": record.get("returncode"),
            "record_path": record.get("record_path") or str(path),
        }
        if record.get("lock_path"):
            slim["lock_path"] = record.get("lock_path")
        latest[str(record["job"])] = slim
    return latest


def scheduler_status(
    config: dict[str, Any] | None = None,
    *,
    record_dir: Path = JOB_RECORDS_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    records = latest_job_records(record_dir)
    jobs = []
    for item in list_jobs(config):
        schedule = item.get("schedule") or {}
        job_name = item.get("job")
        jobs.append(
            {
                "key": item.get("key"),
                "label": item.get("label") or item.get("key"),
                "enabled": bool(item.get("enabled")),
                "job": job_name,
                "schedule": schedule,
                "description": item.get("description", ""),
                "next_run_local": next_run_at(schedule, now=now) if item.get("enabled") else None,
                "last_run": records.get(str(job_name)),
            }
        )
    return {
        "schema_version": 1,
        "generated_local": (now or datetime.now().astimezone()).isoformat(timespec="seconds"),
        "jobs": jobs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Montauk scheduler config.")
    sub = parser.add_subparsers(dest="cmd")
    status = sub.add_parser("status", help="Show computed scheduler status.")
    status.add_argument("--json", action="store_true", help="Emit JSON.")
    init = sub.add_parser("init", help="Create default scheduler config if missing.")
    init.add_argument("--json", action="store_true", help="Emit JSON.")
    listing = sub.add_parser("list", help="List configured jobs.")
    listing.add_argument("--json", action="store_true", help="Emit JSON.")
    enable = sub.add_parser("enable", help="Enable one scheduled job key.")
    enable.add_argument("key")
    enable.add_argument("--json", action="store_true", help="Emit JSON.")
    disable = sub.add_parser("disable", help="Disable one scheduled job key.")
    disable.add_argument("key")
    disable.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    cmd = args.cmd or "list"
    if cmd == "status":
        status_payload = scheduler_status()
        if args.json:
            print(json.dumps(status_payload, indent=2, default=str))
            return 0
        for item in status_payload["jobs"]:
            state = "enabled" if item.get("enabled") else "disabled"
            print(f"{item['key']}: {state} next={item.get('next_run_local') or '-'}")
        return 0
    if cmd == "init":
        config = init_config()
    elif cmd == "enable":
        config = set_enabled(args.key, True)
    elif cmd == "disable":
        config = set_enabled(args.key, False)
    else:
        config = load_config()

    if args.json:
        print(json.dumps(config, indent=2, default=str))
        return 0

    for item in list_jobs(config):
        state = "enabled" if item.get("enabled") else "disabled"
        print(f"{item['key']}: {state} -> {item.get('job')} @ {item.get('schedule')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
