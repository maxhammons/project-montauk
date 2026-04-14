# Avoiding Overfitting and “Magic-Number” Curve-Fitting in Trading Strategy Backtests

## Executive summary

Overfitting in trading research is not a minor technical flaw; it is a **systematic failure mode** that arises naturally when researchers (or optimizers) search across many strategy variants, parameters, assets, and time windows until something “works.” Bailey, Borwein, López de Prado, and Zhu show that **high in-sample performance is easy to obtain after trying many alternative configurations**, and that the **probability of backtest overfitting rises with the number of configurations tried**—especially when the number of trials is not reported. citeturn11view2turn11view0

Large, sophisticated trading organizations do not “know” a strategy is good in the sense of certainty. Instead, they build **institutional processes** that (a) reduce the opportunity to fool yourself, (b) quantify the probability that the apparent performance is a false discovery, and (c) require the strategy to survive multiple independent challenges: out-of-sample validation, robustness tests, transaction-cost realism, capacity constraints, and ongoing monitoring.

A useful mental model is: **a strategy is a hypothesis test performed under extreme multiple-testing pressure** (across variants, markets, regimes, and time). Tools like the **Deflated Sharpe Ratio** (selection-bias and non-normality adjustment), **Probabilistic Sharpe Ratio / minimum track record length**, **White’s Reality Check**, **Hansen’s SPA test**, and **Probability of Backtest Overfitting (PBO) via CSCV** explicitly address this reality. citeturn11view0turn11view1turn11view4turn11view5turn40view0turn40view1

Finally, “big shops do it well” largely because they treat model risk like other risks: they enforce *effective challenge* (independent, competent critique), demand documented conceptual soundness, and then continuously monitor performance and assumptions after deployment. This framing is explicit in the Federal Reserve/OCC model risk management guidance (SR 11-7). citeturn22view0turn22view1turn22view2

## Conceptual foundations of overfitting and curve-fitting in trading

Overfitting (in the backtesting sense) occurs when a strategy’s rules or parameters have been tuned to idiosyncrasies of the historical sample rather than to a repeatable structure. Bailey et al. describe overfitting as a situation where a model “targets particular observations rather than a general structure,” borrowed from machine learning, and emphasize the need to compare **in-sample (IS)** vs **out-of-sample (OOS)** behavior. citeturn10view0

A critical finance-specific driver is that modern research can cheaply test millions of variations. Bailey & López de Prado describe how “backtest optimizers” search parameter combinations to maximize historical performance, which leads to “backtest overfitting,” and they explicitly connect the resulting performance inflation to **selection bias under multiple testing** (reporting only winners). citeturn11view0turn10view0

“Magic-number” curve-fitting is a practical, trader-facing version of the same problem: a parameter (e.g., lookback length, threshold, stop distance) is chosen because it maximizes backtest performance—even if small changes to that number break the strategy. The “magic” is usually a sign of **high parameter sensitivity** and **low robustness**, not a deep market constant. This problem becomes worse when:
- the strategy has many degrees of freedom (multiple indicators, filters, regime switches, discretionary “exceptions”),
- the researcher repeatedly revises rules after viewing results (implicit multiple testing),
- the backtest metric is optimized without correcting for multiple trials (selection bias), and
- the evaluation metric itself is noisy or inflated (e.g., Sharpe measured under violated assumptions). citeturn11view2turn11view0turn12view0

Sharpe ratio inflation is a concrete example of finance’s “measurement risk.” Lo derives the distribution of the Sharpe ratio under several assumptions and shows that **monthly Sharpe ratios cannot generally be annualized by multiplying by √12** except under special conditions; with serial correlation, annualized Sharpe can be **materially overstated** and rankings can change. citeturn12view0

A second institutional insight: large firms rarely evaluate a strategy in isolation. Bailey, López de Prado, and del Pozo argue that firms often use thresholds (e.g., Sharpe and track record length) to approve strategies, but emphasize that there is **no fixed Sharpe threshold that should always be required**; approval must jointly consider a candidate’s Sharpe and its **correlation to the existing set of strategies**, because the portfolio is what ultimately matters. citeturn6view0turn6view1

## Backtest biases and data pitfalls that create false performance

A robust anti-overfitting program starts by eliminating biases that artificially inflate backtest results. Many “great backtests” fail not because the signal is fake, but because the simulator quietly assumed unrealistic information or frictionless execution.

