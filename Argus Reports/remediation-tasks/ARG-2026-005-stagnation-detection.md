# Task: Fix stagnation detection -- write _last_improve on improvement
**Source**: Argus ARG-2026-005
**Severity**: high
**Confidence**: 90%
**Effort**: 10 minutes

## Problem
`evolve.py` reads `_last_improve` at line 234 to calculate stagnation but never writes to it anywhere. The attribute defaults to an empty dict, so `stag` always equals the current generation number. At generation 30, mutation rate unconditionally escalates to 0.30; at generation 80, to 0.50. Any optimizer run longer than 19 generations (the only run so far) will have its evolutionary search corrupted by runaway mutation rates regardless of actual fitness improvement.

## Acceptance Criteria
- [ ] `evolve._last_improve` is initialized as an empty dict at module level or in the optimizer entry point
- [ ] When a generation produces a new best fitness for a strategy, `_last_improve[strat_name]` is set to the current generation number
- [ ] A 50-generation test run shows mutation rate stays at 0.15 when fitness improves continuously
- [ ] A 50-generation test run shows mutation rate escalates only when fitness actually stagnates for 30+ generations

## Files to Modify
- `scripts/evolve.py` — ~line 234: add write logic when new best is found; initialize `_last_improve = {}` at appropriate scope

## Dependencies
- None
