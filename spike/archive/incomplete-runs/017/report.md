# Spike Report — Run 017 (2026-04-10)

**Run:** 0.0h | 603 evals | 123 generations | 1 strategies

## Validation Summary

- Raw candidates: 1
- Pre-tier3 pass: 0
- Fully validated pass: 0
- Tier3 warns: 0
- Failed validation: 1
- Walk-forward split: 2020-01-01 | Tier3 budget: 0.5m @ pop 12
- Champion: none - no entry passed full validation

## Validated Top 10

*No entries passed full validation. See raw results below.*

## Raw Top 10 (Pre-Validation)

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Trades | Params | Fitness |
|---|----------|----|------|--------|-----|--------|--------|--------|---------|
| 1 | rsi_regime | 0.484 | 24.9% | 63.6% | 0.392 | 275.443x | 36 | 5 | 64.6486 |

## Top 3 — Details

### #1: rsi_regime

**Fitness:** 64.6486 | **Regime Score:** 0.484 (bull=0.529, bear=0.440) | **HHI:** 0.200

**CAGR:** 24.9% | **Max DD:** 63.6% | **MAR:** 0.392 | **vs B&H:** 275.443x | **Params:** 5

**Parameters:**
```json
{
  "rsi_len": 11,
  "trend_len": 50,
  "entry_rsi": 40,
  "exit_rsi": 75,
  "panic_rsi": 15
}
```

**Trades:** 36 total (1.3/yr) | **Win rate:** 83.3%

**Exit reasons:** R: 36

| Entry | Exit | PnL | Reason |
|-------|------|-----|--------|
| 1999-02-18 | 1999-07-09 | +77.7% | R |
| 1999-07-27 | 1999-11-16 | +35.5% | R |
| 2000-01-07 | 2000-03-27 | +89.0% | R |
| 2002-12-16 | 2003-09-02 | +44.2% | R |
| 2003-09-29 | 2004-01-06 | +40.4% | R |
| 2004-02-06 | 2004-11-05 | -14.7% | R |
| 2004-12-21 | 2005-05-23 | -15.7% | R |
| 2005-06-28 | 2005-07-14 | +14.6% | R |
| 2005-08-29 | 2005-11-17 | +9.1% | R |
| 2005-12-23 | 2006-08-29 | -8.8% | R |
| ... | +26 more | | |

## vs Previous Best

- **Previous best:** rsi_regime (fitness 66.4727)
- **This run's best:** rsi_regime (fitness 64.6486)
- No improvement (-2.7%)

## All-Time Leaderboard (Top 20)

| # | Strategy | RS | CAGR | Max DD | MAR | vs B&H | Fitness | Status | Date |
|---|----------|----|------|--------|-----|--------|---------|--------|------|
| 1 | rsi_regime | 0.484 | 24.9% | 63.6% | 0.392 | 283.215x | 66.4727 | active | 2026-04-09 |
| 2 | breakout | 0.616 | 15.5% | 65.6% | 0.236 | 33.448x | 12.5122 | active | 2026-04-09 |
| 3 | montauk_821 | 0.403 | 16.7% | 66.1% | 0.254 | 44.721x | 10.2324 | active | 2026-04-09 |
| 4 | ichimoku_trend | 0.573 | 12.2% | 55.7% | 0.218 | 14.995x | 6.3913 | active | 2026-04-09 |
| 5 | slope_persistence | 0.558 | 12.6% | 63.4% | 0.199 | 16.854x | 6.2371 | active | 2026-04-09 |
| 6 | momentum_stayer | 0.528 | 15.5% | 58.0% | 0.268 | 33.664x | 6.2248 | active | 2026-04-09 |
| 7 | vix_trend_regime | 0.554 | 14.0% | 58.2% | 0.240 | 23.280x | 5.5885 | active | 2026-04-09 |
| 8 | donchian_turtle | 0.485 | 15.8% | 72.4% | 0.218 | 35.801x | 5.4162 | active | 2026-04-09 |
| 9 | rsi_regime_trail | 0.539 | 12.2% | 54.5% | 0.223 | 15.003x | 4.7587 | active | 2026-04-09 |
| 10 | rsi_vol_regime | 0.463 | 12.7% | 30.6% | 0.415 | 17.115x | 4.2875 | active | 2026-04-09 |
| 11 | dual_momentum | 0.562 | 11.7% | 62.2% | 0.188 | 13.373x | 3.8012 | active | 2026-04-09 |
| 12 | vol_regime | 0.582 | 12.5% | 66.3% | 0.188 | 16.127x | 2.7078 | active | 2026-04-09 |
| 13 | trough_bounce | 0.392 | 11.6% | 69.2% | 0.168 | 13.171x | 1.4258 | active | 2026-04-09 |
| 14 | keltner_squeeze | 0.541 | 7.7% | 51.1% | 0.151 | 4.962x | 1.2966 | active | 2026-04-09 |
| 15 | vix_mean_revert | 0.479 | 6.4% | 60.9% | 0.105 | 3.545x | 0.6491 | active | 2026-04-09 |
| 16 | always_in_trend | 0.564 | 4.2% | 75.7% | 0.056 | 2.022x | 0.5811 | active | 2026-04-09 |
| 17 | ichimoku_trend | 0.699 | 14.0% | 36.9% | 0.381 | 0.036x | 0.5696 | active | 2026-04-08 |
| 18 | vol_regime | 0.686 | 14.2% | 37.5% | 0.378 | 0.037x | 0.5578 | active | 2026-04-08 |
| 19 | montauk_821 | 0.691 | 20.1% | 39.5% | 0.509 | 0.089x | 0.5546 | active | 2026-04-08 |
| 20 | ichimoku_trend | 0.666 | 16.1% | 33.4% | 0.481 | 0.049x | 0.5544 | active | 2026-04-07 |

## Session Stats

- New unique configs tested: 603
- Configs reused from cache: 4,317
- Total configs in history: 65,483
- Population seeded with 1 historical winners per strategy
