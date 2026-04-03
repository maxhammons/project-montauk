from __future__ import annotations

"""
Python backtesting engine — faithful replica of Project Montauk 8.2.1.

Mirrors the Pine Script logic bar-by-bar:
  - EMA-based entry (short > med) with trend filter
  - Exit stack: EMA cross, ATR shock, Quick EMA, Trailing stop, TEMA slope
  - Cooldown, sideways filter, TEMA entry gates
  - 1-bar execution delay: signals fire on bar i, fills execute on bar i+1's close
    (matches TradingView default behavior — orders placed on bar close fill next bar)

All indicator calculations use exponential moving averages matching
Pine Script's ta.ema() recursive formula.

Regime scoring:
  - detect_bear_regimes(): algorithmically identifies bear periods from price history
  - score_regime_capture(): evaluates bull capture + bear avoidance across all cycles
  - RegimeScore is stored in BacktestResult.regime_score
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Default parameters matching Montauk 8.2.1 TradingView inputs
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class StrategyParams:
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
    commission_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyParams":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ─────────────────────────────────────────────────────────────────────────────
# Indicator calculations (vectorized where possible)
# ─────────────────────────────────────────────────────────────────────────────

def ema(series: np.ndarray, length: int) -> np.ndarray:
    """Pine Script ta.ema() equivalent — recursive EMA."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    # Seed with SMA of first `length` bars
    out[length - 1] = np.mean(series[:length])
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def tema(series: np.ndarray, length: int) -> np.ndarray:
    """Triple EMA: 3*EMA1 - 3*EMA2 + EMA3."""
    e1 = ema(series, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 3 * e1 - 3 * e2 + e3


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Average True Range — EMA-smoothed like Pine's ta.atr()."""
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    # Pine uses RMA (Wilder's smoothing) for ATR, which is EMA with alpha=1/period
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period  # RMA / Wilder's
    for i in range(period, n):
        out[i] = alpha * tr[i] + (1 - alpha) * out[i - 1]
    return out


def highest(series: np.ndarray, length: int) -> np.ndarray:
    """Rolling max (ta.highest)."""
    out = np.full_like(series, np.nan)
    for i in range(length - 1, len(series)):
        out[i] = np.max(series[i - length + 1:i + 1])
    return out


def lowest(series: np.ndarray, length: int) -> np.ndarray:
    """Rolling min (ta.lowest)."""
    out = np.full_like(series, np.nan)
    for i in range(length - 1, len(series)):
        out[i] = np.min(series[i - length + 1:i + 1])
    return out


def sma(series: np.ndarray, length: int) -> np.ndarray:
    """Simple moving average."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    for i in range(length - 1, len(series)):
        out[i] = np.mean(series[i - length + 1:i + 1])
    return out


def adx(hi: np.ndarray, lo: np.ndarray, cl: np.ndarray, period: int) -> np.ndarray:
    """ADX (Average Directional Index) using Wilder's smoothing."""
    n = len(cl)
    out = np.full(n, np.nan)
    if n < period * 2:
        return out
    tr_arr = np.full(n, np.nan)
    dm_plus = np.full(n, np.nan)
    dm_minus = np.full(n, np.nan)
    for i in range(1, n):
        h_diff = hi[i] - hi[i - 1]
        l_diff = lo[i - 1] - lo[i]
        tr_arr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
        dm_plus[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0.0
        dm_minus[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0.0
    # Wilder's smoothing
    alpha = 1.0 / period
    sm_tr = np.full(n, np.nan)
    sm_dp = np.full(n, np.nan)
    sm_dm = np.full(n, np.nan)
    sm_tr[period] = np.nansum(tr_arr[1:period + 1])
    sm_dp[period] = np.nansum(dm_plus[1:period + 1])
    sm_dm[period] = np.nansum(dm_minus[1:period + 1])
    for i in range(period + 1, n):
        sm_tr[i] = sm_tr[i - 1] - sm_tr[i - 1] / period + tr_arr[i]
        sm_dp[i] = sm_dp[i - 1] - sm_dp[i - 1] / period + dm_plus[i]
        sm_dm[i] = sm_dm[i - 1] - sm_dm[i - 1] / period + dm_minus[i]
    di_plus = np.where(sm_tr > 0, 100.0 * sm_dp / sm_tr, np.nan)
    di_minus = np.where(sm_tr > 0, 100.0 * sm_dm / sm_tr, np.nan)
    dx = np.where((di_plus + di_minus) > 0,
                  100.0 * np.abs(di_plus - di_minus) / (di_plus + di_minus), np.nan)
    # Smooth DX with Wilder's to get ADX
    adx_arr = np.full(n, np.nan)
    first_valid = period * 2
    if first_valid < n:
        adx_arr[first_valid] = np.nanmean(dx[period:first_valid + 1])
        for i in range(first_valid + 1, n):
            if not np.isnan(adx_arr[i - 1]) and not np.isnan(dx[i]):
                adx_arr[i] = adx_arr[i - 1] * (1 - alpha) + dx[i] * alpha
    return adx_arr


# ─────────────────────────────────────────────────────────────────────────────
# Regime detection and scoring
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Regime:
    """A single bear or bull market period."""
    kind: str           # "bear" or "bull"
    start_idx: int
    end_idx: int
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    move_pct: float     # negative for bear, positive for bull


@dataclass
class RegimeScore:
    """Regime capture quality metrics."""
    bull_capture_ratio: float   # 0.0–1.0: fraction of each bull leg participated in (avg)
    bear_avoidance_ratio: float # 0.0–1.0: fraction of each bear leg avoided (avg)
    composite: float            # 0.5 * bull + 0.5 * bear
    num_bull_periods: int
    num_bear_periods: int
    bull_detail: list           # per-bull: {start, end, move_pct, captured_pct}
    bear_detail: list           # per-bear: {start, end, move_pct, avoided_pct}

    def summary_str(self) -> str:
        lines = [
            f"Regime Score:    {self.composite:>8.3f}",
            f"  Bull Capture:  {self.bull_capture_ratio:>8.3f}  ({self.num_bull_periods} periods)",
            f"  Bear Avoidance:{self.bear_avoidance_ratio:>8.3f}  ({self.num_bear_periods} periods)",
        ]
        return "\n".join(lines)


def detect_bear_regimes(
    close: np.ndarray,
    dates: np.ndarray,
    bear_threshold: float = 0.30,
    min_duration: int = 20,
) -> list[Regime]:
    """
    Algorithmically detect bear market periods from a price series.

    A bear period starts when price drops bear_threshold% from a rolling peak,
    and ends when price recovers above a new local peak (or the series ends).
    Requires min_duration bars to count as a real bear.

    Parameters
    ----------
    close : price series
    dates : date array (same length as close)
    bear_threshold : minimum peak-to-trough drawdown to qualify (default 0.30 = 30%)
    min_duration : minimum bars between bear start and trough to qualify

    Returns
    -------
    List of Regime objects with kind="bear"
    """
    n = len(close)
    bears = []

    peak_idx = 0
    peak_price = close[0]
    in_bear = False
    bear_start_idx = 0
    trough_idx = 0
    trough_price = close[0]

    for i in range(1, n):
        if in_bear:
            if close[i] < trough_price:
                trough_idx = i
                trough_price = close[i]
            # Bear ends when price recovers above the peak that started it
            # (or recovers enough — use peak_price as the target)
            if close[i] >= peak_price:
                duration = trough_idx - bear_start_idx
                if duration >= min_duration:
                    bears.append(Regime(
                        kind="bear",
                        start_idx=bear_start_idx,
                        end_idx=trough_idx,
                        start_date=str(dates[bear_start_idx])[:10],
                        end_date=str(dates[trough_idx])[:10],
                        start_price=peak_price,
                        end_price=trough_price,
                        move_pct=(trough_price / peak_price - 1) * 100,
                    ))
                # Reset — new peak
                in_bear = False
                peak_idx = i
                peak_price = close[i]
        else:
            if close[i] > peak_price:
                peak_idx = i
                peak_price = close[i]
            else:
                drawdown = (peak_price - close[i]) / peak_price
                if drawdown >= bear_threshold:
                    in_bear = True
                    bear_start_idx = peak_idx
                    trough_idx = i
                    trough_price = close[i]

    # If still in bear at end of data, record it
    if in_bear:
        duration = trough_idx - bear_start_idx
        if duration >= min_duration:
            bears.append(Regime(
                kind="bear",
                start_idx=bear_start_idx,
                end_idx=trough_idx,
                start_date=str(dates[bear_start_idx])[:10],
                end_date=str(dates[trough_idx])[:10],
                start_price=peak_price,
                end_price=trough_price,
                move_pct=(trough_price / peak_price - 1) * 100,
            ))

    return bears


def detect_bull_regimes(
    close: np.ndarray,
    dates: np.ndarray,
    bear_regimes: list[Regime],
    bull_threshold: float = 0.20,
) -> list[Regime]:
    """
    Infer bull market periods as the gaps between bear periods.
    A bull period runs from the trough of one bear to the peak of the next.
    Only includes bull periods with move_pct >= bull_threshold.
    """
    n = len(close)
    bulls = []

    # Start of first bull: beginning of data
    # Each bear gives us a trough; the bull runs trough → next bear start
    prior_end_idx = 0

    for bear in bear_regimes:
        bull_start = prior_end_idx
        bull_end = bear.start_idx

        if bull_end <= bull_start:
            prior_end_idx = bear.end_idx
            continue

        # Find the actual peak in this window
        peak_idx_local = bull_start + int(np.argmax(close[bull_start:bull_end + 1]))
        start_price = close[bull_start]
        peak_price = close[peak_idx_local]
        move_pct = (peak_price / start_price - 1) * 100

        if move_pct >= bull_threshold * 100:
            bulls.append(Regime(
                kind="bull",
                start_idx=bull_start,
                end_idx=peak_idx_local,
                start_date=str(dates[bull_start])[:10],
                end_date=str(dates[peak_idx_local])[:10],
                start_price=start_price,
                end_price=peak_price,
                move_pct=move_pct,
            ))

        prior_end_idx = bear.end_idx

    # Final bull after last bear
    if prior_end_idx < n - 1:
        bull_start = prior_end_idx
        bull_end = n - 1
        peak_idx_local = bull_start + int(np.argmax(close[bull_start:bull_end + 1]))
        start_price = close[bull_start]
        peak_price = close[peak_idx_local]
        move_pct = (peak_price / start_price - 1) * 100
        if move_pct >= bull_threshold * 100:
            bulls.append(Regime(
                kind="bull",
                start_idx=bull_start,
                end_idx=peak_idx_local,
                start_date=str(dates[bull_start])[:10],
                end_date=str(dates[peak_idx_local])[:10],
                start_price=start_price,
                end_price=peak_price,
                move_pct=move_pct,
            ))

    return bulls


def score_regime_capture(
    trades: list,
    close: np.ndarray,
    dates: np.ndarray,
    bear_threshold: float = 0.30,
    bull_threshold: float = 0.20,
) -> RegimeScore:
    """
    Score how well the strategy captures bull markets and avoids bear markets.

    For each bull period: compute what fraction of the price gain (trough to peak)
    the strategy participated in based on bars held within that period.

    For each bear period: compute what fraction of the price loss the strategy
    avoided by being out of the market.

    Returns a RegimeScore with composite = 0.5 * bull_capture + 0.5 * bear_avoidance.
    """
    n = len(close)

    # Build a bar-by-bar "in market" array from the trade log
    in_market = np.zeros(n, dtype=bool)
    for t in trades:
        entry = t.entry_bar
        exit_b = t.exit_bar if t.exit_bar >= 0 else n - 1
        in_market[entry:exit_b + 1] = True

    # Detect regimes
    bears = detect_bear_regimes(close, dates, bear_threshold=bear_threshold)
    bulls = detect_bull_regimes(close, dates, bears, bull_threshold=bull_threshold)

    # ── Score bear avoidance ──
    bear_detail = []
    bear_avoidance_scores = []
    for bear in bears:
        s, e = bear.start_idx, bear.end_idx
        if e <= s:
            continue
        bear_bars = e - s
        bars_out = np.sum(~in_market[s:e])
        avoidance = bars_out / bear_bars if bear_bars > 0 else 1.0
        bear_avoidance_scores.append(avoidance)
        bear_detail.append({
            "start": bear.start_date,
            "end": bear.end_date,
            "move_pct": round(bear.move_pct, 1),
            "avoided_pct": round(avoidance * 100, 1),
        })

    # ── Score bull capture ──
    bull_detail = []
    bull_capture_scores = []
    for bull in bulls:
        s, e = bull.start_idx, bull.end_idx
        if e <= s:
            continue
        bull_bars = e - s
        bars_in = np.sum(in_market[s:e])
        capture = bars_in / bull_bars if bull_bars > 0 else 0.0
        bull_capture_scores.append(capture)
        bull_detail.append({
            "start": bull.start_date,
            "end": bull.end_date,
            "move_pct": round(bull.move_pct, 1),
            "captured_pct": round(capture * 100, 1),
        })

    bull_capture = float(np.mean(bull_capture_scores)) if bull_capture_scores else 0.0
    bear_avoidance = float(np.mean(bear_avoidance_scores)) if bear_avoidance_scores else 1.0
    composite = 0.5 * bull_capture + 0.5 * bear_avoidance

    return RegimeScore(
        bull_capture_ratio=round(bull_capture, 4),
        bear_avoidance_ratio=round(bear_avoidance, 4),
        composite=round(composite, 4),
        num_bull_periods=len(bulls),
        num_bear_periods=len(bears),
        bull_detail=bull_detail,
        bear_detail=bear_detail,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Backtest result
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
    params: dict
    trades: list
    equity_curve: np.ndarray
    # Summary metrics
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    mar_ratio: float = 0.0
    exposure_pct: float = 0.0
    num_trades: int = 0
    trades_per_year: float = 0.0
    avg_bars_held: float = 0.0
    win_rate_pct: float = 0.0
    worst_10_bar_loss_pct: float = 0.0
    exit_reasons: dict = field(default_factory=dict)
    false_signal_rate_pct: float = 0.0   # % of trades held < 10 bars (noise trades)
    # Buy-and-hold comparison (from date of first strategy trade)
    bah_return_pct: float = 0.0       # TECL return if held from first trade to end
    bah_final_equity: float = 0.0     # $100 account just holding TECL
    vs_bah_multiple: float = 0.0      # strategy_final / bah_final (>1.0 = strategy wins)
    bah_start_date: str = ""          # date first trade was entered
    # Regime scoring (primary optimization target)
    regime_score: Optional[object] = None  # RegimeScore or None

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
        if self.bah_start_date:
            sign = "+" if self.vs_bah_multiple >= 1.0 else ""
            alpha = (self.vs_bah_multiple - 1.0) * 100
            lines.append(
                f"vs Buy & Hold:   {sign}{alpha:.1f}%  "
                f"(Strategy ${self.params.get('initial_capital', 100000) * (1 + self.total_return_pct/100):.0f}  "
                f"B&H ${self.bah_final_equity:.0f}  from {self.bah_start_date})"
            )
        if self.regime_score:
            lines.append(self.regime_score.summary_str())
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Core backtest engine
# ─────────────────────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, params: StrategyParams | None = None,
                 score_regimes: bool = True) -> BacktestResult:
    """
    Run a full backtest of the Montauk strategy on OHLCV data.

    Parameters
    ----------
    df : DataFrame with columns: date, open, high, low, close, volume
    params : StrategyParams (uses defaults if None)
    score_regimes : if True, compute regime capture score (adds ~5ms)

    Returns
    -------
    BacktestResult with trades, equity curve, summary metrics, and regime_score
    """
    if params is None:
        params = StrategyParams()

    dates = df["date"].values
    op = df["open"].values.astype(np.float64)
    hi = df["high"].values.astype(np.float64)
    lo = df["low"].values.astype(np.float64)
    cl = df["close"].values.astype(np.float64)
    vol = df["volume"].values.astype(np.float64) if "volume" in df.columns else np.ones(len(cl))
    n = len(cl)

    # ── Pre-compute all indicators ──
    ema_short = ema(cl, params.short_ema_len)
    ema_med = ema(cl, params.med_ema_len)
    ema_long = ema(cl, params.long_ema_len)
    ema_trend = ema(cl, params.trend_ema_len)
    quick_ema_arr = ema(cl, params.quick_ema_len)
    tema_vals = tema(cl, params.triple_ema_len)
    atr_vals = atr(hi, lo, cl, params.atr_period)
    atr_ema_vals = ema(atr_vals, params.atr_ratio_len)  # long-term ATR average
    adx_vals = adx(hi, lo, cl, params.adx_len)
    vol_ema_vals = ema(vol, params.vol_spike_len)  # average volume
    high_vals = highest(hi, params.range_len)
    low_vals = lowest(lo, params.range_len)
    sma_vals = sma(cl, params.range_len)

    # ── Bar-by-bar simulation ──
    equity = params.initial_capital
    equity_curve = np.zeros(n)
    position_size = 0  # 0 = flat, 1 = long
    shares = 0.0
    entry_price = 0.0
    last_sell_bar = -9999
    peak_since_entry = np.nan
    equity_peak = params.initial_capital  # for bear depth guard
    trades: list[Trade] = []
    current_trade: Optional[Trade] = None
    bars_in_position = np.zeros(n)

    # Minimum warmup: only the indicators required for the basic entry signal.
    # Optional filters guard themselves with np.isnan() checks, so they don't
    # need to hold back the whole engine. This matches TradingView, which starts
    # evaluating as soon as the core EMAs are warm.
    warmup = max(params.short_ema_len, params.med_ema_len,
                 params.trend_ema_len if params.enable_trend else 0,
                 params.atr_period if params.enable_atr_exit else 0) + 5

    # process_orders_on_close=true: signals and fills happen on the same bar's close.
    # No pending order deferral — matches TradingView's execution model for 8.2.1.

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
        # A cross occurred recently if ema_short crossed below ema_long within the
        # last sell_confirm_bars bars. We check by scanning back.
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
        # ALL bars in the confirm window must have ema_short < ema_long
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
                # process_orders_on_close=true: fill immediately at this bar's close
                exit_price = cl[i]
                pnl = shares * (exit_price - entry_price)
                commission = equity * params.commission_pct / 100 * 2
                equity += pnl - commission
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
                # process_orders_on_close=true: fill immediately at this bar's close
                entry_price = cl[i]
                shares = equity / entry_price
                position_size = 1
                peak_since_entry = np.nan
                current_trade = Trade(
                    entry_bar=i,
                    entry_date=str(dates[i])[:10],
                    entry_price=entry_price
                )

        # Track position for exposure calc
        if position_size > 0:
            bars_in_position[i] = 1

        # Update equity curve
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

    # Max drawdown
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
    avg_held = np.mean([t.bars_held for t in trades]) if trades else 0.0

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
    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    # ── Regime scoring ──
    regime_score = None
    if score_regimes:
        regime_score = score_regime_capture(trades, cl, dates)

    # ── Buy-and-hold comparison (from start of data, matching TradingView) ──
    bah_return_pct = 0.0
    bah_final_equity = params.initial_capital
    vs_bah_multiple = 1.0
    bah_start_date = str(dates[0])[:10]
    bah_start_price = cl[0]
    bah_end_price = cl[-1]
    if bah_start_price > 0:
        bah_return_pct = (bah_end_price / bah_start_price - 1) * 100
        bah_final_equity = params.initial_capital * (bah_end_price / bah_start_price)
        if bah_final_equity > 0:
            vs_bah_multiple = equity_curve[-1] / bah_final_equity

    return BacktestResult(
        params=params.to_dict(),
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
        worst_10_bar_loss_pct=worst_10,
        exit_reasons=exit_reasons,
        false_signal_rate_pct=round(false_signal_rate, 1),
        bah_return_pct=round(bah_return_pct, 2),
        bah_final_equity=round(bah_final_equity, 2),
        vs_bah_multiple=round(vs_bah_multiple, 3),
        bah_start_date=bah_start_date,
        regime_score=regime_score,
    )


if __name__ == "__main__":
    from data import get_tecl_data
    df = get_tecl_data(use_yfinance=False)
    result = run_backtest(df)
    print("=== Montauk 8.2.1 Baseline (Default Params) ===")
    print(result.summary_str())
    print(f"\nTrades:")
    for t in result.trades:
        print(f"  {t.entry_date} -> {t.exit_date}  {t.pnl_pct:+.1f}%  ({t.exit_reason}, {t.bars_held} bars)")
    if result.regime_score:
        print(f"\nBear periods detected:")
        for b in result.regime_score.bear_detail:
            print(f"  {b['start']} → {b['end']}  move={b['move_pct']:+.1f}%  avoided={b['avoided_pct']:.1f}%")
        print(f"\nBull periods detected:")
        for b in result.regime_score.bull_detail:
            print(f"  {b['start']} → {b['end']}  move={b['move_pct']:+.1f}%  captured={b['captured_pct']:.1f}%")
