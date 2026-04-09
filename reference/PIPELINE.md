# Project Montauk — Data Pipeline

```
                          ┌─────────────────────────────────────┐
                          │           /spike (Claude)            │
                          │                                     │
                          │  1. Read leaderboard.json            │
                          │  2. Study top strategies             │
                          │  3. Write new strategy functions     │
                          │  4. Prune dead weight                │
                          │  5. Commit + push                    │
                          │  6. Trigger GH Actions or run local  │
                          └──────────────┬──────────────────────┘
                                         │
                          ┌──────────────▼──────────────────────┐
                          │         spike_runner.py              │
                          │                                     │
                          │  • Creates spike/runs/NNN/           │
                          │  • Tees stdout → log.txt             │
                          │  • Calls evolve()                    │
                          │  • Prints final paths                │
                          └──────────────┬──────────────────────┘
                                         │
          ┌──────────────────────────────▼──────────────────────────────┐
          │                        evolve.py                            │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ SETUP                                               │    │
          │  │                                                     │    │
          │  │  data.py ─── Yahoo Finance API ──┐                  │    │
          │  │              CSV fallback ────────┤                  │    │
          │  │                                  ▼                  │    │
          │  │                          TECL OHLCV DataFrame       │    │
          │  │                          (2009-present, daily)      │    │
          │  │                                  │                  │    │
          │  │                                  ▼                  │    │
          │  │                    strategy_engine.Indicators()     │    │
          │  │                    Pre-computes ALL indicators:     │    │
          │  │                    EMA, SMA, TEMA, RSI, CCI,       │    │
          │  │                    MACD, ATR, Bollinger, Keltner,   │    │
          │  │                    Ichimoku, ADX, PSAR, OBV, etc.  │    │
          │  │                    (cached — computed once)         │    │
          │  │                                  │                  │    │
          │  │  hash-index.json ────────────────┤ dedup cache      │    │
          │  │  leaderboard.json ───────────────┤ seed winners     │    │
          │  └──────────────────────────────────┴──────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ BASELINE EVAL                                       │    │
          │  │                                                     │    │
          │  │  For each registered strategy:                      │    │
          │  │    • Run with midpoint params                       │    │
          │  │    • Auto-prune: skip if fitness < 0.05 after 2+    │    │
          │  │      runs (except montauk_821 baseline)             │    │
          │  └─────────────────────────────────────────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ EVOLUTIONARY LOOP (runs for N hours)                │    │
          │  │                                                     │    │
          │  │  For each active strategy, each generation:         │    │
          │  │                                                     │    │
          │  │  ┌───────────────────────────────────────────────┐  │    │
          │  │  │ 1. EVALUATE POPULATION                        │  │    │
          │  │  │                                               │  │    │
          │  │  │    For each of 40 param configs:              │  │    │
          │  │  │                                               │  │    │
          │  │  │    Config ──hash──▶ hash-index lookup          │  │    │
          │  │  │                      │                        │  │    │
          │  │  │              ┌───────┴───────┐                │  │    │
          │  │  │              │               │                │  │    │
          │  │  │           CACHED          NEW                 │  │    │
          │  │  │           reuse         evaluate:             │  │    │
          │  │  │           score     ┌────────────────────┐    │  │    │
          │  │  │              │      │ strategy_fn(ind, p) │    │  │    │
          │  │  │              │      │   → entries[], exits│    │  │    │
          │  │  │              │      │                    │    │  │    │
          │  │  │              │      │ backtest()         │    │  │    │
          │  │  │              │      │   → equity curve   │    │  │    │
          │  │  │              │      │   → trades list    │    │  │    │
          │  │  │              │      │   → CAGR, MaxDD,   │    │  │    │
          │  │  │              │      │     vs_bah, MAR    │    │  │    │
          │  │  │              │      │                    │    │  │    │
          │  │  │              │      │ score_regime()     │    │  │    │
          │  │  │              │      │   → bull_capture   │    │  │    │
          │  │  │              │      │   → bear_avoidance │    │  │    │
          │  │  │              │      │   → HHI            │    │  │    │
          │  │  │              │      │                    │    │  │    │
          │  │  │              │      │ fitness()          │    │  │    │
          │  │  │              │      │   PRIMARY: vs_bah  │    │  │    │
          │  │  │              │      │   × trade_scale    │    │  │    │
          │  │  │              │      │   × hhi_penalty    │    │  │    │
          │  │  │              │      │   × dd_penalty     │    │  │    │
          │  │  │              │      │   × complexity     │    │  │    │
          │  │  │              │      │   × regime_mult    │    │  │    │
          │  │  │              │      └────────┬───────────┘    │  │    │
          │  │  │              │               │                │  │    │
          │  │  │              └───────┬───────┘                │  │    │
          │  │  │                      ▼                        │  │    │
          │  │  │              Scored population                │  │    │
          │  │  │              (sorted by fitness)              │  │    │
          │  │  └───────────────────────────────────────────────┘  │    │
          │  │                                                     │    │
          │  │  ┌───────────────────────────────────────────────┐  │    │
          │  │  │ 2. DIVERSITY MEASUREMENT                      │  │    │
          │  │  │                                               │  │    │
          │  │  │    Normalized parameter variance across pop   │  │    │
          │  │  │    Relative diversity = current / initial     │  │    │
          │  │  │    Mutation survival rate (>90% parent fit)   │  │    │
          │  │  └───────────────────────────────────────────────┘  │    │
          │  │                                                     │    │
          │  │  ┌───────────────────────────────────────────────┐  │    │
          │  │  │ 3. ADAPTIVE REPRODUCTION (DGEA)               │  │    │
          │  │  │                                               │  │    │
          │  │  │    Diversity < 15%  → BURST   (40% mut, ±4)  │  │    │
          │  │  │    Diversity 15-60% → BALANCE (20% mut, ±2)  │  │    │
          │  │  │    Diversity > 60%  → EXPLOIT (10% mut, ±1)  │  │    │
          │  │  │                                               │  │    │
          │  │  │    20% elites (carried forward unchanged)     │  │    │
          │  │  │    33% crossover (two elite parents)          │  │    │
          │  │  │    42% mutation (elite parent + noise)        │  │    │
          │  │  │     5% random injection (fresh blood)         │  │    │
          │  │  └───────────────────────────────────────────────┘  │    │
          │  │                                                     │    │
          │  │  Repeat until time runs out or Ctrl+C               │    │
          │  └─────────────────────────────────────────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ OUTPUT                                              │    │
          │  │                                                     │    │
          │  │  1. Rank all strategies by best fitness             │    │
          │  │  2. Update leaderboard.json (top 20 all-time)       │    │
          │  │  3. Save hash-index.json (dedup for next run)       │    │
          │  │  4. Save results.json (full rankings + trades)      │    │
          │  │  5. report.py → report.md (top 10 table + details)  │    │
          │  └─────────────────────────────────────────────────────┘    │
          └────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
          ┌────────────────────────────────────────────────────────────┐
          │                    spike/runs/NNN/                          │
          │                                                            │
          │    report.md ──── Human-readable results                    │
          │    results.json ─ Full rankings, params, trade lists        │
          │    log.txt ────── Raw optimizer stdout                      │
          │    candidate.txt  Pine Script (if generated)               │
          └────────────────────────────────────────────────────────────┘
                                         │
                          ┌──────────────▼──────────────────────┐
                          │  GH Actions: git add spike/ + push   │
                          │  Commit: "spike: run NNN (date)"     │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
          ┌────────────────────────────────────────────────────────────┐
          │                  /spike results (Claude)                    │
          │                                                            │
          │  1. git pull                                                │
          │  2. Read report.md → show top 10 + details                 │
          │  3. Run validation/sprint1.py (6 anti-overfit tests)       │
          │  4. Compare winner to montauk_821 baseline                 │
          │  5. If requested: generate Pine Script for winner          │
          └────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
          ┌────────────────────────────────────────────────────────────┐
          │              VALIDATION SUITE (sprint1.py)                  │
          │                                                            │
          │  For each leaderboard strategy:                            │
          │                                                            │
          │  ┌────────────────────────────────────────────────────┐     │
          │  │ Test 1: Deflated Regime Score                      │     │
          │  │   Monte Carlo null: Beta(17.2, 14.8)               │     │
          │  │   Expected max at N_eff=300: 0.761                 │     │
          │  │   → Is this score better than noise?               │     │
          │  ├────────────────────────────────────────────────────┤     │
          │  │ Test 2: Exit-Boundary Proximity                    │     │
          │  │   Distance from each exit to nearest bear start    │     │
          │  │   Enrichment ratio vs chance expectation            │     │
          │  │   → Are exits memorizing bear boundaries?          │     │
          │  ├────────────────────────────────────────────────────┤     │
          │  │ Test 3: Delete-One-Cycle Jackknife                 │     │
          │  │   Remove each bull/bear cycle, re-score            │     │
          │  │   Flag if any single removal collapses score >2x   │     │
          │  │   → Does one lucky cycle carry everything?         │     │
          │  ├────────────────────────────────────────────────────┤     │
          │  │ Test 4: HHI Concentration                          │     │
          │  │   Separate bull/bear HHI                            │     │
          │  │   Component dominance ratio                         │     │
          │  │   → Is performance spread across cycles?           │     │
          │  ├────────────────────────────────────────────────────┤     │
          │  │ Test 5: Regime Detection Meta-Robustness           │     │
          │  │   28 regime definitions (7 thresholds × 4 windows) │     │
          │  │   Score must stay within 20% on ≥60% of defs       │     │
          │  │   → Is score stable or definition-dependent?       │     │
          │  ├────────────────────────────────────────────────────┤     │
          │  │ Test 6: Component Dominance                        │     │
          │  │   Bull capture vs bear avoidance ratio              │     │
          │  │   Flag if one side carries >3x the other           │     │
          │  │   → Is performance balanced or one-sided?          │     │
          │  └────────────────────────────────────────────────────┘     │
          │                                                            │
          │  Output: PASS / WARN / FAIL per test per strategy          │
          └────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
          ┌────────────────────────────────────────────────────────────┐
          │               PINE SCRIPT GENERATION                       │
          │               (if winner passes validation)                │
          │                                                            │
          │  1. Read winning Python strategy function                   │
          │  2. Read best params from results.json                     │
          │  3. Read 8.2.1 as structural template                      │
          │  4. Reference pinescriptv6-main/ for syntax                │
          │  5. Output: src/strategy/testing/candidate.txt             │
          │  6. Copy into TradingView Pine Editor                      │
          └────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════
                         FITNESS FUNCTION
═══════════════════════════════════════════════════════════════════════

    fitness = vs_bah × trade_scale × hhi_penalty × dd_penalty
                     × complexity_penalty × regime_mult

  ┌──────────────────┬────────────────────────────────────────────────┐
  │ Component        │ What it does                                   │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ vs_bah           │ PRIMARY — strategy equity / B&H equity         │
  │ (primary)        │ >1.0 = beating buy-and-hold                    │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ trade_scale      │ Soft ramp: 5 trades → 0.5x, 10+ → 1.0x       │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ hhi_penalty      │ 0.15→0.35 ramp, >0.35 = REJECT                │
  │                  │ Prevents single-cycle dependence               │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ dd_penalty       │ MaxDD 20% → 0.83x, 40% → 0.67x, 80% → 0.33x │
  │                  │ Penalizes blowup risk                          │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ complexity       │ trades/params < 2 = REJECT                     │
  │                  │ 2-5 ratio → 0.5-1.0 ramp                      │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ regime_mult      │ RS 0.7+ → 1.0x, 0.5 → 0.83x, 0.3 → 0.66x   │
  │                  │ Quality guard — rewards genuine timing skill   │
  └──────────────────┴────────────────────────────────────────────────┘

  HARD GATES (fitness = 0):
    • < 5 trades
    • > 3 trades/year
    • HHI > 0.35
    • trades-per-param < 2.0
    • vs_bah ≤ 0


═══════════════════════════════════════════════════════════════════════
                       FILE MAP
═══════════════════════════════════════════════════════════════════════

  scripts/
  ├── spike_runner.py ──── Entry point: creates run dir, tees output
  ├── evolve.py ────────── GA optimizer, fitness, dedup, leaderboard
  ├── strategies.py ────── All strategy functions + STRATEGY_REGISTRY
  ├── strategy_engine.py ─ Backtest engine + Indicators cache
  ├── data.py ──────────── TECL data (Yahoo API + CSV fallback)
  ├── report.py ────────── Markdown report generator
  └── validation/
      ├── sprint1.py ───── 6 anti-overfitting tests
      ├── candidate.py ─── Single-strategy deep validation
      └── deflate.py ───── Monte Carlo null distribution

  spike/
  ├── leaderboard.json ─── All-time top 20 (fitness-ranked)
  ├── hash-index.json ──── Dedup: {config_hash: {f, rs}}
  └── runs/
      ├── 001/ ──────────── First run
      ├── 002/ ──────────── Second run
      └── NNN/ ──────────── Each run: report.md, results.json, log.txt
```
