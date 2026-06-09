from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import (
    LATEST_PATH,
    LEADERBOARD_PATH,
    OPERATIONS_DIR,
    PROJECT_ROOT,
    SIGNALS_DIR,
    ensure_ops_dirs,
)
from ops.versioning import version_info

# Once-per-day refresh marker. The data pull hits the network for every ticker,
# so we only do it once per local calendar day and record the outcome here.
REFRESH_MARKER_PATH = OPERATIONS_DIR / "last_refresh.json"


def _local_today() -> str:
    """Local calendar date (YYYY-MM-DD) used to gate the once-per-day refresh."""
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def _read_refresh_marker() -> dict[str, Any] | None:
    if not REFRESH_MARKER_PATH.exists():
        return None
    try:
        return _load_json(REFRESH_MARKER_PATH)
    except (json.JSONDecodeError, OSError):
        return None


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
        # Active champion = Montauk Score leader (the leaderboard's #1 ranking).
        return max(
            gold,
            key=lambda entry: float(entry.get("montauk_score") or 0.0),
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


def compute_flip_likelihood(
    df,
    strategy_fn,
    params: dict[str, Any],
    *,
    cooldown_bars: int,
    current_risk_on: bool,
    horizon: int = 21,
    paths: int = 150,
    lookback: int = 120,
    tail: int = 1000,
    seed: int = 12345,
) -> dict[str, Any]:
    """Monte-Carlo "how likely is the position to flip soon" — always shows a value.

    Strategy-agnostic and symmetric:
      - currently In  → probability of an EXIT within ``horizon`` trading days
      - currently Out → probability of a RE-ENTER within ``horizon`` trading days

    Simulates ``paths`` near-term TECL price continuations by bootstrapping
    recent daily returns, appends each to the real history, re-runs the
    champion's real entry/exit logic, and measures the fraction of paths whose
    position flips. Because bootstrapped paths contain realistic sequences
    (pullbacks, recoveries, trends), even pattern-gated re-entries register — so
    this never reads a meaningless 0 the way a single price-level test can.

    Returns:
        flip_likelihood  – 0..1 probability of a flip within the horizon.
        flip_days        – median trading days to the flip among flipping paths, or None.
        flip_move_pct    – median TECL move (%) at the flip among flipping paths, or None.
        flip_horizon     – the horizon (trading days) used.
        flip_direction   – "to_exit" (In) or "to_entry" (Out).
    """
    import numpy as np
    import pandas as pd

    from engine.strategy_engine import Indicators

    direction = "to_exit" if current_risk_on else "to_entry"
    real = df.iloc[-tail:].reset_index(drop=True) if len(df) > tail else df.copy()
    n = len(real)
    close = real["close"].to_numpy(dtype=float)
    if n < 60:
        return {"flip_likelihood": None, "flip_days": None, "flip_move_pct": None,
                "flip_horizon": horizon, "flip_direction": direction}

    window = close[-(lookback + 1):]
    rets = np.diff(window) / window[:-1]
    rets = rets[np.isfinite(rets)]
    if len(rets) < 10:
        return {"flip_likelihood": None, "flip_days": None, "flip_move_pct": None,
                "flip_horizon": horizon, "flip_direction": direction}

    hi = real["high"].to_numpy(dtype=float)[-lookback:]
    lo = real["low"].to_numpy(dtype=float)[-lookback:]
    cl = close[-lookback:]
    with np.errstate(invalid="ignore", divide="ignore"):
        rng_ratio = float(np.nanmean((hi - lo) / cl))
    if not np.isfinite(rng_ratio) or rng_ratio <= 0:
        rng_ratio = 0.03

    # Carry-forward numeric context (vix, macro, etc.); avg recent volume.
    skip = {"date", "open", "high", "low", "close", "volume"}
    carry = {
        c: float(real[c].iloc[-1])
        for c in real.columns
        if c not in skip
        and pd.api.types.is_numeric_dtype(real[c])
        and np.isfinite(real[c].iloc[-1])
    }
    vol_mean = float(np.nanmean(real["volume"].to_numpy(dtype=float)[-lookback:])) if "volume" in real.columns else 1.0
    last_close = float(close[-1])
    last_date = pd.Timestamp(real["date"].iloc[-1])
    future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=horizon)

    rng = np.random.default_rng(seed)
    flips = 0
    days_list: list[int] = []
    move_list: list[float] = []

    for _ in range(paths):
        sampled = rng.choice(rets, size=horizon, replace=True)
        fclose = last_close * np.cumprod(1.0 + sampled)
        fopen = np.empty(horizon)
        fopen[0] = last_close
        fopen[1:] = fclose[:-1]
        fhigh = np.maximum(fopen, fclose) * (1.0 + rng_ratio / 2.0)
        flow = np.minimum(fopen, fclose) * (1.0 - rng_ratio / 2.0)
        fut = {
            "date": future_dates.values,
            "open": fopen, "high": fhigh, "low": flow, "close": fclose,
            "volume": np.full(horizon, vol_mean),
        }
        for c, v in carry.items():
            fut[c] = np.full(horizon, v)
        aug = pd.concat([real, pd.DataFrame(fut)], ignore_index=True)
        entries, exits, _ = strategy_fn(Indicators(aug), params)
        risk_on, _, _ = simulate_signal_state(
            [bool(v) for v in entries],
            [bool(v) for v in exits],
            cooldown_bars=cooldown_bars,
        )
        cur = bool(risk_on[n - 1])
        for i in range(n, n + horizon):
            if bool(risk_on[i]) != cur:
                flips += 1
                days_list.append(i - (n - 1))
                move_list.append((fclose[i - n] / last_close - 1.0) * 100.0)
                break

    likelihood = flips / paths
    return {
        "flip_likelihood": round(likelihood, 4),
        "flip_days": int(np.median(days_list)) if days_list else None,
        "flip_move_pct": round(float(np.median(move_list)), 2) if move_list else None,
        "flip_horizon": horizon,
        "flip_direction": direction,
    }


