"""
Experimental strategy: regime_score

A continuous scoring system that replaces boolean entry/exit gates with
weighted signal contributions. Each signal produces a 0-to-1 score via
tanh normalization. The weighted sum is compared to a threshold.

Why this is different from everything on the leaderboard:
  - Every current strategy uses hard boolean gates (pass/fail)
  - This degrades gracefully — "pretty good" on 3 signals beats "perfect" on 1
  - Uses era-agnostic signals (price-from-peak, price/MA ratio) alongside
    RSI so it doesn't depend on volatile markets to produce clean signals

Four signals, four weights, one entry threshold, one exit threshold.
~14 parameters total — in the sweet spot that the leaderboard proved works.
"""

from __future__ import annotations
import numpy as np
from engine.strategy_engine import Indicators


def _tanh_norm(value: float, center: float, scale: float) -> float:
    """Normalize a value to 0-1 range using tanh, centered on `center`.
    scale controls sensitivity — smaller = sharper transition."""
    if scale == 0:
        return 0.5
    x = (value - center) / scale
    # tanh gives -1 to 1, remap to 0 to 1
    return (np.tanh(x) + 1.0) / 2.0


def regime_score(ind: Indicators, p: dict) -> tuple:
    """
    Continuous scoring strategy with 4 era-agnostic signals.

    Entry signals (high score = bullish recovery):
      1. Drawdown depth — how far below trailing peak (deeper = higher score)
      2. RSI recovery — RSI rising from oversold (lower RSI = higher score)
      3. Vol ratio calming — short vol / long vol declining (lower = higher)
      4. Price/MA ratio — price below long-term MA (lower = higher score)

    Exit signals (high score = bearish exhaustion):
      1. Price extension — how far above trailing trough (higher = higher score)
      2. RSI overbought — high RSI = higher score
      3. Vol ratio spiking — short vol / long vol rising (higher = higher)
      4. Price/MA ratio — price above long-term MA (higher = higher score)

    Each signal is normalized to 0-1 via tanh, then weighted. When the
    weighted sum crosses the threshold, we enter or exit.
    """
    n = ind.n
    cl = ind.close

    # Indicators
    rsi = ind.rsi(p.get("rsi_len", 13))
    ma_long = ind.ema(p.get("ma_len", 200))
    vol_short = ind.realized_vol(p.get("vol_short", 25))
    vol_long = ind.realized_vol(p.get("vol_long", 60))
    dd_lookback = p.get("dd_lookback", 200)
    highest = ind.highest(dd_lookback)
    lowest = ind.lowest(dd_lookback)

    # Weights (must sum to ~1 but optimizer doesn't enforce — relative matters)
    w_dd = p.get("w_drawdown", 0.30)
    w_rsi = p.get("w_rsi", 0.25)
    w_vol = p.get("w_vol", 0.20)
    w_ma = p.get("w_price_ma", 0.25)

    # Thresholds
    entry_thresh = p.get("entry_thresh", 0.65)
    exit_thresh = p.get("exit_thresh", 0.65)

    # Normalization centers and scales
    # Drawdown: center at -25% (a moderate crash), scale 15 (gradual)
    dd_center = p.get("dd_center", -25.0)
    dd_scale = p.get("dd_scale", 15.0)
    # RSI entry: center at 35 (oversold zone), scale 15
    rsi_entry_center = p.get("rsi_center", 35.0)
    rsi_scale = p.get("rsi_scale", 15.0)
    # Price/MA: center at 1.0, scale 0.2
    ma_center = p.get("ma_center", 1.0)
    ma_scale = p.get("ma_scale", 0.2)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    panic_rsi = p.get("panic_rsi", 15)
    prev_entry_score = 0.0
    prev_exit_score = 0.0

    for i in range(1, n):
        if np.isnan(rsi[i]):
            continue

        # ── Compute raw values ──

        # 1. Drawdown from peak (negative number, e.g. -35%)
        dd_pct = 0.0
        if not np.isnan(highest[i]) and highest[i] > 0:
            dd_pct = (cl[i] - highest[i]) / highest[i] * 100

        # 2. RSI value
        rsi_val = rsi[i]

        # 3. Vol ratio (short/long)
        vol_ratio = 1.0
        if not np.isnan(vol_short[i]) and not np.isnan(vol_long[i]) and vol_long[i] > 0:
            vol_ratio = vol_short[i] / vol_long[i]

        # 4. Price / MA ratio
        price_ma = 1.0
        if not np.isnan(ma_long[i]) and ma_long[i] > 0:
            price_ma = cl[i] / ma_long[i]

        # Rise from trough (for exit scoring)
        rise_pct = 0.0
        if not np.isnan(lowest[i]) and lowest[i] > 0:
            rise_pct = (cl[i] - lowest[i]) / lowest[i] * 100

        # ── Entry score (high = bullish recovery) ──
        # Deep drawdown → high score (invert: more negative dd = higher)
        s_dd = _tanh_norm(-dd_pct, -dd_center, dd_scale)
        # Low RSI → high score (invert: lower RSI = higher)
        s_rsi_entry = _tanh_norm(-rsi_val, -rsi_entry_center, rsi_scale)
        # Low vol ratio → high score (invert: lower ratio = higher)
        s_vol_entry = _tanh_norm(-vol_ratio, -1.0, 0.3)
        # Price below MA → high score (invert: lower price/MA = higher)
        s_ma_entry = _tanh_norm(-price_ma, -ma_center, ma_scale)

        entry_score = w_dd * s_dd + w_rsi * s_rsi_entry + w_vol * s_vol_entry + w_ma * s_ma_entry

        # ── Exit score (high = bearish exhaustion) ──
        # High rise from trough → high score
        s_rise = _tanh_norm(rise_pct, 50.0, 30.0)
        # High RSI → high score
        s_rsi_exit = _tanh_norm(rsi_val, 65.0, rsi_scale)
        # High vol ratio → high score (storm arriving)
        s_vol_exit = _tanh_norm(vol_ratio, 1.2, 0.3)
        # Price above MA → high score
        s_ma_exit = _tanh_norm(price_ma, ma_center, ma_scale)

        exit_score = w_dd * s_rise + w_rsi * s_rsi_exit + w_vol * s_vol_exit + w_ma * s_ma_exit

        # ── Entry: score crosses above threshold ──
        if prev_entry_score < entry_thresh and entry_score >= entry_thresh:
            entries[i] = True

        # ── Exit: score crosses above threshold ──
        if prev_exit_score < exit_thresh and exit_score >= exit_thresh:
            exits[i] = True
            labels[i] = "Score Exit"

        # ── Panic exit: unconditional RSI crash ──
        if rsi[i] < panic_rsi:
            exits[i] = True
            labels[i] = "RSI Panic"

        prev_entry_score = entry_score
        prev_exit_score = exit_score

    return entries, exits, labels


# Parameter space — 14 parameters
REGIME_SCORE_PARAMS = {
    "rsi_len": (7, 21, 2, int),
    "ma_len": (100, 300, 50, int),
    "vol_short": (10, 30, 5, int),
    "vol_long": (40, 100, 10, int),
    "dd_lookback": (100, 300, 50, int),
    "w_drawdown": (0.1, 0.5, 0.1, float),
    "w_rsi": (0.1, 0.4, 0.1, float),
    "w_vol": (0.1, 0.4, 0.1, float),
    "w_price_ma": (0.1, 0.4, 0.1, float),
    "entry_thresh": (0.5, 0.8, 0.05, float),
    "exit_thresh": (0.5, 0.8, 0.05, float),
    "dd_center": (-35.0, -15.0, 5.0, float),
    "panic_rsi": (10, 25, 5, float),
    "cooldown": (0, 20, 5, int),
}