Look-ahead bias arises when the backtest uses information that would not have been known at the trade decision time (future prices, future fundamentals, delayed corporate actions, or labels that overlap the future). López de Prado flags “cross-validation leakage” as a core evaluation pitfall and recommends **purging and embargoing** to prevent leakage when labels overlap in time. citeturn19view1turn14search7

Survivorship bias occurs when the tested universe excludes assets that disappeared (delistings, bankruptcies, acquisitions), leading to overstated returns. In equity datasets, correctly handling **delisting returns** is essential: CRSP-oriented documentation defines delisting return as the return after delisting, computed using value after delisting vs last trading-date price; if the stock becomes worthless and cannot be traded after delisting, that value can be zero. citeturn27view1  
A practical preprocessing guide from the SAFE Research Datacenter emphasizes that delisting returns must be accounted for to measure investors’ returns; it combines CRSP holding period returns with delisting returns and (when dlret is missing) applies Shumway-style imputations (example: -30% NYSE/Amex and -55% Nasdaq for certain delisting codes). citeturn27view0  
Even if you do not use these exact imputations, the meta-lesson is that **missing delisting returns is a known failure mode** that must be explicitly handled, not ignored. citeturn27view0turn27view1

Data-snooping (data-mining) bias arises when the same dataset is reused many times for inference or model selection. White defines data snooping precisely in these terms (data reused more than once), motivating procedures (Reality Check) that test whether the best model found in a search truly has predictive superiority over a benchmark after accounting for the search itself. citeturn11view4turn11view5  
Sullivan, Timmermann, and White apply White’s Reality Check bootstrap methodology to technical trading rules and explicitly frame their goal as **quantifying data-snooping bias and adjusting** in the context of the full universe of rules from which the winners were selected. citeturn31view0

Transaction costs and slippage are not “details”: if you ignore them, you are often optimizing nonsense. Institutional-style transaction cost analysis distinguishes explicit costs (commissions, fees) from implicit costs (market impact, opportunity cost). Keim and Madhavan summarize that implicit trading costs are economically significant and that costs vary systematically with trade difficulty and order placement strategy. citeturn29view0  
Market impact is one key driver of implicit costs. Almgren & Chriss model optimal execution as a trade-off between expected cost and risk, explicitly constructing an efficient frontier of execution strategies—underscoring that execution is a decision problem, not a constant spread. citeturn29view1  
Almgren et al. (using institutional execution data) emphasize that market impact is essential and empirically calibrate impact models used for trade scheduling and cost estimation. citeturn29view2

Selection bias is the “publication bias” of systematic trading: teams tend to report (and remember) the winners. Bailey & López de Prado explicitly call this out: performance inflation extends beyond backtesting because researchers and managers tend to report only positive outcomes; failing to control for the number of trials leads to over-optimistic expectations. citeturn11view0  
Harvey, Liu, and Zhu make the same point in the factor-discovery context: given extensive data mining, conventional significance cutoffs are too low, and they propose much higher hurdles (e.g., *t* > 3.0 for new factors) under multiple testing. citeturn36view0

## Advanced methods that detect overfitting and quantify evidence

This section focuses on *tools that force you to confront how fragile your backtest is*.

### Comparative table of major anti-overfitting tests

