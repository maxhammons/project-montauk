from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import GOVERNANCE_PATH, LATEST_PATH, LIVE_HOLDOUT_PATH, ensure_ops_dirs


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def _days_stale(data_end_date: str | None) -> int | None:
    if not data_end_date:
        return None
    try:
        end = date.fromisoformat(str(data_end_date))
    except ValueError:
        return None
    return (date.today() - end).days


def evaluate_governance(
    latest_operation: dict[str, Any] | None,
    live_holdout: dict[str, Any] | None,
    *,
    max_stale_calendar_days: int = 5,
) -> dict[str, Any]:
    latest_operation = latest_operation or {}
    signal = latest_operation.get("active_signal") or latest_operation.get("latest_signal") or {}
    validation = signal.get("validation") or {}
    data_quality = signal.get("data_quality") or {}
    reasons: list[str] = []
    blockers: list[str] = []
    advisories: list[str] = []

    if not signal:
        blockers.append("no active signal snapshot")
    if validation and not validation.get("gold_status", False):
        blockers.append("active champion is not Gold Status")
    if validation and validation.get("verdict") != "PASS":
        blockers.append("active champion validation verdict is not PASS")
    if data_quality.get("fail", 0):
        blockers.append("data quality has failing checks")
    if live_holdout and live_holdout.get("diverged_count", 0):
        blockers.append("live holdout replay diverged from point-in-time signals")

    stale_days = _days_stale(signal.get("data_end_date"))
    if stale_days is None:
        advisories.append("data staleness could not be evaluated")
    elif stale_days > max_stale_calendar_days:
        advisories.append(f"data is {stale_days} calendar days stale")

    warnings = signal.get("warnings") or []
    if warnings:
        advisories.append(f"{len(warnings)} validation warnings are active")

    if blockers:
        state = "active_blocked"
        reasons.extend(blockers)
    elif advisories:
        state = "active_watch"
        reasons.extend(advisories)
    else:
        state = "active_ok"
        reasons.append("active champion is Gold Status with current clean operations artifacts")

    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "state": state,
        "reasons": reasons,
        "blockers": blockers,
        "advisories": advisories,
        "stale_calendar_days": stale_days,
        "active_signal": {
            "data_end_date": signal.get("data_end_date"),
            "risk_state": signal.get("risk_state"),
            "strategy": (signal.get("active_champion") or {}).get("strategy"),
            "params_hash": (signal.get("active_champion") or {}).get("params_hash"),
        },
        "live_holdout": {
            "status": (live_holdout or {}).get("status"),
            "snapshot_count": (live_holdout or {}).get("snapshot_count"),
            "diverged_count": (live_holdout or {}).get("diverged_count"),
        },
    }


def build_governance(
    *,
    latest_path: Path = LATEST_PATH,
    live_holdout_path: Path = LIVE_HOLDOUT_PATH,
    output_path: Path = GOVERNANCE_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    report = evaluate_governance(
        _load_json(latest_path, {}),
        _load_json(live_holdout_path, {}),
    )
    _write_json(output_path, report)
    if report["state"] == "active_blocked":
        append_event(
            "champion_blocked",
            "Active champion requires manual review.",
            severity="error",
            payload=report,
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Montauk champion governance report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_governance()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"governance: {report['state']}")
        for reason in report["reasons"]:
            print(f"- {reason}")
    return 0 if report["state"] != "active_blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())

