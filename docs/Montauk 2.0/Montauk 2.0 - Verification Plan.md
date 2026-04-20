# Montauk 2.0 — Verification Plan

*Run this after execution is "done" to confirm every phase actually landed correctly. Companion to [Montauk 2.0 - Master Plan.md](./Montauk%202.0%20-%20Master%20Plan.md). Read [spirit-guide.md](./spirit-guide.md) first for intent.*

---

## How to use this document

This is an audit, not execution work. You (or a model) walk through each check, record PASS / WARN / FAIL, and produce a report at the end. Do NOT fix things in this pass — log everything first, then triage. Fix-it work is a separate pass.

**Pass verdicts:**
- **PASS** — check satisfied, evidence cited
- **WARN** — partially satisfied / edge case / needs a human eye
- **FAIL** — check not satisfied; the item was skipped, stubbed, or wired incorrectly

**Be skeptical.** Common failure modes (see §9 at the end) include tests that pass vacuously, renames that miss call sites, artifacts that emit with the wrong schema, and "certification" flags hardcoded to `True`. Look for things that exist but don't do what they claim.

**Report format** (per check): `[PASS|WARN|FAIL] <check id> — <evidence / file:line / command output snippet> — <note if WARN/FAIL>`. Produce the full report at the end as `docs/Montauk 2.0/verification-report.md`.

---

## §1. Meta-audit (structural sanity)

Run these first. If any fail, downstream checks will cascade.

| # | Check | Command / File | PASS criteria |
|---|-------|----------------|---------------|
| M1 | Pine files gone | `ls scripts/pine_generator.py scripts/parity.py scripts/deploy.py` | All three: "No such file" |
| M2 | `src/` gone | `ls src/` | "No such file or directory" |
| M3 | `docs/pine-reference/` gone | `ls docs/pine-reference/` | "No such file or directory" |
| M4 | `tests/` exists with expected files | `ls tests/` | At minimum: `test_indicators.py`, `test_regression.py`, `golden_trades_821.json`, `test_shadow_comparator.py`, `test_backtest_engine.py` |
| M5 | `viz/` exists with expected files | `ls viz/` | At minimum: `build_viz.py`, `templates/`, `lightweight-charts.js`, `montauk-viz.html` |
| M6 | Data manifest exists | `ls data/manifest.json` | File present, non-empty |
| M7 | Master grep: no Pine references in active code | `grep -ri "pine_generator\|from parity\|from deploy\|pine_eligible" scripts/ viz/ tests/` | Zero hits |
| M8 | Master grep: no TradingView in active paths | `grep -ri "tradingview" scripts/ viz/src/ tests/ docs/charter.md docs/pipeline.md docs/project-status.md CLAUDE.md` | Zero hits except the phrase "TradingView Lightweight Charts" referring to the OSS library — that's allowed |
| M9 | Historical record preserved | `ls docs/Montauk\ 2.0/` | Contains `spirit-guide.md`, master plan, this verification plan, and `pine-excision-baseline.md` |

---

## §2. Phase 0 audit — Snapshot & Baseline

| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P0.1 | Baseline doc exists | `ls docs/Montauk\ 2.0/pine-excision-baseline.md` | Present |
| P0.2 | Baseline contains parity batch output | Read the file | Section with structural parity report across all strategy builders |
| P0.3 | Baseline contains 8.2.1 param cross-reference | Read the file | Table/section comparing Pine 8.2.1 defaults vs Python `StrategyParams`, with any drift documented |
| P0.4 | Baseline contains top-5 fitness anchor | Read the file | Five entries with strategy name, params hash/summary, and fitness score at snapshot time |
| P0.5 | Divergence-estimation snippet captured | grep baseline doc for commission/slippage divergence math | Formula or code block present |

**Regression use**: Phase 6 must reproduce these fitness scores. If they don't match, suspect silent engine drift from Phase 1c slippage changes.

---

## §3. Phase 1 audit — Engine Hardening (LOAD-BEARING)

This is the most dangerous phase to skimp on. A stubbed test here means every downstream guarantee is fake.

