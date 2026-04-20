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
from strategy_engine import Indicators, _ema, _sma


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
# Strategy 6: MACD Zero Cross — Enter when MACD line crosses above zero,
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
# Strategy 9: RSI + Vol Regime — RSI dip entry (proven winner) but only when
# realized vol is declining (crash ending). Filters out mid-crash false dips.
# ─────────────────────────────────────────────────────────────────────────────

def rsi_vol_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(p.get("rsi_len", 13))
    trend_ema = ind.ema(p.get("trend_len", 150))
    vol_short = ind.realized_vol(p.get("vol_short", 15))
    vol_long = ind.realized_vol(p.get("vol_long", 60))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_rsi = p.get("entry_rsi", 35)
    exit_rsi = p.get("exit_rsi", 80)
    vol_ratio_max = p.get("vol_ratio_max", 0.95)  # short vol < long vol = calming

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Vol filter: short vol declining relative to long vol (storm passing)
        vol_ok = True
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            vol_ok = (vol_short[i] / vol_long[i]) < vol_ratio_max

        # Entry: RSI crosses up + trend OK + vol calming
        if rsi[i-1] < entry_rsi and rsi[i] >= entry_rsi and trend_ok and vol_ok:
            entries[i] = True

        # Exit: RSI overbought
        if rsi[i] >= exit_rsi:
            exits[i] = True
            labels[i] = "RSI Overbought"
            continue

        # Exit: RSI panic
        if rsi[i] < p.get("panic_rsi", 15):
            exits[i] = True
            labels[i] = "RSI Panic"
            continue

        # Exit: vol spike (new crash starting)
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            if vol_short[i] / vol_long[i] > p.get("vol_exit_ratio", 1.5):
                exits[i] = True
                labels[i] = "Vol Spike"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: ADX Trend Strength — Enter when ADX rises above threshold with
# DI+ > DI-, exit when ADX falls or DI- dominates. Catches trend inception.
# Only 6 params — designed for low complexity penalty.
# ─────────────────────────────────────────────────────────────────────────────

