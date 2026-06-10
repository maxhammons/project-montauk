# Evolve.py: early filter + parallel population eval + successive halving

- [x] Create `scripts/search/early_filter.py` (pure decision logic: filter_decision, halving math, pruned cache entry)
- [x] Evolve.py feature A: post-chunk validation-aligned early filter (both GA + bayesian paths), `early_filter=True` param, compact report, cache fitness penalty
- [x] Evolve.py feature B: fork-pool parallel population evaluation (`workers` param, per-chunk pool, parent-side dedup, serial fallback)
- [x] Evolve.py feature C: successive halving via modern-era screen (`halving=True` param, off below pop 16, pruned hash-index entries)
- [x] Tests: `tests/test_evolve_search.py` (filter decisions, halving math, pruned-entry shape/seeding) — 36 new tests
- [x] Benchmark: gc_vjatr_airbag, pop 40, 2 generations — 1,125 → 7,903 cand/min (7.0x), 0 parity mismatches
- [x] `make test` green — 174 passed (was 138)
