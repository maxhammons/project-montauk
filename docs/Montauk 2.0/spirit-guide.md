# Montauk 2.0 — Spirit Guide

*Read this before the master plan. This is the "why." The plan is the "what" and "how."*

---

## The problem

Today the project lives in two worlds:

- **Python** is where discovery and validation happen. Evolutionary optimizer, tier-routed validation gates, leaderboard. This is the brain.
- **TradingView / Pine Script** is where the "real" backtest gets run and where the strategy ultimately executes. This is the eye.

Every strategy has to cross the bridge between them. That bridge is `pine_generator.py` + `parity.py` + a manual paste-into-TradingView step. **The bridge is broken.** Python results don't match TradingView results exactly. Parity checks are brittle. Time spent chasing divergence produces zero edge. Decisions stall because we're never quite sure which engine is right.

Worse: the bridge is load-bearing in the wrong direction. TradingView serves as a safety net — *"if the Python backtest is wrong, at least TV will show us."* That framing means the Python engine has never had to be fully trusted on its own. Every accuracy gap (slippage, commission, exit semantics, synthetic data quality) got waved off as "close enough; TV is the real test." That's no longer acceptable.

---

## The decision

Remove TradingView and Pine Script from the pipeline entirely. Python becomes the single source of truth. Manual execution happens in a brokerage based on Python's daily risk_on/risk_off signal. No translation layer. No parity checks. No second opinion from a platform we're paying for attention we don't have.

This only works if three things become true:

1. **The engine is trustworthy on its own.** Unit tests for every indicator. Golden reference trades as a regression net. A dev-only shadow comparator (a second OSS engine like `backtesting.py`) as a cheap outside opinion. No more "close enough."
2. **The data is certifiable.** Yahoo Finance is cross-checked against Stooq. Synthetic TECL/TQQQ pre-IPO data is deterministically rebuildable from source (XLK/QQQ × leverage − expense). Every CSV has provenance columns and a checksummed manifest. We can answer "where did this bar come from?" for every bar.
3. **We can see what strategies are doing.** A native HTML dashboard replaces TV's chart UI. Every leaderboard strategy is one click away. Trade markers, equity curve, drawdown underwater pane, synthetic-period shading, validation gate status — all visible without leaving the browser. No log-in, no network call, no account.

---

## What "done" looks like

- `pytest tests/` green. Every indicator, every exit condition, every slippage/commission path has a test with known-good expected values.
- `python scripts/data_rebuild_synthetic.py --verify` produces bit-identical output to the stored CSVs.
- `python scripts/data_quality.py` all PASS, including Stooq cross-check <0.01% on real data.
- `python scripts/spike_runner.py --hours 0.5 --quick` runs clean, emits standardized JSON artifacts per run, no Pine references anywhere.
- `open viz/montauk-viz.html` shows the full leaderboard with click-to-swap strategies, trade overlays, drawdown, synthetic shading, recent-period scorecards, and a green "manifest verified" provenance badge.
- `tree` shows no `src/`, no `pine_generator.py`, no `deploy.py`, no `parity.py`, no `docs/pine-reference/`. Just Python, tests, data with manifests, and a viz.

When every one of those is true, the bridge is gone and the pipeline is one thing end-to-end.

---

## Governing principles (the feel)

- **Trust through reproducibility, not through external validation.** If we need TV to tell us we're right, we don't understand our own engine. Tests, golden trades, and checksums replace the platform.
- **Provenance before performance.** Every CSV row answers "where did you come from, and how do I know you haven't been tampered with." No metric is trustworthy if the data under it is suspect.
- **Diagnostic visibility, not fitness gymnastics.** When we want to know "is this strategy working in recent years," we show recent-period scorecards in the dashboard. We do not bake recency into the canonical fitness formula — that way lies hidden bias.
- **One source of truth.** Two engines that "should" agree is a bug waiting to happen. One dashboard that reads one set of JSON artifacts. One signal per day. One place to look.
- **Manual execution is fine.** We are not building broker automation. The output is a daily risk_on/risk_off decision a human reads and acts on.

---

## Non-goals

Things we are deliberately **not** doing in this initiative:

- Wiring a broker API (Alpaca, IBKR). Manual execution is the surface for now.
- Adopting an OSS backtest library as the production engine. We use one as a **dev-only** shadow comparator for certification tests. Our engine remains canonical.
- Rewriting strategies. The strategy logic is fine; we are removing the translation layer around it.
- Adding recency-weighted fitness. Recency appears only as a diagnostic panel in the dashboard.
- Building a server. The dashboard is a single self-contained HTML file.

---

## How to use this document

If you are a model picking up this work, read this file first. It tells you the intent — the shape of what we're trying to become. Then read [Montauk 2.0 - Master Plan.md](./Montauk%202.0%20-%20Master%20Plan.md) for the phased execution steps.

If a task in the master plan seems to conflict with the principles in this spirit guide, trust the spirit guide and flag the conflict. The plan is instructions; this is the compass.
