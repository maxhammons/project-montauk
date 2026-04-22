# Futurist Scratchpad

## Pass 1 Reading List
1. `docs/validation-philosophy.md`
   Hypothesis: the repo is narratively moving from single certified winner to a confidence-ranked portfolio/watchlist, but the operating language still borrows strict-gate terms.
   Expected signal: prose that separates "correctness" from "confidence" and legitimizes multiple deployable candidates.
2. `docs/validation-thresholds.md`
   Hypothesis: recent threshold changes kept the gate scaffolding but weakened the irreversible parts by demoting cross-asset and other structural checks into soft scoring.
   Expected signal: weights, renormalization, advisory-only language, and notes explaining why a formerly load-bearing gate no longer vetoes.
3. `scripts/validation/pipeline.py`
   Hypothesis: the implementation now codifies permissive semantics that are hard to tighten later because downstream artifacts, reports, and operator habits already consume `PASS`, `promotion_ready`, and `composite_confidence`.
   Expected signal: hard-fail logic limited to a narrow correctness core, with most future-facing checks feeding warnings or smooth subscores.
4. `scripts/validation/cross_asset.py`
   Hypothesis: Gate 6 still burns real runtime and conceptual budget while no longer acting as a true architectural brake.
   Expected signal: expensive same-param and re-opt flow whose results mostly become diagnostics.
5. `scripts/certify/recertify_leaderboard.py`
   Hypothesis: the leaderboard is being operationalized as durable state, which means today's validation semantics are becoming historical truth and future migration pain.
   Expected signal: routines that rewrite persisted leaderboard entries under current rules and normalize trust around stored JSON.
6. `spike/leaderboard.json`
   Hypothesis: persisted artifacts already encode mixed-era semantics (`vs_bah` legacy, newer confidence fields, warning-heavy winners), creating schema lock-in and interpretability debt.
   Expected signal: entries with legacy compatibility fields, advisory warnings, and validation outputs that imply softer admission rules than the names suggest.
7. `spirit-guide/spirit-memory/principles.md`
   Hypothesis: project memory still describes the leaderboard/certification boundary more strictly than the code now enforces.
   Expected signal: declarative statements that every leaderboard entry is a binding certification.

## Justified Expansion Budget
- Expansion A: `scripts/certify/full_sweep.py` if leaderboard recertification delegates key state semantics there.
- Expansion B: `scripts/diagnostics/report.py` if user-facing labels are shaping irreversible operator trust.
- Expansion C: `scripts/search/share_metric.py` if TECL-specific metric framing leaks into storage contracts.
- Expansion D: `docs/project-status.md` if current-state prose materially contradicts validation implementation.
- Expansion E: `CLAUDE.md` only for exact charter-language cross-checks already surfaced in Pass 0.

## North Star Readback
- North star says Montauk is becoming a trustworthy TECL decision factory, not just a search toy.
- The productive tension is explicit: docs still speak in single-champion terms while the newer system is drifting toward a confidence-ranked watchlist.
- From a Futurist lens, that matters because semantics adopted during operationalization are the ones that become hardest to unwind later.

## Pass 0 Lock-In Signals
- `CLAUDE.md` still anchors the product around TECL-only, long-only, single-position, manual execution, and `share_multiple` vs TECL buy-and-hold.
- `docs/validation-thresholds.md` already shows one meaningful softening: `cross_asset` removed from the composite on 2026-04-21 while still computed and reported.
- `scripts/validation/pipeline.py` contains a live TODO about splitting Gate 2 result-quality from T2-only search-bias logic, which suggests tier semantics are still fused.
- Artifact churn is extreme in `spike/`, so any schema or naming drift there compounds quickly.
- The world model already marks `scripts/validation/pipeline.py` and `spike/leaderboard.json` as the two unresolved hotspots.

## Working Scenario To Trace Forward
- Plausible 18-month future: the team expands from one operator to several collaborators, the strategy set grows from one "champion" to a portfolio of candidates, and recertification becomes routine rather than exceptional.
- In that future, the dangerous failure is not raw backtest speed. It is semantic lock-in: people trusting persisted PASS/certified labels that were produced under softer, shifting rules.
- The question I am testing is whether Montauk is building clean seams between hard correctness, advisory evidence, and stored operational truth.

## Initial Bets
- Best positive case: the repo is consciously separating correctness from confidence and just has stale language to clean up.
- Main risk case: the code is already storing a blended notion of truth, so future tightening will require artifact migrations, doc rewrites, and retraining operator intuition all at once.
- Secondary risk case: TECL-only focus is strategically fine, but demoting cross-asset while still talking about future generalization leaves the system without a clear replacement for "evidence beyond one tape."

