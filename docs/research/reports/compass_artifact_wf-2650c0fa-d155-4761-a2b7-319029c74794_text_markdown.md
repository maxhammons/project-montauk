# Automated curve-fit detection for low-frequency trading strategies

**A strategy that scores 0.85 on your Regime Score may not beat pure chance when 980K configurations have been evaluated.** This is the central challenge: with 8–12 tunable parameters, 15–50 total trades across 17 years, and nearly a million tested configurations, the multiple-testing burden is so severe that standard academic methods (PBO, DSR, CPCV) either break down or require fundamental adaptation. The pipeline designed here addresses this by combining computationally cheap sensitivity analysis, bootstrap resampling of daily returns (not trades), and a Beta-distribution-based selection bias correction that properly handles the bounded [0,1] Regime Score. The entire validation suite fits within **~20 minutes** on a GitHub Actions runner for 20 leaderboard strategies.

---

## 1. A fail-fast funnel processes 20 strategies in four stages

The pipeline architecture follows a strict cheapest-first ordering. Near-zero-cost gates eliminate obviously overfit strategies before expensive compute is invoked. Each stage receives only strategies that survived the prior stage, conserving budget for the most promising candidates.

**Stage 0 — Free metadata gates (~0 seconds total).** These require no backtests, only inspection of existing optimizer output. Check trade count (reject if fewer than **15 trades**), check the ratio of effective parameters to regime transitions (flag if parameters exceed regime count), verify the strategy isn't degenerate (100% invested or 100% cash throughout any 4-year window), and confirm the GA converged for this strategy family (flag if fitness was still rapidly improving when the run terminated). Roughly **2–4 of 20 strategies** will be rejected or flagged here.

**Stage 1 — Cheap perturbation analysis (~2 minutes total).** Run a 5-point one-at-a-time perturbation (−20%, −10%, 0, +10%, +20%) on each of the 8–12 parameters independently. This costs **51 backtests per strategy × 20 strategies = 1,020 backtests ≈ 77 seconds**. Compute the maximum Regime Score swing. If any single parameter perturbation of ±10% causes a swing exceeding **30%**, reject the strategy outright — it sits on a knife-edge in parameter space. Swings of **20–30%** trigger a flag. Simultaneously, run the analytical selection bias adjustment (see Section 6) using pre-computed statistics from the 980K historical configs — this is pure arithmetic, taking under 1 second.

**Stage 2 — Medium-cost validation (~5 minutes total).** For surviving strategies, run three parallel tests. First, walk-forward analysis across 4 anchored-expanding windows (the system already computes this, so this may simply involve reading cached results; if recomputation is needed, **80 backtests per strategy ≈ 6 seconds each**). Second, regime consistency checks: verify bull capture and bear avoidance are both contributing to the score rather than one component carrying the entire weight. Third, trade clustering analysis: flag strategies where more than 60% of trades occur in a single 4-year window, which indicates temporal concentration rather than genuine regime-responsiveness.

**Stage 3 — Expensive validation for survivors only (~12 minutes total).** Typically **12–15 strategies** survive to this stage. Run two compute-intensive tests. The **Morris sensitivity analysis** (Elementary Effects method with r=30 trajectories and D=10 parameters) costs **330 backtests per strategy ≈ 25 seconds each, ~375 seconds total** for 15 strategies. This provides parameter ranking (μ* statistic) and interaction detection (σ statistic) equivalent in quality to Sobol total-order indices at roughly one-sixth the cost. Then run **stationary bootstrap** with B=200 resamples of the daily return series, re-running strategy logic on each resampled series: **200 backtests per strategy ≈ 15 seconds each, ~225 seconds total**. This produces confidence intervals on the Regime Score that capture uncertainty in both market conditions and trade generation.

**Stage 4 — Composite scoring and tiering (~1 second).** Combine all sub-scores into a single confidence metric and assign each strategy to a tier. Output JSON artifacts.

The decision tree for early termination at each stage:

- Stage 0 rejects → skip all subsequent stages
- Stage 1 fragility reject (>30% swing) → skip Stages 2–3, mark rejected
- Stage 1 selection bias adjustment shows score below null threshold → flag, but continue (the adjustment is approximate)
- Stage 2 walk-forward collapse (>25% OOS degradation in any window) → skip Stage 3, mark rejected
- Stage 2 regime consistency failure → flag, continue to Stage 3 with reduced priority

Parallelization is straightforward: **all strategies at each stage are independent** and can be processed concurrently if multiprocessing is available. Within a single-threaded constraint, process strategies sequentially but within each strategy, the walk-forward windows are independent.

---

## 2. Six sub-scores capture distinct overfitting failure modes

Each sub-score targets a specific way a strategy can appear good while being overfit. The taxonomy below is ordered by diagnostic value per compute-minute.

**Parameter fragility (S_frag).** This measures whether the strategy occupies a broad plateau or a narrow spike in parameter space. It maps to the **Morris Elementary Effects method**, which provides both μ* (average absolute effect of each parameter) and σ (standard deviation of effects, indicating interactions and nonlinearity). The compute cost is **330 backtests per strategy ≈ 25 seconds** at 0.075s per backtest. Statistical power is excellent — this test doesn't depend on trade count at all, only on the ability to evaluate the strategy function at different parameter values. Output is normalized to [0,1] where 1 means perfectly stable: **S_frag = 1 − (max_parameter_swing / 0.40)**, clamped to [0,1]. The 0.40 denominator means a 40% maximum swing at ±10% perturbation yields a score of zero. Threshold: S_frag < 0.25 (equivalent to >30% swing) triggers rejection.

**Walk-forward stability (S_wf).** This measures out-of-sample generalization across sequential time periods. It maps to **anchored walk-forward analysis** with 4 expanding windows. For 17 years of data (2007–2024), a practical windowing scheme uses anchored IS periods starting at 2007 and expanding, with 3-year OOS windows: IS=2007–2014/OOS=2015–2017, IS=2007–2017/OOS=2018–2020, IS=2007–2020/OOS=2021–2023, IS=2007–2021/OOS=2022–2024. Compute cost is **negligible if cached** from the optimizer run, or ~80 backtests ≈ 6 seconds if recomputed. Statistical power is **low** — each OOS window contains only 3–9 trades, making per-window metrics noisy. However, consistency across windows is informative as a qualitative signal. Output: **S_wf = mean(OOS_score / IS_score) across windows**, capped at 1.0. Threshold: S_wf < 0.50 (average OOS performance below 50% of IS) triggers a flag; any single window with OOS degradation exceeding **25%** triggers rejection.

**Selection bias adjustment (S_sel).** This measures whether the strategy's Regime Score exceeds what pure chance would produce given 980K trials. It maps to an **adapted False Strategy Theorem using Beta-distribution extreme value theory** rather than the standard Gumbel approximation (which is invalid for bounded metrics). Compute cost is **~1 second** — pure arithmetic using pre-computed statistics from the 980K historical fitness values stored in hash-index.json. Statistical power depends on the accuracy of the effective-N estimate (see Section 6 for details). Output: **S_sel = (observed_RS − expected_max_RS) / (1 − expected_max_RS)**, clamped to [0,1]. This represents how far the strategy's score exceeds the noise floor as a fraction of the remaining achievable range. Threshold: S_sel < 0.10 triggers a flag (strategy barely beats chance).

**Regime consistency (S_reg).** This measures whether both components of the Regime Score (bull capture and bear avoidance) contribute meaningfully, and whether performance is consistent across different regime instances rather than dominated by one lucky call. It addresses the failure mode where a strategy captures one spectacular bull run and avoids one spectacular bear market but is mediocre otherwise. No direct academic analog — this is a domain-specific diagnostic. Compute cost: **~0 seconds** (computed from existing backtest output). Statistical power is **very low** with only 3–4 bull and 3–4 bear regimes — essentially, you have 6–8 binary observations. Output: **S_reg = min(bull_consistency, bear_consistency)** where each consistency score is the coefficient of variation of per-regime performance, normalized to [0,1]. Threshold: S_reg < 0.30 triggers a flag.

