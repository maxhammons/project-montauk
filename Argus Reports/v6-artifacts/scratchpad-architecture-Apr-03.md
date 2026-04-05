# Architecture Scratchpad — Apr-03

## File Manifest

| # | File | Signal | Finding | Connects to |
|---|------|--------|---------|-------------|
| 1 | `scripts/backtest_engine.py` (~980 lines) | RED FLAG | Monolithic backtest with hardcoded 8.2.1 logic. Duplicated indicator functions (ema, tema, atr, etc.) also in strategy_engine.py. Two completely independent BacktestResult dataclasses exist. | H1, H2, H3 |
| 2 | `scripts/strategy_engine.py` (~625 lines) | RED FLAG | Re-implements all indicator functions from backtest_engine.py. Own Indicators class, own BacktestResult, own backtest() function. Parallel universe. | H1, H2 |
| 3 | `scripts/strategies.py` (~395 lines) | INTERESTING | 7 strategy functions, clean registry pattern. Imports from strategy_engine.py only. Cannot use backtest_engine.py's regime scoring or walk-forward validation. | H1, H2, H4 |
| 4 | `scripts/evolve.py` (~377 lines) | INTERESTING | Multi-strategy evolutionary optimizer. Has its own fitness function. Imports strategy_engine not backtest_engine. Cannot access regime scoring, validation, parity checking. | H1, H2, H4 |
| 5 | `scripts/run_optimization.py` (~427 lines) | RED FLAG | CLI runner that imports backtest_engine only. Only knows about Montauk 8.2.1. Cannot test strategies.py strategies. Orphaned from v4 architecture. | H1, H3 |
| 6 | `scripts/spike_auto.py` (~601 lines) | RED FLAG | v3 single-strategy optimizer. Own fitness function, own evolutionary operators. Imports backtest_engine. Superseded by evolve.py but still exists with 601 lines. | H3 |
| 7 | `scripts/data.py` (~127 lines) | CLEAN | Solid data fetcher. CSV + Yahoo API merge. Only fetched file. |  |
| 8 | `scripts/validation.py` (~347 lines) | INTERESTING | Walk-forward validation. Imports from backtest_engine only. Cannot validate v4 strategy results. | H1, H4 |
| 9 | `scripts/generate_pine.py` (~142 lines) | INTERESTING | Only maps 8.2.1 params. PARAM_MAP doesn't cover RSI Regime or other v4 strategies. Name misleading (says "generate" but only makes diffs). | H4 |
| 10 | `scripts/spike_state.py` (~177 lines) | CLEAN | Crash-safe JSON state management. Well-designed atomic writes. |  |
| 11 | `scripts/parity_check.py` (~185 lines) | INTERESTING | Only has TV reference data for 8.2.1 variants. Cannot check v4 strategies. No evidence of regular use. | H4, H5 |
| 12 | `scripts/signal_queue.json` (~289 lines) | INTERESTING | Signal backlog — 8 implemented, 12 queued. All signals are 8.2.1-specific entry/exit gates. Irrelevant to v4 multi-strategy approach. | H3 |
| 13 | `scripts/requirements.txt` (~3 lines) | CLEAN | Minimal deps: pandas, numpy, requests. |  |
| 14 | `src/strategy/active/Project Montauk 8.2.1.txt` (~403 lines) | INTERESTING | Production Pine Script. Last modified Mar 4. Contains features (conviction slider, groups 9-11) not replicated in Python engine. | H5 |
| 15 | `src/indicator/active/Montauk Composite Oscillator 1.3.txt` (~181 lines) | INTERESTING | Oscillator completely disconnected from all Python tooling. Components (TEMA slope, Quick EMA, MACD, DMI) overlap with strategy signals but not coupled. | H5 |
| 16 | `src/strategy/testing/Montauk RSI Regime.txt` (~97 lines) | INTERESTING | First non-8.2.1 Pine Script. Hand-written from Python logic. Different param names (entryRsi vs entry_rsi). | H4 |
| 17 | `src/strategy/testing/archive/Project Montauk 8.3-conservative.txt` | TRIVIAL | 8.2.1 clone with different defaults. |  |
| 18 | `src/strategy/testing/archive/Project Montauk 9.0-candidate.txt` | TRIVIAL | 8.2.1 clone with different defaults. |  |
| 19 | `src/strategy/testing/archive/backtest-comparison.md` | INTERESTING | Real TV numbers that exposed Python/TV parity gap. CAGR: Python 34.9% vs TV 31.19%. | H5 |
| 20 | `src/strategy/archive/Project Montauk 1.0 (FMC).txt` | TRIVIAL | Pine v5 MACD crossover. Genesis. |  |
| 21-26 | `src/strategy/archive/` (remaining 7 files) | TRIVIAL | Historical Pine Script versions, v5 and v6. Archive only. |  |
| 27-28 | `src/strategy/debug/` (2 files) | TRIVIAL | Debug builds with visual labels. |  |
| 29 | `src/indicator/archive/Montauk Composite Oscillator 1.0.txt` | TRIVIAL | Oscillator v1.0, archived. |  |
| 30 | `src/indicator/archive/Montauk Composite Oscillator 1.2.txt` | TRIVIAL | Oscillator v1.2, archived. |  |
| 31 | `reference/Montauk Charter.md` (~126 lines) | RED FLAG | Charter explicitly says "EMA-trend system" and "do not propose oscillators or countertrend buys." RSI Regime strategy directly violates this. | H4 |
| 32 | `CLAUDE.md` (~207 lines) | INTERESTING | Living documentation. Documents v4 architecture but still references v1-v3 CLI commands as primary. | H3 |
| 33 | `.claude/skills/spike.md` (~137 lines) | INTERESTING | v4 skill definition. Correctly describes evolve.py workflow. | |
| 34 | `.claude/settings.json` | INTERESTING | Allows write to /scripts/ and /remote/ only. Allows git push. | |
| 35 | `.gitignore` | CLEAN | Ignores .DS_Store, .claude/, __pycache__. | |
| 36 | `remote/best-ever.json` | INTERESTING | RSI Regime fitness 2.18. Different params from winners/ file (fitness 1.81). | H2 |
| 37 | `remote/evolve-results-2026-04-03.json` | INTERESTING | Only 19 generations, 1330 evals, 0.01 hours. Tiny run. tema_momentum returned fitness 0 (FAILED). | H2 |
| 38 | `remote/spike-state.json` | CLEAN | Empty initial state from v3 spike_state.py. | H3 |
| 39 | `remote/spike-progress.json` | INTERESTING | v3 spike_auto.py progress. Different best-ever from evolve.py. Shows v3 was also run today. | H3 |
| 40 | `remote/winners/rsi-regime-2026-04-03.json` | INTERESTING | Different RSI Regime params from best-ever.json (rsi_len=14 vs 10, exit_rsi=80 vs 85). Two incompatible "best" records. | H2 |
| 41 | `remote/spike-2026-04-02.md` | CLEAN | Thorough session report. Good documentation of validation process. | |
| 42 | `remote/diff-2026-04-02-8.3-conservative.txt` | TRIVIAL | Pine param diff. | |
| 43 | `remote/diff-2026-04-02-9.0-candidate.txt` | TRIVIAL | Pine param diff. | |
| 44 | `remote/report-2026-03-04.md` | TRIVIAL | Early report. | |
| 45-55 | `reference/pinescriptv6-main/` (all files) | TRIVIAL | Pine Script v6 reference docs. Not project code. | |
| 56 | `.claude/skills/about.md` | TRIVIAL | Claude skills description. | |
| 57 | `.claude/commands/sync.md` | TRIVIAL | Sync command. | |

