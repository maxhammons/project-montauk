# Fragility Scoring for Trend-Following Strategy Parameters

## Executive Overview

This report reviews parameter sensitivity and robustness techniques that are applicable to a medium‑complexity, long‑only trend‑following strategy with 8–12 tunable parameters, focusing on practical methods that fit a limited compute budget.
It draws on the global sensitivity analysis literature (Sobol, Morris/elementary effects, Latin hypercube and quasi–Monte Carlo designs) and practitioner material on trading‑system robustness and parameter stability.[^1][^2][^3][^4][^5][^6][^7]

Key conclusions:

- A single fixed ±10% one‑at‑a‑time perturbation is too narrow and too local; robust systems are typically evaluated over substantially wider ranges that are scaled to parameter type and transformed to a common domain before analysis.[^2][^4][^5][^6]
- For 8–12 parameters with a 0.1‑second backtest, full Sobol first‑ and total‑order indices are computationally heavy but feasible for a small number of top strategies; cheaper global screening via Morris/elementary‑effects plus Latin hypercube sampling is a better default.[^3][^4][^8][^9][^1]
- A composite fragility score should combine: (1) local degradation statistics around the optimum, (2) fraction of a local neighborhood that remains above a performance threshold, and (3) parameter‑importance weights from global screening; this is more informative than a single worst‑case swing threshold.[^10][^5][^6][^7]
- In trend‑following practice, robust strategies tend to show plateaus or gently sloping ridges in performance heatmaps across reasonable parameter ranges rather than isolated sharp peaks; practitioners explicitly recommend choosing parameters from stable regions rather than the single best point.[^11][^5][^6][^7]
- Robustness is best treated as a continuous score that either discounts fitness or acts as a secondary ranking key, with a loose hard floor to reject clearly fragile strategies; pure pass/fail gates based on ad‑hoc thresholds risk discarding useful but moderately sensitive systems.[^12][^5][^13][^10]

The rest of the report addresses each of the seven research questions in detail and then proposes a concrete fragility‑scoring workflow designed for 20 leaderboard strategies under a shared evaluation budget.

***

## 1. Perturbation Radius: How Far to Move Each Parameter

### 1.1 What the literature and practice suggest

Global sensitivity analysis texts emphasize that sensitivity should be assessed over a *meaningful fraction* of each parameter’s admissible range, not just an infinitesimal neighborhood, and that inputs should first be scaled or transformed to a common domain (often the unit hypercube).[^4][^14][^15][^1]
A widely cited handbook notes that for screening, sample designs probing on the order of at least 10 times the number of factors across their ranges are needed, underscoring that significant variation is expected in each dimension.[^16][^4]

Trading‑system optimization practitioners echo this: robustness checks generally sweep parameters over broad grids or random samples rather than narrow ±10% bands, and robustness is defined as stable performance across a *region* of parameter space.[^5][^6][^7]
An FX algorithmic‑trading robustness article, for example, shows a parameter‑stability plot where performance decreases slowly and almost linearly as parameters are moved substantially away from their calibrated values, and presents this as evidence of genuine robustness.[^7]

### 1.2 Parameter‑type‑specific radii

Given the ranges involved in typical trend‑following parameters, a heterogeneous perturbation radius is appropriate:

- **Lookback lengths (EMA windows, slopes)**: Integer ranges like 5–200 for EMAs or 3–30 for slope windows are often explored on coarse grids (e.g., step 5 or 10), and robustness is evaluated by inspecting heatmaps of performance over these grids.[^17][^18][^6][^11]
  - Several moving‑average studies show that profitable regions are not confined to single exact values; there are bands of short/long combinations that perform similarly.[^19][^20][^11]
  - Recommended: treat lookbacks on a log or square‑root scale and perturb by roughly ±30–50% of the value within bounds, with a minimum absolute step (e.g., ±3–5 bars for windows under 50 and ±10–20% of the range for longer windows).

- **Threshold percentages (e.g., EMA buffers, return thresholds)**: These are more sensitive because they sit close to economically meaningful boundaries (e.g., switching between trading and flat regimes).
  - Robust trend‑following construction pieces emphasize stress‑testing such thresholds across multiple values to ensure the edge is not dependent on a single tight level.[^21][^22][^23]
  - Recommended: perturb on a *relative* scale (log or logit transform if bounded in \\(0,1\\)) by ±25–50% of the value, but cap to stay within the plausible economic range; for example, a 0.5% buffer might be tested from about 0.25%–1%.

