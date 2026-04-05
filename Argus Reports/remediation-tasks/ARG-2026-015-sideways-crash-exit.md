# Task: Allow ATR crash exit during sideways filter periods
**Source**: Argus ARG-2026-015
**Severity**: high
**Confidence**: 60%
**Effort**: 30 minutes

## Problem
backtest_engine.py line 804 blocks ALL exits during sideways market periods, including the ATR shock exit that the Charter describes as "the crash-catcher." If the market enters a narrow Donchian range (triggering sideways detection) and then flash-crashes, the strategy holds through the entire crash with no protective exit. The Charter explicitly warns about this scenario but the code does not implement a backstop.

## Acceptance Criteria
- [ ] ATR shock exit is exempt from sideways filter suppression in backtest_engine.py
- [ ] During sideways periods, ATR exit still fires if price falls below previous close minus ATR multiplier
- [ ] Other exits (EMA cross, Quick EMA, trailing stop) remain suppressed during sideways as intended
- [ ] A test scenario with sideways-then-crash price data confirms ATR exit fires correctly

## Files to Modify
- `scripts/backtest_engine.py` — ~line 804: modify sideways filter logic to exempt ATR shock exit

## Dependencies
- None
