# Spike Report — 2026-04-07

**Run:** 0.0h | 6,548 evals | 20 generations | 13 strategies

## Top 10

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Trades | Params | Fitness |
|---|----------|----|------|--------|-----|--------|--------|--------|---------|
| 1 | ichimoku_trend | 0.666 | 16.1% | 33.4% | 0.481 | 0.049x | 48 | 6 | 0.5544 |
| 2 | vol_regime | 0.694 | 17.2% | 41.5% | 0.415 | 0.058x | 39 | 6 | 0.5498 |
| 3 | montauk_821 | 0.681 | 17.9% | 40.2% | 0.446 | 0.065x | 50 | 10 | 0.5438 |
| 4 | dual_momentum | 0.685 | 17.8% | 41.8% | 0.426 | 0.064x | 46 | 9 | 0.5415 |
| 5 | breakout | 0.680 | 20.3% | 45.0% | 0.451 | 0.091x | 40 | 5 | 0.5268 |
| 6 | williams_midline_reclaim | 0.553 | 9.4% | 22.9% | 0.409 | 0.018x | 50 | 10 | 0.4894 |
| 7 | rsi_vol_regime | 0.514 | 16.2% | 28.2% | 0.576 | 0.050x | 52 | 9 | 0.4414 |
| 8 | rsi_regime_trail | 0.590 | 12.2% | 53.1% | 0.229 | 0.027x | 38 | 7 | 0.4331 |
| 9 | mean_revert_channel | 0.474 | 0.1% | 35.9% | 0.002 | 0.004x | 12 | 6 | 0.3888 |
| 10 | accumulation_breakout | 0.520 | -1.9% | 43.4% | -0.045 | 0.003x | 50 | 11 | 0.3763 |

## Top 3 — Details

### #1: ichimoku_trend

**Fitness:** 0.5544 | **Regime Score:** 0.666 (bull=0.444, bear=0.888) | **HHI:** 0.045

**CAGR:** 16.1% | **Max DD:** 33.4% | **MAR:** 0.481 | **vs B&H:** 0.049x | **Params:** 6

**Parameters:**
```json
{
  "kijun_len": 35,
  "cloud_len": 30,
  "atr_period": 30,
  "atr_mult": 3.5,
  "tenkan_len": 11,
  "cloud_buffer": 2.0
}
```

**Trades:** 48 total (2.8/yr) | **Win rate:** 45.8%

**Exit reasons:** B: 44, T: 2, A: 2

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-03-26 | 2009-05-13 | +7.8% | B |
| 2009-07-23 | 2009-10-01 | +8.1% | B |
| 2009-12-24 | 2010-01-22 | -16.1% | T |
| 2010-03-09 | 2010-05-04 | +4.2% | B |
| 2010-07-23 | 2010-08-11 | -11.3% | B |
| 2010-09-17 | 2010-11-16 | +18.9% | B |
| 2011-04-27 | 2011-05-16 | -8.7% | B |
| 2011-07-07 | 2011-08-01 | -8.3% | B |
| 2011-10-19 | 2011-11-17 | -0.1% | B |
| 2012-01-09 | 2012-04-16 | +48.3% | B |
| ... | +38 more | | |

### #2: vol_regime

**Fitness:** 0.5498 | **Regime Score:** 0.694 (bull=0.535, bear=0.853) | **HHI:** 0.043

**CAGR:** 17.2% | **Max DD:** 41.5% | **MAR:** 0.415 | **vs B&H:** 0.058x | **Params:** 6

**Parameters:**
```json
{
  "vol_exit_ratio": 1.4,
  "trend_len": 50,
  "vol_long": 90,
  "vol_short": 25,
  "trend_buffer": 3.0,
  "vol_entry_ratio": 0.8
}
```

**Trades:** 39 total (2.3/yr) | **Win rate:** 53.8%

**Exit reasons:** B: 34, V: 5

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-07-28 | 2009-11-20 | +15.2% | B |
| 2009-12-29 | 2010-01-22 | -16.1% | B |
| 2010-03-08 | 2010-05-05 | +3.1% | B |
| 2010-09-16 | 2011-03-10 | +49.9% | B |
| 2012-01-06 | 2012-04-23 | +42.3% | B |
| 2012-08-14 | 2012-10-09 | +0.6% | B |
| 2013-02-07 | 2013-04-17 | -0.1% | B |
| 2013-05-23 | 2013-06-20 | -9.0% | B |
| 2013-07-30 | 2013-08-27 | -5.1% | B |
| 2013-10-02 | 2013-10-08 | -7.8% | B |
| ... | +29 more | | |

