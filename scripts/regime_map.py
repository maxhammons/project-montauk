#!/usr/bin/env python3
"""
Regime Map — bull/bear cycle detection and formatting for Claude.

Builds a structured map of all market cycles in the TECL dataset,
showing dates, magnitude, duration, and summary statistics. This
gives Claude the ground-truth context it needs to design strategies
that target specific market conditions.

Uses a rolling-peak detection algorithm tuned for 3x leveraged ETFs,
where absolute price recovery to prior peaks may never happen
(dot-com peak $389 → GFC trough $0.20, never recovered due to vol decay).
"""

from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _detect_drawdowns(
    close: np.ndarray,
    dates: np.ndarray,
    dd_threshold: float = 0.35,
    trough_recovery_mult: float = 2.0,
    min_duration: int = 15,
) -> list[dict]:
    """
    Detect bear periods using rolling peaks and TROUGH-RELATIVE recovery.

    A bear starts when drawdown from rolling peak exceeds dd_threshold.
    A bear ends when price has risen trough_recovery_mult times from the trough
    (e.g., 2.0 = price doubles from trough). This handles 3x leveraged ETFs
    where peak-relative recovery is impossible after 99%+ drawdowns.

    Parameters
    ----------
    close : price array
    dates : date array
    dd_threshold : min peak-to-trough drop to qualify as bear (0.35 = 35%)
    trough_recovery_mult : price must reach trough * this to end bear (2.0 = double)
    min_duration : min bars from peak to trough
    """
    n = len(close)
    bears = []

    peak_idx = 0
    peak_price = close[0]
    in_bear = False
    bear_start_idx = 0
    trough_idx = 0
    trough_price = close[0]

    for i in range(1, n):
        if in_bear:
            # Track trough
            if close[i] < trough_price:
                trough_idx = i
                trough_price = close[i]

            # Bear ends when price rises enough FROM THE TROUGH
            if trough_price > 0 and close[i] >= trough_price * trough_recovery_mult:
                duration = trough_idx - bear_start_idx
                if duration >= min_duration:
                    bears.append({
                        "start_idx": bear_start_idx,
                        "end_idx": trough_idx,
                        "start_date": str(dates[bear_start_idx])[:10],
                        "end_date": str(dates[trough_idx])[:10],
                        "start_price": round(float(peak_price), 4),
                        "end_price": round(float(trough_price), 4),
                        "move_pct": round((trough_price / peak_price - 1) * 100, 1),
                    })
                # New uptrend — reset peak to current
                in_bear = False
                peak_idx = i
                peak_price = close[i]
        else:
            if close[i] > peak_price:
                peak_idx = i
                peak_price = close[i]
            else:
                drawdown = (peak_price - close[i]) / peak_price
                if drawdown >= dd_threshold:
                    in_bear = True
                    bear_start_idx = peak_idx
                    trough_idx = i
                    trough_price = close[i]

    # Record any bear still active at end of data
    if in_bear:
        duration = trough_idx - bear_start_idx
        if duration >= min_duration:
            bears.append({
                "start_idx": bear_start_idx,
                "end_idx": trough_idx,
                "start_date": str(dates[bear_start_idx])[:10],
                "end_date": str(dates[trough_idx])[:10],
                "start_price": round(float(peak_price), 4),
                "end_price": round(float(trough_price), 4),
                "move_pct": round((trough_price / peak_price - 1) * 100, 1),
            })

    return bears


def _detect_bulls(close: np.ndarray, dates: np.ndarray, bears: list[dict]) -> list[dict]:
    """Derive bull periods from the gaps between bears."""
    n = len(close)
    bulls = []

    prev_end_idx = 0
    for bear in bears:
        start_idx = bear["end_idx"]  # bull starts at previous bear trough
        # Skip if gap is too small
        if prev_end_idx > 0 and bear["start_idx"] - prev_end_idx < 5:
            prev_end_idx = bear["end_idx"]
            continue

        bull_start = prev_end_idx if prev_end_idx > 0 else 0
        bull_end = bear["start_idx"]

        if bull_end - bull_start >= 10:
            start_p = float(close[bull_start])
            end_p = float(close[bull_end])
            bulls.append({
                "start_idx": bull_start,
                "end_idx": bull_end,
                "start_date": str(dates[bull_start])[:10],
                "end_date": str(dates[bull_end])[:10],
                "start_price": round(start_p, 4),
                "end_price": round(end_p, 4),
                "move_pct": round((end_p / start_p - 1) * 100, 1) if start_p > 0 else 0,
            })

        prev_end_idx = bear["end_idx"]

    # Final bull from last bear trough to end of data
    if prev_end_idx < n - 10:
        start_p = float(close[prev_end_idx])
        end_p = float(close[-1])
        bulls.append({
            "start_idx": prev_end_idx,
            "end_idx": n - 1,
            "start_date": str(dates[prev_end_idx])[:10],
            "end_date": str(dates[-1])[:10],
            "start_price": round(start_p, 4),
            "end_price": round(end_p, 4),
            "move_pct": round((end_p / start_p - 1) * 100, 1) if start_p > 0 else 0,
        })

    return bulls


