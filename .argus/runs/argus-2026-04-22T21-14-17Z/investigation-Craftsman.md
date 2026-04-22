# Craftsman Investigation

## Primary Claim

Montauk's current validation machinery is more nuanced than its language. The code has already split "admitted to the leaderboard" from "fully certified champion artifact bundle," but the repo still uses `gate`, `PASS`, `promotion_ready`, and `backtest_certified` as if they belong to one clean model. They do not. What exists now is a confidence-ranked watchlist with a separate champion-certification path, wrapped in older certification rhetoric. This is not a small documentation gap. It is a mental-model fault line in the core trust surface of the project.

## Observations

### 1. Gate 7's actual contract disagrees with the repo's prose contract.

The code in `scripts/validation/pipeline.py:831-976` defines the live semantics. It sets `promotion_ready = verdict == "PASS"` at line `973`, while `backtest_certified` is stricter and depends on the certification checks at `974-976`, including `artifact_completeness`, which is initialized as pending at `922-930`. That is a coherent model: admission first, final certification later.

But the written contract disagrees. `docs/validation-philosophy.md:100-102` says `backtest_certified` is the correctness flag and `promotion_ready = backtest_certified AND confidence >= 0.70`. `CLAUDE.md:267-268` repeats the same definition. Those cannot both be true with the current code. If I read the docs cold, I build the wrong model first.

### 2. The leaderboard is intentionally storing non-certified entries, yet some files still describe leaderboard membership as certification-grade truth.

`scripts/search/evolve.py:191-235` explicitly excludes `artifact_completeness` from `REQUIRED_CERTIFICATION_CHECKS`, and `_is_leaderboard_eligible` only requires `composite_confidence >= 0.60` plus the four engine-level checks. `scripts/search/spike_runner.py:96-168` then finalizes `artifact_completeness` only after artifacts are emitted for the champion path.

The persisted state matches that code, not the old rhetoric. In `spike/leaderboard.json:431-482`, the top entry is `PASS`, `promotion_ready: true`, `backtest_certified: false`, with `artifact_completeness` still pending. A quick read of the current board shows this is not exceptional; it is the dominant state. Yet `scripts/certify/recertify_leaderboard.py:13-16` still says a strategy on `spike/leaderboard.json` is a binding statement that it is not overfit and will work into the future. That claim is stronger than what the board currently certifies. This is not honest naming. This is aspirational language pasted over a narrower guarantee.

### 3. Marker and cross-asset are still called gates after they stopped behaving like gates.

The marker path is the clearest example. `scripts/validation/pipeline.py:652-735` says the marker check is informational and diagnostic only, then returns `verdict = "PASS"` unconditionally at `733-735`. A strategy can be "essentially uncorrelated with markers" and still have the marker gate say PASS. That may be the right math. It is the wrong noun. A gate that never closes is not a gate.

Cross-asset follows the same pattern. `scripts/validation/pipeline.py:757-809` describes Gate 6 as demoted, non-veto, warning-based. The UI in `viz/montauk-viz.html:1220-1245` still counts and renders PASS/WARN/FAIL gate rows, which keeps the old enforcement theater alive on the surface. This matters because the repo's entire legitimacy story is framed around validation boundaries. If the boundaries are diagnostic, name them diagnostic.

### 4. The repo now contains duplicate validation models, especially around `cross_asset`.

The code and docs are not merely out of sync at the edges. They now carry mutually incompatible equations. In `scripts/validation/pipeline.py:227-254`, `_geometric_composite` omits `cross_asset` from the weights entirely. In `scripts/validation/pipeline.py:906-919`, Gate 7 still carries `cross_asset` in the `sub_scores` payload, but the geometric composite ignores it because no weight exists.

`docs/validation-thresholds.md:79` says `cross_asset` was removed from the composite. Then the same document assigns `cross_asset` effective weights at `81-94` and still treats Gate 6 as a weighted `cross_asset` source later in the file. `CLAUDE.md:248-268` also still lists `cross_asset (demoted) | 0.05 | all`. This is not "some docs are stale." This is multiple incompatible mathematical models coexisting in official surfaces.

### 5. `docs/project-status.md` is teaching a materially obsolete pipeline.

This file claims to describe what is true today, but it blends several eras of the system. It says the project emits a `backtest_certified` signal bundle for the best PASS winner at `docs/project-status.md:13-14`. It says watchlist + admitted entries exist at `60-61`. It also says to keep the leaderboard PASS-only at `154`, repeats PASS-only promotion at `169`, and still describes marker failure as a hard fail at `105-107`. Those cannot all describe the same system.

This matters because `project-status.md` is not archival fluff. It is a status document for orientation. Right now it is a plausible wrong explanation generator.

### 6. The repo itself admits one semantic boundary is still unfinished.

`scripts/validation/pipeline.py:1080-1090` contains the only live authored TODO I found in the code/doc surface relevant to this run: Gate 2 still bundles result-quality and search-bias concerns and needs to be split. That comment is honest. The surrounding naming is not. The code currently says "Gate 2" while also admitting that the conceptual boundary inside Gate 2 is wrong for non-T2 tiers. This is not the biggest lie in the repo, but it is a live example of unfinished conceptual integrity in the validation core.

## What I investigated and ruled out

I investigated whether this was simply "docs are stale but code is clean." I do not think that is the full story. The code, persisted JSON, and UI are broadly aligned around a watchlist/admission model with separate certification. The problem is that the words exported by the repo still describe a stricter model in several official places. That is deeper than stale prose because those words define operator expectations.

I investigated whether current leaderboard entries were duplicated by a broken dedupe path. They are not. The top entries share the same strategy family, but the params differ. This is concentration, not hash-dedup corruption.

I investigated whether artifact completeness was secretly being satisfied for current leaderboard entries via champion backfill. The persisted board says no: the visible entries I checked still carry `artifact_completeness: pending` and `backtest_certified: false`.

I investigated whether marker or cross-asset still had hidden veto power in the live code. I did not find that. The code is explicit that they are warning/score paths now. My claim is not that the code secretly enforces old rules. My claim is that the repo vocabulary still pretends those rules exist.

I investigated whether the UI was the main liar. It is not. The UI is actually one of the more honest layers because it separates admission labels from certification badges. The deeper dishonesty sits in the shared vocabulary exported by docs and comments.

## What I would need to see to change my mind

I would change my mind if the repo converged on one explicit contract and enforced it everywhere. Concretely:

- A single written definition of `promotion_ready`, `backtest_certified`, leaderboard admission, and champion certification that matches `scripts/validation/pipeline.py`, `scripts/search/evolve.py`, `scripts/search/spike_runner.py`, `docs/validation-philosophy.md`, `docs/pipeline.md`, `docs/project-status.md`, and `CLAUDE.md`.
- Either rename diagnostic "gates" to something truthful, or restore actual veto semantics so the word `gate` becomes true again.
- Remove the duplicate `cross_asset` model so the docs and operator guide stop claiming a weight the code does not use.
- Add tests that pin the semantics, not just the computations: one test for leaderboard eligibility, one for champion certification finalization, and one that asserts the docs' exported contract is current when those semantics change.
- If the team really wants the leaderboard to be a binding certification statement, then I would need to see `artifact_completeness` required for every admitted entry, not just the champion path.

Until then, Montauk's trust problem is not that the math is weak. It is that the names are ahead of the truth in some files and behind it in others.
