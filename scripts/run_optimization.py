#!/usr/bin/env python3
"""
Montauk Continuous Optimization — CLI runner.

Every command prints a compact JSON summary on its final line prefixed with
###JSON### so Claude can parse results cheaply without reading tables.

Primary optimization target: regime_score (bull capture + bear avoidance).
MAR and other metrics are reported for reference but NOT used for ranking.

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


def get_regime_score(r: BacktestResult) -> float:
    """Extract composite regime score from a result. Returns 0.0 if not computed."""
    if r.regime_score is None:
        return 0.0
    return r.regime_score.composite


def result_to_dict(r: BacktestResult) -> dict:
    d = {
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
        "false_signal_rate_pct": round(r.false_signal_rate_pct, 1),
        "bah_return_pct": round(r.bah_return_pct, 2),
        "bah_final_equity": round(r.bah_final_equity, 2),
        "vs_bah_multiple": round(r.vs_bah_multiple, 3),
        "bah_start_date": r.bah_start_date,
        "regime_score": round(get_regime_score(r), 4),
    }
    if r.regime_score:
        d["bull_capture"] = r.regime_score.bull_capture_ratio
        d["bear_avoidance"] = r.regime_score.bear_avoidance_ratio
        d["num_bull_periods"] = r.regime_score.num_bull_periods
        d["num_bear_periods"] = r.regime_score.num_bear_periods
    return d


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


def passes_quality_filters(entry: dict, baseline_trades_per_year: float) -> bool:
    """Shared quality guard: minimum trades, no churn, no near-zero MAR."""
    return (
        entry["num_trades"] >= 5
        and entry["trades_per_year"] <= max(baseline_trades_per_year * 1.5, 6)
        and entry["mar_ratio"] > 0.05  # Must have some positive risk-adjusted return
    )


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_baseline(df: pd.DataFrame, args):
    params = StrategyParams()
    result = run_backtest(df, params)
    print("=== BASELINE (Montauk 8.2.1) ===")
    print(result.summary_str())

    windows = {}
    for name, window_df in split_named_windows(df):
        r = run_backtest(window_df, params)
        windows[name] = result_to_dict(r)
        rs = get_regime_score(r)
        print(f"  {name}: CAGR={r.cagr_pct:.1f}% DD={r.max_drawdown_pct:.1f}% MAR={r.mar_ratio:.2f} RegimeScore={rs:.3f} Trades={r.num_trades}")

    trades_log = []
    for t in result.trades:
        trades_log.append({
            "entry": t.entry_date, "exit": t.exit_date,
            "pnl_pct": round(t.pnl_pct, 1), "reason": t.exit_reason,
            "bars": t.bars_held
        })

    regime_detail = {}
    if result.regime_score:
        regime_detail = {
            "bear_detail": result.regime_score.bear_detail,
            "bull_detail": result.regime_score.bull_detail,
        }

    emit_json({
        "command": "baseline",
        "metrics": result_to_dict(result),
        "windows": windows,
        "trades": trades_log,
        "regime_detail": regime_detail,
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

    b_score = b["regime_score"]
    c_score = c["regime_score"]
    score_delta = round(c_score - b_score, 4)

    print(f"Testing: {overrides}")
    print(f"  Baseline  RegimeScore={b_score:.3f}  MAR={b['mar_ratio']}  CAGR={b['cagr_pct']}%")
    print(f"  Candidate RegimeScore={c_score:.3f}  MAR={c['mar_ratio']}  CAGR={c['cagr_pct']}%")
    print(f"  Delta: {score_delta:+.4f} (regime)  {round(c['mar_ratio'] - b['mar_ratio'], 3):+.3f} (MAR)")

    emit_json({
        "command": "test",
        "overrides": overrides,
        "baseline": b,
        "candidate": c,
        "score_delta": score_delta,
        "mar_delta": round(c["mar_ratio"] - b["mar_ratio"], 3),
        "better": c_score > b_score,  # regime score is primary
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
        "avg_test_regime_score": round(v.avg_test_regime_score, 4),
        "avg_test_mar": round(v.avg_test_mar, 3),
        "avg_test_cagr": round(v.avg_test_cagr, 2),
        "avg_test_max_dd": round(v.avg_test_max_dd, 1),
        "regime_score_improvement_pct": round(v.regime_score_improvement_pct, 1),
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
    b_score = get_regime_score(baseline)
    b_mar = baseline.mar_ratio

    print(f"Sweeping {param_name} ({len(values)} values), baseline RegimeScore={b_score:.3f}  MAR={b_mar:.3f}")

    best_score = -999
    best_val = None
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

        if get_regime_score(r) > best_score:
            best_score = get_regime_score(r)
            best_val = val

    # Apply quality filters to find the FILTERED best
    # Primary: regime_score must beat baseline. Secondary guards: trade count, churn, MAR floor.
    filtered_best_score = b_score  # Must beat baseline
    filtered_best_val = None
    filtered_best = None
    for entry in all_results:
        if passes_quality_filters(entry, baseline.trades_per_year):
            if entry["regime_score"] > filtered_best_score:
                filtered_best_score = entry["regime_score"]
                filtered_best_val = entry["value"]
                filtered_best = entry

    # Plateau width: number of sweep values within 0.005 of best score
    # A wide plateau = robust. A narrow spike = fragile.
    plateau_threshold = 0.005
    plateau_width = sum(1 for e in all_results if abs(e["regime_score"] - best_score) <= plateau_threshold)

    print(f"  Raw best: {param_name}={best_val}  RegimeScore={best_score:.3f}")
    if filtered_best_val is not None:
        print(f"  Filtered best: {param_name}={filtered_best_val}  RegimeScore={filtered_best_score:.3f}  (IMPROVES baseline)")
    else:
        print(f"  Filtered best: no improvement over baseline")

    emit_json({
        "command": "sweep",
        "param": param_name,
        "baseline_score": round(b_score, 4),
        "baseline_mar": round(b_mar, 3),
        "baseline_value": StrategyParams().to_dict().get(param_name),
        "raw_best": {"value": best_val, "score": round(best_score, 4)},
        "filtered_best": {
            "value": filtered_best_val,
            "score": round(filtered_best_score, 4),
            "improves": filtered_best_val is not None,
        } if filtered_best else {"value": None, "score": round(b_score, 4), "improves": False},
        "plateau_width": plateau_width,
        "all_results": all_results,
    })


def cmd_bootstrap(df: pd.DataFrame, args):
    """Permutation test: shuffle trade PnL order 1000 times, check if regime score is significant."""
    overrides = json.loads(args.params) if hasattr(args, 'params') and args.params else {}
    base_dict = StrategyParams().to_dict()
    base_dict.update(overrides)
    params = StrategyParams.from_dict(base_dict)
    result = run_backtest(df, params)

    if not result.trades:
        print("No trades to bootstrap.")
        emit_json({"command": "bootstrap", "error": "no_trades"})
        return

    actual_score = get_regime_score(result)
    actual_return = result.total_return_pct

    # Permutation test: shuffle trade returns, recompute final equity
    pnl_series = [t.pnl_pct / 100.0 for t in result.trades]
    n_sim = 1000
    sim_returns = []
    rng = np.random.default_rng(42)

    for _ in range(n_sim):
        shuffled = rng.permutation(pnl_series)
        equity = 1.0
        for pnl in shuffled:
            equity *= (1 + pnl)
        sim_returns.append((equity - 1) * 100)

    sim_returns = np.array(sim_returns)
    percentile = float(np.mean(sim_returns < actual_return) * 100)
    beats_median = actual_return > float(np.median(sim_returns))

    print(f"\n=== BOOTSTRAP TEST ===")
    print(f"Actual Return:   {actual_return:>8.1f}%")
    print(f"Sim Median:      {np.median(sim_returns):>8.1f}%")
    print(f"Sim 95th pct:    {np.percentile(sim_returns, 95):>8.1f}%")
    print(f"Percentile rank: {percentile:>8.1f}%  ({'significant' if percentile >= 75 else 'not significant'})")
    print(f"Regime Score:    {actual_score:.4f}")

    emit_json({
        "command": "bootstrap",
        "actual_return_pct": round(actual_return, 2),
        "actual_regime_score": round(actual_score, 4),
        "sim_median_return_pct": round(float(np.median(sim_returns)), 2),
        "sim_p95_return_pct": round(float(np.percentile(sim_returns, 95)), 2),
        "percentile_rank": round(percentile, 1),
        "significant": percentile >= 75,
        "n_trades": len(result.trades),
        "n_simulations": n_sim,
    })


def cmd_grid(df: pd.DataFrame, args):
    """Grid search over 2+ parameters (proper interaction testing)."""
    spec = json.loads(args.spec)
    param_names = list(spec.keys())
    param_values = list(spec.values())

    baseline = run_backtest(df, StrategyParams())
    b_score = get_regime_score(baseline)
    b_mar = baseline.mar_ratio
    combos = list(product(*param_values))

    print(f"Grid search: {param_names}, {len(combos)} combinations, baseline RegimeScore={b_score:.3f}")

    best_score = -999
    best_combo = None
    all_results = []

    for combo in combos:
        override = dict(zip(param_names, combo))
        base_dict = StrategyParams().to_dict()
        base_dict.update(override)
        params = StrategyParams.from_dict(base_dict)
        r = run_backtest(df, params)
        score = get_regime_score(r)

        entry = {"params": override, **result_to_dict(r)}
        all_results.append(entry)

        if score > best_score:
            best_score = score
            best_combo = override

    # Sort by regime_score descending, take top 5
    all_results.sort(key=lambda x: x["regime_score"], reverse=True)

    emit_json({
        "command": "grid",
        "param_names": param_names,
        "baseline_score": round(b_score, 4),
        "baseline_mar": round(b_mar, 3),
        "num_combos": len(combos),
        "best": {"params": best_combo, "score": round(best_score, 4)},
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

    p_bootstrap = sub.add_parser("bootstrap")
    p_bootstrap.add_argument("--params", default=None)

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
        "bootstrap": cmd_bootstrap,
    }

    start = time.time()
    commands[args.command](df, args)
    elapsed = time.time() - start
    print(f"\n[Done in {elapsed:.1f}s]")


if __name__ == "__main__":
    main()
