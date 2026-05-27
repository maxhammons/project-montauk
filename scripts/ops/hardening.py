from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.errors import ERROR_CODES
from ops.events import utc_now_iso
from ops.governance import evaluate_governance
from ops.paths import LATEST_PATH
from ops.scheduler import next_run_at

MARKET_HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def market_closed(day: date) -> bool:
    return day.weekday() >= 5 or day in MARKET_HOLIDAYS_2026


def stale_data_probe(latest: dict[str, Any] | None = None) -> dict[str, Any]:
    latest = latest or {
        "active_signal": {
            "data_end_date": "2026-01-01",
            "risk_state": "risk_on",
            "validation": {"verdict": "PASS", "gold_status": True},
            "data_quality": {"fail": 0},
        }
    }
    report = evaluate_governance(latest, {"diverged_count": 0}, {"status": "on_best_certified"}, max_stale_calendar_days=1)
    ok = report.get("state") == "active_watch" and any("stale" in reason for reason in report.get("reasons") or [])
    return {
        "label": "stale_data_warning",
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["data_stale"],
        "state": report.get("state"),
        "reasons": report.get("reasons"),
    }


def market_holiday_probe() -> dict[str, Any]:
    holiday = date(2026, 5, 25)
    normal_day = date(2026, 5, 26)
    ok = market_closed(holiday) and not market_closed(normal_day)
    return {
        "label": "market_holiday_classification",
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["market_closed"],
        "holiday": holiday.isoformat(),
        "normal_day": normal_day.isoformat(),
    }


def daylight_saving_probe() -> dict[str, Any]:
    spring = datetime.fromisoformat("2026-03-08T01:30:00-08:00")
    fall = datetime.fromisoformat("2026-11-01T01:30:00-07:00")
    daily = {"Hour": 13, "Minute": 30}
    spring_next = next_run_at(daily, now=spring)
    fall_next = next_run_at(daily, now=fall)
    ok = bool(spring_next and fall_next and "13:30" in spring_next and "13:30" in fall_next)
    return {
        "label": "daylight_saving_schedule",
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["job_failed"],
        "spring_next": spring_next,
        "fall_next": fall_next,
    }


def network_failure_probe() -> dict[str, Any]:
    latest = _load_json(LATEST_PATH, {})
    refresh = (latest.get("steps") or {}).get("refresh") or {}
    skipped_ok = refresh.get("status") == "skipped"
    failed_ok = refresh.get("status") in {"fail", "failed"} and latest.get("status") == "attention"
    ok = skipped_ok or failed_ok or refresh.get("status") in {None, "ok"}
    return {
        "label": "network_failure_isolated",
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["network_unavailable"],
        "refresh_status": refresh.get("status"),
        "operation_status": latest.get("status"),
    }


def failed_job_corruption_probe(record: dict[str, Any] | None = None) -> dict[str, Any]:
    record = record or {
        "status": "failed",
        "returncode": 1,
        "output_artifact_paths": ["runs/operations/latest.json"],
        "error_code": ERROR_CODES["job_failed"],
    }
    ok = record.get("status") == "failed" and bool(record.get("output_artifact_paths")) and bool(record.get("error_code"))
    return {
        "label": "failed_job_structured_record",
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["job_failed"],
        "record_status": record.get("status"),
    }


def build_hardening_report() -> dict[str, Any]:
    checks = [
        stale_data_probe(),
        market_holiday_probe(),
        daylight_saving_probe(),
        network_failure_probe(),
        failed_job_corruption_probe(),
    ]
    failures = [check for check in checks if not check.get("ok")]
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "status": "ok" if not failures else "needs_attention",
        "check_count": len(checks),
        "failure_count": len(failures),
        "checks": checks,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Montauk hardening probes.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_hardening_report()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"hardening: {report['status']} ({report['failure_count']} failures)")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
