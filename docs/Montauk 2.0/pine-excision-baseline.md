# Pine Excision Baseline

Generated: `2026-04-15T19:50:56Z`

Purpose: institutional Phase 0 snapshot before Pine/TradingView excision. This file captures the last structural parity batch, the active 8.2.1 default-parameter audit, the current top-5 leaderboard fitness anchors, and the divergence-estimation seed snippet Phase 1 should reuse.

## Execution note

The master plan specifies `python scripts/parity.py batch`. On this machine, `python` was not available and the repo had no existing virtualenv, so I created `.venv` from `scripts/requirements.txt` and ran the equivalent project-local command:

```bash
.venv/bin/python scripts/parity.py batch
```

That preserves the intended script and environment while making the run reproducible in this workspace.

## Final structural parity report

```text
[data] TECL: 8293 bars, 1993-05-04 to 2026-04-13
[data] VIX: 8292/8293 dates matched
  adx_di_trend: [~] WARN — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 3 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  always_in_trend: [+] PASS — structural
    params: 0/0 matched, 0 mismatches
    settings: OK
    indicators: 0 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  atr_ratio_trend: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  atr_ratio_vix: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  bb_cci_combo: [~] WARN — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 8 Python, 6 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  bb_width_regime: [~] WARN — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 7 Python, 5 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  breakout: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  cci_regime_trend: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  cci_willr_combo: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  donchian_filter: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  donchian_turtle: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  double_ema_slope: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  dual_ema_stack: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  dual_momentum: [+] PASS — structural
    params: 10/10 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=3, cooldown=yes
  dual_tema_breakout: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ema_200_confirm: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ema_200_regime: [+] PASS — structural
    params: 2/2 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ema_pure_slope: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ema_regime: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ema_slope_above: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  fed_funds_pivot: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  gc_asym_fast_entry: [+] PASS — structural
    params: 7/7 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_asym_slope: [+] PASS — structural
    params: 7/7 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_asym_triple: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_pre_vix: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_precross: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_precross_roc: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_precross_strict: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_precross_vol: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_spread_band: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_spread_momentum: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_strict_vix: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  gc_tema_asym: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  golden_cross_slope: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  ichimoku_trend: [+] PASS — structural
    params: 7/7 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=3, cooldown=yes
  keltner_breakout: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 5 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  keltner_squeeze: [+] PASS — structural
    params: 0/0 matched, 0 mismatches
    settings: OK
    indicators: 0 Python, 8 Pine, 0 missing
    conditions: entry=1, exit_branches=1, cooldown=yes
  keltner_squeeze_breakout: [~] WARN — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 4 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  macd_above_zero_trend: [+] PASS — structural
    params: 2/2 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  macd_hist_trend: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  macd_qqq_bull: [~] WARN — structural
    params: 2/2 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 5 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  mfi_above_trend: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  mfi_obv_trend: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  momentum_stayer: [+] PASS — structural
    params: 9/9 matched, 0 mismatches
    settings: OK
    indicators: 7 Python, 8 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  montauk_821: [+] PASS — structural
    params: 11/11 matched, 0 mismatches
    settings: OK
    indicators: 5 Python, 7 Pine, 0 missing
    conditions: entry=1, exit_branches=3, cooldown=yes
  obv_slope_trend: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  roc_above_trend: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  roc_ema_slope: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  rsi_50_above_trend: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  rsi_recovery: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  rsi_recovery_ema: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  rsi_regime: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  rsi_regime_trail: [+] PASS — structural
    params: 8/8 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=3, cooldown=yes
  rsi_roc_combo: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  rsi_vol_regime: [+] PASS — structural
    params: 10/10 matched, 0 mismatches
    settings: OK
    indicators: 5 Python, 7 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  sgov_flight_switch: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  slope_persistence: [+] PASS — structural
    params: 7/7 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  steady_trend: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 3 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=no
  stoch_cross_trend: [~] WARN — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 1 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  stoch_recovery_trend: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  tema_short_slope: [+] PASS — structural
    params: 6/6 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  treasury_curve_trend: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  triple_ema_stack: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  trough_bounce: [+] PASS — structural
    params: 0/0 matched, 0 mismatches
    settings: OK
    indicators: 0 Python, 8 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  vix_gc_filter: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  vix_mean_revert: [+] PASS — structural
    params: 0/0 matched, 0 mismatches
    settings: OK
    indicators: 0 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  vix_term_proxy: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  vix_trend_regime: [+] PASS — structural
    params: 8/8 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 6 Pine, 0 missing
    conditions: entry=1, exit_branches=3, cooldown=yes
  vol_calm_regime: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 4 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  vol_donchian_breakout: [+] PASS — structural
    params: 3/3 matched, 0 mismatches
    settings: OK
    indicators: 2 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  vol_regime: [+] PASS — structural
    params: 7/7 matched, 0 mismatches
    settings: OK
    indicators: 4 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=2, cooldown=yes
  willr_recovery_trend: [+] PASS — structural
    params: 5/5 matched, 0 mismatches
    settings: OK
    indicators: 3 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes
  xlk_relative_strength: [+] PASS — structural
    params: 4/4 matched, 0 mismatches
    settings: OK
    indicators: 1 Python, 5 Pine, 0 missing
    conditions: entry=1, exit_branches=0, cooldown=yes

============================================================
Batch: 73 strategies — 67 PASS, 6 WARN, 0 FAIL, 0 SKIP
```

