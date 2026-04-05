# Debate: Dual Engine Schism Resolution

**Date**: 2026-04-03
**Claim**: "The dual engine schism should be resolved by consolidating into strategy_engine.py as the survivor, porting regime scoring and validation infrastructure from backtest_engine.py, and deprecating backtest_engine.py."

**Defender**: Architecture lens (argues strategy_engine.py should survive)
**Attacker**: Data-Integrity lens (argues backtest_engine.py should survive)

---

## ROUND 1 -- Opening Arguments

### Defender (Architecture) -- Opening

The codebase has a clear evolutionary direction, and strategy_engine.py is on the forward path. The evidence is structural:

**1. strategy_engine.py is the multi-strategy future.** It powers `evolve.py`, the multi-strategy evolutionary optimizer, and `strategies.py`, the strategy library with 7 registered strategies. Its design separates the WHAT (strategy logic as pluggable functions returning signal arrays) from the HOW (position management, equity tracking, metrics). This is the correct abstraction for a system that tests multiple strategies. backtest_engine.py hardcodes Montauk 8.2.1 logic -- its `run_backtest()` function is a 380-line monolith that bakes one specific strategy's entry/exit conditions directly into the engine loop (lines 589-972).

**2. The Indicators class is a genuine architectural advantage.** strategy_engine.py's `Indicators` class (lines 130-428) provides 40+ cached indicator methods -- EMA, SMA, TEMA, ATR, RSI, MACD, Stochastic, ADX/DMI, CCI, Williams %R, MFI, OBV, VWAP, Keltner Channels, Donchian, Parabolic SAR, Ichimoku, Bollinger Bands, and crossover/crossunder helpers. The cache key uses `(indicator_name, *params)` tuples, meaning the same EMA(15) computed for strategy A is reused by strategy B at zero cost. backtest_engine.py recomputes indicators from scratch for every `run_backtest()` call -- there is no caching, no sharing.

**3. The dependency graph points forward.** `evolve.py` imports from strategy_engine. `strategies.py` imports from strategy_engine. These are the growth-path files. The files importing from backtest_engine (`validation.py`, `parity_check.py`, `run_optimization.py`, `generate_pine.py`, `spike_auto.py`) are either legacy tools or validation infrastructure that can be ported.

**4. The consolidation path is well-defined.** What backtest_engine has that strategy_engine lacks:
- `StrategyParams` dataclass (117 lines) -- portable, just a dataclass
- Regime scoring infrastructure (`RegimeScore`, `Regime`, `detect_bear_regimes`, `detect_bull_regimes`, `score_regime_capture` -- ~180 lines) -- pure functions operating on trade lists and price arrays, no dependency on the engine loop
- `BacktestResult` with `regime_score` field and richer metrics (`worst_10_bar_loss_pct`, `false_signal_rate_pct`, `bah_return_pct`)

None of these are entangled with the bar-by-bar simulation loop. They are data classes and scoring functions that operate on the *output* of a backtest, not on its internals. Porting them is a copy-paste operation followed by import rewiring.

---

### Attacker (Data-Integrity) -- Opening

The claim sounds architecturally clean, but it ignores the single most important property this system has: **validated parity with TradingView**. That property lives in backtest_engine.py and nowhere else.

**1. backtest_engine.py is the only engine validated against ground truth.** `parity_check.py` (lines 27-97) contains hard reference data from TradingView for three configurations: 8.2.1 defaults, 8.3-conservative, and 9.0-candidate. It compares Python CAGR, trade count, win rate, average bars held, wins/losses, and average win/loss percentages against TV values. This is not theoretical -- these numbers have been verified. strategy_engine.py has no parity check. Its `backtest()` function has never been compared against TradingView output.

