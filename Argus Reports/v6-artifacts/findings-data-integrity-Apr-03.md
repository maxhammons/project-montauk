# Data-Integrity Findings — Apr-03

**Specialist:** Data-Integrity
**Files read:** 45 / 88 (remaining 43 are Pine Script v6 reference docs and .DS_Store files)
**Scratchpad:** Argus Reports/v6-artifacts/scratchpad-data-integrity-Apr-03.md

---

## Finding 1: Two Divergent Backtest Engines Producing Incompatible Results

**Confidence:** high
**Confidence trajectory:** 85% -> 95% [CONFIRMED RISING]
**Category:** parity-gap
**Files:** `scripts/backtest_engine.py` (lines 589-967), `scripts/strategy_engine.py` (lines 495-624), `scripts/strategies.py` (lines 26-78)
**Claim:** The v4 `strategies.py::montauk_821()` function produces materially different trade signals than the v3 `backtest_engine.py::run_backtest()` function, making cross-engine fitness comparisons invalid.
**Evidence:** The v4 montauk_821 strategy (strategies.py lines 26-78) is missing at least 6 features present in the v3 engine: (1) sideways filter (Donchian range check), (2) TEMA entry filters (slope + price-above), (3) sell confirmation window using barssince logic, (4) trailing peak stop, (5) TEMA slope exit, (6) volume spike exit. The v4 version compares ema_short to ema_med for entry (line 55), while the v3 version also checks trend slope, TEMA slope, above-TEMA, sideways filter, ATR ratio filter, ADX filter, ROC filter, and bear guard (lines 721-722). The v4 EMA cross exit is a simple `ema_s[i] < ema_m[i] * (1 - buffer)` (line 74), while the v3 does a barssince(crossunder) scan within a confirmation window (lines 728-756). These differences mean the evolutionary optimizer in evolve.py is ranking montauk_821 against RSI Regime using a crippled version of 8.2.1, making the 4.7x fitness gap meaningless.
**Financial impact:** The optimizer concluded RSI Regime is 4.7x better than Montauk 8.2.1. If this comparison drove a strategy switch in production, it would be based on a strawman — the real 8.2.1 with all its filters likely performs significantly better than the stripped-down v4 replica. Trading decisions based on invalid comparisons.
**Proposed fix:** Either port the full v3 run_backtest logic into a strategies.py-compatible function, or refactor the v4 backtest() to accept strategy_fn from strategies.py while still running the v3 indicator/exit stack for montauk_821. Estimated: 150-200 LOC, 2-3 hours.
**If not fixed:** Every cross-strategy comparison is corrupted. The optimizer will keep declaring simpler strategies superior because its 8.2.1 baseline is artificially weak.

---

## Finding 2: RSI Regime Winner Exhibits Classic Overfitting Signatures

**Confidence:** high
**Confidence trajectory:** 80% -> 90% [CONFIRMED RISING]
**Category:** overfitting-risk
**Files:** `remote/winners/rsi-regime-2026-04-03.json`, `remote/evolve-results-2026-04-03.json`, `remote/best-ever.json`, `scripts/evolve.py` (lines 122-244)
**Claim:** The RSI Regime strategy with fitness 2.18 is overfitted to the in-sample data and will not generalize to live trading.
**Evidence:** Five red flags converge: (1) 100% win rate on only 10 trades (rsi-regime-2026-04-03.json line 11) — statistically meaningless sample. (2) 75.1% max drawdown (best-ever.json line 14) — a strategy that draws down 75% is functionally broken for real capital. (3) Only 19 generations / 1330 evaluations in 0.01 hours (evolve-results line 4-5) — the search space was barely sampled. (4) No walk-forward validation was run on this result — validation.py only imports from backtest_engine.py (v3) and cannot validate v4 strategies. (5) 0.7 trades/year means the entire backtest produced ~12 trades over 17 years — each trade contributes 8.3% to the win rate, making the metric extremely fragile to any single trade change.
**Financial impact:** If deployed, this strategy holds through 75% drawdowns (a $100K account drops to $25K). The 100% win rate creates false confidence. On real capital, a single losing trade would destroy the psychological basis for continuing the strategy.
**Proposed fix:** (1) Implement walk-forward validation for v4 strategies (port validation.py to work with strategy_engine). (2) Add minimum trade count of 20+ for any strategy to be ranked. (3) Add max drawdown hard cap at 50% in the fitness function. (4) Run the RSI Regime through at least 500 generations before declaring it a winner. Estimated: 100 LOC for validation port, 20 LOC for fitness guards.
**If not fixed:** A strategy with 75% drawdown and 10 trades will be deployed to production, where a single adverse regime shift (e.g., 2022 tech bear) could wipe most of the account.

