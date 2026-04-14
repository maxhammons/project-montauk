# Project Montauk

A Pine Script trading strategy system for TECL (Direxion Daily Technology Bull 3X Shares ETF) on TradingView. The project includes multiple strategy versions and companion indicators, all written in Pine Script v5/v6.

## Directory Structure

```
Project Montauk/
├── CLAUDE.md                  ← You are here
├── data/                      # All data files
│   ├── TECL.csv               # TECL OHLCV (synthetic 1998-2008 + real 2009+) + vix_close
│   ├── VIX.csv                # CBOE VIX OHLCV
│   ├── XLK.csv                # TECL underlying
│   ├── TQQQ.csv               # Synthetic 1999-2010 + real 2010+
│   ├── QQQ.csv                # TQQQ underlying
│   ├── SGOV.csv               # iShares 0-3 Month Treasury Bond ETF
│   ├── treasury-spread-10y2y.csv  # FRED T10Y2Y
│   ├── fed-funds-rate.csv     # FRED DFF
│   ├── tbill-3m.csv           # 3-Month Treasury Bill Rate
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
│   ├── research/              # Market research + academic papers
│   │   ├── synthesis.md       # Research synthesis
│   │   ├── roadmap.md         # Optimization roadmap
│   │   ├── checklist.md       # Research checklist
│   │   ├── sources.csv        # Research source citations
│   │   └── reports/           # Academic papers + deep research
│   └── pine-reference/        # Pine Script v6 documentation
├── scripts/                   # Python backtesting & optimization tools
│   ├── data.py                # TECL data fetcher (Yahoo Finance API + CSV merge)
│   ├── strategies.py          # Strategy library — all strategy functions + registry
│   ├── strategy_engine.py     # Backtest engine + indicator cache
│   ├── pine_generator.py      # Pine Script generation — per-strategy builders
│   ├── parity.py              # Python-vs-Pine parity checks (structural, signal replay, trade comparison)
│   ├── evolve.py              # Multi-strategy evolutionary optimizer (with history/dedup)
│   ├── spike_runner.py        # Main /spike entry point — wraps everything
│   ├── grid_search.py         # Exhaustive canonical grid search + validate
│   ├── report.py              # Auto-generates markdown reports from results
│   ├── canonical_params.py    # Strict canonical parameter sets for T0
│   ├── deploy.py              # Patch active Pine script with optimizer results
│   ├── requirements.txt       # Python deps: pandas, numpy, requests
│   └── validation/            # Tier-routed validation framework
│       ├── pipeline.py        # Main validation funnel
│       ├── sprint1.py         # Zero-backtest validation suite
│       ├── candidate.py       # Walk-forward validation
│       ├── cross_asset.py     # Cross-asset validation (TQQQ, QQQ)
│       ├── deflate.py         # Monte Carlo null distribution
│       ├── integrity.py       # Data integrity checks
│       ├── uncertainty.py     # Morris fragility + bootstrap
│       └── walk_forward.py    # Walk-forward test harness
├── spike/                     # All /spike optimization output
│   ├── runs/NNN/              # Per-session: report.md, results.json, log.txt, candidate.txt
│   ├── leaderboard.json       # All-time top 20 strategies
│   └── hash-index.json        # Compact dedup index: {hash: fitness}
├── src/                       # Pine Script production code
│   ├── strategy/
│   │   ├── active/            # Current production strategy
│   │   ├── archive/           # All previous versions (kept for reference)
│   │   └── debug/             # Debug builds with visual labels
│   └── indicator/
│       ├── active/            # Current production indicator
│       └── archive/           # Previous indicator versions
└── .claude/skills/            # Claude Code skills
    ├── spike.md               # /spike — interactive creative loop
    ├── spike-focus.md         # /spike-focus — GH Actions deep search
    ├── spike-results.md       # /spike-results — view results + generate Pine
    ├── about.md               # Architecture documentation
    └── sync.md                # Git sync utility
```

## Active Code (what's running in TradingView)

### Strategy: `src/strategy/active/Project Montauk 8.2.1.txt`

The current production strategy. Pine Script v6 overlay strategy for TECL.

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

**Key parameters are organized into input groups** for TradingView UI clarity: EMAs, Trend Filter, TEMA Filters, Sideways Filter, Sell Confirmation, Sell Cooldown, ATR Exit, Quick EMA Exit, Trailing Stop, TEMA Slope Exit.

### Indicator: `src/indicator/active/Montauk Composite Oscillator 1.3.txt`

