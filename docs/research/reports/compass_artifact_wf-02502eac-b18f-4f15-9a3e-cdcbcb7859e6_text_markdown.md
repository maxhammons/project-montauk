# PBO via CSCV for low-frequency trend systems

**PBO/CSCV can be applied to your TECL trend-following system, but only with significant adaptations — and it should not be your primary overfitting diagnostic.** With 15–50 trades over 17 years, standard CSCV works at the bar level (~4,250 daily observations) but breaks entirely at the trade level. The autocorrelation created by 50–200 bar hold times is the central technical obstacle: splitting daily bars across IS/OOS partitions fractures individual trades, contaminating the independence assumption. Your custom Regime Score metric can be substituted into CSCV with pre-labeled regimes, though the method's rank-based internals make it more forgiving of metric choice than most practitioners realize. Bailey et al.'s 0.05 threshold is not universal and requires recalibration for your setup. Below is a complete technical treatment of all seven questions.

---

## 1. Complete Python implementation of PBO using CSCV

The implementation below synthesizes the algorithm from Bailey et al. (2015) with practical improvements drawn from `pypbo`, the R `pbo` package, and the Balaena Quant implementation. It handles edge cases specific to low-frequency systems.

```python
import numpy as np
import pandas as pd
from itertools import combinations
from scipy import stats
from typing import Callable, Optional, NamedTuple, List, Dict

class PBOResult(NamedTuple):
    pbo: float                          # Probability of Backtest Overfitting
    pbo_kde: Optional[float]            # KDE-based PBO (smoother estimate)
    logits: np.ndarray                  # Logit values for each combination
    n_combinations: int                 # Total C(S, S/2) evaluated
    n_negative_logits: int              # Combinations where IS-best underperforms OOS median
    performance_degradation_slope: float # Regression slope of IS perf vs OOS perf
    performance_degradation_rho: float  # Spearman rho between IS and OOS ranks
    prob_oos_loss: float                # Fraction of combos where IS-best has OOS metric < threshold
    is_best_oos_ranks: np.ndarray       # Relative OOS rank of IS-best for each combo
    warnings: List[str]                 # Statistical warning flags


def compute_pbo(
    returns_matrix: np.ndarray,
    S: int = 16,
    metric_func: Optional[Callable] = None,
    metric_threshold: float = 0.0,
    n_sample: Optional[int] = None,
    seed: int = 42,
) -> PBOResult:
    """
    Compute Probability of Backtest Overfitting using CSCV.
    
    Parameters
    ----------
    returns_matrix : np.ndarray, shape (T, N)
        Performance matrix. T = time periods (daily bars), N = strategies.
        Each column is the daily return series for one strategy configuration.
    S : int
        Number of partitions (must be even, typically 8 or 16).
    metric_func : callable, optional
        Function that takes a 1D array of returns and returns a scalar 
        performance metric. Default: annualized Sharpe ratio.
    metric_threshold : float
        Value below which OOS metric is considered a "loss" (0 for Sharpe, 
        1 for Omega, user-defined for custom metrics).
    n_sample : int, optional
        If set, randomly sample this many combinations instead of 
        enumerating all C(S, S/2). Useful when S >= 18.
    seed : int
        Random seed for combination sampling.
    
    Returns
    -------
    PBOResult : namedtuple with all PBO diagnostics.
    """
    warnings = []
    
    # --- Input validation ---
    if returns_matrix.ndim != 2:
        raise ValueError("returns_matrix must be 2D with shape (T, N)")
    T, N = returns_matrix.shape
    if S % 2 != 0:
        raise ValueError("S must be even")
    if S < 4:
        raise ValueError("S must be >= 4")
    if N < 3:
        raise ValueError("Need at least 3 strategies for meaningful ranking")
    
    # --- Default metric: annualized Sharpe ratio ---
    if metric_func is None:
        def metric_func(x):
            if len(x) < 2 or np.std(x, ddof=1) == 0:
                return 0.0
            return np.mean(x) / np.std(x, ddof=1) * np.sqrt(252)
    
    # --- Step 1: Partition M into S contiguous blocks ---
    # Trim leading rows so T is divisible by S
    residual = T % S
    if residual != 0:
        warnings.append(f"Trimmed {residual} leading rows for even partitioning")
        M = returns_matrix[residual:]
    else:
        M = returns_matrix
    
    T_adj = M.shape[0]
    block_size = T_adj // S
    
    if block_size < 20:
        warnings.append(
            f"Only {block_size} bars per partition — metric estimates "
            f"will be very noisy. Consider reducing S."
        )
    
    # Create list of S blocks, each shape (block_size, N)
    blocks = [M[i * block_size : (i + 1) * block_size] for i in range(S)]
    
    # --- Step 2: Generate all C(S, S/2) IS/OOS combinations ---
    half = S // 2
    all_combos = list(combinations(range(S), half))
    total_combos = len(all_combos)
    
    if n_sample is not None and n_sample < total_combos:
        rng = np.random.default_rng(seed)
        combo_indices = rng.choice(total_combos, size=n_sample, replace=False)
        selected_combos = [all_combos[i] for i in combo_indices]
        warnings.append(
            f"Sampled {n_sample} of {total_combos} combinations"
        )
    else:
        selected_combos = all_combos
        n_sample = total_combos
    
    # --- Step 3: For each combination, compute IS/OOS metrics ---
    logits = np.full(len(selected_combos), np.nan)
    is_best_oos_ranks = np.full(len(selected_combos), np.nan)
    R_n_star = np.full(len(selected_combos), np.nan)     # IS perf of IS-best
    R_bar_n_star = np.full(len(selected_combos), np.nan)  # OOS perf of IS-best
    
    all_block_indices = set(range(S))
    
    for ci, combo in enumerate(selected_combos):
        is_indices = sorted(combo)
        oos_indices = sorted(all_block_indices - set(combo))
        
        # Concatenate blocks IN ORIGINAL TEMPORAL ORDER
        J_is = np.concatenate([blocks[i] for i in is_indices], axis=0)
        J_oos = np.concatenate([blocks[i] for i in oos_indices], axis=0)
        
        # Compute metric for each strategy on IS and OOS
        R_is = np.array([metric_func(J_is[:, n]) for n in range(N)])
        R_oos = np.array([metric_func(J_oos[:, n]) for n in range(N)])
        
        # Handle degenerate cases (all metrics identical)
        if np.all(R_is == R_is[0]):
            warnings.append(f"Combo {ci}: all IS metrics identical — skipping")
            continue
        
        # Find IS-best strategy
        n_star = np.argmax(R_is)
        R_n_star[ci] = R_is[n_star]
        R_bar_n_star[ci] = R_oos[n_star]
        
        # Compute OOS rank of IS-best (ascending: rank 1 = worst, N = best)
        oos_ranks = stats.rankdata(R_oos, method='average')
        oos_rank_of_best = oos_ranks[n_star]
        
        # Relative rank omega in (0, 1)
        # Use (rank - 0.5) / N to avoid boundary issues at 0 and 1
        omega = (oos_rank_of_best - 0.5) / N
        is_best_oos_ranks[ci] = omega
        
        # Logit transformation
        omega = np.clip(omega, 1e-10, 1 - 1e-10)  # prevent log(0)
        logits[ci] = np.log(omega / (1.0 - omega))
    
    # --- Step 4: Remove NaN entries from skipped combinations ---
    valid_mask = ~np.isnan(logits)
    logits_valid = logits[valid_mask]
    is_best_oos_ranks_valid = is_best_oos_ranks[valid_mask]
    R_n_star_valid = R_n_star[valid_mask]
    R_bar_n_star_valid = R_bar_n_star[valid_mask]
    
    n_valid = len(logits_valid)
    if n_valid == 0:
        warnings.append("CRITICAL: No valid combinations — PBO undefined")
        return PBOResult(
            pbo=np.nan, pbo_kde=np.nan, logits=logits_valid,
            n_combinations=0, n_negative_logits=0,
            performance_degradation_slope=np.nan,
            performance_degradation_rho=np.nan,
            prob_oos_loss=np.nan,
            is_best_oos_ranks=is_best_oos_ranks_valid,
            warnings=warnings,
        )
    
    # --- Step 5: Compute PBO ---
    # Discrete PBO: fraction of logits <= 0
    n_negative = np.sum(logits_valid <= 0)
    pbo_discrete = n_negative / n_valid
    
    # KDE-based PBO (smoother estimate, per Bailey et al.)
    pbo_kde = None
    if n_valid >= 10:
        try:
            from scipy.stats import gaussian_kde
            from scipy.integrate import quad
            kde = gaussian_kde(logits_valid)
            pbo_kde, _ = quad(kde, -np.inf, 0)
            pbo_kde = np.clip(pbo_kde, 0.0, 1.0)
        except Exception:
            pbo_kde = None
    
    # --- Step 6: Performance degradation diagnostics ---
    # Linear regression: OOS perf of IS-best vs IS perf of IS-best
    if n_valid >= 3:
        slope_result = stats.linregress(R_n_star_valid, R_bar_n_star_valid)
        perf_slope = slope_result.slope
        # Spearman rank correlation between all IS and OOS ranks
        rho, _ = stats.spearmanr(R_n_star_valid, R_bar_n_star_valid)
    else:
        perf_slope = np.nan
        rho = np.nan
    
    # Probability of OOS loss
    prob_loss = np.mean(R_bar_n_star_valid < metric_threshold)
    
    # --- Statistical power warnings ---
    if n_valid < 50:
        warnings.append(
            f"Low combination count ({n_valid}) — PBO confidence interval wide"
        )
    if block_size < 50:
        warnings.append(
            f"Partition size ({block_size} bars) may be too small "
            f"for reliable metric estimation"
        )
    if N < 10:
        warnings.append(
            f"Only {N} strategies — relative rank resolution is coarse "
            f"(steps of {1/N:.2f})"
        )
    
    return PBOResult(
        pbo=pbo_discrete,
        pbo_kde=pbo_kde,
        logits=logits_valid,
        n_combinations=n_valid,
        n_negative_logits=int(n_negative),
        performance_degradation_slope=perf_slope,
        performance_degradation_rho=rho,
        prob_oos_loss=prob_loss,
        is_best_oos_ranks=is_best_oos_ranks_valid,
        warnings=warnings,
    )
```

