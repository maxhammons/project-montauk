# Project Montauk Charter

**Canonical summary**: A long-only, single-position EMA-trend system for TECL that captures multi-month bull legs and exits swiftly on regime change using a small, prioritized exit stack and optional filters to avoid chop and hold through benign consolidations.

---

## Rationale and Design

### Instrument scope
Target: Direxion Technology Bull 3× (TECL). Objective: capture large technology bull trends and sidestep major bear phases. Single symbol, single position, no pyramiding. One `"Long"` order id; only enter when flat.

### Core entry thesis
- **Momentum alignment**: buy only when `emaShort > emaMed`. Selects upside phases while ignoring minor countertrends.
- **Trend regime filter**: require the 70-EMA slope to be positive over a 10-bar lookback (`trendSlope > minTrendSlope`). Avoids buying during macro downtrends or flat regimes. Default `minTrendSlope = 0.0`.

### Exit stack and priorities
1. **Primary structural exit**: short EMA crosses under long EMA, with buffer and confirmation bars to prevent one-bar fake-outs.
2. **Shock exit**: ATR stop if price drops more than `atrMultiplier × ATR(period)` from prior close. The crash-catcher.
3. **Fast momentum exit**: quick EMA percent change over window exceeds a negative threshold. Trims tops and avoids drawn-out rollovers.
4. **Optional**: Sideways filter (Donchian range) and TEMA gates suppress bad entries in flat regimes.

### Parameter philosophy
Defaults are deliberately coarse (15/30/500 EMAs, 70-EMA trend slope, ATR 40×3.0) to capture regime shifts, not micro-noise. Use as few tunables as practical. Any change must improve out-of-sample regime handling — not just backtest equity.

### Known trade-offs
- The quick EMA exit uses price units; scaling can shift as TECL's nominal level changes. Consider normalizing (slope / price or ATR) only if it preserves current behavior across price levels.
- Sideways suppression of exits can defer a necessary sell if a sideways window precedes a breakdown. Keep ATR exit enabled as a backstop.
- TECL is 3× daily-reset — expect volatility drag in prolonged chop. The system's job is to maximize time in strong trends and minimize chop exposure.

### Validation windows
Backtests should cover: 2020 melt-up, 2021–2022 tech bear, and subsequent rebounds. The system should stay out or exit early during the bear and re-engage quickly after. These are the primary stress tests.

---

## 1. Scope

- **Symbol**: TECL only
- **Direction**: Long-only
- **Position**: Single open position, all-in/all-out
- **No**: pyramiding, partials, shorts
- **Time horizon**: Multi-month to multi-year trends — no day trading features

---

## 2. Strategy Identity

**Core entry**: `emaShort > emaMed` AND trend EMA slope > threshold. Do not propose oscillators or countertrend buys as primary logic.

**Core exits (priority stack)**:
1. Short-under-Long EMA with buffer and N confirmation bars
2. ATR shock exit
3. Quick-EMA negative momentum exit

**Optional**: Sideways filter and TEMA gates (available since v7.9).

---

## 3. Non-Goals

No multi-asset, no shorting, no options, no martingale, no grid, no optimization sweeps that add many inputs, no hyper-sensitive intraday rules.

---

## 4. Coding Rules

- **Pine Script v6 only**
- `process_orders_on_close=true`, `calc_on_every_tick=false`
- One strategy block. One entry id `"Long"`. Enter only if flat. Close via `strategy.close`.
- Preserve existing parameter names unless the Change Plan explicitly renames them.
- Keep inputs minimal. If proposing a new input, justify it with the failure mode it addresses and how it aligns with long-trend capture.
- No lookahead. No repainting indicators. Signals confirmed on bar close.
- When uncertain about Pine v6 syntax or built-ins, consult `reference/PineScript Version 6 Reference.txt`.

---

## 5. Feature Acceptance Checklist

Before proposing any new feature or change, verify all of the following:

- [ ] Does it improve regime detection or reduce chop without materially delaying re-entry after bears?
- [ ] Does it reduce max drawdown or left-tail risk more than it reduces bull-leg participation?
- [ ] Does it keep total trades/year low and avg hold time high?
- [ ] Can it be explained as a trend or risk control — not an unrelated signal?
- [ ] Does it avoid parameter bloat?

If any answer is no, the feature should be rejected or redesigned before proceeding.

---

## 6. Evaluation Metrics

Backtesting is done by the user in TradingView. When proposing changes, Claude should reason about expected impact on these metrics rather than reporting actual results:

| Metric | Notes |
|--------|-------|
| CAGR | Primary return measure |
| Max Drawdown | Primary risk measure |
| MAR (CAGR / MaxDD) | Risk-adjusted return |
| Exposure % | Time in market |
| Trades/year | Low is better; avoid churn |
| Avg days in trade | High is better; signals trend capture |
| Worst 10-day loss | Left-tail / crash risk |
| Exit reason breakdown | Count by exit type (structural / ATR / quick EMA) |

Win rate is secondary and should not be optimized directly. Backtest comparisons should change only one thing at a time.

---

## 7. Response Format for Code Changes

When proposing code changes, use this structure:

**Section A — Change Plan**: Bullet list of exactly what will change and why. State which failure mode it addresses.

**Section B — Code**: Full Pine Script v6 script only. No partial snippets unless specifically requested.

**Section C — Expected Impact**: Reasoned assessment of how the change is likely to affect the evaluation metrics above. Note any trade-offs.

---

## 8. Scope Guardrails

If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly:

> "Out of scope per Montauk charter. [One-sentence reason.] Trend-aligned alternative: [brief suggestion]."

Then offer one on-charter alternative if one exists.
