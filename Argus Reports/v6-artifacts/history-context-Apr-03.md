# History Context — Apr-03

## Timeline of Major Decisions

### Era 1: Pine Script Genesis (Mar 3-4, 2026)
- **Mar 3**: Initial commit drops 55 files, 55,184 lines. This is not a greenfield project — it is the import of an already-mature Pine Script trading system (versions 1.0 through 8.2) into git for the first time. The version archive goes back through at least 8 major generations.
- **Mar 3**: Bug audit of 8.2 discovers a **critical bug**: the EMA Cross Exit never fires with default settings because `ta.crossunder` (true only on the exact cross bar) is AND'd with an N-bar confirmation window that requires the prior bar to already be below. These conditions are mutually exclusive when `sellConfirmBars >= 2`. The strategy had been silently falling back to ATR and Quick EMA exits only.
- **Mar 4**: Version 8.2.1 is created — the fix uses `barssince(crossunder) < confirmBars` instead, allowing the exit to fire within the confirmation window. This becomes the production strategy and has not been modified since.

### Era 2: The Optimization Pivot (Apr 1, 2026)
- **Apr 1**: Massive architectural decision — instead of manually tweaking Pine Script, build a Python backtesting engine that replicates 8.2.1's logic. This is the `/spike` skill. The bet: Python can evaluate parameter combinations 1000x faster than TradingView.
- **Apr 1**: Immediate dependency issue — yfinance library removed in favor of direct Yahoo Finance API calls (within hours of initial commit). First sign of a pattern: the Python tooling gets rewritten frequently.
- **Apr 1**: `/spike` skill itself gets rewritten for "fully unattended operation" — designed to run overnight with no human input.

### Era 3: The Metric Rewrite (Apr 2, 2026)
- **Apr 2 (early)**: Load-bearing decision — optimization target rewritten from MAR (CAGR/MaxDD) to Regime Score. This is philosophical: the system's purpose is not "maximize returns" but "be in the market during bulls, be out during bears." Bull capture and bear avoidance become the primary fitness function.
- **Apr 2 (mid)**: Buy-and-hold comparison metric (vs_bah) added. This becomes the most-cited number in results: does the strategy beat simply holding TECL?
- **Apr 2**: Spike v2 adds true infinite loop, new-param proposal phase, compact reports. Then v3 immediately follows with bootstrap validation and plateau analysis.
- **Apr 2**: **First major result**: Combo G achieves vs_bah > 1.0 (1.135x), RS=0.603. This is the session winner after ~7.4 hours of automated optimization. Walk-forward validation passes all 4 windows. However, the vol_spike_mult plateau width is only 1 — fragile.

### Era 4: Multi-Strategy Divergence (Apr 3, 2026 — today)
- **Apr 3**: Spike v4 is a ground-up rewrite — from single-strategy parameter optimizer to multi-strategy evolutionary optimizer. Adds 7 completely new strategy archetypes (RSI Regime, Breakout, Golden Cross, Bollinger Squeeze, Trend Stack, TEMA Momentum) alongside the original Montauk 8.2.1. Each strategy is a ~20-line Python function in `strategies.py`. A new `strategy_engine.py` (624 lines) and `evolve.py` (377 lines) support this.
- **Apr 3**: The RSI Regime strategy immediately dominates. Fitness 2.18 vs Montauk 8.2.1's 0.46. vs_bah of 3.49x. Only 0.7 trades/year. The system is telling the developer that the entire EMA-crossover approach (versions 1.0 through 8.2.1) may be inferior to a simple RSI mean-reversion strategy.
- **Apr 3**: Pine Script for RSI Regime is generated and placed in `src/strategy/testing/`. This is the first time a non-Montauk strategy architecture has been produced.

## Velocity Map

### Hypersonic (multiple rewrites per day)
- `scripts/backtest_engine.py` — 6 commits, touched on 4 different dates. The core Python backtester. Added 6 new parameter groups in a single session.
- `.claude/skills/spike.md` — 5 commits, rewritten from v1 through v4. The skill definition drives what Claude does, so each rewrite is effectively a new optimization philosophy.
- `scripts/run_optimization.py` — 3 commits. CLI runner, evolving with the engine.
- `remote/best-ever.json` — 3 updates. The "high score" file. Started as Montauk 8.2.1 parameter tuning, now holds RSI Regime results.

