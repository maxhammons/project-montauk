# Project Montauk

A Python TECL share-accumulation strategy system with native HTML visualization. The Python engine is the single source of truth for signals; daily risk_on / risk_off output is executed manually in a brokerage account. A local TradingView Lightweight Charts viewer replaces the old chart surface.

## Directory Structure

```
Project Montauk/
├── CLAUDE.md                  ← You are here
├── data/                      # All data files
│   ├── TECL.csv               # TECL OHLCV (synthetic pre-2008-12-17 + real after) + vix_close + provenance columns
│   ├── VIX.csv                # CBOE VIX OHLCV
│   ├── XLK.csv                # TECL underlying
│   ├── TQQQ.csv               # Synthetic pre-2010-02-11 + real after + provenance columns
│   ├── QQQ.csv                # TQQQ underlying
│   ├── SGOV.csv               # iShares 0-3 Month Treasury Bond ETF
│   ├── treasury-spread-10y2y.csv  # FRED T10Y2Y
│   ├── fed-funds-rate.csv     # FRED DFF
│   ├── tbill-3m.csv           # 3-Month Treasury Bill Rate
│   ├── manifest.json          # Per-ticker source URLs, seam dates, SHA256 checksums, build timestamps
│   └── markers/               # Hand-marked cycle data
│       ├── TECL-markers.csv   # Buy/sell cycle markers (north star)
│       ├── TECL-chart.csv     # Chart data
│       └── TECL-chart.html    # Interactive chart
├── docs/                      # All documentation
│   ├── charter.md             # Project mission, guardrails, success definition
│   ├── charter-appendix.md    # Discovery north star + Roth overlay extensions
│   ├── design-guide.md        # T0 hypothesis design patterns + pre-flight checklist
│   ├── validation-philosophy.md  # Tier framework (T0/T1/T2) + overfitting defense
│   ├── validation-thresholds.md  # Threshold definitions for validation gates
│   ├── project-status.md      # Current implementation status + known gaps
│   ├── pipeline.md            # Visual pipeline diagram (source of truth)
│   ├── plan.md                # Marker prior + Roth overlay plan
│   ├── Montauk 2.0/           # Historical record of the Pine/TV excision project
│   └── research/              # Market research + academic papers
│       ├── synthesis.md
│       ├── roadmap.md
│       ├── checklist.md
│       ├── sources.csv
│       └── reports/
├── scripts/                   # Python code — grouped by pipeline phase (see scripts/README.md)
│   ├── README.md              # Authoritative folder-by-folder purpose map
│   ├── data/                  # Load + verify market data
│   │   ├── loader.py          # TECL/TQQQ/QQQ/XLK/SGOV/VIX loader (was data.py)
│   │   ├── audit.py           # Synthetic formula re-verification (was data_audit.py)
│   │   ├── crosscheck.py      # Yahoo vs Stooq divergence (was data_crosscheck.py)
│   │   ├── manifest.py        # data/manifest.json build + verify (was data_manifest.py)
│   │   ├── quality.py         # Consolidated PASS/WARN/FAIL audit_all() (was data_quality.py)
│   │   └── rebuild_synthetic.py   # Deterministic synthetic rebuild (was data_rebuild_synthetic.py)
│   ├── engine/                # Backtest machinery
│   │   ├── strategy_engine.py # The engine: Indicators class + backtest() + run_montauk_821()
│   │   ├── regime_helpers.py  # Regime-scoring helpers (was backtest_engine.py post-Phase-7)
│   │   └── canonical_params.py# Canonical-parameter rules + tier auto-promotion
│   ├── strategies/            # Strategy library + ranking helpers
│   │   ├── library.py         # All registered strategies + REGISTRY (was strategies.py)
│   │   ├── markers.py         # Marker-alignment scoring (was discovery_markers.py)
│   │   └── regime_map.py      # Bull/bear cycle segmentation
│   ├── search/                # Discovery + optimization (pipeline phase 1)
│   │   ├── grid_search.py     # Exhaustive canonical-grid backtest + validate
│   │   ├── evolve.py          # GA optimizer + leaderboard updater (with REQUIRED_CERTIFICATION_CHECKS guard)
│   │   ├── spike_runner.py    # Main /spike entry point
│   │   └── share_metric.py    # Legacy share_multiple JSON schema compat
│   ├── validation/            # 7-gate validation pipeline (pipeline phase 2)
│   │   ├── pipeline.py        # Orchestrator: gates 1..7 + composite confidence
│   │   ├── integrity.py       # Gate 0: engine integrity + golden regression + shadow comparator + data_quality precheck
│   │   ├── candidate.py       # Gate 1: result-quality metrics
│   │   ├── sprint1.py         # Gate 2: search-bias diagnostics (T2)
│   │   ├── walk_forward.py    # Gate 4: time-window generalization
│   │   ├── cross_asset.py     # Gate 6: TQQQ + QQQ portability + re-opt
│   │   ├── deflate.py         # Monte Carlo null distribution
│   │   └── uncertainty.py     # Gate 5: Morris fragility + stationary bootstrap
│   ├── certify/               # Post-validation certification + leaderboard sealing (pipeline phase 3)
│   │   ├── certify_champion.py      # Emit 5 artifacts + finalize backtest_certified for one strategy
│   │   ├── recertify_leaderboard.py # Re-validate every leaderboard entry under current rules
│   │   └── backfill_artifacts.py    # Materialize artifacts for older runs
│   ├── diagnostics/           # Post-run analysis (no verdict impact)
│   │   ├── cycle_diagnostics.py  # Per-cycle trade breakdown
│   │   ├── report.py             # Markdown report generator
│   │   └── roth_overlay.py       # Roth IRA cashflow simulator
│   ├── experimental/          # WIP / scratch — not in main pipeline
│   └── requirements.txt       # Python deps: pandas, numpy, requests
├── spike/                     # All /spike optimization output
│   ├── runs/NNN/              # Per-session: report.md, results.json, log.txt + five standardized artifacts
│   ├── leaderboard.json       # All-time top 20 strategies
│   └── hash-index.json        # Compact dedup index: {hash: fitness}
├── tests/                     # Pytest suite
│   ├── test_indicators.py     # EMA / TEMA / ATR / ADX reference-value tests (both engines)
│   ├── test_regression.py     # Golden-trade regression net for 8.2.1 defaults
│   ├── golden_trades_821.json # Frozen trade ledger for 8.2.1 defaults
│   ├── generate_golden_trades.py
│   ├── test_backtest_engine.py
│   └── test_shadow_comparator.py  # Dev-only second-opinion vs backtesting.py / vectorbt
├── viz/                       # Native HTML visualization tool
│   ├── build_viz.py           # Reads spike/runs/NNN/dashboard_data.json, assembles shell, writes HTML
│   ├── templates/             # HTML shell + inline JS/CSS
│   ├── lightweight-charts.js  # Vendored TradingView Lightweight Charts (OSS, MIT-style)
│   └── montauk-viz.html       # Self-contained viewer (open with `open viz/montauk-viz.html`)
└── .claude/skills/            # Claude Code skills
    ├── spike.md               # /spike — interactive creative loop
    ├── spike-focus.md         # /spike-focus — GH Actions deep search
    ├── spike-results.md       # /spike-results — view results + inspect artifacts
    ├── about.md               # Architecture documentation
    └── sync.md                # Git sync utility
```

