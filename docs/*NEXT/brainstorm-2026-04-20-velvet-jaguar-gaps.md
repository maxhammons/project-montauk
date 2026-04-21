# Brainstorm 2026-04-20 — Surpassing Velvet Jaguar

## Context

**Velvet Jaguar** (`gc_n8`) is the current ceiling: fast=120, slow=150, slope_window=3, entry_bars=2, cooldown=2, MACD>0 entry gate. Exits on death cross or VIX panic. Share mult 116x TECL, CAGR 33.77%, 20 trades in 33yr.

Diagnostics say VJ is **lagging its own marker targets**:
- `transition_timing_score = 0.110` (very low — most transitions are >30 bars off)
- `missed_marker_cycles = 10 of 14`
- QQQ same-param share_multiple = 0.41 (underperforms B&H off-asset)

Chart inspection confirms six specific failure modes:

| # | Failure | Mechanism |
|---|---|---|
| 1 | Late COVID crash (Feb-Mar 2020) | 120/150 EMA death cross needs ~30-40 bars; crash was ~25 |
| 2 | Late re-entry post-COVID | EMAs don't cross back until well into the rebound |
| 3 | Late 2022 bear | Slow EMAs — death cross fired months after peak |
| 4 | No signal on Liberation Day (Apr 2025) | ~2-wk tariff shock too short to move 120-EMA |
| 5 | False start Aug 2022 | Bear-market rally looked like a narrow-then-cross |
| 6 | Bad trades Oct 2011 / Dec 2012 | Shallow pullbacks triggered false exits in chop |

**Core tension**: VJ's slow EMAs are both *why* it compounds 116x AND *why* it misses shocks. Every strategy below either (a) stacks a faster overlay on top of VJ, or (b) tests a clean-slate signal family that engages regimes differently.

## Design principles for this batch

From user brainstorm answers (2026-04-20):

1. **Goal**: better regime timing should, in theory, accumulate more shares. Not strictly opposed to share count — just requires faster, correct transitions.
2. **Shock detection**: VIX spike + **confirmed by price dip** (not VIX alone), 2-5 bar window. Faster if possible without whipsaw.
3. **Fast re-entry after shock**: watch for V-recovery, but guard against re-triggering on the same downdraft.
4. **Chop protection**: some volatility / realized-vol regime filter. ADX-only strategies underperformed historically (`always_in_trend` bottom of old leaderboard) — don't bet on ADX as sole filter, but ADX as one component of a composite might still have value.

All params must come from `scripts/engine/canonical_params.py`:
- `MA_PERIODS = {7, 9, 14, 20, 21, 30, 50, 100, 150, 200, 300}`
- `RSI_PERIODS = {7, 14, 21}`
- `ATR_PERIODS = {7, 14, 20, 40}` / `ATR_MULTIPLIERS = {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`
- `LOOKBACK_PERIODS = {5, 10, 20, 50, 100, 150, 200}`
- `SLOPE_CONFIRM_BARS = {1, 2, 3, 5}` / `COOLDOWN_BARS = {0, 1, 2, 3, 5, 10}`
- `PCT_THRESHOLDS = {5.0, 8.0, 10.0, 15.0, 20.0, 25.0}`
- `MACD_TRIPLES = {(12,26,9), (8,17,9)}`

---

## Bucket A — Overlays on Velvet Jaguar

These keep VJ's base signal (`_gc_strict_signals` + MACD>0) and add one surgical overlay. Hypothesis: if VJ is fundamentally sound and just misses shock events, we can bolt on a shock circuit without breaking its 116x engine.

> **All three deferred A candidates (A5/A7/A9) were run in the Final Batch (2026-04-20).** See Final Batch section below for verdicts. Summary: A7 `gc_vjbb` produced the highest raw TECL lift of any overlay across all rounds (126.80x at bb_len=50/bb_width_look=50/bb_pct=40) with *better* marker alignment than VJ (0.617 vs 0.577) — but still WARN'd in validation. A5 (0.52x) and A9 (1.27x) regressed.

*(A5/A7/A9 sections collapsed — see Final Batch section below for verdicts.)*

---

## Bucket B — Clean-slate new families

*(All B candidates run — individual sections collapsed. See Final Batch section below for verdicts.)*

### B7. `vix_termstructure` — (research-grade, DATA-BLOCKED)

Still unimplemented — requires VIX9D / VIX3M data not in repo. Parked.

---

*(B2/B3/B5/B6/B8/B10/B11/B12/B13/B16 sections collapsed — see Final Batch section below for verdicts.)*

---

## Final Batch — COMPLETED 2026-04-20 (all remaining A + B)

Full grid + 7-gate validation on 13 strategies: **PASS=1 / WARN=6 / FAIL=18 across 291 combos. No new leaderboard entries.**

Key findings (raw TECL, pre-validation):

| # | Strategy | Best raw | vs VJ | Marker | Validation | Certification |
|---|---|---|---|---|---|---|
| A7 | `gc_vjbb` | **126.80x** | **+9.0%** | **0.617** (↑ vs VJ 0.577) | WARN | — |
| B10 | `adaptive_ema_vol` | 4.42x | -96% | — | WARN/FAIL | — |
| B16 | `slope_only_200` | 2.06x | -98% | — | **PASS (only one)** | **rejected by `data_quality_precheck`** |
| A9 | `gc_vjdd` | 2.58x | -98% | — | WARN | — |
| B5 | `bounce_breakout` | 1.32x | -99% | — | FAIL | — |
| B3 | `composite_osc_canonical` | 1.03x | -99% | — | FAIL | — |
| A5 | `gc_vjmac` | 1.83x | -98% | — | WARN | — |
| B2/B6/B8/B11/B12/B13 | | 0.00x | 0 configs pass charter pre-filter | | | |

Notable findings:
- **A7 `gc_vjbb` is the single best raw overlay across all five rounds**: +9% share on VJ *and* marker alignment improved (0.617 vs 0.577). First candidate to produce better marker alignment than VJ itself. Still WARN'd — the BB squeeze gate probably weakens cross-asset / walk-forward performance because TECL's squeeze periods are leverage-specific.
- **B16 `slope_only_200` is the only strategy of 25+ across all rounds to clear all 7 validation gates.** Fitness 0.49 (very low vs VJ's 42.21) but PASSed. Then rejected at leaderboard promotion by `data_quality_precheck` in certification — a gate downstream of validation.
- Every clean-slate Bucket B family (vol, RSI, ROC, MACD, voting, state-machine, macro, composite) underperforms on TECL by 1-3 orders of magnitude. The charter-pre-filter (share ≥ 1.0, trades 5-5/yr) kills most configs before validation even runs.

**Overall sweep conclusion (all rounds + Bucket C + Final Batch):**
- ~28 strategies implemented and grid-tested over the brainstorm (~900+ param combos across rounds)
- 0 new leaderboard entries
- Champion VJ (`gc_n8` at 116.34x) still holds
- 1 strategy PASSed validation (slope_only_200); rejected at certification
- 1 strategy produced better raw TECL + better marker alignment than VJ (gc_vjbb 126.80x, marker 0.617); WARN'd in validation

The search space canonical-within-current-gates may be exhausted for incremental VJ improvements. Future moves likely need either: (a) loosening validation (understand what specific gate rejected gc_vjbb), (b) new data sources (VIX term structure, breadth, explicit leverage-decay signals), or (c) a different base asset entirely.

---

## Bucket C — Circuit breakers and safety-net wrappers

Not strategies on their own. Wrappers that layer on top of any base strategy as a robustness guard. Test as independent add-ons.

**Bucket C — COMPLETED 2026-04-20 on VJ base.** Full grid + validation: **0 PASS / 20 WARN / 0 FAIL. No leaderboard changes.**
- **C1 `gc_n8_ddbreaker`** — 0 of 12 configs pass charter. Implemented with price-DD-from-ATH as proxy for equity-DD (valid since VJ is 100%-in-or-flat). On TECL the cumulative ATH drawdown latches permanently after the dot-com crash and the pause never releases. Rejected; proxy is structurally wrong for a leveraged asset with compounded cumulative DD.
- **C2 `gc_n8_timelimit`** — best raw 17.97x (max_hold=750, tl_ema=100) vs VJ's 116x. Forced time-based exits disrupt VJ's long-hold compounding (the feature, not the bug). Every config regresses. Rejected.
- **C3 `gc_n8_panic_flat`** — best raw 116.34x only because panic_vix=50 never fires historically (no-op). At realistic panic_vix=40, drops to 43.85x — VIX>40 overrides interfere with VJ's existing VIX>30 panic exit. Rejected.

**Diagnostic takeaway**: VJ's compounding engine *depends on* staying through drawdowns. Any added exit pressure damages it. Circuit breakers that make sense for cash-overlay/Roth equity smoothing actively conflict with the share-accumulation objective when layered on a leveraged-ETF trend strategy. These three are unlikely to validate on any VJ-family base.

---

## Prioritized test order

Highest expected value first, sized by "how much VJ gap does this close" × "orthogonality to what we've already tested."

**Round 1 — COMPLETED 2026-04-20.** Full grid + 7-gate validation pipeline: **0 PASS / 15 WARN / 5 FAIL. No leaderboard changes.** Raw TECL results (pre-validation) on VJ base (fast=120/slow=150):
- **A1 `gc_vjx`** — raw 130.94x TECL share at shock_look=5/vix_roc=2.0/drop=5-8%; 1 shock exit in 33yr. Validation rejected — not promoted.
- **A3 `gc_vjv`** — raw 118.32x at ratio=1.0 (gate near-inert). Rejected.
- **A10 `gc_vjatr`** — raw 116.34x (ATR exit never fires at best configs). Rejected.
- **A2 `gc_vjxr`** — raw 1.25x (shock over-fires, RSI re-entry can't recover). Rejected.

Per-gate reasons not yet pulled. Raw TECL lift alone is not a promotion criterion.

**Round 2 — COMPLETED 2026-04-20.** Full grid + validation: **0 PASS / 19 WARN / 1 FAIL. No leaderboard changes.** Raw TECL results (pre-validation) on VJ base (fast=120/slow=150):
- **A6 `gc_vjsgov`** — raw 135.74x (+16.8%) at rs_lookback=100, rs_persistence=20; 25 trades. Marker alignment drops 0.577→0.488 — SGOV exits fire out of phase with hand-marked cycles, likely why pipeline rejected. Rejected.
- **A4 `gc_vjrsi`** — identical to VJ (116.34x) across all configs. RSI secondary entry never adds entries beyond VJ primary; trend filter `close > EMA(100)` gates out target bounces. Inert. Rejected.
- **A8 `gc_vjtimer`** — best 7.66x (-93%). Time-stop structurally damages VJ compounding. Rejected.
- **B9 `pullback_in_trend`** — 0 of 72 configs pass charter pre-filter. Buy-the-dip fires in distribution tops on TECL; destroys capital. Rejected.

**Round 1+2 pattern**: raw TECL lifts don't survive cross-asset / walk-forward / marker-alignment gates. VJ's compound engine is hard to improve via surgical overlays that preserve base shape.

**Round 3 — COMPLETED 2026-04-20.** Full grid + validation: **0 PASS / 8 WARN / 12 FAIL. No leaderboard changes.**
- **B4 `dual_tf_gc`** — best raw 3.54x (fast=30/slow=200, outer=150/300). 9 trades, marker=0.501. Nested EMA filter too slow for a 3× leveraged asset; outer pair rarely crosses, holds through crashes. Rejected.
- **B1 `rsi_regime_canonical`** — best raw 2.61x (entry=35, exit=75, trend=200). 26 trades. Exit_rsi=75 fires on healthy momentum, selling the tops of every run. Rejected.
- **B14 `tecl_sgov_rs`** — 0 of 24 configs pass charter. SGOV history starts 2020; 27-year backtest runs 22 years with no signal. Data-blocked as a standalone primary. Rejected.
- **B15 `asym_ema_pair_20_100`** — already covered by existing `golden_cross_slope` grid at fast=20/slow=100 (5.05x) and fast=30/slow=150 (8.36x). Neither is on the leaderboard — previously failed validation too.

**Round 1+2+3 pattern**: only VJ-shape strategies clear validation on this dataset. Faster EMA pairs, RSI rotation, dual-timeframe confirmation, and cash-rotation signals all produce low share multiples and/or fail robustness gates.

**Rounds 4 + 5 + deferred — COMPLETED 2026-04-20 as one Final Batch.** See Final Batch section above for all 13 verdicts. Summary: PASS=1 / WARN=6 / FAIL=18. No leaderboard changes. Best raw TECL: A7 `gc_vjbb` at 126.80x (+9% vs VJ, marker 0.617 > 0.577); only B16 `slope_only_200` cleared all 7 validation gates but was rejected at certification.

**Circuit-breaker layer (Bucket C) — COMPLETED 2026-04-20.** All three rejected on VJ base. See Bucket C section above for per-wrapper verdicts. Summary: circuit breakers conflict with VJ's compounding-through-drawdowns mechanism.

**Still deferred**: B7 `vix_termstructure` (data-blocked — needs VIX3M/VIX9D feed).

---

## Common test protocol

Each candidate should be:

1. **Pre-registered in `docs/design-guide.md`** as a T0 hypothesis (or T1 addon for Bucket A) before any backtest.
2. **Smoke-tested** (60 seconds): log `share_multiple`, `num_trades`, `state_agreement`. Abort if `num_trades == 0` or `share_multiple < 1.0`.
3. **Run through full validation pipeline** (`scripts/validation/pipeline.py`) at the appropriate tier:
   - Bucket A (addons): T1 — same tier as VJ
   - Bucket B (new families): T0 — canonical-only, ≤5 tunable params
4. **Success checkpoint** = PASS verdict + specific gap closed:
   - A1 / A2: COVID + Liberation Day exits within 10 bars of peak
   - A3 / A4: state_agreement > VJ's 0.74
   - B*: share_multiple > 1.5 on TECL AND on QQQ (cross-asset)

## Shared-infrastructure items

While implementing the above, these pieces get built once and reused:

- **Shock circuit** (A1/A2/A10): Reusable exit helpers in `scripts/strategies/library.py`:
  - `_shock_exit_vix(vix_roc, price_drop, vix_look, price_look)` — VIX-driven (A1/A2)
  - `_shock_exit_atr(atr_ratio, price_look)` — ATR-driven (A10)
- **Realized-vol ratio gate** (A3/B2): Reusable `_vol_ratio_ok(ind, short, long, threshold)` entry helper.
- **RSI bounce helper** (A4/B1): Reusable `_rsi_cross_up(rsi, lower, upper)` entry helper.
- **Shock recovery watch state** (A2): Per-strategy state variable for "armed re-entry window." Design as reusable — used again by B9 pullback-in-trend.
- **Relative-strength calc** (A6/B14): `_relative_return(a, b, look)` helper. SGOV/TECL and QQQ/TECL both use it.
- **Percentile-rank helper** (A7): `_percentile_rank(series, look)` — rolling rank of a series within its trailing window. Used to keep BB-width and other continuous signals canonical.
- **Equity-curve tracker** (A9/C1): First time the engine tracks in-trade peak equity vs entry. New state — reusable across every drawdown-based wrapper.
- **Regime classifier** (B10/B11): `_regime_state(indicators)` — returns state label per bar. Shared across B10's adaptive-EMA and B11's state machine.
- **Circuit-breaker wrapper layer** (Bucket C): New architectural pattern — decorator that wraps a base strategy signal with an override. Should live in `scripts/strategies/wrappers.py` (new module).

## Data prerequisites

Some candidates need data-side work before they are testable:

| Candidate | Missing data | Lift required |
|---|---|---|
| A6, B14 | SGOV pre-2020 | Synthetic splice via BIL or constructed 3-mo T-bill series. Stage as "post-2020 only" first. |
| A5, B13 | — | Data already in repo (`fed-funds-rate.csv`, `treasury-spread-10y2y.csv`). Verify quality. |
| B7 | VIX9D, VIX3M | Source from CBOE historical. Blocked until available. |
| C3 | — | VIX data already present. |

## Legacy cross-reference

Related dormant ideas in `docs/Legacy/`:
- `Indicator/active/Montauk Composite Oscillator 1.3.txt` — source for B3
- `Python/strategies_1.2.py :: rsi_regime` — source for B1 (fit=66.47 in legacy era)
- `Python/strategies_1.2.py :: vol_regime` / `rsi_vol_regime` — source for B2
- `Python/strategies_1.2.py :: adx_trend` / `always_in_trend` — **caution**: ADX-only underperformed, don't revive standalone. ADX *as one component of B3 composite or B12 vote* is fine.
- `Python/strategies_1.2.py :: momentum_*` (if present) — cross-reference before building B8.

## What is still missing from this roster

Honest audit of what we have NOT covered:

- **Breadth / leadership signals** — would need XLK sector-component data (AAPL, MSFT, NVDA breadth). Not in repo. Structurally the most rigorous shock detector but data-blocked.
- **Volume-based signals** — OBV, accumulation/distribution. Data is in the CSVs but no strategy here uses it. Worth a future pass.
- **Cross-correlation / TECL-XLK beta decoupling** — when TECL's realized beta to XLK drifts from 3.0, leverage decay is active. Could gate entries. Research-grade — unclear if tractable within canonical params.
- **Seasonality** — worst-month / best-month effects. Documented in academic literature but risky to encode on a 27yr sample.
- **Stochastic / Williams %R family** — not covered. RSI is the only oscillator represented. Adding Stochastic as a sibling of B1 may expand coverage.
- **Explicit leverage-decay compensator** — when TECL underperforms 3×XLK for N bars, regime is "bad for leveraged ETFs" — flat until resolved. This is a TECL-specific rule and would fail charter's cross-asset generalization, but worth quantifying as a diagnostic even if not promotable.

These are not proposed for this round. They are the next frontier if Rounds 1-5 do not close the VJ gap.
