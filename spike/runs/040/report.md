# Spike Report — Run 040 (2026-04-15)

**Run:** 0.5h | 54,583 evals | 438 generations | 20 strategies

## Validation Summary

- Raw candidates: 20
- Pre-tier3 pass: 16
- Fully validated pass: 11
- Tier3 warns: 1
- Failed validation: 8
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: gc_strict_vix (fitness 28.0807, composite 0.833)
- Trade ledger: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/trade_ledger.json
- Signal series: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/signal_series.json
- Equity curve: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/equity_curve.json
- Validation summary: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/validation_summary.json
- Dashboard data: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/dashboard_data.json
- Overlay report: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/040/overlay_report.json

## Validated Top 10

| # | Strategy | Tier | Share Mult. | Marker | RS | CAGR | Max DD | MAR | Trades | Params | Fitness |
|---|----------|------|-------------|--------|----|------|--------|-----|--------|--------|---------|
| 1 | gc_strict_vix | T1 | 77.287x| 0.587 | 0.515 | 32.1% | 68.2% | 0.471 | 19 | 4 | 28.0807 |
| 2 | gc_pre_vix | T1 | 70.551x| 0.583 | 0.515 | 31.8% | 68.2% | 0.465 | 19 | 4 | 25.6359 |
| 3 | gc_precross_roc | T1 | 85.856x| 0.625 | 0.518 | 32.5% | 80.2% | 0.406 | 19 | 4 | 24.0261 |
| 4 | gc_precross_strict | T1 | 50.708x| 0.598 | 0.521 | 30.4% | 75.1% | 0.405 | 19 | 4 | 16.0589 |
| 5 | gc_precross | T1 | 46.428x| 0.608 | 0.521 | 30.1% | 75.1% | 0.401 | 18 | 4 | 14.7093 |
| 6 | atr_ratio_vix | T1 | 18.195x| 0.543 | 0.472 | 26.4% | 61.8% | 0.428 | 30 | 4 | 7.1016 |
| 7 | atr_ratio_trend | T1 | 15.156x| 0.543 | 0.473 | 25.8% | 65.3% | 0.394 | 30 | 4 | 5.5655 |
| 8 | gc_asym_triple | T1 | 13.603x| 0.524 | 0.499 | 25.3% | 65.3% | 0.388 | 31 | 4 | 5.1320 |
| 9 | cci_regime_trend | T1 | 10.883x| 0.502 | 0.496 | 24.5% | 65.3% | 0.375 | 32 | 4 | 4.0945 |
| 10 | gc_asym_fast_entry | T1 | 11.732x| 0.520 | 0.484 | 24.8% | 68.7% | 0.361 | 31 | 6 | 4.0856 |

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | rsi_vol_regime | T2 | 109.392x| 0.523 | 49.8336 | 18 |
| 2 | momentum_stayer | T2 | 75.000x| 0.644 | 32.9725 | 22 |
| 1 | gc_strict_vix | T1 | 77.287x| 0.587 | 28.0807 | 19 |
| 2 | gc_pre_vix | T1 | 70.551x| 0.583 | 25.6359 | 19 |
| 3 | gc_precross_roc | T1 | 85.856x| 0.625 | 24.0261 | 19 |
| 6 | breakout | T2 | 63.734x| 0.520 | 21.3374 | 146 |
| 4 | gc_precross_strict | T1 | 50.708x| 0.598 | 16.0589 | 19 |
| 5 | gc_precross | T1 | 46.428x| 0.608 | 14.7093 | 18 |
| 9 | rsi_regime | T2 | 36.268x| 0.356 | 9.6877 | 41 |
| 10 | dual_momentum | T2 | 13.517x| 0.424 | 7.8850 | 77 |

## Top 3 — Details

### #1: gc_strict_vix  [`T1`]

**Share Mult. vs B&H:** 77.287x | **Marker alignment:** 0.587 | **Fitness:** 28.0807

**Regime Score:** 0.515 (bull=0.750, bear=0.280) | **HHI:** 0.094 | **Params:** 4

**CAGR:** 32.1% | **Max DD:** 68.2% | **MAR:** 0.471

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

**Validation:** PASS | **Composite:** 0.833 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.102 < 0.40 (informational); 2020_meltup: vs_bah=0.410; 2023_rebound: vs_bah=0.322; QQQ same-param vs_bah=0.459 < 0.50

