# Research Synthesis: Overfitting Detection for Project Montauk

> Distilled from 13 research files (~538KB): 6 Compass deep-research reports, 1 OpenAI deep-research report, 3 arxiv papers, 1 Elicit literature review + sources, 1 fragility scoring report, 1 deflated Sharpe report.

---

## 1. Consensus Findings (What All Sources Agree On)

### The Core Problem
With **918K unique configs tested** on a single price path (17 years TECL, 5-8 bull/bear cycles, 15-50 trades), the optimizer is operating in **extreme overfitting territory**. Every source confirms this independently:

- After just 7 trials on 5-year data, you can find a backtest with Sharpe > 1.0 by chance alone (Bailey & de Prado)
- Expected maximum Regime Score from pure noise at N_eff=2,000: **~0.78** on a 0-1 scale (Beta distribution EVT). Your top scores must clear this bar to have any signal.
- E[max] from 918K configs = 4.54 standard deviations above mean — a zero-edge strategy would still look impressive
- Quantopian study of 888 algorithms: backtest Sharpe has **R-squared < 0.025** for predicting out-of-sample performance
- Suhonen et al. (215 alt-beta strategies): median **73% Sharpe degradation** from backtest to live trading

### The Fundamental Constraint
**With 5-8 regime cycles and 8-12 parameters, no statistical method can certify genuine regime-timing skill.** The honest framing is "no evidence of overfitting" rather than "validated." The research converges on this uncomfortable truth:

- Detecting a medium effect (Cohen's d=0.5) at 80% power requires **16 observations per group**. With 5-8 cycles, minimum detectable effect is d=2.0
- Regime-level bootstrap is impossible with 5-8 observations
- 95% CIs on regime-conditional returns span +/-12 percentage points with N=6 cycles
- Trades-per-parameter ratio of 1.25-6.25 is **far below the 10:1 minimum**

### What Robust Strategies Look Like
All sources agree on the signature of genuine vs overfit strategies:

- **Robust**: Performance forms a **broad plateau** across parameter space. Changing a key parameter by 30-50% leaves performance "relatively stable"
- **Overfit**: Performance sits on an **isolated spike**. Moving any parameter by 10% collapses the score
- **Robust**: Works across related instruments (TQQQ, UPRO, QQQ)
- **Overfit**: Only works on the exact instrument it was optimized on
- **Robust**: Mutation survival rate is high (offspring retain >90% of parent fitness)
- **Overfit**: Narrow parameter band (1-2% of range) concentrates most benefit

---

## 2. Key Techniques Ranked by Feasibility

### Tier 1: Implement Immediately (zero/trivial compute, high value)

| Technique | Compute Cost | Power at Your N | Value-Add | Source |
|-----------|-------------|-----------------|-----------|--------|
| **Deflated Regime Score** (Beta-distribution selection bias) | <1 sec (arithmetic on existing stats) | Works on full 918K dataset | CRITICAL — establishes whether any score beats chance | deflated-sharpe-evolutionary.md, compass...2650.md |
| **Regime Boundary Perturbation** | ~20 backtests per strategy | Directly tests the #1 failure mode | HIGH — shift boundaries +/-k bars, if score collapses at k=2-5, it's overfit | compass...c551.md |
| **Concentric Shell Analysis** | 0 (uses existing 918K data) | Works at any N | HIGH — measures basin width vs spike. Fitness retention > 0.85 at d=0.15 = robust | compass...e9e2.md |
| **Mutation Survival Rate** | 0 (from existing GA data) | Works at any N | MEDIUM — best free convergence diagnostic | compass...e9e2.md |
| **Delete-One-Cycle Jackknife** | 5-8 backtests per strategy | N=5-8 is tight but usable | MEDIUM — if removing any single cycle drops score >30%, that cycle is carrying the strategy | compass...c551.md |
| **k-NN Fitness Variance** | 0 (from existing 918K data) | Works at any N | MEDIUM — low variance around top config = flat region = robust | compass...e9e2.md |

### Tier 2: Medium Effort (new backtests needed, fits in spike run)

| Technique | Compute Cost | Power at Your N | Value-Add | Source |
|-----------|-------------|-----------------|-----------|--------|
| **Morris Sensitivity Analysis** | 330 backtests/strategy (~25s each) | Good for 8-12 params | HIGH — ranks parameters by importance + interaction. Fix insensitive ones (ST_i < 0.05) to reduce effective param count from 12 to 6-8 | Fragility Scoring.md, compass...2650.md |
| **Stationary Bootstrap on Daily Returns** | 200 backtests/strategy (~15s each) | Usable at T=4,250 bars | MEDIUM — CIs on Regime Score. Use Student's t method, NOT percentile/BCa. Actual coverage ~87-93% | compass...a863.md |
| **Composite Fragility Score** | ~220 evals/strategy (Morris + LHS) | Good | HIGH — replaces the current +/-10% check. Formula: S_frag = S_rob * S_int where S_rob = 0.5*R_mean + 0.3*p_acc + 0.2*R_0.05 | Fragility Scoring.md |
| **Regime Detection Meta-Robustness** | 25 regime definitions x 20 strategies | Good | HIGH — 5x5 grid of bear thresholds (25-35%) x min durations (10-30 bars). Spearman rank > 0.90 = robust | compass...c551.md |
| **Cross-Asset Validation** | ~100 backtests (20 strategies x 5 instruments) | HIGHEST POWER of any method | CRITICAL — test identical params on TQQQ, UPRO, QQQ, XLK, SOXL. Score >= 0.70 on TECL but < 0.55 on others = almost certainly overfit | Every report mentions this |

### Tier 3: Bigger Lifts (significant implementation)

| Technique | Compute Cost | Power at Your N | Value-Add | Source |
|-----------|-------------|-----------------|-----------|--------|
| **4-Stage Fail-Fast Pipeline** | ~13,000 backtests for 20 strategies (~20 min) | Composite | HIGH — full validation funnel with hard gates and composite scoring | compass...2650.md |
| **PBO/CSCV on Monthly Returns** | Negligible (~0.02s) but needs monthly aggregation | Limited (S=8, ~25 months/partition) | MEDIUM — supplementary only. Use calibrated threshold ~0.20 (not 0.05). Pre-label regimes on full dataset | compass...0250.md |
| **Synthetic Data Extension** | One-time setup + backtests | HIGHEST — multiplies effective sample size | HIGH — calculate synthetic 3x returns from QQQ (back to 1999) or NDX (back to 1985). Captures dot-com crash + 2008 GFC | compass...2cdad.md |
| **N_eff Estimation** (eigenvalue/ONC) | ~6 min one-time (5,000-config subsample) | Calibrates all deflation methods | MEDIUM — needed for accurate DSR. N_eff is likely 150-5,000 (not 918K) | deflated-sharpe-evolutionary.md, compass...e9e2.md |
| **GAN-Based Synthetic Paths** | High (model training) | Would be highest if implementable | LOW priority — complex ML setup, arxiv paper shows promise but implementation burden is high | arxiv:2209.04895 |

---

## 3. Montauk-Specific Risks

### Risk 1: Regime Boundary Memorization (6 failure modes identified)
The Regime Score's focus on bull capture / bear avoidance makes it vulnerable to strategies that "memorize" the exact bars where regime transitions occur:

1. **Coincidental parameter alignment** — with 918K configs and 8-12 params, at least one config's exit signal will fire 1-3 bars before every known bear peak by pure chance
2. **Single-cycle dominance** — HHI > 0.25 on cycle contributions = one lucky cycle carrying the entire score
3. **Regime detector sensitivity** — regime boundaries depend on the 30% threshold and 20-bar minimum. Perturbing these may reshuffle all rankings
4. **Bull/bear weight gaming** — the 0.5/0.5 weighting can be exploited by strategies that nail bear avoidance while being mediocre on bull capture (or vice versa)
5. **Temporal clustering** — >60% of trades in a single 4-year window = concentration, not regime-responsiveness
6. **Goodhart's Law** — directly optimizing a metric that depends on 5-8 discrete events makes it a target, not a measure

**Detection**: Boundary perturbation test (+/-k bars) is the single most diagnostic test for this risk.

### Risk 2: The CAGR/Drawdown Coincidence
The #1 leaderboard strategy shows **72.1% CAGR with 71.7% max drawdown** (MAR = 1.007). The research suggests:

- A 72% max DD on a 3x leveraged ETF with 24 trades is not unusual — it may simply reflect being invested during a single large drawdown
- With only 24 trades and 14 parameters, the trades-per-parameter ratio is **1.7** — far below the 10:1 minimum
- The 83.3% win rate with 24 trades has a one-sided binomial p-value of ~0.10 (not significant at alpha=0.05)
- 22 of 24 exits are "S" (score-based) — the exit mechanism needs scrutiny for boundary memorization

### Risk 3: Strategy Family Concentration
The leaderboard is **RSI/regime-score dominated**:
- Top 4 of 20 slots: regime_score or regime_composite
- 7 of 20 use RSI as a core signal
- Only 4 distinct strategy families in top 10

This means the effective diversity of the leaderboard is low. If RSI-based regime detection is a false positive, most of the leaderboard falls simultaneously.

### Risk 4: Low Effective Independent Trials
The 918K configs are **not** 918K independent trials:
- GA mutation creates highly correlated parent-offspring pairs (rho ~0.95 → lineage of L mutations = ~L/39 effective trials)
- 20% leaderboard seeding further concentrates the search
- N_eff is estimated at **150-5,000** (not 918K)
- But even 150-5,000 effective trials on a dataset with only 5-8 regime transitions is severe multiple testing

---

## 4. What Won't Work (Don't Build These)

| Method | Why It Fails for Montauk | Source |
|--------|--------------------------|--------|
| **Trade-level CSCV/PBO** | 25 trades / S=8 partitions = 3 trades per subset = structurally invalid | compass...0250.md, compass...a863.md |
| **Walk-forward as statistical test** | 3-4 windows with 2-6 trades each has 15-50% power. No threshold calibration fixes this | compass...2cdad.md |
| **Bonferroni correction at 918K** | Requires p < 5.4e-8. Nothing passes. | compass...2650.md |
| **Standard DSR formula on Regime Score** | DSR assumes Sharpe ratio sampling distribution (Gaussian domain). Regime Score is bounded [0,1] — wrong domain of attraction (reversed Weibull Type III, not Gumbel) | compass...2650.md, deflated-sharpe.md |
| **Bootstrap CIs on trade-level returns** | At N=25 with block bootstrap, actual coverage is 75-88% for nominal 95%. Student's t interval is literally better | compass...a863.md |
| **Regime-level bootstrap** | Cannot form meaningful blocks from 5-8 observations | compass...a863.md |
| **Binomial win-rate test** | 26% power at p=0.60 with 25 trades. Need 155 trades for 80% power | compass...a863.md |
| **GT-Score** | Requires minimum 50 trades. System has 15-50, borderline at best | Elicit report |
| **Hamilton Markov-Switching model** | Introduces 6+ parameters, increasing overfitting risk rather than reducing it | compass...c551.md |

---

## 5. Open Questions (Gaps the Research Didn't Resolve)

1. **Optimal N_eff estimation method for this specific GA** — the research offers 4 methods (structural heuristic, eigenvalue, ONC, trade-sequence hashing) but doesn't say which is best for a trend-following GA with 15 strategy families
2. **Regime detector robustness thresholds** — how much should bear threshold / min duration be perturbed? No published guidance specific to trend-following systems
3. **Composite score weights** — the 4-stage pipeline proposes specific weights (S_frag^0.25 x S_wf^0.20 x ...) but acknowledges these are heuristic, not derived from theory
4. **Cross-asset parameter transfer** — should params be re-optimized on each instrument or held fixed? Fixed is a stronger test but may unfairly penalize instrument-specific dynamics
5. **Seeding bias quantification** — the 20% leaderboard seeding creates temporal correlation in the search. How much does this inflate apparent convergence? No published formula
6. **Evolutionary optimizer-specific overfitting** — no published studies specifically address GA optimization risks in trading (the Elicit review flagged this gap)
7. **Regime Score as optimization target** — no academic work validates or invalidates this specific composite metric. It was designed for this project and has no external benchmarking

---

## 6. Python Code Available in Reports (Ready to Adapt)

| Code | Location | What It Does |
|------|----------|-------------|
| `StrategyDiscoveryGovernor` class | deflated-sharpe-evolutionary.md, lines 2-74 | Deflated fitness scoring using EVT. Methods: `estimate_expected_max()`, `calculate_deflated_fitness()`, `process_leaderboard()` |
| `compute_pbo()` function | compass...0250.md, lines 11-243 | Full PBO/CSCV implementation with regime score support |
| `regime_score_factory()` | compass...0250.md, lines 344-373 | Regime score metric adapter for PBO pipeline |
| `assess_pbo_validity()` | compass...0250.md, lines 494-527 | Validates whether PBO results are statistically meaningful |
| R-hat computation | compass...e9e2.md, lines 112-120 | Gelman-Rubin convergence diagnostic across runs |
| Composite fragility formula | Fragility Scoring.md, sections 4.2-4.3 | S_frag = S_rob * S_int (no standalone code, but fully specified formulas) |
| Composite validation score | compass...2650.md, section 2 | S_frag^0.25 x S_wf^0.20 x S_sel^0.20 x S_reg^0.10 x S_trades^0.10 x S_boot^0.15 |
| 7-test pipeline spec | compass...c551.md, section 7 | DSR + permutation + regime perturbation + param stability + CSCV + bootstrap + concentration |

---

## 7. The Validation Stack (What to Actually Build)

Based on consensus across all 13 sources, ordered by bang-for-buck:

1. **Deflated Regime Score** — Beta-distribution selection bias correction. Gate: deflated score >= 0.95
2. **Parameter Sensitivity** — Morris Elementary Effects + composite fragility index. Gate: S_frag >= 0.40
3. **Regime Boundary Perturbation** — +/-k bars (k=1,2,5,10,20). Gate: score degrades < 15% at k=5
4. **Cross-Asset Validation** — identical params on TQQQ, UPRO, QQQ. Gate: profitable on >= 3/5 instruments
5. **Cycle Concentration Check** — HHI on per-cycle contributions. Gate: HHI < 0.25
6. **Concentric Shell Analysis** — basin width from existing data. Gate: fitness retention > 0.85 at d=0.15
7. **Synthetic Data Extension** — 3x leveraged returns from NDX/QQQ back to 1985/1999
8. **PBO/CSCV** (monthly, S=8, calibrated threshold). Supplementary only.

The first 6 items are achievable in a single implementation sprint. Items 7-8 are follow-ups.