| Method | What it detects | Strengths | Weaknesses / gotchas | When to use |
|---|---|---|---|---|
| Walk-forward optimization (WFO) | Time instability; parameter drift; regime brittleness | Intuitive; respects time order; matches “train then trade” workflow | High variance: results depend on one historical path; can still be overfit via repeated design iterations | When the strategy is inherently time-adaptive and you want a realistic rolling deployment simulation citeturn19view0turn38view0 |
| Nested cross-validation | Optimism from tuning on the same folds used to estimate error | Standard “honest” model-selection framework (inner loop tunes, outer loop estimates) | Must align folds with time dependence; computationally heavy | When you tune hyperparameters (especially ML) and need less biased error estimates citeturn24view1 |
| Purged K-fold CV + embargo | Look-ahead/leakage from overlapping labels/horizons | Directly targets leakage in financial labels | Needs correct label-interval logic; embargo choice matters | Event-driven ML; overlapping holding periods; anytime labels use future windows citeturn14search7turn19view1 |
| Combinatorial Purged Cross-Validation (CPCV) | Overreliance on one CV path; unstable OOS estimates | Produces a distribution of OOS outcomes, not a single number; reduces path dependence | Computationally expensive; still requires careful leakage control | When you need a robust distribution of OOS Sharpe / drawdowns for decision-making citeturn19view0turn19view1 |
| Bootstrap / stationary bootstrap (time-series resampling) | Sampling uncertainty of returns and statistics under dependence | Produces confidence intervals and stress distributions; handles weak dependence (stationary bootstrap) | Resampling assumptions matter (block length, stationarity); can mislead in regime shifts | For uncertainty bands on Sharpe, CAGR, drawdown; for Monte Carlo stress tests of sequences citeturn24view0turn34view0 |
| Monte Carlo resampling of parameters / randomized backtests | Parameter fragility; “knife-edge” optima | Directly answers “does it work in a neighborhood?” | Must avoid biased search (don’t re-optimize on the same noisy metric repeatedly) | For “magic-number” detection; for robustness zones and parameter heatmaps citeturn11view2turn19view0 |
| Deflated Sharpe Ratio (DSR) | Sharpe inflation from multiple testing + non-normality | Explicitly adjusts for selection bias and non-normal returns | Requires assumptions/inputs about the trial set and distribution moments | Must-have when many strategies/params were tested before choosing the winner citeturn11view0 |
| Probabilistic Sharpe Ratio (PSR) + Min track record length (MinTRL) | Estimation error in Sharpe; required track record to evidence skill | Converts “Sharpe” into a probability vs a benchmark; connects to track record length | Still requires assumptions (stationarity/ergodicity, moments) | When deciding whether the observed Sharpe is statistically persuasive given track record length citeturn11view1turn12view0 |
| White’s Reality Check | Data-snooping across a tested universe | Controls for search across many models/rules; bootstrap-based p-values | Can be sensitive to choice/set of alternatives, dependence structure | When you searched across many rule parameterizations and need search-adjusted inference citeturn11view4turn31view0 |
| Hansen’s SPA test | Data-snooping with better power properties than RC | More powerful; less sensitive to poor/irrelevant alternatives via studentization | Still needs careful definition of model set and loss function | When RC is too conservative or your model set contains many weak alternatives citeturn11view5 |
| Probability of Backtest Overfitting (PBO) via CSCV | Likelihood that “best IS” underperforms OOS due to overfit | Designed for backtest overfitting; model-free, nonparametric framework | Requires implementing CSCV correctly; interpretation requires care | When you ran systematic search and want a direct “overfit probability” measure citeturn40view0turn40view1 |

### Key institutional takeaway: walk-forward alone is not enough

Walk-forward is widely used, but López de Prado argues that walk-forward backtests can exhibit **high variance** because many decisions are based on a small subset of the dataset, and selecting the maximum estimated Sharpe under high variance leads to false discoveries. citeturn19view0turn19view1  
This is exactly why institutions increasingly prefer *distributional* evaluations (CPCV distributions, bootstrap distributions, PBO estimates), not single-path point estimates. citeturn19view0turn40view0

### Pseudocode outlines requested by the user

**Walk-forward optimization (time-ordered, no peeking):**
```text
inputs:
  data (prices/returns + features), strategy family S(θ), cost model C(.)
  train_window_length, test_window_length
  objective metric M (e.g., net Sharpe, or utility with drawdown penalty)
  parameter search procedure (grid/random/Bayesian), constraints on θ

procedure:
  split timeline into sequential (train, test) windows:
    [t0..t1]=train, [t1..t2]=test, then roll forward by test_window_length

  for each window k:
    IS_data = data[t_k_start : t_k_train_end]
    OOS_data = data[t_k_train_end : t_k_test_end]

    # inner optimization (must use ONLY IS_data)
    θ*_k = argmax_θ  M( backtest(S(θ), IS_data, costs=C) )

    # lock parameters, evaluate ONLY on OOS_data
    trades_k, pnl_k = backtest(S(θ*_k), OOS_data, costs=C)

    record metrics_k = {M_k, drawdown_k, turnover_k, cost_break_even_k, θ*_k}

  aggregate:
    concatenate OOS pnl across k into a single "stitched" equity curve
    compute overall OOS metrics + distribution across windows
    analyze parameter stability: θ*_k over time, and sensitivity bands
```
This aligns with the general “optimize on past, trade in future” concept of walk-forward used in practice and described in trading-system development workflows. citeturn38view0turn19view0

