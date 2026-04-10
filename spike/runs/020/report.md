# Spike Report — Run 020 (2026-04-10)

**Run:** 0.0h | 46 evals | 40 generations | 1 strategies

## Validation Summary

- Raw candidates: 1
- Pre-tier3 pass: 0
- Fully validated pass: 0
- Tier3 warns: 0
- Failed validation: 1
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: none - no entry passed full validation

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Discovery | Fitness | Marker | vs B&H | Trades |
|---|----------|-----------|---------|--------|--------|--------|
| 1 | montauk_821 | 12.4150 | 12.7003 | 0.275 | 55.460x | 80 |

## Top 3 — Details

### #1: montauk_821

**Discovery:** 12.4150 | **Marker alignment:** 0.275 | **Fitness:** 12.7003

**Fitness:** 12.7003 | **Regime Score:** 0.401 (bull=0.217, bear=0.586) | **HHI:** 0.198

**CAGR:** 17.8% | **Max DD:** 66.1% | **MAR:** 0.269 | **vs B&H:** 55.460x | **Params:** 10

**Parameters:**
```json
{
  "sell_buffer": 0.2,
  "quick_thresh": -13.0,
  "quick_lookback": 7,
  "slope_lookback": 11,
  "atr_mult": 3.25,
  "trend_ema": 100,
  "short_ema": 17,
  "atr_period": 35,
  "med_ema": 15,
  "quick_ema": 11
}
```

**Trades:** 80 total (2.9/yr) | **Win rate:** 75.0%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** trades_per_param=8.00 in soft-warning band; n_params=10 exceeds regime_transitions=7; strategy family still unconverged in leaderboard history; concentration nearing limit: dom=2.70x; composite_confidence=0.000 < 0.70
**Hard fails:** selection_bias: observed_rs=0.4013 expected_max=0.7607 deflated=0.0000; meta robustness: only 53.6% within 20% of baseline

**Marker detail:** accuracy=0.430 | f1=0.410 | transition_timing=0.262 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** E: 68, Q: 10, A: 1, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-02-16 | 1999-03-18 | +13.3% | E |
| 1999-04-20 | 1999-04-26 | +33.0% | E |
| 1999-05-10 | 1999-05-13 | +9.7% | E |
| 1999-05-27 | 1999-06-18 | +20.9% | E |
| 1999-07-30 | 1999-08-25 | +18.1% | E |
| 1999-09-27 | 1999-11-04 | +10.0% | E |
| 2000-01-27 | 2000-02-08 | +27.3% | E |
| 2000-04-10 | 2000-04-13 | -29.7% | Q |
| 2003-07-31 | 2003-08-21 | +9.5% | E |
| 2003-09-30 | 2003-10-07 | +19.6% | E |
| ... | +70 more | | |

## vs Previous Best

- **Previous best:** rsi_regime (fitness 66.4727)
- **This run's best:** montauk_821 (fitness 12.7003)
- No improvement (-80.9%)

## All-Time Leaderboard (Top 20)

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Fitness | Status | Date |
|---|----------|----|------|--------|-----|--------|---------|--------|------|
| 1 | rsi_regime | 0.484 | 24.9% | 63.6% | 0.392 | 283.215x | 66.4727 | active | 2026-04-09 |
| 2 | breakout | 0.616 | 15.5% | 65.6% | 0.236 | 33.448x | 12.5122 | active | 2026-04-09 |
| 3 | montauk_821 | 0.403 | 16.7% | 66.1% | 0.254 | 44.721x | 10.2324 | active | 2026-04-09 |
| 4 | ichimoku_trend | 0.573 | 12.2% | 55.7% | 0.218 | 14.995x | 6.3913 | active | 2026-04-09 |
| 5 | slope_persistence | 0.558 | 12.6% | 63.4% | 0.199 | 16.854x | 6.2371 | active | 2026-04-09 |
| 6 | momentum_stayer | 0.528 | 15.5% | 58.0% | 0.268 | 33.664x | 6.2248 | active | 2026-04-09 |
| 7 | vix_trend_regime | 0.554 | 14.0% | 58.2% | 0.240 | 23.280x | 5.5885 | active | 2026-04-09 |
| 8 | donchian_turtle | 0.485 | 15.8% | 72.4% | 0.218 | 35.801x | 5.4162 | active | 2026-04-09 |
| 9 | rsi_regime_trail | 0.539 | 12.2% | 54.5% | 0.223 | 15.003x | 4.7587 | active | 2026-04-09 |
| 10 | rsi_vol_regime | 0.463 | 12.7% | 30.6% | 0.415 | 17.115x | 4.2875 | active | 2026-04-09 |
| 11 | dual_momentum | 0.562 | 11.7% | 62.2% | 0.188 | 13.373x | 3.8012 | active | 2026-04-09 |
| 12 | vol_regime | 0.582 | 12.5% | 66.3% | 0.188 | 16.127x | 2.7078 | active | 2026-04-09 |
| 13 | trough_bounce | 0.392 | 11.6% | 69.2% | 0.168 | 13.171x | 1.4258 | active | 2026-04-09 |
| 14 | keltner_squeeze | 0.541 | 7.7% | 51.1% | 0.151 | 4.962x | 1.2966 | active | 2026-04-09 |
| 15 | vix_mean_revert | 0.479 | 6.4% | 60.9% | 0.105 | 3.545x | 0.6491 | active | 2026-04-09 |
| 16 | always_in_trend | 0.564 | 4.2% | 75.7% | 0.056 | 2.022x | 0.5811 | active | 2026-04-09 |
| 17 | ichimoku_trend | 0.699 | 14.0% | 36.9% | 0.381 | 0.036x | 0.5696 | active | 2026-04-08 |
| 18 | vol_regime | 0.686 | 14.2% | 37.5% | 0.378 | 0.037x | 0.5578 | active | 2026-04-08 |
| 19 | montauk_821 | 0.691 | 20.1% | 39.5% | 0.509 | 0.089x | 0.5546 | active | 2026-04-08 |
| 20 | ichimoku_trend | 0.666 | 16.1% | 33.4% | 0.481 | 0.049x | 0.5544 | active | 2026-04-07 |

## Session Stats

- New unique configs tested: 46
- Configs reused from cache: 114
- Total configs in history: 66,316
- Population seeded with 2 historical winners per strategy
