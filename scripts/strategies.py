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
# Strategy 8: MACD Zero Cross — Enter when MACD line crosses above zero,
# exit when it crosses below. Catches momentum regime shifts cleanly.
# ─────────────────────────────────────────────────────────────────────────────

def macd_zero_cross(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    fast = p.get("macd_fast", 12)
    slow = p.get("macd_slow", 26)
    sig = p.get("macd_sig", 9)
    macd = ind.macd_line(fast, slow)
    signal = ind.macd_signal(fast, slow, sig)
    hist = ind.macd_hist(fast, slow, sig)
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(macd[i]) or np.isnan(macd[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: MACD crosses above zero + above trend
        if macd[i-1] < 0 and macd[i] >= 0 and trend_ok:
            entries[i] = True

        # Exit: MACD crosses below zero
        if macd[i-1] >= 0 and macd[i] < 0:
            exits[i] = True
            labels[i] = "MACD Cross Zero"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 9: DMI Trend — Enter on ADX strength + DI+ dominance
# ADX measures trend strength; high ADX + DI+ > DI- = strong bull regime
# ─────────────────────────────────────────────────────────────────────────────

def dmi_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    adx_len = p.get("adx_len", 14)
    adx = ind.adx(adx_len)
    di_plus = ind.di_plus(adx_len)
    di_minus = ind.di_minus(adx_len)
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    adx_thresh = p.get("adx_thresh", 25.0)
    di_margin = p.get("di_margin", 5.0)

    for i in range(1, n):
        if np.isnan(adx[i]) or np.isnan(di_plus[i]) or np.isnan(di_minus[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        strong_trend = adx[i] > adx_thresh
        bull_direction = di_plus[i] > di_minus[i] + di_margin

        # Entry: strong trend + bullish direction + above trend EMA
        entries[i] = strong_trend and bull_direction and trend_ok

        # Exit: DI- dominates
        if di_minus[i] > di_plus[i] + di_margin * 0.5:
            exits[i] = True
            labels[i] = "DI- Dominant"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 10: ROC Momentum — Enter when Rate of Change exceeds threshold,
# exit when momentum stalls. ROC directly measures pace of price change.
# ─────────────────────────────────────────────────────────────────────────────

def roc_momentum(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    roc = ind.roc(p.get("roc_len", 20))
    roc_smooth = _ema_helper(roc, p.get("roc_smooth", 5))
    trend_ema = ind.ema(p.get("trend_len", 80))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_thresh = p.get("entry_roc", 5.0)
    exit_thresh = p.get("exit_roc", -2.0)

    for i in range(1, n):
        if np.isnan(roc_smooth[i]) or np.isnan(roc_smooth[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: smoothed ROC crosses above threshold + trend OK
        if roc_smooth[i-1] < entry_thresh and roc_smooth[i] >= entry_thresh and trend_ok:
            entries[i] = True

        # Exit: ROC drops below exit threshold
        if roc_smooth[i] < exit_thresh:
            exits[i] = True
            labels[i] = "ROC Fade"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 11: Composite Momentum — Combine RSI + MACD hist + ROC into a
# single score. Enter when composite is positive and rising, exit on reversal.
# Similar to the Montauk Composite Oscillator indicator but used for entries.
# ─────────────────────────────────────────────────────────────────────────────

def composite_momentum(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    # RSI normalized to -1..+1
    rsi = ind.rsi(p.get("rsi_len", 14))
    rsi_norm = (rsi - 50.0) / 50.0  # -1 to +1

    # MACD histogram normalized by ATR
    fast = p.get("macd_fast", 12)
    slow_m = p.get("macd_slow", 26)
    sig = p.get("macd_sig", 9)
    hist = ind.macd_hist(fast, slow_m, sig)
    atr_vals = ind.atr(p.get("atr_period", 20))
    hist_norm = np.where(atr_vals > 0, hist / atr_vals, 0.0)
    hist_norm = np.clip(hist_norm, -2.0, 2.0) / 2.0  # -1 to +1

    # ROC normalized
    roc = ind.roc(p.get("roc_len", 10))
    roc_norm = np.tanh(roc / p.get("roc_scale", 10.0))  # -1 to +1

    trend_ema = ind.ema(p.get("trend_len", 100))

    w_rsi = p.get("w_rsi", 0.3)
    w_hist = p.get("w_hist", 0.4)
    w_roc = p.get("w_roc", 0.3)

    composite = w_rsi * rsi_norm + w_hist * hist_norm + w_roc * roc_norm
    comp_smooth = _ema_helper(composite, p.get("smooth_len", 3))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_level = p.get("entry_level", 0.1)
    exit_level = p.get("exit_level", -0.1)

    for i in range(1, n):
        if np.isnan(comp_smooth[i]) or np.isnan(comp_smooth[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: composite crosses above entry level + trend
        if comp_smooth[i-1] < entry_level and comp_smooth[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: composite drops below exit level
        if comp_smooth[i] < exit_level:
            exits[i] = True
            labels[i] = "Composite Drop"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 12: Donchian Trend — Enter on upper channel breakout,
# exit on middle line cross. Turtle-trading style regime entry.
# ─────────────────────────────────────────────────────────────────────────────

def donchian_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    entry_len = p.get("entry_len", 55)
    exit_len = p.get("exit_len", 20)

    don_hi_entry = ind.donchian_upper(entry_len)
    don_mid_exit = ind.donchian_mid(exit_len)
    don_lo_exit = ind.donchian_lower(exit_len)
    atr_vals = ind.atr(p.get("atr_period", 20))
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(don_hi_entry[i]) or np.isnan(don_hi_entry[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: price breaks above N-day high (Turtle entry)
        if cl[i] >= don_hi_entry[i-1] and trend_ok:
            entries[i] = True

        # Exit: price drops below mid of shorter channel
        if not np.isnan(don_mid_exit[i]) and cl[i] < don_mid_exit[i]:
            exits[i] = True
            labels[i] = "Below Mid"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 13: Keltner + RSI Filter — Enter when price breaks above Keltner
# channel with RSI confirmation. Combines volatility expansion with momentum.
# ─────────────────────────────────────────────────────────────────────────────

def keltner_rsi(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    ema_len = p.get("ema_len", 20)
    atr_len = p.get("atr_len", 10)
    mult = p.get("kelt_mult", 2.0)

    kelt_upper = ind.keltner_upper(ema_len, atr_len, mult)
    kelt_lower = ind.keltner_lower(ema_len, atr_len, mult)
    ema_mid = ind.ema(ema_len)
    rsi = ind.rsi(p.get("rsi_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(kelt_upper[i]) or np.isnan(rsi[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        rsi_ok = rsi[i] > p.get("rsi_min", 50)

        # Entry: price above upper Keltner + RSI confirming momentum + trend
        if cl[i] > kelt_upper[i] and rsi_ok and trend_ok:
            entries[i] = True

        # Exit: price drops below EMA midline
        if not np.isnan(ema_mid[i]) and cl[i] < ema_mid[i]:
            exits[i] = True
            labels[i] = "Below EMA Mid"
            continue

        # Exit: RSI drops below exit level
        if rsi[i] < p.get("rsi_exit", 40):
            exits[i] = True
            labels[i] = "RSI Exit"
            continue

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
    "montauk_821":        montauk_821,
    "golden_cross":       golden_cross,
    "rsi_regime":         rsi_regime,
    "breakout":           breakout,
    "bollinger_squeeze":  bollinger_squeeze,
    "trend_stack":        trend_stack,
    "tema_momentum":      tema_momentum,
    "macd_zero_cross":    macd_zero_cross,
    "dmi_trend":          dmi_trend,
    "roc_momentum":       roc_momentum,
    "composite_momentum": composite_momentum,
    "donchian_trend":     donchian_trend,
    "keltner_rsi":        keltner_rsi,
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
    "macd_zero_cross": {
        "macd_fast": (8, 20, 2, int), "macd_slow": (20, 40, 4, int),
        "macd_sig": (5, 15, 2, int), "trend_len": (50, 200, 25, int),
        "atr_period": (10, 50, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "dmi_trend": {
        "adx_len": (7, 28, 7, int), "adx_thresh": (15.0, 35.0, 5.0, float),
        "di_margin": (2.0, 15.0, 2.0, float), "trend_len": (50, 200, 25, int),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "roc_momentum": {
        "roc_len": (10, 40, 5, int), "roc_smooth": (3, 15, 2, int),
        "trend_len": (50, 200, 25, int), "entry_roc": (2.0, 15.0, 2.0, float),
        "exit_roc": (-8.0, 0.0, 2.0, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "composite_momentum": {
        "rsi_len": (7, 21, 7, int), "macd_fast": (8, 16, 4, int),
        "macd_slow": (20, 32, 4, int), "macd_sig": (7, 13, 3, int),
        "roc_len": (5, 20, 5, int), "roc_scale": (5.0, 20.0, 5.0, float),
        "trend_len": (50, 200, 50, int), "smooth_len": (2, 8, 2, int),
        "entry_level": (0.0, 0.3, 0.1, float), "exit_level": (-0.3, 0.0, 0.1, float),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "donchian_trend": {
        "entry_len": (30, 90, 10, int), "exit_len": (10, 40, 5, int),
        "trend_len": (50, 200, 25, int), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "keltner_rsi": {
        "ema_len": (10, 40, 5, int), "atr_len": (5, 20, 5, int),
        "kelt_mult": (1.0, 3.0, 0.5, float), "rsi_len": (7, 21, 7, int),
        "trend_len": (50, 200, 25, int), "rsi_min": (40, 65, 5, float),
        "rsi_exit": (25, 50, 5, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
}