## Active Signal Engine

The canonical execution path is `scripts/strategy_engine.py :: run_montauk_821()` driving the 8.2.1 parameter set. `strategy_engine.backtest()` is the simpler per-candidate path the evolutionary search uses on entries/exits arrays. Both live in the same module and share the same NaN-safe indicators (`_ema`, `_tema`, `_atr`, `_adx`).

Phase 7 (engine consolidation) collapsed the previous two-engine setup: the monolithic execution loop that used to live in `backtest_engine.py` was ported into `strategy_engine.run_montauk_821()` and now uses the bug-fixed indicators (the old `backtest_engine.tema` returned all-NaN due to an SMA-seed-meets-NaN-prefix bug). The 8.2.1 default ledger is unchanged because the TEMA gates (`enable_slope_filter`, `enable_below_filter`) default OFF — when those flags are toggled on, the engine now actually filters entries.

`scripts/backtest_engine.py` is now a helpers-only module (`Regime`, `RegimeScore`, `detect_bear_regimes`, `detect_bull_regimes`, `score_regime_capture`).

### Strategy: 8.2.1 (current defaults)

**Entry conditions** (all must be true):
- EMA-short (15) > EMA-med (30)
- Trend filter: 70-bar EMA slope is positive
- TEMA slope is positive (optional, 200-bar Triple EMA)
- Price is above TEMA (optional)
- Not in sideways market (optional, Donchian range check)
- Not in post-exit cooldown (2 bars)

