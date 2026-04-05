# Architecture Findings — Apr-03

**Specialist**: Architecture
**Files Investigated**: 88 (57 source/config + 30 reference docs + 11 .DS_Store)
**Scratchpad**: `Argus Reports/v6-artifacts/scratchpad-architecture-Apr-03.md`

---

## Finding 1: Competing Backtesting Architectures — Two Engines That Cannot Talk

**Confidence**: 95%
**Category**: Structural Fracture / Competing Architectures
**Files**: `scripts/backtest_engine.py`, `scripts/strategy_engine.py`, `scripts/strategies.py`, `scripts/evolve.py`, `scripts/run_optimization.py`, `scripts/validation.py`
**Git Evidence**: strategy_engine.py created Apr 3 (today). backtest_engine.py last modified Apr 2. No imports between the two.

**Claim**: The codebase contains two entirely independent backtesting engines that cannot interoperate. This is not a refactor-in-progress — it is an architectural schism where the v4 multi-strategy system (evolve.py + strategy_engine.py + strategies.py) operates in a parallel universe from the v3 single-strategy system (backtest_engine.py + run_optimization.py + validation.py + parity_check.py).

**Evidence**:
- `backtest_engine.py` defines: `StrategyParams`, `run_backtest()`, `BacktestResult` (with regime_score), `Trade`, `RegimeScore`, `detect_bear_regimes()`, `score_regime_capture()`
- `strategy_engine.py` defines: `Indicators`, `backtest()`, `BacktestResult` (without regime_score), `Trade` — completely separate classes with overlapping but non-identical fields
- `evolve.py` imports from `strategy_engine`, never from `backtest_engine`
- `run_optimization.py` imports from `backtest_engine`, never from `strategy_engine`
- `validation.py` imports from `backtest_engine` — the walk-forward framework cannot validate v4 strategies
- `parity_check.py` imports from `backtest_engine` — TV parity checking cannot verify v4 strategies

