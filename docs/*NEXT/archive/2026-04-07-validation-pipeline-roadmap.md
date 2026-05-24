# Implementation Roadmap: Validation Pipeline for Project Montauk

> Derived from SYNTHESIS.md. Tasks ordered by impact/effort ratio. Each task includes files to modify, compute cost, and what "done" looks like.

---

## Tier 1: Quick Wins (Existing Data, No New Backtests)

These use the 918K configs already in `spike/hash-index.json` and the leaderboard data. Zero or near-zero compute.

### 1.1 Deflated Regime Score (Selection Bias Correction)

**What**: Apply Beta-distribution extreme value theory to compute the expected maximum Regime Score from pure noise, then deflate each leaderboard strategy's score against this baseline.

**Why first**: Without this, raw scores are meaningless. A score of 0.85 may not beat chance at N_eff=2,000.

**Files to modify**:
- `scripts/evolve.py` — add deflation to the fitness evaluation / leaderboard promotion logic (around `evaluate()` at line 354)
- New: `scripts/deflate.py` — standalone module with `StrategyDiscoveryGovernor` class (adapt from code in `docs/research/reports/deflated-sharpe-evolutionary.md`)

**Algorithm**:
1. Compute cross-sectional mean and std of Regime Scores across all 918K configs (from hash-index.json)
2. Fit Beta(alpha, beta) via method of moments
3. Expected max = `Beta.ppf(1 - 1/N_eff, alpha, beta)` where N_eff is estimated (start with structural heuristic: 15 families x 20 effective configs = 300, refine later)
4. Deflated score = P(observed > expected_max) using Beta CDF
5. Gate: deflated score >= 0.95 for leaderboard promotion

**Compute cost**: <1 second (pure arithmetic on existing data)

**Done when**: Every leaderboard strategy has a `deflated_score` field. Strategies below 0.50 are flagged.

---

### 1.2 Regime Boundary Perturbation Test

**What**: Shift each detected regime boundary by +/-k bars (k=1, 2, 5, 10, 20) and recompute Regime Score. If score collapses at small shifts, the strategy memorized the boundaries.

**Why**: This is the single most diagnostic test for the #1 failure mode (boundary memorization).

**Files to modify**:
- `scripts/backtest_engine.py` — the regime detection is in `compute_regime_score()` around line 448. Add a `perturb_boundaries(shifts)` parameter that offsets detected bear/bull boundaries before scoring
- `scripts/validate_candidate.py` — add boundary perturbation as a validation step (after the existing walk-forward and stability checks, line 159+)

**Algorithm**:
1. Run regime detection normally to get bear/bull period boundaries
2. For each k in [1, 2, 5, 10, 20]: shift all boundaries by +k and -k bars
3. Recompute Regime Score with shifted boundaries (10 recomputations per strategy, no new backtests — just re-label existing equity curve)
4. Record max score degradation across all shifts
5. Gate: score degrades < 15% at k=5

**Compute cost**: ~10 recomputations per strategy (no backtests, just re-scoring existing trade data). Total ~200 recomputations for 20 strategies. Negligible.

**Done when**: Each leaderboard strategy has `boundary_robustness` score. Strategies with >30% degradation at k=5 are flagged.

---

### 1.3 Concentric Shell Analysis (Basin Width)

**What**: For each leaderboard strategy, find all same-family configs in the 918K hash index, bin them by parameter-space distance, and measure how fitness decays with distance from the optimum.

**Why**: Distinguishes broad plateaus (robust) from narrow spikes (overfit) using data you already have.

**Files to modify**:
- New: `scripts/basin_analysis.py` — standalone module
- `scripts/evolve.py` — needs to store parameter vectors alongside hashes (currently only stores hash → fitness). May need a secondary index or sampling approach.

**Algorithm**:
1. For each top strategy, normalize its parameters to [0,1] using the param ranges from `strategies.py`
2. Compute Euclidean distance from each same-family config to the top config
3. Bin into shells: d < 0.05, 0.05-0.15, 0.15-0.30, 0.30+
4. Compute mean fitness retention per shell = shell_mean / peak_fitness
5. Gate: fitness retention > 0.85 at d=0.15

**Compute cost**: Requires iterating hash-index.json (~918K entries). The index currently stores hash → fitness but **not parameter vectors**. Two options:
- (a) Rebuild a parameter index from run results (if saved), or
- (b) Re-derive from the hash generation logic

**Caveat**: If parameter vectors aren't stored alongside hashes, this requires either modifying the hash index to store them or sampling a subset from run logs.

**Done when**: Each leaderboard strategy has `basin_width` and `fitness_retention_at_d015` metrics.

---

### 1.4 Delete-One-Cycle Jackknife

**What**: For each leaderboard strategy, remove each bull/bear cycle one at a time and recompute Regime Score. If removing any single cycle drops score > 30%, that cycle is carrying the strategy.

**Files to modify**:
- `scripts/backtest_engine.py` — add `exclude_cycle` parameter to `compute_regime_score()`
- `scripts/validate_candidate.py` — add jackknife step

**Compute cost**: 5-8 recomputations per strategy (one per cycle). No new backtests. ~160 recomputations for 20 strategies. Negligible.

**Done when**: Each strategy has per-cycle contribution breakdown and HHI concentration score. HHI > 0.25 = flagged.

---

### 1.5 Cycle Concentration Check (HHI)

**What**: Compute Herfindahl-Hirschman Index on per-cycle Regime Score contributions.

**Why**: A strategy that scores 0.90 overall but gets 0.60 of that from a single lucky bear exit is fragile.

**Files to modify**:
- `scripts/backtest_engine.py` — the per-period scores are already computed (bull_capture_scores, bear_avoidance_scores at lines 465-491). Just need to expose them and compute HHI.

**Compute cost**: Zero — arithmetic on already-computed per-period scores.

**Done when**: `RegimeScore` dataclass includes `hhi` and `per_cycle_scores` fields.

---

## Tier 2: Medium Effort (New Backtests, Fits in Spike Run)

### 2.1 Morris Sensitivity Analysis (Elementary Effects)

**What**: Replace the current +/-10% OAT perturbation with Morris screening. For each parameter, compute mu* (importance) and sigma (interaction) statistics from r=30 random trajectories through the parameter space.

**Why**: Identifies which parameters actually matter and which have interactions. Parameters with ST_i < 0.05 should be fixed to reduce effective degrees of freedom from 12 to 6-8.

**Files to modify**:
- `scripts/validate_candidate.py` — replace the current `_stability_check()` function (line ~130) with Morris EE method
- Possibly use `SALib` library (Morris method is built-in)

**Compute cost**: 330 backtests per strategy (r=30 trajectories x (D+1) = 30 x 11 = 330 for D=10 params). At 0.075s/backtest = ~25 seconds per strategy. 20 strategies = ~8 minutes total.

**Done when**: Each strategy has parameter importance ranking (mu*), interaction flags (sigma), and recommended fixed parameters.

---

### 2.2 Composite Fragility Score

**What**: Combine Morris results with LHS perturbation clouds into a single fragility index: S_frag = S_rob * S_int.

**Formula**:
- S_rob = 0.5 * R_mean + 0.3 * p_acc + 0.2 * R_0.05
  - R_mean = avg neighborhood fitness / peak fitness
  - p_acc = fraction above 80% of peak
  - R_0.05 = 5th percentile fitness / peak
- S_int = 1 - sum(w_j * sigma_j / (sigma_j + mu_j*)) (from Morris)
- S_frag = S_rob * S_int
- Gate: reject if S_frag < 0.40. For survivors: adjusted_fitness = raw_fitness * S_frag

**Files to modify**:
- `scripts/validate_candidate.py` — add composite scoring
- `scripts/evolve.py` — use S_frag as a multiplicative penalty on fitness

**Compute cost**: 200-300 LHS evals per strategy in addition to the Morris 330. Total ~530 evals/strategy x 20 = ~10,600 backtests = ~13 minutes.

**Done when**: Each strategy has `s_frag` score. Leaderboard fitness = raw_fitness * s_frag.

---

### 2.3 Cross-Asset Validation

**What**: Run each top strategy's exact parameters on TQQQ, UPRO, QQQ, XLK, and SOXL. Score >= 0.70 on TECL but < 0.55 on others = almost certainly overfit.

**Why**: The research unanimously identifies this as the single most powerful anti-overfitting test. If a trend-following strategy works on TECL, it should show some edge on similar instruments.

**Files to modify**:
- `scripts/data.py` — add fetchers for TQQQ, UPRO, QQQ, XLK, SOXL
- `scripts/validate_candidate.py` — add cross-asset validation step
- `scripts/strategy_engine.py` — ensure strategies work with any ticker's data (they should already, since they operate on price arrays)

**Compute cost**: 5 instruments x 20 strategies = 100 backtests. ~8 seconds total. Trivial.

**Done when**: Each strategy has `cross_asset_scores` dict and `cross_asset_pass` boolean (profitable on >= 3/5 instruments).

---

### 2.4 Regime Detection Meta-Robustness

**What**: Test whether leaderboard rankings are stable across different regime definitions. Use a 5x5 grid of bear thresholds (25%, 28%, 30%, 33%, 35%) x min durations (10, 15, 20, 25, 30 bars) = 25 definitions.

**Files to modify**:
- `scripts/backtest_engine.py` — parameterize the bear detection threshold and min duration in `compute_regime_score()` (currently hardcoded at 30% and 20 bars)
- `scripts/validate_candidate.py` — add meta-robustness sweep

**Compute cost**: 25 definitions x 20 strategies = 500 re-scorings (no backtests, just re-labeling). ~2 minutes.

**Done when**: Spearman rank correlation of leaderboard across all 25 definitions. Target: > 0.90. Strategies that drop out of top 10 under >3 definitions = flagged.

---

### 2.5 Stationary Bootstrap on Daily Returns

**What**: Resample daily equity curves using stationary bootstrap (Politis & Romano 1994) with B=200 resamples. Produces confidence intervals on Regime Score.

**Files to modify**:
- New: `scripts/bootstrap.py` — stationary bootstrap with automatic block length selection (use `arch` library's `StationaryBootstrap`)
- `scripts/validate_candidate.py` — add bootstrap CI step

**Compute cost**: 200 backtests per strategy (~15s each). 20 strategies = ~5 minutes total.

**Done when**: Each strategy has 90% CI on Regime Score. CIs that include 0.50 (no-skill baseline) = flagged.

---

## Tier 3: Bigger Lifts

### 3.1 Full 4-Stage Validation Pipeline + GitHub Actions Integration

**What**: Integrate Tiers 1 and 2 into the automated fail-fast funnel from the Compass report, then wire it into the GitHub Actions workflow so every spike run automatically screens for overfitting before committing results.

**Validation stages**:
- Stage 0: Free metadata gates (trade count, param ratio, degeneracy)
- Stage 1: Perturbation + deflation (77 sec)
- Stage 2: Walk-forward + regime consistency (2 min)
- Stage 3: Morris + bootstrap for survivors (12 min)
- Stage 4: Composite scoring + tiering (<1 sec)

**Files to modify**:
- New: `scripts/validation_pipeline.py` — orchestrates all stages, callable as `python3 scripts/validation_pipeline.py`
- `scripts/evolve.py` — gate leaderboard promotion through the pipeline
- `scripts/spike_runner.py` — run validation after optimization loop, before report generation
- `scripts/report.py` — add validation results section to the markdown report (tier, sub-scores, flags)
- `.github/workflows/spike.yml` — add a validation step between the optimizer and the commit step

**GitHub Actions changes** (`.github/workflows/spike.yml`):
The current workflow is: checkout → install → **run optimizer** → commit & push. It needs to become:

```
checkout → install → run optimizer → **run validation** → commit & push
```

Add a new step after "Run optimizer" and before "Commit and push results":

```yaml
- name: Validate leaderboard (overfitting screen)
  run: |
    python3 -u scripts/validation_pipeline.py \
      --leaderboard spike/leaderboard.json \
      --output spike/validation.json
```

This step:
1. Reads the leaderboard produced by the optimizer
2. Runs all validation stages on each strategy
3. Writes `spike/validation.json` with per-strategy tiers and sub-scores
4. Writes a human-readable summary to `spike/runs/NNN/validation.md`
5. Flags or rejects strategies that fail hard gates (but does NOT remove them from leaderboard — just annotates)
6. The commit step already does `git add spike/` so validation output is auto-committed

**Time budget**: The workflow has a 5-hour hard cap with 30-min buffer (timeout: 330 min). Validation takes ~20 minutes for 20 strategies. Options:
- (a) Reduce optimizer time by 20 minutes (e.g., pass `hours - 0.35` to spike_runner) — simplest
- (b) Add a `validate` input flag (default: true) so validation can be skipped for quick runs
- (c) Run Tier 1 only (~1 minute) for every run, Tiers 2-3 only on weekend/long runs

**Recommended**: Option (c) — always run the free/cheap checks (deflation, boundary perturbation, HHI, jackknife) and only run expensive checks (Morris, bootstrap, cross-asset) when the user opts in or the run is >= 3 hours.

**Compute cost**: ~1 minute (Tier 1 only) to ~20 minutes (full pipeline) for 20 strategies.

**Done when**: 
- Every spike run auto-produces `spike/validation.json` and `spike/runs/NNN/validation.md`
- Report.md includes a validation summary table with tiers
- Strategies that fail hard gates are annotated with warning flags in leaderboard.json
- `gh workflow run spike.yml` triggers the full optimize → validate → commit cycle

---

### 3.2 Synthetic Data Extension

**What**: Calculate synthetic 3x leveraged returns from QQQ (back to 1999) or NDX (back to 1985) using Avellaneda-Zhang formula: r_TECL = 3*r_underlying - 3*RV - fees. This captures the dot-com crash (NDX -83%) and 2008 GFC (NDX -54%) — regimes the optimizer has never seen.

**Files to modify**:
- `scripts/data.py` — add synthetic TECL generation from NDX/QQQ
- `scripts/evolve.py` — option to evaluate on extended dataset

**Compute cost**: One-time data generation + all backtests now run on 37-41 years instead of 17. Backtests take ~2x longer.

**Done when**: Top strategies are evaluated on 1985-present (NDX-derived) data. Strategies that fail on pre-2009 regimes are flagged.

---

### 3.3 PBO/CSCV (Monthly Aggregation)

**What**: Implement Probability of Backtest Overfitting using CSCV on monthly-aggregated returns with S=8 partitions.

**Files to modify**:
- New: `scripts/pbo.py` — adapt from code in `docs/research/reports/compass_artifact_wf-02502eac-...md` (lines 11-243)
- `scripts/validate_candidate.py` — add PBO check

**Compute cost**: ~0.02 seconds per strategy (pure matrix operations on pre-computed monthly returns). Negligible.

**Caveats**: 
- Use calibrated threshold ~0.20 (not the academic standard of 0.05)
- Pre-label regimes on full dataset before partitioning
- Apply 2-month embargo period between IS/OOS partitions
- PBO is supplementary — do not use as sole criterion

**Done when**: Each strategy has `pbo` score. PBO > 0.20 = flagged (not rejected — supplementary signal only).

---

### 3.4 N_eff Estimation (Eigenvalue Method)

**What**: Properly estimate the effective number of independent trials from the 918K correlated configs.

**Files to modify**:
- New: `scripts/n_eff.py` — eigenvalue analysis on a random subsample of 5,000 configs
- `scripts/deflate.py` — use N_eff from eigenvalue method instead of structural heuristic

**Compute cost**: ~6 minutes one-time (compute correlation matrix of 5,000 return series, extract eigenvalues above Marchenko-Pastur bound).

**Caveat**: Requires storing return series alongside hashes (not currently done). May need to re-run a subsample of configs and save return vectors.

**Done when**: N_eff estimate with confidence interval. Expected range: 150-5,000.

---

## Implementation Order

```
Sprint 1 (1 session): Tier 1 items 1.1-1.5
  → Deflated scores, boundary perturbation, cycle HHI, jackknife
  → Immediate signal on whether top strategies are noise or signal
  → Zero backtests needed

Sprint 2 (1 session): Tier 2 items 2.1-2.3
  → Morris sensitivity, composite fragility, cross-asset validation
  → ~13,000 backtests total, ~20 minutes compute
  → Answers "which parameters matter?" and "does this generalize?"

Sprint 3 (1 session): Tier 2 items 2.4-2.5 + Tier 3 item 3.1 (GH Actions integration)
  → Regime meta-robustness, bootstrap CIs, full pipeline assembly
  → Wire validation into spike.yml so every GH Actions run auto-screens
  → Tier 1 checks run on every spike run (~1 min overhead)
  → Full pipeline (Tiers 1-3) runs on opt-in or long runs (>= 3 hours)
  → Output: validation.json + validation.md auto-committed with results

Sprint 4 (1 session): Tier 3 items 3.2-3.4
  → Synthetic data, PBO, N_eff
  → Extends the testing window and calibrates all deflation methods
```

---

## Quick Reference: Hard Gates

These are the go/no-go thresholds from the research consensus:

| Gate | Threshold | Source |
|------|-----------|--------|
| Minimum trades | >= 15 | compass...2650.md |
| Parameter perturbation swing | < 30% at +/-10% | compass...2650.md |
| Deflated fitness | >= 0.95 | deflated-sharpe-evolutionary.md |
| Boundary robustness | < 15% degradation at k=5 | compass...c551.md |
| Walk-forward efficiency | >= 50% (not 85%) | compass...2cdad.md |
| Cycle concentration (HHI) | < 0.25 | compass...c551.md |
| Composite fragility | >= 0.40 | Fragility Scoring.md |
| Cross-asset profitability | >= 3/5 instruments | compass...c551.md, compass...a863.md |
| Regime meta-robustness | Spearman rank > 0.90 across definitions | compass...c551.md |
