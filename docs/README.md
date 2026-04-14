# Project Montauk Docs

**North star**: Discover long-only TECL strategies that accumulate more shares than buy-and-hold, validate them at the tier appropriate to how they were selected, and generate Pine for the best PASS winner.

## Read Order

1. **[charter.md](charter.md)** — Project mission, guardrails, and success definition. Defines share-count multiplier as the primary metric and the marker chart as the north star.

2. **[charter-appendix.md](charter-appendix.md)** — Approved extensions: the marker-aligned discovery north star and the Roth deployment overlay.

3. **[pipeline.md](pipeline.md)** — The canonical workflow: hypothesize/discover -> route to tier -> validate -> promote -> generate Pine -> manually review in TradingView.

4. **[validation-philosophy.md](validation-philosophy.md)** — Why validation difficulty must match selection bias. Defines the T0/T1/T2 tier framework and the strict canonical parameter set for T0.

5. **[project-status.md](project-status.md)** — What is already true in the codebase today, what is partially true, and what still needs to be built.

6. **[design-guide.md](design-guide.md)** — **Read before authoring any new T0 hypothesis strategy.** What has worked, what has failed (and why), with a pre-flight checklist.

## Other Docs

- **[validation-thresholds.md](validation-thresholds.md)** — Threshold definitions for every validation gate (must stay in sync with `scripts/validation/`)
- **[plan.md](plan.md)** — Marker prior + Roth overlay implementation plan
- **[research/](research/)** — Market research, optimization roadmap, academic papers
- **[pine-reference/](pine-reference/)** — Pine Script v6 language documentation

## Operating Model

Python does the search and tier-routed validation. Pine Script is the execution artifact. TradingView is the final manual review and deployment surface.
