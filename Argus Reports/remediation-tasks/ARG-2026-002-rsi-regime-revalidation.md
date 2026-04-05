# Task: Revalidate RSI Regime fitness after baseline correction
**Source**: Argus ARG-2026-002
**Severity**: critical
**Confidence**: 99%
**Effort**: 1-2 hours (mostly waiting for optimizer run)

## Problem
The RSI Regime strategy's 4.79x fitness claim is built on two compounding errors: (1) the montauk_821 baseline uses the wrong EMA exit, deflating the denominator, and (2) the evaluation is pure in-sample (36 seconds, 19 generations, 1,330 evaluations) with no walk-forward split. The 75.1% max drawdown on a 3x leveraged ETF requires a 301% gain to recover. The true relative performance is unknown until both the baseline and the fitness penalty are corrected.

## Acceptance Criteria
- [ ] Optimizer re-run completes with corrected baseline (ARG-2026-004 fix applied)
- [ ] Optimizer re-run completes with exponential DD penalty (ARG-2026-006 fix applied)
- [ ] New fitness ratios for all 7 strategies are documented
- [ ] RSI Regime's new ranking and fitness value are compared against the original 4.79x claim
- [ ] If RSI Regime still leads, its max drawdown and trade count are flagged for walk-forward follow-up

## Files to Modify
- No code changes -- this is a verification task after ARG-2026-004 and ARG-2026-006 are applied
- Document results in `remote/report-YYYY-MM-DD.md`

## Dependencies
- ARG-2026-004 (baseline EMA fix)
- ARG-2026-006 (DD penalty fix)
