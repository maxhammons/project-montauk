# Craftsman Scratchpad

## Reading List (Pass 1 -> Pass 2)

Hypothesis 1: `promotion_ready`, `backtest_certified`, and leaderboard admission no longer mean the same thing across code and docs.
Files to read: `scripts/validation/pipeline.py`, `scripts/search/evolve.py`, `scripts/search/spike_runner.py`, `scripts/certify/certify_champion.py`, `scripts/certify/recertify_leaderboard.py`, `spike/leaderboard.json`, `docs/validation-philosophy.md`, `docs/pipeline.md`, `docs/project-status.md`, `CLAUDE.md`.
Expected signal: code admits leaderboard entries that are not `backtest_certified`; docs still describe leaderboard presence as certification-grade or PASS-only promotion.

Hypothesis 2: the repo still uses the word `gate` for checks that are now diagnostics, which is a naming lie.
Files to read: `scripts/validation/pipeline.py`, `docs/validation-thresholds.md`, `docs/project-status.md`, `viz/montauk-viz.html`.
Expected signal: marker and cross-asset checks are described as demoted/advisory while still surfaced as PASS/WARN/FAIL gate rows and discussed as if they enforce promotion.

Hypothesis 3: there are duplicate validation models in circulation, especially around `cross_asset`.
Files to read: `scripts/validation/pipeline.py`, `docs/validation-thresholds.md`, `docs/validation-philosophy.md`, `CLAUDE.md`.
Expected signal: code removes `cross_asset` from `composite_confidence`, while docs or operator docs still include it in effective weights or summary formulas.

Hypothesis 4: official status docs are teaching a plausible but wrong mental model of the current pipeline.
Files to read: `docs/project-status.md`, `docs/pipeline.md`, `docs/validation-philosophy.md`, `CLAUDE.md`.
Expected signal: claims like PASS-only promotion, marker hard-fail semantics, or `promotion_ready = backtest_certified AND PASS` survive after the code changed.

Priority:
1. Hypothesis 1
2. Hypothesis 4
3. Hypothesis 2
4. Hypothesis 3

Pass 2 expansions used: 0

## Pass 0 Signal Map

- Atlas scope: 1,073 files; active calibration hotspots are `scripts/validation/pipeline.py` and `spike/leaderboard.json`.
- Complexity hotspots relevant to this lens: `scripts/validation/pipeline.py` (1,304 lines), `scripts/search/evolve.py` (1,875), `scripts/search/spike_runner.py` (694), `scripts/validation/candidate.py` (579).
- Source/doc TODO scan found only one live semantic TODO in authored code: `scripts/validation/pipeline.py:1084` and its emitted skip reason at `1090`.
- The TODO is not cosmetic. It explicitly says Gate 2 still mixes result-quality and search-bias semantics and has not been split honestly yet.
- Term density is concentrated in the semantic boundary files:
- `pipeline.py`: `promotion_ready` x7, `backtest_certified` x6, `cross_asset` x18.
- `spike_runner.py`: `promotion_ready` x9, `backtest_certified` x8.
- `docs/pipeline.md`: `promotion_ready` x6, `backtest_certified` x8.
- `docs/project-status.md`: `backtest_certified` x4, `watchlist` x2, `PASS-only` x2.
- `docs/validation-thresholds.md`: `cross_asset` x5 despite one note saying it was removed from the composite.

## Pass 1 Shared Context Takeaways

- North star says the repo is becoming a trustworthy TECL decision factory, with tension between old PASS-champion rhetoric and newer confidence-ranked watchlist language.
- Prior run brief already flagged `composite_confidence` and threshold drift as open blockers.
- History context says April 21 was the semantics pivot: validation softened from vetoes toward advisory scoring.
- That means the key Craftsman question is not "did they soften validation?" but "did they rename the system honestly after softening it?"

## Pass 2 Files Read

- `scripts/validation/pipeline.py`
- `scripts/search/evolve.py`
- `scripts/search/spike_runner.py`
- `scripts/certify/recertify_leaderboard.py`
- `scripts/certify/certify_champion.py`
- `docs/validation-thresholds.md`
- `docs/validation-philosophy.md`
- `docs/project-status.md`
- `docs/pipeline.md`
- `CLAUDE.md`
- `viz/montauk-viz.html`
- `spike/leaderboard.json`
- `tests/test_regression.py`

## Working Notes

- `scripts/validation/pipeline.py:831-976` is the real contract, not the prose around it.
- Gate 7 says only Gate 1 hard-fails count as Layer 1 correctness in synthesis.
- Gate 7 initializes `artifact_completeness` as pending at `922-930`.
- Gate 7 sets `promotion_ready = verdict == "PASS"` at `973`.
- Gate 7 sets `backtest_certified = promotion_ready and all(checks)` at `974-976`.
- That means `backtest_certified` is not a pure correctness flag. It is a stricter post-PASS status.
- This directly conflicts with `docs/validation-philosophy.md:102`, which says `backtest_certified` is the correctness flag and `promotion_ready = backtest_certified AND confidence >= 0.70`.
- It also conflicts with `CLAUDE.md:267-268`, which repeats the same model.

