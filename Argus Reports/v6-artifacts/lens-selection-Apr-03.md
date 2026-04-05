# Lens Selection — Apr-03

## Selected Lenses for This Run

| # | Lens | Rationale |
|---|------|-----------|
| 1 | Architecture | Always included. Critical for a dual-language (Pine Script + Python) system with backtest engine parity requirements, active/archive file organization, and script-to-TradingView deployment pipeline. |
| 2 | Risk | Always included. A leveraged ETF trading strategy (3x TECL) has inherent financial risk. Code-level risks include no tests, no CI/CD, single-developer bus factor, and Python-Pine parity drift. |
| 3 | Data-Integrity | Primary domain lens. The entire project revolves around financial calculations: regime scoring, walk-forward validation, bull/bear cycle detection, CAGR/MaxDD computation, and backtesting engine fidelity. Any numerical error propagates directly into real trading decisions. CSV data ingestion (Yahoo Finance + merged CSV) adds another data integrity surface. |
| 4 | Vision-Drift | The project has a Montauk Charter (reference/Montauk Charter.md) that defines scope, coding rules, feature acceptance criteria, evaluation metrics, and response format. This is functionally equivalent to a spirit-guide for drift detection purposes. CLAUDE.md also encodes detailed architectural intent. Drift between documented intent and actual implementation is a meaningful risk vector. |
| 5 | Velocity | Borderline on commit count (27), but all commits are within a single month of active development. The project is in a rapid iteration phase (strategy versions 1.0 through 8.2.1, active /spike optimization loops, evolve results dated today). Velocity analysis will reveal development patterns, churn hotspots, and whether the archive-heavy workflow is creating drag. |

## Lenses Evaluated but Not Selected

- **UX-Quality** -- No frontend UI. TradingView is the rendering layer; this project only produces Pine Script text files pasted into an external platform. No user-facing interface to audit.
- **Security** -- No authentication, no API keys exposed in code (Yahoo Finance is public), no payment flows, no public endpoints. The Python scripts run locally. Minimal attack surface.
- **Observability** -- Not a deployed service. Strategies run inside TradingView's sandbox. Python scripts are local CLI tools with JSON output parsing. No logs, metrics, or alerting to evaluate.
- **API-Surface** -- No library, SDK, or public API. The Python CLI tools use a simple `###JSON###` convention for machine parsing, but this is internal tooling, not an API contract.
- **Dependency-Health** -- Only 3 Python dependencies (pandas, numpy, requests) per requirements.txt. Pine Script has zero external dependencies. The dependency surface is too small to warrant a dedicated lens.

## Rationale

Project Montauk is a solo-developer quantitative trading system where correctness of financial calculations is the highest-stakes concern. The selected lenses reflect this priority: Architecture and Risk provide universal coverage, Data-Integrity targets the core domain risk (numerical accuracy in backtesting, regime detection, and parameter optimization), Vision-Drift catches divergence from the Charter's documented guardrails, and Velocity surfaces development health patterns in what is clearly a rapid-iteration phase. The excluded lenses all target concerns (UI, auth, production infra, public APIs, dependency management) that simply do not apply to a local Pine Script + Python strategy development workflow.
