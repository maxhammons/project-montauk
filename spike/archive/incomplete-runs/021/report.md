# Spike Report — Run 021 (2026-04-10)

**Run:** 0.1h | 6,710 evals | 303 generations | 4 strategies

## Validation Summary

- Raw candidates: 4
- Pre-tier3 pass: 0
- Fully validated pass: 0
- Tier3 warns: 0
- Failed validation: 4
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: none - no entry passed full validation

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Discovery | Fitness | Marker | vs B&H | Trades |
|---|----------|-----------|---------|--------|--------|--------|
| 1 | momentum_stayer | 57.3374 | 57.5071 | 0.470 | 214.502x | 53 |
| 2 | slope_persistence | 22.8569 | 22.9144 | 0.475 | 59.224x | 73 |
| 3 | vix_trend_regime | 17.4936 | 17.7042 | 0.381 | 46.966x | 59 |
| 4 | ichimoku_trend | 0.0000 | 0.0000 | 0.429 | 72.553x | 89 |

## Top 3 — Details

### #1: momentum_stayer

**Discovery:** 57.3374 | **Marker alignment:** 0.470 | **Fitness:** 57.5071

**Fitness:** 57.5071 | **Regime Score:** 0.526 (bull=0.504, bear=0.547) | **HHI:** 0.215

**CAGR:** 23.8% | **Max DD:** 49.1% | **MAR:** 0.484 | **vs B&H:** 214.502x | **Params:** 8

**Parameters:**
```json
{
  "vol_short": 10,
  "slow_ema": 100,
  "exit_rsi": 40.0,
  "fast_ema": 40,
  "vol_long": 110,
  "roc_period": 80,
  "vol_exit_ratio": 1.2,
  "rsi_len": 9
}
```

**Trades:** 53 total (1.9/yr) | **Win rate:** 64.2%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** trades_per_param=6.62 in soft-warning band; n_params=8 exceeds regime_transitions=7; strategy family still unconverged in leaderboard history; selection_bias: observed_rs=0.5256 expected_max=0.7607 deflated=0.0000; concentration: bull_hhi=0.360 bear_hhi=0.524 dom=1.08x; meta robustness: only 57.1% within 20% of baseline; composite_confidence=0.000 < 0.70
**Hard fails:** exit proximity: 3.90x/2.04x near bear starts

**Marker detail:** accuracy=0.753 | f1=0.807 | transition_timing=0.321 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** M: 53

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-05-17 | 2000-01-06 | +98.9% | M |
| 2000-01-24 | 2000-04-03 | +30.3% | M |
| 2000-05-01 | 2000-05-03 | -17.9% | M |
| 2003-05-15 | 2004-04-29 | +47.5% | M |
| 2004-11-04 | 2005-02-18 | -10.5% | M |
| 2005-06-16 | 2005-10-14 | -5.6% | M |
| 2005-11-11 | 2006-01-20 | +0.5% | M |
| 2006-02-06 | 2006-04-28 | +7.5% | M |
| 2006-09-15 | 2007-02-27 | +15.9% | M |
| 2007-03-26 | 2007-08-03 | +21.5% | M |
| ... | +43 more | | |

### #2: slope_persistence

**Discovery:** 22.8569 | **Marker alignment:** 0.475 | **Fitness:** 22.9144

**Fitness:** 22.9144 | **Regime Score:** 0.583 (bull=0.436, bear=0.731) | **HHI:** 0.177

**CAGR:** 18.1% | **Max DD:** 63.9% | **MAR:** 0.283 | **vs B&H:** 59.224x | **Params:** 6

**Parameters:**
```json
{
  "entry_bars": 4,
  "ema_len": 70,
  "atr_mult": 2.5,
  "atr_period": 40,
  "slope_window": 7,
  "exit_bars": 7
}
```

**Trades:** 73 total (2.7/yr) | **Win rate:** 54.8%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** strategy family still unconverged in leaderboard history; selection_bias: observed_rs=0.5833 expected_max=0.7607 deflated=0.0000; composite_confidence=0.000 < 0.70
**Hard fails:** exit proximity: 5.63x/2.95x near bear starts

**Marker detail:** accuracy=0.721 | f1=0.782 | transition_timing=0.398 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** S: 39, A: 34

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-04-19 | 1999-06-07 | +29.4% | S |
| 1999-06-29 | 1999-07-20 | +11.6% | A |
| 1999-08-23 | 1999-09-23 | -1.8% | A |
| 1999-10-15 | 1999-10-26 | +0.3% | S |
| 1999-11-17 | 1999-11-30 | +6.5% | A |
| 1999-12-22 | 2000-01-04 | -3.8% | A |
| 2000-01-27 | 2000-04-03 | +39.9% | A |
| 2000-06-27 | 2000-07-07 | +3.9% | S |
| 2000-08-29 | 2000-09-19 | -22.7% | S |
| 2001-11-20 | 2002-01-02 | +0.6% | S |
| ... | +63 more | | |

### #3: vix_trend_regime

**Discovery:** 17.4936 | **Marker alignment:** 0.381 | **Fitness:** 17.7042

**Fitness:** 17.7042 | **Regime Score:** 0.626 (bull=0.352, bear=0.899) | **HHI:** 0.186

**CAGR:** 17.1% | **Max DD:** 55.8% | **MAR:** 0.306 | **vs B&H:** 46.966x | **Params:** 7

**Parameters:**
```json
{
  "vix_exit_ratio": 1.2,
  "short_ema": 10,
  "atr_mult": 3.0,
  "atr_period": 20,
  "vix_entry_ratio": 0.85,
  "vix_slow_len": 40,
  "long_ema": 70
}
```

**Trades:** 59 total (2.2/yr) | **Win rate:** 55.9%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Warnings:** trades_per_param=8.43 in soft-warning band; strategy family still unconverged in leaderboard history; selection_bias: observed_rs=0.6256 expected_max=0.7607 deflated=0.0000; concentration nearing limit: dom=2.55x; composite_confidence=0.000 < 0.70
**Hard fails:** exit proximity: 3.49x/3.65x near bear starts

**Marker detail:** accuracy=0.581 | f1=0.616 | transition_timing=0.327 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** E: 20, A: 3, V: 36

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-04-05 | 1999-05-28 | -15.4% | E |
| 1999-06-30 | 1999-07-20 | +6.7% | A |
| 1999-11-18 | 2000-01-04 | +35.4% | V |
| 2000-03-03 | 2000-04-05 | -7.2% | V |
| 2001-11-19 | 2001-12-24 | -12.9% | E |
| 2002-11-08 | 2002-11-11 | -10.6% | E |
| 2003-04-23 | 2004-03-08 | +91.4% | E |
| 2004-06-23 | 2004-07-06 | -12.5% | E |
| 2004-12-23 | 2005-01-11 | -12.6% | E |
| 2005-06-02 | 2005-09-26 | -0.4% | E |
| ... | +49 more | | |

## vs Previous Best

- **Previous best:** rsi_regime (fitness 66.4727)
- **This run's best:** momentum_stayer (fitness 57.5071)
- No improvement (-13.5%)

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

- New unique configs tested: 6,710
- Configs reused from cache: 41,770
- Total configs in history: 75,054
- Population seeded with 3 historical winners per strategy
