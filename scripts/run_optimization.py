#!/usr/bin/env python3
"""
Montauk Continuous Optimization — CLI runner.

Every command prints a compact JSON summary on its final line prefixed with
###JSON### so Claude can parse results cheaply without reading tables.

Usage:
  python3 scripts/run_optimization.py baseline
  python3 scripts/run_optimization.py test --params '{"short_ema_len": 12}'
  python3 scripts/run_optimization.py validate --params '{"short_ema_len": 12}'
  python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 30 --step 5
  python3 scripts/run_optimization.py grid --spec '{"short_ema_len": [10,15], "med_ema_len": [25,30]}'
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from itertools import product

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import get_tecl_data
from backtest_engine import StrategyParams, run_backtest, BacktestResult
from validation import validate_candidate, split_named_windows

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def result_to_dict(r: BacktestResult) -> dict:
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


class _NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON output."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def emit_json(obj: dict):
    """Print the machine-readable JSON summary on the final line."""
    print(f"\n###JSON### {json.dumps(obj, cls=_NumpyEncoder)}")


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_baseline(df: pd.DataFrame, args):
    params = StrategyParams()
    result = run_backtest(df, params)
    print("=== BASELINE (Montauk 8.2) ===")
    print(result.summary_str())

    windows = {}
    for name, window_df in split_named_windows(df):
        r = run_backtest(window_df, params)
        windows[name] = result_to_dict(r)
        print(f"  {name}: CAGR={r.cagr_pct:.1f}% DD={r.max_drawdown_pct:.1f}% MAR={r.mar_ratio:.2f} Trades={r.num_trades}")

    trades_log = []
    for t in result.trades:
        trades_log.append({
            "entry": t.entry_date, "exit": t.exit_date,
            "pnl_pct": round(t.pnl_pct, 1), "reason": t.exit_reason,
            "bars": t.bars_held
        })

    emit_json({
        "command": "baseline",
        "metrics": result_to_dict(result),
        "windows": windows,
        "trades": trades_log,
    })


def cmd_test(df: pd.DataFrame, args):
    overrides = json.loads(args.params)
    base_dict = StrategyParams().to_dict()
    base_dict.update(overrides)
    candidate = StrategyParams.from_dict(base_dict)

    baseline_result = run_backtest(df, StrategyParams())
    candidate_result = run_backtest(df, candidate)

    b = result_to_dict(baseline_result)
    c = result_to_dict(candidate_result)

    print(f"Testing: {overrides}")
    print(f"  Baseline MAR={b['mar_ratio']}  Candidate MAR={c['mar_ratio']}")
    print(f"  Baseline CAGR={b['cagr_pct']}%  Candidate CAGR={c['cagr_pct']}%")
    print(f"  Baseline DD={b['max_drawdown_pct']}%  Candidate DD={c['max_drawdown_pct']}%")

    emit_json({
        "command": "test",
        "overrides": overrides,
        "baseline": b,
        "candidate": c,
        "mar_delta": round(c["mar_ratio"] - b["mar_ratio"], 3),
        "better": c["mar_ratio"] > b["mar_ratio"],
    })


def cmd_validate(df: pd.DataFrame, args):
    overrides = json.loads(args.params)
    base_dict = StrategyParams().to_dict()
    base_dict.update(overrides)
    candidate = StrategyParams.from_dict(base_dict)

    v = validate_candidate(df, candidate, check_stability=args.stability)
    print(v.summary_str())

    emit_json({
        "command": "validate",
        "overrides": overrides,
        "passes": v.passes_validation,
        "consistent": v.consistent_improvement,
        "avg_test_mar": round(v.avg_test_mar, 3),
        "avg_test_cagr": round(v.avg_test_cagr, 2),
        "avg_test_max_dd": round(v.avg_test_max_dd, 1),
        "mar_improvement_pct": round(v.mar_improvement_pct, 1),
        "stability": round(v.param_stability_score, 2),
        "rejection_reasons": v.rejection_reasons,
        "windows": v.window_results,
    })


def cmd_sweep(df: pd.DataFrame, args):
    param_name = args.param
    values = np.arange(args.min_val, args.max_val + args.step / 2, args.step)

    if param_name.endswith("_len") or param_name.endswith("_bars"):
        values = values.astype(int)

    baseline = run_backtest(df, StrategyParams())
    b_mar = baseline.mar_ratio
    b_trades = baseline.num_trades

    print(f"Sweeping {param_name} ({len(values)} values), baseline MAR={b_mar:.3f}")

    best_mar = -999
    best_val = None
    best_result = None
    all_results = []

    for v in values:
        val = int(v) if isinstance(v, (np.integer,)) else float(v)
        override = {param_name: val}
        base_dict = StrategyParams().to_dict()
        base_dict.update(override)
        params = StrategyParams.from_dict(base_dict)
        r = run_backtest(df, params)

        entry = {"value": val, **result_to_dict(r)}
        all_results.append(entry)

        if r.mar_ratio > best_mar:
            best_mar = r.mar_ratio
            best_val = val
            best_result = entry

    # Apply quality filters to find the FILTERED best
    filtered_best_mar = b_mar  # Must beat baseline
    filtered_best_val = None
    filtered_best = None
    for entry in all_results:
        passes = (
            entry["mar_ratio"] >= b_mar * 0.98  # At least 98% of baseline
            and entry["num_trades"] >= 5  # Minimum trades
            and entry["trades_per_year"] <= max(baseline.trades_per_year * 1.5, 6)
        )
        if passes and entry["mar_ratio"] > filtered_best_mar:
            filtered_best_mar = entry["mar_ratio"]
            filtered_best_val = entry["value"]
            filtered_best = entry

    emit_json({
        "command": "sweep",
        "param": param_name,
        "baseline_mar": round(b_mar, 3),
        "baseline_value": StrategyParams().to_dict().get(param_name),
        "raw_best": {"value": best_val, "mar": round(best_mar, 3)},
        "filtered_best": {
            "value": filtered_best_val,
            "mar": round(filtered_best_mar, 3),
            "improves": filtered_best_val is not None,
        } if filtered_best else {"value": None, "mar": round(b_mar, 3), "improves": False},
        "all_results": all_results,
    })


def cmd_grid(df: pd.DataFrame, args):
    """Grid search over 2+ parameters (proper interaction testing)."""
    spec = json.loads(args.spec)
    param_names = list(spec.keys())
    param_values = list(spec.values())

    baseline = run_backtest(df, StrategyParams())
    b_mar = baseline.mar_ratio
    combos = list(product(*param_values))

    print(f"Grid search: {param_names}, {len(combos)} combinations, baseline MAR={b_mar:.3f}")

    best_mar = -999
    best_combo = None
    all_results = []

    for combo in combos:
        override = dict(zip(param_names, combo))
        base_dict = StrategyParams().to_dict()
        base_dict.update(override)
        params = StrategyParams.from_dict(base_dict)
        r = run_backtest(df, params)

        entry = {"params": override, **result_to_dict(r)}
        all_results.append(entry)

        if r.mar_ratio > best_mar:
            best_mar = r.mar_ratio
            best_combo = override

    # Sort by MAR descending, take top 5
    all_results.sort(key=lambda x: x["mar_ratio"], reverse=True)

    emit_json({
        "command": "grid",
        "param_names": param_names,
        "baseline_mar": round(b_mar, 3),
        "num_combos": len(combos),
        "best": {"params": best_combo, "mar": round(best_mar, 3)},
        "top_5": all_results[:5],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Montauk Backtest Runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("baseline")

    p_test = sub.add_parser("test")
    p_test.add_argument("--params", required=True)

    p_val = sub.add_parser("validate")
    p_val.add_argument("--params", required=True)
    p_val.add_argument("--stability", action="store_true")

    p_sweep = sub.add_parser("sweep")
    p_sweep.add_argument("--param", required=True)
    p_sweep.add_argument("--min", dest="min_val", type=float, required=True)
    p_sweep.add_argument("--max", dest="max_val", type=float, required=True)
    p_sweep.add_argument("--step", type=float, required=True)

    p_grid = sub.add_parser("grid")
    p_grid.add_argument("--spec", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    df = get_tecl_data()
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    commands = {
        "baseline": cmd_baseline,
        "test": cmd_test,
        "validate": cmd_validate,
        "sweep": cmd_sweep,
        "grid": cmd_grid,
    }

    start = time.time()
    commands[args.command](df, args)
    elapsed = time.time() - start
    print(f"\n[Done in {elapsed:.1f}s]")


if __name__ == "__main__":
    main()
