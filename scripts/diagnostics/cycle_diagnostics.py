#!/usr/bin/env python3
"""
Cycle Diagnostics — per-cycle trade analysis for Claude.

Groups a strategy's trades by bull/bear cycle and identifies:
- Which cycles the strategy captured/avoided well
- Where the strategy was out of market during bull runs (gaps)
- Which exit conditions caused premature exits
- Specific actionable insights for strategy improvement

Used by /spike v2 to show Claude intermediate results between optimizer chunks.
"""

from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy_engine import Indicators, backtest
from strategies import STRATEGY_REGISTRY
from regime_map import build_regime_map


def diagnose_strategy(
    strategy_name: str,
    params: dict,
    df: pd.DataFrame,
    regime_map: dict | None = None,
) -> dict:
    """
    Run a strategy and produce per-cycle trade diagnostics.

    Returns dict with:
      summary: overall metrics
      bull_cycles: per-bull analysis with trades and gaps
      bear_cycles: per-bear analysis with trades
      exit_analysis: which exit reasons fire most, and in which cycle types
      bottleneck: "bull_capture" or "bear_avoidance" — where the strategy loses most
    """
    if regime_map is None:
        regime_map = build_regime_map(df)

    # Run the strategy
    ind = Indicators(df)
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    cooldown = params.get("cooldown", 0)
    entries, exits, labels = strategy_fn(ind, params)
    result = backtest(
        df, entries, exits, labels, cooldown_bars=cooldown, strategy_name=strategy_name
    )

    dates = df["date"].values
    close = df["close"].values.astype(np.float64)
    trades = result.trades

    # Group trades by cycle
    bull_analysis = []
    for bi, bull in enumerate(regime_map["bulls"]):
        cycle_trades = _trades_in_range(trades, bull["start_idx"], bull["end_idx"])
        gaps = _find_gaps(
            cycle_trades, bull["start_idx"], bull["end_idx"], dates, close
        )

        # How much of the bull move was captured
        bull_move = bull["move_pct"]
        captured_pct = _compute_capture(
            cycle_trades, close, bull["start_idx"], bull["end_idx"]
        )

        bull_analysis.append(
            {
                "cycle": bull,
                "cycle_num": bi + 1,
                "trades": _serialize_trades(cycle_trades, dates, close),
                "num_trades": len(cycle_trades),
                "captured_pct": round(captured_pct, 1),
                "bull_move_pct": round(bull_move, 1),
                "gaps": gaps,
                "total_gap_bars": sum(g["bars"] for g in gaps),
            }
        )

    bear_analysis = []
    for bi, bear in enumerate(regime_map["bears"]):
        cycle_trades = _trades_in_range(trades, bear["start_idx"], bear["end_idx"])

        # How much of the bear was avoided
        avoided_pct = _compute_avoidance(
            cycle_trades, close, bear["start_idx"], bear["end_idx"]
        )

        bear_analysis.append(
            {
                "cycle": bear,
                "cycle_num": bi + 1,
                "trades": _serialize_trades(cycle_trades, dates, close),
                "num_trades": len(cycle_trades),
                "avoided_pct": round(avoided_pct, 1),
                "bear_move_pct": round(bear["move_pct"], 1),
            }
        )

    # Exit reason analysis: which exits fire in bulls vs bears
    exit_in_bulls = {}
    exit_in_bears = {}
    for t in trades:
        reason = t.exit_reason or "unknown"
        # Determine if this trade's exit was during a bull or bear
        for bull in regime_map["bulls"]:
            if bull["start_idx"] <= t.exit_bar <= bull["end_idx"]:
                exit_in_bulls[reason] = exit_in_bulls.get(reason, 0) + 1
                break
        for bear in regime_map["bears"]:
            if bear["start_idx"] <= t.exit_bar <= bear["end_idx"]:
                exit_in_bears[reason] = exit_in_bears.get(reason, 0) + 1
                break

    # Identify bottleneck
    avg_bull_capture = (
        np.mean([b["captured_pct"] for b in bull_analysis]) if bull_analysis else 0
    )
    avg_bear_avoidance = (
        np.mean([b["avoided_pct"] for b in bear_analysis]) if bear_analysis else 0
    )

    return {
        "strategy": strategy_name,
        "params": params,
        "summary": {
            "share_multiple": round(result.share_multiple, 4),
            "cagr": round(result.cagr_pct, 1),
            "max_dd": round(result.max_drawdown_pct, 1),
            "trades": result.num_trades,
            "trades_yr": round(result.trades_per_year, 1),
            "win_rate": round(result.win_rate_pct, 1),
            "exit_reasons": result.exit_reasons,
        },
        "bull_cycles": bull_analysis,
        "bear_cycles": bear_analysis,
        "exit_in_bulls": exit_in_bulls,
        "exit_in_bears": exit_in_bears,
        "avg_bull_capture": round(avg_bull_capture, 1),
        "avg_bear_avoidance": round(avg_bear_avoidance, 1),
        "bottleneck": "bull_capture"
        if avg_bull_capture < avg_bear_avoidance
        else "bear_avoidance",
    }