---

## Finding 3: RSI Calculation Diverges from Pine Script

**Confidence:** medium
**Confidence trajectory:** 60% -> 75% [RISING]
**Category:** calculation-error
**Files:** `scripts/strategy_engine.py` (lines 90-103), Pine Script `ta.rsi()` specification
**Claim:** The v4 `_rsi()` function produces different values than Pine Script's `ta.rsi()` for the first ~2*length bars, biasing RSI crossover signals near the start of the dataset.
**Evidence:** The v4 _rsi function (strategy_engine.py line 95) computes `delta = np.diff(series, prepend=series[0])`, which sets `delta[0] = 0`. It then applies `_rma()` to gains and losses arrays starting from index `length-1` (the SMA seed). Pine Script's ta.rsi() uses `ta.rma()` which seeds with an SMA of the first `length` values of the change array. The difference: Python prepends a zero to the delta array, shifting all subsequent indices by one. The _rma seed in Python averages gains[0:length] where gains[0] is always 0 (from the prepended zero), while Pine Script's seed averages the actual first `length` changes. For RSI(14), this means the first 28+ bars will have slightly different RSI values, potentially shifting when RSI crosses the 35 entry threshold by 1-2 bars. On a strategy with only 10-12 trades over 17 years, shifting entry timing by even 1 bar could change the trade list.
**Financial impact:** RSI Regime enters on RSI crossing up through 35. If the Python RSI reads 34.8 on bar N where Pine reads 35.2, the Python engine records an entry one bar late (or vice versa). With TECL's 3x leverage, a 1-bar timing difference can mean 2-5% price difference. Over 10 trades, this compounds.
**Proposed fix:** Replace `np.diff(series, prepend=series[0])` with explicit `delta[i] = series[i] - series[i-1]` for i >= 1, and set delta[0] = 0 explicitly. Then verify the RMA seed window starts at the right index. Estimated: 10 LOC, 30 minutes. Also add a parity test that compares Python RSI output against known Pine Script RSI values for the same price data.
**If not fixed:** Every RSI-based strategy in the v4 engine will have slightly different signal timing than the Pine Script version, making Python-discovered winners potentially non-replicable in TradingView.

---

## Finding 4: Walk-Forward Validation Cannot Validate v4 Strategies

**Confidence:** high
**Confidence trajectory:** 70% -> 90% [CONFIRMED RISING]
**Category:** overfitting-risk
**Files:** `scripts/validation.py` (line 17), `scripts/evolve.py` (entire file), `scripts/strategy_engine.py`
**Claim:** The walk-forward validation framework is structurally disconnected from the v4 strategy engine, meaning no anti-overfitting checks are applied to any v4 strategy.
**Evidence:** validation.py line 17 imports `from backtest_engine import StrategyParams, BacktestResult, run_backtest`. It is hardwired to the v3 engine's StrategyParams dataclass and run_backtest function. The v4 engine (strategy_engine.py + strategies.py + evolve.py) uses a completely different API: `Indicators` objects, strategy functions returning signal arrays, and a generic `backtest()` function. There is no adapter between them. evolve.py (the v4 optimizer) never calls validation.py at all — it runs pure in-sample optimization with no out-of-sample testing. The fitness function (evolve.py lines 49-70) has a basic trade count guard (`num_trades < 3` returns 0) but no walk-forward window splitting, no parameter stability check, no named window stress tests.
**Financial impact:** Every v4 strategy result — including the RSI Regime "winner" — has been evaluated only on the full in-sample dataset. Without walk-forward validation, any parameter set that happens to fit the specific sequence of bull/bear periods in TECL 2009-2026 will score highly, regardless of whether the pattern generalizes.
**Proposed fix:** Create a `validate_v4()` function that wraps strategy_engine.backtest() with the walk-forward splitting logic from validation.py. Integrate it into evolve.py as a post-optimization step for any strategy that exceeds baseline fitness. Estimated: 80-120 LOC, 2 hours.
**If not fixed:** The optimizer will continue producing "winners" that are curve-fitted to historical data. The first live drawdown will reveal the overfitting.

