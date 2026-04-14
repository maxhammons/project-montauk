# Statistical validation with 25 trades: what actually works

**With 15–50 trades across 17 years, most standard statistical validation methods have near-zero power — but two critical nuances change the picture.** First, the per-trade signal of a low-frequency strategy is surprisingly concentrated: an annual Sharpe of 1.0 with 1.4 trades/year yields a per-trade Cohen's d of 0.845, which *is* detectable at N=25. Second, the ~4,300 daily bars can power certain tests (like DSR on daily returns) even when trade-level tests fail. The honest answer, however, remains that most distributional tests are unreliable here, and the validation pipeline should pivot toward parameter robustness, cross-asset generalization, and Monte Carlo permutation benchmarks rather than confidence intervals or PBO.

This matters because investing engineering effort into tests with 20–40% power wastes time and generates false confidence. The research below quantifies exactly which tests work at each sample size, what the minimum thresholds are, and how professional macro/trend firms solve this problem — overwhelmingly through cross-asset diversification and theoretical justification rather than single-instrument statistical significance.

---

## Bootstrap CIs at N=25 deliver roughly 80–90% actual coverage, not 95%

The stationary bootstrap of Politis & Romano (1994) is indeed the right tool for time-series data, but it struggles badly at the sample sizes in play here. The core tension is that block length must be long enough to capture the autocorrelation structure (your trades span 50–200 bars), yet you need many independent blocks for reliable inference. These two requirements are in direct conflict at small N.

**For trade-level bootstrapping (N=15–50):** Hesterberg (2015, *The American Statistician*) demonstrated that the standard percentile bootstrap CI is *less accurate* than a classical t-interval for N ≤ 34. Monte Carlo simulations of the BCa bootstrap show actual coverage of a nominal 95% CI at roughly **82–84% for N=5, 89–91% for N=10, 91–93% for N=20, and 93–94% for N=40**. For time-series data with strong autocorrelation, Chandy, Schifano & Yan (2024) found that even N=100 often fails to achieve nominal coverage, and — remarkably — that percentile, BC, and BCa intervals can *deteriorate as sample size increases* for certain parameters in block bootstrap settings. At N=25 with block bootstrap and strong autocorrelation, expect actual coverage of **75–88%** for a nominal 95% CI.

**For bar-level bootstrapping (N=4,300):** This is more tractable. The Politis & White (2004) automatic block length selection algorithm would likely recommend block lengths of **50–200 bars** given the autocorrelation structure, yielding roughly 20–85 effective blocks. The Student's t block bootstrap CI — not the percentile or BCa — is the best-performing method for time-series data at moderate N. With ~43 effective independent blocks (at block length ~100), you're in the marginal N=25–50 range for the effective sample size, with expected coverage around **87–93%**.

**What block length to use:** For the stationary bootstrap, the expected block length parameter should be set via the Politis & White (2004) algorithm with the Patton, Politis & White (2009) correction (available in R's `blocklength` package or Python's `arch` package). The algorithm's upper bound is min(3√N, N/3) — for N=4,300, that's 197, which aligns with your longest trade durations. If bootstrapping at the trade level (N=25), any block length above 5 leaves fewer than 5 blocks, which is **catastrophically insufficient** for any bootstrap method.

**Practical recommendation:** Bootstrap bar-level equity returns using the stationary bootstrap with automatic block length selection. Use the Student's t bootstrap CI, not percentile or BCa. Report that actual coverage is likely 5–10 percentage points below nominal. Do not bootstrap trade-level returns if N < 50.

---

## What to bootstrap: bar-level returns are the least bad option

The choice of what to resample fundamentally determines whether your bootstrap is meaningful:

**Individual trade returns (N=15–50):** The effective sample size is the number of trades. At N=25, bootstrap CIs are unreliable (coverage ~80–88%). However, if trades are approximately independent (no overlapping holding periods, no serial correlation between trade returns), this is at least statistically clean. The problem is purely one of insufficient data.

