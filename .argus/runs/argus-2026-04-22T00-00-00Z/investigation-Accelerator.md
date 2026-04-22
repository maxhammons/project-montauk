# Investigation: Accelerator

## Can a new engineer ship safely today?
The primary blocker to velocity is the feedback loop length and the cognitive overhead of the validation payload.

1. **Feedback Loop Duration**: The validation pipeline runs up to a 2-hour re-optimization budget (`reopt_minutes`). If an engineer makes a change to a strategy, they have to wait hours to see if it passes Gate 6.
2. **Unpredictable Thresholds**: If an engineer asks "what score do I need on the Walk-Forward test?", the answer is "it depends on the other 9 scores." The geometric mean makes it impossible to reason locally about a strategy's success.
3. **Dictionary Boilerplate**: Adding a new metric requires updating 6 different places in `pipeline.py` (the sub-scores dict, the weights dict, the gate output, the unpacking logic). This is a massive friction point for extending the system.
4. **Silent Degradation**: Because hard-fails were demoted to warnings, a new engineer might break a core invariant, see "PASS" (because the composite stayed above 0.70), and ship a broken strategy.
5. **Testing the Tester**: There is no easy way to dry-run the pipeline. It requires a full `ValidationContext` with TECL data, null distributions, and a leaderboard read.

**What I investigated and ruled out:**
I was worried about the `multiprocessing` implementation, but it correctly initializes `_val_worker_init` once per worker to avoid redundant data loading. That part is operationally sound.

**What I would need to see to change my mind:**
A "fast-fail" mode that runs in 10 seconds and gives a deterministic answer on the core statistical tests without the heavy Gate 6 re-optimization.