Normalized composite momentum oscillator displayed in a separate pane. Returns a single value from -1 to +1 using `tanh()` normalization.

**Components (weighted)**:
| Component | Length | Weight | What it measures |
|-----------|--------|--------|-----------------|
| TEMA Slope | 300-bar | Heaviest | Primary trend direction |
| Quick EMA | 7-bar | Medium | Short-term momentum |
| MACD Histogram | 30/180/20 | Medium | Momentum divergence |
| DMI Ratio | 60-bar ADX | Medium | Directional strength |

**Visual output**: Color-coded bands (blue > green > yellow > orange > red) with optional smoothed MA lines for crossover signals.

**Component diagnostics panel** (v1.3): Top-right table showing each component's raw normalized value (-1 to +1) and weighted contribution to the composite. Color-coded to match oscillator bands. Disabled components appear greyed out. Toggled via "Show Component Panel" input.

## Strategy Version History

All versions target TECL. Early versions (1.x) were originally named "FMC" (Flash Momentum Capture) - same project, different name. The approach evolved from MACD-based entries (1.x-6.x) to EMA-crossover entries with layered exit filters (7.x+).

| Version | File | Pine | Key idea |
|---------|------|------|----------|
| 1.0 | `archive/Project Montauk 1.0 (FMC).txt` | v5 | MACD crossover + ATR stop + 200 SMA trend filter + slope-based no-trade zone |
| 1.1 | `archive/Project Montauk 1.1 (FMC).txt` | v5 | Dynamic MACD buffer (% of price), cooldown in bars instead of days |
| 1.4 | `archive/Project Montauk 1.4 (FMC).txt` | v5 | Added 21-EMA exit filter, two-stage "ready" entry (MACD first, then SMA cross) |
| 6.4b | `archive/Project Montauk 6.4 b.txt` | v5 | Simple EMA approach: 2000-bar EMA trend + 200-bar EMA re-entry with fixed buffer exit |
| 6.8c | `archive/Project Montauk 6.8 c.txt` | v5 | Pure MACD zero-cross with dynamic threshold buffer (20% of amplitude) |
| 7-6 | `archive/Project Montauk 7-6.txt` | v6 | Multi-exit system: EMA cross + drop-sell (19% in 3 bars) + ATR + quick EMA slope |
| 7-7 | `archive/Project Montauk 7-7.txt` | v6 | Removed drop-sell filter from 7-6 for cleaner logic |
| 7.8 | `archive/Project Montauk 7.8.txt` | v6 | Production version with exit-reason label tracking on chart |
| 7.9 | `archive/Project Montauk 7.9.txt` | v6 | Added TEMA filters and Donchian-based sideways market detection |
| 8.1 | `archive/Project Montauk 8.1.txt` | v6 | Organized input groups, quick exit changed from slope to % delta |
| 8.2 | `archive/Project Montauk 8.2.txt` | v6 | Added trailing stop and TEMA slope exit (both default OFF) |
| **8.2.1** | **`active/Project Montauk 8.2.1.txt`** | **v6** | **Current. Fixed EMA cross exit to use `barssince(crossunder) < confirmBars` — fires within window, not only on exact cross bar** |

### Debug Builds

These are strategy versions with extra visual debugging for development:

| File | Based on | Debug feature |
|------|----------|---------------|
| `debug/Project Montauk 7.6 - Debug.txt` | 7-6 | Detailed entry/exit comments in order log |
| `debug/Project Montauk 7.8 - Debug.txt` | 7.8 | `label.new()` on chart showing which exit condition fired |

## Architecture Notes

- **All strategies are overlay strategies** (plotted on the price chart, not in a separate pane)
- **The indicator runs in a separate pane** (oscillator output, not overlaid on price)
- **Position sizing**: 8.2.1 uses 100% of equity per trade (single position, long only)
- **No shorting**: All strategies are long-only
- **Cooldown logic**: After every exit, a configurable cooldown (bars) prevents immediate re-entry
- **Price smoothing**: Montauk 6.x versions use OHLC/4 smoothed price; 7.x+ use standard close

## Working with This Code

- **To edit the active strategy**: Modify `src/strategy/active/Project Montauk 8.2.1.txt`, then paste into TradingView Pine Editor
- **To edit the active indicator**: Modify `src/indicator/active/Montauk Composite Oscillator 1.3.txt`, then paste into TradingView Pine Editor
- **When creating a new version**: Copy the active file to the appropriate archive folder first, then modify the active copy
- **Strategy and indicator are separate scripts in TradingView** - the strategy handles entries/exits, the indicator provides visual confirmation in a separate chart pane

