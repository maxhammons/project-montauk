# Meta-Strategy Design: Confidence-Weighted Regime Ensemble (Chimera)

**Status: CONDITIONAL / DEFERRED WITHIN 3.x (updated 2026-07-21).** Do not
implement this as standing 3.0 infrastructure until Montauk has several
materially independent Gold families and an agreed way to measure/control that
dependence. Chimera is optional research, not a 3.0 completion requirement.

**Goal:** Test whether several genuinely different Gold strategies can combine
their votes or confidence estimates into a more defensible TECL signal than the
best single strategy.

## Architecture

The meta-strategy will operate as an ensemble candidate:

1.  **Gold Ingestion:** It queries current, latest-contract Gold certifications
    rather than reading a fixed number of rows from a JSON file. Pending Gold,
    stale, revoked, and historical rows cannot vote.
2.  **Dependence Control:** It groups or downweights correlated configurations so
    thousands of variants from one family cannot dominate the vote. Eligibility
    requires materially independent mechanisms/signals, not merely different
    parameter hashes.
3.  **Regime Detection:** It uses a frozen, real-time-observable classifier with
    no lookahead to describe the current environment.
4.  **Base Weighting:** Each eligible exact configuration receives a predeclared
    weight from Validation Score, deployable performance evidence, and effective
    independence. A composite score must not be treated as a calibrated
    probability unless forward calibration supports that claim.
5.  **Regime Adjustment:** A predeclared rule may scale weights by each frozen
    strategy's performance in similarly classified historical regimes.
6.  **Signal Aggregation:** Each strategy emits `risk_on` or `risk_off`; the
    Chimera combines those signals under a frozen threshold or confidence rule.

## Key Components

*   **Meta-strategy evaluator:** Runs the ensemble as an ordinary, frozen
    candidate definition.
*   **Regime classifier:** Identifies the current regime using only information
    available at that bar. Named historical episodes are diagnostics, not a
    real-time classifier.
*   **Dependence/weight calculator:** Controls family duplication and signal
    correlation before applying confidence/regime adjustments.

## Data Flow

1.  Load verified point-in-time TECL data and any approved causal regime inputs.
2.  Load leaderboard strategies and their parameters/metrics.
3.  For each bar:
    a. Determine the current regime state.
    b. Calculate dynamic weights for all strategies.
    c. Run each strategy's logic for the current bar to get its individual signal.
    d. Aggregate the weighted signals.
    e. Determine the meta-signal based on the threshold.
4.  Track performance and emit standard artifacts (trade ledger, etc.) just like a single strategy.

## Error Handling & Edge Cases

*   **Missing Data:** A predeclared policy determines whether a missing vote is
    excluded, held, or makes the ensemble unavailable. It may not change after
    results are seen.
*   **Regime Ambiguity:** If the current market does not strongly fit a defined
    regime, weights fall back to the frozen base-weight rule rather than an
    improvised interpretation.
*   **Tie-Breaking:** The exact hold-versus-risk-off rule is frozen before the
    search. It cannot be selected after seeing which choice backtests better.

## Testing Strategy

*   **Unit Tests:** Verify the weight calculation logic correctly applies confidence and regime modifiers.
*   **Integration Tests:** Ensure the meta-engine correctly aggregates signals from known, mock strategies and respects the voting threshold.
*   **Regression and certification:** The ensemble runs through the same complete
    backtest, validation, search-accounting, and Gold contract as every other
    candidate. Gold constituents do not make the combination Gold.
*   **Baseline comparison:** Gold eligibility uses the same TECL B&H contract as
    any other candidate. Separately, the Chimera research is successful only if
    it demonstrates improvement over the best eligible single strategy under the
    same execution/evidence contract; that comparison is not an extra Gold gate
    unless Max explicitly makes it one.

## Authority

A Gold Chimera automatically joins the leaderboard like any Gold configuration.
It first follows the same Pending Gold forward-evidence path, receives no special
rank or activation privilege, and normal active-strategy changes still require
Max's approval. If no Chimera beats the best single strategy, the correct outcome
is to keep the single strategy.

## Prerequisites

- several materially independent current Gold families;
- a versioned dependence metric and duplicate-family control;
- a rule that treats “family” as same trigger graph/parameter schema for
  organization while estimating actual dependence from signals and returns;
- enough evidence to estimate regime behavior without turning regime labels into
  another overfit search;
- the same deployable execution contract used by individual strategies; and
- full accounting of Chimera membership, weight, threshold, and regime searches.

---

*This remains a research design. It is not an implementation plan until the
prerequisites above are met and Max explicitly chooses to schedule it. A new #1,
new Gold row, or leaderboard shuffle never triggers Chimera work by itself.*
