# Project Montauk — Data Pipeline

```
                          ┌─────────────────────────────────────┐
                          │       /spike v2 (Claude, local)      │
                          │                                     │
                          │  1. refresh_all() — update CSVs      │
                          │  2. Build regime map (bull/bear)      │
                          │  3. Run cycle diagnostics on top 5   │
                          │  4. Claude writes strategies          │
                          │  5. evolve_chunk() — 20min optimizer │
                          │  6. Analyze results + cycle diag      │
                          │  7. Claude revises strategy CODE      │
                          │  8. Repeat 5-7 until time budget      │
                          │  9. Cross-asset + sprint1 validation  │
                          │                                     │
                          │  /spike-focus (GH Actions, overnight) │
                          │  — Deep param tuning on 1-2 strategies│
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

  Time-Series Data Store (reference/time-series data/):
  All data is local. No API calls during optimization.
  refresh_all() in data.py updates every CSV at /spike start.

  ┌─────────────────────────────────────┬──────────────────────────────┐
  │ File                                │ Contents                     │
  ├─────────────────────────────────────┼──────────────────────────────┤
  │ TECL.csv                            │ Canonical source: OHLCV +    │
  │                                     │ vix_close (synth 1998-2008   │
  │                                     │ + real 2009+). Auto-updated. │
  │ VIX Daily.csv                       │ CBOE VIX OHLCV (1990-now)   │
  │ XLK Daily.csv                       │ TECL underlying (1998-now)   │
  │ QQQ Daily.csv                       │ Cross-asset ref (1999-now)   │
  │ TQQQ Daily.csv                      │ Synth 1999-2010 + real 2010+ │
  │ Treasury Yield Spread 10Y-2Y.csv    │ FRED T10Y2Y (recession sig)  │
  │ Fed Funds Rate.csv                  │ FRED DFF (monetary policy)   │
  └─────────────────────────────────────┴──────────────────────────────┘

  Data refresh (spike_runner.py → data.refresh_all()):
    • Called automatically at /spike start
    • Appends new bars to every CSV from Yahoo Finance + FRED
    • Re-merges VIX into TECL.csv after updates
    • Never overwrites historical data — append only

  Audit (scripts/data_audit.py):
    • Verifies synthetic TECL = 3x XLK daily returns - expense
    • One-time bulk download of all enrichment data


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
    williams_midline_reclaim Williams %R midline
    adx_trend            ADX directional strength
    keltner_squeeze      Bollinger/Keltner squeeze

  High bull-capture strategies (designed to stay IN market):
    always_in_trend      Default long, exit only on confirmed bear (ADX+EMA)
    donchian_turtle      Classic turtle: N-bar high entry, M-bar low exit
    slope_persistence    Enter on N-bar positive EMA slope, exit on M-bar neg

  VIX-enhanced strategies:
    vix_mean_revert      Buy on VIX fear spikes (declining), sell on calm
    vix_trend_regime     Ride calm VIX + trend, exit on VIX spike

  Pine Script: VIX accessed via request.security("CBOE:VIX", ...)

  Pruned (never made leaderboard):
    stoch_drawdown_recovery  (removed: 10 params, never appeared)
    psar_trend               (removed: never appeared)


═══════════════════════════════════════════════════════════════════════
                       FILE MAP
═══════════════════════════════════════════════════════════════════════

  scripts/
  ├── spike_runner.py ──── Entry point: --hours (full) or --chunk (iterative)
  ├── evolve.py ────────── evolve() for full runs, evolve_chunk() for v2 loop
  ├── strategies.py ────── 16 strategy functions + STRATEGY_REGISTRY
  ├── strategy_engine.py ─ Backtest engine + Indicators (incl. VIX)
  ├── data.py ──────────── TECL + VIX + TQQQ + QQQ data loaders + refresh_all()
  ├── data_audit.py ────── Synthetic TECL audit + data enrichment downloads
  ├── regime_map.py ────── Bull/bear cycle detection + formatting for Claude
  ├── cycle_diagnostics.py Per-cycle trade analysis (gaps, exit reasons, capture)
  ├── report.py ────────── Markdown report generator
  ├── requirements.txt ─── pandas, numpy, requests, scipy, optuna
  └── validation/
      ├── sprint1.py ───── 6 anti-overfitting tests
      ├── walk_forward.py  Walk-forward out-of-sample validation
      ├── cross_asset.py ── Run strategy on TQQQ/QQQ (anti-overfit)
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
