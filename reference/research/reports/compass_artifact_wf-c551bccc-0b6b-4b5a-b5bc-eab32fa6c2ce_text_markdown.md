# Overfitting patterns hiding inside regime-conditional strategy scores

**A regime score built from 5–8 historical bull/bear cycles and optimized across 980K+ parameter configurations is acutely vulnerable to at least six distinct overfitting mechanisms**, several of which are invisible to standard backtest diagnostics. The composite metric (0.5 × bull_capture + 0.5 × bear_avoidance) creates a fitness landscape where the optimizer can achieve high scores through coincidental alignment with known regime boundaries, dominance by a single cycle, or sensitivity to the regime detector's own parameters—none of which implies genuine predictive ability. The literature on Goodhart's Law, backtest overfitting probability, and specification gaming converges on a clear conclusion: directly optimizing against a small-N regime-conditional metric is among the highest-risk optimization setups in quantitative finance. A concrete detection pipeline using seven statistical tests can flag these failure modes in under 15 minutes of compute.

---

## 1. Regime boundary memorization is the most insidious failure mode

A strategy can achieve perfect bear avoidance for a specific cycle when its exit signal happens to fire 1–3 bars before a known bear-market peak—not because it detected deteriorating conditions, but because a particular EMA length or threshold parameter coincidentally aligned with that historical date. With 8–12 tunable parameters and 980K+ configurations tested, the probability of at least one configuration producing this exact alignment is not small; it approaches certainty.

**Bai & Perron (2003)** provide confidence intervals for structural break dates in financial time series. When break-date uncertainty spans ±20 bars, any exit signal firing within that window is statistically indistinguishable from coincidence. **White (2000)** and **Hansen (2005)** formalize this through the Reality Check and Superior Predictive Ability test: bootstrap-based p-values for the null hypothesis that the best model from a specification search has no genuine superiority over a benchmark.

The core detection method is **boundary perturbation testing**: shift each identified regime boundary by ±k bars (k = 1, 2, 5, 10, 20) and recompute the strategy's regime score. A genuinely predictive strategy maintains its score because its signals are not tied to exact transition dates. An overfit strategy shows sharp score degradation with shifts of even 2–5 bars, because its "bear avoidance" collapses when the boundary no longer coincides with its exit signal. This test is computationally trivial—re-label regime boundaries, recompute the metric—and delivers the single most diagnostic signal for this specific overfitting pattern.

**Parameter sensitivity near transitions** provides a complementary view. Track which parameter values produce the sharpest regime timing. If a narrow parameter band (1–2% of the range) concentrates most of the regime-timing benefit, this is coincidental alignment rather than genuine detection. **Sullivan, Timmermann & White (1999)** developed bootstrap methods specifically for technical trading rules that account for the full universe of rules evaluated, directly applicable to this scenario.

Standard PBO (Bailey et al., 2016) is **blind to boundary-specific memorization** because it treats the time series holistically without decomposing performance by regime. A regime-aware variant of CSCV—partitioning by regime cycles rather than arbitrary time blocks—is necessary to detect this pattern.

---

## 2. Five to eight cycles cannot support statistically reliable regime-conditional inference

With only 5–8 bull/bear cycles, every summary statistic has dangerously low reliability. The standard error of a mean computed over N=6 observations scales as σ/√6, producing **95% confidence intervals spanning ±12 percentage points** for regime-conditional returns with typical volatility. A single outlier cycle contributes ~17% of the average, and if its metric is 3× the mean of others, it accounts for roughly half the total score.

**Lo (2002)** demonstrated that even unconditional Sharpe ratio estimation requires substantially more data than practitioners typically assume, with autocorrelation further inflating uncertainty. In a regime-conditional context, the effective T drops from ~4,250 daily bars to the number of bars within each regime type, and the effective N drops to the number of distinct cycles—making statistical inference fundamentally unreliable.

