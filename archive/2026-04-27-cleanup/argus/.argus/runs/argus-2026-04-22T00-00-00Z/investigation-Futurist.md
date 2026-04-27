# Investigation: Futurist

## What happens in 18 months?
The validation pipeline is currently undergoing "threshold drift." I am looking at the trajectory of the rules.

1. **Curve-fitting the Validator**: The comments explicitly state: "2026-04-21 revision: these no longer hard-fail." Hard fails in Walk-Forward, Morris Fragility, and Bootstrap were demoted to warnings to allow strategies to pass. The team is overfitting the validation pipeline to the strategies they want to accept.
2. **The Scoring Math Trap**: The shift from boolean hard-gates to a weighted geometric mean (`composite_confidence`) is a one-way door. In 18 months, this equation will have 25 weights, and it will be impossible to tune one without breaking the leaderboard.
3. **Cross-Asset Abandonment**: They demoted the `cross_asset` check because it "penalized TECL-specific era winners." They are explicitly locking into single-asset curve fitting. When TECL behavior shifts, this system will fail catastrophically.
4. **Leaderboard Coupling**: The pipeline reads `leaderboard.json` to determine history state. The validator's logic depends on its own past outputs. This is a feedback loop that will amplify biases.
5. **Tier Escalation**: T0, T1, T2. In 18 months, there will be T3 and T4, each with custom exceptions.

**What I investigated and ruled out:**
I was worried the execution engine (`strategy_engine.py`) was getting too complex, but it looks like Phase 7 actually consolidated it successfully. The complexity has simply migrated to the validation layer.

**What I would need to see to change my mind:**
A frozen, immutable validation standard. If the rules stop changing every week (three revisions in April 2026 alone), the trajectory stabilizes.
