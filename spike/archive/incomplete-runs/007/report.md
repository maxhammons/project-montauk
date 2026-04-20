# Spike Report — 2026-04-06

**Run:** 0.0h | 1,710 evals | 252 generations | 1 strategies

## Top 10

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Trades/Yr | Fitness |
|---|----------|--------|------|--------|-----|-----------|---------|
| 1 | regime_score | 19.083x | 64.0% | 71.7% | 0.893 | 0.8 | 12.2417 |

## Top 3 — Details

### #1: regime_score

**Fitness:** 12.2417 | **vs B&H:** 19.083x | **CAGR:** 64.0% | **Max DD:** 71.7% | **MAR:** 0.893

**Parameters:**
```json
{
  "rsi_len": 7,
  "ma_len": 200,
  "w_rsi": 0.1,
  "exit_thresh": 0.7,
  "panic_rsi": 10,
  "w_vol": 0.4,
  "w_price_ma": 0.2,
  "vol_short": 30,
  "dd_center": -35.0,
  "entry_thresh": 0.5,
  "vol_long": 60,
  "dd_lookback": 100,
  "w_drawdown": 0.3
}
```

**Trades:** 14 total (0.8/yr) | **Win rate:** 85.7%

**Exit reasons:** S: 13, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-05-13 | 2009-11-09 | +139.0% | S |
| 2010-01-29 | 2012-03-21 | +116.2% | S |
| 2012-05-18 | 2018-03-09 | +1214.5% | S |
| 2018-11-20 | 2019-06-18 | +57.5% | S |
| 2019-08-05 | 2020-01-30 | +106.0% | S |
| 2020-03-09 | 2020-10-01 | +97.2% | S |
| 2020-10-28 | 2021-02-08 | +77.5% | S |
| 2021-05-12 | 2021-12-27 | +129.9% | S |
| 2022-01-21 | 2023-05-30 | -20.6% | S |
| 2023-08-17 | 2024-02-08 | +75.9% | S |
| ... | +4 more | | |

## vs Previous Best

- **Previous best:** regime_score (fitness 12.2417)
- **This run's best:** regime_score (fitness 12.2417)
- **Improved by +0.0%**

## All-Time Leaderboard (Top 20)

| # | Strategy | vs B&H | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|--------|------|--------|-----|---------|--------|------|
| 1 | regime_score | 19.083x | 64.0% | 71.7% | 0.893 | 12.2417 | active | 2026-04-06 |
| 2 | regime_composite | 4.379x | 50.6% | 66.7% | 0.758 | 2.9185 | 2 runs flat | 2026-04-06 |
| 3 | regime_score | 4.346x | 50.5% | 71.7% | 0.705 | 2.7878 | active | 2026-04-06 |
| 4 | rsi_vol_regime | 3.810x | 49.4% | 63.6% | 0.776 | 2.5982 | CONVERGED | 2026-04-06 |
| 5 | regime_composite | 2.662x | 46.3% | 75.1% | 0.616 | 1.6622 | 2 runs flat | 2026-04-06 |
| 6 | rsi_regime | 2.132x | 44.4% | 65.8% | 0.675 | 1.4306 | CONVERGED | 2026-04-04 |
| 7 | breakout | 0.877x | 37.2% | 63.2% | 0.588 | 0.6000 | CONVERGED | 2026-04-06 |
| 8 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | CONVERGED | 2026-04-04 |
| 9 | breakout | 0.914x | 37.5% | 71.9% | 0.521 | 0.5852 | CONVERGED | 2026-04-04 |
| 10 | stoch_drawdown_recovery | 0.473x | 32.3% | 46.6% | 0.694 | 0.3627 | 2 runs flat | 2026-04-06 |
| 11 | montauk_821 | 0.496x | 32.7% | 59.0% | 0.554 | 0.3500 | CONVERGED | 2026-04-06 |
| 12 | rsi_regime_trail | 0.495x | 32.7% | 64.5% | 0.507 | 0.3357 | CONVERGED | 2026-04-06 |
| 13 | montauk_821 | 0.454x | 32.0% | 59.4% | 0.539 | 0.3192 | CONVERGED | 2026-04-04 |
| 14 | dual_momentum | 0.397x | 31.0% | 45.5% | 0.681 | 0.3065 | CONVERGED | 2026-04-06 |
| 15 | montauk_821 | 0.357x | 30.2% | 59.4% | 0.509 | 0.2513 | CONVERGED | 2026-04-04 |
| 16 | vol_regime | 0.311x | 29.2% | 47.8% | 0.610 | 0.2368 | CONVERGED | 2026-04-06 |
| 17 | ichimoku_trend | 0.169x | 24.7% | 29.6% | 0.834 | 0.1180 | CONVERGED | 2026-04-06 |
| 18 | mean_revert_channel | 0.151x | 23.9% | 44.5% | 0.537 | 0.1178 | CONVERGED | 2026-04-06 |
| 19 | golden_cross | 0.159x | 24.2% | 75.1% | 0.323 | 0.0994 | CONVERGED | 2026-04-04 |
| 20 | golden_cross | 0.155x | 24.0% | 75.1% | 0.320 | 0.0965 | CONVERGED | 2026-04-04 |

## Session Stats

- New unique configs tested: 1,710
- Configs reused from cache: 2,070
- Total configs in history: 666,040
- Population seeded with 1 historical winners per strategy
