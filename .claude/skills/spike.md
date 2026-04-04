# /spike — Find the Best TECL Strategy

Goal: beat buy-and-hold on TECL with ≤3 trades/year. 8.2.1 is the baseline. Find something better.

## How it works

**One question. Then fully autonomous.**

1. Ask: "How long should the optimizer run?"
2. Claude does two things (50/50 split):
   - **Invents new strategies** — fresh ideas added to `scripts/strategies.py`
   - **Optimizes leaderboard strategies** — reads top performers from history, studies their logic, tunes their parameters or improves their code
3. Python optimizer runs autonomously for the requested duration
4. Auto-generated report with top-10 table, leaderboard, history stats
5. Claude shows you the results, commits, and pushes

## The Flow (step by step)

### Step 1 — Ask duration

Ask the user: **"How long should the optimizer run? (e.g., 1h, 4h, 8h)"**

Do NOT proceed until they answer.

### Step 2 — Study the leaderboard (~50% of Claude's effort)

Before writing any new code, read the current state:

1. Read `remote/history/leaderboard.json` — the all-time top 20
2. Read `scripts/strategies.py` — all existing strategy functions
3. For each top strategy on the leaderboard:
   - Read its function code
   - Read its best params and metrics from the leaderboard
   - Think about WHY it works (or doesn't) — what market conditions does it exploit?
   - Consider: can its logic be refined? Can you add a smarter exit? A better entry filter?
4. Write improved variants as NEW strategy functions (don't modify the original — the optimizer needs both to compare)

**Example optimizations:**
- A strategy exits too late → add an ATR trailing stop variant
- A strategy enters on RSI 35 → try a version that also requires positive MACD slope
- A strategy uses a single EMA → try a version with adaptive EMA length based on volatility
- Two top strategies use different entry signals → try combining them

Name variants clearly: `rsi_regime_v2`, `breakout_with_vol_filter`, etc.

### Step 3 — Generate new strategies (~50% of Claude's effort)

Open `scripts/strategies.py` and add brand new strategy functions. Each one is ~20 lines:

```python
def my_strategy(ind: Indicators, p: dict) -> tuple:
    n = ind.n
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    labels = np.array([""] * n)

    some_indicator = ind.ema(p.get("len", 50))

    for i in range(1, n):
        # Entry logic
        entries[i] = <condition>
        # Exit logic
        if <exit_condition>:
            exits[i] = True
            labels[i] = "Reason"

    return entries, exits, labels
```

Then add to `STRATEGY_REGISTRY` and `STRATEGY_PARAMS` at the bottom.

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

**Use ANY combination.** Invent new composite signals. The only constraints are: long TECL, ≤3 trades/year.

Generate 5-10 strategies total (mix of new ideas + leaderboard variants). Don't self-censor — the optimizer sorts out what works.

### Step 4 — Launch the optimizer (zero tokens)

```bash
python3 scripts/spike_runner.py --hours <N>
```

Run this in the background. It handles everything:
- Tests ALL registered strategies with evolutionary parameter optimization
- Seeds populations from historical winners (doesn't repeat past work)
- Deduplicates configs across runs via JSONL history
- ~500,000+ evaluations in 8 hours
- Auto-generates markdown report with top-10 table
- Updates all-time leaderboard (top 20)
- Saves everything to `remote/runs/YYYY-MM-DD/`

### Step 5 — Show results

When the optimizer finishes:

1. Read `remote/runs/<date>/report.md`
2. Show the user the top-10 table and key findings
3. Commit all changes (new strategies + results) and push
4. **ASK the user** if they want Pine Script generated for any winner

## Converting winner to Pine Script (only when asked)

Only when the user explicitly asks. Read the winning Python function, understand the logic, write equivalent Pine Script v6. Use the reference docs in `reference/pinescriptv6-main/` for correct syntax.

Save to: `src/strategy/testing/Project Montauk [version]-candidate.txt`

## CLI options

| Flag | Default | What |
|------|---------|------|
| `--hours N` | (required) | Duration — user chooses |
| `--pop-size N` | 40 | Population per strategy per generation |
| `--quick` | off | Shorter report intervals |

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | **Strategy library — add new strategies here** |
| `scripts/strategy_engine.py` | Backtest engine + indicator cache |
| `scripts/evolve.py` | Evolutionary optimizer (with history + dedup) |
| `scripts/spike_runner.py` | **Main entry point — wraps everything** |
| `scripts/report.py` | Auto-generates markdown reports |
| `remote/runs/YYYY-MM-DD/` | Per-session output (report, results, log) |
| `remote/history/leaderboard.json` | All-time top 20 strategies |
| `remote/history/tested-configs.jsonl` | Every config ever tested (append-only) |
| `remote/best-ever.json` | Single best config found |

## Directory structure

```
remote/
├── runs/                              # One folder per spike session
│   ├── 2026-04-04/
│   │   ├── report.md                  # The deliverable: top-10 table + details
│   │   ├── results.json               # Full optimizer output (with trade lists)
│   │   └── log.txt                    # Console output
│   └── 2026-04-04-2/                  # Second run same day
├── history/
│   ├── leaderboard.json               # All-time top 20
│   └── tested-configs.jsonl           # Append-only config history
├── best-ever.json                     # Single best
└── winners/                           # Named winner snapshots
```

## Constraints

- **Trade TECL only** — long only, no shorting
- **≤3 trades per year** — this is a regime strategy, not a scalper
- **Beat buy-and-hold** — vs_bah_multiple > 1.0 is the target
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
