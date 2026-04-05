# Risk & Failure Findings — Apr-03

**Specialist**: Risk & Failure (SRE pessimist)
**Lens**: What kills this in production? Silent failures, missing guardrails, fragility, data integrity, overfitting danger.
**Scope**: All 12 Python scripts, all Pine Script sources, all config/data files, all remote results.

---

## Manifest

| # | Finding | Signal | Connects to |
|---|---------|--------|-------------|
| R-01 | Dual backtest engine divergence | Two engines compute different results for same strategy | Parity gap, deployment trust |
| R-02 | Montauk 821 EMA cross exit uses wrong EMA in strategy_engine | Critical logic bug | Pine-Python parity |
| R-03 | RSI Regime best-ever is dangerously overfitted | 100% win rate, 10 trades, 75% DD | Deployment risk |
| R-04 | Silent exception swallowing in optimizer | All errors become score=0 | Data corruption, false positives |
| R-05 | Zero test coverage | 0 tests across 4,387 lines | Every other finding |
| R-06 | Stale data pipeline with silent failure | CSV from Feb 23, Yahoo unofficial API | Backtest accuracy |
| R-07 | No deployment guardrails | No max-DD cap, no automated validation gate | Capital risk |
| R-08 | Validation.py imports broken for new strategies | Imports StrategyParams from backtest_engine | RSI Regime can't be validated |
| R-09 | Breakout strategy cross-trade state contamination | peak_since_entry leaks between positions | Optimizer finds phantom results |
| R-10 | Fitness function under-penalizes catastrophic drawdowns | 75% DD gets 0.625x penalty, not 0x | Promotes ruin-risk configs |
| R-11 | Different optimization targets across engines | regime_score vs vs_bah_multiple | Contradictory "best" results |
| R-12 | Yahoo Finance API dependency is fragile | Unofficial endpoint, User-Agent spoofing | Data freshness |
| R-13 | No data integrity validation | No gap/split/duplicate/NaN checks | Silent corruption |
| R-14 | Orphaned code creates confusion risk | spike_auto.py, run_optimization.py partially dead | Wrong tool gets used |
| R-15 | generate_pine.py cannot produce non-Montauk strategies | Only maps Montauk 8.2.1 params | RSI Regime deployment gap |

---

## Finding R-01: Dual Backtest Engine Divergence

**Confidence**: 92%
**Severity**: CRITICAL
**Category**: Architecture / Data Integrity

**Failure scenario**: The optimizer (evolve.py) uses `strategy_engine.py` to evaluate strategies and declare winners. But the validation framework (validation.py) and parity checker (parity_check.py) use `backtest_engine.py`. These are two completely separate implementations with different indicator calculations, different position management, and different metric computation. A strategy that looks great in one engine may perform differently in the other — and there is no automated cross-check.

**Probability**: Near-certain divergence already exists. The backtest-comparison.md shows Python estimated 34.9% CAGR for 8.3-conservative; TradingView measured 31.19% — an 11.9% gap. That gap is between backtest_engine.py and TradingView. The gap between strategy_engine.py and TradingView is completely unmeasured.

**Impact**: Strategy decisions based on numbers that don't reflect reality. The "best" strategy from evolve.py may underperform or lose money when deployed.

**Blast radius**: All optimization results from evolve.py. All strategy rankings. All deployment decisions.

**Files**:
- `scripts/strategy_engine.py` (lines 1-625) — the engine evolve.py uses
- `scripts/backtest_engine.py` (lines 1-900+) — the engine validation/parity uses
- `scripts/evolve.py` (line 29) — imports from strategy_engine
- `scripts/validation.py` (line 16) — imports from backtest_engine
- `scripts/parity_check.py` (line 20) — imports from backtest_engine

**Evidence**: 
- strategy_engine.py `_ema` seed: `out[length - 1] = np.mean(series[:length])` (line 35)
- backtest_engine.py `ema` seed: identical formula BUT different warmup handling
- strategy_engine.py `backtest()` processes exits BEFORE entries on same bar (line 538-556)
- backtest_engine.py `run_backtest()` processes exits then entries but with different priority logic (lines 806-859)
- strategy_engine.py has NO regime scoring; backtest_engine.py computes regime_score

