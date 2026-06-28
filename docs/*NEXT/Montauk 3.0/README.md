# Montauk 3.0 — The Always-On Strategy Factory

**What this folder is.** The home for every idea and plan pointing at the next
era of Project Montauk: an **always-on server** that runs the deterministic
idea→Gold pipeline 24/7, refreshes its own data, hosts the Montauk app, watches
for buy/sell signal flips, and breeds chimera strategies from new leaderboard
winners — orchestrated by a small local agent plus remote Claude sessions, with
the owner only needing to top up the idea bucket every month or so.

**Status: VISION / PLANNING.** Nothing here is a frozen spec yet — this is the
charter conversation, captured as it happens. The governing draft is
[charter.md](charter.md); resolved calls land in [decisions.md](decisions.md). The
guiding light is the **validation engine**
([validation-engine-hardening.md](validation-engine-hardening.md)): by the time a
strategy is Gold it must be defensible, auditable, testable, and survive academic
critique. Montauk 3.0 is **TECL-only**; the multi-asset / wider-action expansion is a
separate later release in [`../Montauk 4.0/`](../Montauk%204.0/).

---

## Read in this order

1. **[charter.md](charter.md)** — the governing vision: what Montauk 3.0 is, what
   carries over unchanged from today (the Gold bar, deterministic validation,
   legibility), the always-on architecture, the owner/agent/Claude/pipeline role
   split, and the **decision register** of open charter forks that gate the build.
   Start here. Its companion **[decisions.md](decisions.md)** is the running ledger
   of resolved decisions — read it for what's actually been settled.

2. The supporting pillar docs below — each is a deep-dive on one leg of the
   vision. The charter ties them together; these carry the detail.

---

## The pillar docs

Governing docs above the pillars: **[charter.md](charter.md)** (umbrella vision) and
**[decisions.md](decisions.md)** (resolved-decision ledger).

| Doc | Pillar | Status |
|-----|--------|--------|
| [validation-engine-hardening.md](validation-engine-hardening.md) | **The validation engine — the north star.** The three-step pipeline (bucket → backtest/tune → validation), a current-state audit against the academic anti-overfit literature, the gap register, and the hardening backlog. Gold must be academically defensible. | Living doc; line-by-line correctness audit (G10) committed |
| [2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md) | **The conveyor.** Bucket of untested ideas in → deterministic, zero-LLM pipeline → Gold strategies out. The engine of the whole vision. | Build plan (≈2.5 sessions); downstream machinery mostly exists |
| [2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md) | **Chimeras.** Confidence-weighted regime ensembles bred from leaderboard winners — itself just another idea family that must clear the same Gold bar. | Design-only; pipeline fodder |
| [2026-06-10-ios-companion-app.md](2026-06-10-ios-companion-app.md) | **The monitoring surface.** Read-only iPhone app + widget + push on every regime flip — the always-on server's window to the owner's pocket. | Work plan (~2–4 days); needs paid Apple dev account |

> The multi-asset / action-space expansion (the multi-sector-machine + search-expansion
> docs) has moved to [`../Montauk 4.0/`](../Montauk%204.0/) — a separate, later release.

---

## What's already decided vs. still open

The owner's stated vision settles the *shape* of Montauk 3.0:

- **Decided:** TECL-only; an always-on *appliance* server (a dumb deterministic
  churner — no on-box AI) with no local agent; remote Claude for authoring +
  maintenance; grind-constantly with monthly bulk idea dumps; auto-enter intake;
  Gold → a **staging leaderboard** → manual admission; a hard data-integrity rule;
  defined chimera triggers; and the validation engine as the north star (with "the
  bar rises with the search, never falls" locked as a design law). Full ledger in
  [decisions.md](decisions.md).
- **Still open (charter §10):** the breadth-deflation *mechanism* (locked as a **hard
  prerequisite** — it keeps "billions of combinations" from manufacturing false
  Gold); unifying the bucket front door; and the budget / hardware envelope.

---

## Relationship to the rest of `docs/`

This folder is still part of the canonical `*NEXT/` backlog — it is the Montauk
3.0 *subset* of it, organized under one umbrella. The non-negotiables it inherits
live in `docs/charter.md`, `docs/validation-thresholds.md`, and
`docs/validation-philosophy.md`; this charter **extends** those, it does not
override them. When a decision here is actually made, it gets promoted into the
governing docs by explicit decision (never by drift) — same rule as always.
