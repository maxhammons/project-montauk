# Implementation Plan: Argus Elevation (Python Engine Focus)

## Objective
Address the critical blockers and architectural debt identified in the Argus Elevation Report (Apr-09) while entirely dropping TradingView Pine Script deployment workflows. Project Montauk is staying exclusively in Python. 

## Key Files & Context
- `scripts/search/evolve.py`: Houses the caching logic (`_compute_engine_hash`) and the Optuna multi-objective evaluation loop (`_objectives_from_result`, `fitness()`).
- `scripts/search/fitness.py`: Houses the new mathematically robust `weighted_era_fitness` formula.

## Implementation Steps

### Step 1: Fix Unversioned Cache Poisoning
*The `config_hash` generator currently misses `fitness.py`, meaning tweaks to fitness thresholds do not trigger a cache invalidation, resulting in stale Optuna history.*
1. Open `scripts/search/evolve.py`.
2. Locate `_compute_engine_hash()`.
3. Add `os.path.join("search", "fitness.py")` to the tuple of files being hashed. This ensures that any modification to the fitness weights or floor instantly invalidates the `hash-index.json` cache.

### Step 2: Untangle the Fitness Formula (Optuna Integration)
*The existing `_objectives_from_result()` passes Optuna the raw `share_multiple`, completely ignoring the new `weighted_era_fitness` logic which was meant to replace it. Furthermore, the legacy `fitness()` function inside `evolve.py` arbitrarily multiplies performance by HHI and Drawdown penalties—effectively hiding these tradeoffs from Optuna's NSGA-II solver.*
1. Open `scripts/search/evolve.py`.
2. Import `fitness_from_result` from `search.fitness`.
3. Update `_objectives_from_result(result)`:
   - Change the first objective returned from `float(result.share_multiple)` to the era-weighted fitness score: `fitness_from_result(result)`.
   - Keep `max_drawdown_pct` and `hhi` as the second and third minimizing objectives so Optuna natively solves for the Pareto front.
4. Review the legacy `fitness(entry)` function in `evolve.py`. Since Optuna is now actively managing `hhi` and `dd` via the Pareto front, strip out the arbitrary `0.5x` scalar penalties for drawdowns > 30% and HHI > 0.35 if this function is used exclusively for Bayesian evaluation (or document that it is retained only for legacy leaderboard ranking).

## Verification & Testing
1. Run a short Optuna sweep (e.g., `python -m scripts.search.spike_runner --bayesian --minutes 1`) to ensure the cache hash generates correctly and the solver correctly optimizes using the three objectives (weighted fitness, dd, hhi).
2. Modify a value in `scripts/search/fitness.py` and run the script again. Confirm that `_compute_engine_hash` produces a new prefix and forces 100% "new_configs" rather than loading "cached_configs".
3. Verify that the console logs for Optuna print the mathematically correct weighted fitness score instead of a raw share multiple.