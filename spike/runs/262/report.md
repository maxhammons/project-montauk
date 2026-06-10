# Spike Report — Run 262 (2026-06-09)

**Run:** 0.0h | 4,164 evals | 32 generations | 20 strategies

## Validation Summary

- Raw candidates: 20
- Pre-tier3 pass: 20
- Fully validated pass: 2
- Tier3 warns: 16
- Failed validation: 2
- Tier3 budget: 0.5m @ pop 12 | N_eff: 12708
- Champion: chimera_v1_2026_05_26 (fitness 1.3827, composite 0.768)
- Trade ledger: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/trade_ledger.json
- Signal series: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/signal_series.json
- Equity curve: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/equity_curve.json
- Validation summary: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/validation_summary.json
- Dashboard data: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/dashboard_data.json
- Overlay report: /Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/262/overlay_report.json

## Validated Top 10

| # | Strategy | Tier | Share Mult. | Marker | RS | CAGR | Max DD | MAR | Trades | Params | Fitness |
|---|----------|------|-------------|--------|----|------|--------|-----|--------|--------|---------|
| 1 | chimera_v1_2026_05_26 | T2 | 35.181x| 0.654 | 0.555 | 29.8% | 65.0% | 0.459 | 19 | 1 | 1.3827 |
| 2 | gc_vjatr_timing_repair | T2 | 20.906x| 0.468 | 0.616 | 27.8% | 98.5% | 0.282 | 41 | 15 | 0.8123 |

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | gc_vjatr_reclaimer_timing | T2 | 197.261x| 0.638 | 1.7881 | 24 |
| 1 | chimera_v1_2026_05_26 | T2 | 35.181x| 0.654 | 1.3827 | 19 |
| 3 | gc_vjatr_reclaimer | T2 | 79.931x| 0.658 | 1.2836 | 20 |
| 4 | gc_vjatr | T1 | 15.899x| 0.683 | 1.1059 | 16 |
| 2 | gc_vjatr_timing_repair | T2 | 20.906x| 0.468 | 0.8123 | 41 |
| 6 | nh_xlk_anchor_trend | T1 | 39.867x| 0.473 | 0.5824 | 66 |
| 7 | nh_dd_scaled_reclaim | T1 | 14.849x| 0.475 | 0.5760 | 164 |
| 8 | gc_vjatr_airbag | T2 | 13.100x| 0.495 | 0.5581 | 26 |
| 9 | gold_hybrid_switchboard | T2 | 27.917x| 0.577 | 0.4198 | 22 |
| 10 | nh_vol_drag_regime | T1 | 4.107x| 0.474 | 0.3765 | 62 |

## Top 3 — Details

### #1: chimera_v1_2026_05_26  [`T2`]

**Share Mult. vs B&H:** 35.181x | **Marker alignment:** 0.654 | **Fitness:** 1.3827

**Regime Score:** 0.555 (bull=0.269, bear=0.842) | **HHI:** 0.087 | **Params:** 1

**CAGR:** 29.8% | **Max DD:** 65.0% | **MAR:** 0.459

**Parameters:**
```json
{
  "members": [
    {
      "display_name": "Dusky Osprey",
      "strategy": "gc_vjatr_reclaimer",
      "params": {
        "fast_ema": 140,
        "slow_ema": 160,
        "slope_window": 1,
        "entry_bars": 2,
        "cooldown": 0,
        "atr_period": 16,
        "atr_look": 50,
        "atr_expand": 2.0,
        "atr_confirm": 3,
        "rsi_len": 14,
        "fast_len": 50,
        "trend_len": 100,
        "vol_short": 20,
        "vol_long": 60,
        "drawdown_lookback": 80,
        "drawdown_pct": 25.0,
        "rsi_reclaim": 45.0,
        "vol_ratio_max": 0.85
      },
      "weight": 3.540446
    },
    {
      "display_name": "Marbled Bonobo",
      "strategy": "gc_vjatr",
      "params": {
        "fast_ema": 140,
        "slow_ema": 160,
        "slope_window": 1,
        "entry_bars": 2,
        "cooldown": 0,
        "atr_period": 7,
        "atr_look": 40,
        "atr_expand": 2.5,
        "atr_confirm": 1
      },
      "weight": 2.51853
    },
    {
      "display_name": "Ivory Hare",
      "strategy": "gc_vjatr_timing_repair",
      "params": {
        "fast_ema": 140,
        "slow_ema": 160,
        "slope_window": 1,
        "entry_bars": 2,
        "cooldown": 0,
        "atr_period": 16,
        "atr_look": 50,
        "atr_expand": 2.0,
        "atr_confirm": 3,
        "repair_len": 30,
        "rsi_len": 7,
        "drawdown_lookback": 40,
        "drawdown_pct": 25.0,
        "repair_slope": 3,
        "rsi_floor": 45.0,
        "vix_ceiling": 50.0
      },
      "weight": 2.551391
    }
  ],
  "threshold": 0.5
}
```

