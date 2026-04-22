# Futurist Investigation

## Primary Claim

Montauk's likely 18-month failure is semantic lock-in, not raw strategy logic. The repo is operationalizing a confidence-ranked, multi-strategy future, but the persisted artifacts, admission code, and project memory still disagree about what a leaderboard row means. If that disagreement hardens now, future tightening will require migrating state, relabeling operator trust, and reinterpreting history all at once.

## Observations

### 1. `promotion_ready` and `backtest_certified` no longer mean what the docs say they mean

`docs/validation-philosophy.md` says `backtest_certified` is the correctness flag and `promotion_ready = backtest_certified AND confidence >= 0.70`. The implementation in `scripts/validation/pipeline.py::_gate7_synthesis()` does something else: `promotion_ready = verdict == "PASS"`, then `backtest_certified = promotion_ready AND all(certification_checks)`. That inversion matters because the project is now admitting on confidence first and certification second.

Trace this forward. Once several people are reading reports and leaderboard rows, they will internalize `PASS` and `promotion_ready` as deployable truth. Tightening the contract later will not be a code cleanup; it will be a trust migration.

### 2. The live leaderboard is already storing admitted-but-not-certified rows as normal operating state

The current `spike/leaderboard.json` is not a corner case. A census of the file shows 20 entries, all 20 with `verdict="PASS"` and `promotion_ready=true`, and all 20 with `backtest_certified=false`. The only failing certification check across the board is `artifact_completeness`.

That is the exact kind of shape I worry about: not a bug that crashes, but a new operational truth quietly taking hold. The board now behaves like "confidence-admitted memory" while multiple docs still describe it as certification memory. If Montauk keeps this shape for six months, changing the terms later will require re-explaining the last six months of results.

### 3. Cross-asset has already lost authority but still keeps its operational footprint

`scripts/validation/cross_asset.py` still describes cross-asset as the strongest anti-overfitting test. `scripts/validation/pipeline.py::_gate6_cross_asset()` still runs same-parameter replay plus TQQQ re-optimization. But `_geometric_composite()` explicitly removes `cross_asset` from the composite weights, and `_gate6_cross_asset()` now emits warnings rather than vetoes.

This is exactly how a future throughput tax is born. The check still costs compute and mindshare, but because it no longer decides anything load-bearing, the team will either ignore it or resent it. In 18 months that usually ends one of two ways: quiet bypasses, or a rushed late deletion after habits and docs have grown around it.

### 4. The validation spec is already contradictory enough to create historical ambiguity

`docs/validation-thresholds.md` says `cross_asset` was removed from the composite, but its effective-weight table still includes `cross_asset` and omits `era_consistency`. `docs/validation-philosophy.md` still describes T0 using `cross_asset` in its composite summary. `docs/project-status.md` says "Keep the leaderboard PASS-only" while the new framework explicitly supports watchlist rows and the admission code in `scripts/search/evolve.py::_is_leaderboard_eligible()` allows `composite_confidence >= 0.60`.

This is not cosmetic drift. This is how you lose the ability to answer a basic future question: "What rules admitted this row?" Montauk is heading toward an operational research system. Systems in that stage need semantic provenance, not just better prose.

### 5. A known missing seam in Gate 2 will become expensive exactly when the team broadens authored strategy work

`scripts/validation/pipeline.py` has a live TODO to split Gate 2 into result-quality checks and T2-only search-bias corrections. Today T1 skips Gate 2 entirely, even though the code comments admit some of those result-quality checks would still be informative for T1.

This is the kind of decision that feels deferrable until the project adds more human-authored and grid-searched ideas. Then it stops being deferrable. At that point, adding the seam means retroactively reclassifying old T1 results and breaking comparability between "before split" and "after split" validation histories.

### 6. The multi-strategy future is described in prose, but the storage model is still single-family saturation

`docs/validation-philosophy.md` explicitly imagines a future oscillator where multiple strategies run simultaneously. The current leaderboard does not look like that future. All 20 rows in `spike/leaderboard.json` are `gc_vjatr` variants. `scripts/search/evolve.py::update_leaderboard()` deduplicates by config hash, not by strategy family, correlation, or conceptual exposure.

That means Montauk has ranking infrastructure, not portfolio infrastructure. If the next phase really is "7 of 25 strategies are calling sell," then family-level diversity, overlap, and provenance become first-class state contracts. None of those seams exist yet.

### 7. Re-certification rewrites history without recording the scoring regime that produced the new truth

`scripts/certify/recertify_leaderboard.py` backfills `real_share_multiple` and `modern_share_multiple` into legacy entries, re-runs validation under current rules, then overwrites `spike/leaderboard.json`. This is pragmatic and maybe necessary, but it is also a future lock-in signal: the system is comfortable mutating historical truth while not storing a validation-model version in the row.

The day Montauk changes thresholds again, the team will still be able to recertify. What it will not be able to do cleanly is compare eras of certification without reading code archaeology. That is a governance debt, not a documentation debt.

## What I investigated and ruled out

- I checked whether cross-asset still materially affects `composite_confidence`. It does not in code; it remains diagnostic/warning-bearing but not composite-bearing.
- I checked whether the current leaderboard's certification failures point to broad engine-trust collapse. They do not; the sampled board only fails `artifact_completeness`.
- I checked whether the live leaderboard already demonstrates the new watchlist tier in practice. It does not; current rows are all `PASS`, which means the watchlist semantics are code-ready but not yet the dominant stored reality.
- I checked whether legacy `vs_bah` compatibility is the main long-term schema trap. I did not find that in the current sampled rows; the more important long-term problem is absent validation-version provenance.
- I checked whether the repo is still narratively committed to a single champion future. It is mixed: some docs still are, but the newer validation philosophy clearly is not.

## What I would need to see to change my mind

- A single canonical contract, enforced in code and docs, that cleanly defines `verdict`, `promotion_ready`, `backtest_certified`, watchlist admission, and leaderboard eligibility without contradictions.
- Versioned validation metadata stored with leaderboard rows so future recertification does not silently erase which framework admitted a candidate.
- Either true deletion of cross-asset from the critical path, or restoration of real authority that justifies its runtime and narrative cost.
- A family/diversity layer on top of the leaderboard if the project is serious about the oscillator / multi-strategy future.
- The Gate 2 split implemented before T1 history gets large enough that backfilling it becomes a migration project.

## Bottom Line

The codebase is not headed toward an "overfitting detector that got a little softer." It is headed toward a memory-bearing decision system whose labels are beginning to diverge from its evidence model. That is survivable today because one person can hold the nuance in their head. It is exactly the sort of thing that becomes a six-week architectural correction once the team, artifact history, and candidate count all grow together.