**Proposed fix**: Deprecate one engine. If strategy_engine.py is the future (multi-strategy), port regime scoring and parity checking to it. Run cross-engine parity tests on all 7 strategies.

**Verification**: Run identical parameters through both engines, compare trade-by-trade. Delta should be zero for montauk_821.

**If not fixed**: Every optimization result is unverifiable. The system is optimizing against a model that has no validated relationship to TradingView reality.

---

## Finding R-02: Montauk 821 Uses Wrong EMA for Cross Exit in strategy_engine

**Confidence**: 95%
**Severity**: CRITICAL
**Category**: Logic Bug

**Failure scenario**: The `montauk_821()` function in `strategies.py` uses `ema_m` (med_ema, default 30-bar) for its EMA Cross exit check. But the real Montauk 8.2.1 Pine Script uses `emaLong` (500-bar EMA) for the cross exit. This means the Python optimizer's version of 8.2.1 exits on a completely different signal than the production TradingView strategy.

**Probability**: 100% — this is a code-level fact, not probabilistic.

**Impact**: The "baseline to beat" in the optimizer is not actually Montauk 8.2.1. It is a different strategy that exits much earlier (30-bar EMA cross instead of 500-bar). All comparative rankings against 8.2.1 in evolve.py are wrong.

**Blast radius**: All evolve.py rankings. The montauk_821 fitness score of 0.4556 in evolve-results is for a strategy that doesn't exist in production.

**Files**:
- `scripts/strategies.py` line 74: `if ema_s[i] < ema_m[i] * (1 - p.get("sell_buffer", 0.2) / 100):`
- `src/strategy/active/Project Montauk 8.2.1.txt`: uses `emaLong` (500-bar) for cross exit
- `scripts/backtest_engine.py` line 734-736: correctly uses `ema_long` (500-bar)

**Evidence**: strategies.py line 33: `ema_s = ind.ema(p.get("short_ema", 15))` and line 34: `ema_m = ind.ema(p.get("med_ema", 30))`. The exit at line 74 compares short (15) vs med (30). There is no `ema_long` / 500-bar EMA in the function at all.

**Proposed fix**: Add `ema_l = ind.ema(p.get("long_ema", 500))` and change line 74 to use `ema_l` instead of `ema_m`. Also add `sell_confirm_bars` logic to match 8.2.1's barssince-based confirmation window.

**Verification**: Run montauk_821 through both engines with identical default params. Compare trade list. Should match exactly.

**If not fixed**: The optimizer's "Montauk 8.2.1 baseline" is a phantom — any strategy that "beats" it may only be beating a broken implementation.

---

## Finding R-03: RSI Regime Best-Ever Is Dangerously Overfitted

**Confidence**: 90%
**Severity**: CRITICAL
**Category**: Overfitting / Financial Risk

**Failure scenario**: The RSI Regime strategy is declared "best-ever" with fitness 2.18 and vs_bah of 3.49x. Someone deploys it to TradingView with real money. It draws down 75% in the first bear market.

**Probability**: High. Multiple overfitting signals:
1. 100% win rate on only 10 trades (rsi-regime-2026-04-03.json)
2. 75.1% max drawdown — would destroy 3/4 of capital
3. Only 0.7 trades/year — 10 trades over 17 years is not statistically significant
4. Found in a 54-second run with only 2,625 evaluations
5. No walk-forward validation was performed (validation.py cannot validate non-Montauk strategies)
6. The system itself flags this: "100% win rate on 10 trades is suspicious — could be overfitting"

**Impact**: Financial loss. At 100% position sizing on a 3x leveraged ETF with 75% historical drawdown, a single bad cycle wipes out most capital.

**Blast radius**: Anyone who trusts the optimizer's output and deploys without additional validation.

**Files**:
- `remote/best-ever.json`: fitness 2.1803, max_dd 75.1%
- `remote/winners/rsi-regime-2026-04-03.json`: explicitly notes suspicion
- `remote/evolve-results-2026-04-03.json`: 12 trades, 75% win rate (different config, same family)

