# Project Montauk — Project Status

> As of 2026-04-29

---

## 1. Current Project Identity

The project is no longer best described as "an EMA strategy with some optimizer scripts around it."

The correct framing is:

> Project Montauk is a TECL share-accumulation factory: discover long-only TECL strategies that match the hand-marked cycle shape, validate them at the tier appropriate to how they were selected, emit a `backtest_certified` signal bundle, and admit only Gold Status strategies to the authority leaderboard.

That is now the standard the codebase should be measured against.

---

## 2. What Is True Today

### Discovery is real

The repo can search across multiple TECL strategy families rather than only tuning `montauk_821`. The optimizer (Spike → Montauk Engine) is operational with a reusable hash index, leaderboard, and chunked iterative mode.

### Promotion gating exists in the canonical full-run path

The local full-run flow distinguishes between:

- raw optimizer output
- validated output

Only Gold Status entries are intended to become promotable leaderboard memory. PASS entries are certification candidates, not authority rows.

### Signal certification exists (2026-04-15)

A validated winner emits a `backtest_certified` signal bundle: the five standardized run artifacts (`trade_ledger.json`, `signal_series.json`, `equity_curve.json`, `validation_summary.json`, `dashboard_data.json`) plus the native HTML viewer built from `dashboard_data.json`. Certification requires engine integrity, golden regression pass, shadow-comparator agreement, data-quality pre-check pass, and artifact completeness. `promotion_ready` layers the tier-appropriate validation stack on top of that. Execution is manual brokerage from the daily risk_on / risk_off output; there is no external charting or execution surface in the pipeline.

### Gold Status leaderboard contract (2026-04-28)

`spike/leaderboard.json` is an authority surface, not a watchlist. A row belongs there only when it has Gold Status:

- final validation verdict `PASS`
- `certified_not_overfit=True`
- `backtest_certified=True` / complete standardized artifacts
- `share_multiple`, `real_share_multiple`, and `modern_share_multiple` all >= 1.0 versus B&H

Rows that are PASS but not artifact-backed, or that lose to B&H in any canonical era, remain research/certification artifacts outside the leaderboard.

### Timing-repair research lane (2026-04-28)

`gc_vjatr_timing_repair` is a small explicit post-drawdown repair module, separate from `gc_vjatr_reclaimer`. Its job is to test whether marker timing can be improved without forcing the reclaimer overlay to solve both economics and timing.

The first fitness-ranked grid pass searched 3,888 configurations; 1,310 passed the charter prefilter. The top 10 validation candidates all returned `PASS` with `certified_not_overfit=True`. The top representative was then packaged through `scripts/certify/certify_champion.py`, emitted the five standardized artifacts under `spike/runs/157/`, and entered the authority leaderboard as Gold Status row `Ivory Hare`. Certified economics are roughly 10.63x full-history, 1.55x real-era, 2.24x modern-era, 44 trades, and composite confidence 0.767.

The first Gold diversity audit found that `Ivory Hare` is currently the most distinct Gold row by risk-on correlation and trade overlap, but the leaderboard is still highly concentrated: 6 of 8 rows are `gc_vjatr` and the family HHI is 0.594 (effective families 1.68). The overlay-on-Bonobo matrix shows timing repair improves marker timing when grafted onto Bonobo bases, but it fails retention thresholds by degrading full-history, real-era, or modern-era performance. Treat it as a separate Gold family, not as a replacement exit/entry patch for Bonobo.

The first Gold-only ensemble audit did not produce a certification target. The best simple vote was `Obsidian Osprey + Marbled Bonobo + Ivory Hare` at 2-of-3, with all-era-positive economics (21.21x full, 1.33x real, 2.24x modern) and better real-era robustness than `Obsidian Osprey`, but it cut full-history performance to ~51% of the champion and modern performance to ~87%. This is useful as a defensive portfolio diagnostic, not yet an authority leaderboard candidate.

The airbag and state-filter overlays were repaired so they no longer inherit full standalone exit behavior, but a diagnostic profile still found zero charter-pass candidates in the sampled grids because real-era and modern-era performance degrade below 1.0. They should stay in the diagnostic/research lane until redesigned as less destructive filters.

### Diversity-prefilter research lane (2026-04-29)

