# T0 Hypothesis Design Guide

> When authoring a new T0 strategy, read this first. It distills what we have
> learned from the candidates that have cleared (and failed) the new pipeline.

T0 strategies are pre-registered hypotheses with canonical-only params. Their
defense against overfit is structural (canonical + ≤5 params + pre-registered
before any backtest), not statistical. So the bar is **not** "clever optimisation."
The bar is **"is this a coherent hypothesis that engages the marker cycles, beats
B&H share count, and generalises off TECL?"**

---

## 1. The bar a T0 must clear

Every new T0 must clear all of these hard gates to PASS:

| Gate | Threshold | What it asks |
|------|-----------|--------------|
| **Charter** | `share_multiple > 1.0` | "Did you accumulate more TECL units than B&H?" |
| **Charter** | `trades_per_year ≤ 5.0` | "Are you a regime strategy, not a scalper?" |
| **Eligibility** | `trade_count ≥ 5` | "Did the strategy actually engage at all?" |
| **Walk-forward** | OOS/IS ratio decent | "Does it work across time windows, not just one period?" (soft at T0) |
| **Cross-asset** | Beats B&H on TQQQ/UPRO | "Does the logic generalise off TECL?" |
| **Synthesis** | composite_confidence > 0.45 (FAIL floor) | Geometric mean of all sub-scores |

Hitting "all hard gates" is necessary but not sufficient — too many soft warnings
(>= 8 at T0) downgrades to WARN, which is not promotable.

### Marker alignment is a diagnostic, not a gate

The marker chart is a north star for *designing* hypotheses (see Section 4), but
it does NOT hard-fail validation. Soft / critical warnings only:

- `state_agreement < 0.30` → critical warning (essentially uncorrelated with markers)
- `state_agreement < 0.50` → soft warning (barely above random alignment)
- otherwise informational

A strategy that maximizes share count via a different cycle shape than Max's
markers can still PASS, as long as it clears the hard gates above. The marker
shape is "one excellent way to do this," not "the only way."

---

## 2. Patterns that have worked

### `golden_cross_slope` (PASS, share=4.04x, marker=0.733)

```
fast_ema=50, slow_ema=200, slope_window=5, entry_bars=3, cooldown=5

Entry: fast > slow AND slow rising (5-bar slope > 0) for 3 consecutive bars
Exit:  fast crosses below slow (death cross), no confirmation
```

**Why it works:**
- Moderate horizon (50/200) — slow enough to avoid whipsaws, fast enough to engage cycles
- Slope filter on slow EMA filters out chop
- Asymmetric: entry requires confirmation, exit is reactive (preserve capital fast)
- 18 trades over 27yr (0.7/yr) — patient
- Conceptually motivated: classic Wall Street regime signal, not invented

---

## 3. Patterns that have failed (and why — so we don't repeat them)

### `ema_200_regime` (FAIL — marker state_agreement=0.646 < 0.65)

```
ema_len=200, cooldown=2

Entry: close crosses above EMA-200
Exit:  close crosses below EMA-200
```

**Why it fails:** Raw price-vs-EMA cross **whipsaws** at every cycle boundary.
84 candidate buys vs 14 target buys = 6× over-trading. State agreement collapses
because the strategy oscillates in and out far more than the marker shape implies.

**Lesson:** Add a confirmation/slope filter to any single-line cross strategy.
Bare crosses on a leveraged ETF generate too many false transitions.

### `golden_cross_100_300` (FAIL — share=0.358x < 1.0 charter floor)

```
fast_ema=100, slow_ema=300, slope_window=5, entry_bars=3, cooldown=5
```

**Why it fails:** Long EMAs over-lag. By the time 100-EMA crosses 300-EMA, the
move is half over. Then by the time the death cross fires, much of the bear is
realized. The strategy buys high and sells low — *destroys* shares vs B&H.

**Lesson:** Don't push EMA periods beyond ~50/200 on TECL. TECL is 3× leveraged;
its volatility is ~3× QQQ, so a 300-EMA on TECL behaves like a 900-EMA on QQQ.
Long horizons that are sensible on QQQ are fatal on TECL.

### `tema_200_slope` (FAIL — 0 trades, degenerate)

```
tema_len=200, slope_window=5, entry_bars=3, cooldown=5
Entry: close > TEMA AND TEMA rising for 3 consecutive bars
```

**Why it fails:** TEMA needs `length × 3` bars of warmup (600 bars ≈ 2.4 years).
Then the conjunction `close > TEMA AND slope > 0 for 3 consecutive bars` is so
restrictive it never actually fires through TECL's history.

**Lesson:** Sanity-check **base rates** before committing a hypothesis. If your
entry condition is N independent filters AND-ed together with confirmation bars,
the joint probability shrinks fast. A 1-line backtest of `bool_arr.sum()` on the
joined condition catches 0-trade designs in seconds.

### `donchian_200_100` (WARN — beats B&H on TECL but fails QQQ generalisation)

```
entry_len=200, exit_len=100, trend_len=200, cooldown=5
Entry: close > 200-day high AND close > EMA-200
Exit:  close < 100-day low
```