**Evidence**: The best-ever.json config: RSI entry at 35, exit at 85, panic at 15, trend EMA 150. With only 0.7 trades/year, the strategy is almost always out of the market. The 75.1% max drawdown means it was IN the market during a catastrophic period — the few trades it takes are enormous bets that either work perfectly (100% win rate) or would be devastating if they don't.

**Proposed fix**: 
1. Hard cap max_drawdown at 50% in the fitness function (any config exceeding this gets fitness=0)
2. Require minimum 20 trades for a result to be considered valid
3. Port walk-forward validation to work with strategy_engine.py/strategies.py
4. Require parity check against TradingView before any strategy can graduate from testing/ to active/

**Verification**: Run Monte Carlo permutation test — shuffle the dates and re-run. If 100% win rate persists, the strategy is finding genuine structure. If it collapses, it is curve-fitted.

**If not fixed**: The "best" strategy the system has ever found is one that risks 75% of capital on 10 bets over 17 years. This is not a trading strategy — it is a leveraged coin flip with survivorship bias.

---

## Finding R-04: Silent Exception Swallowing in Optimizer

**Confidence**: 95%
**Severity**: HIGH
**Category**: Error Handling / Silent Failure

**Failure scenario**: The `evaluate()` function in evolve.py catches ALL exceptions and returns `(0.0, None)`. This means data corruption, NaN propagation, division by zero, type errors, and any other failure are silently treated as "this config scored zero" — indistinguishable from a legitimately bad strategy.

**Probability**: Near-certain during long optimization runs. With 1,330+ evaluations per run across 7 strategies, some will encounter edge cases (NaN data, extreme parameters causing division by zero, integer overflow on long EMAs).

**Impact**: The optimizer silently ignores broken evaluations. Configs that crash could be viable — they are never retried or investigated. The optimizer could also promote configs that only "work" because a crash on certain data windows isn't counted.

**Blast radius**: All optimizer results. Error count is unknowable — there is no logging.

**Files**:
- `scripts/evolve.py` lines 111-119:
  ```python
  def evaluate(ind, df, strategy_fn, params, name):
      try:
          entries, exits, labels = strategy_fn(ind, params)
          ...
          return fitness(result), result
      except Exception:
          return 0.0, None
  ```
- `scripts/evolve.py` lines 182-184: `except Exception: pass` on loading best-ever.json

**Evidence**: The tema_momentum strategy scored 0.0 with empty params in evolve-results — `"metrics": null`. This could be a legitimate failure (bad default params) or a crash that was swallowed. No way to know.

**Proposed fix**: 
1. Log exceptions to a file (`remote/evolve-errors.log`) with strategy name, params, and traceback
2. Track error count per strategy in the results JSON
3. At minimum: `except Exception as e: print(f"WARN: {name} failed: {e}"); return 0.0, None`

**Verification**: Run evolve.py with a deliberately broken strategy function. Confirm the error is logged, not silently eaten.

**If not fixed**: You are flying blind. The optimizer could be crashing on 30% of evaluations and you would never know.

---

## Finding R-05: Zero Test Coverage

**Confidence**: 100%
**Severity**: HIGH
**Category**: Quality / Reliability

**Failure scenario**: There are 0 test files across 4,387 lines of Python code that computes financial metrics used to make trading decisions. Any refactor, bug fix, or new feature can silently break existing behavior.

**Probability**: Already happening. The montauk_821 EMA cross exit bug (R-02) would have been caught by a single test comparing trade output between engines. The dual-engine divergence (R-01) would have been caught by cross-engine parity tests.

**Impact**: Every finding in this report could have been prevented or detected earlier. Without tests, each code change is a gamble.

**Blast radius**: Entire codebase.

**Files**: Scout context confirms: `Tests | 0 | 0`

**Evidence**: No `tests/` directory. No `test_*.py` files. No `pytest` or `unittest` imports anywhere in the codebase. No CI/CD to run tests even if they existed.

