#!/usr/bin/env python3
"""
Montauk Continuous Optimization — CLI runner.

This is the script that Claude Code calls during the optimization skill loop.
It handles:
  1. Running baseline backtest
  2. Testing a specific parameter configuration
  3. Running walk-forward validation
  4. Parameter sweep across a single dimension
  5. Full report generation

Usage (called by Claude Code, not typically by humans):
  python3 scripts/run_optimization.py baseline
  python3 scripts/run_optimization.py test --params '{"short_ema_len": 12}'
  python3 scripts/run_optimization.py validate --params '{"short_ema_len": 12}'
  python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 30 --step 5
  python3 scripts/run_optimization.py compare --file results.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import get_tecl_data
from backtest_engine import StrategyParams, run_backtest, BacktestResult
from validation import validate_candidate, split_named_windows

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "remote")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def result_to_dict(r: BacktestResult) -> dict:
    """Convert BacktestResult to JSON-serializable dict."""
    return {
        "total_return_pct": round(r.total_return_pct, 2),
        "cagr_pct": round(r.cagr_pct, 2),
        "max_drawdown_pct": round(r.max_drawdown_pct, 2),
        "mar_ratio": round(r.mar_ratio, 3),
        "exposure_pct": round(r.exposure_pct, 1),
        "num_trades": r.num_trades,
        "trades_per_year": round(r.trades_per_year, 1),
        "avg_bars_held": round(r.avg_bars_held, 1),
        "win_rate_pct": round(r.win_rate_pct, 1),
        "worst_10_bar_loss_pct": round(r.worst_10_bar_loss_pct, 1),
        "exit_reasons": r.exit_reasons,
    }


def cmd_baseline(df: pd.DataFrame, args):
    """Run baseline backtest with default 8.2 params."""
    params = StrategyParams()
    print("Running baseline backtest (Montauk 8.2 defaults)...")
    result = run_backtest(df, params)
    print("\n=== BASELINE RESULTS ===")
    print(result.summary_str())

    # Also run named windows
    print("\n=== PER-WINDOW BREAKDOWN ===")
    for name, window_df in split_named_windows(df):
        r = run_backtest(window_df, params)
        print(f"\n  {name}:")
        print(f"    CAGR: {r.cagr_pct:.1f}%  MaxDD: {r.max_drawdown_pct:.1f}%  "
              f"MAR: {r.mar_ratio:.2f}  Trades: {r.num_trades}")

    # Trade log
    print("\n=== TRADE LOG ===")
    for t in result.trades:
        print(f"  {t.entry_date} -> {t.exit_date}  "
              f"${t.entry_price:.2f}->${t.exit_price:.2f}  "
              f"{t.pnl_pct:+.1f}%  {t.exit_reason} ({t.bars_held}d)")

    return result


def cmd_test(df: pd.DataFrame, args):
    """Test a specific parameter configuration."""
    overrides = json.loads(args.params)
    params = StrategyParams()
    base_dict = params.to_dict()
    base_dict.update(overrides)
    candidate = StrategyParams.from_dict(base_dict)

    print(f"Testing params: {overrides}")
    baseline_result = run_backtest(df, StrategyParams())
    candidate_result = run_backtest(df, candidate)

    print("\n=== COMPARISON ===")
    print(f"{'Metric':<20} {'Baseline':>12} {'Candidate':>12} {'Delta':>12}")
    print("-" * 58)

    comparisons = [
        ("CAGR %", baseline_result.cagr_pct, candidate_result.cagr_pct),
        ("Max DD %", baseline_result.max_drawdown_pct, candidate_result.max_drawdown_pct),
        ("MAR Ratio", baseline_result.mar_ratio, candidate_result.mar_ratio),
        ("Exposure %", baseline_result.exposure_pct, candidate_result.exposure_pct),
        ("Trades", baseline_result.num_trades, candidate_result.num_trades),
        ("Trades/Year", baseline_result.trades_per_year, candidate_result.trades_per_year),
        ("Avg Bars Held", baseline_result.avg_bars_held, candidate_result.avg_bars_held),
        ("Win Rate %", baseline_result.win_rate_pct, candidate_result.win_rate_pct),
        ("Worst 10-Bar %", baseline_result.worst_10_bar_loss_pct, candidate_result.worst_10_bar_loss_pct),
    ]

    for name, base, cand in comparisons:
        delta = cand - base
        indicator = "+" if delta > 0 else ""
        print(f"{name:<20} {base:>12.2f} {cand:>12.2f} {indicator}{delta:>11.2f}")

    print(f"\nCandidate exit reasons: {candidate_result.exit_reasons}")

    return candidate_result


def cmd_validate(df: pd.DataFrame, args):
    """Full walk-forward validation of a candidate."""
    overrides = json.loads(args.params)
    params = StrategyParams()
    base_dict = params.to_dict()
    base_dict.update(overrides)
    candidate = StrategyParams.from_dict(base_dict)

    print(f"Validating: {overrides}")
    print("Running walk-forward + named windows + stability check...")
    print("(This takes a minute — running many backtests)\n")

    v = validate_candidate(df, candidate, check_stability=args.stability)
    print(v.summary_str())

    # Per-window detail
    print("\n=== PER-WINDOW DETAIL ===")
    for w in v.window_results:
        name = w["window"]
        b_mar = w.get("baseline_test_mar", 0)
        c_mar = w.get("candidate_test_mar", 0)
        c_cagr = w.get("candidate_test_cagr", 0)
        c_dd = w.get("candidate_test_dd", 0)
        trades = w.get("candidate_test_trades", "?")
        delta = c_mar - b_mar
        print(f"  {name:<20} MAR: {c_mar:.2f} (base {b_mar:.2f}, delta {delta:+.2f})  "
              f"CAGR: {c_cagr:.1f}%  DD: {c_dd:.1f}%  Trades: {trades}")

    return v


def cmd_sweep(df: pd.DataFrame, args):
    """Sweep a single parameter and report results."""
    param_name = args.param
    values = np.arange(args.min_val, args.max_val + args.step, args.step)

    if param_name.endswith("_len") or param_name.endswith("_bars"):
        values = values.astype(int)

    baseline = run_backtest(df, StrategyParams())
    print(f"Sweeping {param_name}: {list(values)}")
    print(f"Baseline MAR: {baseline.mar_ratio:.3f}\n")

    print(f"{'Value':>10} {'CAGR%':>8} {'MaxDD%':>8} {'MAR':>8} {'Trades':>7} {'Exposure%':>10}")
    print("-" * 55)

    best_mar = -999
    best_val = None
    results = []

    for v in values:
        override = {param_name: int(v) if isinstance(v, (np.integer, int)) else float(v)}
        base_dict = StrategyParams().to_dict()
        base_dict.update(override)
        params = StrategyParams.from_dict(base_dict)
        r = run_backtest(df, params)

        marker = " ***" if r.mar_ratio > best_mar else ""
        print(f"{v:>10} {r.cagr_pct:>8.1f} {r.max_drawdown_pct:>8.1f} "
              f"{r.mar_ratio:>8.3f} {r.num_trades:>7} {r.exposure_pct:>10.1f}{marker}")

        if r.mar_ratio > best_mar:
            best_mar = r.mar_ratio
            best_val = v

        results.append({"value": float(v), **result_to_dict(r)})

    print(f"\nBest: {param_name}={best_val} (MAR={best_mar:.3f}, baseline={baseline.mar_ratio:.3f})")
    return results


def cmd_multi_sweep(df: pd.DataFrame, args):
    """Sweep multiple parameters defined in a JSON spec."""
    spec = json.loads(args.spec)
    # spec format: {"param_name": [val1, val2, ...], ...}

    baseline = run_backtest(df, StrategyParams())
    print(f"Baseline MAR: {baseline.mar_ratio:.3f}")

    all_results = []
    for param_name, values in spec.items():
        print(f"\n--- Sweeping {param_name} ---")
        for v in values:
            override = {param_name: v}
            base_dict = StrategyParams().to_dict()
            base_dict.update(override)
            params = StrategyParams.from_dict(base_dict)
            r = run_backtest(df, params)
            print(f"  {param_name}={v}: MAR={r.mar_ratio:.3f} CAGR={r.cagr_pct:.1f}% DD={r.max_drawdown_pct:.1f}%")
            all_results.append({
                "param": param_name,
                "value": v,
                **result_to_dict(r)
            })

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Montauk Backtest Runner")
    sub = parser.add_subparsers(dest="command")

    # baseline
    sub.add_parser("baseline", help="Run baseline 8.2 backtest")

    # test
    p_test = sub.add_parser("test", help="Test specific params")
    p_test.add_argument("--params", required=True, help="JSON param overrides")

    # validate
    p_val = sub.add_parser("validate", help="Full walk-forward validation")
    p_val.add_argument("--params", required=True, help="JSON param overrides")
    p_val.add_argument("--stability", action="store_true", help="Run stability check (slow)")

    # sweep
    p_sweep = sub.add_parser("sweep", help="Sweep a single param")
    p_sweep.add_argument("--param", required=True)
    p_sweep.add_argument("--min", dest="min_val", type=float, required=True)
    p_sweep.add_argument("--max", dest="max_val", type=float, required=True)
    p_sweep.add_argument("--step", type=float, required=True)

    # multi-sweep
    p_multi = sub.add_parser("multi-sweep", help="Sweep multiple params")
    p_multi.add_argument("--spec", required=True, help='JSON: {"param": [vals]}')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load data
    print("Loading TECL data...")
    df = get_tecl_data(use_yfinance=False)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    commands = {
        "baseline": cmd_baseline,
        "test": cmd_test,
        "validate": cmd_validate,
        "sweep": cmd_sweep,
        "multi-sweep": cmd_multi_sweep,
    }

    start = time.time()
    result = commands[args.command](df, args)
    elapsed = time.time() - start
    print(f"\n[Done in {elapsed:.1f}s]")


if __name__ == "__main__":
    main()
