# Velocity & Friction Findings — Apr 03

**Specialist**: Velocity & Friction
**Date**: 2026-04-03
**Scope**: Full codebase, all 27 commits, all Python + Pine Script source files
**Project**: Project Montauk — TECL trading strategy optimization

---

## Summary

Project Montauk is a solo developer + AI pairing project that pivoted from Pine Script strategy editing to a Python meta-optimization platform in 3 days (Apr 1-3). The pivot produced 4,676 lines of Python with zero tests, zero CI, 39% dead code, and a duplicated backtesting engine. The optimization infrastructure has been rewritten 4 times, but the most recent rewrite (v4) discovered a fundamentally superior strategy (RSI Regime) in under 36 seconds — suggesting the architecture is finally converging. The core friction points are: duplicate code creating maintenance risk, dead code creating confusion, and a growing Python-to-TradingView parity gap that could invalidate the entire optimization effort.

---

## Finding 1: Duplicate Backtesting Engines

**Confidence**: 95%
**Category**: Code Duplication / Maintenance Risk

**Quantitative evidence**: `backtest_engine.py` (990 lines) and `strategy_engine.py` (624 lines) both implement identical indicator functions (EMA, TEMA, ATR, SMA, highest, lowest, ADX) and independent backtest loops, Trade dataclasses, and BacktestResult dataclasses. Approximately 300-400 lines are functionally duplicated.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/backtest_engine.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/strategy_engine.py`

**Git evidence**: `backtest_engine.py` was created Apr 1 (commit `4ad11e0`) for 8.2.1 single-strategy optimization. `strategy_engine.py` was created Apr 3 (commit `5dd806f`) for the v4 multi-strategy architecture. The new file reimplements all indicators from scratch rather than importing from the existing file. The old file was modified in the same commit to fix 5 bugs — but the fixes were NOT propagated to the new file because the code was copy-modified.

**Claim**: Two independent implementations of the same indicator math create a divergence risk — a bug fix in one will not reach the other, and the optimizer (which uses `strategy_engine.py`) could produce results that don't match the validator (which uses `backtest_engine.py`).

**Evidence**:
- `backtest_engine.py` line 131-141: `ema()` function with SMA seed
- `strategy_engine.py` line 29-38: `_ema()` function with identical SMA seed logic
- `backtest_engine.py` line 152-169: `atr()` using RMA (alpha=1/period)
- `strategy_engine.py` line 67-74: `_atr()` also using `_rma()` with same alpha
- `backtest_engine.py` line 196-235: `adx()` with Wilder's smoothing
- `strategy_engine.py` line 434-456: `_adx()` and `_dmi()` — different implementation structure, same math
- Both files define their own `Trade` and `BacktestResult` dataclasses (compare `strategy_engine.py` line 463-493 vs `backtest_engine.py` line 238-265 area)

**Why this matters**: The v3 optimizer (`spike_auto.py`) imports from `backtest_engine.py`. The v4 optimizer (`evolve.py`) imports from `strategy_engine.py`. If both are ever run in the same session — or if results are compared across sessions — indicator divergence could produce phantom improvements. The Apr 2 session already documented a Python-vs-TradingView CAGR discrepancy (34.9% vs 31.19%), and having two Python engines with potentially different behavior makes debugging that gap twice as hard.

**Proposed fix**: Consolidate into a single indicator library. `strategy_engine.py`'s `Indicators` class with its caching is the better architecture. Make `backtest_engine.py` import indicators from `strategy_engine.py` instead of reimplementing them. Merge the two `backtest()` functions — the `strategy_engine.py` version is more general (accepts signal arrays) while `backtest_engine.py` has regime scoring built in.
- **Effort**: ~2 hours
- **Expected time savings**: Eliminates all future "fix in one place, forget the other" bugs. Estimated 1-2 hours saved per optimization session.
- **ROI**: 3x within 2 sessions

**Ripple map**: `evolve.py`, `strategies.py`, `spike_auto.py`, `run_optimization.py`, `validation.py`, `parity_check.py` all import from one or the other.

**If not fixed**: A subtle indicator divergence will eventually invalidate an optimization result that looked good in Python but fails in TradingView. The developer will spend hours debugging what turns out to be a difference between the two Python engines, not a Python-vs-TV difference.

---

## Finding 2: 39% Dead Code (1,819 lines)

**Confidence**: 85%
**Category**: Codebase Drag / Confusion Risk

**Quantitative evidence**:
| File | Lines | Status | Reason |
|------|-------|--------|--------|
| `spike_auto.py` | 601 | Dead | v3 optimizer, superseded by `evolve.py` |
| `run_optimization.py` | 427 | Partially dead | v1-v3 CLI, imports from old `backtest_engine.py` |
| `signal_queue.json` | 289 | Orphan | No file imports or references it |
| `spike_state.py` | 176 | Dead | v1-v3 state management, `evolve.py` has its own |
| `parity_check.py` | 184 | Obsolete | Only validates 8.2.1, cannot validate v4 strategies |
| `generate_pine.py` | 142 | Obsolete | Only maps 8.2.1 params, cannot generate RSI Regime |
| **Total** | **1,819** | | **39% of 4,676 total Python lines** |

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/spike_auto.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/run_optimization.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/signal_queue.json`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/spike_state.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/parity_check.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/generate_pine.py`

**Git evidence**: `spike_auto.py` and `run_optimization.py` were created Apr 1-2 for spike v1-v3. `evolve.py` and `strategy_engine.py` were created Apr 3 as their replacements. The spike skill (`spike.md`) was rewritten in commit `5dd806f` to point to `evolve.py` — but the old files were never removed. `signal_queue.json` appears in commit `5dd806f` with 289 lines but is never referenced in any import statement or commit message.

**Claim**: Nearly 40% of the Python codebase is dead weight. For a solo developer + AI pairing workflow, this means every time Claude reads `scripts/` to understand the project, it processes ~1,800 lines of irrelevant code, wasting context window and potentially generating suggestions based on obsolete patterns.

**Evidence**:
- `spike.md` (the canonical skill definition) references `evolve.py` exclusively — no mention of `spike_auto.py`, `run_optimization.py`, or `spike_state.py`
- `evolve.py` imports from `strategy_engine.py` and `strategies.py` — never from `backtest_engine.py` or `spike_auto.py`
- `signal_queue.json` contains 289 lines of JSON with signal data but no Python file imports it (verified via grep)

**Why this matters**: In an AI-pair-programming workflow, stale code is actively harmful — it confuses the AI into using old patterns. When Claude sees both `spike_auto.py` (601 lines) and `evolve.py` (377 lines), it cannot easily distinguish which is current without reading the skill file first. This costs tokens and risks generating code that imports from the wrong module.

**Proposed fix**: Move dead files to `scripts/archive/` or delete them. Keep `parity_check.py` and `generate_pine.py` but mark them as needing v4 updates.
- **Effort**: 15 minutes
- **Expected time savings**: ~5-10 minutes per Claude session (fewer files to read, less confusion)
- **ROI**: Immediate, compounding

**Ripple map**: None — these files are not imported by any active code.

**If not fixed**: Claude will periodically suggest using `spike_auto.py` or `run_optimization.py` for tasks that should use `evolve.py`. The developer will need to correct this, burning tokens and attention.

---

## Finding 3: Spike Skill "Groundhog Day" — 4 Full Rewrites in 3 Days

**Confidence**: 75%
**Category**: Churn / Velocity Waste

**Quantitative evidence**: `.claude/skills/spike.md` has been through 7 modifications across 5 commits in 3 days. Each major version replaced 60-80% of the content. Total churn: 241 lines created, then 183 deleted and 127 added, then 40 deleted and 59 added, then 170 deleted and 145 added, then 76 deleted and 151 added, then 270 deleted and 94 added. The cumulative churn is ~1,300 lines for a file that is currently 137 lines — a 9.5x churn ratio.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.claude/skills/spike.md`

