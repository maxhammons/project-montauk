# Validation Pipeline — Implementation Checklist

> Updated 2026-04-07. Reflects current codebase state after fitness rewrite.

---

## Done: Fitness Function Rewrite

- [x] Replace vs_bah-based fitness with regime_score-primary fitness (`evolve.py`)
- [x] Add HHI hard gate (reject if single cycle dominates >0.35)
- [x] Hard cap trade frequency at 3/yr (was soft penalty)
- [x] vs_bah demoted to small tiebreaker (capped at 1.5x bonus)
- [x] Soft ramp for low trade count (min 5, full credit at 10+)
- [x] Compute regime score inside `evaluate()` and attach to BacktestResult
- [x] Update hash-index to v2 format: `{hash: {f: fitness, rs: regime_score}}`
- [x] Auto-migrate 918K v1 entries (marked rs=null, re-evaluated on encounter)
- [x] Verify: optimizer ranks strategies by regime timing, not B&H outperformance

## Done: Scripts Reorg

- [x] Create `scripts/validation/` subfolder
- [x] Move `deflate.py` → `validation/deflate.py`
- [x] Move `validate_sprint1.py` → `validation/sprint1.py`
- [x] Move `validate_candidate.py` → `validation/candidate.py`
- [x] Fix all imports (sys.path to scripts/, validation.deflate for cross-package)
- [x] Verify: `python3 -m validation.sprint1` works from scripts/

## Done: Sprint 1 — 6 Tier 1 Tests (`validation/sprint1.py`)

### 1.1 Deflated Regime Score
- [x] Monte Carlo null calibration: 434 random backtests → Beta(17.2, 14.8)
- [x] Null cached to `spike/null-distribution.json` (reuse across runs)
- [x] N_eff structural heuristic: 300 (15 families × 20 basins)
- [x] Expected max RS at N_eff=300: **0.761** (score must exceed this to beat noise)
- [x] Deflated probability = CDF(observed)^N_eff
- [x] Null percentile column for interpretability (e.g., "55th percentile of random")

### 1.2 Exit-Boundary Proximity
- [x] For each exit trade, compute distance to nearest bear-market start
- [x] Enrichment ratio: actual % within 5 bars / expected % by chance
- [x] Flag if exits are >3x enriched near bear starts
- [x] Catches: rsi_regime_trail (7.6x), rsi_regime (6.1x), breakout (5.6x)

### 1.3 Concentric Shell Analysis
- [x] Determined hash-index lacks parameter vectors — **blocked**
- [ ] Modify evolve.py to store param vectors alongside hashes *(deferred)*
- [ ] Implement basin width measurement once vectors are available

### 1.4 Delete-One-Cycle Jackknife
- [x] `exclude_bear_idx` / `exclude_bull_idx` params in `score_regime_capture()`
- [x] Scaled threshold: "dominant" = >2x expected impact of average cycle
- [x] Jackknife SE computed for confidence estimation

### 1.5 Cycle Concentration (HHI) + Component Dominance
- [x] Separate HHI for bull_capture and bear_avoidance
- [x] Scaled threshold: HHI > 1.5/N (adapts to cycle count)
- [x] Component dominance: flag if bull/bear ratio > 3x
- [x] Catches: mean_revert (4.5x dominance), breakout (3.5x)

### 1.6 Regime Detection Meta-Robustness
- [x] Wide grid: 7 thresholds (15-50%) × 4 durations (5-40 bars) = 28 definitions
- [x] `min_duration` parameter added to `score_regime_capture()`
- [x] Measures % of definitions where score stays within 20% of baseline
- [x] Flag if <60% stable

---

## Next: Run Spike with New Fitness

- [ ] Kick off a spike run (1-2 hours) with the new regime-score-primary fitness
- [ ] Observe new leaderboard rankings — strategies should sort by RS, not B&H
- [ ] Check if any strategy clears the 0.761 noise floor
- [ ] Use results to inform Sprint 2 priorities

---

## Sprint 2: Robustness Tests (~13K Backtests, ~20 min)

