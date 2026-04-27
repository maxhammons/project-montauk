# Execution Verdicts — Apr-09

## Claim 1: The hash index cache is vulnerable to engine-version poisoning (The Exploiter)
**Status:** **PROVEN**
**Evidence:** Code inspection of `scripts/evolve.py:config_hash(strategy_name: str, params: dict) -> str` confirms that the deterministic SHA-256 hash is generated strictly from the string `strategy_name` and the JSON dump of the `params` dictionary.
If `strategy_engine.py` is modified (e.g., a bug in slippage or regime calculation is fixed), the `config_hash` for a given set of parameters remains identical. `evolve_chunk` will then load the stale, bug-affected metrics from `hash-index.json` instead of re-evaluating the strategy under the new, correct engine logic. 
**Resolution:** The cache hash must incorporate a version stamp of the engine or be aggressively wiped whenever core logic changes.

## Claim 2: The fitness formula obscures the stated target (The Craftsman/Futurist)
**Status:** **PROVEN**
**Evidence:** `evolve.py:fitness()` computes the final score as `vs_bah * trade_scale * hhi_penalty * dd_penalty * complexity_penalty * regime_mult`. While `CLAUDE.md` states the goal is to beat buy-and-hold, a strategy that achieves `vs_bah = 1.5` but has `num_trades = 4` receives a zero multiplier due to the hard gates (`if num_trades < 5: return 0.0`). The final score does not reflect pure market performance; it reflects a heavily guarded algebraic aesthetic.