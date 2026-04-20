"""Phase 1a — indicator unit tests (LOAD-BEARING).

Verifies every foundational indicator in `scripts/strategy_engine.py` against
hand-calculated reference values.

Why this matters: post-Phase-7 consolidation, `strategy_engine` is the single
source of truth for every indicator. Any silent drift in `_ema` / `_rma` /
`_atr` would cascade into every strategy and corrupt the leaderboard. These
tests are the first line of defense.

Historical note: Phase 7 retired the duplicate execution loop, but
`backtest_engine.py` now exposes a thin compatibility façade back to
`strategy_engine`. These tests still pin bit-identical indicator behavior
across both import surfaces so old callers and verification harnesses do not
drift silently.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backtest_engine import ema as be_ema
from strategy_engine import (
    _ema as se_ema,
    _rma as se_rma,
    _atr as se_atr,
    _adx as se_adx,
    _tema as se_tema,
)

DATA = Path(__file__).resolve().parents[1] / "data"


# ─────────────────────────────────────────────────────────────────────────────
# Reference / hand-calculated values
# ─────────────────────────────────────────────────────────────────────────────


def _hand_ema_len5() -> np.ndarray:
    """EMA(length=5) on the series 1..10 with SMA seed.

    alpha = 2/(5+1) = 1/3
    SMA seed at index 4: mean(1..5) = 3.0
    Subsequent bars: ema[i] = alpha * series[i] + (1 - alpha) * ema[i-1]
    """
    expected = np.full(10, np.nan)
    expected[4] = 3.0
    # Worked through by hand — recurrence gives clean integer values on 1..10
    # because (1/3) * k + (2/3) * prev resolves to prev + 1 on this series.
    expected[5] = 4.0
    expected[6] = 5.0
    expected[7] = 6.0
    expected[8] = 7.0
    expected[9] = 8.0
    return expected


def _hand_rma_len3() -> np.ndarray:
    """RMA(length=3) on series 1..6.

    alpha = 1/3
    Seed at index 2: mean(1,2,3) = 2.0
    rma[3] = (1/3) * 4 + (2/3) * 2 = 4/3 + 4/3 = 8/3 ≈ 2.666...
    rma[4] = (1/3) * 5 + (2/3) * 8/3 = 5/3 + 16/9 = 15/9 + 16/9 = 31/9 ≈ 3.444...
    rma[5] = (1/3) * 6 + (2/3) * 31/9 = 2 + 62/27 = 54/27 + 62/27 = 116/27 ≈ 4.296...
    """
    expected = np.full(6, np.nan)
    expected[2] = 2.0
    expected[3] = 8.0 / 3.0
    expected[4] = (1 / 3) * 5 + (2 / 3) * expected[3]
    expected[5] = (1 / 3) * 6 + (2 / 3) * expected[4]
    return expected


def _hand_tema_len3_on_linear_series() -> np.ndarray:
    """TEMA(length=3) on the series 1..10 with SMA-seeded EMAs."""
    expected = np.full(10, np.nan)
    expected[6:] = np.array([7.0, 8.0, 9.0, 10.0])
    return expected


def _hand_adx_len3_strict_uptrend() -> np.ndarray:
    """ADX(length=3) on a strict uptrend with +DM only on every valid bar."""
    expected = np.full(7, np.nan)
    expected[2] = 100.0 / 3.0
    expected[3] = 500.0 / 9.0
    expected[4] = 1900.0 / 27.0
    expected[5] = 6500.0 / 81.0
    expected[6] = 21100.0 / 243.0
    return expected


# ─────────────────────────────────────────────────────────────────────────────
# EMA — hand-calc + cross-engine parity
# ─────────────────────────────────────────────────────────────────────────────


def test_ema_hand_calculated_10_value_series():
    """strategy_engine._ema on 1..10 with length=5 matches hand calc."""
    series = np.arange(1, 11, dtype=np.float64)
    out = se_ema(series, 5)
    expected = _hand_ema_len5()

    # First 4 bars must be NaN (warmup)
    assert np.all(np.isnan(out[:4]))
    # Subsequent 6 bars must equal hand-calculated values
    np.testing.assert_allclose(out[4:], expected[4:], rtol=0, atol=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# TEMA — identity check + fixed-reference values
# ─────────────────────────────────────────────────────────────────────────────


def test_tema_is_3e1_minus_3e2_plus_e3():
    """strategy_engine._tema equals 3*EMA1 - 3*EMA2 + EMA3 by construction.

    Post-Phase-7, `strategy_engine` is the only TEMA implementation. The
    `_ema` helper handles NaN-prefixed input correctly (seeds from the first
    window of `length` consecutive non-NaN values), so the chained EMAs
    inside TEMA produce finite output. This is the fix referenced in the
    Phase 7 verification note.
    """
    rng = np.random.default_rng(7)
    series = rng.uniform(10, 100, size=300).astype(np.float64)

    for length in (5, 20, 50):
        e1 = se_ema(series, length)
        e2 = se_ema(e1, length)
        e3 = se_ema(e2, length)
        expected = 3 * e1 - 3 * e2 + e3

        actual_se = se_tema(series, length)

        mask = ~np.isnan(expected)
        np.testing.assert_allclose(
            actual_se[mask],
            expected[mask],
            rtol=0,
            atol=1e-12,
            err_msg=f"se_tema mismatch length={length}",
        )


def test_tema_hand_calculated_linear_series():
    """TEMA(length=3) on 1..10 matches fixed reference values."""
    series = np.arange(1, 11, dtype=np.float64)
    out = se_tema(series, 3)
    expected = _hand_tema_len3_on_linear_series()

    assert np.all(np.isnan(out[:6]))
    np.testing.assert_allclose(out[6:], expected[6:], rtol=0, atol=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# RMA / Wilder's smoothing — hand-calc
# ─────────────────────────────────────────────────────────────────────────────


def test_rma_wilder_hand_calculated():
    """strategy_engine._rma (Wilder's) on 1..6 with length=3 matches hand calc."""
    series = np.arange(1, 7, dtype=np.float64)
    out = se_rma(series, 3)
    expected = _hand_rma_len3()

    assert np.all(np.isnan(out[:2]))
    np.testing.assert_allclose(out[2:], expected[2:], rtol=0, atol=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# ATR — Wilder's smoothing on constructed TR series
# ─────────────────────────────────────────────────────────────────────────────


def test_atr_wilder_smoothing_on_constant_range():
    """Constant daily range → ATR equals that range once warmup is complete.

    Construct a bar series where high-low is always 2 and no gaps. TR[i] = 2
    for all i; RMA of a constant is that constant. ATR must converge to 2.0.
    """
    n = 30
    close = np.linspace(100, 120, n)
    # Keep TR = 2 by anchoring high = close + 1, low = close - 1, no gaps
    high = close + 1
    low = close - 1

    out = se_atr(high, low, close, period=5)

    # Seed bar = mean of first 5 TRs = 2.0; subsequent bars remain 2.0 exactly
    assert np.all(np.isnan(out[:4]))
    np.testing.assert_allclose(out[4:], 2.0, rtol=0, atol=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# _ema NaN-prefix handling (chained-TEMA case)
# ─────────────────────────────────────────────────────────────────────────────


def test_ema_nan_prefix_handling_chained_tema():
    """The inner EMAs in TEMA feed NaN prefixes to the outer EMAs.

    `_ema` must (a) skip over NaN entries and (b) seed from the first window
    of `length` consecutive non-NaN values. Verified by: TEMA on a clean
    series is finite from index `3*length - 3` onward (three warmup runs each
    of `length - 1` bars).
    """
    length = 5
    series = np.arange(1, 51, dtype=np.float64)
    tema_out = se_tema(series, length)

    # First valid TEMA bar = 3*(length-1) = 12
    first_valid = 3 * (length - 1)
    assert np.all(np.isnan(tema_out[:first_valid]))
    assert np.all(np.isfinite(tema_out[first_valid:]))


def test_ema_reseeds_after_internal_nan_gap():
    """`_ema` re-seeds from the bar after a NaN gap (leaves NaN in, not zero)."""
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0, np.nan, 6.0, 7.0, 8.0])
    out = se_ema(series, 3)
    # The NaN at index 5 must stay NaN in the output
    assert np.isnan(out[5])
    # The bar after the NaN must NOT be NaN — recurrence recovers
    assert np.isfinite(out[6])


# ─────────────────────────────────────────────────────────────────────────────
# Cross-engine EMA parity wrapper
# ─────────────────────────────────────────────────────────────────────────────


def test_backtest_engine_ema_wrapper_matches_strategy_engine():
    """Compatibility façade in backtest_engine must stay bit-identical."""
    series = np.arange(1, 21, dtype=np.float64)
    np.testing.assert_allclose(se_ema(series, 5), be_ema(series, 5), rtol=0, atol=0)


# ─────────────────────────────────────────────────────────────────────────────
# ADX — fixed reference values + real-data sanity
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tecl_excerpt() -> pd.DataFrame:
    """First 200 bars of the stored TECL.csv — a fixed, reproducible sample."""
    path = DATA / "TECL.csv"
    if not path.exists():
        pytest.skip("data/TECL.csv not present")
    df = pd.read_csv(path)
    # Pick a 200-bar window that post-dates the synthetic→real seam
    # (2008-12-17) so we're testing on real market data.
    df["date"] = pd.to_datetime(df["date"])
    real = df[df["date"] >= pd.Timestamp("2010-01-01")].head(200).reset_index(drop=True)
    assert len(real) == 200, "TECL excerpt too short — check data/TECL.csv"
    return real


def test_adx_hand_calculated_strict_uptrend():
    """ADX(length=3) on a strict uptrend matches fixed reference values."""
    high = np.array([10, 11, 12, 13, 14, 15, 16], dtype=np.float64)
    low = np.array([9, 10, 11, 12, 13, 14, 15], dtype=np.float64)
    close = np.array([9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5], dtype=np.float64)
    out = se_adx(high, low, close, period=3)
    expected = _hand_adx_len3_strict_uptrend()

    assert np.all(np.isnan(out[:2]))
    np.testing.assert_allclose(out[2:], expected[2:], rtol=0, atol=1e-10)


def test_adx_on_tecl_excerpt_is_well_formed(tecl_excerpt: pd.DataFrame):
    """ADX on a 200-bar real TECL window: bounded in [0, 100], non-NaN after warmup."""
    hi = tecl_excerpt["high"].values.astype(np.float64)
    lo = tecl_excerpt["low"].values.astype(np.float64)
    cl = tecl_excerpt["close"].values.astype(np.float64)

    adx_out = se_adx(hi, lo, cl, period=14)

    # Post-warmup values must be finite and bounded
    tail = adx_out[50:]  # well past 2*period warmup
    finite = tail[np.isfinite(tail)]
    assert len(finite) > 100, "ADX has too many NaN values post-warmup"
    assert np.all(finite >= 0.0), "ADX must be non-negative"
    assert np.all(finite <= 100.0), "ADX must be <= 100"
