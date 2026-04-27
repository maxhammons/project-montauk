# Investigation: Pragmatist

## Observations

1. **Optimizing the Wrong Metric:** The codebase evaluates strategies against dollar return (`vs_bah`) and penalizes trade frequency, despite the North Star explicitly stating the goal is "share-count multiplier vs B&H" with no trade-frequency punishment. We are running a massive optimization engine against deprecated rules.
2. **Strategy Graveyard:** `scripts/strategies.py` is over 3,500 lines long, carrying dozens of failed or pruned strategies. The evolution engine (`evolve.py`) actively skips them via `PRUNE_RUNS`. They are dead weight and should be deleted; Git remembers them.
3. **Validation Ceremony:** The `scripts/validation/` directory contains 9 layers of complex statistical checks (`deflate.py`, `cross_asset.py`, `walk_forward.py`, etc.). This is academic ceremony. If a strategy beats the hand-marked baseline and holdout data, half of these layers are unnecessary indirection that only introduce maintenance burden.
4. **Translation Tax:** `scripts/pine_generator.py` is 3,300 lines of explicit, per-family string formatting to convert Python back into Pine Script. This isn't an abstraction, it's brittle plumbing. It proves the Python and Pine models aren't unified.
5. **Engine Duplication:** The existence of both `scripts/strategy_engine.py` and `scripts/backtest_engine.py` suggests layered indirection where one engine just feeds the other. This needs to be consolidated into a single straightforward entry point.

## What I investigated and ruled out
I investigated whether the complex Pine generation (`pine_generator.py`) could be easily deleted. I ruled it out because TradingView inherently requires Pine Script to run the systems, so some form of translation is required. However, the *complexity* of the generator is the issue, not its existence. 

## What I would need to see to change my mind
I would need to see empirical evidence that the 9-layer validation pipeline in `scripts/validation/` has actively caught and prevented a false-positive strategy that a simpler 2-layer out-of-sample test would have missed. Show me the specific strategy that passed basic holdout but failed `cross_asset.py` and saved us money. If you can't, I want the extra layers deleted. I also need to see why `strategy_engine` and `backtest_engine` both exist—if one handles purely metrics and the other handles raw arrays, the naming should reflect that, or they should be merged.