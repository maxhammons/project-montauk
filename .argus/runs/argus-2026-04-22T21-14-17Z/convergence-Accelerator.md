## Accelerator — Round 3 Convergence

**Where I've landed:**
My position has narrowed, not reversed. I started with "one operational boundary"; I now think the minimum complete fix is one honest trust contract plus one thin promotion path with the `promotion_ready` / `backtest_certified` invariant restored. Pragmatist and Futurist moved me here: deletion matters because too many scripts (`evolve.py`, `spike_runner.py`, `recertify_leaderboard.py`) write trust state, but semantic cleanup matters because a simplified path that still mislabels authority will remain newcomer-unsafe. The single most important blocker to the North Star is that Montauk still makes humans carry the real trust contract in their heads instead of enforcing and stating it in one place.

**Unexpected agreement:**
I did not expect to agree this strongly with Exploiter's argument that the problem is an authority-laundering surface, but I do now. The key point is not adversarial abuse; it is that `scripts/search/spike_runner.py` can patch certification after artifact generation, which means authority can move through maintenance flows instead of being earned once at the boundary.

**Still contesting:**
I still contest any version of Pragmatist's argument that simplification should come first if it is understood mainly as deletion. If you remove duplicate paths without first pinning one canonical meaning for leaderboard rows, you get a cleaner repo that can still teach the wrong rule. I would change my mind if the team could show one surviving entrypoint whose code, docs, and persisted state all already agree on what a row means.

**Missed opportunity:**
No one has named the need for a fast trust-contract smoke test: a tiny fixture-based suite that asserts the allowed combinations of `verdict`, `promotion_ready`, `backtest_certified`, and leaderboard eligibility. That is the cheapest way to stop this specific ambiguity from reappearing every time the scoring model changes.
