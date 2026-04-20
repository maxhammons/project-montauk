# Project Montauk Docs

**North star**: Discover long-only TECL strategies that accumulate more shares than buy-and-hold, validate them at the tier appropriate to how they were selected, and emit a `backtest_certified` signal bundle + native HTML viewer for the best PASS winner.

## Read Order

1. **[charter.md](charter.md)** — Project mission, guardrails, and success definition. Defines share-count multiplier as the primary metric and the marker chart as the north star.

2. **[charter-appendix.md](charter-appendix.md)** — Approved extensions: the marker-aligned discovery north star and the Roth deployment overlay.

3. **[pipeline.md](pipeline.md)** — The canonical workflow: hypothesize/discover -> route to tier -> validate -> certify signal bundle -> native HTML viewer -> manually execute from daily risk_on/risk_off signal.

4. **[validation-philosophy.md](validation-philosophy.md)** — Why validation difficulty must match selection bias. Defines the T0/T1/T2 tier framework and the strict canonical parameter set for T0.

5. **[project-status.md](project-status.md)** — What is already true in the codebase today, what is partially true, and what still needs to be built.

6. **[design-guide.md](design-guide.md)** — **Read before authoring any new T0 hypothesis strategy.** What has worked, what has failed (and why), with a pre-flight checklist.

## Other Docs

- **[validation-thresholds.md](validation-thresholds.md)** — Threshold definitions for every validation gate (must stay in sync with `scripts/validation/`)
- **[plan.md](plan.md)** — Marker prior + Roth overlay implementation plan
- **[Montauk 2.0/](Montauk%202.0/)** — Historical record of the Pine/TradingView excision project (seven phases, spirit-guide, master plan)
- **[research/](research/)** — Market research, optimization roadmap, academic papers

## Operating Model

Python does the search, tier-routed validation, and signal emission. The `backtest_certified` artifact bundle (trade ledger, signal series, equity curve, validation summary, dashboard data) is the execution contract. The native HTML viewer (`viz/montauk-viz.html`) is the visualization surface. Daily risk_on / risk_off output drives manual brokerage execution.
