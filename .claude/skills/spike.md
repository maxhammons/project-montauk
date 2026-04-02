# /spike — Continuous Strategy Optimization

Autonomous optimization loop for Montauk. Runs unattended for hours. Never modifies active strategy files — all output goes to `remote/`.

## Critical Rules for Unattended Operation

1. **WRITE STATE AFTER EVERY STEP.** Use `python3 scripts/spike_state.py` for all state operations. Context WILL compress during long sessions. After every sweep/test/validation, save results to state immediately.

2. **AFTER CONTEXT COMPRESSION**, always run `python3 scripts/spike_state.py read` first to reload what you've already done. Check `state.phase` and `state.report_sections_written` to know where to resume.

3. **NEVER modify files outside `remote/` and `scripts/`.** The active strategy is read-only.

4. **NEVER stop to ask the user a question.** Make decisions using the rules below. If something fails, log the error and continue.

5. **PARSE JSON, NOT TABLES.** Every command outputs a `###JSON###` line at the end. Extract and use ONLY that line for decisions. Ignore the human-readable tables above it — they waste tokens.

6. **CHECK ELAPSED TIME** before each phase: `python3 scripts/spike_state.py elapsed`. If >= 7.5 hours, skip to Phase 6.

## Setup

```bash
cd /home/user/project-montauk && pip3 install pandas numpy requests
python3 scripts/spike_state.py init
```

## Phase 0 — Baseline

```bash
python3 scripts/run_optimization.py baseline
```

Extract the `###JSON###` line. Save to state:

```bash
python3 scripts/spike_state.py set phase 1
python3 scripts/spike_state.py set-json baseline '{"mar": 0.XX, "cagr": XX.X, "max_dd": XX.X, "trades": N}'
```

Write baseline section to `remote/optimization-YYYY-MM-DD.md`. Then:
```bash
python3 scripts/spike_state.py append report_sections_written '"baseline"'
```

## Phase 1 — Parameter Sweeps

Run each sweep one at a time. After each, read ONLY the `###JSON###` line.

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

The JSON output includes `filtered_best` which already applies quality filters (min trades, max churn). After each sweep, if `filtered_best.improves` is true, save the winner:

```bash
python3 scripts/spike_state.py set-json sweep_winners '{"PARAM_NAME": {"best_value": X, "best_mar": X.XXX, "baseline_mar": X.XXX}}'
```

After ALL sweeps: update report, advance phase:
```bash
python3 scripts/spike_state.py set phase 2
python3 scripts/spike_state.py append report_sections_written '"phase1"'
```

## Phase 2 — Toggle Experiments

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

JSON output has `"better": true/false` and `"mar_delta"`. Save results:

```bash
python3 scripts/spike_state.py set-json toggle_results '{"DESCRIPTION": {"params": {...}, "mar_delta": X.XXX, "better": true}}'
```

After all toggles: update report, advance:
```bash
python3 scripts/spike_state.py set phase 3
python3 scripts/spike_state.py append report_sections_written '"phase2"'
```

## Phase 3 — Combine Winners

Build combined configurations. Follow these steps EXACTLY:

1. Read state: `python3 scripts/spike_state.py get sweep_winners` and `python3 scripts/spike_state.py get toggle_results`
2. Sort sweep winners by `(best_mar - baseline_mar)` descending. Discard any where improvement <= 0.
3. Sort toggle results by `mar_delta` descending. Keep only those where `better` is true.
4. Start with the top sweep winner as the base config.
5. Add the second sweep winner. Test the combination:
   ```bash
   python3 scripts/run_optimization.py test --params '{"param1": val1, "param2": val2}'
   ```
6. If combination MAR > either individual MAR: KEEP. Add the third winner and test again.
7. If combination MAR < either individual MAR: DROP the second, try the third instead.
8. After exhausting sweep winners (or 5 layers max), add helpful toggles one at a time.
9. Save the top 3 combinations to state as candidates:
   ```bash
   python3 scripts/spike_state.py append candidates '{"params": {...}, "mar": X.XXX, "cagr": XX.X, "max_dd": XX.X}'
   ```

Update report, advance:
```bash
python3 scripts/spike_state.py set phase 4
python3 scripts/spike_state.py append report_sections_written '"phase3"'
```

## Phase 4 — Walk-Forward Validation

Validate each candidate:

```bash
python3 scripts/run_optimization.py validate --params '{"param1": val1, ...}'
```

JSON output has `"passes"`, `"consistent"`, `"rejection_reasons"`, and per-window results.

