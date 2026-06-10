# Spike improvements — validation-aligned search, parallel eval, successive halving + roster curation

Approved by Max 2026-06-09. COMPLETE.

- [x] Shared indicator pool (`shared_indicators`) wired into run_eval + realism analyzer — fragility sweep 2.3s → 1.31s
- [x] #1 Validation-aligned early filter — chunk top-5 face next-open + COVID-exclusion checks; hard breach → excluded + cached fitness ×0.25; soft → ×0.85 + warning; per-chunk report; caught a real −30.3% breach in smoke
- [x] #2 Parallel evaluation — fork pool (cpu−2 workers), once per chunk, dedup in parent, serial fallback; 1,125 → 7,903 candidates/min (7x), 0/80 parity mismatches
- [x] #5 Successive halving — modern-era screen (800-bar warmup + MODERN_ERA_START), top max(8, 50%) promoted; pruned configs tombstoned in hash-index (N_eff counts them; seeding can't pick them); auto-off below pop 16
- [x] Benchmark recorded; `make test` 234 passed (138 → 174 → 234)
- [x] Roster curation: spike/search-roster.json retires 94 dead families from DEFAULT search (still registered: board integrity + null distribution intact; --strategies still works)
- [x] Replacement stock: 10 nh_ families authored against design-guide (VIX regime, macro curve/Fed, volume, XLK anchor, dd-scaled reclaim, 52w-high hysteresis, VIX reversion, dual timescale, vol-drag budget) — all smoke-pass, causal-verified, T1-tiered, ≤7 tunables; 3 beat champion-at-defaults out of the box
- [x] Active default roster: 15 families (5 proven gc_ + 10 nh_)
- [ ] Follow-up (flagged): pipeline.md spike-section doc-sync for early-filter/halving/roster
