# Convergence Map

## Convergent Findings

### 1. The core blocker is a broken trust contract around leaderboard admission, `promotion_ready`, `backtest_certified`, and downstream artifact authority.
**Confidence:** strong  
**Support:** Pragmatist, Futurist, Craftsman, Accelerator, Exploiter  
**Why it converged:** All five agents now treat the trust boundary, not indicator math, as the main blocker to the North Star. The disagreement is about repair sequence, not whether the contract is broken.

### 2. Too many scripts can write, rewrite, or replay authority-bearing state around `spike/leaderboard.json`.
**Confidence:** strong  
**Support:** Pragmatist, Futurist, Accelerator, Exploiter; Craftsman agrees this makes honest semantics unstable  
**Why it converged:** The room repeatedly returned to `scripts/search/evolve.py`, `scripts/search/grid_search.py`, `scripts/search/spike_runner.py`, `scripts/certify/full_sweep.py`, and `scripts/certify/recertify_leaderboard.py` as overlapping trust-writing paths.

### 3. `spike/leaderboard.json` is currently trying to be both durable memory and authority surface.
**Confidence:** strong  
**Support:** Futurist, Craftsman, Accelerator, Exploiter; Pragmatist accepted the point in narrower form  
**Why it converged:** The board stores admitted rows that are not fully certified, yet downstream flows and some docs still treat it as stronger truth than the live state supports.

### 4. Restoring a single invariant between validation, certification, and promotion is necessary before the system can honestly function as an evidence machine.
**Confidence:** strong  
**Support:** Futurist, Craftsman, Accelerator, Exploiter; Pragmatist accepts this so long as it happens through path collapse rather than documentation-only repair  
**Why it converged:** The room repeatedly identified the mismatch between Gate 7 semantics and post-hoc certification flows as the sharpest expression of the trust failure.

### 5. The repo needs semantic-layer tests, not just engine regression tests.
**Confidence:** moderate  
**Support:** Craftsman, Accelerator, Exploiter; consistent with Futurist's provenance concerns  
**Why it converged:** Multiple agents independently named missing fixture-level trust-contract tests as the cheapest guard against recurrence.

## Genuine Contests

### Contest 1: Sequence — collapse duplicate trust-writing paths first, or define/version the contract first?
- **Pragmatist position:** collapse duplicate trust-writing paths first; otherwise the team preserves too much ceremony and ends up with versioned ambiguity.
- **Futurist / Craftsman / Accelerator / Exploiter position:** simplification alone is not enough unless the surviving path also restores one invariant definition of trust; provenance and contract repair cannot be deferred behind deletion.
- **What is actually contested:** whether path collapse is the first move, or whether the first move must be a combined patch that formalizes semantics and removes duplicate writers at the same time.
- **What would resolve it:** concrete proof that the surviving authority-writing path can, in one patch, both reduce writers and enforce the intended invariant. If not, provenance-first arguments gain force.

### Contest 2: Is the biggest near-term risk mainly operational confusion or authority laundering?
- **Accelerator position:** the highest-leverage reading is operational delegation and newcomer-unsafety; ambiguity blocks safe shipping.
- **Exploiter position:** the same ambiguity is more severe because it already permits authority to move without being re-earned.
- **What is actually contested:** emphasis, not existence. Both accept the same broken boundary; they differ on whether the main harm is sociotechnical velocity loss or exploit-like authority propagation.
- **What would resolve it:** proof that current flows can or cannot turn softer leaderboard state into authoritative-looking artifacts without full revalidation.

## Ignored Arguments

No meaningful Round 1 argument was ignored. The room converged heavily, but it did not do so by silence.

## Position Evolutions

- **Pragmatist:** from “delete ceremony” to “delete duplicate trust-writing paths first.”
- **Futurist:** from generic semantic lock-in to contradictory language attached to rewrite-capable state surfaces.
- **Craftsman:** from conceptual dishonesty in the abstract to semantic dishonesty as a live control surface with operational consequences.
- **Accelerator:** from “one operational boundary” to “one honest trust contract plus one thin promotion path.”
- **Exploiter:** from fused memory/authority generally to one broken invariant plus duplicate write paths as the cleanest authority-laundering chain.

## Blocker Inventory

- **Pragmatist:** duplicate trust-writing paths around `spike/leaderboard.json`
- **Futurist:** fused memory-and-authority in `spike/leaderboard.json` without one invariant trust contract
- **Craftsman:** broken trust contract between `promotion_ready`, `backtest_certified`, leaderboard admission, and downstream artifact authority
- **Accelerator:** humans still have to carry the real trust contract in their heads
- **Exploiter:** authority can move without being re-earned because admission, certification, and replay do not share one enforced invariant

## Missed Opportunities

- Make per-run validation artifacts immutable and derive leaderboard / watchlist / operator surfaces from those artifacts instead of treating the leaderboard as writable source of truth. (Pragmatist)
- Introduce a historical interpretation layer so old leaderboard rows can be read under the contract that admitted them rather than silently overwritten by current rules. (Futurist)
- Add semantic-layer tests that pin the allowed relationship between `promotion_ready`, `backtest_certified`, leaderboard eligibility, and champion finalization. (Craftsman)
- Add a fast trust-contract smoke test so scoring-model changes cannot silently mutate meaning. (Accelerator)
- Store row-level trust provenance in `spike/leaderboard.json`, including admitting script, admission rule, and whether certification was primary or post-hoc. (Exploiter)

## Evolution Summary

The room moved from a broad “validation semantics are drifting” narrative toward a sharper, more actionable frame:

1. One broken invariant matters more than general drift.
2. Multiple authority-writing paths are why the problem persists.
3. The leaderboard is acting as both memory and trust boundary.
4. The live disagreement is now about sequence, not diagnosis.
