# TASK: Fix Unversioned Cache Poisoning

**Context:** The `config_hash` in `evolve.py` does not hash the engine source code, leading to stale fitness scores persisting after backtester bug fixes.
**Action:** Modify `config_hash` to include an engine version or hash of `strategy_engine.py` and `evolve.py`.