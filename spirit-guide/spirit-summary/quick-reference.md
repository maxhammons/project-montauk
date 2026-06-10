# Quick Reference — Project Montauk

> One-page sanity check. If your intended change conflicts with anything here, stop and reconcile first.

## Non-negotiables
- **Gold certified = fit to trade, beats B&H, full confidence of the system** (Max, 2026-06-09). Operationalized: Layer-1 correctness verified by *executed* checks; beats B&H shares in full, real, AND modern eras; composite ≥ 0.70 across every honest anti-overfit defense (measured-N_eff deflation, PBO, true OOS walk-forward, execution realism, event dependence); artifact bundle verified on disk; and — the part that makes "full confidence" honest — continuously falsified by live forward evidence with automatic demotion (`ops/live_holdout.py`).
- The leaderboard IS a certification. Nothing enters except Gold. Fewer rows is correct behavior, never failure.
- Headline performance claims are real-era / modern-era share multiples. Full-history (synthetic-inclusive) numbers are diagnostic-only (deep-validation ruling, 2026-06-09).
- TECL-only, long-only, single position, ≤5 trades/yr, bar-close signals, manual execution. Never punish low trade frequency.
- Exactly four pipeline phases (search → validate → certify → visualize); scripts live in their named subfolders; no orphan scripts.

## North Star
Accumulate more TECL shares than buy-and-hold by avoiding major drawdowns and re-entering after corrections. Confidence, not certainty: scores not verdicts; swap strategies as regimes shift; live evidence outranks backtests.

## Known Sensitivities
- Family concentration: a board of variants is one idea, not diversity (hard cap: 4 rows/strategy since 2026-06-09).
- Stored metrics go stale with every data refresh — `certify/verify_board_reproducibility.py` is the check; re-certify rather than trust stamps.
- The COVID window carries much of the modern-era edge for current strategies (event_dependence sub-score watches this).

## Vocabulary
- **Montauk Score** — the single headline score (Conviction^0.55 × Performance^0.30 × Durability^0.15); ranks the Gold set; top row = active strategy.
- **Gold Status** — the only admission ticket to the leaderboard (see Non-negotiables).
- **share_multiple** — terminal share-count ratio vs B&H; the primary optimization target (>1.0 required).
- **Spike / Montauk Engine** — the skill entrypoint / the optimizer+validator+artifact-emitter it drives.