- `scripts/search/spike_runner.py:96-168` only finalizes certification for champion targets after artifacts exist.
- It patches `artifact_completeness` to pass/fail and recomputes `backtest_certified`.
- It does not recompute `promotion_ready`; it preserves whatever Gate 7 already set.
- So the code model is:
- `promotion_ready` = validation-level admission.
- `backtest_certified` = champion/finalized artifact-backed admission.
- The docs frequently invert or conflate those.

- `scripts/search/evolve.py:191-235` explicitly excludes `artifact_completeness` from leaderboard eligibility.
- `_is_leaderboard_eligible` only requires `composite_confidence >= 0.60` plus four engine-level checks.
- That is a watchlist/admission model, not a certified-memory model.
- `scripts/search/evolve.py:328-335` still comments "promotion_ready + engine-certified," which is sloppy wording because the code is not requiring `backtest_certified`.

- Current persisted state confirms the code path, not the prose.
- `spike/leaderboard.json:431-482` shows a top entry with:
- `verdict: PASS`
- `promotion_ready: true`
- `backtest_certified: false`
- `composite_confidence: 0.7345`
- `artifact_completeness.passed: false`, `status: pending`
- This is not an edge case. A quick check of the current board found 20/20 entries with `promotion_ready: true` and `backtest_certified: false`.

- `viz/montauk-viz.html:1058-1179` is aligned with the watchlist model.
- The UI labels 0.70+ as `ADMITTED`, 0.60-0.69 as `WATCHLIST`, and separately displays certification badges.
- This is more honest than some docs because it visually separates admission from certification.
- But the same UI still renders validation as PASS/WARN/FAIL gate rows at `1220-1245`, which preserves old veto theater.

- `scripts/validation/pipeline.py:652-735` makes marker behavior explicit:
- marker thresholds are informational / diagnostic only.
- verdict is always `PASS`.
- critical warnings do not block verdict.
- This is not a gate in the ordinary meaning of gate.
- `docs/project-status.md:105-107` still says marker thresholds fail at gate level. That is flatly obsolete.

- `scripts/validation/pipeline.py:757-809` demotes cross-asset to warnings and score input.
- But `_geometric_composite` no longer weights `cross_asset`; it is commented out in `scripts/validation/pipeline.py:227-254`.
- Gate 7 still stores `cross_asset` in `sub_scores` at `915`, but the composite ignores it because the weights dict omits it.
- `docs/validation-thresholds.md:79` says `cross_asset` was removed from the composite.
- The same doc then gives `cross_asset` effective weights at `81-94` and still lists Gate 6 as a `cross_asset` sub-score source at `198-206`.
- `CLAUDE.md:248-268` also still includes `cross_asset (demoted) | 0.05 | all`.
- This is a duplicate model, not just stale wording.

- `docs/pipeline.md` is internally split.
- Lines `10` and `49` understand the watchlist model.
- Lines `135-139`, `186`, and `200` still say PASS-only promotion and `promotion_ready = backtest_certified AND tier-appropriate PASS`.
- Same file, same date band, incompatible meanings.

- `docs/project-status.md` is worse.
- It says leaderboard shows watchlist + admitted at `60-61`.
- It also says keep leaderboard PASS-only at `154`, and plain-English summary repeats PASS-only promotion at `169`.
- It says marker failures are hard fails at `107`.
- It frames the product around emitting a `backtest_certified` bundle for the best PASS winner at `13` and `124`.
- This is not one coherent model.

- `scripts/certify/recertify_leaderboard.py:1-17` still uses absolutist rhetoric: a leaderboard strategy is a binding statement that it is not overfit and will work into the future.
- The implementation at `95-115` is narrower and more reasonable: admit PASS plus WATCHLIST entries using `_is_leaderboard_eligible`.
- The script's prose oversells what the code is actually asserting.

- I checked whether the current leaderboard duplication was a broken dedupe story.
- The top entries are all `gc_vjatr`, but the params differ (`atr_confirm` varies among the first entries).
- So this is not "same config duplicated by bug"; it is a strategy-family concentration issue, not a dedupe lie.

- I checked whether current board entries secretly have completed artifacts elsewhere.
- The persisted `artifact_completeness` status is still `pending` in the board, so the board is intentionally storing non-certified entries.
- That reinforces the need to name the board as admitted/watchlist memory, not certified memory.

## Craftsman Bottom Line

- The code has actually made one important distinction more honest: admission and certification are separate.
- The repo vocabulary has not caught up.
- Right now Montauk has at least three overlapping models in circulation:
- model A: certified champion / PASS-only memory
- model B: confidence-ranked watchlist with separate certification
- model C: seven named "gates" that no longer gate
- That is the central conceptual integrity failure for this run.