### Project Organization

Keep the folder and file structure clean and easy to navigate. The owner needs to be able to jump in and quickly understand what's going on at a glance.

- **Use clear, descriptive file names** — version numbers, dates, and purpose should be obvious from the name
- **Put files in the right place** — follow the directory structure above; don't dump things in the root or create ad-hoc folders
- **Archive, don't delete** — old versions go to `archive/`, not the trash
- **Clean up after yourself** — remove temp files, don't leave orphaned outputs or half-finished work lying around
- **Keep output organized sequentially** — spike runs go in `spike/runs/NNN/`, not loose in the project root
- **When in doubt, match the existing pattern** — look at how similar files are already named and placed
- **Keep `docs/pipeline.md` current** — when you change the fitness function, optimizer logic, validation suite, data flow, GH Actions workflow, or any process/pipeline behavior, update the pipeline diagram to match. This is the visual source of truth for how the system works.

## Optimization Tools — Spike + the Montauk Engine

**Spike** is the skill (the entrypoint / command surface). Spike launches and runs the **Montauk Engine** — the optimizer + tier-routed validator + Pine generator pipeline. This is a semantic split, not a code rename: files and commands keep their existing names.

Two complementary skills for strategy development:

### `/spike` — Interactive creative loop (local)

Iterative optimization where Claude sees per-cycle diagnostics, revises strategy *code* between optimizer chunks, and collaborates with the Montauk Engine to find strategies that match the marker shape and accumulate more shares than buy-and-hold.

1. **Run `/spike`** — asks how long (default 2h), runs locally
2. **Claude sees the regime map** — every bull/bear cycle with dates, magnitude, duration
3. **Claude sees cycle diagnostics** — where each strategy's trades fall in each cycle, what exits fire during bulls
4. **Claude writes strategies** informed by actual cycle data
5. **Optimizer runs 20-min chunks** — Claude reviews results and revises code between chunks
6. **Cross-asset + sprint1 validation** on the winner at the end
7. All output goes to `spike/runs/NNN/` — **the active strategy is never modified**

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

Marker shape alignment (state agreement % vs `TECL-markers.csv`, plus median transition lag and missed-cycle count) is a first-class **validation gate** at every tier and a strong tie-breaker in raw discovery ranking.

### Key metrics

| Metric | Role |
|--------|------|
| **Share-count multiplier vs B&H** | **Primary optimization target** — must be > 1.0 |
| **Marker shape alignment** | First-class validation gate at every tier |
| vs B&H (dollars) | Sanity check on the share-count metric |
| CAGR | Return path quality |
| Max Drawdown | Risk |
| MAR Ratio (CAGR/MaxDD) | Risk-adjusted return |
| Avg Bars Held | High (50+) — trend system, not scalper |

> **Note (2026-04-13):** The fitness formula in scripts still uses dollar `vs_bah` and a `trade_scale` factor. The charter now defines share-count as the primary metric and removes the trade-frequency punishment. The scripts have not yet been updated to match — see `docs/project-status.md` for the full implementation gap.

## Reference Files

- **`docs/design-guide.md`**: **Read before authoring ANY new T0 hypothesis strategy.** Distills what has cleared the pipeline (and what has predictably failed), with a pre-flight design checklist. Prevents wasted cycles on strategies that fail for reasons we already understand.
- **`docs/validation-philosophy.md`**: Why we test, what we've built, and where we're going. Read this to understand the overfitting problem and how every component (fitness function, GA diversity, validation tests, slippage) connects to the research.
- **`docs/charter.md`**: The governing spec for all code work on this project. Read this before proposing any changes — it defines scope, coding rules, feature acceptance criteria, evaluation metrics, and response format.
- **`docs/pine-reference/`**: Structured Pine Script v6 reference. Use the modular files for quick lookups, fall back to the all-in-one for anything not found there:
  - `docs/pine-reference/reference/ta.md` — TA functions (`ta.ema`, `ta.atr`, `ta.crossover`, etc.)
  - `docs/pine-reference/reference/variables.md` — Built-in variables (`close`, `bar_index`, `barstate.*`, etc.)
  - `concepts/common_errors.md`, `pine_script_execution_model.md` — execution and error docs
  - `Pine Script language reference manual` — 393KB all-in-one covering all 884 functions including all `strategy.*` functions. Use Grep or offset reads to search it.
  - Do not guess at Pine v6 API details — look them up.

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
