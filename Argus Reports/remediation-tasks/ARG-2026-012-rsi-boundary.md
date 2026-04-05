# Task: Fix RSI boundary condition -- change < to <= in strategies.py
**Source**: Argus ARG-2026-012
**Severity**: medium (bundled with Phase 0 for completeness)
**Confidence**: 60%
**Effort**: 2 minutes

## Problem
The RSI crossover logic in strategies.py uses strict less-than (`<`) instead of less-than-or-equal (`<=`) when comparing RSI against the entry/exit threshold. This means the Python backtester misses crossover signals when RSI lands exactly on the threshold value, causing a divergence from Pine Script's `ta.crossover`/`ta.crossunder` which use `<=`/`>=` semantics. While rare, this can silently alter trade counts and timing.

## Acceptance Criteria
- [ ] RSI comparison at ~line 133 in strategies.py uses `<=` instead of `<`
- [ ] A test confirms the change does not break existing strategy behavior for non-boundary RSI values
- [ ] Trade count for RSI Regime strategy is compared before and after the fix

## Files to Modify
- `scripts/strategies.py` — ~line 133: change `<` to `<=`

## Dependencies
- None