**Marker detail:** accuracy=0.729 | f1=0.803 | transition_timing=0.102 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 12, V: 6, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-05 | 2000-09-14 | +12399.5% | D |
| 2003-09-02 | 2004-07-12 | +1.6% | D |
| 2004-10-07 | 2005-03-04 | +1.7% | D |
| 2005-05-23 | 2006-06-12 | -13.1% | D |
| 2006-08-30 | 2008-01-29 | +13.5% | D |
| 2008-05-15 | 2008-06-11 | -17.7% | D |
| 2009-07-17 | 2010-05-06 | +32.2% | V |
| 2010-09-21 | 2011-08-08 | -7.4% | V |
| 2011-10-17 | 2011-11-18 | -7.1% | D |
| 2011-12-07 | 2011-12-13 | -8.0% | D |
| ... | +9 more | | |

### #2: gc_pre_vix  [`T1`]

**Share Mult. vs B&H:** 70.551x | **Marker alignment:** 0.583 | **Fitness:** 25.6359

**Regime Score:** 0.515 (bull=0.751, bear=0.280) | **HHI:** 0.093 | **Params:** 4

**CAGR:** 31.8% | **Max DD:** 68.2% | **MAR:** 0.465

**Parameters:**
```json
{
  "fast_ema": 90,
  "slope_window": 3,
  "entry_bars": 2,
  "slow_ema": 200
}
```

**Trades:** 19 total (0.6/yr) | **Win rate:** 57.9%

**Validation:** PASS | **Composite:** 0.838 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=11 > 3 (informational); [T1] transition_timing=0.093 < 0.40 (informational); 2020_meltup: vs_bah=0.407; 2023_rebound: vs_bah=0.325; QQQ same-param vs_bah=0.458 < 0.50

**Marker detail:** accuracy=0.725 | f1=0.800 | transition_timing=0.093 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 12, V: 6, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-03 | 2000-09-14 | +12198.1% | D |
| 2003-09-03 | 2004-07-12 | -1.5% | D |
| 2004-10-07 | 2005-03-04 | +1.7% | D |
| 2005-05-24 | 2006-06-12 | -14.4% | D |
| 2006-08-31 | 2008-01-29 | +14.8% | D |
| 2008-05-16 | 2008-06-11 | -17.1% | D |
| 2009-07-20 | 2010-05-06 | +28.2% | V |
| 2010-09-22 | 2011-08-08 | -5.1% | V |
| 2011-10-17 | 2011-11-18 | -7.1% | D |
| 2011-12-07 | 2011-12-13 | -8.0% | D |
| ... | +9 more | | |

### #3: gc_precross_roc  [`T1`]

**Share Mult. vs B&H:** 85.856x | **Marker alignment:** 0.625 | **Fitness:** 24.0261

**Regime Score:** 0.518 (bull=0.767, bear=0.269) | **HHI:** 0.094 | **Params:** 4

**CAGR:** 32.5% | **Max DD:** 80.2% | **MAR:** 0.406

**Parameters:**
```json
{
  "roc_len": 10,
  "fast_ema": 100,
  "slope_window": 3,
  "slow_ema": 200
}
```

**Trades:** 19 total (0.6/yr) | **Win rate:** 63.2%

**Validation:** PASS | **Composite:** 0.864 | **Backtest Certified:** False | **Promotion Ready:** True
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.092 < 0.40 (informational); 2020_meltup: vs_bah=0.268; 2023_rebound: vs_bah=0.318

**Marker detail:** accuracy=0.816 | f1=0.878 | transition_timing=0.092 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 18, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-02 | 2000-09-19 | +12141.1% | D |
| 2002-11-22 | 2004-07-14 | +12.0% | D |
| 2004-10-04 | 2005-03-08 | +2.2% | D |
| 2005-05-19 | 2006-06-13 | -11.5% | D |
| 2006-08-17 | 2008-01-31 | +23.7% | D |
| 2008-05-01 | 2008-06-11 | -11.6% | D |
| 2009-04-17 | 2010-07-06 | +43.0% | D |
| 2010-09-16 | 2011-08-18 | -6.5% | D |
| 2011-10-13 | 2011-11-18 | -6.2% | D |
| 2011-12-02 | 2011-12-13 | -4.2% | D |
| ... | +9 more | | |

