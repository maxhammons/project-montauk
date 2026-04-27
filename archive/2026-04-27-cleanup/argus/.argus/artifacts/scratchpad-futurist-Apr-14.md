# Futurist Scratchpad

## Initial Assessment
The team is building the "Montauk Engine", an automated strategy discovery and validation pipeline. They are transitioning from manual Pine Script intuition to brute-force and evolutionary Python search. This is a massive shift in trajectory. However, the Python engine is being built with the architectural assumptions of a single-developer, single-asset, single-node script.

The cost of these decisions will come due precisely when the engine "succeeds" and they want to scale it up.

## The Cache Invalidation Timebomb
In `evolve.py`, there is a function `_compute_engine_hash()`:
```python
def _compute_engine_hash() -> str:
    # ...
    for filename in ("strategy_engine.py", "evolve.py", "strategies.py"):
        with open(path, "rb") as f:
            digest.update(f.read())
```
This is an irreversible coupling between file formatting and compute history. Every time a parameter combination is tested, it gets hashed with this engine hash and stored in `hash-index.json`. 
Trace this forward: The evolutionary optimizer runs for a week. A developer realizes a comment in `strategies.py` has a typo, or runs `black`/`ruff` on the codebase. The engine hash changes. The entire cache of thousands of hours of compute time is instantly invalidated. You cannot refactor or document your strategy logic without destroying your historical data. This forces the code to rot because developers will be terrified to touch the files.

## The Generation Bottleneck
`pine_generator.py` uses string formatting blocks like `_build_montauk_821(params: dict)`.
The Python backtester (`backtest_engine.py`) and the Pine Script generator are disconnected. The system only evolves *parameters*, not *logic*. The stated goal is "automated strategy discovery", but the current architecture limits discovery to the bounds of the hardcoded Pine templates.
Trace this forward 18 months: They want the optimizer to discover a new type of exit condition (e.g., using RSI instead of ATR). It can't. A human has to write the Pine Script template, then write the exact replica in Python, then expose the parameters. The "automated discovery" is an illusion; it's just automated parameter tuning. When they actually want to evolve ASTs or logic trees, this string-generation architecture will have to be completely thrown away.

## The Single-Asset Hardcoding
The data pipeline (`data.py`) and validation scripts explicitly import `get_tecl_data`. The entire system assumes TECL.
Trace this forward: The strategy starts degrading on TECL, and they decide to apply the Montauk Engine to TQQQ, SOXL, or a basket of crypto. The entire validation pipeline breaks. `get_tecl_data()` is hardcoded everywhere. The concept of an "Asset" or "Universe" doesn't exist. They will have to fork the codebase or do a massive, painful rename/refactor across the entire validation suite just to test a second ticker.

## The Monolithic Cache File
`evolve.py` relies on `hash-index.json` to store run history.
Trace this forward: They hit the limit of single-thread evolution and try to run `evolve.py` on AWS Batch or a 64-core machine using multiple processes. `hash-index.json` has no file locking. Concurrent writes will corrupt the JSON. If they try to load it into memory, a million-entry JSON dictionary will blow up the RAM. This local-file assumption forecloses the option of distributed compute, which is mandatory for genetic algorithms over large search spaces.

## The Fitness Function Disconnect
The North Star document notes a tension: the charter demands maximizing "share-count multiplier vs B&H", but the Python scripts are using dollar `vs_bah`.
Trace this forward: They run the optimizer for 6 months, find the "perfect" strategy, and deploy it. During a severe bear market, the strategy exits to cash, preventing a dollar drawdown. But because it doesn't re-enter optimally to accumulate shares at the bottom, it loses the share-count compounding effect when the bull market resumes. The architectural decision to optimize for dollar value instead of share accumulation means the engine is systematically selecting for the wrong mathematical outcome based on the charter. By the time they realize it, the entire validated strategy archive is useless.
