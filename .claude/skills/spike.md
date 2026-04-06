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

Ask the user: **"How long should the optimizer run? (1-5 hours, default 5)"**

Hard cap is 5 hours (GitHub Actions free tier limit). If they say more than 5, use 5.
If they just say "go" or "run it", use 5 hours.

Do NOT proceed until they answer.

### Step 2 — Study the leaderboard (~50% of Claude's effort)

Before writing any new code, read the current state:

1. Read `spike/leaderboard.json` — the all-time top 20
2. Read `scripts/strategies.py` — all existing strategy functions
3. **Check the `converged` field on each entry.** Skip strategies marked `"converged": true` — they've plateaued and further optimization is wasted effort. Focus only on strategies that are still `active` or have low `runs_without_improvement`.
4. For each **non-converged** top strategy on the leaderboard:
   - Read its function code
   - Read its best params and metrics from the leaderboard
   - Think about WHY it works (or doesn't) — what market conditions does it exploit?
   - Consider: can its logic be refined? Can you add a smarter exit? A better entry filter?
5. Write improved variants as NEW strategy functions (don't modify the original — the optimizer needs both to compare)

**Convergence rules:**
- Strategies auto-converge after 3 consecutive runs with no fitness improvement
- Converged strategies are still tested by the optimizer (their params may shift), but Claude should NOT spend tokens writing new variants of them
- To manually flag/unflag: `python3 scripts/evolve.py --converge <name>` / `--unconverge <name>`
- If ALL leaderboard strategies are converged, spend 100% of effort on new ideas instead

**Example optimizations (for non-converged strategies only):**
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

**Strategy cap: max 15 in STRATEGY_REGISTRY.** Before adding new strategies, **aggressively prune dead weight:**

1. **Auto-prune in optimizer:** `evolve.py` automatically skips strategies that have been in 2+ runs and never reached fitness 0.05 (baseline). They still exist in code but get zero compute time.
2. **Claude must delete before adding:** Before writing any new strategy, check the leaderboard. Delete any strategy (function + REGISTRY + PARAMS) that meets ANY of these:
   - Fitness below 0.05 after 2+ runs (already auto-skipped, but clean up the code too)
   - Converged AND below top 5 on the leaderboard
   - Never produced a single trade across any run
3. **Net count must stay ≤ 15.** If at 15 after pruning, delete one more before adding.

This keeps optimizer time focused instead of spread thin. A bad strategy costs ~20% of a run's compute — cutting 3 duds is like adding an extra hour.

### Step 4 — Commit, push, and launch GitHub Actions

The optimizer runs in the cloud so Max can close his laptop.

1. **Check for in-progress runs** — BEFORE doing anything else:
   ```bash
   gh run list --workflow=spike.yml --status=in_progress --status=queued --json databaseId,status --jq 'length'
   ```
   If the result is > 0, **STOP**. Tell Max: "A spike run is already in progress. Wait for it to finish or cancel it (`gh run cancel <id>`) before starting a new one." Do NOT proceed.
2. **Commit** all new/modified strategies in `scripts/strategies.py`
3. **Push** to `main`
4. **Trigger the workflow:**
   ```bash
   gh workflow run spike.yml -f hours=<N> -f pop_size=60
   ```
5. **Confirm launch** — show Max the run URL:
   ```bash
   sleep 3 && gh run list --workflow=spike.yml --limit=1 --json url,status --jq '.[0]'
   ```
6. **Tell Max:** "Spike is running. Close your laptop whenever — results auto-commit to `spike/` when done. Run `/spike results` to check later."

That's it for this session. The GH Action handles everything autonomously:
- Tests ALL registered strategies with evolutionary parameter optimization
- Seeds populations from historical winners (doesn't repeat past work)
- Deduplicates configs across runs via hash index
- Auto-generates markdown report with top-10 table
- Updates all-time leaderboard (top 20)
- Commits results to `spike/runs/YYYY-MM-DD/` and pushes

### Step 5 — Show results (separate invocation)

When Max runs `/spike results` (or asks to see results), OR when returning after a run:

1. `git pull` to get the GH Action's commit
2. Find the latest run: `ls spike/runs/ | sort | tail -1`
3. Read `spike/runs/<date>/report.md`
4. Show the top-10 table and key findings
5. **Generate full Pine Script v6 for the #1 winner** (see below)
6. Commit the Pine Script and push

## Pine Script generation (automatic for #1 winner)

After every spike run, convert the winning strategy to production-ready Pine Script v6:

1. Read the winning Python function from `scripts/strategies.py`
2. Read its best parameters from the run results
3. Read `src/strategy/active/Project Montauk 8.2.1.txt` as a structural template (input groups, position sizing, chart labels, etc.)
4. Use the Pine Script v6 reference in `reference/pinescriptv6-main/` for correct syntax — do NOT guess at API
5. Write equivalent Pine Script that:
   - Implements the same entry/exit logic as the Python function
   - Hardcodes the winning parameters as `input.*` defaults (so they're visible and tunable in TradingView)
   - Matches the 8.2.1 structure: input groups, exit-reason labels, cooldown logic, 100% equity sizing
6. Save to: `src/strategy/testing/Project Montauk <version>-candidate.txt`
   - Version = next major after 8.2.1 (e.g., `9.0`, `9.1`, etc.)
   - Check what already exists in `src/strategy/testing/` to avoid overwriting
7. Also save a copy in the run folder: `spike/runs/<date>/candidate.txt`

If the user asks for Pine Script for additional winners (not just #1), generate those too with distinct version suffixes (e.g., `9.0-A`, `9.0-B`).

## Checking on a run

```bash
# Is it still running?
gh run list --workflow=spike.yml --limit=1

# Watch live logs
gh run watch

# Pull results after completion
git pull
```

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | **Strategy library — add new strategies here** |
| `scripts/strategy_engine.py` | Backtest engine + indicator cache |
| `scripts/evolve.py` | Evolutionary optimizer (with history + dedup) |
| `scripts/spike_runner.py` | **Main entry point — wraps everything** |
| `scripts/report.py` | Auto-generates markdown reports |
| `spike/runs/YYYY-MM-DD/` | Per-session output (report, results, log) |
| `spike/leaderboard.json` | All-time top 20 strategies |
| `spike/hash-index.json` | Compact dedup index: {hash: fitness} |
| `src/strategy/testing/` | **Pine Script candidates** — auto-generated for TradingView |
| `src/strategy/active/Project Montauk 8.2.1.txt` | Template for Pine Script generation (read-only) |

## Directory structure

```
spike/
├── runs/                              # One folder per spike session
│   ├── 2026-04-04/
│   │   ├── report.md                  # The deliverable: top-10 table + details
│   │   ├── results.json               # Full optimizer output (with trade lists)
│   │   ├── candidate.txt              # Pine Script v6 for the #1 winner
│   │   └── log.txt                    # Console output
│   └── 2026-04-04-2/                  # Second run same day
├── leaderboard.json                   # All-time top 20
└── hash-index.json                    # Compact dedup index {hash: fitness}

src/strategy/testing/                  # Pine Script candidates ready for TradingView
└── Project Montauk 9.0-candidate.txt  # Latest winner (auto-generated by /spike)
```

## Constraints

- **Trade TECL only** — long only, no shorting
- **≤3 trades per year** — this is a regime strategy, not a scalper
- **Beat buy-and-hold** — vs_bah_multiple > 1.0 is the target
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
