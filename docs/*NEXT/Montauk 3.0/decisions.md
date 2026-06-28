# Montauk 3.0 — Decision Log

Running ledger of **resolved** decisions for the Montauk 3.0 always-on strategy
factory. Pairs with [charter.md](charter.md): the charter's **Decision Register
(§10)** holds the open questions; this file holds the answers as they land. When a
decision changes a core charter claim, the charter gets updated to match — never by
drift.

Each entry: the **call**, the **why**, and the **implications** for the build.

---

## 2026-06-15 — first decision session

### D1 — Scope: TECL-only for v1  *(charter Q1)*
**Call.** Montauk 3.0 is **TECL-only**, long/flat. The multi-asset / sector-rotation
expansion is a **separate later release — Montauk 4.0** (`../Montauk 4.0/`), not part of
3.0.
**Why.** Keeps the goal function simple (`share_multiple` vs B&H TECL — already built)
and the system legible; adds no new data-coverage or cross-asset-benchmark problems.
**Implications.** The action-space expansion (SGOV leg / sizing / shorts), the
cross-asset goal function, and the rotation brain are all **Montauk 4.0**, moved out of
this folder (former charter Q2/Q3).

### D2 — The server is a *dumb deterministic churner* (the appliance principle)
**Call.** The machine running the pipeline has **no AI/agent capability in steady
state.** It holds three things — the **bucket** of untested-but-implemented
strategies, **all the scripts** to run the pipeline, and **verified data** — and the
CPU just **churns the bucket through the deterministic pipeline.** No model runs on
the box during normal operation.
**Why.** Cost (no expensive local model), legibility (a deterministic appliance is
auditable), honesty (no LLM anywhere near the Gold verdict). Owner's framing: "the Mac
is just there for processing."
**Implications.** All intelligence is *off-machine* or *human-initiated*:
- **Idea authoring** (novel mechanisms = new code) happens off-machine in remote
  Claude; the *output* (code + idea files) is deposited into the bucket. (D6)
- **Chimera breeding** is **deterministic** — once the meta-strategy engine is written
  once, assembling a specific chimera from board winners is config math, not new code,
  so the churner does it on-box. (D9)
- **Maintenance/repair** uses Claude, but only when the *human* brings it in. (D7)

### D3 — No local orchestration agent
**Call.** **No local LLM "agent."** Orchestration is **deterministic scripts** (launchd
+ `scripts/ops/scheduler.py`) churning the bucket on a standing schedule.
**Why.** Follows from D2; orchestration work is purely mechanical.
**Implications.** "The agent" = the standing deterministic loop + the escalation
surface (`runs/operations/agent_inbox.json`) that *remote* Claude reads when the human
engages. Scheduling ≠ deciding Gold (the charter §3 seam holds).

### D4 — Promotion: staging leaderboard → manual admission  *(charter Q5)*
**Call.** Two-tier board. The deterministic pipeline publishes every Gold-certified
candidate to a **staging leaderboard** (auto-populated). The owner **manually admits**
chosen rows to the **authority leaderboard.** The **active traded strategy is the top
of the authority board** and never changes without a human.
**Why.** Auto-admitting a lucky-tail strategy toward real money is the one place
autonomy is dangerous. A human gate at admission is cheap insurance; the machine still
does all the work up to that point.
**Implications.** Build: a `staging` leaderboard artifact distinct from
`spike/leaderboard.json` (the authority board); an admit/reject action; a definition of
what the owner reviews per staged candidate *(open — see questions).* Supersedes the
charter's earlier "auto-admit to board + ack before active" with a stricter gate.

### D5 — Schedule: grind continuously
**Call.** The churner runs **continuously**, one family in focus at a time,
bandit-prioritized, cheap-screen-first.
**Why.** The server should earn its keep 24/7.
**Implications.** Need a per-tick + per-day compute budget and a defined
bucket-empty behavior *(open — see questions).*

### D6 — Intake: ideas auto-enter the bucket
**Call.** Authored ideas (code + idea `.md`, smoke-passed, `implemented: true`)
**auto-enter** the bucket. No human pre-review of idea code.
**Why.** "Even if the strategy is bad the validation pipeline will catch it." The
frozen Gold gate + the staging/admission gate (D4) are the backstop, so bad ideas cost
only cheap screen compute, never trust.
**Implications.** Makes the **breadth-deflation guard a hard prerequisite** (charter
Q6): high-volume auto-enter means Gold must get *harder* the more families are
generated, or volume manufactures false Gold. Authoring selects on **mechanism +
distinctness only**, never on guessed performance.

### D7 — Maintenance: a structured error/maintenance-code catalog
**Call.** The deterministic machine emits a **catalog of structured error/maintenance
codes** on faults. The owner resolves via Claude — **remote-first** (preferred), or by
**logging into Claude directly on the machine** for major issues.
**Why.** Keeps steady-state operation agent-free (D2) while giving a fast, legible
repair path: a code tells Claude exactly what broke and how to fix it.
**Implications.** Build a fault taxonomy + codes on the existing ops seam
(`scripts/ops/errors.py`, `doctor.py`, `maintenance.py`, `hardening.py`,
`fresh_shell_check.py`). Each code = symptom + likely cause + fix playbook. Taxonomy
scope *(open — see questions).*

### D8 — Data integrity: never mine *or* validate on unverified data
**Call.** Hard rule: the machine **never mines and never validates** on data that is
not **verified, validated, and complete.** Incomplete/unverified data halts *both*
mining and validation.
**Why.** A single bad/partial feed silently poisons every downstream verdict.
**Implications.** The data-refresh step gates the whole churn: on any quality FAIL,
divergence, or incompleteness → halt mining + validation, keep serving the last-good
signal, emit a maintenance code (D7).

### D9 — Chimera triggers
**Call.** Breed chimeras when **(a)** a new strategy family appears, **(b)** a new #1
emerges, or **(c)** the leaderboard significantly shuffles.
**Why.** Chimeras are most valuable exactly when the winner set changes.
**Implications.** Chimera generation is deterministic (D2) and routes the new ensemble
back into the bucket as an ordinary family that must clear the same Gold bar — no
shortcut. Define "significant shuffle" concretely *(open).* Depends on the
meta-strategy engine existing (`2026-04-23-meta-strategy-design.md`).

---

## 2026-06-17 — the validation engine is the north star

### D10 — Validation is the guiding light; the three-step pipeline
**Call.** The pipeline is three steps — **(1) bucket/authoring → (2) backtest +
parameter tuning → (3) validation engine** (overfit detection + robustness). Step 3
is the **north star**: by the time a strategy is Gold it must be **defensible,
auditable, testable, and survive academic/professional critique**, with very little
doubt of its forward edge. Making the validation engine correct and as robust as
possible is a first-class Montauk 3.0 workstream.
**Why.** No overfit/false strategies on the board. The leaderboard is a
certification; one false Gold turns it back into a watchlist.
**Implications.**
- **The bar rises with the search, never falls** — as generation scales (auto-enter,
  billions of combos), Step 3 must get correspondingly harder. This makes the
  **breadth-deflation guard (G1 / charter Q6) a hard prerequisite**, not optional.
- A **line-by-line correctness audit** of `scripts/validation/` is scheduled (G10).
- **Honest humility** is required about the data-scarcity ceiling (G3): ~3–4
  independent macro regimes and <20 trades mean forward CIs are wide no matter how
  good the method — every Gold claim states how confident *and why it isn't more*.
- Full audit, gap register, and backlog: `validation-engine-hardening.md`.
**Current read (2026-06-17).** The engine is already professional-grade (CSCV/PBO,
expected-max deflation, true OOS walk-forward, stationary bootstrap, Morris
sensitivity, live-forward holdout + auto-demotion). Top gaps: G1 breadth
multiplicity, G2 no board-level SPA/Reality-Check test, G4 the validator's own
hand-tuned weights/anchors can themselves be overfit.

---

## Deferred / still open

- **Substrate / hardware (charter §4):** **DEFERRED** — hardware not chosen. Locked
  constraint regardless: must satisfy the appliance principle (D2). Mac is ideal (the
  ops stack is launchd-based) but not committed.
- **Charter Q6** (breadth deflation — now a hard prerequisite), **Q7** (unify the
  bucket front door), **Q8** (budget ceiling) — open; next question set.
- **Charter Q2/Q3** (action space, goal function) → **Montauk 4.0** (`../Montauk 4.0/`).
  **Q4** (broker execution) — deferred; manual execution is the 3.0 default.