**Bar-level equity returns (N=4,300):** More observations, but the data has a complex block structure — long streaks of "in trade" (generating alpha-related returns) alternated with "out of trade" (generating cash or benchmark returns). The block bootstrap can handle this if the block length exceeds the autocorrelation range. The **effective sample size** is N/(1 + 2Σρ_t), which with strong within-streak autocorrelation might reduce 4,300 bars to ~40–80 effective independent observations. This is marginal but workable. The key advantage is that DSR and similar metrics operate naturally on daily returns.

**Regime-level performance (N=5–8):** With only 5–8 observations, the minimum achievable one-sided p-value for a sign test is 2^(-N) = 0.031 for N=5 or 0.004 for N=8. The standard bootstrap from 5 observations generates only 5^5 = 3,125 possible samples. A t-test at N=6 requires Cohen's d > 1.2 for 80% power. **This is descriptive territory, not inferential.** A Bayesian approach with informative priors (e.g., from cross-asset evidence) is more intellectually honest here — with N=8 cycles and 7/8 successes, a Beta(8,2) posterior gives a mean of 80% with a 95% credible interval of [44%, 97%].

**Best approach for this setup:** Bootstrap bar-level returns for CI estimation. Use Monte Carlo permutation tests (random entry/exit benchmarks) at the trade level. Use Bayesian methods for regime-level statistics. Do not attempt to bootstrap regime-level observations.

---

## The power reality: which tests are worth implementing

The table below is the core deliverable. It shows approximate statistical power for each validation method given the user's constraints, calculated using standard power formulas (Cohen 1988, Lo 2002).

| Method | Sample size | True effect needed | Power | Verdict |
|--------|------------|-------------------|-------|---------|
| **Binomial win rate test** | N=25 trades | p=0.60 vs H₀:0.50 | **26%** | ❌ Useless |
| Binomial win rate test | N=25 trades | p=0.65 | **45%** | ❌ Inadequate |
| Binomial win rate test | N=25 trades | p=0.68 (17/25) | p≈0.054 | ⚠️ Barely misses α=0.05 |
| **t-test on trade returns** | N=25 trades | d=0.845 (SR_ann=1.0) | **99%** | ✅ Strong |
| t-test on trade returns | N=25 trades | d=0.50 | **56%** | ⚠️ Marginal |
| **Regime-level t-test** | N=6 cycles | d=0.50 (medium) | **21%** | ❌ Useless |
| Regime-level t-test | N=6 cycles | d=1.20 (huge) | **82%** | ✅ Only if effect is enormous |
| **CSCV/PBO** | N=25, S=8 | Any | **N/A** | ❌ 3 trades/subset = meaningless |
| CSCV/PBO | N=50, S=8 | Any | **N/A** | ❌ 6 trades/subset = still useless |
| **Walk-forward (4 windows)** | 4–13 trades/window | Any | **~15–25%** | ❌ Useless for inference |
| **DSR on daily returns** | T=4,250 bars | SR_ann > 0 | **Usable** | ⚠️ Works if strategy has daily return variation |
| **DSR on trade returns** | N=25–50 | Any | **Unreliable** | ❌ SE(skew)=0.49, SE(kurt)=0.98 |
| **Parameter sensitivity** | 50–100 perturbations | Plateau shape | **Qualitative** | ✅ Most useful single tool |
| **Permutation test** | N=25 trades | p=0.60 | **~26%** | ❌ Same power as binomial |

A critical nuance emerges from the per-trade Sharpe calculation. **Per-trade SR = SR_annual / √(trades_per_year) = 1.0 / √1.4 = 0.845.** This is a large effect size because each trade concentrates months of signal into a single observation. At d=0.845 and N=25, the t-statistic is 4.2, giving **>99% power**. This means a simple t-test on mean trade return *can* detect a genuinely good low-frequency strategy — but only if the strategy's edge is truly SR ≈ 1.0+ annualized and the trades are approximately independent. For SR=0.5 annually (d=0.42), power drops to ~40% at N=25, requiring **~35 trades** for 80% power.