**Exit conditions** (checked in priority order):
1. **EMA Cross Exit**: `barssince(crossunder(emaShort, emaLong)) < confirmBars` with 0.2% buffer — fires within the confirmation window, not only on the exact cross bar
2. **ATR Exit**: Price falls below previous close minus 3x ATR(40)
3. **Quick EMA Exit**: 15-bar EMA percent change over 5-bar window exceeds -8.2% threshold
4. **Trailing Stop** (optional, default OFF): Price drops >25% from peak since entry
5. **TEMA Slope Exit** (optional, default OFF): TEMA slope turns negative

## Architecture Notes

- **Single position model**: 100% equity per trade, long-only, no pyramiding, no shorting
- **Bar-close signals**: no lookahead, no repainting
- **Cooldown logic**: After every exit, a configurable cooldown (bars) prevents immediate re-entry
- **Slippage**: 5 bps applied on both entry and exit fills (unified in Phase 1c, single engine since Phase 7)
- **Execution**: Python emits a daily `risk_on` / `risk_off` signal; execution happens manually in a brokerage account. No broker API, no auto-deploy.
- **Visualization**: `viz/montauk-viz.html` is a self-contained HTML viewer — no server, no install. Rebuilt from `spike/runs/NNN/dashboard_data.json` via `viz/build_viz.py`.

## Run Artifacts

Every `spike_runner.py` run emits five standardized JSON artifacts under `spike/runs/NNN/` (Codex-promoted schema from Montauk 2.0 Phase 2b):

| Artifact | Contents |
|----------|----------|
| `trade_ledger.json` | Full trade list: entry/exit date, price, reason, pnl_pct |
| `signal_series.json` | Daily risk_on / risk_off state series |
| `equity_curve.json` | Bar-by-bar equity + drawdown series |
| `validation_summary.json` | Per-gate PASS / WARN / FAIL with details |
| `dashboard_data.json` | Precomputed bundle the HTML viz reads directly (no viz-time backtest re-runs) |

## Working with This Code

- **To edit the active strategy defaults**: Modify the `StrategyParams` defaults in `scripts/strategy_engine.py` (post-Phase-7 location). Golden-trade regression (`tests/test_regression.py`) will flag any behavior change until the ledger is regenerated intentionally.
- **To refresh data**: Run the data-refresh flow in `scripts/data.py`, then rebuild the manifest (`scripts/data_manifest.py`) and re-run `scripts/data_quality.py` to confirm all PASS.
- **To visualize a run**: `python viz/build_viz.py && open viz/montauk-viz.html`. The HTML is self-contained.
- **Strategy behavior changes should be tied to a golden-trade refresh**: `tests/generate_golden_trades.py` regenerates `tests/golden_trades_821.json`. Only do this when you intend for the baseline to move.

### Project Organization

Keep the folder and file structure clean and easy to navigate. The owner needs to be able to jump in and quickly understand what's going on at a glance.

