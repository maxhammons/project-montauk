# Task: Charter rewrite -- Part A (describe reality) and Part B (deployment gates)
**Source**: Argus ARG-2026-007
**Severity**: high
**Confidence**: 99%
**Effort**: 2-3 hours

## Problem
The Montauk Charter is 31 days stale and describes a single-strategy EMA-trend system. The actual codebase contains 7 strategy architectures including RSI mean-reversion, which Charter S2 and S8 explicitly ban. spike.md says "no restrictions," directly contradicting the Charter. The fitness metric has been silently changed twice (MAR -> Regime Score -> vs_bah_multiple) without Charter amendment. There are no formal deployment gates beyond manual copy-paste into TradingView.

## Acceptance Criteria
- [ ] Charter Part A accurately describes the multi-strategy evolutionary discovery platform
- [ ] Charter Part A lists all 7 strategy types currently in the codebase
- [ ] Charter Part B preserves and strengthens deployment gates: walk-forward validation required, max DD ceiling defined, minimum trade count, TradingView parity verification
- [ ] spike.md "no restrictions" language is reconciled with Charter scope
- [ ] The fitness metric used by the optimizer is explicitly documented in the Charter

## Files to Modify
- `reference/Montauk Charter.md` — Rewrite into two-part structure (Part A: scope, Part B: gates)
- `.claude/skills/spike.md` — Remove or qualify "no restrictions" to align with Charter Part B

## Dependencies
- ARG-2026-002 (wait for revalidation results to inform deployment gate thresholds)
