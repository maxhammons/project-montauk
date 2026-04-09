# Spike Report — 2026-04-06

**Run:** 5.0h | 586,996 evals | 2,926 generations | 13 strategies

## Top 10

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Trades/Yr | Fitness |
|---|----------|--------|------|--------|-----|-----------|---------|
| 1 | regime_composite | 4.379x | 50.6% | 66.7% | 0.758 | 0.8 | 2.9185 |
| 2 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 1.4 | 2.5982 |
| 3 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 0.6 | 1.4306 |
| 4 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 1.6 | 0.6000 |
| 5 | stoch_drawdown_recovery | 0.473x | 32.3% | 46.6% | 0.694 | 2.0 | 0.3627 |
| 6 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 1.3 | 0.3500 |
| 7 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 1.2 | 0.3357 |
| 8 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 2.5 | 0.3065 |
| 9 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 1.4 | 0.2368 |
| 10 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 3.6 | 0.1180 |

## Top 3 — Details

### #1: regime_composite

**Fitness:** 2.9185 | **vs B&H:** 4.379x | **CAGR:** 50.6% | **Max DD:** 66.7% | **MAR:** 0.758

**Parameters:**
```json
{
  "panic_rsi": 10,
  "macd_fast": 8,
  "macd_slow": 20,
  "vol_exit_ratio": 1.1,
  "exit_rsi": 75,
  "entry_rsi": 40,
  "macd_exit": -1.0,
  "vol_short": 30,
  "vol_ratio_max": 1.0,
  "macd_sig": 13,
  "vol_long": 40,
  "min_signals": 2,
  "trend_len": 100,
  "rsi_len": 7
}
```

**Trades:** 14 total (0.8/yr) | **Win rate:** 85.7%

**Exit reasons:** C: 13, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-03-10 | 2012-03-16 | +554.2% | C |
| 2013-02-22 | 2014-10-31 | +150.8% | C |
| 2015-03-16 | 2016-07-22 | +19.6% | C |
| 2016-11-07 | 2017-05-02 | +56.9% | C |
| 2017-07-05 | 2017-07-18 | +12.6% | C |
| 2017-08-11 | 2018-03-09 | +78.7% | C |
| 2018-03-26 | 2019-04-16 | +28.0% | C |
| 2019-05-16 | 2020-01-02 | +72.7% | C |
| 2020-07-27 | 2021-02-12 | +96.6% | C |
| 2021-02-24 | 2021-10-19 | +52.8% | C |
| ... | +4 more | | |

### #2: rsi_vol_regime

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

- **Previous best:** regime_composite (fitness 2.9185)
- **This run's best:** regime_composite (fitness 2.9185)
- **Improved by +0.0%**

## All-Time Leaderboard (Top 20)

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|--------|------|--------|-----|---------|--------|------|
| 1 | regime_composite | 4.379x | 50.6% | 66.7% | 0.758 | 2.9185 | active | 2026-04-06 |
| 2 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 2.5982 | 1 runs flat | 2026-04-06 |
| 3 | regime_composite | 2.662x | 46.3% | 75.1% | 0.616 | 1.6622 | active | 2026-04-06 |
| 4 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 1.4306 | 2 runs flat | 2026-04-04 |
| 5 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 0.6000 | 1 runs flat | 2026-04-06 |
| 6 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | 1 runs flat | 2026-04-04 |
| 7 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | 1 runs flat | 2026-04-04 |
| 8 | stoch_drawdown_recovery | 0.473x | 32.3% | 46.6% | 0.694 | 0.3627 | active | 2026-04-06 |
| 9 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 0.3500 | 1 runs flat | 2026-04-06 |
| 10 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 0.3357 | 1 runs flat | 2026-04-06 |
| 11 | montauk_821 | 0.454x | 32.0% | 59.4% | 0.539 | 0.3192 | 1 runs flat | 2026-04-04 |
| 12 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 0.3065 | 1 runs flat | 2026-04-06 |
| 13 | montauk_821 | 0.357x | 30.2% | 59.4% | 0.509 | 0.2513 | 1 runs flat | 2026-04-04 |
| 14 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 0.2368 | 1 runs flat | 2026-04-06 |
| 15 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 0.1180 | 1 runs flat | 2026-04-06 |
| 16 | mean_revert_channel | 0.151x | 23.9% | 44.5% | 0.537 | 0.1178 | 1 runs flat | 2026-04-06 |
| 17 | golden_cross | 0.159x | 24.2% | 75.1% | 0.323 | 0.0994 | 2 runs flat | 2026-04-04 |
| 18 | golden_cross | 0.155x | 24.0% | 75.1% | 0.320 | 0.0965 | 2 runs flat | 2026-04-04 |
| 19 | bollinger_squeeze | 0.116x | 22.0% | 66.6% | 0.330 | 0.0776 | 2 runs flat | 2026-04-04 |
| 20 | bollinger_squeeze | 0.110x | 21.6% | 61.2% | 0.354 | 0.0765 | 2 runs flat | 2026-04-04 |

## Session Stats

- New unique configs tested: 586,996
- Configs reused from cache: 2,046,404
- Total configs in history: 937,297
- Population seeded with 3 historical winners per strategy
