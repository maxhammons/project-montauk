# /spike — Find the Best TECL Strategy

Goal: find strategies that genuinely time bull/bear regimes on TECL. 8.2.1 is the baseline. Regime Score is the primary fitness target.

## The Flow

### Step 1 — Ask two questions

1. **"How long should the optimizer run?"** (default 5 hours)
2. **"Local or GitHub Actions?"**
   - **Local**: No time limit, faster feedback, Ctrl+C saves cleanly
   - **GH Actions**: 5-hour cap (free tier), auto-commits, close laptop and walk away

### Step 2 — Study the leaderboard + generate strategies

Before running the optimizer, do the creative work:

1. Read `spike/leaderboard.json` — the all-time top 20
2. Read `scripts/strategies.py` — all existing strategy functions
3. Read `reference/VALIDATION-PHILOSOPHY.md` — understand fitness targets
4. **Check `converged` flags.** Skip converged strategies. Focus on active ones.
5. For each non-converged top strategy:
   - Read its code, best params, and metrics
   - Think about WHY it works — what market conditions does it exploit?
   - Write improved variants as NEW strategy functions
6. **Generate 2-4 new strategy ideas** — fresh approaches, not just variants
7. **Check parameter complexity.** Prefer 5-8 params. Fitness rejects trades-per-param < 2.0.
8. **Prune dead weight** before adding — delete strategies that scored below 0.05 after 2+ runs, or converged below top 5. Max 15 strategies in registry.
9. Add new functions to `STRATEGY_REGISTRY` and `STRATEGY_PARAMS`

**Research-informed design principles:**
- **Fewer parameters is better.** 5-8 params with 30+ trades >>> 12 params with 15 trades
- **Target regime timing.** Fitness = `regime_score × hhi_penalty × dd_penalty × complexity_penalty × bah_bonus`
- **Avoid single-cycle dependence.** HHI > 0.35 = instant rejection
- **Max ≤3 trades/year.** Hard cap in fitness

**Available indicators** (all cached — same as Pine Script `ta.*`):
```
ind.ema(N)  ind.sma(N)  ind.tema(N)  ind.rsi(N)  ind.cci(N)  ind.willr(N)
ind.mfi(N)  ind.stoch_k(N)  ind.stoch_d(N)  ind.roc(N)  ind.mom(N)
ind.macd_line(F,S)  ind.macd_signal(F,S,Sig)  ind.macd_hist(F,S,Sig)
ind.atr(N)  ind.tr()  ind.stddev(N)  ind.realized_vol(N)
ind.bb_upper(N,M)  ind.bb_lower(N,M)  ind.bb_width(N,M)
ind.keltner_upper(E,A,M)  ind.keltner_lower(E,A,M)
ind.donchian_upper(N)  ind.donchian_lower(N)  ind.donchian_mid(N)
ind.adx(N)  ind.di_plus(N)  ind.di_minus(N)  ind.psar()
ind.ichimoku_tenkan(N)  ind.ichimoku_kijun(N)
ind.obv()  ind.vwap()  ind.vol_ema(N)
ind.highest(N)  ind.lowest(N)  ind.pct_change(N)
ind.slope(key, series, N)  ind.ema_of(key, series, N)
ind.crossover(a, b)  ind.crossunder(a, b)
ind.close  ind.high  ind.low  ind.open  ind.volume  ind.dates  ind.n
```

**Strategy cap: max 15.** Prune before adding.

### Step 3 — Launch the optimizer

#### If Local:

Run via Bash tool:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 spike_runner.py --hours <N>
```

Tell the user:
- **To stop**: `Ctrl+C` — saves everything cleanly
- Terminal shows progress every 5 minutes
- Results go to `spike/runs/YYYY-MM-DD/`

#### If GH Actions:

1. Check for in-progress runs:
   ```bash
   gh run list --workflow=spike.yml --status=in_progress --status=queued --json databaseId,status --jq 'length'
   ```
   If > 0: STOP. Tell user a run is already in progress.

2. Commit, push, trigger:
   ```bash
   git add scripts/ spike/
   git commit -m "spike: new strategies for $(date +%Y-%m-%d) run"
   git push
   gh workflow run spike.yml -f hours=<N> -f pop_size=60
   ```

3. Confirm:
   ```bash
   sleep 3 && gh run list --workflow=spike.yml --limit=1 --json url,status --jq '.[0]'
   ```

Tell the user: "Spike is running. Close your laptop — results auto-commit when done. Run `/spike-results` to check later."

### Step 4 — After completion

1. Read `spike/runs/<latest>/report.md`
2. Show top-10 table
3. Run validation: `cd scripts && ~/Documents/.venv/bin/python3 -m validation.sprint1`
4. Compare winner to montauk_821 baseline
5. If user wants Pine Script → generate for #1 winner (see below)
6. If user wants to push results → commit and push

## Pine Script generation

After every spike run, convert the winning strategy to Pine Script v6:

1. Read the winning Python function from `scripts/strategies.py`
2. Read its best parameters from the run results
3. Read `src/strategy/active/Project Montauk 8.2.1.txt` as structural template
4. Use `reference/pinescriptv6-main/` for correct syntax — do NOT guess
5. Write equivalent Pine Script with hardcoded winning params as `input.*` defaults
6. Save to `src/strategy/testing/Project Montauk <version>-candidate.txt`
7. Also save to `spike/runs/<date>/candidate.txt`

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | Strategy library — add new strategies here |
| `scripts/evolve.py` | Evolutionary optimizer (regime-score fitness, diversity-driven GA) |
| `scripts/spike_runner.py` | Main entry point |
| `scripts/validation/sprint1.py` | 6-test overfitting validation suite |
| `reference/VALIDATION-PHILOSOPHY.md` | Why we test, what we've built |
| `spike/leaderboard.json` | All-time top 20 (regime-score ranked) |
| `spike/hash-index.json` | Dedup index: {hash: {f, rs}} |

## Constraints

- **TECL only** — long only, no shorting
- **≤3 trades/year** — regime strategy, not scalper
- **Regime Score is primary** — vs_bah is displayed but doesn't drive ranking
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
