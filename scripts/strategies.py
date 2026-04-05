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
# Strategy 8: ADX Regime — Directional strength trend filter
# Enter when DI+ > DI- and ADX is rising (trend strengthening).
# Exit when DI- overtakes or ADX collapses below threshold.
# Designed to stay in only when trend is confirmed and accelerating.
# ─────────────────────────────────────────────────────────────────────────────

def adx_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    adx = ind.adx(p.get("adx_len", 14))
    dip = ind.di_plus(p.get("adx_len", 14))
    dim = ind.di_minus(p.get("adx_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))
    adx_min = p.get("adx_min", 20.0)
    adx_rise_lb = p.get("adx_rise_lb", 5)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(adx_rise_lb + 1, n):
        if np.isnan(adx[i]) or np.isnan(dip[i]) or np.isnan(dim[i]):
            continue

        adx_rising = adx[i] > adx[i - adx_rise_lb]
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: DI+ > DI- with ADX above floor and rising
        entries[i] = dip[i] > dim[i] and adx[i] >= adx_min and adx_rising and trend_ok

        # Exit: DI- crosses above DI+ (bearish) or ADX collapses
        if dim[i] > dip[i] * (1 + p.get("di_buffer", 0.05)):
            exits[i] = True
            labels[i] = "DI- Cross"
            continue

        if adx[i] < p.get("adx_exit", 15.0):
            exits[i] = True
            labels[i] = "ADX Weak"
            continue

        # ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 9: MACD Recovery — Enter on first positive MACD hist after deep trough
# TECL corrections send MACD deeply negative; the first zero-cross back up
# marks the start of new bull legs. Uses trend filter to avoid whipsaws.
# ─────────────────────────────────────────────────────────────────────────────

def macd_recovery(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    fast = p.get("macd_fast", 12)
    slow = p.get("macd_slow", 26)
    sig = p.get("macd_sig", 9)
    hist = ind.macd_hist(fast, slow, sig)
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))
    deep_neg = p.get("deep_neg", -0.5)   # hist must have been this negative to qualify

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    lookback = p.get("lookback", 20)

    for i in range(lookback + 1, n):
        if np.isnan(hist[i]) or np.isnan(hist[i-1]):
            continue

        # Check if hist was deeply negative recently
        window = hist[max(0, i - lookback):i]
        was_deep = np.any(window[~np.isnan(window)] < deep_neg)

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: crossing above zero after deep negative territory
        if hist[i-1] <= 0 and hist[i] > 0 and was_deep and trend_ok:
            entries[i] = True

        # Exit: hist crosses back below zero
        if hist[i] < p.get("exit_neg", -0.1):
            exits[i] = True
            labels[i] = "MACD Negative"
            continue

        # ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 10: Donchian Regime — Long-term channel breakout / breakdown
# Buy when close breaks above the N-bar Donchian upper channel.
# Sell when close falls below M-bar Donchian lower channel.
# Captures persistent trends; fewer but larger trades.
# ─────────────────────────────────────────────────────────────────────────────

def donchian_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    entry_len = p.get("entry_len", 60)
    exit_len = p.get("exit_len", 20)
    don_upper = ind.donchian_upper(entry_len)
    don_lower = ind.donchian_lower(exit_len)
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(don_upper[i]) or np.isnan(don_lower[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: close breaks above N-bar Donchian upper
        if cl[i] > don_upper[i-1] and trend_ok:
            entries[i] = True

        # Exit: close falls below M-bar Donchian lower
        if cl[i] < don_lower[i]:
            exits[i] = True
            labels[i] = "Donchian Break"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 11: Recovery Momentum — Crash + bounce pattern
# TECL specifc: detect that price fell hard from a peak then enter when
# it has confirmed a recovery (bounced N% above the trough).
# Exploits TECL's pattern of explosive recoveries after crashes.
# ─────────────────────────────────────────────────────────────────────────────

def recovery_momentum(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    atr_vals = ind.atr(p.get("atr_period", 20))
    trend_ema = ind.ema(p.get("trend_len", 80))

    crash_pct = p.get("crash_pct", 30.0)    # min peak-to-trough drop to qualify
    bounce_pct = p.get("bounce_pct", 10.0)  # min trough-to-now rise to enter
    peak_lb = p.get("peak_lb", 60)          # how far back to look for peak

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    quick_ema = ind.ema(p.get("quick_ema", 15))
    quick_lb = p.get("quick_lb", 5)

    for i in range(peak_lb + quick_lb + 1, n):
        if np.isnan(cl[i]):
            continue

        window = cl[max(0, i - peak_lb):i]
        peak = np.nanmax(window)
        trough = np.nanmin(window)

        # Ensure peak happened before trough
        peak_idx_local = np.nanargmax(window)
        trough_idx_local = np.nanargmin(window)
        if peak_idx_local >= trough_idx_local:
            # Trough is before peak — no crash pattern
            crash_ok = False
        else:
            crash_ok = peak > 0 and (peak - trough) / peak * 100 >= crash_pct

        bounce_ok = trough > 0 and (cl[i] - trough) / trough * 100 >= bounce_pct
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        entries[i] = crash_ok and bounce_ok and trend_ok

        # Exit: quick EMA momentum collapses
        if not np.isnan(quick_ema[i]) and not np.isnan(quick_ema[i - quick_lb]) and quick_ema[i - quick_lb] != 0:
            delta = (quick_ema[i] - quick_ema[i - quick_lb]) / quick_ema[i - quick_lb] * 100
            if delta <= p.get("quick_thresh", -8.0):
                exits[i] = True
                labels[i] = "Momentum Drop"
                continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 12: Composite Regime Score — Normalized multi-indicator regime signal
# Inspired by the Montauk Composite Oscillator indicator.
# Score = weighted avg of RSI, TEMA slope, and MACD hist (all normalized -1..+1)
# Enter when score crosses above positive threshold, exit when it drops below.
# ─────────────────────────────────────────────────────────────────────────────

def composite_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(p.get("rsi_len", 14))
    tema = ind.tema(p.get("tema_len", 50))
    fast = p.get("macd_fast", 12)
    slow_m = p.get("macd_slow", 26)
    sig_m = p.get("macd_sig", 9)
    hist = ind.macd_hist(fast, slow_m, sig_m)
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))
    tema_lb = p.get("tema_lb", 5)

    w_rsi = p.get("w_rsi", 0.4)
    w_tema = p.get("w_tema", 0.4)
    w_macd = p.get("w_macd", 0.2)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_thresh = p.get("entry_thresh", 0.2)
    exit_thresh = p.get("exit_thresh", -0.1)

    scores = np.full(n, np.nan)

    for i in range(tema_lb + 1, n):
        # Normalize RSI: (rsi - 50) / 50 → -1..+1
        rsi_norm = (rsi[i] - 50.0) / 50.0 if not np.isnan(rsi[i]) else 0.0

        # Normalize TEMA slope: tanh of scaled slope
        if not np.isnan(tema[i]) and not np.isnan(tema[i - tema_lb]) and tema[i - tema_lb] != 0:
            raw_slope = (tema[i] - tema[i - tema_lb]) / tema[i - tema_lb] * 100
            tema_norm = float(np.tanh(raw_slope / 2.0))
        else:
            tema_norm = 0.0

        # Normalize MACD hist: tanh of scaled value
        if not np.isnan(hist[i]) and not np.isnan(cl[i]) and cl[i] != 0:
            macd_norm = float(np.tanh(hist[i] / cl[i] * 100))
        else:
            macd_norm = 0.0

        score = w_rsi * rsi_norm + w_tema * tema_norm + w_macd * macd_norm
        scores[i] = score

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: score crosses above threshold
        if i >= 1 and not np.isnan(scores[i-1]):
            if scores[i-1] <= entry_thresh and score > entry_thresh and trend_ok:
                entries[i] = True

        # Exit: score drops below exit threshold
        if score < exit_thresh:
            exits[i] = True
            labels[i] = "Score Drop"
            continue

        # ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 13: Chandelier Exit — Enter on trend, hold with highest-high trailing stop
# Enter when EMA crossover confirms uptrend.
# Exit via Chandelier: highest_high(N) - ATR(N) * multiplier.
# This gives a volatility-adjusted trailing stop from the highest high.
# ─────────────────────────────────────────────────────────────────────────────

def chandelier_exit(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    hi = ind.high
    ema_s = ind.ema(p.get("short_ema", 15))
    ema_l = ind.ema(p.get("long_ema", 50))
    atr_vals = ind.atr(p.get("atr_period", 22))
    trend_ema = ind.ema(p.get("trend_len", 100))
    chan_len = p.get("chan_len", 22)
    atr_mult = p.get("atr_mult", 3.0)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(chan_len + 1, n):
        if np.isnan(ema_s[i]) or np.isnan(ema_l[i]) or np.isnan(atr_vals[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: fast EMA crosses above slow EMA in uptrend
        if ema_s[i-1] <= ema_l[i-1] and ema_s[i] > ema_l[i] and trend_ok:
            entries[i] = True

        # Chandelier stop: highest high of last N bars - ATR * mult
        window_high = hi[max(0, i - chan_len + 1):i + 1]
        hh = np.nanmax(window_high)
        chan_stop = hh - atr_vals[i] * atr_mult

        if cl[i] < chan_stop:
            exits[i] = True
            labels[i] = "Chandelier"
            continue

        # Also exit when EMAs cross back down
        if ema_s[i] < ema_l[i] * (1 - p.get("ema_buffer", 0.01)):
            exits[i] = True
            labels[i] = "EMA Cross"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 14: Stochastic Oversold Recovery — Enter on %K cross from oversold
# Similar insight to rsi_regime but uses Stochastic oscillator.
# Stochastic %K crossing up through 20 often marks end of corrections.
# ─────────────────────────────────────────────────────────────────────────────

def stoch_recovery(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    stoch_k = ind.stoch_k(p.get("stoch_len", 14))
    stoch_d = ind.stoch_d(p.get("stoch_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 20))

    entry_level = p.get("entry_level", 20.0)
    exit_level = p.get("exit_level", 80.0)
    panic_level = p.get("panic_level", 10.0)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(stoch_k[i]) or np.isnan(stoch_k[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: %K crosses above oversold level + above trend EMA
        if stoch_k[i-1] < entry_level and stoch_k[i] >= entry_level and trend_ok:
            entries[i] = True

        # Exit: overbought
        if stoch_k[i] >= exit_level:
            exits[i] = True
            labels[i] = "Stoch Overbought"
            continue

        # Exit: panic — %K crashes below extreme oversold
        if stoch_k[i] < panic_level:
            exits[i] = True
            labels[i] = "Stoch Panic"
            continue

        # ATR shock
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
    # New strategies (2026-04-03)
    "adx_regime":       adx_regime,
    "macd_recovery":    macd_recovery,
    "donchian_regime":  donchian_regime,
    "recovery_momentum": recovery_momentum,
    "composite_regime": composite_regime,
    "chandelier_exit":  chandelier_exit,
    "stoch_recovery":   stoch_recovery,
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
    "adx_regime": {
        "adx_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "adx_min": (15.0, 35.0, 5.0, float), "adx_exit": (10.0, 25.0, 5.0, float),
        "adx_rise_lb": (3, 10, 2, int), "di_buffer": (0.0, 0.15, 0.05, float),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "macd_recovery": {
        "macd_fast": (8, 20, 2, int), "macd_slow": (18, 40, 4, int),
        "macd_sig": (5, 15, 2, int), "trend_len": (50, 200, 25, int),
        "lookback": (10, 40, 5, int), "deep_neg": (-2.0, -0.1, 0.3, float),
        "exit_neg": (-0.5, 0.0, 0.1, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "donchian_regime": {
        "entry_len": (30, 120, 10, int), "exit_len": (10, 60, 10, int),
        "trend_len": (50, 200, 25, int), "cooldown": (0, 20, 5, int),
    },
    "recovery_momentum": {
        "crash_pct": (15.0, 50.0, 5.0, float), "bounce_pct": (5.0, 25.0, 5.0, float),
        "peak_lb": (30, 120, 10, int), "trend_len": (50, 150, 25, int),
        "quick_ema": (5, 20, 5, int), "quick_lb": (3, 10, 2, int),
        "quick_thresh": (-15.0, -3.0, 2.0, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "composite_regime": {
        "rsi_len": (7, 21, 2, int), "tema_len": (20, 80, 10, int),
        "macd_fast": (8, 16, 4, int), "macd_slow": (20, 36, 4, int),
        "macd_sig": (5, 15, 5, int), "trend_len": (50, 200, 25, int),
        "tema_lb": (3, 10, 2, int), "w_rsi": (0.1, 0.6, 0.1, float),
        "w_tema": (0.1, 0.6, 0.1, float), "w_macd": (0.1, 0.6, 0.1, float),
        "entry_thresh": (0.0, 0.5, 0.1, float), "exit_thresh": (-0.4, 0.0, 0.1, float),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "chandelier_exit": {
        "short_ema": (5, 25, 5, int), "long_ema": (20, 80, 10, int),
        "chan_len": (10, 40, 5, int), "atr_period": (10, 40, 5, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "trend_len": (50, 200, 25, int),
        "ema_buffer": (0.0, 0.05, 0.01, float), "cooldown": (0, 20, 5, int),
    },
    "stoch_recovery": {
        "stoch_len": (5, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_level": (15.0, 35.0, 5.0, float), "exit_level": (65.0, 85.0, 5.0, float),
        "panic_level": (5.0, 20.0, 5.0, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
}
