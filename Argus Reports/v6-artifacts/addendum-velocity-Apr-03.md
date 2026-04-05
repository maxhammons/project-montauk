# Velocity & Friction Addendum — Cross-Pollination — Apr 03

**Specialist**: Velocity & Friction
**Phase**: Cross-pollination addendum (post-digest)
**Digests received from**: Architecture, Risk, Data-Integrity, Vision-Drift

---

## Part 1: Answering Open Questions

### Q1: Will an 8-hour run change rankings?

**Answer: Almost certainly yes for parameter quality. Probably no for strategy-level rankings. Net: rankings stay, numbers shift.**

The 36-second run executed 1,330 evaluations across 7 strategies (~190 per strategy). RSI Regime won with fitness 2.18 vs the #2 breakout at 0.50 — a 4.3x gap. An 8-hour run at the observed throughput of ~37,000 evals/hour (1,330 / 0.036h) would produce roughly 296,000 evaluations — a 222x increase in search density.

What will change:
- **RSI Regime parameters will improve.** The current winner samples 2.7% of its 28,000-combination grid. An 8-hour run covers roughly 60-70% through evolutionary search. The 75.1% max drawdown is the obvious pressure point — better parameter combinations almost certainly exist that trade drawdown for slightly lower returns. I estimate the 8-hour run finds RSI Regime configs with 55-65% max drawdown and fitness in the 1.8-2.5 range.
- **montauk_821 parameters will improve.** Its current best (fitness 0.46) is artificially low because of the crippled v4 implementation (Data-Integrity Finding 1 confirms 6 missing features). But even within the crippled version, more search time means better parameters. Expect 0.5-0.7 fitness.
- **tema_momentum may finally evaluate.** It scored 0.0 with null metrics in the 36-second run — it was never successfully tested. 8 hours gives it thousands of attempts.

What will NOT change:
- **RSI Regime remains #1.** The 4.3x gap to #2 is too large to close through parameter tuning alone. Even if breakout doubles its fitness, RSI Regime would need to halve (which requires a fundamental flaw, not just suboptimal parameters).
- **Strategy-level ordering is likely stable.** The gap between tiers (RSI at 2.18, breakout cluster at 0.5, tail strategies below 0.1) reflects architectural differences, not parameter luck.

**Critical caveat from Risk/Data-Integrity**: The rankings are meaningless until the montauk_821 baseline is fixed. Risk R-02 confirms the v4 montauk_821 uses EMA(30) for cross exit instead of EMA(500). Data-Integrity Finding 1 confirms 6 missing features. RSI Regime's "4.7x better" claim is against a strawman. An 8-hour run amplifies the wrong answer faster — it does not fix the comparison.

**Velocity recommendation**: Do NOT run the 8-hour overnight until the montauk_821 baseline in strategies.py is corrected. An 8-hour run on the current code would produce high-confidence wrong rankings, which is worse than low-confidence wrong rankings.

---

### Q2: Is the 4x rewrite pattern convergence or indecision?

**Answer: Convergence. Each rewrite contracted the problem scope. The pattern is not oscillation — it is progressive focusing.**

Evidence of convergence (not oscillation):
- **v1** (Apr 1): "Can Python backtest 8.2.1?" — proved the concept, 1,700 lines, broad scope
- **v2** (Apr 2 AM): "What should we optimize FOR?" — rewrote the fitness target from MAR to Regime Score, ~500 lines changed. The problem narrowed from "backtest anything" to "score strategies correctly."
- **v3** (Apr 2 PM): "How do we prevent overfitting?" — added bootstrap validation, plateau analysis. The problem narrowed further to "score strategies correctly and trust the scores."
- **v4** (Apr 3): "What if 8.2.1 is the wrong architecture entirely?" — expanded from parameter tuning to strategy architecture search. This was the breakthrough — the question changed from "how to tune 8.2.1" to "what beats buy-and-hold."

The rewrite sequence shows progressive elimination:
1. v1 eliminated the question "can we replicate TV in Python?" (yes)
2. v2 eliminated "is MAR the right target?" (no — regime capture matters more)
3. v3 eliminated "are our results trustworthy?" (partially — bootstrap helps)
4. v4 eliminated "is 8.2.1 the right architecture?" (probably not — RSI Regime is fundamentally different)

Evidence against indecision:
- Each version discarded scaffolding but retained core infrastructure. `data.py` (v1) is still in use. `validation.py` (v2) is still in use (though disconnected from v4). `Indicators` caching pattern (introduced v4) is clearly superior to v1-v3's standalone functions.
- The spike.md skill definition shrank from 241 lines (v1) to 137 lines (v4). Convergence produces smaller specs, not larger ones.
- No version revisited a previously-rejected approach. v1 did not return in v3. MAR did not return in v4. This is forward movement.