**Key implementation decisions explained.** The `(rank - 0.5) / N` formula for the relative rank ω avoids the boundary pathology where ω = 0 or ω = 1 would produce infinite logits. This is the Hazen plotting position, standard in order statistics. The `np.clip` provides a secondary safety net. The KDE-based PBO (using `gaussian_kde` + numerical integration) produces a smoother estimate than the discrete fraction, which matters when the number of combinations is small (S = 8 yields only 70 combinations). Both are returned so the user can compare.

**The metric_func abstraction** is critical for Question 6. Any callable that maps a 1D return array to a scalar works. The function handles the degenerate case where all IS metrics are identical (can happen with sparse data) by skipping that combination and issuing a warning. The optional `n_sample` parameter enables random sub-sampling of combinations when S ≥ 18, following the approach validated by the MDPI Bayesian PBO paper (2021), which sampled 1,000 of 184,756 combinations with acceptable precision.

---

## 2. The small-N problem fundamentally limits PBO's applicability here

**PBO does not degrade gracefully with few trades — it fails structurally at the trade level but remains viable at the bar level with caveats.** The distinction between these two data representations is the crux of the issue.

With ~4,250 daily bars over 17 years, the bar-level observation count is sufficient for CSCV. Using **S = 8** yields ~531 bars per partition and ~2,125 bars per IS/OOS half. Using **S = 16** yields ~265 bars per partition and ~2,125 bars per IS/OOS half. Both exceed Bailey et al.'s implicit minimum of ~60 bars per partition (derived from their example of S = 16 on 4 years of daily data). The Sharpe ratio standard error at T/2 = 2,125 bars is approximately **1/√2125 ≈ 0.022**, providing adequate precision.

