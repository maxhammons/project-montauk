# Craftsman Investigation — Apr 14

## Observations

1. **The Engine Naming Inversion:** `backtest_engine.py` is not an engine; it is a hardcoded specific strategy (Montauk 8.2.1) coupled with regime scoring and its own backtest loop. `strategy_engine.py` is the actual modular backtest engine. The names are perfectly inverted, creating a false model of the system's architecture.
2. **Fractured Domain Model:** Because of the engine split, core domain entities like `Trade` and `BacktestResult` are defined twice, with slightly different schemas, in both `backtest_engine.py` and `strategy_engine.py`. The abstraction boundary has failed, making the codebase confusing and brittle.
3. **Redundant Indicator Math:** Both "engine" files implement their own internal indicator logic (e.g., `_ema`, `_rma`, `_sma`). The codebase lacks a unified, single source of truth for basic technical indicators.
4. **Vocabulary Drift (`vs_bah` vs Share Count):** The team's mental model has shifted to optimizing for "share-count multiplier", but the code's vocabulary is stuck on `vs_bah_multiple`. The code relies on mathematical identity (dollar ratio == share ratio) and long explanatory comments instead of renaming the variables to reflect the actual domain concept.
5. **The Phantom `trade_scale`:** The perceived tension between the charter and the code regarding frequency punishment (`trade_scale`) no longer exists. It was successfully removed from the code, meaning the code is more honest about its goals than the current documentation implies.

## What I investigated and ruled out
- I investigated whether `trade_scale` was still secretly punishing low-frequency strategies in the optimization loop. I ruled this out; it was explicitly removed from the fitness function in `evolve.py`. The hard floor of `num_trades < 5` remains, but as a structural guard, not a frequency punishment.
- I investigated if the `BacktestResult` in the two engines were actually the same class imported from a shared model. They are not. They are independent `@dataclass` definitions, meaning the duplication is physical and conceptual.

## What I would need to see to change my mind
- I would change my mind about the `backtest_engine.py` naming if someone could demonstrate that it is used generically across multiple independent strategies in the pipeline, rather than just being the vessel for the 8.2.1 baseline and regime scoring.
- I would retract my complaint about `vs_bah_multiple` if the underlying financial model intrinsically requires evaluating cash performance against cash buy-and-hold as a distinct concept from share accumulation, but the charter explicitly states share-count is the primary metric.