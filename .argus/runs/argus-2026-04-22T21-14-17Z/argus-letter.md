## What We Think You're Building

This codebase is trying to become a trustworthy TECL decision factory: a system that can generate, stress-test, rank, and certify long-only TECL timing strategies, then hand a human operator a clean `risk_on` / `risk_off` contract plus a native HTML review surface for manual execution. The center of gravity has shifted away from one-off strategy tuning toward a governed pipeline where Spike is the search surface and the Montauk Engine is the evidence machine: data integrity, tier-routed validation, certification artifacts, and durable leaderboard memory. The productive tension is that some docs still describe a single PASS champion, while the newer validation model and leaderboard logic are pulling toward a confidence-ranked watchlist of deployable TECL strategies that can be re-scored as evidence changes.

We came out of the roundtable with one refinement to that frame. The main problem is not that your validation got softer in the abstract. It is that you have partially moved to a watchlist-plus-certification model in code without finishing the trust contract that tells people what a row, a PASS, and a certification actually mean.

---

## What's Impressive

You have made real anti-self-deception investments where they matter most. The charter boundary is unusually clear for a live research repo: TECL-only, long-only, bar-close, manual execution, Python as source of truth. The engine side is also more serious than the repo's current trust boundary makes it look. The regression net in `tests/test_regression.py` is not decorative. The data-quality checks, golden/shadow comparison posture, standardized run artifacts, and the operational guardrails in `scripts/search/safe_runner.py` all show a team that understands evidence has to be earned.

There is also a strong architectural instinct inside the current code, even where the language around it has lagged. Gate 7, the leaderboard updater, and the champion artifact path are already groping toward a sensible separation between ranked research memory and stricter final certification. That is the right shape for a decision factory. The problem is not that you chose the wrong direction. The problem is that the contract around that direction is still split across conflicting meanings and too many write paths.

---

## What You've Missed

The biggest unlock is not another strategy family, another composite tweak, or more recertification machinery. It is turning trust state into a first-class product surface. Right now too much of the meaning of the system lives in human memory: which rows are watchlist memory, which rows are truly promotion-ready, when `backtest_certified` is earned, and which scripts are allowed to harden that state. If you formalize that once and enforce it once, you get a codebase that can support the multi-strategy future the repo is already leaning toward.

You have also missed the leverage in making the leaderboard a derived view instead of a writable authority object. Several agents circled this, but it deserved more weight. As long as `spike/leaderboard.json` is both durable memory and a privilege-bearing input to later maintenance flows, every repair script has to carry hidden semantics. If immutable run artifacts become the canonical evidence and the leaderboard becomes a view over them, provenance gets easier, replay gets safer, and trust stops depending on archaeology.

---

## What's In The Way

The roundtable stopped being theoretical once the execution verdicts landed. They proved three things.

First, the admission boundary is softer than the repo's stronger rhetoric. A `WARN` row with `promotion_ready=False` can still be admitted and written through the leaderboard path.

Second, the sharpest invariant in the system is actually broken in live code. `scripts/validation/pipeline.py` says `backtest_certified` should only exist when `promotion_ready` and the certification checks are both true. `scripts/search/spike_runner.py` can later recompute `backtest_certified=True` from the checks alone. That is not a wording issue. That is authority moving without being re-earned.

Third, maintenance flows can materialize fresh artifact bundles from leaderboard rows without rerunning the full validation contract in that path. That is why the Exploiter's argument landed so hard. The problem is not just that meanings are fuzzy. The system can already replay softer state into authoritative-looking outputs.

Multiple writers are what keep this alive. `evolve.py`, `grid_search.py`, `full_sweep.py`, `recertify_leaderboard.py`, and `spike_runner.py` all participate in trust-bearing state. That makes the Pragmatist's point real: if you only add version labels while keeping those paths, you get versioned ambiguity. But the execution verdicts also make the limit of the Pragmatist's remedy clear: if you only collapse paths and leave the invariant break in the surviving path, you get one cleaner way to be wrong.

The docs and comments are not the root cause, but they are amplifying it. Right now the repo teaches stronger authority than the live state supports. That makes delegation harder, recertification riskier, and future cleanup more expensive than it needs to be.

---

## Where We Disagreed

The real dispute was sequence. The Pragmatist argued the first move should be path collapse: delete duplicate trust-writing paths before doing anything else. The Futurist and Craftsman argued contract and provenance have to be formalized first, or the repo will preserve the same lie in fewer places and overwrite history without explaining it. The Exploiter forced the dispute out of the abstract by showing the live invariant break, and the Execution Agent proved it.

We think the strongest answer is not path collapse alone or semantic formalization alone. It is an explicitly combined change. The execution verdicts settled this. Deletion alone is insufficient because one surviving path can still set `backtest_certified=True` on a non-`promotion_ready` row. Semantics alone are insufficient because the current authority can still be written and replayed by too many scripts. The first move has to restore the trust invariant and reduce authority-writing paths in the same patch.

There was also a smaller disagreement about how to describe the near-term harm. The Accelerator framed it as delegation and newcomer-unsafety. The Exploiter framed it as authority laundering. We think the Exploiter had the stronger argument because execution reproduced actual authority movement, but the Accelerator was right about blast radius: the practical failure mode here is not an attacker first. It is your own team making a defensible change against the wrong contract.

---

## The Move We'd Make First

We would spend the next two weeks on one combined trust-boundary reset.

In one patch, we would make `backtest_certified = promotion_ready and all(checks)` true everywhere, route leaderboard writes through one canonical authority-bearing path, stop letting maintenance flows upgrade softer rows into harder truth without full revalidation, and state plainly whether the leaderboard is a watchlist/memory surface, a certification surface, or both with distinct tiers. We would ship that patch with a small semantic test suite that pins the allowed relationship between `verdict`, `promotion_ready`, `backtest_certified`, leaderboard eligibility, and champion finalization.

That is the highest-leverage move because it does three things at once: it restores the trust invariant the execution verdicts proved is broken, it reduces the number of places that can mutate authority, and it gives every later doc, UI, provenance, and multi-strategy improvement one contract to stand on.