**Trades:** 19 total (0.6/yr) | **Win rate:** 73.7%

**Validation:** PASS | **Composite:** 0.768 | **Status:** Not Gold | **Verified Not Overfit:** False | **Backtest Certified:** False | **Promotion Ready:** True
**Critical warnings:** bootstrap downside probability 0.85 > 0.50; event dependence: covid_crash exclusion collapses edge 81%
**Soft warnings:** [T2] missed_marker_cycles=9 > 5 (informational); [T2] transition_timing=0.184 < 0.30 (informational); concentration: bull_hhi=0.257 bear_hhi=0.128 dom=3.13x; 2021_2022_bear: zero trades (sat out, share_multiple=3.239); QQQ same-param share_multiple=0.441 < 0.50; execution realism: next-open degradation -12.2%

**Marker detail:** accuracy=0.780 | f1=0.834 | transition_timing=0.144 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** COM: 19

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1994-08-11 | 1995-05-26 | +197.9% | COM |
| 1999-03-24 | 2000-01-06 | +136.3% | COM |
| 2003-06-04 | 2004-07-22 | +14.3% | COM |
| 2004-10-07 | 2005-03-02 | +1.3% | COM |
| 2005-05-24 | 2006-06-13 | -15.8% | COM |
| 2006-08-31 | 2007-08-10 | +56.7% | COM |
| 2007-12-12 | 2008-02-04 | -39.2% | COM |
| 2008-05-15 | 2008-06-11 | -17.8% | COM |
| 2009-06-05 | 2010-05-06 | +53.4% | COM |
| 2010-09-22 | 2011-03-15 | +41.1% | COM |
| ... | +9 more | | |

### #2: gc_vjatr_timing_repair  [`T2`]

**Share Mult. vs B&H:** 20.906x | **Marker alignment:** 0.468 | **Fitness:** 0.8123

**Regime Score:** 0.616 (bull=0.636, bear=0.596) | **HHI:** 0.071 | **Params:** 15

**CAGR:** 27.8% | **Max DD:** 98.5% | **MAR:** 0.282

**Parameters:**
```json
{
  "slope_window": 2,
  "drawdown_pct": 25.0,
  "repair_len": 30,
  "rsi_floor": 45.0,
  "entry_bars": 2,
  "fast_ema": 140,
  "vix_ceiling": 50.0,
  "rsi_len": 7,
  "atr_confirm": 3,
  "atr_expand": 2.0,
  "drawdown_lookback": 40,
  "repair_slope": 3,
  "slow_ema": 180,
  "atr_look": 50,
  "atr_period": 14
}
```

**Trades:** 41 total (1.2/yr) | **Win rate:** 65.9%

**Validation:** PASS | **Composite:** 0.828 | **Status:** Not Gold | **Verified Not Overfit:** False | **Backtest Certified:** False | **Promotion Ready:** True
**Critical warnings:** walk-forward: WF 2024-2025: OOS/IS regime ratio 0.60 < 0.65; morris warning: max_swing=0.12 sigma_ratio=3.28; bootstrap downside probability 0.80 > 0.50; TQQQ same-param share_multiple=0.233 < 0.50; TQQQ share_multiple=0.2329 (loses to buy-and-hold)
**Soft warnings:** [T2] missed_marker_cycles=6 > 5 (informational); walk-forward dispersion 0.71 > 0.65; QQQ same-param share_multiple=0.145 < 0.50; event dependence: 2022_bear exclusion collapses edge 68%; PBO 0.24 above the 0.20 acceptance bound

