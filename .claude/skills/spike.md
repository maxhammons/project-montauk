# /spike — Continuous Strategy Optimization

Autonomous loop for Montauk. Runs until time limit. Never stops early due to "enough candidates." Never modifies `src/` — all output goes to `remote/`.

## Goal

Catch bulls, avoid bears. Primary metric: **Regime Score** (`0.5 × bull_capture + 0.5 × bear_avoidance`). Secondary: `vs_bah_multiple` — does the strategy account beat $100 held in TECL from the date of the first trade? MAR is a sanity check only.

## Critical Rules

1. **State after every step.** Context WILL compress. Use `spike_state.py` after every command.
2. **On resume:** `python3 scripts/spike_state.py read` → check `phase` and `report_sections_written`.
3. **JSON only.** Parse the `###JSON###` line. Ignore human-readable output above it.
4. **Never stop to ask.** Make decisions using the rules below.
5. **Never modify `src/`.** Active strategy is read-only.
6. **Check time before each phase:** `python3 scripts/spike_state.py elapsed`. Stop loop at 7.5 hours.

## Setup

```bash
cd /home/user/project-montauk && pip3 install pandas numpy requests
python3 scripts/spike_state.py init
```

## Phase 0 — Baseline

```bash
python3 scripts/run_optimization.py baseline
```

Save to state:
```bash
python3 scripts/spike_state.py set phase 1
python3 scripts/spike_state.py set-json baseline '{"regime_score":0.XXX,"bull_capture":0.XXX,"bear_avoidance":0.XXX,"mar":0.XX,"cagr":XX.X,"max_dd":XX.X,"vs_bah_multiple":0.XXX,"bah_start_date":"YYYY-MM-DD"}'
```

Append to `remote/spike-YYYY-MM-DD.md` — **baseline section** (see Report Format below).

## Phase 1 — Parameter Sweeps

One at a time. After each: parse `###JSON###` only.

```bash
python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param med_ema_len --min 15 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param atr_multiplier --min 1.5 --max 5.0 --step 0.5
python3 scripts/run_optimization.py sweep --param quick_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param quick_lookback_bars --min 2 --max 10 --step 1
python3 scripts/run_optimization.py sweep --param quick_delta_pct_thresh --min -15.0 --max -3.0 --step 1.0
python3 scripts/run_optimization.py sweep --param atr_period --min 10 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param trend_ema_len --min 30 --max 120 --step 10
python3 scripts/run_optimization.py sweep --param slope_lookback --min 3 --max 20 --step 2
python3 scripts/run_optimization.py sweep --param sell_cooldown_bars --min 0 --max 10 --step 1
python3 scripts/run_optimization.py sweep --param sell_confirm_bars --min 1 --max 5 --step 1
python3 scripts/run_optimization.py sweep --param range_len --min 20 --max 100 --step 10
python3 scripts/run_optimization.py sweep --param max_range_pct --min 10 --max 50 --step 5
```

If `filtered_best.improves: true` → save winner:
```bash
python3 scripts/spike_state.py set-json sweep_winners '{"PARAM":{"best_value":X,"best_score":X.XXX,"delta":X.XXX}}'
```

Advance: `python3 scripts/spike_state.py set phase 2`

## Phase 2 — Toggle Experiments

```bash
python3 scripts/run_optimization.py test --params '{"enable_sell_confirm":false}'
python3 scripts/run_optimization.py test --params '{"enable_slope_filter":true}'
python3 scripts/run_optimization.py test --params '{"enable_below_filter":true}'
python3 scripts/run_optimization.py test --params '{"enable_slope_filter":true,"enable_below_filter":true}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop":true,"trail_drop_pct":15}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop":true,"trail_drop_pct":20}'
python3 scripts/run_optimization.py test --params '{"enable_trail_stop":true,"trail_drop_pct":25}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit":true,"tema_exit_lookback":3}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit":true,"tema_exit_lookback":5}'
python3 scripts/run_optimization.py test --params '{"enable_tema_exit":true,"tema_exit_lookback":10}'
python3 scripts/run_optimization.py test --params '{"enable_sideways_filter":false}'
```

Save winners (regime_score_delta > 0):
```bash
python3 scripts/spike_state.py set-json toggle_results '{"LABEL":{"params":{...},"regime_score_delta":X.XXX}}'
```

Advance: `python3 scripts/spike_state.py set phase 3`

## Phase 3 — Combine & Validate

1. Read `sweep_winners` and `toggle_results` from state.
2. Sort by delta descending. Build combos greedily — add one param at a time, test, keep if regime score improves.
3. Validate top 3 combos:
```bash
python3 scripts/run_optimization.py validate --params '{"p1":v1,"p2":v2}'
```
**PASS**: `passes:true` AND regime score improves in ≥3 of 4 WF windows.

Save passing candidates:
```bash
python3 scripts/spike_state.py append validated '{"params":{...},"regime_score":X.XXX,"bull_capture":X.XXX,"bear_avoidance":X.XXX,"vs_bah_multiple":X.XXX}'
```

Advance: `python3 scripts/spike_state.py set phase 4`

## Phase 4 — Refinement Grid

Fine-sweep around Phase 1 winners (5× resolution), then grid-search interactions:

```bash
python3 scripts/run_optimization.py grid --spec '{"short_ema_len":[10,12,14,16,18],"med_ema_len":[20,25,30,35,40]}'
python3 scripts/run_optimization.py grid --spec '{"atr_period":[20,30,40,50],"atr_multiplier":[2.0,2.5,3.0,3.5,4.0]}'
python3 scripts/run_optimization.py grid --spec '{"quick_ema_len":[4,5,6,7,8,9],"quick_lookback_bars":[3,4,5,6,7]}'
python3 scripts/run_optimization.py grid --spec '{"quick_delta_pct_thresh":[-10,-8,-6,-5,-4],"quick_ema_len":[5,7,9]}'
```

Validate any combo that beats best validated regime score. Save to state as before.

Advance: `python3 scripts/spike_state.py set phase 5`

## Phase 5 — Propose New Parameters (Infinite Loop Core)

This phase never ends until elapsed >= 7.5h. Each iteration:

### 5a — Propose

Read `src/strategy/active/Project Montauk 8.2.1.txt` and `scripts/backtest_engine.py`. Reason about what new filter, exit condition, or entry gate might better detect regime changes. Think in terms of:
- **Bear detection**: what signals reliably precede a regime change from bull→bear? (e.g. volatility spike, EMA fan collapse, volume surge on down days)
- **Bull re-entry**: what confirms a trough is in and a new bull leg is starting? (e.g. multiple EMAs re-aligning, ATR normalizing after a spike)
- **Noise rejection**: what filter would prevent whipsaw entries during choppy/flat regimes?

Pick **one new parameter or filter** not currently in the code. Implement it minimally in `scripts/backtest_engine.py` — add to `StrategyParams`, wire into entry/exit logic, keep the change under ~30 lines. Default value must reproduce current 8.2.1 behavior exactly when set to its off/default state.

### 5b — Sweep & Validate

```bash
python3 scripts/run_optimization.py sweep --param NEW_PARAM --min X --max Y --step Z
```

If it improves regime score: validate, save to state. Whether it passes or fails, log it:
```bash
python3 scripts/spike_state.py append toggle_results '{"NEW_PARAM_label":{"params":{...},"regime_score_delta":X.XXX,"tested_iteration":N}}'
```

### 5c — Loop decision

```bash
python3 scripts/spike_state.py elapsed
python3 scripts/spike_state.py set iteration N  # increment
```

**Continue** (back to 5a) unless elapsed >= 7.5h.
**Never stop** because "we have enough candidates" — keep proposing and testing new ideas.

## Phase 6 — Generate Output

For each validated candidate, generate Pine Script:
```bash
python3 scripts/generate_pine.py '{"p1":v1}' "9.0-candidate-N"
```

Finalize `remote/spike-YYYY-MM-DD.md`. Commit:
```bash
git add remote/ scripts/backtest_engine.py && git commit -m "spike: results YYYY-MM-DD" && git push -u origin $(git branch --show-current)
```

---

## Report Format (compact — minimize tokens)

Every section uses the minimal table format below. No prose paragraphs. No per-trade lists.

### Baseline
```
| Metric | Value |
|--------|-------|
| Regime Score | 0.552 (Bull 0.558 / Bear 0.546) |
| vs B&H | 0.46× ($36k vs $79k from 2011-07-11) |
| CAGR / MaxDD / MAR | 27.5% / 65% / 0.42 |
| Trades/yr · Avg bars | 1.2 · 171 |
```

### Sweep Results
```
| Param | Default | Best | ΔRS | ΔBull | ΔBear |
|-------|---------|------|-----|-------|-------|
| quick_ema_len | 15 | 5 | +0.061 | -0.071 | +0.192 |
```
(Only include params where `filtered_best.improves: true`)

### Candidates
```
| ID | Params | RS | Bull | Bear | vs B&H | MAR | T/yr | Bars | WF |
|----|--------|----|------|------|--------|-----|------|------|----|
| A  | qel=5  | 0.613 | 0.488 | 0.738 | 0.46× | 0.33 | 2.6 | 62 | PASS |
```

### New Parameters Tested (Phase 5)
```
| Iter | Param | Description | ΔRS | Pass? |
|------|-------|-------------|-----|-------|
| 1 | rsi_filter_len | RSI<70 entry gate | +0.012 | yes |
```

---

## Decision Rules

| Situation | Action |
|-----------|--------|
| `filtered_best.improves: false` | Skip — no regime improvement |
| `regime_score_delta <= 0` | Skip toggle |
| Combo RS < either individual | Drop weaker param, try next |
| Bear avoidance ↑, bull capture ↓ slightly | Keep — bear avoidance harder to fix |
| Bull capture ↑, bear avoidance ↓ equally | Neutral — keep searching |
| Validation: RS worse in 2+ WF windows | Reject |
| `vs_bah_multiple` < baseline | Note in report, don't reject on this alone |
| `vs_bah_multiple` > 1.0 | Flag prominently — strategy beating B&H |
| Script error | `spike_state.py append errors '"..."'` → continue |
| Context compressed | `spike_state.py read` → resume from `phase` |
| Elapsed ≥ 7.5h | Go to Phase 6 |

## Quality Floors (reject anything below these)

| Metric | Floor |
|--------|-------|
| Trades/year | < 5 |
| Avg bars held | > 50 |
| Regime score improvement | > 0 (any positive) |
| WF windows improved | ≥ 3 of 4 |

## Anti-Overfitting

- Target 5–15% regime score improvements. >20% is suspicious.
- 2021–22 bear and 2024_onward are the hardest windows — improvements there are signal.
- New parameters MUST default to reproducing current 8.2.1 behavior exactly.
- `vs_bah_multiple > 1.0` is the long-term goal. Narrowing the gap each iteration is progress.