**Why This Matters**: The v4 system that discovered "RSI Regime beats 8.2.1 by 4.7x" has zero access to regime scoring, walk-forward validation, or TradingView parity checking. The fitness score driving strategy selection (evolve.py's `vs_bah * dd_penalty * freq_penalty`) is completely different from the validated scoring framework in backtest_engine.py. The project's most important finding — that RSI Regime should replace 8.2.1 — is running on an unvalidated engine.

**Proposed Fix**: Merge the two engines. Extract `Indicators` from strategy_engine.py as the shared indicator cache. Have `strategies.py` functions return entry/exit arrays. Wire those arrays into backtest_engine.py's position management (which already supports regime scoring, B&H comparison, trade logging). Delete strategy_engine.py's backtest() function and BacktestResult class. Wire evolve.py to use backtest_engine.py's infrastructure.
- **LOC**: ~200 lines of integration code, ~400 lines deleted
- **Effort**: 4-6 hours (careful — must preserve both engines' behavior during merge)

**Ripple Map**: evolve.py, strategies.py, run_optimization.py, validation.py, parity_check.py all need import changes. evolve.py's fitness function needs access to regime_score.

**If Not Fixed**: Every strategy discovered by the v4 optimizer will have unverified fitness scores. Decisions about whether to replace 8.2.1 will be based on metrics that have never been validated against TradingView. The parity gap (already 12% for 8.3-conservative) will be invisible for v4 strategies.

---

## Finding 2: Triple-Duplicated Indicator Code With Subtle Divergences

**Confidence**: 95%
**Category**: Accidental Complexity / Code Duplication
**Files**: `scripts/backtest_engine.py` (lines 131-236), `scripts/strategy_engine.py` (lines 29-128), `scripts/strategies.py` (lines 247-261)

**Claim**: The EMA function is implemented three times. ATR is implemented twice. SMA, TEMA, highest, and lowest are each implemented twice. The implementations are nearly identical but have subtle differences that could produce different outputs for edge cases.

**Evidence**:
- `backtest_engine.py::ema()` — standalone function, SMA seed, alpha = 2/(length+1)
- `strategy_engine.py::_ema()` — standalone function, SMA seed, alpha = 2/(length+1) — same logic
- `strategies.py::_ema_helper()` — different: NaN-tolerant, no SMA seed, starts from first valid value
- `backtest_engine.py::atr()` — uses RMA (alpha=1/period), explicit TR loop
- `strategy_engine.py::_atr()` — uses `_rma()` (alpha=1/period) — same smoothing but different code path
- `backtest_engine.py::adx()` — uses Wilder's smoothing with running sum approach (lines 200-235)
- `strategy_engine.py::_adx()` — uses `_rma()` on DX directly (line 437) — structurally different computation

**Why This Matters**: If a strategy's behavior differs between the two engines due to floating-point divergence in indicator calculations, the v4 optimizer could select winners that don't reproduce in the v3 validation framework. The ADX implementation difference is the most concerning — one uses running-sum Wilder's smoothing, the other uses RMA on DX values. These could produce materially different ADX values, especially during the warmup period.

**Proposed Fix**: Create a single `indicators.py` module. Both engines import from it. Delete duplicates.
- **LOC**: ~150 lines new file, ~300 lines deleted across backtest_engine.py and strategy_engine.py
- **Effort**: 2-3 hours

**Ripple Map**: backtest_engine.py and strategy_engine.py both need to import from the new module. All indicator function calls must be updated if signatures change.

**If Not Fixed**: Indicator divergence will accumulate as more complex indicators are added. A strategy that tests well in evolve.py may produce different results when validated through backtest_engine.py's regime scoring.

---

## Finding 3: 1,028 Lines of Dead Code From Superseded Architectures

**Confidence**: 90%
**Category**: Dead Code / Architecture Debt
**Files**: `scripts/spike_auto.py` (601 lines), `scripts/signal_queue.json` (289 lines), `remote/spike-state.json`, `remote/spike-progress.json`

**Claim**: spike_auto.py (v3 optimizer) and signal_queue.json (v3 signal backlog) are dead code. The v4 architecture (evolve.py + strategies.py) has completely replaced their function. They remain in the codebase as confusion vectors.

**Evidence**:
- spike_auto.py imports from `backtest_engine` and only optimizes StrategyParams (Montauk 8.2.1). It cannot test v4 strategies.
- The spike.md skill file now describes the v4 workflow (evolve.py + strategies.py). No reference to spike_auto.py.
- signal_queue.json lists 12 "queued" signals that are all 8.2.1-specific entry/exit gates (e.g., "bollinger_width_gate", "higher_lows_gate"). In the v4 architecture, new strategies are added as functions in strategies.py — not as togglable gates on a single strategy.
- spike-progress.json was written by spike_auto.py's `save_progress()` function. It shows a separate best-ever (fitness 0.6861) from a different scoring system than evolve.py's best-ever (fitness 2.1803).
- spike-state.json contains an empty v3 state initialization from today (2026-04-03T13:27:17), suggesting spike_auto.py was briefly started then abandoned in favor of evolve.py.

**Why This Matters**: A future Claude session could invoke spike_auto.py instead of evolve.py and spend 8 hours optimizing the wrong system. The two systems have different fitness functions, different search spaces, and different result files. CLAUDE.md still documents run_optimization.py CLI commands as the primary interface.

**Proposed Fix**: 
1. Move spike_auto.py and signal_queue.json to an `archive/` directory (or delete — git preserves history)
2. Remove v3 CLI documentation from CLAUDE.md
3. Consolidate spike-state.json and spike-progress.json into a single v4 state mechanism
- **LOC**: 0 new lines (just deletions/moves)
- **Effort**: 30 minutes

**Ripple Map**: CLAUDE.md needs updating. Any Claude sessions referencing old CLI commands need redirection.

**If Not Fixed**: Confusion about which optimizer to run. Two competing "best-ever" results. Wasted compute on abandoned architectures.

---

## Finding 4: Charter Violation — RSI Regime Contradicts the Project's Governing Document

**Confidence**: 85%
**Category**: Architecture Governance / Identity Crisis
**Files**: `reference/Montauk Charter.md`, `scripts/strategies.py` (rsi_regime function), `src/strategy/testing/Montauk RSI Regime.txt`, `remote/best-ever.json`

**Claim**: The Montauk Charter explicitly defines the project as "a long-only, single-position EMA-trend system" and states "do not propose oscillators or countertrend buys as primary logic." The RSI Regime strategy — now the #1 ranked strategy — is an oscillator-based mean-reversion system. The project has pivoted without updating its governing document.

**Evidence**:
- Charter Section 2: "Core entry: emaShort > emaMed AND trend EMA slope > threshold. Do not propose oscillators or countertrend buys as primary logic."
- Charter Section 8: "If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly: 'Out of scope per Montauk charter.'"
- RSI Regime entry logic: "RSI crosses up through 35 AND price above trend EMA" — this is an oscillator-driven mean-reversion entry
- RSI Regime is now the #1 strategy with fitness 2.18 vs 8.2.1's 0.46

**Why This Matters**: The Charter serves as the Claude context that shapes all future development. If a session reads the Charter first (as instructed), it will correctly reject RSI-based approaches as "out of scope." This creates a conflict: the optimizer discovered something better, but the governance document says it's not allowed. This tension needs explicit resolution — either the Charter evolves or the finding is deliberately set aside.

**Proposed Fix**: Update the Charter to reflect the project's actual evolution. Options:
1. **Expand scope**: Change "EMA-trend system" to "regime-detection system" and allow any entry logic that captures bull legs and avoids bear legs
2. **Fork**: Keep the Charter for 8.2.1, create a separate "Montauk v2 Charter" for multi-strategy exploration
3. **Retire**: Acknowledge that the Charter governs Pine Script changes to 8.2.1 only, while the Python optimizer is free to explore any approach
- **LOC**: ~20 lines of Charter edits
- **Effort**: 30 minutes (writing); the actual decision is the hard part

**Ripple Map**: All future Claude sessions that read the Charter. The spike.md skill. The generate_pine.py deployment path.

**If Not Fixed**: Claude sessions will oscillate between "follow the Charter" and "follow the optimizer's results." Inconsistent behavior across sessions. Risk of a session reverting RSI Regime work because the Charter says to.

---

## Finding 5: Pine Script Generation Is a Bottleneck — Only 8.2.1 Has a Path to Production

**Confidence**: 85%
**Category**: Missing Abstraction / Deployment Gap
**Files**: `scripts/generate_pine.py`, `src/strategy/testing/Montauk RSI Regime.txt`, `scripts/parity_check.py`

**Claim**: The "deployment layer" (Python -> Pine Script) only supports Montauk 8.2.1. For any v4 strategy to reach TradingView, someone must hand-write Pine Script. This negates the v4 system's primary value proposition of discovering better strategies automatically.

**Evidence**:
- `generate_pine.py`'s `PARAM_MAP` contains only 8.2.1 parameter names (27 entries, all EMA/ATR/TEMA-related)
- The RSI Regime Pine Script (`Montauk RSI Regime.txt`) was hand-written by Claude, not generated
- RSI Regime Pine uses different parameter naming (entryRsi, exitRsi, panicRsi) than the Python version (entry_rsi, exit_rsi, panic_rsi)
- `parity_check.py`'s TV_REFERENCE dict only has 8.2.1, 8.3, and 9.0 — all 8.2.1 variants
- No mechanism exists to validate v4 strategies against TradingView

**Why This Matters**: The optimizer can breed 7+ strategy types, but only one can be deployed without manual intervention. If the project continues adding strategy types (the trajectory suggests it will), each new winner requires a separate hand-written Pine Script, separate parity validation reference data, and separate TradingView testing. The automated pipeline stops at Python.

**Proposed Fix**: Create a template-based Pine generator that maps strategy functions to Pine Script blocks. Each strategy in STRATEGY_REGISTRY should have a corresponding Pine template. Alternatively, for the immediate RSI Regime case: add RSI Regime to parity_check.py with TradingView reference data, and add RSI Regime params to generate_pine.py.
- **LOC**: ~200 lines for template system, or ~50 lines for RSI Regime-specific addition
- **Effort**: 4-8 hours (template system) or 1-2 hours (RSI Regime only)

**Ripple Map**: generate_pine.py, parity_check.py, and any future strategy deployment workflow.

**If Not Fixed**: Every new strategy type requires manual Pine Script authorship. The optimizer discovers winners faster than they can be deployed and validated. The Python-TradingView parity gap widens invisibly.

---

## Finding 6: montauk_821 in strategies.py Is NOT Faithful to backtest_engine.py

**Confidence**: 92%
**Category**: Logic Divergence / Parity Bug
**Files**: `scripts/strategies.py` (lines 26-78), `scripts/backtest_engine.py` (lines 720-757)

**Claim**: The montauk_821() function in strategies.py is a simplified approximation of the 8.2.1 logic in backtest_engine.py. Critical differences exist that make the two produce different trade signals on the same data.

**Evidence**:
1. **EMA Cross Exit**: backtest_engine.py checks `emaShort < emaLong` (500-bar EMA) with barssince-style confirmation window scanning. strategies.py checks `ema_s < ema_m` (30-bar EMA) with a simple buffer check. These are fundamentally different exits — one uses a 500-bar long EMA, the other uses a 30-bar medium EMA.
2. **Missing features in strategies.py version**: No TEMA filters, no sideways filter, no trailing stop, no TEMA slope exit, no volume spike exit, no sell confirmation window, no cooldown (handled by caller, but differently), no ADX filter, no ROC filter, no bear guard, no asymmetric ATR exit.
3. **Exit priority**: backtest_engine.py evaluates exits in priority order (EMA Cross > ATR > Quick EMA > Trail > TEMA > Vol Spike). strategies.py uses `continue` statements that skip remaining checks but the priority is ATR > Quick EMA > EMA Cross — reversed.

**Why This Matters**: When evolve.py compares montauk_821's fitness (0.46) against rsi_regime's fitness (2.18), the 8.2.1 baseline is fighting with one arm tied behind its back. The real 8.2.1 with all its filters and the correct 500-bar long EMA exit would score differently. The 4.7x improvement claim for RSI Regime is based on a weakened baseline.

**Proposed Fix**: Either:
1. Wire strategies.py's montauk_821 to import and call backtest_engine.py's run_backtest() directly (with result adaptation)
2. Make montauk_821() in strategies.py faithful to the full 8.2.1 logic including all exit paths and the correct EMA lengths
- **LOC**: ~100 lines to fix montauk_821, or ~30 lines for the import-and-delegate approach
- **Effort**: 2-3 hours (must verify parity with backtest_engine.py)

**Ripple Map**: evolve.py rankings. best-ever.json. Any comparison between 8.2.1 and other strategies.

**If Not Fixed**: The evolutionary optimizer's baseline is wrong. All relative fitness comparisons are unreliable. The "RSI Regime is 4.7x better" narrative may collapse when tested against the real 8.2.1.

---

## Finding 7: Breakout Strategy Has a State Management Bug

**Confidence**: 80%
**Category**: Logic Bug
**Files**: `scripts/strategies.py` (lines 154-197)

**Claim**: The breakout() strategy maintains a `peak_since_entry` variable as local state within the loop, but this state is not properly reset because the function doesn't know when the backtester actually enters/exits positions.

**Evidence**:
- Line 166: `peak_since_entry = np.nan` initialized before the loop
- Line 178-182: Peak tracking updates whenever peak_since_entry is not NaN, regardless of whether the backtester is actually in a position
- Line 194-195: Peak resets to cl[i] on entry bars. But entries[] is True on ALL qualifying bars, not just actual position entries (the backtester filters based on position state). If the strategy sets entries[i] = True on bar 100 and bar 105, peak tracking starts on bar 100 even if the backtester was already in a position and ignores the second entry.
- Line 182-183: Trail stop exit sets peak_since_entry = np.nan and continues — but the next bar will immediately see entries[i] potentially True again, resetting peak tracking

**Why This Matters**: The breakout strategy is ranked #2 (fitness 0.5049) in the optimizer results. If its peak tracking is incorrect, its fitness score is unreliable. The strategy may be generating spurious trail stop exits that inflate its apparent risk management.

**Proposed Fix**: Strategy functions should not maintain position-dependent state. The backtester should handle trailing stops (as backtest_engine.py already does). Alternatively, strategies.py could receive a "position" array from the backtester to condition state updates.
- **LOC**: ~20 lines to fix the breakout function
- **Effort**: 1 hour

**Ripple Map**: Breakout strategy ranking. Any strategy that needs position-aware state.

**If Not Fixed**: The #2 ranked strategy's fitness is unreliable.

---

## Finding 8: The Evolve Run Was Trivially Short — Results Are Statistically Meaningless

**Confidence**: 88%
**Category**: Process / Data Quality
**Files**: `remote/evolve-results-2026-04-03.json`, `remote/best-ever.json`

**Claim**: The evolutionary optimizer that produced the "RSI Regime beats 8.2.1 by 4.7x" finding ran for 0.01 hours (36 seconds) with only 1,330 evaluations across 19 generations. The spike.md skill file says to run for 8 hours with 500,000+ evaluations. The results are from a trivially short test run that hasn't converged.

**Evidence**:
- `evolve-results-2026-04-03.json`: `"elapsed_hours": 0.01`, `"total_evaluations": 1330`, `"generations": 19`
- spike.md: "~500,000+ evaluations in 8 hours"
- tema_momentum returned fitness 0 (FAILED completely) — not enough time to explore its parameter space
- Only 7 strategies × ~10 evals/strategy/generation × 19 generations = 1,330 evals
- No walk-forward validation was performed on the results
- No convergence plateau was reached (only 19 generations)

**Why This Matters**: 19 generations of a population-40 evolutionary algorithm is not enough to explore ANY strategy's parameter space, let alone 7 strategies simultaneously. The RSI Regime's dominance may simply reflect that its default midpoint parameters happen to be good, while other strategies need more exploration. The best-ever.json file has been overwritten with these preliminary results.

**Proposed Fix**: This is a process issue, not a code issue. The results should be treated as preliminary. A full 8-hour run should be executed before any production decisions.
- **LOC**: 0
- **Effort**: 8 hours (wall clock)

**Ripple Map**: All conclusions about strategy rankings. The RSI Regime Pine Script. Any deployment decisions.

**If Not Fixed**: Production strategy decisions based on a 36-second test run.

---

## Finding 9: Two Incompatible "Best Ever" Records Exist

**Confidence**: 92%
**Category**: Data Integrity
**Files**: `remote/best-ever.json`, `remote/winners/rsi-regime-2026-04-03.json`, `remote/spike-progress.json`

**Claim**: Three different "best" records exist with different parameters, different fitness values, and from different scoring systems.

**Evidence**:
- `best-ever.json`: RSI Regime, fitness 2.18, rsi_len=10, exit_rsi=85 (from evolve.py)
- `winners/rsi-regime.json`: RSI Regime, fitness 1.81, rsi_len=14, exit_rsi=80 (from earlier run, different params)
- `spike-progress.json`: Montauk 8.2.1 variant, fitness 0.69, regime_score metric (from spike_auto.py v3)

The "fitness" values are not comparable: evolve.py uses `vs_bah * dd_penalty * freq_penalty`, spike_auto.py uses `vs_bah * dd_penalty * regime_bonus * quality_guards`. A fitness of 2.18 in one system does not mean the same thing as 0.69 in the other.

**Why This Matters**: If a future session reads best-ever.json without understanding which system produced it, it will compare fitness values from incompatible scoring systems. The winners/ directory suggests a curation step happened, but the curated record has worse fitness and different params than best-ever.json.

**Proposed Fix**: 
1. Include the scoring system version in all result files (e.g., `"scoring": "evolve_v4"`)
2. Clear stale state files when switching optimizer versions
3. Add a `"generated_by"` field to best-ever.json
- **LOC**: ~10 lines across evolve.py and spike_auto.py
- **Effort**: 30 minutes

**Ripple Map**: Any session that reads best-ever.json. Future optimizer runs that load previous best.

**If Not Fixed**: Silent comparison of incompatible metrics. Wrong baseline for future optimization runs.

---

## Finding 10: No Tests, No CI, No Safety Net — Direct Push to Main

**Confidence**: 95%
**Category**: Missing Infrastructure
**Files**: `.claude/settings.json`, `.gitignore`, entire `scripts/` directory

**Claim**: The project has zero automated tests, zero CI/CD, and the Claude settings allow direct git push to main. For a financial trading system where code correctness directly affects real money, this is a significant gap.

**Evidence**:
- Scout context confirms: "Tests: 0", "CI/CD: None"
- `.claude/settings.json` allows `Bash(git push *)` — direct push to main
- CLAUDE.md explicitly instructs: "Commit and push directly to `main` — do not create a new branch"
- backtest_engine.py has 980 lines of financial calculation logic with no tests
- The EMA cross exit bug (documented in history context) went undetected through 8 major versions — a single unit test would have caught it
- parity_check.py exists but is not run automatically — it requires manual invocation

**Why This Matters**: Trading strategies have a financial blast radius. A bug in the EMA calculation could produce false entry signals. A bug in the position management could create phantom trades. The existing parity_check.py proves the project's author values correctness (they built a manual verification tool), but correctness is not enforced.

**Proposed Fix**:
1. Add basic tests for indicator functions (compare against known values)
2. Add regression tests using parity_check.py's reference data
3. Add a pre-commit hook that runs parity_check.py
4. Consider branch protection (even for solo developers, a "push to main" gate helps)
- **LOC**: ~200 lines of test code
- **Effort**: 3-4 hours

**Ripple Map**: All future code changes. Development velocity (tests catch bugs faster than manual TradingView comparison).

**If Not Fixed**: Bugs detected only when TradingView results diverge from expectations. The 8.2.1 EMA cross bug survived through 8 versions — future bugs could survive equally long.

---

## Finding 11: The Composite Oscillator Is an Orphan

**Confidence**: 85%
**Category**: Architecture Drift / Orphaned Component
**Files**: `src/indicator/active/Montauk Composite Oscillator 1.3.txt`, `scripts/strategies.py`, `scripts/backtest_engine.py`

**Claim**: The Composite Oscillator (the project's only indicator) is completely disconnected from all Python tooling and has no relationship to any v4 strategy. Its components (TEMA 300-bar slope, Quick EMA 7-bar, MACD 30/180/20, DMI 60-bar) use parameters that don't match any strategy in either the Python or Pine Script systems.

**Evidence**:
- Oscillator MACD: 30/180/20. No Python strategy or backtest_engine.py uses these MACD parameters.
- Oscillator TEMA: 300-bar. backtest_engine.py uses 200-bar TEMA.
- Oscillator DMI: 60-bar ADX with 30-bar smoothing. backtest_engine.py uses 14-bar ADX.
- The oscillator is a separate TradingView script (not an overlay). It provides "visual confirmation" but has no programmatic connection to entry/exit decisions.
- No Python code references the oscillator's component values or thresholds.
- If RSI Regime becomes production, the oscillator's EMA-focused components are irrelevant.

**Why This Matters**: The oscillator is the only visual diagnostic tool for the trading system. If it is measuring different things than the strategy uses for decisions, it provides false confidence or false alarm signals to the user watching TradingView.

**Proposed Fix**: Either update the oscillator to reflect the active strategy's actual decision signals, or document it as a standalone tool not tied to strategy logic.
- **LOC**: ~50 lines of Pine Script changes, or ~5 lines of documentation
- **Effort**: 1-2 hours

**Ripple Map**: User's TradingView setup. Visual decision-making while monitoring trades.

**If Not Fixed**: The indicator provides visual signals that don't correspond to the strategy's actual entry/exit logic.

---

## What I Investigated and Ruled Out

1. **Data integrity issues in data.py**: Investigated the CSV + Yahoo merge logic. The overlap prevention (`yf_df["date"] > csv_last_date`) is correct. The CSV has proper column names. No issues found.

2. **Indicator calculation correctness**: Compared EMA implementations across all three files. The core formula (alpha = 2/(length+1), SMA seed) is identical in backtest_engine.py and strategy_engine.py. The _ema_helper in strategies.py is different but only used by bollinger_squeeze — a secondary strategy.

3. **Position management bugs in strategy_engine.py::backtest()**: Reviewed the full backtest loop (lines 495-624). Cooldown handling, equity tracking, and trade closing logic appear correct. The same-bar exit-then-entry sequence is handled properly (exit processes first, then entry checks position == 0).

4. **State file corruption risk in spike_state.py**: The atomic write pattern (write to temp, os.replace) is correct and crash-safe on all major OS.

5. **Pine Script syntax issues**: Checked 8.2.1 against Pine v6 reference. All built-in function calls are valid v6 syntax. The `barssince(crossunder)` fix is correctly implemented.

6. **Over-fitting in validation.py**: The walk-forward windows are non-overlapping and expanding. The named windows cover the Charter's required stress tests. The stability check with 10% perturbation is a reasonable anti-overfitting measure. No issues found with the validation framework itself — the issue is that v4 strategies can't use it.

---

## Coverage Gaps

1. **Pine Script archive files (8 files)**: Read headers only for versions 1.0-8.1. Did not perform line-by-line review of archived strategies. Low risk — these are historical and frozen.

2. **Pine Script v6 reference docs (30 files)**: Not reviewed — these are third-party reference material, not project code.

3. **Performance profiling**: Did not assess computational efficiency of the Python engines. The indicator functions use Python loops (not vectorized numpy) which will be slow for large datasets. This may limit the optimizer's evaluation throughput.

4. **CSV data quality**: Did not validate the TECL Price History CSV against an independent source. If the CSV has errors, all backtest results are affected.

5. **Remote session artifacts**: Several remote/ files exist from mobile Claude sessions (report-2026-03-04.md, diff files). Did not verify their consistency with current codebase state.
