# /spike-results — View Optimizer Results

Show results from the latest spike run, run validation, and optionally generate Pine Script.

## The Flow

### Step 1 — Find latest results

```bash
# If GH Actions run, pull first
git pull 2>/dev/null

# Find latest run
ls spike/runs/ | grep -E '^[0-9]+$' | sort -n | tail -1
```

### Step 2 — Show the report

Read `spike/runs/<N>/report.md` and show:
- Top-10 table (Regime Score, CAGR, Max DD, MAR, vs B&H, Trades, Params, Fitness)
- Top 3 detail blocks (with regime score breakdown: bull capture, bear avoidance, HHI)
- Leaderboard changes (new entries, improvements, convergence)
- Session stats (evals, cache hits, diversity)

### Step 3 — Run validation

**Sprint 1 (anti-overfitting):**
```bash
cd scripts && ~/Documents/.venv/bin/python3 -m validation.sprint1
```

Show the Sprint 1 summary table:
- Deflated RS (does it beat the noise floor?)
- Exit-boundary proximity (memorization?)
- Jackknife (single-cycle dependence?)
- HHI concentration (bull/bear balance?)
- Meta-robustness (stable across regime definitions?)

Flag anything that fails.

**Cross-asset validation:**
```bash
cd scripts && ~/Documents/.venv/bin/python3 -m validation.cross_asset
```

Show how the top strategy performs on TQQQ and QQQ with the same params.
If vs_bah varies >3x across assets, flag as possible TECL overfit.

**Cycle diagnostics** (if user wants deeper analysis):
```bash
cd scripts && ~/Documents/.venv/bin/python3 cycle_diagnostics.py
```

Show per-cycle trade breakdown for the winner: which bull cycles it captured, which bears it avoided, where the gaps are.

### Step 4 — Generate Pine Script (if requested)

If user asks for Pine Script for any winner:

1. Read the winning Python function from `scripts/strategies.py`
2. Read its best params from `spike/runs/<N>/results.json`
3. Read `src/strategy/active/Project Montauk 8.2.1.txt` as structural template
4. Use `reference/pinescriptv6-main/` for syntax — do NOT guess
5. Write Pine Script v6 with winning params as `input.*` defaults
6. Save to `src/strategy/testing/Project Montauk <version>-candidate.txt`
7. Also save to `spike/runs/<N>/candidate.txt`

### Step 5 — Comparison to baseline

Always compare the top result to montauk_821 (the 8.2.1 baseline):
- Regime Score delta
- CAGR delta
- Max DD delta
- vs B&H delta
- Trade count and frequency comparison

If the winner beats 8.2.1 on Regime Score AND passes validation, recommend it as a candidate for production.
