# Meta-Strategy Design: Confidence-Weighted Regime Ensemble

**Goal:** Create a meta-strategy that aggregates signals from the leaderboard strategies, weighting their votes by their certified composite confidence score and their historical performance in the current market regime.

## Architecture

The meta-strategy will operate as an ensemble model:
1.  **Leaderboard Ingestion:** It loads the top strategies from `spike/leaderboard.json`, filtering for those that are `certified_not_overfit` and `backtest_certified`.
2.  **Regime Detection:** It uses the existing `regime_helpers.py` (or similar logic) to classify the current market environment (e.g., bull, bear, chop, recovery).
3.  **Dynamic Weighting:** Each strategy's base voting power is determined by its `composite_confidence` score (from validation gate 7). This ensures heavily scrutinized strategies have more influence than marginal ones.
4.  **Regime Adjustment:** The base weight is then scaled by the strategy's historical performance (e.g., its `share_multiple` or `fitness`) specifically in the currently detected regime.
5.  **Signal Aggregation:** On each bar, all eligible strategies generate a `risk_on` or `risk_off` signal. The meta-strategy calculates a weighted sum of the "risk on" votes.
6.  **Threshold Execution:** If the weighted sum exceeds a defined threshold (e.g., 60% of total possible weighted votes), the meta-strategy emits a `risk_on` signal; otherwise, `risk_off`.

## Key Components

*   **`MetaStrategy` Engine:** A new class (likely in a new file `scripts/engine/meta_engine.py` or added to `strategy_engine.py`) that orchestrates the ensemble.
*   **Regime Classifier:** A robust method to identify the *current* regime in real-time without lookahead bias. We will need to adapt the historical regime definitions in `leaderboard.json` (like `early_tech_bull`, `covid_crash`) into real-time detectable states based on indicators (e.g., moving averages, volatility).
*   **Weight Calculator:** A function to dynamically calculate the voting weight for each strategy on every bar based on confidence and the active regime.

## Data Flow

1.  Load OHLCV data.
2.  Load leaderboard strategies and their parameters/metrics.
3.  For each bar:
    a. Determine the current regime state.
    b. Calculate dynamic weights for all strategies.
    c. Run each strategy's logic for the current bar to get its individual signal.
    d. Aggregate the weighted signals.
    e. Determine the meta-signal based on the threshold.
4.  Track performance and emit standard artifacts (trade ledger, etc.) just like a single strategy.

## Error Handling & Edge Cases

*   **Missing Data:** If a strategy relies on data not available (e.g., early in the backtest), its vote is excluded from the total.
*   **Regime Ambiguity:** If the current market doesn't strongly fit a defined regime, weights default closer to the base `composite_confidence`.
*   **Tie-Breaking:** If the weighted vote is exactly on the threshold, the system should default to the safer stance (likely `risk_off` or hold previous state).

## Testing Strategy

*   **Unit Tests:** Verify the weight calculation logic correctly applies confidence and regime modifiers.
*   **Integration Tests:** Ensure the meta-engine correctly aggregates signals from known, mock strategies and respects the voting threshold.
*   **Regression:** The meta-strategy must run through the standard validation pipeline (Gates 1-7) to ensure the *ensemble itself* is robust, not just its constituents.

---

*This design has been documented here for review before proceeding to the implementation plan.*