- **Use clear, descriptive file names** — version numbers, dates, and purpose should be obvious from the name
- **Put files in the right place** — follow the directory structure above; don't dump things in the root or create ad-hoc folders
- **Clean up after yourself** — remove temp files, don't leave orphaned outputs or half-finished work lying around
- **Keep output organized sequentially** — spike runs go in `spike/runs/NNN/`, not loose in the project root
- **When in doubt, match the existing pattern** — look at how similar files are already named and placed
- **Keep `docs/pipeline.md` current** — when you change the fitness function, optimizer logic, validation suite, data flow, GH Actions workflow, or any process/pipeline behavior, update the pipeline diagram to match. This is the visual source of truth for how the system works.

## Optimization Tools — Spike + the Montauk Engine

**Spike** is the skill (the entrypoint / command surface). Spike launches and runs the **Montauk Engine** — the optimizer + tier-routed validator + run-artifact emitter. This is a semantic split, not a code rename: files and commands keep their existing names.

Two complementary skills for strategy development:

### `/spike` — Interactive creative loop (local)

Iterative optimization where Claude sees per-cycle diagnostics, revises strategy *code* between optimizer chunks, and collaborates with the Montauk Engine to find strategies that match the marker shape and accumulate more shares than buy-and-hold.

1. **Run `/spike`** — asks how long (default 2h), runs locally
2. **Claude sees the regime map** — every bull/bear cycle with dates, magnitude, duration
3. **Claude sees cycle diagnostics** — where each strategy's trades fall in each cycle, what exits fire during bulls
4. **Claude writes strategies** informed by actual cycle data
5. **Optimizer runs 20-min chunks** — Claude reviews results and revises code between chunks
6. **Cross-asset + sprint1 validation** on the winner at the end
7. All output goes to `spike/runs/NNN/` with the five standardized JSON artifacts

### `/spike-focus` — Deep param optimization (GH Actions)

Fire-and-forget extended optimization on 1-2 specific strategies. Use after `/spike` has identified promising strategy logic.

1. **Run `/spike-focus`** — asks which strategy and how long (default 5h)
2. **Commits, pushes, triggers GH Actions** with `--strategies` filter and pop_size=80
3. **Close your laptop** — results auto-commit when done
4. **Run `/spike-results`** later to see results

### History system

The optimizer remembers everything across runs:
- **`spike/hash-index.json`**: Compact dedup index mapping config hashes to fitness scores
- **`spike/leaderboard.json`**: All-time top 20 with strategy descriptions
- Each run seeds 20% of its population from historical winners
- Exact duplicates are skipped via config hashing (saves 30-40% compute on repeat runs)

### Primary optimization target: Accumulate more shares than B&H

The Montauk Engine optimizes for **share-count multiplier vs B&H** — at the end of the backtest, mark the strategy's equity to TECL share-equivalent and divide by buy-and-hold's terminal share count. A value > 1.0 means the strategy accumulated more units of TECL than passively holding would have.

The goal is share accumulation, not impressive equity curves. Sell high, buy back lower, end up with more shares. A year of holding through new highs without trading is a successful year — the engine does **not** punish low trade frequency.

Marker shape alignment (state agreement % vs `TECL-markers.csv`, plus median transition lag and missed-cycle count) is a first-class **diagnostic** at every tier and a strong tie-breaker in raw discovery ranking (per the 2026-04-13 revision it is a north star + soft/critical-warning diagnostic, not a hard gate).

### Key metrics

| Metric | Role |
|--------|------|
| **Share-count multiplier vs B&H** (`share_multiple`) | **Primary optimization target** — must be > 1.0 |
| **Marker shape alignment** | First-class diagnostic at every tier |
| vs B&H (dollars) | Sanity check on the share-count metric |
| CAGR | Return path quality |
| Max Drawdown | Risk |
| MAR Ratio (CAGR/MaxDD) | Risk-adjusted return |
| Avg Bars Held | High (50+) — trend system, not scalper |

