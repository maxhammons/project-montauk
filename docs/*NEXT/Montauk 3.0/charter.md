# Project Montauk 3.0 Charter — The Always-On TECL Research Appliance

**Status: DRAFT OPERATING CONTRACT (updated 2026-07-17).** This document
captures the owner's clarified intent and is the governing 3.0 planning draft.
It extends, but does not silently override, the repository's existing validation
and execution contracts. Settled changes must be reconciled into canonical
implementation docs and tests before they become production truth.

Terms marked **DECIDED** are owner decisions. Terms marked **OWNER INTENT,
SPECIFICATION PENDING** have a clear desired outcome but still need a precise,
testable rule. Terms marked **OPEN** must not be chosen implicitly by a coding
agent.

**DECIDED — questionnaire promotion rule.** After Max completes a questionnaire
round, the reviewing agent must process the entire answer set into this charter,
the decision log, README, and every affected pillar plan before drafting another
round or a coding handoff. The answered questionnaire remains unchanged as source
evidence; the reconciled active docs become project truth. Conflicts are resolved
explicitly and prior decisions are marked superseded rather than erased.

---

## 0. Purpose

Montauk exists to answer one practical question for TECL:

> **Should the current trusted state be risk-on or risk-off, and why is this the
> most defensible call Montauk can make today?**

Montauk 3.0 replaces a manually driven research loop with a personal, always-on
appliance. It continuously challenges the current strategy, turns human- or
agent-authored ideas into reproducible experiments, rejects candidates that do
not survive the contract, maintains a Gold-only leaderboard, and surfaces only
the decisions or failures that deserve Max's attention.

Its success is not “a large number of features” or “a large number of tests.”
Success is a trustworthy end-to-end research and signal system whose methods are
clear enough that Max can understand why a signal has earned authority.

## 1. Product definition and completion target

**DECIDED.** Montauk 3.0 is:

> A personal, always-on TECL research appliance where a model-agnostic frontier
> agent continuously invents executable strategy candidates, a protected
> deterministic pipeline backtests and validates them, every qualifying Gold
> configuration automatically joins the leaderboard, and Montauk
> recommends—but does not normally activate—a new leader without Max's
> approval.

A complete 3.0 must be able to run unattended through the whole loop:

1. acquire and verify current data;
2. protect the last trusted signal when current data or operations fail;
3. recertify the active strategy with priority;
4. generate or accept executable strategy ideas;
5. perform pre-execution safety and correctness checks;
6. cheaply screen exact parameter configurations;
7. fully backtest survivors under frozen execution semantics;
8. run the complete versioned validation suite;
9. publish every Gold configuration to the current leaderboard;
10. update the Montauk recommendation without silently changing the active
    strategy;
11. generate the current trusted TECL state;
12. retain enough evidence to reproduce every important verdict; and
13. send concise digests, change notifications, and actionable failures.

No daily supervision is part of the target. A normal week may require no action.
The intended steady state is quiet: the machine works, Max receives a useful
daily digest, and stronger attention is requested only for a meaningful change
or fault.

## 2. Scope and priorities

### 2.1 In scope

- TECL, with the existing long/flat or risk-on/risk-off action space.
- A single user: Max.
- An always-on Mac mini or comparable dedicated host.
- A model-agnostic remote frontier agent invoked on a schedule. “No local AI”
  means no locally hosted foundation model; it does not prohibit Claude, Codex,
  or another remote agent from operating through a subscription or API.
- Automated strategy authoring, experiment scheduling, result analysis, bounded
  candidate repair, backtesting, validation, Gold publication, recertification,
  ranking, signal generation, and reporting.
- Manual owner approval for normal active-strategy changes.
- Manual brokerage execution for all of 3.x.
- A mostly read-only Montauk application plus a conversational notification and
  command surface, likely Slack.

### 2.2 Explicitly out of scope

- Multi-asset selection, allocation, sizing, or rotation. Those belong to 4.x.
- Autonomous brokerage execution.
- A general multi-user or commercial product.
- iOS as a 3.0 completion requirement. The companion is a 4.x/5.x convenience.
- Automatic progression to 4.x. Only Max decides when 3.0 is sufficiently proven
  to begin 4.x; no calendar interval makes that decision.

### 2.3 Priority order

**DECIDED.** When priorities conflict:

1. correctness and data integrity;
2. honest validation and protection against false Gold;
3. dependable trusted-signal operation and recovery;
4. auditability and clarity;
5. throughput and the number of configurations tested;
6. convenience and presentation.

A false Gold admission is considered slightly worse than rejecting a strategy
that might have been good.

## 3. Authority and sources of truth

Montauk must have one explicit authority path. Parallel scripts, duplicate
boards, undocumented score variants, silent fallbacks, and contradictory
artifacts are defects.

| Concern | Authority |
|---|---|
| Data fit for trusted use | Versioned deterministic data-verification contract |
| Candidate definition | Frozen source/definition plus exact parameters |
| Backtest result | Versioned deterministic engine and execution contract |
| Gold eligibility | Versioned deterministic validation contract |
| Rank and recommendation | Versioned deterministic Montauk Score/ranking contract |
| Active strategy | Explicit owner selection, except a separately specified emergency rule |
| Current trusted signal | Active Gold strategy evaluated on last verified data |
| Autonomous research priorities | Agent/scheduler policy, never certification authority |
| Core methodology changes | Explicit owner-directed change |

The AI agent may influence **what is proposed and what enters the queue**. It may
not influence a deterministic verdict after observing the answer, reinterpret a
failed gate, soften a threshold, or choose which evidence “counts.”

## 4. The Gold contract

### 4.1 Meaning

**DECIDED IN PRINCIPLE; exact gates pending.**

> **Gold means a frozen strategy configuration beats TECL buy-and-hold across
> every required real-data evaluation period, passes Montauk's complete
> versioned correctness and anti-overfitting contract, and is certified fit to
> trade to the strongest extent Montauk can establish from available evidence.**

“No detected overfitting” is the strongest honest claim. Gold is not a promise
that every trade will be correct or that future returns are certain. Markets can
change, evidence can accumulate, and a previously Gold strategy can lose Gold.

Gold is binary eligibility, not rank. A Gold strategy may have disclosed
weaknesses, high drawdown, few trades, or regime dependence and still qualify if
it satisfies every hard gate. Those weaknesses affect confidence, score, rank,
and the owner's decision; they are not silently hidden.

### 4.2 Evidence roles

- **Real market data determines economic eligibility.** Gold must beat the
  frozen B&H comparator in every required real-data period.
- **Modern/recent evidence matters more to present usefulness.** The owner wants
  recent behavior—roughly the latest five years as an initial intuition—to have
  greater influence than distant history. The exact hard gate and/or score
  weighting is OPEN.
- **Synthetic history is diagnostic.** It may increase or reduce confidence and
  catastrophic synthetic failure must be surfaced. Whether a defined synthetic
  failure blocks Gold is OPEN. Synthetic data never substitutes for passing real
  data.
- **Untouched forward evidence is distinct.** Bars occurring after a strategy was
  frozen and certified could not have been used to design that frozen version.
  Montauk must track this evidence separately from historical validation.
- **One bad call is not revocation.** Gold is judged by the contract over
  meaningful evidence, not by demanding perfect trades.

### 4.3 Universal rigor and search breadth

**DECIDED.** Human-authored and AI-authored candidates face the same mandatory
evidence planks and rigor. A predeclared test may have a valid equivalent or
`not_applicable` result when it is structurally inapplicable, but origin does
not earn skipped evidence, a lighter route, or silent score renormalization.

This does **not** make search history irrelevant. A simple rule discovered after
millions of adaptive attempts has a different false-discovery context from the
same rule genuinely frozen before any observation. Montauk must record the
complete observable search process and apply a defensible multiplicity or
selection-bias correction at the appropriate family, campaign, and board level.
The exact statistical mechanism remains a hard prerequisite for high-volume
autonomous search.

### 4.4 Reproducibility

Every Gold row must be reproducible from:

- frozen strategy source or declarative definition;
- exact parameter configuration;
- data snapshot/fingerprint and comparator definition;
- feature and execution semantics;
- engine, validator, threshold, and ranking versions;
- random seeds and search/campaign provenance;
- complete gate results and retained artifacts; and
- certification and forward-evidence timestamps.

If any required component is missing, the row is not Gold.

## 5. The research funnel

### 5.1 Vocabulary

- **Idea:** a written hypothesis.
- **Family:** one executable mechanism with a declared parameter space.
- **Configuration:** one family plus one exact parameter set.
- **Strategy candidate:** one configuration that completed a backtest.
- **Strategy:** in owner-facing summaries, a configuration; technical views must
  retain the more precise terms above.

Counts must name their funnel stage. “Strategies tested” alone is too ambiguous
at scale. A digest should distinguish, at minimum, configurations generated,
cheap-screened, fully backtested, validated, and newly Gold, plus family counts.

### 5.2 Candidate-ready contract

Before a family can enter executable research it must include:

- executable logic or a valid declarative strategy definition;
- declared parameter domains and constraints;
- a one- or two-sentence economic or behavioral rationale;
- expected failure modes;
- deterministic smoke tests;
- static/lookahead/safety-check results; and
- immutable identity and version metadata.

### 5.3 Ordered gates

The intended cost-ordered funnel is:

1. parse/schema/deduplication checks;
2. pre-execution static and capability checks;
3. sandboxed compile/smoke/determinism/resource tests;
4. very cheap plausibility and correctness screens;
5. required backtest performance gates, including the B&H contract;
6. the complete validation and anti-overfitting suite;
7. artifact/reproducibility verification;
8. Gold publication and ranking.

Failure is terminal for that exact attempt at that version; later expensive
stages do not run. A simple two-EMA family may pass correctness and anti-overfit
checks but fail economic performance, and therefore never reach Gold.

No autonomous candidate is trusted merely because a frontier model authored it.
The pipeline has to execute code before it can backtest it, so safety gates must
precede candidate execution rather than being treated as a benefit of eventual
Gold validation.

## 6. Continual ideation and search

### 6.1 Two cooperating loops

The always-on system contains two parallel loops:

- **Research intelligence loop:** read recent aggregate outcomes, leaderboard
  weaknesses, failure reasons, retired-family samples, and unused mechanisms;
  then propose ready families, repair a bounded number of invalid candidates,
  and restock prioritized queues.
- **Deterministic experiment loop:** consume queued work according to protected
  resource priorities, evaluate configurations, persist outcomes, validate
  survivors, publish Gold, and expose structured feedback.

The frontier provider is replaceable. Prompts, candidate schemas, tool
capabilities, and output contracts should not make “Claude” a system dependency.
One model at a time is sufficient.

### 6.2 Search policy

**OWNER INTENT, SPECIFICATION PENDING.**

- Keep enough queued work to use available research compute without requiring
  every generated configuration to run immediately.
- Favor promising mechanisms and deliberate responses to champion weaknesses,
  while reserving a permanent exploration lane for unusual ideas.
- Initial planning allocation: approximately 70% exploitation/promising
  families, up to 20% champion-weakness work when needed, and 10% unusual
  exploration. The actual allocation should adapt to survivor yield, Gold yield,
  novelty, and operational priorities.
- Recertification and trusted-signal work always preempt discovery research.
- Cheaply sample broad or retired families before committing deep search.
- Do not permanently condemn an indicator or mechanism merely because one
  implementation failed. Preserve failure evidence and permit redesigned
  versions.
- Review aggregate results before generating the next batch so the agent does not
  repeat rejected configurations or get trapped in one mechanism.
- Retest exact prior configurations only when a versioned reason exists, such as
  meaningful new market data, a changed engine/validator, or a deliberate audit.

There is no fixed “one family per hour” completion target. Throughput should be
measured empirically after correctness, resource isolation, and representative
workloads exist.

## 7. System architecture

```text
REMOTE FRONTIER AGENT (scheduled, model-agnostic)
  reads results and failures
  authors isolated candidate definitions/code
  attempts bounded candidate repair
  proposes queue priorities
                  |
                  v
UNTRUSTED CANDIDATE INTAKE
  schema -> static policy -> sandbox -> smoke -> dedupe
                  |
                  v
PROTECTED DETERMINISTIC CORE
  verified data -> cheap screen -> full backtest -> validation
  -> reproducibility -> Gold -> score/rank
                  |
          +-------+-------+
          |               |
          v               v
  EXPERIMENT DATABASE   GOLD LEADERBOARD / ARCHIVE
                          |
                          v
HUMAN-AUTHORIZED OPERATING PLANE
  rank sets Recommended; Max normally sets Active
  Active ID + verified data -> protected signal evaluator
  -> last verified Montauk instruction
                          |
                          v
READ-ONLY APP + SLACK/AGENT SURFACE
  digest, explanation, alerts, owner-authorized commands
```

The architecture must enforce four separate planes:

1. **untrusted model-agnostic ideation;**
2. **sandboxed candidate execution;**
3. **protected deterministic data/backtest/validation/ranking;** and
4. **human-authorized operating and published state.**

Information may flow from protected results back to ideation, but ideation's
write authority never flows into the protected core or Active state.

The high-volume experiment ledger belongs in a queryable local database, not in
millions of committed JSON files. Git/GitHub retains protected infrastructure,
versioned strategy source/definitions, the current and historical Gold
publication layer, migrations, and disaster-recovery essentials. Database
backup and restore are required even if raw experiment rows are not committed.

## 8. Autonomous-agent authority and containment

### 8.1 Allowed

The scheduled agent may:

- author new isolated strategy families and parameter spaces;
- write rationale, failure hypotheses, tests, and metadata;
- read the leaderboard and complete failure ledger;
- submit valid candidates to intake without human review;
- analyze aggregate research outcomes and recommend the next search;
- make frequent commits in the generated-research area;
- attempt two or three immediate repairs of invalid candidate code; and
- place unresolved candidates in a lower-priority repair queue.

### 8.2 Prohibited without explicit owner-directed work

The agent may not change:

- the data pipeline or data-quality contract;
- execution timing, fills, fees, or comparator semantics;
- the backtest/search engine;
- the validation suite or Gold thresholds;
- Montauk Score, confidence, performance, or ranking formulas;
- recertification, demotion, active-strategy, or signal-authority rules;
- operations safety, sandbox policy, notification authority, or recovery rules;
- protected tests, fixtures, golden artifacts, or audit logs; or
- permissions that enforce these boundaries.

This is the highest-priority autonomy rule. It must be mechanically enforced,
not merely stated in a prompt. The exact repository/process boundary—separate
repositories, protected paths, limited credentials, signed manifests, reviewed
promotion, or a combination—is OPEN.

Commits are rollback points, not a sandbox. Candidate execution still requires
capability denial, process isolation, resource/time limits, deterministic inputs,
and explicit output schemas. Network, arbitrary filesystem writes, subprocess
spawning, credential access, and protected-repository mutation should be denied
by default.

### 8.3 Candidate representation

Rust is the fixed production strategy/evaluation language; the agent does not
choose among Python, Go, and Rust. **DECIDED:** the normal and first production
path is a schema-constrained declarative family specification over a protected,
prebuilt Rust primitive library. The agent declares one mechanism, its typed
logic graph, parameter domains, and constraints. It does not enumerate exact
configurations. Rust performs schema/type/causality validation, canonicalizes and
hashes the graph, generates only valid parameter combinations, compiles an
execution plan once, and batch-evaluates configurations as data.

This minimizes the two errors automation can actually prevent: malformed or
unsafe strategy implementations and invalid parameter combinations. It cannot
make the economic hypothesis correct; backtesting and validation still decide
that.

A genuinely novel mechanism may eventually use one isolated Rust module compiled
once for that immutable family version, then sweep its parameter space without
recompilation. That escape hatch is disabled until its containment, causality,
determinism, and parity acceptance tests pass. Python may remain a readable
reference/parity oracle, but it is not a production strategy format or an
independent source of trading truth.

## 9. Leaderboard, recommendation, and active authority

### 9.1 Leaderboard

**DECIDED.**

- There is one current Gold leaderboard, not a staging board or Trade Roster.
- Every current Gold configuration is eligible for its own row.
- Rows may be grouped and collapsed by family for legibility.
- The board has no conceptual maximum size; storage and views must be
  database-backed, paginated, filtered, and indexed rather than represented as
  one giant file.
- A strategy that loses Gold leaves the current board and remains in a historical
  Gold archive with the reason and versions.
- The board reranks after relevant certification, recertification, data, or score
  updates.

The default compact metrics are **Montauk Score, Validation Score (or calibrated
Confidence only when calibration supports that word), and deployable
Performance**. Any additional headline metric must have one clear definition and
earn its place. Plain-English weaknesses and simple gate-state indicators should
be available without exposing a zoo of loosely related scores.

### 9.2 Recommended versus active

- **Montauk Recommended:** the highest-ranked strategy under the current
  recommendation/switch contract.
- **Active Strategy:** the owner-authorized strategy currently allowed to produce
  the trusted signal.
- **Manual Override:** an explicit persistent state showing that Active differs
  from Recommended.

A normal recommendation change does not change Active. Max may approve or
decline it; ignoring it leaves the incumbent active. The interface must make a
manual override impossible to mistake for the recommendation.

Confidence gains matter more than equally sized performance gains. A small score
improvement should not create churn. The exact meaningful-superiority threshold,
minimum forward evidence, and cooling-off rule are OPEN.

### 9.3 Emergency loss of Gold

The owner wants continuous operation on a Gold-certified strategy and also
retains authority over state-changing replacements. The exact rule is therefore
OPEN:

- whether a same-state fallback may activate automatically;
- what happens when the best fallback disagrees with the current risk state;
- how long the last position/state may be held while human review is required;
  and
- the no-Gold behavior.

Until ratified, no implementation may infer that “fallback” authorizes a trade.
The safe provisional behavior is to freeze the last trusted state, mark human
decision required, and send a critical alert.

## 10. Data, live evidence, and recertification

### 10.1 Data failure

If current data fails verification:

- do not produce a new trusted signal;
- do not certify, recertify, demote, or mutate the current leaderboard from the
  failed/partial dataset;
- keep displaying the last verified signal with an explicit stale timestamp;
- preserve current authority state;
- raise an actionable failure for human intervention; and
- optionally continue clearly labeled research against the frozen last-good
  dataset, but do not promote those results as current.

On recovery after downtime: catch up and verify data first, then recertify the
active strategy before trusting a new signal; only then resume lower-priority
research and board maintenance.

### 10.2 Forward evidence and recertification

Montauk must track, per Gold row:

- certification/freeze date;
- untouched forward bars and elapsed market time;
- forward performance versus the frozen comparator;
- observed drawdown and trade count;
- last recertification data/version; and
- current, stale, or revoked state.

The initial operating intuition was active daily, top 20% or top 5,000 twice per
week, and full board every two weeks. The owner prefers evidence-based staleness
triggers if they are more meaningful. The final scheduling policy is OPEN, but
active-strategy verification and recertification always outrank new discovery.

A core data, engine, execution, validator, threshold, or ranking change creates a
new methodology version. The scope of automatically stale rows and the
owner-triggered/full-board recertification workflow must be explicit before such
a change is accepted.

## 11. Storage, audit, and failure memory

The experiment database retains a compact permanent record for every attempted
configuration:

- identity, family, parameters, and campaign;
- generation and evaluation timestamps;
- data/engine/validator versions;
- funnel stage reached;
- key metrics;
- terminal failure code and plain-English reason; and
- references to retained artifacts.

Full artifacts are required for Gold and near-Gold candidates; retention tiers
for the remainder may be compact. Generated strategy source is retained even
after retirement so later agents can study or redesign it.

The failure ledger is part of the research intelligence, not a trash pile. The
agent should read it to avoid exact repetition, distinguish implementation
failure from mechanism failure, identify complementary mechanisms, and sample
retired families when new data or a material redesign justifies it.

Silent fallback and swallowed error behavior are prohibited. Every operational
failure has a structured code, ownership, safe state, retry policy, escalation
policy, and durable audit event.

## 12. User experience

The primary experience should answer:

1. What is the current trusted TECL state?
2. Which strategy is active, is it still Gold, and is it a manual override?
3. Why is it still the most defensible active choice?
4. Is a materially better recommendation waiting?
5. Is anything broken or stale?
6. Is research making useful progress?

The app is primarily read-only. Validation gates should appear as simple,
traceable pass/fail lights with plain-English explanations such as “most of the
historical advantage came from one event,” with detailed evidence available on
demand.

The notification surface may begin with one daily digest because Montauk does
not trade intraday. The digest should include the trusted state and any change,
active Gold/override status, staged recommendation, honest funnel counts, new
Gold rows, important board movement, forward-evidence/recertification status, and
actionable failures. Critical data, active-Gold, signal, or system failures may
later justify immediate alerts.

Slack is expected to support conversation with the resident agent and may support
owner-authorized commands or approvals. Authentication, replay protection,
idempotency, confirmation, audit, and which commands are allowed are OPEN.

## 13. Chimera

Chimera is a candidate family in which several strong strategies vote or
contribute confidence to a system-level risk estimate. It receives no special
Gold treatment and no shortcut.

Chimera work waits until several materially independent Gold strategies exist
and independence can be measured. If no ensemble beats the best single strategy
under the same contract, keeping the single strategy is a valid result.

## 14. Performance implementation

Accuracy is more important than speed; speed matters because it determines how
many honest experiments the available hardware can evaluate.

The preferred direction is:

- a legible reference implementation and frozen behavioral fixtures;
- a prebuilt high-performance Rust evaluator and reusable primitive library;
- compact strategy definitions for normal composition;
- at most one isolated compiled Rust module per genuinely novel family, not a
  newly compiled program for every parameter configuration;
- profiling on representative workloads;
- shared/vectorized/precomputed indicator work where semantics allow;
- optimized Rust kernels and evaluator paths only for measured bottlenecks; and
- parity tests with bit-for-bit equality where possible and explicit,
  tolerance-pinned equivalence otherwise.

Compilation proves syntax/type properties, not trading correctness, absence of
lookahead, or validity of the edge. No optimized path may become an independent,
unreconciled source of trading truth.

## 15. Definition of done

Montauk 3.0 is ready for Max to call complete when:

- the full loop in §1 operates automatically on the dedicated host;
- the protected-core boundary is mechanically enforced;
- the Gold contract and search-breadth correction are versioned, tested, and
  defensible;
- every published Gold row is reproducible;
- data failure, restart, offline recovery, stale evidence, and active-Gold loss
  enter explicit safe states and escalate correctly;
- the recommendation/active distinction and owner authority are unambiguous;
- the system can continuously generate, test, learn from, and revisit strategy
  research without queue starvation or silent failure;
- the current signal and its justification are legible at a glance;
- the system has passed representative end-to-end, recovery, security, parity,
  and unattended-soak acceptance tests; and
- Max decides the evidence is sufficient.

An unattended soak test is evidence for that decision, not an automatic gate to
4.x.

## 16. Remaining decisions

The following require explicit answers or a focused design experiment:

1. Gold-safe signal/execution timing and the exact B&H comparator.
2. Required real-data periods, recent-performance gate/weight, rolling
   underperformance demotion, and minimum trade/evidence rules.
3. Synthetic catastrophic-failure behavior.
4. Search-breadth accounting and board-level false-discovery control.
5. Initial Rust primitive vocabulary, the acceptance evidence required to enable
   the staged isolated-family escape hatch, and who may authorize its use.
6. Mechanical protected-core enforcement and repository/credential boundaries.
7. Recommendation superiority, cooling-off, and forward-evidence requirements.
8. Active-Gold-loss, disagreeing fallback, and no-Gold state machine.
9. Recertification/staleness triggers and methodology-change consequences.
10. Slack command and approval authority.
11. Retention, backup, restore, and disaster-recovery targets.
12. Quantified 3.0 acceptance tests and evidence presentation.

Those questions are collected in
[Questionnaire 3 — Final Operating Contract](Questionnaires/Questionnaire%203%20-%20Final%20Operating%20Contract.rtf).
Answers become entries in [decisions.md](decisions.md) and changes to this
charter; they must not create another parallel source of truth.
