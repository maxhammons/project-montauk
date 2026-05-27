from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.daily import comparable_signal, compute_current_signal, load_active_champion
from ops.events import append_event, utc_now_iso
from ops.paths import LIVE_HOLDOUT_PATH, SIGNALS_DIR, ensure_ops_dirs
from ops.versioning import version_info


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def load_signal_snapshots(signals_dir: Path = SIGNALS_DIR) -> list[dict[str, Any]]:
    if not signals_dir.exists():
        return []
    snapshots = []
    for path in sorted(signals_dir.glob("*.json")):
        payload = _load_json(path)
        payload["_path"] = str(path)
        snapshots.append(payload)
    return snapshots


def compute_replay_by_date(champion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute current replay signal for the latest available date.

    This is deliberately narrow for the first live-holdout slice. It detects
    whether today's point-in-time snapshot still agrees with the current engine
    and champion. Historical full-date replay can be added once the app has more
    live snapshots.
    """

    replay = compute_current_signal(champion)
    return {str(replay["data_end_date"]): replay}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_pct(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 100.0, 4)


def _snapshot_confidence(snapshot: dict[str, Any]) -> float | None:
    return _safe_float((snapshot.get("validation") or {}).get("composite_confidence"))


def execution_proxy(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for current, nxt in zip(snapshots, snapshots[1:]):
        event = None
        if current.get("buy_event") or current.get("entry_signal"):
            event = "entry"
        elif current.get("sell_event") or current.get("exit_signal"):
            event = "exit"
        if event is None:
            continue
        close = _safe_float(current.get("close"))
        next_close = _safe_float(nxt.get("close"))
        proxy_return = None
        if close and next_close:
            proxy_return = next_close / close - 1.0
        rows.append(
            {
                "event": event,
                "signal_date": current.get("data_end_date"),
                "signal_close": close,
                "proxy_execution_date": nxt.get("data_end_date"),
                "proxy_execution_close": next_close,
                "proxy_return_pct": _round_pct(proxy_return),
                "note": "Uses the next immutable signal snapshot close as a next-open execution proxy.",
            }
        )
    return rows


def live_performance(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if len(snapshots) < 2:
        return {
            "live_signal_return_since_start_pct": None,
            "buy_hold_return_since_start_pct": None,
            "live_vs_buy_hold_multiple_proxy": None,
            "backtest_share_multiple": None,
            "backtest_vs_live_degradation_pct": None,
            "confidence_start": _snapshot_confidence(snapshots[0]) if snapshots else None,
            "confidence_latest": _snapshot_confidence(snapshots[-1]) if snapshots else None,
            "confidence_drift": None,
        }

    signal_factor = 1.0
    buy_hold_factor = 1.0
    for previous, current in zip(snapshots, snapshots[1:]):
        previous_close = _safe_float(previous.get("close"))
        current_close = _safe_float(current.get("close"))
        if not previous_close or not current_close:
            continue
        period_factor = current_close / previous_close
        buy_hold_factor *= period_factor
        if previous.get("risk_on", previous.get("risk_state") == "risk_on"):
            signal_factor *= period_factor

    live_multiple = signal_factor / buy_hold_factor if buy_hold_factor else None
    latest = snapshots[-1]
    backtest_share = _safe_float(((latest.get("active_champion") or {}).get("metrics") or {}).get("share_multiple"))
    degradation_pct = None
    if live_multiple is not None and backtest_share and backtest_share > 0:
        degradation_pct = (live_multiple / backtest_share - 1.0) * 100.0

    first_confidence = _snapshot_confidence(snapshots[0])
    latest_confidence = _snapshot_confidence(latest)
    confidence_delta = None
    if first_confidence is not None and latest_confidence is not None:
        confidence_delta = latest_confidence - first_confidence

    return {
        "live_signal_return_since_start_pct": _round_pct(signal_factor - 1.0),
        "buy_hold_return_since_start_pct": _round_pct(buy_hold_factor - 1.0),
        "live_vs_buy_hold_multiple_proxy": round(live_multiple, 4) if live_multiple is not None else None,
        "backtest_share_multiple": backtest_share,
        "backtest_vs_live_degradation_pct": round(degradation_pct, 4) if degradation_pct is not None else None,
        "confidence_start": first_confidence,
        "confidence_latest": latest_confidence,
        "confidence_drift": round(confidence_delta, 4) if confidence_delta is not None else None,
    }


def build_live_holdout(
    *,
    signals_dir: Path = SIGNALS_DIR,
    output_path: Path = LIVE_HOLDOUT_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    snapshots = load_signal_snapshots(signals_dir)
    champion = load_active_champion()
    replay_by_date = compute_replay_by_date(champion)
    comparisons: list[dict[str, Any]] = []

    for snapshot in snapshots:
        date = str(snapshot.get("data_end_date") or "")
        replay = replay_by_date.get(date)
        if not replay:
            comparisons.append({
                "date": date,
                "status": "not_replayed",
                "snapshot_path": snapshot.get("_path"),
            })
            continue
        snapshot_cmp = comparable_signal(snapshot)
        replay_cmp = comparable_signal(replay)
        matches = snapshot_cmp == replay_cmp
        comparisons.append({
            "date": date,
            "status": "match" if matches else "diverged",
            "snapshot_path": snapshot.get("_path"),
            "snapshot": snapshot_cmp,
            "replay": replay_cmp,
            "changed_fields": [
                key for key in sorted(snapshot_cmp) if snapshot_cmp.get(key) != replay_cmp.get(key)
            ],
        })

    matched = sum(1 for item in comparisons if item.get("status") == "match")
    diverged = sum(1 for item in comparisons if item.get("status") == "diverged")
    not_replayed = sum(1 for item in comparisons if item.get("status") == "not_replayed")
    first = snapshots[0] if snapshots else {}
    latest = snapshots[-1] if snapshots else {}
    start_close = float(first.get("close") or 0.0)
    latest_close = float(latest.get("close") or 0.0)
    close_return_pct = None
    if start_close > 0 and latest_close > 0 and len(snapshots) > 1:
        close_return_pct = round((latest_close / start_close - 1.0) * 100.0, 4)
    performance = live_performance(snapshots)

    report = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "status": "attention" if diverged else "ok",
        "snapshot_count": len(snapshots),
        "live_start_date": first.get("data_end_date"),
        "latest_snapshot_date": latest.get("data_end_date"),
        "matched_count": matched,
        "diverged_count": diverged,
        "not_replayed_count": not_replayed,
        "close_return_since_start_pct": close_return_pct,
        "expected_next_open_execution_proxy": execution_proxy(snapshots),
        "active_champion_performance_since_live_start": {
            "start_date": first.get("data_end_date"),
            "latest_date": latest.get("data_end_date"),
            "strategy": (latest.get("active_champion") or {}).get("strategy"),
            "signal_return_pct": performance["live_signal_return_since_start_pct"],
            "buy_hold_return_pct": performance["buy_hold_return_since_start_pct"],
            "live_vs_buy_hold_multiple_proxy": performance["live_vs_buy_hold_multiple_proxy"],
        },
        "backtest_vs_live_degradation": {
            "backtest_share_multiple": performance["backtest_share_multiple"],
            "live_vs_buy_hold_multiple_proxy": performance["live_vs_buy_hold_multiple_proxy"],
            "degradation_pct": performance["backtest_vs_live_degradation_pct"],
        },
        "confidence_drift": {
            "start": performance["confidence_start"],
            "latest": performance["confidence_latest"],
            "delta": performance["confidence_drift"],
        },
        "comparisons": comparisons,
    }
    _write_json(output_path, report)
    if diverged:
        append_event(
            "live_holdout_drift",
            "Live holdout replay diverged from a point-in-time signal snapshot.",
            severity="warning",
            payload={"diverged_count": diverged, "output_path": str(output_path)},
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Montauk live holdout report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_live_holdout()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(
            f"live holdout: {report['status']} "
            f"({report['matched_count']} match, {report['diverged_count']} diverged)"
        )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
