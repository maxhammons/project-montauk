# Validation Gate Thresholds

> Canonical reference for every threshold in the validation pipeline.
> This file MUST stay in sync with `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, and `scripts/validation/uncertainty.py`.

---

## Two-Layer Model

Validation has two layers (see `validation-philosophy.md` §4):

- **Layer 1 — Correctness**: binary, hard-fail, no weights. A strategy that fails any Layer 1 check is disqualified regardless of confidence.
- **Layer 2 — Validation composite**: `composite_confidence` score on [0, 1]. It summarizes the tier-applicable validation stack and still drives PASS/WARN/FAIL. It is not the ranking score.
- **Layer 3 — Montauk Score (ranking + active strategy)**: the single headline score that ranks the Gold leaderboard and selects the active strategy. See [Montauk Score](#layer-3--montauk-score) below. `composite_confidence` feeds it (via the Conviction pillar); it does not compete with it.

One documented exception to "no veto": every sub-score's hard-fail anchor maps to 0.0, and a 0.0 inside the weighted geometric mean annihilates the composite (0^w = 0). This is intentional — a dimension at its catastrophic anchor (e.g. walk-forward ratio < 0.50, state agreement < 0.30, a zeroed era) SHOULD sink the verdict regardless of weight. Between anchors, every sub-score contributes weighted partial credit and no gate can veto.

---

## Layer 3 — Montauk Score

> Source of truth: `scripts/search/montauk_score.py` (weights locked 2026-06-07).
> Stamped on every leaderboard row by `certify/contract.py::sync_entry_contract`.

ONE headline score on [0, 1] (shown 0–100) that collapses the old score zoo
(`fitness`, `composite_confidence`, `overall_performance_score`,
`future_confidence`, `trust`, `overall_confidence`) into three orthogonal pillars:

```
Montauk Score = Conviction^0.55 × Performance^0.30 × Durability^0.15   (geometric)
```

| Pillar | Weight | Meaning | Built from |
|---|:-:|---|---|
| **Conviction** | 0.55 | Trust the edge is real and will persist out-of-sample — the number you hold through a scary drawdown. | confidence_v2 "future confidence" recipe **minus** its raw-performance term, then calibrated: `validation_quality` (0.70·composite + 0.30·evidence_floor), `robustness`, `charter_fit`, `search_deflation`. |
| **Performance** | 0.30 | Era-weighted share accumulation vs B&H, modern > real > synthetic. | `weighted_era_fitness(full, real, modern)` = `full^0.15 × real^0.25 × modern^0.60`, squashed via anchors `0.6→0.0, 1.0→0.5, 6.0→1.0` so it saturates once you clearly beat B&H. |
| **Durability** | 0.15 | Livability — can you actually run it. | confidence_v2 "trust" recipe **minus** its future-confidence term: `drawdown_resilience`, `parameter_parsimony`, `portfolio_redundancy`, `family_crowding`, `artifact_cleanliness`. |

**Geometric blend** so a single broken pillar (e.g. a 98%-drawdown strategy whose
`drawdown_resilience` craters) drags the whole score down instead of being masked
by a strong pillar. The pillars are orthogonal — raw performance lives only in the
Performance pillar (removed from Conviction), and forward-survival trust lives only
in Conviction (removed from Durability) — so there is no double counting.

**Ranking + active strategy.** Gold Status is the admission floor (correctness +
beats B&H in every era). Within the Gold set, rows rank by Montauk Score
(tiebreaks: `overall_performance_score`, then `fitness`), and the top row is the
active strategy. The validation pipeline's champion is likewise the highest-Montauk
PASS candidate.

**Calibration.** When `runs/confidence_v2/calibration_model.json` is present and
`calibrated`, the Conviction pillar is nudged toward observed forward-survival
(`calibration_state = "calibrated"`); otherwise it uses the raw score
(`provisional_uncalibrated`). The stamp uses a process-cached context so every
call site produces the identical, calibrated value.

---

## Layer 1 — Correctness Checklist

Any failure in the required anti-overfit checks here prevents `certified_not_overfit`. `backtest_certified` remains stricter because it also requires artifact completeness after validation.

**Gold Status** is stricter than PASS and `certified_not_overfit`, and is now
required for authority leaderboard admission.
A strategy has Gold Status only when it:

- has final validation verdict `PASS`
- is `certified_not_overfit`
- is `backtest_certified` / artifact-verified
- beats B&H in all three canonical eras: full, real, and modern

| Check | Source | Hard-fail condition |
|---|---|---|
| Engine integrity | `scripts/validation/integrity.py` | Any lookahead / repaint / multi-position / fill-contract violation — verified by executed checks (`_run_engine_behavior_checks`: prefix-consistency at two truncation depths, per-trade bar-close fill verification, trade-overlap scan), not self-reported flags (real since 2026-06-09) |
| Golden regression | `tests/test_regression.py` | Trade-by-trade PnL divergence > ±0.001% on 8.2.1 defaults |
| Shadow comparator (dev) | `tests/test_shadow_comparator.py` | Per-trade divergence > 0.5% vs `backtesting.py` / `vectorbt` |
| Data-quality pre-check | `scripts/data/quality.py` | Yahoo-vs-Stooq divergence, seam discontinuity, manifest checksum mismatch, OHLC insanity |
| Artifact completeness | run dir | Prevents `backtest_certified` packaging, but does not by itself negate anti-overfit certification. Verified on disk at every contract sync (existence + non-empty, machine-portable path rebasing); a stored stamp without resolvable paths is `unverifiable`, never trusted (2026-06-09) |
| Strategy registered | `strategies/library.py` | Strategy name not in `STRATEGY_REGISTRY` |
| Charter-compatible family | `strategies/library.py` | Strategy name listed in `CHARTER_INCOMPATIBLE_STRATEGIES` (real registry set since 2026-06-09; previously the flag was hardcoded compatible and could never fire) |
| Share multiplier | Gate 1 (eligibility) | `share_multiple < 1.0` (charter mission: must beat B&H shares) |
| Trades per year | Gate 1 | `trades_per_year > 5.0` (charter guardrail) |
| Trade count floor | Gate 1 | `trade_count < 5` (T0) / `< 10` (T1) / `< 15` (T2) |
| Degeneracy | Gate 1 | Always-in OR always-out across every 4-year window |

---

## Layer 2 — Validation Composite

### Verdict rules (2-tier)

```
FAIL:  any Layer 1 hard fail  OR  composite_confidence < 0.40
WARN:  composite_confidence >= 0.40 AND composite_confidence < 0.70
PASS:  composite_confidence >= 0.70  (certification candidate)
```

`PASS` means the candidate is eligible for certification work. It does **not**
by itself admit the row to `spike/leaderboard.json`. The authority leaderboard
admits only Gold Status rows.

### Admission tiers (for UI / workflow display)

| Confidence | Label | Leaderboard |
|:-:|---|---|
| 0–39 | Reject | Hidden |
| 40–59 | Research only | Archived |
| 60–69 | Watchlist | Research artifact only |
| 70–89 | Certified candidate | Research/certification queue |
| 90–100 | High confidence candidate | Research/certification queue |
| Gold Status | Certified + verified + all-era B&H winner | Authority leaderboard |

---

## Composite Weights (T2 baseline)

`composite_confidence` is a weighted geometric mean over present sub-scores. Higher means the validation stack is cleaner. Skipped gates return `None` and renormalize out — no penalty for gates that didn't apply to the tier. It remains a validation diagnostic, not a calibrated probability of future success.

| Sub-score | T2 weight | Source gate | T0 applies | T1 applies | T2 applies |
|---|:-:|---|:-:|:-:|:-:|
| `walk_forward` | 0.10 | Gate 4 WF | Y | Y | Y |
| `marker_shape` | 0.10 | Marker (state_agreement) | Y | Y | Y |
| `marker_timing` | 0.15 | Marker (per-cycle, magnitude-weighted) | Y | Y | Y |
| `named_windows` | 0.05 | Gate 4 named windows (split-out) | Y | Y | Y |
| `era_consistency` | 0.20 | min(real, modern) share multipliers | Y | Y | Y |
| `fragility` | 0.15 | Gate 5 Morris (fallback: Gate 3 perturbation) | — | Y (Gate 3) | Y (Gate 5) |
| `selection_bias` | 0.10 | Gate 2 deflation | — | — | Y |
| `bootstrap` | 0.05 | Gate 5 stationary bootstrap | — | — | Y |
| `regime_consistency` | 0.05 | Gate 2 HHI + meta + clustering | — | — | Y |
| `trade_sufficiency` | 0.05 | Gate 1 trade count | Y | Y | Y |
| `execution_realism` | 0.10 | gate_realism (2026-06-09) | Y | Y | Y |
| `event_dependence` | 0.05 | gate_realism (2026-06-09) | Y | Y | Y |
| `pbo` | 0.05 | gate_oos CSCV (2026-06-09) | — | — | Y |
| `oos_walk_forward` | 0.10 | gate_oos re-opt WF (2026-06-09) | — | — | Y |
| **Total (T2)** | **1.00** | | | | |

**Note:** `cross_asset` was removed from the composite in 2026-04-21 after the gc_vjatr finding. It was penalizing TECL-specific era winners for non-portability to TQQQ, which contradicts the charter's TECL-only design intent. The sub-score is still computed in Gate 6 and surfaced in the validation output for diagnostic purposes but does not factor into `composite_confidence`.

### Family-board future confidence

`composite_confidence` remains the validation/certification score. The legacy
family leaderboard score, `future_confidence`, remains available as a stricter
Gold-only ranking overlay. Confidence v2 supersedes it when
`runs/confidence_v2/leaderboard_scores.json` is present: family representatives
rank by `overall_confidence`, then new `future_confidence`, then `trust`, then
legacy family confidence. Non-Gold rows still cannot appear.

`future_confidence` is a weighted geometric mean over:

| Component | Weight | Meaning |
|---|:-:|---|
| `validation_confidence` | 0.35 | Existing `validation.composite_confidence` |
| `evidence_floor` | 0.18 | Blend of weakest and 20th-percentile validation sub-scores |
| `era_balance` | 0.14 | All-era outperformance floor plus real/modern symmetry |
| `drawdown_resilience` | 0.10 | Penalizes high max drawdown |
| `parameter_parsimony` | 0.08 | Penalizes large parameter surfaces and committee sprawl |
| `duplicate_signal` | 0.07 | Penalizes near-identical risk-state and entry/exit behavior |
| `family_crowding` | 0.05 | Mild discount for crowded sibling clusters |
| `warning_cleanliness` | 0.03 | Mild discount for soft/critical validation warnings |

This deliberately makes the family board more conservative than the full
authority leaderboard. A high `future_confidence` row must be Gold, pass the
normal validation stack, avoid relying on one very weak evidence plank, hold up
across eras, and not merely duplicate an already-crowded signal cluster.

### Confidence v2

> **Superseded as a headline by the Montauk Score (Layer 3).** The confidence_v2
> harness still runs to produce the calibration model and score timeseries, and
> its recipes are reused by the Montauk pillars — `future_confidence` (minus its
> raw-performance term) is the basis of **Conviction**, and `trust` (minus its
> future-confidence term) is the basis of **Durability**. These fields are no
> longer surfaced as parallel headline scores; the viz shows the Montauk Score and
> its three pillars.

Confidence v2 separates four concepts:

| Concept | Field | Meaning |
|---|---|---|
| Gold Status | `gold_status` | Binary leaderboard eligibility |
| Future Confidence | `future_confidence` | Calibration-assisted estimate that the strategy remains useful over the next 1-3 years; basis of the Conviction pillar |
| Trust | `trust` | Deployment suitability: drawdown, redundancy, parameter parsimony, artifacts, live degradation; basis of the Durability pillar |
| Overall Confidence | `overall_confidence` | Legacy super score combining Future Confidence and Trust (predecessor of the Montauk Score) |

Confidence v2 artifacts live under `runs/confidence_v2/`:

- `candidate_archive.json` — archived current/near-miss/spike/grid candidates with search provenance
- `vintage_trials.json` — simulated historical vintage trials
- `calibration_model.json` — mapping from raw confidence features to observed forward survival
- `leaderboard_scores.json` — current Gold rows enriched with Overall Confidence, Future Confidence, and Trust
- `confidence_timeseries.json` — score drift by strategy across refreshes
- `live_holdout_log.json` — forward-only evidence starting from 2026-05-01

The live holdout starts on 2026-05-01 because earlier data has already been
seen by Montauk. Historical dates are treated only as simulated vintages, not
pristine holdout data.

The default harness uses the top 120 archived candidates by source quality,
Gold/era evidence, weighted fitness, and marker score. This keeps calibration
broader than the current Gold board without making every refresh a full search
rerun.

### Effective weights per tier (after renormalization)

| Sub-score | T0 effective | T1 effective | T2 effective |
|---|:-:|:-:|:-:|
| `walk_forward` | 0.154 | 0.125 | 0.100 |
| `marker_shape` | 0.154 | 0.125 | 0.100 |
| `marker_timing` | 0.231 | 0.188 | 0.150 |
| `named_windows` | 0.077 | 0.063 | 0.050 |
| `era_consistency` | 0.308 | 0.250 | 0.200 |
| `fragility` | — | 0.188 | 0.150 |
| `selection_bias` | — | — | 0.100 |
| `bootstrap` | — | — | 0.050 |
| `regime_consistency` | — | — | 0.050 |
| `trade_sufficiency` | 0.077 | 0.063 | 0.050 |

T0 composite is dominated by era consistency plus time/marker sub-scores. T2 spreads across the full statistical stack. `cross_asset` is reported diagnostically but has no composite weight.

---

## Sub-Score Anchors (Smooth Interpolation)

Each sub-score is [0, 1] via smooth interpolation between these anchors:

- **hard-fail threshold** → 0.0
- **soft-warn threshold** → 0.5
- **pass threshold** → 1.0
- **fully clean** → 1.0 (capped)

Linear interpolation between anchors. Clamp at [0, 1].

### `walk_forward`
Anchor on `avg_oos_is_ratio` across WF windows (currently 3–4 windows: 2015-2017, 2018-2020, 2021-2023, 2024-present).

| Anchor | Value |
|---|:-:|
| 0.0 (hard-fail) | avg ratio < 0.50 |
| 0.5 (soft-warn) | avg ratio = 0.65 |
| 1.0 (pass) | avg ratio >= 0.80 |

Per-window contributions still flag as advisories in the gate report; they no longer veto.

### `marker_shape` (state agreement)
Anchor on `state_agreement` over the marker overlap window.

| Anchor | Value |
|---|:-:|
| 0.0 | state_agreement < 0.30 (essentially uncorrelated) |
| 0.5 | state_agreement = 0.50 (barely above random) |
| 1.0 | state_agreement >= 0.80 |

### `marker_timing` (per-cycle, magnitude-weighted)

**New sub-score.** For each marker cycle transition (buy and sell markers), compute distance in bars from nearest strategy transition. Per-cycle score = `max(0, 1 - distance / tolerance_bars)`. Aggregate as magnitude-weighted mean where each cycle's weight is its subsequent price move magnitude (bigger drawdowns / rallies carry more weight).

| Tier | Tolerance |
|---|:-:|
| T0 | 20 bars |
| T1 | 30 bars |
| T2 | 40 bars |

A strategy that is 40 bars late on the COVID crash (a ~70% drawdown cycle) pays a much bigger penalty than one that is 40 bars late on a 10% wobble.

### `named_windows`

**Split out from gate 4.** Anchor on the minimum `share_multiple` across the four named stress windows (`2020_meltup`, `2021_2022_bear`, `2023_rebound`, `2024_onward`). Each window's `share_multiple` and trade count are computed strictly inside the documented date range (era-style growth ratio from the window start); the 700-bar warmup prefix feeds indicators only (fixed 2026-06-09 — previously the whole warmup-padded slice was scored, so e.g. `2020_meltup` actually measured ~Sep-2016 → Jan-2021).

| Anchor | Value |
|---|:-:|
| 0.0 | any window share_multiple <= 0 OR errored |
| 0.5 | min share_multiple = 0.60 |
| 1.0 | min share_multiple >= 1.00 |

### `era_consistency`

**New sub-score (2026-04-21)** — guards against strategies that pass the weighted-era fitness gate by having one era compensate for another. Takes the minimum of (real_share_multiple, modern_share_multiple) and applies smooth anchors.

| Anchor | Value |
|---|:-:|
| 0.0 | min(real, modern) = 0.0x (one era totally failed) |
| 0.5 | min(real, modern) = 0.6x (modest in worst era) |
| 1.0 | min(real, modern) >= 1.2x (clearly beats B&H in both eras) |

Anchors tuned to grade the 0–1.2+ range smoothly rather than hard-zeroing everything below 0.5 — the latter would annihilate composite_confidence via geometric mean for any strategy with real<0.5, which is most of the current candidate pool.

Uses `real_share_multiple` (post-2008-12-17) and `modern_share_multiple` (post-2015) computed by `engine/strategy_engine.py::backtest()`.

### `fragility`
- T2: uses Morris `s_frag = clamp(1.0 - max_swing / 0.40)` (already smooth).
- T1: fallback to Gate 3 perturbation `score = 1.0 - max_swing / 0.40`.

### `selection_bias`
Gate 2 `selection_bias_score` — ramped from observed_rs / expected_max ratio (already smooth).

### `cross_asset`
Anchor on TQQQ same-param `share_multiple`.

| Anchor | Value |
|---|:-:|
| 0.0 | TQQQ errored OR share_multiple < 0.20 |
| 0.5 | TQQQ share_multiple = 0.50 |
| 1.0 | TQQQ share_multiple >= 1.00 |

TQQQ re-optimization result is reported as advisory only — no longer feeds a hard-fail.

### `bootstrap`
`s_boot = clamp(1.0 - ci_width / observed_rs)` (T2 only).

### `regime_consistency`
Mean of: bull HHI margin, bear HHI margin, dominance margin, meta robustness, trade-clustering margin. Already smooth [0, 1] (T2 only).

### `trade_sufficiency`
Smooth anchors: 0 trades -> 0.0, 10 trades -> 0.5, 20+ trades -> 1.0. Encourages enough trades to draw signal from noise without punishing low-frequency candidates.

---

## Tier Routing Overview

| Gate | T0 | T1 | T2 | Role in new framework |
|---|:-:|:-:|:-:|---|
| Gate 1 (Eligibility) | RUN | RUN | RUN | Layer 1 correctness + `trade_sufficiency` sub-score |
| Marker (shape + timing) | RUN | RUN | RUN | `marker_shape` + `marker_timing` sub-scores |
| Gate 2 (Search bias) | SKIP | SKIP | RUN | `selection_bias` + `regime_consistency` sub-scores |
| Gate 3 (Param fragility) | SKIP | RUN | RUN | `fragility` fallback (T1) |
| Gate 4 (Time generalization) | RUN | RUN | RUN | `walk_forward` + `named_windows` sub-scores |
| Gate 5 (Uncertainty) | SKIP | SKIP | RUN | `fragility` (Morris) + `bootstrap` sub-scores |
| Gate 6 (Cross-asset) | RUN | RUN | RUN | `cross_asset` sub-score (weight reduced to 0.05) |
| Gate 7 (Synthesis) | RUN | RUN | RUN | Composite + verdict |


### `execution_realism` (2026-06-09)

Re-runs the exact signal arrays under `execution_timing="next_open"` (signal at
close, fill at next open — the actual manual workflow) and scores the
share_multiple degradation vs close fills. Budget from the deep-validation
audit (D3.4): −15%.

| Anchor | Degradation |
|---|:-:|
| 0.0 | ≤ −30% |
| 0.5 | −15% |
| 1.0 | ≥ −5% |

Critical warning at ≤ −15%, soft at ≤ −10%.

### `event_dependence` (2026-06-09)

Splices each major-event window (COVID crash 2020-02-19→04-30, 2022 bear) out
of the series, re-runs strategy + B&H, and scores edge retention
(1 − worst collapse). Closes deep-validation D4.9. Calibration: charter-aligned
defensive strategies legitimately concentrate edge in the few real crashes, so
the anchors punish *near-total* single-event dependence, not concentration.

| Anchor | Retention (1 − collapse) |
|---|:-:|
| 0.0 | ≤ 0.05 (edge IS one event) |
| 0.5 | 0.20 |
| 1.0 | ≥ 0.50 |

Critical warning at collapse ≥ 0.80, soft at ≥ 0.50. Null-calibrated anchors
are backlog.

### `pbo` (T2, 2026-06-09)

CSCV Probability of Backtest Overfitting (Bailey et al.) over the candidate's
32-variant param neighborhood, 16 blocks, 200 splits
(`scripts/validation/pbo.py`). PBO = P(IS-best variant lands bottom-half OOS).

| Anchor | PBO |
|---|:-:|
| 0.0 | ≥ 0.80 |
| 0.5 | 0.50 (selection = chance) |
| 1.0 | ≤ 0.20 (accepted bound) |

Critical warning at PBO > 0.50, soft above 0.20. Static ensembles with no
param space return `insufficient_variants` and the sub-score renormalizes out.

### `oos_walk_forward` (T2, 2026-06-09)

TRUE out-of-sample walk-forward (`scripts/validation/oos_walk_forward.py`):
re-optimizes on each anchored train window (60 evals/window in-pipeline,
seeded), evaluates the train-selected params on the held-out test window.
Same anchors as `walk_forward` (0.50 / 0.65 / 0.80 on the regime OOS/IS
ratio). The legacy `walk_forward` sub-score (same params replayed on both
sides) measures temporal consistency, not OOS — both are kept, documented as
measuring different things. Budget-skipped in quick mode (no warning — a
budget decision is not a quality signal).

### Tier auto-promotion (unchanged)

A strategy declared T0 auto-promotes to T1 if it has > 5 tunable params (excluding cooldown) or any non-canonical param value. T1 auto-promotes to T2 if > 8 tunable params. Declared tier is an upper bound on leniency.

---

## Strict Canonical Parameter Set (T0, unchanged)

| Parameter family | Allowed values |
|---|---|
| EMA / SMA / TEMA period | 7, 9, 14, 20, 21, 30, 50, 100, 150, 200, 300 |
| RSI period | 7, 14, 21 |
| ATR period | 7, 14, 20, 40 |
| ATR multiplier | 0.5, 1.0, 1.5, 2.0, 2.5, 3.0 |
| Lookback / Donchian / Highest-Lowest | 5, 10, 20, 50, 100, 150, 200 |
| Slope / confirmation bars | 1, 2, 3, 5 |
| Cooldown bars | 0, 1, 2, 3, 5, 10 |
| Percent thresholds | 5%, 8%, 10%, 15%, 20%, 25% |
| MACD fast / slow / signal | (12, 26, 9), (8, 17, 9) |

Anything outside this list lifts the strategy to T1.

---

## Warnings Taxonomy (post-revision)

| Level | Effect on verdict | Purpose |
|---|---|---|
| **Advisory** | None | Reported on the leaderboard row for context |
| **Soft warning** | None — no cap, no downgrade | Descriptive observations; kept for diagnostic reading |
| **Critical warning** | None — informational | Flagged on the UI as "watch this" but does not change verdict |
| **Hard fail** | FAIL (Layer 1 only) | Correctness violation; irrecoverable |

Warnings still accumulate in the gate output for diagnostic value. They no longer drive the verdict. If a strategy is stacking up critical warnings across multiple gates, its sub-scores will reflect that and its confidence will land in the 40–60 band organically.

---

## Design Principle: Overfitting vs Strategy Characteristics

The pipeline catches overfitting via the sub-score weighting, not via verdict triggers:

| Metric | Reflected in |
|---|---|
| High param sensitivity | `fragility` sub-score (low = high sensitivity) |
| Concentrated returns (HHI) | `regime_consistency` sub-score (low = heavy concentration) |
| Bootstrap uncertainty | `bootstrap` sub-score (low = wide CI) |
| Search-bias inflation | `selection_bias` sub-score (low = observed vs expected max problematic) |
| Time-window inconsistency | `walk_forward` + `named_windows` sub-scores |
| Cross-asset fragility | `cross_asset` sub-score |
| Missing cycles | `marker_timing` sub-score (magnitude-weighted) |

A strategy that scores weakly across multiple overfit-sensitive sub-scores will land below 0.70 automatically. A strategy that scores strongly on some and weakly on one will still land above 0.70 — which matches the user intent: "close misses cost a little, far misses cost a lot."

---

*Last updated: 2026-05-01*
*Source of truth: `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, `scripts/validation/uncertainty.py`, `scripts/strategies/markers.py`*

