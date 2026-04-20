# Spike Report — Run 039 (2026-04-15)

**Run:** 0.0h | 1,839 evals | 1 generations | 20 strategies

## Validation Summary

- Raw candidates: 20
- Pre-tier3 pass: 18
- Fully validated pass: 11
- Tier3 warns: 3
- Failed validation: 6
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: gc_strict_vix (fitness 16.0205, composite 0.839)
- Trade ledger: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/trade_ledger.json
- Signal series: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/signal_series.json
- Equity curve: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/equity_curve.json
- Validation summary: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/validation_summary.json
- Dashboard data: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/dashboard_data.json
- Overlay report: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/039/overlay_report.json

## Validated Top 10

| # | Strategy | Tier | Share Mult. | Marker | RS | CAGR | Max DD | MAR | Trades | Params | Fitness |
|---|----------|------|-------------|--------|----|------|--------|-----|--------|--------|---------|
| 1 | gc_strict_vix | T1 | 44.374x| 0.543 | 0.509 | 29.7% | 68.2% | 0.435 | 23 | 4 | 16.0205 |
| 2 | gc_pre_vix | T1 | 42.620x| 0.544 | 0.511 | 29.5% | 68.2% | 0.433 | 24 | 4 | 15.4123 |
| 3 | gc_precross_strict | T1 | 44.050x| 0.598 | 0.521 | 29.6% | 75.1% | 0.395 | 19 | 4 | 13.9503 |
| 4 | gc_precross_roc | T1 | 44.438x| 0.555 | 0.513 | 29.7% | 82.3% | 0.361 | 25 | 4 | 11.7243 |
| 5 | gc_precross | T1 | 35.745x| 0.426 | 0.519 | 28.8% | 78.9% | 0.366 | 40 | 4 | 10.3434 |
| 6 | cci_willr_combo | T1 | 10.555x| 0.470 | 0.499 | 24.1% | 65.3% | 0.370 | 34 | 4 | 3.9816 |
| 7 | golden_cross_slope | T1 | 7.806x| 0.465 | 0.495 | 23.0% | 65.3% | 0.352 | 34 | 4 | 2.9339 |
| 8 | cci_regime_trend | T1 | 8.040x| 0.567 | 0.485 | 23.1% | 72.0% | 0.321 | 29 | 4 | 2.6239 |
| 9 | atr_ratio_vix | T1 | 7.332x| 0.536 | 0.449 | 22.8% | 69.8% | 0.326 | 31 | 4 | 2.4080 |
| 10 | gc_spread_momentum | T1 | 5.863x| 0.594 | 0.468 | 21.9% | 71.3% | 0.308 | 25 | 3 | 1.9057 |

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | rsi_vol_regime | T2 | 60.590x| 0.486 | 27.5314 | 17 |
| 1 | gc_strict_vix | T1 | 44.374x| 0.543 | 16.0205 | 23 |
| 2 | gc_pre_vix | T1 | 42.620x| 0.544 | 15.4123 | 24 |
| 3 | gc_precross_strict | T1 | 44.050x| 0.598 | 13.9503 | 19 |
| 4 | gc_precross_roc | T1 | 44.438x| 0.555 | 11.7243 | 25 |
| 5 | gc_precross | T1 | 35.745x| 0.426 | 10.3434 | 40 |
| 7 | momentum_stayer | T2 | 26.000x| 0.665 | 10.2752 | 20 |
| 6 | cci_willr_combo | T1 | 10.555x| 0.470 | 3.9816 | 34 |
| 9 | steady_trend | T2 | 14.683x| 0.514 | 3.8884 | 89 |
| 7 | golden_cross_slope | T1 | 7.806x| 0.465 | 2.9339 | 34 |

## Top 3 — Details

### #1: gc_strict_vix  [`T1`]

**Share Mult. vs B&H:** 44.374x | **Marker alignment:** 0.543 | **Fitness:** 16.0205

**Regime Score:** 0.509 (bull=0.741, bear=0.278) | **HHI:** 0.094 | **Params:** 4

**CAGR:** 29.7% | **Max DD:** 68.2% | **MAR:** 0.435

**Parameters:**
```json
{
  "fast_ema": 100,
  "slow_ema": 150,
  "slope_window": 5,
  "entry_bars": 2
}
```

**Trades:** 23 total (0.7/yr) | **Win rate:** 56.5%

