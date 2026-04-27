## Futurist — Round 3 Convergence

**Where I've landed:**
My position has tightened, not reversed. I no longer think the main danger is contradictory language in the abstract; I think the main danger is contradictory language attached to rewrite-capable trust state. Pragmatist and Exploiter moved me there. `scripts/certify/recertify_leaderboard.py`, `scripts/search/evolve.py`, and `scripts/search/spike_runner.py` mean Montauk is not just describing authority inconsistently, it is rewriting authority through multiple paths while `spike/leaderboard.json` preserves no validation-model provenance. The single most important blocker to the North Star is this fused memory-and-authority surface: the project wants durable leaderboard memory and trustworthy certification, but it currently stores those meanings in one mutable object without one invariant contract.

**Unexpected agreement:**
Pragmatist's narrower argument that the first move is deleting duplicate trust-writing paths landed harder for me than I expected. I still care about provenance first, but he is right that versioning four conflicting writers only gives you versioned ambiguity.

**Still contesting:**
I still contest any version of the Pragmatist remedy that implies collapse alone is enough. If the team removes duplicate scripts but keeps the present semantic mismatch between `promotion_ready`, `backtest_certified`, watchlist admission, and leaderboard meaning, it will end up with one cleaner path that still rewrites history unclearly. I would change my mind if the surviving path also wrote explicit validation-contract provenance per row and restored one invariant between Gate 7 and post-hoc certification flows.

**Missed opportunity:**
No one named a compatibility layer for old truth. Montauk needs a first-class "historical interpretation" surface: a way to read prior leaderboard rows under the contract that admitted them, not just to overwrite them under today's rules. Without that, every future recertification erases evidence about the system's own evolution.
