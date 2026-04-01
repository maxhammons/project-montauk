# /spike — Continuous Strategy Optimization

Run a multi-phase optimization loop on the Montauk trading strategy. This process proposes improvements, backtests them, validates against overfitting, and produces a report with the best candidates as ready-to-paste Pine Script.

**This is a READ-ONLY process** — it never modifies files in `src/strategy/active/` or `src/indicator/active/`. All output goes to `remote/`.

## Prerequisites

Before starting, install dependencies if needed:
```bash
cd /home/user/project-montauk && pip3 install pandas numpy yfinance requests 2>/dev/null
```

## Phase 0 — Establish Baseline

Run the baseline backtest first. This is what every candidate is measured against.

```bash
cd /home/user/project-montauk && python3 scripts/run_optimization.py baseline
```

Record the baseline MAR ratio, CAGR, max drawdown, and trade count. These are the numbers to beat.

## Phase 1 — Parameter Sweeps (find the low-hanging fruit)

Sweep each key parameter one at a time. Run these sweeps and look for improvements:

```bash
# EMA lengths
python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param med_ema_len --min 15 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param long_ema_len --min 200 --max 800 --step 50

# Trend filter
python3 scripts/run_optimization.py sweep --param trend_ema_len --min 30 --max 120 --step 10
python3 scripts/run_optimization.py sweep --param slope_lookback --min 3 --max 20 --step 2

# ATR exit
python3 scripts/run_optimization.py sweep --param atr_period --min 10 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param atr_multiplier --min 1.5 --max 5.0 --step 0.5

# Quick EMA exit
python3 scripts/run_optimization.py sweep --param quick_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param quick_lookback_bars --min 2 --max 10 --step 1
python3 scripts/run_optimization.py sweep --param quick_delta_pct_thresh --min -15.0 --max -3.0 --step 1.0

# Sideways filter
python3 scripts/run_optimization.py sweep --param range_len --min 20 --max 100 --step 10
python3 scripts/run_optimization.py sweep --param max_range_pct --min 10 --max 50 --step 5

# Cooldown
python3 scripts/run_optimization.py sweep --param sell_cooldown_bars --min 0 --max 10 --step 1
```

After each sweep, note which values produced the best MAR ratio. Don't combine winners yet — just collect them.

## Phase 2 — Toggle Experiments

Test enabling/disabling optional filters:

```bash
# Enable TEMA slope filter
python3 scripts/run_optimization.py test --params '{"enable_slope_filter": true}'

# Enable price-below-TEMA filter
python3 scripts/run_optimization.py test --params '{"enable_below_filter": true}'

# Both TEMA filters
python3 scripts/run_optimization.py test --params '{"enable_slope_filter": true, "enable_below_filter": true}'

# Enable trailing stop at various levels
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 20}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 25}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 30}'

# Enable TEMA slope exit
python3 scripts/run_optimization.py test --params '{"enable_tema_exit": true, "tema_exit_lookback": 5}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit": true, "tema_exit_lookback": 10}'

# Disable sideways filter (it suppresses exits too)
python3 scripts/run_optimization.py test --params '{"enable_sideways_filter": false}'

# Disable sell confirmation (fix known EMA cross bug)
python3 scripts/run_optimization.py test --params '{"enable_sell_confirm": false}'
```

## Phase 3 — Combine Winners

Take the top 3-5 individual improvements from Phase 1-2 and combine them. Test the combined configuration:

```bash
# Example: combine best short_ema_len + best atr_multiplier + TEMA filter
python3 scripts/run_optimization.py test --params '{"short_ema_len": <best>, "atr_multiplier": <best>, "enable_slope_filter": true}'
```

If the combination is better than baseline, proceed to validation.

## Phase 4 — Walk-Forward Validation

Every candidate that beats baseline must pass walk-forward validation. This is the overfitting check.

```bash
python3 scripts/run_optimization.py validate --params '{"short_ema_len": <best>, ...}'
```

