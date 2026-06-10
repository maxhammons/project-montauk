# Phase 2 — Real overfitting defenses (execution tracker)

Canonical plan: `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md` (Phase 2).

- [x] 2.1 N_eff from hash-index: 4,116 measured (was hardcoded 300), ratcheting high-water mark in spike/n-eff-state.json
- [x] 2.2 Null distribution: 5,025 valid samples, cache keyed on engine hash + data-manifest fingerprint, Beta fit raises on infeasibility (no silent fallback)
- [x] 2.8 Morris signed elementary effects (sigma fixed); bootstrap resamples 200→1,000; geometric-zero veto documented honestly in thresholds doc
- [x] 2.9 Engine hash now includes data/manifest.json — data refresh invalidates GA cache hits
- [x] 2.3 scripts/validation/oos_walk_forward.py — true re-optimized WF; reclaimer avg OOS/IS 1.13 (concept re-tunes); wired as T2 sub-score (0.10), legacy walk_forward kept as temporal consistency
- [x] 2.4 scripts/validation/pbo.py — CSCV PBO (32 variants, 16 blocks, 200 splits); reclaimer PBO 0.615 (selection noisy though candidate robust at 0.97 OOS top-half); wired as T2 sub-score (0.05)
- [x] 2.5 backtest() gained execution_timing="next_open" (separate branch, default path byte-identical); execution_realism sub-score (0.10 all tiers, −15% budget); champion −12.2% PASS, reclaimer −12.6%
- [x] 2.7 analyze_event_dependence (COVID + 2022-bear splice-out); event_dependence sub-score (0.05 all tiers); champion COVID collapse 0.81 → critical warning + scored ~0.46
- [x] 2.6 docs/Montauk 2.0/deep-validation-report.md written — every CRITICAL ruled (resolved/policy/accepted-risk/open); full-era numbers demoted to diagnostic by policy; owner sign-off line pending
- [x] Pipeline wiring (gate_realism all tiers, gate_oos T2), weights added + renormalize, thresholds doc updated, suite green (79 passed)