**Why it WARNs:** share=1.51x ✓, marker=0.68 ✓, every individual hard gate
clears. But the strategy underperforms B&H in **all 4 named windows** (2020
meltup, 2021/22 bear, 2023 rebound, 2024 onward) AND QQQ same-param share_multiple=0.28.
Eight soft warnings accumulate → WARN.

**Lesson:** Pure breakout-on-new-high is too slow to re-engage after crashes
(takes a long time to recover the prior high). Need to combine breakout logic
with a faster re-entry signal, OR accept that pure breakout strategies are
research-grade not promotable.

---

## 4. Design checklist before you author

Before committing a new T0 to the registry, walk through this list. If any answer
is "no" or "I don't know," redesign first.

### Hypothesis discipline
- [ ] Is the hypothesis stated in plain English in the docstring?
- [ ] Is it conceptually motivated (charter principles, marker chart, leverage-decay
      math, published rule) — **not** "I noticed the GA preferred X"?
- [ ] Are all params committed up front (in the docstring AND the registry)?

### Canonical compliance
- [ ] All param values from the strict canonical set (`canonical_params.py`)?
- [ ] ≤ 5 tunable params (excluding cooldown)?

### Engagement (marker is a design heuristic, not a gate — but still useful)
- [ ] Will this engage every major bull cycle in TECL's history?
  Major bulls: 1999, 2003-2007, 2009-2015, 2016-2018, 2020-2021, 2023+
- [ ] Will this exit before/during major bears?
  Major bears: 2000-2002, 2008-2009, 2018, 2020 crash, 2022
- [ ] Estimated trade count (sanity): ~5–30 over 27 years (T0 is patient)
- [ ] Target: state_agreement > 0.50 (anything below is barely better than random
  alignment — soft warning territory)

### Lag discipline (TECL-specific)
- [ ] Slowest indicator window ≤ 200 bars? (Long EMAs are fatal on 3× leveraged ETFs.)
- [ ] If using TEMA, account for `length × 3` warmup; keep `length ≤ 50` unless you
      explicitly want a slow signal
- [ ] If chaining N conditions with AND, sanity-check that the joint base rate
      isn't ~0 (a simple bool_arr.sum() on each component reveals this in seconds)

### Asymmetry
- [ ] Entry can be slow/confirmed (avoid whipsaws); exit should be reactive
      (preserve capital fast)
- [ ] Don't symmetrically require confirmation for both entry AND exit — that
      compounds restrictiveness

### Generalisation
- [ ] Does the logic depend on TECL-specific noise, or on TREND structure that
      should also work on TQQQ/QQQ/UPRO?
- [ ] Mental cross-asset check: would a trader looking at QQQ daily charts
      recognise this as a sensible signal?

### Charter compliance
- [ ] Long-only, single-position, 100% equity
- [ ] No look-ahead (entry/exit signals computed only from past data)
- [ ] Expressible as a binary risk_on / risk_off signal in the Python engine

### Smoke test (do this in 60 seconds before validation)
- [ ] Backtest on TECL once, log: share_multiple, num_trades, marker state_agreement
- [ ] If share < 1.5x, reconsider before running full validation (close to charter floor)
- [ ] If state_agreement < 0.50, the strategy is barely better than random
      alignment with markers (soft warning territory but not disqualifying)
- [ ] If 0 trades or > 50 trades over 27yr, redesign

---

## 5. Hypothesis families worth exploring

These directions have not yet been tried and are likely to clear T0 if designed well:

### Trend with momentum re-entry
- 200-EMA trend filter + RSI recovery from oversold for re-entry after pullbacks
- Designed to handle the post-crash rebound problem (2020, 2023) that pure
  golden cross failed
- Canonical: `ema_len=200, rsi_len=14`

### Asymmetric EMA pair
- Different fast/slow combos within the canonical set (20/100, 30/150)
- The 50/200 already passed; smaller variants may engage cycles faster
- Canonical: any two from `MA_PERIODS`

### Volatility-regime filter
- Stay long when realized vol is below its long-term average; sit out when above
- Volatility regime is structurally different from price regime
- Canonical: vol windows from `LOOKBACK_PERIODS`

### Slope-only signal
- Hold while EMA-N slope is positive over a window; exit on slope flip
- No price/EMA cross, just slope direction
- Canonical: `ema_len=100 or 200, slope_window=20` (note: 20 not in `SLOPE_CONFIRM_BARS`
  yet — would either need to add or use a 5-bar slope on a slower EMA)

---

## 6. When to abandon a hypothesis

Stop authoring a hypothesis if:

- The smoke test shows < 1.0x share multiple
- The smoke test shows 0 trades (degenerate)
- You find yourself adding more filters to "make it work" — that's tuning, which
  T0 forbids by definition
- The hypothesis only differs from an existing T0 in one canonical-param swap
  (e.g., 50/200 → 100/300) — the existing one already covers that signal family

A failed hypothesis is fine. A failed hypothesis that gets re-tuned into something
that passes is overfit by another name.
