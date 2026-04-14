# Project Montauk Charter

**Canonical summary**: Project Montauk is a TECL share-accumulation factory: discover long-only TECL strategies that match the hand-marked cycle shape, validate them at a level that matches how they were selected, and generate Pine for the best PASS winner.

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
- **Position model**: single open position, all-in / all-out, no pyramiding
- **Time horizon**: multi-week to multi-month trend capture, not intraday
- **Execution surface**: Pine Script v6 on TradingView
- **Signal integrity**: bar-close confirmation only, no lookahead, no repainting

The project may search across many strategy families, but every family must still be:

- TECL-native
- long-only
- Pine-expressible
- compatible with a single `"Long"` order id and `strategy.close`

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
3. It is allowed onto the validated leaderboard, tagged with its tier.
4. It is emitted as a Pine Script candidate ready for TradingView review.

Anything short of that is research output, not a winner.

The system-level success condition is:

> hypothesize / discover -> validate at the right tier -> generate Pine -> manually review in TradingView

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

---

## 7. Coding Rules

- **Pine Script v6 only**
- `process_orders_on_close=true`, `calc_on_every_tick=false`
- One strategy block. One entry id `"Long"`. Exits via `strategy.close`
- Preserve stable parameter names unless there is a strong migration reason
- Python is the research engine; Pine is the execution artifact
- When uncertain about Pine syntax, consult `docs/pine-reference/`

---

## 8. Decision Rule

If asked to add work that breaks the charter, call it out clearly:

> "Out of scope per Montauk charter. The project is a long-only TECL share-accumulation factory. Trend-aligned alternative: [brief suggestion]."

If asked whether a raw optimizer winner should be treated as real, the answer is:

> "Not until it passes the validation tier appropriate to how it was selected, and has a deployable Pine artifact."

---

## 9. Naming

The skill is **Spike**. Spike launches and runs the **Montauk Engine** — the optimizer + validator + Pine generator pipeline.

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
