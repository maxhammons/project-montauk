# Investigation: The Craftsman

**Frame:** Is this honest? Does the code say what it does?

## Observations
1. **The "Beat Buy & Hold" Mirage:** `CLAUDE.md` claims the primary optimization target is beating Buy & Hold. But `fitness_from_cache` reveals a gauntlet of multipliers: HHI penalty, Drawdown penalty, Complexity penalty, and Regime multiplier. A strategy could massively outperform B&H but get zeroed out because it made 4 trades instead of 5, or because its HHI was 0.36. We are not just optimizing for B&H; we are optimizing for an idealized aesthetic of what a "good" strategy looks like.
2. **Pine Script Exit Logic Obfuscation:** In `Project Montauk 8.2.1.txt`, the "EMA Cross Exit" doesn't actually require a cross on that bar. It uses `ta.barssince(ta.crossunder(emaShort, emaLong)) < sellConfirmBars` AND a buffer check. The name `isCrossExit` is slightly dishonest—it's a "recent cross plus momentum collapse" exit. 
3. **Slippage Honesty:** `backtest` in `strategy_engine.py` applies a hardcoded `0.05%` slippage. This is genuinely honest craftsmanship. Most backtesters ignore slippage, leading to scalping artifacts. The code explicitly penalizes excessive trading through realistic market friction.

## What I Ruled Out
- I was suspicious of the Bayesian vs GA split in `evolve.py`. But the code honestly integrates both paradigms, using Optuna for Bayesian and a custom loop for GA, without conflating their results.

## What Would Change My Mind
- If the fitness function is refactored so the "gates" (max trades, HHI) are completely separated from the "score" (vs_bah), it would restore honesty to the ranking system. Right now, a score of "4.2" is a blended, opaque number.