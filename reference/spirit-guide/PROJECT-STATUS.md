# Project Montauk — Status Brief

> As of 2026-04-07

---

## 1. Optimizer State

### Run History
8 spike runs across 5 days (April 3-7, 2026). The most recent run (April 7) ran 5 hours, evaluated 314K configs in 57K generations.

### Hash Index
**918,606 unique configurations** tested and deduplicated. Approximately 40% of evals are cache hits (skipped), meaning ~60% of each run explores new parameter space.

### Leaderboard (20 slots filled)

| Rank | Strategy | Fitness | CAGR | Max DD | MAR | Trades | Win Rate | Converged |
|------|----------|---------|------|--------|-----|--------|----------|-----------|
| 1 | regime_score | 28.27 | 72.1% | 71.7% | 1.007 | 24 | 83.3% | No |
| 2 | regime_score | 12.24 | 64.0% | 71.7% | 0.893 | 14 | 85.7% | No |
| 3 | regime_composite | 2.92 | 50.6% | 66.7% | 0.758 | 14 | 85.7% | Yes |
| 4 | regime_score | 2.79 | 50.5% | 71.7% | 0.705 | 16 | 93.8% | No |
| 5 | rsi_vol_regime | 2.60 | 49.4% | 63.6% | 0.776 | 25 | 92.0% | Yes |
| 6 | regime_composite | 1.66 | 46.3% | 75.1% | 0.616 | 12 | 100% | Yes |
| 7 | rsi_regime | 1.43 | 44.4% | 65.8% | 0.675 | 10 | 100% | Yes |
| 8 | breakout | 0.60 | 37.2% | 63.2% | 0.588 | 27 | 59.3% | Yes |
| 9-10 | breakout (x2) | 0.59 | 37.5% | 71.9% | 0.521 | 15 | 60.0% | Yes |
| 11 | stoch_drawdown | 0.36 | 32.3% | 46.6% | 0.694 | 35 | 85.7% | Yes |
| 12 | montauk_821 | 0.35 | 32.7% | 59.0% | 0.554 | 23 | 65.2% | Yes |
| 13 | rsi_regime_trail | 0.34 | 32.7% | 64.5% | 0.507 | 20 | 70.0% | Yes |
| 14-16 | montauk_821 (x2), dual_momentum | 0.25-0.32 | 30-32% | 45-59% | 0.5-0.7 | 23-43 | 58-61% | Yes |
| 17 | vol_regime | 0.24 | 29.2% | 47.8% | 0.610 | 25 | 56.0% | Yes |
| 18 | ichimoku_trend | 0.12 | 24.7% | 29.6% | 0.834 | 62 | 45.2% | Yes |
| 19 | mean_revert_channel | 0.12 | 23.9% | 44.5% | 0.537 | 42 | 81.0% | Yes |
| 20 | golden_cross | 0.10 | 24.3% | 75.1% | 0.323 | 10 | 70.0% | Yes |

### Key Observations
- **Top 3 are all regime-score family** with a massive fitness gap (28.3 → 2.9)
- **16 of 20 strategies are converged** — the optimizer is hitting diminishing returns
- **Only 3 active strategies** (regime_score variants still improving)
- The #1 strategy jumped from fitness 12.2 → 28.3 in the most recent run — still actively improving
- **Trade counts range from 10 to 62** — median ~23

---

## 2. Strategy Diversity

### Family Distribution on Leaderboard

| Family | Slots | Converged | Notes |
|--------|-------|-----------|-------|
| regime_score | 3 | 0/3 | Dominant, still improving |
| regime_composite | 2 | 2/2 | Plateaued |
| breakout | 3 | 3/3 | Plateaued |
| montauk_821 | 3 | 3/3 | Baseline strategy, plateaued |
| rsi_vol_regime | 1 | 1/1 | Plateaued |
| rsi_regime | 1 | 1/1 | Plateaued (manually unconverged once) |
| rsi_regime_trail | 1 | 1/1 | Plateaued |
| stoch_drawdown_recovery | 1 | 1/1 | Plateaued |
| dual_momentum | 1 | 1/1 | Plateaued |
| vol_regime | 1 | 1/1 | Plateaued |
| ichimoku_trend | 1 | 1/1 | Plateaued |
| mean_revert_channel | 1 | 1/1 | Plateaued |
| golden_cross | 1 | 1/1 | Plateaued, simplest strategy (3 params) |

**Concentration risk**: 7 of top 10 slots use RSI as a core signal component. If RSI-based entry timing is a false positive on TECL, most of the leaderboard collapses simultaneously.

