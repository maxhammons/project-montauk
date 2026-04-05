# Scratchpad — Velocity & Friction Specialist — Apr 03

## Investigation Protocol Tracking

### Phase A: Initial Hypotheses
1. H1: The optimization infrastructure is churning (rewrites without convergence) — Confidence: 70%
2. H2: Dead code accumulation from rapid rewrites is creating drag — Confidence: 60%
3. H3: Duplicate backtesting engines (backtest_engine.py vs strategy_engine.py) — Confidence: 80%
4. H4: The spike skill rewriting pattern is Groundhog Day behavior — Confidence: 65%
5. H5: Python-TradingView parity gap is growing and unvalidated — Confidence: 75%
6. H6: CLAUDE.md rewrite churn is AI-coordination overhead — Confidence: 70%
7. H7: Build vs maintain ratio is extremely skewed toward build — Confidence: 85%

### Phase B: Evidence Collection

#### Git Statistics
- 27 commits over 31 days (Mar 3 - Apr 3)
- Active development only on 4 dates: Mar 3, Mar 4, Apr 1, Apr 2, Apr 3
- 5 active development days, 26 idle days
- Burst pattern: 0 commits for 28 days, then 22 commits in 3 days

#### Churn Analysis (files touched in commits)
- CLAUDE.md: 7 commits (grew from 8 to 207 lines — 25x expansion)
- .claude/skills/spike.md: 5+ commits, 4 full rewrites (v1->v2->v3->v4)
- scripts/backtest_engine.py: 6 commits, significant restructuring each time
- remote/best-ever.json: 3 updates

#### Code Size Growth (Apr 1-3, 3 days)
- Day 0 (before Apr 1): 0 lines Python
- Day 3 (Apr 3 end): 4,676 lines Python across 12 files
- Growth rate: ~1,559 lines/day
- Lines per commit (Apr 1-3): avg ~450 lines added per commit

#### Duplicate Code Audit
- backtest_engine.py (990 lines): EMA, TEMA, ATR, highest, lowest, SMA, ADX functions + 8.2.1 strategy + regime detection + backtesting
- strategy_engine.py (624 lines): _ema, _rma, _sma, _tema, _atr, _highest, _lowest, _rsi, _stddev + Indicators class + backtest function
- OVERLAP: ema(), tema(), atr(), highest(), lowest(), sma(), adx() functions are implemented TWICE
- Both files have independent BacktestResult dataclasses
- Both files have independent Trade dataclasses
- Both files have independent backtest() functions
- Estimated duplication: ~300-400 lines

#### Dead Code Analysis
- spike_auto.py (601 lines): v3 optimizer. Now superseded by evolve.py (377 lines) + strategy_engine.py (624 lines)
- run_optimization.py (427 lines): v1-v3 CLI runner. Imports from backtest_engine.py (old system). The new system uses evolve.py
- spike_state.py (176 lines): State management for v1-v3 spike loop. evolve.py manages its own state
- signal_queue.json (289 lines): No imports reference this file. No commit message mentions it
- parity_check.py (184 lines): Only validates 8.2.1 parameters. Cannot validate RSI Regime or any v4 strategies
- generate_pine.py (142 lines): Only maps 8.2.1 parameter names. Cannot generate Pine for new strategies

Total dead/obsolete code: ~1,819 lines (39% of total Python codebase)

#### Spike Skill Rewrite Timeline
1. Apr 1 (4ad11e0): v1 created — 241 lines
2. Apr 1 (bbc39a4): v1 rewritten for unattended operation
3. Apr 2 (d17b39c): Optimization target rewritten (MAR -> Regime Score)
4. Apr 2 (e648644): v2 — true infinite loop, new-param proposal
5. Apr 2 (e56853b): v3 — bootstrap validation, plateau analysis
6. Apr 2 (daa4b31): v3 bump
7. Apr 3 (5dd806f): v4 — complete rewrite to multi-strategy

