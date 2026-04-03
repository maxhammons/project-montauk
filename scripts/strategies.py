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
# Strategy 8: MFI Regime — Volume-weighted RSI analog
# MFI adds volume confirmation to RSI-style oversold/overbought signals.
# On TECL, volume spikes confirm regime shifts, so this may beat plain RSI.
# ─────────────────────────────────────────────────────────────────────────────

def mfi_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    mfi = ind.mfi(p.get("mfi_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 150))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_level = p.get("entry_mfi", 35)
    exit_level = p.get("exit_mfi", 80)
    panic_level = p.get("panic_mfi", 15)

    for i in range(1, n):
        if np.isnan(mfi[i]) or np.isnan(mfi[i-1]):
            continue

        # Entry: MFI crosses up through entry level + price above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        if mfi[i-1] < entry_level and mfi[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: MFI reaches overbought
        if mfi[i] >= exit_level:
            exits[i] = True
            labels[i] = "MFI Overbought"
            continue

        # Exit: MFI panic (capitulation sell)
        if mfi[i] < panic_level:
            exits[i] = True
            labels[i] = "MFI Panic"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 9: Williams %R Regime — Oversold recovery with trend filter
# WillR is more sensitive than RSI for price-channel-based signals.
# Entry: WillR recovers from deep oversold. Exit: WillR reaches overbought.
# ─────────────────────────────────────────────────────────────────────────────

def willr_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    willr = ind.willr(p.get("willr_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 150))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    # WillR ranges from -100 (oversold) to 0 (overbought)
    entry_level = p.get("entry_willr", -70)   # e.g. -70 = "was oversold"
    exit_level = p.get("exit_willr", -10)     # e.g. -10 = "overbought"
    panic_level = p.get("panic_willr", -90)   # extreme oversold = exit

    for i in range(1, n):
        if np.isnan(willr[i]) or np.isnan(willr[i-1]):
            continue

        # Entry: WillR crosses up through entry level + price above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        if willr[i-1] < entry_level and willr[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: WillR reaches overbought
        if willr[i] >= exit_level:
            exits[i] = True
            labels[i] = "WillR Overbought"
            continue

        # Exit: WillR extreme panic
        if willr[i] < panic_level:
            exits[i] = True
            labels[i] = "WillR Panic"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 10: Stochastic Regime — K/D crossover with trend filter
# Stochastic captures short-term mean reversion better in trending markets.
# Enter when Stoch K crosses D from oversold zone. Exit when overbought.
# ─────────────────────────────────────────────────────────────────────────────

def stoch_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    stoch_k = ind.stoch_k(p.get("stoch_len", 14), p.get("smooth_k", 3))
    stoch_d = ind.stoch_d(p.get("stoch_len", 14), p.get("smooth_k", 3), p.get("smooth_d", 3))
    trend_ema = ind.ema(p.get("trend_len", 150))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    oversold = p.get("oversold", 25)
    overbought = p.get("overbought", 80)

    for i in range(1, n):
        if np.isnan(stoch_k[i]) or np.isnan(stoch_d[i]) or np.isnan(stoch_k[i-1]) or np.isnan(stoch_d[i-1]):
            continue

        # Entry: K crosses above D from oversold zone + price above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        k_cross_up = stoch_k[i-1] <= stoch_d[i-1] and stoch_k[i] > stoch_d[i]
        was_oversold = stoch_k[i-1] < oversold or stoch_d[i-1] < oversold
        if k_cross_up and was_oversold and trend_ok:
            entries[i] = True

        # Exit: both K and D in overbought
        if stoch_k[i] >= overbought and stoch_d[i] >= overbought:
            exits[i] = True
            labels[i] = "Stoch Overbought"
            continue

        # Exit: K crosses below D from overbought zone
        k_cross_down = stoch_k[i-1] >= stoch_d[i-1] and stoch_k[i] < stoch_d[i]
        if k_cross_down and stoch_k[i-1] >= overbought:
            exits[i] = True
            labels[i] = "Stoch Cross Down"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 11: MACD Regime — Zero-line cross with trend anchor
# Based on Montauk 6.x heritage. MACD histogram zero-cross for regime shifts.
# Only enter in uptrend (price above long EMA). ATR exit for protection.
# ─────────────────────────────────────────────────────────────────────────────

def macd_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    macd_hist = ind.macd_hist(p.get("fast", 12), p.get("slow", 26), p.get("signal", 9))
    macd_line = ind.macd_line(p.get("fast", 12), p.get("slow", 26))
    trend_ema = ind.ema(p.get("trend_len", 200))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(macd_hist[i]) or np.isnan(macd_hist[i-1]) or np.isnan(macd_line[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: MACD histogram crosses zero from below + above trend EMA
        if macd_hist[i-1] < 0 and macd_hist[i] >= 0 and trend_ok:
            entries[i] = True

        # Exit: MACD line crosses below zero
        if macd_line[i] < 0:
            exits[i] = True
            labels[i] = "MACD Below Zero"
            continue

        # Exit: MACD histogram crosses zero from above (momentum fading)
        if macd_hist[i-1] >= 0 and macd_hist[i] < 0:
            exits[i] = True
            labels[i] = "MACD Hist Cross"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 12: ADX Trend — Only trade when trend is directionally strong
# ADX > threshold confirms a real trend. DI+/DI- gives direction.
# Designed to avoid the choppy sideways periods that kill leveraged ETFs.
# ─────────────────────────────────────────────────────────────────────────────

def adx_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    adx = ind.adx(p.get("adx_len", 14))
    di_plus = ind.di_plus(p.get("adx_len", 14))
    di_minus = ind.di_minus(p.get("adx_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    adx_thresh = p.get("adx_thresh", 25)

    for i in range(1, n):
        if np.isnan(adx[i]) or np.isnan(di_plus[i]) or np.isnan(di_minus[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        strong_trend = adx[i] > adx_thresh
        bull_direction = di_plus[i] > di_minus[i]

        # Entry: ADX shows strong trend + DI+ > DI- + above long EMA
        if strong_trend and bull_direction and trend_ok:
            entries[i] = True

        # Exit: DI- crosses above DI+ (bearish direction flip)
        if di_minus[i] > di_plus[i]:
            exits[i] = True
            labels[i] = "DI Bear Cross"
            continue

        # Exit: ADX drops below threshold (trend dying)
        if adx[i] < p.get("adx_exit", 20):
            exits[i] = True
            labels[i] = "ADX Weak"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 13: RSI + EMA Hybrid — RSI entry timing with EMA cross protection
# Combines the best of rsi_regime (precise entry timing) with montauk_821
# (EMA cross exit for trend protection). ATR as backstop.
# ─────────────────────────────────────────────────────────────────────────────

def rsi_ema_hybrid(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(p.get("rsi_len", 10))
    ema_s = ind.ema(p.get("short_ema", 15))
    ema_m = ind.ema(p.get("med_ema", 40))
    trend_ema = ind.ema(p.get("trend_len", 150))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_rsi = p.get("entry_rsi", 35)

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i-1]) or np.isnan(ema_s[i]) or np.isnan(ema_m[i]):
            continue

        # Entry: RSI recovery from oversold + EMA trend aligned + price above anchor
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        ema_aligned = ema_s[i] > ema_m[i]
        rsi_recovery = rsi[i-1] < entry_rsi and rsi[i] >= entry_rsi

        if rsi_recovery and trend_ok:
            entries[i] = True

        # Exit: EMA cross (short below med)
        if ema_s[i] < ema_m[i] * (1 - p.get("ema_buffer", 0.3) / 100):
            exits[i] = True
            labels[i] = "EMA Cross"
            continue

        # Exit: RSI extreme (overbought exit)
        if rsi[i] >= p.get("exit_rsi", 80):
            exits[i] = True
            labels[i] = "RSI Overbought"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 14: CCI Regime — Commodity Channel Index oversold recovery
# CCI has wider range than RSI (-300 to +300), may catch extremes better.
# Enter on CCI recovery past -100. Exit on CCI overbought above +200.
# ─────────────────────────────────────────────────────────────────────────────

def cci_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    cci = ind.cci(p.get("cci_len", 20))
    trend_ema = ind.ema(p.get("trend_len", 150))
    atr_vals = ind.atr(p.get("atr_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_level = p.get("entry_cci", -100)
    exit_level = p.get("exit_cci", 200)
    panic_level = p.get("panic_cci", -200)

    for i in range(1, n):
        if np.isnan(cci[i]) or np.isnan(cci[i-1]):
            continue

        # Entry: CCI crosses up through entry level + above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        if cci[i-1] < entry_level and cci[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: CCI reaches overbought
        if cci[i] >= exit_level:
            exits[i] = True
            labels[i] = "CCI Overbought"
            continue

        # Exit: CCI panic capitulation
        if cci[i] < panic_level:
            exits[i] = True
            labels[i] = "CCI Panic"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 15: Volatility Regime — Enter in low-vol uptrends, exit on vol spikes
# TECL bull runs often begin with volatility compression. When realized vol
# drops below its own moving average while price is trending up = entry.
# When vol spikes (bear signal) = exit. Adds ATR shock as backstop.
# ─────────────────────────────────────────────────────────────────────────────

def volatility_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))
    atr_slow = ind.atr(p.get("atr_slow", 60))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    vol_smooth = p.get("vol_smooth", 20)
    # Use ATR as volatility proxy; smooth it for the regime signal
    atr_smooth = _ema_helper(atr_vals, vol_smooth)

    for i in range(vol_smooth + 1, n):
        if np.isnan(atr_vals[i]) or np.isnan(atr_smooth[i]) or np.isnan(trend_ema[i]):
            continue

        # Vol ratio: current ATR vs smoothed ATR
        vol_ratio = atr_vals[i] / atr_smooth[i] if atr_smooth[i] > 0 else 1.0
        price_above_trend = cl[i] > trend_ema[i]
        low_vol = vol_ratio < p.get("low_vol_thresh", 0.9)

        # Entry: volatility compressed + price in uptrend
        if low_vol and price_above_trend:
            entries[i] = True

        # Exit: volatility spikes (regime change warning)
        if vol_ratio > p.get("vol_spike_thresh", 1.5):
            exits[i] = True
            labels[i] = "Vol Spike"
            continue

        # Exit: price falls below trend EMA (trend broken)
        if cl[i] < trend_ema[i] * (1 - p.get("trend_buffer", 0.02)):
            exits[i] = True
            labels[i] = "Trend Break"
            continue

        # Exit: ATR shock (sudden large move)
        if i >= 1 and not np.isnan(atr_slow[i]):
            if cl[i] < cl[i-1] - atr_slow[i] * p.get("atr_mult", 3.0):
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
    "mfi_regime":         mfi_regime,
    "willr_regime":       willr_regime,
    "stoch_regime":       stoch_regime,
    "macd_regime":        macd_regime,
    "adx_trend":          adx_trend,
    "rsi_ema_hybrid":     rsi_ema_hybrid,
    "cci_regime":         cci_regime,
    "volatility_regime":  volatility_regime,
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
    "mfi_regime": {
        "mfi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_mfi": (20, 45, 5, float), "exit_mfi": (70, 90, 5, float),
        "panic_mfi": (10, 25, 5, float), "atr_period": (20, 60, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "willr_regime": {
        "willr_len": (7, 28, 3, int), "trend_len": (50, 200, 25, int),
        "entry_willr": (-85, -50, 5, float), "exit_willr": (-20, -5, 5, float),
        "panic_willr": (-98, -85, 5, float), "cooldown": (0, 20, 5, int),
    },
    "stoch_regime": {
        "stoch_len": (7, 21, 2, int), "smooth_k": (1, 5, 1, int),
        "smooth_d": (1, 5, 1, int), "trend_len": (50, 200, 25, int),
        "oversold": (15, 35, 5, float), "overbought": (70, 90, 5, float),
        "atr_period": (20, 60, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "macd_regime": {
        "fast": (5, 20, 3, int), "slow": (15, 50, 5, int), "signal": (5, 15, 2, int),
        "trend_len": (100, 300, 50, int), "atr_period": (20, 60, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "adx_trend": {
        "adx_len": (7, 28, 3, int), "adx_thresh": (15, 35, 5, float),
        "adx_exit": (10, 25, 5, float), "trend_len": (50, 200, 25, int),
        "atr_period": (20, 60, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "rsi_ema_hybrid": {
        "rsi_len": (7, 21, 2, int), "short_ema": (5, 25, 5, int),
        "med_ema": (20, 80, 10, int), "trend_len": (75, 250, 25, int),
        "entry_rsi": (25, 45, 5, float), "exit_rsi": (70, 90, 5, float),
        "ema_buffer": (0.0, 1.0, 0.2, float), "atr_period": (20, 60, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 15, 3, int),
    },
    "cci_regime": {
        "cci_len": (10, 40, 5, int), "trend_len": (50, 200, 25, int),
        "entry_cci": (-150, -50, 25, float), "exit_cci": (100, 300, 50, float),
        "panic_cci": (-300, -150, 50, float), "atr_period": (20, 60, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "volatility_regime": {
        "trend_len": (50, 200, 25, int), "atr_period": (10, 30, 5, int),
        "atr_slow": (40, 100, 20, int), "vol_smooth": (10, 40, 5, int),
        "low_vol_thresh": (0.6, 1.0, 0.1, float), "vol_spike_thresh": (1.2, 2.5, 0.3, float),
        "trend_buffer": (0.01, 0.05, 0.01, float), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
}
