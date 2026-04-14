# Distinguishing genuine convergence from overfitting in evolutionary trading optimizers

**The 980K configurations your GA has evaluated are not 980K independent trials — they are likely 150–1,500 effective trials, and with only 15–50 trades supporting 8–12 parameters, the system sits deep in overfitting territory by every statistical standard.** The good news: your existing evaluation database is a goldmine for computing convergence quality diagnostics at zero additional compute cost. Fitness landscape topology, population diversity trajectories, cross-run convergence patterns, and adapted MCMC diagnostics can all be derived from data you already generate. This report provides the complete theoretical foundation and implementation blueprint for a convergence quality sub-score.

---

## 1. Overfit optima are spikes; robust optima are plateaus — and you can measure the difference

The intuition that overfit optima are narrow spikes while robust optima are broad plateaus is well-supported across evolutionary computation, deep learning, and optimization theory. Hochreiter & Schmidhuber (1997) showed that flat minima — regions where fitness remains approximately constant — correspond to lower descriptive complexity and better generalization via a minimum description length argument. Keskar et al. (2017) demonstrated that stochastic gradient noise steers optimization toward flat minimizers that generalize better. The practical trading analog is direct: a strategy that only works at RSI period = 17.3 but breaks at 17.0 or 17.6 has found a noise artifact, not a market pattern.

**Critical caveat**: Dinh et al. (2017) showed that naïve flatness measures can be misleading due to reparameterization invariance. Schliserman et al. (2025, NeurIPS) proved that flat empirical minima can incur non-trivial population risk while sharp minima sometimes generalize optimally. Flatness is necessary but not sufficient — it must be measured in functionally meaningful ways.

### Measuring basin width from your 980K configs

Your hash-indexed database enables four complementary basin measurements without any additional evaluations:

**Concentric shell analysis** is the most intuitive. For each leaderboard strategy, normalize parameters to [0,1], compute Euclidean distance to all same-family configs, then bin into shells (e.g., d < 0.05, 0.05–0.15, 0.15–0.30). For each shell, compute mean fitness retention = shell mean fitness / peak fitness. A robust optimum shows **fitness retention > 0.85 out to d = 0.15**; an overfit optimum drops below 0.5 in the first shell. The decay rate — linear regression slope of fitness versus distance — quantifies the sharpness directly.

**k-nearest-neighbor fitness variance** provides a local smoothness measure. For k = 20–100 neighbors of each top config, low variance means a flat region (robust), high variance means a rugged spike (overfit). The **fitness-distance correlation** (Jones & Forrest 1995) around each candidate optimum should be strongly positive for genuine optima — fitness decays smoothly and monotonically with distance.

**Effective dimensionality via PCA** on the k-nearest high-fitness configs reveals the shape of the good region. If the first 2–3 principal components explain most variance, the high-fitness zone is a low-dimensional ridge, which is a stronger structural signal than a point optimum. If many components are needed, the fitness structure is complex and likely spurious.

**Exploratory Landscape Analysis (ELA)** features from the flacco (R) or pflacco (Python) packages compute ~300 landscape characterization features directly from (parameter_vector, fitness) pairs. The most relevant for overfitting detection include: `ela_meta.quad_simple.adj_r2` (high = smooth, broad basins), `disp.ratio_mean_02` (low = best solutions clustered into a funnel), `nbc.nn_nb.sd_ratio` (high = many separate basins), and `ic.h.max` (high = rugged landscape). These features are computable for free from your existing data.

### Formal results from evolutionary computation

Weinberger's **autocorrelation/correlation length** (1990) provides the key landscape diagnostic: compute the autocorrelation function ρ(d) of fitness values at parameter-space distance d, and find the correlation length τ where ρ drops to 1/e. **Short τ = rugged landscape with many narrow optima (high overfitting risk). Long τ = smooth landscape with broad basins (lower risk).** From your 980K configs, bin by pairwise distance and compute fitness autocorrelation at each bin.

Vassilev, Fogarty & Miller's **information content measures** (2000) quantify landscape ruggedness from random walks. Construct walks by connecting configs to nearest neighbors, classify each step as fitness-improving (+), declining (−), or neutral (0), then compute Shannon entropy of the symbol sequence. High entropy = rugged = many narrow optima = overfitting risk. These are computable from your database by constructing nearest-neighbor chains.

