## North Star Statement

This codebase is trying to become an automated strategy discovery and validation pipeline that generates Pine Script trading systems capable of accumulating more TECL shares than buy-and-hold. The team is clearly working toward exhaustive, programmatic validation (grid search, evolutionary optimization, walk-forward testing) to prevent overfitting. The current approach centers on the "Montauk Engine", a Python suite that evaluates strategies against a hand-marked 'perfect' cycle dataset (markers) and validates them across multiple tiers.

There is a documented tension: the charter now defines "share-count multiplier vs B&H" as the primary metric and removes trade-frequency punishment, but the Python scripts still use dollar `vs_bah` and a `trade_scale` factor.

---

## Momentum

**Actively evolving:** Optimization tools and skills (`scripts/evolve.py`, `scripts/grid_search.py`, `.claude/skills/spike*.md`), validation tiers (`scripts/validation/`).
**Settled:** Core indicator logic (`Montauk Composite Oscillator`), historical strategy versions (`src/strategy/archive/`).
**Signals of strategic shift:** The shift from manual Pine Script tuning to the automated "Montauk Engine" and the explicit mandate to optimize for "share-count multiplier vs B&H" over absolute return.

---

## Stage Assessment

**Stage:** Growth

The core infrastructure (Pine Script templates, Python backtester) is in place and functional, but the team is actively expanding the optimization engine (grid search, evolutionary algorithms) and hardening the validation tiers. The focus has shifted from building the core backtester to running bulk hypotheses through it safely.