## 2026-06-09 deflation upgrade

`selection_bias` deflation now uses **N_eff measured from the live search
history** (`spike/hash-index.json` count, 4,116+ at upgrade time) with a
ratcheting high-water mark (`spike/n-eff-state.json`) — never the retired
hardcoded 300. The Monte-Carlo null requires ≥ 5,000 valid samples and is
cache-keyed on (engine hash, data-manifest fingerprint); an infeasible Beta
fit raises instead of falling back to Beta(10,10). Treating every deduped
config as an independent trial is deliberately conservative (harsher
deflation than the true correlated multiplicity).

## Live demotion rule (2026-06-09)

Forward evidence outranks the backtest claim. Once the live holdout stream
contradicts certification, the active champion is demoted rather than
defended. Implemented in `scripts/ops/live_holdout.py::evaluate_demotion`
(constants `DEMOTION_*`), evaluated on every live-holdout build.

| Trigger | Threshold | Sample-size gate |
|---|---|---|
| Live trust proxy | `live_vs_bah_multiple < 0.85` | ≥ 21 live snapshots (~1 trading month) |
| Replay divergence | `diverged_count > 0` (replay disagrees with the immutable signal record) | none — correctness violations fire at any sample size |

> **Removed 2026-06-17 — backtest-vs-live degradation trigger.** The original
> rule also demoted when a "degradation fraction" fell below `-0.15`. That
> fraction divided the live trust proxy (a ~6-week relative-return ratio, ≈1.0
> by construction) by the certified **full-history** share multiple (decades of
> cumulative accumulation, e.g. 35x) — incommensurable quantities. The check
> fired on every leveraged Gold champion the moment it reached 21 snapshots
> regardless of live tracking (avoiding it would require beating B&H ~30x in six
> weeks), and anchoring on a full-history multiple contradicts the project's
> "full-history numbers are diagnostic-only" principle. Forward falsification now
> rests on the live trust proxy floor and replay divergence; the full-history
> degradation survives as a labeled diagnostic (`degradation_fraction_diagnostic`)
> in the live-holdout payload only.

