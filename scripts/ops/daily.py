from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import (
    LATEST_PATH,
    LEADERBOARD_PATH,
    PROJECT_ROOT,
    SIGNALS_DIR,
    ensure_ops_dirs,
)
from ops.versioning import version_info


def _load_json(path: Path) -> Any:
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


def _summarize_validation(validation: dict[str, Any] | None) -> dict[str, Any]:
    validation = validation or {}
    checks = validation.get("certification_checks") or {}
    return {
        "verdict": validation.get("verdict"),
        "promotion_ready": bool(validation.get("promotion_ready", False)),
        "certified_not_overfit": bool(validation.get("certified_not_overfit", False)),
        "backtest_certified": bool(validation.get("backtest_certified", False)),
        "gold_status": bool(validation.get("gold_status", False)),
        "composite_confidence": validation.get("composite_confidence"),
        "tier": validation.get("tier"),
        "warnings": list(validation.get("warnings") or [])[:20],
        "hard_fail_reasons": list(validation.get("hard_fail_reasons") or []),
        "certification_checks": {
            name: {
                "passed": bool((check or {}).get("passed", False)),
                "status": (check or {}).get("status"),
            }
            for name, check in checks.items()
        },
    }


def load_active_champion(leaderboard_path: Path = LEADERBOARD_PATH) -> dict[str, Any]:
    leaderboard = _load_json(leaderboard_path)
    if not isinstance(leaderboard, list) or not leaderboard:
        raise ValueError(f"{leaderboard_path} must contain a non-empty leaderboard list")
    gold = []
    for entry in leaderboard:
        validation = entry.get("validation") or {}
        if entry.get("gold_status") is True or validation.get("gold_status") is True:
            gold.append(entry)
    if gold:
        return max(
            gold,
            key=lambda entry: float((entry.get("validation") or {}).get("composite_confidence") or 0.0),
        )
    return leaderboard[0]


def simulate_signal_state(
    entries: list[bool],
    exits: list[bool],
    *,
    cooldown_bars: int = 0,
) -> tuple[list[bool], list[bool], list[bool]]:
    """Convert entry/exit events to end-of-bar deployment state.

    This is intentionally independent from BacktestResult's forced end-of-data
    close. A daily signal snapshot should describe the state after the latest
    real bar, not create a synthetic sell event just because the dataset ended.
    """

    risk_on: list[bool] = []
    buy_events: list[bool] = []
    sell_events: list[bool] = []
    position = False
    last_sell_bar = -9999

    for i, (entry, exit_) in enumerate(zip(entries, exits)):
        buy = False
        sell = False
        if position and exit_:
            position = False
            sell = True
            last_sell_bar = i
        if (not position) and entry and (i - last_sell_bar) > cooldown_bars:
            position = True
            buy = True
        risk_on.append(position)
        buy_events.append(buy)
        sell_events.append(sell)
    return risk_on, buy_events, sell_events


