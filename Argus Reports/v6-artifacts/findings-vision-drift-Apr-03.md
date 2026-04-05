# Vision-Drift Findings — Apr 03, 2026

**Specialist**: Vision-Drift
**Project**: Project Montauk
**Primary Vision Source**: `reference/Montauk Charter.md`
**Secondary**: `CLAUDE.md`
**Run**: #1 (first Argus pass)

---

## Executive Summary

Project Montauk's Charter describes "a long-only, single-position EMA-trend system for TECL" with explicit guardrails against mean-reversion, countertrend logic, and optimization sweeps. The living codebase as of today is an AI-driven multi-strategy evolutionary discovery platform where the top-performing strategy is an RSI mean-reversion system that violates the Charter's identity, scope guardrails, feature acceptance criteria, and coding rules. The Charter document has not been updated since the project was imported into git on March 3. The gap between documented intent and actual direction is the widest I have seen in a 31-day-old project.

This is not failure. The RSI Regime strategy appears to be genuinely superior (4.7x fitness improvement over 8.2.1). But the Charter is now a historical artifact, not a governing document. The project needs to decide: update the Charter to match reality, or rein in the code to match the Charter.

---

## Finding 1: Identity Metamorphosis — EMA Trend System to Strategy Discovery Platform

- **Confidence**: 99%
- **Category**: silent-direction-change
- **Vision reference**: Charter preamble: "A long-only, single-position EMA-trend system for TECL that captures multi-month bull legs and exits swiftly on regime change using a small, prioritized exit stack"
- **Reality**: The project now contains 7 distinct strategy architectures (montauk_821, golden_cross, rsi_regime, breakout, bollinger_squeeze, trend_stack, tema_momentum) in `scripts/strategies.py`, tested by an evolutionary optimizer (`scripts/evolve.py`) that breeds, mutates, and selects across all architectures. The active development energy (4,387 lines of Python in 3 days) is in the meta-tooling. The Pine Script strategy (8.2.1) has not been touched in 31 days.
- **The gap**: The Charter defines a single strategy with a specific architecture (EMA crossover + exit stack). The code has become a platform that treats that architecture as one candidate among many, and it is currently ranked #3.
- **Type**: deliberate evolution
- **Files**: `scripts/strategies.py`, `scripts/evolve.py`, `scripts/strategy_engine.py`, `.claude/skills/spike.md`
- **Evidence**: spike.md v4 says "Find the Best TECL Strategy" and "Use ANY combination. There are no restrictions on what indicators or logic you can use." This directly contradicts the Charter's identity as "an EMA-trend system."
- **Why this matters**: If the Charter is the constitution, the project is now operating under a different form of government. Every other finding flows from this one.
- **Proposed fix**: Write a new Charter (or a "Charter v2 Amendment") that documents the actual project identity: a strategy discovery platform where TECL long-only with low trade frequency is the constraint, but strategy architecture is open. Preserve the original Charter as historical context.

---

## Finding 2: Charter Section 8 Scope Guardrail Directly Violated