---

## Finding 5: Parity Check Tolerances Mask Real Errors

**Confidence:** high
**Confidence trajectory:** 70% -> 80% [RISING]
**Category:** parity-gap
**Files:** `scripts/parity_check.py` (lines 119-125), `src/strategy/testing/archive/backtest-comparison.md`
**Claim:** The parity check uses tolerance bands of 10-30% which are too wide to detect meaningful discrepancies, and the measured 3.5% CAGR gap is likely an underestimate.
**Evidence:** parity_check.py lines 119-125 define tolerances: total_trades=2 (absolute), win_rate=10%, CAGR=10%, total_return=30%, avg_bars_held=20%. A 10% tolerance on CAGR means Python reporting 34% when TradingView shows 37.7% (an 8.5% relative error) would PASS. The actual comparison data (backtest-comparison.md) shows TradingView 8.2.1 CAGR is 37.73% — if Python reports anything from 33.96% to 41.50%, it passes. The 30% tolerance on total return is extreme: TradingView shows 25,300% total return for 8.2.1, so Python could report anywhere from 17,710% to 32,890% and still "pass." These tolerances exist because the engine genuinely produces different numbers, but declaring the gap acceptable doesn't fix it.
**Financial impact:** A 3.5% CAGR error over 17 years of backtesting (37.73% vs ~34.2%) represents a massive difference in compounded terminal wealth. At $1000 initial: 37.73% CAGR = ~$253K, 34.2% CAGR = ~$169K. The optimizer treats its numbers as ground truth for ranking parameter sets. If the ranking function is off by this much, the "optimal" parameters found in Python may not be optimal on TradingView.
**Proposed fix:** (1) Tighten tolerances to 5% for CAGR and 2 trades for trade count. (2) Add per-trade comparison (not just aggregates) — compare each entry/exit date between Python and TradingView. (3) Identify the root cause of the gap (likely EMA warmup period or order fill timing). Estimated: 50 LOC for tighter checks, 100+ LOC for per-trade comparison.
**If not fixed:** Optimization results will continue to diverge from TradingView reality. The parity check creates a false sense of validation.

---

## Finding 6: Regime Scoring Thresholds Are Miscalibrated for 3x Leveraged ETFs

**Confidence:** medium
**Confidence trajectory:** 50% -> 70% [RISING]
**Category:** calculation-error
**Files:** `scripts/backtest_engine.py` (lines 275-361, 432-511)
**Claim:** The 30% bear threshold and bars-in-market metric are inappropriate for TECL, inflating regime scores and misranking strategies.
**Evidence:** Bear detection (line 279) uses `bear_threshold=0.30` (30% peak-to-trough). TECL, as a 3x leveraged ETF, routinely experiences 30%+ drawdowns during normal corrections — not just bear markets. A 10% SPY pullback becomes a ~30% TECL drawdown through leverage and volatility drag. This means the detector likely identifies 5-8+ "bear" periods where only 2-3 were genuine bear markets, diluting the bear avoidance score across many events. Additionally, bull capture (lines 482-498) measures `bars_in / bull_bars` — the fraction of bars the strategy was in the market during a bull period. This penalizes strategies that enter late in a bull but catch the strongest move (e.g., entering at the 50% mark of a rally but capturing the exponential acceleration phase). A timing-smart strategy gets the same score as one that was in for the same number of bars but missed the best days.
**Financial impact:** A strategy that avoids 3 genuine bears but enters during 2 routine 30% corrections will score lower on bear avoidance than one that happens to be out during all 5 detected "bears" — even if 2 of those 5 were just noise. The regime score is the primary fitness metric for v3 optimization and a secondary bonus in v4. Miscalibrated scoring leads to selecting for noise avoidance rather than genuine regime timing.
**Proposed fix:** (1) Raise bear_threshold to 45-50% for TECL (a real tech bear is 50%+ on TECL due to 3x leverage). (2) Replace bars-in with return-captured: measure the actual equity change during bull periods, not just whether the strategy was "in." Estimated: 30 LOC for threshold change, 60 LOC for return-captured metric.
**If not fixed:** The optimizer will keep rewarding strategies that avoid routine volatility rather than strategies that genuinely time bull/bear regimes.

