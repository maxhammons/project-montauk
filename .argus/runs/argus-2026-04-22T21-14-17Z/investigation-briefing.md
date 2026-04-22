# Scout Investigation Briefing

## Pragmatist

The Pragmatist argues the useful core is still the engine plus one trustworthy admission boundary, and that Montauk is paying too much ceremony around that core. The main evidence is duplicated leaderboard policy across `scripts/search/evolve.py`, `scripts/search/grid_search.py`, `scripts/certify/full_sweep.py`, and `scripts/certify/recertify_leaderboard.py`, plus `scripts/search/spike_runner.py` acting as a second orchestrator and Gate 6 continuing to cost real time after being demoted to diagnostics.

## Futurist

The Futurist argues the long-term risk is semantic lock-in: labels such as `PASS`, `promotion_ready`, and `backtest_certified` no longer line up with how leaderboard admission and certification really work. The evidence centers on contradictions between `scripts/validation/pipeline.py`, `docs/validation-philosophy.md`, `docs/validation-thresholds.md`, `docs/project-status.md`, and `spike/leaderboard.json`, especially the fact that current leaderboard rows are admitted and treated as memory without carrying full certification truth.

## Craftsman

The Craftsman argues the trust surface is dishonest because the repo vocabulary still speaks in one clean validation model while the code already implements two distinct stages: leaderboard admission and champion certification. The evidence is concentrated in Gate 7 semantics inside `scripts/validation/pipeline.py`, doc contradictions across `CLAUDE.md` and multiple docs, and terms like `gate`, `PASS`, and `promotion_ready` being used as though they still describe hard boundaries when several of them are now diagnostic or post-hoc.

## Accelerator

The Accelerator argues the repo is faster to change than before, but still unsafe for a new engineer to ship from because the trust boundary is ambiguous. The evidence is stale onboarding paths in `CLAUDE.md` and `docs/pipeline.md`, a real but mis-aimed regression net in `tests/test_regression.py`, and conflicting definitions of what counts as leaderboard-worthy or deploy-worthy across `scripts/validation/pipeline.py`, `scripts/search/evolve.py`, and recertification flows.

## Exploiter

The Exploiter argues the first meaningful attack surface is not shell execution but semantic authority laundering through `spike/leaderboard.json` and downstream artifact generation. The evidence is soft admission repeated across multiple write paths, grandfathered legacy rows, certification finalization in `scripts/search/spike_runner.py` that can sever `backtest_certified` from `promotion_ready`, and maintenance scripts that can turn leaderboard rows into fresh-looking artifact bundles without rerunning the whole trust contract in that same flow.