`scripts/diagnostics/diversity_prefilter_search.py` is now the dedicated "third independent Gold family" search tool. It reuses `search.grid_search.GRIDS`, runs multicore via `--workers`, anchors against current Gold rows, and ranks candidates by all-era economics plus risk-state/trade-date distance from Gold anchors. It is a research screen, not an admission path.

The strict focused scan searched 679 non-Bonobo overlay/concept configurations with 8 workers and found zero survivors. The strict broad non-`gc_` scan searched 2,407 valid configurations and also found zero survivors; every rejection happened at the all-era economics floor before diversity checks. Best near misses were `vol_calm_regime` (`weighted_era_fitness=0.739`) and `vj_or_slope_meta` (`0.735`), but they still fail the Gold economic contract because one or more canonical eras remain below B&H.

A relaxed diagnostic run at `min_weighted_era_fitness=0.6` produced 9 research survivors (`rsi_regime_canonical`, `atr_ratio_vix`, and `vj_or_slope_meta` variants). These are useful for studying independent timing behavior, but none is certification-ready. The immediate conclusion is that the current non-`gc_` grid library is failing economics more than diversity. The next productive work is either redesigning the best near-miss families around real/modern era robustness or adding genuinely new external/breadth features, not promoting relaxed survivors.

`scripts/diagnostics/near_miss_autopsy.py` now explains why the best near misses fail. The first autopsy covered `vol_calm_regime`, `vj_or_slope_meta`, `rsi_regime_canonical`, and `atr_ratio_vix`. The common damage pattern is missed or undercaptured rebound participation: all four underperform B&H in `2023_rebound`; three also underperform in `2020_meltup`. `rsi_regime_canonical` is the most independent candidate by Gold-anchor distance (`diversity_score=0.945`), but it is too defensive in rebound years. `atr_ratio_vix` and `vj_or_slope_meta` have strong full-history economics, but real-era and modern-era share multiples remain far below 1.0. The next search should force modern/rebound capture into the strategy logic rather than only penalizing it after the fact.

Follow-up rebound repair work added `rsi_rebound_participation` and `atr_ratio_vix_rebound`. The RSI repair underperformed the original canonical RSI lane (`best_weighted_era_fitness=0.454`), so it should stay research-only. ATR/VIX rebound repair was more promising: a focused grid found 44 weighted-era charter-pass rows and 10/10 validation PASS candidates, including raw engine-era rows that beat B&H in full, real, and modern eras. However, canonical leaderboard multi-era reruns reduced the best candidate to real=0.4267 and modern=0.8734, so it is not Gold. This exposed and fixed a process bug: certification and leaderboard sync now re-check Gold eligibility after canonical multi-era metric rewriting, preventing stale `gold_status=True` rows.

Grid validation now reports raw engine-era metrics beside canonical standalone era reruns before admission. Re-running `atr_ratio_vix_rebound` confirmed the gap is semantic, not a dead process or random validation error: the fitness-ranked pass still produced 10/10 validation PASS rows, but 0/10 remained canonical Gold candidates; the best raw all-era row (`19.43/1.07/1.67`) canonicalized to `19.43/0.43/0.87`. A marker-timing ranked pass also failed the same canonical check (4 PASS, 1 WARN, 0/5 canonical Gold candidates), so this lane is useful diagnostic evidence but not a promotion path.

> **Historical note**: the previous code-generation and parity-checking workflow was removed in Phase 2 of the Montauk 2.0 project (see `docs/Montauk 2.0/` for full provenance).

### Deployment-context modeling exists as a separate concern

The Roth overlay model can sit on top of a validated binary TECL signal without changing the identity of the strategy.

---

## 3. What Just Changed (2026-04-21 validation overhaul)

The previous 7-gate pass/fail framework was replaced with a two-layer confidence
model after the "nothing gets through except strategies I don't trust" problem
became persistent. See `docs/validation-philosophy.md` for the full framework.

Summary of the shift:

- **Layer 1 (correctness, binary hard-fail)**: engine integrity, golden regression,
  data quality, charter guardrails, `share_multiple ≥ 1.0`, registry membership,
  degeneracy.
- **Layer 2 (confidence, weighted geometric mean ∈ [0, 1])**: every non-correctness
  gate emits a smooth sub-score that contributes weighted partial credit. The
  composite drives the verdict.