> **Note (2026-04-13, updated 2026-04-15 by Phase 7):** `share_multiple` is the only Python attribute name. The deprecated `vs_bah_multiple` alias was retired in Phase 7 (engine consolidation). Older `spike/leaderboard.json` entries persisted under the JSON key `vs_bah` are still readable via `report.py::_share_mult`.

## Certification & Confidence Score (2026-04-21 framework)

Validation is two-layer. See `docs/validation-philosophy.md` for the full framework.

**Layer 1 — Correctness (hard-fail, binary):**
- engine integrity (bar-close signals, single position, no lookahead)
- golden regression pass (`tests/test_regression.py` matches `golden_trades_821.json` within ±0.001% PnL)
- shadow-comparator agreement (dev-only second opinion against `backtesting.py` / `vectorbt`)
- data-quality pre-check pass (all sources agree, manifest checksum, OHLC sane)
- artifact completeness (all five standardized JSON artifacts emitted)
- charter guardrails: TECL-only, long-only, single-position, ≤ 5 trades/year
- `share_multiple ≥ 1.0` (must beat B&H shares — charter mission)
- registry membership + charter-compatible family
- not degenerate (always-in or always-out across every 4-year window)

**Layer 2 — Confidence (weighted composite, [0, 1]):**
Weighted geometric mean of tier-applicable sub-scores. Each sub-score uses
smooth interpolation: hard-fail threshold → 0.0, soft-warn → 0.5, pass → 1.0.
Weights (T2 baseline) per `docs/validation-thresholds.md`:

| Sub-score | Weight | Tiers |
|---|:-:|---|
| walk_forward | 0.20 | all |
| marker_shape (state agreement) | 0.10 | all |
| **marker_timing (per-cycle, magnitude-weighted)** | **0.15** | all |
| named_windows (split from gate 4) | 0.10 | all |
| fragility | 0.15 | T1 (Gate 3) / T2 (Gate 5 Morris) |
| selection_bias | 0.10 | T2 only |
| cross_asset (demoted) | 0.05 | all |
| bootstrap | 0.05 | T2 only |
| regime_consistency | 0.05 | T2 only |
| trade_sufficiency | 0.05 | all |

Skipped gates drop out and remaining weights renormalize.

**Verdict rules:**
- FAIL: any Layer 1 violation OR composite < 0.40
- WARN: 0.40 ≤ composite < 0.70 (watchlist 60–69 displayed on leaderboard)
- PASS: composite ≥ 0.70 (admitted to leaderboard)

`backtest_certified` = all Layer 1 engine checks pass (regardless of Layer 2).
`promotion_ready` = PASS verdict (composite ≥ 0.70 AND Layer 1 all pass).

**Leaderboard ranking is confidence-first.** Fitness is only a tie-breaker.
The viz UI (`viz/montauk-viz.html`) collapsed the multi-column sort to a
single "Ranked by confidence" column.

## Reference Files

- **`docs/design-guide.md`**: **Read before authoring ANY new T0 hypothesis strategy.** Distills what has cleared the pipeline (and what has predictably failed), with a pre-flight design checklist. Prevents wasted cycles on strategies that fail for reasons we already understand.
- **`docs/validation-philosophy.md`**: Why we test, what we've built, and where we're going. Read this to understand the overfitting problem and how every component (fitness function, GA diversity, validation tests, slippage) connects to the research.
- **`docs/charter.md`**: The governing spec for all code work on this project. Read this before proposing any changes — it defines scope, coding rules, feature acceptance criteria, evaluation metrics, and response format.
- **`docs/Montauk 2.0/`**: Historical record of the Pine/TV excision project and its seven phases. Kept for provenance; not an active reference for current development.

## Doc-Sync Protocol

The `doc-sync.sh` hook fires after every Edit/Write to structural files (`scripts/`, `.github/workflows/`, `.claude/skills/spike*.md`). It detects whether the change looks structural (new functions, changed signatures, registry changes, gate changes, new imports) vs cosmetic (comments, param tweaks, variable renames).

