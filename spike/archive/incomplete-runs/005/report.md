# Spike Report — 2026-04-06

**Run:** 5.0h | 542,076 evals | 4,446 generations | 14 strategies

## Top 10

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Trades/Yr | Fitness |
|---|----------|--------|------|--------|-----|-----------|---------|
| 1 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 1.4 | 2.5982 |
| 2 | regime_composite | 2.662x | 46.3% | 75.1% | 0.616 | 0.7 | 1.6622 |
| 3 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 0.6 | 1.4306 |
| 4 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 1.6 | 0.6000 |
| 5 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 1.3 | 0.3500 |
| 6 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 1.2 | 0.3357 |
| 7 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 2.5 | 0.3065 |
| 8 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 1.4 | 0.2368 |
| 9 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 3.6 | 0.1180 |
| 10 | mean_revert_channel | 0.151x | 23.9% | 44.5% | 0.537 | 2.4 | 0.1178 |

## Top 3 — Details

### #1: rsi_vol_regime

**Fitness:** 2.5982 | **vs B&H:** 3.810x | **CAGR:** 49.4% | **Max DD:** 63.6% | **MAR:** 0.776

**Parameters:**
```json
{
  "vol_ratio_max": 1.0,
  "vol_exit_ratio": 1.6,
  "vol_long": 60,
  "entry_rsi": 40,
  "trend_len": 100,
  "panic_rsi": 10,
  "vol_short": 25,
  "rsi_len": 7,
  "exit_rsi": 85
}
```

**Trades:** 25 total (1.4/yr) | **Win rate:** 92.0%

**Exit reasons:** R: 25

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-01-15 | 2009-07-22 | +122.6% | R |
| 2009-08-18 | 2010-04-14 | +58.6% | R |
| 2010-11-18 | 2011-01-06 | +24.2% | R |
| 2011-04-20 | 2012-01-23 | -5.9% | R |
| 2012-03-07 | 2012-03-19 | +17.5% | R |
| 2012-09-27 | 2013-05-17 | +8.6% | R |
| 2013-06-06 | 2014-11-12 | +121.4% | R |
| 2014-12-18 | 2015-02-20 | +9.6% | R |
| 2015-03-09 | 2015-10-23 | +4.3% | R |
| 2015-11-16 | 2016-03-21 | +2.7% | R |
| ... | +15 more | | |

### #2: regime_composite

**Fitness:** 1.6622 | **vs B&H:** 2.662x | **CAGR:** 46.3% | **Max DD:** 75.1% | **MAR:** 0.616

**Parameters:**
```json
{
  "macd_sig": 5,
  "vol_ratio_max": 1.0,
  "rsi_len": 9,
  "vol_exit_ratio": 1.1,
  "vol_long": 90,
  "macd_slow": 36,
  "exit_rsi": 75,
  "entry_rsi": 40,
  "trend_len": 75,
  "panic_rsi": 10,
  "vol_short": 30,
  "macd_fast": 14,
  "min_signals": 2,
  "macd_exit": -4.5
}
```

**Trades:** 12 total (0.7/yr) | **Win rate:** 100.0%

**Exit reasons:** C: 12

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-05-14 | 2009-12-28 | +140.5% | C |
| 2010-11-18 | 2011-07-07 | +23.2% | C |
| 2011-11-30 | 2013-05-16 | +66.7% | C |
| 2013-06-06 | 2013-07-16 | +6.5% | C |
| 2013-08-22 | 2014-11-04 | +106.9% | C |
| 2015-03-16 | 2016-07-20 | +19.6% | C |
| 2016-09-12 | 2017-06-02 | +78.8% | C |
| 2017-08-11 | 2018-01-05 | +54.6% | C |
| 2018-07-02 | 2021-04-09 | +265.0% | C |
| 2021-05-06 | 2021-10-29 | +55.2% | C |
| ... | +2 more | | |

### #3: rsi_regime

**Fitness:** 1.4306 | **vs B&H:** 2.132x | **CAGR:** 44.4% | **Max DD:** 65.8% | **MAR:** 0.675

**Parameters:**
```json
{
  "rsi_len": 13,
  "trend_len": 150,
  "entry_rsi": 35,
  "exit_rsi": 80,
  "panic_rsi": 15
}
```

**Trades:** 10 total (0.6/yr) | **Win rate:** 100.0%

**Exit reasons:** R: 9, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-02-24 | 2010-04-14 | +326.9% | R |
| 2010-05-10 | 2010-11-03 | +15.2% | R |
| 2011-03-21 | 2012-02-03 | +11.6% | R |
| 2012-10-15 | 2017-02-16 | +352.6% | R |
| 2018-02-06 | 2019-03-21 | +22.6% | R |
| 2019-05-14 | 2020-01-02 | +83.5% | R |
| 2020-03-02 | 2020-08-28 | +52.7% | R |
| 2020-10-29 | 2021-11-05 | +185.6% | R |
| 2023-08-14 | 2024-06-17 | +112.5% | R |
| 2024-07-26 | 2026-04-01 | +9.4% | End of Data |

## vs Previous Best

- **Previous best:** rsi_vol_regime (fitness 2.5982)
- **This run's best:** rsi_vol_regime (fitness 2.5982)
- No improvement (-0.0%)

## All-Time Leaderboard (Top 20)

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|--------|------|--------|-----|---------|--------|------|
| 1 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 2.5982 | active | 2026-04-06 |
| 2 | regime_composite | 2.662x | 46.3% | 75.1% | 0.616 | 1.6622 | active | 2026-04-06 |
| 3 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 1.4306 | 1 runs flat | 2026-04-04 |
| 4 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 0.6000 | active | 2026-04-06 |
| 5 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | active | 2026-04-04 |
| 6 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | active | 2026-04-04 |
| 7 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 0.3500 | active | 2026-04-06 |
| 8 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 0.3357 | active | 2026-04-06 |
| 9 | montauk_821 | 0.454x | 32.0% | 59.4% | 0.539 | 0.3192 | active | 2026-04-04 |
| 10 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 0.3065 | active | 2026-04-06 |
| 11 | montauk_821 | 0.357x | 30.2% | 59.4% | 0.509 | 0.2513 | active | 2026-04-04 |
| 12 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 0.2368 | active | 2026-04-06 |
| 13 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 0.1180 | active | 2026-04-06 |
| 14 | mean_revert_channel | 0.151x | 23.9% | 44.5% | 0.537 | 0.1178 | active | 2026-04-06 |
| 15 | golden_cross | 0.159x | 24.2% | 75.1% | 0.323 | 0.0994 | 1 runs flat | 2026-04-04 |
| 16 | golden_cross | 0.155x | 24.0% | 75.1% | 0.320 | 0.0965 | 1 runs flat | 2026-04-04 |
| 17 | bollinger_squeeze | 0.116x | 22.0% | 66.6% | 0.330 | 0.0776 | 1 runs flat | 2026-04-04 |
| 18 | bollinger_squeeze | 0.110x | 21.6% | 61.2% | 0.354 | 0.0765 | 1 runs flat | 2026-04-04 |
| 19 | rsi_adx_power | 0.085x | 19.8% | 36.2% | 0.548 | 0.0594 | active | 2026-04-06 |
| 20 | keltner_rsi | 0.098x | 20.8% | 49.6% | 0.420 | 0.0494 | active | 2026-04-06 |

## Session Stats

- New unique configs tested: 542,076
- Configs reused from cache: 3,459,324
- Total configs in history: 543,359
- Population seeded with 2 historical winners per strategy