**Git evidence**: Commits `4ad11e0` (v1), `bbc39a4` (unattended rewrite), `d17b39c` (metric rewrite), `e648644` (v2), `e56853b` (v3), `daa4b31` (v3 bump), `5dd806f` (v4 complete rewrite).

**Claim**: Each spike version lasted approximately 10 hours before being replaced. The v1-v3 rewrites were wasted effort because the architecture they optimized (8.2.1 parameter tuning) was the wrong approach — v4 discovered that a different strategy architecture (RSI Regime) outperforms by 4.7x. However, the v1-v3 infrastructure built skills and tooling that v4 builds on, so it was not pure waste.

**Evidence**:
- v1 (Apr 1): Created backtesting engine + CLI runner + skill definition. ~1,700 lines net new.
- v2 (Apr 2 morning): Rewrote metric target, added infinite loop and proposal phase. ~500 lines changed.
- v3 (Apr 2 morning): Added bootstrap validation and plateau analysis. ~350 lines changed.
- v4 (Apr 3): Ground-up rewrite to multi-strategy. ~3,500 lines net new, ~900 lines deleted.
- v1-v3 total investment: ~2,550 lines created. Of that, ~1,028 lines survive in some form (backtest_engine.py, validation.py, data.py). ~1,522 lines were thrown away.