### Pending Strategies (Not Yet Added)
5 new oscillator-based strategies were designed on April 6 but **not yet added to `scripts/strategies.py`**:
1. `flow_exhaustion_reclaim` — MFI + OBV + volatility
2. `stoch_drawdown_recovery` — Stochastic crossover + drawdown awareness (partial overlap with existing)
3. `williams_midline_reclaim` — Williams %R + Donchian
4. `cci_flow_reacceleration` — CCI mean-deviation + volume
5. `accumulation_breakout` — Volume-confirmed Donchian breakout

These would inject non-RSI diversity into the search.

---

## 3. Validation Gap Analysis

| Capability | Research Says | Current Code | Gap |
|------------|-------------|--------------|-----|
| **Selection bias correction** | CRITICAL. Deflated fitness with Beta-distribution EVT | None | Full gap. No deflation of any kind. Raw fitness = raw overfit risk |
| **Parameter sensitivity** | +/-30-50%, Morris screening, composite fragility score | +/-10% OAT in validate_candidate.py | Partial. Too narrow, no interaction detection, no composite score |
| **Regime boundary robustness** | Shift boundaries +/-k bars, reject if score collapses | None | Full gap |
| **Walk-forward** | Underpowered at 3-4 windows (15-50% power). WFE >= 50% threshold | 4 fixed windows, 15% degradation threshold | Threshold too strict (should be 50%). Power acknowledged as low |
| **Cross-asset validation** | Single most powerful anti-overfitting test | None | Full gap. All testing on TECL only |
| **Bootstrap CIs** | Student's t block bootstrap on daily returns (T=4,250) | Archive only (not in active pipeline) | Full gap in active code |
| **PBO/CSCV** | Supplementary, monthly bars, S=8, threshold ~0.20 | None | Full gap |
| **Convergence diagnostics** | Basin width, mutation survival, R-hat across runs | 3-run-without-improvement flag | Minimal. Detects stagnation but not convergence quality |
| **Cycle concentration** | HHI on per-cycle contributions, delete-one-cycle jackknife | None | Full gap |
| **N_eff estimation** | Required for all deflation methods. 4 estimation approaches | None | Full gap. Currently using raw config count |
| **Synthetic data extension** | NDX/QQQ back to 1985/1999 to capture dot-com + 2008 | None | Full gap. 17-year single-path testing only |
| **Parameter count penalty** | Fix insensitive params (Sobol ST_i < 0.05) to reduce effective DOF | None | Full gap. All params treated equally |

### Summary
- **3 of 12 capabilities partially implemented** (parameter sensitivity, walk-forward, basic convergence detection)
- **9 of 12 are full gaps** including the most critical one (selection bias correction)
- The current pipeline can detect obviously bad strategies but **cannot distinguish lucky-good from genuinely-good**

---

## 4. The CAGR/Drawdown Problem

The #1 strategy claims 72.1% CAGR with 71.7% max drawdown. Research context:

### Red Flags
- **14 parameters, 24 trades** → trades-per-parameter ratio = 1.7 (minimum should be 10:1)
- **22 of 24 exits are "S" (score-based)** → single exit mechanism dominance; one overfit exit rule carries everything
- **0 cooldown bars** → aggressive re-entry could be exploiting regime boundary proximity
- **83.3% win rate with 24 trades**: binomial p ≈ 0.10 (not significant at 0.05)
- **71.7% max drawdown**: identical to #2 and #4 strategies (different configs, same drawdown → likely the same bear period)
- **Fitness jumped from 12.2 → 28.3 in one run** → the GA found a narrow parameter improvement, not a structural breakthrough

### What Would Increase Confidence
- Deflated fitness score >= 0.95 after Beta-distribution correction
- Boundary perturbation: score holds within 15% when shifting regime boundaries +/-5 bars
- Cross-asset: profitable on >= 3/5 related instruments
- Parameter sensitivity: S_frag >= 0.40 with +/-30% perturbation
- Cycle jackknife: no single cycle removal drops score > 30%

Until these tests are run, the 72% CAGR claim should be treated as **unvalidated**.

---

## 5. Infrastructure Health

### What's Working Well
- **Dedup system**: 918K+ hashes, 30-40% cache hit rate, zero wasted compute on repeats
- **Convergence detection**: auto-flags plateaued strategies, prevents resource waste
- **GitHub Actions CI/CD**: fully automated 5-hour runs, auto-commit results
- **Report generation**: clean markdown with metrics tables, trade breakdowns, exit reasons
- **Strategy library**: 15 families with parameter registries, clean separation from engine

### What Needs Attention
- **No validation pipeline** in the promotion path (strategy goes from GA → leaderboard with no quality gate)
- **Fitness function is raw regime score** with no deflation, no penalty for complexity
- **Walk-forward thresholds are mis-calibrated** (15% degradation threshold per research should be 50%)
- **5 pending strategies** not yet integrated (strategy diversity is bottlenecked)
- **Active strategy folder is empty** — production code lives in TradingView only, no source-of-truth in repo
