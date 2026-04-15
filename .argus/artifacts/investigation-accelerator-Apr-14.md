# Accelerator Investigation - Project Montauk (Apr-14)

## 5 Observations

1. **Deploy Complexity is a Hard Ceiling:** The deployment pipeline is entirely manual. `scripts/deploy.py` generates a `patched_strategy.txt` file, which a human must manually copy and paste into the TradingView Pine Editor UI. This prevents true continuous deployment and introduces significant human-error risk at the final mile.
2. **Missing Unit Test Safety Net:** While the project has an extensive, sophisticated validation pipeline for trading strategies (Walk-Forward, Monte Carlo, Cross-Asset), it lacks a basic, fast-running unit test suite (like `pytest`) for the Python backtesting engine itself. A new engineer modifying core logic has no immediate, low-latency way to verify they haven't broken basic code execution.
3. **Fear-Inducing Metric Divergence:** There is a documented contradiction between the project's Charter (which dictates "share-count multiplier vs B&H" as the sole primary metric) and the actual codebase (which still uses dollar `vs_bah` and a `trade_scale` penalty). This ambiguity will paralyze a new engineer, as they won't know whether to trust the documentation or the implementation.
4. **AI-Coupled Developer Experience:** The project heavily relies on Claude Code skills (`/spike`, `/spike-focus`) for its core workflows. While powerful, this obscures the raw developer experience for a human engineer onboarding without these specific AI tools. The "how to run" path for a human is buried under AI wrappers.
5. **No Rollback Mechanism for Production:** Because the deployment is a manual copy-paste into a UI, there is no automated "one-click rollback" if a strategy fails in production. Reverting requires finding the old `.txt` file in the `archive/` folder and manually copy-pasting it back into TradingView.

## What I investigated and ruled out

- **I investigated the testing infrastructure** and ruled out the idea that the project is "untested." It is heavily tested from a data-science and strategy-validation perspective (`scripts/validation/`), but it lacks the engineering-level unit tests required for fearless code refactoring.
- **I investigated the deployment scripts (`scripts/deploy.py`)** and ruled out the possibility of automated CI/CD to production. The platform constraint (TradingView) forces a manual GUI step, meaning true zero-touch velocity is currently impossible.
- **I investigated the onboarding path (`CLAUDE.md`)** and ruled out that a new engineer could just "jump in and code." The heavy reliance on AI skills and the complex tier-routed validation mean the onboarding curve is actually quite steep for a human.

## What I would need to see to change my mind

- **To change my mind on Deploy Complexity:** I would need to see an automated way to push Pine Script directly to TradingView (via an unofficial API, web scraping automation, or a supported webhook), entirely removing the human copy-paste step.
- **To change my mind on Code Safety:** I would need to see a `tests/` directory with a fast `pytest` suite that stubs out the data layer and asserts the pure logic of `backtest_engine.py` and `pine_generator.py` in under 2 seconds.
- **To change my mind on Ambiguity/Fear:** I would need to see a PR that aligns the Python fitness functions with the Charter's "share-count multiplier" mandate, explicitly resolving the documented discrepancy.