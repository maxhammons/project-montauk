# Montauk 3.0 — Decision Log

Running ledger of **resolved** decisions for the Montauk 3.0 always-on strategy
factory. Pairs with [charter.md](charter.md): the charter holds the integrated
operating contract while this file preserves the calls and their history. Section
16 of the charter now holds bounded calibration studies, not owner-policy questions
that an implementation agent may answer by implication. When a decision changes a
core charter claim, the charter gets updated to match — never by drift.

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

### D13 — Autonomous strategy code is allowed; the core is forbidden (REFINED by D31–D32)

**Call.** The agent may automatically write isolated executable strategy code or
declarative strategy definitions and submit them without human pre-review. It may
try the original artifact plus at most two immediate repairs when candidate
intake fails, then place the
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

### D15 — Continuous adaptive search, not a fixed one-idea cadence (REFINED by D33)

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

### D16 — Gold is the strongest versioned evidence certification Montauk can make (REFINED by D28–D30)

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

**Implications.** D28–D30 ratify the policy for real/recent evidence, synthetic
diagnostics, executable timing, missing evidence, and economic passage. Their
exact statistical values remain bounded calibration work rather than open owner
authority.

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

### D18 — Recommended and Active are separate authority states (REFINED by D34–D35)

**Call.** Montauk automatically computes its recommended strategy, but a normal
active-strategy change requires Max's explicit approval. Ignoring or declining a
recommendation leaves the incumbent active. A manual override persists until Max
removes it and must be unmistakable in every authority surface.

**Why.** Ranking is a deterministic recommendation; control of the traded
strategy remains human.

**Implications.**

- Confidence improvement matters more than an equally sized performance
  improvement, and trivial gains should not create switch churn.
- D34 fixes the initial superiority thresholds, five-bar persistence, and
  Pending Gold cooling period; D35 fixes the emergency fallback state machine.
- No implementation may interpret a leaderboard reorder as permission to trade.

### D19 — Quiet, read-mostly operation with a conversational notification surface (REFINED by D38)

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

**Implications.** D38 defines the Slack mutation allowlist and the authenticated,
idempotent, replay-protected audit contract required before implementation.

### D20 — Failed current data freezes trusted evolution (REFINED by D36)

**Call.** When current data fails verification, Montauk produces no new trusted
signal and performs no current certification, recertification, demotion, or
leaderboard mutation from that data. It displays the last verified signal with a
stale timestamp and requests human intervention. On recovery, it verifies caught-
up data and recertifies the active strategy before resuming lower-priority work.
**D20 refines D8.**

**Why.** Partial or divergent data cannot be permitted to change authority.

**Implications.** D36 resolves recovery priority: already-safe partial work may
be quarantined, while exploratory compute pauses until verified catch-up, Active
recertification/current signal, and top-cohort refresh complete.

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

### D24 — Forward evidence is first-class and recertification has priority (REFINED by D34 and D36)

**Call.** Each frozen Gold row must visibly accumulate evidence from market bars
that occurred after its freeze/certification time. Active-strategy recertification
has highest research priority. The original scheduling intuition was active
daily, top 20% or top 5,000 twice weekly, and the full board every two weeks; the
owner prefers evidence/staleness-driven triggers if they are more meaningful.

**Implications.** D34 sets the normal 20-bar Pending Gold period and D36 sets the
renewal cadence, rolling demotion behavior, and incompatible-methodology stale
policy. The numeric operating characteristics remain versioned calibration work.

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

### D26 — Rust is the fixed production strategy/evaluation language (REFINED by D27 and D31)

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

**Implications.** 3.0 begins declarative-first. D31 settles the staged module
admission authority. The autonomous agent may create family specifications and
isolated family modules, but it may not modify the protected Rust engine or
shared primitive library.

### D27 — The agent specifies families; Rust generates configurations (REFINED by D31)

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

## 2026-07-21 — Questionnaire 3 final operating contract

The completed questionnaire is preserved unchanged in `Questionnaires/`. The
calls below promote its answers into current planning truth.

### D28 — Gold is fail-closed and every configuration faces every required plank

**Call.** Gold uses the wording accepted in Questionnaire 3: it is Montauk's
highest current certification of one exact frozen configuration under named data,
execution, engine, validation, and monitoring versions. It means no
disqualifying correctness, overfit, or evidence failure was detected to the
strongest extent available evidence supports; it does not guarantee a future
trade or return.