**PASS criteria**: `passes` is true, AND candidate MAR improves in at least 3 of 4 walk-forward windows.
**FAIL criteria**: `passes` is false, OR MAR worse in 2+ windows, OR any rejection reason mentions trade count.

Save passing candidates:
```bash
python3 scripts/spike_state.py append validated '{"params": {...}, "avg_test_mar": X.XX, "consistent": true}'
```

Update report, advance:
```bash
python3 scripts/spike_state.py set phase 5
python3 scripts/spike_state.py append report_sections_written '"phase4"'
```

## Phase 5 — Refinement Loop

This is where hours of runtime pay off. Iterate until convergence.

### 5a — Narrow sweeps around winners
For each Phase 1 winner, re-sweep at 5x finer resolution:
- Example: if best `atr_multiplier` was 3.0 (from step 0.5), re-sweep 2.0–4.0 step 0.1
- Example: if best `short_ema_len` was 11 (from step 2), re-sweep 8–14 step 1

### 5b — Grid search for correlated parameters
Test parameter INTERACTIONS using the grid command:

```bash
python3 scripts/run_optimization.py grid --spec '{"short_ema_len": [10,12,14,16,18], "med_ema_len": [20,25,30,35,40]}'
python3 scripts/run_optimization.py grid --spec '{"atr_period": [20,30,40,50], "atr_multiplier": [2.0,2.5,3.0,3.5,4.0]}'
python3 scripts/run_optimization.py grid --spec '{"quick_lookback_bars": [3,4,5,6,7], "quick_delta_pct_thresh": [-10,-8,-6,-5,-4]}'
```

The JSON output returns the top 5 combinations sorted by MAR.

### 5c — New candidates
Build new candidates from refined/grid winners. Test and validate (repeat Phase 3–4 logic).

### 5d — Loop decision

Increment iteration: `python3 scripts/spike_state.py set iteration N`

Check elapsed: `python3 scripts/spike_state.py elapsed`

**CONTINUE (go back to 5a) if ALL of these are true**:
- Latest iteration found a validated candidate better than previous best
- Elapsed time < 7.5 hours
- There are still untested grid pairs

**STOP (go to Phase 6) if ANY of these are true**:
- Two consecutive iterations produced no improvement
- All 3 grid pairs above have been tested
- Elapsed time >= 7.5 hours
- Already have 3+ validated candidates

## Phase 6 — Generate Output

Generate Pine Script for each validated candidate:
```bash
python3 scripts/generate_pine.py '{"param1": val1, ...}' "9.0-candidate-N"
```

Finalize `remote/optimization-YYYY-MM-DD.md` with:
- Baseline metrics
- Phase 1 sweep winner table
- Phase 2 toggle results
- Phase 3 top combinations
- Phase 4 validation results
- Phase 5 refinement findings
- Winning configuration with full comparison
- Pine Script file reference

Commit:
```bash
cd /home/user/project-montauk && git add remote/ && git commit -m "Add /spike optimization results" && git push -u origin main
```

## Decision Quick Reference

| Situation | Action |
|-----------|--------|
| JSON has `filtered_best.improves: false` | Skip — this param is fine at default |
| JSON has `better: false` | Skip — this toggle hurts |
| Combined MAR < individual winner MAR | Drop the weaker addition |
| Validation `passes: false` | Reject candidate |
| Validation passes but `consistent: false` | PASS with note — still usable |
| Two iterations with no improvement | Stop refinement, go to Phase 6 |
| Python script errors | Log error to state (`spike_state.py append errors '"..."'`), skip, continue |
| Context compressed / lost track | Run `spike_state.py read`, resume from `state.phase` |
| Elapsed >= 7.5 hours | Skip to Phase 6 |

## Anti-Overfitting Principles

1. **MAR ratio (CAGR / MaxDD) is the primary metric.** Not CAGR alone.
2. **This is a robustness scanner, not a magic optimizer.** With ~16 trades over 16 years, parameter optimization has limited statistical power. The goal is to find configurations that are ROBUST across all market regimes, not "optimal" on the full backtest.
3. **Be skeptical of big improvements.** If MAR doubles, it's probably overfit. Target 10-30% improvements that are consistent across windows.
4. **Trades/year must stay under 5.** This is a trend system, not a scalper.
5. **Avg hold time should stay above 50 bars.** Short holds = noise trading.
6. **The 2021-22 bear is the key test.** If a change improves bull returns but holds through the bear, reject it.
7. **Validation is non-negotiable.** No candidate ships without walk-forward validation.
8. **One change at a time in sweeps.** Use grid search for interaction testing.