**Monte Carlo robustness via resampling returns + parameter perturbation (two-layer stress):**
```text
inputs:
  base strategy S(θ0), parameter neighborhood Θ around θ0
  base trade list or base return series (net of baseline costs)
  resampling method R (e.g., stationary bootstrap for dependent returns)
  number of sims B, parameter draws P per sim

procedure:
  for b in 1..B:
    # resample a pseudo-history that preserves dependence approximately
    r_b = R(base_returns or trade PnL, method="stationary_bootstrap")

    for p in 1..P:
      θ_bp ~ sample(Θ)   # random perturbation or random search draw
      pnl_bp = simulate_strategy_on_resampled_path(S(θ_bp), r_b, costs perturbed)
      record risk stats: Sharpe_bp, maxDD_bp, Calmar_bp, turnover_bp, etc.

  outputs:
    distribution of metrics across (b,p)
    "fragility score": how quickly metrics degrade away from θ0
    probability of ruin / probability Sharpe < 0 / probability maxDD exceeds limit
    break-even cost distribution (bps) under cost shocks
```
For dependent data, using time-series bootstrap variants like the **stationary bootstrap** (random block lengths) is one academically grounded approach. citeturn24view0turn34view0

## How large trading houses reduce curve-fit risk in strategy discovery

There is no single “secret test.” What distinguishes strong organizations is that they implement **a pipeline with guardrails** that make it hard to curve-fit without being caught.

A useful analogy is the Federal Reserve/OCC model risk guidance: model risk should be managed via *effective challenge*—critical analysis by objective, informed parties with the incentives, competence, and influence to force changes when needed. citeturn22view0turn22view3  
Even though SR 11-7 is banking supervision guidance, its model lifecycle (development → validation → governance → monitoring) is essentially the same lifecycle a sophisticated systematic trading firm needs. citeturn22view1turn22view2

Below are the highest-leverage practices (asset class and timeframe unspecified, so these are framed generically).

**Start from a thesis, not from the optimizer.** López de Prado explicitly labels “research through backtesting” as a pitfall; the recommended alternative in his “ML funds fail” framework is to shift toward feature importance and more scientific workflows. citeturn19view1turn18view0

**Parameter parsimony and constrained flexibility.** Bailey et al. emphasize that performance inflation increases as more configurations are tried, and that without reporting the number of trials investors cannot assess overfitting risk. The institutional implication is: *limit degrees of freedom* (parameters, filters, conditional logic) and treat “unbounded tweakability” as model risk. citeturn11view2turn11view0

**Separate research and validation roles (“effective challenge”).** In strong shops, the person who built the strategy is usually not the person who signs off on it. SR 11-7 explicitly recommends separation and effective challenge, and also explains that validation includes conceptual soundness, ongoing monitoring, and outcomes analysis (including backtesting). citeturn22view0turn22view1turn22view2

**Portfolio-first approval criteria (diversification matters).** Bailey–López de Prado–del Pozo describe how many firms split allocation into “approval” and “optimization” stages, and warn that selecting by a fixed Sharpe threshold ignores correlation effects; they argue there is no fixed Sharpe threshold for approval and that strategy fit vs existing strategies matters. citeturn6view0turn6view1

**Multiple markets / multiple regimes / multiple granularities.** Pardo’s systematic strategy development framing explicitly includes multimarket, multiperiod testing concepts and walk-forward analysis as a step in the process. citeturn38view0  
A modern academic walk-forward study (2026) shows that walk-forward results can be highly dependent on training/testing window choices—reinforcing the need for robustness across choices, not a single “best” configuration. citeturn7search0turn37view1

**Ensembles and meta-strategies rather than single brittle rules.** López de Prado’s framework of common ML failures explicitly points toward meta-strategy thinking and techniques like sequential bootstrapping / uniqueness weighting (to address non-IID samples), and CPCV (to reduce walk-forward fragility). citeturn19view1turn19view0

**Randomized parameter search (vs exhaustive grid search).** The goal is not speed; it is to avoid the illusion that the optimum is meaningful when small changes break performance. Randomized search also supports your parameter sensitivity analysis and helps estimate how likely you were to find a good result by chance (feeds into DSR / PBO framing). citeturn11view0turn40view1

## What to report and what to interrogate

