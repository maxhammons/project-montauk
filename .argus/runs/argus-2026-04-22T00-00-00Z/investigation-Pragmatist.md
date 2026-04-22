# Investigation: Pragmatist

## Does this need to exist?
I looked at the validation pipeline (`scripts/validation/pipeline.py`). It's 700+ lines of code whose primary job is passing dictionaries between layers and calculating a 10-variable geometric mean.

1. **The Scoring Composite is Indirection**: You have 10 sub-scores (walk_forward, marker_shape, fragility, etc.). You calculate a geometric mean to get a `composite_confidence`. This obscures what actually matters. A strategy passes with a 0.70, but no one knows *why* it passed without unpacking the math.
2. **Warning Bloat**: Every gate returns `advisories`, `soft_warnings`, `critical_warnings`, and `hard_fail_reasons`. This is ceremony. If a warning doesn't fail the build, it's noise.
3. **The "Skipped" Gate Pattern**: `_skip_gate` creates a mock result for a gate that didn't run. Delete the mock. If a gate doesn't run, don't include it in the payload.
4. **Over-engineered Gate 7**: The synthesis gate does nothing but re-pack dictionaries from the previous 6 gates.
5. **Tier Routing**: The system routes `T0`, `T1`, `T2`. It adds massive conditional logic to every gate. 

**What I investigated and ruled out:**
I thought the `ValidationContext` was unnecessary state passing, but it caches the null distribution and heavy computations, so it earns its keep.

**What I would need to see to change my mind:**
Evidence that this 10-variable geometric mean actually selects better strategies than a simple 3-rule hard-fail system.
