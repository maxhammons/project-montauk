# Montauk 3.0 Idea-to-Gold Pipeline

**Status: REVISED DESIGN DRAFT (2026-07-17).** This replaces the earlier
rare-authoring/nightly-drain plan. It implements the clarified direction in
[charter.md](charter.md) and [decisions.md](decisions.md): continuous
model-agnostic ideation, untrusted candidate containment, deterministic
evaluation, automatic Gold-to-leaderboard publication, and human authority over
normal active-strategy changes.

This is an architecture and sequencing brief, **not yet a safe build handoff**.
Questionnaire 3 and Phase A must turn the remaining owner choices into frozen,
testable contracts before a coding agent is authorized to implement the
autonomous system.

## 1. Goal

Accept a human idea or continuously generate new strategy families, turn their
parameter spaces into exact configurations, cheaply reject weak work, fully
backtest and validate survivors, and publish every reproducible Gold
configuration without human research maintenance.

The pipeline optimizes for:

1. false-Gold prevention;
2. correct and reproducible trusted signals;
3. legibility and recovery;
4. maximum useful throughput on available hardware.

“More configurations tested” is useful only when every attempt remains inside the
same honest accounting and methodology contract.

## 2. Four planes and one-way authority

Montauk 3.0 separates four planes:

1. **Untrusted ideation plane.** A scheduled, model-agnostic frontier agent reads
   permitted research summaries, authors new families, and repairs its own
   candidate artifacts.
2. **Sandboxed strategy-execution plane.** Candidate definitions are parsed,
   statically checked, capability-restricted, smoke-tested, and evaluated without
   credentials or write access to the core.
3. **Protected deterministic plane.** Verified data, backtest semantics,
   validation, Gold, scoring, ranking, recertification, and signal generation.
4. **Human-authorized operating plane.** Recommended strategy, active strategy,
   last verified instruction, owner approvals, alerts, and audited commands.

Information may flow from deterministic results back to ideation. Write authority
never flows from ideation or candidate code into the protected or active-authority
planes.

The agent decides what to propose. The scheduler decides what receives compute.
The protected pipeline decides what the evidence says. Max decides normal active
strategy changes.

## 3. Canonical terms and counts

| Term | Meaning |
|---|---|
| Idea | Written hypothesis about a possible signal mechanism |
| Family | One executable mechanism plus its declared parameter space |
| Configuration | One family version plus one exact parameter set |
| Candidate | A configuration that completed the required backtest |
| Gold row | A candidate that passed every current Gold requirement |

Owner-facing copy may call a configuration a “strategy.” Operational metrics must
name the stage:

- families proposed and accepted;
- configurations expanded;
- configurations cheap-screened;
- configurations fully backtested;
- candidates fully validated;
- new/current/revoked Gold rows.

A generated combination that never ran is not “tested.”

## 4. Candidate-ready contract

A family cannot enter executable intake until it is submitted through the
versioned structured StrategySpec contract. The agent authors one family/search
space; it does not enumerate exact configurations. The specification contains:

- immutable family and version identity;
- executable logic or a valid typed/declarative definition;
- parameter names, types, domains, constraints, and intended search method;
- a one- or two-sentence economic/behavioral rationale;
- expected failure modes;
- required inputs and warm-up;
- explicit signal timing;
- deterministic smoke tests and expected results;
- static lookahead/capability-check results;
- author/provider and generation-run provenance; and
- content hash plus parent/redesign lineage.

Rust is the fixed production authoring/evaluation target; the agent never chooses
the implementation language. The high-throughput distinction is:

- **normal family:** the agent submits a compact schema-constrained definition
  over a versioned prebuilt Rust primitive registry. The definition is
  declarative data, not Python code. Unknown primitives, invalid types, causal
  violations, and malformed constraints fail before evaluation;
- **novel family:** the agent may emit one isolated Rust module, compiled once for
  that immutable family version; and
- **configuration:** the trusted evaluator supplies exact parameters to the
  already-built family evaluator. It never compiles a new program per
  configuration.

This is how millions or billions of configurations can share one compiled
execution plan, precomputed indicators, memory layouts, and batched execution.
Python may remain a reference/parity oracle and test harness, but not a production
family or configuration representation. The isolated Rust-module route is staged
and disabled until its containment and correctness acceptance tests pass.

Illustrative manifest only—the final schema remains to be chosen:

```yaml
family_id: vivid_otter
version: 1
definition_hash: sha256:...
representation: composition_v1
author:
  kind: frontier_agent
  provider: replaceable
mechanism: >
  Reduce exposure when medium-term trend weakens under elevated volatility.
expected_failure: >
  Rapid whipsaw in low-volatility sideways markets.
inputs: [tecl_ohlcv]
signal_timing: pending_contract
parameters:
  fast_window: {type: int, min: 5, max: 80}
  slow_window: {type: int, min: 40, max: 400}
  vol_window: {type: int, values: [10, 20, 30, 60]}
constraints:
  - fast_window < slow_window
smoke_fixture: fixtures/strategy_contract_v1
```

Names should follow the owner's adjective-animal convention. Names are labels,
not statistical identities.

## 5. The cost-ordered funnel

```text
verified data + frozen methodology
              |
              v
family proposal -> schema/policy/dedup -> isolated smoke
              |
              v
configuration expansion + cheap screen
              |
              v
full required backtest and B&H performance gates
              |
              v
complete correctness / anti-overfit / robustness validation
              |
              v
artifact and reproducibility verification
              |
              v
Gold certification -> leaderboard row -> recommendation evaluation
              |
              v
structured results and failures -> next ideation cycle
```

### Stage 0 — operational preconditions

Before trusted work:

- the control database is healthy;
- the last committed methodology/version set is internally consistent;
- required market data is complete, verified, and fingerprinted;
- active-strategy signal and recertification deadlines have resource priority;
  and
- the experiment worker has enforced CPU, memory, temperature, and disk limits.

Research may be preempted at any point by data, trusted-signal, active
recertification, recovery, or notification work.

### Stage 1 — agent ideation and bounded repair

On a tunable schedule, initially imagined as roughly hourly:

1. read aggregate results from the last completed interval;
2. read exact-duplicate summaries, family histories, failure-reason aggregates,
   leaderboard composition, and active-champion weaknesses;
3. choose work across promising, weakness-repair, and exploratory lanes;
4. author one or more ready families/search spaces;
5. run local schema/static/smoke tooling;
6. retry invalid candidate artifacts two or three times; and
7. submit valid artifacts or enqueue unresolved ones for low-priority repair.

The agent may predict which work is promising for queue ordering. That adaptive
selection must be logged as part of search provenance; it cannot be treated as
free evidence.

### Stage 2 — untrusted intake

Intake is deterministic and fail-closed:

- parse and validate the manifest;
- content-address and version the family;
- reject exact duplicates under the same data/engine/validator fingerprint;
- reject prohibited capabilities and imports;
- deny network, secrets, arbitrary filesystem writes, subprocesses, and core
  mutation;
- run in a disposable worker with read-only typed inputs;
- enforce time/CPU/memory/output limits;
- verify deterministic output under repeated seeded runs;
- run lookahead/static checks and golden smoke fixtures; and
- persist a structured failure or admit the family to configuration expansion.

Git commits are useful history and rollback. They are not a substitute for this
boundary.

### Stage 3 — configuration expansion and cheap screening

The trusted engine, not the model, expands parameter spaces. It should:

- type-check and canonicalize the family graph against the exact primitive
  registry version;
- apply declared constraints before evaluation;
- generate canonical configuration identities;
- use version-aware exact deduplication;
- reuse safe precomputed indicators where semantics permit;
- compile/optimize one internal execution plan per family version rather than per
  exact configuration;
- record every configuration actually evaluated;
- run the cheapest correctness and economic screens first; and
- promote only survivors to full backtesting.

Related variants are legitimate configurations. Family-level “near twin”
similarity may help presentation or compute allocation, but must not silently
erase exact configurations the owner wants tested.

### Stage 4 — full backtest and economic eligibility

Every survivor runs the required real-data backtests under one frozen executable
contract:

- signal observation time;
- earliest available fill;
- B&H comparator timing;
- fees, slippage, and missing-bar behavior;
- warm-up and boundary rules;
- real and modern evaluation periods; and
- required performance margins.

Configurations that fail required B&H/performance gates stop here. The exact
close-versus-next-executable-price contract and required real-data periods are
OPEN and must be settled before implementation.

Synthetic history may run as a diagnostic screen. It cannot replace required
real-data passage. The exact blocking consequence of catastrophic synthetic
failure is OPEN.

### Stage 5 — complete validation

