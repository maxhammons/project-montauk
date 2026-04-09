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
                          │     (--bayesian for Optuna TPE)      │
                          └──────────────┬──────────────────────┘
                                         │
                          ┌──────────────▼──────────────────────┐
                          │         spike_runner.py              │
                          │                                     │
                          │  • Creates spike/runs/NNN/           │
                          │  • Tees stdout → log.txt             │
                          │  • Calls evolve()                    │
                          │  • Flags: --bayesian, --strategies   │
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
          │  │              VIX (^VIX) ─────────┤                  │    │
          │  │              XLK (synthetic) ────┤ (--extended)     │    │
          │  │                                  ▼                  │    │
          │  │               TECL+VIX DataFrame (daily)           │    │
          │  │               Default: 2009-present                │    │
          │  │               Extended: 1998-present (XLK→3x)      │    │
          │  │                                  │                  │    │
          │  │                                  ▼                  │    │
          │  │                    strategy_engine.Indicators()     │    │
          │  │                    Pre-computes ALL indicators:     │    │
          │  │                    EMA, SMA, TEMA, RSI, CCI,       │    │
          │  │                    MACD, ATR, Bollinger, Keltner,   │    │
          │  │                    Ichimoku, ADX, PSAR, OBV,       │    │
          │  │                    VIX close/EMA/SMA/percentile    │    │
          │  │                    (cached — computed once)         │    │
          │  │                                  │                  │    │
          │  │  hash-index.json ────────────────┤ dedup cache (v3) │    │
          │  │  leaderboard.json ───────────────┤ seed winners     │    │
          │  └──────────────────────────────────┴──────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ BASELINE EVAL                                       │    │
          │  │                                                     │    │
          │  │  For each of 15 registered strategies:              │    │
          │  │    • Run with midpoint params                       │    │
          │  │    • Auto-prune: skip if fitness < 0.05 after 2+    │    │
          │  │      runs (except montauk_821 baseline)             │    │
          │  └─────────────────────────────────────────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ OPTIMIZER (two modes)                                │    │
          │  │                                                     │    │
          │  │  ┌───────────────────────────────────────────────┐  │    │
          │  │  │ MODE A: Genetic Algorithm (default)           │  │    │
          │  │  │                                               │  │    │
          │  │  │  For each strategy, each generation:          │  │    │
          │  │  │  1. Evaluate population (40 configs)          │  │    │
          │  │  │  2. Measure diversity (param variance)        │  │    │
          │  │  │  3. Adaptive reproduction (DGEA):             │  │    │
          │  │  │     Low diversity  → BURST  (40% mut, ±4)    │  │    │
          │  │  │     Mid diversity  → BALANCE(20% mut, ±2)    │  │    │
          │  │  │     High diversity → EXPLOIT(10% mut, ±1)    │  │    │
          │  │  │     20% elites + 33% crossover + 42% mutant  │  │    │
          │  │  │     + 5% random injection                    │  │    │
          │  │  │  Repeat until time runs out or Ctrl+C        │  │    │
          │  │  └───────────────────────────────────────────────┘  │    │
          │  │                                                     │    │
          │  │  ┌───────────────────────────────────────────────┐  │    │
          │  │  │ MODE B: Bayesian (--bayesian flag)            │  │    │
          │  │  │                                               │  │    │
          │  │  │  Uses Optuna TPE sampler per strategy         │  │    │
          │  │  │  • Seeds 5 leaderboard winners                │  │    │
          │  │  │  • Splits time evenly across strategies       │  │    │
          │  │  │  • Builds fitness landscape model             │  │    │
          │  │  │  • ~100x more sample-efficient than GA        │  │    │
          │  │  │  • Same dedup cache + fitness function        │  │    │
          │  │  └───────────────────────────────────────────────┘  │    │
          │  └─────────────────────────────────────────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ PER-CONFIG EVALUATION                               │    │
          │  │                                                     │    │
          │  │  Config ──hash──▶ hash-index lookup                  │    │
          │  │                    │                                 │    │
          │  │            ┌──────┴──────┐                          │    │
          │  │         CACHED v3     NEW CONFIG                    │    │
          │  │         recompute     run backtest:                 │    │
          │  │         fitness from    strategy_fn(ind, params)    │    │
          │  │         raw metrics     → entries[], exits[]        │    │
          │  │            │            backtest()                  │    │
          │  │            │             → equity, trades, metrics  │    │
          │  │            │            score_regime()              │    │
          │  │            │             → bull/bear/HHI            │    │
          │  │            │            fitness()                   │    │
          │  │            └──────┬──────┘                          │    │
          │  │                   ▼                                 │    │
          │  │           Fitness score (ranked)                    │    │
          │  └─────────────────────────────────────────────────────┘    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐    │
          │  │ OUTPUT                                              │    │
          │  │                                                     │    │
          │  │  1. Rank all strategies by best fitness             │    │
          │  │  2. Update leaderboard.json (top 20 all-time)       │    │
          │  │  3. Save hash-index.json v3 (raw metrics for dedup) │    │
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
          │  3. Run validation suite (see below)                       │
          │  4. Compare winner to montauk_821 baseline                 │
          │  5. If requested: generate Pine Script for winner          │
          └────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
          ┌────────────────────────────────────────────────────────────┐
          │                    VALIDATION SUITE                         │
          │                                                            │
          │  ┌────────────────────────────────────────────────────┐     │
          │  │ sprint1.py — 6 Statistical Overfitting Tests       │     │
          │  │                                                    │     │
          │  │  1. Deflated Regime Score (Beta-EVT null)          │     │
          │  │  2. Exit-Boundary Proximity (memorization check)   │     │
          │  │  3. Delete-One-Cycle Jackknife (dependence)        │     │
          │  │  4. HHI Concentration (cycle balance)              │     │
          │  │  5. Regime Meta-Robustness (28 definitions)        │     │
          │  │  6. Component Dominance (bull vs bear balance)     │     │
          │  │                                                    │     │
          │  │  Output: PASS / WARN / FAIL per test per strategy  │     │
          │  └────────────────────────────────────────────────────┘     │
          │                                                            │
          │  ┌────────────────────────────────────────────────────┐     │
          │  │ walk_forward.py — Out-of-Sample Validation         │     │
          │  │                                                    │     │
          │  │  Split: train (2009-2019) / test (2020-present)    │     │
          │  │  For each leaderboard strategy+params:             │     │
          │  │    • Backtest on train → train vs_bah              │     │
          │  │    • Backtest on test  → test vs_bah               │     │
          │  │    • Degradation ratio = test / train              │     │
          │  │                                                    │     │
          │  │  Pass criteria:                                    │     │
          │  │    • test vs_bah > 0.8                             │     │
          │  │    • degradation > 0.5                             │     │
          │  │    • ≥ 2 trades in test period                     │     │
          │  │                                                    │     │
          │  │  Output: PASS / WARN / FAIL + degradation table    │     │
          │  └────────────────────────────────────────────────────┘     │
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
          │  5. VIX data via request.security("CBOE:VIX", ...)        │
          │  6. Output: src/strategy/testing/candidate.txt             │
          │  7. Copy into TradingView Pine Editor                      │
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
                       HASH-INDEX CACHE (v3)
