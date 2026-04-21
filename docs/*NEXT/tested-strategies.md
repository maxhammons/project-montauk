# Tested Strategies Index

Consolidated ledger of all strategies implemented, grid-tested, and validated on this project. Source-of-truth rollup from `scripts/strategies/library.py::STRATEGY_REGISTRY`, `scripts/search/grid_search.py::GRIDS`, `spike/leaderboard.json`, and brainstorm doc verdict logs.

**Snapshot 2026-04-20**: 161 strategies registered, 138 with grids, 5 on leaderboard. 889 unique (strategy, params) combos in `spike/hash-index.json` across all-time runs.

## Leaderboard (5)

| Rank | Strategy | Share | Fitness | Verdict | Notes |
|---|---|---|---|---|---|
| #1 | `gc_vjbb` | 126.80x | 46.33 | WARN \*manual\* | QQQ same-param share_multiple=0.443 < 0.50 (gate 6 soft_warning) |
| #2 | `gc_n8` | 116.34x | 42.21 | PASS  |  |
| #3 | `gc_precross_strict` | 50.71x | 16.06 | PASS  |  |
| #4 | `gc_precross_roc` | 44.44x | 11.72 | PASS  |  |
| #5 | `slope_only_200` | 2.06x | 0.49 | PASS  |  |

## Test rounds summary (2026-04-20 session)

| Round | Batch | Combos | PASS | WARN | FAIL | Leaderboard delta |
|---|---|---|---|---|---|---|
| VJ R1 | A1/A2/A3/A10 | 328 | 0 | 15 | 5 | 0 |
| VJ R2 | A4/A6/A8/B9 | 176 | 0 | 19 | 1 | 0 |
| VJ R3 | B1/B4/B14 | 92 | 0 | 8 | 12 | 0 |
| VJ Bucket C | C1/C2/C3 | 39 | 0 | 20 | 0 | 0 |
| VJ Final | 13 strategies | 291 | 1 | 6 | 18 | +1 (`slope_only_200`) |
| **Manual admission** | `gc_vjbb` | — | WARN | — | — | +1 (override of principle pr/2026-04-20-a) |
| NF Lane 2 | N5/N6/N9 | 72 | — | — | — | 0 (all charter-rejected) |
| NF Lane 1 | N1/N3 | 96 | 0 | 0 | 5 | 0 |
| NF Lane 3 | N7/N8 | 156 | 0 | 9 | 0 | 0 |
| NF Lane 4 | N10 | 16 | **3** | — | — | **0 (blocked by flaky Tiingo API)** |

## Next-Frontier Lane 1 (2)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `rank_slope_regime` | T1 | Y | - | - | - | FAIL (max raw 0.34x; signal fires too often) |
| `zscore_return_reversion` | T1 | Y | - | - | - | FAIL (max 0.19x; mean-revert sells rallies) |

## Next-Frontier Lane 2 (3)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `gc_vj_decay_gate` | T1 | Y | - | - | - | 0 charter (all 24 configs < 1.0x) |
| `gc_vj_dual_regime` | T1 | Y | - | - | - | 0 charter (16 configs — dual-regime exits cut VJ holds) |
| `gc_vj_xlk_relative_trend` | T1 | Y | - | - | - | 0 charter (32 configs) |

## Next-Frontier Lane 3 (1)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `breadth_decay_composite` | T1 | Y | - | - | - | 0 charter (36 configs) |

## Next-Frontier Lane 4 (1)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `vj_or_slope_meta` | T1 | Y | - | - | - | **3 PASS blocked at cert** by Tiingo 429 rate limit. Best fit=2.50. Re-run when API available. |

## VJ Brainstorm R1 (4)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `gc_vjatr` | T1 | Y | - | - | - | WARN (raw 116.34x) |
| `gc_vjv` | T1 | Y | - | - | - | WARN (raw 118.32x, vol-gate near-inert) |
| `gc_vjx` | T1 | Y | - | - | - | WARN (raw 130.94x, +12.5%) |
| `gc_vjxr` | T1 | Y | - | - | - | WARN (raw 1.25x) |

## VJ Brainstorm R2 (4)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `gc_vjrsi` | T1 | Y | - | - | - | WARN (RSI secondary inert) |
| `gc_vjsgov` | T1 | Y | - | - | - | WARN (raw 135.74x but marker 0.488) |
| `gc_vjtimer` | T1 | Y | - | - | - | WARN (max 7.66x) |
| `pullback_in_trend` | T1 | Y | - | - | - | 0 charter |

## VJ Brainstorm R3 (3)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `dual_tf_gc` | T1 | Y | - | - | - | FAIL (max 3.54x) |
| `rsi_regime_canonical` | T1 | Y | - | - | - | FAIL (max 2.61x) |
| `tecl_sgov_rs` | T1 | Y | - | - | - | 0 charter (SGOV post-2020 only) |

## VJ Brainstorm Final (13)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `adaptive_ema_vol` | T1 | Y | - | - | - | WARN/FAIL (max 4.42x) |
| `bounce_breakout` | T1 | Y | - | - | - | 1 charter, FAIL |
| `composite_osc_canonical` | T2 | Y | - | - | - | 1 charter, FAIL |
| `ensemble_vote_3of5` | T1 | Y | - | - | - | 0 charter |
| `fed_macro_primary` | T1 | Y | - | - | - | 0 charter (259 trades) |
| `gc_vjbb` | T1 | Y | Y* | 126.80x | 46.33 | WARN → **manually admitted #1** (raw 126.80x, marker 0.617>VJ, blocked only by QQQ 0.443<0.50) |
| `gc_vjdd` | T1 | Y | - | - | - | WARN (raw 2.58x) |
| `gc_vjmac` | T1 | Y | - | - | - | WARN (raw 1.83x) |
| `momentum_roc_canonical` | T1 | Y | - | - | - | 0 charter |
| `regime_state_machine` | T2 | Y | - | - | - | 0 charter (97.5% DD) |
| `slope_only_200` | T1 | Y | Y | 2.06x | 0.49 | **PASS → leaderboard #5** (raw 2.06x; only full PASS of 28+ brainstorm candidates) |
| `tri_filter_macd` | T1 | Y | - | - | - | 0 charter |
| `vol_regime_canonical` | T1 | Y | - | - | - | 0 charter |

## GC Enhancement Matrix (51)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `gc_c1` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c2` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c3` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c4` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c5` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c6` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c7` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_c8` | T1 | N | - | - | - | pre-session (see hash-index) |
| `gc_e1` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e10` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e11` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e12` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e13` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e14` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e15` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e16` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e17` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e18` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e19` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e2` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e3` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e4` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e5` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e6` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e7` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e8` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_e9` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n1` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n10` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n11` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n12` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n13` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n14` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n2` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n3` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n4` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n5` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n6` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n7` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_n8` | T1 | Y | Y | 116.34x | 42.21 | pre-session (see hash-index) |
| `gc_n8_ddbreaker` | T1 | Y | - | - | - | 0 charter (ATH-DD latches) |
| `gc_n8_panic_flat` | T1 | Y | - | - | - | WARN (interferes with VJ VIX panic) |
| `gc_n8_timelimit` | T1 | Y | - | - | - | WARN (max 17.97x) |
| `gc_n9` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_s1` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_s2` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_s3` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_slope_no_death` | ? | Y | - | - | - | pre-session (see hash-index) |
| `gc_spread_band` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_spread_momentum` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_strict_vix` | T1 | Y | - | - | - | pre-session (see hash-index) |

## GC hybrids 2026-04-14d (10)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `gc_asym_fast_entry` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_asym_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_asym_triple` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_atr_trail` | ? | Y | - | - | - | pre-session (see hash-index) |
| `gc_pre_vix` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_precross` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_precross_roc` | T1 | Y | Y | 44.44x | 11.72 | pre-session (see hash-index) |
| `gc_precross_strict` | T1 | Y | Y | 50.71x | 16.06 | pre-session (see hash-index) |
| `gc_precross_vol` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `gc_tema_asym` | T1 | Y | - | - | - | pre-session (see hash-index) |

## Legacy / Pre-GC-matrix (69)

| Strategy | Tier | Grid | LB | Share | Fit | Verdict |
|---|---|---|---|---|---|---|
| `adx_di_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `atr_ratio_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `atr_ratio_vix` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `bb_cci_combo` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `bb_width_regime` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `breakout` | T2 | N | - | - | - | pre-session (see hash-index) |
| `cci_regime_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `cci_willr_combo` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `consecutive_strength` | ? | Y | - | - | - | pre-session (see hash-index) |
| `donchian_filter` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `donchian_turtle` | T2 | N | - | - | - | pre-session (see hash-index) |
| `donchian_vix` | ? | Y | - | - | - | pre-session (see hash-index) |
| `double_ema_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `drawdown_recovery` | ? | Y | - | - | - | pre-session (see hash-index) |
| `dual_ema_stack` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `dual_momentum` | T2 | N | - | - | - | pre-session (see hash-index) |
| `dual_tema_breakout` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `ema_200_confirm` | T2 | Y | - | - | - | pre-session (see hash-index) |
| `ema_200_regime` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `ema_pure_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `ema_regime` | T2 | N | - | - | - | pre-session (see hash-index) |
| `ema_slope_above` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `fast_ema_atr_trail` | ? | Y | - | - | - | pre-session (see hash-index) |
| `fed_funds_pivot` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `golden_cross_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `ichimoku_trend` | T2 | N | - | - | - | pre-session (see hash-index) |
| `keltner_breakout` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `keltner_squeeze_breakout` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `macd_above_zero_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `macd_hist_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `macd_qqq_bull` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `mfi_above_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `mfi_obv_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `momentum_stayer` | T2 | N | - | - | - | pre-session (see hash-index) |
| `montauk_821` | T2 | N | - | - | - | pre-session (see hash-index) |
| `multi_tf_momentum` | ? | Y | - | - | - | pre-session (see hash-index) |
| `obv_slope_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `price_position_regime` | ? | Y | - | - | - | pre-session (see hash-index) |
| `roc_above_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `roc_ema_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `rsi_50_above_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `rsi_bull_regime` | ? | Y | - | - | - | pre-session (see hash-index) |
| `rsi_mean_revert_trend` | ? | Y | - | - | - | pre-session (see hash-index) |
| `rsi_recovery` | T2 | N | - | - | - | pre-session (see hash-index) |
| `rsi_recovery_ema` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `rsi_regime` | T2 | N | - | - | - | pre-session (see hash-index) |
| `rsi_regime_trail` | T2 | N | - | - | - | pre-session (see hash-index) |
| `rsi_roc_combo` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `rsi_vol_regime` | T2 | N | - | - | - | pre-session (see hash-index) |
| `sgov_flight_switch` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `slope_persistence` | T2 | N | - | - | - | pre-session (see hash-index) |
| `steady_trend` | T2 | N | - | - | - | pre-session (see hash-index) |
| `stoch_cross_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `stoch_recovery_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `tema_short_slope` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `treasury_curve_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `treasury_regime` | ? | Y | - | - | - | pre-session (see hash-index) |
| `triple_ema_stack` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `vix_gc_filter` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `vix_regime_entry` | ? | Y | - | - | - | pre-session (see hash-index) |
| `vix_term_proxy` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `vix_trend_regime` | T2 | N | - | - | - | pre-session (see hash-index) |
| `vol_calm_regime` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `vol_compression_breakout` | ? | Y | - | - | - | pre-session (see hash-index) |
| `vol_donchian_breakout` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `vol_regime` | T2 | N | - | - | - | pre-session (see hash-index) |
| `willr_recovery_trend` | T1 | Y | - | - | - | pre-session (see hash-index) |
| `xlk_relative_momentum` | ? | Y | - | - | - | pre-session (see hash-index) |
| `xlk_relative_strength` | T1 | Y | - | - | - | pre-session (see hash-index) |

## Known test-infrastructure issues

- **Tiingo API rate limiting** (HTTP 429) intermittently causes `crosscheck_divergence` in `scripts/data/quality.py` to return FAIL with null divergence. The `data_quality_precheck` certification gate then blocks promotion of validation-PASS candidates. Affected: `slope_only_200` (initially blocked, later promoted); `vj_or_slope_meta` (3 configs currently blocked awaiting API reset). Fix: retry when API limits clear, OR add a SKIP path for rate-limit errors in `test_crosscheck_divergence`.
- **Cross-asset gate 6** (QQQ same-param share ≥ 0.50) rejects most TECL-tuned strategies. Champion VJ is grandfathered at QQQ ~0.41. Multiple candidates this session failed by <0.1 margin on this exact gate (gc_vjbb at 0.443, nearly all GC-matrix WARNs).
- **Charter pre-filter** rejects >80% of new TECL strategies before validation runs. Share ≥ 1.0, trades ≥ 5, tpy ≤ 5 is tight on a 3× leveraged ETF where b&h compounds huge.

## How to use this index

- **Before adding a new strategy**: grep for similar-sounding names here. If a variant has already failed at charter or a specific gate, save the implementation cycle.
- **After a spike run**: append new rows to the relevant batch table. Update the summary table at top.
- **Before promoting a candidate**: check if it is already on leaderboard; check its verdict here for prior history on the same family.