The standard error of the Sharpe ratio at N=25 (per-trade basis) is SE(SR̂) ≈ √(1.5/25) = **0.245** for normal returns, widening to **0.354** when accounting for typical trading strategy skewness (γ₃ = −1) and kurtosis (γ₄ = 5). A 95% CI for an observed per-trade SR of 0.845 spans roughly (0.14, 1.55) under non-normality — wide, but excluding zero.

---

## Synthetic regime generation is viable but carries serious model risk

Since 5–8 real regime cycles are insufficient for inference, generating synthetic regimes is a reasonable approach — with important caveats.

**Markov regime-switching simulation** (Hamilton 1989) is the most principled approach. Fit a 2-state model to daily XLK (tech sector) returns, where State 0 (bull) has parameters μ₀, σ₀ and State 1 (bear) has μ₁, σ₁, with transition probabilities p₀₀ and p₁₁. The within-regime parameters are well-estimated from thousands of daily observations. The transition probabilities are the bottleneck — with only ~10–16 observed transitions from 5–8 cycles, these have wide confidence intervals. Bayesian estimation with informative priors (Albert & Chib 1993) can regularize this. After fitting, simulate new state sequences, draw regime-conditional daily returns, then apply 3x daily leverage via the Avellaneda-Zhang (2010) formula: **r_TECL = 3·r_XLK − 3·RV − fees**, where the volatility drag coefficient β(β−1)/2 = 3 for a 3x fund. This naturally produces regime-dependent LETF behavior including enhanced volatility decay during bear markets.

**Block resampling of entire regime legs** is simpler but more limited. With 5 bull and 5 bear legs, resample with replacement to create new alternating sequences. This perfectly preserves within-regime dependence structure but generates no new regime shapes — you cannot produce a drawdown worse than the worst observed, which is a significant limitation for stress-testing. The number of unique synthetic histories from 5 items is small (5^5 = 3,125 for each regime type).

**The key risks are real and substantial.** Model misspecification is the biggest danger: if real markets have 3+ regimes (low-vol bull, high-vol bull, bear) but you model only 2, synthetic data misses critical dynamics. López de Prado (2020) argues this is actually *more honest* than walk-forward backtesting because the data-generating process is explicitly stated — if someone objects to the model, they can propose an alternative. The practical recommendation is to test the strategy under **multiple DGPs** (regime-switching, GARCH, GBM with jumps, block-bootstrap) and assess robustness across all of them. Consistency across models is far more convincing than optimization under any single model.

**Monte Carlo permutation tests** (random entry/exit benchmarks) are a powerful complement. Generate 10,000 random strategies with the same number of trades and similar holding periods, then compare real strategy performance to this distribution. This directly answers "could this result have happened by chance?" without assuming any parametric model. Timothy Masters' work demonstrates these are "stable and reliable compared to bootstrap tests" for small samples. The limitation is that power equals the underlying binomial/t-test power for the same test statistic — permutation doesn't create information from nothing.

---

## How AQR, Man AHL, and Carver actually solve this problem

Professional macro and trend-following firms face exactly this low-trade-count problem. Their solution is **not** better statistics — it is a fundamentally different validation philosophy built on four pillars.

**Cross-asset generalization is the primary technique.** AQR tests across **67 markets** in 4 asset classes (Hurst, Ooi & Pedersen 2017). Moskowitz, Ooi & Pedersen (2012) demonstrated time-series momentum across **58 futures contracts** — every single one showed positive predictability. Rob Carver trades ~70+ instruments and backtests across 100+. Man AHL and Winton trade **hundreds** of markets. The strategy is intentionally kept simple (e.g., sign of past 12-month return) so the same rule applies everywhere. This multiplies effective sample size: 25 trades × 50 markets = 1,250 effective trades if markets are independent. **This is the single most important lesson for the user's pipeline.** A strategy validated on TECL alone will never achieve statistical significance through better tests — it needs cross-asset evidence.