- **ATR multipliers and volatility scalers**: Literature on stop‑loss and profit‑target robustness typically varies ATR multipliers across wide ranges (often 1–5× or more) when computing robustness indices.[^10]
  - These parameters often show a broad range where risk‑adjusted performance is similar, with extremes degrading due to too‑tight exits or unbounded drawdowns.[^5][^10]
  - Recommended: use ±33–50% relative perturbations (e.g., 3 \\rightarrow test 2–4.5) within the allowed 1–5 range.

- **Bar counts (cooldown, confirmation bars)**: Small integers like 1–5 are effectively categorical; a ±10% perturbation is meaningless when rounding collapses it to the same integer.
  - Practitioner guidance on parameter stability explicitly warns against relying on tiny local perturbations for such discrete controls and instead advocates testing nearby discrete values directly.[^6][^5]
  - Recommended: use absolute steps (e.g., test 1–4 when base is 2–3) rather than percentages, and treat boundary cases with one‑sided moves.

Overall, a narrow ±10% band is too small for most of these parameters; a wider band (±30–50% for continuous‑like parameters, absolute steps for discrete ones) is more consistent with how robustness and stability are discussed both in the GSA literature and in trading‑strategy practice.[^1][^4][^6][^7][^10][^5]

***

## 2. Relative vs Absolute Perturbations for Integer Parameters

### 2.1 Issues with percentage perturbations on discrete parameters

Global sensitivity frameworks typically rescale all inputs to a continuous  range before analysis; integer parameters are treated as discrete levels within that range, not as quantities suited to small percentage nudges.[^24][^25][^8][^4][^1]
A ±10% adjustment to a small integer yields only one or two adjacent values, which can be insufficient to see meaningful changes in model output or uncover non‑monotonic behaviors.

In trading‑system optimization, parameter‑stability discussions consistently show performance surfaces over discrete grids, for example plotting performance over all pairs of short‑ and long‑term moving‑average lengths or over ranges of bar counts, rather than working with percentage perturbations.[^11][^6][^7][^5]

### 2.2 Recommended treatment of integer parameters

For EMA lookbacks, slope windows, bar counts, and similar integer parameters:

- **Use absolute steps mapped to scaled space**:
  - Define a grid around the base value: e.g., for EMA length 15, test {10, 12, 15, 18, 22} (approximately −33%, −20%, 0, +20%, +47%).
  - Map these discrete candidates to a normalized  coordinate for use in Morris or Sobol designs.[^24]

- **Handle boundaries explicitly**:
  - For parameters close to minimum values (e.g., cooldown_bars = 2 with domain ), construct an asymmetric neighborhood such as {1,2,3,4} instead of enforcing symmetric ± steps.[^17][^24]
  - Global sensitivity methods allow such asymmetries because the underlying sampling is done in normalized space; the grid of feasible integer points can be imposed afterward.[^8][^4]

- **Avoid over‑interpreting tiny moves**:
  - When the neighborhood contains only one distinct alternative (e.g., from 1 to 2 bars), use a wider absolute range to get multiple points; a single comparison cannot characterize sensitivity.

Relative perturbations remain suitable for continuous parameters (e.g., thresholds and multipliers), but integer and near‑integer controls should be probed via absolute steps or explicit discrete grids.

***

## 3. Multi‑Dimensional Sensitivity and Parameter Interactions

### 3.1 Sobol sensitivity analysis: feasibility and sample size

Sobol (variance‑based) global sensitivity analysis decomposes the variance of a model output into contributions from each input and from their interactions, yielding first‑order indices (main effects) and total‑order indices (main plus higher‑order effects).[^26][^15][^1]
A standard construction uses low‑discrepancy Sobol sequences and requires a sample size of approximately \\(N (d + 2)\\) model evaluations to estimate first‑ and total‑order indices, where \\(d\\) is the number of input parameters and \\(N\\) is a scaling factor.[^14][^1]

- A widely used tutorial notes that \\(N\\) is typically set to at least 1000 for reliable indices, with convergence checked by repeating the analysis at increasing \\(N\\).[^1]
- For \\(d = 10\\) parameters, this rule implies on the order of 12,000 model evaluations per strategy for a robust Sobol run.
- Reviews of global sensitivity workflows report that sample sizes in the 10,000‑combination range often yield stable rankings of influential parameters for models of moderate complexity.[^27][^4]

At 0.1 seconds per backtest, 12,000 evaluations consume roughly 20 minutes of CPU for one strategy if run serially; with parallelization this becomes feasible but still non‑trivial, especially if repeated for many leaderboard entries.
As a result, the literature and practice recommend Sobol analysis mainly for a limited subset of high‑value models rather than for all candidates.[^4][^27][^16]