Metrics are not just “scoreboards.” In robust research, each metric is a diagnostic for a specific failure mode: leverage to outliers, hidden tail risk, turnover explosion, cost fragility, or dependency on a small number of trades.

### Core metrics and the failure modes they catch

Annualized Sharpe is common but fragile. Lo shows it is subject to estimation error and that annualization by √12 fails outside special cases; serial correlation can materially overstate Sharpe and reorder rankings. citeturn12view0  
Because of these issues, institutions increasingly report Sharpe alongside statistical uncertainty measures and selection-bias adjustments: PSR/MinTRL and DSR. citeturn11view1turn11view0

Drawdown metrics (max drawdown, time under water, Calmar/MAR) are non-negotiable because many strategies “Sharpe well” but die operationally when tail events hit; the key is to treat drawdown not as a single number but as a distribution across OOS paths and stress tests (CPCV/bootstraps). citeturn19view0turn22view2

Turnover and capacity metrics are where many academic backtests die in production. Keim & Madhavan emphasize implicit trading costs (impact and opportunity costs) and that costs vary by trade difficulty and strategy. citeturn29view0  
Execution cost models (Almgren–Chriss) and empirical impact estimation (Almgren et al.) exist because capacity is strategy-dependent and must be modeled, not assumed. citeturn29view1turn29view2

### Concrete thresholds and “red-flag heuristics” grounded in the literature

Because asset class/timeframe are unspecified, universal cutoffs (e.g., “Sharpe must be X”) are unreliable. Institutions instead prefer **probability-based** or **search-adjusted** thresholds:

- **Multiple-testing significance:** Harvey–Liu–Zhu argue that with extensive data mining a new factor should clear a much higher hurdle, proposing thresholds such as **t-statistic > 3.0** (rather than ~2.0) under their multiple-testing framing. citeturn36view0  
  Practical translation: if your strategy’s alpha (or mean return) depends on weak t-stats, assume it is likely a false positive unless supported by strong economics and multiple independent validations.

- **PBO rejection heuristic:** In the PBO framework, Bailey et al. note a “customary approach” would reject models with estimated **PBO > 0.05** (high likelihood of overfitting). citeturn40view1  
  Practical translation: if your strategy only looks good because the “best IS” choice underperforms OOS frequently, you do not have a strategy—you have a selection process that manufactures winners.

- **Search-adjusted Sharpe:** DSR exists precisely because the “best Sharpe” among many trials is inflated. DSR corrects for **selection bias under multiple testing and non-normal returns**, helping separate empirical findings from statistical flukes. citeturn11view0  
  Practical translation: if you cannot explain (and approximate) your number of trials, you cannot credibly interpret your headline Sharpe.

- **Leakage controls as go/no-go:** López de Prado flags “cross-validation leakage” and recommends purging/embargoing; if you cannot confidently rule out leakage, you should treat the backtest result as invalid. citeturn19view1turn14search7

### Parameter sensitivity table and example “heatmap”

The goal of parameter-sensitivity analysis is to detect the “magic number” phenomenon. A robust strategy typically has a **broad plateau** of acceptable performance, not a single sharp spike.

Below is an **illustrative** sensitivity grid (synthetic numbers) for a strategy with two parameters: lookback length (rows) and entry threshold (columns). You would typically fill this with *OOS* Sharpe (or stitched walk-forward Sharpe) net of costs.

| Lookback \ Threshold | 1.0 | 1.5 | 2.0 | 2.5 |
|---|---:|---:|---:|---:|
| 20 | 0.4 | 0.6 | **1.2** | 0.3 |
| 40 | 0.7 | 0.9 | **1.1** | 0.8 |
| 60 | 0.6 | 0.8 | 0.9 | 0.7 |
| 80 | 0.5 | 0.6 | 0.7 | 0.6 |

Interpretation heuristics:
- A **single isolated maximum** (e.g., only (20,2.0) works) is a classic curve-fit signature.
- A **stable ridge / plateau** (many neighbors close in value) indicates robustness.
- Recompute this under multiple cost assumptions; if the plateau disappears under +X bps, the strategy is cost-fragile. This matters because implicit costs are economically significant and impact-driven. citeturn29view0turn29view1turn29view2