### #3: montauk_821

**Fitness:** 0.5438 | **Regime Score:** 0.681 (bull=0.647, bear=0.714) | **HHI:** 0.042

**CAGR:** 17.9% | **Max DD:** 40.2% | **MAR:** 0.446 | **vs B&H:** 0.065x | **Params:** 10

**Parameters:**
```json
{
  "slope_lookback": 12,
  "quick_thresh": -4.0,
  "atr_period": 35,
  "quick_lookback": 3,
  "sell_buffer": 0.0,
  "trend_ema": 80,
  "short_ema": 17,
  "med_ema": 28,
  "atr_mult": 4.0,
  "quick_ema": 14
}
```

**Trades:** 50 total (2.9/yr) | **Win rate:** 42.0%

**Exit reasons:** Q: 16, E: 32, A: 2

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 2009-02-10 | 2009-02-19 | -17.7% | Q |
| 2009-03-24 | 2009-11-24 | +152.7% | Q |
| 2009-12-22 | 2010-01-25 | -11.5% | Q |
| 2010-03-08 | 2010-05-06 | -7.6% | Q |
| 2010-09-22 | 2011-03-09 | +56.1% | E |
| 2011-04-29 | 2011-05-23 | -11.8% | E |
| 2011-07-14 | 2011-08-04 | -14.8% | Q |
| 2011-10-19 | 2011-11-22 | -9.5% | Q |
| 2012-01-10 | 2012-04-24 | +37.9% | E |
| 2012-08-08 | 2012-10-11 | -0.1% | E |
| ... | +40 more | | |

## vs Previous Best

- **Previous best:** ichimoku_trend (fitness 0.5544)
- **This run's best:** ichimoku_trend (fitness 0.5544)
- No improvement (-0.0%)

## All-Time Leaderboard (Top 20)

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Fitness | Status | Date |
|---|----------|----|------|--------|-----|--------|---------|--------|------|
| 1 | ichimoku_trend | 0.666 | 16.1% | 33.4% | 0.481 | 0.049x | 0.5544 | active | 2026-04-07 |
| 2 | vol_regime | 0.694 | 17.2% | 41.5% | 0.415 | 0.058x | 0.5498 | active | 2026-04-07 |
| 3 | montauk_821 | 0.681 | 17.9% | 40.2% | 0.446 | 0.065x | 0.5438 | active | 2026-04-07 |
| 4 | montauk_821 | 0.686 | 19.8% | 41.9% | 0.471 | 0.085x | 0.5423 | active | 2026-04-07 |
| 5 | dual_momentum | 0.685 | 17.8% | 41.8% | 0.426 | 0.064x | 0.5415 | active | 2026-04-07 |
| 6 | breakout | 0.680 | 20.3% | 45.0% | 0.451 | 0.091x | 0.5268 | active | 2026-04-07 |
| 7 | williams_midline_reclaim | 0.553 | 9.4% | 22.9% | 0.409 | 0.018x | 0.4894 | active | 2026-04-07 |
| 8 | rsi_vol_regime | 0.514 | 16.2% | 28.2% | 0.576 | 0.050x | 0.4414 | active | 2026-04-07 |
| 9 | rsi_regime_trail | 0.590 | 12.2% | 53.1% | 0.229 | 0.027x | 0.4331 | active | 2026-04-07 |
| 10 | mean_revert_channel | 0.474 | 0.1% | 35.9% | 0.002 | 0.004x | 0.3888 | active | 2026-04-07 |
| 11 | accumulation_breakout | 0.520 | -1.9% | 43.4% | -0.045 | 0.003x | 0.3763 | active | 2026-04-07 |
| 12 | stoch_drawdown_recovery | 0.477 | 17.1% | 46.1% | 0.370 | 0.057x | 0.3609 | active | 2026-04-07 |
| 13 | rsi_regime | 0.531 | 27.3% | 65.8% | 0.415 | 0.242x | 0.3562 | active | 2026-04-07 |
| 14 | regime_score | 0.458 | 18.2% | 71.7% | 0.254 | 0.067x | 0.2936 | active | 2026-04-07 |

## Session Stats

- New unique configs tested: 6,548
- Configs reused from cache: 6,252
- Total configs in history: 926,577
- Population seeded with 1 historical winners per strategy
