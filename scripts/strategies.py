#!/usr/bin/env python3
"""
Strategy library for Project Montauk.

Each strategy is a function that takes Indicators + params dict,
and returns (entries, exits, exit_labels) as numpy boolean/string arrays.

To add a new strategy:
  1. Write a function with signature: (ind: Indicators, p: dict) -> tuple
  2. Add it to STRATEGY_REGISTRY at the bottom
  3. Define its parameter space in STRATEGY_PARAMS

The optimizer will test all registered strategies and all parameter combos.
"""

from __future__ import annotations
import numpy as np
from strategy_engine import Indicators


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1: Montauk 8.2.1 — EMA cross with layered exits
# The current production strategy. Baseline to beat.
# ─────────────────────────────────────────────────────────────────────────────

def montauk_821(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    hi = ind.high
    lo = ind.low
    vol = ind.volume

    ema_s = ind.ema(p.get("short_ema", 15))
    ema_m = ind.ema(p.get("med_ema", 30))
    ema_trend = ind.ema(p.get("trend_ema", 70))
    atr_vals = ind.atr(p.get("atr_period", 40))
    quick_ema = ind.ema(p.get("quick_ema", 15))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    slope_lb = p.get("slope_lookback", 10)

    for i in range(max(slope_lb, p.get("quick_lookback", 5)) + 1, n):
        if np.isnan(ema_s[i]) or np.isnan(ema_m[i]):
            continue

        # Entry: short > med + trend slope positive
        trend_ok = True
        if not np.isnan(ema_trend[i]) and not np.isnan(ema_trend[i - slope_lb]):
            trend_slope = (ema_trend[i] - ema_trend[i - slope_lb]) / slope_lb
            trend_ok = trend_slope > 0

        entries[i] = (ema_s[i] > ema_m[i]) and trend_ok

        # Exit 1: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"
                continue

        # Exit 2: Quick EMA momentum drop
        qlb = p.get("quick_lookback", 5)
        if not np.isnan(quick_ema[i]) and not np.isnan(quick_ema[i - qlb]) and quick_ema[i - qlb] != 0:
            delta = (quick_ema[i] - quick_ema[i - qlb]) / quick_ema[i - qlb] * 100
            if delta <= p.get("quick_thresh", -8.2):
                exits[i] = True
                labels[i] = "Quick EMA"
                continue

        # Exit 3: EMA cross (short < med)
        if ema_s[i] < ema_m[i] * (1 - p.get("sell_buffer", 0.2) / 100):
            exits[i] = True
            labels[i] = "EMA Cross"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2: Golden/Death Cross — Simple long-term moving average crossover
# Classic approach: buy when 50 SMA > 200 SMA, sell when it crosses under
# ─────────────────────────────────────────────────────────────────────────────

def golden_cross(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    fast = ind.sma(p.get("fast_len", 50))
    slow = ind.sma(p.get("slow_len", 200))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i-1]) or np.isnan(slow[i-1]):
            continue
        # Golden cross: fast crosses above slow
        if fast[i-1] <= slow[i-1] and fast[i] > slow[i]:
            entries[i] = True
        # Death cross: fast crosses below slow
        if fast[i-1] >= slow[i-1] and fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "Death Cross"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 3: RSI Regime — Enter on oversold recovery, exit on overbought
# Leveraged ETFs tend to mean-revert hard — this exploits that
# ─────────────────────────────────────────────────────────────────────────────

def rsi_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    rsi = ind.rsi(p.get("rsi_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    cl = ind.close

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_level = p.get("entry_rsi", 35)
    exit_level = p.get("exit_rsi", 75)

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i-1]):
            continue

        # Entry: RSI crosses up through entry level + price above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        if rsi[i-1] < entry_level and rsi[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: RSI reaches overbought
        if rsi[i] >= exit_level:
            exits[i] = True
            labels[i] = "RSI Overbought"

        # Exit: RSI crashes below extreme
        if rsi[i] < p.get("panic_rsi", 20):
            exits[i] = True
            labels[i] = "RSI Panic"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 4: Breakout — Enter on new highs, exit on trailing drop
# Ride the momentum of new highs, bail when the move fades
# ─────────────────────────────────────────────────────────────────────────────

