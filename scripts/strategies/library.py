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
from engine.strategy_engine import Indicators, _ema, _sma


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


# ─────────────────────────────────────────────────────────────────────────────
# GC Enhancement Matrix (2026-04-20) — systematic addon testing on the
# gc_strict_vix base. Each addon adds ONE filter to the proven champion.
# See docs/*NEXT/gc-enhancement-matrix.md for the full rationale.
# Base: gc_strict_vix entry (strict pre-cross + VIX panic exit).
# ─────────────────────────────────────────────────────────────────────────────


def _gc_strict_signals(ind, p):
    """Compute the base gc_strict_vix signal arrays.
    Returns (entries, death, vix_panic, fast, slow) — addons compose from here."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 100)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_w = int(p.get("slope_window", 3))
    entry_bars = int(p.get("entry_bars", 2))
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    death = np.zeros(n, dtype=bool)
    vix_panic = np.zeros(n, dtype=bool)
    narrow_count = 0
    fast_slope_count = 0
    for i in range(max(slope_w + 1, 6), n):
        if (np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1])
                or np.isnan(fast[i - slope_w]) or np.isnan(slow[i - slope_w])):
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
        if fast[i] < slow[i] and gap < prev_gap:
            death[i] = True
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                vix_panic[i] = True
    return entries, death, vix_panic, fast, slow


# ── E1-E6: Exit addons targeting D-exit-in-bull leak (58%) ──


def gc_e1(ind, p):
    """T1 addon E1: gc_strict_vix + XLK trend confirmation on death cross.
    Hypothesis: 3x leverage death crosses are noise when XLK underlying still trends."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    slope_w = int(p.get("slope_window", 3))
    xlk_ema = ind.xlk_ema(int(p.get("xlk_ema_len", 100)))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w + 1, n):
        if death[i]:
            if xlk_ema is None or np.isnan(xlk_ema[i]) or np.isnan(xlk_ema[i - slope_w]):
                exits[i] = True
                labels[i] = "D"
            elif xlk_ema[i] < xlk_ema[i - slope_w]:
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e2(ind, p):
    """T1 addon E2: gc_strict_vix + RSI exit gate.
    Death cross only honored if RSI < threshold (real momentum loss vs bull pullback)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    threshold = float(p.get("rsi_exit_threshold", 45))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i] and not np.isnan(rsi[i]) and rsi[i] < threshold:
            exits[i] = True
            labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e3(ind, p):
    """T1 addon E3: gc_strict_vix + volume-confirmed death cross.
    Death cross only honored if volume > vol_mult * vol_ema (real selling conviction)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vol_mult = float(p.get("vol_mult", 2.0))
    vol_ema = ind.vol_ema(int(p.get("vol_ema_len", 50)))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i] and not np.isnan(vol_ema[i]) and vol_ema[i] > 0:
            if ind.volume[i] > vol_mult * vol_ema[i]:
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e4(ind, p):
    """T1 addon E4: gc_strict_vix + ATR-scaled buffer on death cross.
    Requires fast to drop > atr_buffer_mult * ATR/close below slow before exit fires."""
    entries, _, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    atr = ind.atr(int(p.get("atr_period", 20)))
    atr_buffer_mult = float(p.get("atr_buffer_mult", 1.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(atr[i]) or cl[i] <= 0:
            continue
        buffer_pct = atr_buffer_mult * atr[i] / cl[i]
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        if fast[i] < slow[i] * (1 - buffer_pct) and gap < prev_gap:
            exits[i] = True
            labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e5(ind, p):
    """T1 addon E5: gc_strict_vix + gap acceleration filter.
    Death cross fires only when gap-widening rate accelerates (real trend break)."""
    entries, _, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    accel_threshold = float(p.get("accel_threshold", 0.5))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(2, n):
        if (np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1])
                or np.isnan(fast[i - 2]) or np.isnan(slow[i - 2])):
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        prev_prev_gap = fast[i - 2] - slow[i - 2]
        gap_delta = gap - prev_gap
        prev_gap_delta = prev_gap - prev_prev_gap
        if fast[i] < slow[i] and gap < prev_gap:
            if gap_delta - prev_gap_delta < -accel_threshold:
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e6(ind, p):
    """T1 addon E6: gc_strict_vix entry + ATR trailing stop replaces death cross.
    Pure ATR stop adapts to volatility — bull pullbacks won't trigger N×ATR from peak."""
    entries, _, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    atr = ind.atr(int(p.get("atr_period", 14)))
    atr_mult = float(p.get("atr_mult", 2.5))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    peak = 0.0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            peak = cl[i]
        if in_trade and cl[i] > peak:
            peak = cl[i]
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0:
            if cl[i] < peak - atr_mult * atr[i]:
                exits[i] = True
                labels[i] = "ATR"
                in_trade = False
                peak = 0.0
        if vix_panic[i] and in_trade:
            exits[i] = True
            labels[i] = "V"
            in_trade = False
            peak = 0.0
    return entries, exits, labels


# ── E7-E11: Exit addons targeting short-bear avoidance (37% bottleneck) ──