**2. backtest_engine.py faithfully replicates Pine Script 8.2.1 execution semantics.** Its exit processing (lines 806-839) checks exits in exact priority order matching the Pine Script: EMA Cross > ATR Shock > Quick EMA > Trail Stop > TEMA Slope > Vol Spike. The `barssince(crossunder)` logic for EMA cross exit (lines 727-756) is a non-trivial reproduction of Pine Script behavior -- it scans a confirmation window and requires `allBelow` to be true. strategy_engine.py's `backtest()` function (lines 495-624) processes exits with a single boolean `exits[i]` array -- it has no concept of exit priority. If multiple exit conditions fire on the same bar, the label comes from whichever strategy function happened to set `exit_labels[i]` last. This is a semantic difference that would surface as parity failures.

**3. Regime scoring is the Charter's primary optimization target.** The CLAUDE.md states: "Primary optimization target: Regime Score." `RegimeScore` is computed inside `run_backtest()` at line 936, using trade objects that include `entry_bar` and `exit_bar` fields. strategy_engine.py's `BacktestResult` (lines 477-492) does not have a `regime_score` field. Its `Trade` dataclass has the same bar fields, but the scoring infrastructure does not exist. The claim says "port it" -- but the scoring depends on a specific trade format and the full equity curve. Any subtle difference in how trades are recorded (entry timing, exit timing, open-position handling) would silently corrupt regime scores.

**4. validation.py depends on backtest_engine's specific interface.** It imports `StrategyParams`, `BacktestResult`, and `run_backtest`. It calls `run_backtest(df, params)` with a StrategyParams object and reads `result.regime_score.composite`, `result.mar_ratio`, `result.cagr_pct`, `result.max_drawdown_pct`, `result.num_trades`. The walk-forward framework and parameter stability checker depend on these exact interfaces. A port would require rewriting validation.py's entire calling convention -- it cannot simply swap imports.

**5. "Non-trivial porting risk" is not hypothetical.** backtest_engine.py has 17 parameter groups (lines 32-117) controlling features like asymmetric ATR exit, ADX trend strength filter, ROC momentum filter, bear depth guard, and volume spike exit. strategy_engine.py's `backtest()` function accepts none of these. To match backtest_engine's fidelity, you would need to either (a) port all 17 parameter groups into strategy_engine's backtest loop, fundamentally changing its clean separation of concerns, or (b) accept that the "consolidated" engine would be less capable than the one it replaced.

---

## ROUND 2 -- Rebuttals

### Defender (Architecture) -- Rebuttal

The Attacker conflates "validated" with "irreplaceable." Let me address each point:

**On parity validation**: The parity data in `parity_check.py` is a set of reference numbers, not a property of the engine itself. Those reference values (TV CAGR=37.73%, 19 trades, 57.89% win rate for 8.2.1) can be used to validate *any* engine. After consolidation, you run parity_check against the consolidated engine. If the numbers match, you have the same guarantee. If they don't, you fix the port. The parity check is the *test*, not the *code under test*.

**On exit priority**: This is a legitimate concern -- but it's a concern about the *strategy implementation*, not the engine. In the strategy_engine architecture, exit priority is the strategy function's responsibility. The `montauk_821()` function in `strategies.py` already handles its own exit priority via `continue` statements (lines 58, 70, 76). The engine doesn't need to know about exit priority -- the strategy function fires the correct exit on each bar. If a more faithful 8.2.1 replica is needed, the strategy function can be refined. The architecture is correct; only the strategy logic needs tuning.

**On regime scoring portability**: The Attacker claims scoring "depends on a specific trade format" -- but both engines use an identical `Trade` dataclass with the same fields (`entry_bar`, `exit_bar`, `entry_date`, `exit_date`, `entry_price`, `exit_price`, `pnl_pct`, `bars_held`). The `score_regime_capture()` function only reads `entry_bar` and `exit_bar` from trades to build the `in_market` boolean array. It does not read any engine-specific state. This is a pure function: `(trades, close, dates) -> RegimeScore`. It will work identically with trades from either engine.

**On validation.py rewriting**: The Attacker overstates the difficulty. validation.py's core logic is: run backtest on a DataFrame, read regime_score from result. The calling convention change is: `run_backtest(df, params)` becomes something like `backtest(df, entries, exits, labels)` where entries/exits come from running the 8.2.1 strategy function first. This is a 10-line adapter function, not a rewrite. Or -- even simpler -- `StrategyParams.from_dict()` and a thin wrapper that calls the strategy function and then `backtest()` can be added to the consolidated engine, preserving the exact same calling convention.