Ochoa et al.'s **Local Optima Networks** (2008) model the global structure of fitness landscapes. In this framework, a **single-funnel landscape** (all paths lead to one dominant basin) suggests a robust global optimum, while a **multi-funnel landscape** (many competing basins) raises overfitting risk. You can approximate funnel structure by identifying local optima in your database (configs whose fitness exceeds all nearest neighbors) and computing the dispersion of these optima.

---

## 2. Population diversity collapse is a warning signal, not proof of convergence

When all 60 individuals in a strategy family converge to nearly identical parameters, this is **highly suspicious** in the trading context. With population size 60 and 8–12 parameters, the population is small relative to dimensionality, making premature convergence likely. The 20% leaderboard seeding (12 individuals from prior winners) further accelerates convergence by biasing the gene pool toward historically successful — but possibly overfit — parameter regions.

### The diagnostic signatures

**Healthy convergence** shows gradual diversity reduction over 50+ generations, with moderate parameter spread remaining at plateau. The fitness landscape around the converged region is flat — neighboring configs retain >85% of peak fitness. Different strategy families find different parameter regions, reflecting genuinely distinct market signals.

**Suspicious convergence** shows rapid diversity collapse in <15 generations, near-zero parameter variance, and fitness that spikes then plateaus suddenly. The converged region is fragile — ±5% parameter perturbation causes large fitness drops. Leaderboard-seeded individuals dominate the final population, meaning the GA discovered nothing new.

### Metrics to track per generation

The most informative diversity metrics, ordered by diagnostic value:

**Normalized parameter variance** — for each parameter j, compute σ²_j / range_j² across the population, then average. This is your primary convergence indicator, computable in O(N×D) time. Track as a time series; the slope reveals convergence velocity.

**Mean pairwise distance** — (2/N(N−1)) × Σ ||x_i − x_j|| in normalized parameter space. For N = 60, this requires 1,770 pair computations — trivial. This is the gold-standard genotypic diversity measure.

**Shannon entropy per parameter** — discretize each parameter into 10–20 bins, compute H = −Σ p_k log(p_k). Maximum entropy = log(bins) = fully uniform. Near-zero = complete convergence. Use Zahl's unbiased estimator for the small population.

**Fitness variance** combined with genotypic diversity creates a powerful 2×2 diagnostic: low fitness variance + low genotypic diversity = converged (ambiguous). Low fitness variance + HIGH genotypic diversity = flat landscape, different parameters yield the same result — **this is actually a strong anti-overfitting signal**. It means the fitness landscape genuinely doesn't care about the specific parameter values, suggesting the strategy captures something structural.

### Active diversity maintenance

The optimizer should implement at least two mechanisms. First, **inject 5–10% truly random individuals each generation** alongside the leaderboard seeds. The current setup only injects prior winners, which reinforces convergence rather than testing it. Second, implement Ursem's **Diversity-Guided EA (DGEA)** switching rule: when diversity drops below D_low (15% of initial diversity), switch to pure mutation mode; when it exceeds D_high (60% of initial), switch back to selection-driven exploitation. This directly implements diversity-as-control-signal with minimal code changes.

---

## 3. Mutation should increase at convergence — the stress test is sound

The standard EA approach of reducing mutation during convergence (intensification) is exactly wrong for overfitting prevention. For trading strategy optimization, **convergence-triggered mutation bursts** are both theoretically grounded and practically valuable.

### Literature support for the stress test concept

The concept exists under several names in the literature. **Cataclysm operators** (IBM Patent US9305257B2, Cantin 2013) formally describe adaptive cataclysm controllers that detect premature convergence, diagnose the cause, and select from multiple disruption strategies including quarantining dominant genes, migration, and biased reseeding. **Hypermutation** from artificial immune systems (clonal selection algorithms) uses inversely proportional mutation — worse-matching solutions get mutated more. Heavy-tailed mutation operators (Friedrich et al. 2018) help escape deceptive basins of attraction, which is precisely what overfit basins are.

The biological precedent is compelling: Swings et al. (2017, eLife) showed that E. coli under near-lethal stress rapidly evolve hypermutation states, then return to normal mutation rates after adaptation. This is the exact biological analog of convergence-triggered bursts.

### The re-convergence stress test protocol

Your proposed concept — scatter the population via high mutation, then check if it re-converges to the same region — has strong theoretical grounding and maps directly to CMA-ES restart strategies (IPOP/BIPOP). Here is a concrete implementation:

