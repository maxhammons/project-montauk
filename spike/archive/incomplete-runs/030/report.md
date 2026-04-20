# Spike Report — Run 030 (2026-04-13)

**Run:** 0.1h | 5,652 evals | 100,453 generations | 2 strategies

## Validation Summary

- Raw candidates: 2
- Pre-tier3 pass: 2
- Fully validated pass: 0
- Tier3 warns: 0
- Failed validation: 2
- Tier3 budget: 0.5m @ pop 12 | N_eff: 300
- Champion: none - no entry passed full validation

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Discovery Top 10 (Pre-Validation)

| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |
|---|----------|------|-------------|--------|---------|--------|
| 1 | ema_regime | T2 | 130.214x | 0.518 | 21.2727 | 24 |
| 2 | steady_trend | T2 | 55.302x | 0.460 | 16.6311 | 38 |

## Top 3 — Details

### #1: ema_regime  [`T2`]

**Share Mult. vs B&H:** 130.214x | **Marker alignment:** 0.518 | **Fitness:** 21.2727

**Regime Score:** 0.566 (bull=0.603, bear=0.530) | **HHI:** 0.209 | **Params:** 4

**CAGR:** 21.7% | **Max DD:** 75.1% | **MAR:** 0.289

**Parameters:**
```json
{
  "exit_confirm": 8,
  "entry_confirm": 2,
  "slow_ema": 80,
  "fast_ema": 40
}
```

**Trades:** 24 total (0.9/yr) | **Win rate:** 50.0%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Soft warnings:** trades_per_param=6.00 in soft-warning band; [T2] transition_timing=0.088 < 0.30; composite_confidence=0.000 < 0.70
**Hard fails:** [T2] missed_marker_cycles=11 > 2

**Marker detail:** accuracy=0.784 | f1=0.842 | transition_timing=0.088 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** X: 24

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-04-20 | 2000-05-16 | +133.1% | X |
| 2003-05-09 | 2004-04-01 | +72.1% | X |
| 2004-11-03 | 2005-02-08 | -1.2% | X |
| 2005-06-10 | 2005-10-21 | -1.8% | X |
| 2005-11-14 | 2006-05-25 | -10.1% | X |
| 2006-09-14 | 2007-12-12 | +75.8% | X |
| 2007-12-14 | 2008-01-11 | -26.4% | X |
| 2008-05-21 | 2008-07-03 | -24.7% | X |
| 2009-05-08 | 2010-02-19 | +90.9% | X |
| 2010-03-11 | 2010-06-03 | -13.5% | X |
| ... | +14 more | | |

### #2: steady_trend  [`T2`]

**Share Mult. vs B&H:** 55.302x | **Marker alignment:** 0.460 | **Fitness:** 16.6311

**Regime Score:** 0.507 (bull=0.479, bear=0.535) | **HHI:** 0.231 | **Params:** 4

**CAGR:** 18.0% | **Max DD:** 59.8% | **MAR:** 0.300

**Parameters:**
```json
{
  "slope_window": 6,
  "exit_bars": 9,
  "entry_bars": 6,
  "ema_len": 100
}
```

**Trades:** 38 total (1.4/yr) | **Win rate:** 52.6%

**Validation:** FAIL | **Composite:** 0.000 | **Pine Eligible:** True
**Soft warnings:** trades_per_param=9.50 in soft-warning band; [T2] transition_timing=0.218 < 0.30; composite_confidence=0.000 < 0.70
**Hard fails:** [T2] missed_marker_cycles=7 > 2

**Marker detail:** accuracy=0.783 | f1=0.840 | transition_timing=0.218 | window=1999-10-27 -> 2025-10-30

**Exit reasons:** S: 38

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-06-16 | 1999-10-28 | +13.7% | S |
| 1999-11-09 | 2000-04-27 | +63.5% | S |
| 2000-09-05 | 2000-09-20 | -19.4% | S |
| 2003-05-05 | 2004-03-22 | +57.0% | S |
| 2004-04-13 | 2004-04-28 | -7.0% | S |
| 2004-10-27 | 2005-01-21 | -4.1% | S |
| 2005-05-27 | 2005-10-18 | -6.9% | S |
| 2005-11-11 | 2006-05-16 | -7.8% | S |
| 2006-08-29 | 2007-03-15 | +24.7% | S |
| 2007-03-29 | 2007-08-27 | +28.2% | S |
| ... | +28 more | | |

## Session Stats

- New unique configs tested: 5,652
- Configs reused from cache: 4,012,468
- Total configs in history: 233,450
