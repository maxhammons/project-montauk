# Spike Report — 2026-04-07

**Run:** 5.0h | 314,447 evals | 57,330 generations | 1 strategies

## Top 10

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Trades/Yr | Fitness |
|---|----------|--------|------|--------|-----|-----------|---------|
| 1 | regime_score | 44.075x | 72.1% | 71.7% | 1.007 | 1.4 | 28.2741 |

## Top 3 — Details

### #1: regime_score

**Fitness:** 28.2741 | **vs B&H:** 44.075x | **CAGR:** 72.1% | **Max DD:** 71.7% | **MAR:** 1.007

**Parameters:**
```json
{
  "rsi_len": 7,
  "dd_center": -35.0,
  "w_vol": 0.4,
  "ma_len": 200,
  "dd_lookback": 200,
  "exit_thresh": 0.7,
  "w_price_ma": 0.2,
  "w_drawdown": 0.1,
  "panic_rsi": 10,
  "vol_long": 50,
  "vol_short": 25,
  "entry_thresh": 0.55,
  "w_rsi": 0.3
}
```

**Trades:** 24 total (1.4/yr) | **Win rate:** 83.3%

**Exit reasons:** S: 22, R: 1, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-02-23 | 2009-11-17 | +341.7% | S |
| 2010-01-22 | 2011-02-14 | +67.9% | S |
| 2011-04-18 | 2012-03-14 | +43.1% | S |
| 2012-05-17 | 2012-05-18 | -4.3% | R |
| 2012-06-01 | 2013-05-08 | +47.2% | S |
| 2013-06-24 | 2013-07-16 | +20.6% | S |
| 2013-08-27 | 2014-02-13 | +52.0% | S |
| 2014-03-14 | 2014-08-19 | +40.8% | S |
| 2014-12-10 | 2016-07-14 | +20.4% | S |
| 2016-11-01 | 2017-06-02 | +77.2% | S |
| ... | +14 more | | |

## vs Previous Best

- **Previous best:** regime_score (fitness 28.2741)
- **This run's best:** regime_score (fitness 28.2741)
- No improvement (-0.0%)

## All-Time Leaderboard (Top 20)

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|--------|------|--------|-----|---------|--------|------|
| 1 | regime_score | 44.075x | 72.1% | 71.7% | 1.007 | 28.2741 | active | 2026-04-07 |
| 2 | regime_score | 19.083x | 64.0% | 71.7% | 0.893 | 12.2417 | active | 2026-04-06 |
| 3 | regime_composite | 4.379x | 50.6% | 66.7% | 0.758 | 2.9185 | CONVERGED | 2026-04-06 |
| 4 | regime_score | 4.346x | 50.5% | 71.7% | 0.705 | 2.7878 | active | 2026-04-06 |
| 5 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 2.5982 | CONVERGED | 2026-04-06 |
| 6 | regime_composite | 2.662x | 46.3% | 75.1% | 0.616 | 1.6622 | CONVERGED | 2026-04-06 |
| 7 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 1.4306 | CONVERGED | 2026-04-04 |
| 8 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 0.6000 | CONVERGED | 2026-04-06 |
| 9 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | CONVERGED | 2026-04-04 |
| 10 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | CONVERGED | 2026-04-04 |
| 11 | stoch_drawdown_recovery | 0.473x | 32.3% | 46.6% | 0.694 | 0.3627 | CONVERGED | 2026-04-06 |
| 12 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 0.3500 | CONVERGED | 2026-04-06 |
| 13 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 0.3357 | CONVERGED | 2026-04-06 |
| 14 | montauk_821 | 0.454x | 32.0% | 59.4% | 0.539 | 0.3192 | CONVERGED | 2026-04-04 |
| 15 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 0.3065 | CONVERGED | 2026-04-06 |
| 16 | montauk_821 | 0.357x | 30.2% | 59.4% | 0.509 | 0.2513 | CONVERGED | 2026-04-04 |
| 17 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 0.2368 | CONVERGED | 2026-04-06 |
| 18 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 0.1180 | CONVERGED | 2026-04-06 |
| 19 | mean_revert_channel | 0.151x | 23.9% | 44.5% | 0.537 | 0.1178 | CONVERGED | 2026-04-06 |
| 20 | golden_cross | 0.159x | 24.2% | 75.1% | 0.323 | 0.0994 | CONVERGED | 2026-04-04 |

## Session Stats

- New unique configs tested: 314,447
- Configs reused from cache: 545,503
- Total configs in history: 980,152
- Population seeded with 2 historical winners per strategy
