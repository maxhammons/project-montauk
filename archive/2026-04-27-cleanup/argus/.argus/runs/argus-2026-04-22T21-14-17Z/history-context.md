# History Context

## Sources Used
- Git history from `2026-03-03` through `2026-04-22`
- Prior Argus history artifacts: `history-context-Apr-09.md`, `history-context-Apr-14.md`
- Prior Argus elevation outputs: `argus-elevation-Apr-14.md`, `argus-2026-04-22T00-00-00Z/argus-elevation.md`
- Prior-run brief for this run: `prior-run-brief.md`
- Failure memory: no `journals/argus/_failures.md` present

## Timeline Of Major Decisions

### 2026-03-03 to 2026-03-04: Pine-native origin, then early audit hardening
- The repo began as a Pine Script TECL trading system (`Initial commit — Project Montauk Pine Script trading system` on 2026-03-03).
- Within 24 hours, the work shifted into bug-audit mode around strategy version `8.2` and then `8.2.1`, which suggests the earliest load-bearing concern was correctness of an already-active trading idea, not platform architecture.
- This phase established the first durable pattern in the repo: strategy iteration precedes tooling cleanup.

### 2026-04-01 to 2026-04-08: Python optimizer emerges and quickly dominates
- `Add /spike optimization skill with Python backtesting engine` on 2026-04-01 is the real architectural fork. From here, Pine stops being the center of gravity.
- The next week is a velocity burst around unattended optimization, GA search, run history, leaderboard state, GH Actions integration, and deduplication. The repo repeatedly restructures itself to support longer-running search loops.
- Important directional decisions in this window:
  - optimization became the operating loop, not an occasional experiment
  - history/state (`leaderboard.json`, `hash-index.json`, run folders) became part of the product
  - repository shape was bent around automation throughput

### 2026-04-08 to 2026-04-10: Validation becomes first-class
- `major pipeline overhaul — VIX, synthetic TECL, Bayesian, walk-forward` on 2026-04-08 marks the second major fork.
- By `Montauk Engine 1.2` and `1.3` on 2026-04-10, the project is no longer just searching for profitable parameter sets; it is building a formal anti-overfitting apparatus.
- This is where the repo starts acting like a research pipeline rather than a strategy sandbox.

### 2026-04-13: Hard philosophical pivot to hypothesis-driven search
- `Montauk Engine 2.0` and the dense 2026-04-13 commit cluster are the most important single-day transformation in the history.
- Major decisions made that day:
  - pre-registered hypotheses and design guidance were elevated
  - `share_multiple` versus buy-and-hold was formalized as the charter metric
  - marker alignment was first strengthened, then demoted from hard gate to diagnostic/north star
  - grid search replaced batch T0 generation as the primary search path
  - validation thresholds were loosened in several areas
- This is the key contradiction now embedded in the repo: the system talks like a strict validator while recent commits moved parts of validation toward advisory scoring.

### 2026-04-14: Reorg and expansion rather than simplification
- Multiple commits labeled `Reorg`, `Spirit-setup`, data expansion, new strategy work, VIX work, and multicore changes indicate the team chose breadth and operating structure over consolidation.
- The repo absorbed new process memory and organization layers instead of reducing complexity after the April 13 rules shift.

### 2026-04-19 to 2026-04-22: Consolidation around data, UI, and organization
- `Update grid search, validation pipeline, and data backfill tooling` on 2026-04-19 is a large maintenance-and-capability sweep touching data, docs, validation, and artifact generation.
- `Montauk UI and Organization` on 2026-04-20 indicates a presentation and repo-structure pass after the heavy engine work.
- Recent history is quieter in commit count but broader in surface area, which usually signals a system entering operationalization rather than pure invention.

## Velocity Map By Area

### High-velocity zones
- `spike/runs/`: by far the largest churn area. This is expected output churn, but it also means the repo history is dominated by artifacts, which can mask signal about architectural changes.
- `scripts/validation/`: active and load-bearing. This is where the project keeps renegotiating what "pass" means.
- `scripts/search/`, `scripts/evolve.py`, `scripts/grid_search.py`: the search core remains in motion, especially around how candidates survive and how expensive loops are routed.
- `CLAUDE.md` and `.claude/skills/`: process surface changes almost as often as engine code, which means operator workflow is part of the real product.

### Medium-velocity zones
- `scripts/data/` and related data-quality tooling: activity increased sharply by April 19, suggesting synthetic data provenance and ingestion trust are becoming more central.
- `scripts/engine/` and `scripts/strategy_engine.py`: fewer commits than search/validation, but more structurally important when touched.
- `docs/`: frequent enough to matter, especially around charter, validation philosophy, and pipeline diagrams.

### Stable or relatively settled zones
- `tests/`: not dormant, but notably less active than the rule system around them. That mismatch matters.
- `viz/`: present and useful, but not the center of recent historical energy.
- Legacy Pine strategy archives: effectively historical residue.

## Active Evolution Zones Vs Stable Zones

### Active evolution zones
- Validation semantics: still unstable. The repo is actively deciding whether it wants strict vetoes or heuristic confidence scoring.
- Search-to-validation handoff: still evolving. Recent Argus outputs and commit history both point to friction between fast search and expensive, partially non-binding gates.
- Data provenance and synthetic rebuild workflow: becoming more important as the project leans harder on historical simulation quality.
- Operator interface: the skill layer, docs, and UI are converging into a more coherent human-in-the-loop workflow.

