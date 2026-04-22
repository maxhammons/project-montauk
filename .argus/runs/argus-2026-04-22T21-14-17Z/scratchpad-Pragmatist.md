# Pragmatist Scratchpad

## Pass 1 Reading List
1. `scripts/validation/pipeline.py`
   Hypothesis: the file still carries hard-gate ceremony after parts of validation stopped behaving like vetoes.
   Expected signals: skip/warn paths that preserve PASS semantics, composite scoring that blends hard checks with heuristics, tier branching that keeps expensive logic alive after losing enforcement power.
2. `scripts/search/spike_runner.py`
   Hypothesis: this is orchestration glue with more flags, formatting, and artifact handling than business logic.
   Expected signals: repeated argument translation, pass-through wrappers, duplicated run-summary shaping, multiple routes into the same pipeline call.
3. `scripts/search/grid_search.py`
   Hypothesis: discovery logic and validation handoff are too tightly coupled, making the file large because it owns policy, orchestration, and reporting at once.
   Expected signals: validation imports deep in the search path, inline artifact assembly, repeated candidate-shaping code, CLI concerns mixed with core search loops.
4. `scripts/search/evolve.py`
   Hypothesis: the GA path duplicates enough of `grid_search.py` and `spike_runner.py` that the codebase is paying for multiple entrypoints into the same search system.
   Expected signals: near-duplicate filtering, leaderboard, artifact, or validation plumbing; separate CLI shell around the same primitives.
5. `scripts/strategies/library.py`
   Hypothesis: the strategy registry became a 7k-line dumping ground because extension is cheaper than structure, and the file now carries more catalog burden than leverage.
   Expected signals: long repetitive blocks, registry declarations that could be data, repeated parameter scaffolds, code that is hard to delete because everything is centralized here.
6. `scripts/certify/full_sweep.py`
   Hypothesis: certification added another expensive orchestration layer rather than collapsing onto one trusted validation path.
   Expected signals: recertification loops, artifact backfill, leaderboard rewriting, policy duplication from validation/search.
7. `scripts/certify/recertify_leaderboard.py`
   Hypothesis: this script exists because the leaderboard trust boundary is weak and needs repair jobs.
   Expected signals: read-modify-write JSON flows, schema cleanup, replay logic, revalidation after the fact.
8. `scripts/search/safe_runner.py`
   Hypothesis: this is a protective wrapper that may add indirection without enough independent value.
   Expected signals: shelling out, retries, environment guards, and thin pass-through behavior around search entrypoints.

## Allowed Expansions Budget
- Expansion 1 reserved for `scripts/validation/candidate.py` if `pipeline.py` delegates result-quality logic there.
- Expansion 2 reserved for `scripts/search/fitness.py` if both search entrypoints centralize scoring there.
- Expansion 3 reserved for `scripts/search/share_metric.py` if “share_multiple” handling is duplicated around adapters.
- Expansion 4 reserved for `scripts/engine/canonical_params.py` if tier routing is pushed down there.
- Expansion 5 reserved for `scripts/README.md` if the intended boundaries are unclear from code alone.

## North Star Lens
- This repo wants to hand a human a trustworthy `risk_on` / `risk_off` contract.
- My test is simpler: what code would I delete tomorrow without reducing that trust.
- If the answer is “quite a lot of orchestration,” the repo is paying too much plumbing tax.

## Pass 0 Quick Scans
- Atlas confirms large-codebase mode: 1,009 files in scout context and 1,073 in atlas scope after ignores.
- World-model hotspots already point at `scripts/validation/pipeline.py` and `spike/leaderboard.json`.
- Largest live code files are `scripts/strategies/library.py` (7,154 lines), `scripts/search/evolve.py` (1,875), `scripts/search/grid_search.py` (1,606), `scripts/engine/strategy_engine.py` (1,369), and `scripts/validation/pipeline.py` (1,304).
- There are many CLI entrypoints under `scripts/`, especially in `search/`, `validation/`, `certify/`, and `data/`.
- The only obvious live TODO in source is the Gate 2 split note in `scripts/validation/pipeline.py`, but that one matters because it shows semantics and implementation are still misaligned.
- Simple filename scans did not surface obvious `wrapper` or `adapter` filenames. That raises the odds that the indirection is structural, not nominal.

## Initial Claims To Pressure-Test
- Claim A: Montauk has too many top-level entrypoints for one research appliance.
- Claim B: validation semantics are doing too much narrative work and not enough control-flow work.
- Claim C: certification and recertification scripts exist because leaderboard state is not trustworthy enough to stand on its own.
- Claim D: the giant strategy registry is a maintenance liability even if it is not the hottest runtime path.

## What Would Falsify Those Claims
- If `spike_runner.py` is a genuinely thin shell and most logic lives in small reusable units, Claim A weakens.
- If `pipeline.py` cleanly separates hard vetoes from diagnostics and uses names that match behavior, Claim B weakens.
- If certification scripts mostly materialize outputs from a single canonical source without replaying policy, Claim C weakens.
- If `library.py` is mostly declarative data with minimal branching, Claim D weakens.

