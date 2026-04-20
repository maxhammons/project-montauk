"""Phase 1e — dev-only shadow comparator (backtesting.py).

Runs a minimal EMA-cross variant of the 8.2.1 logic through both our engine
and `backtesting.py`, and asserts per-trade PnL agreement within 0.5%.

Why not replicate full 8.2.1? The full strategy has a dozen layered filters
(trend, TEMA, sideways, ATR, Quick EMA, trailing, etc.) whose exact semantics
are bespoke. Replicating every filter in backtesting.py would let implementation
artifacts masquerade as agreement. Instead we compare on a minimal config
(entry=EMA(short) > EMA(med); exit=EMA(short) crosses under EMA(long) with
buffer). That's enough surface area to catch systemic bugs in either engine
(lookahead bias, wrong fill price, off-by-one bar execution, broken slippage
application). A full-strategy comparison belongs post-Phase-7 consolidation.

This is a dev-only sanity test. Do NOT import `backtesting` anywhere in
production code paths.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

backtesting = pytest.importorskip(
    "backtesting", reason="backtesting.py not installed (dev-only dependency)"
)
from backtesting import Backtest, Strategy  # noqa: E402 — after importorskip

from strategy_engine import StrategyParams, run_montauk_821  # noqa: E402
from data import get_tecl_data  # noqa: E402

PER_TRADE_TOLERANCE_PCT = 0.5  # plan specifies ±0.5% per-trade PnL agreement


def _minimal_params(slippage_pct: float = 0.05) -> StrategyParams:
    """Minimal config: only the core EMA crossover; all layered filters off."""
    return StrategyParams(
        short_ema_len=15,
        med_ema_len=30,
        long_ema_len=50,  # shorter than default (500) for more trades
        trend_ema_len=70,
        slope_lookback=10,
        min_trend_slope=0.0,
        enable_trend=False,
        enable_slope_filter=False,
        enable_below_filter=False,
        enable_sideways_filter=False,
        enable_sell_confirm=False,  # exact-bar crossunder semantics
        sell_confirm_bars=1,
        sell_buffer_pct=0.0,  # no buffer — compare raw cross behavior
        enable_sell_cooldown=False,
        enable_atr_exit=False,
        enable_quick_exit=False,
        enable_trail_stop=False,
        enable_tema_exit=False,
        enable_atr_ratio_filter=False,
        enable_adx_filter=False,
        enable_roc_filter=False,
        enable_bear_guard=False,
        enable_asymmetric_exit=False,
        enable_vol_exit=False,
        slippage_pct=slippage_pct,
        commission_pct=0.0,
        initial_capital=10_000.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# backtesting.py equivalent — identical Pine EMA + crossunder at close
# ─────────────────────────────────────────────────────────────────────────────


def _pine_ema(series: np.ndarray, length: int) -> np.ndarray:
    """Pine ta.ema with SMA seed — matches backtest_engine.ema exactly."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    out[length - 1] = float(np.mean(series[:length]))
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


class EmaCrossStrategy(Strategy):
    """Minimal EMA cross for backtesting.py — mirrors our engine precisely.

    Entry: flat AND ema_short[i] > ema_med[i]
    Exit:  long AND crossunder(ema_short, ema_long) on bar i
           (i.e., ema_short[i-1] >= ema_long[i-1] AND ema_short[i] < ema_long[i])
    Orders fill at bar i's close (trade_on_close=True on the Backtest), which
    matches `process_orders_on_close` in our engine.
    """

    short_len = 15
    med_len = 30
    long_len = 50

    def init(self):
        close = self.data.Close
        self.ema_s = self.I(_pine_ema, np.asarray(close), self.short_len)
        self.ema_m = self.I(_pine_ema, np.asarray(close), self.med_len)
        self.ema_l = self.I(_pine_ema, np.asarray(close), self.long_len)

    def next(self):
        if len(self.ema_s) < 2:
            return
        s, m, lg = self.ema_s[-1], self.ema_m[-1], self.ema_l[-1]
        s_prev, lg_prev = self.ema_s[-2], self.ema_l[-2]
        if np.isnan(s) or np.isnan(m) or np.isnan(lg):
            return
        if self.position:
            # True crossunder on this bar
            if (
                not np.isnan(s_prev)
                and not np.isnan(lg_prev)
                and s_prev >= lg_prev
                and s < lg
            ):
                self.position.close()
        else:
            if s > m:
                self.buy()


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tecl_recent() -> pd.DataFrame:
    """Last ~5 years of TECL for the comparison (keeps runtime snappy)."""
    df = get_tecl_data(use_yfinance=False)
    df = df[df["date"] >= pd.Timestamp("2019-01-01")].reset_index(drop=True)
    assert len(df) > 500, "comparator window too short"
    return df


@pytest.fixture(scope="module")
def ours_result(tecl_recent):
    """Our engine under the minimal EMA-cross config."""
    return run_montauk_821(
        tecl_recent, _minimal_params(slippage_pct=0.0), score_regimes=False
    )


@pytest.fixture(scope="module")
def shadow_stats(tecl_recent):
    """backtesting.py run under matching config (no slippage, no commission)."""
    bt_df = pd.DataFrame(
        {
            "Open": tecl_recent["open"].values,
            "High": tecl_recent["high"].values,
            "Low": tecl_recent["low"].values,
            "Close": tecl_recent["close"].values,
            "Volume": tecl_recent["volume"].values,
        },
        index=pd.to_datetime(tecl_recent["date"]),
    )

    bt = Backtest(
        bt_df,
        EmaCrossStrategy,
        cash=10_000,
        commission=0.0,
        trade_on_close=True,  # match our process_orders_on_close
        exclusive_orders=True,
        finalize_trades=True,
    )
    stats = bt.run()
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_trade_count_agrees_within_tolerance(ours_result, shadow_stats):
    """Both engines should find roughly the same number of trades on the same
    entry/exit rules. Allow a 2-trade slack for edge effects (warmup, final
    open-position handling)."""
    ours_n = ours_result.num_trades
    shadow_n = int(shadow_stats["# Trades"])
    assert abs(ours_n - shadow_n) <= 2, (
        f"shadow comparator trade count divergence: ours={ours_n} shadow={shadow_n}"
    )