**Trade sufficiency (S_trades).** This measures whether enough trades exist for any statistical inference to be meaningful. It addresses the **degrees-of-freedom problem**: with 8–12 parameters and only 15–50 trades, the ratio of observations to parameters is dangerously low. No complex computation needed — this is a sample-size adequacy check. Compute cost: **0 seconds**. Output: **S_trades = min(1.0, (trade_count − 10) / 30)**, which linearly scales from 0 at 10 trades to 1.0 at 40+ trades. Below 15 trades is a hard rejection gate.

**Bootstrap confidence width (S_boot).** This measures the precision of the Regime Score estimate by examining how much the score varies under resampled market conditions. It maps to the **stationary bootstrap** (Politis-Romano 1994) applied to daily returns. Compute cost: **200 backtests ≈ 15 seconds per strategy**. Statistical power is moderate — you're bootstrapping 4,420 daily returns (adequate sample) rather than 15–50 trades, but the resulting metric is computed from the synthetic trades, so CIs will still be wide. Output: **S_boot = 1 − (CI_width / observed_RS)**, where CI_width is the 90% bootstrap confidence interval width. A strategy whose CI spans more than its point estimate scores 0. Threshold: S_boot < 0.20 triggers a flag (the estimate is too uncertain to trust).

---

## 3. Weighted geometric mean balances conservatism with discrimination

The composite confidence score uses a **weighted geometric mean** of the six sub-scores:

```
Composite = S_frag^0.25 × S_wf^0.20 × S_sel^0.20 × S_reg^0.10 × S_trades^0.10 × S_boot^0.15
```

The weighted geometric mean was chosen over three alternatives after careful evaluation. A **weighted arithmetic mean** allows a high score in one dimension to mask a catastrophic failure in another — a strategy with perfect parameter stability but zero walk-forward generalization would still score respectably. A **pure minimum (weakest-link)** approach is too conservative: with six sub-scores, each measured noisily, at least one will underperform by chance, amplifying measurement noise into the composite. A **Bayesian combination** is theoretically ideal but requires well-calibrated priors that don't exist during cold start.

The geometric mean provides a natural **soft minimum** property: if any sub-score approaches zero, the composite approaches zero regardless of other scores. Meanwhile, it still rewards strategies that excel across multiple dimensions. The exponents (weights) determine each score's influence.

**Weight rationale.** Parameter fragility gets the highest weight (**0.25**) because with 8–12 tunable parameters and only 15–50 trades, a narrow peak in parameter space is the single strongest indicator of overfitting — and it's the sub-score measured with the highest statistical power (it doesn't depend on trade count). Walk-forward stability and selection bias adjustment share the second tier (**0.20 each**) as direct measures of generalization and multiple-testing risk, respectively. Bootstrap confidence width (**0.15**) captures estimation uncertainty. Regime consistency and trade sufficiency are supporting signals at **0.10 each** — important but either redundant with other scores or simple thresholds.

Concrete examples of how this scoring behaves:

- **All sub-scores at 0.80**: Composite = 0.80 (balanced good performance)
- **One sub-score at 0.10, rest at 0.90**: Composite ≈ 0.56 (one bad score sharply penalizes)
- **Fragility at 0.50, rest at 0.80**: Composite ≈ 0.72 (fragility weighted most heavily)
- **All sub-scores at 0.60**: Composite = 0.60 (mediocre across the board)

---

## 4. Four tiers separate deployment-ready strategies from noise

The tiering system combines hard gates (which trigger immediate rejection regardless of other scores) with the composite confidence score for graduated classification.

**Hard gates (any failure → REJECTED):**

- Fewer than **15 trades** across the full backtest period
- Any single parameter perturbation of ±10% causes Regime Score swing exceeding **30%**
- OOS degradation exceeding **25%** in any single walk-forward window
- Strategy is degenerate (never trades, or always invested)
- More effective parameters than regime transitions (e.g., 12 parameters with only 6 regime transitions)

**Tier thresholds:**

