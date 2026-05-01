# Project Montauk Charter

**Canonical summary**: Project Montauk is a TECL share-accumulation factory: discover long-only TECL strategies that match the hand-marked cycle shape, validate them at a level that matches how they were selected, and emit a certified signal bundle for the best PASS winner.

---

## 1. Mission

The single goal of Project Montauk is to **end up holding more shares of TECL than buy-and-hold would**, by avoiding major drawdowns and re-entering after corrections.

TECL is treated as an instrument anchored to a long-term-rising underlying (the US tech complex). The job is not to predict markets. The job is to:

- stay invested through bull legs
- step aside before serious drawdowns
- buy back more shares than were sold when the cycle resets
- never force a trade

Holding through a year of new highs without trading is a successful year. The strategy is not penalized for inactivity.

`montauk_821` is the current baseline reference, not the mission. The mission is to discover the best charter-compatible TECL strategy family.

---

## 2. Scope Guardrails

Every promotable strategy must stay inside these boundaries:

- **Symbol**: TECL only
- **Direction**: long-only
- **Position model**: single open position, all-in / all-out, no pyramiding, 100% equity
- **Time horizon**: multi-week to multi-month trend capture, not intraday
- **Execution surface**: Python signal engine; manual brokerage execution from the daily risk_on / risk_off output
- **Signal integrity**: bar-close confirmation only, no lookahead, no repainting

The project may search across many strategy families, but every family must still be:

- TECL-native
- long-only
- expressible in the Python signal engine as a single binary risk_on / risk_off state
- compatible with the 100%-equity single-position execution model

---

## 3. North Star: The Marker Chart

The hand-marked TECL cycle file [`data/markers/TECL-markers.csv`](../data/markers/TECL-markers.csv) is the platonic ideal of cycle timing — Max's hindsight-perfect buy/sell calls across the full TECL history.

**The marker chart is a north star for hypothesis design and a diagnostic for ranking — not a hard validation gate.**

What the marker chart IS:
- The reference shape Claude consults when designing new T0 hypotheses (see `T0-DESIGN-GUIDE.md`)
- A diagnostic metric (`state_agreement`, `marker_score`) reported on every candidate
- A meaningful contributor to composite quality scoring and ranking

What the marker chart is NOT:
- A hard gate that blocks promotion
- A requirement to match Max's drawn dates
- The single criterion of success

A strategy is a winner if it **maximizes share count vs B&H within charter constraints** (≤5 trades/year, survives walk-forward / cross-asset / concentration gates). The marker chart describes one excellent way to do that, but not the only way. A strategy that accumulates more shares than B&H by trading a different cycle shape is still winning the charter game.

Marker-shape diagnostics:
- `state_agreement < 0.30` — critical warning (essentially uncorrelated with markers)
- `state_agreement < 0.50` — soft warning (barely above random alignment)
- otherwise — informational only

---

## 4. Success Definition

A strategy is only considered real when it completes this full chain:

1. It is registered in the appropriate validation tier (T0 / T1 / T2 — see `VALIDATION-PHILOSOPHY.md`).
2. It passes the validation pipeline for its tier with a final **PASS** verdict.
3. It becomes **certified not overfit**: passed the tier-appropriate validation verdict and every required anti-overfit certification check.
4. It is emitted as a `backtest_certified` signal bundle (standardized run artifacts + native HTML visualization) ready for manual brokerage execution review.
5. It earns **Gold Status**: certified not overfit, artifact-verified / `backtest_certified`, and beating B&H in the full, real, and modern eras.
6. Only Gold Status strategies may appear on the validated leaderboard, tagged with their tier.

Anything short of that is research output, not a winner.

The system-level success condition is:

> hypothesize / discover -> validate at the right tier -> certify signal bundle -> manually execute in brokerage

The leaderboard is a trust surface, not a research watchlist. All-era performance determines rank only after Gold Status is earned. If fewer than 20 strategies are Gold Status, the leaderboard should contain fewer than 20 rows.

