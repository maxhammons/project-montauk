# Loom Task: Revert Demoted Fails
**Source:** Argus Elevation Plan (Blocker 2)
**Target:** `scripts/validation/pipeline.py`

Revert the April 21 demotion of hard-fails to warnings in Gate 4 (Walk-Forward), Gate 5 (Morris/Bootstrap), and Gate 6 (Cross-Asset). If out-of-sample statistical validation fails, the strategy must hard-fail.