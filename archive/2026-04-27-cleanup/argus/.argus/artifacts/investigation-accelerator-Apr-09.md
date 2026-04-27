# Investigation: The Accelerator

**Frame:** Can a new engineer ship safely today?

## Observations
1. **The Air Gap Deployment:** A new engineer can optimize a strategy using `/spike`, get a winning parameter set, and then... they have to manually type or paste those parameters into the TradingView UI or the Pine Script source. This air gap is a massive friction point and a vector for human error. 
2. **Stateful Optimizer:** `evolve.py` has intricate state management for pausing and resuming chunks (`evolve_chunk`), with dictionaries full of `best_ever_params`, `prev_scored`, and `initial_diversity`. Modifying the optimizer's core loop is dangerous because the state-passing logic is tightly coupled and undocumented.
3. **Excellent Data Pre-computation:** `Indicators` class in `strategy_engine.py` caches all array calculations. A new engineer writing a strategy function in Python doesn't have to worry about performance; they just call `ind.ema(15)` and the engine handles the memoization. This is a massive velocity boost.

## What I Ruled Out
- I looked for missing documentation, but `CLAUDE.md` and the `reference/` folder are highly detailed. The onboarding context is actually very strong. The friction is in the tooling, not the knowledge.

## What Would Change My Mind
- If there is a script I missed that automatically writes `Project Montauk 8.2.x.txt` with the hardcoded optimized parameters embedded as defaults, the air gap risk is significantly reduced.