**Why this matters**: The 60% throwaway rate is the cost of exploration in a solo+AI project. It is not intrinsically bad — v4 would not have existed without v1-v3's lessons. But the pattern of "full rewrite every 10 hours" suggests the skill definition is being used as disposable scaffolding rather than a stable contract. If v5 arrives (likely, given the pattern), another ~1,000 lines will be thrown away.

**Proposed fix**: Separate the spike skill into stable vs experimental sections. The data fetching, indicator library, and validation framework are stable — they should not be rewritten. The strategy search methodology is experimental — it should be in a separate file that the skill delegates to. This way, a v5 rewrites `evolve.py` but does not touch the skill definition or the indicator library.
- **Effort**: 1 hour
- **Expected time savings**: Reduces next rewrite from ~3,500 lines to ~500 lines
- **ROI**: 5x on next architecture change

**Ripple map**: `evolve.py`, `strategies.py`, `strategy_engine.py`

**If not fixed**: v5 will arrive, another 1,000+ lines will be thrown away, and the stable infrastructure (indicators, backtesting, validation) will be at risk of regression.

---

## Finding 4: Zero Tests — 100% Build, 0% Maintain

**Confidence**: 95%
**Category**: Quality Infrastructure Gap

**Quantitative evidence**: 0 test files in the entire project. 0 CI/CD configuration. 0 lint configuration. 4,676 lines of Python with no automated verification of correctness. The only validation is `parity_check.py`, which is manual-run and only covers the old 8.2.1 strategy.

**Files**: N/A (no test files exist)

**Git evidence**: Scout context confirms "Tests: 0" in file manifest. No commit message references testing, test runs, or CI.

**Claim**: The lack of tests means that every optimization run is trusting unverified math. The Apr 2 session already found a 12% discrepancy between Python CAGR and TradingView CAGR. Without regression tests, any bug fix to `backtest_engine.py` (6 commits, 5 documented bugs fixed) could introduce new errors that silently corrupt future optimization results.

**Evidence**:
- Commit `5dd806f` message: "Fix 5 backtest engine bugs (Python 3.9 compat, vs_bah baseline, EMA cross allBelow logic, CAGR date span, same-bar fills)"
- That is 5 bugs found in 3 days of development. With 0 tests, there is no guarantee that these fixes did not break something else.
- `backtest_engine.py` has been modified in 6 of the last 8 commits. Each modification is a regression risk.

**Why this matters**: The entire project's value proposition is "Python can evaluate strategies faster than TradingView." If the Python evaluation is wrong, every hour of optimization is wasted. The 5 bugs already found are the detectable ones — survivorship bias says more lurk.

**Proposed fix**: Add 3 targeted tests: (1) indicator output matches known values (EMA of a short series = known number), (2) `backtest()` output on a synthetic dataset matches expected trades, (3) parity check against the documented TradingView numbers in `parity_check.py`. This is ~100 lines of pytest.
- **Effort**: 1 hour
- **Expected time savings**: Catches regressions before they corrupt a multi-hour optimization run. One prevented bad run = 7+ hours saved.
- **ROI**: 7x on first prevented regression

**Ripple map**: All Python files.

**If not fixed**: A regression in indicator math will silently produce wrong fitness scores. The developer will spend an optimization session chasing a phantom improvement, then discover the Python engine was wrong all along. This has already happened once (the CAGR discrepancy).

---

## Finding 5: Python-TradingView Parity Gap Growing, Not Shrinking

**Confidence**: 90%
**Category**: Validation Gap / Strategy Risk

