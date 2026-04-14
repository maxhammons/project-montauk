# Argus Elevation Plan — Apr-09

## BLOCKERS

### 1. Unversioned Cache Poisoning
- **Identified by:** Exploiter
- **Status:** **PROVEN** via code inspection.
- **The Threat:** The `config_hash` in `evolve.py` ignores changes to the engine source code. If a bug in `strategy_engine.py` is fixed, the optimizer will still use the old, buggy fitness scores from `hash-index.json`. The pipeline's memory is untrustworthy.
- **The Fix:** Modify `config_hash` to include an "engine_version" string, or simply hash the contents of `strategy_engine.py` and `evolve.py`. When the engine changes, the hash changes, invalidating the stale cache.
- **Unlocks:** Trust in the optimizer's long-term history tracking.

### 2. The Deployment Air Gap
- **Identified by:** Accelerator
- **Status:** Architectural reality.
- **The Threat:** The optimizer generates optimal JSON parameters, but the TradingView execution script (`Project Montauk 8.2.1.txt`) requires manual input. This introduces human error and creates massive friction in the feedback loop.
- **The Fix:** Write a deployment script (`scripts/deploy.py`) that reads the best params from `spike/runs/NNN/results.json`, uses regex to replace the `defval=` arguments inside `Project Montauk 8.2.1.txt`, and saves the ready-to-paste file to an output folder.
- **Unlocks:** True end-to-end velocity.

---

## ACCELERATORS

### 3. Untangle the Fitness Formula
- **Identified by:** Craftsman / Futurist
- **Status:** **PROVEN** via code inspection.
- **The Threat:** The current `fitness()` formula multiplies the core metric (`vs_bah`) by five different penalty scaling factors. Optuna (Bayesian mode) cannot differentiate between a terrible strategy and a brilliant strategy that triggered a 0.3x drawdown penalty. It just sees a low scalar.
- **The Fix:** Use Optuna's native multi-objective optimization (e.g., maximize `vs_bah`, minimize `max_drawdown`, minimize `hhi`). Let the solver explore the Pareto front instead of artificially flattening everything into a single, gameable number.
- **Unlocks:** Honest, mathematically rigorous strategy discovery.

---

## BETS

### 4. Python-to-Pine Transpilation
- **Identified by:** Pragmatist
- **The Threat:** As the VIX indicators and strategy logic get more sophisticated, keeping the Python engine perfectly synced with the TradingView Pine Script will become impossible. 
- **The Fix:** Investigate if the core `buyOk` and `exitCond` logic can be generated programmatically from Python into a Pine Script string. Instead of maintaining two codebases, maintain Python logic that emits Pine Script.
- **Unlocks:** Infinite scalability for complex strategy rules without translation drift risk.