Standard power calculations confirm this: detecting a medium effect size (Cohen's d = 0.5) with 80% power requires **at minimum 16 observations per group**. With 5–8 regime cycles, the minimum detectable effect size at conventional significance is d ≈ 2.0—meaning the strategy must outperform by roughly two standard deviations of the per-cycle metric to be statistically distinguishable from noise.

**Concentration diagnostics** are essential alongside averages. The Herfindahl-Hirschman Index (HHI) applied to per-cycle score contributions reveals whether performance is distributed or concentrated. With N=6 cycles, HHI = 1/6 ≈ 0.167 indicates perfect consistency. **HHI > 0.25 signals meaningful concentration; HHI > 0.5 means one or two cycles dominate the score.** The inverse HHI gives the "effective number of contributing cycles"—if this falls below N/2, the regime score is unreliable. Shannon entropy and Gini coefficient provide complementary concentration views.

The **delete-one-cycle jackknife** is the natural diagnostic:

- Compute full-sample regime score θ̂ using all N cycles
- For each cycle i, compute θ̂₍₋ᵢ₎ by removing that cycle and recomputing
- Jackknife SE = √[(N-1)/N × Σ(θ̂₍₋ᵢ₎ − θ̄)²]
- Influence of cycle i = (N-1)(θ̄ − θ̂₍₋ᵢ₎)

Large influence values identify dominant cycles. If removing the 2022 bear drops regime score by 0.15 while removing any other cycle changes it by < 0.03, the strategy's apparent edge is concentrated in a single episode.

**Per-cycle scores must always be reported** alongside averages—both bull_capture and bear_avoidance for each individual regime cycle. This is the minimum standard for transparent regime-conditional evaluation.

---

## 3. Regime detection parameters are themselves a source of overfitting

The regime detection algorithm's own hyperparameters (30% drawdown threshold, 20-bar minimum duration) are not neutral choices. **Zakamulin & Primierski (2021)** explicitly demonstrate that "altering parameters which control assumed regime duration and/or amplitude characteristics may lead to significantly different classification results." **Lunde & Timmermann (2004)** show that standard parameter choices (λ₁ = 20%, λ₂ = 15%) produce dramatically different regime datings than λ₁ = 15%, λ₂ = 10% or λ₁ = 25%, λ₂ = 20%.

For **3x leveraged ETFs specifically**, this problem is amplified. Standard 20–25% drawdown thresholds were calibrated for equity indices. TECL experiences ~60–90% drawdowns when the underlying tech sector drops 20–30%, meaning threshold parameters need fundamental recalibration. The path dependency and volatility decay of leveraged products make regime transitions faster and more violent, further amplifying hyperparameter sensitivity.

**Pagan & Sossounov (2003)** adapted the Bry-Boschan business cycle dating algorithm to financial markets with multiple tunable parameters (window size, minimum phase length, minimum cycle length, amplitude threshold). Their framework reveals that each parameter choice creates a different "version of history" against which strategies are evaluated. When strategies are optimized against one specific version, they may implicitly exploit that version's idiosyncrasies.

**Shu, Yu & Mulvey (2024)** compare HMMs versus Statistical Jump Models for regime detection and find HMMs are especially sensitive: "HMM-inferred regimes display numerous short-lived regimes that are unintuitive and difficult to trade, arising primarily from the HMM's sensitivity to daily market noise." Their Jump Model approach uses time-series cross-validation to select the jump penalty hyperparameter—a form of perturbation-based validation.

The practical meta-robustness test is straightforward: construct a **5 × 5 grid** of bear thresholds (25%, 28%, 30%, 33%, 35%) × minimum durations (10, 15, 20, 25, 30 bars), producing 25 regime definitions. For each, re-detect regimes and recompute strategy rankings. Measure **Spearman rank correlation** between all pairs of regime definitions and check whether the top strategy remains in the top-K across perturbations. Mean rank correlation > 0.90 with > 90% stability indicates robustness. If strategy rankings reshuffle substantially (correlation < 0.70), the regime score is an artifact of the specific detection parameters chosen.

---

## 4. Alternative regime-aware metrics vary substantially in overfitting resistance

The literature identifies four main alternatives to bull-capture/bear-avoidance composites, each with different vulnerability profiles.

**Conditional Sharpe Ratio** decomposes the Sharpe ratio by regime: CSR_s = E[R − Rf | Regime = s] / σ(R − Rf | Regime = s). **Ahmed & Robotti (2024)** derive the conditional squared Sharpe ratio for model comparison under regime switching and find a critical asymmetry: under bull regimes, models are distinguishable; under bear regimes, "none of the competing models is significantly different." This implies bear-regime CSR has low discriminative power—a problem for strategies focused on bear avoidance. CSR inherits all standard Sharpe limitations (sensitivity to non-normality, autocorrelation) but compounds them by reducing T to regime-specific sample sizes.

**Regime Alpha** measures value-add beyond a naive regime-switching benchmark: α_regime = R_strategy − [P(bull) × R_asset + P(bear) × Rf]. **Lewellen & Nagel (2006)** show that unconditional alpha can be non-zero even when conditional alphas are always zero, due to time-varying beta correlated with the risk premium. This makes regime alpha a **more discriminating metric** because it strips out the largest component of apparent skill—the regime timing itself—and isolates genuine within-regime selection ability. For a trend-following strategy on a 3x ETF that generates massive unconditional alpha simply from avoiding 60–80% drawdowns, regime alpha asks the harder question: does the strategy outperform a simple bull/bear switch?

**Hamilton Markov-Switching model likelihoods** offer a probabilistic alternative to deterministic regime labeling. The log-likelihood of the strategy's returns under a fitted 2-state model serves as a holistic fitness metric capturing regime alignment. However, this introduces **6+ model parameters** (2 means, 2 variances, 2 transition probabilities), increasing overfitting risk. **Kole & Van Dijk (2017)** find rule-based approaches are preferred for in-sample identification while MS models are better for forecasting.

**Drawdown-adjusted regime metrics** (regime-conditional Calmar ratio, Conditional Drawdown at Risk) are **harder to overfit** because they are path-dependent. A strategy must maintain consistent performance over time sequences, not just across random return samples. **Magdon-Ismail & Atiya (2004)** derive analytical relationships between expected maximum drawdown and Sharpe ratio, providing a theoretical foundation.

**The GT-Score** (Sheppert, 2025/2026) integrates performance, statistical significance, consistency, and downside risk into a composite objective, claiming **98% reduction in overfitting** (generalization ratio 0.365 vs. baseline 0.185) and greater consistency across market regimes. This represents the state of the art in composite fitness design.

| Metric | Overfitting resistance | Key advantage | Key weakness |
|--------|----------------------|---------------|--------------|
| Bull-capture / Bear-avoidance | Low-Moderate | Intuitive, simple | Boundary-memorizable, small-N vulnerable |
| Conditional Sharpe | Moderate | Risk-adjusted per regime | Low discriminative power in bear regimes |
| Regime Alpha | High | Strips regime-timing credit | Requires benchmark construction |
| Regime-conditional Calmar | High | Path-dependent, hard to game | Noisy with few drawdown events |
| MS Model Likelihood | Moderate | Probabilistic, holistic | Parameter-heavy, distributional assumptions |
| GT-Score composite | Very High | Multi-dimensional, built-in significance | Complex to implement |

---

## 5. Cross-asset validation is the single most powerful overfitting test available

If a strategy truly captures a generalizable phenomenon in 3x leveraged products—momentum amplification, volatility regime dynamics, leverage rebalancing mechanics—it should transfer to structurally similar ETFs with different regime timing. **TQQQ** (3x Nasdaq-100), **UPRO** (3x S&P 500), and **FAS** (3x Financials) share daily rebalancing mechanics, volatility decay, and 3x amplification but have materially different drawdown timing, sector composition, and regime boundaries.

**López de Prado (2018)** specifically recommends: "Develop models for entire asset classes or investment universes, rather than for specific securities" as a primary defense against backtest overfitting. The **Man Group AHL Academic Advisory Board (2015)** roundtable reinforces this: "If you see the same breaking point across all strategies simultaneously, then a regime shift is likely. If the breaking point only appears for one strategy, it is more likely due to overfitting."

A 2025 study on leveraged ETF compounding effects (arXiv:2504.20116) confirms that "results are directionally consistent" across SPY-based and QQQ-based leveraged ETFs, validating that leverage mechanics create shared structural properties while noting "stronger deviations due to sector volatility" in QQQ products.

The cross-asset test's power derives from three properties. First, **different regime timing**: a strategy overfit to TECL's specific 2020–2022 drawdown timing won't coincidentally also align with FAS's different drawdown dates. Second, **shared structural properties**: if the strategy genuinely exploits leverage dynamics, it should transfer. Third, **independent samples**: each new asset is essentially a fresh out-of-sample dataset, and consistent performance across 4 structurally similar assets makes the probability of chance fitting extremely small (roughly p⁴ for independent assets at significance level p).

The practical implementation is straightforward: apply the exact same strategy parameters optimized on TECL to TQQQ, UPRO, and FAS daily data. Compute regime scores on each asset using that asset's own detected regimes. Report the cross-asset mean and standard deviation of regime scores. A strategy scoring ≥ 0.70 on TECL but < 0.55 on the other three is almost certainly overfit to TECL's specific history.

---

## 6. Optimizing 980K configurations against regime score is textbook Goodhart's Law

**Manheim & Garrabrant (2018)** taxonomize four failure modes of proxy optimization, all of which apply here:

**Regressional Goodhart** is the baseline risk: selecting the configuration that maximizes regime score selects for both genuine edge AND the difference between regime score and true profitability (noise). With only 5–8 regime transitions providing the signal, the noise-to-signal ratio is extreme.

**Extremal Goodhart** is the dominant risk: the relationship between regime score and true profitability was observed over a handful of cycles. The optimizer pushes parameters into regions where this limited-sample relationship breaks down. **Skalse et al. (ICLR 2024)** formalize this as a "Goodhart curve"—a predictable pattern where proxy optimization initially improves the true objective, then degrades it past a critical point. They prove this occurs even with positively correlated proxy and true rewards.

The **expected maximum from pure noise** provides a sobering calibration. For N i.i.d. standard normal random variables, E[max] ≈ √(2 ln N). With 980,000 configurations, this yields **E[max] ≈ 4.54 standard deviations**—meaning a strategy with zero genuine edge would still show an impressive apparent regime score if selected as the best of 980K trials.

The **Quantopian empirical study** (Wiecki et al., ~2016) analyzed 888 algorithms and found that commonly reported backtest metrics like Sharpe ratio offer **virtually no predictive value for out-of-sample performance** (R² < 0.025). "The more backtesting a quant has done for a strategy, the larger the discrepancy between backtest and OOS performance." Non-linear ML classifiers could predict OOS performance at R² = 0.17, far better than any single metric—but even this is modest.

**Bailey, Borwein, López de Prado & Zhu (2014/2016)** demonstrate through PBO that the configuration delivering maximum in-sample performance **systematically underperforms** remaining configurations out-of-sample—not merely fails to outperform, but actively underperforms. With the regime score's small-N structure making it an especially noisy fitness signal, this systematic degradation is expected to be severe.

The specification gaming literature from DeepMind (Krakovna et al., 2020) catalogs 60+ examples of optimizers finding unintended solutions that satisfy the literal metric specification without achieving the intended outcome. In this context, the "unintended solution" is a parameter set that coincidentally aligns with known regime boundaries, achieves high bear avoidance on one or two dominant cycles, and exploits the specific regime detection parameters chosen—all without any genuine market-timing ability.

---

## 7. A concrete seven-test overfitting detection pipeline

The following pipeline runs in approximately 15 minutes on pre-computed results (980K configurations with per-cycle regime scores already stored). It requires `numpy`, `scipy`, `pandas`, `statsmodels`, `seaborn`, and `matplotlib`.

**Test 1: Deflated Regime Score (~30 seconds).** Compute the cross-sectional variance of regime scores across all 980K configurations. Use the False Strategy Theorem to compute the expected maximum regime score under the null: RS₀ = 0.5 + √(Var[RS]) × ((1−γ)Φ⁻¹(1−1/N_eff) + γΦ⁻¹(1−1/(N_eff·e))), where N_eff is the effective number of independent trials (estimate via clustering ~15 strategy families × unique parameter dimensions). The deflated score is Φ((RS_observed − RS₀)/SE). DSR > 0.95 is green; 0.80–0.95 yellow; < 0.80 red.

**Test 2: Exact Permutation Test (~2 minutes).** With 6 regime cycles, there are only 2⁶ = 64 possible regime-label permutations—compute the exact null distribution. For the signal-shuffle variant, run 5,000 Monte Carlo permutations on the top 100 strategies: randomly permute the strategy's daily in/out signals while keeping regime labels fixed, recompute regime score each time. The p-value is the fraction of permuted scores ≥ observed. p < 0.05 is green; 0.05–0.10 yellow; ≥ 0.10 red.

**Test 3: Regime Perturbation Meta-Robustness (~5 minutes).** Construct a 5 × 5 grid of bear thresholds × minimum durations (25 regime definitions). For each, re-detect regimes on TECL price history, recompute regime scores for the top 1,000 strategies, compute rankings. Measure pairwise Spearman rank correlation across all 25 definitions and check whether the best strategy remains in the top 1% across perturbations. Mean rank correlation > 0.90 with > 90% stability is green; 0.70–0.90 or 70–90% stability is yellow; below those is red.

**Test 4: Parameter Neighborhood Stability (~3 minutes).** For the top strategy, identify all configurations within ±10% of each parameter value. Compute the mean regime score of this neighborhood and the "retention ratio" (neighborhood mean / best score). Generate 2D heatmap slices for the three most sensitive parameter pairs. Retention > 0.90 (plateau) is green; 0.75–0.90 is yellow; < 0.75 (spike) is red.

**Test 5: Cycle-Level PBO via CSCV (~2 minutes).** Sample 1,000 strategies from 980K (stratified by family). Build a matrix of shape (N_cycles × 1,000) with per-cycle scores. Enumerate all C(N, N/2) splits of cycles into IS/OOS halves (C(6,3) = 20 splits). For each split, find the strategy maximizing the IS-average regime score and record its OOS rank. PBO = fraction of splits where the IS-best ranks below the OOS median. PBO < 0.25 is green; 0.25–0.50 yellow; > 0.50 red.

**Test 6: Bootstrap Confidence Intervals (~1 minute).** Run 10,000 BCa bootstrap resamples of the top strategy's per-cycle scores. Report 95% confidence interval. If the lower bound exceeds 0.55 (meaningfully above the 0.50 null baseline of both buy-and-hold and always-cash), green. If it contains 0.50, red. Between 0.50 and 0.55, yellow.

**Test 7: Cross-Cycle Concentration (~30 seconds).** Compute HHI, effective N (1/HHI), and coefficient of variation (CV) of per-cycle regime scores. Report per-cycle breakdown table. CV < 0.30 and effective N > N/2 is green; CV 0.30–0.50 is yellow; CV > 0.50 or effective N < 3 is red.

### Output format: traffic-light dashboard

| Test | Metric | Value | Threshold | Signal |
|------|--------|-------|-----------|--------|
| Deflated Regime Score | DSR p-value | — | > 0.95 | 🟢/🟡/🔴 |
| Permutation Test | p-value | — | < 0.05 | 🟢/🟡/🔴 |
| Regime Perturbation | Mean rank ρ | — | > 0.90 | 🟢/🟡/🔴 |
| Parameter Stability | Retention ratio | — | > 0.90 | 🟢/🟡/🔴 |
| PBO (Cycle CSCV) | PBO estimate | — | < 0.25 | 🟢/🟡/🔴 |
| Bootstrap CI | 95% lower bound | — | > 0.55 | 🟢/🟡/🔴 |
| Cross-Cycle Concentration | CV / Effective N | — | CV < 0.30 | 🟢/🟡/🔴 |

**Overall verdict**: ≥ 5 green with 0 red = LOW overfitting risk. 3–4 green or any red = MODERATE risk. < 3 green or ≥ 2 red = HIGH overfitting risk.

Seven visualizations should accompany the dashboard: (1) permutation null distribution with observed score marked, (2) PBO logit histogram with fraction ≤ 0 annotated, (3) 2D parameter heatmaps for top parameter pairs, (4) regime perturbation rank-correlation matrix as heatmap, (5) per-cycle bar chart decomposing bull capture and bear avoidance by cycle, (6) histogram of all 980K regime scores with top strategy marked, and (7) bootstrap distribution violin plot with CI bounds.

An eighth test—**cross-asset validation** on TQQQ, UPRO, and FAS—requires additional data but should be considered mandatory. Apply the identical strategy parameters to each asset, compute regime scores using each asset's own detected regimes, and report cross-asset consistency. This single test may have more diagnostic power than all seven in-sample tests combined.

---

## Conclusion: the path to trustworthy regime scores

The regime score metric has attractive properties—it directly measures what matters for a leveraged-ETF trend follower—but its small-N structure makes it among the easiest metrics to overfit. **The expected maximum regime score from 980K trials of pure noise can be substantial**, and five to eight cycles provide insufficient statistical power to distinguish genuine skill from coincidence at conventional significance levels.

Three findings from this analysis are novel or underappreciated. First, **boundary memorization is a distinct and testable overfitting mode** that standard diagnostics like PBO miss entirely; the perturbation test (shifting regime boundaries by ±k bars) is the targeted remedy. Second, **the regime detection algorithm's own hyperparameters are a hidden degrees-of-freedom problem**—the 30% threshold and 20-bar minimum were themselves choices that could have been different, and strategy rankings may not survive perturbation of these parameters. Third, **cross-asset transfer to structurally similar leveraged ETFs is the most powerful single test** because it provides genuinely independent regime timing while preserving the structural hypothesis.

The practical recommendation is to never rely on the regime score alone. Run the seven-test pipeline, require cross-asset validation, report per-cycle scores with concentration metrics, and treat any strategy that fails two or more tests as likely overfit—regardless of how impressive its headline regime score appears.