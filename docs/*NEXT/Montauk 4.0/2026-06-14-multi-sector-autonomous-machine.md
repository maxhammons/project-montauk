# Multi-Sector Autonomous Machine — sector-rotating, AI-orchestrated, always-on

**Status: VISION / NOT EXECUTABLE AS-IS.** This is a direction-setting sketch,
not a build plan. Max does not have all the details worked out yet (2026-06-14).
Most of the hard questions below are *unanswered on purpose*. Do not start
implementing from this document — it needs a charter decision and several rounds
of scoping first. Treat every section as a prompt for discussion, not a spec.

---

## The idea in one paragraph

Today Montauk is a single-asset machine: TECL-only, one Gold-ranked active
strategy, signals executed by hand. The vision is to grow it into a **fleet of
per-sector machines** — each sector (tech, semis, financials, energy,
healthcare/biotech, etc.) gets its own library of strategies, its own
leaderboard, its own Gold champion. On top of the fleet sits a **sector-rotation
layer** that decides *which sector(s) deserve capital right now* and pushes money
toward them as rotation happens. The whole thing is **orchestrated by AI agents**
on an **always-on machine** that continuously: watches the market and macro data
feeds, runs backtests, generates and screens new strategy hypotheses, validates
them through the existing logic gates, and rebalances capital across sectors —
all toward an explicit, stated goal (accumulate more units / more value than a
passive benchmark) rather than toward a fixed parameter set.

It is, in short: **an autonomous, goal-oriented, AI-enabled backtesting and
allocation machine** that never stops working.

---

## Why this is a big departure (read before anything else)

Several of today's *non-negotiables* are directly in tension with this vision.
Surfacing them up front so the conflict is a conscious decision, not a drift:

- **"TECL-only" is a charter non-negotiable** (spirit quick-reference, CLAUDE.md).
  Multi-sector breaks it by definition. This requires an explicit charter
  amendment, not a code change. → see Open Question Q1.
- **"One active strategy whose signal you execute"** becomes "N sector champions
  plus a rotation overlay." The meaning of *the active strategy* changes.
- **"Manual execution in a brokerage account"** does not scale to a fleet that
  rebalances across sectors continuously. Either execution stays manual (and the
  machine only *proposes*), or it gets a broker integration (a large new trust /
  safety surface the charter currently forbids).
- **"≤5 trades/yr, never punish low frequency"** was a per-strategy guardrail.
  Rotation adds a *second* trading layer on top; the combined turnover budget is
  undefined.
- **Autonomy vs. the Gold bar.** The current system's whole credibility rests on
  *nothing enters the board except Gold, and a human is in the authoring loop.*
  An always-on machine that *generates and promotes its own strategies* must not
  quietly lower that bar. Autonomy has to make the bar **more** rigorous, never
  less. → see Q5.

None of these are blockers. They are the decisions that have to be made before
this is buildable.

---

## What already exists that this builds on

This is not greenfield. The vision is largely a *generalization + orchestration*
layer over machinery that already works for one sector:

- **The engine** (`scripts/engine/strategy_engine.py`) — asset-agnostic in
  principle; today it's pointed at TECL.
- **The search + validation + certification pipeline** (4 phases) — already
  produces Gold champions from raw ideas.
- **The idea-to-gold pipeline** (`../Montauk 3.0/2026-06-09-idea-to-gold-pipeline.md`) —
  already describes a *zero-LLM, deterministic, nightly* miner with a hypothesis
  queue, bandit allocation, lifecycle rules, and a verdict ledger. **This is the
  single most important prior art** — the multi-sector machine is essentially
  *"run that pipeline per sector, plus a rotation brain, plus an agent layer."*
- **The meta-strategy ensemble design** (`../Montauk 3.0/2026-04-23-meta-strategy-design.md`)
  — a confidence-weighted regime ensemble. Sector rotation is a close cousin:
  swap "weight strategies by regime" for "weight *sectors* by regime."
- **The ops layer** (`runs/operations/`, events, notifications, the Mac app,
  `ops/live_holdout.py` live demotion) — already an always-on-ish monitoring and
  attention surface.
- **Data loaders + manifest + quality gates** (`scripts/data/`) — the pattern for
  adding, verifying, and checksumming a new ticker already exists.

The honest framing: **~70% of the parts exist for one sector.** The new work is
(a) data + strategy libraries for more sectors, (b) the rotation decision layer,
(c) the agent orchestration / always-on runtime, and (d) the charter + safety
rethink that makes autonomy legitimate.

---

## A rough mental model of the system (sketch, not a spec)

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │ ALWAYS-ON RUNTIME (one machine, never sleeps)                        │
 │                                                                      │
 │  ┌── DATA TRIPS (continuous) ──────────────────────────────────┐    │
 │  │ price feeds · macro (rates, spreads, VIX) · sector breadth   │    │
 │  │ · rotation signals · news/sentiment(?) · health checks       │    │
 │  └──────────────────────────────────────────────────────────────┘   │
 │           │                                                          │
 │  ┌── PER-SECTOR MACHINES (one idea-to-gold pipeline each) ──────┐    │
 │  │  TECH      SEMIS     FINANCIALS   ENERGY    HEALTH   ...      │    │
 │  │  [queue→mine→validate→certify→board→live-watch] × N sectors  │    │
 │  │  each emits its own Gold champion + live forward evidence     │    │
 │  └──────────────────────────────────────────────────────────────┘   │
 │           │ each sector's champion signal + confidence               │
 │  ┌── ROTATION BRAIN ───────────────────────────────────────────┐    │
 │  │ decides capital allocation ACROSS sectors as rotation happens │    │
 │  │ (relative strength / regime / breadth / macro), bounded by    │    │
 │  │ risk + turnover budget; outputs target weights per sector     │    │
 │  └──────────────────────────────────────────────────────────────┘   │
 │           │                                                          │
 │  ┌── AGENT ORCHESTRATION ──────────────────────────────────────┐    │
 │  │ AI agents schedule the miners, triage attention events,       │    │
 │  │ restock hypothesis queues, narrate decisions, escalate to Max │    │
 │  │ — but DO NOT bend the Gold bar or move real money unattended  │    │
 │  └──────────────────────────────────────────────────────────────┘   │
 │           │                                                          │
 │  ┌── OUTPUT ───────────────────────────────────────────────────┐    │
 │  │ proposed allocation + per-sector signals → app / notification │    │
 │  │ → (manual execution?  or  bounded broker integration?)        │    │
 │  └──────────────────────────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────────────┘
```

Everything in this diagram is provisional. The boxes are real questions, not
committed components.

---

## The big open questions (these gate the whole thing)

These are listed because they are *unresolved*, not because answers are implied.

**Q1 — Charter.** Does Montauk stay "TECL-only" with multi-sector as a separate
project, or does the charter formally expand to a sector universe? What is that
universe (which leveraged/unleveraged sector ETFs)? This is the first decision
and everything downstream depends on it.

**Q2 — What is the actual goal function?** Single-asset Montauk optimizes
*share_multiple vs B&H*. Across sectors, "shares" isn't comparable (a TECL share
≠ an ERX share). Is the fleet's objective total-dollar growth vs a blended
benchmark? Vs SPY? Risk-adjusted? The north star has to be re-derived before any
optimization target exists.

**Q3 — Per-sector benchmark + Gold definition.** Does each sector champion still
have to "beat B&H in full/real/modern eras" against *its own* sector? Do
leveraged sector ETFs even have enough clean history? (TECL needed synthetic
pre-2008 data; other sectors will have worse coverage and different splice
problems.)

**Q4 — The rotation layer's own validation.** A rotation overlay is itself a
strategy and can itself be overfit. How does it earn trust? Does it go through
the same 7-gate pipeline? What's its null distribution? Rotation strategies are
*notoriously* prone to in-sample curve-fitting — this needs at least as much
anti-overfit defense as a single strategy, probably more.

**Q5 — Autonomy boundaries / safety.** What is the agent allowed to do
unattended? Almost certainly: mine, validate, propose, alert. Almost certainly
NOT: move real money, promote to Gold without the existing executed checks,
amend its own bar. Where exactly is the line, and what are the kill-switches /
circuit-breakers / drawdown halts? This is the trust core of the whole machine.

**Q6 — Execution model.** Stay manual (machine proposes, Max executes)? Or
bounded broker API with hard caps? The charter currently forbids broker
integration; this is a major scope + risk decision, not a feature toggle.

**Q7 — Compute + cost envelope.** "Constantly running backtests and generating
strategies" across N sectors is N× the nightly compute, plus the rotation search,
plus continuous data + agent costs. What hardware, what budget, what does
"always-on" actually cost per month?

**Q8 — Capital reality.** Sector rotation across many leveraged ETFs implies real
position sizing, tax lots, wash sales, and rebalancing friction the single-asset
model never had to model. Is this paper-only first?

---

## Plausible phasing (illustrative ordering, NOT a commitment)

A way to de-risk this incrementally so it's never a big-bang rewrite. Each phase
is a real stopping point that delivers value on its own.

- **Phase A — Generalize to 2 sectors, manual everything.** Prove the engine +
  pipeline are truly asset-agnostic by standing up *one* second sector end-to-end
  (data → library → Gold champion). No rotation, no agents yet. This phase alone
  answers Q1/Q3 with evidence instead of speculation.
- **Phase B — Static dual-sector allocation.** Hand-set weights between two
  sector champions; build the dollar-based, cross-sector goal function (Q2);
  build a blended benchmark and a combined backtest harness.
- **Phase C — Rotation brain v0.** A *validated* rotation overlay (relative
  strength / breadth / regime) that proposes weights, run through its own
  anti-overfit gauntlet (Q4). Still manual execution.
- **Phase D — Scale the fleet.** Generalize the nightly idea-to-gold miner to run
  per-sector queues with shared compute allocation (the bandit already exists;
  now it allocates across *sectors* as well as families).
- **Phase E — Agent orchestration + always-on runtime.** Agents schedule,
  triage, restock, narrate, escalate — within hard, audited boundaries (Q5). The
  monitoring + attention surfaces already exist to build on.
- **Phase F — (Optional, gated) bounded execution.** Only if Q5/Q6 are settled
  with real safety rails. Likely paper-trading first for a long time.

The ordering matters: **prove asset-agnosticism (A) and a trustworthy rotation
overlay (C) before any autonomy or scale.** The riskiest, least-reversible pieces
(real-money autonomy) come last and stay optional.

---

## What would make this *not* work (failure modes to design against)

- **Overfit rotation.** The rotation layer fits the last decade's specific
  sector leadership and breaks on the next regime. (Mitigation: treat it as the
  most overfit-prone component in the system; hardest gates.)
- **Autonomy eroding the bar.** The machine, optimizing its goal, finds that the
  fastest path to "more strategies promoted" is a softer bar. The bar must be
  *immutable to the optimizer* — autonomy raises rigor, never lowers it.
- **Data quality at scale.** N sectors = N synthetic-splice/coverage problems.
  One bad sector feed silently poisons rotation. Per-sector quality gates are
  non-optional.
- **Cost spiral.** Always-on × N sectors × continuous agents can quietly become
  expensive with no proportional edge. Needs a compute-budget governor from day
  one (the bandit allocator is the natural home).
- **Complexity collapse.** The single-asset system is legible to one person at a
  glance (a stated project value). A fleet + rotation + agents can become
  un-auditable. Legibility has to be a design constraint, not an afterthought.

---

## Immediate, low-regret next steps (if/when this is greenlit)

None of these commit to the full vision; all are useful even if the machine never
gets built:

1. **Charter conversation (Q1/Q2).** Decide the asset universe and the
   cross-sector goal function on paper before any code. Highest-leverage step.
2. **Asset-agnosticism audit.** Grep the engine + pipeline for hardcoded TECL/
   ticker assumptions; quantify what "stand up a second sector" actually costs.
   This is a concrete, bounded investigation that de-risks Phase A.
3. **Pick one second sector** with the cleanest data history and run *one*
   strategy through the existing pipeline against it as a spike. Evidence beats
   speculation for Q3.
4. **Write the rotation-overlay validation spec** (Q4) — how a rotation strategy
   earns Gold-equivalent trust — *before* building a rotation strategy.

---

*This document is intentionally open-ended. It records a direction, names the
unresolved decisions, and orders the work to de-risk it — but it is not a
buildable plan and should not be executed as written. Next move is the Q1/Q2
charter conversation, not code.*