| Tier | Composite Score | Additional Requirements | Action |
|---|---|---|---|
| **High Confidence** | ≥ 0.70 | All sub-scores ≥ 0.50, passes all hard gates | Full leaderboard inclusion, green status |
| **Provisional** | 0.45–0.70 | No sub-score below 0.30, passes hard gates | Leaderboard with yellow status, reduced confidence |
| **Flagged** | 0.25–0.45 | Passes hard gates | Watchlist only, orange status, requires manual review |
| **Rejected** | < 0.25 or fails hard gate | — | Removed from leaderboard, logged for audit |

In steady state, expect roughly **3–5 strategies** at High Confidence, **5–8** Provisional, **4–6** Flagged, and **2–4** Rejected out of 20 leaderboard entries. This distribution reflects the reality that with 980K trials and small samples, most top-ranked strategies will show some evidence of overfitting. A leaderboard where all 20 strategies pass at High Confidence should itself be treated as suspicious.

---

## 5. Twenty minutes, thirteen thousand backtests, carefully allocated

The total validation budget of 15–30 minutes must be allocated across 20 strategies. The recommended allocation uses an **adaptive approach**: all strategies receive cheap tests, but expensive tests are reserved for strategies that survive the funnel.

| Method | Backtests/Strategy | Seconds/Strategy | Total (20 strategies) | Budget % |
|---|---|---|---|---|
| Perturbation (5-point OAT) | 51 | 3.8s | 77s (1.3 min) | 6% |
| Walk-forward (4 windows) | 80 | 6.0s | 120s (2.0 min) | 10% |
| Morris sensitivity (r=30) | 330 | 24.8s | 372s (6.2 min)* | 31% |
| Bootstrap (B=200) | 200 | 15.0s | 225s (3.8 min)* | 19% |
| Selection bias + PBO-lite | ~0 | 0.5s | 10s (0.2 min) | 1% |
| Overhead (I/O, JSON, setup) | — | — | 180s (3.0 min) | 15% |
| **Safety margin** | — | — | **216s (3.6 min)** | **18%** |
| **Total** | **~661 avg** | **~50s avg** | **~1,200s (20 min)** | **100%** |

*Morris and Bootstrap run only on the ~15 strategies surviving Stages 0–2, not all 20.

**Signal per compute-minute ranking.** The methods ordered by diagnostic value relative to their cost:

1. **Perturbation analysis** — 77 seconds reveals the single most important overfitting signal (parameter fragility). Unbeatable efficiency.
2. **Selection bias adjustment** — under 1 second provides the critical multiple-testing correction. Essentially free.
3. **Morris sensitivity** — 6 minutes produces publication-quality parameter sensitivity rankings equivalent to Sobol indices at one-sixth the cost. Literature confirms that Morris μ* correlates strongly with Sobol total-order indices.
4. **Bootstrap** — 4 minutes produces confidence intervals on the Regime Score that no other method provides.
5. **Walk-forward** — 2 minutes provides temporal generalization evidence, though its statistical power with 1–3 trades/year is limited.

**Minimum viable validation in 5 minutes.** If the budget shrinks to 5 minutes, run only Stages 0–1: free metadata gates, perturbation analysis, and the analytical selection bias adjustment. This covers ~80% of the diagnostic value at ~10% of the compute cost. Drop Morris and Bootstrap. You lose parameter interaction detection and confidence intervals but retain the two most discriminating tests.

**Adaptive allocation.** Rather than validating all 20 strategies equally, the pipeline can allocate extra Morris trajectories (r=50 instead of r=30) to the top 5 strategies by Regime Score. This costs an additional 110 backtests × 5 strategies × 0.075s ≈ 41 seconds — a worthwhile investment for the strategies most likely to be deployed.

---

## 6. Selection bias correction demands a Beta-distribution approach, not Gumbel

This is the most technically nuanced component of the pipeline and deserves careful treatment. The standard DSR/FST framework uses a Gumbel extreme-value approximation: E[max] ≈ μ + σ√(2·ln(N)). This is **invalid for the bounded [0,1] Regime Score** because bounded distributions fall in the **reversed Weibull (Type III) domain of attraction**, not the Gumbel domain. Using the Gumbel formula would overestimate the expected maximum, making the correction overly conservative and potentially rejecting genuinely skilled strategies.

