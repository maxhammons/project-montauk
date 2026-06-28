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

## Two activities, one clean seam (2026-06-14 refinement)

There is exactly one non-deterministic step and it does only one job: **author
ideas and format them so the deterministic pipeline can read them.** Everything
that decides whether a strategy is Gold is deterministic and LLM-free. Concretely:

- **Authoring (the ONLY LLM part).** Say "go" / "make strategies." Claude invents
  new strategy families, implements each in `scripts/strategies/library.py`,
  smoke-tests it, and writes the matching `spike/ideas/<name>.md` (frontmatter +
  prose) so the family is machine-readable and queued (`implemented: true,
  status: queued`). The LLM's responsibility ends here — it never mines, never
  validates, never certifies, never decides Gold. Run it on demand and
  high-volume: spend spare usage to build a **huge queue**. Bounded by a count or
  time budget ("generate for an hour").
- **The deterministic pipeline (no LLM).** Works the queue through Stages 1–4
  above — bandit allocation → GA mining → lifecycle (promoted / exhausted /
  condemned) → Gold certification — entirely by seeded, reproducible rules. It
  consumes only `implemented: true` families and never touches `library.py`.
  **It is the same engine whether invoked for a bounded duration ("drain for an
  hour") or left to run overnight via the launchd cron.** Duration is just a
  budget knob; the logic is identical.

Workflow this enables: pour ideas into the bucket whenever you have spare Claude
usage (authoring), then let the deterministic pipeline grind the backlog — a
quick hour when you want a few results, or all night against a deep queue. The
two never overlap in responsibility, so "Zero LLM in Stages 1–4" is exact: the
LLM hands off a machine-readable queue and walks away.

## Idea format — `spike/ideas/*.md` (the front door)

One markdown file per idea family. Frontmatter is the machine-readable contract;
prose is the brief Claude implements against. These `.md` files are the *source
of truth* for ideas; `spike/hypothesis-queue.json` is *derived machine state*
(per-family lifecycle stats) — no duplicated truth.

```markdown
---
name: nh_vix_regime_trend          # also the registry/family name
status: queued                     # queued|mining|exhausted|condemned|promoted
priority: 1
tunables: [ema_short, ema_med, vix_threshold, atr_mult]   # ≤ 8 — enforced
implemented: false                 # flips true once code is in library.py + smoke-passed
author: claude                     # claude (Mode A/B) or human
---
## Mechanism
One paragraph: the edge and why it should persist.

## Entry / Exit
- bar-close rules; long-only; single position

## Variants to sweep
- ema_short ∈ {10,15,20}; vix_threshold ∈ {18,22,26}
```

Claude authors the `.md` *and* the code during the authoring step. A human can
drop a hand-written `.md` in too. The deterministic pipeline only consumes
families whose backing code already exists (`implemented: true`). Verdicts get
stamped back into both the frontmatter and the verdict ledger so authoring
sessions inherit memory.

### Authoring step — creativity inputs + dedup

**What Claude draws on to invent a family (the only creativity in the system):**
- `docs/design-guide.md` — what has cleared the pipeline and what predictably
  fails; the ≤8-tunable, charter-compatible pre-flight checklist.
- Cycle diagnostics — the regime map (every bull/bear cycle) and where current
  strategies' trades/exits fall, so new mechanisms target real gaps.
- The verdict ledger — so it never re-proposes a mechanism already `condemned`
  (and knows which gate killed prior attempts).

**Two-layer dedup, both checked at authoring time:**
- **Config-level (exists):** `spike/hash-index.json` maps config hashes → fitness;
  the GA already skips exact param-combo duplicates. Unchanged.
- **Family/mechanism-level (new):** before depositing a new `.md`, the authoring
  runner checks the candidate against existing families/ideas (registry + queue)
  and rejects mechanical near-twins — same signal stack, same indicators, trivial
  threshold shuffles. High-volume generation must add *distinct* mechanisms, not
  variants the GA would collapse anyway. (A variant sweep belongs in an existing
  family's "Variants to sweep" block, not as a new family.)

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

**Backbone (shared by authoring + drain):**
- [ ] 1. `spike/ideas/*.md` format + parser; `spike/hypothesis-queue.json` schema (derived from the `.md` set); seed with the 10 current nh_ families (`implemented: true, status: mining`) and the meta-strategy design (`status: queued`, spec-only — see `2026-04-23-meta-strategy-design.md`)
- [ ] 2. Queue module `scripts/search/hypothesis_queue.py`: load/save, `.md`↔queue sync, lifecycle transitions (pure functions, unit-tested), bandit allocator (seeded Thompson over Beta posteriors), verdict writer
- [ ] 3. Wire into spike-drain (deterministic drain): evolve() gets a per-family compute-weight map from the allocator; post-run stats + transitions applied; roster auto-updated on exhaust/condemn; **only consumes `implemented: true` families**

**Authoring (the only LLM step — outside Stages 1–4):**
- [ ] 4. "Generate" runner: author idea `.md` + implement family in `library.py` + smoke-test + deposit to queue (`implemented: true`). Bounded by count or time budget. Skill entrypoint (e.g. `/spike-generate`). Inputs: design-guide + cycle diagnostics + verdict ledger (avoid condemned mechanisms). **Family/mechanism-level dedup check** against registry + queue before deposit (rejects near-twins; reuses `spike/hash-index.json` for config-level). Does NOT mine, validate, or certify.

**Drain invocation + surfaces:**
- [ ] 5. Bounded-duration drain entrypoint: run the deterministic pipeline for a fixed budget ("drain for an hour") as well as the existing nightly cron — same engine, duration is just a budget knob.
- [ ] 6. Queue-low event + app attention-banner (reuse existing events/notifications path) → signals when to run an authoring session
- [ ] 7. Verdict ledger + authoring brief: update `docs/ai-research-playbook.md` so generation sessions consume verdicts
- [ ] 8. Tests (lifecycle rules, allocator determinism, queue-low trigger, `.md`↔queue sync) + doc-sync (pipeline.md, CLAUDE.md)

Effort: ~2.5 sessions. Everything downstream of Stage 0 already exists as of
2026-06-09 (drain job, parallel GA, halving, early filter, roster, Gold gate,
live demotion); this plan adds the queue brain, the authoring entrypoint, and a
bounded-duration drain invocation on top.

## Improvements to consider (2026-06-14)

These sharpen the vision rather than just implement it. Roughly ordered by
leverage. None are in the build plan above yet — adopt the ones that earn their
keep.

### 1. Count generated ideas, not just mined ones
**Problem:** the overfit defenses (N_eff deflation, PBO) correct for *configs the
GA searched* — but the new bottleneck is the *number of families authored*. If
Claude generates 500 families and 5 reach Gold, those 5 may just be the lucky
tail of 500 lottery tickets, and the current deflation never sees the 500.
**Fix:** record total families generated (not only mined) and feed authoring
breadth into the multiplicity correction, so a "Gold from 500 ideas" is deflated
harder than a "Gold from 20 ideas." Without this, scaling generation silently
manufactures false Gold — the single biggest risk in the whole vision.

### 2. Author by economic mechanism, never by predicted performance
**Problem:** every time Claude invents/dedups/discards ideas in its head before
writing the `.md`, that is a selection step the statistics cannot observe — exactly
the "hand-tuned toward the bar" pre-selection bias the invariants forbid, except
now it's the dominant input. The cleverer the LLM pre-selects for likely winners,
the more invisible bias it injects.
**Fix:** the authoring step selects on *economic mechanism + distinctness only*,
never on guessed share_multiple. It should honestly author mechanisms it suspects
will fail, so the deflation sees real breadth. Make this an explicit authoring
rule and a review check, not a vibe.

### 3. Let the board steer authoring (not "queue low")
**Problem:** authoring today is triggered by *volume* (queue < QUEUE_MIN). That
yields quantity, not the thing that matters — *economic diversity on the board*.
Four flavors of trend-following all die in the same regime.
**Fix:** the pipeline emits a board-gap report (e.g. "no mean-reversion exposure,
everything COVID-dependent, no rates-driven family"), and that becomes the
authoring brief. Generation gets *targeted* at the board's missing styles instead
of dumping volume. Highest leverage-to-effort change in this list.

### 4. Require an economic rationale per idea (theory gate)
**Problem:** the only pre-mining filter is a smoke test (does it run). All-night
compute is the scarce resource; data-mining-shaped ideas (a pattern with no
mechanism) waste it.
**Fix:** require a written economic rationale in each idea's `## Mechanism` block,
and let the authoring step reject ideas that can't articulate *why* the edge
should exist. This is the LLM's unique advantage — the deterministic pipeline
structurally cannot reason about economic plausibility, so spend the LLM there.

### 5. Queue-global cheap→expensive cascade
**Problem:** with a huge queue, giving every family the full 7-gate validation is
wasteful. Halving/early-filter exist *within* a GA run, but not *across* the queue.
**Fix:** a global cascade — every family gets a ~5-second modern-era screen first;
only survivors earn full validation. The bandit allocator then splits compute
among survivors. ~90% of bad ideas die cheap instead of consuming a full run.

### 6. Make the verdict ledger structured and mineable
**Problem:** the Gold strategies are the output, but the *map of what failed and
why* is the compounding asset — it's what makes each authoring session smarter
than the last. The plan treats it as feedback plumbing.
**Fix:** structure the ledger so it can be aggregated, not just read per-family —
e.g. "73% of vol-based families die on execution_realism," "every macro/rates
family exhausts without Gold." That becomes a design-guide that writes itself, and
it's also the evidence base for #1 (how much breadth was rejected, and where).

### 7. Split auto-admit from auto-promote
**Problem:** Gold = "fit to trade real money," and the app-charter rule is that AI
may not promote the active champion without a human click. The vision wants
autonomous Gold minting.
**Fix:** the deterministic pipeline may *auto-admit* a Gold family to the board (it
is a certification, and it's not an LLM, so the rule holds) — but keep a one-click
human ack before a newly minted family becomes the *active* strategy whose
risk_on/risk_off you actually trade. Cheap insurance against a lucky-tail strategy
landing on real money unattended.

### 8. Let ideas go stale
**Problem:** an idea authored against six-month-old diagnostics may be aimed at a
gap the board has since filled, or a regime that has passed.
**Fix:** ideas carry `born_utc` (already in the schema) and expire / get
re-prioritized after a TTL, so the queue doesn't mine answers to stale questions.

### 9. Match search method to idea complexity
**Problem:** the GA is overkill for a simple 2-tunable family and underpowered
phrasing for a complex one — one-size-fits-all wastes compute either way.
**Fix:** let an idea declare (or the runner infer from tunable count) whether it
wants a small canonical grid or a full GA. Simple families resolve in seconds.

### 10. Instrument the funnel
**Problem:** without meta-metrics you can't tell whether to scale generation or
improve idea quality — you're just burning electricity.
**Fix:** track Gold yield per 100 ideas (overall and per economic category),
compute per Gold, and false-Gold rate (Gold later killed by live demotion). These
numbers tell you where the bottleneck actually is.
