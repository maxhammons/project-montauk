from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import EVENTS_PATH, LATEST_PATH, LEADERBOARD_PATH, STRATEGY_REVIEW_PATH, ensure_ops_dirs


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


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


METRIC_LABELS = {
    "montauk": "Montauk Score",
    "confidence": "composite_confidence",
    "share_multiple": "full-history share multiple",
    "real_share_multiple": "real-era share multiple",
    "modern_share_multiple": "modern-era share multiple",
}


def strategy_score(row: dict[str, Any], metric: str = "montauk") -> float:
    if metric == "montauk":
        # Montauk Score is the headline ranking score (top-level on the row).
        try:
            return float(row.get("montauk_score") or 0.0)
        except (TypeError, ValueError):
            return 0.0
    if metric == "confidence":
        return confidence_score(row)
    metrics = row.get("metrics") or {}
    try:
        return float(metrics.get(metric) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def confidence_score(row: dict[str, Any]) -> float:
    validation = row.get("validation") or {}
    try:
        return float(validation.get("composite_confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def is_gold(row: dict[str, Any]) -> bool:
    validation = row.get("validation") or {}
    return bool(row.get("gold_status") or validation.get("gold_status")) and validation.get("verdict") == "PASS"


def strategy_identity(row: dict[str, Any] | None, *, metric: str = "montauk") -> dict[str, Any]:
    row = row or {}
    validation = row.get("validation") or {}
    metrics = row.get("metrics") or {}
    return {
        "strategy": row.get("strategy"),
        "rank": row.get("rank"),
        "display_name": row.get("display_name"),
        "params_hash": _stable_hash(row.get("params") or {}),
        "montauk_score": row.get("montauk_score"),
        "confidence": validation.get("composite_confidence"),
        "selected_score": strategy_score(row, metric),
        "score_label": METRIC_LABELS.get(metric, metric),
        "share_multiple": metrics.get("share_multiple"),
        "real_share_multiple": metrics.get("real_share_multiple"),
        "modern_share_multiple": metrics.get("modern_share_multiple"),
    }


def active_from_latest(latest: dict[str, Any]) -> dict[str, Any]:
    signal = latest.get("active_signal") or latest.get("latest_signal") or {}
    champion = signal.get("active_champion") or {}
    return {
        "strategy": champion.get("strategy"),
        "rank": champion.get("rank"),
        "params_hash": champion.get("params_hash"),
        "confidence": ((signal.get("validation") or {}).get("composite_confidence")),
        "score_label": "composite_confidence",
        "data_end_date": signal.get("data_end_date"),
        "risk_state": signal.get("risk_state"),
    }


def build_strategy_review(
    *,
    leaderboard_path: Path = LEADERBOARD_PATH,
    latest_path: Path = LATEST_PATH,
    output_path: Path = STRATEGY_REVIEW_PATH,
    events_path: Path = EVENTS_PATH,
    metric: str = "montauk",
    include_signal: bool = False,
    write: bool = True,
    emit_event: bool = True,
) -> dict[str, Any]:
    if metric not in METRIC_LABELS:
        raise ValueError(f"unknown strategy selection metric: {metric}")
    ensure_ops_dirs()
    leaderboard = _load_json(leaderboard_path, [])
    latest = _load_json(latest_path, {})
    gold = [row for row in leaderboard if is_gold(row)]
    best = (
        max(gold, key=lambda row: (strategy_score(row, metric), confidence_score(row)))
        if gold
        else (leaderboard[0] if leaderboard else None)
    )
    active = active_from_latest(latest)
    best_identity = strategy_identity(best, metric=metric)
    active_strategy = active.get("strategy")
    best_strategy = best_identity.get("strategy")
    active_hash = active.get("params_hash")
    best_hash = best_identity.get("params_hash")
    on_best = bool(
        active_strategy
        and best_strategy
        and active_strategy == best_strategy
        and (not active_hash or not best_hash or active_hash == best_hash)
    )
    status = "on_best_certified" if on_best else "switch_candidate"
    if not best_strategy:
        status = "no_certified_strategy"
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "status": status,
        "on_best_certified": on_best,
        "selection_metric": metric,
        "selection_rule": f"highest {METRIC_LABELS[metric]} among current Gold PASS leaderboard rows",
        "active": active,
        "best_certified": best_identity,
        "leaderboard_count": len(leaderboard),
        "gold_count": len(gold),
    }
    if include_signal and best:
        from ops.daily import compute_current_signal

        with contextlib.redirect_stdout(sys.stderr):
            payload["selected_signal"] = compute_current_signal(best)
    if write:
        _write_json(output_path, payload)
    if write and emit_event and status == "switch_candidate":
        append_event(
            "replacement_candidate",
            "A higher-confidence certified strategy is available for review.",
            severity="notice",
            payload=payload,
            events_path=events_path,
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review whether Montauk is on the best certified strategy.")
    parser.add_argument(
        "--metric",
        default="montauk",
        choices=sorted(METRIC_LABELS),
        help="How to choose the best certified strategy.",
    )
    parser.add_argument("--include-signal", action="store_true", help="Also compute risk on/off for the selected strategy.")
    parser.add_argument("--no-write", action="store_true", help="Do not write artifacts or emit events.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_strategy_review(metric=args.metric, include_signal=args.include_signal, write=not args.no_write)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        best = report.get("best_certified") or {}
        print(f"strategy review: {report['status']}")
        print(f"best certified: {best.get('strategy')} confidence={best.get('confidence')}")
    return 0 if report["status"] != "no_certified_strategy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