## Snapshot summary

- Structural parity batch status: `67 PASS`, `6 WARN`, `0 FAIL`, `0 SKIP`.
- WARN strategies: `adx_di_trend`, `bb_cci_combo`, `bb_width_regime`, `keltner_squeeze_breakout`, `macd_qqq_bull`, `stoch_cross_trend`.
- Active strategy anchor: `montauk_821` returned `PASS` with `11/11` params matched, `0` mismatches, `5 Python / 7 Pine / 0 missing` indicators, and `entry=1, exit_branches=3, cooldown=yes`.

## 8.2.1 default-parameter cross-reference

Compared Pine defaults from `src/strategy/active/Project Montauk 8.2.1.txt` against `StrategyParams` in `scripts/backtest_engine.py`.

### Result

No default drift found across all overlapping trade-logic fields.

| Pine input | Python field | Pine default | Python default | Status |
|---|---|---:|---:|---|
| `shortEmaLen` | `short_ema_len` | 15 | 15 | MATCH |
| `medEmaLen` | `med_ema_len` | 30 | 30 | MATCH |
| `longEmaLen` | `long_ema_len` | 500 | 500 | MATCH |
| `enableTrend` | `enable_trend` | `true` | `True` | MATCH |
| `trendEmaLen` | `trend_ema_len` | 70 | 70 | MATCH |
| `slopeLookback` | `slope_lookback` | 10 | 10 | MATCH |
| `minTrendSlope` | `min_trend_slope` | 0.0 | 0.0 | MATCH |
| `enableSlopeFilter` | `enable_slope_filter` | `false` | `False` | MATCH |
| `enableBelowFilter` | `enable_below_filter` | `false` | `False` | MATCH |
| `tripleEmaLen` | `triple_ema_len` | 200 | 200 | MATCH |
| `tripleSlopeLookback` | `triple_slope_lookback` | 1 | 1 | MATCH |
| `enableSidewaysFilter` | `enable_sideways_filter` | `true` | `True` | MATCH |
| `rangeLen` | `range_len` | 60 | 60 | MATCH |
| `maxRangePct` | `max_range_pct` | 30.0 | 30.0 | MATCH |
| `enableSellConfirm` | `enable_sell_confirm` | `true` | `True` | MATCH |
| `sellConfirmBars` | `sell_confirm_bars` | 2 | 2 | MATCH |
| `sellBufferPct` | `sell_buffer_pct` | 0.2 | 0.2 | MATCH |
| `enableSellCooldown` | `enable_sell_cooldown` | `true` | `True` | MATCH |
| `sellCooldownBars` | `sell_cooldown_bars` | 2 | 2 | MATCH |
| `enableATRExit` | `enable_atr_exit` | `true` | `True` | MATCH |
| `atrPeriod` | `atr_period` | 40 | 40 | MATCH |
| `atrMultiplier` | `atr_multiplier` | 3.0 | 3.0 | MATCH |
| `enableQuickExit` | `enable_quick_exit` | `true` | `True` | MATCH |
| `quickEmaLen` | `quick_ema_len` | 15 | 15 | MATCH |
| `quickLookbackBars` | `quick_lookback_bars` | 5 | 5 | MATCH |
| `quickDeltaPctThresh` | `quick_delta_pct_thresh` | -8.2 | -8.2 | MATCH |
| `enableTrailStop` | `enable_trail_stop` | `false` | `False` | MATCH |
| `trailDropPct` | `trail_drop_pct` | 25.0 | 25.0 | MATCH |
| `enableTemaExit` | `enable_tema_exit` | `false` | `False` | MATCH |
| `temaExitLookback` | `tema_exit_lookback` | 5 | 5 | MATCH |

