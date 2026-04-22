# Pragmatist Scratchpad
- Reading `scripts/validation/pipeline.py`
- It's 700 lines of dictionary manipulation.
- `_gate7_synthesis` unpacks 7 different dictionaries just to build another dictionary.
- The `_geometric_composite` has 10 sub-scores. Do we really need 10 sub-scores?
- "2026-04-21 revision: these no longer hard-fail." - The pipeline is accumulating complexity just to avoid failing strategies.