With fewer than 21 snapshots and no divergence, the verdict is always
`demote=False` with reason `insufficient live evidence (n/21)` — performance
noise on a handful of bars must not demote anyone.

**Evidence stream.** Every live-holdout build appends one row per
`data_end_date` (idempotent) to `runs/confidence_v2/live_outcomes.jsonl`:
date, strategy, params_hash, montauk_score, composite_confidence,
live_vs_bah_multiple, diverged_count, n_snapshots. This is the
forward-survival evidence the confidence_vintage harness consumes to
calibrate Conviction against reality. A companion execution-discipline
journal (`runs/ops/fills.jsonl` + `scripts/ops/fills.py reconcile`) grades
actual fills against the next-snapshot-close proxy.

**Enforcement.** Today (Phase 3.3) a `demote=True` verdict is a governance
blocker: governance state goes `active_blocked`, a `live_demotion` event is
emitted, and the demotion block is stamped onto the active leaderboard row
(`live_demotion`). After the Phase-4 recertification pass it additionally
becomes an eligibility gate at leaderboard sync — demoted rows are excluded
from the active-champion pick, not just flagged.

## Warning acknowledgment layer (2026-06-17)

Layer-2 warnings are honest, *measured* properties of a strategy (event
dependence, weak cross-asset portability, parameter parsimony, …) — never bugs
to silence. But once a human has reviewed and accepted those known risks for a
specific config, re-surfacing them every run as fresh "attention" items is
noise. `scripts/ops/acknowledge_warnings.py` records acknowledgments in
`runs/operations/acknowledged_warnings.json`, and `governance.py` excludes
acknowledged warnings from the *active* count that drives the
`"N validation warnings are active"` advisory.

- **Keyed on `params_hash`** — the exact config. If a strategy's params change,
  the hash changes and previously-accepted warnings auto-resurface; a new config
  has not been reviewed.
- **Matched on a digit-normalized signature** (`warning_signature`: all digit
  runs → `#`) so a drifting metric (`-12.2%` → `-12.4%`) does not
  un-acknowledge an accepted warning, while a genuinely new warning stays active
  and re-raises governance.
- **Never deleted from the validation record.** Acknowledged warnings remain in
  the signal/validation output; governance reports both counts
  (`warnings_summary.active` / `warnings_summary.acknowledged`). When every
  active warning is acknowledged (and nothing else is open), governance reaches
  `active_ok` — the dashboard reads "clean" because the known risks were
  explicitly accepted, not hidden.
- **Acknowledge via** `python scripts/ops/acknowledge_warnings.py active`
  (acks the active champion's current warnings); `… list` / `… clear <hash>`
  to inspect or revoke.
