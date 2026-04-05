# Scratchpad — Data-Integrity Specialist — Apr-03

## File Manifest

| File | Finding | Signal | Connects to |
|------|---------|--------|------------|
| scripts/data.py | CSV + Yahoo merge, no split-adjust validation | data-pipeline | CSV integrity |
| scripts/backtest_engine.py | Dual engine (v3 for 8.2.1, v4 strategy_engine.py), EMA/ATR calcs, regime scoring | calculation-error, parity-gap | strategy_engine.py, Pine Script |
| scripts/strategy_engine.py | New v4 modular engine, separate indicator lib, simpler backtest loop | parity-gap | strategies.py, evolve.py |
| scripts/strategies.py | 7 strategy functions, RSI regime winner, montauk_821 simplified replica | parity-gap, overfitting-risk | backtest_engine.py, Pine Script |
| scripts/evolve.py | Multi-strategy evolutionary optimizer, fitness = vs_bah * dd_penalty | overfitting-risk, degenerate-config | strategies.py |
| scripts/validation.py | Walk-forward validation, imports from backtest_engine (v3 only) | overfitting-risk | backtest_engine.py |
| scripts/run_optimization.py | CLI runner, imports from backtest_engine (v3 only) | dead-code | backtest_engine.py |
| scripts/spike_auto.py | v3 evolutionary optimizer, different fitness function | dead-code, overfitting-risk | backtest_engine.py |
| scripts/spike_state.py | Atomic JSON state management, crash-safe | state-corruption | spike sessions |
| scripts/generate_pine.py | Parameter diff generator, only maps 8.2.1 params | parity-gap | Pine Script |
| scripts/parity_check.py | TradingView comparison, 10-30% tolerances | parity-gap | TradingView |
| scripts/signal_queue.json | 20 queued signal ideas | N/A | dead reference |
| scripts/requirements.txt | pandas, numpy, requests | N/A | - |
| src/strategy/active/Project Montauk 8.2.1.txt | Production Pine Script, process_orders_on_close=true | parity-gap | backtest_engine.py |
| src/strategy/testing/Montauk RSI Regime.txt | Generated Pine from RSI regime winner | parity-gap | strategies.py |
| reference/TECL Price History (2-23-26).csv | 4340 bars, 2008-12-31 to 2026-04-01 | data-validation | data.py |
| remote/best-ever.json | RSI regime fitness=2.18, 75.1% DD, 0.7 trades/yr | overfitting-risk | evolve.py |
| remote/evolve-results-2026-04-03.json | 19 generations, 1330 evals in 0.01h | overfitting-risk | evolve.py |
| remote/winners/rsi-regime-2026-04-03.json | 100% win rate, 10 trades, 46.4% CAGR | overfitting-risk | evolve.py |
| remote/spike-state.json | Phase 0, no progress | N/A | spike_state.py |
| remote/spike-results-2026-04-03.json | v3 optimizer results, regime_score=0.686 | dead-code | spike_auto.py |
| remote/spike-progress.json | v3 progress state | dead-code | spike_auto.py |
| .claude/settings.json | Claude config | N/A | - |
| .claude/settings.local.json | Local Claude config | N/A | - |
| .claude/commands/sync.md | Sync command | N/A | - |
| .claude/skills/about.md | Project about | N/A | - |
| .claude/skills/spike.md | Spike skill definition | N/A | - |
| CLAUDE.md | Project documentation | N/A | - |
| .gitignore | Git ignore rules | N/A | - |
| reference/Montauk Charter.md | Strategy charter | N/A | - |
| src/strategy/archive/* (14 files) | Historical Pine Scripts | N/A | - |
| src/strategy/debug/* (2 files) | Debug builds | N/A | - |
| src/strategy/testing/archive/* (2 files) | Archived candidates | N/A | - |
| src/indicator/active/Montauk Composite Oscillator 1.3.txt | Production indicator | N/A | - |
| src/indicator/archive/* (2 files) | Archived indicators | N/A | - |
| reference/pinescriptv6-main/* (28 files) | Pine reference docs | N/A | - |
| remote/diff-2026-04-02-*.txt (2 files) | Parameter diffs | N/A | - |
| remote/report-2026-03-04.md | Old report | N/A | - |
| remote/spike-2026-04-02.md | Old spike report | N/A | - |

## Files Read: ~45 unique files / 88 total (remaining are Pine reference docs and .DS_Store)

## Running Observations

1. TWO SEPARATE BACKTEST ENGINES: backtest_engine.py (v3, 960+ lines, full 8.2.1 replica) and strategy_engine.py (v4, 624 lines, generic). They have independent indicator implementations.
2. The v4 strategies.py montauk_821() is a SIMPLIFIED version of the v3 backtest_engine.py logic — missing sideways filter, missing TEMA filters, missing sell confirmation window logic, missing trailing stop, missing vol spike exit.
3. RSI calculation in strategy_engine.py uses `np.diff(series, prepend=series[0])` which sets delta[0]=0 — Pine Script's ta.rsi() uses a different warmup.
4. The v4 evolve.py fitness function is DIFFERENT from v3 spike_auto.py fitness — v4 doesn't include regime_score bonus, v3 does.
5. validation.py imports from backtest_engine.py (v3) — it does NOT validate v4 strategies at all.
6. Parity check tolerances are extremely loose: 10% for win rate, 10% for CAGR, 30% for total return. These mask significant errors.
7. CSV has a `change_pct` column that is never validated against actual OHLC data — potential for stale/incorrect rows.
8. No split-adjustment validation — TECL prices start at $0.33 in 2008 which looks pre-split, but no verification logic exists.
9. The v4 backtest() function checks exits BEFORE entries on each bar, but the v3 run_backtest() exits then enters too. However, v4 recalculates equity_curve[i] twice per bar while v3 only updates it once at the end.
10. RSI Regime strategy has entry_rsi=35 and exit_rsi=85, meaning it enters on RSI crossing UP through 35 and exits when RSI >= 85 — this creates extremely long hold periods on a 3x leveraged ETF.
11. The RSI panic exit at RSI < 15 on a 3x leveraged ETF would fire during extreme bear markets — but the 100% win rate suggests it NEVER fired for the winning config.
12. evolve.py runs only 19 generations with 1330 evals — not nearly enough for 6-param optimization. Search space is barely explored.
13. The v4 backtest loop does exit-then-entry on same bar, meaning you can exit AND re-enter on the same bar (no cooldown enforcement within the bar loop itself — cooldown is only checked on entry).
14. Bear regime detection uses a fixed 30% threshold — for TECL (3x leveraged), 30% drawdowns happen routinely in normal markets, inflating the count of "bear regimes."
15. Bull capture ratio measures bars-in vs total-bars in the bull period, NOT the actual return captured. A strategy in for 90% of bars during a bull could still miss the best 10% of bars.
16. The v4 breakout strategy tracks peak_since_entry as a local variable in the for-loop BUT the backtest engine independently tracks position state — the strategy's peak tracking doesn't reset properly on backtest engine entries/exits.
17. EMA seed difference: both engines seed with SMA of first `length` bars, matching Pine Script. Good.
18. ATR uses RMA (Wilder's smoothing) with alpha=1/period, matching Pine's ta.atr(). Good.
19. The CSV ends 2026-04-01 but Yahoo API fetch_yahoo() starts from CSV end date + 1 day. No weekend/holiday handling — if CSV ends on a Friday, fetch starts Saturday, which is fine because Yahoo returns nothing for weekends.
20. No data validation on Yahoo API response — null prices could sneak in (only `dropna(subset=["close"])` is applied, not open/high/low).
21. CAGR calculation in v4 strategy_engine.py uses dates[0] to dates[-1] for the year span, while v3 backtest_engine.py does the same. Both use full data span, not first-trade-to-last-trade span. This overestimates CAGR denominator for strategies that don't trade in early years.
22. Commission is 0% in both Python and Pine Script — realistic for modern brokers but worth noting.
23. The regime score bear_avoidance defaults to 1.0 when no bear periods are found — this inflates composite score for short data windows.

## Hypothesis Evolution

### H1: v4 montauk_821 produces different results than v3 backtest_engine.py
- Initial confidence: 85%
- After code review: 95% — confirmed massive logic gaps
- Evidence: v4 missing sideways filter, TEMA filters, sell confirmation barssince logic, vol spike exit, trailing stop, asymmetric ATR
- TRAJECTORY: 85% -> 95% [CONFIRMED RISING]

### H2: RSI Regime "winner" is overfitting
- Initial confidence: 80%
- After reviewing evolve results: 90%
- Evidence: 100% win rate on 10 trades, 75% max DD, only 19 generations, no walk-forward validation run
- TRAJECTORY: 80% -> 90% [CONFIRMED RISING]

### H3: v4 RSI implementation diverges from Pine Script
- Initial confidence: 60%
- After code review: 75%
- Evidence: `np.diff(series, prepend=series[0])` sets first delta to 0, Pine uses SMA warmup for RSI
- TRAJECTORY: 60% -> 75% [RISING]

### H4: Regime scoring is biased for TECL
- Initial confidence: 50%
- After reviewing thresholds: 70%
- Evidence: 30% bear threshold is too sensitive for 3x ETF, bars-in metric doesn't capture return quality
- TRAJECTORY: 50% -> 70% [RISING]

### H5: Parity gap is larger than reported
- Initial confidence: 70%
- After reviewing parity_check.py tolerances: 80%
- Evidence: 10-30% tolerance bands mask real errors, and the check only covers 8.2.1 v3 engine
- TRAJECTORY: 70% -> 80% [RISING]
