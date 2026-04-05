# Risk Scratchpad — Apr-03

## Investigation Protocol Tracking

### Phase A: Orientation (Complete)
- Read all 12 Python source files
- Read all context files (scout, history, calibration)
- Read active Pine Script (8.2.1) and RSI Regime testing script
- Read evolve results, best-ever.json, winners/rsi-regime
- Read backtest-comparison.md (TradingView parity data)
- Read Montauk Charter
- Read signal_queue.json, requirements.txt, spike_state.py

### Phase B: Hypothesis Formation

#### H1: Dual-engine divergence will produce catastrophically wrong decisions
- Confidence: 0.85 -> 0.90 (after reading parity_check.py tolerances)
- Two completely separate backtesting engines exist: `backtest_engine.py` (Montauk 8.2.1 specific, 900+ lines) and `strategy_engine.py` (multi-strategy, 625 lines)
- They implement DIFFERENT indicator calculations, DIFFERENT position management, DIFFERENT metric computation
- The evolve.py optimizer uses strategy_engine.py, but validation.py imports from backtest_engine.py
- RSI Regime was found by strategy_engine.py but would be deployed based on those numbers
- Parity check only covers backtest_engine.py vs TradingView — strategy_engine.py has ZERO parity validation

#### H2: RSI Regime "best-ever" result is dangerously overfitted
- Confidence: 0.92
- 100% win rate on 10 trades (rsi-regime-2026-04-03.json notes this is "suspicious")
- 75.1% max drawdown — would lose 3/4 of capital before recovering
- Only 0.7 trades/year — extremely low sample size
- Found in 54-second run with 2,625 evals (inadequate search)
- No walk-forward validation was run on this result (validation.py imports from backtest_engine.py which doesn't know about RSI Regime)
- The fitness function in evolve.py has a floor of 0.3 on drawdown penalty — 75% DD only gets 0.625x penalty

#### H3: Exception swallowing hides fatal errors
- Confidence: 0.88
- evolve.py evaluate() function: `except Exception: return 0.0, None` — silently treats ALL errors as "strategy scored 0"
- This means NaN propagation, division by zero, data corruption all produce silent zeros instead of crashes
- No logging of what failed or why

#### H4: Data pipeline has silent corruption risk
- Confidence: 0.75
- CSV file is dated Feb 23, 2026 — over a month stale
- Yahoo Finance API uses unofficial endpoint that can break without notice
- No data validation: no checks for gaps, splits, duplicates, NaN injection
- fetch_yahoo catches ALL exceptions and returns empty DataFrame — network errors become "no new data"

#### H5: No guardrails on what configs can be deployed
- Confidence: 0.90
- generate_pine.py produces diffs, not validated configs
- No max drawdown cap in the deployment path
- The optimizer's fitness function allows 75% drawdown configs to win
- Pine Script is generated and placed in testing/ with no automated validation gate

#### H6: Two backtest engines disagree on what "good" means
- Confidence: 0.85
- backtest_engine.py uses regime_score (bull capture + bear avoidance) as primary metric
- strategy_engine.py/evolve.py uses vs_bah_multiple as primary fitness
- These are fundamentally different optimization targets
- A strategy could score well on one and terribly on the other

### Phase C: Evidence Collection

#### Error handler count: 4
1. evolve.py:118 — `except Exception: return 0.0, None` (silent swallow)
2. evolve.py:183 — `except Exception: pass` (silent swallow of best-ever.json load failure)
3. data.py:67 — `except Exception as e: print(); return pd.DataFrame()` (returns empty on any error)
4. spike_state.py:52 — `except Exception: os.unlink(tmp_path); raise` (correct — re-raises)

#### Untested critical paths: ALL
- 0 test files exist
- backtest_engine.py: 900+ lines, 0 tests
- strategy_engine.py: 625 lines, 0 tests  
- strategies.py: 395 lines, 0 tests
- evolve.py: 377 lines, 0 tests
- validation.py: 347 lines, 0 tests
- data.py: 127 lines, 0 tests

#### Security surface: LOW (not internet-facing)
- No authentication, no user input from network
- Yahoo Finance API uses hardcoded User-Agent spoofing
- JSON files written with no sanitization but only consumed locally

#### Dependency risks: MEDIUM
- Yahoo Finance unofficial API (no SLA, can break anytime)
- pandas, numpy, requests — stable but no pinned versions (>=, not ==)
- No virtual environment detected
- No lockfile

### Phase D: Cross-referencing

#### Breakout strategy bug in strategies.py
- Lines 166-194: `peak_since_entry` is stateful across the ENTIRE array
- If entries[i] fires, peak is set at line 194
- But peak tracking at lines 177-183 runs BEFORE the entry check at line 194
- On the FIRST bar where entry fires, peak_since_entry is still NaN, so trailing stop logic at 177-183 is skipped
- On subsequent bars, if a new entry fires, peak was already set from previous position — CROSS-CONTAMINATION between trades

#### Montauk 821 Python vs Pine: EMA cross exit uses different EMAs
- Pine 8.2.1: `ta.crossunder(emaShort, emaLong)` where emaLong = 500-bar EMA
- backtest_engine.py: correctly uses ema_short vs ema_long (500-bar) for cross exit
- BUT strategies.py montauk_821(): `ema_s[i] < ema_m[i]` — uses med_ema (30), NOT long_ema (500)!
- This is a CRITICAL fidelity bug — the strategy_engine version of 8.2.1 exits on a completely different signal

#### Commission handling mismatch
- backtest_engine.py: `commission = equity * params.commission_pct / 100 * 2` (applies to full equity, 2x for round trip)
- strategy_engine.py: NO commission handling at all
- Both default to 0% commission, but backtest_engine has the infrastructure

### Phase E: Synthesis

See findings file.
