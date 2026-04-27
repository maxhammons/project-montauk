# Convergence Map

**Converged findings:**
1. The `composite_confidence` (10-variable geometric mean) obscures the actual reasons a strategy passes or fails.
2. The validation pipeline is undergoing "threshold drift," explicitly demoting hard-fails to warnings to curve-fit the rules.
3. The domain model and vocabulary are actively lying (`verdict = "PASS"` when the test didn't even run).
4. The pipeline implicitly trusts unvalidated JSON (`leaderboard.json`), exposing the control flow to poisoning.

**Contested claims:**
- *Gate 6 Re-optimization (The 2-hour loop):* Futurist claims it is the only remaining defense against massive overfitting. Accelerator claims it creates fear, batching, and destroys velocity, causing more harm than good. Resolution requires testing whether the 2-hour re-opt actually catches overfit strategies that a fast path would miss.

**Blocker inventory:**
- Pragmatist: The `composite_confidence` calculation.
- Futurist: Threshold drift / rule curve-fitting.
- Craftsman: The failure to separate boolean validation from heuristic scoring.
- Accelerator: The lack of a fast, deterministic validation path.
- Exploiter: The lack of a schema/trust boundary for JSON inputs.

**Evolution summary:**
Positions solidified. Pragmatist and Accelerator aligned on the geometric mean being a blocker. Craftsman and Exploiter aligned on the conceptual failure causing the security failure. Futurist remained steadfast on defending the slow, heavy tests against velocity.