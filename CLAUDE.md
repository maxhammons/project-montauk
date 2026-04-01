# Project Montauk

A Pine Script trading strategy system for TECL (Direxion Daily Technology Bull 3X Shares ETF) on TradingView. The project includes multiple strategy versions and companion indicators, all written in Pine Script v5/v6.

## Directory Structure

```
Project Montauk/
├── CLAUDE.md                  ← You are here
├── reference/
│   ├── Montauk Charter.md               # Coding rules, guardrails, and evaluation criteria
│   └── pinescriptv6-main/               # Pine Script v6 reference (structured repo)
├── scripts/                   # Python backtesting & optimization tools
│   ├── data.py                # TECL data fetcher (yfinance + CSV fallback)
│   ├── backtest_engine.py     # Python replica of Montauk 8.2 strategy logic
│   ├── validation.py          # Walk-forward validation & anti-overfitting
│   ├── run_optimization.py    # CLI runner for backtests, sweeps, validation
│   ├── generate_pine.py       # Convert winning params back to Pine Script v6
│   └── requirements.txt       # Python deps: pandas, numpy, yfinance
├── .claude/skills/
│   └── spike.md               # /spike skill — continuous optimization loop
└── src/
    ├── strategy/
    │   ├── active/            # Current production strategy
    │   ├── archive/           # All previous versions (kept for reference)
    │   └── debug/             # Debug builds with visual labels
    └── indicator/
        ├── active/            # Current production indicator
        └── archive/           # Previous indicator versions
```

## Active Code (what's running in TradingView)

### Strategy: `src/strategy/active/Project Montauk 8.1.txt`

The current production strategy. Pine Script v6 overlay strategy for TECL.

**Entry conditions** (all must be true):
- EMA-short (15) > EMA-med (30)
- Trend filter: 70-bar EMA slope is positive
- TEMA slope is positive (optional, 200-bar Triple EMA)
- Price is above TEMA (optional)
- Not in sideways market (optional, Donchian range check)
- Not in post-exit cooldown (2 bars)

**Exit conditions** (checked in priority order):
1. **EMA Cross Exit**: EMA-short crosses below EMA-long (500) with 2-bar confirmation and 0.2% buffer
2. **ATR Exit**: Price falls below previous close minus 3x ATR(14)
3. **Quick EMA Exit**: 15-bar EMA percent change over window exceeds -7% threshold

**Key parameters are organized into 8 input groups** for TradingView UI clarity: EMAs, Trend Filter, TEMA Filters, Sideways Filter, Sell Confirmation, Sell Cooldown, ATR Exit, Quick EMA Exit.

### Indicator: `src/indicator/active/Montauk Composite Oscillator 1.3.txt`

Normalized composite momentum oscillator displayed in a separate pane. Returns a single value from -1 to +1 using `tanh()` normalization.

**Components (weighted)**:
| Component | Length | Weight | What it measures |
|-----------|--------|--------|-----------------|
| TEMA Slope | 300-bar | Heaviest | Primary trend direction |
| Quick EMA | 7-bar | Medium | Short-term momentum |
| MACD Histogram | 30/180/20 | Medium | Momentum divergence |
| DMI Ratio | 60-bar ADX | Medium | Directional strength |

**Visual output**: Color-coded bands (blue > green > yellow > orange > red) with optional smoothed MA lines for crossover signals.

**Component diagnostics panel** (v1.3): Top-right table showing each component's raw normalized value (-1 to +1) and weighted contribution to the composite. Color-coded to match oscillator bands. Disabled components appear greyed out. Toggled via "Show Component Panel" input.

## Strategy Version History

All versions target TECL. Early versions (1.x) were originally named "FMC" (Flash Momentum Capture) - same project, different name. The approach evolved from MACD-based entries (1.x-6.x) to EMA-crossover entries with layered exit filters (7.x+).

| Version | File | Pine | Key idea |
|---------|------|------|----------|
| 1.0 | `archive/Project Montauk 1.0 (FMC).txt` | v5 | MACD crossover + ATR stop + 200 SMA trend filter + slope-based no-trade zone |
| 1.1 | `archive/Project Montauk 1.1 (FMC).txt` | v5 | Dynamic MACD buffer (% of price), cooldown in bars instead of days |
| 1.4 | `archive/Project Montauk 1.4 (FMC).txt` | v5 | Added 21-EMA exit filter, two-stage "ready" entry (MACD first, then SMA cross) |
| 6.4b | `archive/Project Montauk 6.4 b.txt` | v5 | Simple EMA approach: 2000-bar EMA trend + 200-bar EMA re-entry with fixed buffer exit |
| 6.8c | `archive/Project Montauk 6.8 c.txt` | v5 | Pure MACD zero-cross with dynamic threshold buffer (20% of amplitude) |
| 7-6 | `archive/Project Montauk 7-6.txt` | v6 | Multi-exit system: EMA cross + drop-sell (19% in 3 bars) + ATR + quick EMA slope |
| 7-7 | `archive/Project Montauk 7-7.txt` | v6 | Removed drop-sell filter from 7-6 for cleaner logic |
| 7.8 | `archive/Project Montauk 7.8.txt` | v6 | Production version with exit-reason label tracking on chart |
| 7.9 | `archive/Project Montauk 7.9.txt` | v6 | Added TEMA filters and Donchian-based sideways market detection |
| **8.1** | **`active/Project Montauk 8.1.txt`** | **v6** | **Current. Organized input groups, quick exit changed from slope to % delta** |

