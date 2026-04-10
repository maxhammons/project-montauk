# Investigation: The Futurist

**Frame:** What happens in 18 months?

## Observations
1. **The Translation Gap:** In 18 months, the gap between the Python strategies in `strategies.py` and the Pine Script in `src/strategy/active/` will widen into an unbridgeable chasm. The team is adding complex VIX indicators and walk-forward validation. Python is flexible; Pine Script is rigid. Eventually, a highly profitable strategy will be discovered in Python that cannot be accurately or performantly expressed in Pine Script. 
2. **Hardcoded Asset Focus:** The pipeline is entirely hardcoded around TECL (`get_tecl_data`, "Beat Buy & Hold on TECL"). When the team wants to apply this exact same pipeline to TQQQ, SOXL, or crypto, the tight coupling between the data fetcher, the fitness function, and the asset will require a painful extraction of "TECL" from the core engine.
3. **Overfitting to the Fitness Formula:** The fitness formula in `evolve.py` is becoming a massive algebraic polynomial (`vs_bah * trade_scale * hhi_penalty * dd_penalty * complexity_penalty * regime_mult`). In 18 months, the optimizer won't be finding trading strategies; it will be finding mathematical loopholes in this specific penalty structure.

## What I Ruled Out
- I ruled out the idea that TradingView will be replaced. The fact that the output is explicitly structured around Pine Script v6 indicates that TradingView is a hard dependency for execution, likely due to brokerage integrations or charting preferences.

## What Would Change My Mind
- If the project introduces an automated Python-to-Pine generator, the translation gap ceases to be a terminal risk. If the fitness penalties are replaced by purely out-of-sample walk-forward results, the equation-gaming risk disappears.