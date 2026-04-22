## North Star (confirmed)

This codebase is trying to become a trustworthy TECL decision factory: a system that can generate, stress-test, rank, and certify long-only TECL timing strategies, then hand a human operator a clean `risk_on` / `risk_off` contract plus a native HTML review surface for manual execution. The center of gravity has shifted away from one-off strategy tuning toward a governed pipeline where Spike is the search surface and the Montauk Engine is the evidence machine: data integrity, tier-routed validation, certification artifacts, and durable leaderboard memory. The productive tension is that some docs still describe a single PASS champion, while the newer validation model and leaderboard logic are pulling toward a confidence-ranked watchlist of deployable TECL strategies that can be re-scored as evidence changes.

Roundtable refinement: the vision is still correct, but the repo is already partway into a watchlist-plus-certification model and has not finished the contract that makes that model trustworthy.

## Current State Assessment

Montauk is not a toy and it is not blocked by weak engine work. The repo has real seriousness around data quality, regression protection, long-run operational safety, and artifact generation, which means the underlying system can plausibly carry the North Star. The gap is higher in the stack: the trust boundary around `verdict`, `promotion_ready`, `backtest_certified`, leaderboard admission, and downstream artifact authority is contradictory in code, docs, and persisted state. Execution proved that softer rows can be admitted, that post-hoc finalization can sever `backtest_certified` from `promotion_ready`, and that maintenance flows can replay leaderboard state into fresh artifacts without rerunning the full contract. This is a codebase that can reach the vision, but only after structural trust work. Right now the evidence machine computes more honestly than it speaks.

## Opportunities (X -> X+1)

### Canonical Trust Boundary Reset
- **What it is:** Define one enforced contract for `verdict`, `promotion_ready`, `backtest_certified`, leaderboard eligibility, and champion finalization, then make one canonical path own authority-bearing writes. Treat the first move as combined, not sequential: restore the invariant and reduce writers together.
- **Why it matters for the North Star:** The North Star depends on handing a human a clean contract. That is impossible while authority can move without being re-earned and while different scripts imply different meanings for the same row.
- **What makes it achievable:** The seam is already visible. Gate 7 defines the stricter invariant, the execution verdicts isolated the break, and the hot spots are concentrated in a small set of scripts rather than spread across the whole repo.
- **Source:** Emerged across the roundtable, with the Exploiter's invariant-break framing, the Pragmatist's path-collapse framing, and the Accelerator's "one honest contract plus one thin promotion path" synthesis carrying the decision.
- **Effort:** medium

### Immutable Evidence Ledger With Derived Views
- **What it is:** Make per-run validation and certification artifacts the canonical evidence, then derive leaderboard, watchlist, and operator-facing surfaces from those artifacts instead of treating `spike/leaderboard.json` as writable source truth.
- **Why it matters for the North Star:** Durable leaderboard memory only helps if memory and authority are not fused. Derived views let you preserve history without letting replay paths silently harden softer state.
- **What makes it achievable:** The repo already emits standardized run artifacts, already backfills and rebuilds views from state, and already distinguishes research/admitted/watchlist concepts in parts of the UI. The architecture is close; the ownership line is what is missing.
- **Source:** Pragmatist's Round 3 missed opportunity, reinforced by Futurist and Exploiter.
- **Effort:** high

### Historical Trust Provenance
- **What it is:** Stamp rows and derived views with the admitting rule, admitting script, certification mode, and validation-contract version, then add a compatibility layer so old rows can be interpreted under the contract that admitted them instead of silently rewritten under today's meaning.
- **Why it matters for the North Star:** A decision factory with durable memory cannot force future readers to recover trust semantics by code archaeology. Provenance is what lets memory stay durable when rules evolve.
- **What makes it achievable:** Recertification already touches the whole board, the row schema is small enough to extend, and the current pain is narrowly defined around trust-bearing fields rather than every metric in the system.
- **Source:** Futurist's main argument, extended by Exploiter's call for row-level provenance and supported by the witness recommendations.
- **Effort:** medium

## Blockers

