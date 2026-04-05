# Task: Fix montauk_821 baseline EMA exit from 30-bar to 500-bar
**Source**: Argus ARG-2026-004
**Severity**: critical
**Confidence**: 99%
**Effort**: 15 minutes

## Problem
strategies.py montauk_821 uses `ema_m` (30-bar medium EMA) for its cross exit instead of a 500-bar long EMA matching the production Pine Script 8.2.1. This transforms the baseline from a trend-follower that holds for months into a jittery system where all exits fire as Quick EMA. Every fitness ratio, strategy ranking, and comparison in the optimizer is computed against this crippled baseline, making the 4.79x RSI Regime claim and all other relative metrics meaningless.

## Acceptance Criteria
- [ ] `strategies.py` montauk_821 computes a 500-bar long EMA via `ind.ema(p.get("long_ema", 500))`
- [ ] The cross exit compares `ema_s` against the new `ema_l` (500-bar), not `ema_m` (30-bar)
- [ ] `STRATEGY_PARAMS["montauk_821"]` includes `long_ema` as a fixed parameter (value 500, not sweepable)
- [ ] A short optimizer test run confirms the baseline fitness value has changed significantly from 0.4556

## Files to Modify
- `scripts/strategies.py` — ~line 34: add `ema_l = ind.ema(p.get("long_ema", 500))`; ~line 74: change `ema_m[i]` to `ema_l[i]` in exit condition; add `long_ema` to STRATEGY_PARAMS

## Dependencies
- None (this is the highest priority fix; everything else depends on it)