---

## 5. Non-Goals

The project is not trying to become:

- a multi-asset production strategy platform
- a short-selling system
- an options system
- an intraday or high-frequency system
- an auto-live-deployment bot
- a place where raw backtest winners bypass validation
- a system that punishes strategies for trading infrequently

Cross-asset data is allowed for validation only. It is not the production trading scope.

---

## 6. Evaluation Standards

The project optimizes for **share accumulation**, not impressive equity curves.

### Primary metric

| Metric | Definition |
|--------|-----------|
| **Share-count multiplier vs B&H** | At end of backtest, mark the strategy's equity to TECL share-equivalent and divide by buy-and-hold's share count. Must be > 1.0. |

### Secondary metric (shape)

| Metric | Definition |
|--------|-----------|
| **Marker shape alignment** | State agreement % between the strategy's risk-on/risk-off bar-level series and the marker-derived target series, plus median transition lag and missed-cycle count. |

### Tertiary metrics (sanity / quality)

| Metric | Role |
|--------|------|
| vs Buy and Hold (dollars) | Sanity check on the share-count metric |
| CAGR | Return path quality |
| Max Drawdown | Risk |
| MAR | Return-to-drawdown quality |
| Avg days in trade | Should reflect actual trend capture |
| Exit reason breakdown | Reveals whether one brittle rule carries the whole system |

### Removed / downweighted

- **Trade-frequency punishment for low-trade strategies** — a strategy that holds 18 months because TECL is ripping is winning, not under-trading. The pipeline must not penalize this.

Validation quality matters as much as performance. A high-share-count strategy that fails validation is out of scope for promotion.

Raw performance and share multiple do **not** determine leaderboard eligibility by themselves. Gold Status is the eligibility rule: a strategy must be certified not overfit, artifact-verified / `backtest_certified`, and above B&H in the full, real, and modern eras. Ranking happens only after that and should reflect overall performance across full / real / modern eras rather than a single favored regime. The separate family-confidence leaderboard selects one Gold row per family and, when Confidence v2 artifacts are present, ranks those representatives by Edge Confidence, then Capital Readiness.

---

## 7. Coding Rules

- **Python is the single source of truth** for signals and execution logic
- Bar-close confirmation only: no lookahead, no repainting, `process_orders_on_close=true` semantics
- One strategy block per registered candidate. One long entry, one long exit, no pyramiding
- Preserve stable parameter names unless there is a strong migration reason
- Every operational champion ships with the standardized run artifacts (trade ledger, signal series, equity curve, drawdown curve, validation summary, dashboard bundle) — see `docs/pipeline.md`

---

## 8. Decision Rule

If asked to add work that breaks the charter, call it out clearly:

> "Out of scope per Montauk charter. The project is a long-only TECL share-accumulation factory. Trend-aligned alternative: [brief suggestion]."

If asked whether a raw optimizer winner should be treated as real, the answer is:

> "Not until it passes the validation tier appropriate to how it was selected, emits a complete `backtest_certified` signal bundle, and earns Gold Status."

If asked what belongs on the leaderboard, the answer is:

> "Only Gold Status strategies: certified not overfit, artifact-verified / `backtest_certified`, and beating B&H in full, real, and modern eras. Ranking comes after Gold Status, never before it."

---

## 9. Naming

The skill is **Spike**. Spike launches and runs the **Montauk Engine** — the optimizer + tier-routed validator + run-artifact emitter.

- "Spike" = the entrypoint / command surface
- "Montauk Engine" = the underlying machinery

This is a semantic split, not a code rename. Files, scripts, and commands keep their current names.

---

## 10. Appendix Pointer

The core charter stays focused on the TECL signal factory itself.

Approved supporting layers that do not change the core mission, including:

- the marker-aligned discovery north star (formalization of how the marker drives discovery)
- Roth deployment overlays

are described in `Montauk Charter Appendix - Discovery and Roth Overlay.md`.
