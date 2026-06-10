"""New-Hypothesis family (nh_*) contract tests — 2026-06-09 search stock.

For each of the 10 nh_ families:
  - registered in STRATEGY_REGISTRY (and tier-declared T1)
  - has a well-formed STRATEGY_PARAMS space (≤8 tunables excluding cooldown)
  - signals are causal-shaped: boolean entries/exits of length n, labels of
    length n
  - runs without error end-to-end (signals + backtest) on a 1,500-bar TECL
    slice
  - no-lookahead prefix property: signals computed on a data prefix match the
    full-data signals over that prefix
"""

from __future__ import annotations

import numpy as np
import pytest

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_PARAMS, STRATEGY_REGISTRY, STRATEGY_TIERS

NH_FAMILIES = [
    "nh_vix_regime_trend",
    "nh_curve_macro_trend",
    "nh_fed_easing_trend",
    "nh_volume_confirm_trend",
    "nh_xlk_anchor_trend",
    "nh_dd_scaled_reclaim",
    "nh_high_proximity_regime",
    "nh_vix_reversion_reentry",
    "nh_dual_timescale_trend",
    "nh_vol_drag_regime",
]

SLICE_BARS = 1500
PREFIX_BARS = 1000


@pytest.fixture(scope="module")
def tecl_slice():
    """Last 1,500 bars of real TECL data (covers macro/VIX/XLK/SGOV columns)."""
    df = get_tecl_data(use_yfinance=False)
    return df.iloc[-SLICE_BARS:].reset_index(drop=True)


@pytest.fixture(scope="module")
def indicators(tecl_slice):
    return Indicators(tecl_slice)


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_registered(name):
    assert name in STRATEGY_REGISTRY, f"{name} missing from STRATEGY_REGISTRY"
    assert callable(STRATEGY_REGISTRY[name])
    # Function identity: registry maps the name to the matching function.
    assert STRATEGY_REGISTRY[name].__name__ == name


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_tier_declared_t1(name):
    assert STRATEGY_TIERS.get(name) == "T1", f"{name} must be declared T1"


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_param_space_well_formed(name):
    space = STRATEGY_PARAMS.get(name)
    assert space, f"{name} missing from STRATEGY_PARAMS"
    for pname, spec in space.items():
        assert len(spec) == 4, f"{name}.{pname} must be (lo, hi, step, type)"
        lo, hi, step, typ = spec
        assert lo <= hi, f"{name}.{pname}: lo > hi"
        assert step > 0, f"{name}.{pname}: step must be positive"
        assert typ in (int, float), f"{name}.{pname}: type must be int or float"
    tunables = [k for k in space if k != "cooldown"]
    assert len(tunables) <= 8, (
        f"{name} exposes {len(tunables)} tunables (excl. cooldown); T1 cap is 8"
    )


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_signals_causal_shaped(name, indicators):
    entries, exits, labels = STRATEGY_REGISTRY[name](indicators, {})
    n = indicators.n
    assert isinstance(entries, np.ndarray) and entries.dtype == bool
    assert isinstance(exits, np.ndarray) and exits.dtype == bool
    assert len(entries) == n
    assert len(exits) == n
    assert len(labels) == n
    # Not degenerate in shape: signal arrays must not be all-True.
    assert not entries.all(), f"{name}: entries fire on every bar"
    assert not exits.all(), f"{name}: exits fire on every bar"
    # Every exit bar carries a non-empty label.
    assert all(str(labels[i]) != "" for i in np.where(exits)[0]), (
        f"{name}: exit bars must be labeled"
    )


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_runs_backtest_on_slice(name, tecl_slice, indicators):
    entries, exits, labels = STRATEGY_REGISTRY[name](indicators, {})
    result = backtest(
        tecl_slice, entries, exits, labels, cooldown_bars=5, strategy_name=name
    )
    assert np.isfinite(result.share_multiple)
    assert np.isfinite(result.equity_curve[-1])
    assert result.equity_curve[-1] > 0


@pytest.mark.parametrize("name", NH_FAMILIES)
def test_no_lookahead_prefix(name, tecl_slice, indicators):
    """Signals on bars [0, PREFIX_BARS) must be identical whether or not the
    strategy can see the future bars — the bar-close causality contract."""
    full_entries, full_exits, _ = STRATEGY_REGISTRY[name](indicators, {})
    prefix_df = tecl_slice.iloc[:PREFIX_BARS].reset_index(drop=True)
    prefix_ind = Indicators(prefix_df)
    pre_entries, pre_exits, _ = STRATEGY_REGISTRY[name](prefix_ind, {})
    np.testing.assert_array_equal(
        pre_entries,
        full_entries[:PREFIX_BARS],
        err_msg=f"{name}: entries change when future data is appended",
    )
    np.testing.assert_array_equal(
        pre_exits,
        full_exits[:PREFIX_BARS],
        err_msg=f"{name}: exits change when future data is appended",
    )
