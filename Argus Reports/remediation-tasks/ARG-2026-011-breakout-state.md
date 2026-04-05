# Task: Fix breakout state management -- reset peak_since_entry between trades
**Source**: Argus ARG-2026-011
**Severity**: medium
**Confidence**: 84%
**Effort**: 30 minutes

## Problem
In backtest_engine.py, `peak_since_entry` is not properly reset between trades, causing cross-trade state contamination. A high peak from a previous trade can carry forward into the next trade, affecting trailing stop calculations and potentially causing premature exits or missed exits depending on the price trajectory of the new position.

## Acceptance Criteria
- [ ] `peak_since_entry` is explicitly reset to the entry price (or current price) when a new position is opened
- [ ] A test with two consecutive trades confirms the second trade's trailing stop is not affected by the first trade's peak
- [ ] Backtest results are compared before and after fix to quantify the impact on trade count and returns

## Files to Modify
- `scripts/backtest_engine.py` — Reset `peak_since_entry` at position entry logic

## Dependencies
- None