**On the 17 parameter groups**: This actually *supports* consolidation. Those 17 parameter groups are 8.2.1-specific entry/exit filters. In the strategy_engine architecture, they belong *inside the strategy function*, not in the engine. The engine should not know about "asymmetric ATR exit" or "bear depth guard" -- those are strategy decisions. The current backtest_engine violates separation of concerns by mixing strategy logic with engine mechanics.

**The real risk of NOT consolidating**: The codebase currently has two divergent engines computing the same indicators with different code, producing results in different formats, used by different tools. Every new feature (new indicator, new metric, new exit type) must be implemented twice or the engines drift further apart. This is already happening -- strategy_engine has 40+ indicators; backtest_engine has 7. The longer this persists, the harder the eventual merge becomes.

---

### Attacker (Data-Integrity) -- Rebuttal

The Defender's rebuttals are theoretically sound but practically dangerous. Let me explain why.

**On "parity check is the test, not the code"**: Correct in principle. But the Defender glosses over what happens when the test *fails*. The current parity_check uses tolerance bands (trade count +/-2, CAGR +/-10%, etc.) because exact match is impossible due to EMA seeding, warmup handling, and fill timing differences. After a port, any parity failure could be (a) a port bug, (b) an intentional architectural difference, or (c) an inherited difference from strategy_engine's different execution model. Debugging which one is extremely time-consuming. backtest_engine already went through this debugging cycle -- the comments in its code (lines 651-652: "process_orders_on_close=true") document the specific TradingView execution model decisions that produced parity. strategy_engine has none of these annotations because it was never validated.

**On "exit priority is the strategy function's responsibility"**: The Defender points to `montauk_821()` in strategies.py using `continue` statements for exit priority. But look more carefully. In strategies.py lines 58-76, the exit priority is: ATR Shock > Quick EMA > EMA Cross. In backtest_engine.py lines 806-819, the exit priority is: EMA Cross > ATR Shock > Quick EMA > Trail Stop > TEMA Slope > Vol Spike. **These are different orderings.** The strategies.py implementation gets the priority wrong relative to the Pine Script 8.2.1 source. This is exactly the kind of subtle bug that consolidation would bake in permanently. The "correct" version lives in backtest_engine.py because that's the one that was validated against TradingView.

**On "Trade dataclass is identical"**: Formally true. But `score_regime_capture()` builds an `in_market` boolean array from `entry_bar:exit_bar` ranges. If the two engines disagree on *when* an entry or exit occurs by even 1 bar (due to different warmup handling, different fill timing, or the execution delay issue), the `in_market` array will differ on every trade boundary. Over 19 trades across 16 years of data, these 1-bar differences accumulate. Regime scoring is sensitive to this because bear periods are short (often 20-80 bars), so a 1-bar shift at a regime boundary can flip a bar from "avoided" to "exposed" and change the composite score.

**On the "10-line adapter"**: This minimizes the real work. validation.py's `check_param_stability()` perturbs individual parameters of `StrategyParams` and re-runs backtests. In the strategy_engine world, there is no `StrategyParams` -- strategies use raw dicts. The adapter would need to: (1) maintain the StrategyParams dataclass or its equivalent, (2) map dict keys to strategy function parameters, (3) handle the 17 optional feature flags that strategy_engine's backtest function knows nothing about. The "thin wrapper" grows until it is backtest_engine.py again.

**The actual safe path**: Keep both engines. They serve different purposes. backtest_engine.py is the *validated reference implementation* of 8.2.1 -- use it for parity checking, validation, and parameter optimization of the production strategy. strategy_engine.py is the *exploration engine* -- use it for multi-strategy evolution and new strategy development. When evolve.py finds a winner, validate it through backtest_engine.py before promoting it. This dual-engine architecture is not a bug -- it's a feature. The reference engine guards data integrity while the exploration engine enables innovation.

---

## ROUND 3 -- Closing Arguments

