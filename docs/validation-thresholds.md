# Validation Gate Thresholds

> Canonical reference for every threshold in the validation pipeline.
> This file MUST stay in sync with `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, and `scripts/validation/uncertainty.py`.

---

## Tier Routing Overview

The pipeline runs seven gates plus a marker-shape diagnostic. Which gates run and how strict they are depends on the strategy's **effective tier** (computed by `canonical_params.effective_tier()` from the declared tier + actual params):

| Gate | T0 | T1 | T2 | What it checks |
|------|:--:|:--:|:--:|----------------|
| **Gate 1** — Eligibility | RUN (floor=5) | RUN (floor=10) | RUN (floor=15) | Charter gates, trade count, degeneracy |
| **Marker** — Shape diagnostic | RUN (cap=2, floor=0.50) | RUN (cap=3, floor=0.40) | RUN (cap=5, floor=0.30) | Cycle alignment vs TECL-markers.csv |
| **Gate 2** — Search bias | SKIP | SKIP | RUN | HHI, exit proximity, jackknife, meta robustness, clustering |
| **Gate 3** — Param fragility | SKIP | RUN | RUN | +/-10%/20% param perturbation swing |
| **Gate 4** — Time generalization | RUN (WF hard→soft) | RUN | RUN | Walk-forward OOS/IS, named windows |
| **Gate 5** — Uncertainty | SKIP | SKIP | RUN | Morris elementary effects, stationary bootstrap |
| **Gate 6** — Cross-asset | RUN | RUN | RUN | TQQQ/QQQ same-param, TQQQ re-optimization |
| **Gate 7** — Synthesis | RUN | RUN | RUN | Composite confidence, verdict, `backtest_certified`, `promotion_ready` |

**Skipped gates** return `verdict: "SKIPPED"` and contribute `None` sub-scores to the composite, which renormalizes over applicable gates only (no penalty for skipped gates).

### Tier auto-promotion

A strategy declared as T0 is auto-promoted to T1 if it has > 5 tunable params (excluding cooldown) or any non-canonical param value. A T1 is auto-promoted to T2 if it has > 8 tunable params. The declared tier is an upper bound on leniency.

---

## Param-Count Scaling Principle

> Added 2026-04-14. Applies across gates 2, 5, and 7.

Validation gates must distinguish between **overfitting signals** (parameter sensitivity from large searches) and **strategy characteristics** (inherent properties of trend-following). The proxy is **signal-param count** (tunable params excluding cooldown, via `canonical_params.count_tunable_params()`):

- **≤ 4 signal params ("simple")**: Relaxed thresholds on Morris fragility, concentration, bootstrap, and soft-warning cap. Limited search space = limited overfitting risk.
- **5+ signal params ("complex")**: Original strict thresholds. Large search spaces can find lucky combos.

---

## Verdict Logic (Gate 7 Synthesis)

### `backtest_certified` pre-check (runs before verdict)

Gate 7 computes `backtest_certified` before the final verdict. A strategy is certified when **all** of the following hold; any failure propagates hard-fail reasons into the gate 7 verdict:

| Check | Hard Fail | Pass |
|-------|-----------|------|
| Engine integrity (`scripts/validation/integrity.py`) | any failure | all checks pass |
| Golden regression (`tests/test_regression.py`) | trade-by-trade PnL divergence > ±0.001% on 8.2.1 defaults | match |
| Shadow comparator (dev-only) | per-trade divergence > 0.5% vs `backtesting.py` / `vectorbt` | within tolerance |
| Data-quality pre-check (`scripts/data_quality.py`) | any PASS/WARN/FAIL failure (Yahoo-vs-Stooq, seam continuity, manifest checksum, OHLC sanity, etc.) | all PASS |
| Artifact completeness | any of the five standardized JSON artifacts missing or malformed | all present |

Both engines now apply 0.05% slippage on each fill (unified in Phase 1c of Montauk 2.0), so the two engines produce identical trades on 8.2.1 defaults. `promotion_ready = backtest_certified AND tier-appropriate PASS`.

### Verdict rules

```
FAIL:   hard_fail_reasons present OR composite_confidence < 0.45
WARN:   critical_warnings present OR composite_confidence < 0.70 OR soft_warnings >= cap
PASS:   only soft_warnings (< cap) and/or advisories
```

**Soft-warning cap** (param-count aware):

| Condition | Cap | Rationale |
|-----------|:---:|-----------|
| Any tier with ≤ 4 signal params | 10 | Simple strategies emit many descriptive (non-overfit) warnings |
| 5+ signal params | 5 | Accumulated warnings signal real overfit risk |

`clean_pass = True` when verdict is PASS and zero soft warnings.

---

## Gate 1 — Candidate Eligibility

Source: `pipeline.py :: _gate1_candidate()`

**Tier-specific trade count floor:**

| Tier | Trade Floor | Rationale |
|------|:----------:|-----------|
| T0 | 5 | Hypothesis — just needs to engage |
| T1 | 10 | Tuned — more evidence required |
| T2 | 15 | Discovered — must prove not degenerate |

**All-tier hard gates (no tier variation):**

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Share multiplier (charter) | < 1.0 | — | >= 1.0 |
| Trade count | < tier floor | — | >= floor |
| Trades/year (charter) | > 5.0 | — | <= 5.0 |
| Degeneracy (4yr windows) | always-in or always-out across ALL windows | sparse/saturated in some windows | normal exposure |
| In strategy registry | not in registry | — | in registry |
| Charter-compatible | fails charter | — | passes |
| n_params vs regime_transitions | — | n_params > transitions | n_params <= transitions |

---

## Marker — Shape Diagnostic

Source: `pipeline.py :: _gate_marker_shape()`

**No hard fails at any tier.** Marker alignment is a design north star, not a bouncer.

**Universal thresholds (all tiers):**

| Check | Critical Warning | Soft Warning | Pass |
|-------|-----------------|--------------|------|
| state_agreement | < 0.30 (uncorrelated) | < 0.50 (barely above random) | >= 0.50 |

**Tier-specific informational thresholds (soft warnings only):**

| Tier | Missed cycles cap | Timing floor |
|------|:-----------------:|:------------:|
| T0 | > 2 | < 0.50 |
| T1 | > 3 | < 0.40 |
| T2 | > 5 | < 0.30 |

---

## Gate 2 — Search Bias & Regime Memorization

Source: `pipeline.py :: _gate2_search_bias()`

**Runs at T2 only.** T0 and T1 skip this gate entirely. (TODO: split result-quality checks from search-bias checks so result-quality can run at T1.)

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Exit-boundary proximity | enrichment > 3.0x | — | — | <= 3.0x |
| Jackknife | max_impact_ratio > 2.0x | — | — | <= 2.0x |
| Meta robustness (28 defs) | — | < 50% within 20% of baseline | 50% - 75% | >= 75% |
| Trade clustering | — | max_share > 0.60 | — | <= 0.60 |
| Selection bias | — | — | advisory only | — |

**Concentration (HHI) — param-count aware:**

| Condition | Critical Warning | Soft Warning |
|-----------|-----------------|--------------|
| **≤ 4 signal params** | dominance > 3.0 only | bull_flag OR bear_flag OR dom > 2.0 |
| **5+ signal params** | bull_flag OR bear_flag OR dom > 3.0 | dom > 2.0 |

HHI thresholds: `bull_thresh = 1.5 / n_bull`, `bear_thresh = 1.5 / n_bear`. Bull/bear flags fire when HHI exceeds the per-cycle threshold.

> **Why softer for simple strategies:** Trend-following inherently has concentrated returns — a few huge bull runs dominate. With ≤ 4 signal params, this is the strategy type's return profile, not overfitting.

---

## Gate 3 — Parameter Fragility

Source: `candidate.py :: check_parameter_fragility()`, wrapped by `pipeline.py :: _gate3_fragility()`

**Runs at T1 and T2 only.** T0 skips (canonical params are pre-registered, perturbation testing is moot).

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Any param +/-10% swing | > 30% | > 20% | <= 20% |

Perturbation levels tested: +/-10%, +/-20%.

---

## Gate 4 — Time Generalization

Source: `pipeline.py :: _gate4_time_generalization()`

**Runs at all tiers** with tier-aware strictness.

### Walk-Forward

Windows: WF 2015-2017, WF 2018-2020, WF 2021-2023, WF 2024-present (dynamic).

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Per-window OOS/IS regime ratio | < 0.65 | — | — | >= 0.65 |
| Zero OOS trades (expected >= 1.5) | yes | — | — | has trades |
| Zero OOS trades (expected < 1.5) | — | — | yes | has trades |
| Avg OOS/IS ratio | < 0.50 | < 0.65 | — | >= 0.65 |
| Dispersion (max - min) | — | > 0.75 | > 0.65 | <= 0.65 |

**T0 demotion:** At T0, all walk-forward `hard_fail_reasons` are demoted to `soft_warnings` (prefixed with `[T0 demoted]`). Rationale: a WF drop at T2 means the GA fit the IS period and OOS degraded (classic overfit). At T0, it means the committed canonical hypothesis performed inconsistently across time — informative but not overfit.

Named-window hard fails still apply at all tiers.

### Named Windows

Windows: 2020_meltup, 2021_2022_bear, 2023_rebound, 2024_onward.

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Error | yes | — | — |
| share_multiple <= 0 | yes | — | — |
| Zero trades (sat out, share_multiple > 0) | — | yes | — |
| share_multiple | — | < 0.60 | >= 0.60 |

---

## Gate 5 — Uncertainty

Source: `pipeline.py :: _gate5_uncertainty()`, `uncertainty.py`

**Runs at T2 only.** T0 and T1 skip this gate entirely.

### Morris Elementary Effects

30 trajectories, +/-20% delta. Signal-param count excludes cooldown.

**Thresholds scale by signal-param count:**

| Signal params | Interaction (Hard Fail) | Warning (Critical) | Rationale |
|:------------:|------------------------|-------------------|-----------|
| **≤ 2** | max_swing > 0.50 | max_swing > 0.35 | Each param is ~50% of variance; sigma_ratio naturally inflated |
| **3-4** | swing > 0.40 OR (sigma_ratio > 2.0 AND swing > 0.25) | swing > 0.25 OR sigma_ratio > 1.5 | Limited overfit potential |
| **5+** | swing > 0.30 OR (sigma_ratio > 1.5 AND swing > 0.20) | swing > 0.20 OR sigma_ratio > 1.0 | Original thresholds for complex strategies |

Warning flags with `max_swing < 0.10` are dropped as noise (no warning emitted).

`s_frag = clamp(1.0 - max_swing / 0.40)`.

### Stationary Bootstrap

200 resamples, expected block length 20.

**Thresholds scale by signal-param count:**

| Check | Hard Fail | Critical (5+ params) | Critical (≤ 4 params) | Soft Warning | Pass |
|-------|-----------|---------------------|----------------------|--------------|------|
| Downside prob | > 0.50 | > 0.40 | > 0.50 (matches hard-fail) | > 0.25 or s_boot < 0.20 | <= 0.25 and s_boot >= 0.20 |

`s_boot = clamp(1.0 - ci_width / observed_rs)`.

> **Why softer for simple strategies:** Bootstrap variance for trend-following reflects inherent uncertainty of catching a few big moves, not parameter overfitting. The hard-fail line (> 0.50) is the meaningful threshold for simple strategies.

---

## Gate 6 — Cross-Asset

Source: `pipeline.py :: _gate6_cross_asset()`

**Runs at all tiers.** No tier-specific variation in thresholds.

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| TQQQ same-param share_multiple | < 0.50 (or error) | 0.50 - 1.00 | >= 1.00 |
| QQQ same-param share_multiple | — | < 0.50 (or error) | >= 0.50 |
| TQQQ re-optimization (tier3) | share_multiple < 1.0 | — | >= 1.0 |

Tier3 re-opt budget scales with run hours: 0.5m/pop12 (quick), up to 2.0m/pop24 (long).

---

## Composite Confidence (Gate 7)

Source: `pipeline.py :: _geometric_composite()`

Weighted geometric mean of sub-scores. Skipped gates contribute `None` and are excluded (weights renormalize).

| Sub-score | Weight | Source gate | T0 | T1 | T2 |
|-----------|:------:|:----------:|:--:|:--:|:--:|
| marker_shape | 0.20 | Marker | Y | Y | Y |
| walk_forward | 0.20 | Gate 4 | Y | Y | Y |
| fragility | 0.20 | Gate 5 Morris (fallback: Gate 3) | — | Y (G3) | Y (G5) |
| selection_bias | 0.15 | Gate 2 | — | — | Y |
| cross_asset | 0.10 | Gate 6 | Y | Y | Y |
| bootstrap | 0.05 | Gate 5 | — | — | Y |
| regime_consistency | 0.05 | Gate 2 | — | — | Y |
| trade_sufficiency | 0.05 | Gate 1 (trade count) | Y | Y | Y |

**Effective composite weights per tier** (after renormalization of applicable gates):

| Sub-score | T0 effective | T1 effective | T2 effective |
|-----------|:-----------:|:-----------:|:-----------:|
| marker_shape | 0.364 | 0.267 | 0.200 |
| walk_forward | 0.364 | 0.267 | 0.200 |
| fragility | — | 0.267 | 0.200 |
| selection_bias | — | — | 0.150 |
| cross_asset | 0.182 | 0.133 | 0.100 |
| bootstrap | — | — | 0.050 |
| regime_consistency | — | — | 0.050 |
| trade_sufficiency | 0.091 | 0.067 | 0.050 |

T0 composite is dominated by marker_shape + walk_forward (73%). T1 is evenly split across marker/WF/fragility (80%). T2 distributes across all 8 sub-scores.

---

## Per-Tier Summary

### T0 — Hypothesis (pre-registered canonical params)

**Gates that run:** 1, Marker, 4, 6, 7
**Gates skipped:** 2 (search bias), 3 (param fragility), 5 (uncertainty)
**Special behavior:**
- Gate 1 trade floor: 5
- Gate 4 walk-forward hard fails demoted to soft warnings
- Marker missed-cycle cap: 2, timing floor: 0.50
- Soft-warning cap: 10

**Design intent:** T0 cannot overfit (canonical pre-registered params, no tuning). Validation confirms the hypothesis engages cycles, generalizes across time and assets, and emits a complete `backtest_certified` signal bundle. Statistical overfitting tests are irrelevant.

### T1 — Tuned (hand-authored logic, canonical grid search)

**Gates that run:** 1, Marker, 3, 4, 6, 7
**Gates skipped:** 2 (search bias — calibrated for 50K+ GA configs), 5 (uncertainty — T2 only)
**Special behavior:**
- Gate 1 trade floor: 10
- Gate 3 param fragility runs (params were grid-searched, perturbation matters)
- Marker missed-cycle cap: 3, timing floor: 0.40
- Soft-warning cap: 10 if ≤ 4 signal params, else 5

**Design intent:** T1 strategies have been searched over a small canonical grid (~50 combos). Fragility testing catches lucky combos. Search-bias and bootstrap aren't calibrated for small grids so they're skipped.

### T2 — Discovered (GA-searched, complex param spaces)

**Gates that run:** All (1, Marker, 2, 3, 4, 5, 6, 7)
**Gates skipped:** None
**Special behavior:**
- Gate 1 trade floor: 15
- Gate 2 runs full search-bias stack (exit proximity, jackknife, HHI, meta robustness, clustering)
- Gate 5 runs full uncertainty stack (Morris elementary effects, stationary bootstrap)
- Marker missed-cycle cap: 5, timing floor: 0.30
- Concentration, Morris, and bootstrap thresholds scale by signal-param count (≤ 4 vs 5+)
- Soft-warning cap: 10 if ≤ 4 signal params, else 5

**Design intent:** T2 strategies emerged from large search spaces (50K+ GA evaluations). Every statistical test fires to detect overfitting, data snooping, and parameter fragility. The full gauntlet.

---

## Warning Taxonomy

| Level | Effect on verdict | When to use |
|-------|-------------------|-------------|
| **Advisory** | None | FYI only — informational context |
| **Soft Warning** | WARN if count >= cap | Marginal concerns, descriptive observations |
| **Critical Warning** | Always WARN (blocks PASS) | Structural concern that isn't disqualifying but prevents promotion |
| **Hard Fail** | Always FAIL | Disqualifying — strategy cannot be promoted or deployed |

---

## Design Principle: Overfitting vs Strategy Characteristics

The validation pipeline exists to catch overfitting. Not every "bad-looking" metric is an overfitting signal:

| Metric | Overfitting signal (penalize) | Strategy characteristic (don't penalize) |
|--------|------------------------------|----------------------------------------|
| High param sensitivity | Result depends on a lucky combo from 50K GA evaluations | Each param in a 2-param strategy naturally accounts for 50% of variance |
| Concentrated returns (HHI) | One lucky trade in one lucky window drives the whole result | Trend-following inherently captures a few big moves |
| Bootstrap uncertainty | Resampled performance collapses — the "edge" was noise | Trend-following has wide confidence intervals by nature |
| Soft warning accumulation | Many marginal signals compound into overfit suspicion | Simple strategies emit descriptive warnings (marker timing, window performance) that are informational |

**Current proxy:** signal-param count (≤ 4 = simple, 5+ = complex). **Better future proxy:** actual search space size (canonical grid combos or GA evaluations). A hand-authored 6-param strategy with canonical params has the same overfitting risk as a 2-param one — near zero. The risk comes from the search process, not the parameter count.

---

*Last updated: 2026-04-14*
*Source of truth: `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, `scripts/validation/uncertainty.py`*
