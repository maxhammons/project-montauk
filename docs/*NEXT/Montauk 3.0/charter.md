# Project Montauk 3.0 Charter — The Always-On Strategy Factory

**Status: DRAFT / VISION (2026-06-15).** This is the charter the existing `*NEXT/`
docs keep asking for, but it is **not yet ratified**. It records the owner's
stated direction, binds it to the non-negotiables that must survive the
transition, and names the decisions still open. Sections marked **DECIDED**
reflect the owner's vision as stated; sections in the **Decision Register (§10)**
are explicitly **PENDING** and must not be implemented until resolved. Nothing
here overrides `docs/charter.md`, `docs/validation-thresholds.md`, or
`docs/validation-philosophy.md` — it *extends* them, and only by explicit decision.

---

## 0. Why a 3.0 charter

Montauk 1.x/2.x is a **single-asset signal factory operated by hand**: one person
runs `/spike`, reviews results, certifies a champion, and reads the daily
`risk_on`/`risk_off` off a Mac. It works, but it only runs when the owner is
driving, and the idea pipeline is a manual loop.

Montauk 3.0 turns the factory into a **standing machine**. A computer that lives
on Wi-Fi somewhere and never sleeps does the grinding: it pulls fresh data, works
through a deep bucket of untested ideas, validates survivors through the unchanged
Gold gate, populates the leaderboard, hosts the app, watches for signal flips, and
breeds chimeras from new winners. The owner's job shrinks to two things:
**occasionally pour a month's worth of ideas into the bucket**, and **act on the
signals and escalations the machine surfaces.**

This is the same machinery, mostly already built, with an orchestration layer and
an always-on runtime wrapped around it. The hard part is not the code — it is
keeping the system **honest and legible** as it scales from "a person runs it" to
"it runs itself."

---

## 1. The vision in one paragraph

A bucket of untested strategy ideas on one end; a fully deterministic, LLM-free
validation pipeline that drips Gold strategies onto the leaderboard on the other;
and an always-on server in between that runs that pipeline on a standing schedule
(roughly one idea per hour, all night, indefinitely), **orchestrated by a small
local agent for the cheap mechanical work and by remote Claude sessions for
anything that needs real intelligence.** The same server also keeps the data
current, serves the Montauk app and its signals, and assembles chimera strategies
out of fresh leaderboard winners. The owner tops up the bucket every month or so
and otherwise just watches the output.

> In one line: **an always-on, goal-oriented strategy factory that never stops
> working — and never lowers its bar to do it.**

---

## 2. What carries over unchanged (the non-negotiables)

Autonomy and scale make these *more* important, not less. They are immutable to
the machine — the optimizer, the agent, and the schedule may not bend them.

- **The Gold bar never moves.** Layer-1 correctness (integrity, golden regression,
  shadow comparator, data quality, artifact completeness) and the Layer-2
  confidence composite, its sub-scores, weights, and anchors
  (`docs/validation-thresholds.md`) are frozen. The Gold contract stays:
  `certified_not_overfit` + `backtest_certified` + beats B&H in the full, real,
  AND modern eras. **Autonomy must raise rigor, never relax it.**
- **Validation is deterministic and LLM-free.** Every decision that determines
  whether a strategy is Gold is a seeded, reproducible rule. No language model is
  ever in the certification path. (See §3 for the seam.)
- **The leaderboard IS a certification, admission is Gold-only.** Nothing enters
  except Gold. Fewer rows is correct behavior, never failure. The machine may
  *auto-admit* a certified Gold family (it is not an LLM and the bar is intact),
  but a newly minted family does not become the *active* traded strategy without a
  one-click human acknowledgement (see §10 Q5).
- **Python is the single source of truth** for signals and execution logic.
  Bar-close only, no lookahead, no repainting. Every champion ships the
  standardized artifact bundle.
- **Legibility is a design constraint, not an afterthought.** The current system
  is understandable by one person at a glance — a stated project value. A fleet +
  agents + a 24/7 runtime can become un-auditable. If a Montauk 3.0 component
  cannot be explained on one page, it is not done.
- **Live evidence outranks backtests.** `ops/live_holdout.py` continuously
  falsifies the active champion and demotes it automatically. Forward truth, not
  stored stamps, is the final authority.

**The validation engine is the north star.** The pipeline is three steps —
**(1)** the bucket (authoring), **(2)** backtest + parameter tuning, **(3)** the
validation engine (overfit detection + robustness). Steps 1–2 exist to *feed* Step
3, and the whole machine's credibility reduces to that engine's rigor. The standing
standard: **by the time a strategy is Gold it must be defensible, auditable,
testable, and able to survive academic or professional critique, with very little
doubt about its forward edge.** Because Montauk 3.0 makes generation far more
powerful (billions of combos, auto-enter, grind-constantly), **the bar rises with
the search — never falls.** The current-state audit, gap register, and hardening
backlog live in [validation-engine-hardening.md](validation-engine-hardening.md).

---

## 3. The load-bearing seam: authoring vs. the deterministic pipeline

The owner's vision contains an apparent contradiction — "a local agent orchestrates
the pipeline" *and* "the pipeline is deterministic and AI-free." The idea-to-gold
doc already resolved it, and Montauk 3.0 holds the line exactly:

> **There is exactly one non-deterministic step, and it does exactly one job:
> author ideas and format them so the deterministic pipeline can read them.**

- **Authoring (the ONLY LLM step).** Claude (remote, on the owner's other Mac, or
  in bounded local sessions) invents new strategy families, implements each in
  `scripts/strategies/library.py`, smoke-tests it, and deposits a machine-readable
  idea file into the bucket. Its responsibility ends there — it never mines, never
  validates, never certifies, never decides Gold.
- **Orchestration (mechanical, not creative).** The local agent schedules drains,
  triages attention events, restocks/raises queue-low flags, narrates decisions,
  and escalates to the owner. It moves *work through* the pipeline; it does not
  *change the verdict*. Scheduling a run is not the same as deciding its outcome.
- **The deterministic pipeline (no LLM).** Bandit allocation → GA mining →
  lifecycle (promoted/exhausted/condemned) → Gold certification, entirely by
  seeded reproducible rules. It consumes only `implemented: true` families and
  never touches strategy code.

This seam is what makes "AI-orchestrated *and* AI-free validation" true at the
same time. Keep it crisp: **the agent decides *what runs when*; the pipeline
decides *what is Gold*. They never trade jobs.**

---

## 4. System architecture (the always-on server)

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ THE MONTAUK SERVER  (one always-on Mac on Wi-Fi; never sleeps)            │
 │                                                                          │
 │  DATA REFRESH ── pulls + verifies fresh OHLCV / macro feeds, rebuilds    │
 │     manifest, runs quality gates  (scripts/data/*, ops/maintenance.py)   │
 │        │                                                                 │
 │  THE BUCKET ── deep backlog of machine-readable idea files               │
 │     (spike/ideas/*.md + hypothesis-queue.json  [proposed];               │
 │      runs/research_queue/  [exists, embryonic])                          │
 │        │  ▲ owner/Claude pour ideas in (monthly bulk; the ONLY LLM step) │
 │        ▼                                                                 │
 │  DETERMINISTIC PIPELINE (zero-LLM) ── one idea per standing tick:        │
 │     cheap modern-era screen → bandit-allocated GA mine → 7-gate          │
 │     validation → certify → Gold gate → diversity cap → board admission   │
 │     (scripts/search/, scripts/validation/, scripts/certify/)             │
 │        │                                                                 │
 │  LEADERBOARD ── Gold-only; ranked by Montauk Score; top row = active     │
 │     (spike/leaderboard.json)                                             │
 │        │                                                                 │
 │  CHIMERA BREEDER ── assembles regime-ensemble candidates from new        │
 │     winners → drops them back in THE BUCKET as ordinary idea families    │
 │     (must clear the same Gold bar; no shortcut)                          │
 │        │                                                                 │
 │  SIGNAL + APP HOST ── daily risk_on/risk_off, live-holdout demotion,     │
 │     hosts the Montauk app, publishes status.json, fires flip pushes      │
 │     (ops/daily.py, ops/live_holdout.py, ops/app_update.py, iOS companion)│
 │        │                                                                 │
 │  ORCHESTRATION AGENT (small, local) ── runs the schedule, triages        │
 │     events, raises queue-low / escalations to the owner's inbox          │
 │     (ops/scheduler.py, install_launch_agent.py, agent_report.py,         │
 │      runs/operations/agent_inbox.json)  +  remote Claude for real work   │
 └──────────────────────────────────────────────────────────────────────────┘
```

**How much already exists.** A large fraction of this is scaffolded today:
`ops/scheduler.py` + `install_launch_agent.py` give a launchd-driven standing
schedule; `ops/research_runner.py` / `research_queue.py` + `runs/research_queue/`
are an embryonic bucket and runner; `ops/live_holdout.py` is live demotion;
`ops/notifications.py` / `events.py` + `runs/operations/agent_inbox.json` are the
attention/agent surface; `ops/app_update.py` hosts the app; `.github/workflows/
spike.yml` already runs extended searches in the cloud. Montauk 3.0 is mostly
**hardening and wiring this skeleton into a continuous loop**, plus building the
formal bucket front door (§6) — not a greenfield rewrite.

---

## 5. Roles & responsibilities

| Actor | Owns | Must NOT do |
|-------|------|-------------|
| **Owner (Max)** | Pours idea batches into the bucket (~monthly). Acts on signals + escalations. Makes/ratifies charter decisions. One-click ack before a new family goes *active*. | — |
| **Remote Claude** (other Mac, on demand / high-volume) | Authoring: invent families, implement + smoke-test in `library.py`, write idea files. Kick off and steer runs. Narrate results. | Mine, validate, certify, or decide Gold. Promote the active strategy unattended. Move real money. Touch the gate, weights, or Gold contract. |
| **Local orchestration agent** (small, cheap, always-on) | Mechanical orchestration: run the schedule, drain one idea per tick, triage events, restock/queue-low flags, escalate to inbox, narrate. | Author strategy logic of any consequence, change a verdict, or bend the bar. (It schedules; it does not certify.) |
| **The deterministic pipeline** (no LLM) | Screen → mine → validate → certify → admit → demote. Every Gold decision. | Be influenced by any LLM. Consume non-`implemented` families. |

The split is deliberate: **expensive intelligence is rented remotely and only for
the one creative job (authoring); the always-on local agent stays small and
cheap and only does mechanical orchestration.** This is the owner's explicit cost
posture — a powerful local model is not worth the spend.

---

## 6. The bucket — idea format (the front door)

The bucket is the input to the whole machine. Format and contract are specified in
[2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md); the
essentials:

- **One markdown file per idea family.** Frontmatter is the machine-readable
  contract (`name`, `status`, `priority`, `tunables` [≤8, enforced],
  `implemented`, `author`); prose is the brief — a `## Mechanism` block stating
  *why the edge should exist and persist*, plus entry/exit rules and a
  "variants to sweep" block. The `.md` files are the source of truth; the queue
  JSON is derived machine state — no duplicated truth.
- **A strategy "enters the bucket" only when its code already exists** —
  registered in `library.py`, smoke-passed, `implemented: true`. The deterministic
  pipeline never authors or tunes; it only consumes ready families.
- **Verdicts get stamped back** into the frontmatter and a per-family verdict
  ledger, so each authoring session inherits memory and never re-proposes a
  `condemned` mechanism.

> **Reconcile-before-build note.** Two front doors exist in embryo today —
> `runs/research_queue/` (built: `ideas/`, `queue.json`, `hypotheses/`) and the
> proposed `spike/ideas/*.md` + `spike/hypothesis-queue.json`, plus a hand-written
> `spike/strategy-queue/10-new-strategies.md`. Montauk 3.0's first concrete task is
> to **unify these into one canonical bucket**, not to add a third. (Decision
> Register Q7.)

---

## 7. Standing responsibilities of the server

The machine runs these continuously, on its own:

1. **Refresh data** on a schedule — pull, cross-check, re-manifest, re-run quality
   gates; never mine on stale or unverified feeds.
2. **Drain the bucket** — one idea per standing tick (≈hourly), cheap screen first,
   then bandit-allocated GA mining of the parameter space (the "billions of
   combinations" the owner wants swept), within a per-tick compute budget.
3. **Validate + certify** survivors through the unchanged 7-gate pipeline and Gold
   gate; auto-admit Gold to the leaderboard (human ack before *active*).
4. **Maintain the leaderboard** — re-rank by Montauk Score, enforce the family
   diversity cap, re-certify against refreshed data, demote on live evidence.
5. **Breed chimeras** from new winners (§meta-strategy doc) and drop them back into
   the bucket as ordinary families that must clear the same bar.
6. **Host the app + serve signals** — daily `risk_on`/`risk_off`, publish
   `status.json`, fire a push on every regime flip (iOS companion).
7. **Escalate** — when the bucket runs low, when a gate keeps killing a whole
   style, when live demotion fires, or when anything needs a human or an authoring
   session: raise it to the owner's inbox / app banner.

---

## 8. Cadence & the owner's loop

- **Standing tick: ≈1 idea/hour, indefinitely.** As long as the bucket holds
  `queued`/`mining` families, the machine keeps grinding. Duration is just a budget
  knob — the same engine runs a one-hour drain or an all-night cron
  (`ops/scheduler.py` + launchd).
- **Owner cadence: ~monthly bulk idea dump.** Spend spare Claude usage to author a
  deep batch, pour it in, walk away. The machine does the rest until the bucket
  runs low and escalates.
- **Queue-low is a first-class event**, not a silent stall — it drives an app
  banner / inbox item telling the owner it's time to author more (ideally
  *targeted* at the board's missing styles, not just volume — see §9).

---

## 9. Guardrails & failure modes to design against

Scaling generation and running unattended introduces failure modes the manual
system never had. Designing against them is part of the charter:

- **False Gold from breadth — the #1 risk.** The overfit defenses (N_eff
  deflation, PBO) correct for *configs the GA searched*, not for the *number of
  families authored*. If Claude pours in 500 families and 5 reach Gold, those 5 may
  be the lucky tail of 500 lottery tickets the deflation never saw. **Montauk 3.0
  must count generated ideas, not just mined ones, and feed authoring breadth into
  the multiplicity correction.** Without this, scaling the bucket silently
  manufactures fake Gold. This guardrail is a hard prerequisite for "dump in a ton
  of strategies," not a nice-to-have.
- **Authoring selection bias.** Every time the LLM pre-discards ideas it "thinks
  will fail," that is an invisible selection step the statistics can't see.
  Authoring selects on **economic mechanism + distinctness only**, never on guessed
  performance — and should honestly author mechanisms it expects to fail, so the
  deflation sees real breadth.
- **Autonomy eroding the bar.** The machine, optimizing "more strategies promoted,"
  must never find that the cheapest path is a softer bar. The bar is immutable to
  the optimizer (§2). Auto-*admit* is allowed; auto-*activate* onto real money is
  not (human ack).
- **No unattended real money.** Execution stays manual by default. Any bounded
  broker integration is a separate, later, heavily-gated decision (Q4) with
  kill-switches and drawdown halts — never a feature toggle.
- **Data quality at scale.** More feeds = more splice/coverage problems; one bad
  feed silently poisons everything downstream. Per-feed quality gates are
  non-optional and run *before* any mining tick.
- **Cost spiral.** Always-on × continuous mining × remote authoring can quietly get
  expensive with no proportional edge. A compute-budget governor (the bandit
  allocator is its natural home) is required from day one, plus funnel
  instrumentation (Gold yield per 100 ideas, compute per Gold, false-Gold rate).
- **Legibility collapse.** Every new layer must stay explainable on one page
  (§2).

---

## 10. Decision Register (PENDING — gates the build)

These are the forks the owner has **not** yet settled. They are consolidated here
from the pillar docs so the charter conversation happens in one place. **Do not
implement past a decision until it is marked DECIDED here.**

**Status (updated 2026-06-17) — resolved calls live in [decisions.md](decisions.md):**
- **Q1 → DECIDED:** TECL-only, long/flat. The multi-asset / sector-rotation expansion
  (the former Q1–Q3: asset universe, action space, goal function) is now **Montauk 4.0**,
  moved out of this folder to keep 3.0 cleanly single-asset → see `../Montauk 4.0/`.
- **Q5 → DECIDED (refined):** the deterministic pipeline publishes Gold to a **staging
  leaderboard**; the owner **manually admits** to the authority board, and the active
  traded strategy never changes without a human.
- **DESIGN LAW LOCKED (2026-06-17):** *the bar rises with the search, never falls.* As
  generation scales (auto-enter, billions of combos), the validation engine gets
  correspondingly harder — making **Q6 (breadth deflation) a hard prerequisite** before
  high-volume auto-enter goes live (validation-engine-hardening.md, G1).
- **Still open:** Q6 (breadth deflation — locked as a prerequisite; mechanism TBD), Q7
  (unify the bucket), Q8 (budget ceiling).
- **Default (effectively decided):** Q4 — execution stays **manual** for 3.0.
- **New decisions** — the *appliance* principle (dumb deterministic churner, no on-box
  AI), no local agent, auto-enter intake, the error-code maintenance model, the hard
  data-integrity rule, chimera triggers, and the validation north star — are all in
  decisions.md.

> **Q1–Q3 moved to Montauk 4.0.** Asset universe, action-space expansion (SGOV leg /
> sizing / shorts), and the goal function under expansion all depend on the same charter
> amendment and are tracked in `../Montauk 4.0/`. Montauk 3.0 is TECL-only, long/flat.

- **Q4 — Execution model.** Manual (machine proposes, owner executes) for 3.0 — the safe
  default. A bounded broker integration with hard caps is deferred: major
  scope/risk/trust, paper-first if ever. *(Source: idea-to-gold #7.)*

- **Q5 — Autonomy boundaries.** Resolved by the staging gate (D4): the agent may mine,
  validate, certify, publish to *staging*, propose, and alert — but NOT auto-admit to the
  authority board, NOT auto-activate a champion onto real money, NOT amend its own bar.
  Still to specify: the kill-switches / circuit-breakers / drawdown halts. *(Source:
  idea-to-gold #7.)*

- **Q6 — Breadth deflation (the false-Gold fix).** **Locked as a hard prerequisite
  (2026-06-17).** Count *generated* families, not just mined configs, and feed authoring
  breadth into the multiplicity correction *before* scaling the bucket. Mechanism is the
  top hardening-backlog item. *(Source: idea-to-gold #1; validation-engine-hardening G1.)*

- **Q7 — Unify the bucket front door.** Reconcile `runs/research_queue/` (built),
  the proposed `spike/ideas/*.md` + `spike/hypothesis-queue.json`, and the
  hand-written `spike/strategy-queue/` into one canonical bucket format and
  location. First concrete build task; needs a one-time decision so we don't ship a
  third parallel queue. *(Source: idea-to-gold build plan + current repo state.)*

- **Q8 — Hardware, budget, hosting.** What machine is the always-on server (the
  appliance — D2/D3, hardware TBD), what does 24/7 mining + remote authoring + continuous
  data cost per month, and what budget ceiling does the compute governor enforce?

---

## 11. Phasing (de-risk incrementally — illustrative, not committed)

Each phase is a real stopping point that delivers value alone. The
least-reversible piece (real-money autonomy) comes last and stays optional. The
multi-asset / action-space expansion is **out of 3.0 entirely** — it is Montauk 4.0
(`../Montauk 4.0/`).

1. **Unify the bucket + ship the idea→gold front door** (idea-to-gold build plan).
   Formalize the `.md` idea format, the queue brain, the authoring entrypoint, and
   the bounded-duration drain. Resolves Q7 (one bucket).
2. **Bulletproof the validation engine** — run the hardening backlog (breadth
   deflation first, then the line-by-line correctness audit and board-level
   multiple-testing) so every Gold is academically defensible. This is the **north
   star** and runs alongside everything, not after it
   (`validation-engine-hardening.md`).
3. **Harden the always-on loop.** Wire the existing ops skeleton
   (`scheduler` + launchd + `research_runner` + `live_holdout` + `notifications`)
   into a continuous, self-restocking, self-escalating loop with a compute governor
   and funnel instrumentation. Still TECL-only, still manual execution.
4. **Ship the monitoring surface.** iOS companion app + widget + flip push, so the
   owner can leave the machine alone and still feel the signals
   (`2026-06-10-ios-companion-app.md`).
5. **Chimera breeding** from leaderboard winners, routed back through the bucket and
   the unchanged gate (`2026-04-23-meta-strategy-design.md`).
6. **Bounded execution** (only if Q4/Q5 settled, paper-first) — the last, most
   optional, most gated piece.

The ordering matters: **prove the always-on conveyor honest *and* bulletproof the
validation engine at one asset before anything else; real-money autonomy dead last;
the multi-asset expansion is a separate release (Montauk 4.0).**

---

## 12. The other Montauk 3.0 docs

This charter is the umbrella; the detail lives in the pillar docs in this folder
(see [README.md](README.md) for the map):

- **The conveyor:** [2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md)
- **The validation engine (north star):** [validation-engine-hardening.md](validation-engine-hardening.md)
- **Chimeras:** [2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md)
- **The monitoring surface:** [2026-06-10-ios-companion-app.md](2026-06-10-ios-companion-app.md)
- **Resolved decisions:** [decisions.md](decisions.md)

The multi-asset / action-space expansion (the multi-sector-machine + search-expansion
docs) has moved to **`../Montauk 4.0/`** — a separate, later release, out of 3.0 scope.

---

*Draft for the charter conversation. The next moves: the validation-engine hardening
backlog (the north star), then the remaining open items in §10 — Q6 (breadth deflation,
a locked prerequisite), Q7 (unify the bucket), Q8 (budget). Code comes after the
decisions, never before them.*
