#!/usr/bin/env python3
"""
Modular backtesting engine for Project Montauk.

Separates the WHAT (strategy logic) from the HOW (position management,
equity tracking, metrics). Any strategy that implements entry/exit signals
as numpy arrays can be tested.

Usage:
    from engine.strategy_engine import backtest, Indicators, metrics_from_trades

    ind = Indicators(df)  # pre-compute all common indicators
    entries, exits, exit_labels = my_strategy(ind, params)
    result = backtest(df, entries, exits, exit_labels)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional
import warnings


# ─────────────────────────────────────────────────────────────────────────────
# Indicator library — pre-computed, shared across all strategies
# ─────────────────────────────────────────────────────────────────────────────

def _ema(series: np.ndarray, length: int) -> np.ndarray:
    """Pine Script ta.ema() — recursive EMA with SMA seed.

    Handles NaN-prefixed input (e.g., chained EMAs in TEMA) by finding the
    first window of `length` consecutive non-NaN values for the SMA seed.
    """
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    # Find first index where we have `length` consecutive non-NaN values
    run = 0
    seed_end = -1
    for i in range(len(series)):
        if not np.isnan(series[i]):
            run += 1
            if run >= length:
                seed_end = i
                break
        else:
            run = 0
    if seed_end < 0:
        return out
    seed_start = seed_end - length + 1
    out[seed_end] = np.mean(series[seed_start:seed_end + 1])
    for i in range(seed_end + 1, len(series)):
        if np.isnan(series[i]):
            continue  # skip NaN input, leave output NaN
        if np.isnan(out[i - 1]):
            out[i] = series[i]  # re-seed after gap
        else:
            out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _rma(series: np.ndarray, length: int) -> np.ndarray:
    """Wilder's smoothing (RMA) — used by ATR and RSI."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 1.0 / length
    out[length - 1] = np.mean(series[:length])
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _sma(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(series, np.nan, dtype=np.float64)
    for i in range(length - 1, len(series)):
        out[i] = np.mean(series[i - length + 1:i + 1])
    return out


def _tema(series: np.ndarray, length: int) -> np.ndarray:
    e1 = _ema(series, length)
    e2 = _ema(e1, length)
    e3 = _ema(e2, length)
    return 3 * e1 - 3 * e2 + e3


def _atr(hi: np.ndarray, lo: np.ndarray, cl: np.ndarray, period: int) -> np.ndarray:
    n = len(cl)
    tr = np.zeros(n)
    tr[0] = hi[0] - lo[0]
    for i in range(1, n):
        tr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i-1]), abs(lo[i] - cl[i-1]))
    return _rma(tr, period)


