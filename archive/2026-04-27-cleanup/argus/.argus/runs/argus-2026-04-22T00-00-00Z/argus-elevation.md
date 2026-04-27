# Argus Elevation Plan

## Blockers

### 1. The `composite_confidence` Geometric Mean Obscures Validation
- **What it is:** The pipeline calculates a 10-variable geometric mean instead of using boolean hard-fails, making it impossible to know which tests a strategy actually passed or failed without unpacking the math.
- **Surfaced by:** Pragmatist / Craftsman
- **What to do:** Replace the geometric mean with a strict checklist of boolean hard-fails for non-negotiable invariants (e.g., share_multiple > 1.0, max_drawdown limits). Move the rest of the 10 metrics to an "advisory score" that does not determine the PASS/FAIL verdict.
- **What it unlocks:** Deterministic, transparent validation where an engineer immediately knows exactly why a strategy failed.

### 2. Threshold Drift via Demoted Fails
- **What it is:** In recent commits (April 21), hard-fails across Gates 4, 5, and 6 were demoted to warnings. The system is curve-fitting its own validation rules to let strategies pass.
- **Surfaced by:** Futurist
- **What to do:** Revert the demotion for load-bearing gates (like Walk-Forward). If a strategy fails out-of-sample validation, it must not pass. Do not lower the bar to ship.
- **What it unlocks:** Protection against deploying overfit strategies with real capital.

### 3. Missing Input Schema Validation at the JSON Boundary
- **What it is:** The pipeline uses unvalidated `json.load()` on `leaderboard.json` and raw optimizer outputs, using these to dictate control flow (e.g., `_strategy_history_state` tier routing).
- **Surfaced by:** Exploiter
- **What to do:** Implement Pydantic models or strict JSON schemas for the GA payloads and leaderboard entries. 
- **What it unlocks:** Security against leaderboard poisoning and unpredictable crashes from malformed inputs.

## Accelerators

### 4. Remove the 2-Hour Gate 6 Loop from the Critical Path
- **What it is:** The validation pipeline runs a 2-hour cross-asset re-optimization check (Gate 6) that destroys velocity. The Execution Agent proved this gate no longer even vetoes strategies.
- **Surfaced by:** Accelerator (Proven by Execution Agent)
- **What to do:** Move Gate 6 to a nightly asynchronous batch job, or remove it entirely if it no longer serves as a hard veto. 
- **What it unlocks:** A fast, sub-minute validation path that engineers can run locally, encouraging rapid, fearless iteration.

## Bets

### 5. Rename Heuristic "Gates" to "Observers"
- **What it is:** Gates like `_gate_marker_shape` unconditionally return `PASS`. They are diagnostic observers, not gates. 
- **Surfaced by:** Craftsman
- **What to do:** Separate the pipeline into `validation/` (boolean, strict) and `diagnostics/` (heuristic, informative).
- **What it unlocks:** Complete conceptual integrity, where the vocabulary in the codebase perfectly matches the operational reality.