# Project Montauk — Pipeline

**Canonical flow (four phases):**

```
generate ideas   →   backtest + validate / check for overfitting   →   certify + admit only Gold Status rows   →   visualize in the UI
 (scripts/search)         (scripts/validation)                               (scripts/certify → spike/leaderboard.json)                (viz/)
```

**The leaderboard rule:** `spike/leaderboard.json` is the authority surface, not a mixed-trust watchlist. Entries are admitted only if they have **Gold Status**: final validation verdict `PASS`, `certified_not_overfit=True`, `backtest_certified=True` / artifact-verified, and share-count outperformance versus B&H in the full, real, and modern eras. This contract is defined in `scripts/certify/contract.py` and reused by promotion, recertification, artifact backfill, champion finalization, and the viz builder. Raw performance does not admit a row by itself; it only ranks already-Gold rows. If fewer than 20 rows are Gold, the leaderboard has fewer than 20 rows.

This document defines the intended operating model of the project under the charter. If this document ever conflicts with `docs/charter.md`, the charter wins.

---

## 1. Naming

The skill is **Spike**. Spike launches and runs the **Montauk Engine** — the optimizer + tier-routed validator + run-artifact emitter.

- "Spike" = the entrypoint / command surface (`/spike`, `/spike-focus`, `/spike-results`)
- "Montauk Engine" = the underlying machinery (search + tier-routed validation + artifact emission)

This is a semantic split, not a code rename.

---

## 2. Canonical Full-Run Flow

The authoritative full-run path is:

1. **Refresh data + verify integrity**
   Update TECL and validation datasets. Rebuild `data/manifest.json`. Run `scripts/data/quality.py` (consolidated `audit_all()` over every data-integrity check including Yahoo-vs-Stooq divergence, synthetic-rebuild residual, seam continuity, OHLC sanity) as a pre-check before any backtest.

2. **Hypothesize and / or Discover**
   - Hand-author T0 hypothesis strategies (registered with committed params before any backtest)
   - Or: run the optimizer for T1 / T2 candidates across registered strategy families
   - Marker shape alignment is recorded for every candidate

3. **Save raw results + standardized artifacts**
   Each candidate emits the five standardized run artifacts (`trade_ledger.json`, `signal_series.json`, `equity_curve.json`, `validation_summary.json`, `dashboard_data.json`) under `spike/runs/NNN/`. Raw output preserved for research and audit. Each candidate carries its tier tag.

4. **Validate at the candidate's tier**
   - T0 candidates clear the light pipeline
   - T1 candidates clear the medium pipeline
   - T2 candidates clear the full statistical stack
   See `VALIDATION-PHILOSOPHY.md` for what each tier tests.

5. **Certify + Promote**
   Gate 7 synthesis computes `promotion_ready` (tier-appropriate PASS across all 7 gates), `certified_not_overfit` (promotion-ready plus required anti-overfit certification checks), `backtest_certified` (certified plus complete standardized artifacts), and `gold_status` (certified, artifact-verified, and beating B&H in full / real / modern eras). The leaderboard admits entries that satisfy the canonical Gold Status contract in `scripts/certify/contract.py`. Each entry is tagged with its tier and Gold Status. To re-validate every existing leaderboard entry under current rules: `scripts/certify/recertify_leaderboard.py`.

6. **Simulate deployment overlay**
   Run the approved Roth account overlay for the validated champion.

7. **Build native HTML viewer**
   `python viz/build_viz.py` reads `spike/leaderboard.json` + each Gold strategy's `spike/runs/NNN/dashboard_data.json`, assembles the bundle, and writes a self-contained `viz/montauk-viz.html`. Non-blocking; a missing/stale run dir gets flagged with a "stale artifact" badge rather than aborting.

8. **Manually execute from the daily signal**
   The champion's `signal_series.json` emits daily risk_on / risk_off state. Execution happens manually in a brokerage account — no broker API, no auto-deploy.