def breakout(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    lookback = p.get("lookback", 60)
    h = ind.highest(lookback)
    atr_vals = ind.atr(p.get("atr_period", 20))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    peak_since_entry = np.nan
    trail_pct = p.get("trail_pct", 20)

    for i in range(1, n):
        if np.isnan(h[i]):
            continue

        # Entry: close makes new N-bar high
        if cl[i] >= h[i] * p.get("breakout_pct", 0.98):
            entries[i] = True

        # Track peak and trailing stop
        if not np.isnan(peak_since_entry):
            peak_since_entry = max(peak_since_entry, cl[i])
            if cl[i] < peak_since_entry * (1 - trail_pct / 100):
                exits[i] = True
                labels[i] = "Trail Stop"
                peak_since_entry = np.nan
                continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"
                peak_since_entry = np.nan
                continue

        # Reset peak tracking on entry
        if entries[i]:
            peak_since_entry = cl[i]

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 5: Bollinger Squeeze — Enter when volatility expands from compression
# Low vol → high vol breakout. Common regime change signal.
# ─────────────────────────────────────────────────────────────────────────────

def bollinger_squeeze(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    bb_len = p.get("bb_len", 20)
    sma = ind.sma(bb_len)
    std = ind.stddev(bb_len)
    width = np.where(sma > 0, 2 * std / sma, np.nan)
    width_sma = _ema_helper(width, p.get("width_smooth", 20))

    ema_trend = ind.ema(p.get("trend_len", 50))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(2, n):
        if np.isnan(width[i]) or np.isnan(width_sma[i]) or np.isnan(width[i-1]):
            continue

        # Entry: width was below average (squeeze) and is now expanding + price above SMA
        was_squeezed = width[i-1] < width_sma[i-1] * p.get("squeeze_mult", 0.8)
        expanding = width[i] > width[i-1]
        above_mid = cl[i] > sma[i] if not np.isnan(sma[i]) else True
        trend_ok = np.isnan(ema_trend[i]) or cl[i] > ema_trend[i]

        if was_squeezed and expanding and above_mid and trend_ok:
            entries[i] = True

        # Exit: width contracts back below average (momentum fading)
        if width[i] < width_sma[i] * p.get("exit_squeeze_mult", 0.6) and cl[i] < sma[i]:
            exits[i] = True
            labels[i] = "Squeeze Fade"

        # Exit: price drops below lower band
        lower = sma[i] - 2 * std[i] if not np.isnan(std[i]) else np.nan
        if not np.isnan(lower) and cl[i] < lower:
            exits[i] = True
            labels[i] = "Below BB"

    return entries, exits, labels


def _ema_helper(series, length):
    """Local EMA helper for array inputs that may contain NaN."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    alpha = 2.0 / (length + 1)
    valid = ~np.isnan(series)
    started = False
    for i in range(len(series)):
        if not valid[i]:
            continue
        if not started:
            out[i] = series[i]
            started = True
        else:
            out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 6: Trend Following — Multiple timeframe EMA alignment
# Only in when ALL EMAs are stacked bullish. Out the moment any break.
# ─────────────────────────────────────────────────────────────────────────────

def trend_stack(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    e1 = ind.ema(p.get("fast_ema", 10))
    e2 = ind.ema(p.get("mid_ema", 30))
    e3 = ind.ema(p.get("slow_ema", 60))
    e4 = ind.ema(p.get("anchor_ema", 120))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        vals = [e1[i], e2[i], e3[i], e4[i]]
        if any(np.isnan(v) for v in vals):
            continue

        # All EMAs stacked: fast > mid > slow > anchor
        stacked = e1[i] > e2[i] > e3[i] > e4[i]
        entries[i] = stacked

        # Exit when stack breaks (any EMA out of order)
        if not stacked:
            exits[i] = True
            labels[i] = "Stack Break"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 7: TEMA Momentum — Enter on TEMA slope positive, exit on reversal
# Triple EMA is faster than regular EMA, good for catching regime shifts
# ─────────────────────────────────────────────────────────────────────────────

def tema_momentum(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    tema_vals = ind.tema(p.get("tema_len", 50))
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 40))
    lb = p.get("slope_lookback", 5)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(lb + 1, n):
        if np.isnan(tema_vals[i]) or np.isnan(tema_vals[i - lb]):
            continue

        slope = (tema_vals[i] - tema_vals[i - lb]) / lb
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: TEMA slope positive + above trend
        if slope > p.get("min_slope", 0) and trend_ok:
            entries[i] = True

        # Exit: TEMA slope turns negative
        if slope < -p.get("exit_slope", 0):
            exits[i] = True
            labels[i] = "TEMA Reversal"

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Registry — all strategies the optimizer can test
# ─────────────────────────────────────────────────────────────────────────────

STRATEGY_REGISTRY = {
    "montauk_821":      montauk_821,
    "golden_cross":     golden_cross,
    "rsi_regime":       rsi_regime,
    "breakout":         breakout,
    "bollinger_squeeze": bollinger_squeeze,
    "trend_stack":      trend_stack,
    "tema_momentum":    tema_momentum,
}

# Brief descriptions for leaderboard context — Claude reads these to understand
# what each strategy does without re-reading the full source code.
# UPDATE THIS when adding or modifying strategies.
STRATEGY_DESCRIPTIONS = {
    "montauk_821": (
        "EMA crossover (short > med) with trend slope filter. "
        "Exits: ATR shock (price drops > N*ATR), quick EMA momentum drop "
        "(% change over lookback), EMA cross reversal. Current production baseline."
    ),
    "golden_cross": (
        "Classic SMA crossover: buy when fast SMA crosses above slow SMA, "
        "sell on death cross. Simple, low-frequency, trend-following."
    ),
    "rsi_regime": (
        "Enter when RSI crosses up through entry level while price is above "
        "trend EMA. Exit on RSI overbought or RSI panic (extreme low). "
        "Exploits mean-reversion in leveraged ETFs."
    ),
    "breakout": (
        "Enter on new N-bar high (close near highest high). "
        "Exit via trailing stop (% from peak) or ATR shock. Momentum rider."
    ),
    "bollinger_squeeze": (
        "Enter when Bollinger Band width expands from below-average squeeze, "
        "with price above SMA and trend EMA. Exit when width contracts back "
        "or price drops below lower band. Volatility breakout."
    ),
    "trend_stack": (
        "Enter when 4 EMAs are perfectly stacked (fast > mid > slow > anchor). "
        "Exit the moment any EMA breaks the stack order. Pure trend alignment."
    ),
    "tema_momentum": (
        "Enter when TEMA slope is positive and price is above trend EMA. "
        "Exit when TEMA slope turns negative or ATR shock. "
        "TEMA reacts faster than EMA to regime changes."
    ),
}

# Parameter spaces for each strategy: {param: (min, max, step, type)}
STRATEGY_PARAMS = {
    "montauk_821": {
        "short_ema": (5, 25, 2, int), "med_ema": (15, 60, 5, int),
        "trend_ema": (30, 120, 10, int), "slope_lookback": (3, 20, 2, int),
        "atr_period": (10, 60, 5, int), "atr_mult": (1.5, 5.0, 0.5, float),
        "quick_ema": (3, 25, 2, int), "quick_lookback": (2, 10, 1, int),
        "quick_thresh": (-15.0, -3.0, 1.0, float), "sell_buffer": (0.0, 1.0, 0.2, float),
        "cooldown": (0, 10, 1, int),
    },
    "golden_cross": {
        "fast_len": (20, 100, 10, int), "slow_len": (100, 400, 25, int),
        "cooldown": (0, 20, 5, int),
    },
    "rsi_regime": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 45, 5, float), "exit_rsi": (65, 85, 5, float),
        "panic_rsi": (15, 30, 5, float), "cooldown": (0, 20, 5, int),
    },
    "breakout": {
        "lookback": (20, 120, 10, int), "breakout_pct": (0.90, 1.0, 0.02, float),
        "trail_pct": (10, 35, 5, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "bollinger_squeeze": {
        "bb_len": (15, 40, 5, int), "width_smooth": (10, 40, 5, int),
        "trend_len": (30, 100, 10, int), "squeeze_mult": (0.5, 1.0, 0.1, float),
        "exit_squeeze_mult": (0.3, 0.8, 0.1, float), "cooldown": (0, 20, 5, int),
    },
    "trend_stack": {
        "fast_ema": (5, 20, 5, int), "mid_ema": (20, 50, 5, int),
        "slow_ema": (40, 80, 10, int), "anchor_ema": (80, 200, 20, int),
        "cooldown": (0, 20, 5, int),
    },
    "tema_momentum": {
        "tema_len": (20, 100, 10, int), "trend_len": (50, 200, 25, int),
        "slope_lookback": (3, 15, 2, int), "min_slope": (0.0, 1.0, 0.2, float),
        "exit_slope": (0.0, 1.0, 0.2, float), "atr_period": (20, 60, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
}