### Stable zones
- Core project identity: TECL-focused, long-only, share-accumulation strategy research remains consistent from origin through current state.
- Manual execution model: despite all the automation work, the final brokerage action is still manual.
- North-star metric direction: the project has committed to share accumulation over cosmetic equity-curve metrics.

## Abandoned Approach Inventory

### 1. Pine Script as the primary execution environment
- This was the starting point, but from 2026-04-01 onward Python became the center of truth.
- Residual artifacts still exist in historical docs and strategy archives, but they no longer represent the real engine.

### 2. `remote/` as the operating output surface
- Commits on 2026-04-04 and 2026-04-05 show a transition away from `remote/` into `spike/`.
- This was a real operational reversal, not just a rename. The repo changed how it stores run state and results.

### 3. Batch hypothesis queues as the primary discovery loop
- The April 13 sequence shows a shift from queued T0 batches toward exhaustive/canonical grid search plus authored concepts.
- The old mode is not fully erased conceptually, but it has clearly lost primacy.

### 4. Marker alignment as a hard validator
- On 2026-04-13 marker logic was explicitly demoted from a hard gate to a diagnostic/north-star role.
- The codebase still talks about markers as important, but the decision history says they no longer carry veto authority.

### 5. Strict-gate rhetoric
- This is not fully abandoned in naming, but it is partially abandoned in behavior.
- Prior Argus analysis and the latest prior-run brief both point to the same drift: more checks still exist, but some have been softened enough that "gate" is becoming a misleading term.

## Decision Archaeology

### Load-bearing decisions
- Python engine as source of truth instead of Pine.
- `share_multiple` versus buy-and-hold as the primary optimization target.
- Persistent run memory through `spike/runs/`, `leaderboard.json`, and `hash-index.json`.
- Heavy validation pipeline as the legitimacy mechanism for candidate strategies.
- Manual execution at the brokerage edge, which keeps the system research-grade rather than fully autonomous trading infrastructure.

### Reversed or weakened decisions
- Marker alignment moved from enforcement toward guidance on 2026-04-13.
- Gate severity appears to have softened further by April 21 per the prior-run brief and previous Argus conclusions.
- Cross-asset Gate 6 remains expensive, but prior Argus execution work concluded it no longer reliably blocks bad strategies. That makes it a weakened decision still incurring full operational cost.

### Emergent rather than deliberate drift
- The repo has accumulated many process layers: skills, spirit memory, Argus artifacts, validation math, data backfill tools, UI surfaces. The history reads less like one clean architecture plan and more like successive defenses added around a productive search engine.
- Artifact churn is so high that historical outputs can overshadow code intent. That is usually how operational repositories become harder to reason about over time.

## Merge-Conflict / Coordination Hotspots
- `CLAUDE.md` and `.claude/skills/*`: these files sit at the boundary between human process and engine behavior, so they are likely multi-author touchpoints.
- `scripts/validation/*` and `scripts/search/*`: these are the conceptual battlegrounds of the repo. Most strategic disagreements show up here.
- `spike/leaderboard.json` and `spike/hash-index.json`: not traditional merge-conflict hotspots in the code-review sense, but they are trust-boundary hotspots because persisted JSON state influences future control flow.

## Trajectory Predictions

### 30 to 90 days
- The repo is trying to become a disciplined strategy research appliance: search, validate, certify, visualize, and preserve memory around a TECL-specific trading thesis.
- Confidence: high.

### Likely breakpoints if current trends continue
- Validation credibility breaks before search capability does.
  - If more "gates" become warnings or geometric-score components, the system will keep producing candidates while losing the ability to explain why a strategy is truly safe.
  - Confidence: high.
- Operator trust erodes through semantic mismatch.
  - If the code says PASS while the underlying evidence is advisory, the team will eventually stop believing the labels.
  - Confidence: high.
- State integrity becomes the next hidden bottleneck.
  - As more workflow depends on persisted JSON artifacts and backfilled run products, malformed or stale state can distort search history and certification outcomes.
  - Confidence: medium-high.
- Repo cognition cost rises.
  - The addition of UI, spirit/process layers, and ever-richer artifacts without corresponding simplification will make onboarding and safe change progressively harder.
  - Confidence: medium.

### 3 to 6 months extrapolation
- Best-case path: Montauk stabilizes into a TECL-first research pipeline with a strict correctness layer, a separate advisory diagnostics layer, and trustworthy artifact/state boundaries.
- Failure path: it becomes a highly productive candidate generator whose validation language overstates what the system actually proves.

## What The Codebase Is Trying To Become
- Not a generic backtester.
- Not a broker-connected trading bot.
- It is trying to become a memory-bearing TECL strategy factory: a Python-native system that searches for share-accumulating regimes, filters them through increasingly formal validation, and presents the resulting candidates with enough provenance that a human can act on them manually.
- The unresolved question is whether that factory will optimize for truthful vetoes or for continued candidate throughput. Recent history says throughput is still winning that argument unless the validation boundary is re-hardened.
