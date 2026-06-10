# Idea-to-Gold Pipeline — untested ideas in, Gold strategies out, zero LLM in between

**Goal (Max, 2026-06-09):** a bucket of untested ideas on one end; a fully
offline, deterministic, no-LLM pipeline that spits out Gold strategies on the
other. The only non-deterministic step — authoring new strategy logic — happens
*outside* the pipeline, in periodic LLM sessions that restock the bucket.

```
 [LLM authoring session]          (the ONLY non-deterministic step, runs rarely)
        │  deposits implemented + smoke-passed nh_ families
        ▼
 ┌─ STAGE 0: HYPOTHESIS QUEUE ──────────────────────────────────────────┐
 │ spike/hypothesis-queue.json — one entry per family:                  │
 │ {name, mechanism, status: queued|mining|exhausted|condemned|promoted,│
 │  priority, born_utc, nights_mined, dry_nights, verdicts[]}           │
 └──────────────────────────────────────────────────────────────────────┘
        ▼ nightly 02:00 (spike-drain job, launchd, no human, no LLM)
 ┌─ STAGE 1: ALLOCATE + MINE ───────────────────────────────────────────┐
 │ Bandit allocation: per-family Beta posterior on "produces candidates  │
 │ that clear the modern screen"; Thompson-sample (seeded by date) to    │
 │ split the night's 2h budget. Fresh families get an exploration floor. │
 │ GA mines with everything already built: parallel pool, successive     │
 │ halving, early filter, hash-index dedup, search roster.               │
 └──────────────────────────────────────────────────────────────────────┘
        ▼ per-run finalists
 ┌─ STAGE 2: LIFECYCLE (automatic, deterministic rules) ────────────────┐
 │ After each night, stamp per-family stats into the queue:              │
 │  • candidate cleared validation PASS → status=promoted → Stage 3      │
 │  • N_DRY consecutive nights with no screen-clearing candidate         │
 │    (default 5) → status=exhausted → auto-append to search-roster      │
 │    retired list + verdict recorded                                    │
 │  • hard-breach dominance (most finalists die on the same gate, e.g.   │
 │    event-dependence) → status=condemned + verdict names the killer    │
 └──────────────────────────────────────────────────────────────────────┘
        ▼ promoted candidates
 ┌─ STAGE 3: CERTIFY (existing, unchanged) ─────────────────────────────┐
 │ Full hardened validation → Gold gate (fit to trade, beats B&H all     │
 │ eras, full falsifiable confidence) → diversity cap → board admission  │
 │ → artifact bundle → viz rebuild → live-demotion watch begins          │
 └──────────────────────────────────────────────────────────────────────┘
        ▼
 ┌─ STAGE 4: FEEDBACK (writes, never decides) ──────────────────────────┐
 │ • Verdict ledger: runs/research/verdicts/<family>.json — what was     │
 │   tried, what killed it (economics floor / PBO / event dependence /   │
 │   execution realism), best canonical era shares reached               │
 │ • Queue-low signal: < QUEUE_MIN (default 4) families in queued/mining │
 │   → "hypothesis queue low" event → app attention banner → Max runs    │
 │   an authoring session (docs/ai-research-playbook.md is the brief)    │
 │ • Authoring sessions READ the verdict ledger so each batch avoids     │
 │   known killers — institutional memory without LLM in the loop        │
 └──────────────────────────────────────────────────────────────────────┘
```

## Invariants (non-negotiable)
- **Zero LLM in Stages 1–4.** Every decision is a seeded, reproducible rule.
- **Determinism:** nightly seed = f(date); same queue + data + seed → same run.
- **Statistics stay honest:** every config (screened, pruned, mined) lands in
  the hash-index; N_eff ratchets; deflation hardens as the pipeline runs.
- **The bar never bends:** exhausted ≠ failed-the-board; it means "this idea's
  space is mined out." Gold admission criteria are untouchable by the queue.
- **Authoring discipline:** new families enter only as implemented, registered,
  smoke-passed code with ≤8 tunables, design-guide compliant, never hand-tuned
  toward the bar (pre-selection bias is the deflation's enemy).

## Build plan
- [ ] 1. `spike/hypothesis-queue.json` schema + seed it with the 10 current nh_ families (status=mining) and the meta-strategy design (status=queued, spec-only flag — see `*NEXT/2026-04-23-meta-strategy-design.md`)
- [ ] 2. Queue module `scripts/search/hypothesis_queue.py`: load/save, lifecycle transitions (pure functions, unit-tested), bandit allocator (seeded Thompson over Beta posteriors), verdict writer
- [ ] 3. Wire into spike-drain: evolve() gets a per-family compute-weight map from the allocator; post-run stats + transitions applied; roster auto-updated on exhaust/condemn
- [ ] 4. Queue-low event + app attention-banner surface (reuse existing events/notifications path)
- [ ] 5. Verdict ledger + authoring brief: update `docs/ai-research-playbook.md` to consume verdicts; "restock session" checklist
- [ ] 6. Tests (lifecycle rules, allocator determinism, queue-low trigger) + doc-sync (pipeline.md, CLAUDE.md)

Effort: ~2 sessions. Everything downstream of Stage 0 already exists as of
2026-06-09 (drain job, parallel GA, halving, early filter, roster, Gold gate,
live demotion); this plan adds the queue brain on top.