## Questions To Resolve In Pass 2
- What exactly can still hard-fail a candidate?
- What does `promotion_ready` mean after the threshold revisions?
- Is `backtest_certified` reserved for correctness, or is it bleeding into deployment suitability?
- Does the leaderboard store enough provenance to reinterpret old entries under new rules?
- Where does the operator-facing report flatten nuance into durable labels?

## Notes Placeholder
- Pass 2 file findings go below.

## Pass 2 Findings
- `docs/validation-philosophy.md` is explicit that the future state is a confidence-ranked watchlist with multiple simultaneous strategies, not a single certified champion.
- The same file also says `backtest_certified` is the correctness flag and `promotion_ready = backtest_certified AND confidence >= 0.70`.
- `scripts/validation/pipeline.py::_gate7_synthesis()` does not implement that contract. It sets `promotion_ready = verdict == "PASS"` and only then computes `backtest_certified = promotion_ready AND all(certification_checks)`.
- Because `artifact_completeness` is always pending during validation, `backtest_certified` is structurally false inside the validation pass even when `promotion_ready` is true.
- Leaderboard census: 20 entries, 20 `PASS`, 20 `promotion_ready=True`, 20 `backtest_certified=False`, and the only failing certification check is `artifact_completeness`.
- That means the persisted board is already carrying operationally admitted entries that the code itself says are not fully certified.

## Cross-Asset Notes
- `scripts/validation/cross_asset.py` still frames cross-asset as "the single most powerful anti-overfitting test."
- `scripts/validation/pipeline.py::_gate6_cross_asset()` still runs both same-param replay and TQQQ re-optimization.
- `_geometric_composite()` removed `cross_asset` from the weights entirely on 2026-04-21.
- `docs/validation-thresholds.md` says the same in prose, but its effective-weight table still includes `cross_asset` and omits `era_consistency`, so the spec is already internally inconsistent.
- Futurist read: this is a classic future tax. The team is still paying runtime and conceptual cost for a check whose decision authority has already been politically removed.

## Gate 2 / Tier Notes
- `scripts/validation/pipeline.py` contains a live TODO: split Gate 2 into result-quality (should apply more broadly) and search-bias (T2-only).
- Current behavior: T1 skips Gate 2 entirely, even though the comment admits some bundled result-quality checks are informative at T1.
- This is a seam that does not exist yet. If authored/grid strategies become the main collaborative path, historical T1 results will be missing a class of evidence the team already knows it wants.

## Leaderboard State Notes
- `scripts/certify/recertify_leaderboard.py` still says a leaderboard entry is a binding statement that the strategy is not overfit and will work into the future.
- `spirit-guide/spirit-memory/principles.md` says the same.
- `scripts/search/evolve.py::_is_leaderboard_eligible()` now admits watchlist entries at `composite_confidence >= 0.60`, as long as required certification checks pass.
- `docs/project-status.md` still says "Keep the leaderboard PASS-only" and still frames the product around a `backtest_certified` bundle for the best PASS winner.
- So the memory layer, operator docs, and admission code are not describing the same object.

## Schema / Provenance Notes
- `spike/leaderboard.json` stores validation outputs, warnings, and certification checks, but no validation ruleset version or threshold version.
- `scripts/certify/recertify_leaderboard.py` backfills `real_share_multiple` / `modern_share_multiple` into legacy entries before re-running validation under current rules.
- That is practical, but it means the board is mutable historical truth without explicit provenance for which scoring regime admitted a row.
- If the team tightens rules later, there is no clean seam for "this score was produced under framework A, this one under framework B."

## Portfolio-Future Notes
- `docs/validation-philosophy.md` explicitly imagines a future oscillator where many strategies run simultaneously.
- Actual leaderboard census shows 20/20 entries are the same strategy family: `gc_vjatr`.
- `scripts/search/evolve.py::update_leaderboard()` deduplicates by config hash, not by family or conceptual exposure, so one family can fill the board.
- That means the system is not yet structurally prepared for the multi-strategy future it is narrating. It has ranking infrastructure, not portfolio infrastructure.

## Ruled-Out During Pass 2
- I looked for evidence that cross-asset still changes the composite materially. It does not; the weight is removed in code.
- I looked for evidence that current leaderboard failures come from broad engine-integrity problems. The current board only fails `artifact_completeness`.
- I looked for evidence that the current board already contains mixed watchlist/admitted states. It does not; all current rows are `PASS` even though code supports watchlist admission.
- I looked for evidence that old `vs_bah` compatibility is the current dominant schema problem. Current sampled leaderboard rows use `share_multiple`; the more important issue is missing validation-version provenance.

## Provisional Claim
- The future bottleneck is not that Montauk validates too loosely in the abstract.
- The future bottleneck is that it is freezing ambiguous semantics into durable state right as the project shifts from single-champion thinking to multi-strategy operational memory.
- If nothing changes, the 18-month rewrite will be about labels, provenance, and admission meaning, not indicator math.
