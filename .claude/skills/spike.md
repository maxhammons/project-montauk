# /spike — Iterative TECL Strategy Optimization (v2)

Goal: find strategies that beat buy-and-hold on TECL. Iterative creative loop — Claude sees per-cycle diagnostics, revises strategy code, optimizer tunes params, repeat.

## The Flow

### Step 1 — Ask one question

**"How long should we work on this?"** (default 2 hours)

This is local-only. The iterative loop requires Claude in the loop between optimizer chunks.

### Step 2 — Refresh data + build context

1. Run data refresh:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -c "from data import refresh_all; refresh_all()"
```

2. Build and display the regime map:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 regime_map.py
```

3. Read the regime map output. Study every bull/bear cycle — dates, magnitude, duration.

### Step 3 — Diagnose current strategies

1. Read `spike/leaderboard.json` — the all-time top 20
2. Read `scripts/strategies.py` — all existing strategy functions
3. Run cycle diagnostics on top 5 leaderboard strategies:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -c "
from data import get_tecl_data
from regime_map import build_regime_map
from cycle_diagnostics import diagnose_strategy, format_diagnostics
import json

df = get_tecl_data()
rm = build_regime_map(df)
with open('../spike/leaderboard.json') as f:
    lb = json.load(f)

for entry in lb[:5]:
    diag = diagnose_strategy(entry['strategy'], entry['params'], df, rm)
    print(format_diagnostics(diag))
    print('\n' + '='*65 + '\n')
"
```

4. **Study the diagnostics.** For each strategy, identify:
   - Which bull cycles have the lowest capture (biggest missed opportunities)
   - Which exit conditions fire mostly during bulls (these are killing performance)
   - Whether the bottleneck is bull_capture or bear_avoidance
   - Gaps where the strategy was out of market during major moves

### Step 4 — Creative phase (write/revise strategies)

With the regime map and cycle diagnostics in hand:

1. **Read `reference/VALIDATION-PHILOSOPHY.md`** — understand fitness targets
2. **Check `converged` flags** in leaderboard. Skip converged strategies.
3. **Design new strategies** targeting the specific weaknesses you identified:
   - If bull capture is the bottleneck → design strategies that stay in longer (wider exit triggers, faster re-entry)
   - If a specific exit reason fires too much during bulls → write a variant that softens or removes that exit
   - If gaps show the strategy exits and doesn't re-enter for months → add re-entry logic
4. **Generate 2-4 new strategy functions** in `scripts/strategies.py`
5. **Check parameter complexity.** Prefer 5-8 params. Fitness rejects trades-per-param < 2.0.
6. **Prune dead weight** — delete strategies below 0.05 fitness after 2+ runs, or converged below top 5. Max 15 strategies in registry.
7. Add new functions to `STRATEGY_REGISTRY` and `STRATEGY_PARAMS`

**Available indicators** (all cached):
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

### Step 5 — Optimizer chunk (~20 minutes)

Launch the first optimizer chunk:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 spike_runner.py --chunk --minutes 20 --pop-size 40
```

When it finishes, read the chunk results. Note the state file path for the next chunk.

### Step 6 — Analyze intermediate results

After each chunk:

1. Read the chunk results (printed as `###CHUNK_RESULT###` JSON)
2. Run cycle diagnostics on the chunk's top strategies:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -c "
from data import get_tecl_data
from regime_map import build_regime_map
from cycle_diagnostics import diagnose_strategy, format_diagnostics

df = get_tecl_data()
rm = build_regime_map(df)

# Use the best strategy/params from the chunk results
diag = diagnose_strategy('<STRATEGY_NAME>', <PARAMS_DICT>, df, rm)
print(format_diagnostics(diag))
"
```

3. **Check boundary hits** in diagnostics — if a param is hitting "high" or "low", consider expanding the search space in `STRATEGY_PARAMS`
4. **Identify what changed** — did bull capture improve? Did the bottleneck shift?

### Step 7 — Revise strategy CODE and repeat

Based on the intermediate results:

1. **Revise strategy logic** — not just params, the actual entry/exit code
2. **Expand param spaces** if boundary hits were detected
3. **Add/remove strategies** as needed

Launch the next chunk (with state from previous chunk):
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 spike_runner.py --chunk --minutes 20 --pop-size 40 --state-file <STATE_FILE_PATH>
```

**Repeat Steps 6-7 until the time budget is exhausted.**

### Step 8 — Final validation

After the last chunk:

1. **Cross-asset validation** — test the winner on TQQQ and QQQ:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -m validation.cross_asset
```

2. **Sprint 1 validation** — 6 anti-overfitting tests:
```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -m validation.sprint1
```

3. **Compare winner to montauk_821 baseline**

4. If user wants Pine Script → generate for #1 winner

5. If user wants to push results → commit and push

6. If user wants extended param tuning → suggest `/spike-focus`

## Key files

| File | Role |
|------|------|
| `scripts/strategies.py` | Strategy library — add new strategies here |
| `scripts/evolve.py` | Optimizer: `evolve()` for full runs, `evolve_chunk()` for iterative |
| `scripts/spike_runner.py` | Entry point: `--hours` for full, `--chunk` for iterative |
| `scripts/regime_map.py` | Bull/bear cycle detection and formatting |
| `scripts/cycle_diagnostics.py` | Per-cycle trade analysis |
| `scripts/validation/cross_asset.py` | Cross-asset validation (TQQQ, QQQ) |
| `scripts/validation/sprint1.py` | 6-test overfitting validation suite |
| `spike/leaderboard.json` | All-time top 20 |

## Constraints

- **TECL only** — long only, no shorting
- **≤3 trades/year** — regime strategy, not scalper
- **vs B&H is primary** — must beat buy-and-hold
- **Never modify `src/strategy/active/`** — candidates go in `testing/`
- **Max 15 strategies** in registry
