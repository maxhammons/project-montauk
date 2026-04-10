# TASK: Build Deployment Injection Script

**Context:** Transferring optimized params from Python to TradingView Pine Script is a manual air-gapped process causing significant friction.
**Action:** Write a Python script to read `results.json` and inject params into `Project Montauk 8.2.1.txt` via regex replacement on `defval=` arguments.