**However**: The 4x rewrite pattern has a velocity cost that compounds. My Finding 3 documented 1,522 lines thrown away (60% throwaway rate). Cross-pollination with Architecture confirms the debris is not just wasted effort — it is actively harmful. The dead v3 code (spike_auto.py) has a different fitness function that could confuse future sessions.

**Velocity prediction**: v5 is likely if the montauk_821 baseline fix (from Risk/Data-Integrity) changes the rankings significantly. If a fixed montauk_821 narrows the gap to RSI Regime from 4.7x to 2x, the developer may decide to explore hybrid strategies — and that would be v5. If the gap remains >3x, v4 is the terminal architecture and the rewrites are done.

---

## Part 2: Answering Other Specialists' Open Questions (Velocity Perspective)

### ADX implementations differ materially?

**Yes, materially different.** I verified both implementations:

- `backtest_engine.py` (lines 196-235): Uses running-sum Wilder's smoothing. Seeds `sm_tr[period]` with `nansum(tr_arr[1:period+1])`, then smooths forward with `val = prev - prev/period + new`. ADX is seeded at `period * 2` with `nanmean(dx[period:2*period+1])`, then smoothed with `alpha = 1/period`.
- `strategy_engine.py` (lines 434-456): Uses `_rma()` which seeds with `mean(series[:length])` (the SMA seed), then applies exponential smoothing. ADX is computed as `_rma(nan_to_num(dx, nan=0.0), period)` — note the `nan_to_num` which converts NaN DX values to 0 before smoothing, which the backtest_engine version does not do.