- **Confidence**: 98%
- **Category**: principle-violation
- **Vision reference**: Charter S8: "If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly: 'Out of scope per Montauk charter. [One-sentence reason.] Trend-aligned alternative: [brief suggestion].'"
- **Reality**: RSI Regime strategy (`scripts/strategies.py` lines 114-146, `src/strategy/testing/Montauk RSI Regime.txt`) is a textbook mean-reversion strategy. Entry on RSI crossing up through an oversold threshold (35) is countertrend buying. The strategy was not flagged as out-of-scope; it was celebrated as having 4.7x fitness improvement.
- **The gap**: The Charter explicitly lists mean-reversion and countertrend as things that must be flagged and rejected. The project's best-performing strategy IS mean-reversion.
- **Type**: deliberate evolution (knowingly stepping outside the Charter's bounds because the results were compelling)
- **Files**: `reference/Montauk Charter.md` (S8), `scripts/strategies.py` (rsi_regime function), `src/strategy/testing/Montauk RSI Regime.txt`, `remote/best-ever.json`, `remote/winners/rsi-regime-2026-04-03.json`
- **Evidence**: `best-ever.json` shows `"strategy": "rsi_regime"` with `"fitness": 2.1803` vs montauk_821's 0.4556. The winner file notes: "100% win rate on 10 trades is suspicious -- could be overfitting."
- **Why this matters**: Guardrails exist to prevent scope creep. If the guardrail can be overridden by good backtest numbers alone, it was never a guardrail -- it was a suggestion. Either enforce it (delete RSI Regime, stay on EMA) or update the Charter to define when guardrails can be overridden (e.g., "if a non-EMA strategy beats 8.2.1 by >2x on fitness with walk-forward validation, it may be promoted to testing").
- **Proposed fix**: Charter v2 should replace the blanket ban on mean-reversion with a graduated acceptance framework. Keep the ban as a default, but define an explicit "paradigm break" process for strategies that demonstrably outperform.

---

## Finding 3: Evaluation Metrics Silently Replaced

- **Confidence**: 95%
- **Category**: active-drift
- **Vision reference**: Charter S6 defines 8 evaluation metrics with MAR (CAGR/MaxDD) as "Risk-adjusted return" and specifies "Win rate is secondary and should not be optimized directly."
- **Reality**: `CLAUDE.md` now declares "Regime Score" as the "primary optimization target" (not in Charter). `scripts/evolve.py` uses `vs_bah_multiple` (buy-and-hold comparison) as the actual fitness function. Neither metric appears anywhere in the Charter. MAR is now labeled "Secondary" in CLAUDE.md.
- **The gap**: The Charter's metrics table says MAR is the risk-adjusted return measure. The code promotes two novel metrics (Regime Score, vs_bah) to primary status and demotes MAR without updating the Charter.
- **Type**: deliberate evolution
- **Files**: `reference/Montauk Charter.md` (S6), `CLAUDE.md` (lines 174-197), `scripts/evolve.py` (fitness function lines 47-70), `scripts/backtest_engine.py` (RegimeScore class)
- **Evidence**: `evolve.py` line 59: `bah = max(result.vs_bah_multiple, 0.001)` -- this is the core of the fitness function. Regime Score does not appear in evolve.py at all; it was the v2/v3 metric. The project has already moved past its own intermediate metric.
- **Why this matters**: Metrics define what "good" means. Changing metrics without updating the Charter means the Charter's evaluation criteria are fiction. Someone reading the Charter would optimize for MAR; someone reading evolve.py would optimize for vs_bah. These can diverge significantly.
- **Proposed fix**: Update Charter S6 to reflect the actual metric hierarchy: vs_bah_multiple (primary), Regime Score (secondary), MAR/CAGR/drawdown (reference). Document why vs_bah was chosen over MAR.

---

## Finding 4: Charter is Frozen While Project Evolves

- **Confidence**: 98%
- **Category**: stale-spec
- **Vision reference**: The entire Charter document
- **Reality**: The Charter was written before the Python tooling existed (pre-April 1). It has not been modified since the project was imported into git on March 3. Meanwhile: a 4,387-line Python optimization platform was built, 7 new strategy types were created, the primary metric changed twice (MAR -> Regime Score -> vs_bah), and a paradigm-breaking RSI strategy was discovered.
- **The gap**: The Charter describes a Pine-Script-only, TradingView-backtest-only, EMA-crossover-only project. None of those constraints match reality.
- **Type**: unconscious drift (the Charter was simply never revisited as the project evolved)
- **Files**: `reference/Montauk Charter.md`, `CLAUDE.md` (7 commits, evolving rapidly)
- **Evidence**: CLAUDE.md has 7 commits and grew from 8 to 207 lines. The Charter has 1 commit (initial import). The working documentation (CLAUDE.md) evolved; the constitutional document (Charter) did not.
- **Why this matters**: A spec that does not keep pace with implementation becomes worse than no spec -- it creates false confidence that guardrails are in place when they are not. The Charter currently gives the impression that the project is a carefully scoped EMA system when it is actually an open-ended strategy discovery platform.
- **Proposed fix**: Schedule Charter review after each major architectural pivot. At minimum, flag sections that are known to be stale.

---

## Finding 5: Feature Acceptance Checklist (S5) Not Applied to New Strategies

- **Confidence**: 95%
- **Category**: principle-violation
- **Vision reference**: Charter S5 requires 5 checks before any new feature: (1) Does it improve regime detection or reduce chop? (2) Does it reduce max drawdown more than bull participation? (3) Does it keep trades/year low? (4) Can it be explained as a trend or risk control? (5) Does it avoid parameter bloat?
- **Reality**: Seven new strategy types were added to `scripts/strategies.py` with no evidence that any were evaluated against S5. RSI Regime fails check #4 ("Can it be explained as a trend or risk control -- not an unrelated signal?"). It is an oscillator-based mean-reversion signal, not a trend control. Multiple strategies fail check #5 (parameter bloat): 7 strategies x 5-11 params each = 55+ total tunable parameters.
- **The gap**: The checklist was designed as a gate. It is not being used as a gate.
- **Type**: unconscious drift (the checklist predates the multi-strategy architecture and was never adapted to it)
- **Files**: `reference/Montauk Charter.md` (S5), `scripts/strategies.py` (STRATEGY_PARAMS dict showing param counts per strategy)
- **Evidence**: STRATEGY_PARAMS shows: montauk_821 (11 params), golden_cross (3), rsi_regime (6), breakout (6), bollinger_squeeze (6), trend_stack (5), tema_momentum (8). Plus the signal_queue.json has 12 more queued features for the backtest engine.
- **Why this matters**: If the checklist is not applied, new features are judged solely by backtest performance. Backtest performance is noisy (small sample, overfitting risk). The checklist exists to provide qualitative judgment that metrics cannot.
- **Proposed fix**: Either retire S5 and replace it with "fitness > X and walk-forward validation passes" as the acceptance gate, or adapt S5 for multi-strategy context (e.g., "each new strategy archetype must pass these checks before being added to the registry").

---

## Finding 6: "Backtesting Is Done by the User in TradingView" — Charter S6 Obsolete

- **Confidence**: 90%
- **Category**: stale-spec
- **Vision reference**: Charter S6: "Backtesting is done by the user in TradingView. When proposing changes, Claude should reason about expected impact on these metrics rather than reporting actual results."
- **Reality**: The entire Python infrastructure (backtest_engine.py, strategy_engine.py, evolve.py, run_optimization.py, validation.py) exists to do automated backtesting outside TradingView. 4,387 lines of Python backtesting code. The parity check (`scripts/parity_check.py`) already revealed that Python and TradingView produce different numbers (Python estimated 34.9% CAGR for 8.3; TradingView showed 31.19%).
- **The gap**: The Charter says Claude should reason about impacts, not run backtests. Claude now runs hundreds of thousands of backtests autonomously.
- **Type**: deliberate evolution
- **Files**: `reference/Montauk Charter.md` (S6), all files in `scripts/`, `remote/evolve-results-2026-04-03.json` (1,330 evaluations in one session)
- **Evidence**: evolve-results shows `"total_evaluations": 1330` in a 0.01-hour run. The spike skill is designed for 8-hour overnight runs targeting 500,000+ evaluations.
- **Why this matters**: The Python engine is the actual decision-making infrastructure. If it produces systematically different results from TradingView (the deployment target), then optimization winners may not perform as expected in production.
- **Proposed fix**: Update Charter S6 to acknowledge Python backtesting as the primary search tool and TradingView as the validation/deployment target. Elevate parity checking to a required step before any strategy moves to `testing/`.

---

## Finding 7: Two Coexisting Backtesting Engines — Architectural Fracture

- **Confidence**: 90%
- **Category**: active-drift
- **Vision reference**: CLAUDE.md describes a single backtesting pipeline: `backtest_engine.py` replicates 8.2.1's logic.
- **Reality**: Two separate backtesting engines exist:
  1. `scripts/backtest_engine.py` (~500+ lines) — the original, with `StrategyParams` dataclass, `run_backtest()`, regime scoring, all 17 parameter groups. Used by `validation.py`, `parity_check.py`, `generate_pine.py`, `run_optimization.py`, `spike_auto.py`.
  2. `scripts/strategy_engine.py` (624 lines) — the v4 engine with `Indicators` class, generic `backtest()` function taking numpy arrays. Used by `strategies.py`, `evolve.py`.
  These two engines have different APIs, different indicator implementations, and are NOT tested for parity with each other.
- **The gap**: The v4 architecture (`strategy_engine.py + evolve.py`) cannot use the v1-v3 infrastructure (`validation.py`, `parity_check.py`) because they depend on different backtesting APIs. Walk-forward validation and parity checking are effectively disconnected from the evolutionary optimizer.
- **Type**: unconscious drift (rapid iteration left the old engine behind without cleanup)
- **Files**: `scripts/backtest_engine.py`, `scripts/strategy_engine.py`, `scripts/validation.py` (imports from backtest_engine), `scripts/evolve.py` (imports from strategy_engine)
- **Evidence**: `validation.py` line 16: `from backtest_engine import StrategyParams, run_backtest`. `evolve.py` line 29: `from strategy_engine import Indicators, backtest, BacktestResult`. These are different functions from different modules.
- **Why this matters**: The RSI Regime strategy was found by evolve.py using strategy_engine.py. It was NEVER run through validation.py's walk-forward testing or parity_check.py's TradingView comparison, because those tools speak a different API. The validation infrastructure exists but is disconnected from the thing that needs validating most.
- **Proposed fix**: Either port validation.py to use strategy_engine.py's API, or consolidate the two engines. The v4 engine (strategy_engine.py) is more general; the v1 engine (backtest_engine.py) has regime scoring and parity checking. Merge them.

---

## Finding 8: Parity Validation Missing for Non-8.2.1 Strategies

- **Confidence**: 95%
- **Category**: aspirational-gap
- **Vision reference**: CLAUDE.md implies Python engine results should match TradingView: "Python backtesting engine that faithfully replicates Montauk 8.2.1's logic"
- **Reality**: `scripts/parity_check.py` only validates 8.2.1, 8.3, and 9.0 against TradingView data. RSI Regime has a generated Pine Script in `src/strategy/testing/Montauk RSI Regime.txt` but no parity validation exists for it. The existing parity check already shows discrepancies (Python CAGR estimates are ~10-20% optimistic vs TradingView).
- **The gap**: Every new strategy type needs its own parity validation. As strategy diversity increases, the gap between "what Python says works" and "what TradingView produces" will grow unless parity is systematically checked.
- **Type**: not yet built
- **Files**: `scripts/parity_check.py`, `src/strategy/testing/Montauk RSI Regime.txt`, `src/strategy/testing/archive/backtest-comparison.md`
- **Evidence**: backtest-comparison.md shows Python predicted 8.3 CAGR at ~34.9% (from spike report); TradingView measured 31.19%. That is a 12% overestimate. RSI Regime claims 48.61% CAGR with no TradingView validation.
- **Why this matters**: If the RSI Regime's Python-reported 48.61% CAGR is 10-20% optimistic (following the same bias pattern), the real CAGR could be ~39-44%. Still impressive, but the vs_bah multiple would shrink. Decisions are being made on unvalidated numbers.
- **Proposed fix**: Before any strategy moves from `testing/` to `active/`, require a parity check: run the generated Pine Script in TradingView, compare key metrics against Python output, document discrepancies.

---

## Finding 9: RSI Regime Overfitting Red Flags Unaddressed

- **Confidence**: 85%
- **Category**: aspirational-gap
- **Vision reference**: Charter S6: "Backtest comparisons should change only one thing at a time." Charter validation windows: "Backtests should cover: 2020 melt-up, 2021-2022 tech bear, and subsequent rebounds."
- **Reality**: RSI Regime was found by evolutionary optimization (not one-thing-at-a-time). The winner file (`remote/winners/rsi-regime-2026-04-03.json`) explicitly notes: "100% win rate on 10 trades is suspicious -- could be overfitting." The 75.1% max drawdown is extreme. Only 12 trades total (0.7/year) -- tiny sample. And there is no walk-forward validation because validation.py is disconnected from evolve.py (Finding 7).
- **The gap**: The Charter's validation rigor (stress-test across specific windows, change one thing at a time) is not being applied to the most important new discovery.
- **Type**: not yet built (the validation infrastructure exists but is not wired to the new engine)
- **Files**: `remote/winners/rsi-regime-2026-04-03.json`, `remote/evolve-results-2026-04-03.json`, `scripts/validation.py`
- **Evidence**: Winner file: `"win_rate": 100.0`, `"trades": 10`, `"max_dd": 65.8`. evolve-results: only 1,330 evaluations in 0.01 hours (54-second run). This was a quick test, not a full overnight validation.
- **Why this matters**: A 100% win rate on 10 trades over 17 years is almost certainly overfitting or sample-size illusion. If this strategy is promoted to production without rigorous validation, it could fail catastrophically in the next regime it has not seen.
- **Proposed fix**: Run RSI Regime through walk-forward validation across the Charter's named windows (2020 melt-up, 2021-2022 bear, 2023 rebound). Port validation.py to work with strategy_engine.py, or manually test the Pine Script in TradingView across these periods.

---

## Finding 10: Coding Rules (S4) Have a Python-Shaped Blind Spot

- **Confidence**: 90%
- **Category**: missing-spec
- **Vision reference**: Charter S4 specifies coding rules: "Pine Script v6 only", `process_orders_on_close=true`, `calc_on_every_tick=false`, one strategy block, etc.
- **Reality**: The project is now predominantly Python (~4,387 lines of Python vs ~1,000 lines of Pine Script). No coding rules exist for Python. No tests directory exists. No CI/CD. No linting configuration. No type checking.
- **The gap**: The Charter governs Pine Script with precision. It says nothing about the Python infrastructure that now drives all decision-making.
- **Type**: spec ambiguity (the Charter was written before Python existed in the project)
- **Files**: `reference/Montauk Charter.md` (S4), all files in `scripts/`
- **Evidence**: Scout context confirms: "Tests: None found. CI/CD: None found." The `scripts/` directory has 12 Python files and zero test files.
- **Why this matters**: The Python engine determines which strategies get promoted. Bugs in the Python engine (like the CAGR overestimate) flow directly into strategy selection decisions. Without tests, regressions can silently corrupt optimization results.
- **Proposed fix**: Add a Python section to the Charter (or a separate Python coding standards document) covering: testing expectations, parity requirements, indicator implementation standards (must match Pine Script's ta.* functions).

---

## Finding 11: Dead Code Accumulation from Rapid Pivots

- **Confidence**: 90%
- **Category**: active-drift
- **Vision reference**: CLAUDE.md describes a clean architecture: `backtest_engine.py` replicates 8.2.1, `evolve.py` + `strategy_engine.py` handle multi-strategy optimization.
- **Reality**: Multiple orphaned or semi-orphaned files coexist:
  - `scripts/spike_auto.py` (601 lines) — v3 evolutionary optimizer, superseded by `evolve.py`
  - `scripts/run_optimization.py` (427 lines) — v1-v3 CLI, partially superseded
  - `scripts/signal_queue.json` (289 lines) — 12 queued features for backtest_engine.py, but evolve.py uses strategy_engine.py which has none of these
  - `scripts/backtest_engine.py` — shares functionality with strategy_engine.py but neither imports the other
  - `remote/spike-progress.json` — contains v3-era results (fitness 0.6861, regime-score based) that are no longer relevant to the v4 architecture
- **The gap**: CLAUDE.md does not flag which files are current vs legacy. A developer reading the codebase would not know which backtesting engine to use.
- **Type**: unconscious drift
- **Files**: `scripts/spike_auto.py`, `scripts/run_optimization.py`, `scripts/signal_queue.json`, `scripts/backtest_engine.py`, `remote/spike-progress.json`
- **Evidence**: spike_auto.py imports `from backtest_engine import StrategyParams, run_backtest`. evolve.py imports `from strategy_engine import Indicators, backtest`. Two different entry points, two different engines, two different metric systems.
- **Why this matters**: Dead code creates confusion about what is authoritative. signal_queue.json describes 12 features intended for backtest_engine.py, but if the future is strategy_engine.py, those features will never be used.
- **Proposed fix**: Mark or move legacy files. Update CLAUDE.md to clarify which files are active vs archived. Consider moving spike_auto.py and related v1-v3 artifacts to an archive directory.

---

## Finding 12: generate_pine.py Cannot Handle Non-8.2.1 Strategies

- **Confidence**: 92%
- **Category**: aspirational-gap
- **Vision reference**: CLAUDE.md: "Winning configurations are output as ready-to-paste Pine Script v6" and spike.md: "Only the winner becomes Pine Script"
- **Reality**: `scripts/generate_pine.py` generates parameter diff reports against 8.2.1 defaults. It maps Python parameter names to Pine Script variable names using `PARAM_MAP` which only contains 8.2.1's parameters. It cannot generate Pine Script for RSI Regime, Breakout, Golden Cross, or any other strategy type.
- **The gap**: The "deployment layer" described in the history context (strategies.py -> evolve.py -> generate_pine.py) has a broken last step for any non-8.2.1 strategy. The RSI Regime Pine Script was hand-written.
- **Type**: not yet built
- **Files**: `scripts/generate_pine.py` (PARAM_MAP only maps 8.2.1 params), `src/strategy/testing/Montauk RSI Regime.txt` (hand-written)
- **Evidence**: generate_pine.py line 60: `defaults = StrategyParams().to_dict()` -- this is 8.2.1's StrategyParams. There is no equivalent for RSI Regime.
- **Why this matters**: As the strategy zoo grows, hand-writing Pine Script for each winner does not scale. This is the gap between "discovery platform" aspiration and "single-strategy tool" reality.
- **Proposed fix**: Either build Pine Script generation templates for each strategy type, or accept that Pine Script translation is a manual step and document it as such.

---

## Finding 13: Charter Ambiguity Enables Drift

- **Confidence**: 88%
- **Category**: spec-ambiguity
- **Vision reference**: Multiple Charter sections use language that is precise for Pine Script but ambiguous for the broader project:
  - S3 "No optimization sweeps that add many inputs" -- does this mean automated sweeps, or sweeps that result in more Pine Script inputs?
  - S4 "Pine Script v6 only" -- does this mean the project language, or just the deployment target?
  - S6 "Backtesting is done by the user in TradingView" -- does this prohibit automated backtesting, or is it describing the 2026-03-03 workflow?
  - S2 "Do not propose oscillators or countertrend buys as primary logic" -- RSI is an oscillator; RSI Regime's entry is countertrend. But the Charter says "primary logic" -- does a new strategy count as "primary logic" if 8.2.1 is still the active strategy?
- **Reality**: Each of these ambiguities has been resolved in favor of expansion. Every gray area was read permissively.
- **The gap**: The Charter was written for a world where Claude makes Pine Script edits to a single strategy. It does not anticipate Claude building a Python platform that discovers entirely new strategy architectures.
- **Type**: spec ambiguity
- **Files**: `reference/Montauk Charter.md` (S2, S3, S4, S6)
- **Evidence**: Every major architectural decision (Python engine, multi-strategy, RSI Regime) lives in the gray area of Charter language.
- **Why this matters**: Ambiguous specs always drift toward what is exciting rather than what is safe. The Charter's ambiguities have consistently been resolved in the direction of more scope, more strategies, more parameters.
- **Proposed fix**: Rewrite ambiguous sections with explicit scope for Python tooling, multi-strategy architecture, and the boundary between "exploration" and "production."

---

## Finding 14: The Composite Oscillator Is Orphaned

- **Confidence**: 85%
- **Category**: stale-spec
- **Vision reference**: CLAUDE.md describes the Composite Oscillator 1.3 as the "current production indicator" using TEMA Slope, Quick EMA, MACD, DMI -- all EMA-paradigm components.
- **Reality**: If RSI Regime becomes the active strategy, the oscillator's components (TEMA slope, Quick EMA, MACD, DMI) are irrelevant. RSI Regime uses RSI and a simple trend EMA. The oscillator has not been touched since initial commit (March 3).
- **The gap**: The indicator was designed as a companion to the EMA-crossover strategy. A paradigm shift to RSI-based trading leaves it without a purpose.
- **Type**: unconscious drift (nobody explicitly decided to abandon the oscillator; it just became irrelevant)
- **Files**: `src/indicator/active/Montauk Composite Oscillator 1.3.txt`, `src/strategy/testing/Montauk RSI Regime.txt`
- **Evidence**: Oscillator components: TEMA (300-bar), Quick EMA (7-bar), MACD (30/180/20), DMI (60-bar ADX). RSI Regime uses: RSI(14), EMA(150). Zero overlap.
- **Why this matters**: If RSI Regime goes active while the oscillator remains "active," users get contradictory signals. The oscillator might say "strong trend" while RSI Regime is in cash because RSI is not oversold.
- **Proposed fix**: If RSI Regime is promoted, either retire the oscillator or build an RSI-based companion indicator.

---

## What I Investigated and Ruled Out

1. **TECL-only scope violation**: Checked all strategies in strategies.py and all Pine Scripts. Everything targets TECL. No multi-asset drift.
2. **Shorting/pyramiding violation**: All strategies are long-only, single position. No violations found.
3. **Data integrity issues**: data.py handles CSV + Yahoo Finance merge cleanly. No evidence of lookahead bias in the data pipeline.
4. **Pine Script quality regression**: 8.2.1 and RSI Regime both follow correct Pine v6 patterns (`process_orders_on_close=true`, `calc_on_every_tick=false`, `pyramiding=0`).
5. **Audience drift**: The project remains a solo developer's tool. No evidence of scope expansion toward a product or platform for others.

## Coverage Gaps

1. **Full backtest_engine.py** -- file exceeds 10,000 tokens; I read the first 100 lines (parameter definitions) but did not read the full backtest loop. The regime scoring implementation was not read line-by-line.
2. **Pine Script v6 reference material** (~210,000 tokens in `reference/pinescriptv6-main/`) -- not read; these are reference docs, not project code.
3. **Archived strategy files** (1.0 through 8.1) -- read headers only; these are historical artifacts that do not affect current drift analysis.
4. **Git commit messages** -- not read directly; relied on history context from scout. Individual commit messages might reveal decision rationale not captured in the history timeline.

---

## Manifest

| File | Purpose |
|------|---------|
| `Argus Reports/v6-artifacts/scratchpad-vision-drift-Apr-03.md` | Working notes, hypothesis evolution, file read log |
| `Argus Reports/v6-artifacts/findings-vision-drift-Apr-03.md` | This document -- final findings |