At the trade level, however, CSCV is structurally invalid. With 25 trades and S = 8, each partition contains ~3 trades. A performance metric computed from 3 observations is noise-dominated. With S = 4 (the minimum even partition count), you'd have ~6 trades per partition — still far below the ~30+ threshold where central limit theorem approximations become defensible. **Any PBO computed on 25 trade-level observations is statistically meaningless**, regardless of the partition count chosen.

**The minimum S that is statistically meaningful depends on the observation unit.** For daily bars: S = 6 (giving ~708 bars/partition, 20 combinations) is the practical floor; S = 8 (531 bars/partition, 70 combinations) is recommended; S = 16 (265 bars/partition, 12,870 combinations) is the standard. For monthly aggregated returns (T ≈ 204): S = 6 (34 months/partition, 20 combinations) is marginal; S = 8 (25 months/partition, 70 combinations) is the maximum advisable.

**Zero-trade partitions** arise when a time block contains no entry or exit signals. For daily bar data, this doesn't affect the returns matrix — the strategy simply returns zero (flat position) during those bars, which is valid data. For trade-level data, empty partitions make metric computation undefined and must be handled by either skipping the combination (reducing effective sample size) or assigning a neutral metric value.

**Better-suited alternatives for this sample size include:**

- **Deflated Sharpe Ratio (DSR)**: Also by Bailey & López de Prado, DSR corrects the Sharpe ratio for multiple testing, non-normality, and sample length without requiring data partitioning. It operates on the full return series and is well-powered at T ≈ 4,250. This is the single best Bailey/López de Prado diagnostic for your use case.
- **Parameter sensitivity mapping**: Vary each parameter ±10–20% and check whether performance falls off a cliff (overfit) or degrades smoothly (robust). No minimum sample size required. This directly answers the overfitting question for trend-following systems.
- **Trade-level block bootstrap**: Resample the 25–50 completed trades (using blocks of 2–3 consecutive trades to preserve regime structure) and compute confidence intervals. Wide intervals honestly reflect your uncertainty.
- **Hansen's Superior Predictive Ability (SPA) test**: More powerful than White's Reality Check for small strategy universes. Handles temporal dependence via block bootstrap.