---

## Finding 7: Breakout Strategy Has Stateful Bug in Peak Tracking

**Confidence:** high
**Confidence trajectory:** 70% -> 90% [CONFIRMED RISING]
**Category:** calculation-error
**Files:** `scripts/strategies.py` (lines 154-197)
**Claim:** The `breakout()` strategy in strategies.py has a peak tracking variable that persists across trades incorrectly, causing the trailing stop to fire on stale peak values.
**Evidence:** The variable `peak_since_entry` is initialized to `np.nan` on line 166 before the loop, then set to `cl[i]` when `entries[i]` is True (line 195). However, the backtest engine (strategy_engine.py backtest() function) manages position state independently. The strategy function runs the full bar loop ONCE, producing boolean entry/exit arrays. The peak_since_entry in the strategy function tracks the highest price since any entry signal, not since the backtest engine actually entered a position. If the strategy emits entry=True on bar 100, peak starts tracking from bar 100. But if the backtest engine was already in a position and doesn't act on that entry signal, the peak tracking is out of sync. Worse: on line 182, peak_since_entry is only reset to nan on a "Trail Stop" exit (line 183). If the exit was due to "ATR Shock" (line 191), peak_since_entry is reset. But if neither exit fires and entries[i] is True on line 194, peak is reset to cl[i], potentially lowering the peak mid-trade.
**Financial impact:** The trailing stop could fire prematurely (if peak is stale from a prior trade) or never fire (if peak was reset during a position hold). For the breakout strategy specifically, this could explain why its fitness (0.50) underperforms expectations — the trailing stop is not behaving as intended.
**Proposed fix:** Move peak tracking into the backtest engine, where position state is actually managed. Pass a callback or use a stateful strategy object. Alternative: the strategy function should return a separate "peak_reset" signal that the engine uses. Estimated: 30-50 LOC.
**If not fixed:** The breakout strategy's trailing stop is unreliable. Any optimization of trail_pct is optimizing against a buggy implementation.

---

## Finding 8: No CSV Data Validation

**Confidence:** high
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** data-validation
**Files:** `scripts/data.py` (lines 16-21), `reference/TECL Price History (2-23-26).csv` (lines 1-30)
**Claim:** The CSV data is loaded with no integrity checks — corrupted rows, missing splits, or stale prices would silently propagate through all backtests.
**Evidence:** `load_csv()` (data.py lines 16-21) does `pd.read_csv(CSV_PATH, parse_dates=["date"])` followed by sort and column lowercase. No checks for: (1) duplicate dates, (2) out-of-order OHLC (high < low), (3) zero or negative prices, (4) gaps in the date sequence beyond weekends/holidays, (5) consistency between the `change_pct` column and actual (close[i]/close[i-1] - 1), (6) stock split adjustments. The CSV starts at $0.33 in 2008 (line 2), which is the split-adjusted price. If the CSV was ever re-downloaded without split adjustment, all pre-split prices would be wrong by a factor of 2-4x, and no code would detect this. The column `change_pct` is present but never used by any code — it could serve as a validation check but doesn't.
**Financial impact:** If even one row has a corrupted close price (e.g., $0 or a pre-split unadjusted value), it would produce extreme returns in that bar, triggering ATR exits, distorting EMA calculations for hundreds of subsequent bars, and corrupting regime detection. The entire backtest result would be wrong with no warning.
**Proposed fix:** Add a `validate_data()` function that checks: (1) no duplicate dates, (2) high >= low for all rows, (3) close between low and high, (4) no price changes > 50% in a single bar (TECL is 3x but > 50% in one day is suspicious), (5) verify change_pct matches actual returns within 0.5%. Estimated: 40 LOC, 30 minutes.
**If not fixed:** Silent data corruption. The CSV is the foundation of every backtest — if it's wrong, everything downstream is wrong and nobody knows.

