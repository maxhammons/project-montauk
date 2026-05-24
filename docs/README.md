# Project Montauk Docs

**North star**: Discover long-only TECL strategies that accumulate more shares than buy-and-hold, validate them at the tier appropriate to how they were selected, and emit a `backtest_certified` signal bundle + native HTML viewer for the best PASS winner.

## Read Order

1. **[charter.md](charter.md)** — Project mission, guardrails, and success definition. Defines share-count multiplier as the primary metric and the marker chart as the north star.

2. **[charter-appendix.md](charter-appendix.md)** — Approved extensions: the marker-aligned discovery north star and the Roth deployment overlay.

3. **[pipeline.md](pipeline.md)** — The canonical workflow: hypothesize/discover -> route to tier -> validate -> certify signal bundle -> native HTML viewer -> manually execute from daily risk_on/risk_off signal.

4. **[app-charter.md](app-charter.md)** — Product charter for the standalone macOS app and background operations surface.

5. **[validation-philosophy.md](validation-philosophy.md)** — Why validation difficulty must match selection bias. Defines the T0/T1/T2 tier framework and the strict canonical parameter set for T0.

6. **[project-status.md](project-status.md)** — What is already true in the codebase today, what is partially true, and what still needs to be built.

7. **[design-guide.md](design-guide.md)** — **Read before authoring any new T0 hypothesis strategy.** What has worked, what has failed (and why), with a pre-flight checklist.

## Other Docs

- **[validation-thresholds.md](validation-thresholds.md)** — Threshold definitions for every validation gate (must stay in sync with `scripts/validation/`)
- **[*NEXT/](*NEXT/)** — Active plans, outstanding work, and near-term design notes. Fully executed plans move to `*NEXT/archive/`.
- **[*NEXT/2026-05-12-mac-app-implementation-plan.md](*NEXT/2026-05-12-mac-app-implementation-plan.md)** — Active mixed-status build plan for the macOS app, scheduler, notifications, research queue, and strategy ideation loop.
- **[*NEXT/2026-04-07-validation-pipeline-roadmap.md](*NEXT/2026-04-07-validation-pipeline-roadmap.md)** — Active validation-pipeline roadmap with remaining research hardening work.
- **[*NEXT/archive/2026-04-13-marker-roth-overlay-plan.md](*NEXT/archive/2026-04-13-marker-roth-overlay-plan.md)** — Archived marker-prior + Roth overlay implementation plan.
- **[Montauk 2.0/](Montauk%202.0/)** — Historical record of the Pine/TradingView excision project. Executed Montauk 2.0 plan docs are archived under `*NEXT/archive/Montauk 2.0/`.
- **[research/](research/)** — Market research, academic papers, and synthesis docs.

## Operating Model

Python does the search, tier-routed validation, and signal emission. The `backtest_certified` artifact bundle (trade ledger, signal series, equity curve, validation summary, dashboard data) is the execution contract. The native HTML viewer (`viz/montauk-viz.html`) is the visualization surface. Daily risk_on / risk_off output drives manual brokerage execution.