**Quantitative evidence**: `parity_check.py` documents 3 strategy configs with TradingView reference data — all for Montauk 8.2.1 variants. The v4 optimizer has 7 strategy architectures (montauk_821, golden_cross, rsi_regime, breakout, bollinger_squeeze, trend_stack, tema_momentum). Only 1 of 7 has any TradingView validation data. The winning strategy (RSI Regime, fitness 2.18) has ZERO TradingView validation.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/parity_check.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/testing/Montauk RSI Regime.txt`

**Git evidence**: `parity_check.py` was created in commit `5dd806f` with hardcoded TradingView reference data for 8.2.1, 8.3-conservative, and 9.0-candidate only. The RSI Regime Pine Script was generated in commit `28db2e2` but no TradingView backtest results have been recorded against it.

**Claim**: The RSI Regime strategy shows a 3.49x vs buy-and-hold advantage in the Python engine. If the Python-to-TV discrepancy follows the same pattern as 8.2.1 (where Python was ~12% optimistic on CAGR), the real advantage could be significantly lower. Without validation, the developer is making a paradigm shift (abandoning 8 versions of EMA crossover) based on unverified numbers.

**Evidence**:
- `parity_check.py` line 28-97: TV_REFERENCE only contains 8.2.1 variants
- `evolve-results-2026-04-03.json`: RSI Regime listed with `"vs_bah": 3.4913` — this is a Python-only number
- The documented 8.2.1 parity gap: Python CAGR 34.9% vs TV 31.19% = 12% overestimate
- RSI Regime also has 75.1% max drawdown — a number that needs TV confirmation since Python and TV compute drawdown differently (close-to-close vs intrabar)

**Why this matters**: The entire justification for the RSI Regime paradigm shift rests on Python fitness numbers. If RSI Regime's TV results are 12% worse than Python estimates (following the 8.2.1 pattern), its vs_bah drops from 3.49x to approximately 3.07x — still good, but the margin of superiority narrows significantly. More critically, the 75.1% max drawdown in Python could be 80%+ in TradingView (where intrabar drawdown is typically worse), which would be a dealbreaker.

**Proposed fix**: Before any further optimization runs, paste the RSI Regime Pine Script into TradingView, record backtest results, and add them to `parity_check.py`. This is 15 minutes of work that validates the entire v4 thesis.
- **Effort**: 15 minutes (manual TradingView work)
- **Expected time savings**: Prevents building on a false premise. If RSI Regime fails TV validation, all future optimization work changes direction immediately rather than weeks later.
- **ROI**: Unbounded (prevents potentially weeks of wasted effort)

**Ripple map**: Affects the decision to continue optimizing RSI Regime vs reverting to 8.2.1 optimization.

**If not fixed**: The developer deploys RSI Regime to live TradingView, discovers the drawdown is unacceptable, and loses confidence in the entire Python optimization pipeline.

---

## Finding 6: Burst Development Pattern — 26 Idle Days, Then 22 Commits in 3 Days

**Confidence**: 95%
**Category**: Velocity Pattern / Context Loss Risk

**Quantitative evidence**:
- Mar 3-4: 6 commits (initial import, bug audit, 8.2.1 fix)
- Mar 5 - Mar 31: 0 commits (26 days idle)
- Apr 1: 8 commits (entire Python backtesting infrastructure from scratch)
- Apr 2: 9 commits (metric rewrite + 3 spike rewrites + 7.4h optimization run)
- Apr 3: 4 commits (v4 complete rewrite + RSI Regime discovery)

**Files**: N/A (pattern observation)

**Git evidence**: `git log --format="%ai %s"` shows the full timeline. No commits between Mar 4 20:27 and Apr 1 05:48 — a 28-day gap.

**Claim**: The burst pattern means context is rebuilt from scratch each session. The 26-day gap between Era 1 (Pine Script) and Era 2 (Python tooling) required the developer to re-familiarize with the entire project. CLAUDE.md's 25x growth (8 to 207 lines) is direct evidence of this context rebuilding — it grew because each new session needed more documentation to avoid re-learning the same things.

**Evidence**:
- CLAUDE.md started at 8 lines (Mar 3) and grew to 207 lines by Apr 3 — 25x expansion
- 7 separate commits to CLAUDE.md, most adding context that was "discovered" during sessions
- The Mar 4 bug (EMA cross exit never fires) was a rediscovery of something that had been building through 8 strategy versions — suggesting even the pre-git history had context loss between sessions

**Why this matters**: For a solo+AI project, the CLAUDE.md IS the project's working memory. Its growth is necessary but represents "invisible work" — effort spent on coordination and documentation rather than progress. Approximately 7 of 27 commits (26%) are primarily documentation/coordination rather than code.

**Proposed fix**: No code fix needed. This is an observation for calibration. The burst pattern is natural for a side project. The CLAUDE.md growth is correct behavior — it IS the fix for context loss. The recommendation is: keep investing in CLAUDE.md, but be aware that after the next idle gap, expect to spend the first 2-3 commits on context recovery rather than progress.
- **Effort**: 0
- **Expected time savings**: N/A (awareness)
- **ROI**: N/A

**Ripple map**: Affects time estimates for all future work.

**If not fixed**: N/A — this is a pattern observation, not a defect.

---

## Finding 7: generate_pine.py Cannot Generate Pine for New Strategies

**Confidence**: 90%
**Category**: Deployment Bottleneck

**Quantitative evidence**: `generate_pine.py` (142 lines) contains `PARAM_MAP` on lines 26-57 that maps only Montauk 8.2.1 parameter names to Pine Script variable names. There are 0 entries for RSI Regime, breakout, golden cross, bollinger squeeze, trend stack, or TEMA momentum parameters. The RSI Regime Pine Script (`Montauk RSI Regime.txt`, 96 lines) was hand-written by Claude, not generated by `generate_pine.py`.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/generate_pine.py`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/testing/Montauk RSI Regime.txt`

**Git evidence**: Commit `28db2e2` ("RSI Skill gen") adds the RSI Regime Pine Script with 96 new lines. The commit does NOT modify `generate_pine.py` — the Pine Script was written manually/by Claude, not by the generation tool.

**Claim**: The v4 architecture promises "write Python, evolve parameters, auto-generate Pine Script." In practice, the last step is manual. Every new strategy winner requires a human+AI session to hand-translate Python logic to Pine Script. This breaks the automation pipeline and creates a bottleneck between "Python says this is good" and "it runs in TradingView."

**Evidence**:
- `spike.md` line 105-109: "Read the winning Python function, understand the logic, write equivalent Pine Script v6." This is explicitly a manual process.
- `generate_pine.py` only generates a parameter diff report — it does not actually produce Pine Script code, despite its name.
- The RSI Regime strategy (`strategies.py` lines 114-146) is 33 lines of Python. Its Pine Script equivalent (`Montauk RSI Regime.txt`) is 96 lines. This 3x expansion is manual work every time.

**Why this matters**: If the optimizer discovers 10 promising strategies, each needs manual Pine Script translation. At ~15-30 minutes per strategy (reading Python, writing Pine, testing in TV), this is 2.5-5 hours of human+AI work before any TradingView validation can happen. The whole point of the Python optimizer was to avoid this bottleneck.

**Proposed fix**: Either (a) build a real Pine Script code generator that maps Python strategy functions to Pine Script v6, or (b) add a template system where each strategy in `STRATEGY_REGISTRY` has a corresponding Pine Script template that gets filled with optimized parameters. Option (b) is much simpler and aligns with the current architecture.
- **Effort**: 2-4 hours for option (b)
- **Expected time savings**: 15-30 minutes per strategy deployment, across potentially dozens of strategies
- **ROI**: 3x within first 5 strategy deployments

**Ripple map**: `strategies.py`, `spike.md` (workflow description)

**If not fixed**: The deployment bottleneck will cap throughput. The optimizer can test 500,000 parameter combinations overnight, but only 1-2 can be deployed to TradingView per session.

---

## Finding 8: evolve.py Ran for Only 36 Seconds on First Run

**Confidence**: 85%
**Category**: Optimization Efficiency / Premature Convergence Risk

**Quantitative evidence**: `evolve-results-2026-04-03.json` shows `"elapsed_hours": 0.01` (36 seconds), `"total_evaluations": 1330`, `"generations": 19`. Compare to the v3 session report which ran for 7.4 hours. RSI Regime was declared the winner after 19 generations with a population of 40 per strategy.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/remote/evolve-results-2026-04-03.json`