That's 7 modifications in 3 days — average lifespan of each version: ~10 hours.

#### Convergence Analysis
- v1-v3 all optimized the same architecture (8.2.1 EMA crossover)
- v4 discovered RSI Regime is fundamentally better
- The 3 rewrites of v1-v3 were optimizing the wrong thing
- However: the evolve run that found RSI Regime ran for only 0.01 hours (36 seconds) with 1,330 evaluations. The v3 run that found Combo G ran for 7.4 hours with unknown evals
- This suggests v4's architecture is vastly more efficient — but also that v1-v3 were expensive dead ends

#### Production Artifact Stasis
- src/strategy/active/Project Montauk 8.2.1.txt: last modified Mar 4 (31 days ago)
- src/indicator/active/Montauk Composite Oscillator 1.3.txt: last modified Mar 3 (initial commit)
- 4,387 lines of Python tooling orbit a Pine Script that has not changed
- The new RSI Regime Pine Script is in testing/ but not active/

#### Parity Gap
- Python 8.2.1 vs TradingView 8.2.1: documented discrepancy (Python CAGR 34.9%, TV 31.19%)
- parity_check.py only validates 8.2.1 parameters
- No parity validation exists for RSI Regime, breakout, golden cross, or any other v4 strategy
- The v4 strategies have NEVER been validated against TradingView

### Phase C: Hypothesis Updates
1. H1 (infrastructure churning): CONFIRMED at 90%. 4 complete rewrites in 3 days, 3 of which were dead ends. But v4 appears to be converging.
2. H2 (dead code drag): CONFIRMED at 85%. 39% of Python is dead/obsolete.
3. H3 (duplicate engines): CONFIRMED at 95%. Clear duplication of ~300-400 lines across two files.
4. H4 (spike skill Groundhog Day): PARTIALLY CONFIRMED at 75%. The rewrites weren't identical — each added real capability. But the velocity of full rewrites (vs incremental improvement) is wasteful.
5. H5 (parity gap): CONFIRMED at 90%. Growing gap, no automated validation for new strategies.
6. H6 (CLAUDE.md coordination overhead): CONFIRMED at 80%. 7 commits, 25x size growth. Necessary for AI context but high token cost.
7. H7 (build vs maintain ratio): CONFIRMED at 95%. 100% build, 0% maintain. Zero tests, zero CI.

### Coverage Tracking
- [x] Git log analysis (all 27 commits)
- [x] File touch frequency
- [x] Commit size distribution
- [x] Timeline analysis
- [x] backtest_engine.py (990 lines, read in full)
- [x] strategy_engine.py (624 lines, read in full)
- [x] evolve.py (377 lines, read in full)
- [x] spike_auto.py (601 lines, read in full)
- [x] strategies.py (394 lines, read in full)
- [x] run_optimization.py (427 lines, first 50 lines + understood structure)
- [x] validation.py (346 lines, read in full)
- [x] parity_check.py (184 lines, read in full)
- [x] generate_pine.py (142 lines, read in full)
- [x] data.py (126 lines, read in full)
- [x] spike_state.py (176 lines, read in full)
- [x] signal_queue.json (289 lines, noted as orphan)
- [x] spike.md skill (137 lines, read in full)
- [x] CLAUDE.md (207 lines, understood from context)
- [x] RSI Regime Pine Script (read first 30 lines)
- [x] remote/best-ever.json, evolve-results, spike-results
- [x] spike-2026-04-02.md report

### Key Metrics
- Git commits analyzed: 27/27
- Files read: 16/16 Python + JSON source files
- Churn rate: 7 modifications to spike.md in 3 days
- Groundhog Day files: spike.md (4 full rewrites), backtest_engine.py (6 significant changes)
- Regression rate: Cannot determine (no tests exist)
- Build vs maintain ratio: ~100:0
- Invisible work: CLAUDE.md maintenance (7 commits), remote/ directory management, file relocations
- Dead code %: 39% of Python codebase
