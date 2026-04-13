# Project Montauk Spirit Guide

**North star**: Project Montauk is a TECL share-accumulation factory: discover long-only TECL strategies that match the hand-marked cycle shape, validate them at the tier appropriate to how they were selected, and generate Pine for the best PASS winner.

This folder is the source of truth for what the project is trying to become and how work should be evaluated against that goal.

The spirit-guide defines mission, guardrails, and stable operating rules. Exact thresholds, scoring formulas, and fast-moving validation mechanics live in the scripts.

## Read This Folder In Order

1. **`Montauk Charter.md`**
   The project mission, guardrails, and success definition. Defines share-count multiplier as the primary metric and the marker chart as the north star.

2. **`Montauk Charter Appendix - Discovery and Roth Overlay.md`**
   Approved extensions: the marker-aligned discovery north star (formalization) and the Roth deployment overlay.

3. **`PIPELINE.md`**
   The canonical workflow: hypothesize / discover -> route to tier -> validate -> promote -> generate Pine -> manually review in TradingView.

4. **`VALIDATION-PHILOSOPHY.md`**
   Why validation difficulty must match selection bias. Defines the T0 / T1 / T2 tier framework and the strict canonical parameter set for T0.

5. **`PROJECT-STATUS.md`**
   What is already true in the codebase today, what is partially true, and what still needs to be built.

## Non-Negotiable Rules

- A raw optimizer winner is **not** a winner.
- Every candidate is registered under a tier (T0 / T1 / T2) reflecting how it was selected.
- Only a fully validated **PASS** result at the candidate's tier is allowed to become project memory.
- The leaderboard is for validated PASS entries, tagged with their tier.
- A promotable winner must end in a deployable Pine artifact.
- The marker chart is the north star. Marker shape alignment is a first-class validation gate.
- Share-count multiplier vs B&H is the primary metric. Trade frequency is not punished.
- Roth cashflow logic is an account overlay, not the identity of the core strategy.
- `montauk_821` is the baseline reference strategy, not the entire mission of the project.

## Naming

Spike is the skill. Spike launches and runs the **Montauk Engine** (the optimizer + validator + Pine generator pipeline). Files and commands keep their existing names.

## One-Sentence Operating Model

Python does the search and tier-routed validation. Pine Script is the execution artifact. TradingView is the final manual review and deployment surface.