═══════════════════════════════════════════════════════════════════════

  Stores raw backtest metrics so fitness can be recomputed when the
  formula changes without re-running backtests.

  Format: {config_hash: {bah, rs, dd, nt, np, hhi}}

  ┌──────┬──────────────────────────────────────────────────────────┐
  │ Key  │ Value                                                    │
  ├──────┼──────────────────────────────────────────────────────────┤
  │ bah  │ vs_bah_multiple (strategy equity / B&H equity)           │
  │ rs   │ regime_score composite (0-1)                             │
  │ dd   │ max_drawdown_pct                                         │
  │ nt   │ num_trades                                               │
  │ np   │ n_params (non-cooldown numeric params)                   │
  │ hhi  │ HHI cycle concentration                                  │
  └──────┴──────────────────────────────────────────────────────────┘

  On load: v1/v2 entries auto-migrate to v3 (bah=None → re-evaluated)
  fitness_from_cache() recomputes score from raw metrics on the fly


═══════════════════════════════════════════════════════════════════════
                       DATA PIPELINE
═══════════════════════════════════════════════════════════════════════

  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │ TECL CSV    │    │ Yahoo TECL  │    │ Yahoo XLK   │
  │ (bundled)   │    │ (backfill)  │    │ (1998-2009) │
  │ 2009-2026   │    │ latest bars │    │ → 3x synth  │
  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
         │                  │                  │
         └────────┬─────────┘                  │
                  │    (extended=True) ─────────┘
                  ▼
         ┌────────────────┐    ┌─────────────┐
         │  TECL OHLCV    │    │ Yahoo ^VIX  │
         │  (merged)      │◄───│ (daily)     │
         │  + vix_close   │    └─────────────┘
         └────────────────┘
              │
         Default:  2009-present (~4,200 bars, ~6 cycles)
         Extended: 1998-present (~7,000 bars, ~10 cycles)


