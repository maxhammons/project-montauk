## North Star Statement

This codebase is trying to become a trustworthy TECL decision factory: a system that can generate, stress-test, rank, and certify long-only TECL timing strategies, then hand a human operator a clean `risk_on` / `risk_off` contract plus a native HTML review surface for manual execution. The center of gravity has shifted away from one-off strategy tuning toward a governed pipeline where Spike is the search surface and the Montauk Engine is the evidence machine: data integrity, tier-routed validation, certification artifacts, and durable leaderboard memory. The productive tension is that some docs still describe a single PASS champion, while the newer validation model and leaderboard logic are pulling toward a confidence-ranked watchlist of deployable TECL strategies that can be re-scored as evidence changes.

---

## Momentum

**Actively evolving:** `scripts/search/` (`evolve.py`, `grid_search.py`, `safe_runner.py`, `focus_spike.py`), `scripts/validation/pipeline.py` and its scoring model, `scripts/certify/` (`full_sweep.py`, `recertify_leaderboard.py`), marker scoring in `scripts/strategies/markers.py`, the leaderboard/artifact contract under `spike/`, and the native viewer path in `viz/`. The hottest documentation surface is also strategic, not explanatory: `docs/project-status.md`, `docs/validation-philosophy.md`, `docs/validation-thresholds.md`, and `docs/pipeline.md` are being rewritten alongside the code.

**Settled:** the charter boundary is consistent across code and docs: TECL-only, long-only, single-position, bar-close, manual brokerage execution, with Python as the source of truth and the HTML viewer as presentation only. The trust stack around engine/data honesty also looks comparatively settled: golden regression, shadow comparison, data-quality checks, and standardized run artifacts are treated as non-negotiable infrastructure rather than experiments.

**Signals of strategic shift:** 2026-04-13 is the clearest inflection point, when the repo formalized tier routing, canonical parameter rules, grid-search-first discovery, and the Spike/Montauk Engine naming split. Around 2026-04-15, the project reframed itself around certification and Python-native trust after the Pine/TradingView excision. From 2026-04-19 through 2026-04-22, the center of effort moved again toward confidence scoring, leaderboard recertification, full-sweep tooling, and UI/organization work, which implies the team is now optimizing for an operational research system, not just a better backtest.

---

## Stage Assessment

**Stage:** Growth

This repo is beyond the toy or prototype phase: the architecture has named layers, the validation/certification pipeline is real, and recent commits are dominated by structural work rather than isolated experiments. But it is not mature yet; the semantics of promotion, marker usage, and leaderboard meaning are still changing quickly, and several top-level docs disagree in ways that only happen when a system is being actively redefined. The most useful review at this stage is one that clarifies trajectory and governance without freezing the pace of iteration.
