# Spike Report — Run 022 (2026-04-10)

**Run:** 0.0h | 3,647 evals | 150 generations | 4 strategies

## Validation Summary

- Raw candidates: 4
- Pre-tier3 pass: 1
- Fully validated pass: 0
- Tier3 warns: 1
- Failed validation: 3
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: none - no entry passed full validation

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Discovery | Fitness | Marker | vs B&H | Trades |
|---|----------|-----------|---------|--------|--------|--------|
| 1 | momentum_stayer | 45.5403 | 45.7526 | 0.454 | 228.560x | 43 |
| 2 | dual_momentum | 44.9757 | 45.0464 | 0.484 | 136.729x | 67 |
| 3 | ichimoku_trend | 0.0000 | 0.0000 | 0.429 | 72.553x | 89 |
| 4 | always_in_trend | 0.0000 | 0.0000 | 0.462 | 3.461x | 103 |

## Top 3 — Details

### #1: momentum_stayer

**Discovery:** 45.5403 | **Marker alignment:** 0.454 | **Fitness:** 45.7526

**Fitness:** 45.7526 | **Regime Score:** 0.551 (bull=0.559, bear=0.542) | **HHI:** 0.212

**CAGR:** 24.1% | **Max DD:** 57.0% | **MAR:** 0.422 | **vs B&H:** 228.560x | **Params:** 8

**Parameters:**
```json
{
  "slow_ema": 90,
  "rsi_len": 9,
  "exit_rsi": 40.0,
  "vol_long": 80,
  "vol_short": 10,
  "roc_period": 70,
  "fast_ema": 40,
  "vol_exit_ratio": 1.4
}
```

**Trades:** 43 total (1.6/yr) | **Win rate:** 67.4%

**Validation:** WARN | **Composite:** 0.775 | **Pine Eligible:** True
**Warnings:** trades_per_param=5.38 in soft-warning band; n_params=8 exceeds regime_transitions=7; concentration: bull_hhi=0.355 bear_hhi=0.526 dom=1.03x; meta robustness: only 57.1% within 20% of baseline; walk-forward dispersion 0.57 > 0.50; 2023_rebound: vs_bah=0.653; morris warning: max_swing=0.07 sigma_ratio=2.72; bootstrap warning: ci_width=0.265 downside_prob=0.41; QQQ same-param vs_bah=0.582 < 0.90

**Marker detail:** accuracy=0.757 | f1=0.814 | transition_timing=0.244 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** M: 43

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-05-03 | 2000-04-17 | +110.5% | M |
| 2003-05-12 | 2004-04-16 | +57.2% | M |
| 2004-11-03 | 2005-02-18 | -7.5% | M |
| 2005-06-13 | 2005-10-13 | -6.2% | M |
| 2005-11-15 | 2006-01-20 | +1.2% | M |
| 2006-02-06 | 2006-05-16 | -7.5% | M |
| 2006-09-14 | 2007-02-27 | +16.1% | M |
| 2007-03-21 | 2007-08-10 | +17.7% | M |
| 2007-08-27 | 2007-11-13 | +6.5% | M |
| 2007-11-29 | 2008-01-03 | -3.7% | M |
| ... | +33 more | | |

### #2: dual_momentum

**Discovery:** 44.9757 | **Marker alignment:** 0.484 | **Fitness:** 45.0464

**Fitness:** 45.0464 | **Regime Score:** 0.581 (bull=0.458, bear=0.703) | **HHI:** 0.180

**CAGR:** 21.7% | **Max DD:** 55.0% | **MAR:** 0.396 | **vs B&H:** 136.729x | **Params:** 9

**Parameters:**
```json
{
  "short_period": 15,
  "trend_len": 125,
  "abs_thresh": 0.0,
  "abs_period": 60,
  "short_thresh": 0.0,
  "atr_mult": 2.5,
  "short_exit": -15.0,
  "atr_period": 20,
  "abs_exit": -8.0
}
```

**Trades:** 67 total (2.5/yr) | **Win rate:** 56.7%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** trades_per_param=7.44 in soft-warning band; n_params=9 exceeds regime_transitions=7; composite_confidence=0.000 < 0.70
**Hard fails:** exit proximity: 3.08x/1.61x near bear starts

**Marker detail:** accuracy=0.739 | f1=0.792 | transition_timing=0.406 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** A: 46, S: 21

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-04-23 | 1999-04-28 | -4.4% | A |
| 1999-05-07 | 1999-06-03 | -7.3% | S |
| 1999-06-16 | 1999-07-20 | +25.1% | A |
| 1999-08-16 | 1999-10-01 | +0.4% | A |
| 1999-11-03 | 2000-01-04 | +78.2% | A |
| 2000-02-02 | 2000-04-11 | +22.8% | S |
| 2000-07-17 | 2000-07-24 | -19.3% | A |
| 2003-05-27 | 2003-08-05 | +8.9% | S |
| 2003-08-14 | 2003-09-10 | +21.4% | A |
| 2003-10-03 | 2004-03-10 | +7.6% | S |
| ... | +57 more | | |

### #3: ichimoku_trend

**Discovery:** 0.0000 | **Marker alignment:** 0.429 | **Fitness:** 0.0000

**Fitness:** 0.0000 | **Regime Score:** 0.471 (bull=0.398, bear=0.544) | **HHI:** 0.172

**CAGR:** 18.9% | **Max DD:** 44.7% | **MAR:** 0.424 | **vs B&H:** 72.553x | **Params:** 6

**Parameters:**
```json
{
  "cloud_len": 50,
  "kijun_len": 20,
  "atr_mult": 3.0,
  "atr_period": 40,
  "tenkan_len": 15,
  "cloud_buffer": 2.5
}
```

**Trades:** 89 total (3.3/yr) | **Win rate:** 48.3%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** composite_confidence=0.000 < 0.70
**Hard fails:** trades_per_year=3.30 > 3.0

**Marker detail:** accuracy=0.629 | f1=0.675 | transition_timing=0.413 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** T: 28, B: 50, A: 11

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-01-25 | 1999-02-23 | +1.6% | T |
| 1999-04-14 | 1999-04-16 | -5.8% | B |
| 1999-05-10 | 1999-05-18 | +8.1% | T |
| 1999-06-17 | 1999-07-20 | +21.1% | A |
| 1999-08-31 | 1999-09-23 | -4.5% | B |
| 1999-11-09 | 2000-01-04 | +69.4% | A |
| 2000-02-18 | 2000-04-04 | +17.7% | B |
| 2000-08-22 | 2000-09-06 | -3.8% | B |
| 2001-11-08 | 2001-12-20 | -0.6% | B |
| 2002-10-30 | 2002-12-09 | +5.7% | B |
| ... | +79 more | | |

## vs Previous Best

- **Previous best:** rsi_regime (fitness 66.4727)
- **This run's best:** momentum_stayer (fitness 45.7526)
- No improvement (-31.2%)

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

- New unique configs tested: 3,647
- Configs reused from cache: 20,353
- Total configs in history: 81,825
- Population seeded with 3 historical winners per strategy
