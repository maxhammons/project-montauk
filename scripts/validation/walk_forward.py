#!/usr/bin/env python3
"""
Walk-forward out-of-sample validation.

Splits data into train/test periods and checks whether optimized
strategies degrade gracefully or collapse out-of-sample.

Usage:
    python3 -m validation.walk_forward
    python3 -m validation.walk_forward --split-date 2020-01-01 --top 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY

PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
LEADERBOARD_FILE = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


def walk_forward_test(
    strategy_name: str,
    params: dict,
    df_full: pd.DataFrame,
    split_date: str = "2020-01-01",
) -> dict:
    """
    Run walk-forward validation on a single strategy+params.

    Returns dict with train/test metrics and pass/fail verdict.
    """
    strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy_fn:
        return {"error": f"Unknown strategy: {strategy_name}"}

    split_dt = pd.Timestamp(split_date)
    df_train = df_full[df_full["date"] < split_dt].reset_index(drop=True)
    df_test = df_full[df_full["date"] >= split_dt].reset_index(drop=True)

    if len(df_train) < 100 or len(df_test) < 100:
        return {"error": "Insufficient data for split"}

    results = {}
    for label, df_slice in [("train", df_train), ("test", df_test)]:
        ind = Indicators(df_slice)
        try:
            entries, exits, labels = strategy_fn(ind, params)
            cooldown = params.get("cooldown", 0)
            result = backtest(df_slice, entries, exits, labels, cooldown_bars=cooldown,
                            strategy_name=strategy_name)
            results[label] = {
                "share_multiple": round(result.share_multiple, 4),
                "cagr": round(result.cagr_pct, 2),
                "max_dd": round(result.max_drawdown_pct, 1),
                "trades": result.num_trades,
                "win_rate": round(result.win_rate_pct, 1),
            }
        except Exception as e:
            results[label] = {"error": str(e)}

    # Compute verdict
    train = results.get("train", {})
    test = results.get("test", {})

    if "error" in train or "error" in test:
        results["verdict"] = "ERROR"
        results["reason"] = train.get("error", "") or test.get("error", "")
        return results

    train_bah = train.get("share_multiple", 0)
    test_bah = test.get("share_multiple", 0)
    test_trades = test.get("trades", 0)

    degradation = test_bah / train_bah if train_bah > 0 else 0
    results["degradation"] = round(degradation, 3)

    # Pass criteria
    passes_bah = test_bah > 0.8
    passes_degradation = degradation > 0.5
    passes_trades = test_trades >= 2

    if passes_bah and passes_degradation and passes_trades:
        results["verdict"] = "PASS"
    elif not passes_trades:
        results["verdict"] = "FAIL"
        results["reason"] = f"Only {test_trades} trades in test period"
    elif not passes_bah:
        results["verdict"] = "FAIL"
        results["reason"] = f"Test share_multiple {test_bah:.3f} < 0.8"
    else:
        results["verdict"] = "WARN"
        results["reason"] = f"Degradation {degradation:.2f} < 0.5 (train={train_bah:.3f} test={test_bah:.3f})"

    return results


def run_walk_forward(split_date: str = "2020-01-01", top_n: int = 20) -> list:
    """Run walk-forward on all leaderboard strategies."""
    if not os.path.exists(LEADERBOARD_FILE):
        print("No leaderboard found")
        return []

    with open(LEADERBOARD_FILE) as f:
        leaderboard = json.load(f)

    df = get_tecl_data(use_yfinance=False)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Split date: {split_date}")
    print(f"Testing top {min(top_n, len(leaderboard))} strategies\n")

    # Header
    print(f"{'Strategy':<25} {'Train B&H':>10} {'Test B&H':>10} {'Degrad':>8} {'Test Trd':>8} {'Verdict':>8}")
    print("-" * 75)

    results = []
    seen = set()  # deduplicate strategy names (leaderboard can have dupes)
    for entry in leaderboard[:top_n]:
        name = entry["strategy"]
        params = entry.get("params", {})

        # Use strategy+params hash for dedup (same strategy, different params = separate test)
        key = f"{name}:{json.dumps(params, sort_keys=True)}"
        if key in seen:
            continue
        seen.add(key)

        result = walk_forward_test(name, params, df, split_date)
        result["strategy"] = name
        result["fitness"] = entry.get("fitness", 0)
        results.append(result)

        train = result.get("train", {})
        test = result.get("test", {})
        verdict = result.get("verdict", "?")
        degrad = result.get("degradation", 0)

        # Color-code verdict
        v_str = verdict
        print(f"{name:<25} {train.get('share_multiple', 0):>10.3f} {test.get('share_multiple', 0):>10.3f} "
              f"{degrad:>8.2f} {test.get('trades', 0):>8} {v_str:>8}")

    # Summary
    n_pass = sum(1 for r in results if r.get("verdict") == "PASS")
    n_warn = sum(1 for r in results if r.get("verdict") == "WARN")
    n_fail = sum(1 for r in results if r.get("verdict") == "FAIL")
    print(f"\nSummary: {n_pass} PASS / {n_warn} WARN / {n_fail} FAIL out of {len(results)}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walk-forward validation")
    parser.add_argument("--split-date", default="2020-01-01", help="Train/test split date")
    parser.add_argument("--top", type=int, default=20, help="Test top N from leaderboard")
    args = parser.parse_args()

    run_walk_forward(split_date=args.split_date, top_n=args.top)
