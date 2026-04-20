# /spike-results — View Montauk Engine Results

Show results from the latest Spike run (Montauk Engine output), run validation, and inspect the emitted backtest artifacts.

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
- Top-10 table (Regime Score, CAGR, Max DD, MAR, share_multiple, Trades, Params, Fitness)
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
If share_multiple varies >3x across assets, flag as possible TECL overfit.

**Cycle diagnostics** (if user wants deeper analysis):
```bash
cd scripts && ~/Documents/.venv/bin/python3 cycle_diagnostics.py
```

Show per-cycle trade breakdown for the winner: which bull cycles it captured, which bears it avoided, where the gaps are.

### Step 4 — Inspect run artifacts

Read the generated Phase 2 artifacts from `spike/runs/<N>/`:

1. `trade_ledger.json` — full entry/exit ledger
2. `signal_series.json` — daily `risk_on` / `risk_off` state
3. `equity_curve.json` — equity, B&H, and drawdown series
4. `validation_summary.json` — gate-by-gate validation summary
5. `dashboard_data.json` — precomputed bundle for the offline dashboard

### Step 5 — Comparison to baseline

Always compare the top result to montauk_821 (the 8.2.1 baseline):
- Share-count multiplier (`share_multiple`) delta (primary)
- Marker shape alignment delta (secondary)
- CAGR delta
- Max DD delta
- Dollar B&H delta (sanity only)
- Trade count comparison (NOT a quality signal — informational only)

If the winner beats 8.2.1 on `share_multiple` AND passes validation at its tier (T0 / T1 / T2) AND clears the marker shape diagnostic, recommend it as a candidate for production.

> **Note (2026-04-15, updated by Phase 7):** `share_multiple` is the only attribute name on `BacktestResult`. The deprecated `vs_bah_multiple` alias was retired in Phase 7 engine consolidation. Older `spike/leaderboard.json` entries persisted under the JSON key `vs_bah` are still readable via `report.py::_share_mult`.