### Defender (Architecture) -- Closing

The Attacker's final proposal -- "keep both engines forever" -- is the worst possible outcome. It institutionalizes technical debt and guarantees continued divergence.

**The exit priority bug proves my point.** The Attacker found that `montauk_821()` in strategies.py has the wrong exit priority relative to Pine Script 8.2.1. This is not an argument for keeping two engines -- it's an argument for *fixing the strategy function and validating it*. The correct response to finding a bug in strategies.py is to fix strategies.py, not to abandon the architecture that strategies.py implements. After the fix, you run parity_check. If it passes, you have a validated multi-strategy engine. If it fails, you fix more. This is normal software development.

**The "keep both" proposal doubles every future cost.** New indicator? Implement twice. New metric? Implement twice. New exit type? Implement twice. Bug fix? Fix twice. And inevitably, one copy drifts. The Attacker's own evidence shows this is already happening -- the indicator libraries have diverged (40+ vs 7), the exit priority ordering has diverged, the BacktestResult schemas have diverged.

**The consolidation plan, concretely:**
1. Port `StrategyParams`, `RegimeScore`, `Regime`, regime detection functions, and `score_regime_capture()` into strategy_engine.py. These are pure data classes and pure functions -- zero entanglement with the engine loop.
2. Fix `montauk_821()` in strategies.py to match Pine Script 8.2.1 exit priority exactly.
3. Add `regime_score` field to strategy_engine.py's `BacktestResult`. Call `score_regime_capture()` after each backtest.
4. Add `worst_10_bar_loss_pct`, `false_signal_rate_pct`, and `bah_return_pct` to strategy_engine.py's metrics.
5. Write a `run_backtest_compat(df, params)` wrapper that takes `StrategyParams`, calls the appropriate strategy function, calls `backtest()`, and returns the enriched result. validation.py and parity_check.py switch to this wrapper.
6. Run parity_check. Iterate until it passes.
7. Deprecate backtest_engine.py. Keep it in git history.

This is 2-3 days of focused work. The payoff is permanent: one engine, one indicator library, one trade format, one set of metrics, one maintenance burden.

---

### Attacker (Data-Integrity) -- Closing

The Defender's 7-step plan sounds clean on paper. I want to be precise about the risks, because this is a trading system where silent bugs lose money.

**Risk 1: Parity regression.** The Defender says "run parity_check, iterate until it passes." But parity_check uses tolerance bands, not exact match. A port could introduce a systematic 1-bar timing shift that stays within tolerance for trade count and CAGR but silently corrupts regime scoring. Regime score has no TradingView reference to validate against -- there is no "parity" for it. The only guarantee is that the *same engine* that was validated for trades also computes regime scores.

**Risk 2: The warmup difference.** backtest_engine.py computes warmup dynamically based on which indicators are enabled (line 647-649). strategy_engine.py has no warmup concept -- the first bar where entries[i] is True starts trading. This means strategy_engine may take trades during the warmup period that backtest_engine would skip. These ghost trades would affect regime scoring.

**Risk 3: The 17 parameter groups.** The Defender says they "belong inside the strategy function." But some of them interact with the engine loop. Bear depth guard (lines 711-718) reads the equity curve during simulation to block entries when equity is below its rolling peak. Volume spike exit (lines 797-801) checks volume against an EMA computed during pre-processing. These are not pure entry/exit signals -- they are equity-aware and state-aware decisions that require access to the engine's internal state during simulation. Moving them into a strategy function that only sees `(Indicators, params)` would require passing the equity curve and position state into the strategy function, breaking its clean interface.

**My revised position**: I concede that long-term consolidation is correct. Two engines is unsustainable. But the Defender's timeline ("2-3 days") is dangerously optimistic given the risks above. The safe path:

1. **Phase 0 (now)**: Fix the exit priority bug in strategies.py. Run parity against backtest_engine results (not TV -- engine-to-engine comparison) to quantify the delta.
2. **Phase 1**: Port regime scoring, StrategyParams, and enriched metrics to strategy_engine.py. These are safe -- pure functions and data classes.
3. **Phase 2**: Add a compatibility wrapper `run_backtest_compat()`. Validate it passes parity_check within existing tolerances.
4. **Phase 3**: Address the equity-aware exits (bear depth guard, volume spike) by extending strategy_engine's `backtest()` to accept optional callbacks for mid-loop decisions. This preserves the clean interface while enabling stateful exits.
5. **Phase 4**: Only after Phases 1-3 pass parity, switch validation.py and run_optimization.py to the consolidated engine.
6. **Phase 5**: Deprecate backtest_engine.py.

This is closer to 1-2 weeks than 2-3 days, but it preserves data integrity at every step.

---

## JUDGMENT

### Verdict: CLAIM UPHELD -- with significant caveats on execution timeline and sequencing

The claim is directionally correct: strategy_engine.py should be the survivor. The structural arguments are compelling:

- **strategy_engine.py has the right architecture.** Separating strategy logic from engine mechanics is fundamentally sound. backtest_engine.py's monolithic design cannot scale to multi-strategy testing.
- **The Indicators class with caching is a genuine advantage** that would be lost if backtest_engine.py survived.
- **The dependency graph points forward.** evolve.py and strategies.py represent the project's growth direction.

However, the Attacker raised three concerns that the consolidation plan must address before any migration:

**Critical Finding 1 -- Exit Priority Bug.** The `montauk_821()` strategy function in strategies.py processes exits in the wrong order (ATR > Quick EMA > EMA Cross) compared to the validated Pine Script 8.2.1 (EMA Cross > ATR > Quick EMA > Trail > TEMA > Vol Spike). This must be fixed and parity-validated before any consolidation begins. This is not optional.

**Critical Finding 2 -- Equity-Aware Exits.** Bear depth guard and volume spike exit require access to the equity curve during simulation. strategy_engine.py's current `backtest()` function does not expose internal state to strategy functions. The engine will need to be extended (callbacks, context objects, or post-loop re-evaluation) to support these features. The Defender's "just move it to the strategy function" dismissal is incorrect for these specific exits.

**Critical Finding 3 -- Warmup Divergence.** backtest_engine.py computes dynamic warmup; strategy_engine.py does not. This must be reconciled during porting to prevent ghost trades in the warmup period from corrupting metrics.

### Recommended Execution Plan

The Attacker's phased approach (Phases 0-5) is the correct execution plan. The Defender's 2-3 day estimate is unrealistic given the three critical findings above. Budget 1-2 weeks with parity validation gates between each phase.

| Phase | Work | Gate |
|-------|------|------|
| 0 | Fix exit priority in strategies.py montauk_821() | Engine-to-engine parity within 5% |
| 1 | Port RegimeScore, StrategyParams, enriched metrics to strategy_engine.py | Unit tests pass |
| 2 | Add `run_backtest_compat()` wrapper | parity_check.py passes against TV reference |
| 3 | Extend backtest() for equity-aware exits (callbacks/context) | Bear guard and vol spike match backtest_engine behavior |
| 4 | Migrate validation.py, run_optimization.py, spike_auto.py | Walk-forward validation produces same pass/fail as before |
| 5 | Deprecate backtest_engine.py | All importers migrated, backtest_engine.py removed |

### What This Means for the Charter

The Charter's "Primary optimization target: Regime Score" is safe under consolidation because `score_regime_capture()` is a pure function of `(trades, close, dates)` with no engine coupling. The critical dependency is that trades must have accurate `entry_bar` and `exit_bar` values, which both engines already produce from identical `Trade` dataclasses. The risk is not in the scoring function itself but in the engine producing different trade timing -- hence the mandatory parity gates.

### Bottom Line

**Consolidate into strategy_engine.py. But do it in phases with parity gates, not as a big-bang rewrite.** Fix the exit priority bug first -- it's a live correctness issue regardless of consolidation. Then port the scoring infrastructure. Then validate. Then migrate consumers. Then deprecate. The Attacker's caution on sequencing is well-founded; the Defender's structural vision is correct. Both perspectives are necessary for a safe outcome.
