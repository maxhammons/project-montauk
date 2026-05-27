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
from ops.paths import GOVERNANCE_PATH, LATEST_PATH, LIVE_HOLDOUT_PATH, STRATEGY_REVIEW_PATH, ensure_ops_dirs
from ops.versioning import version_info


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
    strategy_review: dict[str, Any] | None = None,
    *,
    max_stale_calendar_days: int = 5,
    min_confidence_drift: float = -0.05,
    min_live_vs_buy_hold_multiple: float = 0.85,
) -> dict[str, Any]:
    latest_operation = latest_operation or {}
    live_holdout = live_holdout or {}
    strategy_review = strategy_review or {}
    signal = latest_operation.get("active_signal") or latest_operation.get("latest_signal") or {}
    validation = signal.get("validation") or {}
    data_quality = signal.get("data_quality") or {}
    reasons: list[str] = []
    blockers: list[str] = []
    advisories: list[str] = []
    review_reasons: list[str] = []

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

    confidence_drift = (live_holdout.get("confidence_drift") or {}).get("delta")
    if isinstance(confidence_drift, (int, float)) and confidence_drift <= min_confidence_drift:
        review_reasons.append(f"confidence drift deteriorated by {confidence_drift:.4f}")

    live_multiple = (
        live_holdout.get("active_champion_performance_since_live_start") or {}
    ).get("live_vs_buy_hold_multiple_proxy")
    if isinstance(live_multiple, (int, float)) and live_multiple < min_live_vs_buy_hold_multiple:
        review_reasons.append(f"live trust proxy fell to {live_multiple:.4f}x buy-and-hold")

    if strategy_review.get("status") == "switch_candidate":
        best = strategy_review.get("best_certified") or {}
        review_reasons.append(
            "replacement candidate available"
            + (f": {best.get('strategy')}" if best.get("strategy") else "")
        )

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
    elif any(reason.startswith(("confidence drift", "live trust proxy")) for reason in review_reasons):
        state = "manual_review_required"
        reasons.extend(review_reasons)
    elif strategy_review.get("status") == "switch_candidate":
        state = "replacement_candidate"
        reasons.extend(review_reasons)
    elif advisories:
        state = "active_watch"
        reasons.extend(advisories)
    else:
        state = "active_ok"
        reasons.append("active champion is Gold Status with current clean operations artifacts")

    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "state": state,
        "reasons": reasons,
        "blockers": blockers,
        "advisories": advisories,
        "review_reasons": review_reasons,
        "stale_calendar_days": stale_days,
        "active_signal": {
            "data_end_date": signal.get("data_end_date"),
            "risk_state": signal.get("risk_state"),
            "strategy": (signal.get("active_champion") or {}).get("strategy"),
            "params_hash": (signal.get("active_champion") or {}).get("params_hash"),
        },
        "live_holdout": {
            "status": live_holdout.get("status"),
            "snapshot_count": live_holdout.get("snapshot_count"),
            "diverged_count": live_holdout.get("diverged_count"),
            "confidence_drift": live_holdout.get("confidence_drift"),
            "active_champion_performance_since_live_start": live_holdout.get(
                "active_champion_performance_since_live_start"
            ),
        },
        "strategy_review": {
            "status": strategy_review.get("status"),
            "active": strategy_review.get("active"),
            "best_certified": strategy_review.get("best_certified"),
        },
    }


def build_governance(
    *,
    latest_path: Path = LATEST_PATH,
    live_holdout_path: Path = LIVE_HOLDOUT_PATH,
    strategy_review_path: Path = STRATEGY_REVIEW_PATH,
    output_path: Path = GOVERNANCE_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    previous = _load_json(output_path, {})
    report = evaluate_governance(
        _load_json(latest_path, {}),
        _load_json(live_holdout_path, {}),
        _load_json(strategy_review_path, {}),
    )
    _write_json(output_path, report)
    previous_signal = previous.get("active_signal") or {}
    current_signal = report.get("active_signal") or {}
    previous_identity = (
        previous_signal.get("strategy"),
        previous_signal.get("params_hash"),
    )
    current_identity = (
        current_signal.get("strategy"),
        current_signal.get("params_hash"),
    )
    if previous_signal and current_signal and previous_identity != current_identity:
        append_event(
            "champion_changed",
            "Active champion changed.",
            severity="notice",
            payload={
                "previous": previous_signal,
                "current": current_signal,
                "governance_state": report.get("state"),
            },
        )
    if report.get("stale_calendar_days") is not None and report["stale_calendar_days"] > 5:
        append_event(
            "data_stale",
            f"Data is {report['stale_calendar_days']} calendar days stale.",
            severity="warning",
            payload=report,
        )
    if report["state"] == "manual_review_required":
        append_event(
            "manual_review_required",
            "Active champion requires manual governance review.",
            severity="warning",
            payload=report,
        )
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