### Scope notes

- Pine group 9 conviction-slider inputs are UI-only and intentionally have no `StrategyParams` counterpart.
- `StrategyParams` contains extra Python-only defaults not present in the active Pine parameter block: ATR-ratio filter, ADX filter, ROC filter, bear guard, asymmetric ATR exit, volume-spike exit, and capital settings.
- The master-plan line range for Pine (`18–80`) stops before trailing-stop and TEMA-exit inputs, but those defaults were checked as well because they are part of active 8.2.1 behavior.

## Top-5 leaderboard fitness anchor

Snapshot taken from `spike/leaderboard.json` on `2026-04-15`.

| Rank | Strategy | Fitness | Tier | Date | `vs_bah` | CAGR | Max DD | Trades | Params |
|---|---|---:|---|---|---:|---:|---:|---:|---|
| 1 | `gc_strict_vix` | 17.965287976899997 | `T1` | `2026-04-14` | 49.7607 | 29.69 | 68.2 | 23 | `fast_ema=100, slow_ema=150, slope_window=5, entry_bars=2, cooldown=5` |
| 2 | `gc_pre_vix` | 17.2919629907 | `T1` | `2026-04-14` | 47.8173 | 29.53 | 68.2 | 23 | `fast_ema=100, slow_ema=150, slope_window=3, entry_bars=2, cooldown=5` |
| 3 | `gc_pre_vix` | 16.536880294666666 | `T1` | `2026-04-14` | 45.7480 | 29.36 | 68.2 | 23 | `fast_ema=100, slow_ema=150, slope_window=3, entry_bars=3, cooldown=5` |
| 4 | `gc_pre_vix` | 16.373528537099997 | `T1` | `2026-04-14` | 45.2961 | 29.32 | 68.2 | 23 | `fast_ema=100, slow_ema=150, slope_window=5, entry_bars=2, cooldown=5` |
| 5 | `gc_strict_vix` | 14.94514693 | `T1` | `2026-04-14` | 41.3700 | 28.96 | 68.2 | 23 | `fast_ema=100, slow_ema=150, slope_window=3, entry_bars=2, cooldown=5` |

Phase 6 reproduction target: at minimum, these five fitness scores should still be reproducible from the same code/data state once Pine is gone.

## Divergence-estimation seed snippet

Saved from `scripts/parity.py` lines `871–920` for reuse in Phase 1 slippage-test work.

```python
def estimate_commission_slippage_divergence(python_trades: list) -> dict:
    """Estimate expected PnL divergence from commission-vs-slippage modeling."""
    divergences = []
    for t in python_trades:
        if t.entry_price > 0 and t.exit_price > 0:
            # Python model: entry at close * 1.0005, exit at close * 0.9995
            # Approximate the "true close" by reversing slippage
            true_entry = t.entry_price / 1.0005
            true_exit = t.exit_price / 0.9995
            py_return = t.exit_price / t.entry_price - 1
            # Pine model: fills at true close, then 0.05% commission each side
            pine_return = (true_exit / true_entry - 1) - 0.001  # ~0.10% total commission
            divergences.append(abs(py_return - pine_return) * 100)

    return {
        "max_expected_pct": max(divergences) if divergences else 0.0,
        "mean_expected_pct": sum(divergences) / len(divergences) if divergences else 0.0,
        "trade_count": len(divergences),
    }


def match_trades(python_trades: list, pine_trades: list[dict], *,
                 date_tolerance_days: int = 1,
                 price_tol_pct: float = 0.15,
                 pnl_tol_pct: float = 0.20) -> list[TradeComparison]:
    """Match Python backtest trades against TV trades and compute divergences."""
    comparisons = []

    # Build lookup by entry date for Pine trades
    pine_by_date = {}
    for pt in pine_trades:
        pine_by_date.setdefault(pt["entry_date"], []).append(pt)
    pine_used = set()

    for i, py_trade in enumerate(python_trades):
        py_entry_date = py_trade.entry_date
        py_exit_date = py_trade.exit_date

        # Try exact date match first, then +/- tolerance
        matched_pine = None
        for offset in range(date_tolerance_days + 1):
            for delta in ([0] if offset == 0 else [-offset, offset]):
                try:
                    check_date = str(
                        (pd.Timestamp(py_entry_date) + pd.Timedelta(days=delta)).date()
                    )
                except Exception:
                    continue
                candidates = pine_by_date.get(check_date, [])
                for pt in candidates:
```
