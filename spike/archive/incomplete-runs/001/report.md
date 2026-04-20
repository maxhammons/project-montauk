# Spike Report — 2026-04-03

## Session Summary
- **Duration:** 20 min (0.33h)
- **Evaluations:** 70,000
- **Generations:** 125
- **Strategies tested:** 14 (7 existing + 7 new added this session)

## All-Time Best (best-ever.json)
| Metric | Value |
|--------|-------|
| Strategy | `rsi_regime` |
| vs B&H | **3.49x** |
| CAGR | 48.6% |
| Max DD | 75.1% |
| Trades/yr | 0.7 |
| Params | rsi_len=10, trend_len=150, entry_rsi=35, exit_rsi=85, panic_rsi=15, cooldown=5 |

## This Session Rankings

| # | Strategy | vs B&H | CAGR | Max DD | Trades/yr | MAR |
|---|----------|--------|------|--------|-----------|-----|
| 1 | `recovery_momentum` ⭐ new | 1.84x | 43.2% | 60.0% | 0.7 | 0.72 |
| 2 | `rsi_regime` | 1.69x | 42.5% | 65.8% | 0.8 | 0.65 |
| 3 | `composite_regime` ⭐ new | 1.73x | 42.6% | 78.0% | 0.6 | 0.55 |
| 4 | `breakout` | 0.93x | 37.7% | 67.5% | 2.7 | 0.56 |
| 5 | `montauk_821` (baseline) | 0.71x | 35.5% | 59.0% | 2.2 | 0.60 |
| 6 | `chandelier_exit` ⭐ new | 0.37x | 30.5% | 48.4% | 2.1 | 0.63 |

## Highlights

### `recovery_momentum` — New #1 this session
Explicit crash+bounce detector. Enters when TECL has dropped ≥30% from a peak and bounced ≥15% off the trough. 12 trades over 17 years, 66.7% win rate, **lowest drawdown of the top 3 at 60%**.

Best params found:
```json
{"crash_pct": 30.0, "bounce_pct": 15.0, "peak_lb": 40, "trend_len": 50,
 "quick_ema": 20, "quick_lb": 5, "quick_thresh": -7.0,
 "atr_period": 10, "atr_mult": 4.5}
```

**Strategy logic (Python source — use this to generate Pine Script):**
```python
def recovery_momentum(ind, p):
    # Looks back peak_lb bars for a peak→trough crash of crash_pct%.
    # Enters when price has since bounced bounce_pct% off the trough,
    # and price is above the trend_len EMA.
    # Exits when quick EMA (quick_ema period, quick_lb lookback) drops
    # more than quick_thresh%, OR ATR shock (close < prev_close - ATR * atr_mult).

    crash_pct  = p["crash_pct"]   # 30.0  — min peak→trough drop to qualify (%)
    bounce_pct = p["bounce_pct"]  # 15.0  — min trough→now rise to enter (%)
    peak_lb    = p["peak_lb"]     # 40    — bars to look back for peak/trough
    trend_len  = p["trend_len"]   # 50    — EMA trend filter length
    quick_ema  = p["quick_ema"]   # 20    — EMA for momentum exit
    quick_lb   = p["quick_lb"]    # 5     — lookback for quick EMA % change
    quick_thresh = p["quick_thresh"]  # -7.0 — exit threshold (%)
    atr_period = p["atr_period"]  # 10   — ATR period
    atr_mult   = p["atr_mult"]    # 4.5  — ATR shock multiplier

    # ENTRY: peak happened before trough in the window,
    #        crash depth >= crash_pct, bounce >= bounce_pct, above trend EMA
    # EXIT 1: quick EMA pct change over quick_lb bars <= quick_thresh
    # EXIT 2: close < close[1] - ATR * atr_mult
```

### `composite_regime` — Strong debut
Normalized multi-indicator score (RSI + TEMA slope + MACD hist). 11 trades, 90.9% win rate, 1.73x vs B&H. High drawdown (78%) is the concern.

### Dead strategies (0 results after 125 gens)
`tema_momentum`, `macd_recovery`, `donchian_regime` never fired — parameter spaces need fixing.

## Next Steps
- [ ] Fix the 3 dead strategies (bad default param ranges)
- [ ] Run overnight (8h) to let `recovery_momentum` and `composite_regime` converge
- [ ] Ask user if Pine Script should be generated for `recovery_momentum`
