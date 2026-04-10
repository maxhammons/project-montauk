# Project Montauk Spirit Guide

**North star**: Project Montauk is a TECL strategy factory: discover many long-only TECL strategies, validate them hard against overfitting, and generate Pine for the best PASS winner.

This folder is the source of truth for what the project is trying to become and how work should be evaluated against that goal.

The spirit-guide defines mission, guardrails, and stable operating rules. Exact thresholds, scoring formulas, and fast-moving validation mechanics live in the scripts.

## Read This Folder In Order

1. **`Montauk Charter.md`**
   The project mission, guardrails, and success definition.

2. **`Montauk Charter Appendix - Discovery and Roth Overlay.md`**
   Approved extensions around the core charter: the discovery-stage marker prior and the Roth deployment overlay.

3. **`PIPELINE.md`**
   The canonical workflow: discover -> validate -> promote -> generate Pine -> manually review in TradingView.

4. **`VALIDATION-PHILOSOPHY.md`**
   Why raw optimizer winners are not truth and what must happen before a strategy is considered real.

5. **`PROJECT-STATUS.md`**
   What is already true in the codebase today, what is partially true, and what still needs to be built.

## Non-Negotiable Rules

- A raw optimizer winner is **not** a winner.
- Only a fully validated **PASS** result is allowed to become project memory.
- The leaderboard is for validated PASS entries, not raw backtest excitement.
- A promotable winner must end in a deployable Pine artifact.
- Discovery may use soft priors, but validation and promotion stay signal-honest and PASS-only.
- Roth cashflow logic is an account overlay, not the identity of the core strategy.
- `montauk_821` is the baseline reference strategy, not the entire mission of the project.

## One-Sentence Operating Model

Python does the search and validation. Pine Script is the execution artifact. TradingView is the final manual review and deployment surface.
