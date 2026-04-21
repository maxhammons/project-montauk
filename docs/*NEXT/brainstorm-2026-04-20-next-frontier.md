# Brainstorm 2026-04-20 — Next Frontier

Follow-up to `brainstorm-2026-04-20-velvet-jaguar-gaps.md`. After that sweep's ~28 candidates × ~900+ param combos added exactly 1 new strategy (`slope_only_200`) to the leaderboard, this doc starts from diagnosis rather than throwing more candidates at the same gate wall.

## What we now know

### Current state (2026-04-20)
- **154 strategies registered**, 131 with grids, 5,648 unique (strategy, params) combos evaluated.
- **Leaderboard: 4 entries.** `gc_n8` (116.34x) still champion; `gc_precross_strict` (50.71x); `gc_precross_roc` (44.44x); **new: `slope_only_200` (2.06x, fit=0.49)** — added this round.
- **Grandfathered legacy entries** predate the cross-asset tightening; new candidates must clear gate 6 fresh.

### The bottleneck: QQQ cross-asset gate 6 (threshold = 0.50)
Per-gate diagnosis on this session's best overlay (`gc_vjbb`, 126.80x raw on TECL, marker 0.617 > VJ's 0.577):
```
verdict: WARN
soft:    ['QQQ same-param share_multiple=0.443 < 0.50']
```
One soft warning, all other gates clean. The candidate is almost-there. Same failure mode as VJ itself (QQQ ~ 0.41), but VJ is grandfathered.

**`slope_only_200` passed because it has no cross-asset weakness**: one 200-EMA slope signal, low share (2.06x), no specific TECL tuning. It's a robustness-over-performance strategy.

### Why TECL→QQQ is hard
TECL = 3× XLK (daily-reset leveraged tech). QQQ = 1× Nasdaq-100. They diverge on:
1. **Volatility amplitude** — entries/exits tuned to TECL's ±3% daily swings mis-time QQQ's gentler moves.
2. **Daily-reset decay** — TECL underperforms 3×XLK in chop; QQQ has no such decay. Strategies that exploit TECL's "stay-out-of-chop" advantage don't help on QQQ.
3. **Sector concentration** — XLK is tech-only (AAPL/MSFT/NVDA heavy); QQQ is broader (adds AMZN/TSLA/COST/PEP). When tech leadership diverges from broader Nasdaq, strategies calibrated to tech shocks mistime QQQ.

### Validation-pipeline shape of what actually clears
Looking at the 4 leaderboard entries: all are EMA-cross or pre-cross with 120-150 range fast/slow EMAs except `slope_only_200`. None of the "creative" bucket-B families cleared. **The validation pipeline is biased toward slow trend-following on leveraged ETFs because that's what survives TECL→TQQQ→QQQ.**

---

## Framing for the next round

Three lanes, not one:

**Lane 1 — Raise the cross-asset floor by design.** Build strategies that *were always meant to generalize*: optimize jointly on TECL + QQQ from the start, or use price-regime-invariant features (percentile ranks, z-scores, state transitions) that don't depend on volatility amplitude.

**Lane 2 — Exploit the grandfathering loophole legitimately.** Champion VJ is 116x but has a QQQ share of ~0.41 (below the 0.50 gate). A surgical overlay that *raises VJ's QQQ share above 0.50 without cutting TECL share much* would clear gate 6 where VJ itself couldn't.

**Lane 3 — Mine unused data.** The repo has XLK and volume data that no current strategy exploits seriously. Breadth / leverage-decay detection sits on data already present.

---

## Lane 1 — Generalization-first strategies

Designed so that TECL and QQQ performance is coupled by construction, not a post-hoc hope.

### N1. `rank_slope_regime` — Percentile-rank slope, amplitude-invariant

> Replaces raw slope magnitude with its percentile rank within a trailing window. Amplitude-invariant by construction — same params work on any volatility regime.

```
Let slope[i] = (EMA(trend_len)[i] - EMA(trend_len)[i-slope_look]) / EMA(trend_len)[i-slope_look]
Let rank[i] = percentile rank of slope[i] within trailing rank_window
Entry: rank crosses up through entry_pct AND close > EMA(trend_len)
Exit:  rank crosses down through exit_pct
Cooldown: 5 bars
```

**Params**: `trend_len=100`, `slope_look=20`, `rank_window=200`, `entry_pct=50`, `exit_pct=30`, `cooldown=5`. 5 tunable, canonical (percentiles are structural).

**Hypothesis**: if slope *rank* (not magnitude) triggers entry, TECL and QQQ will trade in the same rank-space. Gate 6 is designed to fail if a strategy works on TECL because of TECL's amplitude; this removes that confound.

**Success bar**: TECL share > 2x AND **QQQ share > 0.50** at the same params. Not trying to beat VJ on TECL — trying to pass gate 6 cleanly.

---

### N2. `joint_optimization_ema_cross` — Same concept, multi-asset fitness

> Run grid search where the fitness function = min(TECL_share, QQQ_share × leverage_scaling) instead of TECL alone. Strategies are implicitly penalized for failing on QQQ.

**Not a strategy — a search infrastructure change.** Add a `--joint-fitness` flag to `grid_search.py` that computes fitness on the min of TECL and a scaled-QQQ number. Apply to all existing T1 strategies. Expect: current #1-3 leaderboard entries drop; whatever rises to the top has better cross-asset robustness by definition.

**Success bar**: produces at least one strategy that both (a) clears gate 6 easily and (b) has top-10 fitness under joint scoring.

---

### N3. `zscore_return_reversion` — Return-space mean reversion (scale-invariant)

> Enter when z-score of N-day return falls below threshold AND crossing back up. Z-scored returns are amplitude-invariant across TECL/QQQ/TQQQ.

```
Let ret_n[i] = close[i] / close[i-n] - 1
Let z[i] = (ret_n[i] - rolling_mean(ret_n, window)) / rolling_std(ret_n, window)
Entry: z[i-1] < entry_z AND z[i] >= entry_z  (crossing up through entry threshold from below)
       AND close > EMA(trend_len)                (trend filter)
Exit:  z[i] > exit_z   (mean-reverted to normal/overbought)
```

**Params**: `ret_n=20`, `window=100`, `entry_z=-1.5`, `exit_z=1.0`, `trend_len=200`, `cooldown=5`.

**Hypothesis**: Z-scores normalize out TECL's 3× amplitude. Same signal should fire on TECL and QQQ at roughly the same historical points.

**Risk**: z-score thresholds (-1.5, 1.0) aren't in canonical set. Document as free-threshold T1.

---

## Lane 2 — Raise VJ's QQQ share

Overlay VJ to specifically boost QQQ performance without cutting TECL materially. Because VJ is grandfathered at QQQ ~0.41, an overlay that gets VJ's QQQ to ≥ 0.50 *while keeping TECL ≥ ~100x* becomes a cleanly-passing upgrade.

### N4. `gc_vj_qqq_gated` — Entry only when QQQ trend confirms

> **The gate runs the TECL strategy but uses QQQ's own trend filter.** If QQQ is in a downtrend even as TECL's 120/150 EMAs cross, skip entry.

```
Base: gc_n8 (VJ)
Added ENTRY gate:
  QQQ_EMA(50) > QQQ_EMA(200) on bar i
```

**Params**: VJ + `qqq_fast=50`, `qqq_slow=200`.

**Hypothesis**: QQQ-gated entries avoid the tech-idiosyncratic shocks where TECL runs but QQQ doesn't. Should boost QQQ same-param replay.

**Implementation note**: QQQ close already in `Indicators` via the cross-asset machinery. Needs verification.

**Data-availability note**: the `Indicators` class has `xlk_close` but QQQ is loaded at the engine level for validation. Exposing `ind.qqq_close` may require engine work. **Check before building.**

---

### N5. `gc_vj_xlk_relative_trend` — Entry requires XLK-trend-confirmation

> Similar to N4 but uses XLK (the TECL underlying). If XLK is also in an uptrend, the move is structural (tech sector); if only TECL is, it's a leverage-decay echo.

```
Base: gc_n8 (VJ)
Added ENTRY gate:
  XLK_EMA(50) > XLK_EMA(200)
  AND XLK_EMA(50) rising for 2 bars
```

**Params**: VJ + `xlk_fast=50`, `xlk_slow=200`, `xlk_slope=2`. 3 extras.

**Hypothesis**: XLK-confirmed entries should also work on QQQ (which overlaps XLK in tech weighting).

**Implementation**: `ind.xlk_ema(len)` already exists. Low-lift.

---

### N6. `gc_vj_decay_gate` — Flat when TECL decay is active

> Leverage-decay detector: when TECL's realized 20-bar return is *below* 3× XLK's 20-bar return by more than N percentage points, the 3× multiple is breaking down → don't enter.

```
Base: gc_n8 (VJ)
Added ENTRY gate:
  tecl_ret = close[i]/close[i-20] - 1
  xlk_ret = xlk_close[i]/xlk_close[i-20] - 1
  gap = tecl_ret - 3 * xlk_ret     (ideal = 0; negative = decay active)
  Require: gap > decay_threshold   (not in decay regime)
```

**Params**: VJ + `decay_look=20`, `decay_threshold=-0.05` (free).

**Hypothesis**: TECL enters periods where 3× leverage is breaking down via daily-reset (choppy sideways markets). Detecting that should *both* improve TECL share AND improve QQQ share (because QQQ doesn't have decay; strategies that avoid decay periods on TECL will trivially pass on QQQ).

**This is the highest-value candidate in Lane 2** — addresses a TECL-specific weakness directly.

---

## Lane 3 — Unused data

### N7. `volume_confirmed_gc` — Golden cross + OBV trend confirmation

> OBV (already in Indicators) measures accumulation vs distribution. A golden cross confirmed by rising OBV is a "real" trend, not a technical artifact. None of the current leaderboard strategies use volume.

```
Entry: EMA(fast) > EMA(slow)
       AND EMA(fast) rising for entry_bars
       AND OBV_EMA(obv_len) rising over slope_window
Exit:  EMA(fast) < EMA(slow)
       OR OBV_EMA(obv_len) flat/falling over slope_window
Cooldown: 5 bars
```

**Params**: `fast=50-100`, `slow=150-200`, `obv_len=20-100`, `slope_window=3/5`, `entry_bars=2/3`, `cooldown=5`. ~6 tunable.

**Note**: this is similar to existing `obv_slope_trend` in the registry. Check its leaderboard status before duplicating — may be enough to just add 120/150 base to that grid.

---

### N8. `breadth_decay_composite` — (partially data-blocked)

> Ideal: detect when TECL's rally is narrow (few XLK components in uptrend) vs broad. Data-blocked as written — needs individual XLK holdings (AAPL, MSFT, NVDA, etc.).

**Proxy approach (available now)**: use the ratio of TECL-return / XLK-return on a rolling window as a "rally breadth" surrogate. When TECL/3×XLK ratio is low, rally is broad-based (healthy). When ratio is high, rally is narrow (concentrated; fragile).

```
Let breadth_proxy = (1 + tecl_ret_n) / (1 + 3 * xlk_ret_n)
Entry: VJ signal AND breadth_proxy < narrow_threshold (broad rally)
```

**Hypothesis**: broad rallies generalize to QQQ; narrow ones don't.

**Risk**: the proxy conflates leverage decay (a microstructure effect) with genuine breadth. Research-grade.

---

### N9. `dual_asset_regime_classifier` — TECL and XLK both must agree

> Pure state classifier: long only when TECL-regime and XLK-regime both say "BULL". Not a standalone — wraps any base strategy.

```
TECL_regime = BULL if EMA(50)_tecl > EMA(200)_tecl else BEAR
XLK_regime  = BULL if EMA(50)_xlk > EMA(200)_xlk else BEAR

Wrapper: allow entries only when TECL_regime == BULL AND XLK_regime == BULL
Exit on either TECL or XLK regime flip
```

**Applied to**: VJ (to raise QQQ share) or to any clean-slate strategy.

**Hypothesis**: dual-regime gate is a structural cross-asset filter. By definition the signal works when both agree.

---

## Lane 4 — Meta-strategy and infrastructure

### N10. `vj_or_slope_meta` — Champion + robust fallback composite

> VJ compounds 116x but has a weak QQQ. `slope_only_200` is only 2x but passes everything. A meta-strategy that **ORs** their entry signals and takes whichever fires first may combine VJ's TECL performance with slope_only_200's QQQ robustness.

**Implementation**: new function `meta_vj_slope(ind, p)` that returns `entries = vj_entries | slope_entries`, `exits = earlier(vj_exits, slope_exits)`.

**Hypothesis**: we don't know in advance which of these strategies will fire on QQQ; using both gives cross-asset coverage.

**Risk**: composite adds trade frequency. Charter floor/ceiling issues.

---

### N11. `grid_search --joint-fitness` — Infrastructure change

> Not a strategy. Add to `scripts/search/grid_search.py` an alternative fitness: `joint_share = min(TECL_share, QQQ_share * leverage_factor)`. Re-rank all existing 131 strategies by this.

**Expected finding**: strategies that didn't top the TECL-share leaderboard but pass gate 6 easily will rise to the top. Those become promotion candidates *even without new logic*.

**Lift**: small code change (~40 lines) to `_backtest_single` / `_worker_backtest` to compute both TECL and QQQ share multiples, then rank on min.

---

### N12. `dedicated tested-strategies.md index` — Tracking
> Reported request from the last round: no single source of truth for "strategy X tested on date Y with verdict Z." Build one.

**Fields**: strategy name, tier, round/date tested, n_combos, best raw TECL share, best QQQ share, validation verdict, gate rejected (if any), leaderboard status. Sourced from `STRATEGY_REGISTRY` (inventory), `spike/hash-index.json` (combos evaluated), `spike/leaderboard.json` (passed), + manual brainstorm entries (failed verdicts).

**Deliverable**: `docs/*NEXT/tested-strategies.md`, maintained after each spike run.

---

## Execution log (2026-04-20)

All four rounds run through the full grid + 7-gate validation pipeline, same rigor as prior brainstorms. See `docs/*NEXT/tested-strategies.md` for the consolidated index.

### Round A — Lane 2 (VJ cross-asset rescue)
**72 combos, 0 pass charter.** Every N5/N6/N9 config filters enough of VJ's entry stream that the resulting strategy drops below the charter share ≥ 1.0 floor. Adding any cross-asset entry gate to VJ — even the most permissive threshold tested — damages its compounding below b&h.
- **N6 `gc_vj_decay_gate`**: 24 configs, 0 pass. Decay threshold anywhere in [-0.10, 0.0] filters out entries that VJ relies on.
- **N5 `gc_vj_xlk_relative_trend`**: 32 configs, 0 pass. XLK trend filter rejects entries that VJ's own logic already admits properly.
- **N9 `gc_vj_dual_regime`**: 16 configs, 0 pass. Dual-regime exit fires ~8 times per run, cutting VJ's long holds.

### Round B — Lane 1 (generalization-first)
**96 combos, 5 validated, 0 PASS / 0 WARN / 5 FAIL.** Amplitude-invariant signals don't survive validation on the leveraged-ETF share-accumulation objective.
- **N1 `rank_slope_regime`**: 48 configs. Rank-based slope fires 40-50 trades per run; mean-reversion back through exit_pct sells every small dip.
- **N3 `zscore_return_reversion`**: 48 configs. Mean-revert exits sell every rally (z > 1.0 triggers constantly in uptrends).

### Round C — Lane 3 (unused data)
**156 combos, 9 validated, 0 PASS / 9 WARN / 0 FAIL.** No new promotions.
- **N7 (via extending `obv_slope_trend` grid)**: Best raw 1.59x at fast=30/slow=100 (not the VJ 120/150 pair — that fails charter). All 9 WARN.
- **N8 `breadth_decay_composite`**: 0 pass charter. Breadth proxy fires trend exits too often.

### Round D — Lane 4 (meta + infrastructure)
**16 combos, 3 validated PASS, 0 WARN, 0 FAIL — but 0 admitted to leaderboard due to data-quality infrastructure issue.**

- **N10 `vj_or_slope_meta`**: **Three configs PASSED all 7 validation gates** (fitness 2.50, 0.76, 0.64). All three rejected at certification stage by `data_quality_precheck` — caused by **Tiingo API returning HTTP 429 (rate limited)** which cascades into `crosscheck_divergence` FAIL. This is an external-API flakiness, not a strategy defect.
  - The pre-fitness-2.50 config: `fast_ema=100, slow_ema=150, slope_window=3, entry_bars=2, cooldown=2, slope_ema_len=150, slope_look=20`. Worth retrying when API limits clear.

- **N4 `gc_vj_qqq_gated`** — deferred. Requires adding QQQ to `Indicators` class (engine change), out of scope for this session.

- **N11 joint-fitness infrastructure** — scoped but not implemented. One-hour change to `_backtest_single` / `_worker_backtest` to compute joint `min(TECL, QQQ*k)` fitness. Unblocks re-ranking all 138 grids.

- **N12 tested-strategies.md** — **DONE**. See `docs/*NEXT/tested-strategies.md`.

### Session totals
| Round | Combos | PASS | WARN | FAIL | Leaderboard delta |
|---|---|---|---|---|---|
| A (Lane 2) | 72 | — | — | — | 0 (all charter) |
| B (Lane 1) | 96 | 0 | 0 | 5 | 0 |
| C (Lane 3) | 156 | 0 | 9 | 0 | 0 |
| D (Lane 4, N10) | 16 | **3** | 0 | 0 | **0 (blocked by flaky Tiingo API)** |

**Key finding**: `vj_or_slope_meta` is a real validation-PASSing candidate. The only thing stopping admission is transient API rate limiting in the data-quality cross-check. Worth either (a) re-running when the API cools off, (b) the same manual-admit path we used for `gc_vjbb`, or (c) patching `test_crosscheck_divergence` to SKIP on HTTP-429 (cleanest long-term fix).

## Priority order

**Round A — Lane 2 (VJ cross-asset rescue, high-value)**
1. **N6 `gc_vj_decay_gate`** — directly addresses TECL-leverage-decay, which is the structural cause of cross-asset weakness. Highest expected value.
2. **N5 `gc_vj_xlk_relative_trend`** — XLK is TECL's underlying; already in Indicators. Low lift, direct hypothesis.
3. **N9 `dual_asset_regime_classifier`** as wrapper on VJ — structural cross-asset filter.

**Round B — Lane 1 (generalization-first)**
4. **N11 joint-fitness infrastructure change** — no new strategies; re-rank what we have. May find latent winners.
5. **N1 `rank_slope_regime`** — amplitude-invariant by design.
6. **N3 `zscore_return_reversion`** — mean reversion on normalized returns.

**Round C — Lane 3 (unused data)**
7. **N7 `volume_confirmed_gc`** — check existing `obv_slope_trend` first; may be sufficient to extend that grid.
8. **N8 `breadth_decay_composite`** — research-grade proxy; may be diagnostic only.

**Round D — Meta + infrastructure**
9. **N4 `gc_vj_qqq_gated`** — QQQ trend confirmation. Needs engine support for QQQ in Indicators (verify before building).
10. **N10 `vj_or_slope_meta`** — composite of VJ + slope_only_200.
11. **N12 tested-strategies.md index** — parallel to strategy work.

---

## Out of scope for this round

Things still worth considering but parked:
- **Seasonality** — month-of-year, day-of-week effects. Low statistical power on 27yr sample.
- **Stochastic / Williams %R standalone** — already partially covered by `willr_recovery_trend`, `stoch_cross_trend`, etc. in registry.
- **Regime-state machines with deeper rule libraries** — B11 already failed; more rules make overfitting worse.
- **New data feeds (VIX9D, VIX3M, XLK holdings)** — real blocker. Would open N4/N8 properly but requires data sourcing.

## Honest expectations

Given that 28 candidates in the prior brainstorm produced 1 marginal leaderboard addition, realistic target for this round is 1-3 new leaderboard entries, most likely from Lane 2 (N5/N6) since they attack the specific gate (cross-asset) that's been the blocker. Lane 1 is more ambitious structurally; Lane 3 is more speculative. Lane 4's N11 (joint fitness) is the single highest-leverage infrastructure change — it surfaces what's already latent in 131 grids without requiring new logic.