def build_regime_map(
    df: pd.DataFrame,
    dd_threshold: float = 0.35,
    trough_recovery_mult: float = 2.0,
    min_duration: int = 15,
) -> dict:
    """
    Detect all bull/bear cycles and return a structured regime map.

    Uses rolling-peak detection with trough-relative recovery,
    tuned for 3x leveraged ETFs where peak-relative recovery
    is impossible after extreme drawdowns.

    Returns dict with keys:
      bears: list of cycle dicts
      bulls: list of cycle dicts
      cycles: interleaved chronological list
      stats: summary statistics
    """
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values

    bears = _detect_drawdowns(close, dates, dd_threshold, trough_recovery_mult, min_duration)
    bulls = _detect_bulls(close, dates, bears)

    # Tag each with type
    for b in bears:
        b["type"] = "bear"
        d = (pd.Timestamp(b["end_date"]) - pd.Timestamp(b["start_date"])).days
        b["duration_days"] = d
        b["duration_months"] = round(d / 30.4, 1)

    for b in bulls:
        b["type"] = "bull"
        d = (pd.Timestamp(b["end_date"]) - pd.Timestamp(b["start_date"])).days
        b["duration_days"] = d
        b["duration_months"] = round(d / 30.4, 1)

    cycles = sorted(bears + bulls, key=lambda x: x["start_idx"])

    # Summary stats
    bear_durations = [b["duration_months"] for b in bears]
    bear_mags = [b["move_pct"] for b in bears]
    bull_durations = [b["duration_months"] for b in bulls]
    bull_mags = [b["move_pct"] for b in bulls]

    stats = {
        "total_years": round((pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days / 365.25, 1),
        "num_bears": len(bears),
        "num_bulls": len(bulls),
        "avg_bear_duration_months": round(np.mean(bear_durations), 1) if bear_durations else 0,
        "avg_bear_magnitude_pct": round(np.mean(bear_mags), 1) if bear_mags else 0,
        "avg_bull_duration_months": round(np.mean(bull_durations), 1) if bull_durations else 0,
        "avg_bull_magnitude_pct": round(np.mean(bull_mags), 1) if bull_mags else 0,
        "worst_bear_pct": round(min(bear_mags), 1) if bear_mags else 0,
        "best_bull_pct": round(max(bull_mags), 1) if bull_mags else 0,
    }

    return {
        "bears": bears,
        "bulls": bulls,
        "cycles": cycles,
        "stats": stats,
    }


def format_regime_map(regime_map: dict) -> str:
    """Format the regime map as a readable string for Claude."""
    s = regime_map["stats"]
    lines = []
    lines.append(f"TECL Regime Map ({s['total_years']} years)")
    lines.append("=" * 60)
    lines.append(f"{s['num_bears']} bear cycles | {s['num_bulls']} bull cycles\n")

    lines.append("BEAR CYCLES:")
    for i, b in enumerate(regime_map["bears"], 1):
        dur = f"{b['duration_months']:.0f} mo" if b["duration_months"] >= 1 else f"{b['duration_days']}d"
        lines.append(
            f"  #{i:2d}  {b['start_date']} → {b['end_date']}  ({dur:>6s})  {b['move_pct']:+.1f}%"
            f"  ${b['start_price']:.2f} → ${b['end_price']:.2f}"
        )

    lines.append(f"\n  Avg duration: {s['avg_bear_duration_months']:.1f} months")
    lines.append(f"  Avg magnitude: {s['avg_bear_magnitude_pct']:.1f}%")
    lines.append(f"  Worst: {s['worst_bear_pct']:.1f}%")

    lines.append("\nBULL CYCLES:")
    for i, b in enumerate(regime_map["bulls"], 1):
        dur = f"{b['duration_months']:.0f} mo" if b["duration_months"] >= 1 else f"{b['duration_days']}d"
        lines.append(
            f"  #{i:2d}  {b['start_date']} → {b['end_date']}  ({dur:>6s})  {b['move_pct']:+.1f}%"
            f"  ${b['start_price']:.2f} → ${b['end_price']:.2f}"
        )

    lines.append(f"\n  Avg duration: {s['avg_bull_duration_months']:.1f} months")
    lines.append(f"  Avg magnitude: {s['avg_bull_magnitude_pct']:.1f}%")
    lines.append(f"  Best: {s['best_bull_pct']:.1f}%")

    # Key observations (computed, not hardcoded)
    lines.append("\nKEY OBSERVATIONS:")
    if s["avg_bear_duration_months"] > 0:
        bull_bear_ratio = s["avg_bull_duration_months"] / s["avg_bear_duration_months"]
        if bull_bear_ratio > 1.5:
            lines.append(f"  - Bulls last {bull_bear_ratio:.1f}x longer than bears on average")
    if s["avg_bear_magnitude_pct"] != 0:
        mag_ratio = abs(s["avg_bull_magnitude_pct"]) / abs(s["avg_bear_magnitude_pct"])
        if mag_ratio > 2:
            lines.append(f"  - Bull gains are {mag_ratio:.0f}x larger than bear losses on average")
    lines.append(f"  - Implication: missing bull upside costs more than catching bear downside")
    lines.append(f"  - Strategy priority: maximize time IN market during bulls, accept some bear exposure")

    return "\n".join(lines)


if __name__ == "__main__":
    from data import get_tecl_data
    df = get_tecl_data()
    regime_map = build_regime_map(df)
    print(format_regime_map(regime_map))
