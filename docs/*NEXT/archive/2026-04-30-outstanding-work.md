# Outstanding Work

This folder is the canonical home for Montauk follow-up work. If an agent creates
or discovers a non-immediate TODO, add it here instead of leaving it scattered in
root notes, scratch files, or inline comments.

## Active Priorities

### 1. Split `scripts/strategies/library.py`

`library.py` is now over 8,000 lines. It still works, but it is carrying too
many responsibilities: atomic strategy functions, hybrid functions, registries,
descriptions, parameter grids, tier declarations, and legacy candidates.

Target direction:

- keep `scripts/strategies/library.py` as a compatibility/registry facade
- move shared signal helpers into `scripts/strategies/core.py`
- move Golden Cross / Velvet Jaguar families into `scripts/strategies/golden_cross.py`
- move VJATR variants into `scripts/strategies/velvet_jaguar.py`
- move timing-repair, reclaimer, airbag, and diversity concepts into `scripts/strategies/diversity.py`
- move Gold ensemble / hybrid strategies into `scripts/strategies/hybrids.py`
- move retired or low-conviction historical candidates into `scripts/strategies/legacy.py`

Acceptance criteria:

- existing strategy names remain import-compatible through `STRATEGY_REGISTRY`
- all current tests pass without golden-ledger drift
- `grid_search.py`, `spike_runner.py`, validation, certification, diagnostics, and viz builds continue to read the same registry contract
- the split happens in small commits by ownership area, not as one giant rewrite

### 2. Nail Down Confidence Semantics

Confidence is now split into three concepts:

- Gold Status: binary leaderboard admission
- Future Confidence: calibration-assisted estimate of future usefulness
- Trust: deployment suitability after future confidence is established
- Overall Confidence: super score combining Future Confidence and Trust

`composite_confidence` remains the validation-stack composite and still drives
PASS/WARN/FAIL, but it is no longer the final "would I put money behind this?"
score.

Current structure:

- correctness remains binary: engine integrity, golden regression, shadow comparator, data quality, artifacts
- confidence is the weighted geometric mean of tier-applicable robustness sub-scores
- Gold Status requires PASS, certified-not-overfit, backtest-certified artifacts, and full/real/modern B&H outperformance
- the authority leaderboard remains Gold-only
- the family-confidence leaderboard should select one Gold row per family and rank by Overall Confidence when Confidence v2 is available

Open work:

- monitor whether Future Confidence is too punitive to complex but explicit
  committee strategies
- compare Overall Confidence, Future Confidence, and Trust drift after each data refresh before changing the underlying certification score
- recertify the leaderboard before changing `validation.composite_confidence`
  itself

2026-05-01 update:

- `validation.composite_confidence` remains the certification score
- `runs/family_confidence_leaderboard.json` now ranks family representatives by
  `future_confidence`, a stricter Gold-only score that discounts weak evidence
  planks, era imbalance, drawdown, parameter sprawl, duplicate signals, family
  crowding, and validation warnings
- the viz Family tab uses this stricter future-confidence rank while the Full
  leaderboard keeps the canonical certification confidence
- after refreshing data through 2026-05-01, the authority leaderboard compressed
  from 20 rows to 8 Gold rows because several Osprey/reclaimer and Bonobo rows
  no longer beat B&H in every canonical era

2026-05-01 Confidence v2 update:

- `scripts/validation/confidence_v2.py` computes diagnostic Overall Confidence,
  Future Confidence, and Trust
- `scripts/diagnostics/confidence_candidate_archive.py` collects current Gold,
  archived leaderboard, spike run, grid, hybrid, prefilter, and near-miss
  candidates into `runs/confidence_v2/candidate_archive.json`
- `scripts/diagnostics/confidence_vintage_harness.py` writes
  `runs/confidence_v2/vintage_trials.json`, `calibration_model.json`,
  `leaderboard_scores.json`, `confidence_timeseries.json`, and
  `live_holdout_log.json`
- the current archive contains 710 unique candidates across 97 families from
  167 artifacts; the default harness evaluates the top 120 across 6 historical
  vintages, producing 720 simulated vintage trials
- true live holdout evidence starts at 2026-05-01 because older data has already
  been seen by Montauk
- next improvement: make future grid/GA logs store full parameter provenance so
  the archive no longer needs to infer search burden from artifacts

### 3. Build And Use A Family Confidence Leaderboard

The main leaderboard is intentionally Gold-only, but it can still get cluttered
by sibling variants. The family board should be the higher-level strategy
selection surface.

Rules:

- load only Gold Status rows from `spike/leaderboard.json`
- group by strategy family first (`strategy` field)
- choose the highest Overall Confidence row in each family when Confidence v2 is available; fall back to legacy family confidence
- tie-break by all-era score, then fitness, then real/modern share multiples
- emit a JSON artifact under `runs/`
- expose Full leaderboard / Family leaders tabs in the viz

### 4. Continue Hybrid Strategy Research

The first Gold hybrid (`gold_hybrid_committee`) is promising, but the next
hybrid tests should avoid recursive hybrid-on-hybrid inputs unless explicitly
requested.

Next checks:

- keep running the hybrid lab with atomic Gold source members by default
- keep promoted hybrids as comparison champions, not automatic source members
- test stricter committees ranked by confidence and family diversity
- run diversity diagnostics against the current Gold champion
- package a champion dossier only after the hybrid survives recertification

2026-04-30 run notes:

- `gold_hybrid_lab.py --validate` passed 5/5 quick-validation candidates using atomic Gold sources
- the existing `family_committee_0.50` remains the best hybrid candidate and matches the current Gold champion
- entry/exit switchboard and overlay variants improved marker timing, but gave up too much share performance and had unacceptable drawdown, so they should stay research-only
- `gold_diversity_report.py` showed 20 Gold rows compress to about 2.74 effective strategy families
- `family_confidence_leaderboard.py` now emits one-row-per-family confidence rankings to `runs/family_confidence_leaderboard.json`

2026-05-01 run notes:

- current Gold rows form three strategy families: hybrid committee, Bonobo, and
  timing-repair Hare
- the stricter family board ranks Marbled Bonobo first by future confidence
  (69.9), then Cerulean Hare #1 (66.4), then timing-repair Hare (19.5)
- the timing-repair family remains Gold but scores poorly on future confidence
  because max drawdown is still the dominant weak plank
- `gold_hybrid_lab.py --validate` passed 5/5 quick-validation candidates; the
  best new committee variants (`family_committee_0.60` / `0.67`) improve real
  and modern share multiples versus the current champion but give up full-history
  share multiple

### 5. Validation Pipeline Cleanup

Known cleanup item from `scripts/validation/pipeline.py`:

- split Gate 2 result-quality concerns from T2-only search-bias concerns so the
  validation report is easier to reason about

Do this after the current confidence/family-board work stabilizes.

### 6. Confidence v2 Calibration Diagnostics

Goal: make Overall Confidence a better decision surface for finding the best
charter strategy, not just a nicer display score.

Next action:

- run a broader calibration pass using more of
  `runs/confidence_v2/candidate_archive.json`
  - compare top 120 vs top 300 vs top 500 archived candidates
  - preserve runtime and output size by making `--max-rows` explicit in every
    run note
  - compare whether current Gold family ranks and scores are stable across
    candidate-set size
  - document score drift for Overall Confidence, Future Confidence, and Trust

Add a calibration diagnostics report:

- create a report under `runs/confidence_v2/` that shows:
  - trials per raw-score bucket
  - observed survival rate per bucket
  - monotonicity of raw score vs forward survival
  - score drift between top-120 / top-300 / top-500 calibration runs
  - which components appear predictive vs saturated/noisy
- flag weak calibration behavior:
  - higher raw score does not improve forward survival
  - buckets have too few trials
  - one family dominates the trial set
  - a component is saturated across most candidates
- acceptance criteria:
  - diagnostics explain why the top family ranking changed or stayed stable
  - Overall Confidence is still diagnostic-only unless calibration quality is
    acceptable

### 7. Roadmap To The Best Charter Strategy

North star: find the strategy or strategy system that best accomplishes the
charter: accumulate more TECL shares than B&H while surviving full, real, and
modern eras, passing validation, and earning enough Trust to be deployable.

#### Step 1 — Stabilize The Confidence Signal

- broaden calibration as described above
- add diagnostics showing whether Overall Confidence is predictive
- expose Confidence v2 component breakdown in the viz:
  - Overall Confidence
  - Future Confidence
  - Trust
  - Future components: validation quality, forward edge, robustness, charter
    fit, search deflation, live evidence
  - Trust components: drawdown resilience, redundancy, parsimony, family
    crowding, artifact cleanliness, live degradation
- update the family board to show why each family leader won
- do not change Gold admission until the diagnostics support it

#### Step 2 — Improve Search Provenance Going Forward

- make every grid/GA/hybrid run emit explicit provenance:
  - run id and timestamp
  - discovery mode
  - total configs tested
  - family configs tested
  - parameter dimensions and active search ranges
  - seed source, if any
  - whether the candidate was pre-registered, grid-found, GA-found, or
    assembled as a hybrid
- store provenance directly on candidate artifacts instead of inferring it later
- backfill what can be inferred from existing artifacts
- feed provenance into Future Confidence as a first-class search-deflation
  input

#### Step 3 — Build Better Candidate Families, Not More Siblings

- use the family leaderboard as the selection surface
- prioritize families that are different from Bonobo/Hare:
  - crash-airbag exits
  - re-entry reclaimers
  - volatility-compression recovery
  - trend-quality filters
  - state-machine crash/recovery strategies
  - non-Golden-Cross baseline families
- require every new family sprint to report:
  - best Gold candidate, if any
  - best near-Gold candidate
  - why near-Gold failed
  - diversity vs current Gold champion
  - Confidence v2 score if admitted or archived
- stop filling the leaderboard with near-identical siblings unless they improve
  Overall Confidence or represent a materially different risk state

#### Step 4 — Build Hybrids From Proven Specialists

- use Overall Confidence to choose source members, but inspect subscores before
  combining
- maintain separate specialist boards:
  - best entry timing
  - best exit timing
  - best crash avoidance
  - best rebound participation
  - best Trust / drawdown resilience
- test hybrid forms in this order:
  - confidence-weighted committee of family leaders
  - entry-specialist + exit-specialist switchboard
  - Bonobo core with independently validated overlay
  - state-machine allocator using family leaders by market state
- do not let recursive hybrid-on-hybrid inputs become the default source set
- promote a hybrid only if it improves the charter objective without destroying
  Trust

#### Step 5 — Convert The Best Candidate Into A Champion Dossier

- once a candidate leads by Overall Confidence and all-era score, build a
  champion dossier:
  - strategy definition and rationale
  - full/real/modern metrics
  - Confidence v2 component breakdown
  - marker and named-window behavior
  - failure modes and worst historical periods
  - diversity vs existing Gold families
  - parameter sensitivity and search provenance
  - live-holdout monitoring plan
- require recertification after the dossier
- if the candidate remains Gold and Trust is acceptable, make it the comparison
  champion for future research

#### Step 6 — Start Live Confidence Monitoring

- treat 2026-05-01 forward as the true live holdout
- update `live_holdout_log.json` on each data refresh
- track:
  - live share multiple vs B&H
  - live drawdown vs expected drawdown
  - signal behavior vs historical analogs
  - Overall/Future/Trust drift
- define auto-review triggers:
  - Overall Confidence drops materially after refresh
  - Trust drops from drawdown or signal redundancy
  - live behavior diverges from vintage-calibrated expectations
  - current champion loses Gold Status

#### Step 7 — Keep The Codebase Maintainable Enough To Move Fast

- split `scripts/strategies/library.py` after the confidence/family workflow is
  stable
- keep strategy registry compatibility intact
- move hybrid and diversity concepts into dedicated modules so new family work
  is easier to review
- keep generated artifacts separate from source code changes in commits when
  practical
