# History Context — Apr-14

## Temporal Analysis

### Architectural Archaeology
- Began as a manual Pine Script trading system for TECL.
- Evolved into the "Montauk Engine", a robust Python backtesting, validation, and optimization suite.
- The shift represents a move from intuition-based trading to programmatic, mathematically validated edge discovery.

### Velocity Topology
- Active evolution in: `scripts/` (especially `evolve.py`, `grid_search.py`, `validation/`).
- Active evolution in: Claude Code skills (`.claude/skills/spike*.md`).
- Settled: Historical strategy archives (`src/strategy/archive/`).

### Trajectory Prediction
- The codebase is heading towards fully automated, unsupervised strategy discovery.
- If current trends continue, the validation pipeline will become the most complex and critical part of the system to prevent curve-fitting against the synthetic/real TECL datasets.
- "What the codebase is trying to become": An automated strategy discovery and validation pipeline that guarantees out-of-sample edge against TECL B&H without overfitting.

### Decision Archaeology
- Major decision: Moving from MACD entries to EMA-crossover entries with layered exit filters (versions 7.x+).
- Major decision: Defining "share-count multiplier vs B&H" as the sole primary optimization target instead of absolute dollar return or CAGR.
- Major decision: Implementing a tiered validation framework (T0/T1/T2) and using a hand-marked cycle dataset (`TECL-markers.csv`) as a validation gate.