That is the Montauk Engine. Everything else is support work.

---

## 3. Canonical Entrypoints

### Full runs

`scripts/spike_runner.py --hours ...` is the canonical promotion path.

It is responsible for:

- running discovery (T1 / T2 search) and accepting registered T0 candidates
- recording marker shape alignment for every candidate
- preserving raw results with tier tags
- running tier-routed validation
- updating the Gold Status authority leaderboard
- simulating the approved Roth overlay for the validated champion
- generating human-readable reporting
- emitting the five standardized JSON artifacts per run (trade ledger, signal series, equity curve, validation summary, dashboard bundle)
- triggering `viz/build_viz.py` at end-of-run (non-blocking) to rebuild the native HTML viewer

### Raw optimization

`scripts/evolve.py` is the search engine, not the promotion authority.

Its outputs default to T2. They may discover good ideas, but by themselves they do not define what becomes real project memory.

### Hypothesis registration

T0 candidates are registered through the strategy registry with:

- name
- one-line hypothesis description
- committed parameter values (from the strict canonical set)
- registration timestamp

A T0 strategy that fails registration discipline (missing timestamp, non-canonical params, post-hoc registration) is rerouted to T1 or T2.

### Research chunk mode

`spike_runner.py --chunk` is a research loop for iterative local work. It is useful for exploration. It is not the canonical leaderboard promotion path unless explicitly brought under the same tier-routed validation rules.

---

## 4. Required Artifacts Per Full Run

Each full run leaves behind a complete audit trail under `spike/runs/NNN/`:

| Artifact | Purpose |
|----------|---------|
| `raw_results.json` | Raw output before validation, with tier tags and marker shape metrics |
| `results.json` | Validated run output with verdicts, tier tags, and champion state |
| `report.md` | Human-readable summary of raw vs validated outcomes, tier-by-tier |
| `log.txt` | Full execution log |
| `trade_ledger.json` | Full trade list — entry/exit date, price, reason, pnl_pct |
| `signal_series.json` | Daily risk_on / risk_off signal series (the execution-surface contract) |
| `equity_curve.json` | Bar-by-bar equity + drawdown series |
| `validation_summary.json` | Per-gate PASS / WARN / FAIL details including `backtest_certified` and `promotion_ready` flags |
| `dashboard_data.json` | Precomputed bundle the HTML viz reads directly (no viz-time backtest re-runs) |
| `overlay_report.json` | Roth overlay simulation for the validated champion |

Raw output is for research. Validated output is for memory and promotion. The `dashboard_data.json` bundle is what `viz/build_viz.py` embeds into the self-contained `viz/montauk-viz.html`.

---

## 5. Promotion Rules

The pipeline has a simple rule:

- raw winner -> **not promotable**
- validated **PASS** winner at its tier -> certification candidate
- Gold Status winner -> promotable to `spike/leaderboard.json`

Operationally:

- only Gold Status entries belong on `leaderboard.json`, each carrying its tier tag
- WARN and FAIL entries remain in run artifacts only
- if no strategy passes, the run still matters, but the leaderboard does not change
- if a strategy does not emit the five standardized artifacts completely, it cannot become `backtest_certified` and therefore cannot be Gold
- if a strategy fails to beat B&H in any of the full, real, or modern eras, it cannot be Gold
- the leaderboard keeps the top performing Gold strategies, up to 20 rows

A T0-PASS strategy and a T2-PASS strategy are both certification candidates. They become real leaderboard winners only after Gold Status. The tier tag tells the user what level of statistical scrutiny backs the result.

---

## 6. Validation In The Pipeline

Validation is not an optional post-processing step. It is the center of the pipeline.

The validation stack is **tier-routed**:

- Tier 0 (Hypothesis): code integrity → cross-asset → walk-forward → marker shape
- Tier 1 (Tuned): T0 stack + parameter plateau + concentric shell on tuned region
- Tier 2 (Discovered): T1 stack + deflation + boundary perturbation + jackknife + HHI + fragility + bootstrap + cross-asset re-optimization