Human and agent origin are irrelevant. No mandatory test can be skipped because
of simplicity, compute cost, apparent waste, or upstream judgment. Missing,
underpowered, skipped, unverifiable, or incomplete required data blocks Gold.
`not_applicable` is permitted only when predeclared and backed by the required
equivalent evidence. Montauk Score ranks eligible Gold; it cannot compensate for
a failed plank. An empty current board is valid.

**Why.** Max's trust depends on every row making the same complete promise. A
false Gold row is worse than a missed opportunity.

### D29 — Real-data superiority is broad, recent, margin-bearing, and versioned

**Call.** Gold must beat matched TECL B&H over complete real history, a fixed
recent horizon initially centered on trailing five years, and a small
predeclared rolling/window robustness design. Max's intent is that a Gold
strategy should beat B&H however the real history is reasonably sliced, without
building a complicated or retrospectively hand-picked exam.

The economic floor is greater than 1.0. An initial margin around 1.10 is the
owner's provisional starting intuition; the exact margin and one-sided
lower-bound test require Phase-A calibration. A future increase is a new
owner-approved contract version and full compatibility review, not an automatic
ratchet caused by finding many winners. Recent evidence affects eligibility,
rank, and persistent rolling demotion under separate frozen rules.

The matched comparator uses adjusted total-return TECL, identical eligible start
and capital, first obtainable purchase timing, explicit costs, and unrounded
decisions. Initial risk-off cash earns zero in the Gold comparison.

**Why.** A barely positive point estimate or one excellent distant period is not
the strong performance-plus-confidence standard Max wants.

### D30 — Fill timing and synthetic history require bounded calibration, not guesses

**Call.** Gold must use a genuinely obtainable manual-execution model. Same-close
fills cannot certify a signal that consumes that close. Phase A compares the
close-observed/next-open workflow, precisely timestamped alternatives,
conservative high/low/average OHLC stress estimators, spreads/slippage, and later
Max's recorded fills. Daily high/low/average prices are diagnostics unless the
contract proves when they were knowable and executable.

The current synthetic TECL history is real code with reproducible provenance:
3x daily S&P technology-sector-index returns for 1993–1998, 3x daily XLK returns
for 1998–2008, expenses, daily compounding, a real-TECL seam, and a loader-time
189.7 bps/year financing/tracking haircut. The checked-in builder currently
reproduces the stored series. Prior audits nevertheless found material tracking
and volatility differences from real TECL. Synthetic history and named stress
events remain diagnostic/confidence inputs and never replace real passage. Any
weight or catastrophic veto requires independent overlap/model recalibration.

**Why.** Both fill assumptions and synthetic history can make a strategy look
better or worse without changing its logic. They must be defensible measurement
contracts, not after-the-fact preferences.

### D31 — Declarative Rust is normal; custom modules graduate automatically through containment

**Call.** D27 remains the normal path. The first primitive library must reproduce
every current production/Gold/benchmark strategy and cover small fixture-tested
typed operations for arithmetic/boolean logic, lag/rolling data, moving averages,
momentum, RSI/MACD, ATR/volatility/bands, crossover/threshold events, approved
external inputs, and explicit position state.

The agent may author arbitrary candidate specifications and isolated Rust modules
inside the generated-research “pool of chaos.” The isolated-module path stays
disabled until its signed containment, causal-access, determinism, resource, and
reference-parity acceptance suite passes. After that policy is approved, Max
does not approve each module: a conforming module automatically enters untrusted
intake and still must pass every unchanged backtest/validation gate. Adding or
changing a shared primitive is protected core and still requires Max.

Resource limits protect trusted work but do not prove a hypothesis bad. A
timeout/OOM/compile failure enters a quarantine/repair lane with a structured
reason. Use one original attempt plus two immediate repairs, then defer it. The
agent cannot raise its own limits.

**Why.** This preserves speed, expressiveness, and autonomous creativity without
confusing generated code with trusted methodology or discarding a potentially
valid idea because its first implementation was poor.

### D32 — The protected core is cryptographically sealed and fails closed

**Call.** Use separate protected-core and generated-research repositories/
workspaces, different OS identities and credentials, read-only deployed core,
protected remote branches, and a content-addressed core manifest signed by a
human-held key unavailable to the resident agent. Startup, testing, Gold
publication, and trusted-signal evaluation stop if signatures, permissions, or
protected hashes do not verify. A password alone, later rollback, or clean Git
history is insufficient.