def compute_current_signal(champion: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd

    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators
    from strategies.library import STRATEGY_REGISTRY

    strategy_name = champion.get("strategy")
    params = champion.get("params") or {}
    strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
    if strategy_fn is None:
        raise KeyError(f"{strategy_name} missing from STRATEGY_REGISTRY")

    df = get_tecl_data(use_yfinance=False)
    if df.empty:
        raise ValueError("TECL dataset is empty")

    indicators = Indicators(df)
    entries, exits, labels = strategy_fn(indicators, params)
    entries_list = [bool(v) for v in entries]
    exits_list = [bool(v) for v in exits]
    risk_on, buy_events, sell_events = simulate_signal_state(
        entries_list,
        exits_list,
        cooldown_bars=int(params.get("cooldown", 0) or 0),
    )

    idx = len(df) - 1
    data_end = str(pd.Timestamp(df.iloc[idx]["date"]).date())
    exit_label = ""
    if exits_list[idx] and labels is not None:
        exit_label = str(labels[idx])
    validation = champion.get("validation") or {}
    metrics = champion.get("metrics") or {}
    return {
        "snapshot_schema_version": 1,
        "generated_utc": utc_now_iso(),
        "data_end_date": data_end,
        "active_champion": {
            "strategy": strategy_name,
            "rank": champion.get("rank", 1),
            "date": champion.get("date"),
            "params_hash": _stable_hash(params),
            "params": params,
            "metrics": {
                "share_multiple": metrics.get("share_multiple"),
                "real_share_multiple": metrics.get("real_share_multiple"),
                "modern_share_multiple": metrics.get("modern_share_multiple"),
                "max_dd": metrics.get("max_dd"),
                "trades": metrics.get("trades"),
            },
        },
        "risk_state": "risk_on" if risk_on[idx] else "risk_off",
        "risk_on": bool(risk_on[idx]),
        "entry_signal": bool(entries_list[idx]),
        "exit_signal": bool(exits_list[idx]),
        "exit_label": exit_label,
        "buy_event": bool(buy_events[idx]),
        "sell_event": bool(sell_events[idx]),
        "close": round(float(df.iloc[idx]["close"]), 6),
        "validation": _summarize_validation(validation),
        "warnings": list(validation.get("warnings") or [])[:20],
        "blockers": list(validation.get("hard_fail_reasons") or []),
    }


def comparable_signal(snapshot: dict[str, Any]) -> dict[str, Any]:
    champion = snapshot.get("active_champion") or {}
    return {
        "data_end_date": snapshot.get("data_end_date"),
        "strategy": champion.get("strategy"),
        "params_hash": champion.get("params_hash"),
        "risk_state": snapshot.get("risk_state"),
        "entry_signal": bool(snapshot.get("entry_signal", False)),
        "exit_signal": bool(snapshot.get("exit_signal", False)),
        "buy_event": bool(snapshot.get("buy_event", False)),
        "sell_event": bool(snapshot.get("sell_event", False)),
        "close": snapshot.get("close"),
    }


def previous_signal_path(target_date: str, signals_dir: Path = SIGNALS_DIR) -> Path | None:
    if not signals_dir.exists():
        return None
    candidates = [
        path
        for path in signals_dir.glob("*.json")
        if path.stem < target_date
    ]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def detect_signal_change(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    if not previous:
        return {"changed": False, "reason": "no_previous_snapshot"}
    changed_fields = []
    for key in ("risk_state", "buy_event", "sell_event", "entry_signal", "exit_signal"):
        if current.get(key) != previous.get(key):
            changed_fields.append(key)
    return {
        "changed": bool(changed_fields),
        "reason": "field_change" if changed_fields else "unchanged",
        "changed_fields": changed_fields,
        "previous_data_end_date": previous.get("data_end_date"),
        "previous_risk_state": previous.get("risk_state"),
    }


def write_signal_snapshot(
    snapshot: dict[str, Any],
    *,
    signals_dir: Path = SIGNALS_DIR,
    allow_overwrite: bool = False,
) -> tuple[Path, str, dict[str, Any]]:
    target_date = str(snapshot["data_end_date"])
    path = signals_dir / f"{target_date}.json"
    existed = path.exists()
    if path.exists() and not allow_overwrite:
        existing = _load_json(path)
        if comparable_signal(existing) == comparable_signal(snapshot):
            return path, "unchanged", existing
        return path, "existing_differs", existing
    _write_json(path, snapshot)
    return path, "overwritten" if existed and allow_overwrite else "written", snapshot


def run_viz_build() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "viz" / "build_viz.py")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def run_daily(
    *,
    skip_refresh: bool = False,
    skip_viz: bool = False,
    skip_followups: bool = False,
    allow_overwrite: bool = False,
    full_audit: bool = False,
) -> dict[str, Any]:
    ensure_ops_dirs()
    generated_utc = utc_now_iso()
    status = "ok"
    events: list[dict[str, Any]] = []
    steps: dict[str, Any] = {}

    if skip_refresh:
        steps["refresh"] = {"status": "skipped"}
    else:
        from data.loader import refresh_all

        refresh_all()
        steps["refresh"] = {"status": "ok"}

    from data.manifest import write_manifest
    from data.quality import audit_all, summarize

    manifest = write_manifest()
    steps["manifest"] = {
        "status": "ok",
        "built_utc": (manifest.get("_meta") or {}).get("built_utc"),
    }

    quality_results = audit_all(include_crosscheck=full_audit)
    quality_summary = summarize(quality_results)
    steps["data_quality"] = {
        "status": "fail" if quality_summary.get("fail", 0) else "ok",
        "summary": quality_summary,
        "failing_checks": [
            r for r in quality_results if r.get("status") == "FAIL"
        ][:20],
    }
    if quality_summary.get("fail", 0):
        status = "attention"
        events.append(append_event(
            "data_quality_failed",
            "Data quality checks reported failures.",
            severity="error",
            payload=steps["data_quality"],
        ))

    champion = load_active_champion()
    snapshot = compute_current_signal(champion)

    prior_path = previous_signal_path(snapshot["data_end_date"])
    previous = _load_json(prior_path) if prior_path else None
    change = detect_signal_change(snapshot, previous)
    snapshot["signal_changed"] = change["changed"]
    snapshot["signal_change"] = change
    snapshot["data_quality"] = quality_summary

    snapshot_path, write_status, stored_snapshot = write_signal_snapshot(
        snapshot,
        allow_overwrite=allow_overwrite,
    )
    steps["signal_snapshot"] = {
        "status": write_status,
        "path": str(snapshot_path),
    }
    if write_status == "existing_differs":
        status = "attention"
        events.append(append_event(
            "signal_snapshot_conflict",
            f"Signal snapshot already exists for {snapshot['data_end_date']} and differs.",
            severity="warning",
            payload={
                "path": str(snapshot_path),
                "computed": comparable_signal(snapshot),
                "existing": comparable_signal(stored_snapshot),
            },
        ))
    if change["changed"]:
        events.append(append_event(
            "signal_changed",
            f"Montauk signal changed to {snapshot['risk_state']}.",
            severity="notice",
            payload={
                "path": str(snapshot_path),
                "change": change,
                "signal": comparable_signal(snapshot),
            },
        ))

    if skip_viz:
        steps["viz"] = {"status": "skipped"}
    else:
        viz = run_viz_build()
        steps["viz"] = {"status": "ok" if viz["ok"] else "fail", **viz}
        if not viz["ok"]:
            status = "attention"
            events.append(append_event(
                "viz_build_failed",
                "Visualization rebuild failed.",
                severity="warning",
                payload=viz,
            ))

    latest = {
        "schema_version": 1,
        "generated_utc": generated_utc,
        "status": status,
        "version_info": version_info(),
        "active_signal": stored_snapshot if write_status == "existing_differs" else snapshot,
        "computed_signal": snapshot,
        "steps": steps,
        "events": events,
    }
    _write_json(LATEST_PATH, latest)

    if skip_followups:
        steps["followups"] = {"status": "skipped"}
    else:
        followups: dict[str, Any] = {}
        try:
            from ops.live_holdout import build_live_holdout

            live = build_live_holdout()
            followups["live_holdout"] = {
                "status": live.get("status"),
                "snapshot_count": live.get("snapshot_count"),
                "diverged_count": live.get("diverged_count"),
            }
            if live.get("status") != "ok":
                status = "attention"
        except Exception as exc:  # noqa: BLE001
            status = "attention"
            followups["live_holdout"] = {"status": "fail", "error": str(exc)}

        try:
            from ops.governance import build_governance

            governance = build_governance()
            followups["governance"] = {
                "status": governance.get("state"),
                "reasons": governance.get("reasons"),
            }
            if governance.get("state") == "active_blocked":
                status = "attention"
        except Exception as exc:  # noqa: BLE001
            status = "attention"
            followups["governance"] = {"status": "fail", "error": str(exc)}

        try:
            from ops.strategy_review import build_strategy_review

            strategy_review = build_strategy_review()
            followups["strategy_review"] = {
                "status": strategy_review.get("status"),
                "best_certified": strategy_review.get("best_certified"),
                "active": strategy_review.get("active"),
            }
            if strategy_review.get("status") == "switch_candidate":
                status = "attention"
        except Exception as exc:  # noqa: BLE001
            status = "attention"
            followups["strategy_review"] = {"status": "fail", "error": str(exc)}

        try:
            from ops.notifications import scan_notifications

            notifications = scan_notifications()
            followups["notifications"] = {
                "status": "ok",
                "pending_count": notifications.get("pending_count"),
            }
        except Exception as exc:  # noqa: BLE001
            status = "attention"
            followups["notifications"] = {"status": "fail", "error": str(exc)}
        steps["followups"] = {"status": "ok", **followups}
        latest["status"] = status
        latest["steps"] = steps
        _write_json(LATEST_PATH, latest)
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Montauk daily operations.")
    parser.add_argument("--skip-refresh", action="store_true", help="Do not fetch new data.")
    parser.add_argument("--skip-viz", action="store_true", help="Do not rebuild viz HTML.")
    parser.add_argument("--skip-followups", action="store_true", help="Do not build live/governance/notification artifacts.")
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing signal snapshot.")
    parser.add_argument("--full-audit", action="store_true", help="Include external data crosschecks.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    args = parser.parse_args(argv)

    result = run_daily(
        skip_refresh=args.skip_refresh,
        skip_viz=args.skip_viz,
        skip_followups=args.skip_followups,
        allow_overwrite=args.allow_overwrite,
        full_audit=args.full_audit,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        signal = result.get("active_signal") or {}
        print(f"Montauk daily status: {result.get('status')}")
        print(
            "Signal: "
            f"{signal.get('risk_state')} through {signal.get('data_end_date')}"
        )
        for name, step in (result.get("steps") or {}).items():
            print(f"- {name}: {step.get('status')}")
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
