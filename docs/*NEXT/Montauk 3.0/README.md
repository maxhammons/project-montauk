# Montauk 3.0 — The Always-On Strategy Factory

**What this folder is.** The home for every idea and plan pointing at the next
era of Project Montauk: an **always-on server** that runs the deterministic
idea→Gold pipeline 24/7, refreshes its own data, hosts the Montauk app, watches
for buy/sell signal flips, and breeds chimera strategies from new leaderboard
winners — orchestrated by a small local agent plus remote Claude sessions, with
the owner only needing to top up the idea bucket every month or so.

**Status: VISION / PLANNING.** Nothing here is a frozen spec yet. This is the
charter conversation the existing `*NEXT/` docs kept asking for (the multi-sector
doc ends "the next move is the Q1/Q2 charter conversation, not code"; the
search-expansion doc ends "owner answers Q1 — nothing downstream is buildable
until the frozen boundary is explicit"). Montauk 3.0 starts that conversation and
collects the answers in one place.

---

## Read in this order

1. **[charter.md](charter.md)** — the governing vision: what Montauk 3.0 is, what
   carries over unchanged from today (the Gold bar, deterministic validation,
   legibility), the always-on architecture, the owner/agent/Claude/pipeline role
   split, and the **decision register** of open charter forks that gate the build.
   Start here.

2. The supporting pillar docs below — each is a deep-dive on one leg of the
   vision. The charter ties them together; these carry the detail.

---

## The supporting pillars (moved here from `*NEXT/`)

| Doc | Pillar | Status |
|-----|--------|--------|
| [2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md) | **The conveyor.** Bucket of untested ideas in → deterministic, zero-LLM pipeline → Gold strategies out. The single most important prior art; the engine of the whole vision. | Build plan (≈2.5 sessions); downstream machinery mostly exists |
| [2026-06-14-multi-sector-autonomous-machine.md](2026-06-14-multi-sector-autonomous-machine.md) | **The always-on, AI-orchestrated runtime** + the (optional, charter-gated) expansion from one asset to a fleet of per-sector machines with a rotation brain. | Open-ended vision; needs charter decisions |
| [2026-06-15-montauk-search-expansion.md](2026-06-15-montauk-search-expansion.md) | **The action space.** Why the board is a monoculture and how to feed the unchanged gate more diverse candidates (defensive SGOV leg, sizing, shorts) — without touching the proof. | Design/discussion; needs charter decision Q1 |
| [2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md) | **Chimeras.** Confidence-weighted regime ensembles bred from leaderboard winners — itself just another idea family that must clear the same Gold bar. | Design-only; pipeline fodder |
| [2026-06-10-ios-companion-app.md](2026-06-10-ios-companion-app.md) | **The monitoring surface.** Read-only iPhone app + widget + push on every regime flip — the always-on server's window to the owner's pocket. | Work plan (~2–4 days); needs paid Apple dev account |

---

## What's already decided vs. still open

The owner's stated vision settles the *shape* of Montauk 3.0:

- **Decided:** an always-on server; a small local orchestration agent + remote
  Claude (not an expensive local model); an hourly standing run that grinds one
  idea at a time; monthly bulk idea dumps; the server also owns data refresh, app
  hosting, signal monitoring, and chimera breeding.
- **Still open (the decision register in [charter.md](charter.md) §10):** TECL-only
  vs. multi-sector; the action-space expansion (SGOV leg / sizing / shorts) and
  the `≤5 trades/year` rule; the execution model (stay manual vs. bounded broker);
  exact autonomy boundaries and kill-switches; the breadth-deflation fix that
  keeps "billions of combinations" from manufacturing false Gold.

---

## Relationship to the rest of `docs/`

This folder is still part of the canonical `*NEXT/` backlog — it is the Montauk
3.0 *subset* of it, organized under one umbrella. The non-negotiables it inherits
live in `docs/charter.md`, `docs/validation-thresholds.md`, and
`docs/validation-philosophy.md`; this charter **extends** those, it does not
override them. When a decision here is actually made, it gets promoted into the
governing docs by explicit decision (never by drift) — same rule as always.