---

## Finding 9: Yahoo API Data Merge Has No Overlap Validation

**Confidence:** medium
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** data-pipeline
**Files:** `scripts/data.py` (lines 72-118)
**Claim:** The CSV-to-Yahoo merge in `get_tecl_data()` can silently produce a price discontinuity at the merge point if the two sources use different adjustment bases.
**Evidence:** `get_tecl_data()` (line 88) fetches Yahoo data starting from CSV's last date + 1 day, then concatenates the two DataFrames (line 108). The function filters `yf_df[yf_df["date"] > csv_last_date]` (line 96) to avoid overlap, but this means there is NO overlap — no shared date to verify that both sources agree on the same price for the same day. If the CSV uses one split-adjustment factor and Yahoo returns a different one (which happens when Yahoo retroactively adjusts prices), there would be a price jump at the merge point. The EMA calculations would see this as a real price movement, potentially triggering entry or exit signals. The assertions on lines 115-116 only check that columns exist, not that values are consistent.
**Financial impact:** A split-adjusted price mismatch at the merge point (e.g., CSV shows close=100 on the last day, Yahoo shows close=102 for the next day when the real change was 0%) would create a phantom 2% gap. For TECL with 3x leverage, this could trigger ATR exits or shift EMA crossovers. Since the merge point is at the most recent data (where live trading decisions are made), this is the highest-risk location for data errors.
**Proposed fix:** (1) Fetch one overlapping day from Yahoo (the last CSV date). (2) Compare the overlapping close prices — if they differ by more than 0.5%, warn and refuse to merge. (3) If they match, proceed with the merge. Estimated: 15 LOC.
**If not fixed:** A price discontinuity at the merge point could trigger false signals in live trading, exactly when data accuracy matters most.

---

## Finding 10: Evolve.py Stagnation Detection References Non-Existent Attribute

**Confidence:** high
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** calculation-error
**Files:** `scripts/evolve.py` (line 234)
**Claim:** The stagnation-adaptive mutation rate in evolve.py references a function attribute that is never set, causing mutation rate to always use the "extreme stagnation" value.
**Evidence:** Line 234 reads: `stag = generation - getattr(evolve, '_last_improve', {}).get(strat_name, 0)`. The `evolve` here refers to the function `evolve()` at line 122. The attribute `_last_improve` is never set anywhere in the codebase (confirmed via search). `getattr(evolve, '_last_improve', {})` returns an empty dict `{}`, so `.get(strat_name, 0)` returns `0`. Therefore `stag = generation - 0 = generation`. Since generation starts at 1 and increases, `stag` is always > 80 after generation 80, which means `mut_rate = 0.50` (the highest level) kicks in at generation 80 and stays there. Before generation 80: generation > 30 gives `mut_rate = 0.30` starting at generation 31. This means the adaptive mutation rate is actually just `0.15 for gen 1-30, 0.30 for gen 31-80, 0.50 for gen 81+` — not adaptive to actual improvement events.
**Financial impact:** The evolutionary optimizer converges slower than intended because it doesn't adapt mutation rate to actual stagnation. With only 19 generations in the recorded run, this bug didn't matter yet, but for longer 8-hour runs (hundreds of generations), the mutation rate will be stuck at 0.50 (maximum randomness) for most of the run, degrading optimization quality.
**Proposed fix:** Add `if not hasattr(evolve, '_last_improve'): evolve._last_improve = {}` before the loop, and update `evolve._last_improve[strat_name] = generation` whenever a strategy's best score improves. Estimated: 5 LOC.
**If not fixed:** Multi-hour optimization runs will waste compute on maximum-randomness mutations instead of fine-tuning near optima.