Max changes core only in an explicit human-controlled maintenance/release
session with reviewed diff, full protected tests, new signed manifest, audit
record, and credential revocation on exit. Core includes data, Rust primitives/
SDK/compiler, execution/B&H, search accounting, validation/Gold, score/rank,
recertification, authority/fallback, sandbox, operations, migrations, and their
tests.

**Why.** The number-one agent rule must be impossible to bypass mechanically,
not merely remembered in a prompt.

### D33 — Family is organization; configurations remain the certification rows

**Call.** An owner-facing strategy is one exact configuration. Family means the
same trigger logic and parameter schema and exists for batching, collapsible
presentation, search accounting, and Chimera dependence—not as an authority
unit. Every Gold configuration receives its own row. Similarity never condemns
a legitimate nearby configuration, but correlated rows are not independent
discoveries or votes.

The autonomous scheduler reserves 10% exploration by default and adapts above
that floor. Max may explicitly run a bounded campaign with any allocation,
including all exploration or none. Retired families receive small periodic/new-
data samples, and no indicator or data stream is condemned because one use of it
failed. The failure ledger records where and why exact logic/regions failed so
the agent can tune or redesign intelligently.

**Why.** Max cares about finding viable configurations, not maintaining a rigid
taxonomy, while the system still needs dependence control and efficient memory.

### D34 — Pending Gold, recommendation stability, and normal owner authority

**Call.** A historical-suite survivor first becomes `Pending Gold`, a visible
deterministic evidence state rather than a human staging board. It normally
accumulates 20 verified trading bars and passes fresh certification before
automatic graduation to current Gold. It cannot be Active while pending. Max may
explicitly override the cooling delay; the exception is visible and audited.

Initial switch-review thresholds are: +10 absolute Validation Score points with
no material deployable-performance loss; or +10% relative lower-bound deployable
performance with no Validation decline; or +5 absolute Montauk Score points with
neither component materially worse. The advantage must persist for five verified
bars with hysteresis. These versioned values are calibration defaults, not
agent-tunable preferences. Normal recommendation changes never change Active;
only Max approves the exact switch.

**Why.** This gives new configurations a cooling/evidence period and prevents
trivial rank noise from demanding repeated active-strategy changes.

### D35 — Emergency fallback never silently authorizes an opposing trade

**Call.** Loss of Gold immediately revokes Active authority and any manual
override. If the top compatible Gold fallback has the same current risk state as
the last verified instruction, Montauk may transfer the Active pointer
automatically, preserve the instruction, label the emergency fallback, and alert
Max. If it disagrees, Montauk preserves the last instruction, leaves no strategy
Active, enters `human_decision_required`, and alerts Max. If no Gold remains, it
shows `no_certified_strategy`, recommends risk-off for human consideration, and
takes no brokerage action.

Max will acknowledge manual execution, but that acknowledgement belongs to a
dedicated authenticated app/operations surface rather than Slack. Without it,
Montauk says “last instruction,” not “current position.”

**Why.** Continuous Gold governance and Max's authority over a state-changing
trade are both preserved without pretending Montauk controls the brokerage.

### D36 — Current data and the latest contract are mandatory; recertification preempts discovery

**Call.** Missing or failed current data freezes trusted signals, Gold mutation,
and promotion. Partial work may be quarantined, but exploratory compute pauses
while recovery verifies the control store, catches up data, recertifies Active,
computes the current signal, then refreshes the top cohort before discovery.

Replay Active after every verified bar. Formally renew it after 20 new bars, a
signal/trade event, a warning, or before activation/fallback. Renew Recommended/
top cohort weekly or before eligibility; renew the rest after 63 new bars, with
spare compute allowed to accelerate. Rolling underperformance warns first and
revokes after two sufficiently separated formal renewals; correctness, data,
causality, replay, and artifact failures stale/revoke immediately.

A material contract/data/engine change immediately stales incompatible rows and
queues urgent recertification. The current board contains no legacy or
grandfathered Gold under older incompatible validation. A ranking-only change
may preserve compatible certificates under a named rank version.

**Why.** Max wants the time during which any Gold claim is uncertain or stale
minimized, with Active safety ahead of research throughput.

### D37 — Durable state has zero-silent-loss semantics and a GitHub recovery path

**Call.** Use a transactional control database, compressed partitioned experiment
ledger, content-addressed artifacts, and Git/GitHub-managed code/specs/manifests.
Every durable class is backed up off-machine to GitHub using ordinary Git,
partitioned snapshots, releases, or LFS as appropriate. Keep ordinary blobs
below 100 MiB, warn earlier, and split repositories by responsibility before
size hurts sync/restore. Do not commit a live mutable database as a normal file.