def adx_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    adx_len = p.get("adx_len", 14)
    adx = ind.adx(adx_len)
    di_plus = ind.di_plus(adx_len)
    di_minus = ind.di_minus(adx_len)
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_adx = p.get("entry_adx", 20.0)
    exit_adx = p.get("exit_adx", 15.0)

    for i in range(1, n):
        if np.isnan(adx[i]) or np.isnan(adx[i-1]):
            continue
        if np.isnan(di_plus[i]) or np.isnan(di_minus[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: ADX crosses above threshold + DI+ > DI- + trend OK
        if adx[i-1] < entry_adx and adx[i] >= entry_adx and di_plus[i] > di_minus[i] and trend_ok:
            entries[i] = True

        # Exit 1: ADX drops below exit level (trend dying)
        if adx[i] < exit_adx:
            exits[i] = True
            labels[i] = "ADX Fade"
            continue

        # Exit 2: DI- crosses above DI+ (bears take over)
        if di_minus[i] > di_plus[i] and di_minus[i-1] <= di_plus[i-1]:
            exits[i] = True
            labels[i] = "DI Cross"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Keltner Squeeze — Bollinger Bands compress inside Keltner Channel
# (the "squeeze"), then expand out. Volatility contraction → expansion.
# Classic low-frequency breakout signal. 7 params.
# ─────────────────────────────────────────────────────────────────────────────

def keltner_squeeze(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    bb_len = p.get("bb_len", 20)
    bb_mult = p.get("bb_mult", 2.0)
    kelt_len = p.get("kelt_len", 20)
    kelt_mult = p.get("kelt_mult", 1.5)

    bb_upper = ind.bb_upper(bb_len, bb_mult)
    bb_lower = ind.bb_lower(bb_len, bb_mult)
    kelt_upper = ind.keltner_upper(kelt_len, kelt_len, kelt_mult)
    kelt_lower = ind.keltner_lower(kelt_len, kelt_len, kelt_mult)
    trend_ema = ind.ema(p.get("trend_len", 100))
    mom = ind.mom(p.get("mom_len", 12))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if (np.isnan(bb_upper[i]) or np.isnan(kelt_upper[i])
                or np.isnan(bb_lower[i]) or np.isnan(kelt_lower[i])):
            continue
        if np.isnan(mom[i]) or np.isnan(mom[i-1]):
            continue

        # Squeeze: BB inside Keltner
        squeeze_now = bb_lower[i] > kelt_lower[i] and bb_upper[i] < kelt_upper[i]
        squeeze_prev = (not np.isnan(bb_lower[i-1]) and not np.isnan(kelt_lower[i-1])
                        and bb_lower[i-1] > kelt_lower[i-1]
                        and bb_upper[i-1] < kelt_upper[i-1])

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: squeeze just released (was squeezing, now not) + momentum positive + trend OK
        if squeeze_prev and not squeeze_now and mom[i] > 0 and trend_ok:
            entries[i] = True

        # Exit 1: Momentum turns negative after being positive
        if mom[i-1] > 0 and mom[i] <= 0:
            exits[i] = True
            labels[i] = "Mom Reversal"
            continue

        # Exit 2: New squeeze forms (trend consolidating)
        if not squeeze_prev and squeeze_now:
            exits[i] = True
            labels[i] = "Re-Squeeze"

    return entries, exits, labels




# ─────────────────────────────────────────────────────────────────────────────
# Strategy 11: RSI Regime v2 — Add trailing stop to capture bigger moves
# Instead of fixed RSI overbought exit, ride the trend with a trailing stop.
# Keeps the winning RSI-dip entry but lets winners run longer.
# ─────────────────────────────────────────────────────────────────────────────

def rsi_regime_trail(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    rsi = ind.rsi(p.get("rsi_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 150))
    cl = ind.close
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_level = p.get("entry_rsi", 35)
    trail_pct = p.get("trail_pct", 25)
    peak = np.nan

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i-1]):
            continue

        # Entry: RSI crosses up through entry level + price above trend EMA
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]
        if rsi[i-1] < entry_level and rsi[i] >= entry_level and trend_ok:
            entries[i] = True
            peak = cl[i]

        # Track peak
        if not np.isnan(peak):
            peak = max(peak, cl[i])

        # Exit: Trailing stop from peak
        if not np.isnan(peak) and cl[i] < peak * (1 - trail_pct / 100):
            exits[i] = True
            labels[i] = "Trail Stop"
            peak = np.nan
            continue

        # Exit: RSI panic (extreme crash)
        if rsi[i] < p.get("panic_rsi", 15):
            exits[i] = True
            labels[i] = "RSI Panic"
            peak = np.nan
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"
                peak = np.nan

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 14: Volatility Regime — Enter when realized vol drops from high
# (bear market ending), exit when vol spikes (crash starting).
# TECL vol signature: high vol = drawdowns, declining vol = recovery.
# ─────────────────────────────────────────────────────────────────────────────

def vol_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    vol_short = ind.realized_vol(p.get("vol_short", 20))
    vol_long = ind.realized_vol(p.get("vol_long", 60))
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    vol_entry_ratio = p.get("vol_entry_ratio", 0.9)  # short vol < long vol = calming
    vol_exit_ratio = p.get("vol_exit_ratio", 1.5)     # short vol spikes above long vol

    for i in range(1, n):
        if np.isnan(vol_short[i]) or np.isnan(vol_long[i]) or vol_long[i] == 0:
            continue
        if np.isnan(vol_short[i-1]) or np.isnan(vol_long[i-1]) or vol_long[i-1] == 0:
            continue

        ratio = vol_short[i] / vol_long[i]
        prev_ratio = vol_short[i-1] / vol_long[i-1]
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: vol ratio crosses below threshold (calming from storm) + trend OK
        if prev_ratio >= vol_entry_ratio and ratio < vol_entry_ratio and trend_ok:
            entries[i] = True

        # Exit: vol ratio spikes (storm arriving)
        if ratio > vol_exit_ratio:
            exits[i] = True
            labels[i] = "Vol Spike"
            continue

        # Exit: price drops below trend EMA
        if not np.isnan(trend_ema[i]) and cl[i] < trend_ema[i] * (1 - p.get("trend_buffer", 2.0) / 100):
            exits[i] = True
            labels[i] = "Below Trend"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 15: Ichimoku Cloud — Enter above cloud with TK cross, exit below.
# Classic trend system adapted for TECL's long bull/bear cycles.
# ─────────────────────────────────────────────────────────────────────────────

def ichimoku_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    tenkan = ind.ichimoku_tenkan(p.get("tenkan_len", 9))
    kijun = ind.ichimoku_kijun(p.get("kijun_len", 26))
    # Use long EMA as "cloud" proxy (true Ichimoku cloud needs senkou spans)
    cloud_ema = ind.ema(p.get("cloud_len", 52))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(tenkan[i]) or np.isnan(kijun[i]) or np.isnan(tenkan[i-1]):
            continue

        above_cloud = np.isnan(cloud_ema[i]) or cl[i] > cloud_ema[i]

        # Entry: Tenkan crosses above Kijun + price above cloud
        if tenkan[i-1] <= kijun[i-1] and tenkan[i] > kijun[i] and above_cloud:
            entries[i] = True

        # Exit: Tenkan crosses below Kijun
        if tenkan[i-1] >= kijun[i-1] and tenkan[i] < kijun[i]:
            exits[i] = True
            labels[i] = "TK Cross Down"
            continue

        # Exit: Price drops below cloud
        if not np.isnan(cloud_ema[i]) and cl[i] < cloud_ema[i] * (1 - p.get("cloud_buffer", 1.0) / 100):
            exits[i] = True
            labels[i] = "Below Cloud"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 16: Dual Momentum — Enter when both absolute return and relative
# momentum (vs own moving average) are positive. Exit when either fails.
# Captures trend following with momentum confirmation.
# ─────────────────────────────────────────────────────────────────────────────

def dual_momentum(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    roc_abs = ind.roc(p.get("abs_period", 60))    # Absolute: is TECL going up?
    roc_short = ind.roc(p.get("short_period", 20)) # Short-term: is momentum positive?
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    abs_thresh = p.get("abs_thresh", 5.0)    # Require N% absolute return
    short_thresh = p.get("short_thresh", 2.0) # Require N% short return

    for i in range(1, n):
        if np.isnan(roc_abs[i]) or np.isnan(roc_short[i]):
            continue
        if np.isnan(roc_abs[i-1]) or np.isnan(roc_short[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: both momentum measures cross above thresholds + trend OK
        abs_ok = roc_abs[i] > abs_thresh
        short_ok = roc_short[i] > short_thresh
        prev_not_both = roc_abs[i-1] <= abs_thresh or roc_short[i-1] <= short_thresh

        if abs_ok and short_ok and prev_not_both and trend_ok:
            entries[i] = True

        # Exit: absolute momentum goes negative
        if roc_abs[i] < p.get("abs_exit", -5.0):
            exits[i] = True
            labels[i] = "Abs Mom Exit"
            continue

        # Exit: short momentum drops sharply
        if roc_short[i] < p.get("short_exit", -8.0):
            exits[i] = True
            labels[i] = "Short Mom Exit"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Always-In Trend — Default to LONG. Only exit when multiple bear
# signals confirm. The thesis: missing bull runs kills share_multiple more than
# catching bear drops helps. Stay in unless ADX trend dies AND price breaks
# below trend EMA. Re-enter quickly when trend resumes. 6 params.
# ─────────────────────────────────────────────────────────────────────────────

def always_in_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    ema_fast = ind.ema(p.get("fast_ema", 20))
    ema_slow = ind.ema(p.get("slow_ema", 50))
    adx_len = p.get("adx_len", 14)
    adx = ind.adx(adx_len)
    di_plus = ind.di_plus(adx_len)
    di_minus = ind.di_minus(adx_len)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    exit_adx = p.get("exit_adx", 20.0)

    for i in range(1, n):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
            continue

        # Entry: fast EMA above slow EMA (very permissive — stay in market)
        if ema_fast[i] > ema_slow[i]:
            entries[i] = True

        # Exit requires BOTH: trend dying (ADX low or DI- dominant) AND price below slow EMA
        below_trend = cl[i] < ema_slow[i]
        if not np.isnan(adx[i]) and not np.isnan(di_plus[i]) and not np.isnan(di_minus[i]):
            trend_weak = adx[i] < exit_adx or di_minus[i] > di_plus[i]
            if below_trend and trend_weak:
                exits[i] = True
                labels[i] = "B"  # Bear confirmed
        elif below_trend:
            exits[i] = True
            labels[i] = "B"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Donchian Turtle — Classic turtle trading. Enter on N-bar high
# breakout, exit on M-bar low breakdown. Asymmetric: long entry lookback,
# shorter exit lookback. Rides big moves, exits on confirmed reversals. 5 params.
# ─────────────────────────────────────────────────────────────────────────────

def donchian_turtle(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    entry_len = p.get("entry_len", 55)
    exit_len = p.get("exit_len", 20)
    don_upper = ind.donchian_upper(entry_len)
    don_lower_exit = ind.donchian_lower(exit_len)
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(don_upper[i]) or np.isnan(don_lower_exit[i]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: price breaks above N-bar high channel + trend filter
        if cl[i] >= don_upper[i] and trend_ok:
            entries[i] = True

        # Exit: price breaks below M-bar low channel
        if cl[i] <= don_lower_exit[i]:
            exits[i] = True
            labels[i] = "D"  # Donchian breakdown

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Slope Persistence — Enter when long EMA slope stays positive for
# N consecutive bars (confirmed uptrend). Exit only when slope stays negative
# for M consecutive bars (confirmed downtrend). The persistence filter
# prevents whipsaw exits that kill bull capture. 6 params.
# ─────────────────────────────────────────────────────────────────────────────

def slope_persistence(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    ema_len = p.get("ema_len", 50)
    ema = ind.ema(ema_len)
    slope_window = p.get("slope_window", 5)
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_bars = p.get("entry_bars", 3)   # Consecutive positive slope bars to enter
    exit_bars = p.get("exit_bars", 5)     # Consecutive negative slope bars to exit

    pos_count = 0
    neg_count = 0

    for i in range(slope_window, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_window]):
            continue

        slope = ema[i] - ema[i - slope_window]

        if slope > 0:
            pos_count += 1
            neg_count = 0
        else:
            neg_count += 1
            pos_count = 0

        # Entry: slope has been positive for entry_bars consecutive checks
        if pos_count >= entry_bars:
            entries[i] = True

        # Exit: slope has been negative for exit_bars consecutive checks
        if neg_count >= exit_bars:
            exits[i] = True
            labels[i] = "S"  # Slope reversal
            continue

        # Exit: ATR shock (emergency)
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "A"  # ATR shock
                neg_count = 0

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Trough Bounce — Fast entry after bear troughs + sticky exit.
# Cycle diagnostics show strategies miss V-shaped recoveries (Bull #3-#6).
# This enters when RSI recovers from deep oversold AND price bounces above
# recent low by N%, then stays in until multiple bearish confirmations.
# Designed for max bull capture on post-crash recoveries. 7 params.
# ─────────────────────────────────────────────────────────────────────────────

def trough_bounce(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(p.get("rsi_len", 9))
    lowest = ind.lowest(p.get("low_lookback", 40))
    ema_fast = ind.ema(p.get("fast_ema", 10))
    ema_slow = ind.ema(p.get("slow_ema", 50))
    atr_vals = ind.atr(p.get("atr_period", 20))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    bounce_pct = p.get("bounce_pct", 15.0)  # price must be N% above recent low
    exit_confirm = p.get("exit_confirm", 3)  # need N consecutive bars of fast < slow

    below_count = 0  # consecutive bars with fast EMA < slow EMA

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(lowest[i]):
            continue

        # Entry: price has bounced N% off the recent low + RSI recovering
        if lowest[i] > 0:
            bounce = (cl[i] / lowest[i] - 1) * 100
            if bounce >= bounce_pct and rsi[i] > 30 and rsi[i-1] <= 30:
                entries[i] = True

        # Also enter on fast > slow EMA cross (trend resumption after pullback)
        if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
            if not np.isnan(ema_fast[i-1]) and not np.isnan(ema_slow[i-1]):
                if ema_fast[i-1] <= ema_slow[i-1] and ema_fast[i] > ema_slow[i]:
                    entries[i] = True

        # Sticky exit: require N consecutive bars of fast < slow before exiting
        if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
            if ema_fast[i] < ema_slow[i]:
                below_count += 1
            else:
                below_count = 0

            if below_count >= exit_confirm:
                exits[i] = True
                labels[i] = "C"  # Confirmed cross
                below_count = 0
                continue

        # Emergency exit: ATR shock (only for true crashes)
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 4.0):
                exits[i] = True
                labels[i] = "A"
                below_count = 0

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Momentum Stayer — Enter on positive momentum, STAY IN unless
# multiple bearish signals confirm. Cycle diagnostics show the #1 problem is
# exiting during bulls on single-signal triggers. This requires 2+ of 3
# bearish conditions (trend break + RSI weak + vol spike) before exiting.
# Designed for maximum time-in-market during bull cycles. 8 params.
# ─────────────────────────────────────────────────────────────────────────────

def momentum_stayer(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    ema_fast = ind.ema(p.get("fast_ema", 15))
    ema_slow = ind.ema(p.get("slow_ema", 50))
    rsi = ind.rsi(p.get("rsi_len", 14))
    vol_short = ind.realized_vol(p.get("vol_short", 15))
    vol_long = ind.realized_vol(p.get("vol_long", 60))
    roc = ind.roc(p.get("roc_period", 40))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    exit_rsi = p.get("exit_rsi", 30.0)
    vol_exit_ratio = p.get("vol_exit_ratio", 1.5)

    for i in range(1, n):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
            continue

        # Entry: fast EMA > slow EMA + positive momentum (very permissive)
        if ema_fast[i] > ema_slow[i]:
            if not np.isnan(roc[i]) and roc[i] > 0:
                entries[i] = True

        # Exit requires 2+ of 3 bearish conditions simultaneously:
        bearish_signals = 0

        # Condition 1: Trend break (fast < slow EMA)
        if ema_fast[i] < ema_slow[i]:
            bearish_signals += 1

        # Condition 2: RSI weak
        if not np.isnan(rsi[i]) and rsi[i] < exit_rsi:
            bearish_signals += 1

        # Condition 3: Vol spike (short vol >> long vol = crash starting)
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            if vol_short[i] / vol_long[i] > vol_exit_ratio:
                bearish_signals += 1

        if bearish_signals >= 2:
            exits[i] = True
            labels[i] = "M"  # Multi-confirm exit

    return entries, exits, labels
    vol_ratio_max = p.get("vol_ratio_max", 0.9)
    vol_exit_ratio = p.get("vol_exit_ratio", 1.5)

    for i in range(1, n):
        if np.isnan(wr[i]) or np.isnan(wr[i-1]) or np.isnan(don_mid[i]):
            continue

        # Vol filter
        vol_ok = True
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            vol_ok = (vol_short[i] / vol_long[i]) < vol_ratio_max

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: Williams %R crosses up through entry level + price above midline + trend + vol
        if (wr[i-1] < entry_wr and wr[i] >= entry_wr
                and cl[i] > don_mid[i]
                and trend_ok
                and vol_ok):
            entries[i] = True

        # Exit 1: Williams overbought
        if wr[i] >= exit_wr:
            exits[i] = True
            labels[i] = "Williams Overbought"
            continue

        # Exit 2: Midline lost — price below midline and WR weak
        if cl[i] < don_mid[i] and wr[i] < rebreak_wr:
            exits[i] = True
            labels[i] = "Midline Lost"
            continue

        # Exit 3: Vol spike
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            if vol_short[i] / vol_long[i] > vol_exit_ratio:
                exits[i] = True
                labels[i] = "Vol Spike"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Registry — all strategies the optimizer can test (max 15)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Strategy: VIX Mean Reversion — Buy when VIX spikes (fear = opportunity),
# sell when VIX compresses back to normal. Uses VIX percentile rank to
# identify extremes. The thesis: TECL bottoms coincide with VIX spikes.
# ─────────────────────────────────────────────────────────────────────────────

def vix_mean_revert(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    vix = ind.vix_close()
    vix_pctl = ind.vix_percentile(p.get("vix_lookback", 252))
    trend_ema = ind.ema(p.get("trend_len", 100))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_pctl = p.get("entry_pctl", 85)    # VIX in top 15% = fear spike
    exit_pctl = p.get("exit_pctl", 40)      # VIX back to normal
    vix_ema_len = p.get("vix_ema_len", 10)
    vix_smooth = ind.vix_ema(vix_ema_len)

    for i in range(1, n):
        if np.isnan(vix_pctl[i]) or np.isnan(vix_smooth[i]):
            continue

        # Entry: VIX percentile was high (fear spike) and VIX is now turning down
        # (smoothed VIX declining = fear receding)
        vix_was_high = vix_pctl[i] >= entry_pctl or vix_pctl[i - 1] >= entry_pctl
        vix_declining = vix_smooth[i] < vix_smooth[i - 1]
        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i] * (1 - p.get("trend_buffer", 5.0) / 100)

        if vix_was_high and vix_declining and trend_ok:
            entries[i] = True

        # Exit: VIX compresses back to normal (complacency)
        if vix_pctl[i] <= exit_pctl:
            exits[i] = True
            labels[i] = "V"  # VIX normalized
            continue

        # Exit: VIX spikes even higher (panic acceleration — get out)
        if vix[i] > p.get("panic_vix", 45):
            exits[i] = True
            labels[i] = "P"  # Panic

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: VIX Regime + Trend — Combine VIX regime detection with EMA trend.
# Enter when VIX is below its long-term average (calm regime) AND trend is up.
# Exit when VIX spikes above threshold (regime shift to fear) or trend breaks.
# Opposite logic to vix_mean_revert — this rides the calm, exits on fear.
# ─────────────────────────────────────────────────────────────────────────────

def vix_trend_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    vix = ind.vix_close()
    vix_slow = ind.vix_sma(p.get("vix_slow_len", 60))
    ema_short = ind.ema(p.get("short_ema", 20))
    ema_long = ind.ema(p.get("long_ema", 50))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    vix_entry_ratio = p.get("vix_entry_ratio", 0.9)  # VIX < 90% of its SMA = calm
    vix_exit_ratio = p.get("vix_exit_ratio", 1.3)     # VIX > 130% of SMA = fear spike

    for i in range(1, n):
        if np.isnan(ema_short[i]) or np.isnan(ema_long[i]) or np.isnan(vix_slow[i]):
            continue
        if vix_slow[i] <= 0:
            continue

        vix_ratio = vix[i] / vix_slow[i]

        # Entry: trend up + VIX is calm (below its average)
        trend_up = ema_short[i] > ema_long[i]
        vix_calm = vix_ratio < vix_entry_ratio

        if trend_up and vix_calm:
            entries[i] = True

        # Exit 1: VIX spikes (regime shift)
        if vix_ratio > vix_exit_ratio:
            exits[i] = True
            labels[i] = "V"  # VIX spike
            continue

        # Exit 2: Trend break (EMA cross)
        if ema_short[i] < ema_long[i] and ema_short[i - 1] >= ema_long[i - 1]:
            exits[i] = True
            labels[i] = "E"  # EMA cross
            continue

        # Exit 3: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i - 1] - atr_vals[i] * p.get("atr_mult", 3.0):
                exits[i] = True
                labels[i] = "A"  # ATR shock

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: Steady Trend — Ultra-simple trend persistence.
# Default long when EMA slope is positive. Only exit when slope has been
# negative for N consecutive bars. Designed to stay in bulls and avoid
# bear-boundary memorization with structural, non-timing exits.
# 4 params — under regime_transitions ceiling.
# ─────────────────────────────────────────────────────────────────────────────

def steady_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    ema = ind.ema(p.get("ema_len", 50))
    slope_window = p.get("slope_window", 5)
    entry_bars = p.get("entry_bars", 3)
    exit_bars = p.get("exit_bars", 5)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    slope_pos_count = 0
    slope_neg_count = 0

    for i in range(slope_window + 1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_window]):
            continue

        slope = (ema[i] - ema[i - slope_window]) / max(ema[i - slope_window], 1e-6)

        if slope > 0:
            slope_pos_count += 1
            slope_neg_count = 0
        else:
            slope_neg_count += 1
            slope_pos_count = 0

        # Entry: EMA slope positive for entry_bars consecutive bars + price above EMA
        if slope_pos_count >= entry_bars and cl[i] > ema[i]:
            entries[i] = True

        # Exit: EMA slope negative for exit_bars consecutive bars
        if slope_neg_count >= exit_bars:
            exits[i] = True
            labels[i] = "S"  # slope reversal

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: RSI Recovery — Simplified RSI regime without the bull-killing
# overbought exit. Enter on RSI recovery from oversold while above trend.
# Exit only on deep RSI plunge (panic) or trend breakdown.
# 5 params — comfortably under ceiling.
# ─────────────────────────────────────────────────────────────────────────────

def rsi_recovery(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    rsi = ind.rsi(p.get("rsi_len", 14))
    trend_ema = ind.ema(p.get("trend_len", 100))
    entry_rsi = p.get("entry_rsi", 35)
    panic_rsi = p.get("panic_rsi", 20)
    cooldown = p.get("cooldown", 10)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    was_oversold = False

    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(trend_ema[i]):
            continue

        # Track when RSI dips below entry threshold
        if rsi[i] < entry_rsi:
            was_oversold = True

        # Entry: RSI recovers above entry threshold after being oversold
        # + price above trend EMA (confirms trend is intact)
        if was_oversold and rsi[i] > entry_rsi and cl[i] > trend_ema[i]:
            entries[i] = True
            was_oversold = False

        # Exit 1: Panic RSI — deep plunge signals real trouble
        if rsi[i] < panic_rsi:
            exits[i] = True
            labels[i] = "P"  # panic
            continue

        # Exit 2: Trend breakdown — price below trend EMA and RSI weakening
        if cl[i] < trend_ema[i] and rsi[i] < 45:
            exits[i] = True
            labels[i] = "T"  # trend break

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: EMA Regime — Two-EMA crossover with persistence filter.
# Only enter after fast > slow for N bars (avoids whipsaws).
# Only exit after fast < slow for M bars (stays in bulls longer).
# 5 params — lean and testable.
# ─────────────────────────────────────────────────────────────────────────────

def ema_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close

    fast = ind.ema(p.get("fast_ema", 20))
    slow = ind.ema(p.get("slow_ema", 60))
    entry_confirm = p.get("entry_confirm", 3)
    exit_confirm = p.get("exit_confirm", 5)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    bull_count = 0
    bear_count = 0

    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]):
            continue

        if fast[i] > slow[i]:
            bull_count += 1
            bear_count = 0
        else:
            bear_count += 1
            bull_count = 0

        # Entry: fast above slow for entry_confirm consecutive bars
        if bull_count == entry_confirm:
            entries[i] = True

        # Exit: fast below slow for exit_confirm consecutive bars
        if bear_count >= exit_confirm:
            exits[i] = True
            labels[i] = "X"  # cross confirmed

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy: ema_200_regime (T0 HYPOTHESIS)
#
# Hypothesis: TECL is a leveraged wrapper around a long-term-rising asset.
# The 200-day EMA is the canonical long-term trend filter. Hold when price
# is above it; sit out when below.
#
# This is the simplest possible hypothesis strategy:
#   - 1 canonical param (ema_len = 200)
#   - 1 structural cooldown (2 bars, canonical)
#   - No tuning, no interactions, no knobs
#
# Pre-registered as T0 at 2026-04-13. Params committed before first backtest.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# T0 BATCH 2026-04-13 — 17 hypotheses queued for spike testing
#
# All canonical params, ≤5 tunable, pre-registered. Designed across signal
# families known to pass (slope-filtered MA cross, RSI recovery, multi-EMA
# stack, Donchian breakout, MACD trend) at moderate horizons that don't
# over-lag TECL's 3× volatility.
# ─────────────────────────────────────────────────────────────────────────────


def _ma_cross_with_slope(ind, p, fast_len, slow_len):
    """Shared logic: golden_cross_NN_MM strategies (fast EMA crosses slow,
    with slope filter on slow EMA + entry confirmation bars). Exits on death cross."""
    n = ind.n
    fast = ind.ema(fast_len)
    slow = ind.ema(slow_len)
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(slow[i - slope_window]):
            continue
        if fast[i] > slow[i] and slow[i] > slow[i - slope_window]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def golden_cross_30_150(ind, p):
    """T0: 30/150 EMA golden cross with slope filter — faster cycle response than 50/200."""
    return _ma_cross_with_slope(ind, p, p.get("fast_ema", 30), p.get("slow_ema", 150))


def golden_cross_20_100(ind, p):
    """T0: 20/100 EMA golden cross with slope filter — fastest practical golden cross."""
    return _ma_cross_with_slope(ind, p, p.get("fast_ema", 20), p.get("slow_ema", 100))


def golden_cross_50_150(ind, p):
    """T0: 50/150 asymmetric golden cross — same fast as proven 50/200, shorter slow."""
    return _ma_cross_with_slope(ind, p, p.get("fast_ema", 50), p.get("slow_ema", 150))


def golden_cross_100_200(ind, p):
    """T0: 100/200 golden cross — slower fast EMA, classic 200 trend."""
    return _ma_cross_with_slope(ind, p, p.get("fast_ema", 100), p.get("slow_ema", 200))


def _ema_slope_above(ind, p, ema_len):
    """Shared logic: close > EMA AND EMA rising for entry_bars consecutive bars."""
    n = ind.n
    cl = ind.close
    ema = ind.ema(ema_len)
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_window]):
            continue
        if cl[i] > ema[i] and ema[i] > ema[i - slope_window]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if cl[i - 1] >= ema[i - 1] and cl[i] < ema[i]:
            exits[i] = True
            labels[i] = "T"
    return entries, exits, labels


def ema_50_slope_above(ind, p):
    """T0: close > EMA-50 + EMA-50 rising. Faster trend follow than 100+."""
    return _ema_slope_above(ind, p, p.get("ema_len", 50))


def ema_100_slope_above(ind, p):
    """T0: close > EMA-100 + EMA-100 rising. Medium-horizon regime filter with slope."""
    return _ema_slope_above(ind, p, p.get("ema_len", 100))


def ema_150_slope_above(ind, p):
    """T0: close > EMA-150 + EMA-150 rising. Between 100 and 200."""
    return _ema_slope_above(ind, p, p.get("ema_len", 150))


def ema_200_slope_above(ind, p):
    """T0: close > EMA-200 + EMA-200 rising. Improvement on bare ema_200_regime
    by adding slope filter + entry confirmation to reduce whipsaws."""
    return _ema_slope_above(ind, p, p.get("ema_len", 200))


def _rsi_recovery_above_ema(ind, p, trend_len):
    """Shared logic: RSI-14 crosses up through entry_rsi (was below) AND close > trend EMA.
    Designed for fast re-entry after crashes — addresses 2020/2023 weakness."""
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    trend = ind.ema(trend_len)
    entry_rsi = 30  # canonical-implicit (oversold recovery threshold)
    exit_rsi = 20  # canonical-implicit (deep panic exit)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    was_below = False
    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(trend[i]):
            continue
        if rsi[i] < entry_rsi:
            was_below = True
        if was_below and rsi[i - 1] < entry_rsi <= rsi[i] and cl[i] > trend[i]:
            entries[i] = True
            was_below = False
        if rsi[i] < exit_rsi or cl[i] < trend[i]:
            exits[i] = True
            labels[i] = "T"
    return entries, exits, labels


def rsi_recovery_ema_100(ind, p):
    """T0: RSI-14 recovers above 30 + close > EMA-100. Fast post-crash re-entry."""
    return _rsi_recovery_above_ema(ind, p, p.get("trend_len", 100))


def rsi_recovery_ema_200(ind, p):
    """T0: RSI-14 recovers above 30 + close > EMA-200. Same logic, slower trend filter."""
    return _rsi_recovery_above_ema(ind, p, p.get("trend_len", 200))


def rsi_50_above_ema_200(ind, p):
    """T0: RSI-14 sustained > 50 + close > EMA-200. Sustained bullish momentum signal."""
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    trend = ind.ema(int(p.get("trend_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(trend[i]):
            continue
        if rsi[i] > 50 and cl[i] > trend[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if rsi[i] < 50 or cl[i] < trend[i]:
            exits[i] = True
            labels[i] = "M"
    return entries, exits, labels


def triple_ema_stack(ind, p):
    """T0: close > EMA-50 > EMA-100 > EMA-200 (full bullish alignment).
    Exit when alignment breaks (close crosses below EMA-50)."""
    n = ind.n
    cl = ind.close
    ema_short = ind.ema(int(p.get("short_ema", 50)))
    ema_med = ind.ema(int(p.get("med_ema", 100)))
    ema_long = ind.ema(int(p.get("long_ema", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(ema_short[i]) or np.isnan(ema_med[i]) or np.isnan(ema_long[i]):
            continue
        if cl[i] > ema_short[i] > ema_med[i] > ema_long[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if cl[i - 1] >= ema_short[i - 1] and cl[i] < ema_short[i]:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def dual_ema_stack(ind, p):
    """T0: close > EMA-50 AND close > EMA-200 (both trend filters bullish).
    Simpler than triple stack, more responsive than single."""
    n = ind.n
    cl = ind.close
    ema_short = ind.ema(int(p.get("short_ema", 50)))
    ema_long = ind.ema(int(p.get("long_ema", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(ema_short[i]) or np.isnan(ema_long[i]):
            continue
        if cl[i] > ema_short[i] and cl[i] > ema_long[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit on close below either trend
        if cl[i] < ema_long[i]:
            exits[i] = True
            labels[i] = "T"
    return entries, exits, labels


def donchian_100_50_filter(ind, p):
    """T0: 100-day high entry + EMA-100 trend filter; 50-day low exit.
    Faster than 200/100 — should engage more cycles."""
    n = ind.n
    cl = ind.close
    entry_len = int(p.get("entry_len", 100))
    exit_len = int(p.get("exit_len", 50))
    trend = ind.ema(int(p.get("trend_len", 100)))
    upper = ind.donchian_upper(entry_len)
    lower = ind.donchian_lower(exit_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(entry_len, exit_len), n):
        if np.isnan(upper[i - 1]) or np.isnan(lower[i - 1]) or np.isnan(trend[i]):
            continue
        if cl[i] > upper[i - 1] and cl[i] > trend[i]:
            entries[i] = True
        if cl[i] < lower[i - 1]:
            exits[i] = True
            labels[i] = "B"
    return entries, exits, labels


def donchian_150_50_filter(ind, p):
    """T0: 150-day high entry + EMA-200 trend filter; 50-day low exit.
    Middle-ground breakout horizon."""
    n = ind.n
    cl = ind.close
    entry_len = int(p.get("entry_len", 150))
    exit_len = int(p.get("exit_len", 50))
    trend = ind.ema(int(p.get("trend_len", 200)))
    upper = ind.donchian_upper(entry_len)
    lower = ind.donchian_lower(exit_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(entry_len, exit_len), n):
        if np.isnan(upper[i - 1]) or np.isnan(lower[i - 1]) or np.isnan(trend[i]):
            continue
        if cl[i] > upper[i - 1] and cl[i] > trend[i]:
            entries[i] = True
        if cl[i] < lower[i - 1]:
            exits[i] = True
            labels[i] = "B"
    return entries, exits, labels


def macd_above_zero_trend(ind, p):
    """T0: MACD line crosses above zero AND close > EMA-200 trend filter.
    Exit on MACD crossing back below zero."""
    n = ind.n
    cl = ind.close
    macd_line = ind.macd_line(12, 26)
    trend = ind.ema(int(p.get("trend_len", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(macd_line[i]) or np.isnan(trend[i]) or np.isnan(macd_line[i - 1]):
            continue
        # Entry: MACD crosses above 0 AND close > trend
        if macd_line[i - 1] <= 0 < macd_line[i] and cl[i] > trend[i]:
            entries[i] = True
        # Exit: MACD crosses below 0
        if macd_line[i - 1] >= 0 > macd_line[i]:
            exits[i] = True
            labels[i] = "M"
    return entries, exits, labels


def ema_100_pure_slope(ind, p):
    """T0: pure slope signal — enter when EMA-100 has been rising for entry_bars
    consecutive bars; exit when slope turns negative. No price condition."""
    n = ind.n
    ema = ind.ema(int(p.get("ema_len", 100)))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_window]):
            continue
        rising = ema[i] > ema[i - slope_window]
        if rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if not rising and ema[i] < ema[i - 1]:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def golden_cross_100_300(ind: Indicators, p: dict) -> tuple:
    """T0 HYPOTHESIS — Long-horizon golden cross (100/300) with slope filter.

    Same structure as golden_cross_slope but at longer time horizons. The
    100/300 cross is rarer than 50/200 (~5x less frequent) so trades should
    be longer-held and less subject to chop. Slope filter on the 300-EMA
    keeps us out of sideways markets where fast/slow weave without direction.

    Pre-registered as T0 at 2026-04-13. 4 tunable canonical params.
    Params (all canonical):
      fast_ema      = 100  (MA_PERIODS)
      slow_ema      = 300  (MA_PERIODS)
      slope_window  = 5    (SLOPE_CONFIRM_BARS) — slope lookback on slow EMA
      entry_bars    = 3    (SLOPE_CONFIRM_BARS) — confirmation bars for entry
      cooldown      = 5    (COOLDOWN_BARS, structural)
    """
    n = ind.n
    cl = ind.close
    fast = ind.ema(p.get("fast_ema", 100))
    slow = ind.ema(p.get("slow_ema", 300))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(slow[i - slope_window]):
            continue
        slow_rising = slow[i] > slow[i - slope_window]
        golden = fast[i] > slow[i]
        if golden and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"

    return entries, exits, labels


def tema_200_slope(ind: Indicators, p: dict) -> tuple:
    """T0 HYPOTHESIS — Price vs TEMA-200 with positive slope filter.

    TEMA (Triple EMA) reduces lag vs simple EMA while preserving smoothness.
    Hypothesis: hold while price > TEMA-200 AND TEMA-200 is rising; exit on
    cross below. The slope filter keeps us out of false breakouts where
    price pokes above a flat or declining TEMA.

    Pre-registered as T0 at 2026-04-13. 3 tunable canonical params.
    Params (all canonical):
      tema_len      = 200  (MA_PERIODS)
      slope_window  = 5    (SLOPE_CONFIRM_BARS) — slope lookback on TEMA
      entry_bars    = 3    (SLOPE_CONFIRM_BARS) — confirmation bars for entry
      cooldown      = 5    (COOLDOWN_BARS, structural)
    """
    n = ind.n
    cl = ind.close
    tema = ind.tema(p.get("tema_len", 200))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(tema[i]) or np.isnan(tema[i - slope_window]):
            continue
        rising = tema[i] > tema[i - slope_window]
        above = cl[i] > tema[i]
        if above and rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit: close crosses below TEMA
        if cl[i - 1] >= tema[i - 1] and cl[i] < tema[i]:
            exits[i] = True
            labels[i] = "T"

    return entries, exits, labels


def donchian_200_100(ind: Indicators, p: dict) -> tuple:
    """T0 HYPOTHESIS — Channel breakout with long-term trend filter.

    Hypothesis: a 200-day high IS the breakout signal — price making new
    multi-quarter highs while above the 200-EMA confirms a real trend. Exit
    on a 100-day low (give the trend room to breathe but not unlimited).

    Pre-registered as T0 at 2026-04-13. 3 tunable canonical params.
    Params (all canonical):
      entry_len  = 200  (LOOKBACK_PERIODS) — Donchian lookback for breakout
      exit_len   = 100  (LOOKBACK_PERIODS) — Donchian lookback for exit
      trend_len  = 200  (MA_PERIODS) — long-term trend filter
      cooldown   = 5    (COOLDOWN_BARS, structural)
    """
    n = ind.n
    cl = ind.close
    entry_len = int(p.get("entry_len", 200))
    exit_len = int(p.get("exit_len", 100))
    trend_ema = ind.ema(p.get("trend_len", 200))
    upper = ind.donchian_upper(entry_len)
    lower = ind.donchian_lower(exit_len)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(max(entry_len, exit_len), n):
        if np.isnan(upper[i - 1]) or np.isnan(lower[i - 1]) or np.isnan(trend_ema[i]):
            continue
        # Entry: price closes above prior 200-day high AND above 200-EMA trend filter
        if cl[i] > upper[i - 1] and cl[i] > trend_ema[i]:
            entries[i] = True
        # Exit: price closes below prior 100-day low
        if cl[i] < lower[i - 1]:
            exits[i] = True
            labels[i] = "B"  # breakdown

    return entries, exits, labels


def golden_cross_slope(ind: Indicators, p: dict) -> tuple:
    """T0 HYPOTHESIS — Classic 50/200 Golden Cross with a slope filter on the slow EMA.

    Hypothesis: the 50/200 golden cross is the canonical long-term trend signal;
    adding a rising-slope requirement on the 200-EMA filters out the chop
    regime where fast and slow weave around each other without real direction.
    Exit on the reciprocal death cross — no fancy exit, trust the signal.

    Pre-registered as T0 at 2026-04-13. 4 tunable canonical params.
    Params (all canonical):
      fast_ema      = 50   (MA_PERIODS)
      slow_ema      = 200  (MA_PERIODS)
      slope_window  = 5    (SLOPE_CONFIRM_BARS) — slope lookback on slow EMA
      entry_bars    = 3    (SLOPE_CONFIRM_BARS) — confirmation bars for entry
      cooldown      = 5    (COOLDOWN_BARS, structural — not counted toward tier)
    """
    n = ind.n
    cl = ind.close
    fast = ind.ema(p.get("fast_ema", 50))
    slow = ind.ema(p.get("slow_ema", 200))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(slow[i - slope_window]):
            continue
        slow_rising = slow[i] > slow[i - slope_window]
        golden = fast[i] > slow[i]
        # Track consecutive bars with golden+rising-slope state
        if golden and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        # Entry: golden cross confirmed for entry_bars consecutive bars + slow rising
        if bull_count == entry_bars:
            entries[i] = True
        # Exit: fast crosses below slow (death cross) — no slope requirement for exit,
        # we want to be fast on the way out
        if fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"  # death cross

    return entries, exits, labels


def ema_200_confirm(ind: Indicators, p: dict) -> tuple:
    """T0 HYPOTHESIS — EMA-200 price crossover with confirmation bars.

    Hypothesis: the raw EMA-200 crossover (ema_200_regime) whipsaws at cycle
    boundaries because a single bar above/below triggers entry/exit.  Requiring
    close to stay above EMA-200 for entry_bars consecutive bars before entering
    filters out noise transitions.  Exit is immediate on close crossing below
    EMA-200 — asymmetric by design (slow in, fast out preserves capital).

    Distinct from ema_slope_above: NO slope condition on the EMA.  The
    hypothesis is that confirmation alone (sustained above) is sufficient.

    Pre-registered as T0 at 2026-04-14.  2 tunable canonical params.
    Params (all canonical):
      ema_len     = 200  (MA_PERIODS)
      entry_bars  = 3    (SLOPE_CONFIRM_BARS) — consecutive bars close > EMA
      cooldown    = 5    (COOLDOWN_BARS, structural — not counted toward tier)
    """
    n = ind.n
    cl = ind.close
    ema = ind.ema(int(p.get("ema_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    above_count = 0
    for i in range(1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - 1]):
            continue
        # Track consecutive bars where close > EMA
        if cl[i] > ema[i]:
            above_count += 1
        else:
            above_count = 0
        # Entry: close has been above EMA for entry_bars consecutive bars
        if above_count == entry_bars:
            entries[i] = True
        # Exit: close crosses below EMA — immediate, no confirmation
        if cl[i - 1] >= ema[i - 1] and cl[i] < ema[i]:
            exits[i] = True
            labels[i] = "T"  # trend break

    return entries, exits, labels


def ema_200_regime(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    ema = ind.ema(p.get("ema_len", 200))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - 1]):
            continue
        # Entry: close crosses above 200-EMA
        if cl[i - 1] <= ema[i - 1] and cl[i] > ema[i]:
            entries[i] = True
        # Exit: close crosses below 200-EMA
        elif cl[i - 1] >= ema[i - 1] and cl[i] < ema[i]:
            exits[i] = True
            labels[i] = "T"  # trend break

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# T1 Grid-Searchable: New signal families (Spike batch 2026-04-14)
# ─────────────────────────────────────────────────────────────────────────────


def roc_above_trend(ind, p):
    """T1: Rate of Change > 0 + close > trend EMA for confirm bars.
    Hypothesis: positive ROC means price is gaining momentum; combined with
    trend filter, this captures momentum regimes and avoids counter-trend."""
    n = ind.n
    cl = ind.close
    roc = ind.roc(int(p.get("roc_len", 20)))
    trend = ind.ema(int(p.get("trend_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(roc[i]) or np.isnan(trend[i]):
            continue
        if roc[i] > 0 and cl[i] > trend[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if roc[i] < 0:
            exits[i] = True
            labels[i] = "R"
    return entries, exits, labels


def stoch_recovery_trend(ind, p):
    """T1: Stochastic %K crosses up through 20 (oversold recovery) + trend EMA.
    Hypothesis: leveraged ETFs mean-revert hard from oversold; entering on
    stochastic recovery above trend catches post-crash rebounds. Exit on
    %K dropping below 50 (momentum fading to neutral)."""
    n = ind.n
    cl = ind.close
    k = ind.stoch_k(int(p.get("stoch_len", 14)))
    trend = ind.ema(int(p.get("trend_len", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(k[i]) or np.isnan(k[i - 1]) or np.isnan(trend[i]):
            continue
        if k[i - 1] < 20 and k[i] >= 20 and cl[i] > trend[i]:
            entries[i] = True
        if k[i] < 50 and k[i - 1] >= 50:
            exits[i] = True
            labels[i] = "K"
    return entries, exits, labels


def adx_di_trend(ind, p):
    """T1: ADX > 20 + DI+ > DI- for confirm bars + trend EMA filter.
    Hypothesis: ADX measures trend strength; DI+/DI- gives direction.
    Strong uptrend = ADX high + DI+ dominant + above trend EMA."""
    n = ind.n
    cl = ind.close
    adx_len = int(p.get("adx_len", 14))
    adx = ind.adx(adx_len)
    dip = ind.di_plus(adx_len)
    dim = ind.di_minus(adx_len)
    trend = ind.ema(int(p.get("trend_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(adx[i]) or np.isnan(dip[i]) or np.isnan(dim[i]) or np.isnan(trend[i]):
            continue
        if adx[i] > 20 and dip[i] > dim[i] and cl[i] > trend[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if dim[i] > dip[i]:
            exits[i] = True
            labels[i] = "A"
    return entries, exits, labels


def keltner_breakout(ind, p):
    """T1: Close breaks above upper Keltner channel + trend EMA filter.
    Hypothesis: Keltner channels are volatility-adjusted — close above upper
    band means price exceeds normal range, signaling trend acceleration.
    Exit on close below lower band (reactive)."""
    n = ind.n
    cl = ind.close
    kc_ema = int(p.get("kc_ema_len", 20))
    kc_mult = float(p.get("kc_atr_mult", 2.0))
    upper = ind.keltner_upper(kc_ema, kc_ema, kc_mult)
    lower = ind.keltner_lower(kc_ema, kc_ema, kc_mult)
    trend = ind.ema(int(p.get("trend_len", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(upper[i]) or np.isnan(lower[i]) or np.isnan(trend[i]):
            continue
        if cl[i] > upper[i] and cl[i] > trend[i]:
            entries[i] = True
        if cl[i] < lower[i]:
            exits[i] = True
            labels[i] = "K"
    return entries, exits, labels


def vol_calm_regime(ind, p):
    """T1: Hold when short realized vol < long realized vol.
    Hypothesis: when short-term volatility declines below long-term average,
    the storm is passing. Pure volatility regime — structurally different
    from price-based signals. Enter on calm transition, exit on storm."""
    n = ind.n
    vol_short = ind.realized_vol(int(p.get("vol_short", 20)))
    vol_long = ind.realized_vol(int(p.get("vol_long", 100)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(vol_short[i]) or np.isnan(vol_long[i]) or vol_long[i] <= 0:
            continue
        if np.isnan(vol_short[i - 1]) or np.isnan(vol_long[i - 1]) or vol_long[i - 1] <= 0:
            continue
        if vol_short[i] < vol_long[i] and vol_short[i - 1] >= vol_long[i - 1]:
            entries[i] = True
        if vol_short[i] >= vol_long[i] and vol_short[i - 1] < vol_long[i - 1]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def macd_hist_trend(ind, p):
    """T1: MACD histogram positive for N bars + close > trend EMA.
    Hypothesis: histogram captures momentum acceleration. Requiring it
    positive for N bars filters noise. More selective than zero-cross
    because histogram leads the MACD line."""
    n = ind.n
    cl = ind.close
    hist = ind.macd_hist(12, 26, 9)
    trend = ind.ema(int(p.get("trend_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    pos_count = 0
    for i in range(1, n):
        if np.isnan(hist[i]) or np.isnan(trend[i]):
            continue
        if hist[i] > 0 and cl[i] > trend[i]:
            pos_count += 1
        else:
            pos_count = 0
        if pos_count == entry_bars:
            entries[i] = True
        if hist[i] < 0:
            exits[i] = True
            labels[i] = "H"
    return entries, exits, labels


def roc_ema_slope(ind, p):
    """T1: Dual momentum — ROC > 0 AND EMA slope positive for confirm bars.
    Hypothesis: two independent momentum signals (price ROC + EMA slope)
    must agree before entry. Reduces false signals because both short-term
    price momentum and underlying trend must be positive simultaneously."""
    n = ind.n
    roc = ind.roc(int(p.get("roc_len", 20)))
    ema = ind.ema(int(p.get("ema_len", 100)))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(roc[i]) or np.isnan(ema[i]) or np.isnan(ema[i - slope_window]):
            continue
        ema_rising = ema[i] > ema[i - slope_window]
        if roc[i] > 0 and ema_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if not ema_rising:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def stoch_cross_trend(ind, p):
    """T1: Stochastic %K > %D for confirm bars + close > trend EMA.
    Hypothesis: %K/%D crossover is a classic momentum signal; combining
    with trend filter ensures entry only in confirmed uptrends. Exit on
    bearish cross (%K drops below %D)."""
    n = ind.n
    cl = ind.close
    stoch_len = int(p.get("stoch_len", 14))
    k = ind.stoch_k(stoch_len)
    d = ind.stoch_d(stoch_len)
    trend = ind.ema(int(p.get("trend_len", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(k[i]) or np.isnan(d[i]) or np.isnan(trend[i]):
            continue
        if k[i] > d[i] and cl[i] > trend[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if not np.isnan(k[i - 1]) and not np.isnan(d[i - 1]):
            if k[i - 1] >= d[i - 1] and k[i] < d[i]:
                exits[i] = True
                labels[i] = "K"
    return entries, exits, labels


def double_ema_slope(ind, p):
    """T1: Both fast and slow EMA slopes positive for N bars.
    Hypothesis: requiring both short-term and long-term EMAs to be rising
    means both momentum horizons agree. Stricter than single-slope but
    higher quality entries. Exit when slow slope turns negative."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_window = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - slope_window]) or np.isnan(slow[i - slope_window]):
            continue
        fast_rising = fast[i] > fast[i - slope_window]
        slow_rising = slow[i] > slow[i - slope_window]
        if fast_rising and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if not slow_rising:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def rsi_roc_combo(ind, p):
    """T1: RSI > 50 AND ROC > 0 AND close > trend EMA.
    Hypothesis: two independent oscillators (RSI + ROC) must both confirm
    bullish conditions along with trend filter. Triple confirmation reduces
    false entries. Exit when RSI drops below 50."""
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    roc = ind.roc(int(p.get("roc_len", 20)))
    trend = ind.ema(int(p.get("trend_len", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(roc[i]) or np.isnan(trend[i]):
            continue
        if rsi[i] > 50 and roc[i] > 0 and cl[i] > trend[i]:
            entries[i] = True
        if rsi[i] < 50:
            exits[i] = True
            labels[i] = "R"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Spike batch 2026-04-14b: Untapped indicator families
# CCI, Williams %R, MFI, OBV, Bollinger Width, TEMA, ATR ratio, combos
# ─────────────────────────────────────────────────────────────────────────────


def cci_regime_trend(ind, p):
    """T1: CCI > 0 + fast EMA > slow EMA for confirm bars. Exit: death cross.
    Hypothesis: CCI confirms bullish regime within a golden cross. Oscillator
    gates entry timing (avoids false golden crosses), death cross exits."""
    n = ind.n
    cci = ind.cci(int(p.get("cci_len", 20)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(cci[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if cci[i] > 0 and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def willr_recovery_trend(ind, p):
    """T1: Williams %R > -50 + fast EMA > slow EMA + confirm. Exit: death cross.
    Hypothesis: Williams %R in upper half of range confirms momentum within a
    golden cross regime. Death cross exit prevents oscillator whipsaw."""
    n = ind.n
    willr = ind.willr(int(p.get("willr_len", 14)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(willr[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if willr[i] > -50 and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def mfi_above_trend(ind, p):
    """T1: MFI > 50 + fast EMA > slow EMA + confirm. Exit: death cross.
    Hypothesis: MFI (volume-weighted RSI) > 50 = buying pressure dominates.
    Volume confirmation gates entry into golden cross regime."""
    n = ind.n
    mfi = ind.mfi(int(p.get("mfi_len", 14)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(1, n):
        if np.isnan(mfi[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if mfi[i] > 50 and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def obv_slope_trend(ind, p):
    """T1: OBV EMA slope positive + fast EMA > slow EMA + confirm. Exit: death cross.
    Hypothesis: rising OBV = accumulation confirms uptrend within golden cross.
    Volume-confirmed entries, death cross exit."""
    n = ind.n
    obv = ind.obv()
    obv_ma = _ema(obv, int(p.get("obv_ema_len", 50)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w, n):
        if np.isnan(obv_ma[i]) or np.isnan(obv_ma[i - slope_w]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        obv_rising = obv_ma[i] > obv_ma[i - slope_w]
        if obv_rising and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def bb_width_regime(ind, p):
    """T1: BB width < SMA (vol calm) + fast EMA > slow EMA. Exit: death cross.
    Hypothesis: calm volatility during golden cross = healthy trend. Entry requires
    both calm vol AND uptrend. Death cross exit."""
    n = ind.n
    bb_w = ind.bb_width(int(p.get("bb_len", 20)))
    bb_w_avg = _sma(bb_w, int(p.get("bb_avg_len", 100)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(bb_w[i]) or np.isnan(bb_w_avg[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if bb_w[i] < bb_w_avg[i] and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def tema_short_slope(ind, p):
    """T1: Short TEMA slope positive + close > TEMA + fast > slow. Exit: death cross.
    Hypothesis: TEMA entry catches trend turns earlier than EMA cross alone.
    Asymmetric: fast TEMA entry, slow death cross exit."""
    n = ind.n
    cl = ind.close
    tema = ind.tema(int(p.get("tema_len", 50)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w, n):
        if np.isnan(tema[i]) or np.isnan(tema[i - slope_w]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        slope_pos = tema[i] > tema[i - slope_w]
        above = cl[i] > tema[i]
        if slope_pos and above and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def cci_willr_combo(ind, p):
    """T1: CCI > 0 AND Williams %R > -50 + fast > slow EMA. Exit: death cross.
    Hypothesis: dual oscillator confirmation (deviation + range families) gates
    entry into golden cross regime. Both must agree. Death cross exit."""
    n = ind.n
    cci = ind.cci(int(p.get("cci_len", 20)))
    willr = ind.willr(int(p.get("willr_len", 14)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(cci[i]) or np.isnan(willr[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if cci[i] > 0 and willr[i] > -50 and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def mfi_obv_trend(ind, p):
    """T1: MFI > 50 AND OBV slope positive + fast > slow EMA. Exit: death cross.
    Hypothesis: volume consensus — MFI + OBV agree — gates golden cross entry."""
    n = ind.n
    mfi = ind.mfi(int(p.get("mfi_len", 14)))
    obv = ind.obv()
    obv_ma = _ema(obv, int(p.get("obv_ema_len", 50)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_w = int(p.get("slope_window", 5))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w, n):
        if np.isnan(mfi[i]) or np.isnan(obv_ma[i]) or np.isnan(obv_ma[i - slope_w]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        obv_rising = obv_ma[i] > obv_ma[i - slope_w]
        if mfi[i] > 50 and obv_rising and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def atr_ratio_trend(ind, p):
    """T1: ATR(short)/ATR(long) < 1.0 + fast > slow EMA. Exit: death cross.
    Hypothesis: low ATR ratio = calm vol = trending. Gates golden cross entry."""
    n = ind.n
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 100)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(atr_s[i]) or np.isnan(atr_l[i]) or atr_l[i] == 0 or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        ratio = atr_s[i] / atr_l[i]
        if ratio < 1.0 and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def bb_cci_combo(ind, p):
    """T1: CCI > 0 AND BB width < average + fast > slow EMA. Exit: death cross.
    Hypothesis: above statistical mean + calm vol + golden cross. Triple filter."""
    n = ind.n
    cci = ind.cci(int(p.get("cci_len", 20)))
    bb_w = ind.bb_width(int(p.get("bb_len", 20)))
    bb_w_avg = _sma(bb_w, int(p.get("bb_avg_len", 100)))
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(cci[i]) or np.isnan(bb_w[i]) or np.isnan(bb_w_avg[i]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        if cci[i] > 0 and bb_w[i] < bb_w_avg[i] and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


# ── Spike batch 2026-04-14c: queued strategies ──
# Macro-overlay and cross-asset strategies using external data (VIX, Treasury,
# XLK, Fed Funds, SGOV) plus advanced technical setups (Keltner squeeze,
# dual TEMA, volume Donchian).  All T1 grid-searchable.


def vix_gc_filter(ind, p):
    """T1: VIX regime filter + golden cross.
    Entry: fast EMA > slow EMA AND VIX < threshold.
    Exit: death cross OR VIX > danger threshold (2x entry threshold).
    When VIX data unavailable, produce no signals."""
    n = ind.n
    if ind.vix is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    vix = ind.vix
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    vix_thresh = float(p.get("vix_threshold", 25))
    vix_danger = vix_thresh * 2
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(vix[i]):
            continue
        if fast[i] > slow[i] and vix[i] < vix_thresh:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
        elif vix[i] > vix_danger:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def treasury_curve_trend(ind, p):
    """T1: EMA slope positive + treasury spread > 0 (not inverted) + confirm.
    Exit: death cross. When treasury spread unavailable, produce no signals."""
    n = ind.n
    if ind.treasury_spread is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    spread = ind.treasury_spread
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w, n):
        if np.isnan(fast[i]) or np.isnan(fast[i - slope_w]) or np.isnan(slow[i]) or np.isnan(spread[i]):
            bull_count = 0
            continue
        slope_pos = fast[i] > fast[i - slope_w]
        curve_ok = spread[i] > 0
        if slope_pos and curve_ok and fast[i] > slow[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def xlk_relative_strength(ind, p):
    """T1: XLK fast EMA > XLK slow EMA AND TECL fast EMA slope positive.
    Exit: XLK death cross (XLK fast < XLK slow).
    When xlk_close unavailable, produce no signals."""
    n = ind.n
    if ind.xlk_close is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    xlk = ind.xlk_close
    xlk_fast_len = int(p.get("xlk_fast", 50))
    xlk_slow_len = int(p.get("xlk_slow", 200))
    xlk_f = _ema(xlk, xlk_fast_len)
    xlk_s = _ema(xlk, xlk_slow_len)
    slope_w = int(p.get("slope_window", 5))
    tecl_fast = ind.ema(int(p.get("fast_ema", 30)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w, n):
        if np.isnan(xlk_f[i]) or np.isnan(xlk_s[i]) or np.isnan(tecl_fast[i]) or np.isnan(tecl_fast[i - slope_w]):
            continue
        xlk_bull = xlk_f[i] > xlk_s[i]
        tecl_slope_pos = tecl_fast[i] > tecl_fast[i - slope_w]
        if xlk_bull and tecl_slope_pos:
            entries[i] = True
        if xlk_f[i] < xlk_s[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def fed_funds_pivot(ind, p):
    """T1: Mean-reversion capitulation strategy.
    Entry: RSI < 30 AND fed funds 3-month slope <= 0 (rates peaked/paused).
    Exit: RSI > 70 OR close > trend EMA.
    When fed_funds_rate unavailable, produce no signals."""
    n = ind.n
    if ind.fed_funds_rate is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    ff = ind.fed_funds_rate
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    trend = ind.ema(int(p.get("trend_len", 100)))
    cl = ind.close
    slope_w = 63  # ~3 months of trading days
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w, n):
        if np.isnan(rsi[i]) or np.isnan(ff[i]) or np.isnan(ff[i - slope_w]) or np.isnan(trend[i]):
            continue
        ff_slope = ff[i] - ff[i - slope_w]
        if rsi[i] < 30 and ff_slope <= 0:
            entries[i] = True
        if rsi[i] > 70:
            exits[i] = True
            labels[i] = "R"
        elif cl[i] > trend[i]:
            exits[i] = True
            labels[i] = "T"
    return entries, exits, labels


def keltner_squeeze_breakout(ind, p):
    """T1: Keltner channel squeeze then breakout.
    Entry: Keltner width < its SMA (squeeze) then close > upper Keltner.
    Exit: close < middle Keltner (the EMA center line)."""
    n = ind.n
    kc_ema_len = int(p.get("kc_ema_len", 20))
    kc_atr_mult = float(p.get("kc_atr_mult", 2.0))
    kc_avg_len = int(p.get("kc_avg_len", 50))
    cl = ind.close
    kc_upper = ind.keltner_upper(kc_ema_len, kc_ema_len, kc_atr_mult)
    kc_lower = ind.keltner_lower(kc_ema_len, kc_ema_len, kc_atr_mult)
    kc_mid = ind.ema(kc_ema_len)
    # Keltner width = (upper - lower) / mid
    kc_width = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(kc_upper[i]) and not np.isnan(kc_lower[i]) and not np.isnan(kc_mid[i]) and kc_mid[i] > 0:
            kc_width[i] = (kc_upper[i] - kc_lower[i]) / kc_mid[i]
    kc_width_avg = _sma(kc_width, kc_avg_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_squeeze = False
    for i in range(1, n):
        if np.isnan(kc_width[i]) or np.isnan(kc_width_avg[i]) or np.isnan(kc_upper[i]) or np.isnan(kc_mid[i]):
            continue
        if kc_width[i] < kc_width_avg[i]:
            in_squeeze = True
        if in_squeeze and cl[i] > kc_upper[i]:
            entries[i] = True
            in_squeeze = False
        if cl[i] < kc_mid[i]:
            exits[i] = True
            labels[i] = "K"
    return entries, exits, labels


def vix_term_proxy(ind, p):
    """T1: VIX term structure proxy.
    Entry: EMA slope positive AND VIX < VIX SMA (contango proxy).
    Exit: VIX > VIX SMA * 1.05 OR death cross.
    When VIX unavailable, produce no signals."""
    n = ind.n
    if ind.vix is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    vix = ind.vix
    vix_avg = ind.vix_sma(int(p.get("vix_sma_len", 30)))
    if vix_avg is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = 5
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w, n):
        if np.isnan(fast[i]) or np.isnan(fast[i - slope_w]) or np.isnan(slow[i]) or np.isnan(vix[i]) or np.isnan(vix_avg[i]):
            continue
        slope_pos = fast[i] > fast[i - slope_w]
        vix_below = vix[i] < vix_avg[i]
        if slope_pos and vix_below and fast[i] > slow[i]:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
        elif vix_avg[i] > 0 and vix[i] > vix_avg[i] * 1.05:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def macd_qqq_bull(ind, p):
    """T1: MACD zero-line crossover in bull regime.
    Entry: MACD line crosses above signal AND XLK 200-SMA slope positive.
    Exit: MACD line crosses below signal.
    When xlk_close unavailable, skip XLK filter (just use MACD cross)."""
    n = ind.n
    macd_l = ind.macd_line()
    macd_s = ind.macd_signal()
    trend_len = int(p.get("trend_len", 200))
    # XLK trend filter (optional)
    xlk_trend = None
    if ind.xlk_close is not None:
        xlk_trend = _sma(ind.xlk_close, trend_len)
    slope_w = 5
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w + 1, n):
        if np.isnan(macd_l[i]) or np.isnan(macd_s[i]) or np.isnan(macd_l[i - 1]) or np.isnan(macd_s[i - 1]):
            continue
        # MACD crosses above signal
        macd_cross_up = macd_l[i] > macd_s[i] and macd_l[i - 1] <= macd_s[i - 1]
        # XLK bull regime check
        xlk_ok = True
        if xlk_trend is not None and not np.isnan(xlk_trend[i]) and not np.isnan(xlk_trend[i - slope_w]):
            xlk_ok = xlk_trend[i] > xlk_trend[i - slope_w]
        if macd_cross_up and xlk_ok:
            entries[i] = True
        # MACD crosses below signal
        macd_cross_dn = macd_l[i] < macd_s[i] and macd_l[i - 1] >= macd_s[i - 1]
        if macd_cross_dn:
            exits[i] = True
            labels[i] = "M"
    return entries, exits, labels


def dual_tema_breakout(ind, p):
    """T1: Dual-timeframe TEMA breakout.
    Entry: Weekly TEMA (synthesized via 5x multiplier) slope positive
    AND daily TEMA slope positive + confirm.
    Exit: death cross (fast < slow EMA) for stability."""
    n = ind.n
    tema_len = int(p.get("tema_len", 20))
    tema_daily = ind.tema(tema_len)
    tema_weekly = ind.tema(tema_len * 5)  # synthesize weekly via 5x multiplier
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w, n):
        if np.isnan(tema_daily[i]) or np.isnan(tema_daily[i - slope_w]) or np.isnan(tema_weekly[i]) or np.isnan(tema_weekly[i - slope_w]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            bull_count = 0
            continue
        weekly_up = tema_weekly[i] > tema_weekly[i - slope_w]
        daily_up = tema_daily[i] > tema_daily[i - slope_w]
        if weekly_up and daily_up:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def vol_donchian_breakout(ind, p):
    """T1: Volume-weighted Donchian breakout.
    Entry: close > Donchian upper(entry_len) AND volume > 1.5x volume SMA.
    Exit: close < Donchian lower(exit_len).
    Constraint: exit_len < entry_len."""
    n = ind.n
    cl = ind.close
    vol = ind.volume
    entry_len = int(p.get("entry_len", 50))
    exit_len = int(p.get("exit_len", 20))
    don_upper = ind.donchian_upper(entry_len)
    don_lower = ind.donchian_lower(exit_len)
    vol_avg = _sma(vol.astype(np.float64), entry_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(don_upper[i]) or np.isnan(vol_avg[i]) or vol_avg[i] == 0:
            continue
        if cl[i] > don_upper[i] and vol[i] > 1.5 * vol_avg[i]:
            entries[i] = True
        if not np.isnan(don_lower[i]) and cl[i] < don_lower[i]:
            exits[i] = True
            labels[i] = "C"
    return entries, exits, labels


def sgov_flight_switch(ind, p):
    """T1: SGOV flight-to-safety switch.
    Entry: fast EMA > slow EMA AND SGOV ROC(10) <= 0 (capital NOT fleeing to safety).
    Exit: death cross OR SGOV ROC > 0.5 (sudden flight to safety).
    When sgov_close unavailable, produce no signals."""
    n = ind.n
    if ind.sgov_close is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    sgov_r = ind.sgov_roc(10)
    if sgov_r is None:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.array([""] * n)
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(sgov_r[i]):
            continue
        if fast[i] > slow[i] and sgov_r[i] <= 0:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
        elif sgov_r[i] > 0.5:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


# ── Spike batch 2026-04-14d: golden cross hybrids ──
# Pre-cross entry, asymmetric pairs, spread-based regime, and multi-confirmation hybrids.
# These exploit two prototyped innovations: pre-cross entry (enter BEFORE golden cross
# when gap is narrowing) and asymmetric pairs (faster entry pair, slower exit pair).


def gc_precross(ind, p):
    """T1: Pre-cross entry — enter BEFORE golden cross when gap is narrowing.
    Entry: fast < slow BUT (fast-slow) > prev (fast-slow) AND fast slope positive
    for entry_bars AND slow slope positive.
    Exit: fast < slow AND gap widening (death cross + divergence)."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 20)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]):
            bull_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        # Pre-cross: fast still below slow but gap is narrowing + both slopes positive
        if gap < 0 and gap > prev_gap and fast_rising and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit: fast < slow AND gap is widening (diverging further below)
        if fast[i] < slow[i] and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_asym_fast_entry(ind, p):
    """T1: Asymmetric fast entry / slow exit.
    Entry: entry_fast EMA > entry_slow EMA AND entry_slow slope positive for entry_bars.
    Exit: exit_fast EMA < exit_slow EMA (different, slower pair)."""
    n = ind.n
    ef = ind.ema(int(p.get("entry_fast", 20)))
    es = ind.ema(int(p.get("entry_slow", 50)))
    xf = ind.ema(int(p.get("exit_fast", 30)))
    xs = ind.ema(int(p.get("exit_slow", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(ef[i]) or np.isnan(es[i]) or np.isnan(xf[i]) or np.isnan(xs[i]) or np.isnan(es[i - slope_w]):
            bull_count = 0
            continue
        golden = ef[i] > es[i]
        es_rising = es[i] > es[i - slope_w]
        if golden and es_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit on slower pair death cross
        if xf[i] < xs[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_tema_asym(ind, p):
    """T1: TEMA fast entry, EMA slow exit.
    Entry: TEMA(tema_len) > EMA(slow_ema) AND TEMA slope positive for entry_bars.
    Exit: EMA(fast_ema) < EMA(slow_ema) death cross."""
    n = ind.n
    tema = ind.tema(int(p.get("tema_len", 30)))
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(tema[i]) or np.isnan(tema[i - slope_w]) or np.isnan(fast[i]) or np.isnan(slow[i]):
            bull_count = 0
            continue
        tema_above = tema[i] > slow[i]
        tema_rising = tema[i] > tema[i - slope_w]
        if tema_above and tema_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_spread_momentum(ind, p):
    """T1: Spread acceleration entry — pure spread-based regime.
    Entry: (fast-slow)/slow > 0 AND increasing for entry_bars AND slow slope positive.
    Exit: (fast-slow)/slow < 0."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    entry_bars = int(p.get("entry_bars", 2))
    slope_w = 5  # hardcoded for slow slope check
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]) or slow[i] == 0 or slow[i - 1] == 0:
            bull_count = 0
            continue
        spread = (fast[i] - slow[i]) / slow[i]
        prev_spread = (fast[i - 1] - slow[i - 1]) / slow[i - 1]
        slow_rising = slow[i] > slow[i - slope_w]
        if spread > 0 and spread > prev_spread and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if spread < 0:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def gc_precross_roc(ind, p):
    """T1: Pre-cross entry with ROC confirmation.
    Entry: fast < slow BUT gap narrowing AND fast slope positive AND ROC > 0.
    Exit: fast < slow AND gap widening."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 20)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    roc = ind.roc(int(p.get("roc_len", 20)))
    slope_w = int(p.get("slope_window", 5))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]) or np.isnan(roc[i]):
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        # Pre-cross: below but narrowing + fast rising + ROC positive
        if gap < 0 and gap > prev_gap and fast_rising and roc[i] > 0:
            entries[i] = True
        # Exit: below and widening
        if fast[i] < slow[i] and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_asym_triple(ind, p):
    """T1: Triple-pair asymmetric — two crosses must agree for entry, one for exit.
    Entry: entry_fast/entry_mid golden cross AND entry_mid/exit_slow golden cross.
    Exit: exit_fast/exit_slow death cross."""
    n = ind.n
    ef = ind.ema(int(p.get("entry_fast", 14)))
    em = ind.ema(int(p.get("entry_mid", 50)))
    xf = ind.ema(int(p.get("exit_fast", 30)))
    xs = ind.ema(int(p.get("exit_slow", 100)))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(ef[i]) or np.isnan(em[i]) or np.isnan(xf[i]) or np.isnan(xs[i]):
            continue
        # Both crosses must agree for entry
        if ef[i] > em[i] and em[i] > xs[i]:
            entries[i] = True
        # Single slower cross for exit
        if xf[i] < xs[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_spread_band(ind, p):
    """T1: Spread threshold entry — symmetric band around zero.
    Entry: (fast-slow)/slow > 1% AND slow slope positive for entry_bars.
    Exit: (fast-slow)/slow < -1%. Threshold hardcoded at 1%."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    entry_bars = int(p.get("entry_bars", 2))
    slope_w = 5  # hardcoded for slow slope check
    threshold = 0.01  # 1% hardcoded
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or slow[i] == 0 or np.isnan(slow[i - slope_w]):
            bull_count = 0
            continue
        spread = (fast[i] - slow[i]) / slow[i]
        slow_rising = slow[i] > slow[i - slope_w]
        if spread > threshold and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if spread < -threshold:
            exits[i] = True
            labels[i] = "S"
    return entries, exits, labels


def gc_precross_vol(ind, p):
    """T1: Pre-cross with volume confirmation.
    Entry: fast < slow BUT gap narrowing AND fast slope positive AND volume > volume SMA.
    Exit: death cross."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 20)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    vol = ind.volume
    vol_avg = _sma(vol.astype(np.float64), 50)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]) or np.isnan(vol_avg[i]):
            bull_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        # Pre-cross: below but narrowing + fast rising + volume above average
        if gap < 0 and gap > prev_gap and fast_rising and vol[i] > vol_avg[i]:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit: death cross
        if fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_asym_slope(ind, p):
    """T1: Asymmetric pairs with strict slope — both entry EMA slopes must be positive.
    Entry: entry_fast > entry_slow AND BOTH slopes positive for entry_bars.
    Exit: exit_fast < exit_slow."""
    n = ind.n
    ef = ind.ema(int(p.get("entry_fast", 20)))
    es = ind.ema(int(p.get("entry_slow", 50)))
    xf = ind.ema(int(p.get("exit_fast", 30)))
    xs = ind.ema(int(p.get("exit_slow", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(ef[i]) or np.isnan(es[i]) or np.isnan(xf[i]) or np.isnan(xs[i]) or np.isnan(ef[i - slope_w]) or np.isnan(es[i - slope_w]):
            bull_count = 0
            continue
        golden = ef[i] > es[i]
        ef_rising = ef[i] > ef[i - slope_w]
        es_rising = es[i] > es[i - slope_w]
        if golden and ef_rising and es_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if xf[i] < xs[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def gc_precross_strict(ind, p):
    """T1: Pre-cross with multi-bar confirmation.
    Entry: fast < slow BUT gap narrowing for entry_bars consecutive bars AND
    fast slope positive for 2*entry_bars AND slow slope positive.
    Exit: death cross + gap widening."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 20)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    narrow_count = 0
    fast_slope_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]) or np.isnan(fast[i - slope_w]) or np.isnan(slow[i - slope_w]):
            narrow_count = 0
            fast_slope_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        # Track consecutive narrowing bars
        if gap < 0 and gap > prev_gap:
            narrow_count += 1
        else:
            narrow_count = 0
        # Track consecutive fast slope positive bars
        if fast_rising:
            fast_slope_count += 1
        else:
            fast_slope_count = 0
        # Entry: narrowing for entry_bars + fast slope for 2*entry_bars + slow rising
        if narrow_count >= entry_bars and fast_slope_count >= 2 * entry_bars and slow_rising:
            entries[i] = True
        # Exit: death cross + gap widening
        if fast[i] < slow[i] and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# gc-pre-VIX: pre-cross entry + VIX panic circuit breaker
# Same pre-cross logic as gc_precross, plus an emergency exit when VIX
# spikes > 30 AND has jumped > 75% in 5 trading days (genuine panic event).
# The VIX exit fires ~4 times in 33 years: Flash Crash, Volmageddon,
# COVID, Japan carry unwind. Death cross handles normal exits.
# ─────────────────────────────────────────────────────────────────────────────


def gc_pre_vix(ind, p):
    """T1: Pre-cross entry + VIX panic circuit breaker.
    Entry: fast < slow BUT gap narrowing + fast slope positive for entry_bars + slow slope positive.
    Exit: (fast < slow AND gap widening) OR (VIX > 30 AND VIX 5-day change > 75%).
    The VIX exit is a safety net for black-swan events, not a regime signal."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 3))
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(max(slope_w + 1, 6), n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]):
            bull_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        # Pre-cross entry: fast still below slow but gap narrowing + both slopes positive
        if gap < 0 and gap > prev_gap and fast_rising and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        # Exit 1: death cross + gap widening (same as gc_precross)
        if fast[i] < slow[i] and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
        # Exit 2: VIX panic circuit breaker — VIX > 30 AND spiked 75%+ in 5 days
        if vix is not None and not np.isnan(vix[i]) and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


def gc_strict_vix(ind, p):
    """T1: gc_precross_strict + VIX panic circuit breaker.
    Entry: pre-cross with multi-bar narrowing + fast slope for 2x entry_bars + slow slope.
    Exit: (death cross + gap widening) OR (VIX > 30 AND 5-day jump > 75%)."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 100)))
    slow = ind.ema(int(p.get("slow_ema", 150)))
    slope_w = int(p.get("slope_window", 5))
    entry_bars = int(p.get("entry_bars", 2))
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    narrow_count = 0
    fast_slope_count = 0
    for i in range(max(slope_w + 1, 6), n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]) or np.isnan(fast[i - slope_w]) or np.isnan(slow[i - slope_w]):
            narrow_count = 0
            fast_slope_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        if gap < 0 and gap > prev_gap:
            narrow_count += 1
        else:
            narrow_count = 0
        if fast_rising:
            fast_slope_count += 1
        else:
            fast_slope_count = 0
        if narrow_count >= entry_bars and fast_slope_count >= 2 * entry_bars and slow_rising:
            entries[i] = True
        # Exit 1: death cross + gap widening
        if fast[i] < slow[i] and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
        # Exit 2: VIX panic circuit breaker
        if vix is not None and not np.isnan(vix[i]) and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


def atr_ratio_vix(ind, p):
    """T1: atr_ratio_trend + VIX panic circuit breaker.
    Entry: ATR(short)/ATR(long) < 1.0 + fast > slow EMA (calm vol + golden cross).
    Exit: death cross OR (VIX > 30 AND 5-day jump > 75%)."""
    n = ind.n
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 100)))
    fast = ind.ema(int(p.get("fast_ema", 30)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(6, n):
        if np.isnan(atr_s[i]) or np.isnan(atr_l[i]) or atr_l[i] == 0 or np.isnan(fast[i]) or np.isnan(slow[i]):
            continue
        ratio = atr_s[i] / atr_l[i]
        if ratio < 1.0 and fast[i] > slow[i]:
            entries[i] = True
        # Exit 1: death cross
        if fast[i] < slow[i]:
            exits[i] = True
            labels[i] = "D"
        # Exit 2: VIX panic circuit breaker
        if vix is not None and not np.isnan(vix[i]) and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Spike batch 2026-04-15a: Diversity strategies (non-crossover signals)
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Spike batch 2026-04-15b: Diagnostic-informed designs
#
# Cycle diagnostics on the gc_* champions reveal three structural weaknesses:
#   1. Miss all pre-2003 bulls (200-bar EMA warmup too slow)
#   2. Death-cross exit fires 44-58% during bulls (cuts gains)
#   3. Poor avoidance of short 2-6 month bears (26-37%)
#
# These strategies target each weakness directly.
# ─────────────────────────────────────────────────────────────────────────────


def gc_atr_trail(ind, p):
    """T1: Golden cross entry (proven) + ATR trailing stop exit (fixes D-in-bull problem).
    Diagnosis: gc_strict_vix's death-cross exit fires 58% during bulls — the
    EMA cross is noisy during pullbacks. Replace it with an ATR trailing stop
    that adapts to volatility. A normal bull pullback won't trigger N×ATR from
    peak, but a true bear regime change will.
    Entry: pre-cross (fast < slow, gap narrowing, both slopes positive) — same as gc_precross.
    Exit: price drops > atr_mult × ATR below highest-close-since-entry.
    VIX panic circuit breaker retained as safety net."""
    n = ind.n
    cl = ind.close
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    atr = ind.atr(int(p.get("atr_period", 20)))
    slope_w = int(p.get("slope_window", 3))
    entry_bars = int(p.get("entry_bars", 2))
    atr_mult = p.get("atr_mult", 3.0)
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    peak_since_entry = 0.0
    in_trade = False
    for i in range(max(slope_w + 1, 6), n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]):
            bull_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        # Pre-cross entry
        if gap < 0 and gap > prev_gap and fast_rising and slow_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
            peak_since_entry = cl[i]
            in_trade = True
        # Track peak
        if in_trade and cl[i] > peak_since_entry:
            peak_since_entry = cl[i]
        # Exit: ATR trailing stop from peak
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0:
            stop_level = peak_since_entry - atr_mult * atr[i]
            if cl[i] < stop_level:
                exits[i] = True
                labels[i] = "ATR"
                in_trade = False
                peak_since_entry = 0.0
        # Exit: VIX panic circuit breaker
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
                peak_since_entry = 0.0
    return entries, exits, labels


def fast_ema_atr_trail(ind, p):
    """T1: Shorter EMAs (faster warmup) + ATR trailing stop.
    Diagnosis: gc_* misses all pre-2003 bulls because EMA(200) needs 800+ bars.
    Use EMA(20-50)/EMA(50-150) for faster engagement. Accept more signals but
    use ATR trailing stop instead of death cross to avoid the D-in-bull problem.
    Entry: fast > slow AND fast slope positive for confirm bars.
    Exit: ATR trailing stop OR VIX panic."""
    n = ind.n
    cl = ind.close
    fast = ind.ema(int(p.get("fast_ema", 20)))
    slow = ind.ema(int(p.get("slow_ema", 100)))
    atr = ind.atr(int(p.get("atr_period", 20)))
    slope_w = int(p.get("slope_window", 3))
    confirm = int(p.get("confirm_bars", 3))
    atr_mult = p.get("atr_mult", 3.0)
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    confirm_count = 0
    peak = 0.0
    in_trade = False
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]):
            confirm_count = 0
            continue
        fast_above = fast[i] > slow[i]
        fast_rising = fast[i] > fast[i - slope_w]
        if fast_above and fast_rising:
            confirm_count += 1
        else:
            confirm_count = 0
        if confirm_count == confirm:
            entries[i] = True
            peak = cl[i]
            in_trade = True
        if in_trade and cl[i] > peak:
            peak = cl[i]
        # ATR trailing stop
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0:
            if cl[i] < peak - atr_mult * atr[i]:
                exits[i] = True
                labels[i] = "ATR"
                in_trade = False
                peak = 0.0
        # VIX panic
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
                peak = 0.0
    return entries, exits, labels


def vix_regime_entry(ind, p):
    """T1: VIX as PRIMARY entry signal (inverts current VIX-as-exit-only approach).
    Hypothesis: VIX declining below threshold = fear subsiding = risk-on.
    VIX rising above threshold = fear building = risk-off.
    The gc_* strategies use VIX only as a panic exit. This strategy uses VIX
    level + direction as the main regime signal, with a trend EMA as confirmation.
    Entry: VIX < entry_vix AND VIX declining (5-bar) AND close > trend EMA.
    Exit: VIX > exit_vix AND VIX rising (5-bar)."""
    n = ind.n
    cl = ind.close
    vix = ind.vix
    trend_ema = ind.ema(int(p.get("trend_len", 100)))
    entry_vix = p.get("entry_vix", 20.0)
    exit_vix = p.get("exit_vix", 25.0)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if vix is None:
        return entries, exits, labels
    for i in range(6, n):
        if np.isnan(vix[i]) or np.isnan(vix[i - 5]) or np.isnan(trend_ema[i]):
            continue
        vix_declining = vix[i] < vix[i - 5]
        vix_rising = vix[i] > vix[i - 5]
        # Entry: low VIX + declining + uptrend
        if vix[i] < entry_vix and vix_declining and cl[i] > trend_ema[i]:
            entries[i] = True
        # Exit: elevated VIX + rising (fear building)
        if vix[i] > exit_vix and vix_rising:
            exits[i] = True
            labels[i] = "VIX"
    return entries, exits, labels


def rsi_bull_regime(ind, p):
    """T1: RSI as a regime indicator — fast warmup (14 bars).
    Diagnosis: EMA(200) warmup misses early bulls. RSI(14) warms up in 14 bars.
    Hypothesis: RSI sustained above 50 = bull regime. RSI dropping below a lower
    threshold = regime change. Asymmetric exit (40 not 50) avoids whipsaw.
    Entry: RSI crosses above 50 AND RSI rising for confirm_bars.
    Exit: RSI drops below exit_level (< 50, asymmetric to avoid whipsaw)
          OR VIX panic circuit breaker."""
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    confirm = int(p.get("confirm_bars", 3))
    exit_level = p.get("exit_level", 40.0)
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    above_count = 0
    for i in range(2, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i - 1]):
            above_count = 0
            continue
        # RSI above 50 and rising
        if rsi[i] > 50 and rsi[i] > rsi[i - 1]:
            above_count += 1
        else:
            above_count = 0
        if above_count == confirm:
            entries[i] = True
        # Exit: RSI drops below exit level (asymmetric)
        if rsi[i] < exit_level:
            exits[i] = True
            labels[i] = "RSI"
        # VIX panic
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


def donchian_vix(ind, p):
    """T1: Donchian channel breakout + VIX safety net.
    Diagnosis: gc_* all use EMA cross. Donchian uses pure price extremes —
    completely different signal family. Fast warmup (N bars).
    Entry: close > highest(entry_len) — new high breakout.
    Exit: close < lowest(exit_len) OR VIX panic.
    Known issue from design guide: pure breakout is slow to re-engage after
    crashes. The shorter exit_len (vs entry_len) mitigates this."""
    n = ind.n
    cl = ind.close
    entry_len = int(p.get("entry_len", 100))
    exit_len = int(p.get("exit_len", 50))
    vix = ind.vix
    highest_arr = ind.highest(entry_len)
    lowest_arr = ind.lowest(exit_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(entry_len, exit_len) + 1, n):
        if np.isnan(highest_arr[i]) or np.isnan(lowest_arr[i]):
            continue
        # Entry: breakout above entry_len-bar high
        if cl[i] >= highest_arr[i]:
            entries[i] = True
        # Exit: breakdown below exit_len-bar low
        if cl[i] <= lowest_arr[i]:
            exits[i] = True
            labels[i] = "Low"
        # VIX panic
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


def gc_slope_no_death(ind, p):
    """T1: Standard golden cross entry but NO death-cross exit.
    Diagnosis: death cross exit fires 58% during bulls. What if we remove it
    entirely and rely only on ATR stop + VIX panic? The hypothesis is that
    staying in longer during bulls is worth the pain of slower bear exits.
    Entry: fast > slow AND slow slope positive for confirm bars.
    Exit: ATR trailing stop OR VIX panic. No EMA cross exit at all."""
    n = ind.n
    cl = ind.close
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    atr = ind.atr(int(p.get("atr_period", 20)))
    slope_w = int(p.get("slope_window", 5))
    confirm = int(p.get("confirm_bars", 3))
    atr_mult = p.get("atr_mult", 3.0)
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    gc_count = 0
    peak = 0.0
    in_trade = False
    for i in range(slope_w + 1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(slow[i - slope_w]):
            gc_count = 0
            continue
        above = fast[i] > slow[i]
        slow_rising = slow[i] > slow[i - slope_w]
        if above and slow_rising:
            gc_count += 1
        else:
            gc_count = 0
        if gc_count == confirm:
            entries[i] = True
            peak = cl[i]
            in_trade = True
        if in_trade and cl[i] > peak:
            peak = cl[i]
        # Only ATR trailing stop — no death cross exit
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0:
            if cl[i] < peak - atr_mult * atr[i]:
                exits[i] = True
                labels[i] = "ATR"
                in_trade = False
                peak = 0.0
        # VIX panic
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
                peak = 0.0
    return entries, exits, labels


def drawdown_recovery(ind, p):
    """T1: Enter when price recovers from a pullback within an uptrend.
    Hypothesis: TECL trends hard. Buying dips that bounce within the trend
    accumulates shares at lower cost. No moving average crossovers.
    Entry: price dropped >thresh% from recent high, then recovered >recover%
           of that drop, AND current close > long EMA (still in uptrend).
    Exit: new drawdown from entry exceeds exit_dd%, OR close < long EMA."""
    n = ind.n
    cl = ind.close
    trend_ema = ind.ema(int(p.get("trend_len", 200)))
    lookback = int(p.get("lookback", 50))
    thresh_pct = p.get("thresh_pct", 15.0)
    recover_pct = p.get("recover_pct", 50.0)  # recover 50% of the dip
    exit_dd_pct = p.get("exit_dd_pct", 20.0)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(lookback + 1, n):
        if np.isnan(trend_ema[i]):
            continue
        recent_high = np.nanmax(cl[i - lookback:i])
        recent_low = np.nanmin(cl[i - lookback // 2:i])  # low in more recent window
        if recent_high == 0:
            continue
        drop_pct = (recent_high - recent_low) / recent_high * 100
        if drop_pct >= thresh_pct and recent_low > 0:
            recovery = (cl[i] - recent_low) / (recent_high - recent_low) * 100
            if recovery >= recover_pct and cl[i] > trend_ema[i]:
                entries[i] = True
        # Exit: drawdown from local peak or trend break
        local_peak = np.nanmax(cl[max(0, i - 20):i + 1])
        if local_peak > 0:
            dd = (local_peak - cl[i]) / local_peak * 100
            if dd >= exit_dd_pct:
                exits[i] = True
                labels[i] = "DD"
                continue
        if cl[i] < trend_ema[i]:
            exits[i] = True
            labels[i] = "Trend"
    return entries, exits, labels


def multi_tf_momentum(ind, p):
    """T1: Multi-timeframe absolute momentum — no MA crosses.
    Hypothesis: when TECL is rising over all three horizons simultaneously,
    a strong trend is in place. When any horizon turns negative, the trend
    is breaking. Different from MA crosses because it compares price to
    its own history, not two averages to each other.
    Entry: close > close[short_lb] AND close > close[med_lb] AND close > close[long_lb]
           sustained for confirm_bars.
    Exit: close < close[short_lb] (shortest horizon fails)."""
    n = ind.n
    cl = ind.close
    short_lb = int(p.get("short_lb", 20))
    med_lb = int(p.get("med_lb", 50))
    long_lb = int(p.get("long_lb", 200))
    confirm = int(p.get("confirm_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(long_lb + 1, n):
        all_up = (cl[i] > cl[i - short_lb] and
                  cl[i] > cl[i - med_lb] and
                  cl[i] > cl[i - long_lb])
        if all_up:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == confirm:
            entries[i] = True
        # Exit: medium horizon fails (short is too noisy on 3x leverage)
        if cl[i] < cl[i - med_lb]:
            exits[i] = True
            labels[i] = "Mom"
    return entries, exits, labels


def rsi_mean_revert_trend(ind, p):
    """T1: RSI mean-reversion entry within a trend.
    Hypothesis: when RSI drops below oversold but price is still above a long
    EMA, it's a pullback not a breakdown. Buy the dip. Sell when RSI gets
    overbought or when trend breaks.
    Entry: RSI < oversold AND close > trend EMA.
    Exit: RSI > overbought OR close < trend EMA."""
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    trend_ema = ind.ema(int(p.get("trend_len", 200)))
    oversold = p.get("oversold", 30.0)
    overbought = p.get("overbought", 75.0)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(trend_ema[i]):
            continue
        # Entry: RSI oversold + uptrend intact
        if rsi[i] < oversold and cl[i] > trend_ema[i]:
            entries[i] = True
        # Exit: overbought (take profit) or trend break
        if rsi[i] > overbought:
            exits[i] = True
            labels[i] = "OB"
        elif cl[i] < trend_ema[i]:
            exits[i] = True
            labels[i] = "Trend"
    return entries, exits, labels


def vol_compression_breakout(ind, p):
    """T1: Volatility compression → breakout.
    Hypothesis: when TECL's realized volatility contracts (ATR as % of price
    hits a low), it's coiling for a move. Enter when price breaks above the
    recent range after compression. Exit when vol expands (danger) and price
    momentum fades. Completely different from VIX — uses TECL's own vol.
    Entry: ATR%price < compress_pct AND close > highest(lookback).
    Exit: ATR%price > expand_pct OR close < EMA(trend_len)."""
    n = ind.n
    cl = ind.close
    atr = ind.atr(int(p.get("atr_period", 14)))
    trend_ema = ind.ema(int(p.get("trend_len", 100)))
    lookback = int(p.get("lookback", 50))
    compress_pct = p.get("compress_pct", 3.0)
    expand_pct = p.get("expand_pct", 8.0)
    highest_arr = ind.highest(lookback)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(lookback + 1, n):
        if np.isnan(atr[i]) or cl[i] == 0 or np.isnan(trend_ema[i]):
            continue
        atr_pct = atr[i] / cl[i] * 100
        # Entry: compressed vol + breakout above range
        if atr_pct < compress_pct and cl[i] >= highest_arr[i]:
            entries[i] = True
        # Exit: vol expansion or trend break
        if atr_pct > expand_pct:
            exits[i] = True
            labels[i] = "VolExp"
        elif cl[i] < trend_ema[i]:
            exits[i] = True
            labels[i] = "Trend"
    return entries, exits, labels


def price_position_regime(ind, p):
    """T1: Price-position within its own range as a regime signal.
    Hypothesis: when price is near its highs AND well above its lows,
    the trend is healthy. When it collapses toward the lows, exit.
    No moving averages. Pure structural price position.
    Entry: close > pct_of_high% of highest(high_lb) AND
           close > (1 + above_low_pct%) * lowest(low_lb).
    Exit: close drops below midpoint of (highest, lowest) over exit_lb."""
    n = ind.n
    cl = ind.close
    high_lb = int(p.get("high_lb", 200))
    low_lb = int(p.get("low_lb", 50))
    exit_lb = int(p.get("exit_lb", 100))
    pct_of_high = p.get("pct_of_high", 90.0)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    highest_arr = ind.highest(high_lb)
    lowest_arr = ind.lowest(low_lb)
    for i in range(max(high_lb, low_lb, exit_lb) + 1, n):
        if np.isnan(highest_arr[i]) or np.isnan(lowest_arr[i]):
            continue
        if highest_arr[i] == 0:
            continue
        near_high = cl[i] >= highest_arr[i] * (pct_of_high / 100)
        above_low = cl[i] > lowest_arr[i] * 1.15  # at least 15% above recent low
        if near_high and above_low:
            entries[i] = True
        # Exit: price drops below midpoint of the exit-lookback range
        exit_high = np.nanmax(cl[max(0, i - exit_lb):i + 1])
        exit_low = np.nanmin(cl[max(0, i - exit_lb):i + 1])
        midpoint = (exit_high + exit_low) / 2
        if cl[i] < midpoint:
            exits[i] = True
            labels[i] = "Mid"
    return entries, exits, labels


def treasury_regime(ind, p):
    """T1: Treasury yield curve as a regime signal.
    Hypothesis: an inverted yield curve (10Y-2Y < 0) signals recession risk.
    Stay in TECL when curve is positive and steepening. Exit when it inverts
    or steepens negatively. Completely macro-driven, no price indicators.
    Entry: spread > 0 AND spread rising over slope_window AND close > EMA.
    Exit: spread < 0 (inverted) OR spread falling for exit_bars."""
    n = ind.n
    cl = ind.close
    spread = ind.treasury_spread
    trend_ema = ind.ema(int(p.get("trend_len", 100)))
    slope_w = int(p.get("slope_window", 5))
    exit_bars = int(p.get("exit_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if spread is None:
        return entries, exits, labels
    fall_count = 0
    for i in range(slope_w + 1, n):
        if np.isnan(spread[i]) or np.isnan(spread[i - slope_w]) or np.isnan(trend_ema[i]):
            fall_count = 0
            continue
        spread_rising = spread[i] > spread[i - slope_w]
        # Entry: positive spread + rising + price in uptrend
        if spread[i] > 0 and spread_rising and cl[i] > trend_ema[i]:
            entries[i] = True
        # Exit: inverted curve
        if spread[i] < 0:
            exits[i] = True
            labels[i] = "Inv"
            fall_count = 0
            continue
        # Exit: sustained spread deterioration
        if spread[i] < spread[i - 1]:
            fall_count += 1
        else:
            fall_count = 0
        if fall_count >= exit_bars and cl[i] < trend_ema[i]:
            exits[i] = True
            labels[i] = "Sprd"
    return entries, exits, labels


def xlk_relative_momentum(ind, p):
    """T1: TECL vs XLK relative strength momentum.
    Hypothesis: when 3x leverage is working (TECL outperforming XLK),
    stay in. When leverage is decaying (TECL underperforming), get out.
    Uses the TECL/XLK ratio, not price directly.
    Entry: ratio rising over lookback AND ratio EMA slope positive.
    Exit: ratio declining over lookback (leverage decay)."""
    n = ind.n
    cl = ind.close
    xlk = ind.xlk_close
    lookback = int(p.get("lookback", 20))
    trend_len = int(p.get("trend_len", 50))
    confirm = int(p.get("confirm_bars", 3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if xlk is None:
        return entries, exits, labels
    # Compute ratio series and its EMA
    ratio = np.where(xlk > 0, cl / xlk, np.nan)
    ratio_ema = _ema(ratio, trend_len)
    rise_count = 0
    for i in range(max(lookback, trend_len) + 1, n):
        if np.isnan(ratio[i]) or np.isnan(ratio[i - lookback]) or np.isnan(ratio_ema[i]) or np.isnan(ratio_ema[i - 1]):
            rise_count = 0
            continue
        ratio_rising = ratio[i] > ratio[i - lookback]
        ema_rising = ratio_ema[i] > ratio_ema[i - 1]
        if ratio_rising and ema_rising:
            rise_count += 1
        else:
            rise_count = 0
        if rise_count == confirm:
            entries[i] = True
        # Exit: ratio declining
        if ratio[i] < ratio[i - lookback]:
            exits[i] = True
            labels[i] = "Decay"
    return entries, exits, labels


def consecutive_strength(ind, p):
    """T1: Consecutive bullish price action.
    Hypothesis: strings of bullish bars (close > open, higher closes) signal
    strong buying. Enter after N consecutive bullish bars. Exit after M
    bearish bars. Pure price action, no computed indicators.
    Entry: N consecutive bars where close > open AND close > prev close.
    Exit: M consecutive bars where close < open AND close < prev close,
          OR hard ATR stop."""
    n = ind.n
    cl = ind.close
    op = ind.open
    atr = ind.atr(int(p.get("atr_period", 14)))
    entry_streak = int(p.get("entry_streak", 5))
    exit_streak = int(p.get("exit_streak", 3))
    atr_mult = p.get("atr_mult", 3.0)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_streak = 0
    bear_streak = 0
    for i in range(1, n):
        # Bullish bar: close > open AND close > prev close
        if cl[i] > op[i] and cl[i] > cl[i - 1]:
            bull_streak += 1
            bear_streak = 0
        elif cl[i] < op[i] and cl[i] < cl[i - 1]:
            bear_streak += 1
            bull_streak = 0
        else:
            bull_streak = 0
            bear_streak = 0
        if bull_streak == entry_streak:
            entries[i] = True
        if bear_streak >= exit_streak:
            exits[i] = True
            labels[i] = "Bear"
        # Hard ATR stop
        if not np.isnan(atr[i]) and i >= 1 and cl[i] < cl[i - 1] - atr[i] * atr_mult:
            exits[i] = True
            labels[i] = "ATR"
    return entries, exits, labels


STRATEGY_REGISTRY = {
    # Grid-searchable T1 concepts (logic functions that accept any canonical param combo).
    # Grid search evaluates these exhaustively over canonical param grids.
    # The GA/spike can also search their STRATEGY_PARAMS ranges if desired.
    "golden_cross_slope":       golden_cross_slope,      # _ma_cross_with_slope — EMA cross + slope + confirm
    "ema_slope_above":          ema_200_slope_above,     # _ema_slope_above — close > EMA + slope + confirm
    "rsi_recovery_ema":         rsi_recovery_ema_200,    # _rsi_recovery_above_ema — RSI oversold + trend
    "rsi_50_above_trend":       rsi_50_above_ema_200,    # RSI sustained > 50 + trend
    "triple_ema_stack":         triple_ema_stack,         # 3-EMA alignment
    "dual_ema_stack":           dual_ema_stack,           # 2-EMA alignment
    "donchian_filter":          donchian_200_100,         # channel breakout + trend filter
    "macd_above_zero_trend":    macd_above_zero_trend,    # MACD zero-cross + trend
    "ema_pure_slope":           ema_100_pure_slope,       # slope-only, no price condition
    "ema_200_confirm":          ema_200_confirm,            # T0: close > EMA-200 with confirm bars
    "ema_200_regime":           ema_200_regime,            # simplest: close > EMA-200
    # Legacy T2 strategies (GA-searched, complex param spaces)
    "montauk_821":              montauk_821,
    "rsi_regime":               rsi_regime,
    "breakout":                 breakout,
    "rsi_regime_trail":         rsi_regime_trail,
    "vol_regime":               vol_regime,
    "ichimoku_trend":           ichimoku_trend,
    "dual_momentum":            dual_momentum,
    "rsi_vol_regime":           rsi_vol_regime,
    "momentum_stayer":          momentum_stayer,
    "donchian_turtle":          donchian_turtle,
    "slope_persistence":        slope_persistence,
    "vix_trend_regime":         vix_trend_regime,
    "steady_trend":             steady_trend,
    "rsi_recovery":             rsi_recovery,
    "ema_regime":               ema_regime,
    # ── T1 grid-searchable: Spike batch 2026-04-14 ──
    "roc_above_trend":          roc_above_trend,
    "stoch_recovery_trend":     stoch_recovery_trend,
    "adx_di_trend":             adx_di_trend,
    "keltner_breakout":         keltner_breakout,
    "vol_calm_regime":          vol_calm_regime,
    "macd_hist_trend":          macd_hist_trend,
    "roc_ema_slope":            roc_ema_slope,
    "stoch_cross_trend":        stoch_cross_trend,
    "double_ema_slope":         double_ema_slope,
    "rsi_roc_combo":            rsi_roc_combo,
    # ── T1 grid-searchable: Spike batch 2026-04-14b (untapped families) ──
    "cci_regime_trend":         cci_regime_trend,
    "willr_recovery_trend":     willr_recovery_trend,
    "mfi_above_trend":          mfi_above_trend,
    "obv_slope_trend":          obv_slope_trend,
    "bb_width_regime":          bb_width_regime,
    "tema_short_slope":         tema_short_slope,
    "cci_willr_combo":          cci_willr_combo,
    "mfi_obv_trend":            mfi_obv_trend,
    "atr_ratio_trend":          atr_ratio_trend,
    "bb_cci_combo":             bb_cci_combo,
    # ── T1 grid-searchable: Spike batch 2026-04-14c (macro + cross-asset + advanced) ──
    "vix_gc_filter":            vix_gc_filter,
    "treasury_curve_trend":     treasury_curve_trend,
    "xlk_relative_strength":    xlk_relative_strength,
    "fed_funds_pivot":          fed_funds_pivot,
    "keltner_squeeze_breakout": keltner_squeeze_breakout,
    "vix_term_proxy":           vix_term_proxy,
    "macd_qqq_bull":            macd_qqq_bull,
    "dual_tema_breakout":       dual_tema_breakout,
    "vol_donchian_breakout":    vol_donchian_breakout,
    "sgov_flight_switch":       sgov_flight_switch,
    # ── T1 grid-searchable: Spike batch 2026-04-14d (golden cross hybrids) ──
    "gc_precross":              gc_precross,
    "gc_asym_fast_entry":       gc_asym_fast_entry,
    "gc_tema_asym":             gc_tema_asym,
    "gc_spread_momentum":       gc_spread_momentum,
    "gc_precross_roc":          gc_precross_roc,
    "gc_asym_triple":           gc_asym_triple,
    "gc_spread_band":           gc_spread_band,
    "gc_precross_vol":          gc_precross_vol,
    "gc_asym_slope":            gc_asym_slope,
    "gc_precross_strict":       gc_precross_strict,
    # ── gc-pre-VIX: pre-cross + VIX panic circuit breaker ──
    "gc_pre_vix":               gc_pre_vix,
    "gc_strict_vix":            gc_strict_vix,
    "atr_ratio_vix":            atr_ratio_vix,
    # ── T1: Spike batch 2026-04-15a (diversity — non-crossover strategies) ──
    "drawdown_recovery":        drawdown_recovery,
    "multi_tf_momentum":        multi_tf_momentum,
    "rsi_mean_revert_trend":    rsi_mean_revert_trend,
    "vol_compression_breakout": vol_compression_breakout,
    "price_position_regime":    price_position_regime,
    "treasury_regime":          treasury_regime,
    "xlk_relative_momentum":    xlk_relative_momentum,
    "consecutive_strength":     consecutive_strength,
    # ── T1: Spike batch 2026-04-15b (diagnostic-informed — fix gc_* weaknesses) ──
    "gc_atr_trail":             gc_atr_trail,
    "fast_ema_atr_trail":       fast_ema_atr_trail,
    "vix_regime_entry":         vix_regime_entry,
    "rsi_bull_regime":          rsi_bull_regime,
    "donchian_vix":             donchian_vix,
    "gc_slope_no_death":        gc_slope_no_death,
}

# Declared validation tier for each strategy family.
# "T0" = hand-authored hypothesis with ≤5 canonical params — pre-registered before any backtest
# "T1" = hand-authored logic with tuned or non-canonical params — registered with grid size up front
# "T2" = optimizer-discovered, or anything pulled from large search — full statistical stack
# See docs/validation-philosophy.md for routing rules.
# Any strategy whose params get touched by the GA is effectively T2 regardless of its
# declared tier — the declared tier is an upper bound on leniency, not a bypass.
STRATEGY_TIERS = {
    # T1 grid-searchable concepts (hand-authored logic + canonical param grid)
    "golden_cross_slope":       "T1",
    "ema_slope_above":          "T1",
    "rsi_recovery_ema":         "T1",
    "rsi_50_above_trend":       "T1",
    "triple_ema_stack":         "T1",
    "dual_ema_stack":           "T1",
    "donchian_filter":          "T1",
    "macd_above_zero_trend":    "T1",
    "ema_pure_slope":           "T1",
    "ema_200_confirm":          "T2",   # run ALL gates — simple strategy should pass everything
    "ema_200_regime":           "T1",
    "montauk_821":              "T2",  # heavily tuned
    "rsi_regime":               "T2",
    "breakout":                 "T2",
    "rsi_regime_trail":         "T2",
    "vol_regime":               "T2",
    "ichimoku_trend":           "T2",
    "dual_momentum":            "T2",
    "rsi_vol_regime":           "T2",
    "momentum_stayer":          "T2",
    "donchian_turtle":          "T2",
    "slope_persistence":        "T2",
    "vix_trend_regime":         "T2",
    "steady_trend":             "T2",
    "rsi_recovery":             "T2",
    "ema_regime":               "T2",
    # ── T1 grid-searchable: Spike batch 2026-04-14 ──
    "roc_above_trend":          "T1",
    "stoch_recovery_trend":     "T1",
    "adx_di_trend":             "T1",
    "keltner_breakout":         "T1",
    "vol_calm_regime":          "T1",
    "macd_hist_trend":          "T1",
    "roc_ema_slope":            "T1",
    "stoch_cross_trend":        "T1",
    "double_ema_slope":         "T1",
    "rsi_roc_combo":            "T1",
    # ── T1 grid-searchable: Spike batch 2026-04-14b (untapped families) ──
    "cci_regime_trend":         "T1",
    "willr_recovery_trend":     "T1",
    "mfi_above_trend":          "T1",
    "obv_slope_trend":          "T1",
    "bb_width_regime":          "T1",
    "tema_short_slope":         "T1",
    "cci_willr_combo":          "T1",
    "mfi_obv_trend":            "T1",
    "atr_ratio_trend":          "T1",
    "bb_cci_combo":             "T1",
    # ── T1 grid-searchable: Spike batch 2026-04-14c (macro + cross-asset + advanced) ──
    "vix_gc_filter":            "T1",
    "treasury_curve_trend":     "T1",
    "xlk_relative_strength":    "T1",
    "fed_funds_pivot":          "T1",
    "keltner_squeeze_breakout": "T1",
    "vix_term_proxy":           "T1",
    "macd_qqq_bull":            "T1",
    "dual_tema_breakout":       "T1",
    "vol_donchian_breakout":    "T1",
    "sgov_flight_switch":       "T1",
    # ── T1 grid-searchable: Spike batch 2026-04-14d (golden cross hybrids) ──
    "gc_precross":              "T1",
    "gc_asym_fast_entry":       "T1",
    "gc_tema_asym":             "T1",
    "gc_spread_momentum":       "T1",
    "gc_precross_roc":          "T1",
    "gc_asym_triple":           "T1",
    "gc_spread_band":           "T1",
    "gc_precross_vol":          "T1",
    "gc_asym_slope":            "T1",
    "gc_precross_strict":       "T1",
    "gc_pre_vix":               "T1",
    "gc_strict_vix":            "T1",
    "atr_ratio_vix":            "T1",
}

# Parameter spaces for each strategy: {param: (min, max, step, type)}
STRATEGY_PARAMS = {
    # ── T1 grid-searchable concepts ──
    # Real canonical ranges for GA (if spike is used) or grid_search.py.
    # grid_search.py defines its own discrete grids from canonical values;
    # these ranges are used by the GA's random_params/mutate_params.
    "golden_cross_slope": {
        "fast_ema":     (20, 100, 10, int),   # canonical: 20, 30, 50, 100
        "slow_ema":     (100, 300, 50, int),   # canonical: 100, 150, 200, 300
        "slope_window": (3, 5, 2, int),        # canonical: 3, 5
        "entry_bars":   (2, 5, 1, int),        # canonical: 2, 3, 5
        "cooldown":     (2, 10, 3, int),
    },
    "ema_slope_above": {
        "ema_len":      (50, 200, 50, int),    # canonical: 50, 100, 150, 200
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "rsi_recovery_ema": {
        "rsi_len":      (7, 21, 7, int),       # canonical: 7, 14, 21
        "trend_len":    (50, 200, 50, int),     # canonical: 50, 100, 150, 200
        "cooldown":     (2, 10, 3, int),
    },
    "rsi_50_above_trend": {
        "rsi_len":      (7, 21, 7, int),
        "trend_len":    (100, 200, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "triple_ema_stack": {
        "short_ema":    (20, 50, 10, int),
        "med_ema":      (50, 150, 50, int),
        "long_ema":     (100, 300, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "dual_ema_stack": {
        "short_ema":    (20, 100, 10, int),
        "long_ema":     (100, 300, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "donchian_filter": {
        "entry_len":    (50, 200, 50, int),
        "exit_len":     (20, 100, 20, int),
        "trend_len":    (50, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "macd_above_zero_trend": {
        "trend_len":    (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "ema_pure_slope": {
        "ema_len":      (50, 200, 50, int),
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "ema_200_confirm": {
        "ema_len":      (100, 200, 50, int),    # canonical: 100, 150, 200
        "entry_bars":   (2, 5, 1, int),          # canonical: 2, 3, 5
        "cooldown":     (2, 10, 3, int),
    },
    "ema_200_regime": {
        "ema_len":      (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "montauk_821": {
        "short_ema": (5, 25, 2, int), "med_ema": (15, 60, 5, int),
        "trend_ema": (30, 120, 10, int), "slope_lookback": (3, 20, 2, int),
        "atr_period": (10, 60, 5, int), "atr_mult": (1.5, 5.0, 0.5, float),
        "quick_ema": (3, 25, 2, int), "quick_lookback": (2, 10, 1, int),
        "quick_thresh": (-15.0, -3.0, 1.0, float), "sell_buffer": (0.0, 1.0, 0.2, float),
        "cooldown": (0, 10, 1, int),
    },
    "rsi_regime": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 45, 5, float), "exit_rsi": (65, 85, 5, float),
        "panic_rsi": (15, 30, 5, float), "cooldown": (0, 20, 5, int),
    },
    "breakout": {
        "lookback": (20, 180, 10, int), "breakout_pct": (0.85, 1.0, 0.02, float),
        "trail_pct": (10, 50, 5, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 25, 5, int),
    },
    "rsi_vol_regime": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 55, 5, float), "exit_rsi": (65, 90, 5, float),
        "panic_rsi": (10, 25, 5, float), "vol_short": (10, 30, 5, int),
        "vol_long": (40, 100, 10, int), "vol_ratio_max": (0.7, 1.2, 0.05, float),
        "vol_exit_ratio": (1.2, 2.0, 0.2, float), "cooldown": (0, 20, 5, int),
    },
    "momentum_stayer": {
        "fast_ema": (10, 40, 5, int), "slow_ema": (30, 120, 10, int),
        "rsi_len": (7, 21, 2, int), "exit_rsi": (20.0, 40.0, 5.0, float),
        "vol_short": (10, 30, 5, int), "vol_long": (40, 120, 10, int),
        "vol_exit_ratio": (1.2, 2.5, 0.2, float), "roc_period": (20, 100, 10, int),
        "cooldown": (0, 25, 5, int),
    },
    "donchian_turtle": {
        "entry_len": (30, 80, 10, int), "exit_len": (10, 40, 5, int),
        "trend_len": (50, 200, 25, int), "cooldown": (0, 20, 5, int),
    },
    "slope_persistence": {
        "ema_len": (30, 80, 10, int), "slope_window": (3, 10, 2, int),
        "entry_bars": (2, 6, 1, int), "exit_bars": (3, 10, 1, int),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "rsi_regime_trail": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 45, 5, float), "trail_pct": (15, 35, 5, float),
        "panic_rsi": (10, 25, 5, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "vol_regime": {
        "vol_short": (10, 30, 5, int), "vol_long": (40, 100, 10, int),
        "trend_len": (50, 200, 25, int), "vol_entry_ratio": (0.6, 1.0, 0.1, float),
        "vol_exit_ratio": (1.2, 2.0, 0.2, float), "trend_buffer": (0.0, 5.0, 1.0, float),
        "cooldown": (0, 20, 5, int),
    },
    "ichimoku_trend": {
        "tenkan_len": (5, 15, 2, int), "kijun_len": (15, 40, 5, int),
        "cloud_len": (30, 80, 10, int), "cloud_buffer": (0.0, 3.0, 0.5, float),
        "atr_period": (10, 40, 10, int), "atr_mult": (2.0, 5.0, 0.5, float),
        "cooldown": (0, 20, 5, int),
    },
    "dual_momentum": {
        "abs_period": (40, 100, 10, int), "short_period": (10, 30, 5, int),
        "trend_len": (50, 200, 25, int), "abs_thresh": (0.0, 15.0, 2.5, float),
        "short_thresh": (0.0, 8.0, 2.0, float), "abs_exit": (-10.0, 0.0, 2.0, float),
        "short_exit": (-15.0, -3.0, 2.0, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "vix_trend_regime": {
        "short_ema": (10, 30, 5, int), "long_ema": (30, 80, 10, int),
        "vix_slow_len": (30, 90, 10, int), "vix_entry_ratio": (0.7, 1.0, 0.05, float),
        "vix_exit_ratio": (1.1, 1.6, 0.1, float), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
    },
    "steady_trend": {
        "ema_len": (30, 120, 10, int), "slope_window": (3, 10, 1, int),
        "entry_bars": (2, 6, 1, int), "exit_bars": (3, 10, 1, int),
    },
    "rsi_recovery": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 45, 5, float), "panic_rsi": (10, 25, 5, float),
        "cooldown": (0, 20, 5, int),
    },
    "ema_regime": {
        "fast_ema": (10, 40, 5, int), "slow_ema": (30, 120, 10, int),
        "entry_confirm": (2, 6, 1, int), "exit_confirm": (2, 8, 1, int),
    },
    # ── T1 grid-searchable: Spike batch 2026-04-14 ──
    "roc_above_trend": {
        "roc_len":      (10, 50, 10, int),
        "trend_len":    (100, 200, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "stoch_recovery_trend": {
        "stoch_len":    (7, 21, 7, int),
        "trend_len":    (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "adx_di_trend": {
        "adx_len":      (7, 21, 7, int),
        "trend_len":    (100, 200, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "keltner_breakout": {
        "kc_ema_len":   (20, 50, 10, int),
        "kc_atr_mult":  (1.5, 2.5, 0.5, float),
        "trend_len":    (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "vol_calm_regime": {
        "vol_short":    (10, 50, 10, int),
        "vol_long":     (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "macd_hist_trend": {
        "trend_len":    (100, 200, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "roc_ema_slope": {
        "roc_len":      (10, 50, 10, int),
        "ema_len":      (100, 200, 50, int),
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "stoch_cross_trend": {
        "stoch_len":    (7, 21, 7, int),
        "trend_len":    (100, 200, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "double_ema_slope": {
        "fast_ema":     (20, 50, 10, int),
        "slow_ema":     (100, 200, 50, int),
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "rsi_roc_combo": {
        "rsi_len":      (7, 21, 7, int),
        "roc_len":      (10, 50, 10, int),
        "trend_len":    (100, 200, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    # ── T1 grid-searchable: Spike batch 2026-04-14b (oscillator-filtered golden cross) ──
    "cci_regime_trend": {
        "cci_len":      (14, 50, 10, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "willr_recovery_trend": {
        "willr_len":    (7, 21, 7, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "mfi_above_trend": {
        "mfi_len":      (7, 21, 7, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "obv_slope_trend": {
        "obv_ema_len":  (20, 100, 20, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "bb_width_regime": {
        "bb_len":       (14, 50, 10, int),
        "bb_avg_len":   (50, 200, 50, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "tema_short_slope": {
        "tema_len":     (20, 50, 10, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "slope_window": (3, 5, 2, int),
        "entry_bars":   (2, 5, 1, int),
        "cooldown":     (2, 10, 3, int),
    },
    "cci_willr_combo": {
        "cci_len":      (14, 50, 10, int),
        "willr_len":    (7, 21, 7, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "mfi_obv_trend": {
        "mfi_len":      (7, 21, 7, int),
        "obv_ema_len":  (20, 100, 20, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "slope_window": (3, 5, 2, int),
        "cooldown":     (2, 10, 3, int),
    },
    "atr_ratio_trend": {
        "atr_short":    (7, 20, 7, int),
        "atr_long":     (50, 200, 50, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    "bb_cci_combo": {
        "cci_len":      (14, 50, 10, int),
        "bb_len":       (14, 50, 10, int),
        "bb_avg_len":   (50, 200, 50, int),
        "fast_ema":     (20, 100, 10, int),
        "slow_ema":     (100, 300, 50, int),
        "cooldown":     (2, 10, 3, int),
    },
    # ── T1 grid-searchable: Spike batch 2026-04-14c (macro + cross-asset + advanced) ──
    "vix_gc_filter": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "vix_threshold":  (20, 50, 10, int),
        "cooldown":       (2, 10, 3, int),
    },
    "treasury_curve_trend": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "xlk_relative_strength": {
        "xlk_fast":       (20, 100, 10, int),
        "xlk_slow":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "cooldown":       (2, 10, 3, int),
    },
    "fed_funds_pivot": {
        "rsi_len":        (7, 21, 7, int),
        "trend_len":      (50, 200, 50, int),
        "cooldown":       (2, 10, 3, int),
    },
    "keltner_squeeze_breakout": {
        "kc_ema_len":     (20, 50, 10, int),
        "kc_atr_mult":    (1.5, 2.5, 0.5, float),
        "kc_avg_len":     (20, 100, 20, int),
        "cooldown":       (2, 10, 3, int),
    },
    "vix_term_proxy": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "vix_sma_len":    (20, 100, 20, int),
        "cooldown":       (2, 10, 3, int),
    },
    "macd_qqq_bull": {
        "trend_len":      (100, 200, 50, int),
        "cooldown":       (2, 10, 3, int),
    },
    "dual_tema_breakout": {
        "tema_len":       (20, 50, 10, int),
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "vol_donchian_breakout": {
        "entry_len":      (50, 200, 50, int),
        "exit_len":       (10, 100, 10, int),
        "cooldown":       (2, 10, 3, int),
    },
    "sgov_flight_switch": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "cooldown":       (2, 10, 3, int),
    },
    # ── T1 grid-searchable: Spike batch 2026-04-14d (golden cross hybrids) ──
    "gc_precross": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_asym_fast_entry": {
        "entry_fast":     (14, 50, 10, int),
        "entry_slow":     (50, 100, 10, int),
        "exit_fast":      (20, 100, 10, int),
        "exit_slow":      (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_tema_asym": {
        "tema_len":       (20, 50, 10, int),
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_spread_momentum": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_precross_roc": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "roc_len":        (10, 50, 10, int),
        "slope_window":   (3, 5, 2, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_asym_triple": {
        "entry_fast":     (14, 50, 10, int),
        "entry_mid":      (30, 100, 10, int),
        "exit_fast":      (20, 100, 10, int),
        "exit_slow":      (100, 300, 50, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_spread_band": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_precross_vol": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_asym_slope": {
        "entry_fast":     (14, 50, 10, int),
        "entry_slow":     (50, 100, 10, int),
        "exit_fast":      (20, 100, 10, int),
        "exit_slow":      (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_precross_strict": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_pre_vix": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_strict_vix": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "atr_ratio_vix": {
        "atr_short":      (7, 20, 7, int),
        "atr_long":       (50, 200, 50, int),
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "cooldown":       (2, 10, 3, int),
    },
    # ── T1: Spike batch 2026-04-15 (diversity) ──
    "drawdown_recovery": {
        "trend_len":      (100, 200, 50, int),
        "lookback":       (50, 200, 50, int),
        "thresh_pct":     (15.0, 25.0, 5.0, float),
        "recover_pct":    (25.0, 75.0, 25.0, float),
        "exit_dd_pct":    (15.0, 25.0, 5.0, float),
    },
    "multi_tf_momentum": {
        "short_lb":       (20, 50, 10, int),
        "med_lb":         (50, 100, 50, int),
        "long_lb":        (100, 200, 50, int),
        "confirm_bars":   (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "rsi_mean_revert_trend": {
        "rsi_len":        (7, 21, 7, int),
        "trend_len":      (100, 200, 50, int),
        "oversold":       (20.0, 40.0, 10.0, float),
        "overbought":     (70.0, 80.0, 5.0, float),
        "cooldown":       (2, 10, 3, int),
    },
    "vol_compression_breakout": {
        "atr_period":     (7, 20, 7, int),
        "trend_len":      (50, 200, 50, int),
        "lookback":       (20, 100, 20, int),
        "compress_pct":   (2.0, 5.0, 1.0, float),
        "expand_pct":     (6.0, 10.0, 2.0, float),
    },
    "price_position_regime": {
        "high_lb":        (100, 200, 50, int),
        "low_lb":         (20, 100, 20, int),
        "exit_lb":        (50, 200, 50, int),
        "pct_of_high":    (85.0, 95.0, 5.0, float),
        "cooldown":       (2, 10, 3, int),
    },
    "treasury_regime": {
        "trend_len":      (50, 200, 50, int),
        "slope_window":   (3, 5, 2, int),
        "exit_bars":      (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "xlk_relative_momentum": {
        "lookback":       (20, 100, 20, int),
        "trend_len":      (20, 100, 20, int),
        "confirm_bars":   (2, 5, 1, int),
        "cooldown":       (2, 10, 3, int),
    },
    "consecutive_strength": {
        "atr_period":     (7, 20, 7, int),
        "entry_streak":   (3, 5, 1, int),
        "exit_streak":    (2, 5, 1, int),
        "atr_mult":       (2.0, 3.0, 0.5, float),
        "cooldown":       (2, 10, 3, int),
    },
    # ── T1: Spike batch 2026-04-15b (diagnostic-informed) ──
    "gc_atr_trail": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "atr_period":     (7, 20, 7, int),
        "slope_window":   (3, 5, 2, int),
        "entry_bars":     (2, 5, 1, int),
        "atr_mult":       (2.0, 3.0, 0.5, float),
    },
    "fast_ema_atr_trail": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (50, 200, 50, int),
        "atr_period":     (7, 20, 7, int),
        "slope_window":   (3, 5, 2, int),
        "confirm_bars":   (2, 5, 1, int),
        "atr_mult":       (2.0, 3.0, 0.5, float),
    },
    "vix_regime_entry": {
        "trend_len":      (50, 200, 50, int),
        "entry_vix":      (15.0, 25.0, 5.0, float),
        "exit_vix":       (25.0, 35.0, 5.0, float),
        "cooldown":       (2, 10, 3, int),
    },
    "rsi_bull_regime": {
        "rsi_len":        (7, 21, 7, int),
        "confirm_bars":   (2, 5, 1, int),
        "exit_level":     (30.0, 45.0, 5.0, float),
        "cooldown":       (2, 10, 3, int),
    },
    "donchian_vix": {
        "entry_len":      (50, 200, 50, int),
        "exit_len":       (20, 100, 20, int),
        "cooldown":       (2, 10, 3, int),
    },
    "gc_slope_no_death": {
        "fast_ema":       (20, 100, 10, int),
        "slow_ema":       (100, 300, 50, int),
        "atr_period":     (7, 20, 7, int),
        "slope_window":   (3, 5, 2, int),
        "confirm_bars":   (2, 5, 1, int),
        "atr_mult":       (2.0, 3.0, 0.5, float),
    },
}
