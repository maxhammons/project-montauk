# Task: Generalize Pine Script generation for non-8.2.1 strategies
**Source**: Argus ARG-2026-009
**Severity**: high
**Confidence**: 84%
**Effort**: 4-8 hours

## Problem
generate_pine.py's PARAM_MAP only contains entries for montauk_821 parameters. If the optimizer discovers a winning RSI Regime or other non-8.2.1 strategy, there is no automated path to convert it to deployable Pine Script. Manual translation has already introduced at least one boundary bug. This blocks the entire deployment pipeline for any strategy the optimizer was specifically built to discover.

## Acceptance Criteria
- [ ] PARAM_MAP or equivalent supports RSI Regime strategy parameters
- [ ] PARAM_MAP or equivalent supports at least the top 3 strategy types by optimizer usage
- [ ] A test generates valid Pine Script from a known RSI Regime config
- [ ] Generated Pine Script compiles without errors when pasted into TradingView Pine Editor
- [ ] Parameter names in generated Pine match the expected TradingView input names

## Files to Modify
- `scripts/generate_pine.py` — Extend PARAM_MAP with entries for additional strategy types; add strategy-specific Pine templates

## Dependencies
- ARG-2026-001 (engine bridge should inform the parameter naming convention)
