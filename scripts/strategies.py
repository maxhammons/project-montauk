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
# Strategy: PSAR Trend Follow — Parabolic SAR as primary regime signal.
# Simplest possible trend follower. Enter above PSAR + trend EMA, exit below.
# Only 5 params — maximizes complexity bonus.
# ─────────────────────────────────────────────────────────────────────────────

def psar_trend(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    psar = ind.psar()
    trend_ema = ind.ema(p.get("trend_len", 100))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    for i in range(1, n):
        if np.isnan(psar[i]) or np.isnan(psar[i-1]):
            continue

        trend_ok = np.isnan(trend_ema[i]) or cl[i] > trend_ema[i]

        # Entry: price crosses above PSAR + trend OK
        if cl[i-1] <= psar[i-1] and cl[i] > psar[i] and trend_ok:
            entries[i] = True

        # Exit 1: price crosses below PSAR
        if cl[i-1] >= psar[i-1] and cl[i] < psar[i]:
            exits[i] = True
            labels[i] = "PSAR Flip"
            continue

        # Exit 2: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

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
# Strategy 18: Stochastic Drawdown Recovery — Slow stochastic crossover
# from oversold, but only after a deep drawdown or in confirmed uptrend.
# ─────────────────────────────────────────────────────────────────────────────

def stoch_drawdown_recovery(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    stoch_len = p.get("stoch_len", 21)
    smooth_k = p.get("smooth_k", 5)
    smooth_d = p.get("smooth_d", 5)
    stoch_k = ind.stoch_k(stoch_len, smooth_k)
    stoch_d = ind.stoch_d(stoch_len, smooth_k, smooth_d)
    dd_lookback = p.get("dd_lookback", 252)
    highest = ind.highest(dd_lookback)
    trend_ema = ind.ema(p.get("trend_len", 150))
    atr_vals = ind.atr(p.get("atr_period", 30))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_stoch = p.get("entry_stoch", 25)
    exit_stoch = p.get("exit_stoch", 80)
    dd_thresh = p.get("dd_thresh", -35.0)

    for i in range(1, n):
        if np.isnan(stoch_k[i]) or np.isnan(stoch_d[i]) or np.isnan(stoch_k[i-1]) or np.isnan(stoch_d[i-1]):
            continue

        # Drawdown context: either in deep drawdown or price above trend
        dd = 0.0
        if not np.isnan(highest[i]) and highest[i] > 0:
            dd = (cl[i] - highest[i]) / highest[i] * 100
        in_deep_dd = dd <= dd_thresh
        trend_ok = not np.isnan(trend_ema[i]) and cl[i] > trend_ema[i]

        # Entry: stoch K crosses above D from below entry level + context filter
        stoch_cross = stoch_k[i-1] <= stoch_d[i-1] and stoch_k[i] > stoch_d[i]
        stoch_low = stoch_k[i] < entry_stoch

        if stoch_cross and stoch_low and (in_deep_dd or trend_ok):
            entries[i] = True

        # Exit: stoch overbought
        if stoch_k[i] >= exit_stoch:
            exits[i] = True
            labels[i] = "Stoch Overbought"
            continue

        # Exit: ATR shock
        if not np.isnan(atr_vals[i]) and i >= 1:
            if cl[i] < cl[i-1] - atr_vals[i] * p.get("atr_mult", 3.5):
                exits[i] = True
                labels[i] = "ATR Shock"

    return entries, exits, labels


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 19: Williams %R Midline Reclaim — Williams %R escapes deep oversold
# while price reclaims Donchian midpoint. Higher-conviction regime transitions.
# ─────────────────────────────────────────────────────────────────────────────

def williams_midline_reclaim(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    cl = ind.close
    wr = ind.willr(p.get("willr_len", 21))
    don_mid = ind.donchian_mid(p.get("channel_len", 60))
    trend_ema = ind.ema(p.get("trend_len", 150))
    vol_short = ind.realized_vol(p.get("vol_short", 15))
    vol_long = ind.realized_vol(p.get("vol_long", 60))

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    entry_wr = p.get("entry_wr", -75.0)
    exit_wr = p.get("exit_wr", -10.0)
    rebreak_wr = p.get("rebreak_wr", -55.0)
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

STRATEGY_REGISTRY = {
    "montauk_821":              montauk_821,
    "rsi_regime":               rsi_regime,
    "breakout":                 breakout,
    "rsi_regime_trail":         rsi_regime_trail,
    "vol_regime":               vol_regime,
    "ichimoku_trend":           ichimoku_trend,
    "dual_momentum":            dual_momentum,
    "rsi_vol_regime":           rsi_vol_regime,
    "stoch_drawdown_recovery":  stoch_drawdown_recovery,
    "williams_midline_reclaim": williams_midline_reclaim,
    "adx_trend":                adx_trend,
    "keltner_squeeze":          keltner_squeeze,
    "psar_trend":               psar_trend,
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
    "rsi_vol_regime": {
        "rsi_len": (7, 21, 2, int), "trend_len": (50, 200, 25, int),
        "entry_rsi": (25, 45, 5, float), "exit_rsi": (65, 85, 5, float),
        "panic_rsi": (10, 25, 5, float), "vol_short": (10, 30, 5, int),
        "vol_long": (40, 100, 10, int), "vol_ratio_max": (0.7, 1.0, 0.05, float),
        "vol_exit_ratio": (1.2, 2.0, 0.2, float), "cooldown": (0, 20, 5, int),
    },
    "adx_trend": {
        "adx_len": (10, 30, 4, int), "trend_len": (50, 200, 25, int),
        "entry_adx": (15.0, 30.0, 5.0, float), "exit_adx": (10.0, 20.0, 5.0, float),
        "cooldown": (0, 20, 5, int),
    },
    "keltner_squeeze": {
        "bb_len": (15, 30, 5, int), "bb_mult": (1.5, 2.5, 0.5, float),
        "kelt_len": (15, 30, 5, int), "kelt_mult": (1.0, 2.0, 0.5, float),
        "trend_len": (50, 200, 25, int), "mom_len": (8, 20, 4, int),
        "cooldown": (0, 20, 5, int),
    },
    "psar_trend": {
        "trend_len": (50, 200, 25, int), "atr_period": (10, 40, 10, int),
        "atr_mult": (2.0, 5.0, 0.5, float), "cooldown": (0, 20, 5, int),
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
    "stoch_drawdown_recovery": {
        "dd_lookback": (100, 300, 50, int), "dd_thresh": (-50.0, -20.0, 5.0, float),
        "stoch_len": (14, 40, 4, int), "smooth_k": (3, 10, 2, int),
        "smooth_d": (3, 10, 2, int), "entry_stoch": (15, 35, 5, float),
        "exit_stoch": (70, 90, 5, float), "trend_len": (100, 200, 25, int),
        "atr_period": (15, 40, 5, int), "atr_mult": (2.5, 5.0, 0.5, float),
        "cooldown": (5, 20, 5, int),
    },
    "williams_midline_reclaim": {
        "willr_len": (14, 34, 4, int), "entry_wr": (-90.0, -60.0, 5.0, float),
        "exit_wr": (-20.0, -5.0, 5.0, float), "rebreak_wr": (-70.0, -40.0, 5.0, float),
        "channel_len": (40, 100, 10, int), "trend_len": (100, 200, 25, int),
        "vol_short": (10, 25, 5, int), "vol_long": (40, 90, 10, int),
        "vol_ratio_max": (0.75, 1.0, 0.05, float), "vol_exit_ratio": (1.2, 1.8, 0.1, float),
        "cooldown": (5, 20, 5, int),
    },
}