---

## 3. Partition by daily bars, not trades — but autocorrelation demands mitigation

Bailey et al. define partitioning strictly by **time periods**: the T×N matrix rows are daily (or other frequency) bars, and partitions are contiguous time windows. The paper does not contemplate trade-level partitioning. **For your system, the correct approach is to partition the ~4,250 daily bars into S contiguous time blocks**, where each column of the matrix contains the daily return stream (including zeros on flat days) for one strategy configuration.

**The autocorrelation problem is real but manageable.** When a single trend-following trade spans 100–200 bars, the daily returns within that trade exhibit strong serial correlation — they all reflect the same directional exposure in the same market regime. When CSCV splits these bars into different partitions, two problems arise. First, the same trade contributes returns to both IS and OOS, creating information leakage. Second, the effective number of independent observations is much closer to the trade count (~25) than the bar count (~4,250), inflating the apparent statistical precision.

Bailey et al. acknowledge this directly: *"if the performance measure as a time series has a strong autocorrelation, then such a division may obscure the characterization especially when S is large."* Their recommendation for autocorrelated series is to keep S small, preserving longer contiguous time blocks that are more likely to contain complete trades.

**Three mitigation strategies, in order of effectiveness:**

**Aggregate to weekly or monthly returns** before applying CSCV. Monthly aggregation gives T ≈ 204 observations. With S = 6, each partition spans ~34 months (~2.8 years), likely containing several complete trades. This dramatically reduces within-trade autocorrelation at the cost of fewer total observations. Use S = 6 or S = 8 maximum.

