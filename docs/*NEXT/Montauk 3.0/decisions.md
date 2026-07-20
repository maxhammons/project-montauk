# Montauk 3.0 — Decision Log

Running ledger of **resolved** decisions for the Montauk 3.0 always-on strategy
factory. Pairs with [charter.md](charter.md): the charter's **Remaining Decisions
(§16)** holds the open questions; this file holds the answers as they land. When a
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

### D2 — The server is a *dumb deterministic churner* (SUPERSEDED by D11)
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

### D3 — No local orchestration agent (SUPERSEDED by D11)
**Call.** **No local LLM "agent."** Orchestration is **deterministic scripts** (launchd
+ `scripts/ops/scheduler.py`) churning the bucket on a standing schedule.
**Why.** Follows from D2; orchestration work is purely mechanical.
**Implications.** "The agent" = the standing deterministic loop + the escalation
surface (`runs/operations/agent_inbox.json`) that *remote* Claude reads when the human
engages. Scheduling ≠ deciding Gold (the charter §3 seam holds).

### D4 — Promotion: staging leaderboard → manual admission (SUPERSEDED by D12)
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

### D5 — Schedule: grind continuously (REFINED by D15)
**Call.** The churner runs **continuously**, one family in focus at a time,
bandit-prioritized, cheap-screen-first.
**Why.** The server should earn its keep 24/7.
**Implications.** Need a per-tick + per-day compute budget and a defined
bucket-empty behavior *(open — see questions).*

### D6 — Intake: ideas auto-enter the bucket (REFINED by D13 and D14)
**Call.** Authored ideas (code + idea `.md`, smoke-passed, `implemented: true`)
**auto-enter** the bucket. No human pre-review of idea code.
**Why.** "Even if the strategy is bad the validation pipeline will catch it." The
frozen Gold gate + the staging/admission gate (D4) are the backstop, so bad ideas cost
only cheap screen compute, never trust.
**Implications.** Makes the **breadth-deflation guard a hard prerequisite** (charter
Q6): high-volume auto-enter means Gold must get *harder* the more families are
generated, or volume manufactures false Gold. Authoring selects on **mechanism +
distinctness only**, never on guessed performance.

### D7 — Maintenance: a structured error/maintenance-code catalog (REFINED by D11 and D13)
> **Historical scope note:** the agent-free rationale below is superseded.
> Structured fault codes remain required, but current steady state and bounded
> repair authority are defined by D11 and D13.

**Call.** The deterministic machine emits a **catalog of structured error/maintenance
codes** on faults. The owner resolves via Claude — **remote-first** (preferred), or by
**logging into Claude directly on the machine** for major issues.
**Why.** Keeps steady-state operation agent-free (D2) while giving a fast, legible
repair path: a code tells Claude exactly what broke and how to fix it.
**Implications.** Build a fault taxonomy + codes on the existing ops seam
(`scripts/ops/errors.py`, `doctor.py`, `maintenance.py`, `hardening.py`,
`fresh_shell_check.py`). Each code = symptom + likely cause + fix playbook. Taxonomy
scope *(open — see questions).*

### D8 — Data integrity: never mine *or* validate on unverified data (REFINED by D20)
**Call.** Hard rule: the machine **never mines and never validates** on data that is
not **verified, validated, and complete.** Incomplete/unverified data halts *both*
mining and validation.
**Why.** A single bad/partial feed silently poisons every downstream verdict.
**Implications.** The data-refresh step gates the whole churn: on any quality FAIL,
divergence, or incompleteness → halt mining + validation, keep serving the last-good
signal, emit a maintenance code (D7).

### D9 — Chimera triggers (SUPERSEDED by D22)
**Call.** Breed chimeras when **(a)** a new strategy family appears, **(b)** a new #1
emerges, or **(c)** the leaderboard significantly shuffles.
**Why.** Chimeras are most valuable exactly when the winner set changes.
**Implications.** Chimera generation is deterministic (D2) and routes the new ensemble
back into the bucket as an ordinary family that must clear the same Gold bar — no
shortcut. Define "significant shuffle" concretely *(open).* Depends on the
meta-strategy engine existing (`2026-04-23-meta-strategy-design.md`).

---

## 2026-06-17 — the validation engine is the north star

### D10 — Validation is the guiding light; the three-step pipeline (REFINED by D16)
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

**Reassessment (2026-07-17).** “Professional-grade” is retained above as the
June snapshot, not the current claim. Until the correctness audit, breadth and
board-level correction, deployable execution contract, mandatory-gate semantics,
and per-frozen-row forward attribution are complete, the accurate status is
**advanced but provisional**. See the expanded G1–G13 register.

---

## 2026-07-17 — clarified operating contract

This session records the owner's answers to the first two vision questionnaires.
Where these calls conflict with June entries, the newer numbered decision
explicitly supersedes the older one. History is retained so the change is
auditable.

### D11 — A scheduled, model-agnostic frontier agent is part of steady state

**Call.** Montauk 3.0 includes a standing agent loop on the always-on machine. It
may call Claude, Codex, or another remote frontier model through a subscription or
API; the provider is replaceable. “No local AI” means **no locally hosted
foundation model**, not “no agent.” The agent continuously authors strategy
candidates, reads aggregate results and the failure ledger, restocks and
prioritizes queues, attempts bounded candidate repair, prepares reports, and
escalates operational failures. **D11 supersedes D2 and D3.**

**Why.** The intended appliance removes ongoing idea-generation and research
maintenance from Max. A bucket that depends on monthly manual refills does not
meet that goal.

**Implications.**

- Gold, ranking, recertification, and trusted-signal verdicts remain entirely
  deterministic.
- One model at a time is sufficient, but prompts and candidate formats may not
  make one provider the architecture.
- The agent should review recent outcomes before generating the next batch.
- Subscription and API access should both be evaluated for reliability and cost.

### D12 — One Gold leaderboard; no staging board or Trade Roster

**Call.** Every configuration that satisfies the current Gold contract
automatically enters the current leaderboard. There is no staging leaderboard,
authority board, or Trade Roster. Every Gold configuration remains independently
addressable, while the interface may group/collapse rows by family. A row that
loses Gold moves to a historical Gold archive. **D12 supersedes D4.**

**Why.** Gold itself is the admission contract. Adding a second approval concept
creates needless process and a duplicate source of authority.

**Implications.**

- Gold publication and board reranking are automatic.
- The current board is conceptually unbounded and therefore needs database-backed
  pagination, filtering, and family grouping rather than a giant JSON document.
- Human authority applies to normal active-strategy changes, not board admission.

### D13 — Autonomous strategy code is allowed; the core is forbidden

**Call.** The agent may automatically write isolated executable strategy code or
declarative strategy definitions and submit them without human pre-review. It may
try two or three immediate repairs when candidate intake fails, then place the
candidate in a lower-priority repair queue. It may commit generated research
frequently for history and rollback.

The agent may **never**, without explicit owner-directed work, change the data
pipeline, execution semantics, backtest/search engine, validation suite, Gold
thresholds, score/ranking formulas, recertification and active-authority rules,
operations safety layer, protected tests/fixtures, or the controls that enforce
this boundary.

**Why.** Autonomous authoring creates the desired throughput; autonomous
methodology changes would let the researcher alter the exam and destroy trust.
This is the highest-priority agent rule.

**Implications.**

- The prohibition must be enforced mechanically through credentials, protected
  paths/repositories, review boundaries, signed/versioned artifacts, or an
  equivalent control. Prompt instructions and Git rollback are not enforcement.
- Generated code is untrusted **before** validation; static checks, sandboxing,
  denied capabilities, resource limits, deterministic inputs, and immutable core
  mounts are required before execution.
- A ready family includes logic, parameter space, a short rationale, expected
  failure mode, smoke results, lookahead/static-safety results, and immutable
  version metadata.

### D14 — One complete candidate contract, regardless of author

**Call.** Human-authored and AI-authored strategies face the same mandatory
backtest, correctness, and validation evidence planks and rigor. A structurally
inapplicable algorithm may have a predeclared equivalent or valid
`not_applicable` treatment; no origin earns a T0/T1 shortcut, skipped evidence,
or silent weight renormalization. The cost-ordered funnel rejects work as early
as honestly possible: intake and safety checks, cheap screen, full required
backtest/B&H gates, full validation, artifact verification, then Gold.

**Why.** The result should depend on evidence, not who typed the initial idea.
There is no value in running expensive anti-overfit validation for a configuration
that already fails the required economic gate.

**Implications.**

- A configuration can pass correctness/anti-overfit checks and still fail Gold on
  performance.
- “Same gates” does not erase adaptive-selection bias. The complete observable
  search breadth, family/campaign lineage, and board-level multiplicity must still
  be counted and corrected.
- Existing tier-skipping and renormalized validation paths require reconciliation
  before they can represent this decision.

### D15 — Continuous adaptive search, not a fixed one-idea cadence

**Call.** Montauk maintains a deep queue and uses available research compute
continuously. It favors promising families, reserves capacity for weaknesses in
the current champion, and permanently reserves a smaller exploration lane for
unusual ideas. Allocation adapts to useful survivor/Gold yield and queue state.
Recertification, verified-data work, trusted-signal generation, and operational
health always preempt discovery research. **D15 refines D5.**

**Why.** The desired quantity is the maximum number of *honest* experiments the
machine can evaluate, not an arbitrary family/hour count.

**Implications.**

- The 70% promising / up-to-20% champion-weakness / 10% exploratory split is an
  initial planning heuristic, not a frozen scheduler constant.
- Retired mechanisms are sampled periodically or when new data, complementary
  indicators, champion weaknesses, or material redesigns justify another look.
- Exact configuration deduplication is version-aware; meaningful new data or
  methodology versions may justify retesting.

### D16 — Gold is the strongest versioned evidence certification Montauk can make

**Call.** Gold means a frozen configuration beats TECL buy-and-hold across every
required real-data evaluation period, passes the complete versioned correctness
and anti-overfitting contract, and is certified fit to trade to the strongest
extent Montauk can establish from available evidence. It means no disqualifying
overfit/correctness failure was detected; it does not guarantee every future call
or return.

Real market evidence determines eligibility. Synthetic history is diagnostic and
is preferred to show strength, but it does not substitute for real data. One bad
trade does not revoke Gold; sustained or contract-defined failure can. **D16
refines D10.**

**Why.** Max wants the strongest defensible assurance, especially against
overfitting, without encoding an impossible promise about future markets.

**Implications.** Exact real-data periods, recent-performance treatment,
synthetic catastrophic-failure behavior, executable fill timing, rolling B&H
demotion, minimum evidence, and search-breadth correction remain open
specification work.

### D17 — Configurations are the owner-facing strategies; experiment history is a database

**Call.** The canonical vocabulary is:

- idea = written hypothesis;
- family = executable mechanism plus a parameter space;
- configuration = one family with one exact parameter set; and
- candidate = a configuration that completed a backtest.

Owner-facing summaries may call configurations “strategies,” but funnel counts
must name their stage. High-volume experiment history belongs in a queryable local
database. Core code, strategy definitions/source, Gold publication snapshots, and
disaster-recovery essentials receive Git/GitHub backup. Every Gold row must remain
fully reproducible from frozen code/definition, parameters, data fingerprint,
versions, seeds/provenance, and artifacts.

**Why.** Millions or billions of configurations cannot be represented honestly or
operated safely as scattered scripts and JSON files.

### D18 — Recommended and Active are separate authority states

**Call.** Montauk automatically computes its recommended strategy, but a normal
active-strategy change requires Max's explicit approval. Ignoring or declining a
recommendation leaves the incumbent active. A manual override persists until Max
removes it and must be unmistakable in every authority surface.

**Why.** Ranking is a deterministic recommendation; control of the traded
strategy remains human.

**Implications.**

- Confidence improvement matters more than an equally sized performance
  improvement, and trivial gains should not create switch churn.
- The exact superiority threshold, forward-observation/cooling-off requirement,
  and emergency fallback state machine remain open.
- No implementation may interpret a leaderboard reorder as permission to trade.

### D19 — Quiet, read-mostly operation with a conversational notification surface

**Call.** The normal app experience is “Montauk at a glance”: current state,
active strategy and Gold status, override/recommendation status, Montauk Score,
Validation Score (or calibrated Confidence only after calibration justifies
that term), deployable Performance, simple gate lights, and plain-English
weaknesses. It is primarily read-only, with no forest of sliders or duplicated
control surfaces. A daily digest is sufficient as the initial notification
cadence because Montauk is not intraday. Slack is the likely conversation,
notification, and eventually owner-command surface.

**Why.** Healthy steady state should be quiet and easy. Detail remains inspectable
without demanding constant tinkering.

**Implications.** Slack approvals/commands require an explicit authenticated,
idempotent, audited authority contract before implementation.

### D20 — Failed current data freezes trusted evolution

**Call.** When current data fails verification, Montauk produces no new trusted
signal and performs no current certification, recertification, demotion, or
leaderboard mutation from that data. It displays the last verified signal with a
stale timestamp and requests human intervention. On recovery, it verifies caught-
up data and recertifies the active strategy before resuming lower-priority work.
**D20 refines D8.**

**Why.** Partial or divergent data cannot be permitted to change authority.

**Implications.** Research may potentially continue against a frozen last-good
dataset if it is clearly labeled and cannot publish current Gold; whether to allow
that mode remains open.

### D21 — Manual brokerage and human-controlled release progression

**Call.** Brokerage execution remains manual for all of 3.x. iOS is not required
for 3.0 and belongs to 4.x/5.x if still useful. Multi-asset work is 4.x. No soak
duration or evidence counter automatically begins 4.x; only Max makes that
decision.

### D22 — Chimera is conditional research, not standing infrastructure

**Call.** Chimera waits until Montauk has several materially independent Gold
strategies and can keep correlated configurations from dominating the vote. It is
then an ordinary candidate family that must beat the same comparator and pass the
same complete contract. If no Chimera beats the best single strategy, retaining
the single strategy is correct. **D22 supersedes D9's automatic standing
triggers.**

### D23 — Accuracy first; optimize measured bottlenecks behind parity (REFINED by D26)

> **Historical scope note:** D26 fixes Rust as the production language. The
> Rust/Go alternatives below are retained as the earlier design step; only the
> profile-first, no-per-configuration-compilation, and parity principles remain
> current.

**Call.** Language is an implementation choice, not a trading truth. The leading
architecture to benchmark is a prebuilt native Rust/Go evaluator with a reusable
primitive library. For normal families, the agent emits compact strategy
definitions that compose those primitives. For a genuinely novel mechanism, the
agent may author one isolated Rust/Go module compiled once for that family and
used across its parameter sweep. Do not generate or compile a unique program for
every configuration. Maintain a legible reference oracle, profile representative
workloads, and require exact or explicitly tolerance-pinned parity before any
optimized path can participate in certification.

**Why.** Speed increases honest search capacity only when semantics stay identical.
Compilation catches syntax/type errors, not lookahead, bad logic, or false edge.

### D24 — Forward evidence is first-class and recertification has priority

**Call.** Each frozen Gold row must visibly accumulate evidence from market bars
that occurred after its freeze/certification time. Active-strategy recertification
has highest research priority. The original scheduling intuition was active
daily, top 20% or top 5,000 twice weekly, and the full board every two weeks; the
owner prefers evidence/staleness-driven triggers if they are more meaningful.

**Implications.** The exact forward waiting period, staleness threshold, rolling
demotion rule, board recertification policy, and consequences of a core
methodology version change remain open.

### D25 — Completed questionnaire rounds must be promoted into the active docs

**Call.** After Max completes each questionnaire round, the reviewing agent must
read the full answer set and update the 3.0 README, charter, decision log, and
every affected pillar plan before drafting another questionnaire or preparing a
coding handoff. The answered questionnaire is preserved unchanged as source
evidence; the reconciled Markdown documents become current project truth.

**Why.** The vision cannot depend on one model's conversation context or force a
later coding agent to infer policy from several answered files.

**Implications.** Each round ends with a reconciliation pass: record new
decisions, mark superseded calls without deleting history, resolve
cross-document contradictions, update the remaining-question register, and
verify the answered questionnaire itself was not rewritten.

### D26 — Rust is the fixed production strategy/evaluation language (REFINED by D27)

**Call.** The agent does not choose whether a strategy is implemented in Python,
Go, or Rust. Rust is the fixed production language for strategy logic,
configuration evaluation, and the performance-critical backtest path.

The normal agent output is a typed declarative family specification: logic built
from a protected Rust primitive library plus parameter domains and constraints.
The Rust engine expands that search space into exact configurations, which are
data records rather than source files. When a genuinely novel mechanism cannot
be represented, the agent may author one isolated Rust family module compiled
once for that immutable family version and reused across its entire parameter
sweep.

Python may remain a readable reference/parity implementation, audit tool, and
test harness. It is not a production strategy format or a second source of
trading truth. Go is not part of the strategy/evaluator decision.

**Why.** One production language, SDK, primitive library, compiler toolchain, and
execution model improves consistency, containment, caching, reproducibility, and
throughput. Avoiding per-configuration compilation preserves the speed advantage
when Montauk evaluates millions or billions of parameter sets.

**Implications.** The remaining representation decision is whether 3.0 begins
declarative-only or includes the isolated Rust-module escape hatch immediately.
The autonomous agent may create family specifications and isolated family
modules, but it may not modify the protected Rust engine or shared primitive
library.

### D27 — The agent specifies families; Rust generates configurations

**Call.** Optimize normal strategy authoring for the owner's two priorities:
fastest evaluation and the fewest preventable implementation errors. The agent
therefore does **not** hand-write exact configurations and does not write normal
strategy source code. It submits one schema-constrained declarative family
specification containing:

- a typed logic graph using registered Rust primitives;
- parameter types, domains, and cross-parameter constraints;
- required inputs, timing, warm-up, and state behavior;
- rationale, expected failure mode, and provenance; and
- deterministic fixture expectations.

The protected Rust engine validates and canonicalizes the specification,
generates only valid exact parameter configurations, deduplicates them, compiles
the family graph into an execution plan once, shares/precomputes common features,
and batch-evaluates the resulting configurations.

**Why.** This removes normal agent compile errors, prevents invented primitive
names and malformed parameter combinations, avoids token-heavy configuration
enumeration, enables shared Rust computation, and preserves one execution truth.
A structurally valid strategy can still be economically wrong; backtesting and
validation remain responsible for that distinction.

**Implications.** 3.0 begins declarative-first. The isolated agent-authored Rust
family-module path is staged and remains disabled until containment, causal
access, determinism, resource, and parity acceptance tests pass. When enabled it
is an exception for an unexpressible mechanism, not the default authoring path.
D27 resolves D26's declarative-versus-immediate-escape-hatch question.

## Deferred / still open

- Exact executable signal/fill timing and the B&H comparator.
- Required real-data periods, recent-performance policy, synthetic red-flag
  behavior, rolling demotion, minimum evidence, and confidence claim.
- Search-breadth accounting and board-level false-discovery control. This is a
  hard prerequisite for high-volume autonomous search.
- Canonical StrategySpec/intake schema, initial Rust primitive vocabulary,
  staged module-admission authority, sandbox, and protected-core enforcement.
- Meaningful-superiority, cooling-off/forward-evidence, emergency fallback, and
  no-Gold authority rules.
- Recertification/staleness scheduling and methodology-change consequences.
- Slack command/approval permissions.
- Experiment retention, backup/restore objectives, and quantified 3.0 acceptance
  tests.
- Hardware SKU and provider/cost selection, after representative profiling.
- Action-space and multi-asset work remain Montauk 4.x; iOS is 4.x/5.x; brokerage
  is manual throughout 3.x.