The best raw strategy can still be rejected. That is a healthy run, not a broken one.

This document defines the sequence and promotion logic. Exact thresholds, formulas, and heuristic settings belong in the scripts.

---

## 7. Signal Certification And Visualization

The end product of the factory is a `backtest_certified` signal bundle: the five standardized JSON run artifacts plus the native HTML viewer rebuilt from `dashboard_data.json`.

Rules:

- the best validated PASS winner becomes the champion regardless of tier
- `montauk_821` is the canonical 8.2.1 baseline; its params live in `scripts/backtest_engine.py :: StrategyParams`
- final execution remains manual — the daily `signal_series.json` is the contract with the user's brokerage
- there is no longer any auto-generated external script or platform compile step

Python is the research, validation, and execution-signal layer. The HTML viewer is the visualization layer.

The Roth overlay sits after validation and before manual deployment review. It is an account-analysis layer, not a change to the signal definition.

### Gate 7 — `certified_not_overfit`, `backtest_certified`, and `promotion_ready`

Gate 7 synthesis determines promotion readiness and anti-overfit certification. A strategy is `promotion_ready` when it is a tier-appropriate PASS. A strategy is `certified_not_overfit` when `promotion_ready=True` and the anti-overfit certification checks below all pass. A strategy becomes `backtest_certified` only when **all** of the following hold:

- **Engine integrity** — bar-close signals, single-position, no lookahead; passes `scripts/validation/integrity.py`
- **Golden regression pass** — `tests/test_regression.py` matches `tests/golden_trades_821.json` within ±0.001% PnL per trade on the 8.2.1 default config
- **Shadow-comparator agreement** — dev-only check (`tests/test_shadow_comparator.py`) against `backtesting.py` / `vectorbt` within 0.5% per trade
- **Data-quality pre-check pass** — `scripts/data_quality.py` all PASS (including Yahoo-vs-Stooq divergence < 0.01% on real data, manifest checksum match, synthetic-rebuild residual)
- **Artifact completeness** — all five standardized JSON artifacts emitted for the run

`certified_not_overfit = promotion_ready AND required certification checks`

`backtest_certified = certified_not_overfit AND artifact completeness`

`gold_status = certified_not_overfit AND backtest_certified AND full/real/modern share_multiple >= 1.0`

Only Gold Status entries reach the leaderboard. `certified_not_overfit` is necessary but not sufficient.

### Visualization (`viz/montauk-viz.html`)

Built by `viz/build_viz.py` from `dashboard_data.json` + `spike/leaderboard.json`. Library: TradingView Lightweight Charts v4 (OSS, MIT-style, vendored to `viz/lightweight-charts.js`). The output is a single self-contained HTML file — `open viz/montauk-viz.html`, no server, no install. MVP feature set: price candles with synthetic-period shading, trade markers, equity + drawdown panes, drawdown underwater pane, Gold Status strategy sidebar, metrics + gate-by-gate validation summary, 1Y / 3Y / 5Y recent-period scorecards, manifest-verified provenance badge, north-star marker toggle, 1Y/5Y/ALL time range controls, crosshair + tooltip.

---

## 8. CI And Local Should Match

GitHub Actions should run the same promotion logic as local full runs:

- discover and / or accept registered hypotheses
- validate at each candidate's tier
- promote Gold Status only
- generate artifacts
- commit `spike/` outputs

There should never be a special CI-only path that bypasses tier routing or validation rules.

---

## 9. Strategy Scope

Project Montauk is allowed to search across many TECL strategy families.

What it is **not** allowed to do is drift outside the charter:

- no non-TECL production strategy
- no shorting
- no intraday logic
- no multi-position system
- no "research winner" that skips `backtest_certified` and still counts as complete
- no strategy that punishes low trade frequency

The project is a TECL share-accumulation factory, not a generic quant sandbox.
