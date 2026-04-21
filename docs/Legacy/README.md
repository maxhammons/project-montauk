# Legacy — Montauk Strategy + Indicator Archive

Restored from git history. Pine Script + Python files that were deleted during the Apr-2026 reorg, kept here as design references for reviving ideas (ADX/DI, Ichimoku, Keltner squeeze, volatility regime, composite oscillator, etc.) in the current pipeline.

Not in active use. Do not import from here.

## Provenance

| Folder | Original Path | Source Commit | Deleted In |
|---|---|---|---|
| `Strategy/active/` | `src/strategy/active/` | `3b83706` | `9ab75e5` (2026-04-19) |
| `Strategy/archive/` | `src/strategy/archive/` | `3b83706` | `9ab75e5` |
| `Strategy/debug/` | `src/strategy/debug/` | `9385531` | `f151a08` |
| `Strategy/testing/` | `src/strategy/testing/` | `80263cf` | `dab54b9` |
| `Indicator/active/` | `src/indicator/active/` | `3b83706` | `9ab75e5` |
| `Indicator/archive/` | `src/indicator/archive/` | `3b83706` | `9ab75e5` |
| `Python/strategies_1.2.py` | `scripts/strategies.py` | `dc29e51` | subsumed into `scripts/strategies/library.py` (`041ea2e`) |
| `Python/strategy_engine_1.2.py` | `scripts/strategy_engine.py` | `dc29e51` | replaced by `scripts/engine/strategy_engine.py` |

## What's in here

### Pine Script strategies (`Strategy/`)
- **active/**: The final Pine version of 8.2.1. Source of the baseline `run_montauk_821()` in the Python engine.
- **archive/**: Historical Pine versions 1.0 → 7.9. The evolutionary record of the strategy — what was tried, what was dropped. FMC = "Fast/Med Cross," the very earliest branch.
- **debug/**: Instrumented versions of 7.6 and 7.8 (extra plots / labels / exit reason tagging). Useful as templates if you need to debug a live Pine version again.
- **testing/**: The "Montauk 9.0" branch — three Pine versions hand-translated from Python candidates (rsi_regime, rsi_vol_regime, regime composite) in early April 2026 when the Pine/Python parity work was still live.

### Pine Script indicators (`Indicator/`)
- **active/Montauk Composite Oscillator 1.3.txt** — Weighted composite of TEMA slope + Quick EMA slope + MACD histogram + DMI bull strength, each normalized with `tanh`. Produces a [-1, +1] regime score. Worth reviving as a *Python* composite entry gate (not currently implemented in the library).
- **archive/** — Earlier versions 1.0 and 1.2 of the same indicator.

### Python strategies (`Python/`)
- **strategies_1.2.py** (1131 lines) — The full pre-reorg strategy library. Contains 15+ families not currently registered in `scripts/strategies/library.py`:
  - `adx_trend` (ADX + DI+/DI- entry, ADX fade + DI cross exit)
  - `keltner_squeeze` (BB inside Keltner squeeze→release)
  - `psar_trend` (Parabolic SAR flip)
  - `ichimoku_trend` (Tenkan/Kijun cross + cloud filter)
  - `rsi_regime` / `rsi_regime_trail` / `rsi_vol_regime` (RSI-dip entries)
  - `vol_regime` (realized-vol ratio contraction→expansion)
  - `vix_trend_regime` / `vix_mean_revert`
  - `dual_momentum` (absolute + relative momentum)
  - `slope_persistence`, `momentum_stayer`, `always_in_trend`, `trough_bounce`, `donchian_turtle`, `breakout`
- **strategy_engine_1.2.py** — The monolithic engine before the Phase-7 consolidation (separate `backtest_engine` + `strategy_engine`). All its indicators (adx, di_plus, di_minus, psar, keltner_upper/lower, ichimoku_tenkan/kijun, realized_vol, bb_width, macd_line) **still exist** in the current `scripts/engine/strategy_engine.py` — so reviving these strategies does not require rebuilding indicators.

## Legacy leaderboard context (commit `dc29e51`, Engine 1.2)

Top-10 under the *old* fitness function (regime-score-weighted, not share-multiple-primary). Useful as a sanity check on which families were promising under a different objective:

| Rank | Strategy | Old fitness | CAGR | DD | Trades |
|---|---|---|---|---|---|
| 1 | rsi_regime | 66.47 | 24.91% | 63.6% | 36 |
| 2 | breakout | 12.51 | 15.51% | 65.6% | 70 |
| 3 | montauk_821 | 10.23 | 16.74% | 66.1% | 80 |
| 4 | ichimoku_trend | 6.39 | 12.16% | 55.7% | 75 |
| 5 | slope_persistence | 6.24 | 12.64% | 63.4% | 62 |
| 6 | momentum_stayer | 6.22 | 15.54% | 58.0% | 43 |
| 7 | vix_trend_regime | 5.59 | 13.98% | 58.2% | 45 |
| 8 | donchian_turtle | 5.42 | 15.80% | 72.4% | 20 |
| 9 | rsi_regime_trail | 4.76 | 12.16% | 54.5% | 51 |
| 10 | rsi_vol_regime | 4.29 | 12.71% | 30.6% | 58 |

Bottom-of-leaderboard (pruned): `always_in_trend` (pure ADX), `keltner_squeeze`, `vix_mean_revert` — these were the "ADX-only didn't work" cohort.

**Reading this table**: the metrics look weak vs current leaderboard (Velvet Jaguar has 116x share_multiple) because (a) the fitness function was different and (b) the old backtests used non-canonical params optimized by the pre-Phase-7 GA. The *shapes* of these strategies — not the specific params — are the salvageable part.