### 3.2 Morris / elementary‑effects method as a cheaper alternative

The Morris (elementary‑effects) method is a global one‑factor‑at‑a‑time screening technique designed to balance accuracy and efficiency.[^9][^28][^2][^3][^8]
It constructs multiple random “trajectories” across a discretized parameter space and computes finite‑difference estimates of the effect of perturbing each factor along those trajectories.

Key properties:

- For \\(r\\) trajectories and \\(d\\) inputs, Morris requires \\(r (d + 1)\\) model evaluations; typical practice is to set \\(r\\) in the range 5–50.[^29][^8][^9]
- The mean of the absolute elementary effects for a factor measures its overall influence, while the standard deviation reflects nonlinearity and interactions (high variance indicates that the effect depends strongly on the values of other factors).[^25][^3][^8]
- Morris is qualitative: it ranks and screens variables and signals which ones are involved in interactions, but does not provide exact variance shares like Sobol indices.

For 10 parameters and \\(r = 20\\), Morris requires only 220 model evaluations, several orders of magnitude cheaper than Sobol at \\(N = 1000\\), while still revealing which parameters and interactions are most important.
This cost profile is well suited to screening 20 leaderboard strategies under a fixed compute budget.

### 3.3 Latin hypercube and quasi‑Monte Carlo designs

Sampling‑based studies commonly use Latin hypercube sampling (LHS) and quasi‑Monte Carlo (e.g., Sobol sequences) to fill the parameter space more efficiently than simple random sampling or full factorial grids.[^30][^31][^32][^1]

- LHS stratifies each marginal distribution to ensure coverage while keeping sample size modest; it is widely used in sensitivity studies for models with several inputs.[^31][^30]
- Reviews of global sensitivity methods state a rule of thumb that at least \\(10 \\times d\\) well‑spread samples are needed to identify key factors, with higher counts used for more precise index estimation.[^16][^4]

Quant‑oriented articles on robust trend‑following and parameter‑sensitivity surfaces explicitly recommend generating parameter combinations via LHS or Sobol sequences instead of dense Cartesian grids, then visualizing performance landscapes (heatmaps, surfaces) to identify plateaus and cliffs.[^22][^23][^33][^21]

### 3.4 How multi‑dimensional sensitivity is handled in trading practice

Commercial and educational trading platforms typically avoid exhaustive full‑factorial searches for strategies with many parameters; instead, they:

- Use sequential or ascent optimization for parameters, combined with subsequent robustness tests over neighborhoods or random samples.[^12][^6]
- Employ cross‑checks such as walk‑forward analysis, Monte Carlo resampling, and parameter‑stability plots to evaluate robustness rather than relying solely on a single in‑sample optimum.[^34][^13][^12][^5]
- Present parameter‑stability “heatmaps” where performance is plotted across grids of two key parameters (often lookback lengths), and robustness is judged visually by the presence of broad stable regions rather than isolated spikes.[^7][^11][^12][^5]

The upshot is that a combination of global screening (Morris or LHS‑based perturbations) and targeted, higher‑fidelity analysis (Sobol on a few top strategies) is aligned with both the academic literature and quantitative trading practice.

***

## 4. Designing a Composite Fragility Score

### 4.1 Conceptual building blocks

A useful fragility score should capture:

1. **Local sensitivity**: How quickly does performance degrade in a neighborhood around the calibrated parameters?
2. **Interaction structure**: Are there strong parameter interactions or nonlinearities that make the surface rugged and unpredictable?
3. **Volume of acceptable performance**: What fraction of a neighborhood around the optimum yields acceptably good performance (e.g., within 80% of peak)?
4. **Asymmetry and cliffs**: Are there directions in parameter space where performance collapses abruptly, even if the average behavior seems stable?

A robustness index proposed for trading systems (Backtesting Robustness Index, BRI) defines robustness as the ratio between the average performance metric over many perturbed parameter sets and the unperturbed performance, highlighting the value of averaging over a cloud of perturbations rather than inspecting a single worst case.[^10]
Trading‑system optimization guides stress choosing parameter values that are representative of a stable plateau instead of maximizing backtest performance at an isolated peak, again implying that average behavior and plateau width are central to robustness.[^6][^5][^7]

### 4.2 A practical composite fragility score

A concrete, model‑agnostic fragility score for each strategy can be constructed in three layers:

1. **Local perturbation cloud**:
   - Around the candidate parameter vector, generate \\(K\\) perturbed configurations using LHS or Sobol sampling within a parameter‑wise radius \\((r_j)\\) (relative or absolute depending on type, as discussed earlier).[^30][^31][^4][^1]
   - Evaluate the backtest for each configuration and record the primary fitness metric (regime score) and any secondary metrics of interest.

   Compute:
   - Mean relative performance: \\(R_{\text{mean}} = \operatorname{E}[f(\\theta')] / f(\\theta_{0})\\).
   - 5th‑percentile relative performance: \\(R_{0.05} = Q_{0.05}(f(\\theta') / f(\\theta_{0}))\\) to capture downside sensitivity.
   - Fraction of acceptable points: \\(p_{\text{acc}} = \Pr(f(\\theta') \geq \alpha f(\\theta_{0}))\\), with \\(
\\alpha\\) e.g. 0.8.

2. **Global screening via Morris**:
   - Run a Morris experiment over the same normalized neighborhood with \\(r\\) trajectories (e.g., 20–30) to estimate for each parameter:
     - \\(\mu_j^{\\*}\\): mean absolute elementary effect (importance).
     - \\(\sigma_j\\): standard deviation of elementary effects (nonlinearity/interaction indicator).[^3][^25][^8][^9]
   - Normalize \\(\mu_j^{\\*}\\) across parameters to get importance weights \\(w_j\\) that sum to 1.

3. **Composite fragility score**:
   - Define a robustness score \\(S_{\\text{rob}}\\) on \\([0,1]\\) as a weighted combination, for example:
     - \\(S_{\\text{rob}} = 
        
        0.5 \\cdot R_{\\text{mean}} 
        + 0.3 \\cdot p_{\\text{acc}} 
        + 0.2 \\cdot R_{0.05}\\).
   - Define an interaction penalty based on Morris indices:
     - \\(I = \\sum_j w_j \\cdot (\\sigma_j / (\\sigma_j + \\mu_j^{\\*}))\\), which increases as nonlinearities and interactions dominate.
   - Convert this into an interaction robustness factor, e.g. \\(S_{\\text{int}} = 1 - I\\).

   Finally, set the **overall fragility score** as:

   \\[ S_{\\text{frag}} = S_{\\text{rob}} \\cdot S_{\\text{int}}. \\]

This design blends average behavior (via \\(R_{\\text{mean}}\\)), tail behavior (via \\(R_{0.05}\\)), the thickness of the local plateau (via \\(p_{\\text{acc}}\\)), and the degree of interaction‑driven instability (via \\(S_{\\text{int}}\\), informed by Morris indices).
It is directly analogous in spirit to the BRI concept but enhanced with multi‑dimensional information and explicit attention to interaction structure.[^25][^8][^9][^3][^10]

### 4.3 Worst‑case vs average vs volume

Using a single worst‑case perturbation outcome as the fragility measure is discouraged in both the sensitivity‑analysis literature and trading‑system practice, because local cliffs in otherwise stable regions are common and can overstate fragility if considered in isolation.[^4][^5][^6][^1]
Averaging across a neighborhood (as BRI does) and incorporating the *volume* of acceptable performance (e.g., \\(p_{\\text{acc}}\\)) more faithfully reflects whether the optimum sits in a genuine plateau or on a precarious ridge.

Weighting by parameter importance (through the \\(w_j\\)) is also consistent with global sensitivity methodology, where parameters with low total‑order indices are often fixed or ignored in robustness assessments while influential parameters receive more scrutiny.[^15][^26][^1]

***

## 5. What Robust Performance Surfaces Look Like in Trend Following

### 5.1 Evidence from moving‑average and trend‑following studies

Studies and practitioner analyses of moving‑average crossover and trend‑following strategies often present performance surfaces across grids of short and long lookback periods.
These generally show that:

- Only a fraction of parameter combinations are profitable, but profitable regions tend to form *contiguous bands* or plateaus rather than single isolated points.[^20][^35][^21][^11]
- Heatmaps for robust strategies show reasonably smooth variation: performance changes gradually as one moves along the band, and only outside these bands do sharp drops appear.[^21][^11][^7]
- An MQL5 article on a long‑lived trend‑following system explicitly demonstrates that changing a key parameter from 10 to 20 (a 100% change) leaves performance “relatively stable” with no major deviation, and uses this as confirmation of robustness.[^36]

Parameter‑optimization blogs focused on robustness explicitly advise avoiding “unstable profit peaks” and instead picking parameter sets located in broad, stable regions where neighboring combinations perform similarly.  Another robustness‑assessment article for FX algorithmic strategies shows a parameter‑stability plot where the performance curve declines slowly and linearly as parameters move away from their optimal values, again highlighting the absence of sharp cliffs as a robustness hallmark.[^5][^6][^7]

### 5.2 Expected geometry: plateaus, ridges, and fraction of acceptable space

In the context of a trend‑following system with EMAs and volatility‑based filters:

- **Performance plateaus**: Robust systems commonly exhibit plateaus where varying lookback lengths or thresholds within a band produces similar Sharpe or regime scores; this is especially evident when lookbacks are scaled to the volatility and autocorrelation structure of the underlying.[^22][^20][^21]
- **Ridges along economic structure**: Performance ridges often align with economically meaningful relationships, such as short‑to‑long moving‑average ratios or volatility‑adjusted thresholds, rather than with arbitrary absolute parameter values.[^11][^21][^6]
- **Cliffs at extremes**: Very short lookbacks or extremely tight thresholds tend to produce over‑trading and noise‑dominated behavior, while extremely long lookbacks or very loose thresholds delay response and degrade performance; these regions appear as low‑performance valleys surrounding the main plateaus.[^18][^21][^17][^11]

The quantitative literature does not prescribe a specific numeric fraction of parameter space that “should” be acceptable, because this depends heavily on how the domain and priors are defined.[^14][^16][^4]
However, robustness practitioners in trading often use informal criteria such as “most of the surrounding grid cells are profitable” or “the chosen parameters are near the center of a broad profitable region,” which can be formalized as requiring that a meaningful minority (for example, several percent of the local neighborhood volume) lies above a chosen performance threshold.[^33][^6][^7][^5]

***

## 6. Pass/Fail vs Continuous Scoring

### 6.1 How robustness is typically used in trading workflows

Trading‑system development tools and educational materials treat robustness tests—Monte Carlo resampling, walk‑forward, parameter stability—as part of a *filtering and ranking* process rather than as single hard gates.[^13][^34][^12][^5]
Typical workflows:

- Discard obviously overfit systems that fail multiple robustness tests (e.g., large degradation under OOS or Monte Carlo perturbations).
- Among remaining systems, prefer those with smoother parameter‑stability surfaces or better performance under perturbations, even if their raw in‑sample metrics are slightly lower.

The BRI concept presents robustness as a percentage factor that can be compared across systems (e.g., BRI above 100% is excellent, between 50% and 100% is good, below 50% suggests overfitting), again treating robustness as a continuous score rather than a binary outcome.[^10]

### 6.2 Recommended use: soft gates plus continuous discounting

Given this context, a reasonable approach for a regime‑score‑based optimizer is:

- **Compute a continuous fragility score** \\(S_{\\text{frag}}\\) as described in Section 4.
- **Apply a soft hard gate**:
  - Reject strategies with \\(S_{\\text{frag}} < S_{\\min}\\) (e.g., 0.4–0.5) as clearly overfit or overly fragile.
- **For survivors, either**:
  - Use *multiplicative discounting*: \\(f_{\\text{adj}} = f_{\\text{raw}} \\times S_{\\text{frag}}\\), which directly penalizes fragile strategies while allowing them to compete if their raw fitness is high enough, or
  - Treat \\(S_{\\text{frag}}\\) as a secondary sort key: first rank by \\(f_{\\text{raw}}\\), then by \\(S_{\\text{frag}}\\), or by a lexicographic rule such as “
  prefer strategies with \\(S_{\\text{frag}} \\geq 0.8\\) even at some cost in raw score.”

This structure mirrors guidance in optimization literature that emphasizes robust optimal solutions—solutions that achieve near‑optimal objective values while minimizing losses under perturbations in parameter space—and often expresses robustness in terms of expected loss or expected distance in objective space.[^37]
It also reflects trading‑system guidance that warns against selecting parameter sets at isolated peaks and instead encourages sacrificing some raw performance for stability.[^6][^7][^5]

***

## 7. Compute Budget and Recommended Workflow

### 7.1 Budget implications of different methods

Under the assumption of approximately 0.1 seconds per backtest evaluation, the compute costs of candidate sensitivity methods are roughly:

- **Single strategy, Sobol with \\(N = 1000, d = 10\\)**:
  - Evaluations: about 12,000 per strategy.[^1]
  - Time: about 20 minutes serial; less with parallel execution.

- **Single strategy, Morris with \\(r = 20, d = 10\\)**:
  - Evaluations: 220 per strategy.[^8][^9]
  - Time: under a minute serial.

- **Local perturbation cloud** (e.g., \\(K = 200\\) LHS points in a neighborhood):
  - Evaluations: 200 per strategy.
  - Time: comparable to Morris, under a minute serial.

Given a shared budget on the order of a few hundred thousand evaluations for all strategies, full Sobol analysis for every leaderboard configuration would be expensive, but combining cheap screening and local clouds for all candidates with full Sobol only for a handful of finalists is feasible.
This aligns with global sensitivity workflow recommendations, where large‑sample Sobol runs are reserved for models that have already passed preliminary screening.[^27][^16][^4]

### 7.2 A staged workflow for 20 leaderboard strategies

A practical, high‑signal‑per‑compute workflow could be:

1. **Parameter normalization and radius definition** (once per strategy):
   - Map each parameter to \\[0,1]\\) using appropriate transforms (log for scale parameters, logit for bounded thresholds, linear for simple counts), and define parameter‑wise perturbation radii \\((r_j)\\) as per Section 1.

2. **Morris screening for all 20 strategies**:
   - For each strategy, run a Morris experiment with \\(r = 20\\) trajectories over the normalized domain restricted to a neighborhood around the current parameter vector.
   - Cost: roughly 220 evaluations \\times 20 strategies \\approx 4400 backtests.
   - Output: rankings of parameter importance and indicators of where interactions and nonlinearities are significant.

3. **Local perturbation clouds for all 20 strategies**:
   - For each strategy, draw \\(K \\approx 200–300\\) LHS points within the local hyper‑rectangle defined by the radii \\((r_j)\\).
   - Cost: about 4000–6000 additional evaluations across all strategies.
   - Output: empirical distributions of regime scores, \\(R_{\\text{mean}}\\), \\(R_{0.05}\\), and \\(p_{\\text{acc}}\\) for each strategy.

4. **Compute fragility scores**:
   - Combine local statistics and Morris indices into \\(S_{\\text{frag}}\\) as described above.
   - Apply a soft hard gate (e.g., drop strategies with \\(S_{\\text{frag}} < 0.4\\)) and compute adjusted fitness values.

5. **Optional Sobol analysis for top 3–5 strategies**:
   - For the highest‑ranked systems by adjusted fitness, run a Sobol analysis with \\(N\\) chosen based on convergence but likely in the 500–1000 range, yielding around 6000–12,000 evaluations per strategy.
   - Use first‑ and total‑order indices to sanity‑check that the Morris‑identified important parameters remain dominant and that strong, unexpected interactions do not dominate variance.

The total cost of Morris plus local clouds for 20 strategies is on the order of 10,000 evaluations, a small fraction of a 300,000‑evaluation budget, while providing enough information to compute a meaningful fragility score for each strategy.
Optional Sobol analysis on a few finalists may raise the total cost to perhaps 70,000–80,000 evaluations, still well within budget.

### 7.3 Integration into an evolutionary optimizer pipeline

Given that the evolutionary search has already evaluated close to a million parameter configurations for the underlying strategy, the sensitivity analysis can be integrated as a post‑processing step applied only to strategies that reach the leaderboard.
This is consistent with guidance from both sensitivity‑analysis and quantitative‑finance literatures, which stress separating the model search phase from robustness evaluation and applying more demanding robustness diagnostics only after promising candidates are identified.

The fragility score \\(S_{\\text{frag}}\\) can be stored alongside each strategy’s fitness metrics and used either as a multiplicative discount to regime score or as a secondary ranking dimension when selecting strategies for deployment or further analysis.

***

## 8. Summary of Practical Recommendations

1. **Abandon fixed ±10% perturbations** in favor of parameter‑type‑aware radii: ±30–50% for continuous parameters like lookbacks and ATR multipliers (within bounds), and discrete multi‑step grids for small integer parameters.
2. **Normalize parameters to \\[0,1]\\)** and perform global sensitivity analysis in that space; treat integer parameters as discrete grids mapped into the normalized domain, not as objects for tiny percentage moves.[^1][^4][^25][^8]
3. **Use Morris / elementary‑effects analysis** as the default global screening tool for all leaderboard strategies to obtain parameter‑importance rankings and interaction indicators at low computational cost.[^2][^9][^3][^8]
4. **Augment Morris with local perturbation clouds** (LHS or Sobol samples within a neighborhood) to estimate average and tail performance degradation and the fraction of acceptable parameter configurations around the optimum.[^31][^33][^30][^4][^1]
5. **Define a composite fragility score** \\(S_{\\text{frag}}\\) combining mean robustness (BRI‑style), tail robustness, plateau volume, and interaction penalties derived from Morris indices, and express it on \\[0,1]\\) for direct interpretability.
6. **Treat robustness as a continuous factor** with a soft hard gate and either multiplicative discounting of fitness or use as a secondary ranking key, rather than as a single binary pass/fail test based on an arbitrary threshold.
7. **Reserve full Sobol variance‑based analysis** for a small set of top strategies, using sample sizes in the 500–1000 range and checking convergence of indices, to validate insights from Morris and obtain detailed variance decompositions without exhausting the compute budget.

Taken together, these steps yield a fragility‑scoring system that is more statistically grounded than simple one‑at‑a‑time ±10% tests, captures multi‑dimensional interactions, and fits comfortably within the stated compute budget for a TECL trend‑following optimization pipeline.

---

## References

1. [3. Sensitivity Analysis: The Basics](https://uc-ebook.org/docs/html/3_sensitivity_analysis_the_basics.html) - The Sobol method is able to calculate three types of sensitivity indices that provide different type...

2. [Stastistical Sensitivity Analysis - Morris' method - OpenMOLE](https://openmole.org/all/10.1/Sensitivity.html) - OpenMOLE: a workflow system for distributed computing and parameter tuning

3. [Morris Method - an overview | ScienceDirect Topics](https://www.sciencedirect.com/topics/engineering/morris-method) - The main advantage of the Morris method is the low computational cost, requiring only about one mode...

4. [A comprehensive evaluation of various sensitivity analysis methods](https://www.sciencedirect.com/science/article/pii/S1364815213002338) - A rough rule of thumb about the sample size is that at least 10 × n sample points are needed to iden...

5. [Mastering Trading System Optimization: Avoid Common Pitfalls](https://enlightenedstocktrading.com/trading-system-optimization/) - Parameter Stability: Test your system with slight variations in parameter values. A stable system wi...

6. [Parameter Optimisation for Systematic Trading - Robot Wealth](https://robotwealth.com/parameter-optimisation-for-systematic-trading/) - Picking outlying points on the parameter space is not optimising for future robustness. Picking regi...

7. [The importance of robustness assessment in algorithmic FX trading ...](https://fxalgonews.com/the-importance-of-robustness-assessment-in-algorithmic-fx-trading-strategies/) - Picture 2 shows a parameter stability analysis of a very robust strategy made back in 2012: it's cle...

8. [Morris method — UQpy v4.2.0 documentation](https://uqpyproject.readthedocs.io/en/stable/sensitivity/morris.html) - The Morris method is a so-called one-at-a-time (OAT) screening method that is known to achieve a goo...

9. [Morris method](https://uqpyproject.readthedocs.io/en/latest/sensitivity/morris.html)

10. [Backtesting Robustness Index](https://www.priceactionlab.com/Blog/2013/02/backtesting-robustness-index/) - In this post I introduce the general form of the Backtesting Robustness Index (BRI) I have developed...

11. [Leave a Reply Cancel reply](https://www.forex.academy/sma-crossover-strategy-with-a-twist/)

12. [Types of robustness tests in SQX - StrategyQuant](https://strategyquant.com/doc/strategyquant/types-of-robustness-tests-in-sqx/) - In-Sample (IS) and Out-of-Sample (OOS) testing are essential concepts in the development, testing, a...

13. [How to Backtest Trading Strategies - TradersPost](https://blog.traderspost.io/article/how-to-backtest-trading-strategies) - Parameter Stability Assessment. Monitor how optimal parameters change across different time periods ...

14. [[PDF] Global Sensitivity Analysis. The Primer - Andrea Saltelli](https://www.andreasaltelli.eu/file/repository/A_Saltelli_Marco_Ratto_Terry_Andres_Francesca_Campolongo_Jessica_Cariboni_Debora_Gatelli_Michaela_Saisana_Stefano_Tarantola_Global_Sensitivity_Analysis_The_Primer_Wiley_Interscience_2008_.pdf) - This publication is designed to provide accurate and authoritative information in regard to the subj...

15. [Variance-based sensitivity analysis - Wikipedia](https://en.wikipedia.org/wiki/Variance-based_sensitivity_analysis)

16. [An efficient protocol for the global sensitivity analysis of stochastic ...](https://esajournals.onlinelibrary.wiley.com/doi/10.1002/ecs2.1238) - In this paper, we tested different sensitivity-analysis designs and emulators for a complex ecologic...

17. [Moving Average Crossover Strategies - QuantInsti Blog](https://blog.quantinsti.com/moving-average-trading-strategies/) - The triple moving average strategy involves plotting three different moving averages to generate buy...

18. [Moving Average Crossover Strategies: A Complete Guide](https://trendspider.com/learning-center/moving-average-crossover-strategies/) - Moving average crossovers use the interaction of two moving averages to reveal shifts in trend direc...

19. [Let's test every moving average crossover algorithm](https://www.alphaontheedge.com/p/lets-test-every-moving-average-crossover) - MAs are extremely helpful for smoothing high-noise time series into a discernible signal. They aim t...

20. [Challenging the Robustness of Optimal Portfolio Investment With Moving Average-based Strategies](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2774061) - The aim of this paper is to compare the performance of a theoretically optimal portfolio with that o...

21. [Designing Robust Trend-Following System - QuantPedia](https://quantpedia.com/designing-robust-trend-following-system/) - It is not easy to build a robust trend-following strategy that will withstand different difficult ma...

22. [How to Create a Robust Trend Following Strategy](https://quantra.quantinsti.com/glossary/How-to-Create-a-Robust-Trend-Following-Strategy) - This post will help you learn to create a robust trend following strategy to optimise your trading p...

23. [Designing Robust Trend-Following System | IBKR Quant](https://www.interactivebrokers.com/campus/ibkr-quant-news/designing-robust-trend-following-system/) - The method presents sensitivity analysis and robustness checks through various time horizons and sam...

24. [Momentum EMA Pullback Trading Strategy](https://www.fmz.com/lang/en/strategy/501772) - The core of this strategy is based on using the Exponential Moving Average (EMA) as a dynamic suppor...

25. [Elementary effects method - Wikipedia](https://en.wikipedia.org/wiki/Elementary_effects_method) - Published in 1991 by Max Morris the elementary effects (EE) method is one of the most used screening...

26. [Sensitivity analysis using Sobol' indices](https://openturns.github.io/openturns/latest/theory/reliability_sensitivity/sensitivity_sobol.html)

27. [Global sensitivity analysis workflows and rankings - ScienceDirect.com](https://www.sciencedirect.com/science/article/pii/S1364815226001039) - They also provide some approximate rules of thumb ... 10,000 parameter combinations were used, a sam...

28. [Morris — OTMORRIS 0.19 documentation - OpenTURNS](https://openturns.github.io/otmorris/master/user_manual/_generated/otmorris.Morris.html) - . The Morris method is a screening method, which is known to be very efficient in case of huge numbe...

29. [[PDF] new extension of morris method for sensitivity analysis of](https://publications.ibpsa.org/proceedings/bso/2016/papers/bso2016_1101.pdf) - Figure 2: Four examples for histogram plots out of the 10 independent runs of Morris Method with 10 ...

30. [[PDF] A Latin Hypercube Sampling Utility: with an application to an ...](https://jgea.org/ojs/index.php/jgea/article/download/180/226/1402) - This paper describes the use of a utility that creates a Latin Hypercube Sample (LHS). The LHS appro...

31. [LatinHypercube — SciPy v1.17.0 Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html) - In [9], a Latin Hypercube sampling (LHS) strategy was used to sample a parameter space to study the ...

32. [Progressive Latin Hypercube Sampling: An efficient approach for ...](https://www.sciencedirect.com/science/article/abs/pii/S1364815216305096) - We propose a new strategy, called Progressive Latin Hypercube Sampling (PLHS), which sequentially ge...

33. [Parameter Sensitivity Surface: Mapping Strategy Performance in 3D Hyperparameter Space](https://academy.dupoin.com/en/parameter-sensitivity-surface-38767-186428.html) - Master Parameter Sensitivity Surface analysis to visualize strategy performance across hyperparamete...

34. [How To Implement Robustness Testing In Trading Backtests For Better Results (5/7) | Quantreo](https://www.youtube.com/watch?v=FyMtD3MQ2rA) - Robustness testing is crucial for making your trading backtests more accurate. Visit my website for ...

35. [Testing the profitability of moving-average rules as a ...](https://www.sciencedirect.com/science/article/abs/pii/S0927538X12000327)

36. [A Robust Trend-Following Strategy: 13 Years of Consistent ... - MQL5](https://www.mql5.com/en/blogs/post/759933) - The strategy is idea-driven, rather than data-driven, and is adapted from a former trading strategy....

37. [[PDF] Robustness Measures and Optimization Strategies for Multi ... - kluedo](https://kluedo.ub.rptu.de/files/6577/Robustness_Measures_and_Optimization_Strategies_for_Multi-Objective_Robust_Design.pdf) - This work introduces new ideas for robustness measures in the context of multi- objective robust des...