### 2.1 Morris Sensitivity Analysis
- [ ] Add `SALib` to requirements.txt
- [ ] Replace `_stability_check()` in `validation/candidate.py` with Morris EE
- [ ] r=30 trajectories, 330 backtests/strategy, ~25s each
- [ ] Compute mu* (importance) and sigma (interaction) per parameter
- [ ] Fix parameters with ST_i < 0.05 to reduce effective DOF from 12 to 6-8

### 2.2 Composite Fragility Score (S_frag)
- [ ] LHS perturbation clouds: 200-300 evals/strategy
- [ ] S_rob = 0.5×R_mean + 0.3×p_acc + 0.2×R_0.05
- [ ] S_int = 1 - interaction_index (from Morris sigma/mu*)
- [ ] S_frag = S_rob × S_int
- [ ] Gate: S_frag < 0.40 → reject
- [ ] Wire into fitness as multiplicative penalty

### 2.3 Cross-Asset Validation
- [ ] Add data fetchers for TQQQ, UPRO, QQQ, XLK, SOXL to `data.py`
- [ ] Run each top strategy's exact params on all 5 instruments
- [ ] Gate: profitable on ≥ 3/5 instruments
- [ ] Flag: RS ≥ 0.70 on TECL but < 0.55 on others

### 2.4 Concentric Shell Analysis
- [ ] Store param vectors in hash-index (alongside {f, rs})
- [ ] Create `validation/basin.py`
- [ ] Normalize params to [0,1], bin by distance, measure fitness retention
- [ ] Gate: retention > 0.85 at d=0.15

---

## Sprint 3: Pipeline Assembly + GH Actions

### 3.1 Validation Pipeline
- [ ] Create `validation/pipeline.py` orchestrating all stages
- [ ] Stage 0: metadata gates (trade count, param ratio, degeneracy)
- [ ] Stage 1: Sprint 1 tests + deflation (~1 min)
- [ ] Stage 2: walk-forward + regime consistency (~2 min)
- [ ] Stage 3: Morris + bootstrap for survivors (~12 min)
- [ ] Stage 4: composite scoring + tiering
- [ ] Output: `spike/validation.json` + `spike/runs/NNN/validation.md`
- [ ] Tiers: High Confidence ≥ 0.70 | Provisional 0.45-0.70 | Flagged 0.25-0.45 | Rejected < 0.25

### 3.2 GitHub Actions Integration
- [ ] Add validation step to `spike.yml` (between optimizer and commit)
- [ ] Tier 1 (~1 min) on every run; full pipeline on runs ≥ 3 hours
- [ ] Add `validate` workflow_dispatch input (default: "auto")
- [ ] Validation output auto-committed with `git add spike/`
- [ ] Add validation summary to `report.py` markdown output

### 3.3 Stationary Bootstrap
- [ ] Add `arch` library to requirements.txt
- [ ] Create `validation/bootstrap.py` (Politis & Romano 1994)
- [ ] Automatic block length selection (Politis & White 2004)
- [ ] Student's t bootstrap CI (NOT percentile/BCa)
- [ ] B=200 resamples per strategy, 90% CI on Regime Score
- [ ] Flag if CI includes 0.50 (no-skill baseline)

---

## Sprint 4: Extended Testing + Calibration

### 4.1 Synthetic Data Extension
- [ ] Fetch NDX back to 1985 (or QQQ to 1999)
- [ ] Avellaneda-Zhang formula: r_TECL = 3×r_underlying - 3×RV - fees
- [ ] Validate synthetic matches real TECL in overlap period (2009+)
- [ ] Run top strategies on 1985-present — flag failures on dot-com/2008 GFC

### 4.2 PBO/CSCV
- [ ] Create `validation/pbo.py` (adapt from compass report code)
- [ ] Monthly aggregation (T~204), S=8 partitions, 2-month embargo
- [ ] Pre-label regimes on full dataset before partitioning
- [ ] Calibrated threshold ~0.20 (not academic 0.05)
- [ ] Supplementary signal only — not a hard gate

### 4.3 N_eff Calibration (Eigenvalue Method)
- [ ] Create `validation/n_eff.py`
- [ ] Sample 5,000 configs, compute return series correlation matrix
- [ ] Extract eigenvalues above Marchenko-Pastur bound
- [ ] Replace structural heuristic (N_eff=300) with empirical estimate
- [ ] Re-run all deflated scores with calibrated N_eff