**Validation:** PASS | **Composite:** 0.839 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.112 < 0.40 (informational); 2020_meltup: vs_bah=0.404; 2023_rebound: vs_bah=0.258; QQQ same-param vs_bah=0.277 < 0.50

**Marker detail:** accuracy=0.745 | f1=0.815 | transition_timing=0.112 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 17, V: 6

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-09 | 1998-01-15 | +1175.6% | D |
| 1998-02-05 | 2000-08-04 | +572.5% | D |
| 2000-08-30 | 2000-09-06 | -8.8% | D |
| 2003-06-02 | 2004-07-16 | +22.2% | D |
| 2004-10-08 | 2005-03-11 | +2.5% | D |
| 2005-05-25 | 2006-06-08 | -7.0% | D |
| 2006-08-30 | 2008-01-24 | +14.5% | D |
| 2008-05-07 | 2008-06-11 | -8.6% | D |
| 2009-06-08 | 2010-05-06 | +53.4% | V |
| 2010-09-22 | 2011-08-08 | -5.1% | V |
| ... | +13 more | | |

### #2: gc_pre_vix  [`T1`]

**Share Mult. vs B&H:** 42.620x | **Marker alignment:** 0.544 | **Fitness:** 15.4123

**Regime Score:** 0.511 (bull=0.744, bear=0.277) | **HHI:** 0.094 | **Params:** 4

**CAGR:** 29.5% | **Max DD:** 68.2% | **MAR:** 0.433

**Parameters:**
```json
{
  "fast_ema": 100,
  "slow_ema": 150,
  "slope_window": 3,
  "entry_bars": 2
}
```

**Trades:** 24 total (0.7/yr) | **Win rate:** 50.0%

**Validation:** PASS | **Composite:** 0.871 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.112 < 0.40 (informational); 2020_meltup: vs_bah=0.429; 2023_rebound: vs_bah=0.258; QQQ same-param vs_bah=0.422 < 0.50

**Marker detail:** accuracy=0.747 | f1=0.818 | transition_timing=0.112 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 17, V: 6, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-04 | 1998-01-15 | +1243.2% | D |
| 1998-02-02 | 2000-08-04 | +610.8% | D |
| 2000-08-28 | 2000-09-06 | -10.3% | D |
| 2003-05-30 | 2004-07-16 | +20.3% | D |
| 2004-10-06 | 2005-03-11 | -4.9% | D |
| 2005-05-23 | 2006-06-08 | -6.9% | D |
| 2006-08-30 | 2008-01-24 | +14.5% | D |
| 2008-05-06 | 2008-06-11 | -13.4% | D |
| 2009-06-08 | 2010-05-06 | +53.4% | V |
| 2010-09-21 | 2011-08-08 | -7.4% | V |
| ... | +14 more | | |

### #3: gc_precross_strict  [`T1`]

**Share Mult. vs B&H:** 44.050x | **Marker alignment:** 0.598 | **Fitness:** 13.9503

**Regime Score:** 0.521 (bull=0.762, bear=0.280) | **HHI:** 0.093 | **Params:** 4

**CAGR:** 29.6% | **Max DD:** 75.1% | **MAR:** 0.395

**Parameters:**
```json
{
  "fast_ema": 90,
  "slow_ema": 200,
  "slope_window": 3,
  "entry_bars": 2
}
```

**Trades:** 19 total (0.6/yr) | **Win rate:** 63.2%

**Validation:** PASS | **Composite:** 0.845 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.064 < 0.40 (informational); 2020_meltup: vs_bah=0.288; 2023_rebound: vs_bah=0.322

**Marker detail:** accuracy=0.771 | f1=0.842 | transition_timing=0.064 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 19

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-05 | 2000-09-14 | +12399.8% | D |
| 2003-09-02 | 2004-07-12 | +1.6% | D |
| 2004-10-07 | 2005-03-04 | +1.7% | D |
| 2005-05-23 | 2006-06-12 | -13.1% | D |
| 2006-08-30 | 2008-01-29 | +13.5% | D |
| 2008-05-15 | 2008-06-11 | -17.7% | D |
| 2009-07-20 | 2010-07-01 | -7.6% | D |
| 2010-09-21 | 2011-08-17 | +4.8% | D |
| 2011-10-17 | 2011-11-18 | -7.1% | D |
| 2011-12-07 | 2011-12-13 | -8.0% | D |
| ... | +9 more | | |

## Roth Overlay