**Proposed fix**: Priority test targets (highest risk per line of code):
1. `strategy_engine.py` backtest() — test that a known trade sequence produces expected equity
2. `strategies.py` montauk_821() — test that output matches backtest_engine.py for default params
3. `backtest_engine.py` indicator functions (ema, atr, tema) — test against known values
4. `data.py` — test CSV loading, Yahoo merge logic, duplicate handling
5. Cross-engine parity test — same config through both engines should produce same trades

**Verification**: `pytest` runs and passes.

**If not fixed**: Confidence in any result from this system is faith-based, not evidence-based.

---

## Finding R-06: Stale Data Pipeline with Silent Failure

**Confidence**: 80%
**Severity**: HIGH
**Category**: Data Integrity

**Failure scenario**: The bundled CSV file is `TECL Price History (2-23-26).csv` — data through Feb 23, 2026. Today is Apr 3, 2026 — 39 days of missing data. The Yahoo Finance fallback uses an unofficial API endpoint that returns empty DataFrame on any error, silently falling back to stale data.

**Probability**: The evolve.py explicitly calls `get_tecl_data(use_yfinance=False)` (line 134), meaning it ALWAYS uses stale CSV-only data. All optimization results are based on data ending Feb 23, 2026.

**Impact**: Optimization results miss the most recent 39 days of market data. If a regime change occurred in March 2026, the optimizer doesn't know about it.

**Blast radius**: All backtest results, all strategy rankings, all fitness scores.

**Files**:
- `scripts/data.py` line 13: `CSV_PATH = .../"TECL Price History (2-23-26).csv"`
- `scripts/evolve.py` line 134: `df = get_tecl_data(use_yfinance=False)`
- `scripts/data.py` lines 67-69: `except Exception as e: print(...); return pd.DataFrame()`

**Evidence**: The CSV filename contains the date. The evolve.py explicitly disables Yahoo Finance. 39 trading days is roughly 2 months of data — significant for a strategy that trades 0.7 times per year.

**Proposed fix**:
1. Update the CSV with current data
2. Enable Yahoo Finance in evolve.py (change line 134 to `use_yfinance=True`)
3. Add data freshness check: warn if data is more than 5 trading days old
4. Add data validation: check for gaps > 3 days, price continuity, volume anomalies

**Verification**: Run `python3 scripts/data.py` and confirm data extends to within 1 trading day of today.

**If not fixed**: Optimizing on 39-day-stale data for a 3x leveraged ETF. Market conditions can shift dramatically in that window.

---

## Finding R-07: No Deployment Guardrails

**Confidence**: 88%
**Severity**: HIGH
**Category**: Financial Risk / Process

**Failure scenario**: A config with 75% max drawdown and 10 trades gets promoted to production because nothing prevents it. The path from "optimizer found it" to "Pine Script in testing/" has no automated gates.

**Probability**: Already happening. The RSI Regime was generated as Pine Script and placed in `src/strategy/testing/Montauk RSI Regime.txt` with:
- `slippage=0` (unrealistic)
- `commission_value=0` (unrealistic)
- 75% historical max drawdown
- 10 trades total
- No walk-forward validation

**Impact**: A human copies the testing/ strategy to active/ and uses it with real money. The strategy has a 75% drawdown in its own backtest — this is the BEST case.

**Blast radius**: Financial capital.

**Files**:
- `src/strategy/testing/Montauk RSI Regime.txt`: slippage=0, commission=0
- `scripts/evolve.py`: no validation gate before saving to best-ever.json
- `scripts/generate_pine.py`: generates diffs with no quality checks

**Evidence**: The RSI Regime Pine Script at `src/strategy/testing/` has `slippage=0` and `commission_value=0` hardcoded. The Pine Script `process_orders_on_close=true` setting means orders fill at bar close — but with zero slippage, this assumes perfect execution.

**Proposed fix**:
1. Add mandatory quality gates before any strategy can move to testing/:
   - Max drawdown < 50%
   - Minimum 20 closed trades
   - Walk-forward validation passes
   - Parity check against TradingView