**Git evidence**: The results JSON was created in commit `5dd806f` along with the v4 code itself — suggesting the optimizer was run once, briefly, as a proof-of-concept rather than a thorough search.

**Claim**: 19 generations with 40 individuals across 7 strategies = ~5,320 evaluations needed (7 * 40 * 19). The reported 1,330 evaluations suggest early termination or only partial strategy evaluation. Either way, declaring RSI Regime the winner based on 36 seconds of optimization is premature — the parameter space has barely been explored. The current winning parameters (`entry_rsi=35, exit_rsi=85, trend_len=150`) may be a local optimum.

**Evidence**:
- RSI Regime parameter space has 6 parameters with ranges: `rsi_len` 7-21, `trend_len` 50-200, `entry_rsi` 25-45, `exit_rsi` 65-85, `panic_rsi` 15-30, `cooldown` 0-20
- The grid size is approximately 8 * 7 * 5 * 5 * 4 * 5 = 28,000 combinations
- 19 generations * 40 individuals = 760 evaluations for RSI Regime specifically
- That is 2.7% of the search space — a very thin sample
- `tema_momentum` shows `"fitness": 0.0` with no metrics — it was never successfully evaluated

**Why this matters**: The v4 architecture is designed for 8-hour overnight runs. It has been validated for approximately 36 seconds. RSI Regime's 4.7x superiority over 8.2.1 may be real, but the specific parameters are almost certainly not optimal. An 8-hour run would explore orders of magnitude more of the parameter space and likely find better RSI Regime parameters (or discover that the 75.1% drawdown can be reduced with different settings).

