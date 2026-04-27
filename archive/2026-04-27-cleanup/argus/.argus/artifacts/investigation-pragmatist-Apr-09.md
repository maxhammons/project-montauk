# Investigation: The Pragmatist

**Frame:** Does this need to exist?

## Observations
1. **The Dual-Engine Overhead:** We are maintaining two separate execution engines. `scripts/strategy_engine.py` is a custom Pandas/Numpy backtester, while the actual production execution happens in TradingView via Pine Script v6. This means every indicator and entry/exit logic must be written twice. Does the Python engine earn its keep? Yes, because Pine Script cannot run Bayesian optimization across 100,000 parameter combinations or use synthetic 1998-2008 data. But the maintenance cost is immense.
2. **The Kitchen Sink Strategy:** `Project Montauk 8.2.1.txt` has 11 input groups (EMAs, Trend, TEMA, Sideways, Sell Confirm, Cooldown, ATR, Quick EMA, Trailing Stop, TEMA Slope). Several are "default OFF". This isn't a single strategy; it's a framework masquerading as a script. Every new idea is bolted on with an `enableX` toggle.
3. **The Hash Index Cache:** `evolve.py` uses a custom JSON-based cache (`hash-index.json`) to skip re-evaluating identical configs. It has complex migration logic (v1 to v2 to v3). Does a custom cache need to exist? Yes, to save compute during GA/Bayesian runs. 

## What I Ruled Out
- I initially questioned if the custom `Indicators` class in `strategy_engine.py` was reinventing the wheel vs using `pandas-ta`. However, the need to exactly match Pine Script's `ta.ema` and `ta.rma` calculations justifies a custom implementation. Pine Script's EMA seed logic is notoriously specific.

## What Would Change My Mind
- If someone can show me that maintaining the Pine Script translation is automated (e.g., a transpiler exists), I would accept the dual-engine setup. Right now, it looks like a manual sync liability.