def _match_trades_with_drift(ours, shadow, max_drift_days: int = 2):
    """Positionally match trades, allowing ±max_drift_days on entry date.

    `backtesting.py` has a documented bar-close execution offset vs our engine
    (see risk register: "different bar-close semantics"). Matching positionally
    and asserting entry dates are within a small window accommodates that
    while still catching systemic bugs.
    """
    ours_sorted = sorted(ours.items())
    shadow_sorted = sorted(shadow.items())
    pairs = []
    i = j = 0
    while i < len(ours_sorted) and j < len(shadow_sorted):
        od, op = ours_sorted[i]
        sd, sp = shadow_sorted[j]
        drift = (pd.Timestamp(sd) - pd.Timestamp(od)).days
        if abs(drift) <= max_drift_days:
            pairs.append((od, op, sd, sp, drift))
            i += 1
            j += 1
        elif drift < 0:
            j += 1  # shadow trade has no peer in ours — advance shadow
        else:
            i += 1  # ours trade has no peer — advance ours
    return pairs


def test_per_trade_pnl_within_0p5pct(ours_result, shadow_stats):
    """For trades that line up on the EXACT same entry date, PnL% must agree
    within ±0.5 percentage points.

    We don't assert parity on trades that drift by 1–2 bars (documented
    bar-close-semantic difference with `backtesting.py`): those trades exit
    on different bars and naturally have different PnL. The core systemic
    assertion — same entry/exit bar ⇒ same PnL — is what catches bugs.
    """
    ours_by_date = {t.entry_date: float(t.pnl_pct) for t in ours_result.trades}

    shadow_trades = shadow_stats["_trades"]
    shadow_by_date = {
        str(pd.Timestamp(row.EntryTime).date()): float(row.ReturnPct) * 100
        for row in shadow_trades.itertuples()
    }

    common = sorted(set(ours_by_date) & set(shadow_by_date))
    assert len(common) >= 10, (
        f"only {len(common)} trades line up on exact entry dates; need at least "
        "10 to meaningfully assert PnL parity"
    )

    shadow_zero_duration = {
        str(pd.Timestamp(row.EntryTime).date())
        for row in shadow_trades.itertuples()
        if row.EntryBar == row.ExitBar and float(row.ReturnPct) == 0.0
    }

    divergences = []
    for d in common:
        # backtesting.py force-finalizes the last open trade as a zero-duration,
        # same-bar liquidation. Our engine records the same position through the
        # final bar as an End-of-Data exit. Excluding that artifact keeps this
        # test focused on true same-bar execution parity.
        if d in shadow_zero_duration:
            continue
        op, sp = ours_by_date[d], shadow_by_date[d]
        diff = op - sp
        if abs(diff) > PER_TRADE_TOLERANCE_PCT:
            divergences.append(
                f"  {d}: ours={op:+.3f}% shadow={sp:+.3f}% Δ={diff:+.3f}pp"
            )

    if divergences:
        pytest.fail(
            f"{len(divergences)}/{len(common)} same-date-entry trades exceeded "
            f"±{PER_TRADE_TOLERANCE_PCT}pp per-trade PnL tolerance:\n"
            + "\n".join(divergences[:10])
        )


def test_drift_mismatched_trades_are_minority(ours_result, shadow_stats):
    """No more than ~1/3 of trades may drift by >0 bars on entry date.

    A small minority of drifted trades is acceptable (different bar-close
    semantics between engines), but if the majority drift we've likely
    introduced a systemic 1-bar execution shift that needs investigation.
    """
    ours_by_date = {t.entry_date: float(t.pnl_pct) for t in ours_result.trades}
    shadow_by_date = {
        str(pd.Timestamp(row.EntryTime).date()): float(row.ReturnPct) * 100
        for row in shadow_stats["_trades"].itertuples()
    }

    pairs = _match_trades_with_drift(ours_by_date, shadow_by_date, max_drift_days=3)
    drifted = sum(1 for _, _, _, _, drift in pairs if drift != 0)
    total = len(pairs)
    assert total > 0
    drift_frac = drifted / total
    assert drift_frac <= 1 / 3, (
        f"{drifted}/{total} trades ({drift_frac:.0%}) drift by ≥1 bar — "
        "possible systemic execution-timing shift"
    )


def test_majority_of_trades_line_up_exactly(ours_result, shadow_stats):
    """At least two-thirds of trades should line up on the EXACT same entry date.

    This catches systemic execution-timing bugs (e.g., if we silently shifted
    to next-bar fills). A 1-bar drift on a minority of trades is acceptable —
    bar-close semantics differ between engines. A majority drift is not.
    """
    ours_dates = {t.entry_date for t in ours_result.trades}
    shadow_dates = {
        str(pd.Timestamp(row.EntryTime).date())
        for row in shadow_stats["_trades"].itertuples()
    }
    exact = len(ours_dates & shadow_dates)
    total_min = min(len(ours_dates), len(shadow_dates))
    assert exact >= (2 * total_min) // 3, (
        f"only {exact}/{total_min} trades line up exactly — execution-timing drift "
        "may have been introduced"
    )
