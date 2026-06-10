# Phase 0 — Restore green baseline (execution tracker)

Canonical plan: `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md` (Phase 0). This file tracks the in-flight execution.

- [x] 0.1 Confirm trade-50 divergence is data-refresh-driven (golden exit_reason was "End of Data" on 2026-05-22, same day data ended), then regenerate golden ledger — 51 trades, share_multiple 12.689, matches fresh engine
- [x] 0.2 Unify champion selection on montauk_score — certify_champion.py `_pick_montauk_leader` (confidence tie-break), ops/daily + strategy_review tie-breaks, tests updated to Montauk contract; both selectors pick Jade Bonobo on live board
- [x] 0.3 Fix sync_packaged_status.py — added `import os`, sort key now (montauk, all-era, fitness) matching evolve contract; compiles
- [x] 0.4 Added `backtesting>=0.3.3` to requirements + installed in venv; shadow comparator verified executing live (passed, status: pass)
- [x] 0.5 Added root Makefile `make test` (venv python, fails loud) + CI test gate in spike.yml; also fixed broken CI optimizer path (`scripts/spike_runner.py` → `scripts/search/spike_runner.py`)
- [x] 0.6 Full suite green: 78 passed, 0 failed via `make test`