---

## Finding 11: v4 Backtest Entry/Exit Same-Bar Allows Position Flip Without Cooldown

**Confidence:** medium
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** parity-gap
**Files:** `scripts/strategy_engine.py` (lines 534-557)
**Claim:** The v4 backtest engine allows a position to be closed and re-opened on the same bar, bypassing the cooldown period.
**Evidence:** In strategy_engine.py backtest(), the exit check (line 538) runs first. If `position > 0 and exits[i]`, the position is closed and `last_sell_bar = i` (line 542). Immediately after, the entry check (line 556) runs: `if position == 0 and entries[i]`, with cooldown check `if (i - last_sell_bar) > cooldown_bars`. When cooldown_bars=0 (default), `i - i > 0` is `0 > 0 = False`, so entry is blocked. When cooldown_bars=0 and the condition is `> cooldown_bars`, a same-bar re-entry is blocked. However, when cooldown_bars=0 and both entry and exit signals fire on the same bar, this means a valid entry is being suppressed (because `0 > 0` is false). Compare to Pine Script 8.2.1 (line 239-241): `(bar_index - lastSellBar) > sellCooldownBars` — same logic. BUT: In Pine, `strategy.close()` and `strategy.entry()` on the same bar are both processed (process_orders_on_close=true). The v4 Python engine processes exit first, then entry, which means on a bar where both fire with cooldown=0, Pine enters but Python doesn't.
**Financial impact:** For strategies with cooldown=0 (like golden_cross and some breakout configs), valid entry signals are suppressed on bars where both entry and exit conditions are true. This could cause the Python engine to miss trades that TradingView would take, further widening the parity gap.
**Proposed fix:** Change the cooldown check from `> cooldown_bars` to `>= cooldown_bars + 1` or handle the same-bar case explicitly by allowing re-entry when cooldown is 0 and the exit just happened. Estimated: 5 LOC.
**If not fixed:** Strategies with cooldown=0 will produce fewer trades in Python than in TradingView, making the Python optimizer biased toward strategies that don't trigger simultaneous entry/exit signals.

---

## Finding 12: generate_pine.py Cannot Generate Non-Montauk Strategies

**Confidence:** high
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** parity-gap
**Files:** `scripts/generate_pine.py` (lines 26-57), `src/strategy/testing/Montauk RSI Regime.txt`
**Claim:** The Pine Script generation pipeline only maps Montauk 8.2.1 parameters and cannot produce production-quality Pine Script for new strategy architectures like RSI Regime.
**Evidence:** generate_pine.py contains a PARAM_MAP (lines 26-57) that maps Python parameter names to Pine Script variable names — exclusively for 8.2.1's parameter set. The file's only function, `generate_diff()`, compares candidate params against 8.2.1 defaults and outputs a text diff. It cannot generate a complete Pine Script file for a different strategy architecture. The RSI Regime Pine Script (src/strategy/testing/Montauk RSI Regime.txt) was hand-written (or LLM-generated separately), not produced by generate_pine.py. Any parameters found by the v4 optimizer for RSI Regime, breakout, golden_cross, etc. must be manually translated to Pine Script. This is not just a convenience issue — manual translation is an error source. The RSI Regime Pine uses `ta.rsi()` and `ta.crossover()` which may not match the v4 _rsi() and crossover condition (the Python checks `rsi[i-1] < entry_level and rsi[i] >= entry_level`, while Pine uses `ta.crossover(rsi, entryRsi)` which checks `rsi[i-1] <= entryRsi and rsi[i] > entryRsi` — the boundary condition `<=` vs `<` differs).
**Financial impact:** When the optimizer discovers a winning strategy, the hand-translation step introduces errors. The RSI crossover boundary condition difference (`<` vs `<=`) means that on bars where RSI exactly equals entry_rsi, Python and Pine disagree on whether entry fires. This is a single-bar timing issue but it's the kind of discrepancy that erodes trust in the pipeline.
**Proposed fix:** Create a strategy-specific Pine Script template system. Each strategy in strategies.py should have a corresponding Pine Script template with parameter insertion points. Estimated: 200-300 LOC for a template system covering all 7 strategies.
**If not fixed:** Every new strategy discovered by the optimizer requires manual Pine Script implementation with no automated verification that the Pine matches the Python logic.

