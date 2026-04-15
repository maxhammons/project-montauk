# Pragmatist Scratchpad

I read the North Star. I looked at the codebase. We have a problem.

## The Optimization Target
The charter says we are optimizing for "share-count multiplier vs B&H" and we don't care about trade frequency.
The code actually optimizes for dollar `vs_bah` and includes a `trade_scale` punishment factor.

This means we built a nine-layer validation pipeline to optimize the wrong metric. We are evaluating hundreds of strategies against a target that is explicitly documented as deprecated. This is the definition of complexity that isn't earning its keep. We are validating against a ghost. Fix the metric in the code. Stop punishing trade frequency if the charter says we don't care about it.

## The Strategy Graveyard
Look at `scripts/strategies.py`. It's over 3,500 lines long. It contains dozens, maybe hundreds of strategies.
`evolve.py` has a `PRUNE_RUNS` variable to skip strategies that don't beat the baseline.
Why are they still in the file?
If a strategy fails validation, delete it.
If it doesn't beat the baseline, delete it.
We are carrying the corpse of every failed idea in the main execution path.
This is not a museum. The historical strategy archives exist (`src/strategy/archive/`). Move them there, or better yet, just delete them. Version control remembers.

## The Translation Tax
Look at `scripts/pine_generator.py`. 3,300 lines of explicit string generation.
We wrote an entire shadow codebase to translate Python back into Pine Script.
I get why it exists — TradingView runs Pine, we run Python.
But the fact that it requires 3,300 lines of explicit, per-family generation means our Python abstractions and Pine primitives aren't aligned.
It's a massive maintenance tax. If you change a strategy in Python, you have to write a custom string formatter for it in Pine.
This is brittle plumbing. The generator is explicit per strategy family because the abstractions don't hold up across the language barrier.

## The Validation Ceremony
Look at `scripts/validation/`. Nine files.
`pipeline.py`, `candidate.py`, `walk_forward.py`, `uncertainty.py`, `cross_asset.py`, `sprint1.py`, `deflate.py`.
This is a validation framework that thinks it's a PhD thesis.
Are we trying to trade TECL or win a Nobel prize?
What breaks if we remove half of these?
If the strategy beats the hand-marked cycle dataset and out-of-sample data, what does "cross-asset validation" actually save us from? If it works on TECL, it works on TECL.
We are trying to mathematically prove an edge with a complexity that introduces its own statistical errors.

## The Engine Duplication
We have `scripts/strategy_engine.py` and `scripts/backtest_engine.py`.
Why do we have two engines?
One of them is likely wrapping the other, or they evolved concurrently and no one merged them.
I want to see the call graph. If one is just passing data through to the other without transforming it, the layer needs to go. The whole layer is a function call with extra steps.

## My Stance
1. Fix the optimization target. Change the code to use the share-count multiplier.
2. Delete the trade frequency punishment. The charter says it's gone, so remove the code.
3. Delete every strategy in `strategies.py` that doesn't currently beat Montauk 8.2.1. We don't need a museum of failures.
4. Consolidate the validation pipeline. If we're optimizing for the right metric, we don't need nine layers of statistical deflation to tell us if a line goes up.

I am not against validation. I am against building a machine that is more complicated than the problem it solves.
Our problem is beating buy-and-hold on a 3x leveraged ETF.
The solution is finding an edge, not building an impenetrable fortress of code to protect an edge we haven't found yet.

We are solving for scale we don't have, using metrics we don't believe in, protected by validation we can't easily debug.

Delete the dead strategies.
Fix the metric.
Simplify the pipeline.
