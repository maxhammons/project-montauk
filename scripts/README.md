# scripts/ — Python code that runs Project Montauk

This folder holds every Python script the project uses. It's grouped by purpose so you can navigate even if you don't read code. Each subfolder owns one phase of the canonical pipeline:

```
generate ideas  →  backtest + validate  →  if PASS → leaderboard  →  visualize
```

## Folder map

| Folder | What it does | When you'd look here |
|--------|--------------|----------------------|
| [`data/`](data/) | Loads and verifies the TECL/TQQQ/QQQ/XLK/SGOV/VIX market data. Synthetic-formula re-verification, Yahoo-vs-Stooq cross-check, checksum/manifest integrity. | "Is the data clean? Where does TECL come from before 2008?" |
| [`engine/`](engine/) | The backtest machinery. Pre-computed indicators, bar-by-bar execution, regime scoring, canonical-parameter rules. | "How does a strategy actually run on TECL history?" |
| [`strategies/`](strategies/) | The strategy library itself (every registered strategy function) + helpers that score how well a strategy tracks the hand-marked cycles. | "What strategies does the engine know about?" |
| [`search/`](search/) | Discovery + optimization. `grid_search.py` (exhaustive canonical grid), `evolve.py` (GA optimizer + **leaderboard guard**), `spike_runner.py` (the `/spike` entry point). | "How do we generate and tune new strategies?" |
| [`validation/`](validation/) | The 7-gate validation pipeline. Each file = one gate (integrity, candidate, fragility, walk-forward, uncertainty, cross-asset, synthesis). A strategy that reaches `spike/leaderboard.json` has cleared every gate here. | "Why did strategy X WARN instead of PASS?" |
| [`certify/`](certify/) | Post-validation certification + leaderboard sealing. `certify_champion.py` emits the 5 standardized run artifacts and flips `backtest_certified=True`. `recertify_leaderboard.py` re-validates the entire current leaderboard under today's rules. | "After I patched the engine, how do I re-verify the leaderboard is still correct?" |
| [`diagnostics/`](diagnostics/) | Post-run analysis tools that don't affect verdicts: per-cycle trade breakdowns, markdown report generation, Roth-IRA cashflow overlay. | "Where did strategy X miss bull #7?" |
| [`experimental/`](experimental/) | Work-in-progress / scratch code. Not wired into the main pipeline. | Rarely. |

## The pipeline rule (cement)

**A strategy lives on [`spike/leaderboard.json`](../spike/leaderboard.json) if and only if it satisfies the canonical authority contract in [`certify/contract.py`](certify/contract.py).** The leaderboard is a binding statement that the listed strategies are **certified not overfit** under current rules.

Concretely, to be admitted to the leaderboard an entry must satisfy both:

1. **`promotion_ready=True`** — passed all 7 validation gates (gate1-7), verdict `PASS`
2. **All required certification checks pass** (see `certify/contract.py::REQUIRED_CERTIFICATION_CHECKS`):
   - `engine_integrity` — slippage active, bar-close execution, lookahead-safe, repaint-safe
   - `golden_regression` — `montauk_821` trade ledger matches `tests/golden_trades_821.json`
   - `shadow_comparator` — engine agrees with `backtesting.py` on per-trade PnL (majority-agrees rule)
   - `data_quality_precheck` — `scripts/data/quality.py` reports 0 FAIL

When both conditions hold, the row is marked `certified_not_overfit=True`. That is the leaderboard truth.

The `artifact_completeness` check (5 standardized JSONs in `spike/runs/NNN/`) is required for the run's **champion** only — it upgrades that champion from `certified_not_overfit=True` to `backtest_certified=True`. It is not part of non-champion leaderboard admission.

Performance does not affect eligibility. It only ranks already-certified rows and trims the leaderboard to the top 20.

This rule is enforced programmatically by `search/evolve.py::update_leaderboard` via [`certify/contract.py`](certify/contract.py). Final artifact certification uses the same contract, so artifact generation cannot upgrade a WARN / non-`promotion_ready` row into `backtest_certified=True`.

## One-liner per file