Every remaining candidate, regardless of human or AI origin, must satisfy the
same mandatory versioned evidence planks and rigor. Structurally inapplicable
algorithms require a predeclared equivalent or valid `not_applicable` outcome;
they do not disappear through silent score renormalization. At minimum the target
contract covers:

- engine/data/integrity correctness;
- no lookahead, overlap, or repaint;
- independent comparator/golden regression;
- search-path and family/campaign selection-bias accounting;
- parameter-neighborhood and walk-forward behavior;
- PBO and performance deflation;
- stationary-bootstrap uncertainty and minimum evidence;
- parameter sensitivity and fragility;
- event, regime, and return concentration;
- execution degradation;
- board-level multiple-testing control;
- artifact completeness and independent reproduction; and
- explicit confidence limits and data-scarcity disclosure.

The pipeline does not “give everything its due diligence” by wasting full
validation compute on candidates that already failed. It does so by applying the
correct decisive test at every stage and recording why work stopped.

### Stage 6 — Gold, leaderboard, and recommendation

A candidate becomes Gold only if all hard eligibility conditions are true under
one frozen contract version. Publication is transactional:

1. freeze the strategy definition and exact parameters;
2. finalize complete artifacts and fingerprints;
3. create/update the Gold certification record;
4. atomically expose the row through the leaderboard view;
5. calculate current score/rank;
6. compare it with the recommendation under the switch contract;
7. start forward-evidence tracking; and
8. emit the appropriate digest/event.

Gold publication never changes the active strategy. A recommendation change never
changes the active strategy. Normal activation requires an audited owner action.
Emergency active-Gold-loss behavior remains an explicit unresolved state machine.

### Stage 7 — feedback and memory

Every terminal result writes a structured record:

- exact identity and versions;
- stage reached and compute used;
- metrics measured at that stage;
- pass/fail code and plain-English reason;
- source campaign and queue lane;
- parent/revision lineage; and
- artifact references.

The next ideation cycle receives aggregates and representative examples—not an
unbounded raw dump. It should learn:

- which implementations failed to compile or violated safety rules;
- which parameter regions lack economic traction;
- which mechanisms repeatedly fail specific gates;
- which champion weaknesses remain unaddressed;
- which families are overrepresented;
- which retired families deserve a small resample; and
- which novel combinations have not been explored.

“Retired” means low priority under current evidence, not permanently forbidden.
A family may be revisited with meaningful new data, a complementary primitive, a
champion weakness, periodic sampling, or a material redesign.

## 6. Scheduling and resource allocation

Priority order:

1. **P0:** verified-data refresh, active-signal generation, active-strategy
   forward replay/recertification;
2. **P1:** recovery, integrity failures, critical notifications;
3. **P2:** recommendation/top-cohort and rolling full-board recertification;
4. **P3:** candidate validation and Gold finalization;
5. **P4:** preemptible discovery research and low-priority repair.

Initial discovery planning uses approximately:

- 70% promising families/regions;
- up to 20% active-champion weakness work when useful; and
- at least 10% unusual exploration.

These are adaptive allocations, not scientific facts. The scheduler should
change them from observed useful yield while preserving an exploration floor.
Queue backlog is acceptable. Queue starvation should wake the ideation loop
rather than ask Max for routine maintenance.

## 7. Persistence model

The target scale requires more than Markdown and JSON queues. The operational
design should include:

- a transactional control database for families, versions, configurations, jobs,
  certifications, recommendation/active state, recertification state, and a
  notification outbox;
- append-only, compressed, partitioned experiment results for high-volume
  screens;
- content-addressed immutable artifacts for Gold and near-Gold candidates;
- compact reproducible Gold manifests/snapshots suitable for Git/GitHub backup;
  and
- tested database backup, restore, and corruption-recovery procedures.

The leaderboard is a query/materialized view over current Gold certifications,
not a manually edited file. The historical Gold archive is an immutable status
history, not a deletion pile.

Storage volume must be benchmarked. At extreme claimed throughput, even a tiny
record per configuration can exceed local-disk capacity; retention and
aggregation tiers must be derived from measured bytes/configuration and recovery
needs.

## 8. Protected-core rules

The autonomous agent's write credentials must be incapable of changing:

- data acquisition/verification;
- backtest/execution/comparator semantics;
- search accounting;
- validation and Gold thresholds;
- score/ranking;
- board/active authority;
- signal generation;
- operations safety and recovery;
- protected tests/golden fixtures; and
- the permissions themselves.

