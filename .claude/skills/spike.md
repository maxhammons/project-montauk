# /spike — Continuous Strategy Optimization

Autonomous optimization loop for Montauk. Runs unattended for hours. Never modifies active strategy files — all output goes to `remote/`.

## Critical Rules for Unattended Operation

1. **WRITE STATE TO DISK AFTER EVERY STEP.** Context will compress during long sessions. After every sweep, test, or validation, append results to `remote/spike-state.json` using the Python helper below. When resuming after context compression, ALWAYS read this file first.

2. **NEVER modify files outside `remote/` and `scripts/`.** Do not touch `src/strategy/active/`, `src/indicator/active/`, `CLAUDE.md`, or `backtest_engine.py`. If you want to test structural changes, copy `backtest_engine.py` to `scripts/backtest_engine_experimental.py` and modify that copy.

3. **NEVER stop to ask the user a question.** Make decisions autonomously using the rules below. If something fails, log it to state and move on.

4. **SAVE the report incrementally.** Write/update `remote/optimization-YYYY-MM-DD.md` after EACH phase completes, not just at the end.

## Setup (run once at start)

```bash
cd /home/user/project-montauk && pip3 install pandas numpy requests 2>/dev/null
```

Initialize the state file:

```bash
python3 -c "
import json, os
from datetime import datetime
state = {
    'started': datetime.now().isoformat(),
    'phase': 0,
    'baseline': {},
    'sweep_winners': {},
    'toggle_results': {},
    'candidates': [],
    'validated': [],
    'best_config': {},
    'iteration': 0
}
os.makedirs('remote', exist_ok=True)
with open('remote/spike-state.json', 'w') as f:
    json.dump(state, f, indent=2)
print('State initialized')
"
```

## State Management

After EVERY meaningful result, update the state file. Use this pattern:

```bash
python3 -c "
import json
with open('remote/spike-state.json') as f:
    state = json.load(f)
# Example: state['sweep_winners']['atr_multiplier'] = {'best_value': 3.0, 'best_mar': 0.51}
# Example: state['phase'] = 2
with open('remote/spike-state.json', 'w') as f:
    json.dump(state, f, indent=2)
"
```

If you have lost context (e.g. after compression), read the state file FIRST:

```bash
python3 -c "
import json
with open('remote/spike-state.json') as f:
    state = json.load(f)
print(json.dumps(state, indent=2))
"
```

## Phase 0 — Baseline

```bash
cd /home/user/project-montauk && python3 scripts/run_optimization.py baseline
```

Save baseline metrics to state. These are the numbers to beat:
- `baseline.mar_ratio`
- `baseline.cagr_pct`
- `baseline.max_drawdown_pct`
- `baseline.num_trades`

Update state: `state['baseline'] = {mar, cagr, max_dd, trades}`, `state['phase'] = 1`.
Write the first section of the report to `remote/optimization-YYYY-MM-DD.md`.

## Phase 1 — Parameter Sweeps

Run each sweep. After EACH sweep, immediately save the best value to state.

**Decision rule**: A sweep winner is the value with the highest MAR ratio, BUT only if:
- MAR > baseline MAR (or within 2% of it)
- Trades >= 8 (reject if too few trades — likely overfit)
- Trades/year < 5 (reject if churning)

Sweeps to run (one at a time):

```bash
python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param med_ema_len --min 15 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param long_ema_len --min 200 --max 800 --step 50
python3 scripts/run_optimization.py sweep --param trend_ema_len --min 30 --max 120 --step 10
python3 scripts/run_optimization.py sweep --param slope_lookback --min 3 --max 20 --step 2
python3 scripts/run_optimization.py sweep --param atr_period --min 10 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param atr_multiplier --min 1.5 --max 5.0 --step 0.5
python3 scripts/run_optimization.py sweep --param quick_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param quick_lookback_bars --min 2 --max 10 --step 1
python3 scripts/run_optimization.py sweep --param quick_delta_pct_thresh --min -15.0 --max -3.0 --step 1.0
python3 scripts/run_optimization.py sweep --param range_len --min 20 --max 100 --step 10
python3 scripts/run_optimization.py sweep --param max_range_pct --min 10 --max 50 --step 5
python3 scripts/run_optimization.py sweep --param sell_cooldown_bars --min 0 --max 10 --step 1
python3 scripts/run_optimization.py sweep --param sell_confirm_bars --min 1 --max 5 --step 1
```

After ALL sweeps: save state, update report, advance to Phase 2.

## Phase 2 — Toggle Experiments

Test enabling/disabling each optional filter. Run each test and compare MAR to baseline.

```bash
python3 scripts/run_optimization.py test --params '{"enable_sell_confirm": false}'
python3 scripts/run_optimization.py test --params '{"enable_slope_filter": true}'
python3 scripts/run_optimization.py test --params '{"enable_below_filter": true}'
python3 scripts/run_optimization.py test --params '{"enable_slope_filter": true, "enable_below_filter": true}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 15}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 20}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 25}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop": true, "trail_drop_pct": 30}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit": true, "tema_exit_lookback": 3}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit": true, "tema_exit_lookback": 5}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit": true, "tema_exit_lookback": 10}'
python3 scripts/run_optimization.py test --params '{"enable_sideways_filter": false}'
```

**Decision rule**: A toggle is "helpful" if candidate MAR > baseline MAR. Record all results to state.

Save state, update report, advance to Phase 3.

## Phase 3 — Combine Winners

Build combined configurations from Phase 1-2 winners.

