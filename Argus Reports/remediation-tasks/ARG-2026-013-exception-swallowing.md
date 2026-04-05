# Task: Fix silent exception swallowing in evolve.py
**Source**: Argus ARG-2026-013
**Severity**: high
**Confidence**: 36%
**Effort**: 15 minutes

## Problem
evolve.py contains a bare `except Exception: return 0.0` block (~line 118) that silently swallows all errors during strategy evaluation. When a strategy crashes due to a bug (e.g., division by zero, index out of range, missing parameter), the optimizer treats it as a zero-fitness result rather than surfacing the error. This hides systematic failures and makes debugging nearly impossible. The optimizer could be silently discarding large portions of its population due to a single recurring bug.

## Acceptance Criteria
- [ ] Exceptions during strategy evaluation are logged with strategy name, parameters, and traceback
- [ ] A counter tracks consecutive exceptions per strategy type
- [ ] If consecutive exception count exceeds a threshold (e.g., 10), the optimizer halts with an error message
- [ ] Zero-fitness results from exceptions are distinguishable from legitimate zero-fitness evaluations in output logs

## Files to Modify
- `scripts/evolve.py` — ~line 118: replace bare except with logging + threshold halt logic

## Dependencies
- None
