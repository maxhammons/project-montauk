# Spike Report — Run 101 (2026-04-21)

**Run:** 0.5h | 16 evals | 4,268,038 generations | 1 strategies

## Validation Summary

- Raw candidates: 1
- Pre-tier3 pass: 1
- Fully validated pass: 0
- Tier3 warns: 1
- Failed validation: 0
- Tier3 budget: 1.5m @ pop 20 | N_eff: 300
- Champion: none - no entry passed full validation
- Trade ledger: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/101/trade_ledger.json
- Signal series: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/101/signal_series.json
- Equity curve: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/101/equity_curve.json
- Validation summary: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/101/validation_summary.json
- Dashboard data: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/101/dashboard_data.json

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | gc_vjatr | T1 | 15.960x| 0.559 | 0.5044 | 24 |

## Top 3 — Details

### #1: gc_vjatr  [`T1`]

**Share Mult. vs B&H:** 15.960x | **Marker alignment:** 0.559 | **Fitness:** 0.5044

**Regime Score:** 0.574 (bull=0.306, bear=0.843) | **HHI:** 0.086 | **Params:** 8

**CAGR:** 26.2% | **Max DD:** 61.0% | **MAR:** 0.430

**Parameters:**
```json
{
  "entry_bars": 2,
  "atr_period": 20,
  "atr_confirm": 3,
  "fast_ema": 100,
  "slope_window": 3,
  "slow_ema": 150,
  "atr_look": 50,
  "atr_expand": 2.0
}
```

**Trades:** 24 total (0.7/yr) | **Win rate:** 54.2%

**Validation:** WARN | **Composite:** 0.584 | **Backtest Certified:** False | **Promotion Ready:** False
**Soft warnings:** [T1] missed_marker_cycles=10 > 3 (informational); [T1] transition_timing=0.135 < 0.40 (informational); 2023_rebound: share_multiple=0.246; QQQ same-param share_multiple=0.454 < 0.50

**Marker detail:** accuracy=0.753 | f1=0.814 | transition_timing=0.135 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** A: 7, D: 12, V: 4, End of Data: 1

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-05 | 1995-05-26 | +232.3% | A |
| 1998-02-04 | 1999-01-13 | +232.8% | A |
| 2000-08-29 | 2000-09-06 | -10.6% | D |
| 2003-05-29 | 2004-07-16 | +25.5% | D |
| 2004-10-07 | 2005-03-11 | -1.8% | D |
| 2005-05-24 | 2006-06-08 | -8.2% | D |
| 2006-08-29 | 2007-08-13 | +67.7% | A |
| 2008-05-06 | 2008-06-11 | -13.4% | D |
| 2009-06-03 | 2010-05-06 | +62.1% | V |
| 2010-09-21 | 2011-08-08 | -7.4% | V |
| ... | +14 more | | |

## vs Previous Best

- **Previous best:** breakout (fitness 63.7344)
- **This run's best:** gc_vjatr (fitness 0.5044)
- No improvement (-99.2%)

## All-Time Leaderboard (Top 20)

| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|
| 1 | breakout | T2 | 63.734x| 0.644 | 31.4% | 77.8% | 0.403 | 63.7344 | 1 flat | 2026-04-21 |
| 2 | gc_vjatr | T1 | 13.322x| 0.546 | 25.3% | 51.2% | 0.493 | 0.8624 | CONVERGED | 2026-04-21 |
| 3 | gc_vjatr | T1 | 7.604x| 0.555 | 23.1% | 58.9% | 0.393 | 0.6100 | CONVERGED | 2026-04-21 |
| 4 | slope_persistence | T2 | 20.205x| 0.574 | 26.9% | 86.4% | 0.311 | 20.2052 | 1 flat | 2026-04-21 |
| 5 | gc_vjatr | T1 | 7.640x| 0.547 | 23.2% | 54.4% | 0.425 | 0.5871 | CONVERGED | 2026-04-21 |
| 6 | gc_vjatr | T1 | 6.771x| 0.547 | 22.7% | 54.4% | 0.417 | 0.5766 | CONVERGED | 2026-04-21 |
| 7 | gc_vjatr | T1 | 2.887x| 0.515 | 19.6% | 49.1% | 0.399 | 0.7716 | CONVERGED | 2026-04-21 |
| 8 | gc_n8_timelimit | T1 | 7.775x| 0.507 | 23.2% | 49.9% | 0.465 | 0.6211 | active | 2026-04-21 |

## Session Stats

- New unique configs tested: 16
- Configs reused from cache: 341,443,024
- Total configs in history: 19,660
- Population seeded with 5 historical winners per strategy