def compute_top_strategies(n: int = 5, *, df=None) -> list[dict[str, Any]]:
    """Top-N Gold strategies by Montauk Score, each with live position + mini flip.

    Used by the dashboard's bottom strategy bar. Ranked by the Montauk Score
    (same ordering as the active-champion selector), so rank 1 == active.
    """
    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators
    from strategies.library import STRATEGY_REGISTRY

    leaderboard = _load_json(LEADERBOARD_PATH)
    if not isinstance(leaderboard, list) or not leaderboard:
        return []

    def _conf(entry: dict[str, Any]) -> float:
        return float((entry.get("validation") or {}).get("composite_confidence") or 0.0)

    def _montauk(entry: dict[str, Any]) -> float:
        return float(entry.get("montauk_score") or 0.0)

    gold = [
        e for e in leaderboard
        if e.get("gold_status") is True or (e.get("validation") or {}).get("gold_status") is True
    ]
    pool = sorted(gold or leaderboard, key=_montauk, reverse=True)[:n]

    if df is None:
        df = get_tecl_data(use_yfinance=False)

    rows: list[dict[str, Any]] = []
    for rank, entry in enumerate(pool, start=1):
        name = entry.get("strategy")
        params = entry.get("params") or {}
        fn = STRATEGY_REGISTRY.get(name)
        if fn is None:
            continue
        cur: bool | None = None
        flip: dict[str, Any] = {}
        try:
            entries, exits, _ = fn(Indicators(df), params)
            risk_on, _, _ = simulate_signal_state(
                [bool(v) for v in entries],
                [bool(v) for v in exits],
                cooldown_bars=int(params.get("cooldown", 0) or 0),
            )
            cur = bool(risk_on[-1])
            # Lower-fidelity MC for the mini indicator (kept fast across N strategies).
            flip = compute_flip_likelihood(
                df, fn, params,
                cooldown_bars=int(params.get("cooldown", 0) or 0),
                current_risk_on=cur, paths=60, tail=800,
            )
        except Exception:  # noqa: BLE001
            pass
        rows.append({
            "rank": rank,
            "active": rank == 1,
            "display_name": entry.get("display_name") or name,
            "strategy": name,
            "position": "in" if cur else ("out" if cur is not None else "unknown"),
            "risk_state": ("risk_on" if cur else "risk_off") if cur is not None else None,
            "flip_likelihood": flip.get("flip_likelihood"),
            "flip_direction": flip.get("flip_direction"),
            "montauk_score": _montauk(entry),
            "composite_confidence": _conf(entry),
        })
    return rows


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

    # Price-driven flip likelihood (best-effort; never break the signal).
    flip = {
        "flip_likelihood": None, "flip_days": None, "flip_move_pct": None,
        "flip_horizon": None, "flip_direction": None,
    }
    try:
        flip = compute_flip_likelihood(
            df,
            strategy_fn,
            params,
            cooldown_bars=int(params.get("cooldown", 0) or 0),
            current_risk_on=bool(risk_on[idx]),
        )
    except Exception:  # noqa: BLE001
        pass

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
        "flip_likelihood": flip.get("flip_likelihood"),
        "flip_days": flip.get("flip_days"),
        "flip_move_pct": flip.get("flip_move_pct"),
        "flip_horizon": flip.get("flip_horizon"),
        "flip_direction": flip.get("flip_direction"),
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
    force_refresh: bool = False,
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

    # Refresh gating: the data pull is network-heavy, so run it at most once per
    # local calendar day. `last_refresh.json` is the persistent log of when we
    # last pulled and whether anything actually changed; it lets us skip the
    # step on repeat launches the same day.
    today = _local_today()
    marker = _read_refresh_marker()
    already_today = bool(marker) and marker.get("date") == today

    if skip_refresh:
        steps["refresh"] = {"status": "skipped", "reason": "skip_refresh_flag"}
    elif already_today and not force_refresh:
        steps["refresh"] = {
            "status": "skipped",
            "reason": "already_refreshed_today",
            "last_refresh": {
                "date": marker.get("date"),
                "refreshed_utc": marker.get("refreshed_utc"),
                "updated": marker.get("updated"),
                "total_new_bars": marker.get("total_new_bars"),
                "data_end_date": marker.get("data_end_date"),
            },
        }
        events.append(append_event(
            "data_refresh_skipped",
            f"Data already refreshed today ({today}); skipping the network pull.",
            severity="info",
            payload=steps["refresh"]["last_refresh"],
        ))
    else:
        from data.loader import refresh_all

        summary = refresh_all() or {}
        refreshed_utc = utc_now_iso()
        steps["refresh"] = {
            "status": "ok" if summary.get("status", "ok") == "ok" else "fail",
            "updated": bool(summary.get("updated", False)),
            "total_new_bars": int(summary.get("total_new_bars", 0) or 0),
            "new_bars": summary.get("new_bars", {}),
            "data_end_date": summary.get("data_end_date"),
            "refreshed_utc": refreshed_utc,
            "forced": bool(force_refresh and already_today),
        }
        # Persist the marker (the once-per-day log) only on a successful pull.
        if summary.get("status", "ok") == "ok":
            _write_json(REFRESH_MARKER_PATH, {
                "schema_version": 1,
                "date": today,
                "refreshed_utc": refreshed_utc,
                "updated": bool(summary.get("updated", False)),
                "total_new_bars": int(summary.get("total_new_bars", 0) or 0),
                "new_bars": summary.get("new_bars", {}),
                "data_end_date": summary.get("data_end_date"),
            })
        events.append(append_event(
            "data_refreshed",
            (
                f"Data refresh added {steps['refresh']['total_new_bars']} new bars."
                if steps["refresh"]["updated"]
                else "Data refresh ran; no new bars (already current)."
            ),
            severity="info",
            payload={
                "updated": steps["refresh"]["updated"],
                "total_new_bars": steps["refresh"]["total_new_bars"],
                "new_bars": steps["refresh"]["new_bars"],
                "data_end_date": steps["refresh"]["data_end_date"],
            },
        ))

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

    # Top-5 strategy bar (best-effort; never break the daily run).
    try:
        top = compute_top_strategies(5)
        _write_json(OPERATIONS_DIR / "top_strategies.json", {
            "schema_version": 1,
            "generated_utc": generated_utc,
            "data_end_date": snapshot["data_end_date"],
            "strategies": top,
        })
        steps["top_strategies"] = {"status": "ok", "count": len(top)}
    except Exception as exc:  # noqa: BLE001
        steps["top_strategies"] = {"status": "fail", "error": str(exc)}

    if skip_viz:
        steps["viz"] = {"status": "skipped"}
    else:
        try:
            from certify.backfill_artifacts import backfill_leaderboard_dashboard_artifacts

            created, skipped = backfill_leaderboard_dashboard_artifacts(
                top_n=20,
                refresh_stale=True,
            )
            steps["artifact_backfill"] = {
                "status": "ok",
                "created_or_refreshed": created,
                "skipped": skipped,
            }
        except Exception as exc:  # noqa: BLE001
            status = "attention"
            steps["artifact_backfill"] = {"status": "fail", "error": str(exc)}
            events.append(append_event(
                "viz_build_failed",
                "Strategy artifact refresh failed before visualization rebuild.",
                severity="warning",
                payload=steps["artifact_backfill"],
            ))

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
    parser.add_argument("--force-refresh", action="store_true",
                        help="Refresh data even if it already ran today (overrides once-per-day gate).")
    parser.add_argument("--skip-viz", action="store_true", help="Do not rebuild viz HTML.")
    parser.add_argument("--skip-followups", action="store_true", help="Do not build live/governance/notification artifacts.")
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing signal snapshot.")
    parser.add_argument("--full-audit", action="store_true", help="Include external data crosschecks.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    args = parser.parse_args(argv)

    result = run_daily(
        skip_refresh=args.skip_refresh,
        force_refresh=args.force_refresh,
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