### 3a. Indicator tests
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.1 | `tests/test_indicators.py` exists | Read file | Present |
| P1.2 | EMA test uses hand-calculated values | Read test | Expected values are **concrete floats**, not dynamically computed from the same implementation. If the expected value is produced by calling `ema(...)` and comparing to itself, the test is vacuous — FAIL. |
| P1.3 | TEMA test verifies `3·EMA1 − 3·EMA2 + EMA3` | Read test | Formula verification present with known-good numbers |
| P1.4 | ATR test uses Wilder's RMA on known OHLC | Read test | Explicit OHLC input, expected ATR sequence as concrete floats |
| P1.5 | ADX test | Read test | Input + expected output present, not self-referential |
| P1.6 | NaN-prefix chained-TEMA test | Read test | Test case specifically for the chained-EMA NaN handling edge case |
| P1.7 | Both engines' EMA produce bit-identical output | Read test + run it | Test imports both `strategy_engine.ema` and `backtest_engine.ema` (if both exist), asserts equality on same input |
| P1.8 | Tests actually run and pass | `pytest tests/test_indicators.py -v` | All green, no SKIP |

### 3b. Golden reference trades
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.9 | `tests/golden_trades_821.json` exists and has content | `wc -l tests/golden_trades_821.json` | Non-empty, contains trade entries (not `[]`) |
| P1.10 | Schema has required fields | Read file | Each trade has: entry_date, exit_date, entry_price, exit_price, exit_reason, pnl_pct |
| P1.11 | `tests/test_regression.py` asserts match | Read test | Loads golden_trades, runs backtest with 8.2.1 defaults on `data/TECL.csv`, asserts each trade matches within ±0.001% PnL tolerance |
| P1.12 | Regression test passes | `pytest tests/test_regression.py -v` | Green |
| P1.13 | Golden trades regenerated AFTER slippage change | Check: was `generate_golden_trades.py` run after Phase 1c slippage unification? | Timestamp on `golden_trades_821.json` should be after the `slippage_pct` commit. If golden trades predate the slippage change, they encode the old (wrong) behavior — FAIL. |

### 3c. Slippage unification
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.14 | `StrategyParams` has `slippage_pct` | grep `backtest_engine.py` for `slippage_pct` | Field defined in dataclass with default 0.05 |
| P1.15 | Slippage applied on entry AND exit | Read `run_backtest()` fill logic | Entry price shifted by `+slippage`, exit price shifted by `−slippage` (or equivalent) |
| P1.16 | Old `* 2 × equity` commission math removed | grep `backtest_engine.py` for `* 2` near commission logic | Gone, or replaced with standard per-fill percentage |
| P1.17 | Both engines produce identical trades | Run both on 8.2.1 defaults, diff trade lists | Zero trade differences |

### 3d. `vs_bah` → `share_multiple` rename
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.18 | `BacktestResult.share_multiple` exists | grep `strategy_engine.py` for `share_multiple` | Field present |
| P1.19 | `vs_bah_multiple` kept as deprecated alias | grep for `vs_bah_multiple` | Still readable (property or alias), marked deprecated until Phase 7 |
| P1.20 | Leaderboard writes `share_multiple` | Read new entries in `spike/leaderboard.json` | Key `share_multiple` appears in freshly-written entries (old entries may still have `vs_bah`) |
| P1.21 | Fitness formula in `evolve.py` uses `share_multiple` | grep `evolve.py` for both names | Primary key is `share_multiple`; `vs_bah` only via alias if at all |
| P1.22 | Report output updated | grep `report.py` | No raw `vs_bah` references outside the alias pass-through |
| P1.23 | All call sites found | `grep -r "vs_bah" scripts/ tests/ viz/ --include="*.py"` | Only in alias definition; every other reference is `share_multiple`. Common miss: report markdown templates, CLI flag names, docstrings. |

### 3e. Shadow comparator
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.24 | `tests/test_shadow_comparator.py` exists | Read file | Present |
| P1.25 | Actually invokes an OSS engine | Read test | Imports `backtesting.py`, `vectorbt`, or equivalent. NOT a mock. If it just hardcodes expected PnL and calls our engine, it's not a shadow comparator — FAIL. |
| P1.26 | Tolerance is tight enough to catch real bugs | Read test | Per-trade PnL tolerance ≤ 0.5%. If tolerance is >5%, it will pass for any strategy — WARN. |
| P1.27 | Bridging code handles StrategyParams → shadow engine API | Read test | Explicit parameter mapping, not a blind `**kwargs` passthrough |
| P1.28 | Test passes on 8.2.1 defaults | `pytest tests/test_shadow_comparator.py -v` | Green |