A candidate PASSES validation if:
- MAR ratio improves (or stays equal) across ALL time windows
- Has at least 3 trades per window
- Results are consistent across train and test periods

A candidate FAILS if:
- Great on train, bad on test (overfit)
- Only improves in one time window
- Very few trades (lucky runs)

**Run stability check on final candidates only** (it's slow):
```bash
python3 scripts/run_optimization.py validate --params '...' --stability
```

## Phase 5 — Structural Experiments

If parameter tuning hits a ceiling, try structural changes by modifying `scripts/backtest_engine.py` directly. Ideas to explore:

1. **Fix the EMA Cross exit bug**: Remove `rawSell` from exit condition (it requires crossunder AND confirmation, which are mutually exclusive with sellConfirmBars >= 2)
2. **Adaptive ATR multiplier**: Tighten in high-vol regimes, loosen in low-vol
3. **Oscillator-gated exit**: Exit faster when composite oscillator < -0.5
4. **Multi-timeframe trend**: Add weekly EMA confirmation to entry
5. **Regime-aware parameters**: Different EMA lengths in high-vol vs low-vol

For each structural change:
1. Modify `backtest_engine.py` (add the new logic + parameter)
2. Run baseline comparison
3. If promising, run full validation
4. If it passes, generate Pine Script equivalent

**IMPORTANT**: After structural experiments, restore `backtest_engine.py` to its original state before trying the next experiment. Keep changes isolated.

## Phase 6 — Generate Report and Pine Script

For every candidate that passes validation, generate a report and Pine Script:

```bash
# Generate Pine Script for the winner
python3 scripts/generate_pine.py '{"short_ema_len": <best>, ...}' "9.0-candidate-1"
```

Save the final report to `remote/`:
- `remote/optimization-YYYY-MM-DD.md` — Full report with all results
- `remote/candidate-YYYY-MM-DD.txt` — Pine Script ready to paste into TradingView

## Report Format

The optimization report saved to `remote/` should include:

```markdown
# Montauk Optimization Report — YYYY-MM-DD

## Baseline (8.2 defaults)
CAGR: X%  MaxDD: X%  MAR: X  Trades: X

## Phase 1 Results — Parameter Sweeps
[Table of best value for each parameter]

## Phase 2 Results — Toggle Experiments
[Which filters helped/hurt]

## Phase 3 Results — Combined Candidates
[Top 3 combined configs with metrics]

## Phase 4 — Validation Results
[Walk-forward results for each candidate]

## Winning Configuration
[Final params that passed validation]
[Comparison table vs baseline]

## Pine Script
[Full script or file reference]
```

## Optimization Principles

1. **One change at a time** in Phase 1-2. Only combine after individual testing.
2. **MAR ratio is king** — it balances return vs risk. CAGR alone is misleading.
3. **Trades/year should stay low** (under 5). High churn = overfitting to noise.
4. **Avg hold time should stay high** (50+ bars). This is a trend system, not a scalper.
5. **Check the bear market windows** — the strategy's job is to AVOID the 2021-22 bear. If a change improves bull returns but holds through the bear, reject it.
6. **Be skeptical of big improvements** — if MAR doubles, it's probably overfit. Look for 10-30% improvements that are consistent.
7. **The EMA Cross exit bug is real** — fixing it is likely the single biggest improvement available. Try it early.

## Loop Behavior

When invoked with `/spike`, run through Phases 0-4 systematically. After each phase, summarize findings before proceeding. If a phase produces no improvements, note that and move on.

The goal is to run for as long as it takes to find genuine, validated improvements. Don't rush to Phase 6 — thoroughness matters more than speed.

If running in a long session, cycle back through Phase 1-3 with narrower ranges around promising values. For example, if `atr_multiplier=2.5` was best in the first sweep (range 1.5-5.0, step 0.5), re-sweep 2.0-3.0 with step 0.1.