**Suggested Mermaid-style sketch for a sensitivity “heatmap” workflow (not a literal heatmap renderer):**
```mermaid
flowchart LR
A[Define parameter grid Θ] --> B[For each θ in Θ]
B --> C[Run OOS evaluation: WFO/CPCV]
C --> D[Compute metric: net Sharpe / Calmar / maxDD]
D --> E[Store in matrix M[lookback, threshold]]
E --> F[Visualize: heatmap + contour lines]
F --> G[Identify plateau vs spike]
G --> H[Stress: costs, slippage, delay, regime splits]
```

## Validation workflow and “is this good enough to trade?” checklist

A strong workflow is staged and adversarial: each stage is designed to kill weak strategies early, before they consume execution and political capital.

### Institutional validation lifecycle

SR 11-7 describes an effective validation framework with three core elements: **conceptual soundness**, **ongoing monitoring**, and **outcomes analysis (including back-testing)**. citeturn22view1turn22view2  
It also emphasizes that model risk cannot be eliminated and requires limits, monitoring, and revisions—an operational truth for live trading. citeturn22view0turn22view2

### A rigorous end-to-end workflow

**Data and simulation integrity (precondition gates)**  
Ensure point-in-time correctness, corporate actions correctness, and survivorship correctness. For equities, explicitly incorporate delisting returns; CRSP-oriented documentation defines delisting return mechanics, and applied preprocessing guides combine holding-period returns with delisting returns to measure investor returns correctly. citeturn27view1turn27view0

**Partitioning and OOS discipline (design the experiment before you see results)**  
Use a locked “final holdout” that is not touched until the end, and keep a research log of how many variants you tried (this matters for DSR/PBO interpretation). citeturn11view0turn11view2

**Primary evaluation: walk-forward + distributional OOS (CPCV where appropriate)**  
- Use WFO to simulate realistic rolling deployment. citeturn38view0turn19view0  
- Recognize WFO’s high variance; augment with CPCV to get a distribution of Sharpe ratios rather than a single (possibly overfit) estimate. citeturn19view0turn19view1

**Anti-leakage ML validation (if predictive labels overlap)**  
Apply purged/embargoed CV to remove label overlap and reduce leakage risk. citeturn14search7turn19view1

**False-discovery controls**  
- Compute Reality Check / SPA-style p-values if you searched across many strategy variants. citeturn11view4turn11view5turn31view0  
- Compute DSR (selection-bias adjustment) and PSR/MinTRL (estimation uncertainty). citeturn11view0turn11view1turn12view0  
- Compute PBO via CSCV; reject if the estimated overfitting probability is unacceptably high (e.g., > 0.05 per the customary Neyman–Pearson framing discussed by Bailey et al.). citeturn40view0turn40view1

**Monte Carlo + bootstrap stress tests**  
Use bootstrap methods (including stationary bootstrap for dependent time series) to produce confidence intervals on Sharpe/drawdown and to test sequence robustness. citeturn24view0turn34view0

**Transaction cost and capacity testing**  
Model both explicit and implicit costs. Institutional evidence shows implicit costs are economically significant. citeturn29view0  
Use execution/impact models (Almgren–Chriss; empirical impact estimation) to evaluate whether expected alpha survives realistic impact as size increases. citeturn29view1turn29view2

**Paper trading and monitoring plan**  
Deploy with a paper book or minimal risk, then measure live slippage vs model, fill rates, latency effects, and drift. SR 11-7 explicitly frames ongoing monitoring, benchmarking, and investigation of discrepancies as core validation elements, and emphasizes predefined thresholds and early warning metrics for performance deterioration. citeturn22view2turn22view3

### Walk-forward procedure diagram with timeline

```mermaid
flowchart LR
A[Define windows: train L, test T] --> B[Window k: Train on past]
B --> C[Optimize θ* on IS only]
C --> D[Lock θ*; Trade/Simulate on OOS window]
D --> E[Record OOS metrics + θ*]
E --> F[Roll forward by T and repeat]
F --> G[Stitch all OOS windows -> final OOS equity curve]
G --> H[Analyze stability: θ* over time, costs, regimes]
```

### Actionable “go-live” checklist

The checklist below is designed to be used as an approval gate in a research-to-production pipeline (the exact pass/fail thresholds depend on asset class and turnover; where possible, thresholds are probability-based per the cited frameworks).

