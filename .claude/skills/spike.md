# /spike — Montauk Engine Strategy Discovery

**Spike is the skill. Spike launches and runs the Montauk Engine** — the strategy concept authoring + grid search + validation + backtest-artifact pipeline.

Goal: find strategies that **accumulate more shares of TECL than buy-and-hold** with ≤5 trades/year. Strategies must survive walk-forward, cross-asset, and concentration validation to earn a leaderboard slot and artifact bundle.

## The Flow

### Step 1 — Ask two questions

1. **"Do you have a strategy idea?"** (optional — Claude will also brainstorm its own)
2. **"How long should we work on this?"** (default 30 min)

If the user has an idea (e.g., "what about RSI recovery after oversold + a trend filter?"), Claude authors it as a concept. **Claude ALSO brainstorms 10 additional new concepts** regardless of whether the user has an idea. Shoot for 10 new concepts every run — more ideas = more grid combos = higher chance of finding winners. Sources for brainstorming:
- Signal families NOT yet in the registry (check `scripts/strategies.py`)
- Weaknesses of current leaderboard entries (e.g., "nothing handles post-crash rebounds well")
- The T0-DESIGN-GUIDE patterns that haven't been tried
- Cross-pollination of existing families (e.g., combining slope + RSI)
- Published trend-following signals (Donchian, Keltner, ADX, Parabolic SAR, etc.)
- Volatility-regime filters (realized vol vs long-term average)
- Momentum indicators (ROC, Williams %R, Stochastic) + trend confirmation

### Step 2 — Read the design guide + current state

1. Read `docs/design-guide.md` — the patterns that work and fail
2. Read `scripts/strategies.py` — existing concepts and GRIDS in `scripts/grid_search.py`
3. Read `spike/leaderboard.json` — current champion and gaps

### Step 3 — Author new concepts (the creative phase)

For each new idea (user's + Claude's brainstorms):

1. **Write the strategy function** in `scripts/strategies.py`
   - Use existing helpers where possible (`_ma_cross_with_slope`, `_ema_slope_above`, `_rsi_recovery_above_ema`)
   - Or write a new function following the `(ind, params) -> (entries, exits, labels)` pattern
   - Add docstring with the hypothesis in plain English

2. **Register** in `STRATEGY_REGISTRY`, `STRATEGY_TIERS` (as "T1"), and `STRATEGY_PARAMS`

3. **Define the canonical grid** in `scripts/grid_search.py :: GRIDS`
   - Each param gets a list of canonical values from `canonical_params.py`
   - Constraint: all values from the strict canonical set
   - Target: 10-50 combos per concept (product of list lengths)

4. **Smoke test (T0)** — backtest ONE canonical config to verify the concept has signal:
   ```bash
   cd scripts && ~/Documents/.venv/bin/python3 -c "
   from data import get_tecl_data
   from strategy_engine import Indicators, backtest
   from strategies import new_concept_fn
   df = get_tecl_data(); ind = Indicators(df)
   e, x, l = new_concept_fn(ind, {committed_params})
   r = backtest(df, e, x, l, cooldown_bars=5, strategy_name='new_concept')
   print(f'share={r.share_multiple:.3f}x trades={r.num_trades} tpy={r.trades_per_year:.2f}')
   "
   ```
   - If share < 1.5x → reconsider the concept before grid searching
   - If 0 trades → the concept is degenerate, redesign
   - If tpy > 5.0 → too active, add filtering

### Step 4 — Grid search (the testing phase)

Run the grid search on ALL registered concepts (existing + new):

```bash
cd scripts && ~/Documents/.venv/bin/python3 grid_search.py --top-n 25
```

This does:
1. **Exhaustive backtest** of every combo in every grid (~200 combos, ~5 seconds)
2. **Charter pre-filter** — drop combos with share < 1.0, trades < 5, tpy > 5.0
3. **Validate** top 25 survivors through the full tier-routed pipeline (~5-10 min):
   - Walk-forward across 4 time windows
   - Cross-asset on TQQQ + QQQ (same params)
   - Cross-asset re-optimization on TQQQ
   - Concentration (HHI), meta-robustness
   - Marker shape alignment (diagnostic, not a gate)
   - Composite confidence synthesis
4. **Update leaderboard** with PASS entries
5. **Report** champion + artifact bundle (`trade_ledger.json`, `signal_series.json`, `equity_curve.json`, `validation_summary.json`, `dashboard_data.json`)

### Step 5 — Report results

Show the user:
- Total combos tested → charter survivors → validated PASS/WARN/FAIL counts
- New leaderboard state (ranked by share_multiple)
- Champion: strategy name, params, share_multiple, trades/yr, CAGR, MaxDD
- Key validation metrics: composite confidence, walk-forward score, cross-asset score
- Artifact bundle paths (auto-generated for champion)

### Step 6 — Optional: GA deep search (T2)

If the user wants to explore beyond canonical grids (rare — grid search usually suffices):

```bash
cd scripts && ~/Documents/.venv/bin/python3 spike_runner.py --hours 1 --quick
```

This runs the GA evolutionary optimizer on all registered strategies with their `STRATEGY_PARAMS` ranges. GA-found candidates go through T2 validation (full statistical stack including Morris fragility, bootstrap, exit-proximity). T2 is the strictest tier — very few candidates survive.

Only suggest T2 if:
- Grid search found promising concepts but the canonical grid seems too coarse
- User explicitly asks for "deep search" or "overnight run"
- User wants to explore strategy families outside the canonical set

## Key files

| File | Role |
|------|------|
| `scripts/grid_search.py` | **Primary entry point** — exhaustive canonical search + validate |
| `scripts/strategies.py` | Strategy concepts + REGISTRY + TIERS + PARAMS |
| `scripts/canonical_params.py` | Strict canonical parameter sets |
| `scripts/spike_runner.py` | GA entry point (T2 deep search only) |
| `scripts/evolve.py` | Evolutionary optimizer (used by spike_runner) |
| `spike/leaderboard.json` | Validated PASS entries |
| `docs/design-guide.md` | Strategy design patterns + pre-flight checklist |

## Constraints

- **TECL only** — long only, no shorting
- **Regime strategy, not scalper** — ≤5 trades/year by charter. Low trade frequency is a feature.
- **Share-count multiplier vs B&H is primary** — must accumulate more TECL units than passive
- **Marker alignment** is a diagnostic, not a gate — north star for design, not the bouncer at the door
- **Every param value from the canonical set** — see `canonical_params.py`
- **Do not edit 8.2.1 defaults casually** — `StrategyParams` in `scripts/backtest_engine.py` is pinned by the golden-trade regression (`tests/test_regression.py`). Changing defaults means regenerating `tests/golden_trades_821.json` intentionally.
- **Read T0-DESIGN-GUIDE.md before authoring** — avoid known-failing patterns
