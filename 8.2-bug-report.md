# Project Montauk 8.2 — Bug Audit Report

**Date**: 2026-03-04
**Audited file**: `src/strategy/active/Project Montauk 8.2.txt`
**Reference**: `src/strategy/active/Project Montauk 8.1.txt` (baseline)

---

## Bug 1 — CRITICAL: EMA Cross Exit never fires with default settings

**Lines**: 157–161

### Code

```pine
rawSell     = ta.crossunder(emaShort, emaLong)
bufferOk    = emaShort < emaLong * (1 - sellBufferPct / 100)
allBelow    = ta.lowest(emaShort < emaLong ? 1 : 0, sellConfirmBars) == 1
confirmSell = not enableSellConfirm or allBelow
isCrossExit = rawSell and bufferOk and confirmSell
```

### Problem

`rawSell` (`ta.crossunder`) is `true` only on the single bar where `emaShort` crosses below `emaLong`. `allBelow` uses `ta.lowest(..., sellConfirmBars)`, which requires **every bar in the window** (including the prior bar) to have `emaShort < emaLong`. These two conditions are mutually exclusive when `sellConfirmBars >= 2`:

| Bar | `rawSell` | `allBelow` (N=2) | `isCrossExit` |
|-----|-----------|------------------|---------------|
| Crossunder bar | `true` | `false` (prior bar was still above) | `false` |
| All subsequent bars | `false` | potentially `true` | `false` |

With default settings (`enableSellConfirm=true`, `sellConfirmBars=2`), **the EMA Cross exit never fires**. The strategy silently falls back to only ATR and Quick EMA exits. This bug is present in 8.1 and was inherited by 8.2.

### Fix

Remove `rawSell` from `isCrossExit`. The `allBelow` check already implies a crossunder occurred within the confirmation window:

```pine
isCrossExit = bufferOk and confirmSell
```

This fires on the first bar where the buffer and N-bar confirmation are both satisfied — which is the correct semantics for "EMA cross with confirmation."

---

## Bug 2 — MINOR: `exitReason` overwritten to "Other" on every in-position bar

**Lines**: 206–218

### Code

```pine
var string exitReason = na
if strategy.position_size > 0
    if isCrossExit
        exitReason := "EMA Cross"
    else if isAtrExit
        exitReason := "ATR Exit"
    else if isQuickExit
        exitReason := "Quick EMA"
    else if isTrailExit
        exitReason := "Trail Stop"
    else if isTemaExit
        exitReason := "TEMA Slope"
    else
        exitReason := "Other"    // ← fires on every non-exit bar
```

### Problem

The `else` branch executes on every bar while in a position where no exit condition is firing — which is the vast majority of bars. `exitReason` is continuously overwritten to `"Other"`.

This is **functionally harmless**: `exitReason` is only used inside the `if exitCond` label block (line 233), and `exitCond` requires one of the five specific exit flags to be true. So a label with text `"Other"` can never actually appear. However, the logic is misleading and the `else` branch serves no purpose.

### Fix

Remove the `else` branch, or restructure so `exitReason` is only assigned when `exitCond` is true.

---

## No Other Bugs Found

The following 8.2-new features were reviewed and are correct:

- **Trailing Peak Stop** (Group 10): Peak initializes cleanly on the first in-position bar and ratchets upward. Resets to `na` when flat so each trade starts fresh.
- **TEMA Slope Exit** (Group 11): Uses `temaExitLookback` independently from the entry slope lookback (`tripleSlopeLookback`). Correctly decoupled.
- **Conviction Slider** (Group 9): `_tanh` implementation is correct. Slider index mapping covers columns 0–9 (danger) and 11–20 (safe) with column 10 as the gap separator. Gradient color math is correct. Driver label tracks the weakest gate accurately.
- **`allowExit` sideways suppression**: Consistent with 8.1 behavior — all exits are suppressed during a sideways window when the filter is enabled. This is a documented design choice, not a bug.

---

## Summary

| # | Severity | Description | Inherited from 8.1? |
|---|----------|-------------|---------------------|
| 1 | Critical | EMA Cross Exit never fires (`rawSell` and `allBelow` mutually exclusive for `sellConfirmBars >= 2`) | Yes |
| 2 | Minor | `exitReason` set to `"Other"` on every non-exit in-position bar | Yes |

Bug 1 is the only issue that affects trade behavior. It should be fixed before 8.2 is used in production.
