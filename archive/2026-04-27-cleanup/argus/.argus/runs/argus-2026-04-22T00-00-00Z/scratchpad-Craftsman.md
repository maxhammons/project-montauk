# Craftsman Scratchpad
- Looking at `pipeline.py`.
- `_gate_marker_shape` is called a gate, but the code explicitly says `verdict = "PASS"`.
- `composite_confidence` isn't confidence, it's a weighted penalty score.
- `_cert_check` sets status to "missing" or "pending". 
- `backtest_certified` vs `promotion_ready`.
