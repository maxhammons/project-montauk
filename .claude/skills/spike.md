# /spike — Continuous Strategy Optimization

Autonomous loop for Montauk. Runs until 7.5-hour time limit. **Never stops early** due to "enough candidates" — keep finding better configs until time runs out. Never modifies `src/` — all output goes to `remote/`.

## Goal

Catch bulls, avoid bears. The strategy skips the down legs so that, even with imperfect timing, it beats buy-and-hold on TECL over time. Perfect timing is impossible; close-enough timing on big regime swings is the target.

**Primary metric: Regime Score** = `0.5 × bull_capture + 0.5 × bear_avoidance` (0–1, higher = better)  
**Ultimate goal: `vs_bah_multiple > 1.0`** — strategy account beats $100 held in TECL from the date of the first trade.  
MAR is a secondary sanity check only.

## Critical Rules

1. **State after every step.** Context WILL compress. `spike_state.py` after every command.
2. **On resume:** `python3 scripts/spike_state.py read` → check `phase` and `report_sections_written`.
3. **JSON only.** Parse the `###JSON###` line. Ignore human-readable output above it.
4. **Never stop to ask.** Make decisions using the rules below.
5. **Never modify `src/`.** Active strategy is read-only.
6. **Check time before each phase:** `python3 scripts/spike_state.py elapsed`. Phase 6 when ≥ 7.5h.

## Setup

```bash
cd /home/user/project-montauk && pip3 install pandas numpy requests
python3 scripts/spike_state.py init
```

## Phase 0 — Baseline + Parity Check

### 0a — Run baseline
```bash
python3 scripts/run_optimization.py baseline
```

Save to state:
```bash
python3 scripts/spike_state.py set phase 1
python3 scripts/spike_state.py set-json baseline '{"regime_score":0.XXX,"bull_capture":0.XXX,"bear_avoidance":0.XXX,"vs_bah_multiple":0.XXX,"bah_start_date":"YYYY-MM-DD","mar":0.XX,"cagr":XX.X,"max_dd":XX.X,"false_signal_rate":XX.X}'
```

### 0b — TradingView parity check (run once per session)

Read `src/strategy/active/Project Montauk 8.2.1.txt` and compare the engine's trade log against the actual TradingView trade history (if available from a previous report in `remote/`). Check:
- Do entry/exit dates match within 1 bar?
- Does trade count match?
- Are exit reasons consistent?

If discrepancies exist, note them in the report and adjust interpretation accordingly. Do NOT fix the engine mid-session — log the discrepancy and continue.

### 0c — Cross-session context

Read `remote/best-ever.json`. If `best-ever.regime_score > baseline.regime_score`, you are starting ahead of baseline — use `best-ever.params` as the starting point for Phase 1 sweeps (test the best-ever config first before sweeping defaults).

Write baseline section to `remote/spike-YYYY-MM-DD.md`.

## Phase 1 — Parameter Sweeps

One at a time. Parse `###JSON###` only. Order: most likely impactful first based on prior session results.

