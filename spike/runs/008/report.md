# Spike Report — 2026-04-07

**Run:** 0.0h | 3,041 evals | 9 generations | 14 strategies

## Top 10

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Trades | Params | Fitness |
|---|----------|----|------|--------|-----|--------|--------|--------|---------|
| 1 | regime_score | 0.600 | 62.2% | 70.1% | 0.888 | 15.854x | 14 | 13 | 0.5842 |
| 2 | ichimoku_trend | 0.699 | 14.0% | 36.9% | 0.381 | 0.036x | 50 | 6 | 0.5696 |
| 3 | dual_momentum | 0.688 | 24.1% | 36.1% | 0.667 | 0.155x | 49 | 9 | 0.5640 |
| 4 | vol_regime | 0.666 | 16.2% | 35.1% | 0.460 | 0.050x | 30 | 6 | 0.5493 |
| 5 | montauk_821 | 0.686 | 19.8% | 41.9% | 0.471 | 0.085x | 51 | 10 | 0.5423 |
| 6 | breakout | 0.664 | 20.1% | 44.1% | 0.456 | 0.089x | 45 | 5 | 0.5179 |
| 7 | rsi_vol_regime | 0.588 | 49.1% | 63.6% | 0.773 | 3.716x | 25 | 9 | 0.5133 |
| 8 | accumulation_breakout | 0.513 | 4.3% | 9.4% | 0.456 | 0.008x | 12 | 11 | 0.4890 |
| 9 | williams_midline_reclaim | 0.513 | 3.1% | 11.1% | 0.282 | 0.006x | 12 | 10 | 0.4852 |
| 10 | regime_composite | 0.534 | 50.5% | 66.7% | 0.756 | 4.320x | 14 | 14 | 0.4764 |

## Top 3 — Details

### #1: regime_score

**Fitness:** 0.5842 | **Regime Score:** 0.600 (bull=0.774, bear=0.425) | **HHI:** 0.053

**CAGR:** 62.2% | **Max DD:** 70.1% | **MAR:** 0.888 | **vs B&H:** 15.854x | **Params:** 13

**Parameters:**
```json
{
  "w_vol": 0.4,
  "entry_thresh": 0.5,
  "vol_long": 50,
  "w_drawdown": 0.3,
  "rsi_len": 7,
  "dd_lookback": 100,
  "ma_len": 200,
  "exit_thresh": 0.7,
  "w_rsi": 0.1,
  "w_price_ma": 0.2,
  "panic_rsi": 10,
  "dd_center": -35.0,
  "vol_short": 25
}
```

**Trades:** 14 total (0.8/yr) | **Win rate:** 85.7%

**Exit reasons:** S: 13, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-05-13 | 2009-11-16 | +153.4% | S |
| 2010-01-29 | 2011-02-11 | +89.0% | S |
| 2011-06-13 | 2012-03-13 | +56.0% | S |
| 2012-05-18 | 2018-02-26 | +1155.1% | S |
| 2018-11-19 | 2019-04-11 | +44.9% | S |
| 2019-10-02 | 2020-01-30 | +91.2% | S |
| 2020-03-09 | 2020-07-10 | +60.3% | S |
| 2020-10-28 | 2021-02-04 | +72.8% | S |
| 2021-05-12 | 2021-12-27 | +129.6% | S |
| 2022-02-11 | 2023-05-25 | -27.2% | S |
| ... | +4 more | | |

### #2: ichimoku_trend

**Fitness:** 0.5696 | **Regime Score:** 0.699 (bull=0.464, bear=0.933) | **HHI:** 0.046

**CAGR:** 14.0% | **Max DD:** 36.9% | **MAR:** 0.381 | **vs B&H:** 0.036x | **Params:** 6

**Parameters:**
```json
{
  "cloud_len": 50,
  "atr_period": 40,
  "atr_mult": 2.0,
  "cloud_buffer": 0.0,
  "kijun_len": 40,
  "tenkan_len": 13
}
```

**Trades:** 50 total (2.9/yr) | **Win rate:** 38.0%

**Exit reasons:** B: 37, A: 10, T: 3

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-03-27 | 2009-07-07 | +37.0% | B |
| 2009-07-27 | 2009-10-30 | +18.2% | B |
| 2009-12-29 | 2010-01-22 | -16.1% | B |
| 2010-03-10 | 2010-05-04 | +2.0% | B |
| 2010-07-26 | 2010-07-29 | -6.2% | B |
| 2010-09-20 | 2011-01-28 | +52.3% | A |
| 2011-05-03 | 2011-05-16 | -6.5% | B |
| 2011-10-12 | 2011-11-17 | -0.1% | B |
| 2012-01-11 | 2012-04-19 | +45.4% | B |
| 2012-12-18 | 2012-12-21 | -4.0% | B |
| ... | +40 more | | |

### #3: dual_momentum

**Fitness:** 0.5640 | **Regime Score:** 0.688 (bull=0.606, bear=0.769) | **HHI:** 0.042