## Evidence Tracker
- Need concrete examples where warnings/skips still flow into operator-facing PASS language.
- Need concrete examples of duplicated orchestration between `spike_runner.py`, `grid_search.py`, `evolve.py`, and certification scripts.
- Need to distinguish “many scripts because they are separate jobs” from “many scripts because responsibilities are smeared.”
- Need at least one place where code exists to repair or reinterpret prior state rather than producing trustworthy state the first time.
- Need to keep an eye on whether some complexity is justified by reversibility or historical audit requirements.

## Ruled-Out Early Suspicions
- I do not yet have evidence that the native HTML viewer is the main complexity problem.
- I do not yet have evidence that data loaders are unnecessary layers; they may be one of the few honest boundaries here.
- I am not treating docs/legacy bulk as an engineering issue unless live code still depends on it.

## Pass 2 Notes
- Read only the files above unless one of the reserved expansions is clearly triggered.
- Favor deletion questions:
  What breaks if this file disappears?
  What unique responsibility lives here?
  Is this script a policy boundary or just a convenience shell?
- Keep looking for duplicate candidate-shaping, duplicate leaderboard writes, and duplicate validation-summary shaping.

## Pass 2 Evidence Notes
- `scripts/validation/pipeline.py` answers the main question fast:
  Gate names survived; gate behavior did not.
- `_geometric_composite()` explicitly says cross-asset was removed from the composite while the sub-score is still computed for diagnostics (`pipeline.py:236-250`).
- `_gate4_time_generalization()` demotes former hard fails into critical warnings and returns `WARN` or `PASS`, never `FAIL` (`pipeline.py:556-570`).
- Marker shape is now always `PASS`; the comments say it is for UI and does not drive verdict (`pipeline.py:733-753`).
- `_gate7_synthesis()` says only gate1 can hard-fail, and verdict is now mostly composite-threshold math (`pipeline.py:822-975`).
- Despite that, `_validate_entry()` still runs Gate 6 cross-asset re-opt for every non-hard-stopped candidate across all tiers (`pipeline.py:1114-1127`).
- `run_validation_pipeline()` still budgets and reports Gate 6 re-opt time as a first-class cost center (`pipeline.py:1231-1282`).

## Search Path Notes
- `spike_runner.py` is not a thin shell.
- It owns pre-run refresh, optimizer invocation, validation, overlay generation, artifact emission, certification patch-up, leaderboard mutation, report generation, and a viz backfill attempt (`spike_runner.py:498-671`).
- It also mutates `validation_summary.json` and `dashboard_data.json` after they are first written (`spike_runner.py:78-93`).
- It separately “finalizes” certification after validation because artifact completeness only exists post-write (`spike_runner.py:96-110`).
- That is a sign the pipeline contract is not closed when validation returns.
- `spike_runner.py` points at `scripts/backfill_dashboard_artifacts.py`, and the file is missing in the repo.
- That branch is already optional, which means the code is carrying a non-fatal dead path rather than an actual guarantee.

## Search / Certify Duplication Notes
- `grid_search.py` imports fitness from `search.evolve`, validation from `validation.pipeline`, and then applies its own composite-confidence admission filter before calling `update_leaderboard()` (`grid_search.py:33-40`, `1499-1571`).
- `full_sweep.py` repeats the same shape: run validation, keep entries at `composite >= 0.60`, then call `update_leaderboard()` (`full_sweep.py:228-263`).
- `recertify_leaderboard.py` rehydrates leaderboard entries into minimal pipeline inputs, reruns validation, filters with `_is_leaderboard_eligible()`, clears the leaderboard, then rebuilds it (`recertify_leaderboard.py:45-142`).
- `evolve.py` centralizes some admission logic in `_is_leaderboard_eligible()` and `update_leaderboard()`, but other entrypoints still pre-filter before they call into it (`evolve.py:210-235`, `238-434`).
- The policy exists in one helper and three caller-side copies. That is not a boundary. That is drift waiting to happen.

## Leaderboard Trust Notes
- `_is_leaderboard_eligible()` still grandfatheres entries that have no `validation` block (`evolve.py:220-224`).
- The existence of `recertify_leaderboard.py` is the cleanup tax for that softness.
- `full_sweep.py` exists largely to rescore the world after the confidence-model change and then rebuild a report from leaderboard plus runs plus fixed-param outputs (`full_sweep.py:1-15`, `290-399`).
- When a repo needs rescore, recertify, backfill, and dashboard artifact repair jobs around the same state file, the state file is not trustworthy enough yet.

## Strategy Library Notes
- `library.py` makes the extension path explicit: write function, add registry entry, add params in the same file (`library.py:8-11`).
- That is cheap for one engineer adding one idea. It is expensive for everyone else reading the system.
- Shared helpers like `_ma_cross_with_slope()` and `_gc_strict_signals()` prove there is family structure in the strategy set (`library.py:1184-1208`, `3715-3763`).
- But registry, tiers, and params still pile into the same giant file (`library.py:6289-6655`).
- This is not the worst complexity in the repo, but it is obvious catalog debt.

## Things I Checked And Did Not Escalate
- `safe_runner.py` is not dead. Repo-wide grep shows it is used by `focus_spike.py`.
- I still do not think it is the main problem because the primary `/spike` path bypasses it.
- I did not need any reserved Pass 2 expansions.
- I did not read deeper into data loaders or viz templates because the higher-cost duplication is already exposed in validation/search/certify.