═══════════════════════════════════════════════════════════════════════
                       STRATEGY FAMILIES (15)
═══════════════════════════════════════════════════════════════════════

  Price-only strategies:
    montauk_821          EMA cross + layered exits (production baseline)
    rsi_regime           RSI dip-buy with trend filter
    breakout             Donchian breakout + trailing stop
    rsi_regime_trail     RSI entry + trailing stop exit
    vol_regime           Realized vol ratio entry/exit
    ichimoku_trend       Ichimoku cloud + ATR exits
    dual_momentum        Absolute + relative momentum
    rsi_vol_regime       RSI + vol calming filter
    stoch_drawdown_recovery  Buy after major drawdowns
    williams_midline_reclaim Williams %R midline
    adx_trend            ADX directional strength
    keltner_squeeze      Bollinger/Keltner squeeze
    psar_trend           Parabolic SAR trend follow

  VIX-enhanced strategies (new):
    vix_mean_revert      Buy on VIX fear spikes (declining), sell on calm
    vix_trend_regime     Ride calm VIX + trend, exit on VIX spike

  Pine Script: VIX accessed via request.security("CBOE:VIX", ...)


═══════════════════════════════════════════════════════════════════════
                       FILE MAP
═══════════════════════════════════════════════════════════════════════

  scripts/
  ├── spike_runner.py ──── Entry point (--hours, --bayesian, --strategies)
  ├── evolve.py ────────── GA + Bayesian optimizer, fitness, dedup, leaderboard
  ├── strategies.py ────── 15 strategy functions + STRATEGY_REGISTRY
  ├── strategy_engine.py ─ Backtest engine + Indicators (incl. VIX)
  ├── data.py ──────────── TECL + VIX + synthetic XLK→3x data
  ├── report.py ────────── Markdown report generator
  ├── requirements.txt ─── pandas, numpy, requests, scipy, optuna
  └── validation/
      ├── sprint1.py ───── 6 anti-overfitting tests
      ├── walk_forward.py  Walk-forward out-of-sample validation
      ├── candidate.py ─── Single-strategy deep validation
      └── deflate.py ───── Monte Carlo null distribution

  spike/
  ├── leaderboard.json ─── All-time top 20 (fitness-ranked)
  ├── hash-index.json ──── Dedup v3: {hash: {bah, rs, dd, nt, np, hhi}}
  └── runs/
      ├── 001/ ──────────── First run
      ├── 002/ ──────────── Second run
      └── NNN/ ──────────── Each run: report.md, results.json, log.txt

  .github/workflows/
  └── spike.yml ─────────── GH Actions (hours, pop_size, strategies, bayesian)
```