### 3f. EMA-cross exit test
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P1.29 | Constructed-scenario test exists | Read `tests/test_backtest_engine.py` | Test with explicit EMA sequence that crosses under, verifies exit fires within confirmation window |

---

## §4. Phase 2 audit — Pine/TV Excision

| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P2.1 | `integrity.py` import cleaned | grep `scripts/validation/integrity.py` for `pine_generator`, `REQUIRED_PINE_SNIPPETS` | Zero hits |
| P2.2 | `integrity.py` slippage guard preserved | Read file | Zero-slippage check still present (it's non-Pine) |
| P2.3 | `pipeline.py` parity import removed | grep `scripts/validation/pipeline.py` for `from parity` | Zero hits |
| P2.4 | Gate 7 renamed to `backtest_certified` | Read `_gate7_synthesis` | Field is `backtest_certified`, not `pine_eligible` |
| P2.5 | Certification combines required inputs | Read Gate 7 logic | `backtest_certified = (engine_integrity AND golden_regression_pass AND shadow_agreement AND data_quality_pass AND artifact_completeness)`. If it's just hardcoded `True` or only one of these — FAIL. This is a common cargo-cult failure. |
| P2.6 | `promotion_ready` flag replaces promotion logic | grep for `promotion_ready` | Used in place of `promotion_eligible` or paired with it |
| P2.7 | `spike_runner.py` Pine imports removed | grep `scripts/spike_runner.py` for Pine | Zero hits |
| P2.8 | Five standardized run artifacts emit | Check most recent `spike/runs/NNN/` dir | Contains: `trade_ledger.json`, `signal_series.json`, `equity_curve.json`, `validation_summary.json`, `dashboard_data.json` |
| P2.9 | Artifact schemas are populated, not stubs | Read each JSON | Non-trivial content. `trade_ledger.json` has trade records; `equity_curve.json` has full curve; `validation_summary.json` has per-gate details |
| P2.10 | `report.py` `pine_eligible` display removed | grep for `pine_eligible` | Only in Montauk 2.0 historical doc |
| P2.11 | Claude skills cleaned | Read `.claude/skills/spike.md`, `spike-results.md`, `about.md` | No Pine generator references, no "Pine candidate" in outputs |
| P2.12 | End-to-end smoke test | `python scripts/spike_runner.py --hours 0.01 --quick` | Runs clean, no import errors, emits artifacts |
| P2.13 | Old Pine artifacts purged from `spike/runs/` | `find spike/runs -name "*.pine" -o -name "candidate_strategy.txt" -o -name "patched_strategy.txt"` | Zero hits (historical runs can keep them; new runs should not emit them) |

---

## §5. Phase 3 audit — Data Triple-Check

### 5a. Cross-check
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P3.1 | `scripts/data_crosscheck.py` exists and runs | `python scripts/data_crosscheck.py` | Exits 0, produces per-ticker table |
| P3.2 | Divergence <0.01% on real data | Read cross-check output | Max close divergence on post-IPO data for TECL, TQQQ, QQQ, XLK, VIX is below threshold; any day >0.5% is flagged explicitly |
| P3.3 | Handles Stooq fetch failures | Kill network / set bad URL, rerun | Fails gracefully with clear error, not silent pass |

### 5b. Provenance columns
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P3.4 | TECL.csv has provenance columns | `head -1 data/TECL.csv` | Columns include: `is_synthetic`, `source_symbol`, `source_kind`, `synthetic_model_version`, `stitch_segment` |
| P3.5 | TQQQ.csv has provenance columns | `head -1 data/TQQQ.csv` | Same columns present |
| P3.6 | Boundary dates correct | Spot-check rows around 2008-12-17 (TECL) and 2010-02-11 (TQQQ) | `is_synthetic` flips at the IPO date; `source_symbol` changes from XLK→TECL (or QQQ→TQQQ) |
| P3.7 | `BacktestResult` logs synthetic vs real trade counts | Read engine return value | Field present in result object |

### 5c. Manifest
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P3.8 | `data/manifest.json` exists and has all tickers | Read file | Entries for TECL, TQQQ, QQQ, XLK, VIX, SGOV, and FRED series |
| P3.9 | Checksums match current CSVs | `python scripts/data_manifest.py --verify` (or equivalent) | PASS — every checksum matches |
| P3.10 | Build timestamps present and recent | Read manifest | `built_utc` fields populated with ISO timestamps |
| P3.11 | Source URLs recorded | Read manifest | Non-empty URL / "Yahoo Finance API" / "FRED DFF" per entry |

### 5d. Deterministic rebuild
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P3.12 | `scripts/data_rebuild_synthetic.py` exists | Read file | Present, runnable |
| P3.13 | `--verify` mode produces bit-identical output | `python scripts/data_rebuild_synthetic.py --verify` | Exits 0, reports bit-identical match for both TECL and TQQQ synthetic sections |
| P3.14 | Runs are deterministic | Run twice, diff outputs | Diff is empty (same bytes both runs) |
| P3.15 | Correct expense ratios | Read script | TECL: 0.0095/252, TQQQ: 0.0075/252, cited to ProShares prospectus |

### 5e. Data quality runner
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P3.16 | `scripts/data_quality.py` exists, runs end-to-end | `python scripts/data_quality.py` | Exits 0, produces PASS/WARN/FAIL table |
| P3.17 | All tests PASS on current data | Read output | Every row PASS |
| P3.18 | Tests cover every item from master plan table | Compare output to master plan §3f table | Row count matches expected set (row-by-row residual, seam, manifest checksum, duplicates, weekends, gaps, OHLC inversion, NaN/neg/zero, split detection, adjusted close, monotonicity, volume sanity, Stooq divergence) |
| P3.19 | Wired into validation pipeline | grep `scripts/validation/pipeline.py` for `data_quality` invocation | Called as pre-check before gate 0, and its result feeds into `backtest_certified` |

---

## §6. Phase 4 audit — HTML Visualization

Most of this requires opening the viewer in a browser. Automate what you can with the dev-browser skill; manual-eyeball the rest.

### 6a. Build pipeline
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P4.1 | `viz/build_viz.py` exists and runs | `python viz/build_viz.py` | Exits 0, prints size / strategy count |
| P4.2 | Lightweight Charts vendored, not CDN | Read `viz/templates/shell.html` | `<script src="lightweight-charts.js">` (local), NO `unpkg.com` / `cdn.jsdelivr.net` references |
| P4.3 | `viz/montauk-viz.html` generated | `ls -la viz/montauk-viz.html` | Present, recent mtime |
| P4.4 | Bundle embedded, not fetched | grep generated HTML for `window.__MONTAUK_DATA__` | Data is embedded inline in the HTML, no runtime `fetch()` calls for core data |
| P4.5 | Dashboard reads pre-computed JSON (no viz-time backtest re-run) | Read `build_viz.py` | Reads `spike/runs/NNN/dashboard_data.json`; does NOT import `strategy_engine` to run backtests at build time. **Common failure**: build_viz falls back to re-running because `dashboard_data.json` isn't there — see P2.8. |

### 6b. Visual MVP checks (open `viz/montauk-viz.html` in a browser)
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P4.6 | Page loads without console errors | DevTools console | Zero errors |
| P4.7 | Candlestick chart renders | Visual | TECL OHLC visible, date axis populated from 1998 to present |
| P4.8 | Synthetic period shaded/tinted | Visual | Background tint clearly visible on pre-2008-12-17 bars |
| P4.9 | Synthetic boundary indicator | Visual | Dashed vertical line at 2008-12-17 with "Real data starts" label |
| P4.10 | Sidebar lists all 20 strategies | Visual | Count matches `spike/leaderboard.json` length |
| P4.11 | Click-to-swap works | Click 3 different strategies | Chart markers, metrics panel, equity curve all update |
| P4.12 | Trade markers render | Visual | Up/down triangles on selected strategy's entry/exit bars |
| P4.13 | Equity curve pane visible | Visual | Strategy vs B&H, two distinct lines |
| P4.14 | **Drawdown underwater pane visible** | Visual | Separate pane below equity, red area descending below zero |
| P4.15 | Metrics panel populated | Visual | All primary metrics: share_multiple, CAGR, max_DD, MAR, trades, trades/yr, win_rate, regime_score, marker_alignment |
| P4.16 | `backtest_certified` / `promotion_ready` badges shown | Visual | Clear ✓ / ✗ indicators per strategy in sidebar or metrics panel |
| P4.17 | Recent-period scorecards visible (1Y / 3Y / 5Y) | Visual | Three cards showing share_multiple + max_DD + trades for each window |
| P4.18 | Provenance badge shows | Visual | "✓ manifest verified" chip or equivalent |
| P4.19 | North-star toggle works | Click toggle | Hand-marked cycle markers appear/disappear with distinguishable shape (circles) |
| P4.20 | Time range selector works | Click 1Y, 5Y, ALL | View zooms correctly |
| P4.21 | Crosshair + tooltip | Hover chart | Date, OHLC, volume show; hovering near a trade marker shows trade details |
| P4.22 | Offline test | Disable network, reload | Page still loads (library is vendored, data is embedded) |

### 6c. Pipeline integration
| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P4.23 | `spike_runner.py` triggers viz build at end | Read end of `main()` | Optional non-blocking call to `viz/build_viz.py` present |

---

## §7. Phase 5 audit — Docs Cleanup

| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P5.1 | `CLAUDE.md` intro rewritten | Read first 5 lines | References Python engine + manual execution + Lightweight Charts viewer; NO "Pine Script trading strategy system for TECL on TradingView" |
| P5.2 | `CLAUDE.md` directory structure updated | Read directory tree section | Contains `viz/`, `tests/`, new `data_*.py` scripts, `data/manifest.json`; does NOT contain `src/`, `pine_generator.py`, `parity.py`, `deploy.py`, `pine-reference/` |
| P5.3 | `docs/charter.md` execution surface rewritten | grep for "Pine Script" / "TradingView" | Only historical references (e.g., in a "history" or "migration" section), not in current spec |
| P5.4 | `docs/project-status.md` Pine sections marked historical | Read file | Previous Pine-related sections tagged as historical / resolved |
| P5.5 | `docs/pipeline.md` diagram updated | Read diagram | No Pine generation step; includes `viz/` build and five new run artifacts |
| P5.6 | Global grep confirms no stray references | `grep -ri "pine\|tradingview" docs/ CLAUDE.md .claude/skills/` | Hits only in `docs/Montauk 2.0/` (historical record) and any allowed "TradingView Lightweight Charts" OSS library references |
| P5.7 | Primary metric name in docs | grep docs/ for `vs_bah` | Only in historical/alias context; primary references use `share_multiple` |

---

## §8. Phase 6 audit — Final Validation (end-to-end)

| # | Check | How | PASS criteria |
|---|-------|-----|---------------|
| P6.1 | Full pytest suite green | `pytest tests/ -v` | All tests pass, zero SKIP (skips are OK only if documented) |
| P6.2 | Data rebuild verify | `python scripts/data_rebuild_synthetic.py --verify` | Bit-identical match |
| P6.3 | Data quality all PASS | `python scripts/data_quality.py` | Every row PASS |
| P6.4 | Stooq cross-check OK | `python scripts/data_crosscheck.py` | <0.01% max divergence on real data |
| P6.5 | Live spike run | `python scripts/spike_runner.py --hours 0.5 --quick` | Exits clean, leaderboard updates, five artifacts emit |
| P6.6 | Phase 0 baseline reproduces | Compare current top-5 fitness against `pine-excision-baseline.md` | Within floating-point tolerance. **WARN (not FAIL)** if ±5% drift — engine cache invalidation is expected; investigate if >5% drift. |
| P6.7 | Viz loads | `python viz/build_viz.py && open viz/montauk-viz.html` | Renders with all §6b checks green |
| P6.8 | No Pine refs in active paths | `grep -r "pine_generator\|from parity\|from deploy\|pine_eligible" scripts/ docs/charter.md docs/pipeline.md docs/project-status.md CLAUDE.md viz/ tests/` | Zero hits |
| P6.9 | Directory structure matches master plan §1 | `tree -L 2` (or manual) | Matches the target layout |

---

## §9. Common failure modes — look for these specifically

These are the "it looks right but isn't" failures. Each deserves a deliberate check even if everything above passed.

1. **Vacuous tests.** A test that computes expected value from the same function it's testing. Look for patterns like `assert ema(x, n) == ema(x, n)` or fixtures generated at test-time by the code under test. Every expected value in an indicator test should be a **concrete literal** produced by a trusted external source (hand calculation, TradingView export, Excel reference, or a well-known library like `pandas_ta`).
2. **Stale golden trades.** `golden_trades_821.json` was generated once and never refreshed after Phase 1c changed slippage. File mtime test: golden file should post-date the slippage commit. If it doesn't, the regression test is locking in the wrong behavior.
3. **Missed call sites in `vs_bah` → `share_multiple` rename.** Common misses: CLI arg names, markdown report templates, docstrings referenced in user-facing messages, cached leaderboard entries, string literals in logging. Run `grep -r "vs_bah" scripts/ tests/ viz/ docs/` and audit every hit.
4. **`backtest_certified` hardcoded to `True`.** The certification logic was supposed to combine five inputs. Check that each input is actually queried and a `False` from any of them propagates to the final flag.
5. **Shadow comparator with runaway tolerance.** Test "passes" because tolerance was set to ±10% or the comparator isn't actually invoked. Read the test; if it doesn't raise on a deliberately-wrong mock, it's not comparing anything real.
6. **Artifact schemas that exist but are empty.** `spike/runs/NNN/trade_ledger.json` is present but contains `[]`, or `validation_summary.json` has only top-level verdict and no per-gate detail. Check every artifact's contents, not just existence.
7. **Viz that secretly re-runs backtests at build time.** `build_viz.py` was supposed to read `dashboard_data.json`. Check for `import strategy_engine` or `import backtest_engine` in `build_viz.py` — if it's there, the build path fell back to runtime simulation, which defeats the performance and reproducibility goals.
8. **Data manifest built once, never refreshed.** Checksums are in the manifest but don't match the current CSVs (because data was refreshed after manifest was built, or vice versa). Run the verify step.
9. **`is_synthetic` column added but not used.** The provenance data is in the CSVs but nothing in the viz shades the synthetic period (visual check §6b P4.8) and nothing in `BacktestResult` counts synthetic trades (§5b P3.7).
10. **Lightweight Charts loaded from CDN despite "vendored" claim.** Read `viz/templates/shell.html` and `viz/montauk-viz.html`; if you see `unpkg.com` or `cdn.jsdelivr.net`, it's still network-dependent. This breaks the offline-viewing promise.
11. **Recent scorecards compute on wrong window.** "1Y" is supposed to mean the last 252 trading bars, not the last calendar year. Spot-check the math on one strategy.
12. **Tests that PASS because they were SKIP'd.** `pytest` output shows `5 passed, 3 skipped` and skips aren't flagged as failures. Run with `pytest --strict-markers` or audit the output for skip messages.
13. **Docs updated for appearance, not substance.** The charter.md intro changed but a section three pages down still describes the Pine workflow in present tense. Read full files, not just the first paragraph.
14. **Skills still reference Pine.** `.claude/skills/spike-results.md` may still have a "Generate Pine Script" section even if the skill list in `about.md` was cleaned.
15. **No error path for missing data.** `viz/build_viz.py` may silently skip strategies whose `dashboard_data.json` is missing, producing a viewer with fewer than 20 strategies and no warning. Count strategies in the rendered page vs the leaderboard.

---

## §10. Report format

Produce `docs/Montauk 2.0/verification-report.md` with:

```markdown
# Montauk 2.0 — Verification Report
*Run date: YYYY-MM-DD*
*Auditor: <model / human>*

## Summary
- Total checks: <n>
- PASS: <n>
- WARN: <n>
- FAIL: <n>
- Critical failures (load-bearing): <list or "none">

## Detailed results
[One section per phase (§2–§8), each row: `[PASS|WARN|FAIL] <check-id> — <evidence>`]

## Common failure modes audit (§9)
[One line per item 1–15 with PASS / WARN / FAIL]

## Recommended remediation
[Only FAIL items, prioritized: load-bearing (Phase 1, data integrity, certification flag) first]

## Residual risks
[WARN items worth flagging for the user even if not blocking]
```

**Triage rule**: Any FAIL in Phase 1 or in §9 items 1, 2, 4, or 6 blocks sign-off. Fix those before trusting any result from the pipeline. WARN items can go on a follow-up list. PASS-only phases can be marked "verified" in `project-status.md`.