Core changes occur only in an explicit Max-authorized maintenance/release mode.
They create new version identities and trigger a defined stale/recertification
policy. A generated strategy should be isolated and immutable by family version;
the agent should not append autonomous work into one shared monolithic strategy
file.

## 9. Delivery sequence for a coding agent

Do not build the hourly agent first. Build the truth and containment boundaries
it will depend on. Every phase needs named artifacts, tests, rollback/cutover
instructions, and a blocking exit review; a phase title is not permission to
invent the unresolved contract inside it.

### Phase A — freeze and test the contracts

- Settle execution/fill/B&H semantics.
- Settle the real-data, recent, synthetic, rolling, and minimum-evidence Gold
  gates.
- Complete the validation correctness audit and close or explicitly disposition
  G1, G2, G10, G11, G12, and G13.
- Specify multiplicity as a formal statistical design: tested universe,
  within-family versus board/lifetime scope, online versus batch behavior,
  dependency clustering, alpha/sequential policy, and whether a new search can
  change an existing certificate. Calibrate it with simulation and independent
  review.
- Write transition tables and invariants for jobs/candidates, certifications,
  Recommended/Active/override, stale data, no Gold, human decision required,
  and the exact states permitted to emit a trusted instruction.
- Reconcile the resulting truth into canonical repository docs and tests,
  including `CLAUDE.md`, `docs/charter.md`,
  `docs/validation-thresholds.md`, and
  `docs/validation-philosophy.md`; publish one version/hash manifest so these
  3.0 planning files do not become a parallel authority.
- Turn every contract into versioned schemas, fixtures, decision tables, and
  acceptance tests.

**Exit:** Max ratifies the contract package; the validation audit and statistical
design have review evidence; no canonical doc/test still says “top row is
automatically active” or preserves an incompatible validation route.

### Phase B — representation, causality, containment, and scale prototypes

- Prototype the prebuilt Rust evaluator and primitive library with typed
  strategy definitions on representative current and novel families.
- Implement a structured StrategySpec submission tool exposing the exact
  primitive registry/schema; prove malformed types, invented primitives, invalid
  constraints, and causal violations fail before configuration generation.
- Compile each accepted declarative family graph into one optimized internal Rust
  execution plan, then reuse it across the full parameter sweep.
- Separately prototype one isolated agent-authored Rust family module to measure
  compile/repair cost and containment burden, but keep the module route disabled
  in autonomous operation until its acceptance suite passes.
- Provide a causal feature/signal API or prove prefix-replay invariance so
  read-only access to a full historical array cannot create future-data leakage.
- Prototype disposable workers, capability denial, static checks, core
  read-only mounts, and CPU/memory/time/output limits.
- Measure representative throughput, latency, bytes retained per configuration,
  result-compression ratios, and trusted-work preemption on target-class
  hardware.

**Exit:** representative families are expressible; lookahead/prefix and sandbox
escape suites pass; candidate failure cannot mutate core or miss a trusted
deadline; scale measurements are sufficient to design storage honestly.

### Phase C — canonical persistence, identities, and migration

- Introduce the control database and migrations.
- Define immutable family/configuration/campaign/certification identities.
- Import or reference existing queues, hash history, leaderboard, active pointer,
  and artifacts without creating dual authorities.
- Add transactional jobs, leases, idempotent transitions, and notification
  outbox.
- Derive retention/partitioning from Phase B bytes-per-configuration results;
  identify which store is authoritative after recovery.
- Implement backup/restore, reconciliation, legacy rollback, and corruption
  reports.

**Exit:** a dry-run migration preserves every authoritative identity; crash and
restore drills recover the declared Gold/authority state; rollback to the legacy
read path is tested; there is exactly one operational source for each concern.

### Phase D — deterministic funnel

- Implement cost-ordered stages and durable state transitions.
- Run global engine/data/golden-comparator attestation before screening; run
  candidate-specific causality, determinism, and safety checks before/during
  candidate evaluation rather than deferring integrity to final validation.
- Record honest stage-specific counts and failure codes.
- Connect existing search/backtest/validation capabilities behind versioned
  adapters rather than copying them.
- Make Gold publication atomic and fully reproducible.