def gc_e7(ind, p):
    """T1 addon E7: gc_strict_vix + treasury yield curve modes.
    Mode A: exit on death cross within last `lookback` bars when spread<0.
    Mode B: exit immediately on plain fast<slow when spread<0 (no gap-widening req)."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    spread = ind.treasury_spread
    mode = str(p.get("curve_mode", "A"))
    lookback = int(p.get("lookback", 10))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    death_recent = 0
    for i in range(1, n):
        if death[i]:
            death_recent = lookback
        elif death_recent > 0:
            death_recent -= 1
        # Always honor base death cross
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        # Curve modes — extra exit triggers when spread inverted
        if spread is not None and not np.isnan(spread[i]) and spread[i] < 0:
            if mode == "A" and death_recent > 0 and not exits[i]:
                exits[i] = True
                labels[i] = "T"
            elif mode == "B":
                if not np.isnan(fast[i]) and not np.isnan(slow[i]) and fast[i] < slow[i] and not exits[i]:
                    exits[i] = True
                    labels[i] = "T"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e8(ind, p):
    """T1 addon E8: gc_strict_vix + fed funds rate direction modulator.
    During hiking cycles (fed_funds rising over `rate_lookback`), tighten exit:
    plain fast<slow triggers exit (skip gap-widening requirement)."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    ff = ind.fed_funds_rate
    rate_lookback = int(p.get("rate_lookback", 50))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(rate_lookback, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        # Hiking cycle: looser death cross criteria (any fast<slow exits)
        if ff is not None and not np.isnan(ff[i]) and not np.isnan(ff[i - rate_lookback]):
            if ff[i] > ff[i - rate_lookback]:
                if not np.isnan(fast[i]) and not np.isnan(slow[i]) and fast[i] < slow[i] and not exits[i]:
                    exits[i] = True
                    labels[i] = "F"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e9(ind, p):
    """T1 addon E9: gc_strict_vix + SGOV relative flow exit.
    If TECL/SGOV ratio EMA declining for `sgov_lookback` bars AND gap is negative,
    exit early. SGOV data only available post-2020 — pre-2020 falls back to base."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    sgov = ind.sgov_close
    sgov_lookback = int(p.get("sgov_lookback", 20))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    # Compute TECL/SGOV ratio EMA
    if sgov is not None:
        ratio = np.full(n, np.nan)
        for i in range(n):
            if not np.isnan(sgov[i]) and sgov[i] > 0:
                ratio[i] = cl[i] / sgov[i]
        ratio_ema = ind.ema_of("tecl_sgov_ratio", ratio, 20)
    else:
        ratio_ema = None
    for i in range(sgov_lookback, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if (ratio_ema is not None and not np.isnan(ratio_ema[i]) and not np.isnan(ratio_ema[i - sgov_lookback])
                and not np.isnan(fast[i]) and not np.isnan(slow[i])):
            if ratio_ema[i] < ratio_ema[i - sgov_lookback] and (fast[i] - slow[i]) < 0:
                if not exits[i]:
                    exits[i] = True
                    labels[i] = "S"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e10(ind, p):
    """T1 addon E10: gc_strict_vix + realized vol expansion exit.
    Exit when ATR(short)/ATR(long) > vol_ratio_threshold (vol regime change)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 100)))
    threshold = float(p.get("vol_ratio_threshold", 2.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if not np.isnan(atr_s[i]) and not np.isnan(atr_l[i]) and atr_l[i] > 0:
            if atr_s[i] / atr_l[i] > threshold and not exits[i]:
                exits[i] = True
                labels[i] = "R"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e11(ind, p):
    """T1 addon E11: gc_strict_vix + drawdown percentage exit.
    Exit when close < peak_over_lookback * (1 - dd_pct/100).
    Different from ATR trailing: percentage-based, doesn't adapt to vol."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    dd_pct = float(p.get("dd_pct", 20.0))
    dd_lookback = int(p.get("dd_lookback", 100))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(dd_lookback, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        peak = np.nanmax(cl[i - dd_lookback:i + 1])
        if peak > 0 and cl[i] < peak * (1 - dd_pct / 100) and not exits[i]:
            exits[i] = True
            labels[i] = "P"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


# ── E12-E19: Additional exit signals ──


def gc_e12(ind, p):
    """T1 addon E12: gc_strict_vix + MACD histogram divergence exit.
    Exit when MACD histogram negative for `macd_exit_bars` consecutive bars + gap narrowing."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    macd_hist = ind.macd_hist(12, 26, 9)
    bars_required = int(p.get("macd_exit_bars", 3))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    neg_count = 0
    for i in range(1, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if not np.isnan(macd_hist[i]):
            if macd_hist[i] < 0:
                neg_count += 1
            else:
                neg_count = 0
        if neg_count >= bars_required and not exits[i]:
            if not np.isnan(fast[i]) and not np.isnan(slow[i]) and not np.isnan(fast[i - 1]) and not np.isnan(slow[i - 1]):
                gap = fast[i] - slow[i]
                prev_gap = fast[i - 1] - slow[i - 1]
                if gap < prev_gap:
                    exits[i] = True
                    labels[i] = "M"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e13(ind, p):
    """T1 addon E13: gc_strict_vix + slow EMA slope flattening exit.
    Replace death cross with slope-based exit: slow EMA slope < threshold over window."""
    entries, _, vix_panic, _, slow = _gc_strict_signals(ind, p)
    n = ind.n
    window = int(p.get("slope_exit_window", 10))
    threshold = float(p.get("slope_threshold", 0.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(window, n):
        if not np.isnan(slow[i]) and not np.isnan(slow[i - window]):
            slope = (slow[i] - slow[i - window]) / window
            if slope <= threshold:
                exits[i] = True
                labels[i] = "L"
        if vix_panic[i] and not exits[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e14(ind, p):
    """T1 addon E14: gc_strict_vix + N consecutive bearish bars exit.
    Exit when close<open for `bear_bars` consecutive bars (real-time price action)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    bears_required = int(p.get("bear_bars", 5))
    cl = ind.close
    op = ind.open
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bear_count = 0
    for i in range(n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if cl[i] < op[i]:
            bear_count += 1
        else:
            bear_count = 0
        if bear_count >= bears_required and not exits[i]:
            exits[i] = True
            labels[i] = "B"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e15(ind, p):
    """T1 addon E15: gc_strict_vix + gap-down exit.
    Exit when open < prev_close * (1 - gap_down_pct/100) — overnight shock detector."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    gap_pct = float(p.get("gap_down_pct", 5.0))
    cl = ind.close
    op = ind.open
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if cl[i - 1] > 0 and op[i] < cl[i - 1] * (1 - gap_pct / 100) and not exits[i]:
            exits[i] = True
            labels[i] = "G"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e16(ind, p):
    """T1 addon E16: gc_strict_vix + relative-strength deterioration exit.
    NOTE: matrix specifies QQQ but no qqq_close in dataframe — substituting XLK
    (the underlying TECL tracks). Exit when TECL/XLK ratio EMA declining."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    xlk = ind.xlk_close
    ratio_lookback = int(p.get("ratio_lookback", 20))
    ratio_ema_len = int(p.get("ratio_ema", 50))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if xlk is not None:
        ratio = np.full(n, np.nan)
        for i in range(n):
            if not np.isnan(xlk[i]) and xlk[i] > 0:
                ratio[i] = cl[i] / xlk[i]
        ratio_ema = ind.ema_of("tecl_xlk_ratio", ratio, ratio_ema_len)
    else:
        ratio_ema = None
    for i in range(ratio_lookback, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if ratio_ema is not None and not np.isnan(ratio_ema[i]) and not np.isnan(ratio_ema[i - ratio_lookback]):
            if ratio_ema[i] < ratio_ema[i - ratio_lookback] and not exits[i]:
                exits[i] = True
                labels[i] = "X"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_e17(ind, p):
    """T1 addon E17: gc_strict_vix entry + profit-lock trailing tightener.
    Replaces death cross with ATR trailing stop. After profit > profit_lock_pct,
    tighten the multiplier from 3.0 to tight_atr_mult. Locks gains on big winners."""
    entries, _, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    atr = ind.atr(int(p.get("atr_period", 14)))
    base_mult = float(p.get("base_atr_mult", 3.0))
    tight_mult = float(p.get("tight_atr_mult", 1.5))
    profit_pct = float(p.get("profit_lock_pct", 100.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    entry_price = 0.0
    peak = 0.0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            entry_price = cl[i]
            peak = cl[i]
        if in_trade and cl[i] > peak:
            peak = cl[i]
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0 and entry_price > 0:
            pnl = (cl[i] / entry_price - 1) * 100
            mult = tight_mult if pnl > profit_pct else base_mult
            if cl[i] < peak - mult * atr[i]:
                exits[i] = True
                labels[i] = "PL"
                in_trade = False
                entry_price = 0.0
                peak = 0.0
        if vix_panic[i] and in_trade:
            exits[i] = True
            labels[i] = "V"
            in_trade = False
            entry_price = 0.0
            peak = 0.0
    return entries, exits, labels


def gc_e18(ind, p):
    """T1 addon E18: gc_strict_vix + time-in-trade max with slope check.
    After max_bars in trade AND slow EMA slope <= 0, exit (catches topping patterns)."""
    entries, death, vix_panic, _, slow = _gc_strict_signals(ind, p)
    n = ind.n
    max_bars = int(p.get("max_bars", 300))
    slope_w = int(p.get("slope_window", 3))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    entry_bar = 0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            entry_bar = i
        if death[i]:
            exits[i] = True
            labels[i] = "D"
            in_trade = False
        if in_trade and (i - entry_bar) > max_bars and not exits[i]:
            if i >= slope_w and not np.isnan(slow[i]) and not np.isnan(slow[i - slope_w]):
                if slow[i] - slow[i - slope_w] <= 0:
                    exits[i] = True
                    labels[i] = "T"
                    in_trade = False
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
            in_trade = False
    return entries, exits, labels


def gc_e19(ind, p):
    """T1 addon E19: gc_strict_vix + VIX term structure proxy on death cross.
    Death cross only honored if VIX > VIX EMA * (1 + vix_above_pct/100)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    vix_ema = ind.vix_ema(int(p.get("vix_ema_len", 50)))
    pct = float(p.get("vix_above_pct", 10.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i]:
            if vix is None or vix_ema is None or np.isnan(vix[i]) or np.isnan(vix_ema[i]):
                exits[i] = True
                labels[i] = "D"
            elif vix[i] > vix_ema[i] * (1 + pct / 100):
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


# ── N1-N14: Entry addons (gate base entries with extra filters) ──


def _compose_base_exits(n, death, vix_panic):
    """Helper: combine death + vix_panic into (exits, labels) arrays."""
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return exits, labels


def gc_n1(ind, p):
    """T1 addon N1: gc_strict_vix entry gated by VIX < entry_vix_max."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    threshold = float(p.get("entry_vix_max", 25.0))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and vix is not None and not np.isnan(vix[i]) and vix[i] < threshold:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n2(ind, p):
    """T1 addon N2: gc_strict_vix entry gated by ADX > adx_threshold (trend strength)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    adx = ind.adx(int(p.get("adx_len", 14)))
    threshold = float(p.get("adx_threshold", 20.0))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and not np.isnan(adx[i]) and adx[i] > threshold:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n3(ind, p):
    """T1 addon N3: gc_strict_vix entry gated by XLK EMA rising (underlying trend)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    slope_w = int(p.get("slope_window", 3))
    xlk_ema = ind.xlk_ema(int(p.get("xlk_ema_len", 100)))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(slope_w, n):
        if not entries[i]:
            continue
        if xlk_ema is None or np.isnan(xlk_ema[i]) or np.isnan(xlk_ema[i - slope_w]):
            continue
        if xlk_ema[i] > xlk_ema[i - slope_w]:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n4(ind, p):
    """T1 addon N4: gc_strict_vix entry suppressed during post-crash recovery.
    After drawdown >crash_threshold% from ATH, require close > trough * (1+min_recovery%)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    crash_thresh = float(p.get("crash_threshold", 40.0))
    min_recovery = float(p.get("min_recovery_pct", 20.0))
    new_entries = np.zeros(n, dtype=bool)
    ath = -np.inf
    in_crash = False
    trough = np.inf
    for i in range(n):
        if cl[i] > ath:
            ath = cl[i]
            in_crash = False
            trough = np.inf
        if ath > 0 and (ath - cl[i]) / ath * 100 > crash_thresh:
            in_crash = True
        if in_crash:
            if cl[i] < trough:
                trough = cl[i]
            if trough > 0 and cl[i] > trough * (1 + min_recovery / 100):
                in_crash = False
                trough = np.inf
        if entries[i] and not in_crash:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n5(ind, p):
    """T1 addon N5: gc_strict_vix entry strengthened — gap narrowing rate must increase.
    Replaces simple narrowing condition with second-derivative confirmation."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 100)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    slope_w = int(p.get("slope_window", 3))
    entry_bars = int(p.get("entry_bars", 2))
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    death = np.zeros(n, dtype=bool)
    vix_panic = np.zeros(n, dtype=bool)
    narrow_count = 0
    fast_slope_count = 0
    for i in range(max(slope_w + 1, 6), n):
        if (np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1])
                or np.isnan(fast[i - 2]) or np.isnan(slow[i - 2])
                or np.isnan(fast[i - slope_w]) or np.isnan(slow[i - slope_w])):
            narrow_count = 0
            fast_slope_count = 0
            continue
        gap = fast[i] - slow[i]
        prev_gap = fast[i - 1] - slow[i - 1]
        prev_prev_gap = fast[i - 2] - slow[i - 2]
        narrow_rate = gap - prev_gap
        prev_narrow_rate = prev_gap - prev_prev_gap
        fast_rising = fast[i] > fast[i - slope_w]
        slow_rising = slow[i] > slow[i - slope_w]
        # Stronger condition: narrowing rate accelerating (narrow_rate > prev_narrow_rate)
        if gap < 0 and narrow_rate > 0 and narrow_rate > prev_narrow_rate:
            narrow_count += 1
        else:
            narrow_count = 0
        if fast_rising:
            fast_slope_count += 1
        else:
            fast_slope_count = 0
        if narrow_count >= entry_bars and fast_slope_count >= 2 * entry_bars and slow_rising:
            entries[i] = True
        if fast[i] < slow[i] and gap < prev_gap:
            death[i] = True
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                vix_panic[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return entries, exits, labels


def gc_n6(ind, p):
    """T1 addon N6: gc_strict_vix entry suppressed during May-Sep (or Jun-Sep) — seasonality."""
    import pandas as pd
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    months_off = str(p.get("seasonal_months_off", "May-Sep"))
    if months_off == "May-Sep":
        skip_months = {5, 6, 7, 8, 9}
    else:  # Jun-Sep
        skip_months = {6, 7, 8, 9}
    months = pd.DatetimeIndex(ind.dates).month
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and months[i] not in skip_months:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n7(ind, p):
    """T1 addon N7: gc_strict_vix entry gated by volume > vol_entry_mult * vol_ema."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vol_mult = float(p.get("vol_entry_mult", 1.5))
    vol_ema = ind.vol_ema(int(p.get("vol_ema_len", 50)))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and not np.isnan(vol_ema[i]) and vol_ema[i] > 0:
            if ind.volume[i] > vol_mult * vol_ema[i]:
                new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n8(ind, p):
    """T1 addon N8: gc_strict_vix entry gated by MACD > 0 (12,26,9)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    macd = ind.macd_line(12, 26)
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and not np.isnan(macd[i]) and macd[i] > 0:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n9(ind, p):
    """T1 addon N9: gc_strict_vix entry gated by Bollinger Band squeeze.
    Entry only when bb_width is at its squeeze_lookback minimum (coiling)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    bb_len = int(p.get("bb_len", 20))
    squeeze_lookback = int(p.get("squeeze_lookback", 100))
    bb_width = ind.bb_width(bb_len)
    new_entries = np.zeros(n, dtype=bool)
    for i in range(squeeze_lookback, n):
        if not entries[i] or np.isnan(bb_width[i]):
            continue
        window = bb_width[i - squeeze_lookback:i + 1]
        if not np.all(np.isnan(window)):
            min_width = np.nanmin(window)
            if bb_width[i] <= min_width * 1.0001:  # at or near floor
                new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n10(ind, p):
    """T1 addon N10: gc_strict_vix entry gated by bullish bar (close > open)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and ind.close[i] > ind.open[i]:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n11(ind, p):
    """T1 addon N11: gc_strict_vix entry gated by VIX declining over vix_slope_window."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    window = int(p.get("vix_slope_window", 5))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(window, n):
        if not entries[i] or vix is None:
            continue
        if not np.isnan(vix[i]) and not np.isnan(vix[i - window]) and vix[i] < vix[i - window]:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n12(ind, p):
    """T1 addon N12: gc_strict_vix entry gated by treasury_spread > 0 (no recession signal)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    spread = ind.treasury_spread
    new_entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if entries[i] and spread is not None and not np.isnan(spread[i]) and spread[i] > 0:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n13(ind, p):
    """T1 addon N13: gc_strict_vix entry gated by short AND medium horizon positive returns."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    short_lb = int(p.get("short_ret_lb", 20))
    med_lb = int(p.get("med_ret_lb", 50))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(med_lb, n):
        if entries[i] and cl[i - short_lb] > 0 and cl[i - med_lb] > 0:
            if cl[i] > cl[i - short_lb] and cl[i] > cl[i - med_lb]:
                new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_n14(ind, p):
    """T1 addon N14: gc_strict_vix entry gated by close > high_lookback high * proximity%."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    proximity = float(p.get("high_proximity_pct", 90.0))
    high_lb = int(p.get("high_lookback", 50))
    high_arr = ind.highest(high_lb)
    new_entries = np.zeros(n, dtype=bool)
    for i in range(high_lb, n):
        if entries[i] and not np.isnan(high_arr[i]) and high_arr[i] > 0:
            if cl[i] > high_arr[i] * proximity / 100:
                new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


# ── S1-S3: Structural addons (modify trade lifecycle / cooldown / re-entry) ──


def gc_s1(ind, p):
    """T1 addon S1: gc_strict_vix + adaptive cooldown.
    Suppress entries for `base_cooldown * max(1, atr_short/atr_long * vol_cooldown_mult)`
    bars after each exit. Implements cooldown internally rather than via backtest()."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    base_cooldown = int(p.get("base_cooldown", 5))
    vol_mult = float(p.get("vol_cooldown_mult", 2.0))
    atr_s = ind.atr(14)
    atr_l = ind.atr(100)
    exits, labels = _compose_base_exits(n, death, vix_panic)
    new_entries = np.zeros(n, dtype=bool)
    cooldown_until = -1
    for i in range(n):
        if exits[i]:
            ratio = 1.0
            if not np.isnan(atr_s[i]) and not np.isnan(atr_l[i]) and atr_l[i] > 0:
                ratio = atr_s[i] / atr_l[i]
            cd = base_cooldown * max(1, int(ratio * vol_mult))
            cooldown_until = i + cd
        if entries[i] and i > cooldown_until:
            new_entries[i] = True
    return new_entries, exits, labels


def gc_s2(ind, p):
    """T1 addon S2: gc_strict_vix + bear regime memory.
    After drawdown >bear_threshold% from ATH, require 2x entry confirmation
    (i.e. require an additional confirmed entry signal in next bar) for next
    bear_memory_bars bars."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    bear_thresh = float(p.get("bear_threshold_pct", 50.0))
    memory_bars = int(p.get("bear_memory_bars", 100))
    exits, labels = _compose_base_exits(n, death, vix_panic)
    new_entries = np.zeros(n, dtype=bool)
    ath = -np.inf
    bear_memory_until = -1
    for i in range(n):
        if cl[i] > ath:
            ath = cl[i]
        if ath > 0 and (ath - cl[i]) / ath * 100 > bear_thresh:
            bear_memory_until = i + memory_bars
        if entries[i]:
            if i <= bear_memory_until:
                # Require 2x confirmation: previous bar also had entry signal
                if i > 0 and entries[i - 1]:
                    new_entries[i] = True
            else:
                new_entries[i] = True
    return new_entries, exits, labels


def gc_s3(ind, p):
    """T1 addon S3: gc_strict_vix + asymmetric VIX re-entry.
    After a V exit, suppress new entries until VIX drops below vix_reentry_below."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    reentry_threshold = float(p.get("vix_reentry_below", 25.0))
    exits, labels = _compose_base_exits(n, death, vix_panic)
    new_entries = np.zeros(n, dtype=bool)
    awaiting_vix_drop = False
    for i in range(n):
        if vix_panic[i]:
            awaiting_vix_drop = True
        if awaiting_vix_drop:
            if vix is not None and not np.isnan(vix[i]) and vix[i] < reentry_threshold:
                awaiting_vix_drop = False
        if entries[i] and not awaiting_vix_drop:
            new_entries[i] = True
    return new_entries, exits, labels


# ── C1-C8: Combo addons stacking top individual performers (per matrix) ──


def gc_c1(ind, p):
    """T1 combo C1: VIX entry gate (N1) + XLK exit confirmation (E1).
    Entry: gc_strict_vix + VIX < entry_vix_max.
    Exit: (death AND xlk_ema declining) OR vix_panic."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    slope_w = int(p.get("slope_window", 3))
    vix_max = float(p.get("entry_vix_max", 25.0))
    xlk_ema = ind.xlk_ema(int(p.get("xlk_ema_len", 100)))
    new_entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w + 1, n):
        if entries[i] and vix is not None and not np.isnan(vix[i]) and vix[i] < vix_max:
            new_entries[i] = True
        if death[i]:
            if xlk_ema is None or np.isnan(xlk_ema[i]) or np.isnan(xlk_ema[i - slope_w]):
                exits[i] = True
                labels[i] = "D"
            elif xlk_ema[i] < xlk_ema[i - slope_w]:
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return new_entries, exits, labels


def gc_c2(ind, p):
    """T1 combo C2: RSI exit gate (E2) + treasury curve mode B (E7).
    Death cross requires RSI < threshold; spread<0 forces tighter exit."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    rsi_thresh = float(p.get("rsi_exit_threshold", 45))
    spread = ind.treasury_spread
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if death[i] and not np.isnan(rsi[i]) and rsi[i] < rsi_thresh:
            exits[i] = True
            labels[i] = "D"
        # Treasury mode B: when spread<0, fast<slow alone exits
        if spread is not None and not np.isnan(spread[i]) and spread[i] < 0:
            if not np.isnan(fast[i]) and not np.isnan(slow[i]) and fast[i] < slow[i] and not exits[i]:
                exits[i] = True
                labels[i] = "T"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_c3(ind, p):
    """T1 combo C3: XLK exit (E1) + realized vol expansion exit (E10).
    Triple exit: (death AND xlk declining) OR (atr_short/atr_long > thresh) OR vix_panic."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    slope_w = int(p.get("slope_window", 3))
    xlk_ema = ind.xlk_ema(int(p.get("xlk_ema_len", 100)))
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 100)))
    vol_thresh = float(p.get("vol_ratio_threshold", 2.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(slope_w + 1, n):
        if death[i]:
            if xlk_ema is None or np.isnan(xlk_ema[i]) or np.isnan(xlk_ema[i - slope_w]):
                exits[i] = True
                labels[i] = "D"
            elif xlk_ema[i] < xlk_ema[i - slope_w]:
                exits[i] = True
                labels[i] = "D"
        if not np.isnan(atr_s[i]) and not np.isnan(atr_l[i]) and atr_l[i] > 0:
            if atr_s[i] / atr_l[i] > vol_thresh and not exits[i]:
                exits[i] = True
                labels[i] = "R"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_c4(ind, p):
    """T1 combo C4: best entry (RSI exit gate E2) + best exit (treasury curve A E7).
    Note: matrix says 'top entry + top exit'. Top entry-side individual = N1 (VIX gate)
    or N4 (post-crash), but the strongest standalone *fitness* came from the exit side.
    We pair N1 (top entry filter) with E7 (top exit filter)."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    vix = ind.vix
    spread = ind.treasury_spread
    vix_max = float(p.get("entry_vix_max", 25.0))
    lookback = int(p.get("lookback", 20))
    new_entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    death_recent = 0
    for i in range(1, n):
        if entries[i] and vix is not None and not np.isnan(vix[i]) and vix[i] < vix_max:
            new_entries[i] = True
        if death[i]:
            death_recent = lookback
            exits[i] = True
            labels[i] = "D"
        elif death_recent > 0:
            death_recent -= 1
        if spread is not None and not np.isnan(spread[i]) and spread[i] < 0:
            if death_recent > 0 and not exits[i]:
                exits[i] = True
                labels[i] = "T"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return new_entries, exits, labels


def gc_c5(ind, p):
    """T1 combo C5: XLK exit (E1) + profit-lock trailing tightener (E17).
    Address D-in-bull AND giving-back-gains. Replaces death cross with XLK-gated
    death cross + ATR trailing stop that tightens after profit_lock_pct."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    slope_w = int(p.get("slope_window", 3))
    xlk_ema = ind.xlk_ema(int(p.get("xlk_ema_len", 100)))
    atr = ind.atr(int(p.get("atr_period", 14)))
    base_mult = float(p.get("base_atr_mult", 3.0))
    tight_mult = float(p.get("tight_atr_mult", 1.5))
    profit_pct = float(p.get("profit_lock_pct", 100.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    entry_price = 0.0
    peak = 0.0
    for i in range(slope_w + 1, n):
        if entries[i] and not in_trade:
            in_trade = True
            entry_price = cl[i]
            peak = cl[i]
        if in_trade and cl[i] > peak:
            peak = cl[i]
        # XLK-gated death cross
        if in_trade and death[i]:
            if xlk_ema is None or np.isnan(xlk_ema[i]) or np.isnan(xlk_ema[i - slope_w]):
                exits[i] = True
                labels[i] = "D"
                in_trade = False
                entry_price = peak = 0.0
            elif xlk_ema[i] < xlk_ema[i - slope_w]:
                exits[i] = True
                labels[i] = "D"
                in_trade = False
                entry_price = peak = 0.0
        # Profit-lock trailing stop
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0 and entry_price > 0 and not exits[i]:
            pnl = (cl[i] / entry_price - 1) * 100
            mult = tight_mult if pnl > profit_pct else base_mult
            if cl[i] < peak - mult * atr[i]:
                exits[i] = True
                labels[i] = "PL"
                in_trade = False
                entry_price = peak = 0.0
        if vix_panic[i] and in_trade:
            exits[i] = True
            labels[i] = "V"
            in_trade = False
            entry_price = peak = 0.0
    return entries, exits, labels


def gc_c6(ind, p):
    """T1 combo C6: RSI exit gate (E2) + VIX term structure proxy (E19).
    Death cross requires both RSI < threshold AND VIX > VIX_EMA*(1+pct)."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    rsi_thresh = float(p.get("rsi_exit_threshold", 45))
    vix = ind.vix
    vix_ema = ind.vix_ema(int(p.get("vix_ema_len", 50)))
    vix_pct = float(p.get("vix_above_pct", 10.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if death[i] and not np.isnan(rsi[i]) and rsi[i] < rsi_thresh:
            ok_vix = (vix is None or vix_ema is None or np.isnan(vix[i]) or np.isnan(vix_ema[i])
                      or vix[i] > vix_ema[i] * (1 + vix_pct / 100))
            if ok_vix:
                exits[i] = True
                labels[i] = "D"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_c7(ind, p):
    """T1 combo C7: treasury curve A (E7) + bear regime memory (S2) + adaptive cooldown (S1).
    Best exit filter combined with smarter re-entry timing."""
    entries, death, vix_panic, _, _ = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    spread = ind.treasury_spread
    lookback = int(p.get("lookback", 20))
    bear_thresh = float(p.get("bear_threshold_pct", 50.0))
    memory_bars = int(p.get("bear_memory_bars", 100))
    base_cooldown = int(p.get("base_cooldown", 5))
    vol_mult = float(p.get("vol_cooldown_mult", 2.0))
    atr_s = ind.atr(14)
    atr_l = ind.atr(100)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    death_recent = 0
    for i in range(1, n):
        if death[i]:
            death_recent = lookback
            exits[i] = True
            labels[i] = "D"
        elif death_recent > 0:
            death_recent -= 1
        if spread is not None and not np.isnan(spread[i]) and spread[i] < 0:
            if death_recent > 0 and not exits[i]:
                exits[i] = True
                labels[i] = "T"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    new_entries = np.zeros(n, dtype=bool)
    ath = -np.inf
    bear_memory_until = -1
    cooldown_until = -1
    for i in range(n):
        if cl[i] > ath:
            ath = cl[i]
        if ath > 0 and (ath - cl[i]) / ath * 100 > bear_thresh:
            bear_memory_until = i + memory_bars
        if exits[i]:
            ratio = 1.0
            if not np.isnan(atr_s[i]) and not np.isnan(atr_l[i]) and atr_l[i] > 0:
                ratio = atr_s[i] / atr_l[i]
            cd = base_cooldown * max(1, int(ratio * vol_mult))
            cooldown_until = i + cd
        if entries[i] and i > cooldown_until:
            if i <= bear_memory_until:
                if i > 0 and entries[i - 1]:
                    new_entries[i] = True
            else:
                new_entries[i] = True
    return new_entries, exits, labels


def gc_c8(ind, p):
    """T1 combo C8: full defense stack — treasury A exit + RSI exit gate + profit-lock trail
    + VIX entry gate + post-crash recovery gate. Maximum filtering."""
    entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    cl = ind.close
    spread = ind.treasury_spread
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    rsi_thresh = float(p.get("rsi_exit_threshold", 45))
    lookback = int(p.get("lookback", 20))
    vix = ind.vix
    vix_max = float(p.get("entry_vix_max", 25.0))
    crash_thresh = float(p.get("crash_threshold", 40.0))
    min_recovery = float(p.get("min_recovery_pct", 20.0))
    atr = ind.atr(int(p.get("atr_period", 14)))
    base_mult = float(p.get("base_atr_mult", 3.0))
    tight_mult = float(p.get("tight_atr_mult", 1.5))
    profit_pct = float(p.get("profit_lock_pct", 100.0))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    new_entries = np.zeros(n, dtype=bool)
    in_trade = False
    entry_price = 0.0
    peak = 0.0
    death_recent = 0
    ath = -np.inf
    in_crash = False
    trough = np.inf
    for i in range(1, n):
        # Track ATH and crash recovery state
        if cl[i] > ath:
            ath = cl[i]
            in_crash = False
            trough = np.inf
        if ath > 0 and (ath - cl[i]) / ath * 100 > crash_thresh:
            in_crash = True
        if in_crash:
            if cl[i] < trough:
                trough = cl[i]
            if trough > 0 and cl[i] > trough * (1 + min_recovery / 100):
                in_crash = False
                trough = np.inf
        # Entry gates: VIX + post-crash
        entry_ok = (entries[i]
                    and not in_crash
                    and vix is not None and not np.isnan(vix[i]) and vix[i] < vix_max)
        if entry_ok and not in_trade:
            new_entries[i] = True
            in_trade = True
            entry_price = cl[i]
            peak = cl[i]
        if in_trade and cl[i] > peak:
            peak = cl[i]
        # Exit: RSI-gated death cross
        if in_trade and death[i] and not np.isnan(rsi[i]) and rsi[i] < rsi_thresh:
            exits[i] = True
            labels[i] = "D"
            in_trade = False
            entry_price = peak = 0.0
        # Track death cross window for treasury exit
        if death[i]:
            death_recent = lookback
        elif death_recent > 0:
            death_recent -= 1
        if in_trade and spread is not None and not np.isnan(spread[i]) and spread[i] < 0:
            if death_recent > 0 and not exits[i]:
                exits[i] = True
                labels[i] = "T"
                in_trade = False
                entry_price = peak = 0.0
        # Profit-lock trail
        if in_trade and not np.isnan(atr[i]) and atr[i] > 0 and entry_price > 0 and not exits[i]:
            pnl = (cl[i] / entry_price - 1) * 100
            mult = tight_mult if pnl > profit_pct else base_mult
            if cl[i] < peak - mult * atr[i]:
                exits[i] = True
                labels[i] = "PL"
                in_trade = False
                entry_price = peak = 0.0
        if vix_panic[i] and in_trade:
            exits[i] = True
            labels[i] = "V"
            in_trade = False
            entry_price = peak = 0.0
    return new_entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Velvet Jaguar Overlays 2026-04-20 (Round 1) — VJ = gc_n8 base, one overlay.
# See docs/*NEXT/brainstorm-2026-04-20-velvet-jaguar-gaps.md for rationale.
# VJ entry = _gc_strict_signals + MACD(12,26) > 0. Exits keep D and V.
# ─────────────────────────────────────────────────────────────────────────────


def _vj_base(ind, p):
    """Returns VJ (gc_n8) base signals: entries with MACD>0 filter, death, vix_panic."""
    strict_entries, death, vix_panic, fast, slow = _gc_strict_signals(ind, p)
    n = ind.n
    macd = ind.macd_line(12, 26)
    entries = np.zeros(n, dtype=bool)
    for i in range(n):
        if strict_entries[i] and not np.isnan(macd[i]) and macd[i] > 0:
            entries[i] = True
    return entries, death, vix_panic, fast, slow


def gc_vjx(ind, p):
    """T1 addon A1: VJ + dual-confirmed VIX shock exit.
    Exit when VIX/VIX[-look] > vix_roc AND close drops > price_drop% over same window."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    vix = ind.vix
    look = int(p.get("shock_look", 5))
    vix_roc = float(p.get("shock_vix_roc", 1.5))
    price_drop = float(p.get("shock_price_drop", 5.0)) / 100.0
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(look, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if (vix is not None and not np.isnan(vix[i]) and not np.isnan(vix[i - look])
                and vix[i - look] > 0 and cl[i - look] > 0):
            vix_ratio = vix[i] / vix[i - look]
            price_ret = cl[i] / cl[i - look] - 1
            if vix_ratio > vix_roc and price_ret < -price_drop:
                exits[i] = True
                labels[i] = "S"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_vjxr(ind, p):
    """T1 addon A2: VJ + price-velocity shock exit + RSI-bounce re-entry watch.
    Exit on close dropping > shock_drop% over shock_look bars. After shock exit,
    arm a watch_bars window; during watch, emit a re-entry when RSI crosses up
    through rsi_bounce AND close > EMA(bounce_ema)."""
    entries_vj, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    bounce_ema = ind.ema(int(p.get("bounce_ema", 50)))
    look = int(p.get("shock_look", 5))
    price_drop = float(p.get("shock_drop", 10.0)) / 100.0
    rsi_bounce = float(p.get("rsi_bounce", 35.0))
    watch_bars = int(p.get("watch_bars", 20))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    watch_remaining = 0
    for i in range(max(look, 2), n):
        if entries_vj[i]:
            entries[i] = True
        if watch_remaining > 0:
            if (not np.isnan(rsi[i - 1]) and not np.isnan(rsi[i])
                    and not np.isnan(bounce_ema[i])
                    and rsi[i - 1] < rsi_bounce and rsi[i] >= rsi_bounce
                    and cl[i] > bounce_ema[i]):
                entries[i] = True
                watch_remaining = 0
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if cl[i - look] > 0:
            price_ret = cl[i] / cl[i - look] - 1
            if price_ret < -price_drop:
                exits[i] = True
                labels[i] = "S"
                watch_remaining = watch_bars
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
        if watch_remaining > 0:
            watch_remaining -= 1
    return entries, exits, labels


def gc_vjv(ind, p):
    """T1 addon A3: VJ entries gated by realized-vol calm (rv_short/rv_long < ratio)."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    vol_short = int(p.get("vol_short", 20))
    vol_long = int(p.get("vol_long", 50))
    vol_entry_ratio = float(p.get("vol_entry_ratio", 0.9))
    rv_short = ind.realized_vol(vol_short)
    rv_long = ind.realized_vol(vol_long)
    new_entries = np.zeros(n, dtype=bool)
    for i in range(vol_long, n):
        if not entries[i]:
            continue
        if np.isnan(rv_short[i]) or np.isnan(rv_long[i]) or rv_long[i] <= 0:
            continue
        if rv_short[i] / rv_long[i] < vol_entry_ratio:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_vjatr(ind, p):
    """T1 addon A10: VJ + directional ATR-expansion shock exit (VIX-independent).
    Exit when ATR(atr_period)/ATR[-atr_look] > atr_expand AND close[i] < close[-atr_confirm]."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    atr_len = int(p.get("atr_period", 14))
    atr_look = int(p.get("atr_look", 20))
    atr_expand = float(p.get("atr_expand", 2.0))
    atr_confirm = int(p.get("atr_confirm", 5))
    atr_vals = ind.atr(atr_len)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(atr_look, atr_confirm), n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        if (not np.isnan(atr_vals[i]) and not np.isnan(atr_vals[i - atr_look])
                and atr_vals[i - atr_look] > 0):
            atr_ratio = atr_vals[i] / atr_vals[i - atr_look]
            if atr_ratio > atr_expand and cl[i] < cl[i - atr_confirm]:
                exits[i] = True
                labels[i] = "A"
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Velvet Jaguar Overlays 2026-04-20 (Round 2)
# See docs/*NEXT/brainstorm-2026-04-20-velvet-jaguar-gaps.md.
# ─────────────────────────────────────────────────────────────────────────────


def gc_vjrsi(ind, p):
    """T1 addon A4: VJ primary entry OR RSI-bounce secondary entry.
    Secondary: RSI crosses up through rsi_bounce from below rsi_oversold AND
    close > EMA(rsi_trend_ema) AND MACD line rising over 5 bars."""
    entries_vj, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    rsi_len = int(p.get("rsi_len", 14))
    rsi_oversold = float(p.get("rsi_oversold", 30.0))
    rsi_bounce = float(p.get("rsi_bounce", 35.0))
    trend_len = int(p.get("rsi_trend_ema", 100))
    rsi = ind.rsi(rsi_len)
    trend_ema = ind.ema(trend_len)
    macd = ind.macd_line(12, 26)
    entries = np.zeros(n, dtype=bool)
    for i in range(max(5, trend_len), n):
        if entries_vj[i]:
            entries[i] = True
            continue
        if (not np.isnan(rsi[i - 1]) and not np.isnan(rsi[i])
                and rsi[i - 1] < rsi_oversold and rsi[i] >= rsi_bounce
                and not np.isnan(trend_ema[i]) and cl[i] > trend_ema[i]
                and not np.isnan(macd[i]) and not np.isnan(macd[i - 5])
                and macd[i] > macd[i - 5]):
            entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return entries, exits, labels


def gc_vjsgov(ind, p):
    """T1 addon A6: VJ + SGOV relative-strength rotation exit.
    Exit when SGOV_ret(rs_lookback) > TECL_ret(rs_lookback) for rs_persistence bars."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    sgov = ind.sgov_close
    rs_lookback = int(p.get("rs_lookback", 50))
    rs_persistence = int(p.get("rs_persistence", 20))
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    rs_count = 0
    for i in range(rs_lookback, n):
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        # SGOV RS exit (only active when SGOV data available)
        if (sgov is not None and not np.isnan(sgov[i]) and not np.isnan(sgov[i - rs_lookback])
                and sgov[i - rs_lookback] > 0 and cl[i - rs_lookback] > 0):
            sgov_ret = sgov[i] / sgov[i - rs_lookback] - 1
            tecl_ret = cl[i] / cl[i - rs_lookback] - 1
            if sgov_ret > tecl_ret:
                rs_count += 1
            else:
                rs_count = 0
            if rs_count >= rs_persistence:
                exits[i] = True
                labels[i] = "R"
        else:
            rs_count = 0
        if vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def gc_vjtimer(ind, p):
    """T1 addon A8: VJ + time-based escape hatch.
    Exit when position held >= time_stop_bars AND close < EMA(below_ema) for below_persist bars."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    time_stop_bars = int(p.get("time_stop_bars", 150))
    below_ema_len = int(p.get("below_ema", 150))
    below_persist = int(p.get("below_persist", 10))
    ema_long = ind.ema(below_ema_len)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    entry_bar = 0
    below_count = 0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            entry_bar = i
            below_count = 0
        if in_trade:
            if not np.isnan(ema_long[i]) and cl[i] < ema_long[i]:
                below_count += 1
            else:
                below_count = 0
            if death[i]:
                exits[i] = True
                labels[i] = "D"
                in_trade = False
                below_count = 0
            if (i - entry_bar) >= time_stop_bars and below_count >= below_persist:
                exits[i] = True
                labels[i] = "T"
                in_trade = False
                below_count = 0
            if vix_panic[i]:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
                below_count = 0
    return entries, exits, labels


def rsi_regime_canonical(ind, p):
    """T1 standalone (B1): canonical-only RSI regime revive.
    Entry: RSI(rsi_len) crosses up through entry_rsi AND close > EMA(trend_len).
    Exit: RSI >= exit_rsi ("RSI Overbought") OR RSI < panic_rsi ("RSI Panic")."""
    n = ind.n
    cl = ind.close
    rsi_len = int(p.get("rsi_len", 14))
    trend_len = int(p.get("trend_len", 100))
    entry_rsi = float(p.get("entry_rsi", 35.0))
    exit_rsi = float(p.get("exit_rsi", 75.0))
    panic_rsi = float(p.get("panic_rsi", 15.0))
    rsi = ind.rsi(rsi_len)
    trend = ind.ema(trend_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(rsi[i]) or np.isnan(rsi[i - 1]) or np.isnan(trend[i]):
            continue
        if rsi[i - 1] < entry_rsi and rsi[i] >= entry_rsi and cl[i] > trend[i]:
            entries[i] = True
        if rsi[i] >= exit_rsi:
            exits[i] = True
            labels[i] = "OB"
        elif rsi[i] < panic_rsi:
            exits[i] = True
            labels[i] = "P"
    return entries, exits, labels


def dual_tf_gc(ind, p):
    """T1 standalone (B4): nested EMA pair-ups as daily+'weekly' proxy.
    Entry: EMA(fast_ema) > EMA(slow_ema) AND EMA(outer_fast) > EMA(outer_slow)
           AND EMA(fast_ema) rising over slope_window for entry_bars bars.
    Exit: EMA(outer_fast) < EMA(outer_slow)  (outer pair death cross)."""
    n = ind.n
    fast = ind.ema(int(p.get("fast_ema", 50)))
    slow = ind.ema(int(p.get("slow_ema", 200)))
    outer_fast = ind.ema(int(p.get("outer_fast", 100)))
    outer_slow = ind.ema(int(p.get("outer_slow", 300)))
    slope_window = int(p.get("slope_window", 2))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    bull_count = 0
    for i in range(slope_window + 1, n):
        if (np.isnan(fast[i]) or np.isnan(slow[i])
                or np.isnan(outer_fast[i]) or np.isnan(outer_slow[i])
                or np.isnan(fast[i - slope_window])):
            bull_count = 0
            continue
        fast_rising = fast[i] > fast[i - slope_window]
        daily_bull = fast[i] > slow[i]
        outer_bull = outer_fast[i] > outer_slow[i]
        if daily_bull and outer_bull and fast_rising:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if outer_fast[i] < outer_slow[i]:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def tecl_sgov_rs(ind, p):
    """T1 standalone (B14): TECL vs SGOV relative-strength rotation.
    Entry: rs = TECL_ret(rs_look) - SGOV_ret(rs_look) crosses up through 0
           AND close > EMA(trend_ema).
    Exit: rs < rs_exit AND close < EMA(exit_ema).
    Pre-2020 bars have no SGOV signal (data-blocked)."""
    n = ind.n
    cl = ind.close
    sgov = ind.sgov_close
    rs_look = int(p.get("rs_look", 50))
    rs_exit = float(p.get("rs_exit", -5.0)) / 100.0
    trend_len = int(p.get("trend_ema", 200))
    exit_ema_len = int(p.get("exit_ema", 50))
    trend = ind.ema(trend_len)
    exit_ema = ind.ema(exit_ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if sgov is None:
        return entries, exits, labels
    for i in range(rs_look + 1, n):
        if (np.isnan(sgov[i]) or np.isnan(sgov[i - rs_look])
                or sgov[i - rs_look] <= 0 or cl[i - rs_look] <= 0
                or np.isnan(trend[i]) or np.isnan(exit_ema[i])):
            continue
        sgov_ret_now = sgov[i] / sgov[i - rs_look] - 1
        tecl_ret_now = cl[i] / cl[i - rs_look] - 1
        rs_now = tecl_ret_now - sgov_ret_now
        if np.isnan(sgov[i - 1]) or np.isnan(sgov[i - rs_look - 1]) or sgov[i - rs_look - 1] <= 0 or cl[i - rs_look - 1] <= 0:
            continue
        sgov_ret_prev = sgov[i - 1] / sgov[i - rs_look - 1] - 1
        tecl_ret_prev = cl[i - 1] / cl[i - rs_look - 1] - 1
        rs_prev = tecl_ret_prev - sgov_ret_prev
        if rs_prev < 0 and rs_now >= 0 and cl[i] > trend[i]:
            entries[i] = True
        if rs_now < rs_exit and cl[i] < exit_ema[i]:
            exits[i] = True
            labels[i] = "R"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Circuit breakers on VJ (Round 4 of brainstorm) — wrappers, not standalone
# strategies. Each layers on top of gc_n8 (VJ) as a robustness guard.
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Final batch 2026-04-20 — remaining A/B candidates run in one sweep.
# See docs/*NEXT/brainstorm-2026-04-20-velvet-jaguar-gaps.md.
# ─────────────────────────────────────────────────────────────────────────────


def gc_vjmac(ind, p):
    """T1 addon A5: VJ + macro regime gate.
    Entry requires (treasury_spread > 0) OR (fed_funds cutting over ff_lookback)."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    spread = ind.treasury_spread
    ff = ind.fed_funds_rate
    ff_lookback = int(p.get("ff_lookback", 150))
    new_entries = np.zeros(n, dtype=bool)
    for i in range(ff_lookback, n):
        if not entries[i]:
            continue
        spread_ok = spread is not None and not np.isnan(spread[i]) and spread[i] > 0
        ff_ok = (ff is not None and not np.isnan(ff[i]) and not np.isnan(ff[i - ff_lookback])
                 and ff[i] < ff[i - ff_lookback])
        if spread_ok or ff_ok:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_vjbb(ind, p):
    """T1 addon A7: VJ + Bollinger-Band squeeze entry gate.
    Entry requires BB-width at or below bb_pct percentile of trailing bb_width_look window."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    bb_len = int(p.get("bb_len", 20))
    bb_mult = float(p.get("bb_mult", 2.0))
    bb_width_look = int(p.get("bb_width_look", 50))
    bb_pct = float(p.get("bb_pct", 30.0))
    bb_w = ind.bb_width(bb_len, bb_mult)
    new_entries = np.zeros(n, dtype=bool)
    for i in range(bb_width_look, n):
        if not entries[i] or np.isnan(bb_w[i]):
            continue
        window = bb_w[i - bb_width_look + 1:i + 1]
        valid = window[~np.isnan(window)]
        if len(valid) < bb_width_look // 2:
            continue
        pct_rank = (np.sum(valid <= bb_w[i]) / len(valid)) * 100
        if pct_rank <= bb_pct:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_vjdd(ind, p):
    """T1 addon A9: VJ + intra-trade peak drawdown exit (uses close as equity proxy)."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    dd_pct = float(p.get("dd_pct", 20.0)) / 100.0
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    peak = 0.0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            peak = cl[i]
        if in_trade and cl[i] > peak:
            peak = cl[i]
        if in_trade:
            if peak > 0 and cl[i] < peak * (1 - dd_pct):
                exits[i] = True
                labels[i] = "X"
                in_trade = False
                peak = 0.0
            if death[i] and not exits[i]:
                exits[i] = True
                labels[i] = "D"
                in_trade = False
                peak = 0.0
            if vix_panic[i] and not exits[i]:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
                peak = 0.0
    return entries, exits, labels


def vol_regime_canonical(ind, p):
    """T1 standalone (B2): realized-vol contraction entry + vol-spike exit."""
    n = ind.n
    cl = ind.close
    vol_short = int(p.get("vol_short", 20))
    vol_long = int(p.get("vol_long", 50))
    trend_len = int(p.get("trend_len", 100))
    vol_entry_ratio = float(p.get("vol_entry_ratio", 0.9))
    vol_exit_ratio = float(p.get("vol_exit_ratio", 1.5))
    rv_s = ind.realized_vol(vol_short)
    rv_l = ind.realized_vol(vol_long)
    trend = ind.ema(trend_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(vol_long, trend_len) + 1, n):
        if np.isnan(rv_s[i]) or np.isnan(rv_l[i]) or rv_l[i] <= 0:
            continue
        if np.isnan(rv_s[i - 1]) or np.isnan(rv_l[i - 1]) or rv_l[i - 1] <= 0:
            continue
        ratio_now = rv_s[i] / rv_l[i]
        ratio_prev = rv_s[i - 1] / rv_l[i - 1]
        if ratio_prev >= vol_entry_ratio and ratio_now < vol_entry_ratio and cl[i] > trend[i]:
            entries[i] = True
        if ratio_now > vol_exit_ratio:
            exits[i] = True
            labels[i] = "VS"
        elif not np.isnan(trend[i]) and cl[i] < trend[i] * 0.98:
            exits[i] = True
            labels[i] = "BT"
    return entries, exits, labels


def composite_osc_canonical(ind, p):
    """T2 standalone (B3): weighted composite regime score on canonical lengths.
    Composite = 0.5*tema_slope + 0.2*quick_slope + 0.2*macd_hist + 0.2*dmi_bull (tanh-normed).
    Entry: composite crosses up through 0.33. Exit: composite crosses below 0."""
    n = ind.n
    tema_len = int(p.get("tema_len", 200))
    quick_len = int(p.get("quick_len", 7))
    adx_len = int(p.get("adx_len", 14))
    tema = ind.tema(tema_len)
    quick = ind.ema(quick_len)
    macd_hist = ind.macd_hist(12, 26, 9)
    di_plus = ind.di_plus(adx_len)
    di_minus = ind.di_minus(adx_len)
    composite = np.full(n, np.nan)
    for i in range(max(tema_len, adx_len) + 5, n):
        if np.isnan(tema[i]) or np.isnan(tema[i - 2]) or tema[i] <= 0:
            continue
        if np.isnan(quick[i]) or np.isnan(quick[i - 5]):
            continue
        if np.isnan(macd_hist[i]) or np.isnan(di_plus[i]) or np.isnan(di_minus[i]):
            continue
        tema_slope = (tema[i] - tema[i - 2]) / tema[i]
        quick_slope = (quick[i] - quick[i - 5]) / 5.0
        denom_dmi = di_plus[i] + di_minus[i]
        dmi_bull = (di_plus[i] - di_minus[i]) / denom_dmi if denom_dmi > 0 else 0.0
        comp = (0.5 * np.tanh(tema_slope / 0.003)
                + 0.2 * np.tanh(quick_slope / 0.0015)
                + 0.2 * np.tanh(macd_hist[i] / 0.03)
                + 0.2 * np.tanh(dmi_bull / 0.18))
        composite[i] = comp / 1.1
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(1, n):
        if np.isnan(composite[i]) or np.isnan(composite[i - 1]):
            continue
        if composite[i - 1] < 0.33 and composite[i] >= 0.33:
            entries[i] = True
        if composite[i - 1] >= 0.0 and composite[i] < 0.0:
            exits[i] = True
            labels[i] = "C"
    return entries, exits, labels


def bounce_breakout(ind, p):
    """T1 standalone (B5): Donchian breakout with EMA-reclaim secondary entry."""
    n = ind.n
    cl = ind.close
    hi = ind.high
    lo = ind.low
    entry_len = int(p.get("entry_len", 100))
    exit_len = int(p.get("exit_len", 50))
    trend_len = int(p.get("trend_len", 200))
    reclaim_ema_len = int(p.get("reclaim_ema", 50))
    watch_bars = int(p.get("watch_bars", 50))
    trend = ind.ema(trend_len)
    reclaim = ind.ema(reclaim_ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    watch = 0
    in_trade = False
    for i in range(max(entry_len, trend_len) + 1, n):
        if np.isnan(trend[i]) or np.isnan(reclaim[i]) or np.isnan(reclaim[i - 1]):
            continue
        recent_high = np.nanmax(hi[i - entry_len:i])
        recent_low = np.nanmin(lo[i - exit_len:i])
        # Primary entry
        if cl[i] > recent_high and cl[i] > trend[i] and not in_trade:
            entries[i] = True
            in_trade = True
            watch = 0
        # Secondary entry during watch window
        if not in_trade and watch > 0:
            if cl[i - 1] < reclaim[i - 1] and cl[i] >= reclaim[i] and cl[i] > trend[i]:
                entries[i] = True
                in_trade = True
                watch = 0
        # Exit on lower Donchian
        if in_trade and cl[i] < recent_low:
            exits[i] = True
            labels[i] = "D"
            in_trade = False
            watch = watch_bars
        if watch > 0:
            watch -= 1
    return entries, exits, labels


def tri_filter_macd(ind, p):
    """T1 standalone (B6): MACD zero-cross entry with RSI + trend filter, multi-exit."""
    n = ind.n
    cl = ind.close
    trend_len = int(p.get("trend_len", 200))
    rsi_len = int(p.get("rsi_len", 14))
    rsi_entry_floor = float(p.get("rsi_entry_floor", 40.0))
    rsi_panic = float(p.get("rsi_panic", 30.0))
    exit_confirm = int(p.get("exit_confirm", 3))
    macd_line = ind.macd_line(12, 26)
    macd_sig = ind.macd_signal(12, 26, 9)
    trend = ind.ema(trend_len)
    rsi = ind.rsi(rsi_len)
    vix = ind.vix
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    below_count = 0
    for i in range(max(trend_len, 30), n):
        if (np.isnan(macd_line[i]) or np.isnan(macd_line[i - 1])
                or np.isnan(macd_sig[i]) or np.isnan(trend[i]) or np.isnan(rsi[i])):
            continue
        if (macd_line[i - 1] < 0 and macd_line[i] >= 0
                and cl[i] > trend[i] and rsi[i] > rsi_entry_floor):
            entries[i] = True
        if macd_line[i] < macd_sig[i]:
            below_count += 1
        else:
            below_count = 0
        if below_count >= exit_confirm:
            exits[i] = True
            labels[i] = "M"
            below_count = 0
        if rsi[i] < rsi_panic:
            exits[i] = True
            labels[i] = "RP"
        if vix is not None and not np.isnan(vix[i]) and i >= 5 and not np.isnan(vix[i - 5]):
            if vix[i] > 30 and vix[i - 5] > 0 and (vix[i] - vix[i - 5]) / vix[i - 5] > 0.75:
                exits[i] = True
                labels[i] = "V"
    return entries, exits, labels


def momentum_roc_canonical(ind, p):
    """T1 standalone (B8): ROC zero-cross entry with trend filter + ROC/EMA panic exit."""
    n = ind.n
    cl = ind.close
    roc_len = int(p.get("roc_len", 50))
    trend_ema_len = int(p.get("trend_ema", 200))
    exit_ema_len = int(p.get("exit_ema", 50))
    panic_roc = float(p.get("panic_roc", -5.0))
    roc = ind.roc(roc_len)
    trend = ind.ema(trend_ema_len)
    exit_ema = ind.ema(exit_ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(roc_len, trend_ema_len) + 1, n):
        if (np.isnan(roc[i]) or np.isnan(roc[i - 1])
                or np.isnan(trend[i]) or np.isnan(exit_ema[i])):
            continue
        if roc[i - 1] < 0 and roc[i] >= 0 and cl[i] > trend[i]:
            entries[i] = True
        if roc[i] < panic_roc and cl[i] < exit_ema[i]:
            exits[i] = True
            labels[i] = "P"
    return entries, exits, labels


def adaptive_ema_vol(ind, p):
    """T1 standalone (B10): vol-adaptive EMA pair — faster in shocks, slower in calm.
    VIX < vix_low → (fast1,slow1); VIX in [vix_low,vix_high) → (fast2,slow2); VIX ≥ vix_high → (fast3,slow3)."""
    n = ind.n
    cl = ind.close
    vix = ind.vix
    vix_low = float(p.get("vix_low", 20.0))
    vix_high = float(p.get("vix_high", 30.0))
    fast1 = ind.ema(int(p.get("fast1", 50)))
    slow1 = ind.ema(int(p.get("slow1", 200)))
    fast2 = ind.ema(int(p.get("fast2", 30)))
    slow2 = ind.ema(int(p.get("slow2", 100)))
    fast3 = ind.ema(int(p.get("fast3", 20)))
    slow3 = ind.ema(int(p.get("slow3", 50)))
    dwell = int(p.get("dwell", 10))
    entry_bars = int(p.get("entry_bars", 2))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    regime = 0
    last_regime = 0
    dwell_count = 0
    bull_count = 0
    for i in range(50, n):
        vi = vix[i] if (vix is not None and not np.isnan(vix[i])) else 0.0
        proposed = 0 if vi < vix_low else (1 if vi < vix_high else 2)
        if proposed == last_regime:
            dwell_count += 1
        else:
            last_regime = proposed
            dwell_count = 1
        if dwell_count >= dwell:
            regime = last_regime
        if regime == 0:
            f, s = fast1[i], slow1[i]
            f_prev = fast1[i - 2] if i >= 2 else np.nan
        elif regime == 1:
            f, s = fast2[i], slow2[i]
            f_prev = fast2[i - 2] if i >= 2 else np.nan
        else:
            f, s = fast3[i], slow3[i]
            f_prev = fast3[i - 2] if i >= 2 else np.nan
        if np.isnan(f) or np.isnan(s) or np.isnan(f_prev):
            bull_count = 0
            continue
        if f > s and f > f_prev and cl[i] > s:
            bull_count += 1
        else:
            bull_count = 0
        if bull_count == entry_bars:
            entries[i] = True
        if f < s:
            exits[i] = True
            labels[i] = "D"
    return entries, exits, labels


def regime_state_machine(ind, p):
    """T2 standalone (B11): explicit 5-state classifier (BULL/RECOVERY/CHOP/BEAR/SHOCK).
    Long in BULL + RECOVERY; flat elsewhere."""
    n = ind.n
    cl = ind.close
    vix = ind.vix
    rv_s = ind.realized_vol(20)
    rv_l = ind.realized_vol(60)
    ema50 = ind.ema(50)
    ema200 = ind.ema(200)
    rsi = ind.rsi(14)
    state = "CHOP"
    bull_cross_count = 0
    chop_count = 0
    long_states = {"BULL", "RECOVERY"}
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    prev_long = False
    for i in range(200, n):
        if (np.isnan(ema50[i]) or np.isnan(ema200[i])
                or np.isnan(rv_s[i]) or np.isnan(rv_l[i]) or rv_l[i] <= 0
                or np.isnan(rsi[i])):
            continue
        vix_now = vix[i] if (vix is not None and not np.isnan(vix[i])) else 0.0
        vix_prev3 = vix[i - 3] if (vix is not None and i >= 3 and not np.isnan(vix[i - 3])) else 0.0
        rv_ratio = rv_s[i] / rv_l[i]
        bull_ma = ema50[i] > ema200[i]
        if bull_ma:
            bull_cross_count += 1
        else:
            bull_cross_count = 0
        # Transition rules
        if state == "BULL":
            if rv_ratio > 1.3:
                chop_count += 1
                if chop_count >= 5:
                    state = "CHOP"
                    chop_count = 0
            else:
                chop_count = 0
            if vix_prev3 > 0 and (vix_now / vix_prev3) > 1.5 and cl[i] < cl[i - 3] * 0.95:
                state = "SHOCK"
            if not bull_ma:
                state = "BEAR"
        elif state == "CHOP":
            if bull_ma and ema50[i] > ema50[i - 10]:
                state = "BULL"
            if vix_prev3 > 0 and (vix_now / vix_prev3) > 1.5 and cl[i] < cl[i - 3] * 0.95:
                state = "SHOCK"
        elif state == "SHOCK":
            if vix_now < 25 and i >= 10 and cl[i] > cl[i - 10]:
                state = "RECOVERY"
        elif state == "RECOVERY":
            if bull_cross_count >= 10:
                state = "BULL"
        elif state == "BEAR":
            if i >= 1 and rsi[i - 1] < 40 and rsi[i] >= 40 and cl[i] > ema50[i]:
                state = "RECOVERY"
        now_long = state in long_states
        if now_long and not prev_long:
            entries[i] = True
        if not now_long and prev_long:
            exits[i] = True
            labels[i] = state[0]
        prev_long = now_long
    return entries, exits, labels


def airbag_vix_atr(ind, p):
    """T1 diversity lane: simple trend participation with fast VIX/ATR crash airbag.

    Purposefully exit-led. The entry side is conservative and generic; the
    hypothesis under test is whether a volatility shock detector improves
    marker sell timing without becoming another golden-cross variant.
    """
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    trend = ind.ema(int(p.get("trend_len", 200)))
    repair = ind.ema(int(p.get("repair_len", 50)))
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 60)))
    xlk = ind.xlk_close
    vix_lookback = int(p.get("vix_lookback", 5))
    repair_slope = int(p.get("repair_slope", 5))
    vix_spike_pct = float(p.get("vix_spike_pct", 35.0))
    vix_level = float(p.get("vix_level", 28.0))
    vix_reset = float(p.get("vix_reset", 24.0))
    atr_ratio_exit = float(p.get("atr_ratio_exit", 1.6))
    price_drop_pct = float(p.get("price_drop_pct", -7.0))
    xlk_drop_pct = float(p.get("xlk_drop_pct", -3.0))
    trend_buffer_pct = float(p.get("trend_buffer_pct", 0.0))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    risk_off = False
    prev_allowed = False
    start = max(200, vix_lookback + 1, repair_slope + 1)

    for i in range(start, n):
        if np.isnan(trend[i]) or np.isnan(repair[i]) or np.isnan(repair[i - repair_slope]):
            continue
        vix_prev = vix[i - vix_lookback]
        vix_spike = vix_prev > 0 and (vix[i] / vix_prev - 1.0) * 100 >= vix_spike_pct
        atr_ratio = atr_s[i] / atr_l[i] if atr_l[i] > 0 and not np.isnan(atr_l[i]) else 0.0
        price_drop = (cl[i] / cl[i - vix_lookback] - 1.0) * 100
        xlk_drop = 0.0
        if xlk is not None and xlk[i - vix_lookback] > 0:
            xlk_drop = (xlk[i] / xlk[i - vix_lookback] - 1.0) * 100

        volatility_shock = (
            (vix[i] >= vix_level and vix_spike)
            or (atr_ratio >= atr_ratio_exit and price_drop <= price_drop_pct)
            or (vix[i] >= vix_level and xlk_drop <= xlk_drop_pct)
        )
        repaired = (
            vix[i] <= vix_reset
            and cl[i] > repair[i]
            and repair[i] > repair[i - repair_slope]
        )

        if risk_off:
            if repaired:
                risk_off = False
        elif volatility_shock:
            risk_off = True

        trend_ok = cl[i] > trend[i] * (1.0 + trend_buffer_pct / 100.0)
        allowed = (not risk_off) and trend_ok
        if allowed and not prev_allowed:
            entries[i] = True
        if (not allowed) and prev_allowed:
            exits[i] = True
            labels[i] = "AIR"
        prev_allowed = allowed

    return entries, exits, labels


def reclaimer_vol_rsi(ind, p):
    """T1 diversity lane: buy-only recovery detector after panic/high volatility."""
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    fast = ind.ema(int(p.get("fast_len", 50)))
    trend = ind.ema(int(p.get("trend_len", 150)))
    rv_s = ind.realized_vol(int(p.get("vol_short", 20)))
    rv_l = ind.realized_vol(int(p.get("vol_long", 80)))
    atr = ind.atr(int(p.get("atr_period", 20)))
    lookback = int(p.get("drawdown_lookback", 120))
    drawdown_pct = float(p.get("drawdown_pct", 25.0))
    rsi_reclaim = float(p.get("rsi_reclaim", 45.0))
    vol_ratio_max = float(p.get("vol_ratio_max", 0.95))
    vix_floor = float(p.get("vix_floor", 24.0))
    exit_trend_buffer = float(p.get("exit_trend_buffer", 3.0))
    panic_atr_mult = float(p.get("panic_atr_mult", 3.0))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    armed = False
    prev_long = False
    start = max(lookback, int(p.get("trend_len", 150)), int(p.get("vol_long", 80))) + 1

    for i in range(start, n):
        if (
            np.isnan(rsi[i]) or np.isnan(rsi[i - 1])
            or np.isnan(fast[i]) or np.isnan(fast[i - 5])
            or np.isnan(trend[i]) or np.isnan(rv_s[i]) or np.isnan(rv_l[i])
            or rv_l[i] <= 0
        ):
            continue

        recent_high = np.max(cl[i - lookback + 1:i + 1])
        drawdown = (cl[i] / recent_high - 1.0) * 100 if recent_high > 0 else 0.0
        if drawdown <= -drawdown_pct or vix[i] >= vix_floor:
            armed = True

        vol_calm = rv_s[i] / rv_l[i] <= vol_ratio_max
        rsi_cross = rsi[i - 1] < rsi_reclaim <= rsi[i]
        repair_slope = fast[i] > fast[i - 5]
        reclaim = armed and vol_calm and rsi_cross and repair_slope and cl[i] > fast[i]

        if reclaim:
            entries[i] = True
            armed = False
            prev_long = True

        trend_exit = cl[i] < trend[i] * (1.0 - exit_trend_buffer / 100.0)
        atr_panic = not np.isnan(atr[i]) and cl[i] < cl[i - 1] - panic_atr_mult * atr[i]
        if prev_long and (trend_exit or atr_panic):
            exits[i] = True
            labels[i] = "REC"
            prev_long = False
            if atr_panic:
                armed = True

    return entries, exits, labels


def state_machine_crash_recovery(ind, p):
    """T1 diversity lane: explicit crash, repair, bull, and chop states."""
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    ema_fast = ind.ema(int(p.get("fast_len", 50)))
    ema_slow = ind.ema(int(p.get("slow_len", 200)))
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    rv_s = ind.realized_vol(int(p.get("vol_short", 20)))
    rv_l = ind.realized_vol(int(p.get("vol_long", 80)))
    vix_lookback = int(p.get("vix_lookback", 5))
    vix_shock_pct = float(p.get("vix_shock_pct", 35.0))
    vix_shock_level = float(p.get("vix_shock_level", 28.0))
    vix_repair_level = float(p.get("vix_repair_level", 24.0))
    vol_shock_ratio = float(p.get("vol_shock_ratio", 1.45))
    rsi_repair = float(p.get("rsi_repair", 42.0))
    bull_confirm = int(p.get("bull_confirm", 5))
    chop_exit_bars = int(p.get("chop_exit_bars", 5))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    state = "CHOP"
    prev_long = False
    bull_count = 0
    chop_count = 0
    start = max(200, int(p.get("vol_long", 80)), vix_lookback + 1, bull_confirm + 1)

    for i in range(start, n):
        if (
            np.isnan(ema_fast[i]) or np.isnan(ema_slow[i])
            or np.isnan(rsi[i]) or np.isnan(rv_s[i]) or np.isnan(rv_l[i])
            or rv_l[i] <= 0
        ):
            continue

        vix_prev = vix[i - vix_lookback]
        vix_spike = vix_prev > 0 and (vix[i] / vix_prev - 1.0) * 100 >= vix_shock_pct
        vol_ratio = rv_s[i] / rv_l[i]
        crash = (
            (vix[i] >= vix_shock_level and vix_spike)
            or (vol_ratio >= vol_shock_ratio and cl[i] < cl[i - vix_lookback])
        )
        bull_raw = ema_fast[i] > ema_slow[i] and cl[i] > ema_slow[i]
        bull_count = bull_count + 1 if bull_raw else 0

        if crash:
            state = "CRASH"
            chop_count = 0
        elif state == "CRASH":
            if vix[i] <= vix_repair_level and rsi[i] >= rsi_repair and cl[i] > ema_fast[i]:
                state = "REPAIR"
        elif state == "REPAIR":
            if bull_count >= bull_confirm:
                state = "BULL"
            elif crash:
                state = "CRASH"
        elif state == "BULL":
            if not bull_raw or vol_ratio > 1.25:
                chop_count += 1
                if chop_count >= chop_exit_bars:
                    state = "CHOP"
                    chop_count = 0
            else:
                chop_count = 0
        else:
            if bull_count >= bull_confirm:
                state = "BULL"

        now_long = state in {"REPAIR", "BULL"}
        if now_long and not prev_long:
            entries[i] = True
        if (not now_long) and prev_long:
            exits[i] = True
            labels[i] = state[:3]
        prev_long = now_long

    return entries, exits, labels


def _state_from_events(entries: np.ndarray, exits: np.ndarray) -> np.ndarray:
    """Convert entry/exit event arrays into a bar-level long-state mask."""
    state = np.zeros(len(entries), dtype=bool)
    long = False
    for i in range(len(entries)):
        if exits[i]:
            long = False
        if entries[i]:
            long = True
        state[i] = long
    return state


def _merge_exit_overlay(
    base_exits: np.ndarray,
    base_labels: np.ndarray,
    overlay_exits: np.ndarray,
    overlay_label: str,
) -> tuple[np.ndarray, np.ndarray]:
    exits = base_exits.copy()
    labels = base_labels.copy()
    for i in range(len(exits)):
        if overlay_exits[i]:
            exits[i] = True
            if not labels[i]:
                labels[i] = overlay_label
    return exits, labels


def _airbag_shock_events(ind, p) -> np.ndarray:
    """Crash-shock events only, excluding standalone trend-filter exits."""
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    atr_s = ind.atr(int(p.get("atr_short", 14)))
    atr_l = ind.atr(int(p.get("atr_long", 60)))
    xlk = ind.xlk_close
    vix_lookback = int(p.get("vix_lookback", 5))
    vix_spike_pct = float(p.get("vix_spike_pct", 35.0))
    vix_level = float(p.get("vix_level", 28.0))
    atr_ratio_exit = float(p.get("atr_ratio_exit", 1.6))
    price_drop_pct = float(p.get("price_drop_pct", -7.0))
    xlk_drop_pct = float(p.get("xlk_drop_pct", -3.0))
    events = np.zeros(n, dtype=bool)
    start = max(vix_lookback + 1, int(p.get("atr_long", 60)) + 1)
    for i in range(start, n):
        vix_prev = vix[i - vix_lookback]
        vix_spike = vix_prev > 0 and (vix[i] / vix_prev - 1.0) * 100 >= vix_spike_pct
        atr_ratio = atr_s[i] / atr_l[i] if atr_l[i] > 0 and not np.isnan(atr_l[i]) else 0.0
        price_drop = (cl[i] / cl[i - vix_lookback] - 1.0) * 100
        xlk_drop = 0.0
        if xlk is not None and xlk[i - vix_lookback] > 0:
            xlk_drop = (xlk[i] / xlk[i - vix_lookback] - 1.0) * 100
        events[i] = (
            (vix[i] >= vix_level and vix_spike)
            or (atr_ratio >= atr_ratio_exit and price_drop <= price_drop_pct)
            or (vix[i] >= vix_level and xlk_drop <= xlk_drop_pct)
        )
    return events


def _state_crash_risk_off(ind, p) -> tuple[np.ndarray, np.ndarray]:
    """Return risk-off state and first crash bars for soft state-filter overlays."""
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    ema_fast = ind.ema(int(p.get("fast_len", 50)))
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    rv_s = ind.realized_vol(int(p.get("vol_short", 20)))
    rv_l = ind.realized_vol(int(p.get("vol_long", 80)))
    vix_lookback = int(p.get("vix_lookback", 5))
    vix_shock_pct = float(p.get("vix_shock_pct", 35.0))
    vix_shock_level = float(p.get("vix_shock_level", 28.0))
    vix_repair_level = float(p.get("vix_repair_level", 24.0))
    vol_shock_ratio = float(p.get("vol_shock_ratio", 1.45))
    rsi_repair = float(p.get("rsi_repair", 42.0))
    risk_off = np.zeros(n, dtype=bool)
    crash_start = np.zeros(n, dtype=bool)
    off = False
    start = max(int(p.get("vol_long", 80)), vix_lookback + 1, int(p.get("fast_len", 50))) + 1
    for i in range(start, n):
        if np.isnan(ema_fast[i]) or np.isnan(rsi[i]) or np.isnan(rv_s[i]) or np.isnan(rv_l[i]) or rv_l[i] <= 0:
            risk_off[i] = off
            continue
        vix_prev = vix[i - vix_lookback]
        vix_spike = vix_prev > 0 and (vix[i] / vix_prev - 1.0) * 100 >= vix_shock_pct
        vol_ratio = rv_s[i] / rv_l[i]
        crash = (
            (vix[i] >= vix_shock_level and vix_spike)
            or (vol_ratio >= vol_shock_ratio and cl[i] < cl[i - vix_lookback])
        )
        repaired = vix[i] <= vix_repair_level and rsi[i] >= rsi_repair and cl[i] > ema_fast[i]
        if off:
            if repaired:
                off = False
        elif crash:
            off = True
            crash_start[i] = True
        risk_off[i] = off
    return risk_off, crash_start


def timing_repair_entries(ind, p) -> np.ndarray:
    """Small post-drawdown re-entry module for marker-timing research."""
    n = ind.n
    cl = ind.close
    vix = ind.vix_close()
    repair = ind.ema(int(p.get("repair_len", 30)))
    rsi = ind.rsi(int(p.get("rsi_len", 14)))
    lookback = int(p.get("drawdown_lookback", 60))
    drawdown_pct = float(p.get("drawdown_pct", 15.0))
    slope_lookback = int(p.get("repair_slope", 3))
    rsi_floor = float(p.get("rsi_floor", 40.0))
    vix_ceiling = float(p.get("vix_ceiling", 45.0))
    entries = np.zeros(n, dtype=bool)
    armed = False
    start = max(lookback, int(p.get("repair_len", 30)), slope_lookback) + 1
    for i in range(start, n):
        if np.isnan(repair[i]) or np.isnan(repair[i - slope_lookback]) or np.isnan(rsi[i]):
            continue
        recent_high = np.max(cl[i - lookback + 1:i + 1])
        drawdown = (cl[i] / recent_high - 1.0) * 100 if recent_high > 0 else 0.0
        if drawdown <= -drawdown_pct:
            armed = True
        repair_cross = cl[i - 1] <= repair[i - 1] and cl[i] > repair[i]
        repair_slope = repair[i] > repair[i - slope_lookback]
        if armed and repair_cross and repair_slope and rsi[i] >= rsi_floor and vix[i] <= vix_ceiling:
            entries[i] = True
            armed = False
    return entries


def gc_vjatr_airbag(ind, p):
    """T1 overlay test: Bonobo/VJ-ATR base plus independent VIX/ATR airbag exits."""
    entries, base_exits, base_labels = gc_vjatr(ind, p)
    airbag_exits = _airbag_shock_events(ind, p)
    exits, labels = _merge_exit_overlay(base_exits, base_labels, airbag_exits, "AIR")
    return entries, exits, labels


def gc_vjatr_reclaimer(ind, p):
    """T1 overlay test: Bonobo/VJ-ATR base plus post-panic reclaimer entries.

    The reclaimer contributes entry events only. Base exits remain authoritative
    so this tests whether recovery timing improves without adding a second exit
    doctrine.
    """
    base_entries, exits, labels = gc_vjatr(ind, p)
    reclaim_entries, _reclaim_exits, _reclaim_labels = reclaimer_vol_rsi(ind, p)
    entries = base_entries | reclaim_entries
    return entries, exits, labels


def gc_vjatr_state_filter(ind, p):
    """T1 overlay test: Bonobo/VJ-ATR with soft crash-state suppression."""
    base_entries, base_exits, base_labels = gc_vjatr(ind, p)
    risk_off, crash_start = _state_crash_risk_off(ind, p)
    entries = base_entries & (~risk_off)
    exits, labels = _merge_exit_overlay(base_exits, base_labels, crash_start, "STM")
    return entries, exits, labels


def gc_vjatr_timing_repair(ind, p):
    """T1 research overlay: Bonobo/VJ-ATR plus minimal post-drawdown re-entry."""
    base_entries, exits, labels = gc_vjatr(ind, p)
    entries = base_entries | timing_repair_entries(ind, p)
    return entries, exits, labels


def ensemble_vote_3of5(ind, p):
    """T1 standalone (B12): 5 signals vote; enter on score>=entry_vote, exit on score<=exit_vote."""
    n = ind.n
    cl = ind.close
    entry_vote = int(p.get("entry_vote", 3))
    exit_vote = int(p.get("exit_vote", -1))
    trend_len = int(p.get("trend_len", 200))
    ema50 = ind.ema(50)
    ema200 = ind.ema(200)
    ema100 = ind.ema(100)
    trend = ind.ema(trend_len)
    macd_h = ind.macd_hist(12, 26, 9)
    rsi = ind.rsi(14)
    roc50 = ind.roc(50)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(max(200, trend_len) + 10, n):
        if (np.isnan(ema50[i]) or np.isnan(ema200[i]) or np.isnan(ema100[i])
                or np.isnan(ema100[i - 10]) or np.isnan(macd_h[i]) or np.isnan(macd_h[i - 1])
                or np.isnan(rsi[i]) or np.isnan(roc50[i]) or np.isnan(trend[i])):
            continue
        s1 = 1 if ema50[i] > ema200[i] else -1
        if macd_h[i] > 0 and macd_h[i] > macd_h[i - 1]:
            s2 = 1
        elif macd_h[i] < 0 and macd_h[i] < macd_h[i - 1]:
            s2 = -1
        else:
            s2 = 0
        if rsi[i] > 55:
            s3 = 1
        elif rsi[i] < 45:
            s3 = -1
        else:
            s3 = 0
        s4 = 1 if roc50[i] > 0 else -1
        s5 = 1 if ema100[i] > ema100[i - 10] else -1
        score = s1 + s2 + s3 + s4 + s5
        if score >= entry_vote and cl[i] > trend[i]:
            entries[i] = True
        if score <= exit_vote:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def fed_macro_primary(ind, p):
    """T1 standalone (B13): Fed-funds direction as primary signal."""
    n = ind.n
    ff = ind.fed_funds_rate
    spread = ind.treasury_spread
    ff_long = int(p.get("ff_long", 150))
    ff_short = int(p.get("ff_short", 20))
    ff_exit = int(p.get("ff_exit", 50))
    spread_floor = float(p.get("spread_floor", -0.3))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if ff is None:
        return entries, exits, labels
    for i in range(ff_long, n):
        if np.isnan(ff[i]) or np.isnan(ff[i - ff_long]) or np.isnan(ff[i - ff_short]):
            continue
        cutting_long = ff[i] < ff[i - ff_long]
        cutting_short = ff[i] < ff[i - ff_short]
        spread_ok = spread is None or np.isnan(spread[i]) or spread[i] > spread_floor
        if cutting_long and cutting_short and spread_ok:
            entries[i] = True
        if i >= ff_exit and not np.isnan(ff[i - ff_exit]) and ff[i] > ff[i - ff_exit]:
            exits[i] = True
            labels[i] = "H"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Next-Frontier brainstorm 2026-04-20 — Lane 2 (VJ cross-asset rescue)
# See docs/*NEXT/brainstorm-2026-04-20-next-frontier.md.
# ─────────────────────────────────────────────────────────────────────────────


def gc_vj_decay_gate(ind, p):
    """T1 addon N6: VJ + leverage-decay entry gate.
    Entry requires TECL_ret(decay_look) - 3*XLK_ret(decay_look) > decay_threshold.
    Filters out periods when TECL underperforms its 3× target (daily-reset decay)."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    xlk = ind.xlk_close
    decay_look = int(p.get("decay_look", 20))
    decay_threshold = float(p.get("decay_threshold", -0.05))
    new_entries = np.zeros(n, dtype=bool)
    if xlk is None:
        exits, labels = _compose_base_exits(n, death, vix_panic)
        return new_entries, exits, labels
    for i in range(decay_look, n):
        if not entries[i]:
            continue
        if np.isnan(xlk[i]) or np.isnan(xlk[i - decay_look]) or xlk[i - decay_look] <= 0:
            continue
        if cl[i - decay_look] <= 0:
            continue
        tecl_ret = cl[i] / cl[i - decay_look] - 1
        xlk_ret = xlk[i] / xlk[i - decay_look] - 1
        gap = tecl_ret - 3.0 * xlk_ret
        if gap > decay_threshold:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_vj_xlk_relative_trend(ind, p):
    """T1 addon N5: VJ + XLK trend confirmation gate.
    Entry requires XLK_EMA(xlk_fast) > XLK_EMA(xlk_slow) AND XLK_fast rising."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    xlk_fast_len = int(p.get("xlk_fast", 50))
    xlk_slow_len = int(p.get("xlk_slow", 200))
    xlk_slope = int(p.get("xlk_slope", 2))
    xlk_fast = ind.xlk_ema(xlk_fast_len)
    xlk_slow = ind.xlk_ema(xlk_slow_len)
    new_entries = np.zeros(n, dtype=bool)
    if xlk_fast is None or xlk_slow is None:
        exits, labels = _compose_base_exits(n, death, vix_panic)
        return new_entries, exits, labels
    for i in range(xlk_slow_len + xlk_slope, n):
        if not entries[i]:
            continue
        if (np.isnan(xlk_fast[i]) or np.isnan(xlk_slow[i])
                or np.isnan(xlk_fast[i - xlk_slope])):
            continue
        if xlk_fast[i] > xlk_slow[i] and xlk_fast[i] > xlk_fast[i - xlk_slope]:
            new_entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return new_entries, exits, labels


def gc_vj_dual_regime(ind, p):
    """T1 addon N9: VJ + dual-asset regime classifier.
    Entry requires TECL in BULL (EMA50>EMA200) AND XLK in BULL (EMA50>EMA200).
    Additionally exits when either asset's regime flips to BEAR."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    reg_fast = int(p.get("reg_fast", 50))
    reg_slow = int(p.get("reg_slow", 200))
    tecl_fast = ind.ema(reg_fast)
    tecl_slow = ind.ema(reg_slow)
    xlk_fast = ind.xlk_ema(reg_fast)
    xlk_slow = ind.xlk_ema(reg_slow)
    new_entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if xlk_fast is None or xlk_slow is None:
        exits, labels = _compose_base_exits(n, death, vix_panic)
        return new_entries, exits, labels
    for i in range(reg_slow, n):
        if np.isnan(tecl_fast[i]) or np.isnan(tecl_slow[i]) or np.isnan(xlk_fast[i]) or np.isnan(xlk_slow[i]):
            continue
        tecl_bull = tecl_fast[i] > tecl_slow[i]
        xlk_bull = xlk_fast[i] > xlk_slow[i]
        dual_bull = tecl_bull and xlk_bull
        if entries[i] and dual_bull:
            new_entries[i] = True
        if death[i]:
            exits[i] = True
            labels[i] = "D"
        elif not dual_bull and (not tecl_bull or not xlk_bull):
            # Regime flip exit
            exits[i] = True
            labels[i] = "R"
        if vix_panic[i] and not exits[i]:
            exits[i] = True
            labels[i] = "V"
    return new_entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Next-Frontier brainstorm 2026-04-20 — Lane 4 (meta + infrastructure)
# ─────────────────────────────────────────────────────────────────────────────


def vj_or_slope_meta(ind, p):
    """T1 standalone (N10): OR-composite of VJ entries with slope_only_200 entries.
    Hypothesis: VJ compounds on TECL; slope_only_200 generalizes on QQQ. A union of
    their entry signals may combine TECL performance with QQQ robustness.
    Exits take whichever fires first from either parent."""
    # VJ base
    vj_entries, vj_death, vj_vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    # Slope-only(200) signal
    slope_ema_len = int(p.get("slope_ema_len", 200))
    slope_look = int(p.get("slope_look", 20))
    ema = ind.ema(slope_ema_len)
    slope_entries = np.zeros(n, dtype=bool)
    slope_exits = np.zeros(n, dtype=bool)
    prev_slope_pos = False
    for i in range(slope_ema_len + slope_look + 1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_look]) or ema[i - slope_look] <= 0:
            continue
        slope = (ema[i] - ema[i - slope_look]) / ema[i - slope_look]
        slope_pos = slope >= 0
        if not prev_slope_pos and slope_pos and cl[i] > ema[i]:
            slope_entries[i] = True
        if prev_slope_pos and not slope_pos:
            slope_exits[i] = True
        prev_slope_pos = slope_pos
    # Compose: entries = vj OR slope; exits = vj_death OR vj_vix_panic OR slope_exits (whichever fires)
    entries = vj_entries | slope_entries
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(n):
        if vj_death[i]:
            exits[i] = True
            labels[i] = "D"
        if vj_vix_panic[i]:
            exits[i] = True
            labels[i] = "V"
        if slope_exits[i]:
            exits[i] = True
            labels[i] = "S" if not labels[i] else labels[i]
    return entries, exits, labels


def breadth_decay_composite(ind, p):
    """T1 standalone (N8): breadth-proxy via TECL/3×XLK ratio as entry gate.
    When breadth_proxy = (1+tecl_ret_n)/(1+3*xlk_ret_n) is BELOW narrow_threshold,
    rally is broad-based (healthy). When ABOVE, rally is concentrated (fragile).
    Entry: close > EMA(trend_len) AND breadth_proxy < narrow_threshold
           AND tecl_ret_n > 0 (we're actually rising).
    Exit:  close < EMA(exit_ema) (trend break)."""
    n = ind.n
    cl = ind.close
    xlk = ind.xlk_close
    trend_len = int(p.get("trend_len", 200))
    exit_ema_len = int(p.get("exit_ema", 50))
    breadth_look = int(p.get("breadth_look", 20))
    narrow_threshold = float(p.get("narrow_threshold", 1.05))
    trend = ind.ema(trend_len)
    exit_ema = ind.ema(exit_ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    if xlk is None:
        return entries, exits, labels
    for i in range(max(trend_len, breadth_look) + 1, n):
        if (np.isnan(trend[i]) or np.isnan(exit_ema[i])
                or np.isnan(xlk[i]) or np.isnan(xlk[i - breadth_look])
                or xlk[i - breadth_look] <= 0 or cl[i - breadth_look] <= 0):
            continue
        tecl_ret = cl[i] / cl[i - breadth_look] - 1
        xlk_ret = xlk[i] / xlk[i - breadth_look] - 1
        denom = 1.0 + 3.0 * xlk_ret
        if denom <= 0:
            continue
        breadth_proxy = (1.0 + tecl_ret) / denom
        if (cl[i] > trend[i] and breadth_proxy < narrow_threshold and tecl_ret > 0):
            entries[i] = True
        if cl[i] < exit_ema[i]:
            exits[i] = True
            labels[i] = "T"
    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Next-Frontier brainstorm 2026-04-20 — Lane 1 (generalization-first)
# ─────────────────────────────────────────────────────────────────────────────


def rank_slope_regime(ind, p):
    """T1 standalone (N1): percentile-rank slope — amplitude-invariant by design.
    slope[i] = (EMA(trend_len) - EMA(trend_len)[-slope_look]) / EMA(trend_len)[-slope_look]
    rank[i] = percentile rank of slope[i] within trailing rank_window.
    Entry: rank crosses up through entry_pct AND close > EMA(trend_len).
    Exit:  rank crosses down through exit_pct."""
    n = ind.n
    cl = ind.close
    trend_len = int(p.get("trend_len", 100))
    slope_look = int(p.get("slope_look", 20))
    rank_window = int(p.get("rank_window", 200))
    entry_pct = float(p.get("entry_pct", 50.0))
    exit_pct = float(p.get("exit_pct", 30.0))
    ema = ind.ema(trend_len)
    slope = np.full(n, np.nan)
    for i in range(slope_look, n):
        if not np.isnan(ema[i]) and not np.isnan(ema[i - slope_look]) and ema[i - slope_look] > 0:
            slope[i] = (ema[i] - ema[i - slope_look]) / ema[i - slope_look]
    rank = np.full(n, np.nan)
    for i in range(rank_window + slope_look, n):
        w = slope[i - rank_window + 1:i + 1]
        valid = w[~np.isnan(w)]
        if len(valid) < rank_window // 2 or np.isnan(slope[i]):
            continue
        rank[i] = (np.sum(valid <= slope[i]) / len(valid)) * 100
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(rank_window + slope_look + 1, n):
        if np.isnan(rank[i]) or np.isnan(rank[i - 1]) or np.isnan(ema[i]):
            continue
        if rank[i - 1] < entry_pct and rank[i] >= entry_pct and cl[i] > ema[i]:
            entries[i] = True
        if rank[i - 1] >= exit_pct and rank[i] < exit_pct:
            exits[i] = True
            labels[i] = "R"
    return entries, exits, labels


def zscore_return_reversion(ind, p):
    """T1 standalone (N3): z-score of N-day return — scale-invariant.
    z[i] = (ret_n[i] - mean(ret_n, window)) / std(ret_n, window).
    Entry: z crosses up through entry_z from below + close > EMA(trend_len).
    Exit:  z > exit_z  (mean-reverted)."""
    n = ind.n
    cl = ind.close
    ret_n = int(p.get("ret_n", 20))
    window = int(p.get("window", 100))
    entry_z = float(p.get("entry_z", -1.5))
    exit_z = float(p.get("exit_z", 1.0))
    trend_len = int(p.get("trend_len", 200))
    ema = ind.ema(trend_len)
    returns = np.full(n, np.nan)
    for i in range(ret_n, n):
        if cl[i - ret_n] > 0:
            returns[i] = cl[i] / cl[i - ret_n] - 1
    z = np.full(n, np.nan)
    for i in range(ret_n + window, n):
        w = returns[i - window + 1:i + 1]
        valid = w[~np.isnan(w)]
        if len(valid) < window // 2 or np.isnan(returns[i]):
            continue
        mu = np.mean(valid)
        sd = np.std(valid)
        if sd > 0:
            z[i] = (returns[i] - mu) / sd
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    for i in range(ret_n + window + 1, n):
        if np.isnan(z[i]) or np.isnan(z[i - 1]) or np.isnan(ema[i]):
            continue
        if z[i - 1] < entry_z and z[i] >= entry_z and cl[i] > ema[i]:
            entries[i] = True
        if z[i] > exit_z:
            exits[i] = True
            labels[i] = "M"
    return entries, exits, labels


def slope_only_200(ind, p):
    """T1 standalone (B16): pure 200-EMA slope signal."""
    n = ind.n
    cl = ind.close
    ema_len = int(p.get("ema_len", 200))
    slope_look = int(p.get("slope_look", 20))
    ema = ind.ema(ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    prev_slope_pos = False
    for i in range(ema_len + slope_look + 1, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - slope_look]) or ema[i - slope_look] <= 0:
            continue
        slope = (ema[i] - ema[i - slope_look]) / ema[i - slope_look]
        slope_pos = slope >= 0
        if not prev_slope_pos and slope_pos and cl[i] > ema[i]:
            entries[i] = True
        if prev_slope_pos and not slope_pos:
            exits[i] = True
            labels[i] = "S"
        prev_slope_pos = slope_pos
    return entries, exits, labels


def gc_n8_ddbreaker(ind, p):
    """T1 circuit-breaker C1 on VJ: pause entries after severe price drawdown.
    Approximates equity drawdown with price-drawdown-from-ATH — valid because
    VJ is 100%-invested-or-flat, so equity tracks close when in a trade.
    Pause when DD > pause_dd_pct; resume when DD < resume_dd_pct."""
    entries_vj, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    pause_pct = float(p.get("pause_dd_pct", 30.0)) / 100.0
    resume_pct = float(p.get("resume_dd_pct", 15.0)) / 100.0
    entries = np.zeros(n, dtype=bool)
    paused = False
    ath = -np.inf
    for i in range(n):
        if cl[i] > ath:
            ath = cl[i]
        dd = (ath - cl[i]) / ath if ath > 0 else 0.0
        if not paused and dd > pause_pct:
            paused = True
        elif paused and dd < resume_pct:
            paused = False
        if entries_vj[i] and not paused:
            entries[i] = True
    exits, labels = _compose_base_exits(n, death, vix_panic)
    return entries, exits, labels


def gc_n8_timelimit(ind, p):
    """T1 circuit-breaker C2 on VJ: force-exit long-held positions when trend fades.
    If bars held >= max_hold AND close < EMA(tl_ema), exit. Then VJ re-entry resumes."""
    entries, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    cl = ind.close
    max_hold = int(p.get("max_hold", 500))
    tl_ema_len = int(p.get("tl_ema", 150))
    ema_long = ind.ema(tl_ema_len)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    in_trade = False
    entry_bar = 0
    for i in range(n):
        if entries[i] and not in_trade:
            in_trade = True
            entry_bar = i
        if in_trade:
            if death[i]:
                exits[i] = True
                labels[i] = "D"
                in_trade = False
            if ((i - entry_bar) >= max_hold
                    and not np.isnan(ema_long[i]) and cl[i] < ema_long[i]):
                exits[i] = True
                labels[i] = "TL"
                in_trade = False
            if vix_panic[i]:
                exits[i] = True
                labels[i] = "V"
                in_trade = False
    return entries, exits, labels


def gc_n8_panic_flat(ind, p):
    """T1 circuit-breaker C3 on VJ: extreme-VIX hard override.
    When VIX > panic_vix AND VIX 5-bar ROC > panic_roc, force exit and
    suppress entries for flat_bars. Distinct from VJ's existing >30 VIX panic."""
    entries_vj, death, vix_panic, _, _ = _vj_base(ind, p)
    n = ind.n
    vix = ind.vix
    panic_vix = float(p.get("panic_vix", 40.0))
    panic_roc = float(p.get("panic_roc", 1.5))
    flat_bars = int(p.get("flat_bars", 10))
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    suppress_remaining = 0
    for i in range(5, n):
        # Detect panic
        panic_now = False
        if (vix is not None and not np.isnan(vix[i]) and not np.isnan(vix[i - 5])
                and vix[i - 5] > 0
                and vix[i] > panic_vix and vix[i] / vix[i - 5] > panic_roc):
            panic_now = True
        # Suppression window management
        if panic_now:
            suppress_remaining = flat_bars
            exits[i] = True
            labels[i] = "PF"
        elif suppress_remaining > 0:
            suppress_remaining -= 1
        # Entries: VJ signal, unless suppressed
        if entries_vj[i] and suppress_remaining <= 0:
            entries[i] = True
        # Base exits
        if death[i] and not exits[i]:
            exits[i] = True
            labels[i] = "D"
        if vix_panic[i] and not exits[i]:
            exits[i] = True
            labels[i] = "V"
    return entries, exits, labels


def pullback_in_trend(ind, p):
    """T1 standalone (B9): mean reversion inside an uptrend.
    Entry: close > EMA(trend_len) AND close/max(high[-pullback_look..-1]) < 1-pullback_pct%
           AND two-bar reversal (close[-1]<close[-2] AND close>close[-1]).
    Exit: close < EMA(exit_ema) for exit_persist consecutive bars."""
    n = ind.n
    cl = ind.close
    hi = ind.high
    trend_len = int(p.get("trend_len", 200))
    pullback_look = int(p.get("pullback_look", 50))
    pullback_pct = float(p.get("pullback_pct", 15.0)) / 100.0
    exit_ema_len = int(p.get("exit_ema", 50))
    exit_persist = int(p.get("exit_persist", 3))
    trend_ema = ind.ema(trend_len)
    exit_ema = ind.ema(exit_ema_len)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)
    below_count = 0
    for i in range(max(trend_len, pullback_look) + 2, n):
        if np.isnan(trend_ema[i]) or np.isnan(exit_ema[i]):
            below_count = 0
            continue
        # Entry
        recent_high = np.nanmax(hi[i - pullback_look:i])
        if (cl[i] > trend_ema[i]
                and recent_high > 0 and cl[i] / recent_high < 1.0 - pullback_pct
                and cl[i - 1] < cl[i - 2] and cl[i] > cl[i - 1]):
            entries[i] = True
        # Exit: below exit_ema for exit_persist bars
        if cl[i] < exit_ema[i]:
            below_count += 1
        else:
            below_count = 0
        if below_count >= exit_persist:
            exits[i] = True
            labels[i] = "EX"
            below_count = 0
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
    # ── GC Enhancement Matrix 2026-04-20: Exit addons E1-E19 ──
    "gc_e1":  gc_e1,   # XLK trend confirmation on death cross
    "gc_e2":  gc_e2,   # RSI exit gate
    "gc_e3":  gc_e3,   # Volume-confirmed death cross
    "gc_e4":  gc_e4,   # ATR-scaled death cross buffer
    "gc_e5":  gc_e5,   # Gap acceleration filter
    "gc_e6":  gc_e6,   # ATR trailing stop replaces death cross
    "gc_e7":  gc_e7,   # Treasury yield curve mode A/B
    "gc_e8":  gc_e8,   # Fed funds direction modulator
    "gc_e9":  gc_e9,   # SGOV relative flow exit
    "gc_e10": gc_e10,  # Realized vol expansion exit
    "gc_e11": gc_e11,  # Drawdown percentage exit
    "gc_e12": gc_e12,  # MACD histogram divergence exit
    "gc_e13": gc_e13,  # Slow EMA slope flattening exit
    "gc_e14": gc_e14,  # Consecutive bearish bars exit
    "gc_e15": gc_e15,  # Gap-down exit
    "gc_e16": gc_e16,  # TECL/XLK relative-strength deterioration
    "gc_e17": gc_e17,  # Profit-lock trailing tightener
    "gc_e18": gc_e18,  # Time-in-trade max + slope check
    "gc_e19": gc_e19,  # VIX term structure proxy on death cross
    # ── GC Enhancement Matrix: Entry addons N1-N14 ──
    "gc_n1":  gc_n1,   # VIX entry gate
    "gc_n2":  gc_n2,   # ADX trend strength gate
    "gc_n3":  gc_n3,   # XLK rising entry gate
    "gc_n4":  gc_n4,   # Post-crash recovery gate
    "gc_n5":  gc_n5,   # Momentum acceleration entry
    "gc_n6":  gc_n6,   # Seasonality filter
    "gc_n7":  gc_n7,   # Volume surge entry
    "gc_n8":  gc_n8,   # MACD > 0 entry gate
    "gc_n9":  gc_n9,   # Bollinger Band squeeze entry
    "gc_n10": gc_n10,  # Bullish bar entry gate
    "gc_n11": gc_n11,  # VIX slope declining entry gate
    "gc_n12": gc_n12,  # Treasury spread > 0 entry gate
    "gc_n13": gc_n13,  # Multi-horizon return entry gate
    "gc_n14": gc_n14,  # Near 50d-high entry gate
    # ── GC Enhancement Matrix: Structural addons S1-S3 ──
    "gc_s1":  gc_s1,   # Adaptive cooldown
    "gc_s2":  gc_s2,   # Bear regime memory
    "gc_s3":  gc_s3,   # Asymmetric VIX re-entry
    # ── GC Enhancement Matrix: Combo addons C1-C8 ──
    "gc_c1":  gc_c1,   # VIX entry + XLK exit confirmation
    "gc_c2":  gc_c2,   # RSI exit gate + treasury curve mode B
    "gc_c3":  gc_c3,   # XLK exit + realized vol expansion exit + VIX panic
    "gc_c4":  gc_c4,   # VIX entry gate + treasury curve A exit
    "gc_c5":  gc_c5,   # XLK exit + profit-lock trailing tightener
    "gc_c6":  gc_c6,   # RSI exit gate + VIX term structure
    "gc_c7":  gc_c7,   # treasury A + bear regime memory + adaptive cooldown
    "gc_c8":  gc_c8,   # full defense stack
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 1) ──
    "gc_vjx":   gc_vjx,    # A1: VJ + dual-confirmed VIX shock exit
    "gc_vjxr":  gc_vjxr,   # A2: VJ + price-velocity shock exit + RSI-bounce re-entry
    "gc_vjv":   gc_vjv,    # A3: VJ + realized-vol calm entry gate
    "gc_vjatr": gc_vjatr,  # A10: VJ + ATR-expansion directional shock exit
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 2) ──
    "gc_vjrsi":         gc_vjrsi,          # A4: VJ + RSI-bounce secondary entry
    "gc_vjsgov":        gc_vjsgov,         # A6: VJ + SGOV relative-strength rotation exit
    "gc_vjtimer":       gc_vjtimer,        # A8: VJ + time-based escape hatch
    "pullback_in_trend": pullback_in_trend, # B9: standalone buy-the-dip
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 3) ──
    "rsi_regime_canonical": rsi_regime_canonical,  # B1: canonical-only RSI regime revive
    "dual_tf_gc":           dual_tf_gc,            # B4: nested EMA pair-ups
    "tecl_sgov_rs":         tecl_sgov_rs,          # B14: TECL/SGOV relative-strength rotation
    # ── Circuit breakers on VJ (Round 4, Bucket C) ──
    "gc_n8_ddbreaker":  gc_n8_ddbreaker,   # C1: drawdown circuit breaker (pause/resume)
    "gc_n8_timelimit":  gc_n8_timelimit,   # C2: max-hold escape hatch
    "gc_n8_panic_flat": gc_n8_panic_flat,  # C3: extreme-VIX hard override
    # ── Final batch 2026-04-20 (deferred A + remaining B) ──
    "gc_vjmac":                 gc_vjmac,                   # A5
    "gc_vjbb":                  gc_vjbb,                    # A7
    "gc_vjdd":                  gc_vjdd,                    # A9
    "vol_regime_canonical":     vol_regime_canonical,       # B2
    "composite_osc_canonical":  composite_osc_canonical,    # B3
    "bounce_breakout":          bounce_breakout,            # B5
    "tri_filter_macd":          tri_filter_macd,            # B6
    "momentum_roc_canonical":   momentum_roc_canonical,     # B8
    "adaptive_ema_vol":         adaptive_ema_vol,           # B10
    "regime_state_machine":     regime_state_machine,       # B11
    # ── Diversity Sprint 2026-04-27: orthogonal marker-failure hypotheses ──
    "airbag_vix_atr":           airbag_vix_atr,             # D1: fast crash airbag
    "reclaimer_vol_rsi":        reclaimer_vol_rsi,          # D2: post-panic re-entry
    "state_machine_crash_recovery": state_machine_crash_recovery, # D3: explicit states
    "gc_vjatr_airbag":          gc_vjatr_airbag,            # D4: Bonobo + airbag exits
    "gc_vjatr_reclaimer":       gc_vjatr_reclaimer,         # D5: Bonobo + recovery entries
    "gc_vjatr_state_filter":    gc_vjatr_state_filter,      # D6: Bonobo + state filter exits
    "gc_vjatr_timing_repair":   gc_vjatr_timing_repair,     # D7: minimal post-drawdown re-entry
    "ensemble_vote_3of5":       ensemble_vote_3of5,         # B12
    "fed_macro_primary":        fed_macro_primary,          # B13
    "slope_only_200":           slope_only_200,             # B16
    # ── Next-Frontier 2026-04-20 (Lane 2: VJ cross-asset rescue) ──
    "gc_vj_decay_gate":        gc_vj_decay_gate,        # N6
    "gc_vj_xlk_relative_trend": gc_vj_xlk_relative_trend, # N5
    "gc_vj_dual_regime":       gc_vj_dual_regime,       # N9
    # ── Next-Frontier 2026-04-20 (Lane 1: generalization-first) ──
    "rank_slope_regime":       rank_slope_regime,       # N1
    "zscore_return_reversion": zscore_return_reversion, # N3
    # ── Next-Frontier 2026-04-20 (Lane 3: unused data) ──
    "breadth_decay_composite": breadth_decay_composite, # N8
    # ── Next-Frontier 2026-04-20 (Lane 4: meta + infrastructure) ──
    "vj_or_slope_meta":        vj_or_slope_meta,        # N10
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
    # ── GC Enhancement Matrix 2026-04-20 addons (E1-E19, N1-N14, S1-S3) ──
    "gc_e1":  "T1", "gc_e2":  "T1", "gc_e3":  "T1", "gc_e4":  "T1",
    "gc_e5":  "T1", "gc_e6":  "T1", "gc_e7":  "T1", "gc_e8":  "T1",
    "gc_e9":  "T1", "gc_e10": "T1", "gc_e11": "T1", "gc_e12": "T1",
    "gc_e13": "T1", "gc_e14": "T1", "gc_e15": "T1", "gc_e16": "T1",
    "gc_e17": "T1", "gc_e18": "T1", "gc_e19": "T1",
    "gc_n1":  "T1", "gc_n2":  "T1", "gc_n3":  "T1", "gc_n4":  "T1",
    "gc_n5":  "T1", "gc_n6":  "T1", "gc_n7":  "T1", "gc_n8":  "T1",
    "gc_n9":  "T1", "gc_n10": "T1", "gc_n11": "T1", "gc_n12": "T1",
    "gc_n13": "T1", "gc_n14": "T1",
    "gc_s1":  "T1", "gc_s2":  "T1", "gc_s3":  "T1",
    "gc_c1":  "T1", "gc_c2":  "T1", "gc_c3":  "T1", "gc_c4":  "T1",
    "gc_c5":  "T1", "gc_c6":  "T1", "gc_c7":  "T1", "gc_c8":  "T1",
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 1) ──
    "gc_vjx":   "T1", "gc_vjxr":  "T1", "gc_vjv":   "T1", "gc_vjatr": "T1",
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 2) ──
    "gc_vjrsi":         "T1",
    "gc_vjsgov":        "T1",
    "gc_vjtimer":       "T1",
    "pullback_in_trend": "T1",
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 3) ──
    "rsi_regime_canonical": "T1",
    "dual_tf_gc":           "T1",
    "tecl_sgov_rs":         "T1",
    # ── Circuit breakers on VJ (Round 4, Bucket C) ──
    "gc_n8_ddbreaker":  "T1",
    "gc_n8_timelimit":  "T1",
    "gc_n8_panic_flat": "T1",
    # ── Final batch 2026-04-20 (deferred A + remaining B) ──
    "gc_vjmac":                 "T1",
    "gc_vjbb":                  "T1",
    "gc_vjdd":                  "T1",
    "vol_regime_canonical":     "T1",
    "composite_osc_canonical":  "T2",  # ≥8 tunable
    "bounce_breakout":          "T1",
    "tri_filter_macd":          "T1",
    "momentum_roc_canonical":   "T1",
    "adaptive_ema_vol":         "T1",
    "regime_state_machine":     "T2",  # brainstorm explicit: exploratory, not promotion-track
    "airbag_vix_atr":           "T1",
    "reclaimer_vol_rsi":        "T1",
    "state_machine_crash_recovery": "T1",
    "gc_vjatr_airbag":          "T1",
    "gc_vjatr_reclaimer":       "T1",
    "gc_vjatr_state_filter":    "T1",
    "gc_vjatr_timing_repair":   "T1",
    "ensemble_vote_3of5":       "T1",
    "fed_macro_primary":        "T1",
    "slope_only_200":           "T1",
    # ── Next-Frontier 2026-04-20 (Lane 2) ──
    "gc_vj_decay_gate":        "T1",
    "gc_vj_xlk_relative_trend": "T1",
    "gc_vj_dual_regime":       "T1",
    # ── Next-Frontier 2026-04-20 (Lane 1) ──
    "rank_slope_regime":       "T1",
    "zscore_return_reversion": "T1",
    # ── Next-Frontier 2026-04-20 (Lane 3) ──
    "breadth_decay_composite": "T1",
    # ── Next-Frontier 2026-04-20 (Lane 4) ──
    "vj_or_slope_meta":        "T1",
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
    # ── T1: Diversity Sprint 2026-04-27 (marker-failure hypotheses) ──
    "airbag_vix_atr": {
        "trend_len":        (150, 200, 50, int),
        "repair_len":       (30, 70, 20, int),
        "atr_short":        (7, 21, 7, int),
        "atr_long":         (50, 100, 25, int),
        "vix_lookback":     (3, 7, 2, int),
        "vix_spike_pct":    (25.0, 45.0, 10.0, float),
        "vix_level":        (24.0, 32.0, 4.0, float),
        "vix_reset":        (20.0, 26.0, 3.0, float),
        "atr_ratio_exit":   (1.3, 1.9, 0.3, float),
        "cooldown":         (0, 10, 5, int),
    },
    "reclaimer_vol_rsi": {
        "rsi_len":          (7, 21, 7, int),
        "fast_len":         (30, 70, 20, int),
        "trend_len":        (100, 200, 50, int),
        "vol_short":        (10, 30, 10, int),
        "vol_long":         (60, 120, 30, int),
        "drawdown_lookback": (80, 160, 40, int),
        "drawdown_pct":     (20.0, 35.0, 5.0, float),
        "rsi_reclaim":      (40.0, 50.0, 5.0, float),
        "vol_ratio_max":    (0.80, 1.05, 0.05, float),
        "cooldown":         (0, 10, 5, int),
    },
    "state_machine_crash_recovery": {
        "fast_len":         (30, 70, 20, int),
        "slow_len":         (150, 250, 50, int),
        "rsi_len":          (7, 21, 7, int),
        "vol_short":        (10, 30, 10, int),
        "vol_long":         (60, 120, 30, int),
        "vix_lookback":     (3, 7, 2, int),
        "vix_shock_pct":    (25.0, 45.0, 10.0, float),
        "vix_shock_level":  (24.0, 32.0, 4.0, float),
        "vix_repair_level": (20.0, 26.0, 3.0, float),
        "vol_shock_ratio":  (1.25, 1.75, 0.25, float),
        "cooldown":         (0, 10, 5, int),
    },
    "gc_vjatr_airbag": {
        "fast_ema":         (100, 140, 20, int),
        "slow_ema":         (150, 200, 10, int),
        "slope_window":     (1, 3, 1, int),
        "entry_bars":       (2, 3, 1, int),
        "cooldown":         (0, 5, 5, int),
        "atr_period":       (14, 20, 2, int),
        "atr_look":         (20, 60, 10, int),
        "atr_expand":       (1.5, 2.5, 0.5, float),
        "atr_confirm":      (3, 5, 1, int),
        "trend_len":        (150, 200, 50, int),
        "repair_len":       (50, 70, 20, int),
        "vix_lookback":     (3, 7, 2, int),
        "vix_spike_pct":    (25.0, 45.0, 10.0, float),
        "vix_level":        (24.0, 32.0, 4.0, float),
        "vix_reset":        (20.0, 26.0, 3.0, float),
        "atr_short":        (7, 14, 7, int),
        "atr_long":         (50, 100, 25, int),
        "atr_ratio_exit":   (1.3, 1.9, 0.3, float),
    },
    "gc_vjatr_reclaimer": {
        "fast_ema":         (100, 140, 20, int),
        "slow_ema":         (150, 200, 10, int),
        "slope_window":     (1, 3, 1, int),
        "entry_bars":       (2, 3, 1, int),
        "cooldown":         (0, 5, 5, int),
        "atr_period":       (14, 20, 2, int),
        "atr_look":         (20, 60, 10, int),
        "atr_expand":       (1.5, 2.5, 0.5, float),
        "atr_confirm":      (3, 5, 1, int),
        "rsi_len":          (7, 21, 7, int),
        "fast_len":         (30, 70, 20, int),
        "trend_len":        (100, 200, 50, int),
        "vol_short":        (10, 30, 10, int),
        "vol_long":         (60, 120, 30, int),
        "drawdown_lookback": (80, 160, 40, int),
        "drawdown_pct":     (20.0, 35.0, 5.0, float),
        "rsi_reclaim":      (40.0, 50.0, 5.0, float),
        "vol_ratio_max":    (0.80, 1.05, 0.05, float),
    },
    "gc_vjatr_state_filter": {
        "fast_ema":         (100, 140, 20, int),
        "slow_ema":         (150, 200, 10, int),
        "slope_window":     (1, 3, 1, int),
        "entry_bars":       (2, 3, 1, int),
        "cooldown":         (0, 5, 5, int),
        "atr_period":       (14, 20, 2, int),
        "atr_look":         (20, 60, 10, int),
        "atr_expand":       (1.5, 2.5, 0.5, float),
        "atr_confirm":      (3, 5, 1, int),
        "fast_len":         (30, 70, 20, int),
        "slow_len":         (150, 250, 50, int),
        "rsi_len":          (7, 21, 7, int),
        "vol_short":        (10, 30, 10, int),
        "vol_long":         (60, 120, 30, int),
        "vix_lookback":     (3, 7, 2, int),
        "vix_shock_pct":    (25.0, 45.0, 10.0, float),
        "vix_shock_level":  (24.0, 32.0, 4.0, float),
        "vix_repair_level": (20.0, 26.0, 3.0, float),
        "vol_shock_ratio":  (1.25, 1.75, 0.25, float),
    },
    "gc_vjatr_timing_repair": {
        "fast_ema":          (100, 140, 20, int),
        "slow_ema":          (150, 200, 10, int),
        "slope_window":      (1, 3, 1, int),
        "entry_bars":        (2, 3, 1, int),
        "cooldown":          (0, 5, 5, int),
        "atr_period":        (14, 20, 2, int),
        "atr_look":          (20, 60, 10, int),
        "atr_expand":        (1.5, 2.5, 0.5, float),
        "atr_confirm":       (3, 5, 1, int),
        "repair_len":        (20, 50, 10, int),
        "rsi_len":           (7, 21, 7, int),
        "drawdown_lookback": (40, 100, 20, int),
        "drawdown_pct":      (10.0, 25.0, 5.0, float),
        "repair_slope":      (1, 5, 2, int),
        "rsi_floor":         (35.0, 45.0, 5.0, float),
        "vix_ceiling":       (30.0, 50.0, 10.0, float),
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
