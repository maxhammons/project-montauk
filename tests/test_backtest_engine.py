"""Phase 1f — EMA-cross exit verification.

The EMA-cross exit is documented as equivalent to Pine's semantic:

    barssince(ta.crossunder(emaShort, emaLong)) < confirmBars
    AND ta.lowest(emaShort < emaLong ? 1 : 0, confirmBars) == 1
    AND emaShort < emaLong * (1 - buffer_pct/100)

No code fix is required (Phase 0 baseline confirmed parity). These tests pin
that behavior with a constructed scenario plus a property check on real TECL
data — if someone edits the exit block in `run_montauk_821`, we catch it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategy_engine import StrategyParams, run_montauk_821, _ema as ema
from data import get_tecl_data


# ─────────────────────────────────────────────────────────────────────────────
# Test utilities
# ─────────────────────────────────────────────────────────────────────────────


def _ohlcv_from_close(close: np.ndarray, start: str = "2020-01-01") -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with tight intrabar range.

    The intrabar range is small enough that ATR-based exits won't fire —
    lets us isolate the EMA-cross exit in constructed scenarios.
    """
    n = len(close)
    dates = pd.date_range(start, periods=n, freq="B")
    high = close + 0.01
    low = close - 0.01
    # Open = previous close (flat overnight); first open = first close
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(n, 1e6),
        }
    )


def _minimal_params() -> StrategyParams:
    """Short EMAs so a 300-bar scenario is tractable; all optional exits off."""
    return StrategyParams(
        short_ema_len=3,
        med_ema_len=5,
        long_ema_len=20,
        trend_ema_len=10,
        slope_lookback=3,
        min_trend_slope=0.0,
        enable_trend=True,
        enable_slope_filter=False,
        enable_below_filter=False,
        enable_sideways_filter=False,  # don't suppress exits by sideways
        enable_sell_confirm=True,
        sell_confirm_bars=2,
        sell_buffer_pct=0.2,
        enable_sell_cooldown=False,  # don't gate re-entries
        enable_atr_exit=False,  # isolate EMA-cross exit
        enable_quick_exit=False,
        enable_trail_stop=False,
        enable_tema_exit=False,
        enable_atr_ratio_filter=False,
        enable_adx_filter=False,
        enable_roc_filter=False,
        enable_bear_guard=False,
        enable_asymmetric_exit=False,
        enable_vol_exit=False,
        slippage_pct=0.0,  # cleaner prices for the assertion
    )


# ─────────────────────────────────────────────────────────────────────────────
# Constructed scenario: an EMA cross must fire during a sustained reversal
# ─────────────────────────────────────────────────────────────────────────────


def test_ema_cross_exit_fires_on_constructed_reversal():
    """Build a price path that enters, then reverses hard enough to cross EMAs.

    Structure:
      - 60 bars flat at 100 (warm all EMAs, including long_ema=20)
      - 40 bars of steady rise 100 → 140 (entry fires: short > med, trend+)
      - 60 bars of decline 140 → 90 (short falls below long → EMA cross exit)

    Must produce at least one trade with exit_reason == "EMA Cross".
    """
    close = np.concatenate(
        [
            np.full(60, 100.0),
            np.linspace(100.0, 140.0, 40),
            np.linspace(140.0, 90.0, 60),
        ]
    )
    df = _ohlcv_from_close(close)

    params = _minimal_params()
    result = run_montauk_821(df, params, score_regimes=False)

    assert result.num_trades >= 1, "no trades on a constructed entry+reversal"
    ema_cross_trades = [t for t in result.trades if t.exit_reason == "EMA Cross"]
    assert ema_cross_trades, (
        "constructed reversal produced no EMA Cross exit — possible regression "
        "in the exit stack priority or crossunder detection"
    )


def test_ema_cross_exit_respects_buffer():
    """The sell buffer must prevent exit when short is just barely below long.

    Hover short slightly below long (within buffer) → no EMA Cross exit.
    """
    # Construct: rise then gentle drift so short ~= long within buffer
    close = np.concatenate(
        [
            np.full(60, 100.0),
            np.linspace(100.0, 115.0, 40),
            # Tiny decay — short dips below long by far less than 0.2%
            100.0 - np.linspace(0.0, 0.05, 50) + 15.0,
        ]
    )
    df = _ohlcv_from_close(close)

    params = _minimal_params()
    # Wide buffer so only a clear break produces the cross
    params.sell_buffer_pct = 2.0
    result = run_montauk_821(df, params, score_regimes=False)

    # With a 2% buffer on an almost-flat decay, no EMA Cross exit should fire.
    for t in result.trades:
        assert t.exit_reason != "EMA Cross", (
            f"EMA Cross fired despite 2% buffer not being breached: "
            f"trade {t.entry_date}→{t.exit_date}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property check on real TECL data + default 8.2.1 params
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_result():
    df = get_tecl_data(use_yfinance=False)
    return df, run_montauk_821(df, StrategyParams(), score_regimes=False)


def test_every_ema_cross_exit_satisfies_pine_semantics(real_result):
    """For every EMA Cross exit in the default 8.2.1 run, verify:

    1. `ema_short[exit_bar] < ema_long[exit_bar] * (1 - buffer/100)`  — buffer_ok
    2. Within the last `sell_confirm_bars` bars, at least one had
       `ema_short[k-1] >= ema_long[k-1]` and `ema_short[k] < ema_long[k]`
       — i.e., `barssince(crossunder) < confirmBars`.
    3. All bars in `[exit_bar - sell_confirm_bars + 1, exit_bar]` had
       `ema_short < ema_long` — the `ta.lowest(... == 1)` semantic.
    """
    df, result = real_result
    p = StrategyParams()

    cl = df["close"].values.astype(np.float64)
    ema_short = ema(cl, p.short_ema_len)
    ema_long = ema(cl, p.long_ema_len)

    cross_trades = [t for t in result.trades if t.exit_reason == "EMA Cross"]
    assert cross_trades, "expected at least one EMA Cross exit on 8.2.1 default run"

    for t in cross_trades:
        i = t.exit_bar

        # 1. Buffer condition
        buffer_limit = ema_long[i] * (1 - p.sell_buffer_pct / 100)
        assert ema_short[i] < buffer_limit, (
            f"trade exiting {t.exit_date}: buffer violated "
            f"(short={ema_short[i]:.4f}, limit={buffer_limit:.4f})"
        )

        # 2. Recent crossunder within confirm window
        recent_cross = False
        for j in range(p.sell_confirm_bars):
            k = i - j
            if k - 1 < 0:
                break
            if (
                not np.isnan(ema_short[k - 1])
                and not np.isnan(ema_long[k - 1])
                and not np.isnan(ema_short[k])
                and not np.isnan(ema_long[k])
            ):
                if ema_short[k - 1] >= ema_long[k - 1] and ema_short[k] < ema_long[k]:
                    recent_cross = True
                    break
        assert recent_cross, (
            f"trade exiting {t.exit_date}: no crossunder within "
            f"sell_confirm_bars={p.sell_confirm_bars}"
        )

        # 3. all_below: every bar in the window has short < long
        for j in range(p.sell_confirm_bars):
            k = i - j
            assert k >= 0 and not np.isnan(ema_short[k]) and not np.isnan(ema_long[k])
            assert ema_short[k] < ema_long[k], (
                f"trade exiting {t.exit_date}: bar {k} violates all_below "
                f"(short={ema_short[k]:.4f} >= long={ema_long[k]:.4f})"
            )
