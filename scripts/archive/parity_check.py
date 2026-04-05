#!/usr/bin/env python3
"""
Parity check: compare Python backtest engine output against TradingView results.

Reads the TradingView comparison data and runs the same configs through the
Python engine, then reports discrepancies. This catches logic errors before
they pollute optimization results.

Usage:
  python3 scripts/parity_check.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import get_tecl_data
from backtest_engine import StrategyParams, run_backtest


# ─────────────────────────────────────────────────────────────────────────────
# TradingView reference data (from backtest-comparison.md)
# ─────────────────────────────────────────────────────────────────────────────

TV_REFERENCE = {
    "8.2.1": {
        "params": {},  # defaults
        "tv": {
            "total_trades": 19,
            "win_rate": 57.89,
            "cagr": 37.73,
            "total_return_pct": 25300.32,
            "avg_bars_held": 187,
            "avg_bars_winning": 260,
            "avg_bars_losing": 80,
            "wins": 11,
            "losses": 8,
            "max_dd_intrabar_pct": 44.26,
            "sortino": 1.400,
            "avg_win_pct": 94.12,
            "avg_loss_pct": 13.68,  # absolute value
            "bah_return_pct": 12556.40,
        },
    },
    "8.3-conservative": {
        "params": {
            "sell_confirm_bars": 1,
            "sell_cooldown_bars": 8,
            "atr_period": 50,
            "enable_vol_exit": True,
            "vol_spike_mult": 2.5,
        },
        "tv": {
            "total_trades": 21,
            "win_rate": 52.38,
            "cagr": 31.19,
            "total_return_pct": 10804.72,
            "avg_bars_held": 167,
            "avg_bars_winning": 229,
            "avg_bars_losing": 98,
            "wins": 11,
            "losses": 10,
            "max_dd_intrabar_pct": 47.76,
            "sortino": 0.847,
            "avg_win_pct": 82.13,
            "avg_loss_pct": 17.06,
            "bah_return_pct": 22419.60,
        },
    },
    "9.0-candidate": {
        "params": {
            "sell_confirm_bars": 1,
            "sell_cooldown_bars": 8,
            "atr_period": 50,
            "enable_vol_exit": True,
            "vol_spike_mult": 2.3,
        },
        "tv": {
            "total_trades": 24,
            "win_rate": 45.83,
            "cagr": 34.55,
            "total_return_pct": 16870.55,
            "avg_bars_held": 139,
            "avg_bars_winning": 218,
            "avg_bars_losing": 71,
            "wins": 11,
            "losses": 13,
            "max_dd_intrabar_pct": 40.98,
            "sortino": 1.126,
            "avg_win_pct": 98.72,
            "avg_loss_pct": 13.86,
            "bah_return_pct": 22499.60,
        },
    },
}


def run_parity():
    df = get_tecl_data(use_yfinance=False)

    print("=" * 70)
    print("PARITY CHECK: Python Engine vs TradingView")
    print("=" * 70)

    total_issues = 0

    for name, ref in TV_REFERENCE.items():
        print(f"\n── {name} ──")

        base = StrategyParams().to_dict()
        base.update(ref["params"])
        params = StrategyParams.from_dict(base)
        result = run_backtest(df, params)
        tv = ref["tv"]

        # Compare key metrics
        checks = [
            ("Total trades",   result.num_trades,         tv["total_trades"],      2),
            ("Win rate %",     result.win_rate_pct,        tv["win_rate"],          10),
            ("CAGR %",         result.cagr_pct,            tv["cagr"],              10),
            ("Total return %", result.total_return_pct,     tv["total_return_pct"],  30),
            ("Avg bars held",  result.avg_bars_held,        tv["avg_bars_held"],     20),
        ]

        wins = sum(1 for t in result.trades if t.pnl_pct > 0)
        losses = sum(1 for t in result.trades if t.pnl_pct <= 0)
        checks.append(("Wins", wins, tv["wins"], 2))
        checks.append(("Losses", losses, tv["losses"], 2))

        if wins > 0:
            avg_win = sum(t.pnl_pct for t in result.trades if t.pnl_pct > 0) / wins
            checks.append(("Avg win %", avg_win, tv["avg_win_pct"], 15))
        if losses > 0:
            avg_loss = abs(sum(t.pnl_pct for t in result.trades if t.pnl_pct <= 0) / losses)
            checks.append(("Avg loss %", avg_loss, tv["avg_loss_pct"], 15))

        issues = 0
        for metric, py_val, tv_val, tolerance_pct in checks:
            if tv_val == 0:
                match = abs(py_val) < 1
            else:
                pct_diff = abs(py_val - tv_val) / abs(tv_val) * 100
                match = pct_diff <= tolerance_pct

            status = "OK" if match else "MISMATCH"
            if not match:
                issues += 1

            if isinstance(py_val, float):
                print(f"  {status:>8}  {metric:<20} Py={py_val:>10.1f}  TV={tv_val:>10.1f}"
                      f"{'  ⚠ ' + str(round(abs(py_val - tv_val) / max(abs(tv_val), 1) * 100, 1)) + '% off' if not match else ''}")
            else:
                print(f"  {status:>8}  {metric:<20} Py={py_val:>10}  TV={tv_val:>10}"
                      f"{'  ⚠ diff=' + str(abs(py_val - tv_val)) if not match else ''}")

        # Trade log comparison
        print(f"\n  Python trades ({result.num_trades}):")
        for t in result.trades:
            win_loss = "W" if t.pnl_pct > 0 else "L"
            print(f"    {t.entry_date} → {t.exit_date}  {t.pnl_pct:+6.1f}% {win_loss}  "
                  f"{t.exit_reason:<12} ({t.bars_held} bars)")

        if issues == 0:
            print(f"\n  ✓ All checks pass")
        else:
            print(f"\n  ✗ {issues} issue(s) found")
        total_issues += issues

    print(f"\n{'=' * 70}")
    if total_issues == 0:
        print("PARITY: ALL PASS — engine matches TradingView within tolerances")
    else:
        print(f"PARITY: {total_issues} ISSUE(S) — review discrepancies above")
        print("Common causes: warmup period differences, fill timing, EMA seed values")
    print("=" * 70)

    return total_issues


if __name__ == "__main__":
    issues = run_parity()
    sys.exit(0 if issues == 0 else 1)