**The correct approach uses the Beta distribution.** Fit a Beta(α,β) to the empirical distribution of all 980K Regime Scores stored in hash-index.json using method of moments: α = μ·[μ(1−μ)/σ² − 1] and β = (1−μ)·[μ(1−μ)/σ² − 1]. Then compute the expected maximum of N_eff draws as **F⁻¹(1 − 1/N_eff; α, β)** using `scipy.stats.beta.ppf()`. This is exact for the Beta distribution and trivially computable.

**Worked example.** Suppose empirical Regime Scores across 980K configs have mean μ = 0.48 and standard deviation σ = 0.12. Then α ≈ 7.85, β ≈ 8.52. With N_eff = 2,000 effective independent trials: expected max = Beta.ppf(1 − 1/2000, 7.85, 8.52) ≈ **0.78**. Any strategy scoring below 0.78 has not demonstrably beaten chance. With N_eff = 500: threshold drops to ≈ **0.74**. The sensitivity to N_eff is moderate, making the effective-N estimate important but not catastrophically so.

**Estimating effective N.** The 980K configurations are highly correlated — neighboring parameter values produce nearly identical strategies. Use the **Gao eigenvalue method**: sample ~5,000 configurations' daily return series, compute their correlation matrix, extract eigenvalues, and count the minimum number needed to explain 99.5% of variance. This is a one-time computation (cacheable across runs) costing ~5,000 backtests × 0.075s ≈ 6 minutes. In practice, **effective N is likely 500–5,000** (two to three orders of magnitude below raw trial count), reflecting the fact that ~15 strategy families with smooth parameter landscapes have far fewer truly independent configurations than 980K.

**Why standard DSR cannot be directly applied.** The Deflated Sharpe Ratio formula explicitly uses the sampling distribution of the Sharpe ratio estimator (Lo, 2002), which depends on the skewness and kurtosis of returns. The Regime Score has entirely different distributional properties — it's a composite ratio of regime participation counts, not a risk-adjusted return measure. Deriving an analogous "Deflated Regime Score" would require deriving the sampling distribution of the Regime Score under the null, which has no known closed form. The Beta quantile approach sidesteps this entirely by working directly with the empirical distribution.

---

## 7. Validation output schema tracks confidence across runs