**CAGR:** 24.1% | **Max DD:** 36.1% | **MAR:** 0.667 | **vs B&H:** 0.155x | **Params:** 9

**Parameters:**
```json
{
  "abs_period": 40,
  "abs_exit": -4.0,
  "short_thresh": 2.0,
  "atr_period": 40,
  "short_exit": -13.0,
  "short_period": 10,
  "trend_len": 50,
  "atr_mult": 3.5,
  "abs_thresh": 5.0
}
```

**Trades:** 49 total (2.8/yr) | **Win rate:** 53.1%

**Exit reasons:** A: 31, S: 18

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-03-18 | 2009-04-07 | +19.2% | A |
| 2009-05-11 | 2009-11-20 | +84.3% | A |
| 2009-12-23 | 2010-01-15 | +0.9% | A |
| 2010-03-22 | 2010-05-05 | -4.1% | S |
| 2010-07-23 | 2010-07-29 | -3.8% | A |
| 2010-09-16 | 2011-03-10 | +49.9% | A |
| 2011-07-22 | 2011-07-27 | -8.8% | A |
| 2011-10-10 | 2011-11-21 | -5.5% | S |
| 2012-01-18 | 2012-05-07 | +27.0% | A |
| 2012-07-27 | 2012-10-12 | +7.9% | A |
| ... | +39 more | | |

## vs Previous Best

- **Previous best:** regime_score (fitness 28.2741)
- **This run's best:** regime_score (fitness 0.5842)
- No improvement (-97.9%)

## All-Time Leaderboard (Top 20)

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Fitness | Status | Date |
|---|----------|----|------|--------|-----|--------|---------|--------|------|
| 1 | regime_score | 0.000 | 72.1% | 71.7% | 1.007 | 44.075x | 28.2741 | CONVERGED | 2026-04-07 |
| 2 | regime_score | 0.000 | 64.0% | 71.7% | 0.893 | 19.083x | 12.2417 | CONVERGED | 2026-04-06 |
| 3 | regime_composite | 0.000 | 50.6% | 66.7% | 0.758 | 4.379x | 2.9185 | CONVERGED | 2026-04-06 |
| 4 | regime_score | 0.000 | 50.5% | 71.7% | 0.705 | 4.346x | 2.7878 | CONVERGED | 2026-04-06 |
| 5 | rsi_vol_regime | 0.000 | 49.4% | 63.6% | 0.776 | 3.810x | 2.5982 | CONVERGED | 2026-04-06 |
| 6 | regime_composite | 0.000 | 46.3% | 75.1% | 0.616 | 2.662x | 1.6622 | CONVERGED | 2026-04-06 |
| 7 | rsi_regime | 0.000 | 44.4% | 65.8% | 0.675 | 2.132x | 1.4306 | CONVERGED | 2026-04-04 |
| 8 | breakout | 0.000 | 37.2% | 63.2% | 0.588 | 0.877x | 0.6000 | CONVERGED | 2026-04-06 |
| 9 | breakout | 0.000 | 37.5% | 71.9% | 0.521 | 0.914x | 0.5852 | CONVERGED | 2026-04-04 |
| 10 | breakout | 0.000 | 37.5% | 71.9% | 0.521 | 0.914x | 0.5852 | CONVERGED | 2026-04-04 |
| 11 | regime_score | 0.000 | 62.4% | 70.1% | 0.889 | 16.069x | 0.5842 | CONVERGED | 2026-04-07 |
| 12 | ichimoku_trend | 0.699 | 14.0% | 36.9% | 0.381 | 0.036x | 0.5696 | active | 2026-04-07 |
| 13 | dual_momentum | 0.000 | 24.4% | 36.0% | 0.679 | 0.163x | 0.5640 | 2 flat | 2026-04-07 |
| 14 | ichimoku_trend | 0.000 | 13.2% | 41.2% | 0.321 | 0.032x | 0.5529 | active | 2026-04-07 |
| 15 | vol_regime | 0.666 | 16.2% | 35.1% | 0.460 | 0.050x | 0.5493 | active | 2026-04-07 |
| 16 | vol_regime | 0.000 | 16.8% | 34.9% | 0.483 | 0.055x | 0.5476 | active | 2026-04-07 |
| 17 | montauk_821 | 0.686 | 19.8% | 41.9% | 0.471 | 0.085x | 0.5423 | active | 2026-04-07 |
| 18 | montauk_821 | 0.000 | 19.6% | 43.6% | 0.449 | 0.082x | 0.5327 | active | 2026-04-07 |
| 19 | breakout | 0.664 | 20.1% | 44.1% | 0.456 | 0.089x | 0.5179 | CONVERGED | 2026-04-07 |
| 20 | breakout | 0.000 | 18.4% | 43.9% | 0.420 | 0.069x | 0.5143 | CONVERGED | 2026-04-07 |

## Session Stats

- New unique configs tested: 3,041
- Configs reused from cache: 2,719
- Total configs in history: 922,508
- Population seeded with 4 historical winners per strategy
