# Task: Bridge validation.py to v4 strategy engine
**Source**: Argus ARG-2026-001 / ARG-2026-003
**Severity**: critical
**Confidence**: 99%
**Effort**: 2-4 hours

## Problem
The v4 optimizer (strategy_engine.py + evolve.py) and the validation framework (validation.py) are completely disconnected. validation.py imports from backtest_engine.py and expects StrategyParams dataclasses, while v4 uses plain dicts with different key names. There is no bridge function, adapter, or shared interface. Walk-forward validation is structurally impossible for any strategy discovered by the v4 optimizer.

## Acceptance Criteria
- [ ] A `validate_v4()` bridge function exists that translates v4 strategy dicts into a format validation.py can consume
- [ ] Parameter name mapping is correct (e.g., `short_ema` -> `short_ema_len`)
- [ ] At least one v4 strategy can be passed through walk-forward validation end-to-end
- [ ] The bridge function is importable from both evolve.py and standalone CLI usage

## Files to Modify
- `scripts/validation.py` — Add bridge function or adapter layer for v4 strategy dicts
- `scripts/evolve.py` — Add optional post-optimization validation call using the bridge

## Dependencies
- ARG-2026-004 (fix baseline EMA first so validation produces meaningful numbers)