**Marker detail:** accuracy=0.774 | f1=0.848 | transition_timing=0.249 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** A: 19, D: 18, V: 4

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1993-10-12 | 1993-11-15 | +11.9% | A |
| 1994-07-18 | 1995-05-26 | +251.8% | A |
| 1995-07-24 | 1995-07-28 | +4.1% | A |
| 1995-08-22 | 1995-08-23 | -0.1% | A |
| 1995-11-09 | 1996-12-31 | +61.6% | A |
| 1997-06-06 | 1998-08-31 | +28.1% | A |
| 1998-10-19 | 1999-01-12 | +191.3% | A |
| 1999-03-15 | 2000-01-05 | +152.5% | A |
| 2000-01-25 | 2000-01-26 | -9.9% | A |
| 2000-02-23 | 2000-03-14 | +11.9% | A |
| ... | +31 more | | |

## Roth Overlay

- Contribution schedule: first_trading_day_of_month at $625.00/month ($7,500.00/year)
- Risk-off sleeve: SGOV
- Simulation window: 2020-06-01 -> 2026-06-09
- Total contributions: $45,625.00
- Final account value: $297,372.62 (TECL $0.00, SGOV $297,372.62)
- Max drawdown: 35.8% | Sweeps: 3 | Avg cash lag: 54.7 days
- vs TECL DCA: $113,553.07 (+61.77%) against baseline $183,819.55

## vs Previous Best

- **Previous best:** chimera_v1_2026_05_26 (fitness 3.4491)
- **This run's best:** chimera_v1_2026_05_26 (fitness 1.3827)
- No improvement (-59.9%)

## All-Time Leaderboard (Top 20)

| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |
|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|
| 1 | chimera_v1_2026_05_26 | T2 | 33.221x| 0.555 | 28.8% | 65.8% | 0.437 | 3.4491 | Gold Status | 2026-06-09 |
| 2 | gc_vjatr | T2 | 13.853x| 0.542 | 25.2% | 64.7% | 0.390 | 2.6605 | Gold Status | 2026-06-09 |
| 3 | gc_vjatr_reclaimer | T2 | 37.983x| 0.568 | 30.5% | 60.6% | 0.503 | 2.5281 | Gold Status | 2026-06-09 |
| 4 | gc_vjatr_reclaimer | T2 | 37.983x| 0.568 | 30.5% | 60.6% | 0.503 | 2.5281 | Gold Status | 2026-06-09 |
| 5 | gc_vjatr_reclaimer | T2 | 37.983x| 0.568 | 30.5% | 60.6% | 0.503 | 2.5281 | Gold Status | 2026-06-09 |
| 6 | gc_vjatr_reclaimer | T2 | 37.983x| 0.568 | 30.5% | 60.6% | 0.503 | 2.5281 | Gold Status | 2026-06-09 |
| 7 | gc_vjatr | T2 | 15.013x| 0.541 | 25.5% | 64.7% | 0.394 | 2.6928 | Gold Status | 2026-06-09 |
| 8 | gc_vjatr | T2 | 15.013x| 0.541 | 25.5% | 64.7% | 0.394 | 2.6928 | Gold Status | 2026-06-09 |
| 9 | gc_vjatr | T2 | 13.853x| 0.542 | 25.2% | 64.7% | 0.390 | 2.6605 | Gold Status | 2026-06-09 |
| 10 | gc_vjatr_timing_repair | T2 | 9.793x| 0.616 | 24.5% | 98.2% | 0.250 | 2.3667 | Gold Status | 2026-06-09 |
| 11 | gc_vjatr_timing_repair | T2 | 10.315x| 0.615 | 24.7% | 98.2% | 0.252 | 2.3852 | Gold Status | 2026-06-09 |
| 12 | gc_vjatr_timing_repair | T2 | 9.793x| 0.616 | 24.5% | 98.2% | 0.250 | 2.3667 | Gold Status | 2026-06-09 |

## Session Stats

- New unique configs tested: 4,164
- Configs reused from cache: 116,288
- Total configs in history: 12,711
- Population seeded with 4 historical winners per strategy