**Total files catalogued: 57 source/config + 30 reference docs + 11 .DS_Store = 88**

---

## Hypotheses

### H1: Competing Architecture Schism (Confidence: 95%)
Two parallel backtesting worlds exist with no bridge:
- **backtest_engine.py** world: StrategyParams, run_backtest(), regime scoring, validation, parity check. Only knows 8.2.1.
- **strategy_engine.py** world: Indicators, backtest(), 7 strategy types. No regime scoring, no validation, no parity check.

Trajectory: 35% (initial scan) -> 85% (read both engines) -> 95% (confirmed no cross-imports)

### H2: Duplicated Indicator Code (Confidence: 95%)
ema(), tema(), atr(), sma(), highest(), lowest() are implemented TWICE — once in backtest_engine.py and once in strategy_engine.py. The implementations are nearly identical but not exactly: backtest_engine.py uses RMA for ATR, strategy_engine.py uses _rma for ATR. Both should produce the same output but were written independently.

Additionally, strategies.py has its own _ema_helper() that is a THIRD implementation of EMA (NaN-tolerant variant).

### H3: Dead Code Accumulation (Confidence: 90%)
- spike_auto.py (601 lines) — superseded by evolve.py
- run_optimization.py (427 lines) — partially superseded (still useful for 8.2.1 baseline/sweep/grid but cannot test v4 strategies)
- signal_queue.json (289 lines) — 12 queued signals that are 8.2.1-specific and irrelevant to v4 multi-strategy approach
- spike-state.json — initialized by v3 system, unused by v4
- spike-progress.json — written by spike_auto.py (v3), not evolve.py

