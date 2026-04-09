#!/usr/bin/env python3
"""
Cross-Asset Validation — test strategies on TQQQ and QQQ.

If a strategy works on TECL (3x tech) AND on TQQQ (3x QQQ) and QQQ (1x),
it is less likely to be overfit to TECL-specific noise. This is the single
most powerful anti-overfitting test (per VALIDATION-PHILOSOPHY.md).

Note: Parameters are tuned for TECL's volatility profile. QQQ's vol is ~3x
lower, so ATR multipliers and percentage thresholds may not translate
perfectly. This is a known limitation — we report raw results and let
Claude interpret whether the strategy logic generalizes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from strategy_engine import Indicators, backtest
from strategies import STRATEGY_REGISTRY
from data import get_tecl_data, get_tqqq_data, get_qqq_data


def cross_asset_validate(
    strategy_name: str,
    params: dict,
    assets: list[str] | None = None,
) -> dict:
    """
    Run a strategy on multiple assets with the same params.

    Returns dict with per-asset metrics:
      {asset_name: {vs_bah, cagr, max_dd, trades, trades_yr, win_rate}}
    """
    if assets is None:
        assets = ["TECL", "TQQQ", "QQQ"]

    loaders = {
        "TECL": get_tecl_data,
        "TQQQ": get_tqqq_data,
        "QQQ": get_qqq_data,
    }

    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    cooldown = params.get("cooldown", 0)
    results = {}

    for asset in assets:
        if asset not in loaders:
            print(f"[cross_asset] Unknown asset: {asset}, skipping")
            continue

        try:
            df = loaders[asset]()
            ind = Indicators(df)
            entries, exits, labels = strategy_fn(ind, params)
            result = backtest(df, entries, exits, labels,
                              cooldown_bars=cooldown, strategy_name=strategy_name)

            results[asset] = {
                "vs_bah": round(result.vs_bah_multiple, 4),
                "cagr": round(result.cagr_pct, 1),
                "max_dd": round(result.max_drawdown_pct, 1),
                "trades": result.num_trades,
                "trades_yr": round(result.trades_per_year, 1),
                "win_rate": round(result.win_rate_pct, 1),
                "exit_reasons": result.exit_reasons,
            }
        except Exception as e:
            print(f"[cross_asset] {asset} failed: {e}")
            results[asset] = {"error": str(e)}

    return {
        "strategy": strategy_name,
        "params": params,
        "results": results,
    }


def format_cross_asset(validation: dict) -> str:
    """Format cross-asset results as a readable string."""
    lines = []
    lines.append(f"CROSS-ASSET VALIDATION: {validation['strategy']}")
    lines.append("=" * 60)

    header = f"  {'Asset':<8s} {'vs B&H':>8s} {'CAGR':>7s} {'MaxDD':>7s} {'Trades':>7s} {'Tr/Yr':>6s} {'Win%':>6s}"
    lines.append(header)
    lines.append("  " + "-" * 52)

    for asset, metrics in validation["results"].items():
        if "error" in metrics:
            lines.append(f"  {asset:<8s} ERROR: {metrics['error']}")
            continue
        lines.append(
            f"  {asset:<8s} {metrics['vs_bah']:>8.4f} {metrics['cagr']:>6.1f}% "
            f"{metrics['max_dd']:>6.1f}% {metrics['trades']:>7d} {metrics['trades_yr']:>5.1f} "
            f"{metrics['win_rate']:>5.1f}%"
        )

    # Consistency check
    asset_results = [v for v in validation["results"].values() if "error" not in v]
    if len(asset_results) >= 2:
        vs_bahs = [v["vs_bah"] for v in asset_results]
        if all(v > 0 for v in vs_bahs):
            ratio = max(vs_bahs) / min(vs_bahs)
            if ratio < 3:
                lines.append(f"\n  Consistency: GOOD — vs_bah varies by {ratio:.1f}x across assets")
            else:
                lines.append(f"\n  Consistency: POOR — vs_bah varies by {ratio:.1f}x (possible TECL overfit)")

    return "\n".join(lines)


if __name__ == "__main__":
    import json

    # Test on top leaderboard strategy
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lb_path = os.path.join(project_root, "spike", "leaderboard.json")
    with open(lb_path) as f:
        lb = json.load(f)

    if lb:
        top = lb[0]
        print(f"Testing: {top['strategy']} (fitness: {top['fitness']})\n")
        result = cross_asset_validate(top["strategy"], top["params"])
        print(format_cross_asset(result))
