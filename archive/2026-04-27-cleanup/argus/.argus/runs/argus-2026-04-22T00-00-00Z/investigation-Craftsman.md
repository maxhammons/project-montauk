# Investigation: Craftsman

## Is this honest?
The validation pipeline's vocabulary is actively misleading the developer.

1. **Gates that do not gate**: `_gate_marker_shape` always returns `"verdict": "PASS"`. A gate that cannot fail is not a gate; it is an observer. Calling it a gate creates a false sense of security.
2. **Warnings that do not warn**: The system tracks `critical_warnings` and `soft_warnings`, but explicitly states "Warnings (soft/critical) no longer drive verdict — they're advisory." An advisory is not a warning. 
3. **Composite "Confidence"**: The `composite_confidence` metric is a weighted geometric mean of penalties. It is not a measure of statistical confidence; it is a heuristic penalty score.
4. **Mock Results**: `_skip_gate` returns a populated dictionary for a test that never ran. The code lies about its own execution path to satisfy a fixed data shape.
5. **Vocabulary Inflation**: We have `promotion_ready`, `clean_pass`, and `backtest_certified`. This means the domain model is confused. If you have three different ways to say "it passed," you don't know what passing means.

**What I investigated and ruled out:**
I checked the core mathematical implementations (e.g., `_interp` and `_clamp`). They are honest and do exactly what they claim.

**What I would need to see to change my mind:**
Rename `_gate_marker_shape` to `_observe_marker_shape`. Remove the mock dictionaries. Make the types reflect the actual data, not a theoretical uniform interface.