**When you see `[DOC_SYNC_NEEDED]`:**

1. Finish your current task first — don't interrupt mid-work to update docs.
2. Read the `docs_to_review` list in the signal. Those are the files that may need updating.
3. For each listed doc, read it and check whether the change you just made invalidates anything.
4. If a section is now inaccurate, update it to reflect the new behavior. Keep edits minimal — only change what's actually wrong.
5. **Never touch `docs/charter.md` or `docs/charter-appendix.md`** — those are governance docs that only change by explicit decision, not by code drift.
6. If the change is minor enough that all docs are still accurate, skip silently.

Docs that may need updates and what to check:
- **`docs/pipeline.md`** — Does the pipeline diagram still match the code flow?
- **`docs/validation-thresholds.md`** — Do threshold values, gate names, or gate logic still match `scripts/validation/`?
- **`docs/project-status.md`** — Has an implementation gap been closed or a new one opened?
- **`docs/design-guide.md`** — Have strategy patterns or pre-flight checks changed?
- **`CLAUDE.md`** — Has the directory structure, data layout, or skill behavior changed?

---

## Spirit Protocol

This project uses spirit-guide (static brief) + spirit-memory (dynamic intent log). Treat both as binding project context.

### On session start
The `spirit-session-start.sh` hook loads `spirit-guide/README.md`, `spirit-summary/quick-reference.md`, `spirit-memory/INDEX.md`, and any `Important: true` north-star entries. Respect what you see.

### During conversation
The `spirit-prompt-submit.sh` hook pre-filters every user message with regex. When it detects project-voice (goals, sentiments, principles, decisions, glossary-worthy definitions), it emits a `[SPIRIT_CLASSIFY_NEEDED]` block into your context.

**When you see `[SPIRIT_CLASSIFY_NEEDED]`**, do the following silently — do not mention it in your reply:

1. Use the Task tool with `subagent_type: "general-purpose"` and `model: "haiku"`.
2. Pass the subagent this brief:

   > You are a spirit-memory classifier. Classify the statement below into exactly one of these files:
   > - `northstar.md` — goals, vision, aspirations, direction
   > - `sentiment.md` — concerns, reactions, feelings, frustrations
   > - `principles.md` — rules, "always / never", design laws
   > - `decisions.md` — choices made + rationale
   > - `glossary.md` — project-specific vocabulary definitions
   >
   > Also assign:
   > - Tags: ≥1 from controlled core (`#vision #ux #ui #brand #tech #business #team #process #content #data`) plus optional free-form tags
   > - `Important: true` if the statement is foundational ("the core idea", "this is load-bearing", "never change this"). Else `false`.
   > - Confidence score 0.0–1.0.
   >
   > Then:
   > - If confidence ≥ 0.70 → append to `<project_root>/spirit-guide/spirit-memory/<file>` using the entry format defined in that folder's README.md. Entry ID = today's date + next available suffix (a, b, c, …).
   > - If confidence < 0.70 → append to `<project_root>/spirit-guide/spirit-memory/_inbox.md` with the suggested file and confidence noted.
   > - After writing, update `<project_root>/spirit-guide/spirit-memory/INDEX.md` `[meta]` line to today's date. Full re-index is spirit-audit's job.
   >
   > Return nothing to the parent. Silent completion.

3. Continue your normal response to the user as if nothing happened.

### On demand
When the user asks about project health, contradictions, drift, or inbox triage, invoke the `spirit-audit` skill.

### Read order when in doubt
1. `spirit-guide/README.md`
2. `spirit-guide/spirit-memory/INDEX.md`
3. The specific spirit-memory file relevant to the task
4. `spirit-guide/spirit-summary/` for codified specs
5. `spirit-guide/spirit-src/` only for provenance questions

Never read `spirit-guide/_ARCHIVE/` unless explicitly asked.
