# Pragmatist Investigation

## Primary claim

Montauk's useful core is still the Python engine plus a single trustworthy admission path. The repo is spending too much complexity on ceremony around that core: advisory gates that still run like vetoes, multiple scripts that each restate leaderboard policy, and repair jobs that exist because persisted state is not trusted enough the first time.

I do not want to delete the engine. I want to delete duplicated policy and post-hoc repair layers.

## Substantive observations

### 1. Gate 6 still burns real time after the code explicitly demoted it to diagnostics.

`pipeline.py` says cross-asset was removed from `composite_confidence` and is still computed only for diagnostics ([scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:236)). The same file still runs `_gate6_cross_asset()` for every non-hard-stopped candidate across all tiers, and that gate still performs same-parameter replay plus Tier 3 re-optimization ([scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:757), [scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:1114), [scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:1231)).

That is classic bad leverage. The repo is paying interactive-path cost for a check it no longer lets decide the outcome.

### 2. The validation pipeline still talks like it has many gates, but control flow says there is basically one hard gate and one score threshold.

Walk-forward and named-window failures were demoted into critical warnings instead of hard fails ([scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:556)). Marker shape now always returns `PASS` by design ([scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:733)). `_gate7_synthesis()` says only gate1 can hard-fail and the final verdict mostly comes from `composite_confidence` thresholds ([scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:822), [scripts/validation/pipeline.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/validation/pipeline.py:960)).

This is too much structure for what the system now does. If most gates are advisory math, stop pretending they are bouncers.

### 3. Leaderboard admission policy is scattered across multiple entrypoints instead of living in one place.

`evolve.py` defines `_is_leaderboard_eligible()` and `update_leaderboard()` as the central guard ([scripts/search/evolve.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/evolve.py:210), [scripts/search/evolve.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/evolve.py:238)). But `grid_search.py` still applies its own `composite_confidence >= 0.60` filter before calling `update_leaderboard()` ([scripts/search/grid_search.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/grid_search.py:1529)). `full_sweep.py` repeats the same pattern ([scripts/certify/full_sweep.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/full_sweep.py:241)). `recertify_leaderboard.py` reconstructs candidates, reruns validation, filters again, clears the file, then rebuilds it ([scripts/certify/recertify_leaderboard.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/recertify_leaderboard.py:45), [scripts/certify/recertify_leaderboard.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/recertify_leaderboard.py:95), [scripts/certify/recertify_leaderboard.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/recertify_leaderboard.py:134)).

That is not one admission contract. That is several scripts trying to remember the same contract.

### 4. `spike_runner.py` is carrying too much orchestration to qualify as a clean entrypoint.

The main `/spike` path refreshes data, runs the optimizer, runs validation, generates overlays, emits artifacts, patches certification state after artifact creation, updates the leaderboard, writes the report, and then tries to backfill viz artifacts ([scripts/search/spike_runner.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/spike_runner.py:498)). It also rewrites `validation_summary.json` and `dashboard_data.json` after initially emitting them ([scripts/search/spike_runner.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/spike_runner.py:78), [scripts/search/spike_runner.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/spike_runner.py:171)).

That is not a thin shell around a run object. It is a second orchestrator with its own artifact semantics.

There is also a dangling branch to `scripts/backfill_dashboard_artifacts.py` in the happy path, and that file does not exist in the repo ([scripts/search/spike_runner.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/spike_runner.py:660)). Non-fatal dead paths are still dead paths.

### 5. The repo has accumulated repair jobs because `leaderboard.json` is still a weak trust boundary.

`_is_leaderboard_eligible()` still grandfatheres entries with no validation block ([scripts/search/evolve.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/search/evolve.py:220)). Then the repo needs `recertify_leaderboard.py` to rerun the world under current rules and eject stale entries ([scripts/certify/recertify_leaderboard.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/recertify_leaderboard.py:2)). It also needs `full_sweep.py` to rescore the full registry after framework changes, merge data from current leaderboard, run files, and fixed-parameter outputs, then backfill dashboard artifacts for the top 20 ([scripts/certify/full_sweep.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/full_sweep.py:1), [scripts/certify/full_sweep.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/full_sweep.py:290), [scripts/certify/full_sweep.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/certify/full_sweep.py:487)).

When state needs recertify, rescore, and backfill scripts around it, the state contract is not done.

### 6. `scripts/strategies/library.py` is a giant convenience file that has outlived its convenience.

The file’s own extension instructions tell engineers to add the function, add the registry entry, and add params in the same file ([scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:8)). The file also contains reusable family helpers like `_ma_cross_with_slope()` and `_gc_strict_signals()` that clearly define coherent strategy families ([scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:1184), [scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:3715)). But registry, tiers, and parameter maps are all still centralized in the same 7k-line module ([scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:6289), [scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:6484), [scripts/strategies/library.py](/Users/Max.Hammons/Documents/local-sandbox/Project%20Montauk/scripts/strategies/library.py:6615)).

This is not the worst offender in the repo. It is still too big to be honest.

## What I investigated and ruled out

- I checked `scripts/search/safe_runner.py` as a likely ornamental wrapper. It is not dead code. Repo-wide search shows it is used by `focus_spike.py`. I ruled out “delete safe_runner” as the main claim.
- I did not find enough evidence that `viz/` is the primary complexity problem. The heavy duplication lives in search, validation, certification, and leaderboard state management.
- I did not find enough evidence that `scripts/data/*` is the wrong abstraction target for this run. Whatever problems exist there, they are not the current leverage sink.
- I ruled out “too many TODOs” as the headline. The important problem is not littered TODO debt. It is live semantic drift in code that already shipped.

## What I would need to see to change my mind

- Evidence that Gate 6 is cheap enough or asynchronous enough that keeping it on every validation path costs almost nothing in operator time.
- Evidence that one function, not three callers plus one helper, now owns leaderboard admission policy across `evolve`, `grid_search`, `full_sweep`, and `recertify`.
- Evidence that `leaderboard.json` can be treated as authoritative without needing recertification or full rescore jobs after routine rule changes.
- Evidence that `spike_runner.py` has become a thin entrypoint again, with artifact writing and certification fix-up collapsed into one canonical run contract.
- Evidence that strategy family code has been split so `library.py` is mostly registry data, not registry plus family helpers plus tier metadata plus parameter maps.

## Bottom line

The repo is not failing because it lacks abstractions. It is failing because it kept the old amount of ceremony after demoting the force of that ceremony.

If I were forcing one simplification direction, I would start here:

1. Stop paying synchronous cost for advisory-only validation checks.
2. Collapse leaderboard admission and repair logic into one canonical state boundary.
3. Shrink `spike_runner.py` until it is a shell, not a second pipeline.