The material differences:
1. **Seed window**: backtest_engine sums `tr_arr[1:period+1]` (excludes index 0). strategy_engine's `_rma` uses `mean(series[:length])` (includes index 0, which is `hi[0]-lo[0]` for TR). Different seed = different warmup trajectory.
2. **NaN handling**: strategy_engine converts NaN DX to 0.0 before RMA smoothing. backtest_engine's Wilder's loop naturally propagates NaN (skips via `nanmean`). Zero and NaN produce different smoothed outputs.
3. **ADX double-smoothing**: backtest_engine explicitly double-smooths (DI -> DX -> ADX with separate Wilder's pass). strategy_engine applies `_rma` once to DX — same intent but the seed initialization differs.

**Velocity impact**: Any strategy using ADX (currently none of the top 3, but `ind.adx()` is available) would get different values from each engine. This reinforces the "merge engines" recommendation — it is not just code duplication, it is correctness divergence.

### Does process_orders_on_close match Python?

**Mostly yes, with one subtle gap.** Both Python engines process exits before entries on the same bar, and both fill at `cl[i]` (the close price). This matches TradingView's `process_orders_on_close=true` behavior where signals evaluated on the current bar fill at the current bar's close.

The gap: TradingView with `process_orders_on_close=true` evaluates the strategy on the current bar's data and fills at that bar's close. But the Python engines compute signals across the full dataset first (numpy vectorized in strategy functions), then simulate bar-by-bar. This means Python strategies can "see" future bars during signal generation if they use backward-looking functions incorrectly. The strategy functions in `strategies.py` appear to use only `[i]` and `[i-N]` indexing (no forward-looking), so this is not currently a problem — but it is an architectural difference that could bite if a new strategy function accidentally uses `[i+1]`.

### TECL leverage decay modeled?

**No, not modeled anywhere.** Grep for "leverage", "decay", "3x" in scripts/ returns zero relevant hits (one mention in signal_queue.json is a description string, not code). TECL's daily 3x leverage reset creates path-dependent returns that diverge from 3x the underlying over multi-month holds. Since the strategies hold for 50-170 bars (3-10 months), leverage decay is a real factor that is not captured. However — the Python backtests use actual TECL historical prices (which already reflect leverage decay), so the backtest results implicitly include its effect. The risk is that future regime periods may have different volatility patterns producing different decay profiles than historical. This is a model risk, not a code bug.

### Is RSI paradigm shift deliberate or unconscious?

**From a velocity lens: deliberate.** The spike.md v4 explicitly states "Use ANY combination. There are no restrictions on what indicators or logic you can use." This was a conscious decision to remove the Charter's EMA-only constraint. The RSI Regime strategy was not an accident — the optimizer was told to explore freely. Whether the Charter violation was deliberate is Vision-Drift's domain, but the code architecture was intentionally designed to discover non-EMA strategies.

### Should Charter update or code rein in?

**Velocity says: update the Charter.** Reining in the code means deleting the v4 architecture and reverting to v3 single-strategy optimization. That discards 3,500 lines and the RSI Regime discovery. The velocity cost of reverting is higher than the velocity cost of updating a document. The Charter is 1 file; the code is 12 files. Update the 1.

---

## Part 3: Revised Scores

After cross-pollination, I am revising severity/priority scores for my original findings based on new information from other specialists.

### Finding 1: Duplicate Backtesting Engines
- **Original**: Maintenance risk, effort ~2 hours
- **Revised**: **CRITICAL** (upgraded). Architecture, Risk, and Data-Integrity all independently found this. The divergence is not theoretical — ADX implementations differ materially (confirmed above), EMA cross exit uses wrong EMA (Risk R-02), and 6 features are missing from v4 montauk_821 (Data-Integrity F1). This is not just duplication — it is active corruption of optimization results.
- **Revised effort**: 4-6 hours (Architecture's estimate is more realistic — the merge must preserve both engines' behavior)

### Finding 3: 4x Rewrite Pattern
- **Original**: 75% confidence, churn / velocity waste
- **Revised**: 70% confidence (downgraded). Cross-pollination confirms this is convergence, not waste. The throwaway cost is real but is the normal cost of exploration in a 3-day-old project. The dead code is the bigger problem (Finding 2), not the rewrite pattern itself.

### Finding 5: Python-TradingView Parity Gap
- **Original**: 90% confidence, validation gap
- **Revised**: **CRITICAL** (upgraded). Data-Integrity F5 confirms parity tolerances are 10-30%, masking real errors. Risk R-02 confirms montauk_821 uses the wrong EMA (30 vs 500), meaning the existing parity data is against a different strategy than production. The parity gap is worse than I reported — it is not just "growing, not shrinking" — it is structurally broken for all v4 strategies.

### Finding 8: 36-second optimizer run
- **Original**: 85% confidence, premature convergence risk
- **Revised**: Confidence unchanged, but priority **downgraded**. Running longer is pointless until the baseline is fixed (per Q1 above). The 36-second run is fine as a proof-of-concept. The correct next step is fix montauk_821, fix the parity checker, THEN run 8 hours.

### Finding 10: Fitness function changed 3 times
- **Original**: 90% confidence, strategy stability risk
- **Revised**: Confidence unchanged, severity **upgraded to HIGH**. Vision-Drift F3 confirms the metrics were silently replaced without Charter update. Risk R-11 confirms the two active fitness functions produce contradictory "best" results. The velocity impact is that every previous session's results are non-comparable with current results — there is no longitudinal performance tracking.

### Finding 11: Production strategy unchanged 31 days
- **Original**: 95% confidence, motion vs progress observation
- **Revised**: Reframed. Vision-Drift F1 (identity metamorphosis) provides the context I was missing. The 31-day freeze is not just "no production change" — it is evidence that the project's identity shifted from "iterate on 8.2.1" to "build a strategy discovery platform." The production strategy was not supposed to change during platform construction. The velocity concern is not "why hasn't it changed?" but "when will the platform produce a deployable candidate?" Answer: after montauk_821 is fixed, parity is verified, and a full 8-hour run completes. Estimated: 2-3 sessions (6-12 hours of active work).

---

## Part 4: Cross-Lens Findings

These findings emerge from combining my velocity data with insights from other specialists. No single lens would have found these.

### Cross-1: The "Fix, Then Run" Sequencing Problem

**Lenses**: Velocity + Risk + Data-Integrity

The natural developer instinct is "run the 8-hour optimizer overnight, fix bugs tomorrow." But the cross-lens analysis reveals this is backwards:

1. montauk_821 baseline is crippled (Risk R-02, Data-Integrity F1) — wrong EMA, 6 missing features
2. RSI Regime's superiority claim rests on beating this strawman (my Finding 5)
3. An 8-hour run on current code produces 296,000 evaluations of wrong comparisons (my Q1 analysis)
4. Every future session will reference these wrong results (my Finding 10 — fitness changes invalidate history)

**The correct sequence is**: (1) fix montauk_821 in strategies.py, (2) verify parity with backtest_engine.py's version, (3) run 8-hour overnight, (4) validate RSI Regime results against TradingView. Each step gates the next.

**Velocity cost of wrong sequence**: If the 8-hour run happens first, and montauk_821 fix reveals RSI Regime's advantage was smaller than believed, the 8-hour run must be re-run — 16 hours total instead of 8. This is the single highest-leverage sequencing decision in the project right now.

### Cross-2: Dead Code Is Not Just Token Waste — It Is a Trust Vector

**Lenses**: Velocity + Architecture + Vision-Drift

My Finding 2 framed dead code as "confusion for Claude" (token waste, wrong suggestions). Cross-pollination reveals a deeper problem:

- Architecture confirms spike_auto.py has a different fitness function (regime_bonus vs freq_penalty)
- Vision-Drift confirms the Charter still describes the pre-v4 world
- Risk confirms spike-progress.json has a separate "best-ever" (fitness 0.6861) from a different scoring system

The dead code is not just confusing — it is an alternative reality that competes with the current one. If anyone (human or AI) reads spike-progress.json and sees "best_ever_score: 0.6861," they might conclude the project is less advanced than it is (the real best-ever is 2.18). If they read spike_auto.py's fitness function, they might believe regime_score is still the primary target (it is not). The dead code actively contradicts the living code.

**Combined recommendation**: Archive dead code AND update CLAUDE.md/Charter in the same commit. Half the fix (archiving without updating docs) leaves the contradiction in the documentation. Half the fix (updating docs without archiving) leaves the contradiction in the code.

### Cross-3: The Validation Disconnect Is the #1 Velocity Blocker

**Lenses**: Velocity + Risk + Data-Integrity + Architecture

Four lenses independently identified that validation.py cannot validate v4 strategies:
- Architecture: "walk-forward framework cannot validate v4 strategies"
- Risk R-08: "Validation.py imports broken for new strategies"
- Data-Integrity F4: "Walk-forward validation cannot validate v4 strategies"
- Velocity (me): "parity_check.py only validates 8.2.1" (Finding 5)

This is the single most impactful blocker to forward velocity. The project cannot:
- Trust RSI Regime's numbers (no walk-forward validation)
- Compare v4 results to TradingView (no parity checking for v4)
- Detect overfitting (Data-Integrity F2: 100% win rate on 10 trades)
- Make a deployment decision (Risk R-07: no automated validation gate)

Every other fix is lower priority. The engine merge (Cross-1), dead code cleanup (Cross-2), Charter update (Vision-Drift), and 8-hour run (my Finding 8) all depend on having a working validation pipeline for v4 strategies.

**Velocity-optimal fix order**:
1. Port validation.py to accept v4 strategy functions (2 hours, unblocks everything)
2. Fix montauk_821 in strategies.py (1 hour, corrects baseline)
3. Archive dead code + update Charter (30 min, eliminates confusion)
4. Run 8-hour optimizer overnight (0 hours active, 8 hours wall clock)
5. Validate top 3 results against TradingView (45 min manual)

Total: ~4 hours of active work, then one overnight run. This is the critical path.

### Cross-4: The Oscillator Is Orphaned but Not Dead

**Lenses**: Velocity + Vision-Drift

Vision-Drift flags the Montauk Composite Oscillator 1.3 as orphaned — it is a Pine Script indicator that was designed to complement 8.2.1's EMA-based entries but has no equivalent in the Python optimization pipeline. From a velocity lens, this is not a current problem (the indicator does not block anything), but it becomes one the moment a strategy is deployed.

If RSI Regime is deployed, the Oscillator needs to be either:
- Updated to show RSI-relevant signals (replacing or supplementing the EMA/TEMA/MACD components)
- Deprecated (the strategy trades on RSI alone, no visual confirmation needed)

This is a downstream velocity cost that should be noted but not actioned until deployment is imminent.

---

## Part 5: Priority-Ordered Action List (Velocity-Optimal)

| Priority | Action | Effort | Unblocks | Source |
|----------|--------|--------|----------|--------|
| 1 | Port validation.py to v4 strategy API | 2h | Trust in all v4 results | Cross-3 |
| 2 | Fix montauk_821 in strategies.py (EMA 500, 6 missing features) | 1-2h | Correct baseline for all comparisons | Risk R-02, DI F1 |
| 3 | Archive dead code (spike_auto, signal_queue, spike_state, run_optimization) | 15min | Cleaner context for AI + human | Cross-2, my F2 |
| 4 | Update Charter v2 + CLAUDE.md | 30min | Aligned documentation | Vision-Drift F4, my F9 |
| 5 | Run 8-hour optimizer overnight | 0h active | Validated strategy rankings | My F8 |
| 6 | Validate top results in TradingView | 45min | Deployment decision | My F5 |
| 7 | Merge backtest engines | 4-6h | Single source of truth | Arch F1, my F1 |
| 8 | Add 3 targeted tests (indicators, trades, parity) | 1h | Regression safety | My F4 |

---

*End of addendum. Total active work on critical path: ~4 hours to unblock the 8-hour run. The project is closer to a deployable result than the finding count suggests — the bugs are concentrated in the validation layer, not the core optimizer.*
