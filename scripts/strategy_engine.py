#!/usr/bin/env python3
"""
Modular backtesting engine for Project Montauk.

Separates the WHAT (strategy logic) from the HOW (position management,
equity tracking, metrics). Any strategy that implements entry/exit signals
as numpy arrays can be tested.

Usage:
    from strategy_engine import backtest, Indicators, metrics_from_trades

    ind = Indicators(df)  # pre-compute all common indicators
    entries, exits, exit_labels = my_strategy(ind, params)
    result = backtest(df, entries, exits, exit_labels)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Indicator library — pre-computed, shared across all strategies
# ─────────────────────────────────────────────────────────────────────────────

def _ema(series: np.ndarray, length: int) -> np.ndarray:
    """Pine Script ta.ema() — recursive EMA with SMA seed."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    out[length - 1] = np.mean(series[:length])
    for i in range(length, len(series)):
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


# ─────────────────────────────────────────────────────────────────────────────
# ADX/DMI helper (needed by Indicators)
# ─────────────────────────────────────────────────────────────────────────────

def _adx(hi, lo, cl, period):
    di_p, di_m = _dmi(hi, lo, cl, period)
    dx = np.where((di_p + di_m) > 0, 100.0 * np.abs(di_p - di_m) / (di_p + di_m), np.nan)
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
    vs_bah_multiple: float = 0.0
    bah_start_date: str = ""
    exit_reasons: dict = field(default_factory=dict)
    strategy_name: str = ""
    regime_score: object = None  # RegimeScore from backtest_engine, attached by evolve.py
    params: dict = field(default_factory=dict)  # strategy params, attached by evolve.py


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

    # vs B&H
    bah_start = cl[0]
    bah_end = cl[-1]
    bah_equity = initial_capital * (bah_end / bah_start) if bah_start > 0 else initial_capital
    vs_bah = equity_curve[-1] / bah_equity if bah_equity > 0 else 1.0

    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

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
        vs_bah_multiple=round(vs_bah, 4),
        bah_start_date=str(dates[0])[:10],
        exit_reasons=exit_reasons,
        strategy_name=strategy_name,
    )