**Proposed fix**: Run `python3 scripts/evolve.py --hours 8` overnight before making any decisions based on v4 results. The 36-second run was a proof of concept, not a real optimization.
- **Effort**: 0 (just run the command and wait)
- **Expected time savings**: Potentially discovers parameter sets with lower drawdown, which would change the deployment decision
- **ROI**: Immediate (the infrastructure already exists)

**Ripple map**: `remote/best-ever.json`, `remote/evolve-results-*.json`, deployment decision for RSI Regime

**If not fixed**: The developer may deploy RSI Regime with parameters that produce 75.1% max drawdown when an 8-hour run might find parameters with 50-60% drawdown and similar returns.

---

## Finding 9: CLAUDE.md as Growing Token Tax

**Confidence**: 80%
**Category**: Invisible Work / Token Overhead

**Quantitative evidence**: CLAUDE.md grew from 8 lines (Mar 3) to 207 lines (Apr 3) across 7 commits. It is now ~850 tokens. Every Claude Code session reads it as context. At current project velocity (multiple sessions per active day), this is a fixed per-session cost that grows over time but never shrinks.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/CLAUDE.md`

**Git evidence**: Commits `49371c1` (8 lines), `4ad11e0` (+49 lines), `c6adb70` (+14 lines), `baef422` (+45 lines), `39e5331` (+3 lines), `98e5e71` (+64 lines), `ce7ad7c` (restructure), `5dd806f` (current).

**Claim**: 26% of all commits (7/27) modified CLAUDE.md. This is correct behavior — it is the project's living memory. But significant content is now stale: the detailed version history table (15 lines), the "Remote Sessions" section (aimed at mobile Claude), the CLI tools section (references v1-v3 commands that are now obsolete), and the generate_pine.py docs (still references 8.2.1-only generation). At least 40% of CLAUDE.md describes the pre-v4 world.

**Evidence**:
- Lines describing `run_optimization.py` commands (baseline, test, sweep, grid, validate) — these are v1-v3 patterns
- "Generate Pine Script from params" section references `generate_pine.py` which does not actually generate Pine Script
- The version history table lists 12 Pine Script versions — useful for context but rarely referenced

**Why this matters**: Stale CLAUDE.md content costs tokens every session and can actively mislead Claude into suggesting v1-v3 workflows. The file should be pruned to reflect the v4 reality.

**Proposed fix**: Trim CLAUDE.md to focus on the v4 architecture. Move the version history to a separate `HISTORY.md`. Remove v1-v3 CLI commands. Update the `/spike` section to match the current `spike.md` skill. Target: 120 lines instead of 207.
- **Effort**: 30 minutes
- **Expected time savings**: ~200 tokens per session, plus fewer misleading suggestions
- **ROI**: Marginal but compounding

**Ripple map**: All future Claude sessions.

**If not fixed**: CLAUDE.md will continue growing. By v5 it will be 300+ lines, 30% stale, costing 1,200+ tokens per session for diminishing marginal value.

---

## Finding 10: Fitness Function Changed 3 Times in 3 Days

**Confidence**: 90%
**Category**: Strategy Stability Risk

**Quantitative evidence**:
- Apr 1: Primary fitness = MAR (CAGR / Max Drawdown)
- Apr 2: Rewritten to Regime Score (0.5 * bull_capture + 0.5 * bear_avoidance)
- Apr 3 (spike_auto.py): Rewritten to vs_bah_multiple * dd_penalty * regime_bonus
- Apr 3 (evolve.py): Rewritten to vs_bah_multiple * dd_penalty * freq_penalty

There are now TWO different fitness functions in the codebase:
- `spike_auto.py` line 194-237: `bah * dd_penalty * regime_bonus` with quality guards (min 5 trades, max 6 trades/yr, etc.)
- `evolve.py` line 49-70: `bah * dd_penalty * freq_penalty` with hard cap at 3 trades/yr

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/spike_auto.py` (lines 194-237)
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/scripts/evolve.py` (lines 49-70)

**Git evidence**: `d17b39c` "spike: rewrite optimization target from MAR to Regime Score", `5dd806f` introduces two new fitness functions in the same commit.

**Claim**: Changing the fitness function is the single highest-impact decision in the entire optimization pipeline. Each change invalidates all previous results because the same parameters score differently under different fitness functions. The current state has two active fitness functions that would rank strategies differently — if `spike_auto.py` is accidentally used, its results cannot be compared with `evolve.py` results.

**Evidence**:
- `spike_auto.py` fitness penalizes < 5 trades (0.3x), > 6 trades/yr (0.5x), < 20 avg bars (0.5x), > 30% false signal rate (0.7x), > 85% DD (0.3x)
- `evolve.py` fitness only penalizes > 3 trades/yr and < 3 total trades
- A strategy with 4 trades would score 0.3x in `spike_auto.py` but full score in `evolve.py`
- The `evolve.py` fitness does not include regime_bonus at all — regime capture is not part of the v4 fitness function, despite being the v3 primary target

**Why this matters**: The developer spent an entire session (Apr 2, 7.4 hours) optimizing for Regime Score. The v4 fitness function does not use Regime Score at all. If the developer assumes RSI Regime was selected for good regime capture (as the history suggests), they may be surprised to find its regime score is not even being evaluated — it won purely on vs_bah_multiple.

**Proposed fix**: Delete `spike_auto.py`'s fitness function (it is dead code per Finding 2). Ensure `evolve.py` is the single source of truth for fitness. If regime capture matters, add it back to the v4 fitness as a secondary signal.
- **Effort**: 15 minutes (part of dead code cleanup)
- **Expected time savings**: Eliminates confusion about which fitness function is active
- **ROI**: Prevents a category of "results don't match" debugging

**Ripple map**: Addresses Finding 2 (dead code) simultaneously.

**If not fixed**: The developer will eventually reference the v3 "Regime Score" results alongside v4 "vs_bah" results and wonder why the rankings differ. The answer is: they used different fitness functions.

---

## Finding 11: The Production Strategy Has Not Changed in 31 Days

**Confidence**: 95%
**Category**: Velocity Paradox / Motion vs Progress

**Quantitative evidence**: `src/strategy/active/Project Montauk 8.2.1.txt` was last modified Mar 4 (commit `4e23b2f`). Since then: 22 commits, 4,676 lines of Python, 3 spike versions, 7 strategy architectures, 1 paradigm shift (EMA crossover -> RSI Regime). Zero changes to production.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/active/Project Montauk 8.2.1.txt`