### Broken Certification Invariant
- **What it is:** The repo's own stricter rule says `backtest_certified` should require `promotion_ready` plus passing certification checks, but post-hoc finalization can set `backtest_certified=True` from the checks alone.
- **Which opportunity it blocks:** Canonical Trust Boundary Reset; Immutable Evidence Ledger With Derived Views
- **Confidence:** Confirmed
- **Roundtable position:** Exploiter surfaced it, Craftsman and Accelerator strengthened its importance, Futurist treated it as proof that semantics are attached to rewrite-capable state, and the Execution Agent reproduced it directly.

### Duplicate Authority-Writing And Replay Paths
- **What it is:** Multiple scripts can admit, rewrite, rebuild, or replay trust-bearing state around `spike/leaderboard.json`, which means authority does not have one owner.
- **Which opportunity it blocks:** Canonical Trust Boundary Reset; Immutable Evidence Ledger With Derived Views; Historical Trust Provenance
- **Confidence:** Confirmed
- **Roundtable position:** Pragmatist centered this blocker, Futurist accepted it as the reason provenance cannot be the only fix, Accelerator tied it to delegation risk, and the Execution Agent proved soft admission and maintenance replay paths are live.

### Fused Memory And Authority Surface
- **What it is:** `spike/leaderboard.json` is currently acting as durable memory, ranking surface, and downstream authority source at the same time, even though the rows it stores do not all represent the same level of trust.
- **Which opportunity it blocks:** Immutable Evidence Ledger With Derived Views; Historical Trust Provenance
- **Confidence:** Strong
- **Roundtable position:** Futurist, Craftsman, Accelerator, and Exploiter treated this as a core architectural blocker; Pragmatist accepted it in narrower form and proposed deriving views from immutable artifacts.

### Unpinned Semantic Contract
- **What it is:** The repo lacks fixture-level tests and explicit exported language that pin the allowed relationship between leaderboard eligibility, `promotion_ready`, `backtest_certified`, and champion finalization.
- **Which opportunity it blocks:** Canonical Trust Boundary Reset; Historical Trust Provenance
- **Confidence:** Moderate
- **Roundtable position:** Craftsman, Accelerator, and Exploiter named the semantic test gap directly, Futurist's provenance argument depends on the same missing seam, and the witness recommended a semantic smoke test as the cheapest guard against recurrence.

## The Sequence

1. Canonical Trust Boundary Reset
   Why first: This is the only move that clears the live execution-proven trust failure and unlocks every later improvement. It must be a combined patch, not a debate outcome. If you only formalize semantics, the current writers keep replaying ambiguity. If you only collapse paths, the surviving path can still break the invariant.

2. Immutable Evidence Ledger With Derived Views
   Why second: Once one contract owns authority, move the storage model so memory stops being able to masquerade as authority. This is the highest-leverage architectural follow-through because it removes the need for future repair machinery and makes watchlist vs certification a property of derived views, not a hidden nuance in one mutable file.

3. Historical Trust Provenance
   Why third: After authority and storage ownership are clean, preserve interpretability across rule changes. Doing this earlier risks stamping today's ambiguity into a more explicit schema. Doing it later leaves you with a cleaner present but an unreadable history.

What this sequence assumes: it assumes the team wants to preserve a ranked memory/watchlist surface rather than collapse back to a strict PASS-only board. It also assumes the current multi-strategy and recertification trajectory is real enough that historical interpretation will matter, not just present-tense cleanup.

## Open Questions

### Is the leaderboard supposed to be a watchlist/memory surface, a certification surface, or two explicit tiers in one view?
- The answer to this determines whether Opportunity 1 is mainly a contract repair inside one file or a harder split between authority and derived views.
- A 30-minute conversation with the repo owner and whoever uses the HTML review surface would likely resolve this.

### Do you need old leaderboard rows to remain comparable under the rule that admitted them, or is present-tense reinterpretation acceptable?
- The answer to this determines how much of Opportunity 3 is required now versus later. If historical comparability matters, provenance cannot be deferred.
- A 30-minute conversation with the repo owner and anyone using recertification outputs for longitudinal comparison would likely resolve this.

### Is the project committed to a confidence-ranked multi-strategy future, or is the watchlist model still transitional?
- The answer to this determines whether Opportunity 2 should optimize for durable multi-family memory now or whether a stricter PASS-only interim boundary is the better near-term simplification.
- A 30-minute conversation with the repo owner would likely resolve this.