The JSON schema below is designed for three consumers: a markdown report generator, the optimizer's leaderboard promotion logic, and longitudinal trend analysis across nightly runs.

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "run_id": "2026-04-07-nightly-a3f8",
    "timestamp": "2026-04-07T05:32:00Z",
    "git_sha": "abc123def",
    "optimizer_configs_evaluated": 302847,
    "total_historical_configs": 983412,
    "effective_independent_trials": 2340,
    "validation_runtime_seconds": 1182,
    "validation_budget_seconds": 1800,
    "data_range": {"start": "2007-01-03", "end": "2024-12-31"},
    "phase": "authoritative",
    "null_distribution": {
      "regime_score_mean": 0.48,
      "regime_score_std": 0.12,
      "beta_alpha": 7.85,
      "beta_beta": 8.52,
      "expected_max_at_current_neff": 0.78
    }
  },
  "strategies": [
    {
      "strategy_id": "trend_ma_cross_v3",
      "family": "moving_average_crossover",
      "parameters": {"fast": 21, "slow": 63, "atr_mult": 2.1},
      "num_parameters": 10,
      "regime_score": 0.87,
      "trade_count": 34,
      "regime_cycles": 7,

      "sub_scores": {
        "fragility":    {"value": 0.82, "max_swing": 0.072, "details": {}},
        "walk_forward": {"value": 0.68, "windows": [], "mean_degradation": 0.11},
        "selection_bias": {"value": 0.53, "raw_vs_threshold": [0.87, 0.78]},
        "regime_consistency": {"value": 0.71, "bull_cv": 0.15, "bear_cv": 0.22},
        "trade_sufficiency": {"value": 0.80, "trade_count": 34},
        "bootstrap_ci":  {"value": 0.61, "ci_90": [0.64, 0.94], "resamples": 200}
      },

      "sensitivity": {
        "method": "morris",
        "trajectories": 30,
        "evaluations": 330,
        "parameters": [
          {"name": "fast", "mu_star": 0.041, "sigma": 0.018, "rank": 3},
          {"name": "slow", "mu_star": 0.089, "sigma": 0.052, "rank": 1}
        ]
      },

      "composite_score": 0.69,
      "tier": "provisional",
      "flags": ["walk_forward_window_3_degradation_18pct"],
      "warnings": ["bootstrap_ci_width_exceeds_30pct_of_score"],

      "trend": {
        "composite_prev_run": 0.72,
        "composite_delta": -0.03,
        "composite_5run_avg": 0.71,
        "tier_prev_run": "provisional",
        "tier_changes_last_10_runs": 1
      }
    }
  ],
  "summary": {
    "high_confidence": 4,
    "provisional": 7,
    "flagged": 5,
    "rejected": 4,
    "mean_composite": 0.58,
    "alerts": ["strategy_x dropped from high_confidence to flagged"]
  }
}
```

**Key design decisions.** The `null_distribution` block in metadata stores the fitted Beta parameters and expected maximum, enabling downstream tools to recompute selection bias adjustments without re-fitting. The `trend` block within each strategy tracks composite score deltas and tier stability across runs, making it trivial to detect drift. The `phase` field ("cold_start", "calibrating", or "authoritative") signals to consumers how much weight to place on the validation results. Each sub-score includes both its normalized [0,1] value and the raw diagnostic values that produced it, supporting both automated thresholding and manual review.

---

## 8. Cold start resolves in three phases over ~20 runs

**Phase 1: Advisory only (Runs 1–5).** The pipeline runs all tests but outputs results as advisory — no automatic rejections beyond the hard gates (trade count, degenerate behavior). All sub-scores are logged. The `phase` field is set to "cold_start". The critical accelerator: **on the very first run, compute the null distribution by sampling 5,000 random configurations from hash-index.json** and fitting the Beta distribution. This immediately enables the selection bias adjustment without waiting for multiple runs. Similarly, the 980K historical fitness values provide the cross-sectional variance needed for effective-N estimation from day one.

**Phase 2: Calibrated thresholds (Runs 6–20).** After 5 runs, roughly 100 strategy-level sub-score observations exist (20 strategies × 5 runs). Compute empirical percentiles for each sub-score distribution. Set soft thresholds at empirical percentiles: bottom 20% of fragility scores triggers a flag, for example. Enable the full composite scoring but mark outputs as "calibrating". Hard gates remain at their theoretical values.

**Phase 3: Authoritative (Run 21+).** With 400+ observations, sub-score distributions are stable. Enable z-score-based anomaly detection for individual strategies (detecting drift relative to historical behavior). Trend tracking becomes meaningful. Mark outputs as "authoritative".

**The effective cold-start period is shorter than it appears.** Because hash-index.json already contains 980K evaluated configurations with their fitness values, the null distribution and selection bias adjustment can be computed authoritatively from run 1. What requires burn-in is the *per-strategy* trend tracking and the empirical calibration of sub-score thresholds — which genuinely need multiple runs to stabilize.

---

## 9. What works, what doesn't, and what to honestly tell yourself

This section addresses the methodological constraints with the candor the system demands.

**Methods that genuinely work with 15–50 trades:**

- **Morris/Sobol sensitivity analysis** works perfectly because it evaluates the strategy *function*, not the trade outcomes. It doesn't care how many trades the strategy produces — it only needs to call the backtest repeatedly with different parameter inputs. This is the single most reliable diagnostic in the pipeline.
- **Selection bias adjustment via Beta extreme-value theory** works because it operates on the cross-sectional distribution of 980K scores, not on individual strategy trade counts. The statistical power comes from the large number of trials, not from per-strategy observations.
- **Stationary bootstrap of daily returns** (~4,420 observations) is valid because you're resampling the market data (large sample), not the trades (small sample). Each bootstrap replicate generates a fresh set of synthetic trades, properly capturing uncertainty in both market conditions and trade timing.

**Methods that provide limited but nonzero signal:**

- **Walk-forward analysis** with 1–3 trades/year degenerates into anecdotes. Each OOS window contains 3–9 trades — far too few for statistical significance. However, **catastrophic OOS failure** (the strategy completely stops working in a window) is still informative, even from a small sample. Treat walk-forward as a sanity check, not a statistical test.
- **PBO/CSCV** can be computed in a "lite" form using 4–6 sub-periods, but each sub-period contains only 2–8 trades. The resulting PBO estimate will be noisy and should receive low weight. It's essentially free to compute (operates on pre-computed return matrices), so it's worth including but should not be a primary decision driver.

**Methods that fundamentally cannot work:**

- **Standard CPCV** requires meaningful training within each fold. With 1–3 trades per year and 6 folds, each fold contains 3–8 trades. You cannot train, evaluate, or infer anything meaningful from 3 trades. Skip this entirely.
- **DSR in its standard form** is mathematically specific to the Sharpe ratio. The formula depends on Lo's (2002) derivation of σ(SR̂) in terms of returns skewness and kurtosis. This does not generalize to the Regime Score. Do not use the DSR formula — use the Beta quantile approach instead.
- **Regime-level bootstrap** (resampling the 5–8 regime cycles) is impossible. You cannot form meaningful blocks or generate enough bootstrap samples with distinct compositions from 5–8 observations.
- **Bonferroni correction with 980K trials** requires p-values below 5.1 × 10⁻⁸. Nothing will pass. Even Benjamini-Hochberg at FDR=0.05 is extremely stringent unless you correctly estimate the effective number of independent trials (which reduces the burden by 2–3 orders of magnitude).

**The uncomfortable truth about 5–8 regime cycles.** The Regime Score is computed from strategy behavior across algorithmically-detected bull and bear periods. With roughly 3–4 bull regimes and 3–4 bear regimes in 17 years, **you have fewer regime observations than tunable parameters**. No statistical method can overcome this fundamental information-theoretic constraint. A strategy with 10 parameters and 7 regime transitions has more degrees of freedom than data points at the regime level. The validation pipeline can detect obvious overfitting (parameter fragility, failure to generalize out-of-sample), but it **cannot certify** that a strategy has genuine regime-timing skill. The honest framing is: "this strategy shows no evidence of overfitting" rather than "this strategy is validated."

**Regime Score–specific vulnerabilities** that the pipeline should monitor: hindsight bias in regime labeling (ensure regime detection uses only data available at decision time), leverage-decay conflation (TECL's 3x leverage means volatility avoidance looks like regime timing — test the same rules on the unleveraged XLK), and regime class imbalance (markets are bullish ~70–75% of the time, so 80% bull capture is nearly trivial; bear avoidance should carry disproportionate weight in the score).

---

## Conclusion

The pipeline's effectiveness rests on three pillars: **parameter sensitivity analysis** (Morris method) as the highest-signal diagnostic, **Beta-distribution selection bias correction** as the proper handling of 980K bounded-metric trials, and **honest epistemic boundaries** that acknowledge what 15–50 trades across 5–8 regime cycles cannot prove.

The total compute budget of ~20 minutes accommodates **~13,000 backtests** across 20 strategies — sufficient for Morris sensitivity, stationary bootstrap, walk-forward validation, and perturbation analysis. The fail-fast funnel architecture ensures that expensive tests run only on strategies that survive cheap gates, maximizing signal per compute-minute. The weighted geometric mean composite score naturally penalizes strategies with any near-zero sub-score while remaining discriminating among plausible candidates.

The most important implementation priority is computing the **effective number of independent trials** from the 980K historical configurations. This single number determines whether the selection bias threshold is 0.74 or 0.82, which in turn determines whether your best strategies clear the noise floor. Compute it once via the Gao eigenvalue method on a 5,000-configuration subsample, cache the result, and update it quarterly. Everything else in the pipeline is secondary to getting this right.