```bash
python3 scripts/run_optimization.py sweep --param quick_ema_len --min 3 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param short_ema_len --min 5 --max 25 --step 2
python3 scripts/run_optimization.py sweep --param med_ema_len --min 15 --max 60 --step 5
python3 scripts/run_optimization.py sweep --param atr_multiplier --min 1.5 --max 5.0 --step 0.5
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

Check `plateau_width` in JSON: wide plateau (≥5 values near best) = robust; narrow spike (1–2 values) = fragile, treat cautiously.

If `filtered_best.improves: true` → save winner:
```bash
python3 scripts/spike_state.py set-json sweep_winners '{"PARAM":{"best_value":X,"best_score":X.XXX,"delta":X.XXX,"plateau_width":N}}'
```

Also note if best value improves `vs_bah_multiple`.

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

Save toggles where `regime_score_delta > 0`:
```bash
python3 scripts/spike_state.py set-json toggle_results '{"LABEL":{"params":{...},"regime_score_delta":X.XXX}}'
```

Advance: `python3 scripts/spike_state.py set phase 3`

## Phase 3 — Combine & Validate

1. Read `sweep_winners` and `toggle_results` from state. Sort by delta descending.
2. Build combos greedily: start with top winner, add one at a time, keep if regime score improves.
3. Prefer wide-plateau params over narrow spikes when building combos.
4. Validate top 3 combos:

```bash
python3 scripts/run_optimization.py validate --params '{"p1":v1,"p2":v2}'
```

**PASS**: `passes:true` AND regime score improves over baseline in ≥3 of 4 WF windows.  
Special weight: improvements in the 2021–22 bear and 2024_onward windows are the most valuable.

Run bootstrap on any passing candidate:
```bash
python3 scripts/run_optimization.py bootstrap --params '{"p1":v1}'
```
Note `percentile_rank` — candidates scoring ≥75th percentile have non-random results.

Save passing candidates:
```bash
python3 scripts/spike_state.py append validated '{"params":{...},"regime_score":X.XXX,"bull_capture":X.XXX,"bear_avoidance":X.XXX,"vs_bah_multiple":X.XXX,"bootstrap_pct":XX.X}'
```

Update best-ever if this candidate beats `remote/best-ever.json`:
```bash
# Read best-ever, compare regime_score, if better overwrite with new values
```

Advance: `python3 scripts/spike_state.py set phase 4`

## Phase 4 — Refinement Grid

Fine-sweep around Phase 1 winners (3–5× finer resolution), then grid-search interactions:

```bash
python3 scripts/run_optimization.py grid --spec '{"short_ema_len":[10,12,14,16,18],"med_ema_len":[20,25,30,35,40]}'
python3 scripts/run_optimization.py grid --spec '{"atr_period":[20,30,40,50],"atr_multiplier":[2.0,2.5,3.0,3.5,4.0]}'
python3 scripts/run_optimization.py grid --spec '{"quick_ema_len":[4,5,6,7,8,9],"quick_lookback_bars":[3,4,5,6,7]}'
python3 scripts/run_optimization.py grid --spec '{"quick_delta_pct_thresh":[-10,-8,-6,-5,-4],"quick_ema_len":[5,7,9]}'
```

Validate and bootstrap any grid combo that beats the best validated regime score from Phase 3. Save to state.

Advance: `python3 scripts/spike_state.py set phase 5`

## Phase 5 — Infinite Proposal Loop

**This phase loops until elapsed ≥ 7.5h.** Each iteration: propose → implement → test → validate → loop.

### 5a — Check time and state
```bash
python3 scripts/spike_state.py elapsed
python3 scripts/spike_state.py set iteration N   # increment
```
If elapsed ≥ 7.5h → skip to Phase 6.

### 5b — Pick a signal category to explore

Track which categories have been tried. Each iteration pick the next UNTRIED category:

| # | Category | Signal ideas |
|---|----------|-------------|
| 1 | Volatility regime | ATR ratio (current/long-avg), Bollinger width, realized vol spike |
| 2 | Trend alignment | Multiple EMA fan (all EMAs trending same direction), ADX threshold |
| 3 | Momentum confirmation | Rate-of-change filter on entry, MACD histogram direction |
| 4 | Price structure | Higher-highs/higher-lows count, distance from long-term mean |
| 5 | Noise rejection | Minimum move requirement between exit and re-entry |
| 6 | Asymmetric exit | Faster exit in high-vol environments, slower in low-vol |
| 7 | Bear depth guard | Don't re-enter if equity is X% below recent equity peak |
| 8 | Volume | Volume spike as bear confirmation (exit faster on high-vol down days) |

Save which categories have been tried:
```bash
python3 scripts/spike_state.py append toggle_results '"tried_category_N"'
```

### 5c — Design and implement the parameter

Read `src/strategy/active/Project Montauk 8.2.1.txt` for the Pine Script logic, and `scripts/backtest_engine.py` for the Python engine.

Implement a **minimal** new parameter in `scripts/backtest_engine.py`:
- Add to `StrategyParams` with a sensible default that reproduces 8.2.1 behavior when at default
- Wire into entry or exit logic (< 30 lines of new code)
- The parameter must have a clear on/off toggle or a "disabled" default value

### 5d — Sweep and validate
```bash
python3 scripts/run_optimization.py sweep --param NEW_PARAM --min X --max Y --step Z
```

If it improves regime score: validate, bootstrap, save. If it passes and beats best-ever, update `remote/best-ever.json`.

Whether it passes or fails, log it and move to next iteration.

### 5e — Beat B&H milestone check

After each validated candidate, check `vs_bah_multiple`. If any candidate has `vs_bah_multiple > 1.0`:
- Flag it prominently in the report with **"BEATS BUY-AND-HOLD"**
- Commit immediately (don't wait for Phase 6)

### 5f — Loop

Go to 5a.

---

## Phase 6 — Generate Output

For each validated candidate, generate parameter diff (NOT full Pine Script):
```bash
python3 scripts/generate_pine.py '{"p1":v1}' "9.0-candidate-N"
```
This writes a compact diff to `remote/diff-YYYY-MM-DD-9.0-candidate-N.txt`. That's all that's needed to implement in TradingView.

Finalize `remote/spike-YYYY-MM-DD.md` (see Report Format). Update `remote/best-ever.json` if any candidate beats the stored best.

Commit and push:
```bash
git add remote/ scripts/backtest_engine.py && git commit -m "spike: results YYYY-MM-DD itr-N RS=X.XXX" && git push -u origin $(git branch --show-current)
```

---

## Report Format (compact — every section is a table, no prose)

### Baseline section
```
| Metric | Value |
|--------|-------|
| Regime Score | 0.552 (Bull 0.558 / Bear 0.546) |
| vs B&H | 0.46× ($36k vs $79k from 2011-07-11) |
| CAGR/MaxDD/MAR | 27.5% / 65% / 0.42 |
| Trades/yr · Avg bars · False signals | 1.2 · 171 · 0% |
| Bootstrap percentile | — (run separately) |
```

### Sweep winners (only params where `filtered_best.improves: true`)
```
| Param | Default | Best | ΔRS | ΔBull | ΔBear | Plateau |
|-------|---------|------|-----|-------|-------|---------|
| quick_ema_len | 15 | 5 | +0.061 | -0.071 | +0.192 | 3 vals |
```

### Candidates (one row per validated candidate)
```
| ID | Params | RS | Bull | Bear | vs B&H | T/yr | Bars | Btstrp | WF |
|----|--------|----|------|------|--------|------|------|--------|----|
| A  | qel=5  | 0.613 | 0.49 | 0.74 | 0.46× | 2.6 | 62 | 81% | PASS |
```

### Phase 5 proposals (one row per iteration)
```
| Itr | Category | Param | ΔRS | Plateau | Btstrp | WF |
|-----|----------|-------|-----|---------|--------|----|
| 1   | Volatility | atr_ratio_len | +0.012 | 4 | 78% | PASS |
```

### Best-ever update (if applicable)
```
NEW BEST: RS=X.XXX  vs B&H=X.XXXx  params={...}
[BEATS BUY-AND-HOLD]  ← if vs_bah_multiple > 1.0
```

---

## Decision Rules

| Situation | Action |
|-----------|--------|
| `filtered_best.improves: false` | Skip — no regime improvement |
| `plateau_width` = 1 or 2 | Treat as fragile — require validation to be consistent before using |
| Bear avoidance ↑, bull capture ↓ slightly | Keep — bear avoidance harder to recover from |
| Bull capture ↑, bear avoidance ↓ equally | Neutral — keep searching |
| Regime score > baseline but `false_signal_rate` doubled | Suspect — check if noise trades are driving the score |
| Validation: RS worse in 2+ WF windows | Reject |
| Bootstrap `percentile_rank` < 75% | Note in report — not statistically strong, don't reject but flag |
| `vs_bah_multiple` crosses 1.0 | Flag prominently, commit immediately |
| Script error | `spike_state.py append errors '"..."'` → continue |
| Context compressed | `spike_state.py read` → resume from `phase` |
| Elapsed ≥ 7.5h | Phase 6 |
| Two iterations with no improvement in Phase 5 | Continue anyway — try next signal category |

## Quality Floors

| Metric | Floor | Reason |
|--------|-------|--------|
| Trades/year | < 5 | Trend system, not scalper |
| Avg bars held | > 50 | Short holds = noise |
| Regime score vs baseline | > 0 | Any improvement counts |
| WF windows improved | ≥ 3 of 4 | Robustness check |

## Anti-Overfitting

- Target 5–15% RS improvements. >20% is suspicious on ~18 trades over 16 years.
- 2021–22 bear and 2024_onward are hardest windows — improvements there are signal.
- New params MUST reproduce 8.2.1 exactly at their default value.
- Wide plateau (≥5 sweep values near best) = robust. Narrow spike = fragile.
- `vs_bah_multiple > 1.0` is the long-term goal. Each session should narrow the gap.
- Bootstrap ≥75th percentile = non-random. Below that, weight results less.
- When a new param is proposed: if it only helps in bull windows and not bear, it's likely curve-fitting.
