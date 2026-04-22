# Loom Task: Add JSON Schema Validation
**Source:** Argus Elevation Plan (Blocker 3)
**Target:** `scripts/validation/pipeline.py`

Implement Pydantic models or strict schema validation for the raw optimizer dictionary inputs and `spike/leaderboard.json`. Remove the pipeline's implicit trust in the structure of injected payloads.