### Fast (changing within days)
- `scripts/strategies.py`, `scripts/strategy_engine.py`, `scripts/evolve.py` — all brand new as of today (Apr 3). v4 architecture.
- `remote/spike-state.json` — session state, updated each run.
- `CLAUDE.md` — 7 commits. Grew from 8 lines to 207 lines. Acts as living documentation that co-evolves with the codebase.

### Frozen (untouched since creation)
- `src/strategy/active/Project Montauk 8.2.1.txt` — last modified Mar 4. The production Pine Script. 31 days without a change despite 27 commits of optimization work. The Python tooling orbits around it but never touches it.
- `src/indicator/active/Montauk Composite Oscillator 1.3.txt` — last modified Mar 3 (initial commit). Completely untouched.
- `src/strategy/archive/` — all files frozen at initial commit.
- `reference/` — frozen at initial commit.
- `scripts/data.py` — only 1 commit (Yahoo API rewrite), then stable. Data fetching is solved.

## Active Evolution vs Stable Zones

```
ACTIVE EVOLUTION                          STABLE / FROZEN
================================          ================================
scripts/backtest_engine.py    [6x]        src/strategy/active/8.2.1     [2x, last Mar 4]
.claude/skills/spike.md       [5x]        src/indicator/active/1.3      [1x, Mar 3]
scripts/run_optimization.py   [3x]        src/strategy/archive/*        [1x, Mar 3]
remote/best-ever.json         [3x]        reference/*                   [1x, Mar 3]
CLAUDE.md                     [7x]        scripts/data.py               [1x, Apr 1]
scripts/strategies.py         [NEW]       scripts/generate_pine.py      [2x, stable]
scripts/strategy_engine.py    [NEW]       scripts/validation.py         [2x, stable]
scripts/evolve.py             [NEW]
```

The pattern is clear: the **meta-tooling** (how to search for better strategies) is the active frontier. The **production artifacts** (what actually runs in TradingView) are frozen. The optimization infrastructure has grown from 0 to 4,387 lines of Python in 3 days while the thing it optimizes (8.2.1) has not changed.

## Abandoned Approach Inventory

### 1. Remote Scripts Duplication (created Apr 1, deleted Apr 2)
- An entire copy of `scripts/` was created inside `remote/scripts/` — likely from a mobile Claude session that could not find the root scripts. Also `remote/remote/spike-state.json` (nested remote dir). Cleaned up in commit `386b214`.
- **Artifact risk**: None, fully cleaned.

### 2. Candidate Pine Script Files (created Apr 2, deleted Apr 2)
- `remote/candidate-2026-04-02-9.0-candidate-A.txt` and `-B.txt` were generated then removed.
- Replaced by the diff-based approach (`remote/diff-2026-04-02-*.txt`) which is more maintainable.
- **Artifact risk**: None, fully cleaned.

### 3. MAR as Primary Metric (created Apr 1, replaced Apr 2)
- The original optimization target was MAR (CAGR / Max Drawdown). This was replaced by Regime Score within 24 hours. The old MAR-based results are no longer referenced.
- **Artifact risk**: Low. `backtest_engine.py` still computes MAR but it is now secondary.

### 4. Single-Strategy Optimization (spike v1-v3, created Apr 1-2, superseded Apr 3)
- The entire v1-v3 spike approach focused on tuning Montauk 8.2.1's parameters. Spike v4 replaces this with multi-strategy evolution. The old `run_optimization.py` and `spike_auto.py` still exist but may be dead code now that `evolve.py` + `strategy_engine.py` handle optimization.
- **Artifact risk**: MEDIUM. `spike_auto.py` (601 lines) and `run_optimization.py` (427 lines) may be orphaned. The spike skill now points to the v4 architecture but these files remain.

### 5. Screenshot Comparison Approach (created Apr 3, deleted Apr 3)
- 13 TradingView screenshots were committed for visual comparison of 8.2.1 vs 8.3 vs 9.0, then immediately deleted and moved to `testing/archive/`. The backtest-comparison.md survived.
- **Artifact risk**: None for the screenshots. The comparison results in `backtest-comparison.md` are valuable — they show real TradingView numbers that revealed the Python engine's CAGR estimates were optimistic (Python said 8.3 would get ~34.9% CAGR; TradingView showed 31.19%).