- Contribution schedule: first_trading_day_of_month at $625.00/month ($7,500.00/year)
- Risk-off sleeve: SGOV
- Simulation window: 2020-06-01 -> 2026-04-15
- Total contributions: $44,375.00
- Final account value: $68,068.77 (TECL $0.00, SGOV $68,068.77)
- Max drawdown: 48.2% | Sweeps: 3 | Avg cash lag: 29.8 days
- vs TECL DCA: $-43,142.27 (-38.79%) against baseline $111,211.04

## vs Previous Best

- **Previous best:** gc_strict_vix (fitness 17.9653)
- **This run's best:** gc_strict_vix (fitness 16.0205)
- No improvement (-10.8%)

## All-Time Leaderboard (Top 20)

| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|
| 1 | gc_strict_vix | T1 | 49.761x| 0.509 | 29.7% | 68.2% | 0.435 | 17.9653 | CONVERGED | 2026-04-14 |
| 2 | gc_pre_vix | T1 | 47.817x| 0.511 | 29.5% | 68.2% | 0.433 | 17.2920 | CONVERGED | 2026-04-14 |
| 3 | gc_pre_vix | T1 | 45.748x| 0.510 | 29.4% | 68.2% | 0.430 | 16.5369 | CONVERGED | 2026-04-14 |
| 4 | gc_pre_vix | T1 | 45.296x| 0.510 | 29.3% | 68.2% | 0.430 | 16.3735 | CONVERGED | 2026-04-14 |
| 5 | gc_strict_vix | T1 | 41.370x| 0.510 | 29.0% | 68.2% | 0.424 | 14.9451 | CONVERGED | 2026-04-14 |
| 6 | gc_pre_vix | T1 | 48.887x| 0.518 | 29.6% | 78.9% | 0.376 | 14.1318 | CONVERGED | 2026-04-14 |
| 7 | gc_precross_strict | T1 | 44.050x| 0.521 | 29.6% | 75.1% | 0.395 | 13.9503 | 1 flat | 2026-04-15 |
| 8 | gc_precross | T1 | 40.084x| 0.519 | 28.8% | 78.9% | 0.366 | 13.7289 | CONVERGED | 2026-04-14 |
| 9 | gc_pre_vix | T1 | 40.210x| 0.503 | 28.9% | 71.3% | 0.405 | 13.5687 | CONVERGED | 2026-04-14 |
| 10 | gc_pre_vix | T1 | 37.272x| 0.504 | 28.6% | 70.5% | 0.405 | 12.7890 | CONVERGED | 2026-04-14 |
| 11 | gc_strict_vix | T1 | 37.533x| 0.507 | 28.6% | 71.5% | 0.400 | 12.6550 | CONVERGED | 2026-04-14 |
| 12 | gc_precross_strict | T1 | 31.638x| 0.514 | 27.9% | 75.1% | 0.372 | 11.8377 | 1 flat | 2026-04-14 |
| 13 | gc_precross_roc | T1 | 44.438x| 0.513 | 29.7% | 82.3% | 0.361 | 11.7243 | 1 flat | 2026-04-15 |
| 14 | gc_strict_vix | T1 | 42.239x| 0.532 | 29.0% | 82.0% | 0.354 | 11.4529 | CONVERGED | 2026-04-14 |
| 15 | gc_strict_vix | T1 | 33.831x| 0.506 | 28.2% | 71.3% | 0.395 | 11.4514 | CONVERGED | 2026-04-14 |
| 16 | gc_precross | T1 | 30.402x| 0.516 | 27.8% | 75.1% | 0.370 | 11.3754 | CONVERGED | 2026-04-14 |
| 17 | gc_pre_vix | T1 | 32.767x| 0.508 | 28.1% | 71.3% | 0.393 | 11.1050 | CONVERGED | 2026-04-14 |
| 18 | gc_precross_strict | T1 | 34.633x| 0.533 | 28.3% | 82.0% | 0.345 | 10.9672 | 1 flat | 2026-04-14 |
| 19 | gc_precross | T1 | 29.086x| 0.515 | 27.6% | 75.1% | 0.367 | 10.8832 | CONVERGED | 2026-04-14 |
| 20 | gc_strict_vix | T1 | 32.144x| 0.507 | 28.0% | 71.6% | 0.391 | 10.8223 | CONVERGED | 2026-04-14 |

## Session Stats

- New unique configs tested: 1,839
- Configs reused from cache: 921
- Total configs in history: 17,437
- Population seeded with 7 historical winners per strategy