### `data/`
- `loader.py` — single source of truth for loading TECL/TQQQ/QQQ/XLK/SGOV/VIX into a pandas DataFrame with synthetic-era stitching
- `audit.py` — re-verify the synthetic pre-IPO math (daily return residual < 1e-7)
- `crosscheck.py` — fetch a second data source (Tiingo/Stooq) and flag any divergence > 0.01%
- `manifest.py` — write/verify `data/manifest.json` (provenance, checksums, seam dates)
- `quality.py` — single `audit_all()` that runs every data integrity test → PASS/WARN/FAIL report
- `rebuild_synthetic.py` — deterministic rebuild of the synthetic portion of TECL/TQQQ from the underlying

### `engine/`
- `strategy_engine.py` — the engine. `Indicators` class (cached pre-computed signals), `backtest()` (single-position bar-by-bar loop), `run_montauk_821()` (canonical 8.2.1 entry point)
- `regime_helpers.py` — regime-scoring helpers used by the validation pipeline (detect_bear_regimes, detect_bull_regimes, score_regime_capture). Formerly `backtest_engine.py` pre-Phase-7.
- `canonical_params.py` — "which parameter values are canonical vs. GA-tuned" rules. Auto-promotes tier (T0 → T1 → T2) based on canonical-ness.

### `strategies/`
- `library.py` — every registered strategy function, plus the `STRATEGY_REGISTRY`, `STRATEGY_TIERS`, and `STRATEGY_PARAMS` dicts
- `markers.py` — score how well a strategy's buy/sell dates align with the hand-marked cycle file
- `regime_map.py` — segment TECL history into bull/bear cycles for diagnostic purposes

### `search/`
- `grid_search.py` — exhaustive canonical-grid backtest + validation driver. The main entry after adding a new strategy family.
- `evolve.py` — GA optimizer (used inside `/spike`), fitness function, leaderboard updater + guard, config-hash dedup
- `spike_runner.py` — `/spike` entry point. Runs the GA in timed chunks, validates winners, emits run artifacts.
- `share_metric.py` — tiny compat helper for reading `share_multiple` from both new and legacy leaderboard JSON schemas

### `validation/`
See `validation/__init__.py` and `validation/pipeline.py`. Each gate lives in its own module:
- `integrity.py` — gate 0 (engine integrity, golden regression, shadow comparator, data-quality precheck)
- `candidate.py` — gate 1 (result-quality metrics)
- `sprint1.py` — gate 2 (search-bias diagnostics, T2 only)
- `walk_forward.py` — gate 4 (time-window generalization)
- `cross_asset.py` — gate 6 (TQQQ + QQQ portability + same-param re-opt)
- `deflate.py` — Monte Carlo null distribution for regime scoring
- `uncertainty.py` — gate 5 (Morris fragility + stationary bootstrap)
- `pipeline.py` — orchestrator; runs all gates, computes verdict + composite confidence

### `certify/`
- `certify_champion.py` — seal a single strategy as `backtest_certified=True`. Creates `spike/runs/NNN/` + emits the 5 standardized artifacts.
- `recertify_leaderboard.py` — re-validate every leaderboard entry under today's rules. Use after engine patches or rule changes.
- `backfill_artifacts.py` — materialize missing 5-artifact bundles for older run directories

### `diagnostics/`
- `cycle_diagnostics.py` — per-bull/per-bear cycle trade breakdown for a single strategy
- `report.py` — generate the markdown report that summarizes a `/spike` run
- `roth_overlay.py` — post-validation Roth IRA cashflow simulator (tax-aware net-of-contribution-limit share count)

### `experimental/`
Scratch / WIP. Not imported by any production path.

## How to add a new strategy

1. Write the strategy function in `strategies/library.py` (follow the existing `gc_*` pattern — takes `Indicators` + `params` dict, returns `(entries, exits, labels)`).
2. Register it in `STRATEGY_REGISTRY` and `STRATEGY_TIERS` at the bottom of the same file.
3. Add a canonical grid in `search/grid_search.py::GRIDS` for the new concept.
4. Run `python3 scripts/search/grid_search.py --concepts your_strategy` — this backtests every grid combo, pushes the top-N through validation, and (if any PASS with full certification) appends them to `spike/leaderboard.json`.
5. If a new champion emerges, run `python3 scripts/certify/certify_champion.py` to produce the deployment artifacts.

**Do not** manually add entries to `spike/leaderboard.json`. The leaderboard is an output, not an input.