2. Add non-zero slippage and commission to Pine Script templates (even 0.1% each)
3. Add a `DEPLOYMENT_CHECKLIST.md` that must be signed off before active/ changes

**Verification**: Attempt to generate Pine Script for a config with 80% DD — it should be rejected.

**If not fixed**: The path from "AI found something" to "real money" has no safety net.

---

## Finding R-08: Validation Framework Cannot Validate New Strategies

**Confidence**: 95%
**Severity**: HIGH
**Category**: Architecture Gap

**Failure scenario**: `validation.py` imports `StrategyParams` and `run_backtest` from `backtest_engine.py`. These are Montauk 8.2.1-specific. RSI Regime, Golden Cross, Breakout, and all other strategies from `strategies.py` CANNOT be validated through the walk-forward framework.

**Probability**: 100% — this is structural. The validation framework is wired to one engine; the optimizer uses a different engine.

**Impact**: The most important strategies (the ones the optimizer finds that beat 8.2.1) cannot be validated for overfitting. The validation framework only validates the strategy that doesn't need validating (8.2.1, which is already running in production).

**Blast radius**: All non-Montauk strategies. Specifically RSI Regime, which is the current "best-ever."

**Files**:
- `scripts/validation.py` line 16: `from backtest_engine import StrategyParams, BacktestResult, run_backtest`
- `scripts/strategy_engine.py`: defines its own `backtest()` and `BacktestResult`
- `scripts/strategies.py`: defines strategies that only work with strategy_engine.py's `Indicators`

**Evidence**: `validation.py` `validate_candidate()` accepts `StrategyParams` objects and calls `run_backtest()` — both from backtest_engine.py. There is no code path to pass an RSI Regime config through walk-forward validation.

**Proposed fix**: Create a `validate_strategy()` function that accepts a strategy function + params dict (strategy_engine.py style) and runs walk-forward + stability checks using strategy_engine.py's backtest().

**Verification**: Call validate on RSI Regime params — it should complete without import errors and produce a ValidationResult.

**If not fixed**: Walk-forward validation exists but cannot be used on the strategies that need it most.

---

## Finding R-09: Breakout Strategy Cross-Trade State Contamination

**Confidence**: 85%
**Severity**: MEDIUM
**Category**: Logic Bug

**Failure scenario**: The `breakout()` function in strategies.py uses a local variable `peak_since_entry` that persists across the entire array scan. When one trade exits (line 182-183: `peak_since_entry = np.nan`), the reset happens correctly. But the entry check at line 194 (`if entries[i]: peak_since_entry = cl[i]`) runs AFTER the trailing stop check at line 178-183. On the exact bar where a new entry fires, the peak from the PREVIOUS trade may still be active if the reset didn't fire (because exits[i] didn't fire on the previous bar).

**Probability**: Moderate. Depends on whether entries and exits ever fire on the same bar, and whether there are bars between exit and next entry where peak is NaN.

**Impact**: Trailing stop could fire prematurely on a new trade because it is comparing against a peak from a previous trade. This would produce phantom results in the optimizer.

**Blast radius**: All breakout strategy results in evolve.py.

**Files**:
- `scripts/strategies.py` lines 165-197: breakout() function

**Evidence**: Line 166: `peak_since_entry = np.nan` (initialized once). Line 178: `if not np.isnan(peak_since_entry):` — this runs before line 194's entry check. If entries[i] fires on a bar where peak_since_entry is still set from a previous trade (e.g., because the exit was via ATR, not trailing stop, and the ATR exit at line 189 sets peak to NaN but the entries check at line 194 then resets it), the logic is correct. But if entries and exits never co-occur, peak can leak.

**Proposed fix**: Move the entry peak initialization (line 194) to BEFORE the exit checks, or restructure to separate entry/exit arrays from position tracking.

**Verification**: Run breakout strategy, dump trade-by-trade peak_since_entry values, confirm no cross-contamination.

**If not fixed**: Breakout strategy optimizer results may be unreliable.

---

## Finding R-10: Fitness Function Under-Penalizes Catastrophic Drawdowns

**Confidence**: 90%
**Severity**: MEDIUM
**Category**: Financial Risk / Optimization Design

