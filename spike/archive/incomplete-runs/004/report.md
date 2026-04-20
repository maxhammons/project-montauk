# Spike Report — 2026-04-05

**Session:** 20 min | 59,280 evaluations | 114 generations | 13 strategies | 48 evals/sec

## Session Summary

Added 6 new strategies (`macd_zero_cross`, `dmi_trend`, `roc_momentum`, `composite_momentum`, `donchian_trend`, `keltner_rsi`) bringing the registry to 13 total. Best-ever record (2.1803, rsi_regime) was **not** beaten this session — the population needs more evolution time to find the peak. Session best for rsi_regime was 1.0102.

## Top Rankings (This Session)

| Rank | Strategy | Fitness | vs BAH | CAGR | MaxDD | MAR | t/yr | vs 8.2.1 |
|------|----------|---------|--------|------|-------|-----|------|----------|
| 1 | rsi_regime | 1.0102 | 1.656x | 42.3% | 78.0% | 0.54 | 0.2 | baseline winner |
| 2 | breakout | 0.6092 | 0.899x | 37.4% | 64.5% | 0.58 | 1.4 | +1,192% |
| 3 | montauk_821 | 0.6010 | 0.853x | 36.9% | 59.0% | 0.63 | 1.6 | +1,175% |
| 4 | roc_momentum | 0.0959 | 0.139x | 23.3% | 61.9% | 0.38 | 2.0 | **NEW +103%** |
| 5 | macd_zero_cross | 0.0924 | 0.121x | 22.3% | 47.1% | 0.47 | 2.4 | **NEW +95%** |
| 6 | bollinger_squeeze | 0.0764 | 0.117x | 22.0% | 68.9% | 0.32 | 2.9 | +62% |
| 7 | keltner_rsi | 0.0666 | 0.103x | 21.1% | 35.7% | 0.59 | 3.7 | **NEW +41%** |
| 8 | golden_cross | 0.0611 | 0.095x | 20.6% | 71.6% | 0.29 | 0.9 | +29% |
| 9 | dmi_trend | 0.0532 | 0.095x | 20.6% | 46.3% | 0.44 | 3.9 | **NEW +13%** |
| 10 | trend_stack | 0.0331 | 0.045x | 15.5% | 53.0% | 0.29 | 3.0 | -30% |
| 11 | donchian_trend | 0.0213 | 0.029x | 12.4% | 45.7% | 0.27 | 3.1 | **NEW -55%** |
| 12 | composite_momentum | 0.0029 | 0.003x | -0.7% | 23.1% | -0.03 | 0.2 | **NEW -95%** |
| — | tema_momentum | 0.0 | — | — | — | — | 0.0 | no trades found |

*8.2.1 baseline fitness ≈ 0.047 at default params*

## Best-Ever (All Sessions)

```
Strategy:  rsi_regime
Fitness:   2.1803
vs BAH:    3.49x
CAGR:      48.6%
MaxDD:     75.1%
Trades/yr: 0.7
Params:    rsi_len=10, trend_len=150, entry_rsi=35, exit_rsi=85, panic_rsi=15, cooldown=5
```

## Notable New Strategies

### `roc_momentum` — Promising debut (#4)
- Rate of Change momentum: enter when smoothed ROC > threshold, exit when it fades
- 23.3% CAGR at 2.0 trades/yr — cleaner signal than many EMA-based approaches
- Best params: roc_len=35, roc_smooth=9, entry_roc=12.0, exit_roc=0.0, trend_len=50

### `macd_zero_cross` — Solid debut (#5)
- Wide MACD (20/40/15) crossing zero — catches bigger regime swings than default (12/26/9)
- 22.3% CAGR, 47.1% MaxDD, 2.4 trades/yr — lower DD than rsi_regime
- Saved to `remote/winners/macd-zero-cross-2026-04-05.json`

### `keltner_rsi` — Lowest DD of all new strategies (#7)
- Keltner breakout + RSI confirmation: requires price > upper channel AND RSI > 65
- **35.7% MaxDD** — lowest among strategies beating 8.2.1, with MAR=0.59
- Worth more exploration at lower trade frequency

### `donchian_trend` and `composite_momentum` — Didn't land
- Donchian: exceeded trade frequency constraint, couldn't stay under 3/yr
- Composite momentum: too few signals, near-zero CAGR. May need rethinking.

## What to Try Next

1. **Longer run for `roc_momentum`** — 114 gen wasn't enough to find the floor. Previous `rsi_regime` took multiple sessions to hit 2.18. ROC has similar characteristics.
2. **Hybrid `roc_momentum` + ATR exits** — the ROC signal with a tighter ATR exit multiplier may reduce the 61.9% DD
3. **`keltner_rsi` at ≤2 trades/yr** — currently sitting at 3.7 t/yr due to param space ceiling. Constrain `cooldown` range and rerun.
4. **`composite_momentum` rewrite** — the normalized composite approach is valid but needs a cleaner entry trigger (e.g. level cross rather than zero-cross)

## Files
- Results: `remote/evolve-results-2026-04-05.json`
- Best-ever: `remote/best-ever.json` (unchanged at 2.1803)
- Winner saved: `remote/winners/macd-zero-cross-2026-04-05.json`