**Long histories provide more regime coverage.** AQR constructs backtests back to **1880** — 137 years of data using hand-collected commodity futures data from Chicago Board of Trade annual reports. Before futures existed, they use cash index returns financed at local short-term interest rates. Critically, the first 100+ years are out-of-sample relative to the original research (Moskowitz et al. 2012 used 1985 onward), providing genuine temporal out-of-sample validation. Rob Carver uses 50+ years across 100+ instruments. For TECL specifically, since the ETF only launched in 2008, you'd need to reconstruct 3x leveraged tech sector returns from XLK or QQQ data going back further.

**Economic rationale substitutes for statistical significance.** When trade counts are inherently low, firms lean heavily on theoretical justification. AQR cites three specific behavioral mechanisms for trend-following: **anchoring** (investors adapt slowly to new information), **herding** (amplifying and extending trends), and **non-profit-seeking participants** (central banks, corporate hedgers creating persistent price pressures). Rob Carver explicitly separates strategies with and without economic rationale: "Where backtest results can't be logically explained, there is a good chance it is data-mining: pure luck, and not to be trusted regardless of statistical significance." For the user's regime-based strategy on TECL, the question is: *why* should bull capture + bear avoidance work? If the answer involves a documented anomaly (momentum, volatility timing, regime persistence), that provides a prior that reduces the statistical evidence burden.

**Simplicity and no-fitting are preferred to sophisticated overfitting tests.** Carver's most powerful prescription: "A very easy way to avoid over-fitting is to do no fitting at all." Use theory-driven fixed parameters, equal weights across strategies and instruments, and avoid optimization entirely. His system uses 8 trading rules with 30 variations, all combined with handcrafted (not optimized) weights. Harvey, Liu & Zhu (2016) recommend a **t-statistic threshold of 3.0** (not 2.0) for newly discovered factors after accounting for multiple testing. Carver notes that even "20 years of data and a pretty decent Sharpe ratio of 0.5" is insufficient to statistically confirm a positive Sharpe — the SE is ~1/√20 ≈ 0.22, giving t ≈ 2.2, which is marginal for a single test and fails after any multiple-testing correction.

---

## The minimum trades question has a clean formal answer

The universal minimum track record formula, derived from Lo (2002) and Bailey & López de Prado (2014), is: **minimum years ≈ 6.2 / SR²_annual** for 80% power at one-sided α=0.05. This holds regardless of trading frequency because what matters is cumulative information, not trade count per se.

| Annual Sharpe | Trades/year | Per-trade d | Min trades (80% power) | Min years |
|--------------|-------------|-------------|----------------------|-----------|
| 0.5 | 1.4 | 0.423 | 35 | 25 |
| 1.0 | 1.4 | 0.845 | 9 | 6.4 |
| 1.5 | 1.4 | 1.268 | 4 | 2.9 |
| 0.5 | 12 | 0.144 | 298 | 24.8 |
| 1.0 | 12 | 0.289 | 74 | 6.2 |

For the specific case of **25 trades with a 68% win rate** (17 wins, 8 losses): the one-sided binomial p-value is **0.054** — agonizingly close to but failing the α=0.05 threshold. You'd need 18/25 (72%) to cross the line (p ≈ 0.022). To detect a true 60% win rate with 80% power requires approximately **155 trades**. López de Prado's institutional guidance suggests **200–500 trades** for full confidence.

For **regime score with N=5–8 cycles**: the minimum achievable one-sided p-value is 2^(-N), which is 0.031 for N=5 or 0.004 for N=8. This means you can only achieve significance if the strategy works in *every single observed cycle* (or all but one at N=8). A t-test at N=6 requires Cohen's d > 1.2 for 80% power — the signal must exceed the noise by more than a full standard deviation, which essentially means the result must be visually obvious without any test.

