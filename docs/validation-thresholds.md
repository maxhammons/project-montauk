# Validation Gate Thresholds

> Canonical reference for every threshold in the validation pipeline.
> This file MUST stay in sync with `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, and `scripts/validation/uncertainty.py`.

---

## Two-Layer Model

Validation has two layers (see `validation-philosophy.md` §4):

- **Layer 1 — Correctness**: binary, hard-fail, no weights. A strategy that fails any Layer 1 check is disqualified regardless of confidence.
- **Layer 2 — Validation composite**: `composite_confidence` score on [0, 1]. It summarizes the tier-applicable validation stack and still drives PASS/WARN/FAIL. It is not the capital-allocation confidence metric.
- **Confidence v2 diagnostics**: Gold rows can also carry `overall_confidence`, `future_confidence`, and `trust`. These are diagnostic-only until the vintage calibration harness has enough evidence to replace heuristic ranking.

No gate in Layer 2 has veto power on its own. Every sub-score contributes weighted partial credit.

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
| Engine integrity | `scripts/validation/integrity.py` | Any lookahead / repaint / multi-position violation |
| Golden regression | `tests/test_regression.py` | Trade-by-trade PnL divergence > ±0.001% on 8.2.1 defaults |
| Shadow comparator (dev) | `tests/test_shadow_comparator.py` | Per-trade divergence > 0.5% vs `backtesting.py` / `vectorbt` |
| Data-quality pre-check | `scripts/data/quality.py` | Yahoo-vs-Stooq divergence, seam discontinuity, manifest checksum mismatch, OHLC insanity |
| Artifact completeness | run dir | Prevents `backtest_certified` packaging, but does not by itself negate anti-overfit certification |
| Strategy registered | `strategies/library.py` | Strategy name not in `STRATEGY_REGISTRY` |
| Charter-compatible family | `strategies/library.py` | Registry flag set to `False` |
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

Confidence v2 separates four concepts:

| Concept | Field | Meaning |
|---|---|---|
| Gold Status | `gold_status` | Binary leaderboard eligibility |
| Future Confidence | `future_confidence` | Calibration-assisted estimate that the strategy remains useful over the next 1-3 years |
| Trust | `trust` | Deployment suitability after future confidence: drawdown, redundancy, parameter parsimony, artifacts, and live degradation |
| Overall Confidence | `overall_confidence` | Super score combining Future Confidence and Trust |

Confidence v2 artifacts live under `runs/confidence_v2/`:

- `vintage_trials.json` — simulated historical vintage trials
- `calibration_model.json` — mapping from raw confidence features to observed forward survival
- `leaderboard_scores.json` — current Gold rows enriched with Overall Confidence, Future Confidence, and Trust
- `confidence_timeseries.json` — score drift by strategy across refreshes
- `live_holdout_log.json` — forward-only evidence starting from 2026-05-01

The live holdout starts on 2026-05-01 because earlier data has already been
seen by Montauk. Historical dates are treated only as simulated vintages, not
pristine holdout data.

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

**Split out from gate 4.** Anchor on the minimum `share_multiple` across the four named stress windows (`2020_meltup`, `2021_2022_bear`, `2023_rebound`, `2024_onward`).

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