def format_diagnostics(diag: dict, top_n_cycles: int = 5) -> str:
    """Format cycle diagnostics as a readable string for Claude."""
    lines = []
    s = diag["summary"]
    lines.append(f"CYCLE DIAGNOSTICS: {diag['strategy']} (share_multiple: {s['share_multiple']:.4f}x)")
    lines.append("=" * 65)
    lines.append(
        f"CAGR: {s['cagr']}% | MaxDD: {s['max_dd']}% | Trades: {s['trades']} ({s['trades_yr']}/yr)"
    )
    lines.append(
        f"Avg Bull Capture: {diag['avg_bull_capture']}% | Avg Bear Avoidance: {diag['avg_bear_avoidance']}%"
    )
    lines.append(f"Bottleneck: {diag['bottleneck'].upper()}\n")

    # Show worst bull cycles (lowest capture = biggest missed opportunities)
    bulls_sorted = sorted(diag["bull_cycles"], key=lambda x: x["captured_pct"])
    lines.append("WORST BULL CYCLES (lowest capture):")
    for b in bulls_sorted[:top_n_cycles]:
        c = b["cycle"]
        lines.append(
            f"  Bull #{b['cycle_num']}: {c['start_date']} → {c['end_date']}  "
            f"({c['move_pct']:+.0f}% move)"
        )
        lines.append(
            f"    Captured: {b['captured_pct']}% | Trades: {b['num_trades']} | Gap bars: {b['total_gap_bars']}"
        )

        # Show gaps (periods out of market)
        for g in b["gaps"][:3]:
            lines.append(
                f"    GAP: {g['start_date']} → {g['end_date']} ({g['bars']} bars) "
                f"— missed {g['missed_move_pct']:+.1f}% move"
            )

        # Show trades with exit reasons
        for t in b["trades"][:5]:
            lines.append(
                f"    TRADE: {t['entry_date']} → {t['exit_date']} {t['pnl_pct']:+.1f}% [{t['exit_reason']}]"
            )

    # Show best bear cycles (highest avoidance)
    bears_sorted = sorted(diag["bear_cycles"], key=lambda x: -x["avoided_pct"])
    lines.append("\nBEST BEAR AVOIDANCE:")
    for b in bears_sorted[:3]:
        c = b["cycle"]
        lines.append(
            f"  Bear #{b['cycle_num']}: {c['start_date']} → {c['end_date']}  "
            f"({c['move_pct']:+.0f}% drop) — avoided {b['avoided_pct']}%"
        )

    # Show worst bear cycles (lowest avoidance = got caught)
    bears_worst = sorted(diag["bear_cycles"], key=lambda x: x["avoided_pct"])
    lines.append("\nWORST BEAR AVOIDANCE (got caught):")
    for b in bears_worst[:3]:
        c = b["cycle"]
        lines.append(
            f"  Bear #{b['cycle_num']}: {c['start_date']} → {c['end_date']}  "
            f"({c['move_pct']:+.0f}% drop) — avoided only {b['avoided_pct']}%"
        )

    # Exit reason breakdown: bulls vs bears
    lines.append("\nEXIT REASONS IN BULL vs BEAR CYCLES:")
    all_reasons = set(
        list(diag["exit_in_bulls"].keys()) + list(diag["exit_in_bears"].keys())
    )
    for reason in sorted(all_reasons):
        bull_count = diag["exit_in_bulls"].get(reason, 0)
        bear_count = diag["exit_in_bears"].get(reason, 0)
        total = bull_count + bear_count
        if total > 0:
            bull_pct = bull_count / total * 100
            lines.append(
                f"  {reason:20s}: {bull_count:3d} in bulls, {bear_count:3d} in bears "
                f"({bull_pct:.0f}% during bulls)"
            )
            if bull_pct > 70:
                lines.append(
                    "    ^ THIS EXIT FIRES MOSTLY DURING BULLS — likely hurting bull capture"
                )

    return "\n".join(lines)


