# Codebase Atlas — Project Montauk — 2026-04-22

Manifest scope: 1,073 files after excluding `.git`, `.venv`, `.pytest_cache`, `.ruff_cache`, and `__pycache__`.

## Module Index

### `.argus/` (122 files)
Exports: run artifacts, calibration caches, POC helpers.
Imports from: mostly none; tiny Python helper under `artifacts/`.
Churn: 75 touched paths in last 30 days (HIGH).
Complexity signals: artifact-heavy, `runs/` dominates the tree, no test files.
Risk vector: orchestration metadata and run-state drift.

### `.claude/` (11 files)
Exports: skill docs, focus notes, local settings.
Imports from: none.
Churn: 63 touched paths in last 30 days (HIGH).
Complexity signals: prompt and skill documentation only.
Risk vector: workflow conventions.

### `.github/` (1 file)
Exports: workflow config.
Imports from: none.
Churn: 10 touched paths in last 30 days (LOW).
Complexity signals: tiny CI surface.
Risk vector: release automation.

### `data/` (14 files)
Exports: market CSVs, `manifest.json`, `markers/TECL-chart.html`.
Imports from: none in the current tree.
Churn: 36 touched paths in last 30 days (MED).
Complexity signals: static data bundle, marker HTML asset, no tests.
Risk vector: input-data integrity.

### `docs/` (61 files)
Exports: charter, pipeline notes, validation docs, legacy Python references.
Imports from: none; mostly documentation.
Churn: 140 touched paths in last 30 days (HIGH).
Complexity signals: `docs/Legacy/Python/*.py` is real code-sized legacy, not just prose.
Risk vector: stale spec and legacy drift.

### `journals/` (1 file)
Exports: journal log.
Imports from: none.
Churn: no recent signal.
Complexity signals: negligible.
Risk vector: low.

### `scripts/` (90 files)
Exports: core engine, data loaders, strategy registry, search and validation pipelines.
Imports from: `scripts/engine/strategy_engine.py`, `scripts/data/loader.py`, `scripts/strategies/library.py`, `scripts/engine/regime_helpers.py`, `scripts/search/share_metric.py`, and validation helpers.
Churn: 287 touched paths in last 30 days (VERY HIGH).
Complexity signals: largest code surface; several files over 500 lines and a 7k-line registry.
Risk vector: strategy logic, validation orchestration, and data plumbing.
Submodules: `engine/`, `data/`, `validation/`, `search/`, `diagnostics/`, `strategies/`, `certify/`, `experimental/`, `archive/`.

### `spike/` (734 files)
Exports: run outputs, leaderboards, hash indexes, registry snapshots.
Imports from: none; overwhelmingly generated state.
Churn: 944 touched paths in last 30 days (EXTREME).
Complexity signals: `runs/` and `archive/` dominate; artifact churn is the hottest zone in the repo.
Risk vector: generated output drift and historical state confusion.

### `spirit-guide/` (16 files)
Exports: spirit-memory, summary, and source notes.
Imports from: none.
Churn: 18 touched paths in last 30 days (LOW).
Complexity signals: mostly guidance text and small notes.
Risk vector: advisory context only.

### `tests/` (13 files)
Exports: regression, indicator, backtest, and shadow-comparator coverage.
Imports from: `scripts/engine/strategy_engine.py`, `scripts/engine/regime_helpers.py`, `scripts/data/loader.py`, `scripts/search/share_metric.py`, and external `backtesting`.
Churn: 13 touched paths in last 30 days (LOW).
Complexity signals: only dedicated test zone; `__pycache__/` present but ignored.
Risk vector: coverage baseline.

### `viz/` (5 files)
Exports: `montauk-viz.html`, `build_viz.py`, `templates/app.js`, `templates/shell.html`.
Imports from: `scripts/search/share_metric.py`.
Churn: 17 touched paths in last 30 days (LOW).
Complexity signals: large HTML shell plus generated template JS.
Risk vector: presentation layer.

### `ROOT` (5 files)
Exports: repo instructions and ignore rules.
Imports from: none.
Churn: 33 touched paths in last 30 days (MED).
Complexity signals: shared governance files only.
Risk vector: operating instructions.

## Import Graph

Top 20 most-imported files:
1. `scripts/engine/strategy_engine.py` — 17 imports
2. `scripts/data/loader.py` — 16 imports
3. `scripts/strategies/library.py` — 11 imports
4. `scripts/engine/regime_helpers.py` — 8 imports
5. `scripts/search/share_metric.py` — 4 imports
6. `scripts/strategies/markers.py` — 3 imports
7. `scripts/validation/sprint1.py` — 2 imports
8. `scripts/validation/deflate.py` — 2 imports
9. `scripts/validation/candidate.py` — 2 imports
10. `scripts/search/evolve.py` — 2 imports
11. `scripts/validation/uncertainty.py` — 1 import
12. `scripts/validation/pipeline.py` — 1 import
13. `scripts/validation/integrity.py` — 1 import
14. `scripts/validation/cross_asset.py` — 1 import
15. `scripts/strategies/regime_map.py` — 1 import
16. `scripts/strategies/__init__.py` — 1 import
17. `scripts/search/spike_runner.py` — 1 import
18. `scripts/engine/canonical_params.py` — 1 import
19. `scripts/data/rebuild_synthetic.py` — 1 import
20. `scripts/data/manifest.py` — 1 import

## Complexity Hotspots

- `scripts/strategies/library.py` — 7,154 lines.
- `scripts/search/evolve.py` — 1,875 lines.
- `scripts/search/grid_search.py` — 1,606 lines.
- `viz/montauk-viz.html` — 1,491 lines.
- `scripts/engine/strategy_engine.py` — 1,369 lines.
- `scripts/validation/pipeline.py` — 1,304 lines.
- `docs/Legacy/Python/strategies_1.2.py` — 1,131 lines.
- `viz/templates/app.js` — 783 lines.
- `scripts/data/loader.py` — 719 lines.
- `scripts/search/spike_runner.py` — 694 lines.
- `scripts/validation/candidate.py` — 579 lines.
- `scripts/data/quality.py` — 545 lines.
- `scripts/data/audit.py` — 509 lines.
- `scripts/certify/full_sweep.py` — 504 lines.
- `scripts/diagnostics/report.py` — 503 lines.
- `scripts/data/crosscheck.py` — 502 lines.

## Zero-Test Directories

- `.argus/`
- `.claude/`
- `.github/`
- `data/`
- `docs/`
- `journals/`
- `scripts/`
- `spike/`
- `spirit-guide/`
- `viz/`

## Shared Context Files

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `scripts/engine/strategy_engine.py`
- `scripts/data/loader.py`
- `scripts/strategies/library.py`
- `scripts/engine/regime_helpers.py`
- `scripts/search/share_metric.py`
- `scripts/validation/pipeline.py`
- `scripts/validation/candidate.py`
- `scripts/validation/deflate.py`
- `scripts/validation/sprint1.py`