---

## A practical validation pipeline for 25-trade strategies

Given these constraints, here is the most honest and useful set of statistical procedures, ranked by information value:

**Tier 1 — High value, implement first:**

Parameter sensitivity analysis across 50–100 perturbations of all key parameters. This is the single most powerful tool because it tests "is this parameter region profitable?" rather than "is this exact result significant?" — the former question is answerable at low N. If 70%+ of perturbations are profitable and the fitness landscape shows a broad plateau rather than a sharp peak, this is strong evidence against overfitting. Report the fraction of profitable perturbations and visualize the fitness landscape.

Monte Carlo permutation benchmark: generate 10,000 random strategies matching the real strategy's trade count, average holding period, and directional constraint (long-only). Compare the actual strategy's regime score to this distribution. Report the percentile rank. This directly answers "could random entry/exit produce this result?" and does not require parametric assumptions.

**Tier 2 — Moderate value, implement second:**

Cross-asset validation on related leveraged and unleveraged ETFs (QQQ, XLK, TQQQ, SOXL, or sector ETFs) to increase effective N. If the same regime logic produces positive results across 5–10 instruments, this is far more convincing than any single-instrument test. This is how AQR, Man AHL, and Winton validate low-frequency strategies.

t-test on per-trade returns with honest confidence intervals. With per-trade d = 0.845 (if SR_annual ≈ 1.0), this test has genuine power at N=25. Report the 95% CI on per-trade mean return and the implied annual Sharpe range, noting that actual coverage is ~85–90%.

DSR on daily returns (T ≈ 4,250), adjusting for the number of strategy configurations tested. This is one of few formal tests that functions here because it operates on the full daily return series.

**Tier 3 — Low value, implement only if time permits:**

Regime-level sign test (does the strategy outperform in every observed cycle?). Only informative at the binary level — perfect performance is significant; anything less is not. Consider supplementing with Bayesian estimation using a Beta prior.

Synthetic regime generation via regime-switching model for stress-testing (not statistical inference). Useful for asking "would this strategy survive a regime sequence we haven't seen?" but cannot create statistical power from 5–8 cycles.

**Do not implement:** CSCV/PBO (requires hundreds of observations per subset), walk-forward with formal statistical evaluation (2–6 trades per window is meaningless), bootstrap CIs on trade-level returns at N < 30, or DSR on trade-level returns (skewness and kurtosis estimates have standard errors of 0.49 and 0.98 respectively at N=25, making the correction unreliable).

**The output should look like:** A dashboard reporting (1) parameter sensitivity heatmap with % of profitable perturbations, (2) Monte Carlo percentile rank vs. random strategies, (3) per-trade return CI and implied Sharpe range, (4) DSR p-value on daily returns, (5) cross-asset consistency table, and (6) an explicit disclaimer: "With N=25 trades and 6 regime cycles, these results constitute hypothesis-generating evidence, not validated conclusions. The strategy requires forward-testing across additional assets and time periods before deployment."

## Conclusion

The fundamental insight is that **the validation problem cannot be solved with better statistics — it requires more data**, and the most practical way to get more data is cross-asset testing rather than longer backtests. A single-instrument, 17-year backtest with 25 trades is pre-statistical in nature. The per-trade Sharpe concentration effect (d=0.845 for SR_annual=1.0 at 1.4 trades/year) provides a narrow path to significance via the t-test, but this requires the edge to be genuinely large and the trades to be independent — assumptions that should themselves be scrutinized. Parameter sensitivity analysis, Monte Carlo benchmarking, and cross-asset generalization collectively provide more information than any combination of distributional tests. If this research changes one thing about the pipeline design, it should be this: **add cross-asset testing as the primary validation mechanism and treat single-instrument bootstrap CIs as supplementary evidence with wide uncertainty bands, not as gatekeeping criteria.**