## North Star Statement

This codebase is trying to become a fully automated, rigorous strategy discovery and validation pipeline for TradingView. The team is clearly working toward eliminating overfitting through walk-forward validation, synthetic deep history (1998-2008), and Bayesian optimization. The current approach centers on generating robust Pine Script v6 strategies that consistently beat buy-and-hold for TECL, using Python for heavy lifting and TradingView for execution.

---

## Momentum

**Actively evolving:** The Python backtest/optimization pipeline (`scripts/evolve.py`, `scripts/walk_forward.py`, data fetching) and VIX-based regime detection strategies.
**Settled:** The base strategy template format and the Pine Script execution model.
**Signals of strategic shift:** The recent "major pipeline overhaul" commit marks a shift from manual strategy tweaking to automated, data-driven strategy generation using Optuna and expanded historical datasets.

---

## Stage Assessment

**Stage:** Growth

The project has moved past its "Spike v1" phase and is formalizing its infrastructure (sequential runs, rigorous validation, GH Actions integration). The focus has shifted from building the basic backtester to improving its statistical validity and optimization power.