def _highest(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(series, np.nan)
    for i in range(length - 1, len(series)):
        out[i] = np.max(series[i - length + 1:i + 1])
    return out


def _lowest(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(series, np.nan)
    for i in range(length - 1, len(series)):
        out[i] = np.min(series[i - length + 1:i + 1])
    return out


def _rsi(series: np.ndarray, length: int) -> np.ndarray:
    n = len(series)
    out = np.full(n, np.nan)
    if n < length + 1:
        return out
    delta = np.diff(series, prepend=series[0])
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = _rma(gains, length)
    avg_loss = _rma(losses, length)
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    out = 100.0 - 100.0 / (1.0 + rs)
    return out


def _stddev(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(series, np.nan, dtype=np.float64)
    for i in range(length - 1, len(series)):
        out[i] = np.std(series[i - length + 1:i + 1], ddof=0)
    return out


def _slope(series: np.ndarray, lookback: int) -> np.ndarray:
    """Slope: (series[i] - series[i - lookback]) / lookback."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    for i in range(lookback, len(series)):
        if not np.isnan(series[i]) and not np.isnan(series[i - lookback]):
            out[i] = (series[i] - series[i - lookback]) / lookback
    return out


def _pct_change(series: np.ndarray, lookback: int) -> np.ndarray:
    """Percent change over lookback bars."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    for i in range(lookback, len(series)):
        if not np.isnan(series[i]) and not np.isnan(series[i - lookback]) and series[i - lookback] != 0:
            out[i] = (series[i] - series[i - lookback]) / series[i - lookback] * 100
    return out


class Indicators:
    """
    Pre-computed indicator cache. Compute once, use across all strategies.
    Access indicators by calling methods with desired lengths.
    Results are cached — same (indicator, length) pair is computed only once.
    """

    def __init__(self, df: pd.DataFrame):
        self.dates = df["date"].values
        self.open = df["open"].values.astype(np.float64)
        self.high = df["high"].values.astype(np.float64)
        self.low = df["low"].values.astype(np.float64)
        self.close = df["close"].values.astype(np.float64)
        self.volume = df["volume"].values.astype(np.float64) if "volume" in df.columns else np.ones(len(self.close))
        self.vix = df["vix_close"].values.astype(np.float64) if "vix_close" in df.columns else None
        self.treasury_spread = df["treasury_spread"].values.astype(np.float64) if "treasury_spread" in df.columns else None
        self.fed_funds_rate = df["fed_funds_rate"].values.astype(np.float64) if "fed_funds_rate" in df.columns else None
        self.xlk_close = df["xlk_close"].values.astype(np.float64) if "xlk_close" in df.columns else None
        self.sgov_close = df["sgov_close"].values.astype(np.float64) if "sgov_close" in df.columns else None
        self.n = len(self.close)
        self._cache = {}

    def _cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def ema(self, length: int) -> np.ndarray:
        return self._cached(("ema", length), lambda: _ema(self.close, length))

    def sma(self, length: int) -> np.ndarray:
        return self._cached(("sma", length), lambda: _sma(self.close, length))

    def tema(self, length: int) -> np.ndarray:
        return self._cached(("tema", length), lambda: _tema(self.close, length))

    def atr(self, period: int) -> np.ndarray:
        return self._cached(("atr", period), lambda: _atr(self.high, self.low, self.close, period))

    def rsi(self, length: int) -> np.ndarray:
        return self._cached(("rsi", length), lambda: _rsi(self.close, length))

    def highest(self, length: int) -> np.ndarray:
        return self._cached(("highest", length), lambda: _highest(self.high, length))

    def lowest(self, length: int) -> np.ndarray:
        return self._cached(("lowest", length), lambda: _lowest(self.low, length))

    def stddev(self, length: int) -> np.ndarray:
        return self._cached(("stddev", length), lambda: _stddev(self.close, length))

    def slope(self, series_key: str, series: np.ndarray, lookback: int) -> np.ndarray:
        return self._cached(("slope", series_key, lookback), lambda: _slope(series, lookback))

    def pct_change(self, length: int) -> np.ndarray:
        return self._cached(("pct_change", length), lambda: _pct_change(self.close, length))

    def vol_ema(self, length: int) -> np.ndarray:
        return self._cached(("vol_ema", length), lambda: _ema(self.volume, length))

    def bb_upper(self, length: int, mult: float = 2.0) -> np.ndarray:
        return self._cached(("bb_upper", length, mult),
                            lambda: self.sma(length) + mult * self.stddev(length))

    def bb_lower(self, length: int, mult: float = 2.0) -> np.ndarray:
        return self._cached(("bb_lower", length, mult),
                            lambda: self.sma(length) - mult * self.stddev(length))

    def bb_width(self, length: int, mult: float = 2.0) -> np.ndarray:
        sma = self.sma(length)
        upper = self.bb_upper(length, mult)
        lower = self.bb_lower(length, mult)
        return self._cached(("bb_width", length, mult),
                            lambda: np.where(sma > 0, (upper - lower) / sma, np.nan))

    # ── MACD ──
    def macd_line(self, fast: int = 12, slow: int = 26) -> np.ndarray:
        return self._cached(("macd_line", fast, slow),
                            lambda: _ema(self.close, fast) - _ema(self.close, slow))

    def macd_signal(self, fast: int = 12, slow: int = 26, sig: int = 9) -> np.ndarray:
        return self._cached(("macd_signal", fast, slow, sig),
                            lambda: _ema(self.macd_line(fast, slow), sig))

    def macd_hist(self, fast: int = 12, slow: int = 26, sig: int = 9) -> np.ndarray:
        return self._cached(("macd_hist", fast, slow, sig),
                            lambda: self.macd_line(fast, slow) - self.macd_signal(fast, slow, sig))

    # ── Stochastic ──
    def stoch_k(self, length: int = 14, smooth: int = 3) -> np.ndarray:
        def _calc():
            h = _highest(self.high, length)
            l = _lowest(self.low, length)
            raw = np.where((h - l) > 0, (self.close - l) / (h - l) * 100, 50.0)
            return _sma(raw, smooth)
        return self._cached(("stoch_k", length, smooth), _calc)

    def stoch_d(self, length: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> np.ndarray:
        return self._cached(("stoch_d", length, smooth_k, smooth_d),
                            lambda: _sma(self.stoch_k(length, smooth_k), smooth_d))

    # ── ADX / DMI ──
    def adx(self, length: int = 14) -> np.ndarray:
        return self._cached(("adx", length), lambda: _adx(self.high, self.low, self.close, length))

    def di_plus(self, length: int = 14) -> np.ndarray:
        return self._cached(("di_plus", length),
                            lambda: _dmi(self.high, self.low, self.close, length)[0])

    def di_minus(self, length: int = 14) -> np.ndarray:
        return self._cached(("di_minus", length),
                            lambda: _dmi(self.high, self.low, self.close, length)[1])

    # ── CCI ──
    def cci(self, length: int = 20) -> np.ndarray:
        def _calc():
            tp = (self.high + self.low + self.close) / 3
            tp_sma = _sma(tp, length)
            # Mean deviation
            md = np.full_like(tp, np.nan)
            for i in range(length - 1, len(tp)):
                md[i] = np.mean(np.abs(tp[i - length + 1:i + 1] - tp_sma[i]))
            return np.where(md > 0, (tp - tp_sma) / (0.015 * md), 0)
        return self._cached(("cci", length), _calc)

    # ── Williams %R ──
    def willr(self, length: int = 14) -> np.ndarray:
        def _calc():
            h = _highest(self.high, length)
            l = _lowest(self.low, length)
            return np.where((h - l) > 0, (h - self.close) / (h - l) * -100, -50)
        return self._cached(("willr", length), _calc)

    # ── MFI (Money Flow Index) ──
    def mfi(self, length: int = 14) -> np.ndarray:
        def _calc():
            tp = (self.high + self.low + self.close) / 3
            mf = tp * self.volume
            n = len(tp)
            out = np.full(n, np.nan)
            for i in range(length, n):
                pos = sum(mf[j] for j in range(i - length + 1, i + 1) if tp[j] > tp[j - 1])
                neg = sum(mf[j] for j in range(i - length + 1, i + 1) if tp[j] < tp[j - 1])
                out[i] = 100 - 100 / (1 + pos / neg) if neg > 0 else 100
            return out
        return self._cached(("mfi", length), _calc)

    # ── OBV (On Balance Volume) ──
    def obv(self) -> np.ndarray:
        def _calc():
            out = np.zeros(self.n)
            for i in range(1, self.n):
                if self.close[i] > self.close[i - 1]:
                    out[i] = out[i - 1] + self.volume[i]
                elif self.close[i] < self.close[i - 1]:
                    out[i] = out[i - 1] - self.volume[i]
                else:
                    out[i] = out[i - 1]
            return out
        return self._cached(("obv",), _calc)

    # ── VWAP (cumulative) ──
    def vwap(self) -> np.ndarray:
        def _calc():
            tp = (self.high + self.low + self.close) / 3
            cum_tpv = np.cumsum(tp * self.volume)
            cum_vol = np.cumsum(self.volume)
            return np.where(cum_vol > 0, cum_tpv / cum_vol, np.nan)
        return self._cached(("vwap",), _calc)

    # ── Keltner Channels ──
    def keltner_upper(self, ema_len: int = 20, atr_len: int = 20, mult: float = 2.0) -> np.ndarray:
        return self._cached(("keltner_upper", ema_len, atr_len, mult),
                            lambda: self.ema(ema_len) + mult * self.atr(atr_len))

    def keltner_lower(self, ema_len: int = 20, atr_len: int = 20, mult: float = 2.0) -> np.ndarray:
        return self._cached(("keltner_lower", ema_len, atr_len, mult),
                            lambda: self.ema(ema_len) - mult * self.atr(atr_len))

    # ── Donchian Channels ──
    def donchian_upper(self, length: int = 20) -> np.ndarray:
        return self.highest(length)

    def donchian_lower(self, length: int = 20) -> np.ndarray:
        return self.lowest(length)

    def donchian_mid(self, length: int = 20) -> np.ndarray:
        return self._cached(("donchian_mid", length),
                            lambda: (self.highest(length) + self.lowest(length)) / 2)

    # ── Rate of Change ──
    def roc(self, length: int = 10) -> np.ndarray:
        return self.pct_change(length)

    # ── Momentum ──
    def mom(self, length: int = 10) -> np.ndarray:
        def _calc():
            out = np.full(self.n, np.nan)
            for i in range(length, self.n):
                out[i] = self.close[i] - self.close[i - length]
            return out
        return self._cached(("mom", length), _calc)

    # ── External series indicators (VIX, XLK, Treasury, Fed Funds, SGOV) ──
    def vix_ema(self, length: int) -> np.ndarray | None:
        if self.vix is None:
            return None
        return self._cached(("vix_ema", length), lambda: _ema(self.vix, length))

    def vix_sma(self, length: int) -> np.ndarray | None:
        if self.vix is None:
            return None
        return self._cached(("vix_sma", length), lambda: _sma(self.vix, length))

    def xlk_ema(self, length: int) -> np.ndarray | None:
        if self.xlk_close is None:
            return None
        return self._cached(("xlk_ema", length), lambda: _ema(self.xlk_close, length))

    def sgov_roc(self, length: int) -> np.ndarray | None:
        if self.sgov_close is None:
            return None
        return self._cached(("sgov_roc", length), lambda: _pct_change(self.sgov_close, length))

    # ── True Range ──
    def tr(self) -> np.ndarray:
        def _calc():
            out = np.zeros(self.n)
            out[0] = self.high[0] - self.low[0]
            for i in range(1, self.n):
                out[i] = max(self.high[i] - self.low[i],
                             abs(self.high[i] - self.close[i - 1]),
                             abs(self.low[i] - self.close[i - 1]))
            return out
        return self._cached(("tr",), _calc)

    # ── Parabolic SAR (simplified) ──
    def psar(self, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> np.ndarray:
        def _calc():
            n = self.n
            psar = np.full(n, np.nan)
            bull = True
            af = af_start
            ep = self.low[0]
            psar[0] = self.high[0]
            for i in range(1, n):
                if bull:
                    psar[i] = psar[i-1] + af * (ep - psar[i-1])
                    psar[i] = min(psar[i], self.low[i-1], self.low[max(0, i-2)])
                    if self.low[i] < psar[i]:
                        bull = False
                        psar[i] = ep
                        ep = self.low[i]
                        af = af_start
                    else:
                        if self.high[i] > ep:
                            ep = self.high[i]
                            af = min(af + af_step, af_max)
                else:
                    psar[i] = psar[i-1] + af * (ep - psar[i-1])
                    psar[i] = max(psar[i], self.high[i-1], self.high[max(0, i-2)])
                    if self.high[i] > psar[i]:
                        bull = True
                        psar[i] = ep
                        ep = self.high[i]
                        af = af_start
                    else:
                        if self.low[i] < ep:
                            ep = self.low[i]
                            af = min(af + af_step, af_max)
            return psar
        return self._cached(("psar", af_start, af_step, af_max), _calc)

    # ── Ichimoku components ──
    def ichimoku_tenkan(self, length: int = 9) -> np.ndarray:
        return self._cached(("ichi_tenkan", length),
                            lambda: (_highest(self.high, length) + _lowest(self.low, length)) / 2)

    def ichimoku_kijun(self, length: int = 26) -> np.ndarray:
        return self._cached(("ichi_kijun", length),
                            lambda: (_highest(self.high, length) + _lowest(self.low, length)) / 2)

    # ── Pivot Points ──
    def pivot(self) -> np.ndarray:
        return self._cached(("pivot",),
                            lambda: (self.high + self.low + self.close) / 3)

    # ── EMA on any series (not just close) ──
    def ema_of(self, key: str, series: np.ndarray, length: int) -> np.ndarray:
        return self._cached(("ema_of", key, length), lambda: _ema(series, length))

    # ── SMA on any series ──
    def sma_of(self, key: str, series: np.ndarray, length: int) -> np.ndarray:
        return self._cached(("sma_of", key, length), lambda: _sma(series, length))

    # ── Daily returns ──
    def daily_returns(self) -> np.ndarray:
        def _calc():
            out = np.zeros(self.n)
            for i in range(1, self.n):
                out[i] = (self.close[i] / self.close[i - 1] - 1) if self.close[i - 1] > 0 else 0
            return out
        return self._cached(("daily_returns",), _calc)

    # ── Realized volatility ──
    def realized_vol(self, length: int = 20) -> np.ndarray:
        return self._cached(("rvol", length), lambda: _stddev(self.daily_returns(), length))

    # ── Crossover/crossunder helpers ──
    def crossover(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """True on bars where a crosses above b."""
        out = np.zeros(len(a), dtype=bool)
        for i in range(1, len(a)):
            if not np.isnan(a[i]) and not np.isnan(b[i]) and not np.isnan(a[i-1]) and not np.isnan(b[i-1]):
                out[i] = a[i-1] <= b[i-1] and a[i] > b[i]
        return out

    def crossunder(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """True on bars where a crosses below b."""
        out = np.zeros(len(a), dtype=bool)
        for i in range(1, len(a)):
            if not np.isnan(a[i]) and not np.isnan(b[i]) and not np.isnan(a[i-1]) and not np.isnan(b[i-1]):
                out[i] = a[i-1] >= b[i-1] and a[i] < b[i]
        return out

    # ── VIX indicators ──

    def vix_close(self) -> np.ndarray:
        """Raw VIX close. Returns zeros if VIX data not available."""
        return self.vix if self.vix is not None else np.zeros(self.n)

    def vix_ema(self, length: int) -> np.ndarray:
        return self._cached(("vix_ema", length), lambda: _ema(self.vix_close(), length))

    def vix_sma(self, length: int) -> np.ndarray:
        return self._cached(("vix_sma", length), lambda: _sma(self.vix_close(), length))

    def vix_percentile(self, length: int) -> np.ndarray:
        """Rolling percentile rank of current VIX within last N bars (0-100)."""
        def _calc():
            vix = self.vix_close()
            out = np.full(self.n, np.nan)
            for i in range(length - 1, self.n):
                window = vix[i - length + 1:i + 1]
                out[i] = np.sum(window <= vix[i]) / length * 100
            return out
        return self._cached(("vix_pctl", length), _calc)


# ─────────────────────────────────────────────────────────────────────────────
# ADX/DMI helper (needed by Indicators)
# ─────────────────────────────────────────────────────────────────────────────

def _adx(hi, lo, cl, period):
    di_p, di_m = _dmi(hi, lo, cl, period)
    den = di_p + di_m
    dx = np.full_like(den, np.nan, dtype=np.float64)
    np.divide(100.0 * np.abs(di_p - di_m), den, out=dx, where=den > 0)
    return _rma(np.nan_to_num(dx, nan=0.0), period)

def _dmi(hi, lo, cl, period):
    n = len(cl)
    dm_plus = np.zeros(n)
    dm_minus = np.zeros(n)
    tr_arr = np.zeros(n)
    tr_arr[0] = hi[0] - lo[0]
    for i in range(1, n):
        h_diff = hi[i] - hi[i-1]
        l_diff = lo[i-1] - lo[i]
        tr_arr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i-1]), abs(lo[i] - cl[i-1]))
        dm_plus[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0
        dm_minus[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0
    sm_tr = _rma(tr_arr, period)
    sm_dp = _rma(dm_plus, period)
    sm_dm = _rma(dm_minus, period)
    di_p = np.where(sm_tr > 0, 100.0 * sm_dp / sm_tr, np.nan)
    di_m = np.where(sm_tr > 0, 100.0 * sm_dm / sm_tr, np.nan)
    return di_p, di_m


# ─────────────────────────────────────────────────────────────────────────────
# Backtest engine — strategy-agnostic
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_bar: int
    entry_date: str
    entry_price: float
    exit_bar: int = -1
    exit_date: str = ""
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl_pct: float = 0.0
    bars_held: int = 0


@dataclass
class BacktestResult:
    trades: list
    equity_curve: np.ndarray
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    mar_ratio: float = 0.0
    exposure_pct: float = 0.0
    num_trades: int = 0
    trades_per_year: float = 0.0
    avg_bars_held: float = 0.0
    win_rate_pct: float = 0.0
    # Charter primary metric: share-count multiplier vs B&H.
    # Math identity: terminal strategy equity / terminal B&H equity equals
    # strategy_shares_equiv / bah_shares when equity is marked-to-market to
    # TECL shares — i.e., the share-count multiplier itself.
    share_multiple: float = 0.0
    # Era-sliced share multiples (2026-04-21). Computed from the equity curve
    # starting at each era boundary. Used by the weighted-era fitness function
    # (search/fitness.py) to prevent optimization from being dominated by the
    # synthetic 1993-2008 dotcom-crash sidestep.
    #   real_share_multiple    — share multiplier on post-2008-12-17 data only
    #   modern_share_multiple  — share multiplier on post-2015-01-01 data only
    real_share_multiple: float = 0.0
    modern_share_multiple: float = 0.0
    bah_start_date: str = ""
    exit_reasons: dict = field(default_factory=dict)
    strategy_name: str = ""
    regime_score: object = None  # RegimeScore (from backtest_engine), attached by evolve.py / run_montauk_821
    params: dict = field(default_factory=dict)  # strategy params, attached by evolve.py / run_montauk_821
    # ── Fields populated by `run_montauk_821` (canonical 8.2.1 path) ──
    # `backtest()` (the entries/exits-array path) leaves these at their defaults.
    false_signal_rate_pct: float = 0.0   # % of trades held < 10 bars (noise trades)
    worst_10_bar_loss_pct: float = 0.0
    bah_return_pct: float = 0.0          # passive return over the same window
    bah_final_equity: float = 0.0        # $initial_capital just holding the asset
    # Provenance: how many trades opened on synthetic vs real bars.
    # Populated when the input df has the `is_synthetic` column (see data/manifest.json).
    # If the column is absent (e.g. raw OHLCV with no provenance), both stay at 0.
    synthetic_trades: int = 0
    real_trades: int = 0

    @property
    def vs_bah_multiple(self) -> float:
        """Deprecated compatibility alias for pre-Phase-7 callers."""
        warnings.warn(
            "BacktestResult.vs_bah_multiple is deprecated; use share_multiple.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.share_multiple

    def summary_str(self) -> str:
        lines = [
            f"Total Return:    {self.total_return_pct:>8.1f}%",
            f"CAGR:            {self.cagr_pct:>8.2f}%",
            f"Max Drawdown:    {self.max_drawdown_pct:>8.1f}%",
            f"MAR Ratio:       {self.mar_ratio:>8.2f}",
            f"Exposure:        {self.exposure_pct:>8.1f}%",
            f"Trades:          {self.num_trades:>8d}",
            f"Trades/Year:     {self.trades_per_year:>8.1f}",
            f"Avg Bars Held:   {self.avg_bars_held:>8.1f}",
            f"Win Rate:        {self.win_rate_pct:>8.1f}%",
            f"False Signals:   {self.false_signal_rate_pct:>8.1f}%",
            f"Worst 10-Bar:    {self.worst_10_bar_loss_pct:>8.1f}%",
            f"Exit Reasons:    {self.exit_reasons}",
        ]
        if self.bah_start_date and self.bah_final_equity:
            sign = "+" if self.share_multiple >= 1.0 else ""
            alpha = (self.share_multiple - 1.0) * 100
            initial = self.params.get("initial_capital", 1000.0) if self.params else 1000.0
            lines.append(
                f"vs Buy & Hold:   {sign}{alpha:.1f}%  "
                f"(Strategy ${initial * (1 + self.total_return_pct/100):.0f}  "
                f"B&H ${self.bah_final_equity:.0f}  from {self.bah_start_date})"
            )
        if self.synthetic_trades or self.real_trades:
            lines.append(
                f"Trade provenance: synthetic={self.synthetic_trades}  real={self.real_trades}"
            )
        if self.regime_score:
            lines.append(self.regime_score.summary_str())
        return "\n".join(lines)


REAL_DATA_START = pd.Timestamp("2008-12-17")  # first real TECL trading day
MODERN_ERA_START = pd.Timestamp("2015-01-01")  # modern-era cutoff (post-GFC/QE normalization)


def _era_share_multiple(
    dates: np.ndarray,
    equity_curve: np.ndarray,
    close: np.ndarray,
    era_start: pd.Timestamp,
) -> float:
    """Share-count multiplier computed from `era_start` forward.

    Slices equity + close at the first bar with date >= era_start, then:
      era_share_multiple = (equity[-1] / equity[slice]) / (close[-1] / close[slice])

    Interpretation identical to the full-history share_multiple — strategy shares
    accumulated since the era boundary vs B&H shares over the same window.

    Returns 0.0 if the era start is beyond the data or the slice can't be formed
    (caller treats 0.0 as "not available").
    """
    ds = pd.to_datetime(dates)
    mask = ds >= era_start
    if not mask.any():
        return 0.0
    idx = int(np.argmax(mask.values if hasattr(mask, "values") else mask))
    if idx >= len(equity_curve) - 1:
        return 0.0
    eq0 = float(equity_curve[idx])
    eq1 = float(equity_curve[-1])
    p0 = float(close[idx])
    p1 = float(close[-1])
    if eq0 <= 0 or p0 <= 0:
        return 0.0
    strat_growth = eq1 / eq0
    bah_growth = p1 / p0
    if bah_growth <= 0:
        return 0.0
    return float(strat_growth / bah_growth)


def _count_synthetic_real_trades(df: pd.DataFrame, trades: list) -> tuple[int, int]:
    """Count trades that opened on synthetic vs real bars.

    Uses the `is_synthetic` provenance column added by `data_rebuild_synthetic.py`
    (see data/manifest.json). If the column is missing — e.g. raw OHLCV with no
    provenance, or a downstream caller passing a stripped df — returns (0, 0)
    so callers can detect the absence and fall back to "unknown".
    """
    if "is_synthetic" not in df.columns or not trades:
        return (0, 0)
    syn_col = df["is_synthetic"].values
    n_syn = 0
    n_real = 0
    for t in trades:
        bar = t.entry_bar
        if 0 <= bar < len(syn_col):
            if bool(syn_col[bar]):
                n_syn += 1
            else:
                n_real += 1
    return (n_syn, n_real)


def backtest(df: pd.DataFrame,
             entries: np.ndarray,
             exits: np.ndarray,
             exit_labels: np.ndarray | None = None,
             cooldown_bars: int = 0,
             initial_capital: float = 1000.0,
             slippage_pct: float = 0.05,
             strategy_name: str = "") -> BacktestResult:
    """
    Run a backtest given boolean entry/exit signal arrays.

    Parameters
    ----------
    df : OHLCV DataFrame
    entries : bool array, True on bars where entry signal fires
    exits : bool array, True on bars where exit signal fires
    exit_labels : string array, label for each exit signal (optional)
    cooldown_bars : bars to wait after exit before re-entering
    initial_capital : starting equity
    slippage_pct : simulated slippage per trade as % of price (0.05 = 5 bps each way).
                   Research: zero-slippage backtests inflate results by 50-100+ bps/yr.
                   TECL bid-ask spread is typically 2-5 bps; we add execution impact.
    strategy_name : label for this strategy

    Returns BacktestResult.
    """
    dates = df["date"].values
    cl = df["close"].values.astype(np.float64)
    n = len(cl)

    if exit_labels is None:
        exit_labels = np.array(["Exit"] * n)

    equity = initial_capital
    equity_curve = np.zeros(n)
    position = 0
    shares = 0.0
    entry_price = 0.0
    last_sell_bar = -9999
    trades = []
    current_trade = None
    bars_in = np.zeros(n)

    for i in range(n):
        equity_curve[i] = equity + (shares * (cl[i] - entry_price) if position > 0 else 0)

        # Exit
        if position > 0 and exits[i]:
            exit_price = cl[i] * (1 - slippage_pct / 100)  # slippage: sell slightly lower
            pnl = shares * (exit_price - entry_price)
            equity += pnl
            position = 0
            last_sell_bar = i
            if current_trade:
                current_trade.exit_bar = i
                current_trade.exit_date = str(dates[i])[:10]
                current_trade.exit_price = exit_price
                current_trade.exit_reason = str(exit_labels[i])
                current_trade.pnl_pct = (exit_price / entry_price - 1) * 100
                current_trade.bars_held = i - current_trade.entry_bar
                trades.append(current_trade)
                current_trade = None
            shares = 0.0
            entry_price = 0.0

        # Entry
        if position == 0 and entries[i]:
            if (i - last_sell_bar) > cooldown_bars:
                entry_price = cl[i] * (1 + slippage_pct / 100)  # slippage: buy slightly higher
                shares = equity / entry_price
                position = 1
                current_trade = Trade(entry_bar=i, entry_date=str(dates[i])[:10],
                                      entry_price=entry_price)

        if position > 0:
            bars_in[i] = 1
        equity_curve[i] = equity + (shares * (cl[i] - entry_price) if position > 0 else 0)

    # Close open position
    if position > 0 and current_trade:
        equity += shares * (cl[-1] - entry_price)
        current_trade.exit_bar = n - 1
        current_trade.exit_date = str(dates[-1])[:10]
        current_trade.exit_price = cl[-1]
        current_trade.exit_reason = "End of Data"
        current_trade.pnl_pct = (cl[-1] / entry_price - 1) * 100
        current_trade.bars_held = (n - 1) - current_trade.entry_bar
        trades.append(current_trade)
        equity_curve[-1] = equity

    # ── Metrics ──
    first_date = pd.Timestamp(dates[0])
    last_date = pd.Timestamp(dates[-1])
    years = (last_date - first_date).days / 365.25

    total_return = (equity_curve[-1] / initial_capital - 1) * 100
    cagr = ((equity_curve[-1] / initial_capital) ** (1 / years) - 1) * 100 if years > 0 and equity_curve[-1] > 0 else 0
    peak = np.maximum.accumulate(equity_curve)
    dd = np.where(peak > 0, (equity_curve - peak) / peak * 100, 0)
    max_dd = abs(dd.min())
    mar = cagr / max_dd if max_dd > 0 else 0

    trading_bars = n
    exposure = np.sum(bars_in) / trading_bars * 100 if trading_bars > 0 else 0
    tpy = len(trades) / years if years > 0 else 0
    avg_held = np.mean([t.bars_held for t in trades]) if trades else 0
    wins = sum(1 for t in trades if t.pnl_pct > 0)
    win_rate = wins / len(trades) * 100 if trades else 0

    # Share-count multiplier vs buy-and-hold.
    bah_start = cl[0]
    bah_end = cl[-1]
    bah_equity = initial_capital * (bah_end / bah_start) if bah_start > 0 else initial_capital
    share_multiple = equity_curve[-1] / bah_equity if bah_equity > 0 else 1.0

    # Era-sliced share multipliers (2026-04-21) — used by weighted-era fitness.
    real_sm = _era_share_multiple(dates, equity_curve, cl, REAL_DATA_START)
    modern_sm = _era_share_multiple(dates, equity_curve, cl, MODERN_ERA_START)

    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    n_syn, n_real = _count_synthetic_real_trades(df, trades)

    return BacktestResult(
        trades=trades, equity_curve=equity_curve,
        total_return_pct=round(total_return, 2),
        cagr_pct=round(cagr, 2),
        max_drawdown_pct=round(max_dd, 1),
        mar_ratio=round(mar, 3),
        exposure_pct=round(exposure, 1),
        num_trades=len(trades),
        trades_per_year=round(tpy, 1),
        avg_bars_held=round(avg_held, 0),
        win_rate_pct=round(win_rate, 1),
        share_multiple=round(share_multiple, 4),
        real_share_multiple=round(real_sm, 4),
        modern_share_multiple=round(modern_sm, 4),
        bah_start_date=str(dates[0])[:10],
        exit_reasons=exit_reasons,
        strategy_name=strategy_name,
        synthetic_trades=n_syn,
        real_trades=n_real,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Canonical Montauk 8.2.1 execution path (Phase 7 consolidation)
#
# Ported from the retired `backtest_engine.run_backtest()` monolithic loop.
# Uses this module's bug-fixed `_ema` / `_tema` / `_atr` / `_adx` so the chained
# TEMA inside `enable_slope_filter` / `enable_below_filter` actually computes
# (the old `backtest_engine.tema` returned all-NaN due to an SMA-seed-meets-NaN
# bug — see the Phase 7 note in `Montauk 2.0 - Master Plan.md`).
#
# The 8.2.1 default param set keeps the TEMA filters OFF, so the regression
# ledger (`tests/golden_trades_821.json`) is untouched by this port.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class StrategyParams:
    """Canonical Montauk 8.2.1 strategy parameters.

    Defaults match the production 8.2.1 strategy: EMA(15)/EMA(30) cross with
    a 70-bar trend filter, ATR(40)×3 stop, Quick-EMA(15) momentum exit, and
    a 2-bar EMA-cross sell-confirmation window.

    All optional filter groups (TEMA gates, ATR-ratio, ADX, ROC, bear-guard,
    asymmetric ATR, volume-spike) default to OFF — turn them on per-config.
    """
    # Group 1 — EMAs
    short_ema_len: int = 15
    med_ema_len: int = 30
    long_ema_len: int = 500

    # Group 2 — Trend Filter
    enable_trend: bool = True
    trend_ema_len: int = 70
    slope_lookback: int = 10
    min_trend_slope: float = 0.0

    # Group 3 — TEMA Filters (entry gates)
    enable_slope_filter: bool = False
    enable_below_filter: bool = False
    triple_ema_len: int = 200
    triple_slope_lookback: int = 1

    # Group 4 — Sideways Filter
    enable_sideways_filter: bool = True
    range_len: int = 60
    max_range_pct: float = 30.0

    # Group 5 — Sell Confirmation
    enable_sell_confirm: bool = True
    sell_confirm_bars: int = 2
    sell_buffer_pct: float = 0.2

    # Group 6 — Sell Cooldown
    enable_sell_cooldown: bool = True
    sell_cooldown_bars: int = 2

    # Group 7 — ATR Exit
    enable_atr_exit: bool = True
    atr_period: int = 40
    atr_multiplier: float = 3.0

    # Group 8 — Quick EMA Exit
    enable_quick_exit: bool = True
    quick_ema_len: int = 15
    quick_lookback_bars: int = 5
    quick_delta_pct_thresh: float = -8.2

    # Group 10 — Trailing Peak Stop (default OFF)
    enable_trail_stop: bool = False
    trail_drop_pct: float = 25.0

    # Group 11 — TEMA Slope Exit (default OFF)
    enable_tema_exit: bool = False
    tema_exit_lookback: int = 5

    # Group 12 — ATR Ratio Volatility Filter (default OFF)
    enable_atr_ratio_filter: bool = False
    atr_ratio_len: int = 100
    atr_ratio_max: float = 2.0

    # Group 13 — ADX Trend Strength Filter (default OFF)
    enable_adx_filter: bool = False
    adx_len: int = 14
    adx_min: float = 20.0

    # Group 14 — ROC Momentum Entry Filter (default OFF)
    enable_roc_filter: bool = False
    roc_len: int = 20

    # Group 15 — Bear Depth Guard (default OFF)
    # Block re-entry if equity is >X% below its recent peak
    enable_bear_guard: bool = False
    bear_guard_pct: float = 20.0
    bear_guard_lookback: int = 60

    # Group 16 — Asymmetric ATR Exit (default OFF)
    # In high-vol environments, tighten exit multiplier
    enable_asymmetric_exit: bool = False
    asym_atr_ratio_threshold: float = 1.5  # trigger when atr_ratio > this
    asym_exit_multiplier: float = 1.5       # tighter multiplier during high-vol

    # Group 17 — Volume Spike Exit (default OFF)
    enable_vol_exit: bool = False
    vol_spike_len: int = 20    # EMA length for average volume
    vol_spike_mult: float = 2.5  # exit if volume > mult × avg AND price down

    # Capital
    initial_capital: float = 1000.0
    # Per-fill slippage, applied on BOTH entry and exit.
    # 0.05 = 5 bps per fill (Phase 1c unification with `backtest()`).
    slippage_pct: float = 0.05
    # Deprecated: legacy `commission_pct × equity × 2` model was non-standard.
    # Execution costs are modeled entirely via `slippage_pct`. Retained only
    # for back-compat with older StrategyParams dicts; has no effect on fills.
    commission_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyParams":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


def run_montauk_821(df: pd.DataFrame, params: StrategyParams | None = None,
                    score_regimes: bool = True) -> BacktestResult:
    """Run a full backtest of the canonical Montauk 8.2.1 strategy on OHLCV data.

    This is the canonical execution path the regression ledger and the
    integrity gate run against. It is a faithful bar-by-bar replica of the
    8.2.1 logic, with `process_orders_on_close=True` semantics (signals and
    fills happen on the same bar's close).

    Parameters
    ----------
    df : DataFrame with columns: date, open, high, low, close, volume
    params : StrategyParams (uses canonical 8.2.1 defaults if None)
    score_regimes : if True, compute regime capture score (adds ~5ms)

    Returns
    -------
    BacktestResult with trades, equity curve, summary metrics, regime_score,
    and the `params` dict attached so reports can introspect the config.
    """
    # Local import — `backtest_engine` is a sibling module that retains only
    # the regime-scoring helpers post-Phase-7. Importing at call time avoids
    # a circular import if anything else in this module ever needs to be
    # imported by `backtest_engine`.
    from engine.regime_helpers import score_regime_capture

    if params is None:
        params = StrategyParams()

    dates = df["date"].values
    op = df["open"].values.astype(np.float64)  # noqa: F841 — kept for symmetry / future use
    hi = df["high"].values.astype(np.float64)
    lo = df["low"].values.astype(np.float64)
    cl = df["close"].values.astype(np.float64)
    vol = df["volume"].values.astype(np.float64) if "volume" in df.columns else np.ones(len(cl))
    n = len(cl)

    # ── Pre-compute all indicators (using strategy_engine's NaN-safe variants) ──
    ema_short = _ema(cl, params.short_ema_len)
    ema_med = _ema(cl, params.med_ema_len)
    ema_long = _ema(cl, params.long_ema_len)
    ema_trend = _ema(cl, params.trend_ema_len)
    quick_ema_arr = _ema(cl, params.quick_ema_len)
    tema_vals = _tema(cl, params.triple_ema_len)
    atr_vals = _atr(hi, lo, cl, params.atr_period)
    atr_ema_vals = _ema(atr_vals, params.atr_ratio_len)  # long-term ATR average
    adx_vals = _adx(hi, lo, cl, params.adx_len)
    vol_ema_vals = _ema(vol, params.vol_spike_len)
    high_vals = _highest(hi, params.range_len)
    low_vals = _lowest(lo, params.range_len)
    sma_vals = _sma(cl, params.range_len)

    # ── Bar-by-bar simulation ──
    equity = params.initial_capital
    equity_curve = np.zeros(n)
    position_size = 0  # 0 = flat, 1 = long
    shares = 0.0
    entry_price = 0.0
    last_sell_bar = -9999
    peak_since_entry = np.nan
    trades: list[Trade] = []
    current_trade: Optional[Trade] = None
    bars_in_position = np.zeros(n)

    # Minimum warmup: only the indicators required for the basic entry signal.
    # Optional filters guard themselves with np.isnan() checks, so they don't
    # need to hold back the whole engine. Matches the historical baseline.
    warmup = max(params.short_ema_len, params.med_ema_len,
                 params.trend_ema_len if params.enable_trend else 0,
                 params.atr_period if params.enable_atr_exit else 0) + 5

    for i in range(n):
        equity_curve[i] = equity + (shares * cl[i] - shares * entry_price if position_size > 0 else 0)

        if i < warmup:
            continue

        # Check for NaN indicators
        if np.isnan(ema_short[i]) or np.isnan(ema_med[i]) or np.isnan(ema_long[i]):
            continue

        # ── Trend filter ──
        slope_lb = params.slope_lookback
        if i >= slope_lb and not np.isnan(ema_trend[i]) and not np.isnan(ema_trend[i - slope_lb]):
            trend_slope = (ema_trend[i] - ema_trend[i - slope_lb]) / slope_lb
        else:
            trend_slope = 0.0
        trend_ok = (not params.enable_trend) or (trend_slope > params.min_trend_slope)

        # ── TEMA entry filters ──
        t_lb = params.triple_slope_lookback
        if i >= t_lb and not np.isnan(tema_vals[i]) and not np.isnan(tema_vals[i - t_lb]):
            tema_slope = (tema_vals[i] - tema_vals[i - t_lb]) / t_lb
        else:
            tema_slope = 0.0
        slope_ok = (not params.enable_slope_filter) or (tema_slope > 0)
        above_ok = (not params.enable_below_filter) or (cl[i] > tema_vals[i] if not np.isnan(tema_vals[i]) else True)

        # ── Sideways filter ──
        if not np.isnan(high_vals[i]) and not np.isnan(low_vals[i]) and not np.isnan(sma_vals[i]) and sma_vals[i] > 0:
            rng = high_vals[i] - low_vals[i]
            rng_pct = rng / sma_vals[i] * 100
        else:
            rng_pct = 100.0  # Assume not sideways if data unavailable
        sideways = rng_pct < params.max_range_pct
        sideways_ok = (not params.enable_sideways_filter) or (not sideways)

        # ── ATR ratio volatility filter ──
        if (params.enable_atr_ratio_filter and
                not np.isnan(atr_vals[i]) and not np.isnan(atr_ema_vals[i]) and
                atr_ema_vals[i] > 0):
            atr_ratio_ok = (atr_vals[i] / atr_ema_vals[i]) <= params.atr_ratio_max
        else:
            atr_ratio_ok = True

        # ── ADX trend strength filter ──
        if params.enable_adx_filter and not np.isnan(adx_vals[i]):
            adx_ok = adx_vals[i] >= params.adx_min
        else:
            adx_ok = True

        # ── ROC momentum entry filter ──
        if params.enable_roc_filter and i >= params.roc_len and cl[i - params.roc_len] > 0:
            roc_ok = cl[i] > cl[i - params.roc_len]
        else:
            roc_ok = True

        # ── Bear depth guard ──
        current_equity = equity + (shares * (cl[i] - entry_price) if position_size > 0 else 0)
        equity_curve[i] = current_equity  # update for rolling peak
        if params.enable_bear_guard:
            lookback_start = max(0, i - params.bear_guard_lookback)
            rolling_peak = np.max(equity_curve[lookback_start:i + 1])
            bear_guard_ok = rolling_peak <= 0 or current_equity >= rolling_peak * (1 - params.bear_guard_pct / 100)
        else:
            bear_guard_ok = True

        # ── Entry conditions ──
        buy_zone = ema_short[i] > ema_med[i]
        buy_ok = buy_zone and trend_ok and slope_ok and above_ok and sideways_ok and atr_ratio_ok and adx_ok and roc_ok and bear_guard_ok

        # ── Exit 1: EMA Cross (8.2.1 logic: barssince(crossunder) < confirmBars) ──
        recent_cross = False
        if params.enable_sell_confirm:
            for j in range(params.sell_confirm_bars):
                idx = i - j
                idx_prev = idx - 1
                if idx_prev < 0:
                    break
                if (not np.isnan(ema_short[idx_prev]) and not np.isnan(ema_long[idx_prev]) and
                        not np.isnan(ema_short[idx]) and not np.isnan(ema_long[idx])):
                    if ema_short[idx_prev] >= ema_long[idx_prev] and ema_short[idx] < ema_long[idx]:
                        recent_cross = True
                        break
        else:
            # No confirmation window: require exact cross bar
            if i >= 1 and not np.isnan(ema_short[i-1]) and not np.isnan(ema_long[i-1]):
                recent_cross = (ema_short[i-1] >= ema_long[i-1]) and (ema_short[i] < ema_long[i])

        buffer_ok = ema_short[i] < ema_long[i] * (1 - params.sell_buffer_pct / 100)
        # Match Pine's allBelow: ta.lowest(emaShort < emaLong ? 1 : 0, sellConfirmBars) == 1
        all_below = True
        for j in range(params.sell_confirm_bars):
            idx = i - j
            if idx < 0 or np.isnan(ema_short[idx]) or np.isnan(ema_long[idx]):
                all_below = False
                break
            if ema_short[idx] >= ema_long[idx]:
                all_below = False
                break
        is_cross_exit = recent_cross and buffer_ok and all_below

        # ── Exit 2: ATR Shock ──
        is_atr_exit = False
        if params.enable_atr_exit and i >= 1 and not np.isnan(atr_vals[i]):
            eff_multiplier = params.atr_multiplier
            if (params.enable_asymmetric_exit and
                    not np.isnan(atr_ema_vals[i]) and atr_ema_vals[i] > 0 and
                    atr_vals[i] / atr_ema_vals[i] > params.asym_atr_ratio_threshold):
                eff_multiplier = params.asym_exit_multiplier
            is_atr_exit = cl[i] < cl[i - 1] - atr_vals[i] * eff_multiplier

        # ── Exit 3: Quick EMA ──
        is_quick_exit = False
        if params.enable_quick_exit and i >= params.quick_lookback_bars:
            qe_now = quick_ema_arr[i]
            qe_past = quick_ema_arr[i - params.quick_lookback_bars]
            if not np.isnan(qe_now) and not np.isnan(qe_past) and qe_past != 0:
                quick_delta_pct = 100.0 * (qe_now - qe_past) / qe_past
                is_quick_exit = quick_delta_pct <= params.quick_delta_pct_thresh

        # ── Exit 4: Trailing Peak Stop ──
        is_trail_exit = False
        if position_size > 0:
            if np.isnan(peak_since_entry):
                peak_since_entry = cl[i]
            else:
                peak_since_entry = max(peak_since_entry, cl[i])
            if params.enable_trail_stop and not np.isnan(peak_since_entry):
                is_trail_exit = cl[i] < peak_since_entry * (1 - params.trail_drop_pct / 100)

        # ── Exit 5: TEMA Slope Exit ──
        is_tema_exit = False
        if params.enable_tema_exit and position_size > 0:
            te_lb = params.tema_exit_lookback
            if i >= te_lb and not np.isnan(tema_vals[i]) and not np.isnan(tema_vals[i - te_lb]):
                tema_exit_slope = (tema_vals[i] - tema_vals[i - te_lb]) / te_lb
                is_tema_exit = tema_exit_slope < 0

        # ── Exit 6: Volume Spike Exit ──
        is_vol_exit = False
        if (params.enable_vol_exit and position_size > 0 and i >= 1 and
                not np.isnan(vol_ema_vals[i]) and vol_ema_vals[i] > 0):
            vol_spike = vol[i] > vol_ema_vals[i] * params.vol_spike_mult
            price_down = cl[i] < cl[i - 1]
            is_vol_exit = vol_spike and price_down

        # ── Unified exit (sideways suppresses exits) ──
        allow_exit = not (params.enable_sideways_filter and sideways)

        if position_size > 0 and allow_exit:
            exit_reason = ""
            if is_cross_exit:
                exit_reason = "EMA Cross"
            elif is_atr_exit:
                exit_reason = "ATR Exit"
            elif is_quick_exit:
                exit_reason = "Quick EMA"
            elif is_trail_exit:
                exit_reason = "Trail Stop"
            elif is_tema_exit:
                exit_reason = "TEMA Slope"
            elif is_vol_exit:
                exit_reason = "Vol Spike"

            if exit_reason:
                # process_orders_on_close=true: fill at this bar's close.
                # Slippage: selling fills slightly below close (per-fill model).
                exit_price = cl[i] * (1 - params.slippage_pct / 100)
                pnl = shares * (exit_price - entry_price)
                equity += pnl
                position_size = 0
                last_sell_bar = i
                peak_since_entry = np.nan
                shares = 0.0
                if current_trade:
                    current_trade.exit_bar = i
                    current_trade.exit_date = str(dates[i])[:10]
                    current_trade.exit_price = exit_price
                    current_trade.exit_reason = exit_reason
                    current_trade.pnl_pct = (exit_price / entry_price - 1) * 100
                    current_trade.bars_held = i - current_trade.entry_bar
                    trades.append(current_trade)
                    current_trade = None
                entry_price = 0.0

        # ── Entry with cooldown ──
        if position_size == 0:
            can_enter = True
            if params.enable_sell_cooldown:
                if (i - last_sell_bar) <= params.sell_cooldown_bars:
                    can_enter = False

            if buy_ok and can_enter:
                # process_orders_on_close=true: fill at this bar's close.
                # Slippage: buying fills slightly above close (per-fill model).
                entry_price = cl[i] * (1 + params.slippage_pct / 100)
                shares = equity / entry_price
                position_size = 1
                peak_since_entry = np.nan
                current_trade = Trade(
                    entry_bar=i,
                    entry_date=str(dates[i])[:10],
                    entry_price=entry_price,
                )

        if position_size > 0:
            bars_in_position[i] = 1

        equity_curve[i] = equity + (shares * (cl[i] - entry_price) if position_size > 0 else 0)

    # Close any open position at end
    if position_size > 0 and current_trade:
        exit_price = cl[-1]
        pnl = shares * (exit_price - entry_price)
        equity += pnl
        current_trade.exit_bar = n - 1
        current_trade.exit_date = str(dates[-1])[:10]
        current_trade.exit_price = exit_price
        current_trade.exit_reason = "End of Data"
        current_trade.pnl_pct = (exit_price / entry_price - 1) * 100
        current_trade.bars_held = (n - 1) - current_trade.entry_bar
        trades.append(current_trade)
        equity_curve[-1] = equity

    # ── Compute summary metrics ──
    trading_bars = n - warmup
    total_return_pct = (equity_curve[-1] / params.initial_capital - 1) * 100

    # CAGR — use actual date span, not truncated trading_bars
    first_date = pd.Timestamp(dates[0])
    last_date = pd.Timestamp(dates[-1])
    years = (last_date - first_date).days / 365.25
    if years > 0 and equity_curve[-1] > 0:
        cagr = (equity_curve[-1] / params.initial_capital) ** (1 / years) - 1
    else:
        cagr = 0.0

    # Max drawdown (post-warmup)
    peak = np.maximum.accumulate(equity_curve[warmup:])
    dd = (equity_curve[warmup:] - peak) / peak * 100
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0

    # MAR ratio
    mar = (cagr * 100) / max_dd if max_dd > 0 else 0.0

    # Exposure
    exposure = np.sum(bars_in_position[warmup:]) / trading_bars * 100 if trading_bars > 0 else 0.0

    # Trades per year
    trades_per_year = len(trades) / years if years > 0 else 0.0

    # Average bars held
    avg_held = float(np.mean([t.bars_held for t in trades])) if trades else 0.0

    # Win rate
    wins = sum(1 for t in trades if t.pnl_pct > 0)
    win_rate = wins / len(trades) * 100 if trades else 0.0

    # False signal rate (trades held < 10 bars — noise, not regime)
    false_signals = sum(1 for t in trades if t.bars_held < 10)
    false_signal_rate = false_signals / len(trades) * 100 if trades else 0.0

    # Worst 10-bar loss
    worst_10 = 0.0
    eq = equity_curve[warmup:]
    if len(eq) > 10:
        for i in range(10, len(eq)):
            change = (eq[i] / eq[i - 10] - 1) * 100 if eq[i - 10] > 0 else 0.0
            worst_10 = min(worst_10, change)

    # Exit reason breakdown
    exit_reasons: dict = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    # ── Regime scoring ──
    regime_score = None
    if score_regimes:
        regime_score = score_regime_capture(trades, cl, dates)

    # ── Buy-and-hold comparison (from start of data, matching the historical baseline) ──
    bah_return_pct = 0.0
    bah_final_equity = params.initial_capital
    share_multiple = 1.0
    bah_start_date = str(dates[0])[:10]
    bah_start_price = cl[0]
    bah_end_price = cl[-1]
    if bah_start_price > 0:
        bah_return_pct = (bah_end_price / bah_start_price - 1) * 100
        bah_final_equity = params.initial_capital * (bah_end_price / bah_start_price)
        if bah_final_equity > 0:
            share_multiple = equity_curve[-1] / bah_final_equity

    # Era-sliced share multipliers (2026-04-21)
    real_sm = _era_share_multiple(dates, equity_curve, cl, REAL_DATA_START)
    modern_sm = _era_share_multiple(dates, equity_curve, cl, MODERN_ERA_START)

    n_syn, n_real = _count_synthetic_real_trades(df, trades)

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        total_return_pct=total_return_pct,
        cagr_pct=cagr * 100,
        max_drawdown_pct=max_dd,
        mar_ratio=mar,
        exposure_pct=exposure,
        num_trades=len(trades),
        trades_per_year=trades_per_year,
        avg_bars_held=avg_held,
        win_rate_pct=win_rate,
        share_multiple=round(share_multiple, 3),
        real_share_multiple=round(real_sm, 4),
        modern_share_multiple=round(modern_sm, 4),
        bah_start_date=bah_start_date,
        exit_reasons=exit_reasons,
        strategy_name="montauk_821",
        regime_score=regime_score,
        params=params.to_dict(),
        false_signal_rate_pct=round(false_signal_rate, 1),
        worst_10_bar_loss_pct=worst_10,
        bah_return_pct=round(bah_return_pct, 2),
        bah_final_equity=round(bah_final_equity, 2),
        synthetic_trades=n_syn,
        real_trades=n_real,
    )
