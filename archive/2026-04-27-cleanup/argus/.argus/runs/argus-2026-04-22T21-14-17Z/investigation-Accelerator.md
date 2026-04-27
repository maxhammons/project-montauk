# Accelerator Investigation

## Primary Claim

Project Montauk is faster to change than it was in the prior run, but it is still not newcomer-safe to ship from today because the repo's trust boundary is ambiguous. A new engineer can now get useful local feedback from the engine tests, yet they still cannot answer the crucial operational question cleanly: which outputs are safe to treat as real. The docs, gate-7 synthesis, leaderboard updater, and recertifier do not agree on what "admitted", "promotion_ready", and `backtest_certified` mean.

## Substantive Observations

### 1. The first-run instructions are stale in the exact places a new engineer would touch first.

`CLAUDE.md:155` instructs the engineer to run `scripts/data.py`, `scripts/data_manifest.py`, and `scripts/data_quality.py`, but those files do not exist anymore in the current tree. `docs/pipeline.md:68` says the canonical promotion path is `scripts/spike_runner.py --hours ...`, while the real runner lives at `scripts/search/spike_runner.py`. `docs/pipeline.md:168` still points `StrategyParams` to `scripts/backtest_engine.py`, which is also gone, and `docs/pipeline.md:183` still names `scripts/data_quality.py` instead of `scripts/data/quality.py`.

This is not cosmetic drift. These are the commands and files a new engineer uses to get oriented and to prove they can do a safe end-to-end pass. If the repo lies on the first three moves, they stop trusting the written operating model and start depending on tribal knowledge.

### 2. The promotion contract is split across three incompatible definitions.

`scripts/validation/pipeline.py:837-975` defines gate 7 in strict terms: FAIL below 0.40, WARN from 0.40 to 0.69, PASS at 0.70+, with `promotion_ready = verdict == "PASS"` and `backtest_certified` requiring all certification checks. That is a hard PASS-only view.

But `scripts/search/evolve.py:210-235` uses a looser eligibility rule for leaderboard admission: anything at `composite_confidence >= 0.60` plus the four required certification checks can be admitted. `scripts/certify/recertify_leaderboard.py:95-105` explicitly reinforces the same watchlist rule during rebuild.

Then `docs/pipeline.md` says both things at once. Line 10 describes `spike/leaderboard.json` as a 0.60+ watchlist with ADMITTED vs WATCHLIST tiers. But lines 135-139 and 186 still say only PASS / `promotion_ready` entries belong on the leaderboard. This is exactly the kind of semantic split that makes engineers ship a behavior they can defend with one file while violating another.

### 3. The comments claim the leaderboard is stricter than the code actually enforces.

`scripts/search/evolve.py:250-255` says leaderboard admission requires `promotion_ready` plus engine-level certification checks. That comment is false as written. The implementation at `scripts/search/evolve.py:210-235` checks only `composite_confidence >= 0.60` and the four certification checks, not `promotion_ready`.

That matters because engineers trust comments when they are trying to move quickly through a large file. Here the comment describes a stronger contract than the code executes. This is how a repository grows a culture of "be careful, the comments are stale," which is operational poison.

### 4. The engine safety net is materially better now, but it protects the wrong layer of risk.

The prior Accelerator concern that the repo had no real `pytest` safety net is outdated. `tests/test_regression.py:1-161` is legitimate protection. It replays the canonical 8.2.1 path, checks exact trade count, per-trade dates / reasons / pnl tolerances, summary metrics, slippage baseline, compatibility-facade parity, and legacy leaderboard schema reading. That is a real confidence multiplier for engine edits.

But the tests do not appear to pin the contract that now matters more operationally: leaderboard admission semantics, doc-to-code consistency, or the distinction between "on the leaderboard", `promotion_ready`, and `backtest_certified`. So the repo has become safer to change at the math layer without becoming equally safe to change at the trust-boundary layer.

### 5. The live leaderboard is not a deploy-ready contract, even when docs often imply that it is.

The current `spike/leaderboard.json` top entries are all PASS entries, but they are not `backtest_certified`. For example, `spike/leaderboard.json:431-470` shows the top `gc_vjatr` entry with `validation.verdict = "PASS"`, `promotion_ready = true`, `composite_confidence = 0.7345`, and `backtest_certified = false` because `artifact_completeness` is still pending there.

That distinction is technically defensible if the leaderboard is a research-memory surface rather than a deployment surface. The problem is that the repo's prose does not hold that distinction consistently. `docs/pipeline.md:163-186` and parts of `scripts/README.md:24-37` describe the leaderboard in language that sounds like a binding certification statement, while the live state shows a weaker object: leaderboard memory that may still need champion artifact sealing before it is actually deployment-complete.

### 6. The codebase has made thoughtful reliability investments for long runs, but recovery is still lore-heavy.

`scripts/search/safe_runner.py` is good operational engineering. It adds crash tracking, top-K preservation, mid-grid checkpoints, heartbeats, signal handling, and raw-ranking persistence before validation. That is exactly the sort of guardrail that reduces fear during long search runs.

But `scripts/search/safe_runner.py:355-387` still ends the hardest failure mode with "re-run validation manually with `python -c ...`". That is survivable for the owner. It is not the same thing as being newcomer-safe. Likewise, `scripts/certify/full_sweep.py:1-18` offers a one-command rescore, but it is explicitly exhaustive across the full registry. That is a heavy hammer, not a gentle onboarding loop. The repo is resilient for insiders and still awkward for fresh hands.

## What I investigated and ruled out

- I ruled out the prior-run claim that the repo lacks a meaningful `pytest` suite. The engine now has a real regression net in `tests/test_regression.py`, and the current state is materially better on that front.
- I ruled out the fear that the live leaderboard is already full of WARN/watchlist entries. The current top 20 entries are all PASS in the on-disk state I inspected.
- I ruled out the idea that `artifact_completeness` is supposed to gate every leaderboard entry equally. The code treats it as champion-facing, and `scripts/search/spike_runner.py:96-149` finalizes it only on champion-oriented targets.
- I ruled out "no one-command path exists at all." One-command paths do exist (`safe_runner`, `full_sweep`, the runner itself). The problem is not absence; it is that the canonical instructions for those paths are stale or too heavy for a new engineer's first safe ship.

## What I would need to see to change my mind

- One canonical statement of leaderboard semantics, with identical wording reflected in `docs/pipeline.md`, `scripts/README.md`, `scripts/validation/pipeline.py`, `scripts/search/evolve.py`, and `scripts/certify/recertify_leaderboard.py`.
- A small test suite that asserts the actual admission contract: below 0.60 rejected, 0.60-0.69 watchlist or rejected by policy, 0.70+ PASS, and explicit behavior for `promotion_ready` vs `backtest_certified`.
- Fixed onboarding commands in the top-level docs so the first-run workflow references real paths only.
- A dry-run or explain mode for leaderboard recertification and promotion logic, so a new engineer can prove what would change before mutating `spike/leaderboard.json`.
- A clear human sentence in the docs about whether the leaderboard is a research watchlist, a validated memory surface, or a deployable certification surface. Right now it is trying to be all three.

## Bottom Line

I do not think the repo is paralyzed. I think it is deceptively movable. A strong engineer can ship here today, but they have to carry the contract in their head instead of trusting the repo to state it plainly. That is survivable for the owner and hostile to onboarding. The next velocity win is not another optimizer feature. It is making the trust boundary say one thing everywhere.
