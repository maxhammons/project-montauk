# Project Montauk — Validation Philosophy

> Why we test, what we've built, and where we're going.

---

## The Goal

Project Montauk is a **long-only trend-following system for TECL** (3x leveraged tech ETF). The objective is simple: capture multi-month bull legs and exit before bear phases destroy capital. The system targets 1-3 trades per year with high hold times.

The **optimizer** (`/spike`) evolves strategy parameters across 16 families to find configs that time bull/bear regimes well. It runs overnight on GitHub Actions and maintains an all-time leaderboard of the top 20 configs.

## The Problem We're Solving

**Overfitting is the default outcome, not the exception.** With 918K+ configs tested on a single 17-year price path with only 5-8 bull/bear cycles, the optimizer will always find something that *looks* great in backtest. The research (13 papers/reports, synthesized in `SYNTHESIS.md`) is unambiguous:

- After 7 trials on 5-year data, you can find Sharpe > 1.0 by pure chance
- Backtest Sharpe has R² < 0.025 for predicting live performance (Quantopian, 888 algos)
- Median 73% Sharpe degradation from backtest to live trading (Suhonen et al., 215 strategies)
- With 8-12 tunable parameters and 15-50 trades, the trades-per-parameter ratio is far below the 10:1 research minimum

**If we can't distinguish signal from noise, nothing else matters.** A strategy that returns 72% CAGR in backtest but has a Regime Score at the 55th percentile of random configs is not a trading system — it's a lottery ticket.

## What We've Built

### Research-Aligned Fitness Function (`evolve.py`)

The optimizer's fitness function now targets what we actually care about:

```
fitness = regime_score × hhi_penalty × dd_penalty × complexity_penalty × bah_bonus
```

| Component | What It Does | Source |
|-----------|-------------|--------|
| `regime_score` (primary) | Bull capture + bear avoidance composite (0-1) | Montauk Charter: "capture bull legs, exit before bears" |
| `hhi_penalty` | Rejects strategies where one lucky cycle carries everything | compass...c551.md: cycle concentration |
| `dd_penalty` | Mild drawdown penalty (regime score already captures timing) | Standard risk control |
| `complexity_penalty` | Penalizes strategies with too many params relative to trades | Lopez de Prado: 10:1 trades-per-param minimum |
| `bah_bonus` | Small tiebreaker for beating buy-and-hold (capped at 1.5x) | Not primary — prevents regime-timing optimized configs that somehow lose to B&H |

**Hard gates** (fitness = 0 immediately):
- Trades/year > 3.0 (Charter: low churn)
- Trades-per-parameter ratio < 2.0 (catastrophically underdetermined)
- HHI > 0.35 (single cycle dominates)
- < 5 total trades

### Diversity-Driven Evolution (`evolve.py`)

The GA now actively prevents premature convergence:

| Mechanism | What It Does | Research Source |
|-----------|-------------|----------------|
| **Population diversity tracking** | Measures normalized parameter variance each generation | compass...e9e2.md: convergence diagnostics |
| **DGEA switching** | Low diversity → burst mutation (40%, ±4 steps). High diversity → exploitation (10%, ±1 step) | Ursem's Diversity-Guided EA |
| **5% random injection/gen** | 2 random individuals per generation (was 1 every 15 gens) | compass...e9e2.md: "inject 5-10% truly random" |
| **Mutation survival tracking** | Measures fraction of offspring retaining >90% parent fitness | compass...e9e2.md: free convergence proxy |

### Sprint 1 Validation Suite (`validation/sprint1.py`)

6 tests that run in ~11 seconds on the full leaderboard:

| Test | What It Catches | Research Source |
|------|----------------|----------------|
| **Deflated Regime Score** | Is this RS better than noise at N_eff=300? Monte Carlo calibrated null: Beta(17.2, 14.8), expected max 0.761 | compass...2650.md, deflated-sharpe-evolutionary.md |
| **Exit-Boundary Proximity** | Are exits clustered suspiciously near known bear starts? Enrichment ratio vs chance expectation | compass...c551.md: boundary memorization |
| **Delete-One-Cycle Jackknife** | Does removing any single cycle collapse the score? Scaled threshold: >2x average impact | compass...c551.md: cycle dependence |
| **HHI Concentration** | Separate bull/bear HHI + bull vs bear dominance ratio | compass...c551.md: cycle concentration |
| **Meta-Robustness** | Is the score stable across 28 different regime definitions? (7 thresholds × 4 durations) | compass...c551.md: regime detector sensitivity |
| **Component Dominance** | Does one side (bull capture vs bear avoidance) carry the composite? | Derived from HHI research |

### Slippage Modeling (`strategy_engine.py`)

5 bps per side (10 bps round-trip) applied to all backtests. Verified: -0.38% CAGR impact on a 55-trade strategy. Prevents inflated results from zero-friction assumptions.

### Hash-Index v2 (`evolve.py`)

Stores `{hash: {f: fitness, rs: regime_score}}` so formula changes don't require re-running all 918K+ backtests. Old v1 entries auto-migrate with rs=null and re-evaluate on encounter.

---

## What's Still Missing (Roadmap)

See `CHECKLIST.md` for detailed task tracking.

### Sprint 2: Robustness Tests
- **Morris Sensitivity Analysis** — which parameters actually matter? Fix the rest to reduce effective DOF
- **Composite Fragility Score (S_frag)** — broad plateau vs narrow spike measurement
- **Cross-Asset Validation** — do these strategies work on TQQQ, UPRO, QQQ? Single most powerful anti-overfitting test
- **Concentric Shell Analysis** — basin width from existing optimizer data

### Sprint 3: Pipeline + CI
- Wire validation into `spike.yml` so every GH Actions run auto-screens
- Full 4-stage fail-fast pipeline with composite tiering
- Bootstrap confidence intervals on Regime Score

### Sprint 4: Extended Testing
- Synthetic data extension (NDX back to 1985 — captures dot-com, 2008 GFC)
- PBO/CSCV on monthly returns
- Eigenvalue-based N_eff calibration (replace the 300 heuristic)

---

## Principles

1. **The research is the spec.** Every test, threshold, and formula traces to a specific paper or report in `/reference/research/reports/`.
2. **Multiplicative deflation, not additive.** A fragile but high-scoring strategy gets heavily discounted automatically.
3. **No severity ranking.** A wrong slippage assumption and a wrong fitness function are both bugs. Fix everything.
4. **Honesty over optimism.** If the null distribution says the expected max RS from noise is 0.76, and our best strategy scores 0.69, we don't rationalize — we acknowledge we haven't found signal yet.
5. **Optimize what you measure.** The fitness function targets regime timing because that's what the Charter says the system should do. Not CAGR, not Sharpe, not beating buy-and-hold.
