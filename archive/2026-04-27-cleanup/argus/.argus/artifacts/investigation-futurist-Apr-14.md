# Investigation: Futurist

## 5 Observations

1. **The Cache Invalidation Timebomb**
   - **Finding:** `evolve.py` uses the raw bytes of `strategy_engine.py`, `evolve.py`, and `strategies.py` to compute `_ENGINE_HASH`, which prefixes all cache keys in `hash-index.json`.
   - **What happens in 18 months when a developer runs a linter?** Adding a single comment, fixing a typo, or running `ruff`/`black` will change the file hash. This instantly invalidates the entire cache of tested configurations. The team will be locked out of refactoring or documenting their core engine because doing so destroys thousands of hours of evolutionary compute history. 

2. **String-Template Logic Lock-in**
   - **Finding:** `pine_generator.py` generates Pine Script by injecting parameters into massive, hardcoded string templates (e.g., `_build_montauk_821`). There is no shared AST between the Python backtester and the Pine generator.
   - **What happens in 18 months when the optimizer needs to discover novel logic?** The codebase's goal is "automated strategy discovery", but it can currently only tune parameters for human-written templates. If the engine needs to combine an RSI entry with a TEMA exit, a human has to manually code both the Python and Pine representations. True strategy evolution is blocked by this string-formatting architecture.

3. **Single-Asset Validation Coupling**
   - **Finding:** The data access pattern (`get_tecl_data`) is hardcoded into `data.py` and imported directly across the `validation/*.py` pipeline.
   - **What happens in 18 months when the team needs to diversify?** If TECL liquidity dries up or they want to apply the engine to a 3x Semiconductor ETF (SOXL), the validation pipeline will require a massive structural rewrite. The lack of an abstract `Universe` or `Asset` model means the entire testing framework is coupled to a single ticker symbol.

4. **Concurrency Ceiling via `hash-index.json`**
   - **Finding:** `evolve.py` stores its state in a single local JSON dictionary (`hash-index.json`).
   - **What happens in 18 months when the search space requires a cluster?** Evolutionary algorithms scale horizontally. When the team attempts to run `evolve.py` across 10 EC2 instances or even multiple local processes, the lack of a database or file-locking mechanism for `hash-index.json` will cause immediate file corruption and race conditions. This data model guarantees they cannot scale their compute.

5. **Fitness Function Drift**
   - **Finding:** The charter explicitly states the primary goal is "share-count multiplier vs B&H". However, the history index and the codebase still rely on `vs_bah` (dollar value) and `trade_scale` modifiers.
   - **What happens in 18 months when the deployed strategy survives a bear market?** The engine will have spent months selecting strategies that protect absolute dollar drawdowns but fail to accumulate shares at the bottom. The team will realize their mathematically "validated" strategies actually underperform Buy & Hold in share-count compounding, rendering the entire historical archive of optimization runs invalid.

---

## What I investigated and ruled out

- **Performance of Python Backtester:** I looked into `backtest_engine.py` to see if the Python iterative approach would be too slow. It uses vectorized operations where possible (like `np.full_like`, recursive EMA arrays) and seems adequate for daily timeframe data over a 20-year span. While not C++, it isn't an architectural dead-end that will halt development soon.
- **Pine Script v6 Migration:** `pine_generator.py` is already outputting `//@version=6`. I ruled out a looming version deprecation crisis from TradingView.
- **Data Source Fragility:** `data.py` relies on Yahoo Finance for daily updates. While YF can be flaky, the system caches locally to CSVs and handles missing data gracefully. It's an annoyance, not an irreversible lock-in.

---

## What I would need to see to change my mind

- **For the Cache:** I would need to see the cache key generated from the semantic structure (AST) of the strategy logic or explicit strategy versioning strings, rather than raw file bytes.
- **For the Logic Lock-in:** I would need to see the Python backtester and Pine generator both compiling from a shared configuration object or DSL (Domain Specific Language) that defines the indicator topology, rather than parallel human-maintained implementations.
- **For Single-Asset Coupling:** I would need to see the validation tier accept an `Asset` object or ticker string dynamically, rather than importing `get_tecl_data`.
- **For Concurrency:** I would need to see a migration to SQLite, Postgres, or at least a file-locking/append-only log architecture for the evolutionary state.