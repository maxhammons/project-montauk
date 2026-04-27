# Loom Task: Replace Geometric Mean with Hard-Fails
**Source:** Argus Elevation Plan (Blocker 1)
**Target:** `scripts/validation/pipeline.py`

Replace the `composite_confidence` 10-variable geometric mean with a strict boolean hard-fail system for non-negotiable invariants. Move all heuristic metrics into an "advisory score" that does not dictate the PASS/FAIL verdict.