Record the converged centroid. Replace 80% of the population with random individuals within full parameter bounds, keeping the top 20% as elites. Run N_stress generations (e.g., 20–30) with 3× normal mutation rate (±30% floats, ±3 integers). Record the new centroid. Compute a **reconvergence score** = 1 − ||new_centroid − original_centroid|| / max_possible_distance. Repeat K times (e.g., 3–5). If the mean reconvergence score > 0.7, the original basin is genuinely dominant in the landscape — a strong robustness signal. If < 0.3, the original convergence was likely to a narrow noise artifact.

### Recommended mutation regime

Replace the fixed ±10% mutation with a **three-regime adaptive system**. During normal exploration (high diversity), maintain current ±10%/±1. During exploitation (moderate diversity, diversity > 15% of initial), reduce to ±5%/±0.5. When diversity drops below 15% of initial OR fitness has not improved for K generations, trigger a **burst**: increase to ±30%/±3 for 5–10 generations. Alternatively, implement Doerr et al.'s (2018) **two-rate EA**: create half of offspring at 2× mutation rate and half at 0.5× rate, then adopt whichever rate produced the better offspring. This is provably optimal on certain function classes and trivial to implement.

---

## 4. Multi-run convergence is your strongest diagnostic signal

If a strategy converges to the same parameter region across independent nightly runs started from different random populations (with different 80% random components beyond the 20% seed), this is **strong evidence of a genuine basin of attraction**. The reasoning mirrors MCMC theory: if multiple chains initialized from overdispersed starting points converge to the same distribution, this operationalizes the principle that convergence is robust to initial conditions.

### What different convergence patterns mean

**Same region across runs**: The fitness landscape has a dominant basin that consistently captures populations from diverse starting configurations. This is the strongest evidence of genuine signal, though all runs share the same historical data, so consistent convergence to an overfit pattern is possible — cross-temporal validation remains essential.

**Different regions across runs**: Multiple local optima exist. If these regions have similar fitness, you have genuine alternative strategies. If fitness varies, the GA is getting trapped in suboptimal basins. If regions show no clustering at all (highly dispersed endpoints), the landscape is likely noise-dominated.

**Quantitative multimodality index**: Cluster the converged centroids across M runs using DBSCAN. Compute MI = (number of distinct clusters) / M. **MI < 0.2 suggests genuine convergence. MI > 0.5 suggests a noise-dominated landscape with high overfitting risk.**

### What to track across nightly runs

For each strategy family s and run r, log the centroid μ̂ and covariance Σ̂ of the top-10 parameter vectors, plus the best fitness trajectory. After accumulating ≥5 runs, compute the pairwise centroid distance matrix across runs. If centroid distances shrink over successive runs while fitness plateaus, the optimizer is homing in on a genuine signal. If distances remain large or oscillate, the signal is weak.

---

## 5. MCMC diagnostics translate directly to multi-population EA

The Gelman-Rubin R̂ statistic is the most natural adaptation. Each nightly run = one MCMC chain. The elite individuals from each run provide the "samples." The core formula compares **between-run variance B** (do different runs find different parameter regions?) to **within-run variance W** (how spread are elites within a single run?):

**R̂ = √(V̂ / W)** where V̂ = ((N−1)/N)·W + ((M+1)/(M·N))·B

Compute R̂ per parameter, per strategy family, using the top-10 elites from each of M runs. **R̂ < 1.05 indicates convergence across runs. R̂ > 1.2 indicates non-convergence — different runs are finding different regions.** Vehtari et al. (2021) recommend the stricter R̂ < 1.01 threshold and the improved rank-normalized split-R̂ variant, which handles non-normal parameter distributions and detects scale differences between runs.

```python
def compute_rhat_ea(param_matrix):
    """param_matrix: shape (M_runs, N_elites) for one parameter dimension"""
    M, N = param_matrix.shape
    chain_means = param_matrix.mean(axis=1)
    grand_mean = chain_means.mean()
    B = N / (M - 1) * np.sum((chain_means - grand_mean)**2)
    W = param_matrix.var(axis=1, ddof=1).mean()
    V_hat = (N - 1) / N * W + (M + 1) / (M * N) * B
    return np.sqrt(V_hat / W)
```

### Effective sample size for EA