### Debug Builds

These are strategy versions with extra visual debugging for development:

| File | Based on | Debug feature |
|------|----------|---------------|
| `debug/Project Montauk 7.6 - Debug.txt` | 7-6 | Detailed entry/exit comments in order log |
| `debug/Project Montauk 7.8 - Debug.txt` | 7.8 | `label.new()` on chart showing which exit condition fired |

## Architecture Notes

- **All strategies are overlay strategies** (plotted on the price chart, not in a separate pane)
- **The indicator runs in a separate pane** (oscillator output, not overlaid on price)
- **Position sizing**: 8.1 uses 100% of equity per trade (single position, long only)
- **No shorting**: All strategies are long-only
- **Cooldown logic**: After every exit, a configurable cooldown (bars) prevents immediate re-entry
- **Price smoothing**: Montauk 6.x versions use OHLC/4 smoothed price; 7.x+ use standard close

## Remote Sessions (Phone / Off-Computer Work)

When running in a remote session (e.g. Claude Code on mobile), follow these rules:

- **Save all outputs** (reports, backtests, code reviews, new strategy files, analysis) to the `remote/` folder at the project root
- **Use timestamped filenames** to prevent overwrites: `[type]-YYYY-MM-DD.txt` (e.g. `backtest-2026-03-08.txt`, `report-2026-03-08.txt`, `strategy-review-2026-03-08.txt`)
- **Commit and push directly to `main`** — do not create a new branch
- This ensures the desktop auto-syncs via `git pull` without any manual merging

## Working with This Code

- **To edit the active strategy**: Modify `src/strategy/active/Project Montauk 8.1.txt`, then paste into TradingView Pine Editor
- **To edit the active indicator**: Modify `src/indicator/active/Montauk Composite Oscillator 1.3.txt`, then paste into TradingView Pine Editor
- **When creating a new version**: Copy the active file to the appropriate archive folder first, then modify the active copy
- **Strategy and indicator are separate scripts in TradingView** - the strategy handles entries/exits, the indicator provides visual confirmation in a separate chart pane

## Optimization Tools (`/spike`)

The `/spike` skill runs a continuous strategy optimization loop. It uses a Python backtesting engine that faithfully replicates Montauk 8.2's logic, enabling rapid parameter sweeps and walk-forward validation without TradingView.

### How to use

1. **Install deps** (first time only): `pip3 install pandas numpy yfinance requests`
2. **Run `/spike`** in Claude Code — this kicks off the multi-phase optimization loop
3. All output goes to `remote/` — **the active strategy is never modified**
4. Winning configurations are output as ready-to-paste Pine Script v6

### CLI tools (used by `/spike`, also available standalone)

```bash
# Run baseline backtest with 8.2 defaults
python3 scripts/run_optimization.py baseline

# Test specific parameter overrides
python3 scripts/run_optimization.py test --params '{"short_ema_len": 12}'

# Sweep a single parameter
python3 scripts/run_optimization.py sweep --param atr_multiplier --min 1.5 --max 5.0 --step 0.5

# Walk-forward validation (anti-overfitting)
python3 scripts/run_optimization.py validate --params '{"short_ema_len": 12}'

# Generate Pine Script from params
python3 scripts/generate_pine.py '{"short_ema_len": 12}' "9.0-candidate"
```

### Key metrics (from Charter)

| Metric | Target direction |
|--------|-----------------|
| MAR Ratio (CAGR/MaxDD) | Higher is better — primary optimization target |
| CAGR | Higher |
| Max Drawdown | Lower |
| Trades/Year | Low (<5) — avoid churn |
| Avg Bars Held | High (50+) — trend system, not scalper |

## Reference Files

- **`reference/Montauk Charter.md`**: The governing spec for all code work on this project. Read this before proposing any changes — it defines scope, coding rules, feature acceptance criteria, evaluation metrics, and response format.
- **`reference/pinescriptv6-main/`**: Structured Pine Script v6 reference. Use the modular files for quick lookups, fall back to the all-in-one for anything not found there:
  - `reference/functions/ta.md` — TA functions (`ta.ema`, `ta.atr`, `ta.crossover`, etc.)
  - `reference/variables.md` — Built-in variables (`close`, `bar_index`, `barstate.*`, etc.)
  - `concepts/common_errors.md`, `pine_script_execution_model.md` — execution and error docs
  - `Pine Script language reference manual` — 393KB all-in-one covering all 884 functions including all `strategy.*` functions. Use Grep or offset reads to search it.
  - Do not guess at Pine v6 API details — look them up.