### 6. Orphaned Branch Commits
- Two small branch forks visible in git graph: `9ae2939 commit` (orphaned from initial) and `4e23b2f 8.2.1` + `4a180f7 clean` (orphaned from bug audit). These are harmless dead branches.

## Trajectory Predictions

### 1. RSI Regime Will Become Production (HIGH confidence)
The evolutionary optimizer found RSI Regime with fitness 2.18 vs Montauk 8.2.1's 0.46 — a 4.7x improvement. vs_bah of 3.49x vs 0.63x. The system is strongly signaling that the EMA-crossover paradigm (8 major versions over months) is inferior to RSI mean-reversion for TECL. The Pine Script has already been generated. Expect `src/strategy/active/` to change for the first time in a month within the next 1-2 sessions. However, the 100% win rate on only 10 trades and 75.1% max drawdown are red flags that need walk-forward validation.

### 2. The Python Engine Will Continue Growing (HIGH confidence)
The `scripts/` directory has grown from 0 to 4,387 lines in 3 days with no signs of slowing. The v4 architecture (multi-strategy evolution) is clearly the direction. Expect more strategy functions in `strategies.py`, more sophisticated fitness scoring, and potentially a portfolio/ensemble layer.

### 3. Dead Code Accumulation Risk (MEDIUM confidence)
Each spike version has left behind infrastructure. `spike_auto.py` (v3 runner, 601 lines) and parts of `run_optimization.py` (v1-v3 CLI) may already be dead. `parity_check.py` and `signal_queue.json` exist but were never mentioned in any commit message — likely created by a session and never used again. If v5 arrives, more code will be orphaned without cleanup.

### 4. Python-TradingView Parity Gap Will Widen (MEDIUM confidence)
The backtest comparison already showed discrepancies: Python estimated 34.9% CAGR for 8.3, TradingView measured 31.19%. As the Python engine adds more strategy types (RSI Regime, Breakout, etc.), each new strategy needs a separate parity validation against TradingView. The `parity_check.py` script exists for this but shows no evidence of regular use.

### 5. The Indicator Is Being Left Behind (HIGH confidence)
The Composite Oscillator 1.3 has not been touched since day one. If RSI Regime becomes the active strategy, the existing oscillator (built around TEMA slope, Quick EMA, MACD, and DMI) will be irrelevant to the new approach. Expect either a rewrite or abandonment.

## "What the Codebase is Trying to Become"

Project Montauk started as a **Pine Script trading strategy** — a hand-tuned indicator system for TECL that evolved through 8+ versions of manual iteration in TradingView.

It is becoming an **AI-driven strategy discovery platform**. The Pine Script is no longer the thing being developed — it is the deployment target. The actual development happens in Python, where Claude writes strategy functions, an evolutionary optimizer breeds them through hundreds of generations, and the winners get compiled to Pine Script for TradingView deployment.

The key inflection point was Apr 3 (today): the shift from "optimize parameters for a fixed strategy architecture" (spike v1-v3) to "evolve across multiple strategy architectures" (spike v4). This is a qualitative leap — the system no longer assumes EMA crossovers are the right approach. It discovered that RSI mean-reversion outperforms 8 months of hand-tuned EMA logic by nearly 5x on the primary fitness metric.

The codebase is converging toward a three-layer architecture:
1. **Strategy Layer** (`strategies.py`): Small, composable Python functions that define entry/exit logic. Disposable and cheap to write.
2. **Evolution Layer** (`evolve.py` + `strategy_engine.py`): Infrastructure that breeds, mutates, and evaluates strategy populations. This is the load-bearing investment.
3. **Deployment Layer** (`generate_pine.py`): Translates winners into TradingView-compatible Pine Script. Currently only supports Montauk 8.2.1's structure — will need expansion for RSI Regime and other winners.

The risk: the gap between "what Python says works" and "what TradingView actually produces" is already measurable and will grow as strategy diversity increases. The parity validation infrastructure exists but is not integrated into the automated pipeline.