**Decision rules for combining**:
1. Start with the single biggest MAR improver from Phase 1.
2. Layer on the second-biggest improver. Test the combination.
3. If the combination MAR > either individual MAR, keep it and add the third.
4. If the combination MAR < either individual, drop the second and try the third instead.
5. Continue until adding more changes stops helping.
6. Layer on any helpful toggles from Phase 2.

Test each combination:
```bash
python3 scripts/run_optimization.py test --params '{"param1": val1, "param2": val2, ...}'
```

**Keep the top 3 combinations** that beat baseline. Save them to `state['candidates']`.

Save state, update report, advance to Phase 4.

## Phase 4 — Walk-Forward Validation

Validate EACH candidate from Phase 3:

```bash
python3 scripts/run_optimization.py validate --params '{"param1": val1, ...}'
```

**Decision rules**:
- **PASS**: Validation says "PASS", consistent_improvement is True or MAR improves in majority of windows
- **FAIL**: Validation says "FAIL", or MAR is worse in 2+ windows, or trades < 3 in any window

Move passing candidates to `state['validated']`. Drop failures.

If ANY candidates pass, save state, update report, advance to Phase 5.
If NO candidates pass, go to Phase 5 (Refinement) anyway.

## Phase 5 — Refinement Loop

This is where the hours of runtime pay off. Go back and dig deeper.

### 5a — Narrow sweeps around winners
For each Phase 1 winner, re-sweep with 5x finer resolution:
- If best `atr_multiplier` was 3.0 (step 0.5), re-sweep 2.0-4.0 step 0.1
- If best `short_ema_len` was 11 (step 2), re-sweep 8-14 step 1

### 5b — Cross-parameter interactions
Test pairs of parameters that might interact:
- `short_ema_len` × `med_ema_len` (entry timing)
- `atr_multiplier` × `atr_period` (exit sensitivity)
- `quick_delta_pct_thresh` × `quick_lookback_bars` (momentum exit)

Use multi-sweep:
```bash
python3 scripts/run_optimization.py multi-sweep --spec '{"short_ema_len": [10,12,14,16], "med_ema_len": [20,25,30,35,40]}'
```

### 5c — New combinations from refined values
Build new candidates from refined winners. Test and validate (Phase 3-4 again).

### 5d — Loop decision
After each refinement cycle, increment `state['iteration']`.

**CONTINUE looping if**:
- The latest iteration found a new validated candidate better than the previous best
- Total runtime < 8 hours
- There are still untested parameter interactions

**STOP looping if**:
- Two consecutive iterations produced no improvement
- All major parameter pairs have been tested
- Already have 3+ validated candidates

## Phase 6 — Generate Output

For each validated candidate:

1. Generate Pine Script:
```bash
python3 scripts/generate_pine.py '{"param1": val1, ...}' "9.0-candidate-N"
```

2. Save Pine Script to `remote/candidate-YYYY-MM-DD-N.txt`

3. Finalize the report in `remote/optimization-YYYY-MM-DD.md` with:

```markdown
# Montauk Optimization Report — YYYY-MM-DD

## Baseline (8.2 defaults)
| Metric | Value |
|--------|-------|
| CAGR | X% |
| Max Drawdown | X% |
| MAR | X |
| Trades | X |

## Phase 1 — Parameter Sweep Results
| Parameter | Baseline Value | Best Value | Baseline MAR | Best MAR | Delta |
|-----------|---------------|------------|-------------|---------|-------|

## Phase 2 — Toggle Experiments
| Configuration | MAR | vs Baseline |
|--------------|-----|------------|

## Phase 3 — Top Combined Candidates
| Candidate | Config | MAR | CAGR | MaxDD |
|-----------|--------|-----|------|-------|

## Phase 4 — Validation Results
| Candidate | Walk-Forward | Named Windows | Stability | Verdict |
|-----------|-------------|---------------|-----------|---------|

## Phase 5 — Refinement Results
[Narrowed sweep results, cross-parameter findings]

## Winning Configuration
[Best validated params with full comparison to baseline]

## Pine Script
See: remote/candidate-YYYY-MM-DD-N.txt

## Iteration Log
[How many loops, what was tried, what worked]
```

4. Commit results:
```bash
cd /home/user/project-montauk
git add remote/
git commit -m "Add /spike optimization results — YYYY-MM-DD"
git push -u origin main
```

## Decision Quick Reference

| Situation | Action |
|-----------|--------|
| Sweep value has MAR > baseline but < 8 trades | REJECT (overfit) |
| Sweep value has MAR > baseline but trades/yr > 5 | REJECT (churning) |
| Combined config MAR < individual winner MARs | DROP the weaker addition |
| Validation fails on 1 window but passes others | PASS with note |
| Validation fails on 2+ windows | FAIL — reject candidate |
| Two iterations with no improvement | STOP refinement |
| Context feels compressed / lost track | READ spike-state.json |
| Python script errors | Log error to state, skip that test, continue |
| Something unexpected happens | Log it, move to next step |

## Anti-Overfitting Principles

1. **MAR ratio is the primary metric** (CAGR / Max Drawdown). Not CAGR alone.
2. **Trades must stay low** (< 5/year). This is a trend system, not a scalper.
3. **Hold time must stay high** (50+ bars average). Short holds = noise trading.
4. **Be skeptical of big improvements.** If MAR doubles, it's probably overfit. Target 10-30% improvements.
5. **The 2021-22 bear is the key test.** If a change improves bull returns but holds through the bear, reject it.
6. **Validation is non-negotiable.** No candidate ships without walk-forward validation.
7. **One change at a time in sweeps.** Only combine after individual testing.