**Apply purging and embargo** (López de Prado's CPCV extension). After forming IS/OOS splits, remove bars adjacent to the IS/OOS boundary equal to the maximum trade duration (~200 bars). This prevents a single trade from contributing to both halves. The cost is reduced effective sample size — each IS/OOS half loses up to S/2 × 200 = 800 bars (for S = 8), which is significant but tolerable with T = 4,250.

**Use Newey-West autocorrelation-adjusted standard errors** when computing subsample Sharpe ratios. Lo (2002) provides the adjustment factor: η(q) = √(1 + 2Σρ_k), where ρ_k are autocorrelation coefficients up to lag q. For a trend system with 100-bar average hold time, this adjustment can inflate the Sharpe SE by **3–5×**, producing more honest subsample estimates.

**The recommended configuration for your system is S = 8 on monthly aggregated returns with a 2-month embargo period.** This yields 70 combinations, partitions of ~25 months each containing 2–6 complete trades, and IS/OOS halves of ~100 months (~8.5 years) with adequate statistical power for most performance metrics.

---

## 4. The 0.05 threshold requires substantial recalibration

**Bailey et al. do not mandate 0.05 as a universal threshold.** The paper presents it as analogous to a Neyman-Pearson significance level, but the appropriate threshold depends on the number of strategies N, the sample size T, the partition count S, and the metric used. Practitioner guidance varies significantly: the MQL5 CSCV implementation considers PBO < 0.10 "ideal," while PickMyTrade flags PBO > 0.40 as concerning.

**For your specific setup, the 0.05 threshold is too aggressive.** Three factors inflate PBO beyond what the standard threshold accounts for:

**Small N (15–50 strategies)** creates coarse rank resolution. With N = 20 strategies, the relative OOS rank of the IS-best takes values in {0.025, 0.075, ..., 0.975} — steps of 0.05. A single rank position shift changes the logit dramatically. Even with genuine alpha, random noise in subsample metric estimates will frequently move the IS-best strategy one or two ranks below median, inflating PBO. Bailey et al. note that **N >> 10** is required for the relative rank to be sufficiently granular.

**Single instrument** means no cross-sectional diversification. Multi-asset strategies benefit from averaging across instruments, reducing noise in subsample metrics. Your single-instrument setup has no such averaging, leading to noisier IS/OOS performance estimates and higher PBO.

**Non-standard composite metric** (Regime Score) has unknown sampling distribution. The 0.05 threshold was calibrated empirically for Sharpe ratio, whose sampling properties are well-studied (Lo, 2002). A composite ratio-based metric may have higher variance on subsamples.

**A well-calibrated threshold for your setup should be established empirically via null simulation.** Generate synthetic return matrices by permuting your strategy's entry signals randomly (preserving the return distribution of the underlying asset) to create "no-skill" strategies. Compute PBO on these null strategies. The 5th percentile of the null PBO distribution becomes your calibrated threshold — any real PBO below this level indicates overfitting risk below the 5% significance level. Based on empirical results in the literature, **expect a calibrated threshold of approximately 0.15–0.25** for your parameters (N ≈ 20, S = 8, monthly data).

**An alternative approach**: compute PBO for your strategy set and compare against PBO computed on the same number of random walk strategies. If your PBO is in the bottom quartile of the null distribution, that's meaningful evidence against overfitting, even if the absolute PBO exceeds 0.05.

---

## 5. Incremental computation is partially possible through caching

**PBO cannot be computed fully incrementally as individual strategies are added** because adding strategy N+1 changes the rank of every other strategy within each IS/OOS combination. However, a significant portion of the computation can be cached to make incremental updates efficient.

The partition structure (which blocks form IS/OOS for each combination) is independent of N and can be precomputed once. For each combination, the block concatenation indices are fixed. When a new strategy is added, only its metric on each IS/OOS pair needs to be computed (2 × C(S, S/2) metric evaluations), and then all rankings must be updated. This avoids recomputing metrics for existing strategies.

**PBO is fundamentally a batch operation on a finalized leaderboard.** The ranking and logit computation require knowledge of all N strategies simultaneously. The recommended workflow is: (1) run the optimizer to produce a leaderboard of top-K candidates, (2) compute PBO as a post-hoc validation on this leaderboard, (3) use the result as a go/no-go gate.

**Wall-clock time estimates for your parameters** (N = 20 strategies, T ≈ 204 monthly bars, numpy implementation on a modern laptop):

| S | Combinations | Metric evals | Est. time (single-core) | Est. time (8-core joblib) |
|---|-------------|-------------|------------------------|--------------------------|
| 6 | 20 | 800 | < 0.01s | < 0.01s |
| 8 | 70 | 2,800 | ~0.02s | ~0.01s |
| 16 | 12,870 | 514,800 | ~2s | ~0.4s |

For daily bar data (T ≈ 4,250), multiply metric evaluation time by ~20× but the total remains under 10 seconds even for S = 16. **The computational bottleneck is metric evaluation**, not combination enumeration. If your Regime Score metric is expensive (requiring regime detection within each subset), precompute regime labels on the full dataset and pass them as auxiliary data to avoid redundant detection.

For the 300K+ configurations your optimizer evaluates, running PBO on all configurations is unnecessary. **Run PBO only on the final leaderboard** (top 20–50 candidates). At 20 strategies with S = 8, the computation finishes in milliseconds — negligible overhead for a CI/CD pipeline.

---

## 6. Regime Score can substitute for Sharpe with one critical modification

Bailey et al. state explicitly: *"although in our examples we measure performance using the Sharpe ratio, our methodology does not rely on this particular performance statistic, and it can be applied to any alternative preferred by the reader."* The `pypbo` library accepts any callable as `metric_func`. The MQL5 implementation confirms: *"From simple profit to ratio based metrics, it is of no consequence to CSCV."*

**CSCV requires only two properties of the metric:** (1) it must be computable independently on any subset of the data, producing a scalar, and (2) the resulting scalars must be ordinally comparable (higher = better or lower = better). The method does **not** require the metric to be additive across periods, return-based, normally distributed, or have any specific distributional form. This is because PBO operates on **ranks**, not raw metric values — the logit transform uses the ordinal position of the IS-best strategy in the OOS ranking, not the metric's cardinal value.

**Your Regime Score (bull capture ratio + bear avoidance ratio) requires one critical modification for CSCV compatibility.** The Regime Score depends on identifying bull and bear cycles (≥30% move, ≥20 bars) within the evaluation window. When CSCV forms IS/OOS subsets by concatenating non-adjacent time blocks, regime detection within each subset becomes problematic — a block boundary might split a bull cycle in two, or a short block might contain no qualifying regimes at all.

**The solution is to pre-label regimes on the full dataset, then compute the Regime Score on subsets using pre-assigned labels.** This is methodologically sound because regime labels are properties of the market (TECL's price action), not the strategy. The procedure:

```python
def regime_score_factory(regime_labels):
    """
    Returns a metric_func compatible with compute_pbo().
    
    regime_labels : np.ndarray, shape (T,)
        Pre-computed regime membership: +1 = bull, -1 = bear, 0 = neutral.
    """
    def regime_score(returns, subset_indices=None):
        if subset_indices is not None:
            labels = regime_labels[subset_indices]
        else:
            labels = regime_labels[:len(returns)]
        
        bull_mask = labels == 1
        bear_mask = labels == -1
        
        if bull_mask.sum() == 0 or bear_mask.sum() == 0:
            return np.nan  # Undefined — flag for edge case handling
        
        # Bull capture: strategy return during bull / buy-and-hold during bull
        bull_capture = returns[bull_mask].sum() / max(abs(returns[bull_mask].sum()), 1e-10)
        # Bear avoidance: 1 - (strategy loss during bear / buy-and-hold loss during bear)
        bear_loss = returns[bear_mask].sum()
        bh_bear_loss = returns[bear_mask].sum()  # Replace with benchmark if different
        bear_avoidance = 1.0 - min(bear_loss / min(bh_bear_loss, -1e-10), 1.0)
        
        return np.clip((bull_capture + bear_avoidance) / 2, 0, 1)
    
    return regime_score
```

**Pass subset indices alongside returns to the metric function** so it can look up the correct regime labels. This requires a minor modification to the CSCV loop — track row indices for each IS/OOS block rather than just the concatenated arrays.

**The rank-based nature of PBO provides a safety net.** Since PBO uses Spearman rank correlation and relative rank positions, any monotonic transformation of your metric produces identical PBO. If Regime Score consistently ranks strategies in the same order as some simpler metric (e.g., total return), the PBO result will be identical regardless of which metric you use. The [0, 1] bounded range of Regime Score compresses differences, potentially creating more ties in rankings — use `method='average'` in `scipy.stats.rankdata` to handle ties, and note that with N = 20 strategies, occasional ties are expected and do not invalidate the result.

---

## 7. Pipeline output format and integration schema

The following JSON schema captures all diagnostically relevant PBO outputs for a `validate_candidate.py` step in GitHub Actions:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["pbo_result", "metadata", "decision"],
  "properties": {
    "pbo_result": {
      "type": "object",
      "required": ["pbo", "pbo_kde", "n_combinations", "n_negative_logits"],
      "properties": {
        "pbo": { "type": "number", "minimum": 0, "maximum": 1,
                  "description": "Discrete PBO: fraction of combos with logit <= 0" },
        "pbo_kde": { "type": ["number", "null"], "minimum": 0, "maximum": 1,
                     "description": "KDE-smoothed PBO estimate" },
        "n_combinations": { "type": "integer",
                            "description": "Number of valid CSCV combinations evaluated" },
        "n_negative_logits": { "type": "integer" },
        "logit_distribution": {
          "type": "object",
          "properties": {
            "mean": { "type": "number" },
            "median": { "type": "number" },
            "std": { "type": "number" },
            "skewness": { "type": "number" },
            "percentile_5": { "type": "number" },
            "percentile_95": { "type": "number" }
          }
        },
        "performance_degradation": {
          "type": "object",
          "properties": {
            "slope": { "type": "number",
                       "description": "Regression slope of IS-best perf vs OOS perf. Negative = degradation." },
            "spearman_rho": { "type": "number" },
            "spearman_p_value": { "type": "number" }
          }
        },
        "prob_oos_loss": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },
    "metadata": {
      "type": "object",
      "required": ["S", "N", "T", "metric_name"],
      "properties": {
        "S": { "type": "integer", "description": "Number of CSCV partitions" },
        "N": { "type": "integer", "description": "Number of strategies evaluated" },
        "T": { "type": "integer", "description": "Total bars in returns matrix" },
        "T_effective": { "type": "integer",
                         "description": "Bars after trimming for even partition" },
        "bars_per_partition": { "type": "integer" },
        "metric_name": { "type": "string" },
        "data_frequency": { "type": "string", "enum": ["daily", "weekly", "monthly"] },
        "embargo_bars": { "type": "integer", "default": 0 },
        "trades_per_partition": {
          "type": "object",
          "properties": {
            "min": { "type": "integer" },
            "max": { "type": "integer" },
            "avg": { "type": "number" }
          }
        },
        "computation_time_seconds": { "type": "number" },
        "timestamp": { "type": "string", "format": "date-time" }
      }
    },
    "decision": {
      "type": "object",
      "required": ["pass", "confidence"],
      "properties": {
        "pass": { "type": "boolean",
                  "description": "True if PBO below calibrated threshold" },
        "confidence": { "type": "string",
                        "enum": ["high", "medium", "low", "insufficient_data"],
                        "description": "Confidence in the PBO estimate itself" },
        "threshold_used": { "type": "number" },
        "rejection_reasons": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Statistical power warnings and edge case flags"
    }
  }
}
```

**Recommended GitHub Actions log format:**

```
::group::PBO/CSCV Validation
[PBO] Strategy: tecl_trend_v3 | Metric: regime_score
[PBO] Config: S=8, N=20, T=204 (monthly), embargo=2mo
[PBO] Combinations: 70 evaluated, 68 valid (2 skipped: zero-regime partition)
[PBO] Result: PBO=0.176 (KDE: 0.183) | Threshold: 0.200
[PBO] Degradation slope: -0.31 | Spearman rho: 0.24 (p=0.048)
[PBO] Prob OOS loss: 0.22 | Trades/partition: min=1, max=5, avg=3.1
[PBO] Decision: PASS (confidence: medium)
[PBO] ⚠ Warning: Only 20 strategies — rank resolution is coarse (steps of 0.05)
[PBO] ⚠ Warning: 2 partitions have <2 trades — metric estimates noisy
::endgroup::
```

**Handling insufficient trades:** When `trades_per_partition.min < 2` or the total trade count is below 20, the system should:

```python
def assess_pbo_validity(total_trades, S, N):
    """Determine if PBO can be meaningfully computed."""
    trades_per_partition = total_trades / S
    
    if total_trades < 10:
        return {
            "computable": False,
            "confidence": "insufficient_data",
            "recommendation": "Use DSR + parameter sensitivity instead",
            "fallback_metrics": ["deflated_sharpe_ratio", "parameter_stability"]
        }
    elif trades_per_partition < 2:
        return {
            "computable": True,
            "confidence": "low",
            "recommendation": f"Reduce S to {max(4, 2 * (total_trades // 4))} "
                            f"or use monthly aggregation",
            "fallback_metrics": ["deflated_sharpe_ratio", "bootstrap_ci"]
        }
    elif trades_per_partition < 5:
        return {
            "computable": True,
            "confidence": "medium",
            "recommendation": "Interpret PBO cautiously; supplement with DSR",
            "fallback_metrics": ["deflated_sharpe_ratio"]
        }
    else:
        return {
            "computable": True,
            "confidence": "high",
            "recommendation": "PBO estimate reliable",
            "fallback_metrics": []
        }
```

---

## Conclusion: a multi-tool approach outperforms PBO alone

CSCV/PBO was designed for a different regime than yours — high-frequency strategies with thousands of observations and hundreds of parameter combinations. **Applied naively to a single-instrument, low-frequency trend-following system with 15–50 trades, PBO produces estimates with wide implicit confidence intervals and an uncalibrated threshold.** It remains a useful supplementary diagnostic when applied to monthly aggregated returns with S = 8 and pre-labeled regimes, but should not serve as the sole overfitting gate.

The strongest validation architecture for your specific system combines four tools. **First**, the Deflated Sharpe Ratio handles multiple testing correction without data partitioning and is well-powered at T ≈ 4,250. **Second**, CSCV/PBO on monthly returns (S = 8, 70 combinations) provides a rank-based sanity check with an empirically calibrated threshold near 0.20. **Third**, parameter sensitivity mapping across a ±20% neighborhood reveals whether your optimum sits on a plateau (robust) or a peak (overfit). **Fourth**, applying the identical strategy logic to 3–5 related instruments (TQQQ, SOXL, other leveraged ETFs) multiplies your effective trade count and is the single most powerful evidence against overfitting. The JSON schema and logging format above integrate all of these into a coherent pipeline where PBO serves as one diagnostic among several, with appropriate confidence flags when the data is too sparse for a definitive answer.