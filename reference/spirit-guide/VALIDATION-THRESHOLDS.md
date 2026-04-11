# Validation Gate Thresholds

> Canonical reference for every threshold in the validation pipeline.
> This file MUST stay in sync with `scripts/validation/pipeline.py` and `scripts/validation/candidate.py`.

---

## Verdict Logic (Gate 7 Synthesis)

```
FAIL:   hard_fail_reasons present OR composite_confidence < 0.45
WARN:   critical_warnings present OR composite_confidence < 0.70 OR soft_warnings >= 4
PASS:   only soft_warnings (< 4) and/or advisories
```

`clean_pass = True` when verdict is PASS and zero soft warnings.

---

## Gate 1 — Candidate Eligibility

Source: `pipeline.py :: _gate1_candidate()`

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Trade count | < 15 | — | >= 15 |
| Trades/year | > 3.0 | — | <= 3.0 |
| Trades per param | < 5.0 | 5.0 - 10.0 | >= 10.0 |
| n_params vs regime_transitions | — | n_params > transitions | n_params <= transitions |
| Degeneracy (4yr windows) | always-in or always-out across ALL windows | sparse/saturated in some windows | normal exposure |
| Pine-deployable | not in registry | — | in registry |
| Charter-compatible | fails charter | — | passes |

---

## Gate 2 — Search Bias & Regime Memorization

Source: `pipeline.py :: _gate2_search_bias()`

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Exit-boundary proximity | enrichment > 3.0x | — | — | <= 3.0x |
| Jackknife | max_impact_ratio > 2.0x | — | — | <= 2.0x |
| Concentration (HHI) | — | bull_flag OR bear_flag OR dom > 3.0 | dom > 2.0 | below thresholds |
| Meta robustness (28 defs) | — | < 50% within 20% of baseline | 50% - 75% | >= 75% |
| Trade clustering | — | max_share > 0.60 | — | <= 0.60 |
| Selection bias | — | — | advisory only | — |

HHI thresholds: `bull_thresh = 1.5 / n_bull`, `bear_thresh = 1.5 / n_bear`.

---

## Gate 3 — Parameter Fragility

Source: `candidate.py :: check_parameter_fragility()`, wrapped by `pipeline.py :: _gate3_fragility()`

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Any param +/-10% swing | > 30% | > 20% (or +/-20% > 40%) | <= 20% |

Perturbation levels tested: +/-10%, +/-20%.

---

## Gate 4 — Time Generalization

### Walk-Forward

Source: `candidate.py :: analyze_walk_forward()`

Windows: WF 2015-2017, WF 2018-2020, WF 2021-2023, WF 2024-present (dynamic).

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Per-window OOS/IS regime ratio | < 0.75 | — | — | >= 0.75 |
| Zero OOS trades (expected >= 1.5) | yes | — | — | has trades |
| Zero OOS trades (expected < 1.5) | — | — | yes | has trades |
| Avg OOS/IS ratio | < 0.50 | < 0.65 | — | >= 0.65 |
| Dispersion (max - min) | — | > 0.65 | 0.50 - 0.65 | <= 0.50 |

Zero-trade threshold: `expected_trades = full_period_trades_yr * window_years`. If < 1.5, zero trades is soft warning (statistically normal for low-frequency strategies).

### Named Windows

Source: `candidate.py :: analyze_named_windows()`

Windows: 2020_meltup, 2021_2022_bear, 2023_rebound, 2024_onward.

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| Error | yes | — | — |
| vs_bah <= 0 (backtest broke) | yes | — | — |
| Zero trades (strategy sat out, vs_bah > 0) | — | yes | — |
| vs_bah | — | < 0.60 | >= 0.60 |

---

## Gate 5 — Uncertainty

### Morris Elementary Effects

Source: `uncertainty.py :: morris_fragility()`, severity routing in `pipeline.py :: _gate5_uncertainty()`

30 trajectories, +/-20% delta.

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Interaction flag (swing > 0.30 or sigma_ratio > 1.5 + swing > 0.20) | yes | — | — | — |
| Warning flag with max_swing >= 0.10 | — | yes | — | — |
| Warning flag with max_swing < 0.10 | — | — | — | dropped (noise) |
| No flag | — | — | — | pass |

`s_frag = clamp(1.0 - max_swing / 0.40)`.

### Stationary Bootstrap

Source: `uncertainty.py :: stationary_bootstrap_validation()`, severity routing in `pipeline.py :: _gate5_uncertainty()`

200 resamples, expected block length 20.

| Check | Hard Fail | Critical Warning | Soft Warning | Pass |
|-------|-----------|-----------------|--------------|------|
| Downside prob (% resamples < B&H) | > 0.50 | > 0.40 | > 0.25 or s_boot < 0.20 | <= 0.25 and s_boot >= 0.20 |

`s_boot = clamp(1.0 - ci_width / observed_rs)`.

---

## Gate 6 — Cross-Asset

Source: `pipeline.py :: _gate6_cross_asset()`

| Check | Hard Fail | Soft Warning | Pass |
|-------|-----------|--------------|------|
| TQQQ same-param vs_bah | < 0.50 (or error) | 0.50 - 1.00 | >= 1.00 |
| QQQ same-param vs_bah | — | < 0.50 (or error) | >= 0.50 |
| TQQQ re-optimization (tier3) | vs_bah < 1.0 | — | >= 1.0 |

Tier3 budget scales with run hours: 0.5m/pop12 (quick), up to 2.0m/pop24 (long).

---

## Composite Confidence

Source: `pipeline.py :: _geometric_composite()`

Weighted geometric mean of sub-scores:

| Sub-score | Weight | Source |
|-----------|--------|--------|
| fragility | 0.25 | Gate 5 Morris s_frag (fallback: Gate 3 score) |
| selection_bias | 0.20 | Gate 2 deflation-adjusted score |
| walk_forward | 0.20 | Gate 4 avg OOS/IS ratio (clamped 0-1) |
| bootstrap | 0.15 | Gate 5 s_boot |
| trade_sufficiency | 0.10 | (trades - 10) / 30, clamped 0-1 |
| regime_consistency | 0.10 | Gate 2 concentration/meta/clustering blend |

---

## Warning Taxonomy

1. **Advisories** — FYI only, no effect on verdict
2. **Soft Warnings** — acceptable if composite >= 0.70 and count < 4
3. **Critical Warnings** — block promotion to PASS
4. **Hard Fails** — result in FAIL verdict

---

*Last updated: 2026-04-10*
*Source of truth: `scripts/validation/pipeline.py`, `scripts/validation/candidate.py`, `scripts/validation/uncertainty.py`*
