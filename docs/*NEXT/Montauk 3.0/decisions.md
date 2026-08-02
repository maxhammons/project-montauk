# Montauk 3.0 — Decision Log

**Status: HISTORICAL RATIONALE / NON-AUTHORITATIVE FOR IMPLEMENTATION (updated
2026-07-25).**

Running ledger of **resolved** decisions for the Montauk 3.0 always-on strategy
factory. Pairs with [charter.md](charter.md): the charter holds the integrated
operating contract while this file preserves the calls and their history. Section
16 of the charter now holds bounded calibration studies, not owner-policy questions
that an implementation agent may answer by implication. When a decision changes a
core charter claim, the charter gets updated to match — never by drift.

Each entry: the **call**, the **why**, and the **implications** for the build.

> **DO NOT IMPLEMENT FROM THIS LEDGER.** It intentionally retains superseded
> Mac/`launchd`, no-agent, staging-board, Python/Go, synthetic-Gold, Slack-only,
> and other historical calls so the reasoning is auditable. The current
> requirement is whatever [charter.md](charter.md) and the active pillar plans
> say. If this ledger appears to disagree with them, the ledger is history and
> must be marked/refined—not treated as an alternate specification.

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
meta-strategy research design now preserved in `chimera-research-design.md`.

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
**advanced but provisional**. See the expanded G1–G19 register.

---

## 2026-07-17 — clarified operating contract

This session records the owner's answers to the first two vision questionnaires.
Where these calls conflict with June entries, the newer numbered decision
explicitly supersedes the older one. History is retained so the change is
auditable.

### D11 — A scheduled, model-agnostic frontier agent is part of steady state (REFINED by D61)

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

### D19 — Quiet, read-mostly operation with a conversational notification surface (REFINED by D38 and D61–D63)

**Call.** The normal app experience is “Montauk at a glance”: current state,
active strategy and Gold status, override/recommendation status, Montauk Score,
Validation Score (or calibrated Confidence only after calibration justifies
that term), deployable Performance, forward-evidence status/age, simple gate
lights, and plain-English
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

**Implications.** D36 resolves recovery priority: low-priority deterministic
research may continue only on the labeled last-good snapshot when it does not
delay verified catch-up, Active recertification/current signal, and top-cohort
refresh; it cannot affect current Gold before replay on repaired data.

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

### D29 — Real-data superiority is broad, recent, margin-bearing, and versioned (REFINED by D46–D47, D65–D66)

**Call.** Gold must beat matched TECL B&H over complete real history, a fixed
recent horizon initially centered on trailing five years, and a small
predeclared rolling/window robustness design. Max's intent is that a Gold
strategy should beat B&H however the real history is reasonably sliced, without
building a complicated or retrospectively hand-picked exam.

The economic floor is greater than 1.0. An initial margin around 1.10 is the
owner's provisional starting intuition; the exact margin and one-sided
lower-bound test require Phase 1 calibration. A future increase is a new
owner-approved contract version and full compatibility review, not an automatic
ratchet caused by finding many winners. Recent evidence affects eligibility,
rank, and persistent rolling demotion under separate frozen rules.

The matched comparator uses adjusted total-return TECL, identical eligible start
and capital, first obtainable purchase timing, explicit costs, and unrounded
decisions. Initial risk-off cash earns zero in the Gold comparison.

**Why.** A barely positive point estimate or one excellent distant period is not
the strong performance-plus-confidence standard Max wants.

### D30 — Fill timing and synthetic history require bounded calibration, not guesses (REFINED by D46 and D53–D56)

**Call.** Gold must use a genuinely obtainable manual-execution model. Same-close
fills cannot certify a signal that consumes that close. Phase 1 compares the
close-observed/next-open workflow, precisely timestamped alternatives,
conservative high/low/average OHLC stress estimators, and spreads/slippage. Daily
high/low/average prices are diagnostics unless the contract proves when they
were knowable and executable. The original D30 proposal to compare against Max's
recorded fills is superseded by D54; personal fill capture is outside 3.0.

D46 later fixes signal-after-verified-close/next-regular-session-open as the
certification workflow. The remaining study calibrates costs and diagnostics; it
no longer chooses among fill timings.

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

### D31 — Declarative Rust is normal; custom modules graduate automatically through containment (REFINED by D64)

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

### D32 — The protected core is cryptographically sealed and fails closed (SIMPLIFIED by D44)

**Historical call.** The original design prescribed separate protected-core and
generated-research repositories/workspaces, protected remote branches, and a
larger release ceremony. D44 retains the cryptographic, read-only, fail-closed
outcome while making those topology choices optional implementation controls.
A password alone, later rollback, or clean Git history is insufficient.

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

The default board view is collapsed by family: show its leading exact row and
sibling count, then expand/page on demand. This keeps every certified
configuration queryable without filling the normal screen with tiny parameter
variations.

**Why.** Max cares about finding viable configurations, not maintaining a rigid
taxonomy, while the system still needs dependence control and efficient memory.

### D34 — Pending Gold, recommendation stability, and normal owner authority (REFINED by D49, D73, and D74)

**Call.** A historical-suite survivor becomes Gold and joins the one leaderboard
automatically with activation status `Pending Gold`; D49 later defines
“automatically” as publication in the next daily frozen certification epoch
rather than one-row-at-a-time publication. This is a visible badge, not a human
staging board or a weaker/pre-Gold certification tier. It normally
accumulates 20 verified trading bars and passes fresh certification before
becoming eligible to be Recommended or Active. Max may explicitly override the
cooling delay; the exception is visible and audited.

Initial switch-review thresholds are: +10 absolute Validation Score points with
no material deployable-performance loss; or +10% relative lower-bound deployable
performance with no Validation decline; or +5 absolute Montauk Score points with
neither component materially worse. The advantage must persist for five verified
bars with hysteresis. These versioned values are calibration defaults, not
agent-tunable preferences. Normal recommendation changes never change Active;
only Max approves the exact switch.

**Why.** This gives new configurations a cooling/evidence period and prevents
trivial rank noise from demanding repeated active-strategy changes.

### D35 — Emergency fallback never silently authorizes an opposing trade (EXECUTION-ACKNOWLEDGEMENT PORTION SUPERSEDED by D54)

**Call.** Loss of Gold immediately revokes Active authority and any manual
override. If the top compatible Gold fallback has the same current risk state as
the last verified instruction, Montauk may transfer the Active pointer
automatically, preserve the instruction, label the emergency fallback, and alert
Max. If it disagrees, Montauk preserves the last instruction, leaves no strategy
Active, enters `human_decision_required`, and alerts Max. If no Gold remains, it
shows `no_certified_strategy`, recommends risk-off for human consideration, and
takes no brokerage action.

The original D35 manual-execution acknowledgement is superseded by D54. Montauk
does not collect execution acknowledgement in 3.0 and therefore says “last
instruction,” not “current position.”

**Why.** Continuous Gold governance and Max's authority over a state-changing
trade are both preserved without pretending Montauk controls the brokerage.

### D36 — Current data and the latest contract are mandatory; recertification preempts discovery (EXTENDED by D67 and D71)

**Call.** Missing or failed current data freezes trusted signals, Gold mutation,
and promotion. Low-priority deterministic discovery may continue only against
the content-addressed last-good snapshot, clearly labeled `stale_data_research`,
and only when it cannot delay recovery. Its survivors cannot affect current Gold
until replayed through the complete current pipeline after recovery verifies the
control store, catches up data, recertifies Active, computes the current signal,
and refreshes the top cohort.

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

### D37 — Durable state has zero-silent-loss semantics and a GitHub recovery path (CURRENT-SIGNAL PORTION SUPERSEDED by D68; SCOPED by D69)

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

### D38 — Slack is conversational but has a narrow authority allowlist (REFINED by D54, D61, D63, D73, and D74)

**Call.** Slack may query/explain status, request a named ideation/research
campaign, trigger recertification, and approve one exact pending Active switch.
The original D38 execution-acknowledgement command is superseded by D54. Slack
may not acknowledge alerts, enter/exit maintenance, modify core/methodology, or
infer approval from free-form text. Every mutation uses Max's allowlisted
identity, exact immutable ID, confirmation, expiry, idempotency, replay
protection, and durable audit.

Critical integrity/authority failures attempt delivery within five minutes;
ordinary research, new non-leading Gold, and board movement go to the daily
digest. Multiple Slack channels were expected. The former Slack-plan assumption
is historical; D63 makes provider/plan choice a commissioning bake-off. No
conversation provider is the durable audit log.

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

### D40 — The validator must prove it is neither permissive nor blindly over-strict (SIMPLIFIED by D43)

**Call.** Questionnaire 3 reopens methodological research before the autonomous
scale-up. Select the smallest complete method set, audit every final retained or
rewritten validation implementation against its cited method, and calibrate both
false-Gold and false-rejection behavior. Use null/randomized and adversarial
controls, seeded leakage/overfit defects, simple frozen structural controls,
simulation, and genuine per-row forward outcomes. Simple EMA/RSI rules are useful
controls, not certified ground truth. Define Validation Score as an evidence-
strength/robustness index until a frozen target and forward reliability study
support a probability.

**Why.** A pipeline that calls everything overfit is not bulletproof; it is an
invalid grader in the opposite direction. Confidence comes from defendable
methods with measured operating characteristics, not merely more gates.

### D41 — Provider operations are owner-configured; only Max controls completion (REFINED by D58)

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

## 2026-07-21 — independent alignment and simplification review

### D42 — One canonical conveyor; configurations are data, not scripts

**Call.** The complete owner-facing system is one line: model/Max creates a typed
family definition → protected Rust primitives validate and expand it → exact
configurations enter the research bucket as data → matched-B&H backtest resolves
economic passage → validation resolves the remaining four Gold planks → Gold
leaderboard → rank → Max normally chooses Active.
One family may yield millions of configurations without compiling millions of
programs. A novel unexpressible mechanism uses at most one isolated module for
the family.

The bucket is logical at scale: deterministic family/search shards may stream
bounded configuration batches just in time. Montauk persists the exact identity
and compact verdict of every configuration actually evaluated, not billions of
pre-created script files or empty job rows.

Sandboxing, storage, backup, monitoring, and Slack protect or operate that line;
they are not parallel pipelines. The charter alone owns product/Gold/authority
policy, pillar plans own implementation domains, and the decision log is history
rather than an alternative requirements source.

**Why.** This is the smallest expression of Max's questionnaire intent and the
test for needless complexity: every component must map to the conveyor or protect
it.

### D43 — Five Gold planks; methods must earn admission

**Call.** The Gold exam exposes exactly five hard planks: correctness, economic
passage, generalization, search honesty, and reproducibility/currentness. Every
technical test belongs beneath one plank and has one predeclared decision role.
The backtest stage resolves economic passage and the following validation stage
resolves the other four; this is one contract, not a duplicated performance test.
Phase 1 admits a method only after proving relevant assumptions, implementation
parity, incremental value, usable power, and acceptable false-Gold/false-reject
behavior. PBO, SPA/Reality Check, bootstrap, walk-forward, sensitivity analysis,
synthetic history, and any other named technique are candidates—not mandatory by
reputation. Hindsight labels or discovery targets stay diagnostic unless a truly
independent design earns another role.

No legacy Gold row is presumed to meet 3.0. Every row must pass the final contract
from scratch. Gold aims to earn operational trust in the process, never certainty
that the next call is correct.

**Why.** A kitchen-sink validator can double-count evidence, use underpowered
methods, create tunable weights, and manufacture either false confidence or false
rejection. A small proven exam is more defensible than a large impressive one.

### D44 — Protect the core with the smallest enforceable seal

**Call.** D32's required security outcome remains, but repository topology and
release ceremony are not product concepts. The minimum is one resident-agent OS
identity with no core-write credential, one read-only content-addressed core
release, generated research outside it, a manifest signed by Max's unavailable
human-held key, and fail-closed signature/hash/permission verification at startup
and every Gold/signal job. Additional repository or branch controls must justify
their operational value rather than becoming mandatory layers by default.

**Why.** This makes the number-one agent prohibition mechanically real without
turning a personal appliance into an enterprise security program that is harder
to operate than the threat requires.

## 2026-07-21 — Questionnaire 4 and the testing-pipeline guiding light

Questionnaire 4 accepts the proposed owner-facing outcomes in questions 1–6 and
10–15, tentatively asks to use both CPCV and walk-forward in question 7, and
leaves questions 8–9 blank. Max then clarified that much of the technical
language was unclear and supplied one higher-authority requirement: Gold should,
to the best knowledge available from scholarship, market expertise, AI-assisted
research, best practice, and Montauk's own reasoning and controls, establish that
a strategy is not overfit and performs better when followed than TECL B&H.
Accordingly, the calls below distinguish owner-visible policy from methods that
Phase 1 must justify scientifically.

### D45 — One testing-pipeline guiding light

**Call.** Gold exists to provide the strongest honest assurance Montauk can
produce that an exact frozen strategy has no detected material overfit or
correctness failure and that following it under obtainable execution should
outperform matched TECL B&H. Research and expert/model critique help find the
best available methods; opinions and consensus never substitute for reproducible
evidence. “Strongest honest assurance” does not guarantee the next trade or
future return.

**Why.** This is Max's plain-language goal and the controlling interpretation
when a questionnaire's statistical wording is ambiguous. The five planks are the
minimum evidence needed to earn this one promise, not five competing goals.

### D46 — Gold measures actual deployable outperformance (REFINED by D52–D54)

**Call.** The strategy observes the verified official daily bar, then uses the
next regular-session open plus calibrated slippage and fees for certification.
Same-close and alternative OHLC fills remain diagnostics/stresses. The primary
economic estimand is the exact terminal deployable TECL wealth/share multiple
versus a matched B&H investment; daily net log-wealth difference supports
inference, while CAGR, drawdown, Sharpe, and trade statistics are explanations.

Complete observed TECL history and trailing five years are hard real-data gates.
The provisional 1.10 value is a starting hypothesis for the unrounded point
estimate, while an uncertainty-aware lower bound must exceed no edge (1.0) or
return insufficient evidence. Phase 1 calibrates final costs, margin, and
uncertainty rule on controls, never around preservation of the current champion.

**Why.** “Better when followed” requires a price Max could actually obtain and
one stable economic target; optimistic fill timing or interchangeable metrics
would defeat the guiding light.

### D47 — Rolling periods and named moments are predeclared, not hand-picked

**Call.** A small fixed rolling-window suite uses a calibrated aggregate passage
rule plus a calibrated catastrophic-window veto rather than demanding victory in
every imaginable slice. The named-moment diagnostic suite includes Max's
examples—2001/dot-com, 2008, 2020, 2022, and tariff announcements—and grows only
through a methodology version. Each result is source-labelled: pre-TECL moments
are reconstructed/synthetic diagnostics; events within observed TECL history use
verified real data. No reconstructed episode can satisfy a real-data Gold gate.

**Why.** Important crises should be visible, but candidate-specific windows and
synthetic history masquerading as observations would create the very overfit
exam Montauk is meant to prevent.

### D48 — Chronological validation is required; CPCV must be real, not ceremonial

**Call.** Nested rolling-origin reconstruction is the required chronological
spine and frozen-configuration replay remains a separately labelled diagnostic.
Phase 1 compares expanding and fixed rolling training windows. It also evaluates
CPCV alongside rolling-origin and aims to retain both, but CPCV is hard only
where it has a defined selection target, adequate power, and measured
incremental defect detection. Otherwise the contract supplies a predeclared
valid equivalent or `not_applicable`; an invalid test cannot award confidence.

Purge and embargo derive from the exact information/label/holding-outcome
intervals and are zero when no overlap path exists. Candidate intake fails when
a required interval cannot be computed. There is no permanent untouched
historical lockbox: a revealed campaign holdout becomes spent/reused evidence
and enters lifetime search accounting. Only bars arriving after an exact row is
frozen are untouched for that row.

**Why.** Max's preference for both CPCV and walk-forward is honored wherever both
are scientifically meaningful. The purge/embargo and lockbox rules were not
direct owner answers; they are conservative methodological consequences of D45
and remain subject to independent Phase 1 implementation review.

### D49 — Gold is published in daily frozen cohorts (HARDENED by D71 and D72)

**Call.** Discovery and backtesting run continuously. Once per day, the pipeline
freezes the complete eligible survivor cohort and search-ledger snapshot, runs
the cohort-dependent shared multiplicity/search-honesty correction, assembles
the final five-plank verdict from existing immutable candidate and shared
artifacts, and automatically publishes all passing rows together. Candidate-
local checks are not rerun as a second exam, and no human admission is added.
Later epochs inherit all prior disclosures and lifetime search history; a day
boundary never resets the multiple-testing denominator.

One immutable family/campaign/epoch search-honesty certificate may be referenced
by many exact rows. Numeric parameter distance and hashed signal/position/trade
behavior are recorded separately so duplicate paths are neither independent
discoveries nor independent Chimera votes.

**Why.** A coherent candidate universe makes continual-search correction
auditable while preserving continuous research, one row per exact Gold
configuration, and automatic board admission.

### D50 — Evidence sufficiency replaces a universal trade-count cliff (REFINED by D76)

**Call.** Gold has no fixed minimum number of trades. It reports trades, state
transitions, exposure episodes, effective observations, regimes, uncertainty
width, and method power; any method without enough information returns
`insufficient`.

Phase 1 reports the whole-appliance tradeoff between the probability of any false
Gold during a simulated year of continuous search and recovery of planted
economically meaningful signals. One percent annual probability of any false
Gold is an aspirational reference, not a ratified cutoff. Max chooses the final
achievable operating point after reviewing its false-rejection cost.

**Why.** Low-frequency strategies can be valid with few trades, while many
clustered trades can still provide little independent evidence. The relevant
risk is a false certificate from the whole machine, not a conventional p-value
on one selected row.

### D51 — The leaderboard states performance and ranking uncertainty plainly

**Call.** Each compact row shows terminal deployable TECL wealth/share multiple
versus matched B&H as a simple relative expression, Validation Score (or
calibrated Confidence only after it earns that interpretation), Montauk Score,
and forward-evidence status. The board keeps one deterministic exact rank but
shows `leader not clearly separated` when calibrated uncertainty cannot
distinguish the leading group. This is a status, not another score.

**Why.** Max needs an intelligible performance-versus-B&H result and evidentiary
strength to choose Active, without false precision or another metric zoo.

## 2026-07-21 — Questionnaire 5 remaining scope and research mandate

Questionnaire 5 is preserved unchanged in `Questionnaires/`. Question 8 and
question 21 contain no answer, so they do not create new decisions: the already-
ratified Gold-first delivery order remains in force, and no additional product
outcome is inferred. Question 4 accepted the size-band approach without selecting
a band; Max's subsequent clarification in D59 fixes the backtesting band and
keeps actual order sizing outside 3.0.

### D52 — 3.0 assumes a tax-advantaged primary account; tax is out of scope

**Call.** Montauk 3.0 is designed for Max's tax-advantaged primary account. Gold
compares pre-tax terminal performance net of frozen trading costs. Tax rates,
holding periods, wash sales, lot selection, tax optimization, and multiple
account profiles are outside 3.0.

**Why.** Tax modeling does not affect the intended account and would introduce a
large unrelated rules system into the Gold contract.

### D53 — Max will submit an after-close order for the next market open (REFINED by D59)

**Call.** After Montauk verifies the official close and emits a position change,
Max will manually submit the order after close for execution at the next regular-
session market open. Gold models that opening execution plus calibrated costs;
same-close and other OHLC fills remain diagnostics.

Risk-off cash earns zero by default. SGOV is an interesting later alternative
but is not a 3.0 traded leg. Questionnaire 5 accepted a conservative order-size
band without selecting one; D59 subsequently fixes the backtesting band while
keeping actual order size and account size outside 3.0.

**Why.** This is a repeatable causal workflow and a conservative TECL-only
economic comparison without pretending Max disclosed a financial value he did
not provide.

### D54 — Personal fill tracking and mandatory outside-human review are out of scope (EXTENDED by D78)

**Call.** 3.0 does not require Max to record brokerage time, price, quantity, or
execution acknowledgement, and it does not reconcile modeled fills with his
account. Montauk therefore displays the trusted signal and last issued
instruction, never an asserted brokerage position. Remove the manual-execution
acknowledgement from Slack's 3.0 mutation allowlist.

An outside paid or credentialed human review is not a launch gate. Independent
reference implementation, clean reproduction, adversarial review by a separate
agent/process, primary-source audit, and control evidence remain mandatory.

**Why.** Max explicitly placed both recurring personal fill capture and external-
human review outside 3.0. The retained reproducibility requirements protect the
method without silently restoring either scope item.

### D55 — Every Gold step is proven; research must address a named Montauk gap

**Call.** Continual-search multiplicity is the highest-priority statistical
research. Phase 1 must exercise the complete author/search/select/backtest/
validation system in null, planted-signal, regime-change, low-trade,
event-memorizing, lookahead, impossible-fill, and duplicate-behavior control
worlds and report both false Gold and false rejection. Every safety- or
evidence-critical step receives a fixture and acceptance proof.

Broad literature collection stops unless a primary source addresses a named
Montauk failure mode and produces a testable consequence. A method enters Gold
only after Montauk-specific controls establish assumptions, power, and
incremental protection.

**Why.** The research bottleneck is now proving this exact always-on examiner,
not accumulating a longer list of respected statistical names.

### D56 — Synthetic TECL must walk forward through the real overlap (REFINED by D65)

**Call.** Extend the frozen XLK-based synthetic transformation through the actual
TECL era and compare the modeled path with observed TECL. Use rolling/forward
overlap evaluation: calibrate transformation assumptions only on earlier overlap
blocks and test later blocks without refitting. Report daily-return bias,
tracking error, volatility, terminal path, drawdowns, financing/expense error,
and named-event behavior.

The goal is the most accurate defensible estimate of how TECL might have behaved
before inception, with explicit uncertainty. Synthetic evidence remains
diagnostic and never becomes observed real-data passage merely because overlap
fit improves.

**Why.** Direct overlap is the best available empirical check on the synthetic
construction, while time-separated evaluation prevents tuning the entire real
era and then calling the fit validation.

### D57 — Phase 1 explains decisions simply and Max ratifies after evidence

**Call.** Every owner decision report begins in simple language and includes a
simple example. It states the problem, recommended choice, measured false-Gold/
false-reject consequences, and known limits; formulas, papers, and technical
detail move to an appendix.

The performance margin, whole-appliance false-Gold tolerance, minimal validation
package, activation/renewal schedule, ranking ambiguity, and switch thresholds
remain provisional until Phase 1 or commissioning presents evidence. Max
approves the recommended package. Later fine-tuning requires another versioned
control study and owner approval; it is not autonomous threshold drift.

**Why.** Max owns the trust standard and final decision without being asked to
select unfamiliar statistical machinery.

### D58 — Hardware, provider, budget, and throughput targets do not define 3.0 (COMPLEMENTED by D60)

**Call.** The product remains an always-on, provider-neutral appliance with a
correct and efficient Rust evaluation path. Exact hardware procurement, frontier
provider/subscription, spending budget, and a numerical strategies-per-hour
target are deployment concerns outside the 3.0 product contract. Profiling and
ordinary optimization may improve operation after correctness, but no hardware
comparison or throughput threshold gates Gold or completion.

**Why.** Max explicitly removed these purchasing and performance-target choices
from 3.0. This preserves the settled architecture without turning a benchmark or
machine purchase into product authority.

### D59 — Backtests use a fixed $10,000–$100,000 modeled order band

**Call.** Execution calibration and every Gold backtest model TECL position-change
orders in the fixed $10,000–$100,000 notional band. Slippage and opening-execution
assumptions must be defensible across that range and use the conservative result
where costs vary materially within it.

This is a research assumption, not an account-size disclosure or operational
order limit. Montauk 3.0 does not collect, infer, enforce, or reconcile Max's
actual account balance or order size. Its execution claim is limited to the
frozen modeled band.

**Why.** A fixed scale makes transaction-cost testing reproducible without adding
personal portfolio tracking to 3.0.

## 2026-07-21 — dedicated host, remote operation, and OpenClaw comparison

### D60 — Minimal native Debian is the appliance deployment baseline

**Call.** Montauk 3.0 is planned to run natively on current Debian Stable on the
dedicated tower, without a desktop unless hardware evidence requires one.
`systemd` supervises the controller, low-priority Rust research, bounded model
invocations, the selected channel adapter, health, and backup. Hot state requires SSD/NVMe; HDD is for
cold archive/backup. Research may use all spare compute, but verified data,
signal generation, Active recertification, recovery, and alerts preempt it.

This does not supersede D58: exact hardware purchase and numerical throughput are
still not Gold or completion gates. Worker count, batch size, RAM cap, and thermal
ceiling are measured on the actual tower.

**Why.** A minimal native Linux host provides predictable resources, durable
service supervision, headless operation, and clearer OS permission boundaries.
The benefit is primarily simplicity and stability; it does not replace Rust
profiling or make the OS itself part of strategy evidence.

### D61 — Montauk owns Slack and scheduling; remote repair is a separate path (REFINED by D63)

**Call.** One private custom Montauk Slack app initially uses Socket Mode to the
Debian host. Its typed bridge renders the deterministic outbox and accepts only
the charter's exact allowlisted commands from Max's stable user/channel IDs. The
controller—not Slack and not the model—queues, validates, audits, and commits
each mutation. Free-form chat remains explanatory/advisory and may create a
bounded, thread-linked agent task with read-only Montauk views and candidate-
workspace access; it does not create protected maintenance authority.

Durable model calls are bounded one-shot jobs triggered by `systemd`, not an
interactive provider loop. Tailscale plus SSH is the independent administration
and recovery path. Claude Remote Control or an equivalent provider feature may
be used for a deliberately launched local repair session, but it is not the
scheduler or authority layer. Direct Claude-in-Slack is not the Montauk bridge.

**Why.** This makes the daily relationship conversational and easy while
preserving recovery when Slack or the model is down and making the number-one
agent rule mechanically enforceable.

### D62 — Borrow OpenClaw's gateway patterns, not its authority or blast radius

**Call.** Montauk is **OpenClaw-like in interaction, not OpenClaw-dependent in
authority**. It borrows one gateway boundary, typed messages, stable thread/
session routing, per-session serialization and global backpressure, distinct
scheduled/health/event mechanisms, a durable task ledger, immediate run status,
idempotency, private remote access, scoped identities, and health/doctor/audit
patterns.

OpenClaw is not a required 3.0 dependency and may not own Montauk's queue truth,
methodology, backtest, validator, Gold, leaderboard, signal, Active state, or
audit. General computer control, broad shell/tool access, plugin/skill sprawl,
inferred conversational authority, multi-channel/multi-agent breadth, and
provider-hosted memory do not enter 3.0 merely because OpenClaw supports them.
If trialed later, OpenClaw is a replaceable outer adapter under the no-core-write
agent identity or stricter container.

OpenClaw's current ACP path is not accepted as containment: its documentation
states that external ACP agents execute on the host under the external CLI's
permissions rather than inside OpenClaw's sandbox. A candidate-only working
directory is therefore organization, not security; OS/container capabilities
must enforce the Montauk boundary.

**Why.** OpenClaw has good solutions to conversational routing and long-lived
agent operation, but Montauk needs a much smaller trusted computing base. The
useful UX does not justify importing a general-purpose agent's blast radius.

### D63 — One channel contract; Slack is the default and Buzz must earn replacement (REFINED by D81)

**Call.** Montauk owns one provider-neutral typed conversation-channel adapter
and runs only one primary provider in production. Slack Socket Mode is the
conservative commissioning default, not a permanent product dependency. Before
full channel implementation, a time-boxed Slack-versus-Buzz bake-off may select
Buzz if it is at least as reliable for Max's phone, daily digest, and critical
alerts; passes the identical identity, typed-confirmation, expiry, replay,
idempotency, restart, and no-core-authority tests; and earns its greater
self-hosting/operations burden through materially better thread and agent
continuity. Max makes the final UX choice from the evidence. The rejected
adapter is not left running as a second command path.

Buzz's signed identities/events, hash-chained relay receipts, searchable rooms,
JSON CLI, and ACP support are useful outer-channel properties. They do not make
Buzz an authority. Its relay/workflow/audit state cannot replace Montauk's
controller ledger, and its shell/file agent receives no protected credential or
write capability. A Buzz trial must account for its pre-1.0 status, unfinished
mobile/push/approval features, relay/PostgreSQL/Redis/object-store operations,
TLS/private-network setup, absent enforced rate limiting in the current
architecture, and operator-trust-level shell. Same-host resource impact is
measured under saturated Rust research.

**Why.** Buzz may fit the desired “talk to the resident agent in its own room”
experience better than Slack, but adopting both would create the exact parallel
authority and needless operational complexity 3.0 is trying to remove. A single
adapter seam lets evidence—not novelty—choose the outer UX while keeping the
deterministic controller unchanged.

### D64 — The rewrite preserves required truth, not every legacy strategy

**Call.** Montauk 3.0 is a rewrite whose active folder is the planning authority.
Legacy code, tests, scores, thresholds, folder structure, and Gold rows are
migration evidence, not blanket compatibility requirements. Rust parity before
cutover is required for the legacy Active strategy needed for safe shadowing,
the matched B&H/execution reference, the final validator's controls and
benchmarks, and any legacy strategy Max explicitly selects as a migration
candidate. The implementation does not have to reconstruct every historical
Gold strategy or old pipeline surface.

No old row is grandfathered. An explicitly migrated legacy candidate receives a
new immutable identity and must pass the complete current 3.0 contract before it
can join the current board. Old rows that are not migrated remain historical
evidence without consuming rewrite scope.

**Why.** Reproducing every old implementation would preserve accidental
architecture and slow the clean Rust conveyor without improving Gold. Safe
cutover requires continuity for the actual trusted signal and reference
controls—not a compatibility museum.

## 2026-07-25 — Questionnaires 6 and 7 Part A

Questionnaire 6 (operational edge cases) and Questionnaire 7 Part A (research
reconciliation) are preserved unchanged in `Questionnaires/`. Both were written
as source evidence pending an explicit reconciliation pass; this section is that
pass. Questionnaire 7 **Part B (items 13–20) contains no answers** and therefore
creates no decisions — those items are registered as open owner authority at the
end of this file and may not be filled in by an implementation agent.

Two answers required interpretation rather than direct transcription, and both
are called out explicitly below: Questionnaire 6 question 2 (Max read
“off-machine replication” as “off-machine testing”) and Questionnaire 6
question 1 (the answer states an alert severity, not the state-machine choice
the question asked about).

### D65 — TECL and TYH are distinguishable product eras

**Call.** The fund now trading as TECL launched 2008-12-17 as **TYH** tracking
the Russell 1000 Technology Index and changed ticker and benchmark to the
Technology Select Sector Index around 2012-06-29. Montauk treats 2008-12-17
through 2012-06-28 as **real observed fund evidence in a separate product era**,
not as an interchangeable part of one continuous TECL contract.

The TYH era keeps its own era-specific matched-B&H result, must avoid
catastrophic failure there, and may **not** be used to calibrate the XLK-based
synthetic reconstruction. Phase 1 determines from controls whether it becomes a
hard economic sub-gate or a required stress/generalization gate, after measuring
how much the benchmark change moves otherwise sound controls. The 2018 GICS
reconstitution is evaluated in the same study as a possible additional
product/composition seam. **D65 refines D29, D46, D47, and D56.**

**Why.** Silently treating the fund as one unchanged product is wrong; discarding
3.5 years of genuinely tradeable history throws away scarce real evidence.

**Implications.** “Complete observed TECL history” must be expressed as an
era-labelled series, and `data/manifest.json` must record both seams.

### D66 — One symmetric distribution and total-return convention

**Call.** Montauk uses one complete, primary-source TECL distribution ledger.
Entitlement is recognized on the ex-date and cash becomes available on the
pay-date. **Distributions are reinvested when they are paid out**, at the same
first obtainable price and cost convention, for both the invested strategy and
matched B&H — except when the strategy is risk-off on the reinvestment date, in
which case the cash joins the zero-return risk-off balance.

Tradable OHLC, causally split-adjusted feature prices, and total-return wealth
accounting are three separate data views so distributions can never be omitted
or double-counted. **D66 refines D29.**

**Why.** “Adjusted total return” needs one explicit symmetric convention before
Gold can honestly claim to beat matched B&H.

**Implications.** The current runtime ledger (`data/TECL_distributions.csv`) is
insufficient as-is: it begins 2021-12-09, credits cash by ex-date, and does not
reinvest. Phase 1 must rebuild it from primary sources and add tests that detect
missing distributions, early cash availability, and double-counting against a
total-return price series.

### D67 — A material TECL product change suspends trusted signals

**Call.** Splits and ordinary distributions follow the tested corporate-action
path. A **benchmark change, leverage-objective change, ticker/CUSIP
discontinuity, closure, prolonged halt, or other material prospectus event**
triggers an immediate critical alert to Max, suspends new trusted signals once
effective, stales every affected certificate, and requires an owner-approved
data/execution contract update plus full recertification. Montauk never
automatically substitutes another leveraged ETF or ticker.

Montauk must therefore monitor TECL product news on a recurring schedule and
escalate material events to Max immediately.

**Why.** Montauk is TECL-specific. Product drift changes the object being
traded, not merely one more daily observation.

**Implications.** This adds a monitoring input and an alert class; it does not
add a new authority state beyond the existing stale/recertify machinery.

### D68 — A GitHub-only outage does not suppress a valid signal

**Call.** When the host, control database, verified data, engine, and strategy
are all healthy but off-machine replication alone is unavailable, Montauk
durably journals the signal locally, enters a visible `degraded_backup` state,
alerts Max, and **delivers the valid signal on time**. It blocks Gold
publication, Active changes, methodology changes, and other non-essential
authority mutations until off-machine replication catches up, then reconciles
the queued events.

**D68 supersedes D37's inclusion of the current signal in the
replicate-before-acknowledgement rule.** Authority, approval, and Gold lifecycle
mutations still replicate before acknowledgement; the current trusted signal does
not.

**Why.** A backup-provider outage should be visible, but it must not silently
become a trading rule or suppress a time-sensitive instruction Max can still act
on.

**Note on Questionnaire 6 question 2.** That answer (“are we doing off machine
testing? I dont believe so”) reads the question as being about off-machine
*testing* rather than off-machine *replication*. Questionnaire 7 question 3 asks
the intended question and is the governing answer. A future reconciler must not
take Q6 #2 literally.

### D69 — The durability promise is scoped to what the hardware can support

**Call.** For 3.0, Montauk promises **zero loss of already-acknowledged Active,
approval, signal, and Gold mutations against ordinary process and disk failure**,
using a proven local journal plus a second local device. It **explicitly accepts
a bounded physical-disaster recovery point equal to the last verified GitHub
sync** until a second offsite backup exists. Re-runnable in-progress research may
restart from the beginning of the pipeline. **D69 refines D37.**

Questionnaire 6 question 3 keeps GitHub as the only *off-machine* path for now,
with additional wired deep-backup drives possible later. The second local device
required here is on-site redundancy, not a second off-machine domain, so the two
answers are compatible.

**Why.** The earlier “no data loss” intent cannot be met by a GitHub-only design
if the whole tower is destroyed between syncs. Naming the one residual exception
is more honest than an unachievable promise.

### D70 — Restore drills are permitted but owner-initiated

**Call.** Montauk may perform a periodic, isolated, **non-authoritative**
clean-machine restore onto a spare machine or temporary VM using only documented
backups. It may verify hashes, reconstruct the last trusted state, and run
acceptance fixtures. It may not run live discovery, publish Gold, emit trusted
signals, or become a second authority, and it is destroyed or resealed after the
drill.

**Max's approval is required before beginning or even planning a drill.** No
scheduler may start one autonomously.

**Why.** Recovery cannot be proven on the same computer that would be lost, but
production and strategy testing stay contained on one machine by owner decision.

### D71 — A search-accounting defect stales affected certificates

**Call.** Ordinary future searching never changes an already-issued Gold
certificate. However, a **material search-ledger, holdout-reveal, lineage, or
multiplicity defect** — omitted prior searches, mis-clustered near-twins, a
leaked holdout, or an invalid correction method — immediately stales every
affected certificate and triggers prioritized recertification under a corrected
signed contract, exactly like a material data or engine correctness defect.
**D71 refines D36 and D49.**

**Why.** An immutable certificate should preserve what was claimed and why. It
should not remain current Gold after evidence shows one mandatory plank was
computed incorrectly.

### D72 — No release resets lifetime search history

**Call.** A signed core or validator release **never** resets Montauk's
search-history penalty. Every release retains lifetime search and holdout
provenance. A new signed epoch may use a separately justified allocation only
when the statistical contract explains why the old and new questions differ; it
never erases or hides earlier search. A renamed optimizer, campaign, or feature
source is not sufficient justification.

**Why.** Versioning should identify changed methodology, not manufacture a fresh
untested history. This closes the easiest available loophole in the Search
Honesty plank.

**Implications.** Confirms and hardens D49 against a reset path that the round-1
research package had left open.

### D73 — Defer and dismiss are a fourth channel action

**Call.** Max may durably **defer or dismiss one exact Recommended-versus-Active
proposal** without changing Active. The reason is optional, the action is
audited, and it never changes Gold, rank, Recommended, Active, or the trusted
signal.

A **deferral** resurfaces at its chosen expiry or on a material Gold/integrity
event. A **dismissal** stays quiet until the proposal clears a versioned
material-improvement threshold beyond the evidence already dismissed, the current
Active strategy weakens materially, or Max asks for it. Phase 1 calibrates that
improvement threshold from recommendation-churn tests; the research package's
“50% of threshold or 20 bars” is not adopted. **D73 refines D38.**

**Why.** Quiet-by-default requires a way to say “not now” that does not read as a
methodology decision or a training signal.

### D74 — An Active switch is approved from one complete review card

**Call.** Before confirmation, Montauk presents **one review card** showing exact
old and new strategy IDs, both current signals, whether approval changes the
target state immediately, the resulting next-open instruction,
performance/confidence differences, drawdown and catastrophe evidence,
data/certification timestamps, and the expiry. After that information is already
visible, **one explicit button confirms the switch**. There is no default
acceptance, no timeout acceptance, and no hidden second trade.

An opposite-state switch must make its trade impact conspicuous rather than
reusing the generic pointer-change acknowledgement. Max may also request a view
of candidates that improve on the currently selected Active strategy, not only on
Montauk Recommended. **D74 refines D34 and D38.**

**Why.** Max executes manually, so the practical consequence of an authority
change must be impossible to miss — while still being one button once the
evidence has been read.

### D75 — Active losing Gold is the highest alert class; the integrity state remains OPEN

**Call.** Loss of Gold by the **Active** strategy is Montauk's highest-severity
alert class and escalates immediately and unmistakably.

Questionnaire 6 question 1 asked whether a *correctness/causality/data/artifact
defect* should enter a **separate** `integrity_emergency` state distinct from
ordinary performance deterioration. The answer supplied an alert-severity
statement rather than a state-machine choice, so **no decision is recorded here
and D35's existing same-state/opposing-state machine stands unchanged.** The
question is registered as open owner authority below.

**Why.** The distinction between “the edge may have weakened” and “the signal may
be wrong” is real and load-bearing, but it must not be resolved by inference.

### D76 — The false-Gold promise is stated over the appliance's real horizon

**Call.** Phase 1 must present the false-Gold operating point over **annual,
five-year, ten-year, and lifetime** interpretations under explicitly stated
dependence assumptions, alongside the planted-signal recovery cost at each. It
must state whether the chosen online policy spends a finite lifetime error
budget, controls a rolling annual risk, or offers another guarantee. Max approves
the understandable long-run promise, not only the one-year number. The 1% annual
figure remains an aspirational plotting reference. **D76 refines D50.**

**Why.** Montauk runs continuously. A stable 1% annual risk is not a 1% lifetime
risk, and the safety claim should use the product's own time horizon.

### D77 — A catastrophic-loss floor is studied, not installed

**Call.** Phase 1 tests whether a **narrow catastrophic-loss/ruin veto** adds
distinct protection on real and validated stress controls without rejecting sound
trend strategies. No preferred maximum drawdown is installed now. Ordinary
drawdown remains a disclosed ranking and decision input. If no defensible
catastrophic boundary emerges, no veto is installed and the limitation stays
prominent in every activation review.

The adoption rule itself (Questionnaire 7 item 20) is unanswered, so installing
any veto remains a separate owner decision.

**Why.** A Gold strategy may have high drawdown by earlier decision, but “high
drawdown” and “structural near-ruin” may not be the same thing. The check must
not become a disguised preference for smooth backtests.

### D78 — Broker verification, dead-man alerting, and paid execution data are out of 3.0

**Call.** Naming the broker and verifying opening-auction participation
(Questionnaire 7 item 1), an independent outbound dead-man/heartbeat service
(Questionnaire 7 item 5), and any paid official-close/auction/quote dataset
(Questionnaire 7 item 16, unanswered) are **outside Montauk 3.0**.
Questionnaire 6 question 4's read-only update channels and command DM are
delivered inside the one selected channel; they are not an independent dead-man
path. **D78 refines D54 and D58.**

**Disclosed consequence.** Gold's execution claim is therefore limited to the
**modeled** signal-after-verified-close/next-regular-session-open contract across
the fixed $10,000–$100,000 band using a documented conservative cost range. The
research package identified broker auction participation as the top live-trading
blocker; with it out of scope, no Gold row may be described as
broker-verified-tradeable, and precise execution cost is reported as
`insufficient` rather than as a point estimate.

**Why.** Max explicitly scoped all three out. Recording the consequence keeps the
scope reduction honest instead of silently weakening the execution claim.

## Calibration / implementation work still required

- calibrate slippage/fees from market evidence within the fixed next-open,
  $10,000–$100,000 modeled-order, and matched-B&H contract;
- calibrate the rolling aggregate/catastrophic rule, provisional 1.10
  point-estimate margin, lower bound above 1.0, and rolling demotion behavior;
- choose expanding versus fixed rolling windows for required nested
  rolling-origin reconstruction; prove when CPCV is applicable, adequately
  powered, and incremental; and freeze interval-derived purge/embargo rules;
- freeze the source-labelled named-moment suite and calibrated diagnostic/veto
  semantics;
- independently recalibrate the synthetic construction using time-separated
  XLK-model-versus-real-TECL overlap blocks and decide any diagnostic weight/veto;
- choose and independently audit the hierarchical/board/lifetime multiplicity
  method and daily certification-epoch artifact;
- map the annual any-false-Gold versus planted-signal-recovery frontier around
  the aspirational 1% reference;
- define and calibrate Validation Score against explicit controls and forward
  outcomes;
- calibrate the `leader not clearly separated` rule;
- implement and prove the signed-core seal, sandbox/module acceptance suite,
  zero-silent-loss storage/restore plan, and exact acceptance matrix;
- commission the minimal Debian/`systemd` service topology, SSD hot-storage and
  resource-preemption policy, Tailscale/SSH recovery path, bounded provider
  adapter, and one selected private typed channel under the dedicated operations
  [plan](debian-host-agent-and-channel-operations.md) — the channel provider is
  settled (Slack, D81), so this is adapter implementation rather than provider
  comparison;
- rebuild the primary-source TECL distribution ledger, implement the symmetric
  ex-date/pay-date reinvestment convention, and add omission/double-count tests
  (D66);
- determine from controls whether the TYH product era is a hard economic
  sub-gate or a required stress gate, and record both product seams in
  `data/manifest.json` (D65);
- calibrate the dismissal retrigger threshold from recommendation-churn tests
  (D73); and
- produce the annual/5-year/10-year/lifetime false-Gold frontier with
  planted-signal recovery at each horizon (D76).

These are bounded studies and engineering deliverables under D28–D78. They are
not unresolved owner authority that a coding agent may fill in implicitly.

## Open owner authority — must not be inferred

These remain unanswered. No implementation agent, and no Phase 1 report, may
resolve them by implication, by choosing a convenient default, or by treating a
suggested answer in a questionnaire as ratified.

| Source | Question | Blocks |
|---|---|---|
| Q6 #1 | Does an integrity/correctness defect enter a separate `integrity_emergency` state, or reuse the ordinary loss-of-Gold machine? (D75) | Authority state tables |
| Q7 #13 | Which long-run false-Gold promise should Phase 1 optimize for, once annual/5y/10y/lifetime behavior is visible? | Search-honesty plank |
| Q7 #14 | Does every hard real-data horizon require its own uncertainty-aware lower bound, and does `insufficient` on one horizon block Gold? | Economic passage plank |
| Q7 #15 | Final confidence level and evidence-sufficiency floors (90% vs 95%, regime/block/MinTRL floors) | Economic passage plank |
| Q7 #16 | May Phase 1 buy official-close/auction/quote data if free sources cannot support the execution claim? (currently out of scope per D78) | Execution study |
| Q7 #17 | On what basis may a third Montauk Score pillar be admitted? | Ranking study |
| Q7 #18 | How is the `leader not clearly separated` confidence level selected? | Ranking study |
| Q7 #19 | When may the custom Rust escape hatch be enabled, and by what owner ceremony? | Containment study |
| Q7 #20 | When may a catastrophic real-data risk veto be installed? (D77) | Gold contract |

A completeness audit on 2026-07-25 found four further blanks that earlier rounds
never carried forward, and four decisions the plan requires that no questionnaire
had ever asked. All are now in Questionnaire 8 Part C:

| Source | Question | Blocks |
|---|---|---|
| Q3 #24 | Explicit confirmation of the declarative-Rust representation path. The plan treats it as DECIDED and non-reopenable on the strength of the adjacent items 25/26 answers, which presuppose it. | Core architecture |
| Q4 #9 | May Montauk keep one permanent untouched historical lockbox? Charter §4.2 currently states "no" as a conservative consequence of D45, not as an owner answer. | Generalization plank |
| Q5 #8 | Confirm the Gold-exam-first build order over factory-first. | Phase sequencing |
| Q5 #21 | Open-ended check for a missing product-level outcome. | Product scope |
| **new** | Which legacy strategies migrate into 3.0? The plan requires "any legacy strategy Max explicitly selects" in five places and the list has never been requested. | Phase 2 parity scope |
| **new** | Must cutover be blocked until at least one activation-eligible 3.0 Gold row exists? Nothing currently prevents retiring the legacy signal into an empty 3.0 board. | Cutover safety |
| **new** | Is there a review trigger if the Gold board stays empty for a long period? Needed to distinguish a correctly high bar from a mis-implemented over-strict gate. | Validator governance |
| **new** | What time must the daily signal be delivered, and what time constitutes a missed-deadline alert? Charter §12 alerts on "a missed required-signal deadline" that is never defined. | Operations + alerting |
| **new** | Which additional data streams does Phase 1 actually acquire and wire up? D39 permits VIX/volume/options/macro/idiosyncratic inputs but schedules none, converting Max's Questionnaire 3 closing request into a permission rather than a deliverable. | Data contract |

Questionnaire 4 item 8 (purge/embargo derivation) is also blank and is
deliberately **not** returned to Max: it has one defensible answer, the charter
already implements it, and no owner preference would improve it.

## 2026-07-26 — agent runtime billing and the gateway build/rent line

### D79 — Subscription-first for the resident agent; API billing is a documented fallback

**Call.** The resident agent runs on Max's Claude subscription
(`claude setup-token`) rather than metered API billing. API billing is permitted
where a needed capability requires it, under the migration triggers recorded in
[channel-gateway-and-agent-runtime.md](channel-gateway-and-agent-runtime.md) §7.
This is a cost and operations preference, not a Gold or completion criterion, and
it is reversible without reopening the strategy or validation contract.

The consequence is architectural, not merely financial: Managed Agents is
API-key-only, so the resident runtime is the **Claude Agent SDK** (preferred over
a bare `claude -p` subprocess because it supplies sessions, permission gating,
and lifecycle hooks as library features). Server-side session context,
cron-driven deployments, webhook notifications, and a first-class interrupt event
all return to Montauk's own plate. Two of those four — scheduling and
notifications — were already Montauk's job under D61 and §5.2, so the genuinely
new work is thread context and cooperative steering.

This does not relax D61 or §5.1. The surviving rule is the one that matters: no
permanently privileged interactive session is kept alive to imitate a daemon.
An SDK-hosted invocation is still bounded, supervised, non-interactive, and run
under the `montauk-agent` identity with a timeout, a turn limit, and a
candidate-only working directory.

**Why.** Routine operation should not meter. The three-path design in D80 keeps
digests and mutations model-free, so the subscription allowance is consumed only
by genuine conversation and research restocking — which is exactly the workload a
subscription suits. Recording the fallback triggers now means a later cost or
reliability finding is a planned migration rather than a redesign.

### D80 — Build the channel gateway; rent only the agent runtime. The authority path is model-free

**Call.** Montauk builds the Slack adapter, the typed command schema, the review
card, the confirmation components, the outbox renderer, and the controller. It
does not build the agent loop, session/context management, model retry, or
streaming. The channel carries three paths with different trust levels, and the
two that carry authority never invoke a model:

1. **digests and alerts** render directly from the durable notification outbox;
2. **mutations** are initiated by a slash command or a Slack interactive
   component carrying the immutable proposal ID — never by prose a model
   interprets;
3. **free-form chat** routes to a bounded agent task that may explain, inspect,
   propose, and *surface* a review card, but cannot approve one.

This settles the previously undefined ingress rule: **slash command or button =
typed mutation; anything else = advisory.**

**Why.** The charter forbids any gateway from owning command semantics, task
state, or audit truth, so items 1–5 of the build list could never have been
delegated — adopting OpenClaw would have removed none of them (D62, §8.2). What a
general gateway actually saves is the runtime, which the Agent SDK supplies
anyway. Meanwhile the button-based mutation path converts §7.4's rule that
free-form conversation can never approve an Active switch from an instruction the
model is asked to honor into a property of the transport: a signed interactive
payload cannot be produced by anything that merely writes text into the channel,
and therefore cannot be prompt-injected. General gateways are built on the
assumption that the model is the interface; Montauk's charter assumes the
opposite, which is why the narrower purpose-built adapter is the better fit here
despite being more code.

## 2026-07-30 — channel provider selected

### D81 — Slack is the selected primary channel; the Buzz bake-off is closed by decision, not by measurement

**Call.** Slack is the one primary conversational channel for Montauk 3.0,
deployed as a workspace-scoped custom Slack app on Socket Mode exactly as
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md)
§7.2 specifies. The Slack-versus-Buzz bake-off that D63 and §7.3 *authorized* is
**closed without being run**. Buzz is not implemented, is not retained as a
parallel command path, and is removed from the commissioning sequence as a
budgeted task.

This is a decision taken on cost and maturity evidence already on record, **not**
a measurement result. Nothing in this entry should be read as reporting a
bake-off outcome — no comparative measurements were taken. §7.3's eight criteria
are retired unrun.

The deployed shape:

- a free Slack workspace, with no paid plan at any point;
- one workspace-scoped **custom** app — created by Max, installed only into his
  own workspace, never submitted to the public App Directory — built from a
  versioned minimal app manifest retained with protected operations code (§7.2
  step 1);
- **Socket Mode**: `montauk-channel.service` opens an outbound WebSocket to
  Slack and events return on that connection. No public request URL, no TLS
  termination, no port forwarding, no dynamic DNS, and no inbound listener on the
  appliance;
- an app-level `xapp-…` token scoped to `connections:write`, and a bot `xoxb-…`
  token scoped to `chat:write`, `commands`, and `app_mentions:read`;
- an official Bolt SDK for reconnection and envelope acknowledgement rather than
  hand-written socket handling (§7.2).

**Why — the recurring cost is zero and stays zero.** Free workspace; free app
install against a free-plan ceiling of ten apps and a requirement of one; Socket
Mode is a standard platform feature rather than a paid tier; the Bolt SDK is open
source; phone push is built into the stock Slack client; and the adapter is a
`systemd` service on an appliance Montauk already owns. The free plan's 90-day
history window is not a constraint here, because §7.2 already establishes that
Slack history is never Montauk's durable memory — the control database is. Under
D79 and D80 the subscription allowance is likewise untouched by routine
operation: Paths 1 and 2 are model-free, so digests and every mutation cost
nothing, and only free-form chat consumes the subscription Max already pays for.

**Why — Buzz's true cost is capacity, not dollars.** A tempting shorthand is that
Buzz was rejected because it has no free hosting. That is not accurate and should
not enter the record: Buzz is Apache-2.0 and could be self-hosted on the
appliance for zero dollars. What it actually costs is the appliance. §7.3 records
that its full self-hosted architecture wants a relay **plus PostgreSQL, Redis,
and S3/MinIO-style object storage** — four resident services on a two-core
i3-6100 with 120 GB of storage. That collides with §2.3, which grants research
only *spare* CPU precisely because capacity must stay reserved for the
controller and the channel adapter, and with §2.2, which requires storage
pressure to pause research before it threatens the control database, Gold
artifacts, or backup. Bake-off criterion 5 — overhead while Rust research is
saturated — is answerable from the specification sheet without instrumentation.

**Why — maturity outranks cost, and would survive a free managed Buzz.** Cost is
the weakest of the three arguments, and a hypothetical free managed Buzz would
erase it. These objections, all already recorded in §7.3 from the 2026-07-21
snapshot, would survive it: Buzz is pre-1.0 and fully supports only `main`;
mobile clients, push notifications, and workflow approval gates are described as
still being wired up; rate limiting is not enforced; and channel membership is
the primary access gate, which §7.3 judged "not fine-grained enough to replace
Montauk's typed mutation allowlist." Buzz is weakest exactly where Montauk is
most dependent — §7.2 selects on mature phone clients and push delivery, because
the daily digest and critical alerts are the channel's primary job. A managed
offering would also remove owner-controlled conversation data, which is Buzz's
principal stated advantage.

**Why — Socket Mode is load-bearing, not an implementation detail.** The default
Slack ingress is an Events API **Request URL**: Slack delivers events by making
an inbound HTTPS POST, which for a home appliance behind NAT means a domain, a
certificate, an open port, router forwarding, and a public path to the machine
holding the signed core, the Gold database, and the Active switch. Socket Mode
inverts the direction, so nothing on the internet can initiate a connection to
the host. This is the identical property credited to D79's migration target in
[channel-gateway-and-agent-runtime.md](channel-gateway-and-agent-runtime.md) §7
— an outbound-polling worker with no inbound port, no forwarding, behind NAT.
It is also what makes D80's model-free mutation path reachable without exposing
the host: a Block Kit button click would otherwise POST to a public
Interactivity Request URL, and under Socket Mode that signed payload arrives on
the socket the appliance already opened.

**Not to be confused with Claude-in-Slack.** The app in this decision is
Montauk's own custom app driving Montauk's own adapter. It is unrelated to
Anthropic's Claude-in-Slack / Claude Tag product, which the charter separately
excludes because it does not authorize the local appliance. Claude Tag's paid
Slack plan requirement therefore never applies to Montauk, and the zero-cost
claim above is unaffected by it.

**Conditions that reopen the choice.** All four must hold together; any one alone
is insufficient:

1. Buzz reaches a stable release with `main` no longer the only fully supported
   configuration;
2. mobile clients, push notifications, and workflow approval gates are shipped
   rather than in progress, and measurably match Slack for Max's phone/digest
   workflow;
3. per-action authorization exists that can carry the typed mutation allowlist,
   rather than channel membership as the access gate; and
4. the resident footprint fits the appliance without displacing reserved
   controller/adapter capacity or threatening the §2.2 storage floor — or the
   appliance is replaced by a host where that is no longer binding.

Should all four hold, the reopened comparison runs §7.3's criteria as written.
Because D80's three-path architecture is transport-independent — Paths 1 and 2
are model-free, and only the interactive-component mechanism is Slack-specific —
a later migration does not invalidate the adapter contract, the command schema,
the review card, or the outbox renderer.

**Implications.**

- §7.2's Slack setup steps become the commissioning procedure rather than one
  branch of a comparison.
- §9 step 10 no longer budgets a bake-off; it records this decision and deploys
  the Slack adapter.
- Open item 4 of the gateway document is closed.
- Email is separately evaluated and rejected as a conversational channel in a new
  §7.6; it is not an alternative that survives this decision.
- No paid Slack plan may be introduced as a dependency without a new decision.
  If a future requirement can only be met on a paid tier, that is a cost decision
  Max takes explicitly, not an implementation choice.

**D81 refines D63.** D63 made the bake-off *permission*, not obligation — "a
time-boxed Slack-versus-Buzz bake-off **may** select Buzz" — and assigned the
final UX call to Max. Declining to exercise that permission and taking the
recorded default is consistent with D63 and with the charter's matching
permissive language, so neither is amended by this entry.