**Failure scenario**: The fitness function in evolve.py computes drawdown penalty as `max(0.3, 1.0 - max_drawdown_pct / 200.0)`. This means:
- 50% DD: penalty = 0.75x
- 75% DD: penalty = 0.625x  
- 100% DD: penalty = 0.5x
- Any DD: minimum penalty = 0.3x (floor)

A strategy that loses 75% of capital only gets a 37.5% haircut to its fitness score. If it beats buy-and-hold by 3.5x (like RSI Regime does), it still dominates despite being potentially ruinous.

**Probability**: Already happening. RSI Regime has 75.1% DD and fitness 2.18 — by far the winner.

**Impact**: The optimizer actively promotes high-drawdown strategies because the penalty is too gentle. In leveraged ETF trading, 75% drawdown means you need a 300% gain to recover.

**Blast radius**: All strategy rankings in evolve.py.

**Files**:
- `scripts/evolve.py` lines 61-62: `dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)`

**Evidence**: RSI Regime: vs_bah = 3.4913, dd_penalty = max(0.3, 1.0 - 75.1/200) = max(0.3, 0.6245) = 0.6245. fitness = 3.4913 * 0.6245 * 1.0 = 2.18. The drawdown barely dents the score.

**Proposed fix**: 
1. Hard cap: `if max_drawdown_pct > 60: return 0.0` — no strategy with >60% DD should be considered
2. Exponential penalty: `dd_penalty = max(0.0, 1.0 - (max_drawdown_pct / 100) ** 2)` — 50% DD gets 0.75x, 70% DD gets 0.51x, 80% DD gets 0.36x

**Verification**: Re-run evolve.py with the new penalty. RSI Regime should rank lower or be eliminated.

**If not fixed**: The optimizer will continue finding high-variance strategies that look great in backtests but are unsurvivable in practice.

---

## Finding R-11: Different Optimization Targets Across Engines

**Confidence**: 85%
**Severity**: MEDIUM
**Category**: Architecture / Coherence

**Failure scenario**: `backtest_engine.py` and `run_optimization.py` use `regime_score` (bull capture + bear avoidance) as the primary metric. `evolve.py` and `strategy_engine.py` use `vs_bah_multiple` (beat buy-and-hold) as the primary fitness. These optimize for fundamentally different things. A strategy that maximizes time-in-market during bulls (high regime score) may have mediocre returns. A strategy that maximizes returns (high vs_bah) may do it through concentrated bets with terrible drawdowns.

**Probability**: Already manifested. The charter says the system's purpose is "be in the market during bulls, be out during bears." But the active optimizer (evolve.py) ranks by vs_bah, not regime quality.

**Impact**: Optimization drift — the newer engine is optimizing for something different than the stated goal.

**Blast radius**: Strategic direction. The RSI Regime wins on vs_bah (3.49x) but its regime behavior is unmeasured.

**Files**:
- `scripts/evolve.py` line 59: `bah = max(result.vs_bah_multiple, 0.001)` (primary fitness component)
- `scripts/run_optimization.py` line 39-42: uses `regime_score` as primary
- `CLAUDE.md`: "Primary optimization target: regime_score"

**Evidence**: CLAUDE.md explicitly states "Primary optimization target: Regime Score" but evolve.py uses vs_bah_multiple. These are different metrics that can contradict each other.

**Proposed fix**: Add regime scoring to strategy_engine.py's BacktestResult. Use it in the evolve.py fitness function as either the primary target or a co-equal component.

**Verification**: Compute regime_score for RSI Regime's winning config. If bear avoidance is low despite high vs_bah, the metric divergence is confirmed.

**If not fixed**: The documented optimization target and the actual optimization target disagree.

---

## Finding R-12: Yahoo Finance API Fragility

**Confidence**: 75%
**Severity**: MEDIUM
**Category**: Dependency Risk

**Failure scenario**: `data.py` uses `https://query1.finance.yahoo.com/v8/finance/chart/TECL` — an unofficial Yahoo Finance API endpoint. Yahoo has historically broken this endpoint multiple times (cookie consent changes, rate limiting, endpoint deprecation). When it fails, the code returns an empty DataFrame and silently falls back to stale CSV data.