---

## Finding 13: Bear Avoidance Score Defaults to 1.0 When No Bears Detected

**Confidence:** medium
**Confidence trajectory:** N/A [FIRST ASSESSMENT]
**Category:** calculation-error
**Files:** `scripts/backtest_engine.py` (line 500)
**Claim:** When no bear periods are detected in a data window, bear_avoidance defaults to 1.0 (perfect score), inflating the composite regime score for short or truncated time windows.
**Evidence:** Line 500: `bear_avoidance = float(np.mean(bear_avoidance_scores)) if bear_avoidance_scores else 1.0`. This means if the walk-forward validation splits the data into a window that contains no 30%+ drawdown (e.g., 2013-2017 for SPY-like assets, or early 2009-2011 for TECL which was just recovering), the bear avoidance score is automatically 1.0. Combined with the composite formula `0.5 * bull_capture + 0.5 * bear_avoidance`, a strategy gets a free 0.5 added to its composite score for any bear-free window. This biases validation toward time windows without bears, and inflates scores for strategies evaluated on benign market periods.
**Financial impact:** A strategy that scores composite 0.8 might actually be 0.3 bull capture + 0.5 free bear avoidance. In live trading during a real bear market, the strategy's actual bear avoidance is untested. The score creates false confidence.
**Proposed fix:** When no bears are detected, set bear_avoidance to 0.5 (neutral) rather than 1.0 (perfect). Or require at least 1 bear period per validation window for the regime score to be considered valid. Estimated: 3 LOC.
**If not fixed:** Regime scores are inflated for benign market windows, biasing the optimizer toward strategies that happened to be tested in bull-only periods.

---

## What I Investigated and Ruled Out

1. **EMA seed method**: Both Python engines (v3 and v4) seed EMA with SMA of first `length` bars, matching Pine Script's ta.ema(). Ruled out as a parity source.
2. **ATR calculation**: Both engines use RMA (Wilder's smoothing) with alpha=1/period, matching Pine's ta.atr(). Ruled out.
3. **Commission handling**: Both Python and Pine use 0% commission. No discrepancy.
4. **Cooldown logic in v3**: The v3 backtest_engine.py uses `(i - last_sell_bar) <= sell_cooldown_bars`, which matches Pine's `(bar_index - lastSellBar) > sellCooldownBars`. Ruled out for v3 (but found issue in v4, see Finding 11).
5. **Spike state corruption**: spike_state.py uses atomic write (tempfile + os.replace), which is crash-safe on POSIX. No corruption risk found.
6. **Date timezone issues**: data.py normalizes dates with `dt.tz_localize(None)` and the CSV has no timezone info. Both sources are tz-naive. Ruled out.
7. **Floating point precision in equity tracking**: Both engines use float64 throughout. No precision issues found for the scale of values involved ($1K growing to $200K+).

## Coverage Gaps

1. **Pine Script execution model**: I did not run the Pine Script in TradingView to independently verify the parity check results. The 3.5% CAGR gap could be larger or smaller in current TradingView.
2. **Full spike_auto.py analysis**: Read first 300 lines but the file is 601 lines. The remaining 300 lines contain the main evolutionary loop, which may have additional issues.
3. **run_optimization.py grid/bootstrap commands**: Only read the first 300 lines. Grid search and bootstrap commands were not fully analyzed.
4. **Pine Script v6 reference docs**: Not read (28 files, ~140K tokens). Relied on inline comments for Pine behavior assumptions.
5. **Composite Oscillator 1.3**: Not analyzed in depth — it is a display indicator, not a trading signal, so data integrity impact is low.
6. **Historical archive strategies (14 files)**: Not read — they are frozen and not used by the optimizer.
