# /spike — Find the Best TECL Strategy

Goal: beat buy-and-hold on TECL with ≤3 trades/year. 8.2.1 is the baseline. Find something better.

## How it works

**Claude writes Python strategy functions. Python tests them overnight. Only the winner becomes Pine Script.**

Writing Pine Script for each idea = slow + expensive. Writing a 20-line Python function = fast + testable 500,000 times overnight.

## Step 1 — Generate strategies (Claude, ~10 min of tokens)

Open `scripts/strategies.py` and add new strategy functions. Each one is ~20 lines:

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

**Use ANY combination.** There are no restrictions on what indicators or logic you can use. Combine them however you want. Invent new composite signals. The only constraints are: long TECL, ≤3 trades/year.

Generate as many strategies as you can. More variety = higher chance of finding something that beats 8.2.1. Don't self-censor ideas — the optimizer will sort out what works.

Generate 5-10 new strategies per session. More is better — the optimizer handles the rest.

## Step 2 — Launch optimizer (zero tokens)

```bash
cd /path/to/project-montauk
pip3 install pandas numpy requests  # first time only
python3 scripts/evolve.py --hours 8
```

This runs autonomously all night:
- Tests ALL registered strategies with evolutionary parameter optimization
- ~500,000+ evaluations in 8 hours
- Compares everything against 8.2.1 baseline
- Hard constraint: ≤3 trades/year, penalizes high drawdown
- Saves best to `remote/best-ever.json`, full results to `remote/evolve-results-YYYY-MM-DD.json`

## Step 3 — Report results (Claude, ~2 min)

1. Read `remote/evolve-results-YYYY-MM-DD.json`
2. Compare #1 ranked strategy vs 8.2.1 baseline
3. Save winning config to `remote/winners/[strategy]-[date].json`
4. Write compact report to `remote/spike-YYYY-MM-DD.md`
5. Commit and push
6. **ASK the user** if they want Pine Script generated. Do NOT generate it automatically — it costs tokens and the user may want to run more sessions first.

## Converting winner to Pine Script (only when asked)

Only when the user explicitly asks. Read the winning Python function, understand the logic, write equivalent Pine Script v6. Use the reference docs in `reference/pinescriptv6-main/` for correct syntax.

Save to: `src/strategy/testing/Project Montauk [version]-candidate.txt`

## CLI options

| Flag | Default | What |
|------|---------|------|
| `--hours N` | 8 | Duration |
| `--pop-size N` | 40 | Population per strategy per generation |
| `--quick` | off | Shorter report intervals |
| `--list` | — | Show registered strategies and exit |

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | **Strategy library — add new strategies here** |
| `scripts/strategy_engine.py` | Backtest engine + indicator cache |
| `scripts/evolve.py` | Multi-strategy evolutionary optimizer |
| `scripts/parity_check.py` | Verify Python engine matches TradingView |
| `remote/evolve-results-*.json` | Per-session results |
| `remote/best-ever.json` | Best config found across all sessions |

## Constraints

- **Trade TECL only** — long only, no shorting
- **≤3 trades per year** — this is a regime strategy, not a scalper
- **Beat buy-and-hold** — vs_bah_multiple > 1.0 is the target
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