**Probability**: Moderate. Yahoo has changed this API multiple times in the past. The User-Agent spoofing (`Mozilla/5.0`) is a fragile workaround.

**Impact**: Data pipeline silently degrades to stale data. No alert, no error — just a print statement.

**Blast radius**: All backtests that use `use_yfinance=True`. Currently only standalone data.py calls use it (evolve.py disables it).

**Files**:
- `scripts/data.py` lines 24-69: fetch_yahoo()
- `scripts/data.py` line 42: `headers = {"User-Agent": "Mozilla/5.0"}`

**Proposed fix**: 
1. Add a proper data provider (e.g., `yfinance` library, Alpha Vantage, or a paid data feed)
2. Alert when Yahoo fetch fails instead of silently falling back
3. Cache fetched data to a dated CSV so fresh data survives API outages

**Verification**: Deliberately break the URL and confirm the system alerts rather than silently degrading.

**If not fixed**: Data freshness depends on an unofficial API that can break without notice.

---

## Finding R-13: No Data Integrity Validation

**Confidence**: 80%
**Severity**: MEDIUM
**Category**: Data Integrity

**Failure scenario**: Neither CSV loading nor Yahoo fetch validates data quality. No checks for: date gaps (market holidays vs data gaps), stock splits/reverse splits, duplicate rows, NaN values in OHLCV (beyond a basic dropna on close), volume anomalies, price continuity (e.g., a 90% overnight gap from a data error).

**Probability**: Moderate. TECL has had reverse splits. CSV data merged with Yahoo data could have overlap, gaps, or inconsistent adjusted prices.

**Impact**: Corrupt data produces corrupt backtest results. A data error in a key market period (e.g., March 2020 crash) could make the optimizer favor strategies that exploit the error rather than real market dynamics.

**Blast radius**: All backtest results.

**Files**:
- `scripts/data.py` lines 16-19: load_csv() — just read and sort, no validation
- `scripts/data.py` lines 72-118: get_tecl_data() — merge logic with column alignment but no integrity checks

**Evidence**: Line 96: `yf_df = yf_df[yf_df["date"] > csv_last_date]` — this handles overlap but not price level discontinuity. If the CSV has unadjusted prices and Yahoo has adjusted prices, the merge creates a price level jump.

**Proposed fix**: Add a `validate_data()` function that checks:
1. No gaps > 5 calendar days (excluding known holidays)
2. No single-day price changes > 50% (detect data errors, not real moves, on TECL)
3. No duplicate dates
4. No NaN in OHLCV
5. Volume > 0 on all trading days
6. Price continuity at CSV/Yahoo merge point

**Verification**: Inject a known data error (duplicate row, NaN close) and confirm it is caught.

**If not fixed**: Garbage in, garbage out — and you won't know it's garbage.

---

## Finding R-14: Orphaned Code Creates Confusion Risk

**Confidence**: 70%
**Severity**: LOW
**Category**: Maintenance / Cognitive Load

**Failure scenario**: `spike_auto.py` (601 lines) and parts of `run_optimization.py` (427 lines) are partially or fully orphaned from the v4 architecture. A developer (or Claude session) uses the old spike_auto.py instead of evolve.py and gets results from a different optimization philosophy.

**Probability**: Low but has already happened (history-context documents a "remote scripts duplication" incident). Mobile Claude sessions have used wrong paths before.

**Impact**: Wasted compute time, confusing results, potential for contradictory "best" configs.

**Blast radius**: Developer confusion and wasted time.

**Files**:
- `scripts/spike_auto.py`: 601 lines, v3 architecture (single-strategy only)
- `scripts/run_optimization.py`: 427 lines, partially alive (baseline/test still work) but sweep/grid may be outdated
- `scripts/parity_check.py`: exists but "shows no evidence of regular use" (history context)

**Proposed fix**: 
1. Move spike_auto.py to an `archive/` folder or add a deprecation header
2. Add a `# DEPRECATED: Use evolve.py instead` comment to the top of spike_auto.py
3. Clean up run_optimization.py to remove dead code paths

