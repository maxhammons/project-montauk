# Project Montauk Charter

**Canonical summary**: A long-only, single-position EMA-trend system for TECL that captures multi-month bull legs and exits swiftly on regime change using a small, prioritized exit stack and optional filters to avoid chop and hold through benign consolidations.

---

## Rationale and Design

### Instrument scope
Target: Direxion Technology Bull 3× (TECL). Objective: capture large technology bull trends and sidestep major bear phases. Single symbol, single position, no pyramiding. One `"Long"` order id.

### Known trade-offs
- The quick EMA exit uses price units; scaling can shift as TECL's nominal level changes. Consider normalizing (slope / price or ATR) only if it preserves current behavior across price levels.
- Sideways suppression of exits can defer a necessary sell if a sideways window precedes a breakdown. Keep ATR exit enabled as a backstop.
- TECL is 3× daily-reset — expect volatility drag in prolonged chop. The system's job is to maximize time in strong trends and minimize chop exposure.

### Validation windows
Backtests should cover: 2008 fallout, 2020 melt-up, 2021–2022 tech bear, and subsequent rebounds. The system should stay out or exit early during the bear and re-engage quickly after. These are the primary stress tests.

---

## 1. Scope

- **Symbol**: TECL only
- **Direction**: Long-only
- **Position**: Single open position, all-in/all-out
- **No**: pyramiding, partials, shorts
- **Time horizon**: Multi-month to multi-year trends — no day trading features

---

## 2. Non-Goals

No multi-asset, no shorting, no options, no martingale, no margin, no grid, no optimization sweeps that add many inputs, no hyper-sensitive intraday rules.

---

## 3. Coding Rules

- **Pine Script v6 only**
- `process_orders_on_close=true`, `calc_on_every_tick=false`
- One strategy block. One entry id `"Long"`. Close via `strategy.close`.
- Preserve existing parameter names unless the Change Plan explicitly renames them.
- No lookahead. No repainting indicators. Signals confirmed on bar close.
- When uncertain about Pine v6 syntax or built-ins, consult `reference/PineScript Version 6 Reference.txt`.

---

## 4. Evaluation Metrics

Backtesting is done by the user in TradingView. When proposing changes, Claude should reason about expected impact on these metrics rather than reporting actual results:

| Metric | Notes |
|--------|-------|
| Versus Buy and Hold | Returns of both buy an hold and the strategy from time of trade 1 in the strategy |
| CAGR | Primary return measure |
| Max Drawdown | Primary risk measure |
| MAR (CAGR / MaxDD) | Risk-adjusted return |
| Exposure % | Time in market |
| Trades/year | Low is better; shoot for 3 at most. Avoid churn |
| Avg days in trade | High is better; signals trend capture |
| Worst 10-day loss | Left-tail / crash risk |
| Exit reason breakdown | Count by exit type (structural / ATR / quick EMA) |

Win rate is secondary and should not be optimized directly. Backtest comparisons should change only one thing at a time.

---


## 5. Scope Guardrails

If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly:

> "Out of scope per Montauk charter. [One-sentence reason.] Trend-aligned alternative: [brief suggestion]."

Then offer one on-charter alternative if one exists.