- **Backtest integrity**
  - No obvious look-ahead/leakage; if labels overlap, purged/embargoed CV or equivalent leakage controls are implemented. citeturn14search7turn19view1  
  - Survivorship handling is explicit; for equities, delisting returns are included or defensibly approximated (and sensitivity-tested). citeturn27view1turn27view0  
  - Execution assumptions are realistic (bid/ask, slippage, delay, partial fills) and documented.

- **Robustness across time**
  - WFO results are acceptable and not dominated by one window; if window choice materially changes performance, treat as a warning (recent academic evidence finds WFO performance can be highly sensitive to window size choices). citeturn37view1turn19view0  
  - CPCV/bootstrapped distributions show acceptable downside probabilities (not just good point estimates). citeturn19view0turn24view0

- **False discovery controls**
  - You can state (even approximately) how many variants were tried; DSR or comparable adjustment is reported. citeturn11view0turn11view2  
  - Data-snooping-adjusted inference (Reality Check / SPA) is used when appropriate. citeturn11view4turn11view5turn31view0  
  - PBO is estimated; if **PBO > 0.05**, treat as high overfitting likelihood per the customary rejection framing discussed by Bailey et al. citeturn40view1  
  - Statistical significance hurdles reflect multiple testing pressure (e.g., t-stat > 3.0 in the Harvey–Liu–Zhu multiple-testing framing, when relevant). citeturn36view0

- **Costs and capacity**
  - Strategy edge survives plausible cost regimes; cost break-even is reported and stress-tested.
  - Impact/capacity analysis exists; cost sensitivity reflects that implicit costs are economically significant and impact-driven. citeturn29view0turn29view1turn29view2

- **Portfolio fit**
  - Correlation to existing strategies is evaluated; strategy is assessed by incremental portfolio contribution, not only standalone Sharpe. citeturn6view0turn6view1

- **Governance and monitoring**
  - Independent review (“effective challenge”) occurs before deployment; assumptions and limitations are documented. citeturn22view0turn22view1  
  - Monitoring plan exists: early warning metrics, benchmarking vs expectations, investigation triggers, and a kill-switch policy for model deterioration. citeturn22view2turn22view3

### Recommended prioritized sources

Academic / primary foundations (high priority):
- Lo (2002), *The Statistics of Sharpe Ratios* (CFA/FAJ) — Sharpe estimation error, serial correlation, correct annualization. citeturn12view0  
- Bailey et al. (2014), *Pseudo-Mathematics and Financial Charlatanism* — backtest overfitting as an endemic risk. citeturn11view2turn10view0  
- Bailey & López de Prado (2014), *Deflated Sharpe Ratio* — corrects for selection bias and non-normality. citeturn11view0turn8view0  
- Bailey & López de Prado (2012), *Sharpe Ratio Efficient Frontier* — Probabilistic Sharpe Ratio and minimum track record length. citeturn11view1turn8view1  
- Bailey et al. (2015/2017), *Probability of Backtest Overfitting* — PBO and CSCV, including a practical rejection heuristic. citeturn40view0turn40view1  
- White (2000), *A Reality Check for Data Snooping*; Hansen (2005), *SPA test* — search-adjusted inference methods. citeturn11view4turn11view5  
- Sullivan, Timmermann & White (1999) — practical application of the Reality Check with bootstrap methodology. citeturn31view0  
- Harvey, Liu & Zhu (2016) — multiple-testing framing and higher significance thresholds under data mining pressure. citeturn36view0  
- Efron (1979) and Politis & Romano (1994) — bootstrap and time-series resampling foundations. citeturn34view0turn24view0

Institutional practice anchors:
- Federal Reserve/OCC SR 11-7 (Model Risk Management) — effective challenge, validation elements, ongoing monitoring, governance. citeturn22view0turn22view1turn22view2  
- Keim & Madhavan (1998) — empirical evidence that implicit trading costs are economically significant and systematic. citeturn29view0  
- Almgren & Chriss (2000) and Almgren et al. (2005) — execution/impact modeling for realistic cost and capacity testing. citeturn29view1turn29view2  
- CRSP-oriented documentation on delisting returns and preprocessing notes on combining delisting + holding period returns. citeturn27view1turn27view0

Industry best-practice synthesis (useful, but treat as secondary):
- López de Prado (2018), *The 10 Reasons Most Machine Learning Funds Fail* — practical pitfalls: cross-validation leakage, WFO variance, CPCV, deflated Sharpe framing. citeturn19view0turn19view1