ESS estimates how many truly independent configurations have been explored. Using the autocorrelation-based formula ESS = (M·N) / (1 + 2·Σ ρ̂_t), applied to centroid trajectories across generations, you can estimate the effective exploration. With population 60 and significant seeding, effective independence is much lower than the raw count. **Target ESS > 400 per parameter dimension** (Vehtari et al.'s recommendation) for reliable inference about convergence.

### Fitness trajectory stationarity via Geweke diagnostic

The Geweke test compares the mean of the first 10% of a fitness trajectory to the mean of the last 50%, using spectral density estimates to correct for autocorrelation. Under stationarity, Z ~ N(0,1). **Reject stationarity (convergence not achieved) if |Z| > 1.96.** Apply to best-fitness-per-generation, mean-elite-fitness-per-generation, and per-parameter centroid trajectories. If fitness trajectories have NOT achieved stationarity, the strategy is still improving and the current optimum is not the final answer.

### The R* classifier diagnostic

Lambert & Vehtari (2022) proposed training a random forest to discriminate between chains. **For EA: train a classifier to predict which run a parameter vector came from using the elite individuals.** If classification accuracy ≈ 1/M (chance level), the runs have converged to the same distribution — strong convergence signal. If accuracy >> 1/M, runs are distinguishable — non-convergence. This is a powerful multivariate diagnostic that captures parameter interactions that per-parameter R̂ misses.

---

## 6. Your effective trial count is roughly 150–1,500, not 980K

This is the most consequential finding for DSR/PBO calculations. The Deflated Sharpe Ratio threshold SR₀ grows as ~√(2·ln(N)), so using N = 980,000 versus N = 500 dramatically changes the significance threshold. With N = 980K, SR₀ ≈ 5.3 — virtually no strategy would pass. With N = 500, SR₀ ≈ 3.5 — still strict but achievable for genuine signals.

### Why 980K massively overcounts

With ±10% float mutations and 15–50 trades over 17 years, parent-offspring backtests are highly correlated (ρ ≈ 0.95–0.99). A 10% shift in a lookback period (e.g., 50 → 55 bars) changes very few trade signals. Using the MCMC autocorrelation formula, a lineage of L successive mutations produces approximately L × (1−ρ)/(1+ρ) ≈ **L/39 effective independent trials** at ρ = 0.95. The 20% leaderboard seeding further reduces independence by carrying forward prior search trajectories.

### Three estimation approaches

**Structural heuristic** (implement immediately): N_eff ≈ N_families × N_eff_per_family. With 15 families and 10–30 effectively independent parameter regions per family, **N_eff ≈ 150–450**. Use the higher estimate — López de Prado advises that overestimating N is safer because it makes the DSR test stricter.

**Eigenvalue method** (moderate effort): Sample ~2,000 configs, build a fitness correlation matrix, compute eigenvalues, apply Galwey's formula: M_eff = (Σ λ'_i)² / Σ (λ'_i)². This is the effective rank / participation ratio of the correlation matrix and typically yields **50–500** for correlated optimization runs. Implementable in ~10 lines of NumPy.

**ONC clustering** (gold standard): Store daily return series for a representative sample of configs, compute the return correlation matrix, apply the Optimal Number of Clusters algorithm (available in `mlfinlab`). N_eff = number of clusters found, likely **15–100**.

### The SRIC complement

Paulsen & Söhl's **Sharpe Ratio Information Criterion** (2020) provides a per-family correction: SRIC = SR_in-sample − (k+1) / (T × SR_in-sample), where k = number of parameters and T = number of return observations. This AIC-like penalty addresses parameter-space dimension within a single family, while DSR addresses multiple testing across families. **Use both**: SRIC corrects each strategy's Sharpe for its own parameter count, DSR corrects the best strategy's Sharpe for the number of independent strategies tested.

### The hash index gives a better upper bound if you hash trade sequences

Rather than hashing parameter vectors, hash the actual trade entry/exit date sequences. Two configs producing identical trade sets are functionally identical trials regardless of parameter differences. This gives a much tighter upper bound, likely **10,000–50,000**, which is still an overcount but far more realistic than 980K.

---

## 7. The trades-per-parameter problem is severe and must be addressed

With **15–50 trades and 8–12 parameters, the trades-per-parameter ratio is 1.25–6.25** — far below the minimum 10:1 ratio from regression statistics, and catastrophically below the 20:1 ratio that some authors recommend for financial applications. VC dimension analysis confirms the generalization bound is vacuous at this ratio. Even Fermi's famous quip — "with four parameters I can fit an elephant" — understates the problem here.

### Dimensionality reduction via sensitivity analysis

Run Morris screening or Sobol analysis on the 8–12 parameters using your existing 980K evaluations. Parameters with total-effect index ST_i < 0.05 contribute negligibly to fitness and should be fixed to default values. In practice, 3–4 parameters are typically insensitive (e.g., exact exit timing thresholds that rarely trigger). Reducing effective parameters from 12 to 6–8 dramatically improves the trades-per-parameter ratio and makes the generalization bound meaningful.

The Sobol first-order index S_i = Var_θi(E[Y|θ_i]) / Var(Y) can be estimated from your database by binning each parameter and computing the between-bin variance of mean fitness divided by total fitness variance. Parameters with high S_i are genuinely influential; parameters with low S_i are noise amplifiers.

---

## 8. The complete implementable diagnostic suite

Every metric below uses data the optimizer already generates — zero additional backtest evaluations required.

### Per-generation metrics (log every generation)

**Fitness trajectory**: best fitness, mean fitness, fitness std, delta_best (improvement from prior generation), plateau counter (consecutive generations with delta_best < 0.001).

**Parameter stability**: centroid drift (L2 norm of centroid change / centroid magnitude), per-parameter coefficient of variation across top-10, top-10 parameter consensus (range of each parameter in top-10 / full parameter range).

**Diversity**: mean pairwise distance in normalized parameter space, Shannon entropy per parameter, population uniqueness ratio.

**Free robustness proxy**: from existing parent-offspring mutation pairs, compute mutation survival rate = fraction of offspring retaining >90% of parent fitness. This is the perturbation robustness test you get for free from the GA's normal operation. A strategy whose offspring consistently maintain high fitness has a flat optimum; one whose offspring frequently collapse has a sharp, overfit peak.

### Per-run summary metrics

**Basin width score**: concentric shell analysis around each leaderboard config using same-family configs from the hash index. Report fitness retention at d = 0.05, 0.10, 0.15, 0.20 shells.

**Convergence quality flags**: did fitness achieve stationarity (Geweke |Z| < 1.96)? Did diversity stabilize rather than collapse to zero? Did the centroid stabilize (drift < 0.01 for final 20% of generations)?

### Cross-run diagnostics (after ≥5 runs)

**R̂ per parameter per family**: flag any parameter with R̂ > 1.1 as showing non-convergence across runs.

**Multimodality index**: cluster run endpoints, compute MI = clusters / runs. MI > 0.5 = high overfitting risk.

**ESS across runs**: target > 400 per parameter. If ESS < 100, the search space has not been adequately explored.

### Composite convergence quality score

Combine into a single 0–1 score with these weights:

| Component | Weight | Measures |
|---|---|---|
| **Mutation survival rate** (robustness) | 0.25 | Flat vs sharp optimum |
| **Cross-run R̂** (agreement) | 0.20 | Genuine vs path-dependent convergence |
| **Basin width** (landscape) | 0.15 | Broad plateau vs narrow spike |
| **Parameter stability** | 0.15 | Converged vs drifting |
| **Diversity health** | 0.10 | Maintained then reduced vs collapsed |
| **Regime consistency** | 0.10 | Scores well across all regimes vs one |
| **Fitness trajectory quality** | 0.05 | Smooth approach vs sudden spike |

A score above 0.7 feeds into the validation pipeline as evidence of genuine convergence. Below 0.4 triggers automatic flagging for additional out-of-sample testing before the strategy can be promoted.

---

## Conclusion: the hierarchy of trust

The single most important diagnostic is the **mutation survival rate** — the fraction of offspring that maintain >90% of parent fitness. This is a free, zero-cost proxy for perturbation robustness that directly measures the flatness of the optimum. Combined with cross-run R̂ (do independent runs agree?) and basin width from your hash index (is the neighborhood consistently high-fitness?), you get a three-pronged convergence quality assessment entirely from existing data.

The deeper structural problem is the trades-per-parameter ratio. With 15–50 trades and 8–12 parameters, **no amount of convergence diagnostics can rescue a fundamentally underdetermined optimization**. The most impactful single change is to run Sobol sensitivity analysis on your 980K configs, identify and fix insensitive parameters, and reduce effective dimensionality to 4–6 parameters. This alone shifts strategies from "hopelessly overfit" territory (1.25 trades/parameter) to "marginal but testable" territory (8–12 trades/parameter).

For DSR calculations, use N_eff ≈ 300–500 as your working estimate, derived from the structural heuristic (15 families × 20–30 independent regions per family). Validate this with the eigenvalue method once implemented. The key insight is that N_eff scales logarithmically in the DSR threshold, so even a 3× error in estimation produces only moderate impact on the significance cutoff — but using the raw 980K would inflate the threshold by ~50%, making virtually nothing significant.