- **Admission tiers**: 0–39 Reject · 40–59 Research · 60–69 Watchlist · 70–89
  certified candidate · 90+ high confidence candidate. Leaderboard shows only
  Gold Status rows.
- **Per-cycle magnitude-weighted marker timing** is a new first-class sub-score
  (0.15 T2 weight). This is what penalizes strategies that are late on COVID,
  late on 2022, or missed the 2025 tariff — previously averaged away in
  state_agreement. See `scripts/strategies/markers.py::_magnitude_weighted_timing_score`.
- **Named-window performance** split out from walk-forward as its own sub-score
  (0.10 T2 weight).
- **Cross-asset demoted** from hard-fail to 0.05 weighted input. Rationale:
  TECL is 3× leveraged and uniquely volatile; cross-asset is a useful but
  non-definitive signal, not a bouncer.
- **Trade sufficiency anchors relaxed** (0/10/20 instead of 0/25/40) to honor
  charter's "low-frequency strategies are not punished" principle.
- **Leaderboard admission** is now Gold Status only. Confidence and fitness
  rank rows only after the Gold contract is satisfied.
- **15/15 existing entries rescored**; 5 Admitted, 10 Watchlist, 0 Rejected.
  `gc_vjbb`'s manual admission is no longer needed — it scores 65.6 (watchlist)
  organically. The ranking inverts from fitness-dominant (raw shares) to
  quality-dominant (per-cycle timing + named-window robustness).

---

## 3b. What Changed Earlier (2026-04-13 charter revision)

The spirit-guide was revised to address a structural mismatch: the validation framework was calibrated for high-DOF GA winners and was being applied uniformly to all candidates, including simple human-authored hypotheses. This punished the wrong thing and effectively closed the door on small, conceptually motivated strategies.

The revision introduces:

- **Share-count multiplier vs B&H** (`share_multiple`) as the primary metric (replacing the dollar `vs_bah` multiple as the optimization target; the deprecated `vs_bah_multiple` alias was retired in Phase 7)
- **Marker shape alignment** as a first-class validation gate (replacing the ±5% soft-prior nudge)
- **Three validation tiers**: T0 (Hypothesis), T1 (Tuned), T2 (Discovered) with strict canonical parameter set for T0
- **Tier routing**: validation difficulty matches selection bias
- **Removal of trade-frequency punishment** for low-trade strategies
- **Naming**: Spike is the skill; Spike launches and runs the Montauk Engine

The existing T2 statistical stack stays intact. It is not wrong — it is just being scoped to its actual job (large-search-budget candidates).

---

## 4. What Is Still Incomplete

### Tier routing — implemented (2026-04-13)

`canonical_params.py` defines the strict canonical set plus `effective_tier()`. `strategies.STRATEGY_TIERS` carries the declared tier per strategy (all current entries default to T2). `validation/pipeline.py` routes by tier in `_validate_entry`: T0 skips gates 2/3/5, T1 skips gates 2/5, T2 runs the full stack. All three tiers run gate 1 (tier-aware thresholds), the marker gate, gate 4 (walk-forward), and gate 6 (cross-asset). The composite confidence renormalizes over present gates.

### Marker shape gate — implemented (2026-04-13)

`_gate_marker_shape` in `validation/pipeline.py` runs for every tier. Reuses `discovery_markers.score_marker_alignment`. Thresholds: T0 state_agreement ≥ 0.75 + 0 missed cycles; T1 ≥ 0.70 + ≤ 1; T2 ≥ 0.65 + ≤ 2. Failure is a hard fail at gate level, not a nudge.

### Share-count metric — implemented (2026-04-13, codified 2026-04-15)

Math identity established: `share_multiple` equals the share-count multiplier when equity is marked-to-market. `strategy_engine.BacktestResult` exposes `share_multiple` as the sole attribute name (the deprecated `vs_bah_multiple` alias was retired in Phase 7). Fitness formula renamed and reframed. `trade_scale` low-trade penalty removed. `discovery_score_value` retired as a nudge — now an alias for fitness so the marker operates at the gate level instead.

### Engine trust — golden regression + shadow comparator (2026-04-15, Montauk 2.0 Phase 1)

The Python engine is now the single source of truth. Trust is established via four mechanisms:

- **Indicator unit tests** (`tests/test_indicators.py`): every indicator in `scripts/strategy_engine.py` (`ema`, `tema`, `atr`, `adx`, `_ema`) is pinned to hand-calculated reference values. Both engines must produce bit-identical EMAs on identical input.
- **Golden trade regression** (`tests/test_regression.py` + `tests/golden_trades_821.json`): every trade from a default-8.2.1 run is frozen. Any future change must match ±0.001% PnL per trade or explicitly regenerate the baseline.
- **Shadow comparator** (`tests/test_shadow_comparator.py`): dev-only second opinion that runs the same 8.2.1 config through `backtesting.py` / `vectorbt` and asserts agreement within 0.5% per trade. Catches systemic bugs that pinned tests miss.
- **Slippage unification** (Phase 1c): both engines now apply 5 bps on entry and exit, producing identical trades on 8.2.1 defaults. The monolithic `backtest_engine.run_backtest()` remains the canonical 8.2.1 path; `strategy_engine.backtest()` is the simpler per-candidate path the evolutionary search uses. Phase 7 will collapse them into one.

### Final deployment is manual brokerage

Acceptable, by design. The factory ends at validated champion → `backtest_certified` signal bundle → daily risk_on / risk_off output → manual brokerage execution. No broker API, no auto-deploy.

---

## 5. Current Strategic Risks

### Validation gates that don't fit the candidate

~~Until tier routing lands in code, the project will continue to over-validate simple hypotheses and under-validate large-search winners.~~ Closed 2026-04-13 (tier routing) and 2026-04-21 (confidence-score framework). Validation is now tier-routed and weighted; no single gate has veto power outside Layer 1 correctness.

### Strategy-family concentration is still a real risk

If too much of the validated memory depends on one idea cluster, the project can fool itself into thinking it has diversity when it only has variants.

### Documentation / code drift

The next implementation sprint must close the gap between what the spirit-guide now requires and what the scripts actually do. Until then, the docs lead the code.

---

## 6. Immediate Priorities

1. ~~Implement T0 / T1 / T2 tier routing in the validation pipeline.~~ ✓ 2026-04-13
2. ~~Implement strict canonical parameter set check for T0.~~ ✓ 2026-04-13 (`canonical_params.py`)
3. ~~Add share-count multiplier as the primary metric.~~ ✓ 2026-04-13 (math identity — already computed as `vs_bah_multiple`, renamed and reframed)
4. ~~Promote marker shape alignment to a first-class validation gate at every tier.~~ ✓ 2026-04-13 (`_gate_marker_shape`)
5. ~~Remove low-trade-frequency punishment from fitness and gates.~~ ✓ 2026-04-13 (`trade_scale` removed; gate1 tier-aware)
6. Author a real T0 hypothesis strategy (e.g. EMA-200 crossover with canonical params) to exercise the T0 pipeline end-to-end.
7. Update the `VALIDATION-THRESHOLDS.md` doc to split per tier now that the code supports it.
8. ~~Add formal parity checks against external execution surface.~~ Superseded 2026-04-15: external path removed. Replaced by engine trust stack (indicator unit tests + golden regression + shadow comparator + slippage unification) — see Montauk 2.0 Phase 1.
9. Keep the leaderboard Gold Status-only, with tier tags.
10. ~~Phase 7 engine consolidation — port full `montauk_821` semantics from `backtest_engine.py` into the modular `strategies.py` + `strategy_engine.py` pattern, drop the `vs_bah_multiple` alias.~~ Done 2026-04-15: `run_montauk_821()` now lives in `strategy_engine.py`, `backtest_engine.py` retains only regime-scoring helpers, `vs_bah_multiple` alias retired.

---

## 7. Plain-English Summary

Project Montauk already behaves like a promising strategy factory.

What it still needs is to become a **trustworthy and productive** strategy factory:

- broad discovery (search) AND fast hypothesis iteration (T0)
- tier-routed validation that matches selection bias
- the marker chart as the working definition of success
- share-count accumulation as the goal
- Gold Status-only promotion across all tiers
- `backtest_certified` signal bundle + native HTML viewer for the real winner
- deployment analysis that sits downstream of validation instead of corrupting it

That is the line between "interesting research repo" and "rock-solid guiding system."
