## North Star Statement

This codebase is trying to become a fully autonomous strategy discovery and validation pipeline for trading TECL. The team is clearly working toward robust, heavily-validated (7-gate pipeline) trading algorithms that accumulate more shares than a buy-and-hold approach, avoiding overfitting through rigorous out-of-sample and cross-asset checks. The current approach centers on `scripts/strategy_engine.py` as the single source of truth, optimized via GA and grid search tools.

---

## Momentum

**Actively evolving:** `scripts/search/grid_search.py`, `scripts/search/evolve.py`, and the validation pipeline (gates).
**Settled:** The core indicators and base HTML visualization shell.
**Signals of strategic shift:** The excision of PineScript/TradingView in favor of a pure Python backtest engine (Montauk 2.0) marks a massive shift toward programmatic, headless validation and away from visual charting tools.

---

## Stage Assessment

**Stage:** Growth

The architecture has settled after a major rewrite (Pine excision), and the focus has shifted entirely to running the pipeline (Spike runs, GA optimization, grid search). The infrastructure is in place to scale the number of hypotheses tested.
