## Elevation Plan: Project Montauk
**From:** A manual backtesting environment burdened by fractured domain models, lacking localized tests, and restricted by brittle string-template code generation.
**To:** A test-driven, cryptographically secure, and unified automated strategy compiler capable of programmatic logic discovery via a shared AST.

---

## Priority 1: Sub-2-Second Unit Test Suite
**What:** Introduce a fast `pytest` suite for the core Python backtesting logic, completely stubbing out external data ingestion and state files.
**Why first:** This is the universal mechanical safety net. Attempting to unify the fractured domain models or delete the heavy validation layers without basic execution telemetry will inevitably break the system silently. Fearless change requires immediate feedback.
**Definition of done:** All core execution paths in `strategy_engine.py` and `backtest_engine.py` have passing tests that execute in under 2 seconds.
**Estimated scope:** Medium — The logic exists, but decoupling it from the data layer for testing will require surgical dependency injection.
**Dependencies:** None.

---

## Priority 2: Secure Data Ingestion and State Integrity
**What:** Implement bounds checking, anomaly detection, and atomic file locks on `TECL-markers.csv`, external API streams, and concurrent JSON state files (`hash-index.json`).
**Why second:** With unit tests verifying the logic, we must ensure the data is trustworthy. As the optimization engine scales horizontally, concurrent file corruption and poisoned data streams become the primary attack surface. You cannot automate deployment until the inputs are cryptographically verified.
**Definition of done:** Data ingestion pipelines reject anomalous payloads, and state files use atomic locks to prevent concurrent corruption.
**Estimated scope:** Medium.
**Dependencies:** Priority 1 (Unit tests to verify data parsing logic safely).

---

## Priority 3: Domain Model Unification and Linguistic Purge
**What:** Consolidate the redundant `Trade` and `BacktestResult` schemas across `strategy_engine.py` and `backtest_engine.py`, and systematically replace all obsolete references to `vs_bah` with "share-count multiplier" vocabulary.
**Why third:** Protected by the unit tests and secure data boundaries, we can now safely untangle the core domain. You cannot build a shared AST compiler on top of contradictory primitives.
**Definition of done:** A single, authoritative definition exists for `Trade` and `BacktestResult`, and `vs_bah` is entirely eradicated from the codebase.
**Estimated scope:** Large — This is a system-wide structural and linguistic refactor.
**Dependencies:** Priority 1 (Unit tests to ensure math and execution logic don't break during consolidation).

---

## Priority 4: Abstract Syntax Tree (AST) Migration
**What:** Replace the 3380-line string formatting in `pine_generator.py` with a shared AST/DSL that represents strategy topologies abstractly across both Python and Pine Script.
**Why fourth:** This is the ultimate North Star unlock. It shifts the engine from parameter optimization to programmatic logic discovery and neutralizes Pine Script injection vulnerabilities. It can only happen once the domain primitives are unified.
**Definition of done:** The Python backtester and Pine Script generator compile strategies from a single shared configuration object or DSL.
**Estimated scope:** Large.
**Dependencies:** Priority 3 (Unified domain models).

---

## Not In This Plan (And Why)

- **Automating TradingView Deployment:** The Accelerator strongly advocated for zero-touch deployments to TradingView. We are excluding this because automating deployment before Priorities 2 and 4 are complete merely builds a high-speed pipeline for poisoned, curve-fit strategies.
- **Immediate Deletion of 9-Layer Validation:** The Pragmatist pushed to burn down the complex statistical validation ceremony immediately. We are excluding this because until Priority 2 is complete, those layers serendipitously act as anomaly detection against poisoned data.

---

## What Would Change This Plan

If the team has an explicit, near-term mandate to scale the `evolve.py` engine horizontally across a remote cluster this month, Priority 2 (Secure Data Ingestion and State Integrity) instantly becomes Priority 1. The lack of atomic file locks on the JSON state index will physically break distributed compute before the lack of unit tests does.