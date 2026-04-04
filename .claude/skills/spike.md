# /spike — Find the Best TECL Strategy

Goal: beat buy-and-hold on TECL with ≤3 trades/year. 8.2.1 is the baseline. Find something better.

## How it works

**One question. Then fully autonomous.**

Claude asks how long to run, generates/improves strategies, launches the optimizer, reads the report, and pushes results. No further input needed.

## The Flow

### Step 0 — Ask duration

Ask the user: **"How many hours should the optimizer run?"**

Wait for their answer. Then proceed through the remaining steps with zero interaction.

### Step 1 — Study the leaderboard (Claude, ~1 min)

Read `remote/history/leaderboard.json` to understand what's currently winning. Each entry contains:
- Strategy name, description, params, fitness, metrics, and the date it was found
- This tells you what approaches work and what doesn't

Also read `scripts/strategies.py` to see ALL current strategy implementations.

### Step 2 — Generate & improve strategies (Claude, ~10 min)

Split effort **50/50** between:

#### A) New strategy ideas (~half)

Generate 3-5 completely new strategies. Think creatively — combine indicators in novel ways, try approaches not yet in the registry. Write them as Python functions in `scripts/strategies.py`.

#### B) Optimize leaderboard winners (~half)

Look at the top 5 strategies on the leaderboard. For each one worth improving:
- Read its code in `scripts/strategies.py`
- Understand WHY it works (what market regime does it capture?)
- Create an improved variant: add a better exit, combine with another signal, fix a weakness
- Name variants clearly: `rsi_regime_v2`, `montauk_821_tightened`, etc.

For BOTH (A) and (B), each strategy function must follow this pattern:

```python
def my_strategy(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    some_indicator = ind.ema(p.get("len", 50))

    for i in range(1, n):
        entries[i] = <condition>
        if <exit_condition>:
            exits[i] = True
            labels[i] = "Reason"

    return entries, exits, labels
```

Then add to `STRATEGY_REGISTRY`, `STRATEGY_PARAMS`, and `STRATEGY_DESCRIPTIONS`.

**Available indicators** (all cached, call with any length — same as Pine Script's `ta.*`):
```
# Moving averages
ind.ema(N)         ind.sma(N)          ind.tema(N)

# Momentum / oscillators
ind.rsi(N)         ind.cci(N)          ind.willr(N)        ind.mfi(N)
ind.stoch_k(N)     ind.stoch_d(N)      ind.roc(N)          ind.mom(N)
ind.macd_line(F,S) ind.macd_signal(F,S,Sig)  ind.macd_hist(F,S,Sig)

# Volatility
ind.atr(N)         ind.tr()            ind.stddev(N)       ind.realized_vol(N)

# Channels / bands
ind.bb_upper(N,M)  ind.bb_lower(N,M)   ind.bb_width(N,M)
ind.keltner_upper(E,A,M)               ind.keltner_lower(E,A,M)
ind.donchian_upper(N)                   ind.donchian_lower(N)   ind.donchian_mid(N)

# Trend
ind.adx(N)         ind.di_plus(N)      ind.di_minus(N)     ind.psar()
ind.ichimoku_tenkan(N)                  ind.ichimoku_kijun(N)

# Volume
ind.obv()          ind.vwap()          ind.vol_ema(N)

# Price
ind.highest(N)     ind.lowest(N)       ind.pivot()
ind.pct_change(N)  ind.daily_returns()

# Helpers
ind.slope(key, series, N)               ind.ema_of(key, series, N)
ind.sma_of(key, series, N)              ind.crossover(a, b)    ind.crossunder(a, b)

# Raw data
ind.close          ind.high            ind.low             ind.open
ind.volume         ind.dates           ind.n
```

**Use ANY combination.** Invent composite signals. The only constraints: long TECL, ≤3 trades/year.

### Step 3 — Launch optimizer (zero tokens)

```bash
python3 scripts/spike_runner.py --hours <N>
```

Run this in the background. This is fully autonomous:
- Tests ALL registered strategies with evolutionary parameter optimization
- Seeds populations from historical winners (no wasted work)
- Deduplicates against previous runs (skips already-tested configs)
- Generates a markdown report with top-10 table
- Updates the all-time top-20 leaderboard
- Saves everything to `remote/runs/YYYY-MM-DD/`

### Step 4 — Show results (Claude, ~1 min)

When the optimizer finishes:
1. Read `remote/runs/<date>/report.md`
2. Show the user the top-10 table and key findings
3. Commit all changes (new strategies + results) and push

**ASK the user** if they want Pine Script generated for any winner. Do NOT generate it automatically.

## Converting winner to Pine Script (only when asked)

Only when the user explicitly asks. Read the winning Python function, understand the logic, write equivalent Pine Script v6. Use the reference docs in `reference/pinescriptv6-main/` for correct syntax.

Save to: `src/strategy/testing/Project Montauk [version]-candidate.txt`

## Directory Structure

```
remote/
├── runs/                          # One folder per spike session
│   ├── 2026-04-04/
│   │   ├── report.md              # Auto-generated: top-10 table + details
│   │   ├── results.json           # Full optimizer output
│   │   └── log.txt                # Console output
│   └── 2026-04-04-2/              # Second run same day
├── history/
│   ├── leaderboard.json           # All-time top 20 (with descriptions)
│   └── tested-configs.jsonl       # Every config ever tested (append-only)
├── best-ever.json                 # Single best config
└── winners/                       # Named winner snapshots
```

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | **Strategy library — add new strategies here** |
| `scripts/strategy_engine.py` | Backtest engine + indicator cache |
| `scripts/evolve.py` | Evolutionary optimizer with history/dedup |
| `scripts/spike_runner.py` | **Main entry point — wraps everything** |
| `scripts/report.py` | Auto-generates markdown reports |
| `remote/history/leaderboard.json` | **All-time top 20 — read this first** |
| `remote/history/tested-configs.jsonl` | Full history (dedup source) |
| `remote/best-ever.json` | Best config found across all sessions |

## Constraints

- **Trade TECL only** — long only, no shorting
- **≤3 trades per year** — this is a regime strategy, not a scalper
- **Beat buy-and-hold** — vs_bah_multiple > 1.0 is the target
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
