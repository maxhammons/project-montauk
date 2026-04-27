# The Historian — Temporal Analysis

## Architectural Archaeology
- The project started as "FMC" (Flash Momentum Capture) using MACD entries.
- Evolved systematically to EMA-crossovers with layered filters (TEMA, Donchian sideways detection, trailing stops).
- Recent structural changes include a major pipeline overhaul for data (synthetic TECL, VIX inclusion) and optimizer enhancements (Bayesian/Optuna replacing pure GA).

## Velocity Topology
- Active evolution in `scripts/` (engine, evolve, data fetch) and `src/strategy/` (Pine Script logic).
- Output structure (`spike/runs/`) was recently formalized from dates to sequential numbers.
- High velocity in validation logic (Walk-forward testing added).

## Trajectory Prediction
- The codebase is moving from a collection of scripts to a robust, automated factory for trading strategies.
- With the addition of Bayesian optimization and synthetic data, the risk of overfitting is the primary technical debt/challenge.
- The pipeline will likely become the core product, rather than any single strategy.

## Decision Archaeology
- Decision to add Bayesian optimization (Optuna) alongside Genetic Algorithm.
- Decision to separate Pine Script generation from backtesting (TradingView remains the execution environment).
- Decision to emphasize "Beat Buy & Hold" as the primary fitness target over pure Regime Score.