## Roth Overlay

- Contribution schedule: first_trading_day_of_month at $625.00/month ($7,500.00/year)
- Risk-off sleeve: SGOV
- Simulation window: 2020-06-01 -> 2026-04-15
- Total contributions: $44,375.00
- Final account value: $111,607.22 (TECL $0.00, SGOV $111,607.22)
- Max drawdown: 48.3% | Sweeps: 2 | Avg cash lag: 38.4 days
- vs TECL DCA: $396.18 (+0.36%) against baseline $111,211.04

## vs Previous Best

- **Previous best:** gc_strict_vix (fitness 17.9653)
- **This run's best:** gc_strict_vix (fitness 28.0807)
- **Improved by +56.3%**

## All-Time Leaderboard (Top 20)

| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|
| 1 | gc_strict_vix | T1 | 77.287x| 0.515 | 32.1% | 68.2% | 0.471 | 28.0807 | active | 2026-04-15 |
| 2 | gc_pre_vix | T1 | 70.551x| 0.515 | 31.8% | 68.2% | 0.465 | 25.6359 | active | 2026-04-15 |
| 3 | gc_precross_roc | T1 | 85.856x| 0.518 | 32.5% | 80.2% | 0.406 | 24.0261 | active | 2026-04-15 |
| 4 | gc_strict_vix | T1 | 49.761x| 0.509 | 29.7% | 68.2% | 0.435 | 17.9653 | active | 2026-04-14 |
| 5 | gc_pre_vix | T1 | 47.817x| 0.511 | 29.5% | 68.2% | 0.433 | 17.2920 | active | 2026-04-14 |
| 6 | gc_pre_vix | T1 | 45.748x| 0.510 | 29.4% | 68.2% | 0.430 | 16.5369 | active | 2026-04-14 |
| 7 | gc_pre_vix | T1 | 45.296x| 0.510 | 29.3% | 68.2% | 0.430 | 16.3735 | active | 2026-04-14 |
| 8 | gc_precross_strict | T1 | 50.708x| 0.521 | 30.4% | 75.1% | 0.405 | 16.0589 | active | 2026-04-15 |
| 9 | gc_strict_vix | T1 | 41.370x| 0.510 | 29.0% | 68.2% | 0.424 | 14.9451 | active | 2026-04-14 |
| 10 | gc_precross | T1 | 46.428x| 0.521 | 30.1% | 75.1% | 0.401 | 14.7093 | active | 2026-04-15 |
| 11 | gc_pre_vix | T1 | 48.887x| 0.518 | 29.6% | 78.9% | 0.376 | 14.1318 | active | 2026-04-14 |
| 12 | gc_precross_strict | T1 | 44.050x| 0.521 | 29.6% | 75.1% | 0.395 | 13.9503 | active | 2026-04-15 |
| 13 | gc_precross | T1 | 40.084x| 0.519 | 28.8% | 78.9% | 0.366 | 13.7289 | active | 2026-04-14 |
| 14 | gc_pre_vix | T1 | 40.210x| 0.503 | 28.9% | 71.3% | 0.405 | 13.5687 | active | 2026-04-14 |
| 15 | gc_pre_vix | T1 | 37.272x| 0.504 | 28.6% | 70.5% | 0.405 | 12.7890 | active | 2026-04-14 |
| 16 | gc_strict_vix | T1 | 37.533x| 0.507 | 28.6% | 71.5% | 0.400 | 12.6550 | active | 2026-04-14 |
| 17 | gc_precross_strict | T1 | 31.638x| 0.514 | 27.9% | 75.1% | 0.372 | 11.8377 | active | 2026-04-14 |
| 18 | gc_precross_roc | T1 | 44.438x| 0.513 | 29.7% | 82.3% | 0.361 | 11.7243 | active | 2026-04-15 |
| 19 | gc_strict_vix | T1 | 42.239x| 0.532 | 29.0% | 82.0% | 0.354 | 11.4529 | active | 2026-04-14 |
| 20 | gc_strict_vix | T1 | 33.831x| 0.506 | 28.2% | 71.3% | 0.395 | 11.4514 | active | 2026-04-14 |

## Session Stats

- New unique configs tested: 54,583
- Configs reused from cache: 1,154,297
- Total configs in history: 75,062
- Population seeded with 7 historical winners per strategy
