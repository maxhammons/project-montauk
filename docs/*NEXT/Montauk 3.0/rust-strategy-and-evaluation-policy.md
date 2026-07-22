# Montauk 3.0 — Rust Strategy and Evaluation Policy

**Status: REQUIRED IMPLEMENTATION PILLAR / CHARTER-SUBORDINATE (updated
2026-07-21).** This document owns the production representation and performance
policy for strategy families and configurations. It cannot alter Gold,
authority, or product scope defined by [charter.md](charter.md).

Decision
--------
Rust is the fixed production language for strategy logic, configuration
evaluation, and the performance-critical backtest path. The autonomous agent
does not decide between Python, Go, and Rust.

Python may remain a readable reference/parity implementation, audit tool, and
test harness. It is not a production strategy format or an independent source of
trading truth. Go is outside the strategy/evaluator architecture.

The important vocabulary
------------------------
- Family specification: one trigger/decision graph and one parameter schema,
  plus its domains, constraints, rationale, and failure hypothesis. Family is an
  organizational/batching identity, not the certification unit.
- Configuration: one family version plus one exact set of parameter values.
- Primitive: a protected reusable Rust operation such as EMA, RSI, ATR,
  crossover, threshold, state hold, or exit rule.

A configuration is data. It is not Python code, Rust code, or a separately
compiled executable.

The configuration bucket is logical. Rust may expand deterministic search shards
in bounded batches immediately before evaluation rather than pre-writing an
entire billion-row Cartesian product. Every evaluated exact parameter set still
receives a stable identity, dedup key, and compact durable verdict.

Authoring contract optimized for speed and preventable errors
-------------------------------------------------------------
The normal agent does not enumerate configurations and does not write normal
strategy source code. It submits one schema-constrained StrategySpec through an
allowlisted structured tool/CLI. The tool exposes the exact versioned primitive
registry and parameter types, so the agent cannot silently invent indicator
names or signatures.

The StrategySpec declares:
- a typed logic graph of registered Rust primitives;
- parameter types, domains, and cross-parameter constraints;
- input, warm-up, timing, and state requirements, including point-in-time source,
  publication/revision lag, causal availability, and missing-data semantics for
  every non-TECL input;
- rationale, expected failure mode, and provenance; and
- deterministic fixture expectations.

Rust then:
1. deserializes against the versioned schema;
2. type-checks series/scalar/boolean/state operations;
3. enforces causal-access and warm-up rules;
4. canonicalizes and hashes the family graph;
5. expands only parameter combinations satisfying constraints, in bounded
   deterministic batches when scale requires;
6. deduplicates configurations;
7. compiles one optimized internal execution plan for the family; and
8. shares/precomputes common features and batch-evaluates configurations.

This is the default 3.0 path. The isolated Rust family-module path is staged and
disabled until its containment, causal-access, determinism, resource, and parity
acceptance tests pass.

The first primitive registry is intentionally small and fixture-heavy. Before
cutover it must reproduce the legacy Active strategy needed for shadow safety,
the matched B&H/execution reference, every control/benchmark admitted to the
final 3.0 validator, and any legacy strategy Max explicitly selects as a
migration candidate. Historical Gold rows and legacy scripts are not blanket
coverage requirements. Its initial coverage matrix includes typed
arithmetic and boolean logic; lag/rolling operations; moving averages; momentum;
RSI/MACD; ATR, volatility, and bands; crossover/threshold events; approved
external inputs; and explicit position state. Missing a primitive does not prove
an idea invalid: the agent may use the isolated-module lane, or propose a shared
primitive for a later Max-authorized core release.

Production architecture
-----------------------
1. PROTECTED RUST ENGINE
   Owns verified arrays, causal feature access, reusable primitives, batched
   parameter expansion, shared indicator calculation, backtest/fill semantics,
   metrics, deterministic scheduling interfaces, and artifact output.

2. NORMAL AGENT OUTPUT: DECLARATIVE FAMILY SPEC
   The agent writes a small typed specification that composes protected Rust
   primitives and declares parameter domains/constraints. The Rust engine parses
   the spec, expands exact configurations, and evaluates them in batches. No
   Python strategy wrapper and no compile step are needed for each family or
   configuration.

3. NOVEL-MECHANISM ESCAPE HATCH: ISOLATED RUST FAMILY MODULE
   If the primitive library cannot express a genuinely new mechanism, the agent
   may write one Rust module against a frozen Montauk Strategy SDK. It is compiled
   once for that immutable family version, sandboxed and conformance-tested, then
   reused for every configuration in its parameter sweep. The module begins in
   the generated-research “pool of chaos.” The escape hatch is disabled until Max
   approves its signed acceptance policy. After that one policy approval, any
   module that passes it automatically enters untrusted pipeline intake; Max does
   not review each module individually.

4. REFERENCE ORACLE
   Readable fixtures and, where useful, a Python reference implementation verify
   signals, fills, trades, metrics, and boundary behavior. Reference code does
   not generate the production verdict.

Why not base-Python strategies calling Rust blocks?
---------------------------------------------------
That design is possible through bindings, but it is not the intended production
architecture:

- it creates two production languages and two execution models;
- arbitrary Python strategy code expands the security and nondeterminism surface;
- calls and object conversion can become overhead unless work is carefully
  batched;
- strategy semantics can split between Python glue and Rust primitives; and
- it makes it easier for the reference implementation to become a second source
  of truth.

Python bindings may be useful for development, diagnostics, and parity tests.
The production family representation should remain declarative data consumed
directly by Rust.

Why this is fast
----------------
- Common indicators can be calculated once and shared across configurations.
- Parameter sets can be evaluated in cache-friendly batches.
- The agent spends tokens describing one family/search space rather than emitting
  millions of source variants.
- The compiler runs when the protected engine changes or, at most, once for a
  genuinely novel family—not once per configuration.
- The engine can control memory layout, allocation, parallelism, SIMD/native
  kernels, and work partitioning consistently.

Protected-core boundary
-----------------------
The autonomous agent may create:
- declarative family specifications; and
- isolated Rust family modules against the frozen SDK, if that escape hatch is
  enabled.

It may not modify:
- the protected Rust engine;
- the shared primitive library or Strategy SDK;
- data, fill, comparator, backtest, validation, Gold, score, rank, authority, or
  operations semantics; or
- parity fixtures and controls that police this boundary.

A useful new primitive can be proposed for the shared Rust library, but promotion
requires a Max-authorized core release, review, fixtures, and reference/parity
evidence.

The boundary is a cryptographic release seal, not a prompt or Git convention.
The minimum enforceable design is deliberately small:

- the resident agent runs under an OS identity that has no protected-core write
  credential;
- one content-addressed core release is deployed read-only;
- generated family specs/modules and research artifacts live outside that
  release;
- Max signs the release manifest with a human-held key unavailable to the
  resident agent; and
- startup plus every Gold-publication and trusted-signal job verifies the
  signature, hashes, and permissions and fails closed on any mismatch.

A core change therefore requires an explicit Max-controlled maintenance session,
reviewed diff, protected tests, and a newly signed release. Separate repositories,
protected remote branches, temporary credentials, and other release controls may
support that outcome, but are not additional Montauk product concepts or mandatory
layers unless an implementation threat/recovery test proves they are needed.

Compilation is not validation
-----------------------------
Successful Rust compilation can catch syntax, type, and memory-safety classes of
failure. It does not prove causal data access, correct fill timing,
determinism, a valid economic mechanism, or freedom from overfitting.

Every isolated Rust family module remains untrusted before intake. It must compile
and execute in a disposable worker with no credentials, no network, no protected-
repository writes, no unrestricted subprocesses, causal typed inputs,
deterministic seeds, and strict CPU, memory, time, and output limits.

Compilation, timeout, OOM, or another resource failure is an implementation/
operations verdict, not an economic verdict on the hypothesis. Use one original
attempt plus two immediate bounded repairs, then quarantine the artifact with a
structured reason for lower-priority repair. Candidate code and the resident
agent cannot raise their own resource limits.

Priority
--------
1. Accuracy and one semantic truth.
2. Trusted-signal and recertification deadlines.
3. Throughput and runtime efficiency on the available host.
4. Implementation convenience.

Profiling work after correctness
--------------------------------
The language is decided; the precise Rust design is not. Profiling is ordinary
engineering after correctness, not a hardware-procurement study or numerical
throughput gate for 3.0. Representative workloads may compare:

- primitive-coverage parity for the legacy Active migration fixture, final
  controls/benchmarks, and explicitly selected migration candidates;
- declarative interpreter versus compiled execution plan;
- primitive caching and batched parameter layouts;
- CPU parallelism, SIMD, memory, disk, and thermal behavior;
- declarative family versus isolated Rust family-module throughput;
- compile and bounded-repair costs for novel modules;
- bytes retained per configuration;
- exact signal/trade/fill/metric parity with the reference fixtures under the
  calibrated execution/B&H contract;
- trusted-work preemption and sustainable thermal behavior under full discovery
  load; and
- isolated-module acceptance/repair cost without weakening containment.

Those measurements guide safe Rust optimization on whichever host is supplied.
They do not choose hardware, provider budget, or a strategies-per-hour acceptance
target. The agent does not choose the language.

Dedicated-host execution baseline
---------------------------------
The planned appliance runs native release-mode Rust on minimal current Debian
Stable. Debian and systemd improve predictability, supervision, and permissions;
they are not substitutes for benchmark evidence and do not change strategy or
Gold semantics.

- Hot market data, control state, experiment partitions, builds, and logs live
  on SSD/NVMe. HDD is cold archive/backup only.
- The scheduler gives verified data, signal generation, Active recertification,
  recovery, and alerts first claim on CPU and I/O. Discovery workers use all
  spare capacity at lower priority and must be preemptible.
- Benchmark physical-core and logical-thread counts rather than assuming the
  maximum thread count wins on an older CPU.
- Expand and evaluate configurations in bounded streaming shards; never create a
  file/process/object or compile step per configuration.
- Use matched-channel RAM where the machine supports it. Keep a small emergency
  swap area, but treat sustained swapping as a load-shedding fault.
- Profile release builds under sustained CPU/RAM/SSD/thermal load. Tune worker
  count, batch size, memory cap, reserve capacity, caching, and data layout before
  kernel, governor, filesystem, or exotic compiler changes.
- No overclocking or optimization is accepted if it weakens deterministic parity,
  stability, containment, or a trusted deadline.

The full host, service, remote-agent, conversation-channel, Slack/Buzz, and
OpenClaw-pattern policy is in
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md).