**Git evidence**: `git log --oneline -- "src/strategy/active/"` shows last change was `4e23b2f` on Mar 4.

**Claim**: 22 commits of optimization infrastructure have produced zero changes to the thing that actually runs in TradingView. This is not necessarily bad — the infrastructure was needed to discover that 8.2.1 is suboptimal. But it means 3 days of intense development (Apr 1-3) have moved the "what runs in production" needle exactly 0%.

**Evidence**:
- RSI Regime Pine Script exists in `src/strategy/testing/` — it is one step from production but has not been promoted
- The v3 optimization found Combo G (vs_bah 1.135x) which could have been deployed to production — it was not
- The v4 optimization found RSI Regime (vs_bah 3.49x) which has a Pine Script ready — it has not been deployed

**Why this matters**: The optimization infrastructure is not a product — the TradingView strategy is. If the goal is "beat buy-and-hold on TECL," zero progress has been made in 31 days by the production metric. The Python tooling is valuable enablement work, but it needs to translate into a production change to deliver value.

**Proposed fix**: Establish a deployment cadence. After every full optimization session, the session report should include a binary decision: "Deploy candidate Y/N?" with a specific checklist (TV parity check passes, drawdown < threshold, walk-forward validates). This prevents the optimization loop from running indefinitely without producing production changes.
- **Effort**: 0 (process change)
- **Expected time savings**: Forces production decisions instead of endless exploration
- **ROI**: Qualitative — breaks the build-without-deploying loop

