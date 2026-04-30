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

`composite_confidence` should mean: higher score means stronger evidence that
the strategy is likely to remain robust and useful into future TECL data. It is
not a raw performance score.

Current structure:

- correctness remains binary: engine integrity, golden regression, shadow comparator, data quality, artifacts
- confidence is the weighted geometric mean of tier-applicable robustness sub-scores
- Gold Status requires PASS, certified-not-overfit, backtest-certified artifacts, and full/real/modern B&H outperformance
- the authority leaderboard remains Gold-only
- the family-confidence leaderboard should select one Gold row per family and rank by `composite_confidence`

Open work:

- audit whether `selection_bias` should become stronger for heavily searched families
- decide whether confidence should include a family-diversity or duplicate-signal penalty
- document any change in `docs/validation-thresholds.md` before reranking
- recertify the leaderboard after any scoring-weight change

### 3. Build And Use A Family Confidence Leaderboard

The main leaderboard is intentionally Gold-only, but it can still get cluttered
by sibling variants. The family board should be the higher-level strategy
selection surface.

Rules:

- load only Gold Status rows from `spike/leaderboard.json`
- group by strategy family first (`strategy` field)
- choose the highest-confidence row in each family
- tie-break by all-era score, then fitness, then real/modern share multiples
- emit a JSON artifact under `runs/`
- optionally add a viz view once the report format is stable

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

### 5. Validation Pipeline Cleanup

Known cleanup item from `scripts/validation/pipeline.py`:

- split Gate 2 result-quality concerns from T2-only search-bias concerns so the
  validation report is easier to reason about

Do this after the current confidence/family-board work stabilizes.
