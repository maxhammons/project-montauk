# Project Montauk Charter

**Canonical summary**: Project Montauk is a TECL strategy factory: discover many long-only TECL strategies, validate them hard against overfitting, and generate Pine for the best PASS winner.

---

## 1. Mission

Project Montauk exists to find robust long-only TECL strategies that:

- capture major bull legs
- exit bear phases early enough to preserve capital
- survive hard validation
- end as deployable Pine Script candidates for TradingView

This project is **not** limited to one hand-authored strategy. `montauk_821` is the current baseline and reference implementation, but the project goal is broader: discover the best charter-compatible TECL strategy family, not just tune one EMA system forever.

---

## 2. Scope Guardrails

Every promotable strategy must stay inside these boundaries:

- **Symbol**: TECL only
- **Direction**: long-only
- **Position model**: single open position, all-in/all-out, no pyramiding
- **Time horizon**: multi-week to multi-month trend capture, not intraday trading
- **Execution surface**: Pine Script v6 on TradingView
- **Signal integrity**: bar-close confirmation only, no lookahead, no repainting

The project may search across many strategy families, but every family must still be:

- TECL-native
- long-only
- Pine-expressible
- compatible with a single `"Long"` order id and `strategy.close`

---

## 3. Success Definition

A strategy is only considered real when it completes this full chain:

1. It is discovered by the optimizer across a broad TECL strategy search space.
2. It passes the validation pipeline with a final **PASS** verdict.
3. It is allowed onto the validated leaderboard.
4. It is emitted as a Pine Script candidate ready for TradingView review.

Anything short of that is research output, not a winner.

The system-level success condition is therefore:

> discover -> validate -> generate Pine -> manually review in TradingView

---

## 4. Non-Goals

The project is not trying to become:

- a multi-asset production strategy platform
- a short-selling system
- an options system
- an intraday or high-frequency system
- an auto-live-deployment bot
- a place where raw backtest winners bypass validation

Cross-asset data is allowed for validation only. It is not the production trading scope.

---

## 5. Evaluation Standards

Raw backtest numbers are not enough. The project optimizes for **robust outperformance**, not impressive charts.

Primary strategy-level metrics:

| Metric | Why it matters |
|--------|----------------|
| vs Buy and Hold | Core benchmark: the strategy must justify its existence |
| CAGR | Primary return measure |
| Max Drawdown | Primary risk measure |
| MAR | Return quality under drawdown |
| Trades/year | Must stay low; the project is not a churn machine |
| Avg days in trade | Should reflect actual trend capture |
| Exit reason breakdown | Reveals whether one brittle rule carries the whole system |

Validation quality matters as much as performance. A high-return strategy that fails validation is out of scope for promotion.

---

## 6. Coding Rules

- **Pine Script v6 only**
- `process_orders_on_close=true`, `calc_on_every_tick=false`
- One strategy block. One entry id `"Long"`. Exits via `strategy.close`
- Preserve stable parameter names unless there is a strong migration reason
- Python is the research engine; Pine is the execution artifact
- When uncertain about Pine syntax, consult `reference/PineScript Version 6 Reference.txt`

---

## 7. Decision Rule

If asked to add work that breaks the charter, call it out clearly:

> "Out of scope per Montauk charter. The project is a long-only TECL strategy factory. Trend-aligned alternative: [brief suggestion]."

If asked whether a raw optimizer winner should be treated as real, the answer is:

> "Not until it passes validation and has a deployable Pine artifact."

---

## 8. Appendix Pointer

The core charter stays focused on the TECL signal factory itself.

Approved supporting layers that do not change the core mission, including:

- discovery-stage marker priors
- Roth deployment overlays

are described in `Montauk Charter Appendix - Discovery and Roth Overlay.md`.
