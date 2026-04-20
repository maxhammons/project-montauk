"""Phase 1b — golden-trade regression (LOAD-BEARING regression net).

Re-runs `strategy_engine.run_montauk_821()` with default 8.2.1
`StrategyParams` on the current `data/TECL.csv` and asserts every trade
matches the ledger stored in `tests/golden_trades_821.json` within
±0.001% PnL tolerance.

This is the regression anchor that lets us delete the legacy Pine bridge with
confidence: if the Python engine silently changes behavior (slippage, EMA
seeding, exit priority, etc.), this test fails loudly.

Refreshing the golden:
    python tests/generate_golden_trades.py
Only do this when the change is intentional — document the reason in the
commit message, and treat it as a breaking change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backtest_engine import run_backtest
from strategy_engine import StrategyParams, run_montauk_821
from data import get_tecl_data
from share_metric import LEGACY_SHARE_MULTIPLE_KEY

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_trades_821.json"
PNL_TOLERANCE_PCT = 0.001  # ±0.001 percentage points on pnl_pct per trade
PRICE_TOLERANCE = 1e-4  # fill prices compared in dollars


@pytest.fixture(scope="module")
def golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.skip(f"missing {GOLDEN_PATH.name}; run tests/generate_golden_trades.py")
    with open(GOLDEN_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fresh_result():
    df = get_tecl_data(use_yfinance=False)
    return run_montauk_821(df, StrategyParams(), score_regimes=False)


def test_trade_count_matches_golden(golden, fresh_result):
    expected = len(golden["trades"])
    actual = len(fresh_result.trades)
    assert actual == expected, (
        f"trade count drifted: golden={expected} actual={actual}. "
        "If intentional, re-run tests/generate_golden_trades.py."
    )


def test_every_trade_matches_golden_within_tolerance(golden, fresh_result):
    """Each trade must agree on entry/exit date, exit reason, and pnl_pct."""
    golden_trades = golden["trades"]
    fresh_trades = fresh_result.trades

    assert len(fresh_trades) == len(golden_trades)

    mismatches: list[str] = []
    for i, (g, t) in enumerate(zip(golden_trades, fresh_trades)):
        if t.entry_date != g["entry_date"]:
            mismatches.append(
                f"trade {i}: entry_date {t.entry_date} != golden {g['entry_date']}"
            )
            continue
        if t.exit_date != g["exit_date"]:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_date {t.exit_date} != golden {g['exit_date']}"
            )
            continue
        if t.exit_reason != g["exit_reason"]:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_reason {t.exit_reason!r} != golden {g['exit_reason']!r}"
            )
            continue
        if abs(float(t.pnl_pct) - g["pnl_pct"]) > PNL_TOLERANCE_PCT:
            mismatches.append(
                f"trade {i} ({t.entry_date}): pnl_pct {t.pnl_pct:.6f} vs golden {g['pnl_pct']:.6f} "
                f"(Δ={t.pnl_pct - g['pnl_pct']:+.6f} > ±{PNL_TOLERANCE_PCT})"
            )
            continue
        if abs(float(t.entry_price) - g["entry_price"]) > PRICE_TOLERANCE:
            mismatches.append(
                f"trade {i} ({t.entry_date}): entry_price {t.entry_price:.6f} != golden {g['entry_price']:.6f}"
            )
        if abs(float(t.exit_price) - g["exit_price"]) > PRICE_TOLERANCE:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_price {t.exit_price:.6f} != golden {g['exit_price']:.6f}"
            )

    if mismatches:
        header = (
            f"{len(mismatches)} trade(s) diverged from golden_trades_821.json — "
            "engine behavior changed. If intentional, re-run generate_golden_trades.py."
        )
        pytest.fail(header + "\n  " + "\n  ".join(mismatches[:10]))


def test_summary_metrics_match_golden(golden, fresh_result):
    """Terminal metrics (share_multiple, CAGR, max_dd) must match."""
    meta = golden["metadata"]
    assert abs(float(fresh_result.share_multiple) - meta["share_multiple"]) < 1e-3, (
        f"share_multiple drift: {fresh_result.share_multiple} vs golden {meta['share_multiple']}"
    )
    assert abs(float(fresh_result.cagr_pct) - meta["cagr_pct"]) < 1e-2, (
        f"CAGR drift: {fresh_result.cagr_pct} vs golden {meta['cagr_pct']}"
    )
    assert (
        abs(float(fresh_result.max_drawdown_pct) - meta["max_drawdown_pct"]) < 1e-1
    ), (
        f"max_drawdown_pct drift: {fresh_result.max_drawdown_pct} vs golden {meta['max_drawdown_pct']}"
    )


def test_slippage_is_unified_per_phase1c(golden):
    """Sanity: golden was generated with slippage_pct=0.05 (Phase 1c unification)."""
    assert golden["metadata"]["slippage_pct"] == 0.05, (
        "golden_trades_821.json was generated with a non-unified slippage value — "
        "regenerate after Phase 1c."
    )


def test_compat_run_backtest_matches_strategy_engine(fresh_result):
    """The backtest_engine compatibility façade must mirror the canonical run."""
    df = get_tecl_data(use_yfinance=False)
    compat_result = run_backtest(df, StrategyParams(), score_regimes=False)

    assert compat_result.share_multiple == fresh_result.share_multiple
    assert compat_result.num_trades == fresh_result.num_trades
    assert [
        (t.entry_date, t.exit_date, t.exit_reason, round(float(t.pnl_pct), 6))
        for t in compat_result.trades
    ] == [
        (t.entry_date, t.exit_date, t.exit_reason, round(float(t.pnl_pct), 6))
        for t in fresh_result.trades
    ]


def test_legacy_leaderboard_entries_still_readable():
    """Phase 1d / Phase 7: report.py must still read old leaderboard entries.

    The old Python alias was retired in Phase 7, but older
    `spike/leaderboard.json` entries still need to load. This test pins the
    JSON-side back-compat shim in `report.py::_share_mult`.
    """
    from report import _share_mult  # noqa: WPS433 — test-local import is intentional

    # New format (Phase 1d onward)
    assert _share_mult({"share_multiple": 2.5}) == 2.5
    # Legacy format (pre-Phase 1d entries)
    assert _share_mult({LEGACY_SHARE_MULTIPLE_KEY: 3.14}) == 3.14
    # New format wins when both present
    assert _share_mult({"share_multiple": 2.5, LEGACY_SHARE_MULTIPLE_KEY: 9.0}) == 2.5
    # Missing both → zero fallback
    assert _share_mult({}) == 0.0
