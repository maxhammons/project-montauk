#!/usr/bin/env python3
"""Build Confidence v2 vintage calibration artifacts.

This is diagnostic-only.  It does not promote, demote, or rewrite the
authority leaderboard.  It evaluates the current Gold strategy configs as if
they existed at historical vintage dates, then measures fixed forward outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from search.fitness import weighted_era_fitness
from strategies.library import STRATEGY_REGISTRY
from validation.confidence_v2 import (
    CALIBRATION_MODEL_PATH,
    LEADERBOARD_SCORES_PATH,
    LIVE_HOLDOUT_LOG_PATH,
    VINTAGE_TRIALS_PATH,
    append_timeseries,
    build_leaderboard_scores,
    clamp,
    load_gold_rows,
    safe_float,
    strategy_key,
    write_leaderboard_scores,
)

DEFAULT_CANDIDATE_ARCHIVE = os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "candidate_archive.json")
DEFAULT_VINTAGES = (
    "2014-01-01",
    "2016-01-01",
    "2018-01-01",
    "2020-01-01",
    "2022-01-01",
    "2024-01-01",
)


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def load_candidate_rows(path: str = DEFAULT_CANDIDATE_ARCHIVE, *, limit: int | None = 120) -> list[dict[str, Any]]:
    archive = _load_json(path, {})
    rows = archive.get("candidates") if isinstance(archive, dict) else None
    if not isinstance(rows, list) or not rows:
        return load_gold_rows()
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        strategy = row.get("strategy")
        params = row.get("params")
        if strategy not in STRATEGY_REGISTRY or not isinstance(params, dict):
            continue
        key = strategy_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if limit and len(out) >= limit:
            break
    return out


def _slice_through(df: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    return df[df["date"] <= end].reset_index(drop=True)


def _run_strategy(df: pd.DataFrame, strategy: str, params: dict[str, Any]):
    fn = STRATEGY_REGISTRY.get(strategy)
    if fn is None:
        raise KeyError(f"unknown strategy: {strategy}")
    ind = Indicators(df)
    entries, exits, labels = fn(ind, params)
    return backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0) or 0),
        strategy_name=strategy,
    )


def _window_metrics(
    df: pd.DataFrame,
    result,
    *,
    start: pd.Timestamp,
    months: int,
) -> dict[str, Any] | None:
    end = start + pd.DateOffset(months=months)
    dates = pd.to_datetime(df["date"])
    mask = (dates >= start) & (dates <= end)
    if mask.sum() < 40:
        return None
    idx = np.flatnonzero(mask.to_numpy())
    i0 = int(idx[0])
    i1 = int(idx[-1])
    eq = result.equity_curve.astype(float)
    close = df["close"].to_numpy(dtype=float)
    if eq[i0] <= 0 or close[i0] <= 0 or close[i1] <= 0:
        return None
    strat_growth = eq[i1] / eq[i0]
    bah_growth = close[i1] / close[i0]
    share_multiple = strat_growth / bah_growth if bah_growth > 0 else 0.0

    peak = np.maximum.accumulate(eq[i0 : i1 + 1])
    dd = np.where(peak > 0, (eq[i0 : i1 + 1] - peak) / peak * 100.0, 0.0)
    max_dd = abs(float(dd.min())) if len(dd) else 0.0
    start_iso = start.date().isoformat()
    end_iso = pd.Timestamp(dates.iloc[i1]).date().isoformat()
    trades = [
        t for t in result.trades
        if start_iso <= str(t.entry_date)[:10] <= end_iso
    ]
    return {
        "start": start_iso,
        "end": end_iso,
        "months": months,
        "share_multiple": round(float(share_multiple), 4),
        "beats_bh": bool(share_multiple >= 1.0),
        "max_dd": round(max_dd, 1),
        "trades": len(trades),
    }


def _prediction_score(train_metrics: dict[str, Any]) -> float:
    full = safe_float(train_metrics.get("share_multiple"))
    real = safe_float(train_metrics.get("real_share_multiple"), full)
    modern = safe_float(train_metrics.get("modern_share_multiple"), real)
    fitness = weighted_era_fitness(full, real, modern)
    fit_score = 0.15 + 0.85 * clamp((fitness - 0.75) / 2.25)
    dd_score = 0.05 + 0.95 * (1.0 - clamp((safe_float(train_metrics.get("max_dd"), 100.0) - 55.0) / 40.0))
    trade_count = safe_float(train_metrics.get("trades"))
    trade_score = 0.20 + 0.80 * clamp(trade_count / 20.0)
    return round(float((fit_score ** 0.50) * (dd_score ** 0.30) * (trade_score ** 0.20)), 4)


def build_trials(
    *,
    vintages: tuple[str, ...],
    horizons: tuple[int, ...],
    max_rows: int | None = None,
    candidate_archive: str = DEFAULT_CANDIDATE_ARCHIVE,
) -> dict[str, Any]:
    df = get_tecl_data(use_yfinance=False)
    df["date"] = pd.to_datetime(df["date"])
    rows = load_candidate_rows(candidate_archive, limit=max_rows)
    if max_rows is not None:
        rows = rows[:max_rows]
    trials = []

    for vintage_str in vintages:
        vintage = pd.Timestamp(vintage_str)
        if vintage >= df["date"].max():
            continue
        max_horizon_end = vintage + pd.DateOffset(months=max(horizons))
        eval_df = _slice_through(df, min(max_horizon_end, df["date"].max()))
        train_df = df[df["date"] < vintage].reset_index(drop=True)
        if len(train_df) < 750 or len(eval_df) <= len(train_df):
            continue
        for row in rows:
            strategy = row.get("strategy")
            params = row.get("params") or {}
            if strategy not in STRATEGY_REGISTRY:
                continue
            try:
                train_result = _run_strategy(train_df, strategy, params)
                eval_result = _run_strategy(eval_df, strategy, params)
            except Exception as exc:
                trials.append(
                    {
                        "vintage_date": vintage_str,
                        "strategy_key": strategy_key(row),
                        "display_name": row.get("display_name") or strategy,
                        "strategy": strategy,
                        "error": str(exc),
                    }
                )
                continue

            train_metrics = {
                "share_multiple": train_result.share_multiple,
                "real_share_multiple": train_result.real_share_multiple,
                "modern_share_multiple": train_result.modern_share_multiple,
                "max_dd": train_result.max_drawdown_pct,
                "trades": train_result.num_trades,
            }
            forward = {}
            for months in horizons:
                metrics = _window_metrics(eval_df, eval_result, start=vintage, months=months)
                if metrics:
                    label = f"{months // 12}y" if months % 12 == 0 else f"{months}m"
                    forward[label] = metrics

            two_year = forward.get("2y") or forward.get("24m") or {}
            survived = bool(
                two_year
                and two_year.get("beats_bh")
                and safe_float(two_year.get("max_dd"), 100.0) <= 90.0
                and (
                    int(two_year.get("trades") or 0) > 0
                    or safe_float(two_year.get("share_multiple")) >= 1.0
                )
            )
            trials.append(
                {
                    "vintage_date": vintage_str,
                    "strategy_key": strategy_key(row),
                    "display_name": row.get("display_name") or strategy,
                    "strategy": strategy,
                    "leaderboard_rank": row.get("leaderboard_rank"),
                    "prediction_score": _prediction_score(train_metrics),
                    "train_metrics": train_metrics,
                    "forward": forward,
                    "survived_useful_2y": survived,
                }
            )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "method": (
            "Archived and current candidate configs are evaluated at historical "
            "vintage dates. This is simulated vintage evidence, not pristine "
            "historical discovery."
        ),
        "candidate_source": os.path.relpath(candidate_archive, PROJECT_ROOT)
        if os.path.exists(candidate_archive)
        else "current Gold rows fallback",
        "candidate_count": len(rows),
        "vintages": list(vintages),
        "horizons_months": list(horizons),
        "trial_count": len(trials),
        "trials": trials,
    }


def build_calibration_model(trials_report: dict[str, Any]) -> dict[str, Any]:
    trials = [
        t for t in trials_report.get("trials", [])
        if t.get("prediction_score") is not None and "survived_useful_2y" in t
    ]
    valid = [t for t in trials if not t.get("error")]
    if len(valid) < 12:
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "uncalibrated",
            "reason": "fewer than 12 valid vintage trials",
            "trial_count": len(valid),
            "buckets": [],
        }

    ordered = sorted(valid, key=lambda t: safe_float(t.get("prediction_score")))
    n_buckets = min(4, max(2, len(ordered) // 8))
    buckets = []
    for bucket_idx in range(n_buckets):
        lo = int(round(bucket_idx * len(ordered) / n_buckets))
        hi = int(round((bucket_idx + 1) * len(ordered) / n_buckets))
        chunk = ordered[lo:hi]
        if not chunk:
            continue
        scores = [safe_float(t.get("prediction_score")) for t in chunk]
        survival = [1.0 if t.get("survived_useful_2y") else 0.0 for t in chunk]
        buckets.append(
            {
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4),
                "midpoint": round(sum(scores) / len(scores), 4),
                "n": len(chunk),
                "observed_survival_rate": round(sum(survival) / len(survival), 4),
            }
        )

    # The small first-generation vintage sample can be noisy.  Enforce a
    # monotone calibration curve so higher raw scores never map to lower
    # observed survival than weaker raw-score buckets.
    levels = [safe_float(bucket.get("observed_survival_rate")) for bucket in buckets]
    weights = [max(int(bucket.get("n") or 1), 1) for bucket in buckets]
    i = 0
    while i < len(levels) - 1:
        if levels[i] <= levels[i + 1]:
            i += 1
            continue
        total_w = weights[i] + weights[i + 1]
        pooled = (levels[i] * weights[i] + levels[i + 1] * weights[i + 1]) / total_w
        levels[i] = levels[i + 1] = pooled
        weights[i] = weights[i + 1] = total_w
        i = max(i - 1, 0)
    for bucket, level in zip(buckets, levels):
        bucket["observed_survival_rate"] = round(float(level), 4)

    overall = sum(1 for t in valid if t.get("survived_useful_2y")) / len(valid)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "calibrated",
        "model_type": "quantile_bucket_survival_v1",
        "trial_count": len(valid),
        "overall_survival_rate": round(overall, 4),
        "target": "survived_useful_2y",
        "buckets": buckets,
        "limitations": [
            "Uses current Gold configs as historical candidates; it does not reconstruct historical discovery runs yet.",
            "Confidence values are calibration-assisted but still provisional until more vintage candidates are added.",
        ],
    }


def write_json(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def write_live_holdout_log(path: str = LIVE_HOLDOUT_LOG_PATH) -> None:
    if os.path.exists(path):
        return
    write_json(
        path,
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "live_holdout_start": "2026-05-01",
            "diagnostic_only": True,
            "entries": [],
            "note": "True forward evidence starts here because prior data has been seen by Montauk.",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintage", action="append", dest="vintages")
    parser.add_argument("--quick", action="store_true", help="Use fewer vintages and top 4 Gold rows")
    parser.add_argument("--candidate-archive", default=DEFAULT_CANDIDATE_ARCHIVE)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--output", default=VINTAGE_TRIALS_PATH)
    parser.add_argument("--calibration-output", default=CALIBRATION_MODEL_PATH)
    parser.add_argument("--leaderboard-output", default=LEADERBOARD_SCORES_PATH)
    args = parser.parse_args()

    vintages = tuple(args.vintages or DEFAULT_VINTAGES)
    max_rows = args.max_rows
    if args.quick:
        vintages = ("2020-01-01", "2022-01-01", "2024-01-01")
        max_rows = max_rows or 4
    else:
        max_rows = max_rows or 120

    trials = build_trials(
        vintages=vintages,
        horizons=(6, 12, 24),
        max_rows=max_rows,
        candidate_archive=args.candidate_archive,
    )
    calibration = build_calibration_model(trials)
    scores = build_leaderboard_scores(calibration_model=calibration)

    write_json(args.output, trials)
    write_json(args.calibration_output, calibration)
    write_leaderboard_scores(scores, args.leaderboard_output)
    append_timeseries(scores)
    write_live_holdout_log()

    print(
        "[confidence-v2] "
        f"trials={trials['trial_count']} calibration={calibration['status']} "
        f"leaderboard_scores={len(scores.get('scores', []))}"
    )
    print(f"[confidence-v2] wrote {args.output}")
    print(f"[confidence-v2] wrote {args.calibration_output}")
    print(f"[confidence-v2] wrote {args.leaderboard_output}")


if __name__ == "__main__":
    main()
