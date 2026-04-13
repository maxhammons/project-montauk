# Spike Report — Run 031 (2026-04-13)

**Run:** 0.2h | 23,050 evals | 586 generations | 17 strategies

## Validation Summary

- Raw candidates: 17
- Pre-tier3 pass: 10
- Fully validated pass: 1
- Tier3 warns: 2
- Failed validation: 14
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: golden_cross_slope (fitness 0.9692, composite 0.720)
- Candidate Pine: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/031/candidate_strategy.txt
- Overlay report: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/031/overlay_report.json

## Validated Top 10

| # | Strategy | Tier | Share Mult. | Marker | RS | CAGR | Max DD | MAR | Trades | Params | Fitness |
|---|----------|------|-------------|--------|----|------|--------|-----|--------|--------|---------|
| 1 | golden_cross_slope | T0 | 4.041x | 0.587 | 0.655 | 7.2% | 85.1% | 0.084 | 18 | 4 | 0.9692 |

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | rsi_regime | T2 | 263.635x | 0.344 | 61.8771 | 36 |
| 2 | momentum_stayer | T2 | 194.564x | 0.465 | 57.1794 | 52 |
| 3 | montauk_821 | T2 | 250.322x | 0.335 | 49.2269 | 60 |
| 4 | dual_momentum | T2 | 130.868x | 0.484 | 43.1153 | 67 |
| 5 | breakout | T2 | 166.324x | 0.477 | 40.1393 | 28 |
| 6 | ichimoku_trend | T2 | 69.443x | 0.429 | 32.6651 | 89 |
| 7 | rsi_recovery | T2 | 75.810x | 0.425 | 25.1364 | 34 |
| 8 | slope_persistence | T2 | 56.685x | 0.475 | 21.9321 | 73 |
| 9 | ema_regime | T2 | 130.214x | 0.518 | 21.2727 | 24 |
| 10 | rsi_vol_regime | T2 | 49.193x | 0.305 | 20.3070 | 105 |

## Top 3 — Details

### #1: golden_cross_slope  [`T0`]

**Share Mult. vs B&H:** 4.041x | **Marker alignment:** 0.587 | **Fitness:** 0.9692

**Regime Score:** 0.655 (bull=0.440, bear=0.871) | **HHI:** 0.206 | **Params:** 4

**CAGR:** 7.2% | **Max DD:** 85.1% | **MAR:** 0.084

**Parameters:**
```json
{
  "fast_ema": 50,
  "slow_ema": 200,
  "slope_window": 5,
  "entry_bars": 3
}
```

**Trades:** 18 total (0.7/yr) | **Win rate:** 50.0%

**Validation:** PASS | **Composite:** 0.720 | **Pine Eligible:** True
**Soft warnings:** [T0] missed_marker_cycles=13 > 2; [T0] transition_timing=0.026 < 0.50; [T0 demoted] WF 2018-2020: OOS/IS regime ratio 0.68 < 0.75; [T0 demoted] WF 2024-2025: OOS/IS regime ratio 0.60 < 0.75; 2020_meltup: vs_bah=0.209; 2023_rebound: vs_bah=0.396

**Marker detail:** accuracy=0.733 | f1=0.802 | transition_timing=0.026 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** D: 18

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-10-18 | 2000-07-31 | +57.7% | D |
| 2003-10-15 | 2004-05-14 | -9.6% | D |
| 2004-11-18 | 2005-02-18 | -20.6% | D |
| 2005-07-18 | 2005-10-28 | -11.0% | D |
| 2005-11-07 | 2006-05-30 | -11.2% | D |
| 2006-10-03 | 2008-01-17 | +9.3% | D |
| 2009-09-01 | 2010-06-10 | +5.5% | D |
| 2010-10-22 | 2011-06-28 | +7.1% | D |
| 2011-07-07 | 2011-08-09 | -30.4% | D |
| 2012-01-31 | 2012-07-24 | -2.7% | D |
| ... | +8 more | | |

## Roth Overlay

- Contribution schedule: first_trading_day_of_month at $625.00/month ($7,500.00/year)
- Risk-off sleeve: SGOV
- Simulation window: 2020-06-01 -> 2026-04-13
- Total contributions: $44,375.00
- Final account value: $63,199.32 (TECL $0.00, SGOV $63,199.32)
- Max drawdown: 44.8% | Sweeps: 3 | Avg cash lag: 42.1 days
- vs TECL DCA: $-35,972.85 (-36.27%) against baseline $99,172.17

## vs Previous Best

- **Previous best:** golden_cross_slope (fitness 0.9692)
- **This run's best:** golden_cross_slope (fitness 0.9692)
- No change

## All-Time Leaderboard (Top 20)

| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|
| 1 | golden_cross_slope | T0 | 4.041x | 0.655 | 7.2% | 85.1% | 0.084 | 0.9692 | 1 flat | 2026-04-13 |

## Session Stats

- New unique configs tested: 23,050
- Configs reused from cache: 226,000
- Total configs in history: 256,532
- Population seeded with 1 historical winners per strategy