Authority, signal, approval, and Gold mutations replicate before acknowledgement.
Create a pre-batch recovery point and end-of-batch commit/snapshot; one hour is
the maximum background sync interval. In-flight compute may rerun, but completed
acknowledged state cannot disappear silently. Any loss/corruption or overdue
backup is critical.

Keep compact permanent identity/parameter/version/verdict/dedup records for every
evaluated configuration. Full Gold/historical-Gold and audit-sample artifacts are
permanent; near-Gold is retained at least one year. Bulky hopeless-region traces
may expire only after an archive preserves the exact tested space and enough
evidence to prevent wasteful retesting.

**Why.** “Everything backed up” is achieved without turning Git history into a
multi-billion-row database or ignoring GitHub's actual storage constraints.

### D38 — Slack is conversational but has a narrow authority allowlist

**Call.** Slack may query/explain status, request a named ideation/research
campaign, trigger recertification, and approve one exact pending Active switch.
It may not acknowledge alerts or brokerage execution, enter/exit maintenance,
modify core/methodology, or infer approval from free-form text. Every mutation
uses Max's allowlisted identity, exact immutable ID, confirmation, expiry,
idempotency, replay protection, and durable audit.

Critical integrity/authority failures attempt delivery within five minutes;
ordinary research, new non-leading Gold, and board movement go to the daily
digest. Multiple Slack channels are expected. Slack Free is sufficient for
multiple channels and one custom integration at the time of this decision, but
its limited history means the local outbox/audit record remains authoritative.

**Why.** This delivers the OpenClaw-like low-friction relationship without making
chat history the system of record or an ambiguous sentence a methodology change.

### D39 — TECL-only trading permits other assets and data as causal inputs

**Call.** The 3.0 action space remains TECL long/flat. Strategy inputs may include
VIX, price/volume data, options-derived measures, related assets, macro series,
and an idiosyncratic TECL component. Every field requires provenance,
point-in-time availability/publication lag, revision handling, missing-data
semantics, causal access, and data-quality tests. The agent may compose approved
inputs; adding a source/primitive to protected data infrastructure is a signed
core change.

**Why.** Useful market context can improve a TECL call without prematurely
building multi-asset selection, allocation, or brokerage behavior.

### D40 — The validator must prove it is neither permissive nor blindly over-strict

**Call.** Questionnaire 3 reopens methodological research before the autonomous
scale-up. Audit every validation implementation against its cited method and
calibrate both false-Gold and false-rejection behavior. Use null/randomized and
adversarial controls, seeded leakage/overfit defects, simple frozen structural
controls, simulation, and genuine per-row forward outcomes. Simple EMA/RSI rules
are useful controls, not certified ground truth. Define Validation Score as an
evidence-strength/robustness index until a frozen target and forward reliability
study support a probability.

**Why.** A pipeline that calls everything overfit is not bulletproof; it is an
invalid grader in the opposite direction. Confidence comes from defendable
methods with measured operating characteristics, not merely more gates.

### D41 — Provider operations are owner-configured; only Max controls completion

**Call.** Max personally configures model providers, credentials, subscription/
API choice, and cost controls. The core remains provider-neutral and secrets stay
outside candidate workers, but 3.0 does not autonomously select new providers or
invent spending policy.

Objective replay, parity, security, recovery, load, notification, and soak
evidence are required inputs to Max's judgment. They never declare completion or
start later-version work. Max alone declares 3.0 complete, and only a separate
explicit Max instruction begins any later major-version effort.

**Why.** Operational evidence should make the decision well informed without
turning a timer or checklist into project authority.

## Calibration / implementation work still required

- freeze the executable notification-to-fill and matched-B&H contract;
- calibrate the fixed real/recent/rolling horizons, provisional ~1.10 margin,
  uncertainty floor, and rolling demotion operating characteristics;
- independently recalibrate the synthetic construction and any weight/veto;
- choose and independently audit the hierarchical/board/lifetime multiplicity
  method;
- define and calibrate Validation Score against explicit controls and forward
  outcomes;
- implement and prove the signed-core seal, sandbox/module acceptance suite,
  zero-silent-loss storage/restore plan, and exact acceptance matrix; and
- profile the Rust evaluator and target hardware after correctness fixtures pass.

These are bounded studies and engineering deliverables under D28–D41. They are
not unresolved owner authority that a coding agent may fill in implicitly.
