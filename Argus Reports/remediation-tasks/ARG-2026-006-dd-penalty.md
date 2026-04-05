# Task: Replace linear DD penalty with exponential penalty in fitness function
**Source**: Argus ARG-2026-006
**Severity**: high
**Confidence**: 78%
**Effort**: 5 minutes

## Problem
The fitness function in evolve.py uses a linear drawdown penalty: `1 - DD/200`. A strategy with 75% max drawdown receives only a 0.625x penalty, which is far too lenient for a 3x leveraged ETF where 75% DD requires a 301% gain to recover. This allows catastrophic-drawdown strategies to win the optimizer simply by having high raw returns, defeating the purpose of risk-adjusted ranking.

## Acceptance Criteria
- [ ] Fitness DD penalty changed to exponential: `exp(-2.0 * (DD/100)^2)` or equivalent
- [ ] A strategy with 75% DD receives approximately 0.325x penalty (not 0.625x)
- [ ] A strategy with 50% DD receives approximately 0.607x penalty
- [ ] A strategy with 25% DD receives approximately 0.882x penalty
- [ ] The coefficient (-2.0) is extracted as a named constant for future tuning

## Files to Modify
- `scripts/evolve.py` — ~line 62: replace linear penalty formula with exponential

## Dependencies
- None (but should be applied before ARG-2026-002 revalidation run)
