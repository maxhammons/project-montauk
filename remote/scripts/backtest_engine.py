"""
Python backtesting engine — faithful replica of Project Montauk 8.2.

Mirrors the Pine Script logic bar-by-bar:
  - EMA-based entry (short > med) with trend filter
  - Exit stack: EMA cross, ATR shock, Quick EMA, Trailing stop, TEMA slope
  - Cooldown, sideways filter, TEMA entry gates
  - process_orders_on_close=True (signals and fills on same bar's close)

All indicator calculations use exponential moving averages matching
Pine Script's ta.ema() recursive formula.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Default parameters matching Montauk 8.2 TradingView inputs
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
            f"Worst 10-Bar:    {self.worst_10_bar_loss_pct:>8.1f}%",
            f"Exit Reasons:    {self.exit_reasons}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Core backtest engine
# ─────────────────────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, params: StrategyParams | None = None) -> BacktestResult:
    """
    Run a full backtest of the Montauk strategy on OHLCV data.

    Parameters
    ----------
    df : DataFrame with columns: date, open, high, low, close, volume
    params : StrategyParams (uses defaults if None)

    Returns
    -------
    BacktestResult with trades, equity curve, and summary metrics
    """
    if params is None:
        params = StrategyParams()

    dates = df["date"].values
    op = df["open"].values.astype(np.float64)
    hi = df["high"].values.astype(np.float64)
    lo = df["low"].values.astype(np.float64)
    cl = df["close"].values.astype(np.float64)
    n = len(cl)

    # ── Pre-compute all indicators ──
    ema_short = ema(cl, params.short_ema_len)
    ema_med = ema(cl, params.med_ema_len)
    ema_long = ema(cl, params.long_ema_len)
    ema_trend = ema(cl, params.trend_ema_len)
    quick_ema = ema(cl, params.quick_ema_len)
    tema_vals = tema(cl, params.triple_ema_len)
    atr_vals = atr(hi, lo, cl, params.atr_period)
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
    trades: list[Trade] = []
    current_trade: Optional[Trade] = None
    bars_in_position = np.zeros(n)

    # Minimum bar to start trading (need longest indicator warm-up)
    warmup = max(params.long_ema_len, params.trend_ema_len,
                 params.triple_ema_len * 3,  # TEMA needs 3x warmup
                 params.atr_period, params.range_len) + 10

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

        # ── Entry conditions ──
        buy_zone = ema_short[i] > ema_med[i]
        buy_ok = buy_zone and trend_ok and slope_ok and above_ok and sideways_ok

        # ── Exit 1: EMA Cross ──
        raw_sell = False
        if i >= 1 and not np.isnan(ema_short[i-1]) and not np.isnan(ema_long[i-1]):
            raw_sell = (ema_short[i-1] >= ema_long[i-1]) and (ema_short[i] < ema_long[i])
        buffer_ok = ema_short[i] < ema_long[i] * (1 - params.sell_buffer_pct / 100)

        # Confirmation: all bars in window have emaShort < emaLong
        all_below = True
        if params.enable_sell_confirm and params.sell_confirm_bars > 0:
            for j in range(params.sell_confirm_bars):
                idx = i - j
                if idx < 0 or np.isnan(ema_short[idx]) or np.isnan(ema_long[idx]):
                    all_below = False
                    break
                if not (ema_short[idx] < ema_long[idx]):
                    all_below = False
                    break
        confirm_sell = (not params.enable_sell_confirm) or all_below
        is_cross_exit = raw_sell and buffer_ok and confirm_sell

        # ── Exit 2: ATR Shock ──
        is_atr_exit = False
        if params.enable_atr_exit and i >= 1 and not np.isnan(atr_vals[i]):
            is_atr_exit = cl[i] < cl[i - 1] - atr_vals[i] * params.atr_multiplier

        # ── Exit 3: Quick EMA ──
        is_quick_exit = False
        if params.enable_quick_exit and i >= params.quick_lookback_bars:
            qe_now = quick_ema[i]
            qe_past = quick_ema[i - params.quick_lookback_bars]
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

            if exit_reason:
                # Close position at this bar's close
                exit_price = cl[i]
                pnl = shares * (exit_price - entry_price)
                commission = equity * params.commission_pct / 100 * 2  # round trip
                equity += pnl - commission
                position_size = 0
                last_sell_bar = i
                peak_since_entry = np.nan

                if current_trade:
                    current_trade.exit_bar = i
                    current_trade.exit_date = str(dates[i])[:10]
                    current_trade.exit_price = exit_price
                    current_trade.exit_reason = exit_reason
                    current_trade.pnl_pct = (exit_price / entry_price - 1) * 100
                    current_trade.bars_held = i - current_trade.entry_bar
                    trades.append(current_trade)
                    current_trade = None

                shares = 0.0
                entry_price = 0.0

        # ── Entry with cooldown ──
        if position_size == 0:
            can_enter = True
            if params.enable_sell_cooldown:
                if (i - last_sell_bar) <= params.sell_cooldown_bars:
                    can_enter = False

            if buy_ok and can_enter:
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

    # CAGR
    years = trading_bars / 252.0
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
    )


if __name__ == "__main__":
    from data import get_tecl_data
    df = get_tecl_data(use_yfinance=False)
    result = run_backtest(df)
    print("=== Montauk 8.2 Baseline (Default Params) ===")
    print(result.summary_str())
    print(f"\nTrades:")
    for t in result.trades:
        print(f"  {t.entry_date} -> {t.exit_date}  {t.pnl_pct:+.1f}%  ({t.exit_reason}, {t.bars_held} bars)")