# ─── Helpers ─────────────────────────────────────────────────────────


def _trades_in_range(trades: list, start_idx: int, end_idx: int) -> list:
    """Find trades that overlap with a cycle [start_idx, end_idx]."""
    result = []
    for t in trades:
        # Trade overlaps if it entered before cycle ends AND exited after cycle starts
        if t.entry_bar <= end_idx and t.exit_bar >= start_idx:
            result.append(t)
    return result


def _find_gaps(
    trades: list, start_idx: int, end_idx: int, dates: np.ndarray, close: np.ndarray
) -> list[dict]:
    """Find periods within [start_idx, end_idx] where no trade is active."""
    # Build a coverage array
    covered = np.zeros(end_idx - start_idx + 1, dtype=bool)
    for t in trades:
        t_start = max(t.entry_bar, start_idx) - start_idx
        t_end = min(t.exit_bar, end_idx) - start_idx
        covered[t_start : t_end + 1] = True

    gaps = []
    i = 0
    while i < len(covered):
        if not covered[i]:
            gap_start = i
            while i < len(covered) and not covered[i]:
                i += 1
            gap_end = i - 1

            abs_start = start_idx + gap_start
            abs_end = start_idx + gap_end
            gap_bars = gap_end - gap_start + 1

            if gap_bars >= 5:  # Only report gaps >= 5 bars
                start_price = float(close[abs_start])
                end_price = float(close[abs_end])
                missed = (end_price / start_price - 1) * 100 if start_price > 0 else 0

                gaps.append(
                    {
                        "start_idx": abs_start,
                        "end_idx": abs_end,
                        "start_date": str(dates[abs_start])[:10],
                        "end_date": str(dates[abs_end])[:10],
                        "bars": gap_bars,
                        "missed_move_pct": round(missed, 1),
                    }
                )
        else:
            i += 1

    return gaps


def _compute_capture(
    trades: list, close: np.ndarray, start_idx: int, end_idx: int
) -> float:
    """Compute what % of a bull cycle's gains were captured by active trades."""
    if end_idx <= start_idx:
        return 0.0

    total_bull_move = close[end_idx] - close[start_idx]
    if total_bull_move <= 0:
        return 0.0

    captured_move = 0.0
    for t in trades:
        t_start = max(t.entry_bar, start_idx)
        t_end = min(t.exit_bar, end_idx)
        if t_end > t_start:
            captured_move += close[t_end] - close[t_start]

    return (captured_move / total_bull_move) * 100


def _compute_avoidance(
    trades: list, close: np.ndarray, start_idx: int, end_idx: int
) -> float:
    """Compute what % of a bear cycle's losses were avoided."""
    if end_idx <= start_idx:
        return 100.0

    total_bear_move = close[start_idx] - close[end_idx]  # positive = loss avoided
    if total_bear_move <= 0:
        return 100.0

    exposed_loss = 0.0
    for t in trades:
        t_start = max(t.entry_bar, start_idx)
        t_end = min(t.exit_bar, end_idx)
        if t_end > t_start:
            loss = close[t_start] - close[t_end]
            if loss > 0:
                exposed_loss += loss

    avoided = total_bear_move - exposed_loss
    return (avoided / total_bear_move) * 100


def _serialize_trades(trades: list, dates: np.ndarray, close: np.ndarray) -> list[dict]:
    """Convert Trade objects to serializable dicts."""
    result = []
    for t in trades:
        result.append(
            {
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_bar": t.entry_bar,
                "exit_bar": t.exit_bar,
                "pnl_pct": round(t.pnl_pct, 1),
                "exit_reason": t.exit_reason,
                "bars_held": t.bars_held,
            }
        )
    return result


if __name__ == "__main__":
    from data import get_tecl_data

    df = get_tecl_data()
    regime_map = build_regime_map(df)

    # Diagnose top leaderboard strategy
    import json

    lb_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "spike",
        "leaderboard.json",
    )
    with open(lb_path) as f:
        lb = json.load(f)

    if lb:
        top = lb[0]
        print(f"Diagnosing: {top['strategy']} (fitness: {top['fitness']})\n")
        diag = diagnose_strategy(top["strategy"], top["params"], df, regime_map)
        print(format_diagnostics(diag))
