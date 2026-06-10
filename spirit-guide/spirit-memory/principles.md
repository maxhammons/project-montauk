# Principles

Rules, design laws, "always / never" statements. The commitments that shape every decision.

Populated automatically by the prompt-submit hook when the user states rules ("we always…", "never ship without…", "our principle is…"). Seeded at setup time from stated principles in raw docs if a seed source was provided.

Entries follow the format defined in `README.md`.

<!-- Entries below -->

## 2026-04-20-a
**Tags**: #process #tech #data
**Status**: active
**Important**: true
**Statement**: The leaderboard (`spike/leaderboard.json`) IS a certification. A strategy on the leaderboard is a binding statement that it is not overfit and is expected to work into the future under current rules. Nothing enters the leaderboard unless it clears the **entire** validation pipeline: the 7 gates (`promotion_ready=True`) AND every engine-level certification check (`engine_integrity`, `golden_regression`, `shadow_comparator`, `data_quality_precheck`). The `artifact_completeness` check is required for the champion only — it is a deployment concern, not a validity concern, and does not gate leaderboard admission for non-champion entries.
**Context**: Established after the GC Enhancement Matrix run (2026-04-20) surfaced overfit "champion-beaters" with high in-sample fitness but gate4/gate6 WARNs. The pipeline correctly rejected them; the leaderboard must reflect that. Enforced programmatically by `search/evolve.py::_is_leaderboard_eligible` + `REQUIRED_CERTIFICATION_CHECKS`. Re-certification utility: `scripts/certify/recertify_leaderboard.py`.
---

## 2026-04-20-b
**Tags**: #process #tech
**Status**: active
**Important**: true
**Statement**: The canonical pipeline has **exactly four phases**: (1) generate ideas [`scripts/search/`], (2) backtest + validate / check for overfitting [`scripts/validation/`], (3) if PASS certify + admit to leaderboard [`scripts/certify/`], (4) visualize in the UI [`viz/`]. Every Python script in `scripts/` belongs to one of seven named subfolders (`data`, `engine`, `strategies`, `search`, `validation`, `certify`, `diagnostics`). Single-use scripts do not live in `/tmp` or at the root — they either belong in the appropriate subfolder as a permanent entry point, or they get deleted after use. The `scripts/README.md` is the authoritative map.
**Context**: Established 2026-04-20 during the post-matrix cleanup. Before the restructure `scripts/` was a flat dump of 22 files; unclear which were load-bearing, which were single-use, which were orphans. The subfolder layout makes the pipeline phase of each file obvious from the path.
---

## 2026-06-09-a
**Tags**: #process #tech #data #vision
**Status**: active
**Important**: true
**Refs**: supersedes the artifact-scope sentence of principles#2026-04-20-a (artifact_completeness is now required for EVERY leaderboard row, verified on disk — the Gold contract won the conflict); operationalizes Max's 2026-06-09 statement.
**Statement**: Gold certified means: **fit to trade, beats B&H, and has the full confidence of the system.** Operationalized: (1) fit to trade — Layer-1 correctness proven by *executed* checks (prefix-consistency lookahead/repaint, fill-contract, single-position, golden regression, shadow comparator, data quality) and the next-open execution-realism budget respected; (2) beats B&H — share multiple ≥ 1.0 in full, real, AND modern eras under current data; (3) full confidence — composite ≥ 0.70 across every honest anti-overfit defense (measured-N_eff deflation, CSCV/PBO, true re-optimized walk-forward, event dependence, fragility, bootstrap), artifact bundle verified on disk, AND continuously falsified going forward: hash-chained signal log, fills reconciliation, live auto-demotion the moment live evidence breaches thresholds. "Full confidence" is the system's highest attainable, continuously re-earned confidence — not a guarantee of future returns, which no honest system can issue.
**Context**: Phase 4 of the 2026-06-09 gold-standard remediation. Max's directive while launching the board re-certification under the hardened rules. Replaces the earlier "binding statement that it is not overfit and is expected to work into the future" phrasing with a falsifiable contract: the forward-looking half of the promise is carried by live demotion, not by the backtest.
---