**Verification**: `git grep spike_auto` — confirm nothing still imports or references it.

**If not fixed**: Code confusion accumulates. Each new spike version leaves behind infrastructure.

---

## Finding R-15: generate_pine.py Cannot Produce Non-Montauk Strategies

**Confidence**: 90%
**Severity**: MEDIUM
**Category**: Deployment Gap

**Failure scenario**: The deployment pipeline (`generate_pine.py`) only maps Montauk 8.2.1 parameter names to Pine Script variable names. It cannot generate Pine Script for RSI Regime, Golden Cross, Breakout, or any other strategy from `strategies.py`. The RSI Regime Pine Script in testing/ was hand-written, not generated by the pipeline.

**Probability**: Already happening. The RSI Regime Pine Script exists in testing/ but was not produced by generate_pine.py — the PARAM_MAP in generate_pine.py has no RSI-related entries.

**Impact**: The "winner" from the optimizer cannot be automatically deployed. Each new strategy type requires manual Pine Script authoring, introducing human error and breaking the automated pipeline vision.

**Blast radius**: All non-Montauk strategies. The entire v4 multi-strategy architecture is optimizing for strategies it cannot automatically deploy.

**Files**:
- `scripts/generate_pine.py` lines 26-57: PARAM_MAP only contains Montauk 8.2.1 parameters
- `src/strategy/testing/Montauk RSI Regime.txt`: hand-written Pine Script

**Proposed fix**: Extend generate_pine.py with per-strategy Pine Script templates. Each strategy in STRATEGY_REGISTRY should have a corresponding Pine Script template that can be parameterized.

**Verification**: Call generate_pine.py with RSI Regime params — it should produce a valid Pine Script file.

**If not fixed**: The three-layer architecture (Strategy -> Evolution -> Deployment) has a broken deployment layer for 6 out of 7 strategies.

---

## What I Investigated and Ruled Out

1. **Race conditions in spike_state.py**: Investigated the atomic write pattern (tempfile + os.replace). This is correctly implemented and crash-safe. NOT a risk.

2. **Indicator calculation correctness**: Compared EMA, ATR, RMA implementations against Pine Script documentation. The formulas match (SMA seed, recursive alpha). The indicator math itself is NOT the source of parity issues — the divergence comes from position management and execution timing differences.

3. **Memory exhaustion during long runs**: The Indicators class caches computed arrays, but for ~4000 bars this is trivially small. With 7 strategies x 40 population x ~30 cached indicators each, peak memory is well under 1GB. NOT a risk.

4. **Git history corruption**: Checked for orphaned commits mentioned in history context. These are harmless dead branches. NOT a risk.

5. **Secret exposure**: No API keys, credentials, or sensitive data in the codebase. The Yahoo Finance endpoint requires no authentication. NOT a risk.

6. **Concurrency bugs**: All optimization is single-threaded. No parallel execution, no shared mutable state. NOT a risk (but also a performance limitation).

## Coverage Gaps

1. **Pine Script execution model**: I did not verify whether `process_orders_on_close=true` in TradingView matches the Python implementation's fill timing. The backtest-comparison.md shows discrepancies that could stem from this.

2. **TECL-specific risks**: I did not analyze whether TECL's 3x daily leverage reset (volatility decay) is properly modeled in either backtesting engine. Neither engine accounts for leverage decay explicitly — they treat TECL as a regular stock.

3. **CSV data quality**: I did not actually validate the CSV file for splits, gaps, or errors. The file is ~17K tokens and could contain data issues.

4. **Regime detection sensitivity**: The bear/bull detection in backtest_engine.py uses hardcoded thresholds (30% bear, 20% bull). I did not verify these are appropriate for TECL (a 3x leveraged ETF where 30% moves are common).

5. **Stochastic optimizer convergence**: I did not verify whether 19 generations is sufficient for the evolutionary optimizer to converge. The 54-second run time and 1,330 evaluations suggest the RSI Regime result may be a local optimum found early, not a global optimum.