**Ripple map**: `spike.md` (add deployment gate step), `remote/spike-*.md` (add deploy decision)

**If not fixed**: The optimization infrastructure will continue growing while 8.2.1 runs unchanged in TradingView. The gap between "what Python says is optimal" and "what actually runs" will grow until confidence in the Python pipeline erodes.

---

## Finding 12: No Rollback Safety for Strategy Deployment

**Confidence**: 80%
**Category**: Risk / Deployment Safety

**Quantitative evidence**: `src/strategy/active/` contains exactly 1 file. `src/strategy/archive/` contains 12 historical versions. There is no mechanism to promote a candidate from `testing/` to `active/` or to roll back from `active/` to a previous version — these are manual file operations.

**Files**:
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/active/`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/archive/`
- `/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/src/strategy/testing/`

**Claim**: When RSI Regime (or any candidate) is promoted to `active/`, the old 8.2.1 strategy needs to be manually archived first. Git provides history, but the CLAUDE.md instructions say "copy the active file to archive first, then modify the active copy." This is error-prone and has no automated verification.

**Why this matters**: For a trading strategy, deploying the wrong version is directly costly — it affects real money. The manual copy-archive-modify workflow has no guards against overwriting without archiving.

**Proposed fix**: This is low priority given the current deployment velocity (0 deployments in 31 days). But when deployment does happen, a simple shell script (`scripts/deploy.sh`) that automates the archive-copy-promote workflow would eliminate human error.
- **Effort**: 30 minutes
- **Expected time savings**: Prevents a potential "forgot to archive before overwriting" incident
- **ROI**: Insurance — low probability, high impact

**Ripple map**: `CLAUDE.md` (update deployment instructions)

**If not fixed**: Acceptable risk in the short term. Becomes problematic if deployment velocity increases.

---

## What I Investigated and Ruled Out

1. **Data fetching as a bottleneck**: `data.py` (126 lines) is clean, stable (1 commit after initial), and well-designed with CSV fallback + Yahoo Finance API. Ruled out as a friction source.

2. **Pine Script reference docs as dead weight**: The `reference/pinescriptv6-main/` directory is 210K tokens but frozen — it never changes and serves as a valid lookup resource. It does not contribute to churn or confusion.

3. **Git branching issues**: The 2 orphaned branch forks are harmless dead commits. The project correctly uses linear main-branch development. Ruled out.

4. **validation.py as a problem**: The walk-forward validation framework (346 lines) is solid, well-structured, and correctly parameterized. It is one of the few files that has remained stable after creation. Ruled out as a friction source.

5. **strategies.py quality**: The 7 strategy implementations are clean, well-documented, and follow a consistent interface. No issues found. Ruled out.

## Coverage Gaps

1. **Cannot verify indicator parity between Python engines and TradingView**: This requires running Pine Script in TradingView, which is outside the scope of a code analysis.

2. **Cannot measure actual optimization wall-clock time**: The `evolve-results-2026-04-03.json` shows 0.01 hours, but this may have been a test run. A real 8-hour run would provide much better convergence data.

3. **Cannot assess whether RSI Regime's 75.1% max drawdown is acceptable**: This is a risk tolerance question for the developer, not a code quality question.

4. **Remote/mobile session friction**: The `remote/` directory and remote session workflow suggest some work happens on mobile Claude. Cannot assess the friction of that workflow from code alone.

---

## File Manifest

| File | Action | Purpose |
|------|--------|---------|
| `Argus Reports/v6-artifacts/scratchpad-velocity-Apr-03.md` | Created | Investigation working notes |
| `Argus Reports/v6-artifacts/findings-velocity-Apr-03.md` | Created | This file — final findings |