### H4: Pine Script Generation Bottleneck (Confidence: 85%)
generate_pine.py only maps 8.2.1 parameters. If RSI Regime becomes production:
- No automated Pine generation for RSI Regime
- No automated Pine generation for ANY v4 strategy
- The RSI Regime Pine Script was hand-written, diverging from generate_pine.py's approach
- parity_check.py cannot validate v4 strategies against TradingView

### H5: Python-TradingView Parity Gap (Confidence: 80%)
backtest-comparison.md showed Python CAGR was 34.9% vs TradingView 31.19% for 8.3-conservative — a 12% overestimate. This gap will be WORSE for v4 strategies because:
- v4 strategies bypass backtest_engine.py entirely (use strategy_engine.py)
- strategy_engine.py has NO regime scoring
- No parity check infrastructure exists for v4 strategies
- The RSI Regime "3.49x vs buy-and-hold" claim is unverified against TradingView

---

## Running Observations (20+ required)

1. Two completely separate backtesting engines exist with no shared code
2. EMA is implemented three times across the codebase
3. spike_auto.py is 601 lines of dead code
4. The Montauk Charter says "do not propose oscillators or countertrend buys" — RSI Regime is an oscillator-based countertrend buy
5. best-ever.json and winners/rsi-regime.json have different RSI Regime params
6. evolve.py ran for only 0.01 hours (36 seconds) with 1330 evals before generating "best-ever" results
7. tema_momentum strategy returned fitness 0 (FAILED) — likely a bug in the strategy or indicator warmup
8. signal_queue.json has 12 queued signals that will never be implemented in the v4 architecture
9. generate_pine.py's PARAM_MAP only covers 8.2.1 parameters
10. The parity_check.py tolerance is extremely generous (30% for total return, 20% for avg bars)
11. strategy_engine.py has ~30 indicator methods, many never used by any strategy (e.g., psar, ichimoku, pivot, mfi, willr, cci)
12. backtest_engine.py checks for ema_long[i] but strategy_engine.py doesn't have a concept of "long EMA"
13. The breakout strategy in strategies.py has a stateful peak_since_entry variable that persists across the loop — this could cause incorrect behavior since entries[] fires every qualifying bar, not just on actual position entry
14. CLAUDE.md documents CLI tools from v1-v3 as the primary workflow, while spike.md correctly describes v4
15. .claude/settings.json allows git push but the project has no CI/CD — direct-to-main pushes with no safety net
16. The v4 fitness function in evolve.py (vs_bah * dd_penalty * freq_penalty) is completely different from v3's fitness in spike_auto.py (vs_bah * dd_penalty * regime_bonus * quality_guards)
17. validation.py's walk-forward windows extend to 2027-01-01 which is in the future — this is fine for expanding-window validation but looks odd
18. No Python tests exist anywhere in the project
19. The composite oscillator indicator uses completely different MACD/DMI parameters than anything in the Python strategies
20. backtest_engine.py's EMA cross exit checks emaShort vs emaLong (500-bar), but strategies.py montauk_821 checks ema_s vs ema_m (30-bar) — fundamentally different exit logic
21. The RSI Regime Pine Script uses ta.crossover(rsi, entryRsi) — exact cross — while the Python version uses `rsi[i-1] < entry_level and rsi[i] >= entry_level` — these should match but differences in bar-exact timing could diverge
22. strategies.py sets entries/exits as boolean arrays, then strategy_engine.py's backtest() handles position management — but entries fire on ALL qualifying bars (not just when flat), creating redundant entry signals that the engine must filter
23. The Indicators cache in strategy_engine.py uses tuple keys like ("ema", 15) — if a strategy passes a float length, the cache key differs from an int length call
