# Architecture Addendum — Cross-Pollination

**Specialist**: Architecture
**Phase**: Cross-pollination (responding to Risk, Data-Integrity, Vision-Drift, Velocity digests)

---

## Part 1: Answering Other Specialists' Open Questions

### RISK OPEN Q: Does process_orders_on_close=true in Pine match Python's fill timing?

**ANSWERED: Yes for backtest_engine.py. Yes for strategy_engine.py. But they match in different ways.**

Both Python engines fill at `cl[i]` (current bar's close) on the same bar that the signal fires. The Pine Script declares `process_orders_on_close=true`, which means TradingView processes orders placed during the bar's calculation at that same bar's close — no next-bar deferral.

However, the docstring at the top of backtest_engine.py is misleading. It says "1-bar execution delay: signals fire on bar i, fills execute on bar i+1's close" — but the actual code at lines 822 and 850 does the opposite: `exit_price = cl[i]` and `entry_price = cl[i]`, both on bar `i`, with explicit comments saying "process_orders_on_close=true: fill immediately at this bar's close." The docstring is stale from an earlier version and contradicts the implementation.

strategy_engine.py's `backtest()` also fills at `cl[i]` on the signal bar (lines 539, 559).

**Verdict**: Fill timing is consistent across both Python engines and matches Pine's `process_orders_on_close=true`. The stale docstring is a minor confusion vector but does not affect correctness.

---

### RISK OPEN Q: Are TECL leverage decay effects modeled in either engine?

**ANSWERED: No. Neither engine models leverage decay. Both treat TECL as a simple price series.**

I searched all Python files for any reference to leverage, decay, 3x modeling, or compounding effects. The only mention is in `signal_queue.json` line 234: "mean reversion risk on leveraged ETF" — a comment, not code.

Both engines take the TECL close price as-is from the CSV/Yahoo data. This is actually correct for backtesting purposes — the historical prices already embed the leverage decay that occurred. You would only need to model decay separately if you were simulating TECL from the underlying index (QQQ or XLK). Since both engines use actual TECL historical prices, leverage decay is implicitly captured.

**However**: The Data-Integrity specialist's concern about the 30% bear threshold being too low for a 3x ETF is valid from an architecture perspective. A 30% drawdown in TECL is a ~10% move in the underlying — barely a correction, not a bear market. The `detect_bear_regimes()` function at backtest_engine.py line 292 uses `bear_threshold=0.30` as default. For a 3x leveraged ETF that routinely draws down 60-80%, this will detect many minor pullbacks as "bear markets," inflating the number of regime periods and diluting the regime score's meaning. This should be at least 50% for TECL.

---

### DATA-INTEGRITY OPEN Q: Does the Pine Script RSI boundary condition (<=) vs Python (<) cause signal divergence?

**ANSWERED: Yes, confirmed divergence.**

Pine Script RSI Regime (line 46): `ta.crossover(rsi, entryRsi)` — Pine's `crossover` fires when the series crosses from `<=` to `>` the threshold. This means the entry fires when `rsi[1] <= entryRsi AND rsi[0] > entryRsi`.

Python RSI Regime (strategies.py line 133): `rsi[i-1] < entry_level and rsi[i] >= entry_level` — Python fires when previous RSI was strictly less than the threshold AND current RSI is greater than or equal.

The divergence: If RSI sits exactly at the threshold (e.g., RSI = 35.0 with entry_rsi = 35), then on the next bar if RSI rises to 36:
- **Pine**: `crossover` does NOT fire because `rsi[1]` was NOT `<= 35` in a way that constitutes a cross (rsi[1] == 35 IS `<=`, so if rsi[0] > 35, crossover DOES fire). Actually wait — Pine's `crossover(a, b)` fires when `a[0] > b AND a[1] <= b`. So `rsi[1]=35 <= 35` is true, `rsi[0]=36 > 35` is true: crossover fires.
- **Python**: `rsi[i-1]=35 < 35` is FALSE. Entry does NOT fire.

So when RSI exactly equals the threshold then rises above: **Pine fires, Python does not.** The Python condition should use `<=` instead of `<` for the previous bar check to match Pine's `crossover` semantics.

Similarly for exits: Pine line 53 uses `rsi >= exitRsi`, Python line 137 uses `rsi[i] >= exit_level` — these match.

**Verdict**: Confirmed signal divergence on the exact-boundary case. The fix is one character: change `<` to `<=` in strategies.py line 133.

---

### DATA-INTEGRITY OPEN Q: Is bear_avoidance=1.0 default inflating regime scores for bear-free windows?

**ANSWERED: Yes, architecturally confirmed.**

backtest_engine.py line 500: `bear_avoidance = float(np.mean(bear_avoidance_scores)) if bear_avoidance_scores else 1.0`. If no bear periods are detected (empty list), bear avoidance defaults to 1.0 (perfect score). The composite at line 501 then becomes `0.5 * bull_capture + 0.5 * 1.0`.

This means any walk-forward window or sub-period that happens to be bear-free gets a free 0.5 added to its regime composite. For a strategy being evaluated on a window like 2012-2018 (which had no 30%+ TECL drawdown), the regime score is artificially high.

However, this only matters if `score_regime_capture()` is called on sub-periods. In the current architecture, `backtest_engine.py` calls it on the full data range. Since `evolve.py` doesn't call `score_regime_capture()` at all (it uses its own fitness function), and `validation.py` (which does walk-forward on sub-windows) can't validate v4 strategies anyway, this bug is dormant — but it will activate the moment the engine merge connects validation.py to v4 strategies.

---

### VISION-DRIFT OPEN Q: Is the RSI Regime paradigm shift deliberate evolution or unconscious drift?

**ANSWERED from architecture evidence: Unconscious drift.**

The structural evidence is unambiguous:
1. The Charter was never updated (Vision-Drift confirms: frozen 31 days)
2. The strategies.py file comment (line 111) says "Leveraged ETFs tend to mean-revert hard — this exploits that" — this is a design rationale for mean-reversion, but no corresponding Charter amendment exists
3. The evolve.py framework treats all strategies equally with no paradigm filter — it simply maximizes `vs_bah * dd_penalty * freq_penalty`. It has no concept of "allowed" vs "disallowed" strategy types.
4. The spike.md skill file describes the v4 workflow without referencing the Charter's constraints

The architecture enabled the drift: by building a framework that accepts any strategy function, the constraint that once existed in the single-strategy engine (only EMA trend parameters can be optimized) was removed. The v4 architecture's open-ended strategy registry is the mechanism that made the paradigm shift possible without any deliberate decision point.

---

### VELOCITY OPEN Q: Is the 4x rewrite pattern a sign of convergence or chronic indecision?

**PARTIAL ANSWER from architecture perspective**: The rewrite pattern (spike_auto.py v1 -> v2 -> v3 -> evolve.py v4) shows clear architectural convergence. Each version solved a real structural problem:

- v1-v3 (spike_auto.py): Monolithic — optimizer, backtester, and strategy logic in one file. Could only test parameter variations of a single strategy.
- v4 (evolve.py + strategy_engine.py + strategies.py): Properly separated concerns — strategy definitions are pluggable, backtester is generic, optimizer is strategy-agnostic.

The architecture got better each time. But the convergence is incomplete — the old engine (backtest_engine.py) wasn't retired, creating the dual-engine problem. The rewrites converged on a better design but didn't clean up after themselves.

---

### VELOCITY OPEN Q: Will a full 8-hour run change the RSI Regime ranking?

**ANSWERED from architecture analysis: Almost certainly yes, but the direction is unpredictable.**

The current rankings are from 19 generations. The evolve.py mutation schedule at line 234-235 uses `getattr(evolve, '_last_improve', {}).get(strat_name, 0)` to detect stagnation — but `_last_improve` is never set anywhere in the code. This means `stag` is always equal to `generation - 0 = generation`, so by generation 30 the mutation rate jumps to 0.30, and by generation 80 it jumps to 0.50. This is the Data-Integrity specialist's "stagnation detection references non-existent attribute" finding, confirmed from architecture review.

The consequence: mutation rate escalates monotonically regardless of actual improvement. After 80 generations (a few minutes), half of all parameters mutate per offspring. This turns the evolutionary search into near-random search, defeating the purpose of selection pressure. A full 8-hour run with this bug would explore the parameter space essentially randomly after the first few minutes, which could find better or worse configurations by chance.

---

## Part 2: Score Revisions to My Own Findings

### Finding 1 (Dual Engines): Confidence RAISED from 95% to 98%

All five other-specialist digests independently identified this as the root cause of multiple problems. Risk calls it "CRITICAL: Dual engine divergence." Data-Integrity confirms "Walk-forward validation disconnected from v4 engine entirely." Vision-Drift notes "Two coexisting engines — validation disconnected from optimizer." Velocity quantifies "~300-400 lines functionally duplicated." The convergence across all lenses confirms this is not a judgment call — it is the project's central structural defect.

### Finding 6 (montauk_821 infidelity): Confidence RAISED from 92% to 95%

Risk digest bullet #2 independently confirmed: "montauk_821 uses 30-bar EMA (ema_m) for cross exit; real 8.2.1 uses 500-bar EMA (ema_long)." The 4.7x improvement claim for RSI Regime is now doubly suspect: weakened baseline (my finding) + overfitted on 10 trades (Risk finding #3) + 36-second run (my finding #8).

### Finding 4 (Charter Violation): Confidence RAISED from 85% to 95%

Vision-Drift's entire lens corroborates this. Their bullet #2 states: "Charter S8 directly violated — RSI Regime IS mean-reversion, explicitly banned." This is not a gray area — the Charter explicitly bans what the optimizer selected as best.

### Finding 8 (Trivially Short Run): Confidence RAISED from 88% to 95%

Velocity independently confirms: "evolve.py ran for only 36 seconds — 2.7% of RSI Regime parameter space explored." Combined with my new finding that the stagnation detection is broken (mutation rate escalates regardless of improvement), even a full 8-hour run may not converge properly without fixing the `_last_improve` bug.

### Finding 7 (Breakout State Bug): No change (80%)

Data-Integrity's bullet #7 ("peak_since_entry bug — state leaks between trades") confirms the same finding. Confidence stays at 80% because the behavioral impact depends on how often the backtester ignores stale entry signals in practice.

---

## Part 3: Cross-Lens Findings

### Cross-Finding A: Architecture x Risk — The Unvalidated Decision Pipeline

**Intersection of**: Architecture Finding 1 (dual engines) + Risk bullets #1, #3, #7

The project's decision-making pipeline is:
1. `evolve.py` discovers "RSI Regime is 4.7x better"
2. Someone hand-writes Pine Script for RSI Regime
3. RSI Regime gets deployed to TradingView

Every link in this chain is broken:
- Link 1: evolve.py uses an unvalidated engine with a weakened 8.2.1 baseline, a broken stagnation detector, and results from a 36-second run
- Link 2: The hand-written Pine Script has boundary condition divergence (`<` vs `<=`) from the Python version
- Link 3: No parity check exists for RSI Regime — parity_check.py only supports 8.2.1 variants

There is no validation gate between "optimizer says it's good" and "real money is at risk." Risk's bullet #7 calls this out: "No deployment guardrails — no max-DD cap, no validation gate before testing/." Architecture confirms this is structural, not a missing check — the infrastructure literally cannot validate v4 strategies because validation.py imports from the wrong engine.

**Severity**: This is the single most dangerous cross-lens finding. A strategy can go from "36-second optimizer run" to "live trading on TradingView" with zero automated validation.

---

### Cross-Finding B: Architecture x Data-Integrity — RSI Calculation Divergence Compounds Through the Dual-Engine Gap

**Intersection of**: Architecture Finding 2 (triple-duplicated indicators) + Data-Integrity bullet #3 (RSI divergence from Pine)

Data-Integrity identified that the Python RSI's `np.diff(series, prepend=series[0])` shifts signals by 1-2 bars versus Pine's RSI. I can now trace the impact through the architecture:

- strategy_engine.py's `_rsi()` (line 90-102) uses `np.diff(series, prepend=series[0])` to compute deltas. The `prepend=series[0]` creates a zero-change first bar, which means the first delta is always 0, and subsequent deltas are shifted by one position relative to Pine's behavior.
- This shifted RSI feeds into `rsi_regime()` in strategies.py, where it's compared against thresholds.
- The shifted signals mean that the Python RSI Regime enters and exits 1 bar late relative to where the Pine Script version would.
- For a strategy with only 10 trades, a 1-bar shift on each entry and exit could change the P&L substantially (TECL moves ~3% per day on average).

The dual-engine gap means this can never be caught by parity_check.py (which uses backtest_engine.py, not strategy_engine.py). Even if someone added RSI Regime to parity_check.py, it would use a different RSI implementation than the one that evolved the winning parameters.

---

### Cross-Finding C: Architecture x Vision-Drift — The Charter Cannot Govern What It Cannot See

**Intersection of**: Architecture Finding 4 (Charter violation) + Vision-Drift bullets #1, #2, #5

The architectural reason the Charter became irrelevant is that the v4 system was designed without any governance interface. Consider:

- backtest_engine.py's `StrategyParams` dataclass is implicitly Charter-scoped — every parameter maps to a documented 8.2.1 feature. The Charter can govern this because the parameter space is fixed.
- evolve.py's strategy registry accepts arbitrary functions with arbitrary parameter dicts. There is no validation that a strategy's logic conforms to any rules. The Framework literally cannot check "does this strategy use oscillators?" because strategy functions are opaque.

The fix is not just updating the Charter — it's adding a governance layer. Each entry in `STRATEGY_REGISTRY` should carry metadata: paradigm tag (trend/mean-reversion/breakout), required validation level (walk-forward/parity/none), and deployment eligibility. The evolve.py optimizer should filter or flag strategies that violate governance rules. Without this, updating the Charter is performative — Claude sessions will still discover and promote strategies that violate it.

---

### Cross-Finding D: Architecture x Velocity — Dead Code Is the Visible Symptom, Missing Cleanup Phase Is the Root Cause

**Intersection of**: Architecture Finding 3 (1,028 lines dead code) + Velocity bullets #2, #3

Velocity identifies 39% dead code (1,819 lines — higher than my count because they include additional files). The architectural root cause is that each rewrite added a new system without removing the old one. The v4 architecture (evolve.py + strategy_engine.py + strategies.py) was built alongside v3 (backtest_engine.py + spike_auto.py + run_optimization.py) rather than replacing it.

This is not just a cleanup problem — it's an architectural pattern. The dual-engine situation exists because the developer built a new engine instead of refactoring the existing one. The spike.md skill file was updated to reference the new system, but the old system's entry points (run_optimization.py CLI, spike_auto.py) still work. CLAUDE.md still documents them. A future session that reads CLAUDE.md before spike.md will use the wrong system.

The fix order matters: merge the engines first (Architecture Finding 1), then delete dead code. Deleting dead code while two engines exist just creates confusion about which code is "the real one."

---

### Cross-Finding E: Architecture x Risk — Fitness Function Design Flaw Enables Dangerous Strategies

**Intersection of**: Architecture (evolve.py fitness function) + Risk bullets #3, #9, #10

The evolve.py fitness function (lines 49-70) has no maximum drawdown cap. A strategy with 75% max DD gets only a 0.625x penalty (`1 - 75/200 = 0.625`). If its vs_bah multiple is 4x, the penalized fitness is still 2.5 — easily the best score.

Risk's bullet #9 calls this "too gentle." From the architecture perspective, it's worse than that: the fitness function's design incentivizes strategies that accept catastrophic drawdowns in exchange for high returns. RSI Regime's 75.1% max DD should be disqualifying for a 3x leveraged ETF (where 75% DD means you need a 300% gain to recover), but the fitness function ranks it #1.

The architectural fix: add a hard DD gate to the fitness function. If `max_drawdown_pct > 60`, return 0.0. This is a 2-line change in evolve.py that would fundamentally change which strategies survive evolution.

Meanwhile, backtest_engine.py's regime scoring (the v3 system) has a more nuanced approach — it measures bear avoidance explicitly. The v4 fitness function threw away this sophistication. This is another consequence of the dual-engine split: the better scoring logic exists but isn't used by the active optimizer.

---

## Summary of Actionable Items from Cross-Pollination

| Priority | Item | Source |
|----------|------|--------|
| P0 | Fix `_last_improve` stagnation bug in evolve.py (line 234) — mutation escalates regardless of improvement | New finding from answering Velocity Q |
| P0 | Fix RSI boundary condition in strategies.py line 133: change `<` to `<=` | Answering Data-Integrity Q |
| P0 | Add hard DD gate to evolve.py fitness function (max_drawdown_pct > 60 → 0) | Cross-Finding E |
| P0 | Merge engines (original Finding 1, now 98% confidence) | Confirmed by all 5 lenses |
| P1 | Raise bear_threshold in score_regime_capture to 50% for TECL | Answering Risk Q |
| P1 | Fix stale docstring in backtest_engine.py (claims 1-bar delay, code does same-bar fill) | Answering Risk Q |
| P1 | Add governance metadata to STRATEGY_REGISTRY | Cross-Finding C |
| P2 | Fix bear_avoidance=1.0 default for bear-free windows | Answering Data-Integrity Q |
| P2 | Delete dead code AFTER engine merge | Cross-Finding D |