**Exit:** every stage has deterministic replay, fail-closed behavior, fault
injection, durable provenance, and clean-environment Gold reproduction.

### Phase E — authority, forward evidence, recovery, and minimum alerts

- Separate recommended, active, and last-verified-instruction identities.
- Implement manual override and audited approval.
- Implement current/stale/revoked/archive certification states.
- Implement data-failure, restart, offline catch-up, recertification, and
  active-Gold-loss state machines.
- Implement the minimum critical alert path, dead-man/health indication,
  kill/disable control, and notification outbox before unattended research is
  possible.

**Exit:** exhaustive state-transition tests prove that only the allowed Active
state can emit a trusted instruction; fault, no-Gold, stale-data, restart,
notification, and owner-override drills reach the specified safe state.

### Phase F — resident agent and feedback loop

- Add a provider-neutral agent adapter and scheduled trigger.
- Generate only allowlisted candidate artifacts.
- Add two/three-attempt candidate repair plus deferred repair queue.
- Feed bounded structured result/failure summaries into subsequent cycles.
- Validate queue allocation and diversity/exploration behavior.

**Exit:** two permitted providers or a provider mock satisfy the same contract;
malicious/invalid outputs cannot cross the sandbox or protected-core boundary;
queue starvation, runaway backlog, and provider failure are visible and safe.

### Phase G — read-mostly surfaces

- Build the daily digest and critical alerts.
- Expose Montauk Score, Validation Score (or calibrated Confidence only when
  justified), deployable Performance, current signal,
  active/override/recommendation status, gate lights, and plain-English weakness
  explanations.
- Add Slack chat in read-only mode first; add authenticated structured mutations
  only after their authority contract is tested.

**Exit:** every headline value traces to one authoritative record; stale,
override, Recommended/Active disagreement, and actionable failures are
unmistakable; privileged Slack commands pass identity, confirmation,
idempotency, replay, and audit tests.

### Phase H — measured performance work

- Profile representative family and parameter workloads.
- Optimize shared computation and data layout first.
- Port only demonstrated bottlenecks behind exact/tolerance-pinned parity tests.
- Set throughput and hardware targets from benchmarks, not aspirations.

**Exit:** optimized and reference paths satisfy frozen signal/trade/fill/metric
parity; discovery load cannot violate data/signal/recertification deadlines;
hardware targets and sustainable thermal/storage envelopes are measured.

### Phase I — commissioning and authority cutover

- Provision the target always-on host from a documented clean build.
- Run the new system in shadow without changing legacy Active authority.
- Rehearse database restore, data divergence, candidate escape, agent/provider
  outage, active-Gold loss, no-Gold, and notification failure.
- Compare shadow signals/artifacts to the frozen reference and investigate every
  divergence.
- Perform an explicit reversible legacy-authority cutover.
- Run the agreed unattended soak and produce the owner-review package.

**Exit:** every acceptance-matrix row has evidence and rollback instructions;
Max explicitly approves autonomous 3.0 operation. This approval does not begin
4.x.

## 10. End-to-end acceptance evidence

The implemented conveyor must demonstrate:

- deterministic replay from the same inputs and versions;
- exact rejection at every funnel stage with durable reasons;
- complete search accounting across adaptive agent cycles;
- no candidate ability to read secrets, use the network, mutate core, escape
  limits, or forge a verdict;
- atomic recovery from termination at each job transition;
- Gold reproduction from a clean environment;
- board publication without active-strategy mutation;
- owner approval/override behavior with audit and replay protection;
- safe current-data failure and offline recovery;
- active recertification preemption under full research load;
- bounded storage growth, successful backup, and restore;
- provider replacement at the agent seam; and
- an unattended soak showing that failures become visible rather than silent.

Before coding handoff, convert this list into an acceptance matrix with a stable
test ID, invariant, fixture/workload, measurable threshold or SLA, expected
artifact, failure severity/safe state, rollback procedure, and owner-sign-off
field. Keep three decisions distinct:

1. objective operational acceptance evidence is complete;
2. Max declares Montauk 3.0 complete; and
3. Max separately authorizes work on 4.x.

## 11. Open decisions

Implementation is blocked on the same concentrated questions listed in charter
§16: execution timing, exact Gold gates, multiplicity correction, candidate
representation/sandbox, protected-core enforcement, recommendation and emergency
authority, forward-evidence/recertification rules, Slack authority, retention,
and measurable acceptance thresholds.
