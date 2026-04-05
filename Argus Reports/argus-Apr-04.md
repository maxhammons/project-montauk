# Argus Report — Apr 04, 2026

> **Mode:** Deep | **Argus v6** | **First Run**
> The project's most important number — "RSI Regime is 4.7x better than 8.2.1" — is wrong. The Python backtesting infrastructure produces unreliable numbers at every layer, from a crippled baseline to a disconnected validation framework. The code computes confidently and incorrectly.

---

## Run Metadata

| Metric | Value |
|---|---|
| Specialists deployed | Architecture, Risk, Data-Integrity, Vision-Drift, Velocity |
| Files in manifest | 88 |
| Total findings generated (Layer 1) | 65 original + 13 cross-lens = 78 |
| Agreements (2+ specialists) | 11 |
| Contradictions | 6 (all resolved or partially resolved) |
| Debates conducted | 4 (RSI Regime Illusion, Charter Governance, Fitness Drawdown, Engine Merge) |
| Alien critics | 3 (Financial Auditor, Airline Safety Engineer, Compiler Writer) |
| Execution PoCs attempted | 5 |
| Execution PROVEN | 4 |
| Execution DISPROVEN | 1 |
| Devil's Advocate verdicts | 7 SURVIVE, 3 WEAKENED, 1 KILLED |
| Blind spot findings (missed by all specialists) | 5 |
| Final findings in report | 11 confirmed + 3 moderate + 8 suspected |

---

# PART 1: WHAT TO DO

---

## The State

Project Montauk built a multi-strategy Python optimizer in 3 days that discovered a strategy claiming to be 4.7x better than the production system. That number is wrong — provably, structurally, at multiple layers. The baseline it compared against uses a 30-bar EMA instead of the production 500-bar EMA (confirmed by execution PoC). The winning strategy has 75% max drawdown with no walk-forward validation (the validation framework physically cannot reach it). The fitness function treats a 75% drawdown as a 37.5% penalty. The optimizer ran for 36 seconds exploring 2.7% of the search space. The project has built a strategy discovery machine that cannot tell truth from noise.

The infrastructure is architecturally sound in pieces — the indicator math is correct, both backtest loops work individually, the validation framework is well-built. The bugs are all at integration points: wrong EMA passed to the wrong function, missing imports between engines, boundary conditions lost in translation. This is the signature of AI-assisted rapid development where each component is generated correctly in isolation but the connections are fragile.

---

## The One Thing

If you do ONE thing from this report, do this.

**What:** Fix the montauk_821 baseline in `strategies.py` (30-bar → 500-bar EMA exit), fix the stagnation detection bug, implement exponential drawdown penalty, then run the 8-hour optimizer overnight.

**Why:** Every comparison in the system flows through the montauk_821 baseline. The baseline is provably wrong (PoC #1: 30-bar vs 500-bar EMA). Fixing it instantly recalibrates every fitness ratio. Combined with the DD penalty fix and stagnation bug fix, the overnight run produces trustworthy numbers for the first time.

**How:**
1. `strategies.py` line 34: add `long_ema` parameter (default 500) and use it for the exit comparison instead of `ema_m`
2. `strategies.py` line 133: change `<` to `<=` for RSI boundary condition
3. `evolve.py` line 234: add `_last_improve` write when fitness improves
4. `evolve.py` line 62: replace `max(0.3, 1.0 - DD/200)` with `exp(-2.0 * (DD/100)**2)`
5. Run overnight: `python3 scripts/evolve.py` with corrected code

**Effort:** 90 minutes active + 8 hours passive (overnight run)
**Impact:** The 4.7x claim either survives with real evidence or collapses. Either outcome is progress.

**Provenance:**
- Source: Architecture, Risk, Data-Integrity, Velocity, Vision-Drift (5/5)
- Agreement: All specialists independently flagged the crippled baseline
- Prosecution: SURVIVES-TESTED (Devil's Advocate confirmed, zero counter-evidence)
- Execution: PROVEN (PoC #1 — code-level proof of 30-bar vs 500-bar discrepancy)

---

## The Drift

### Drift 1: From EMA-Trend System to Open Strategy Discovery Platform

**The Charter says:** "Core entry: emaShort > emaMed" (Section 2). "Do not propose oscillators or countertrend buys as primary logic" (Section 2). "If asked to add mean-reversion... flag it clearly" (Section 8).

**The product is doing:** RSI Regime uses RSI (an oscillator) as primary entry logic in a mean-reversion strategy. spike.md explicitly states "There are no restrictions on what indicators or logic you can use."

**The gap:** The Charter defines a single-strategy EMA-trend system. The codebase implements a 7-strategy discovery platform. spike.md is the de facto governing document. The Charter has not been updated in 31 days.

**How to correct:** Two-part Charter rewrite. Part A: update project description to reflect multi-strategy discovery. Part B: preserve and strengthen deployment gates (walk-forward required, max drawdown cap, TradingView parity required before any strategy goes live). Do this AFTER the engine merge settles the architecture.

**Provenance:** Source: Vision-Drift Specialist (14 drift points documented) | Debate: Charter Governance — split verdict (update description, preserve gates) | Devil's Advocate: SURVIVES-TESTED

### Drift 2: From Validated Results to Unfalsifiable Claims

**The Charter says:** Feature acceptance requires TradingView parity check (Section 5).

**The product is doing:** RSI Regime was crowned winner with zero validation. No walk-forward, no parity check, no TradingView confirmation. The validation framework cannot even reach v4 strategies.

**The gap:** The project has a complete validation infrastructure (validation.py, parity_check.py) that works for 8.2.1 and is structurally disconnected from the strategies that need it most.

**How to correct:** Port validation.py to v4 API — or better, merge engines so validation works for all strategies automatically.

**Provenance:** Source: Risk, Architecture, Data-Integrity, Velocity (4/5) | Execution: PROVEN (PoC #4 — zero bridge code exists)

### Drift 3: From MAR Ratio to vs_bah Multiple

**The Charter says:** Primary metric is MAR ratio (CAGR/MaxDD).

**The product is doing:** evolve.py optimizes `vs_bah_multiple`. spike_auto.py uses `regime_score`. validation.py uses `regime_score`. Three different fitness definitions across three tools. No single consistent definition of "good."

**The gap:** The metric the Charter prescribes (MAR) is not computed by the v4 engine. The metric the v4 engine uses (vs_bah) is not mentioned in the Charter.

**How to correct:** Define the canonical fitness metric in the updated Charter. All tools must use the same definition.

**Provenance:** Source: Vision-Drift F3, Financial Auditor AE-02

---

## The Traps

### The Optimization Illusion — stuck since Apr 3

**The loop:** Run optimizer → get exciting number → celebrate → discover the number is wrong → fix something → re-run → get new number → discover new problem with methodology → fix something else → repeat.

**Why surface fixes can't break it:** Each individual fix (correct the EMA, harden the fitness function, wire up validation) solves one link in a 6-link chain of unreliable computations. Fixing one link does not make the chain trustworthy. The developer has been optimizing the optimizer instead of validating a strategy.

**How to break out:** Apply all 4 quick fixes simultaneously (90 minutes), run the optimizer overnight with corrected infrastructure, then validate the top result in TradingView manually (45 minutes). Only the TradingView parity check breaks the loop.

**Effort to escape:** 90 min active + 8h passive + 45 min manual = ~3h active work
**Provenance:** Source: Velocity Specialist (critical path analysis) | Agreement: 5 specialists identified the sequencing dependency | Devil's Advocate: SURVIVES-TESTED

---

## What's About to Break

**The stagnation detection bug** — predicted to corrupt results within the first long optimizer run.

**Signals:** `evolve._last_improve` is never written (PROVEN by PoC #3). At generation 30, mutation rate escalates to 0.30 even if improving every generation. At generation 80, it hits 0.50 unconditionally. The 19-generation test run was too short to trigger this. The planned 8-hour run will reach 200+ generations.

**Preemptive fix:** Add 5 lines to `evolve.py` to write `_last_improve` when fitness improves. Effort: 5 min. Prevents: corrupted mutation rates across the entire overnight run.
**Provenance:** Source: Data-Integrity, Architecture | Execution: PROVEN (latent) | Devil's Advocate: WEAKENED on impact (zero effect on prior run), SURVIVES on correctness

**Hardcoded validation windows** will silently expire after Dec 2026.

**Signals:** `validation.py` `NAMED_WINDOWS` and `split_walk_forward` boundaries hard-stop at dates in 2026-2027. After those dates, walk-forward produces fewer windows, eventually none. No runtime warning.

**Preemptive fix:** Derive window boundaries from the dataset's actual date range, not hardcoded dates. Effort: 1h. Prevents: silent validation degradation 8 months from now.
**Provenance:** Source: Blind Spot Hunter BSH-09 (missed by all 5 specialists)

---

## You're Fighting the Wrong War

**Currently:** 100% of development effort (Apr 1-3) went to building optimizer infrastructure. 0% went to validating any result in TradingView.

**Wasted effort:** The 36-second evolve run, the 4x spike rewrite cycle, and the entire v4 architecture were built around an unvalidated claim. Not one minute was spent confirming whether RSI Regime actually performs in TradingView.

**Stop:** Building more optimizer infrastructure until current results are validated.
**Start:** Manual TradingView validation of the corrected top result. 15 minutes of manual work.
**Continue:** The v4 multi-strategy architecture is sound. The bugs are in parameters and wiring, not design.

**Provenance:** Source: Velocity Specialist | Data from git analysis (3 days of commits, 0 TradingView validations)

---

## The Playbook

### Fix Execution Order

```
Phase 0 — Quick Fixes (90 minutes, no dependencies):
  1. Fix montauk_821 EMA exit: 30-bar → 500-bar in strategies.py
     Effort: 1h | Status: Fix is a param addition + exit condition rewrite
  2. Fix RSI boundary: < to <= in strategies.py:133
     Effort: 5 min | Status: 1-character fix
  3. Fix stagnation detection: write _last_improve in evolve.py
     Effort: 5 min | Status: ~5 lines
  4. Implement exponential DD penalty: exp(-2.0*(DD/100)^2) in evolve.py
     Effort: 5 min | Status: Formula swap
  5. Fix exception swallowing: log + threshold halt in evolve.py:118
     Effort: 15 min | Status: Add logging, halt if >10% error rate

Phase 1 — Overnight Run (0 hours active):
  6. Run 8-hour optimizer with all Phase 0 fixes applied
     Review results next morning

Phase 2 — Evaluate and Decide (1 hour):
  7. Review overnight results: Is RSI Regime still #1?
  8. TradingView manual validation of top result (15 min)
  9. Decision gate: does the engine merge scope change?

Phase 3 — Test Infrastructure (4-8 hours, depends on Phase 2):
  10. Write integration tests for backtest_engine.py montauk_821
      These become the regression gate for the engine merge

Phase 4 — Engine Merge (1-2 weeks, depends on Phase 3):
  11. Merge engines (strategy_engine.py survives, per debate verdict)
  12. Port regime scoring, validation hooks, parity annotations
  13. Fix breakout state management bug as part of merge
  14. Run integration tests after each merge phase

Phase 5 — Deployment + Governance (3-5 days, depends on Phase 4):
  15. Generalize Pine Script generation for non-8.2.1 strategies
  16. Charter rewrite (Part A: describe reality; Part B: deployment gates)
  17. Update CLAUDE.md, archive dead code
```

### Tasks for Issue Tracker

#### Task 1: Fix montauk_821 Baseline (CRITICAL)
**Component:** `scripts/strategies.py`
**Problem:** EMA cross exit uses 30-bar medium EMA instead of 500-bar long EMA, making the baseline a fundamentally different strategy than Pine Script 8.2.1.
**Acceptance criteria:**
- [ ] `strategies.py` montauk_821 has a `long_ema` parameter defaulting to 500
- [ ] Exit condition compares `ema_s` against 500-bar EMA, not 30-bar
- [ ] `STRATEGY_PARAMS["montauk_821"]` includes `long_ema` with range (200, 600)
- [ ] Running evolve.py with corrected montauk_821 produces a different baseline fitness
**Why this task exists:** The 4.7x fitness ratio denominator is a crippled strategy. Every comparison is wrong.
**Provenance:** Source: Architecture F6, Risk R-02 | Agreement: 5/5 | Execution: PROVEN (PoC #1) | Devil's Advocate: SURVIVES-TESTED

#### Task 2: Implement Exponential Drawdown Penalty
**Component:** `scripts/evolve.py`
**Problem:** Linear penalty `1 - DD/200` lets a 75% drawdown strategy win with only 37.5% penalty.
**Acceptance criteria:**
- [ ] `dd_penalty = math.exp(-2.0 * (max_dd / 100) ** 2)` replaces the linear formula
- [ ] Remove the `max(0.3, ...)` floor — the exponential curve handles all ranges
- [ ] RSI Regime's fitness drops from ~2.18 to ~1.13 under the new formula
**Why this task exists:** The fitness function crowned a 75% drawdown strategy as the winner.
**Provenance:** Source: Risk R-10, Architecture addendum | Debate: Fitness-Drawdown — exponential formula recommended | Devil's Advocate: WEAKENED (exploration-phase argument) but core concern valid

#### Task 3: Fix Stagnation Detection
**Component:** `scripts/evolve.py`
**Problem:** `_last_improve` is read but never written. Mutation rate escalation is broken for runs >30 generations.
**Acceptance criteria:**
- [ ] `evolve._last_improve` is updated when a strategy's best fitness improves
- [ ] At generation 30 with continuous improvement, mutation rate stays at 0.15 (base)
- [ ] At generation 80 with no improvement since gen 50, mutation rate escalates to 0.50
**Why this task exists:** The 8-hour overnight run will reach 200+ generations and hit this bug.
**Provenance:** Source: Data-Integrity F10, Architecture addendum | Execution: PROVEN (PoC #3, latent)

#### Task 4: Fix RSI Boundary Condition
**Component:** `scripts/strategies.py:133`
**Problem:** `<` should be `<=` for RSI crossover detection to match Pine Script's `ta.crossover` behavior.
**Acceptance criteria:**
- [ ] RSI crossover uses `<=` not `<`
- [ ] When RSI exactly equals the threshold, a crossover is detected
**Provenance:** Source: Data-Integrity F3, Architecture addendum | Debate: RSI bar-shift debunked, boundary bug confirmed

#### Task 5: Wire Walk-Forward Validation to v4 Strategies
**Component:** `scripts/validation.py` + `scripts/evolve.py`
**Problem:** validation.py imports from backtest_engine only. It cannot validate any v4 strategy.
**Acceptance criteria:**
- [ ] A `validate_v4()` function exists that accepts strategy_engine-style parameters
- [ ] evolve.py can invoke walk-forward validation on its best result
- [ ] RSI Regime can be validated with walk-forward before any deployment decision
**Why this task exists:** The entire v4 pipeline produces unvalidated results. This is the single most impactful blocker.
**Provenance:** Source: Architecture, Risk, Data-Integrity, Velocity (4/5) | Execution: PROVEN (PoC #4) | Devil's Advocate: SURVIVES-TESTED

#### Task 6: Merge Backtest Engines
**Component:** `scripts/strategy_engine.py` (survivor), `scripts/backtest_engine.py` (deprecated)
**Problem:** Two engines with incompatible APIs, different exit logic, no cross-validation.
**Acceptance criteria:**
- [ ] strategy_engine.py includes regime scoring from backtest_engine.py
- [ ] All strategies (including montauk_821) run through a single engine
- [ ] Parity annotations from backtest_engine.py preserved in comments
- [ ] Integration tests pass before and after merge
- [ ] backtest_engine.py moved to archive/
**Why this task exists:** Root cause of 9+ downstream findings. Every specialist flagged this.
**Provenance:** Source: All 5 specialists | Debate: Engine Merge — strategy_engine.py survives with phased parity gates | Devil's Advocate: SURVIVES-TESTED

### Questions for the Team

1. **Is the gentle drawdown penalty intentional for exploration?**
   The exponential penalty will eliminate high-drawdown strategies from the leaderboard. On TECL (a 3x leveraged ETF), 40-60% drawdowns are common even for good strategies. Is the current gentle penalty a deliberate choice to see the full frontier, or an oversight?
   **Why this matters:** If intentional, the exponential penalty may be too aggressive and should be tunable. If an oversight, apply it immediately.
   **Provenance:** Risk R-10, Devil's Advocate counter-argument

2. **Should the Charter govern Python research or only Pine deployment?**
   The Charter's language is scoped to Pine Script edits. spike.md explicitly contradicts it. Is this a governance gap or an intended separation of concerns?
   **Why this matters:** Determines whether RSI Regime is a Charter violation that should be flagged, or a legitimate discovery that the Charter never intended to restrict.
   **Provenance:** Vision-Drift F1-F5, Devil's Advocate counter-argument

3. **Is the v4 architecture (strategy_engine.py + evolve.py) permanent or a prototype?**
   If permanent, it needs the full engine merge, test suite, and validation wiring (2-4 weeks). If a prototype that will be replaced, the quick fixes alone (90 minutes) are sufficient.
   **Why this matters:** The scope of Phase 3-5 depends entirely on this answer.
   **Provenance:** Velocity Specialist (convergence vs churn analysis), Second-Order Thinker

---

## ⚖️ Contested Findings

### ⚖️ Charter: Update or Enforce?

**One view (Vision-Drift):** The Charter is dead letter describing a project that no longer exists. The project has evolved from Pine Script editing to Python strategy discovery. Update the Charter to match reality.

**Counter view (Risk):** The Charter's guardrails are financially sound. The RSI Regime result (75% DD, unvalidated) proves exactly why the mean-reversion ban and deployment gates were needed. Enforce the Charter.

**Debate result:** Split verdict. Update the description (Vision-Drift wins). Preserve the deployment gates (Risk wins). The deepest insight: "Updating the Charter to rubber-stamp unvalidated results is as dangerous as pretending the Charter still governs anything."

**Reader decision:** Both are needed. But do not update the Charter until the engine merge settles the architecture — documenting a system that is about to change is premature.

### ⚖️ Which Engine Survives the Merge?

**One view (Architecture):** strategy_engine.py has better abstractions (pluggable strategies, cached indicators, generic backtest loop). Port regime scoring and validation from backtest_engine.py.

**Counter view (Data-Integrity):** backtest_engine.py is the only TradingView-validated engine. It contains parity annotations. Porting introduces regression risk.

**Debate result:** Architecture wins on direction (strategy_engine.py survives). Data-Integrity wins on execution (phased merge with parity gates at each phase). Three critical porting risks identified: exit priority order, equity-aware exits, warmup divergence.

**Reader decision:** Proceed with strategy_engine.py as survivor, but write integration tests against backtest_engine.py's behavior BEFORE starting the merge. Those tests become the regression gate.

---

## Project Health Score

| Dimension | Score | Trend | Biggest drag | Source |
|---|---|---|---|---|
| Architecture quality | 35/100 | → | Dual engine schism | Architecture Specialist |
| Velocity / Friction | 40/100 | ↓ | Optimization illusion loop | Velocity Specialist |
| Risk posture | 20/100 | ↓ | Unvalidated 75% DD strategy crowned winner | Risk Specialist |
| Vision alignment | 30/100 | ↓ | Charter frozen 31 days, project evolved past it | Vision-Drift Specialist |
| Fix durability | 15/100 | → | Zero tests; 4x rewrite pattern | Velocity Specialist |
| **Overall** | **28/100** | **↓** | | Composite |

---

## Comparison to Last Report

**First run.** No prior report exists. This establishes the baseline.

---

# PART 2: THE EVIDENCE

---

## The Root Cause

**The root cause:** strategy_engine.py was created as a fresh implementation rather than extending backtest_engine.py. This single architectural decision cascades into 9+ downstream findings.

**What it explains:** Dual engine divergence, validation disconnect, crippled baseline, indicator boundary bugs, incompatible BacktestResult types, incompatible parameter names, missing regime scoring in v4, pine generation bottleneck.

**Evidence chain:** The connections graph identifies this as Cluster A's root node. All 5 specialists independently traced their primary findings back to this decision. The debate confirmed strategy_engine.py should survive, but the split created the structural fracture.

**Agreement:** 5/5 specialists' findings trace to this root cause.

#### How to fix
**The structural change:** Engine merge — port regime scoring, validation, and parity annotations from backtest_engine.py into strategy_engine.py. Deprecate backtest_engine.py.
**Effort:** 1-2 weeks | **Downstream savings:** eliminates all dual-engine findings (~30% of total findings) | **ROI:** 2 weeks work prevents recurring class of integration bugs
**Fix status:** VALIDATED by debate (phased approach with parity gates). HIGH regression risk without tests.

---

## Full Findings with Provenance — Sorted by Priority Score

---

### 1. VERDICT: RSI Regime's 4.7x Superiority Is a Triple Illusion

**Confidence: 99% | CONVERGENT (5/5) | PROVEN**
**Priority Score: 18.0**

The claim "RSI Regime is 4.7x better than 8.2.1" is structurally invalid. The denominator (montauk_821 baseline) uses a 30-bar EMA instead of the production 500-bar EMA — a completely different strategy. The numerator (RSI Regime) has 75% max drawdown, 12 trades, and 75% win rate from a 36-second in-sample-only run exploring 2.7% of the parameter space. The validation framework cannot reach v4 strategies. The actual superiority of RSI Regime is unknown — estimated 1.0-2.5x after corrections, but genuinely uncertain until the baseline is fixed and walk-forward validation is wired in.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Architecture F6 | montauk_821 uses 30-bar EMA not 500-bar | Code-cited: strategies.py:34 |
| Risk R-02 | Wrong EMA exit, 30-bar vs 500-bar | Code-cited: strategies.py:74 vs backtest_engine.py:618 |
| Data-Integrity F1 | montauk_821 missing 6+ features from v3 | Code-cited: strategies.py:26-78 |
| Risk R-03 | RSI Regime: 75% win, 12 trades, 75.1% DD | Data-cited: evolve-results-2026-04-03.json |
| Velocity F8 | 2.7% of parameter space explored | Calculated from search ranges vs evaluations |
| Debate Chamber | 4.7x is a triple illusion: crippled baseline + insufficient search + in-sample only | Debate: RSI Regime Illusion |
| Execution Agent | PROVEN — 30-bar vs 500-bar confirmed in code | PoC: poc-ema-exit.py |
| Devil's Advocate | SURVIVES-TESTED. Corrected meta-synthesis stat error (75% win, not 100%) | DA report §2 |

### Confidence Breakdown
- Base (CONVERGENT, 5 sources): 70
- Debate survived (RSI Regime Illusion): ×1.3 → 91
- Execution PROVEN (PoC #1 + #2): ×1.5 → 136 (capped at 99)
- Calibration (first run): ×1.0
- Code-cited: ×1.2
- **Final: 99%**

### Why This Exists (Succession of Explanations)

**Explanation 1 (60%):** Premature celebration of a proof-of-concept run. The 36-second evolve run was a test of the v4 architecture. RSI Regime's 4.7x result was automatically written to best-ever.json and treated as a real finding.
*Fix if correct:* Fix the baseline, re-run, validate properly.

**Explanation 2 (25%):** Confirmation bias. Three days of infrastructure work needed a payoff. RSI Regime was the first answer to "what beats 8.2.1?" Questioning it meant questioning the entire v4 pivot.
*Fix if correct:* Same technical fixes, but also establish a process: no result is "real" until walk-forward + TradingView parity.

**Explanation 3 (15%):** Structural incentive in the fitness function. Gentle drawdown penalty + broken stagnation detection systematically produces high-variance, few-trade strategies as winners.
*Fix if correct:* Exponential DD penalty + stagnation fix.

### Fix Plan

**Recommended fix (assumes Explanation 1):** Fix montauk_821 baseline (1h), fix DD penalty (5min), run overnight optimizer (8h passive), validate top result in TradingView (15min manual).
**Effort:** Small (<1 day active)
**Risk of fix:** Low — the fixes are independent point changes with no interaction risk.

### Lifecycle Status

**Status:** NEW
**Finding ID:** ARG-2026-001

---

### 2. VERDICT: The Charter Is Dead Letter — But Its Guardrails Were Right

**Confidence: 96% | CONVERGENT (3/5) | DEBATE-RESOLVED**
**Priority Score: 13.5**

The Montauk Charter has not been updated in 31 days. It describes a single-strategy EMA-trend system. The codebase implements a 7-strategy discovery platform. spike.md explicitly contradicts Charter Section 2 (oscillator ban) and Section 8 (mean-reversion ban). RSI Regime violates both sections. No flagging occurred. However, the Charter's deployment gates (TradingView parity, validation requirements) are financially sound — the RSI Regime result proves exactly why those gates were needed.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Vision-Drift F1-F5 | 14 specific drift points mapped Charter vs codebase | Code-cited: Charter S2, S5, S8 vs strategies.py, spike.md |
| Architecture F4 | RSI Regime contradicts Charter identity | Code-cited: Charter S2 vs strategies.py RSI Regime function |
| Risk addendum CROSS-03 | All 7 governance layers have bypasses | Inference from cross-specialist analysis |
| Debate Chamber | Split verdict: update description, preserve gates | Debate: Charter Governance |
| Devil's Advocate | SURVIVES-TESTED with nuance (Charter may only govern Pine edits) | DA report §7 |

### Confidence Breakdown
- Base (CONVERGENT, 3 sources): 70
- Debate survived (split verdict, defender won on gates): ×1.2 → 84
- Not executed: ×1.0
- Calibration: ×1.0
- Code-cited: ×1.2 → 100 (capped at 99, adjusted to 96 for split verdict nuance)
- **Final: 96%**

### Fix Plan

**Recommended fix:** Two-part Charter rewrite. Part A: update project description to reflect multi-strategy Python discovery platform. Part B: preserve and strengthen deployment gates (walk-forward required, max DD cap, TradingView parity before any deployment).
**Do not fix until:** The engine merge settles the architecture (don't document a system that is about to change).
**Effort:** Medium (1-2 days)
**Risk of fix:** Low — document change, no code impact.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-002

---

### 3. VERDICT: Zero Automated Tests on 4,387 Lines of Financial Code

**Confidence: 78% | CONVERGENT (3/5)**
**Priority Score: 13.5**

Zero test files, zero test framework imports, zero CI configuration across 4,387 lines of Python that make financial calculations. The EMA cross exit bug survived 8 strategy versions. Five bugs were found and fixed on Apr 3 with zero regression protection. The parity_check.py script is a real manual verification tool (Devil's Advocate caught this — the project is not devoid of correctness concern), but it only covers one engine and is not automated.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Architecture F10 | Zero tests, zero CI, direct push to main | Code-cited: no test_*, no pytest.ini, no .github/ |
| Risk R-05 | 0 tests across 4,387 lines | Diagnostic: find + grep for test patterns |
| Velocity F4 | 5 bugs found in 3 days with 0 regression protection | Git-cited: Apr 1-3 commit history |
| Devil's Advocate | WEAKENED: parity_check.py exists as manual verification | DA report §6 |

### Fix Plan

**Recommended fix:** Write integration tests for backtest_engine.py's montauk_821 behavior BEFORE the engine merge. These tests become the regression gate for the merge.
**Priority test targets:** (1) Cross-engine parity: montauk_821 in strategies.py vs backtest_engine.py produce same trades. (2) EMA exit: confirm 500-bar EMA is used. (3) Walk-forward: validate_candidate produces expected pass/fail for known configs.
**Effort:** Medium (4-8 hours)

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-003

---

### 4. VERDICT: Stagnation Detection Is Broken — Will Corrupt the Overnight Run

**Confidence: 82% | REINFORCED | PROVEN (latent)**
**Priority Score: 13.5**

`evolve._last_improve` is read at line 234 but never written anywhere in the file. The mutation rate escalation mechanism is broken: `stag = generation - 0 = generation` always. At generation 30, mutation rate jumps to 0.30 even if improving every generation. At generation 80, it hits 0.50 unconditionally. The bug had zero impact on the 19-generation test run but will corrupt any run lasting 30+ generations — including the planned 8-hour overnight run.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Data-Integrity F10 | _last_improve never assigned | Code-cited: evolve.py:234 |
| Architecture addendum | Confirmed independently | Code-cited |
| Execution Agent | PROVEN (latent — zero impact on 19-gen run) | PoC: poc-stagnation.py |
| Devil's Advocate | WEAKENED on impact (gen 19 < threshold) | DA report §9 |

### Fix Plan

**Fix:** Add `if not hasattr(evolve, '_last_improve'): evolve._last_improve = {}` initialization and `evolve._last_improve[strat_name] = generation` when best fitness improves.
**Effort:** Small (5 minutes, ~5 lines)

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-004

---

### 5. VERDICT: Two Backtest Engines With Zero Integration

**Confidence: 99% | CONVERGENT (5/5) | DEBATE-RESOLVED**
**Priority Score: 12.0**

backtest_engine.py (980 lines, validated against TradingView) and strategy_engine.py (534 lines, better architecture) implement overlapping but incompatible logic. Zero cross-imports. Different data structures (StrategyParams dataclass vs plain dicts). Different exit evaluation (strategy_engine pre-computes signals without position awareness; backtest_engine evaluates exits within position context). Different parameter names (`short_ema` vs `short_ema_len`). Results from one engine cannot be validated, compared, or consumed by the other.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| All 5 specialists | Independent identification through different lenses | Code-cited: import graph analysis |
| Debate Chamber | strategy_engine.py survives, phased merge with parity gates | Debate: Engine Merge |
| Devil's Advocate | SURVIVES-TESTED (zero cross-imports confirmed) | DA report §1 |
| Financial Auditor | "Two books of record with no reconciliation" | Alien critic AE-01 |
| Safety Engineer | "Two altimeters reading different values" | Alien critic SF-01 |
| Compiler Writer | "Two execution models implementing different contracts" | Alien critic IF-01 |

### Confidence Breakdown
- Base (CONVERGENT, 5 sources): 70
- Debate survived (engine merge): ×1.3 → 91
- Not directly tested by execution agent: ×1.0
- Code-cited: ×1.2 → 109 (capped at 99)
- **Final: 99%**

### Fix Plan

**Recommended fix:** Merge engines. strategy_engine.py survives (debate verdict). Port regime scoring, validation hooks, and parity annotations from backtest_engine.py. Phased approach with integration tests as regression gate.
**Effort:** Large (1-2 weeks)
**Risk of fix:** HIGH — largest code change, highest integration risk, on a zero-test codebase. Write tests (Task 3) before starting.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-005

---

### 6. VERDICT: Validation Framework Cannot Reach v4 Strategies

**Confidence: 99% | CONVERGENT (4/5) | PROVEN**
**Priority Score: 12.0**

validation.py imports `StrategyParams, BacktestResult, run_backtest` from backtest_engine. It cannot import from strategy_engine. evolve.py never imports from validation. No bridge function exists anywhere in the codebase. The disconnect is three-layered: import layer (zero cross-imports), type layer (StrategyParams vs plain dicts), name layer (different parameter key names). Walk-forward validation is well-built and completely useless for the strategies that need it most.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Architecture F1 | Walk-forward cannot validate v4 | Code-cited: validation.py imports |
| Risk R-08 | "Walks forward only on the strategy that needs it least" | Code-cited |
| Data-Integrity F4 | Structurally disconnected | Code-cited |
| Velocity addendum Cross-3 | "#1 velocity blocker for entire project" | Inference from critical-path analysis |
| Execution Agent | PROVEN — three-layer disconnect confirmed | PoC: poc-validation-disconnect.py |
| Devil's Advocate | SURVIVES-TESTED (zero bridge code exists) | DA report §3 |

### Fix Plan

**Short-term (if engine merge deferred):** Write a `validate_v4()` adapter function that translates strategy_engine dicts to StrategyParams. ~50 lines. Effort: 2 hours.
**Long-term:** Engine merge makes this unnecessary — validation works for all strategies automatically.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-006

---

### 7. VERDICT: montauk_821 in strategies.py Is a Different Strategy Than Pine 8.2.1

**Confidence: 99% | REINFORCED | PROVEN**
**Priority Score: 12.0**

strategies.py `montauk_821()` uses `ema_m` (30-bar medium EMA) for the cross exit. Pine Script 8.2.1 and backtest_engine.py both use 500-bar long EMA. The STRATEGY_PARAMS for montauk_821 has no `long_ema` parameter at all — the function literally cannot produce the correct exit behavior. Additionally, montauk_821 lacks 6+ features of the production strategy: TEMA entry filters, sideways market filter, sell confirmation window, trailing stop, TEMA slope exit, and cooldown logic.

### Evidence Package

| Source | Claim | Evidence Quality |
|--------|-------|-----------------|
| Architecture F6 | 30-bar vs 500-bar discrepancy | Code-cited: strategies.py:34 vs backtest_engine.py:36 |
| Risk R-02 | Wrong EMA exit confirmed | Code-cited: strategies.py:74 |
| Execution Agent | PROVEN — code-level proof, no ambiguity | PoC: poc-ema-exit.py |
| Devil's Advocate | SURVIVES-TESTED (no counter-evidence, not even a comment suggesting intentional simplification) | DA report §4 |

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-007

---

### 8. VERDICT: Pine Script Generation Has No Path for Non-8.2.1 Strategies

**Confidence: 76% | CONVERGENT (4/5)**
**Priority Score: 9.0**

generate_pine.py's PARAM_MAP only contains 8.2.1 entries. Six of seven strategies in the optimizer have no automated deployment path. The hand-written RSI Regime Pine file exists in `src/strategy/testing/` (Devil's Advocate caught this — manual translation works), but the manual process already introduced a boundary condition bug (< vs <=), proving the error risk is not theoretical.

### Fix Plan

**Recommended fix:** Template-based Pine generation system. One template per strategy architecture. Effort: 3-5 hours.
**Do not fix until:** After the engine merge determines the final strategy API.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-008

---

### 9. VERDICT: Fitness Function Rewards Catastrophic Risk

**Confidence: 72% | REINFORCED | DEBATE-RESOLVED**
**Priority Score: 9.0**

The linear drawdown penalty `max(0.3, 1.0 - DD/200)` gives a 75% drawdown only a 37.5% penalty. A 75% drawdown requires a 300% gain to recover. The 0.3 floor means even a total wipeout only gets a 0.7x penalty. The debate resolved this: implement `exp(-2.0 * (DD/100)^2)` which maps 30% DD → 0.835x, 50% DD → 0.607x, 75% DD → 0.325x. The Devil's Advocate raised a legitimate counter-argument: the gentle penalty may be an intentional exploration-phase choice. The exponential formula preserves the full frontier while creating meaningful selection pressure.

**Second-order concern:** On TECL (3x leveraged ETF), drawdowns above 40% are common for any strategy that holds through corrections. The exponential penalty could inadvertently favor ultra-conservative strategies that underperform buy-and-hold. Sanity-check buy-and-hold's own drawdown score under the new formula before deploying it.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-009

---

### 10. VERDICT: Dead Code Competes With Living Code

**Confidence: 84% | CONVERGENT (4/5)**
**Priority Score: 6.0**

1,819 lines (39%) of the Python codebase is dead or partially dead. spike_auto.py (601 lines) has a different fitness function, writes to the same best-ever.json, and is still documented in CLAUDE.md. signal_queue.json is orphaned. A future Claude session could invoke the wrong system. This is not just clutter — it is "an alternative reality that competes with the current one" (Velocity addendum).

### Fix Plan

**Fix:** Archive spike_auto.py, signal_queue.json, and stale files to `archive/`. Update CLAUDE.md simultaneously. Must be paired — never archive files without updating docs that reference them.
**Effort:** Small (30 minutes)

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-010

---

### 11. VERDICT: Breakout Strategy Has Cross-Trade State Contamination

**Confidence: 84% | CONVERGENT (3/5)**
**Priority Score: 6.0**

The breakout strategy's `peak_since_entry` is not properly reset between trades. Trailing stop calculations can fire on stale peak values from a previous trade. The bug is real but not decision-material — breakout ranks #2 at fitness 0.50, far below RSI Regime. Fix as part of the engine merge.

### Lifecycle Status
**Status:** NEW | **Finding ID:** ARG-2026-011

---

## Moderate Confidence Findings (40-75%)

### 12. Regime Scoring Thresholds Miscalibrated for 3x ETF (60%)

The 30% bear threshold in `detect_bear_regimes()` was designed for equity indices. TECL is a 3x leveraged ETF that experiences routine 30-50% corrections during normal bull market pullbacks. The threshold may classify too many periods as "bear," inflating bear avoidance scores for strategies that simply exit during normal volatility. Source: Data-Integrity F6, Architecture addendum. Priority Score: 4.0.

### 13. RSI Boundary Condition Bug: < vs <= (60%)

strategies.py line 133 uses `<` where Pine Script's `ta.crossover` uses `<=`. When RSI exactly equals the entry threshold, Python misses the crossover. Source: Data-Integrity F3. Confirmed by debate (bar-shift debunked, boundary bug confirmed). 1-character fix. Priority Score: 4.0.

### 14. Composite Oscillator Orphaned (60%)

The oscillator was designed as a companion to the EMA-trend strategy. If RSI Regime becomes production, the oscillator's components (TEMA, Quick EMA, MACD, DMI) measure the wrong things. Low urgency — only matters when a deployment decision is imminent. Source: Architecture F11, Vision-Drift F14. Priority Score: 3.0.

---

## Suspected (Unconfirmed) — Confidence < 40%

These findings have insufficient evidence from the specialist layer to confirm, but warrant attention.

1. **Silent exception swallowing in evolve.py** — 36% confidence. Single specialist (Risk R-04). However, independently flagged by both the Airline Safety Engineer (SF-03) and Financial Auditor (AE-03). The `except Exception: return 0.0, None` pattern silently discards all errors. If 30% of candidates crash, the optimizer thinks 30% of the search space is empty. *What to look for:* Add `logging.exception()` in the catch block and run the optimizer — check if any exceptions are being swallowed.

2. **Same-bar entry/exit cooldown suppression in v4** — 36%. Single specialist (Data-Integrity F11). The strategy_engine processes exits and entries on the same bar, which can cause a sell+buy on the same bar when cooldown=0. *What to look for:* Check if any v4 strategy uses cooldown=0 and produces same-bar round trips.

3. **No deployment guardrails** — 36%. Single specialist (Risk R-07). No automated validation gate between optimizer output and TradingView deployment. The single checkpoint is a human copy-paste step. *What to look for:* Consider adding a `--validate` flag to generate_pine.py that runs walk-forward before producing Pine output.

4. **Bear avoidance defaults to 1.0 in bear-free windows** — 36%. Single specialist (Data-Integrity F13). When no bear period exists in a validation window, `bear_avoidance` defaults to 1.0, adding a free 0.5 to the composite regime score. *What to look for:* Check validation windows that happen to exclude all bear periods.

5. **Parity check tolerances too wide (10-30%)** — 36%. Single specialist (Data-Integrity F5). parity_check.py tolerances are wide enough to mask a systematic 1-bar exit shift. *What to look for:* Tighten tolerances to ±5% and see what fails.

6. **CLAUDE.md 40% stale content** — 36%. Single specialist (Velocity F9). Documents v1-v3 workflows that no longer exist. *What to look for:* Cross-reference CLAUDE.md sections against actual file existence.

7. **Fitness function changed 3 times in 3 days** — 36%. Single specialist (Velocity F10). Each change invalidated all prior results. *What to look for:* Ensure the fitness function is stable before any long optimizer run.

8. **Yahoo Finance API fragility** — 36%. Single specialist (Risk R-12). Single request, no retry, spoofed User-Agent, generic exception catch. *What to look for:* Run with a network interruption and see if it fails gracefully.

---

## What I Need to Know (30-Minute Interview List)

These are questions the codebase cannot answer. A 30-minute conversation with the developer would resolve them.

1. **Was the 30-bar EMA in montauk_821 intentional?** — resolves whether this is a simplification bug or a deliberate parameter choice for faster optimizer convergence.
   *Why it matters:* If intentional, the "crippled baseline" narrative changes to "alternative baseline" and the fix approach changes.

2. **Is the v4 architecture permanent or a prototype?** — resolves the scope of the engine merge (2 weeks vs not needed).
   *Why it matters:* The entire Phase 3-5 playbook depends on this. If v4 is a prototype that will be replaced, only the quick fixes matter.

3. **Is the gentle drawdown penalty a deliberate exploration choice?** — resolves whether to apply the exponential formula immediately or make it configurable.
   *Why it matters:* The exponential penalty will eliminate high-drawdown strategies. On TECL, this may be too aggressive.

4. **What is the deployment timeline?** — resolves priority of Pine generation generalization vs optimizer correctness.
   *Why it matters:* If deployment is months away, optimizer fixes matter more. If deployment is days away, the manual Pine translation + TradingView validation is the critical path.

5. **Has RSI Regime been manually tested in TradingView?** — resolves whether the strategy has any real-world validation beyond the Python backtest.
   *Why it matters:* If yes, the crippled baseline is less urgent (the strategy works regardless of how it was found). If no, the 4.7x claim has zero external validation.

---

## What Argus Knows vs. Suspects vs. Doesn't Know

### High Confidence (> 75%)

| Finding | Confidence | Evidence Level |
|---------|-----------|----------------|
| RSI Regime 4.7x is wrong | 99% | PROVEN (PoC #1 + #2) |
| Dual engine schism | 99% | 5/5 convergent, debate-confirmed |
| Validation disconnected from v4 | 99% | PROVEN (PoC #4) |
| montauk_821 wrong EMA (30 vs 500) | 99% | PROVEN (PoC #1) |
| Charter is dead letter | 96% | 3/5 convergent, debate split verdict |
| Dead code (39% / 1,819 lines) | 84% | 4/5 convergent, quantified |
| Breakout state contamination | 84% | 3/5 convergent |
| Stagnation bug (latent) | 82% | PROVEN (PoC #3) |
| Zero automated tests | 78% | 3/5 convergent, DA weakened |

### Moderate Confidence (40-75%)

| Finding | Confidence | What would increase confidence |
|---------|-----------|-------------------------------|
| Pine gen only supports 8.2.1 | 76% | Attempting to generate non-8.2.1 Pine and measuring error rate |
| Fitness under-penalizes DD | 72% | Running optimizer with exponential penalty, comparing leaderboard |
| Regime scoring thresholds miscalibrated | 60% | Testing with TECL-appropriate thresholds (e.g., 50% bear threshold) |
| RSI boundary condition bug | 60% | Running both < and <= variants, comparing trade count/timing |
| Composite oscillator orphaned | 60% | Confirming via deployment decision (does it serve any strategy?) |

### Suspected (< 40%)

See Suspected section above. 8 findings with < 40% confidence.

### Investigated and Ruled Out

| Hypothesis | Tested By | Result |
|-----------|-----------|--------|
| EMA indicator divergence between engines | Execution Agent PoC #5 | **DISPROVEN** — bit-identical output. The divergence is in parameters (30 vs 500), not math. |
| Stale CSV data (39 days old) | Devil's Advocate | **KILLED** — CSV extends through Apr 1, 2026 (2 days stale). Filename is misleading. |
| RSI calculation bar shift (np.diff prepend) | Debate: RSI Regime Illusion | **DISPROVEN** — delta array is correctly aligned. No bar shift. |
| 4x spike rewrite is waste/churn | Cross-pollination (all specialists) | **REVISED** — convergence pattern, not waste. Each version contracted scope. Dead code left behind is the real problem. |

### Not Investigated

- **Runtime performance** — no profiling data. Unknown whether the 36-second evolve run was CPU-bound or I/O-bound.
- **Pine Script execution model fidelity** — parity_check.py exists but only for 8.2.1. No systematic verification of the Pine Script execution model assumptions (order processing, bar timing).
- **Historical data quality** — the CSV is assumed correct. No cross-validation against a second data source (e.g., Alpha Vantage, Polygon.io).
- **Leveraged ETF decay modeling** — prices embed leverage decay, but regime scoring thresholds may need adjustment for 3x products.
- **Actual TradingView performance of any v4 strategy** — zero TradingView validation has been performed for any strategy discovered by the v4 optimizer.

### Cannot Determine from Code Alone

See Interview List above. Developer intent, deployment timeline, and the permanence of the v4 architecture require human input.

---

## What Happens If You Fix Everything

*From the Second-Order Thinker's analysis.*

### Fix Interaction Map

| Fix A | Fix B | Interaction |
|-------|-------|-------------|
| F1 (engine merge) | F6 (validation port) | F6 is SUBSUMED by F1. Do not do F6 independently. |
| F1 (engine merge) | F2 (EMA fix) | F2 is only needed if F1 is deferred. The merge uses backtest_engine's validated logic. |
| F5 (DD penalty) | F15 (optimizer run) | Hard dependency. F5 invalidates all prior fitness scores. Must run AFTER. |
| F1 (engine merge) | F8 (Charter update) | F8 should come AFTER F1. Don't document an architecture about to change. |
| F7 (archive dead code) | F14 (CLAUDE.md update) | Must be done together. Never archive files without updating docs. |

**Safe to parallelize:** F3 (RSI boundary), F4 (stagnation), F5 (DD penalty), F7 (archive), F12 (data), F13 (exceptions) — all independent point fixes.

### Minimum Intervention Set (3 fixes for 80% of value)

1. **F2: Fix montauk_821 EMA** — makes all comparisons trustworthy
2. **F5: Exponential DD penalty** — prevents catastrophic-risk strategies from winning
3. **F4: Fix stagnation detection** — makes the overnight run work as designed

These three can be applied in 90 minutes, followed by the overnight run. The results inform whether the full engine merge (2 weeks) is even necessary.

### Ordering Constraints

```
F2, F3, F4, F5 ──→ F15 (overnight run) ──→ Phase 2 decision gate
F10 (tests) ──→ F1 (engine merge) ──→ F6, F9, F8 (all subsumed/dependent)
F7 + F14 together (archive + docs)
```

### Collective Assessment

**The codebase improves substantially.** The fixes eliminate a genuine structural fracture, correct a misleading metric, harden the optimization process, and create a validation path that did not exist.

**The trade-off:** Stability for correctness. The current codebase is wrong but stable. The fix set introduces 2-4 weeks of active development during which the codebase is in flux. The quick fixes (Phase 0) deliver 70-80% of the value in 90 minutes. The remaining 20-30% (engine merge, tests, governance) is a multi-week project.

**The single biggest risk:** Attempting the engine merge (F1) without writing tests first (F10), introducing integration bugs that take longer to find than the original bugs.

**Do the quick fixes. Run the optimizer. Read the results. Then decide how deep to go.**

---

# PART 3: TRANSPARENCY

---

## Domain-Alien Analysis

These findings come from critics with orthogonal professional frames. They are presented separately because they represent a different mode of analysis.

### From the Financial Auditor

**AE-01: Two Books of Record** — Two backtest engines producing incompatible results that flow into the same best-ever.json without reconciliation controls. Material weakness. [DOMAIN-CONVERGENT with SF-01, IF-01]

**AE-02: Fitness Function Fragmentation** — Three different fitness functions (spike_auto, evolve, validation) with different criteria. A parameter set can be "fit" under one and unfit under another. Significant deficiency. [DOMAIN-CONVERGENT with IF-02]

**AE-03: Non-Reproducible, Non-Auditable Optimization** — Only the winning candidate survives. Losing candidates discarded. No random seed saved. Results cannot be verified after the fact. Deficiency.

**AE-04: Uncontrolled Data Pipeline** — No checksum on CSV. No overlap validation at Yahoo merge point. No data quality checks. Significant deficiency.

**AE-05: Zero Transaction Cost Modeling** — Both Pine and Python model zero slippage on a 3x leveraged ETF with 100% equity position sizing. Backtest returns systematically overstated. [BLIND-SPOT — missed by all 5 specialists]

### From the Airline Safety Engineer

**SF-01: Silent Engine Divergence** — Two altimeters reading different values with no flag to the pilot. [DOMAIN-CONVERGENT with AE-01, IF-01]

**SF-02: Sideways Filter Blocks Crash Protection** — The ATR shock exit (the "crash-catcher") is suppressed during sideways periods. The Charter explicitly warns about this (line 28) but the code does not implement the backstop. Fail-catastrophic design. [BLIND-SPOT — partially. Specialists noted the sideways filter but not this specific failure cascade]

**SF-03: Exception Swallowing** — `except Exception: return 0.0, None` in both optimizers. If all evaluations throw, the optimizer sees all-zeros and runs forever producing nothing useful. No smoke in the cockpit.

**SF-04: No Bounds Checking on Generated Parameters** — Evolutionary operators can produce inverted EMA lengths, lookback periods exceeding data length, or structurally impossible configurations. evolve.py has NO enforce_constraints() function.

**SF-05: No Kill Switch or Circuit Breaker** — No convergence detection, no data-change detection during run, no concurrent access protection on best-ever.json.

**SF-06: Single Data Source** — All backtesting depends on one CSV + one API. No redundancy, no cross-validation.

### From the Compiler Writer

**IF-01: Two Execution Models** — backtest_engine computes exits within position context. strategy_engine pre-computes all signals without position awareness. These are fundamentally different execution models, not just different implementations. [DOMAIN-CONVERGENT with AE-01, SF-01]

**IF-02: Regime Score Measures Bar-Time, Not Dollar-Weighted Returns** — `score_regime_capture()` counts bars in/out of market, not returns captured/avoided. A strategy in 90% of bull bars but only during the flat consolidation phase scores 0.90 bull capture. The primary optimization target measures the wrong thing. [BLIND-SPOT — missed by all 5 specialists. Most significant blind spot in the analysis.]

**IF-03: StrategyParams.from_dict() Silently Drops Unknown Keys** — Parameter names differ between engines (`short_ema` vs `short_ema_len`). Cross-engine parameter flow silently drops all strategy-specific values, reverting to defaults. [BLIND-SPOT]

**IF-04: EMA Cross Exit Window Off-By-One Sensitivity** — Whether Python's backward scan matches Pine's `barssince` depends on a bar-alignment assumption that is not tested. Parity tolerances (10-30%) could mask a systematic 1-bar shift.

**IF-05: Equity Curve Updated Multiple Times Per Bar** — Bear depth guard reads stale equity values from earlier in the same bar's processing loop. [BLIND-SPOT]

**IF-06: Indicator Cache Keys Are Fragile** — String-based cache keys with no collision detection. Two strategies using the same key for different series get wrong cached data silently.

**IF-07: Bootstrap Test Measures Wrong Thing** — Shuffles trade return ORDER (tests compounding sensitivity) not entry/exit TIMING (tests strategy alpha). False confidence that timing is statistically significant.

### Domain Convergence

**[DOMAIN-CONVERGENT] DC-01: Two-Engine Divergence** (AE-01 + SF-01 + IF-01) — All three critics independently identified the dual-engine problem through different professional lenses. Highest-confidence finding in the alien analysis.

**[DOMAIN-CONVERGENT] DC-02: Silent Failure / Error Swallowing** (AE-03 + SF-03 + IF-03) — The system optimizes for producing output rather than producing correct output. Errors are invisible at every layer.

**[DOMAIN-CONVERGENT] DC-03: Sideways Filter Blocks Safety Exits** (Charter warning + SF-02) — A known, documented, unimplemented safety requirement.

**[DOMAIN-CONVERGENT] DC-04: Fitness Function Fragmentation** (AE-02 + IF-02) — Not only do the tools disagree on what "good" means, but the primary metric (regime score) measures the wrong thing (bar-count instead of economic participation).

### [BLIND-SPOT] Findings Specialists Missed Entirely

**BS-01: Regime Scoring Uses Bar-Time, Not Dollar-Weighted Returns** (IF-02, BSH-01) — The most significant blind spot. All 5 specialists discussed regime scoring without questioning whether its methodology is sound. Bar-time fraction is a crude proxy that can materially mislead the optimizer. This should be investigated before the overnight run.

**BS-02: Zero Slippage on Crisis Exits** (AE-05, BSH-06) — The ATR shock exit fires during extreme volatility when spreads widen most. Zero-friction modeling systematically overstates the exit that matters most for risk management. Over 19+ trades on a 3x leveraged ETF, this is material.

**BS-03: Parameter Name Mismatch Between Engines** (IF-03, BSH-02) — `short_ema` vs `short_ema_len`, `atr_mult` vs `atr_multiplier`. Results from evolve.py cannot be fed to backtest_engine.py without manual translation. Silent, complete parameter loss.

**BS-04: Bootstrap Test Measures Compounding, Not Timing** (IF-07) — False confidence metric. The test answers "does trade order matter?" not "does the strategy time entries/exits better than random?"

**BS-05: Equity Curve Stale Read in Bear Guard** (IF-05) — Subtle bar-processing ordering dependency.

---

## Red Team Analysis

The Red Team approached this codebase with adversarial intent. These findings represent exploitable leverage, not code quality concerns.

### Attack Surface

```
[TECL CSV] ──no integrity──→ data.py ──no validation──→ engines ──no tests──→ optimizer
[Yahoo API] ──no pinning──→                                                     ↓
                                                                        best-ever.json
                                                                    (no signing, no lock)
                                                                             ↓
                                                                    generate_pine.py
                                                                             ↓
                                                                  [Human copy-paste gate]
                                                                     (single checkpoint)
```

### Exploit Findings

| # | Target | Impact | Detection Risk | Vector |
|---|--------|--------|----------------|--------|
| CRITICAL-1 | **TECL CSV file** | Corrupts ALL backtests simultaneously | Very low — no checksums | Direct edit |
| CRITICAL-2 | **Yahoo API MITM** | Inject false recent prices affecting validation windows | Medium — requires network position | DNS spoof / proxy |
| CRITICAL-3 | **AI prompt injection via data files** | Hijack Claude to modify any script | Very low — looks like normal data | Embed instructions in signal_queue.json or best-ever.json |
| HIGH-1 | **Fitness function** | Optimizer converges on attacker-chosen strategy | Medium — code review catches | Modify scoring weights |
| HIGH-2 | **Validation windows** | Strategies pass that should fail | Medium — date changes visible | Shift NAMED_WINDOWS boundaries |
| HIGH-3 | **best-ever.json** | Bias all future optimizer runs | Low — file changes between runs | Write inflated regime_score |
| HIGH-4 | **Single manual gate** | Social-engineer the human copy-paste step | Low — convincing reports | Corrupt optimizer results upstream |
| MEDIUM-1 | **Regime thresholds** | Change what counts as bear/bull | Medium | Adjust bear_threshold |
| MEDIUM-2 | **Dual engine** | Strategy works in test, differs in production | High — engines differ by design | Exploit engine differences |
| MEDIUM-3 | **AI script permissions** | Claude can edit all Python scripts | Medium — requires prompt injection first | settings.json grants Write(/scripts/**) |

### [RED-TEAM-CONFIRMED] Findings

**Dual engine divergence** — appears in both specialist analysis (#1 finding) AND Red Team (MEDIUM-2). Exploitable because a strategy optimized against the simpler engine may behave differently when manually translated to Pine and run against the full engine's equivalent.

**Data pipeline integrity** — specialists flagged merge-point validation gaps; Red Team identified CSV poisoning as the #1 highest-value, lowest-detection-risk attack.

### Recommended Mitigations

1. SHA-256 checksum on CSV, verified on every load
2. Sanity bounds on Yahoo data (price > 0, high >= low, date continuity)
3. Schema validation on signal_queue.json (do not read as free-form AI input)
4. Cross-engine parity test (both engines, same config, assert results match)
5. Sign or re-verify best-ever.json scores
6. Fixed random seeds for reproducibility
7. Narrow Claude's write permissions on scripts/

---

## What Was Killed (and Why)

### Stale Data Pipeline (39 Days Old) — KILLED

**Source:** Risk R-06, Data-Integrity F8/F9
**Original claim:** CSV is from Feb 23, 39 days stale. evolve.py disables Yahoo refresh.
**Kill reason:** Devil's Advocate found the CSV data extends through April 1, 2026 (2 days stale, not 39). The filename is misleading but the data is current.
**Devil's Advocate evidence:** Read actual CSV content — last 3 rows: 2026-03-30, 2026-03-31, 2026-04-01.
**What would change the verdict:** If the CSV is not updated regularly, this finding resurrects. The secondary concern (no price continuity check at the merge point) remains a minor code quality issue.

### EMA Indicator Divergence Between Engines — DISPROVEN

**Source:** Meta-synthesis concern about indicator calculation differences
**Original claim:** EMA implementations may diverge between backtest_engine.py and strategy_engine.py.
**Kill reason:** Execution Agent PoC #5 ran both implementations on identical data. Max absolute difference: 0.000000000000000e+00. Numerically identical. Source code logic comparison: identical.
**What this means:** The divergence problem is in PARAMETERS (30-bar vs 500-bar), not in MATH. This is actually good news — fixing parameters is trivial; fixing algorithms would be hard.

---

## Specialist Dissent

### Data-Integrity vs Architecture — Engine Survival

**Data-Integrity thesis:** backtest_engine.py should survive (only validated engine, contains parity annotations).
**Challenge:** Architecture argued strategy_engine.py has better abstractions for multi-strategy future.
**Status:** Thesis rejected by debate verdict. strategy_engine.py survives.
**Reader note:** Data-Integrity's concern about porting regression risk is valid. Their proposed execution plan (phased merge with parity gates) was adopted by the debate as the HOW, even though their WHICH lost.

### Risk vs Vision-Drift — Charter Disposition

**Risk thesis:** Enforce the Charter's guardrails.
**Challenge:** Vision-Drift argued the Charter is dead letter.
**Status:** Split verdict — both partially correct.
**Reader note:** The synthesis (update description + strengthen gates) is the resolution. Neither pure enforcement nor pure update is correct.

---

## Argus Blind Spots

**What Argus v6 cannot analyze:**
- No runtime performance data (would need profiling)
- No real user behavior data (this is a single-developer system)
- No TradingView execution verification (would need TradingView API or manual testing)
- No real-money trading data (system has never been deployed with real capital)
- No network security assessment beyond code-level API analysis
- No load testing of the optimizer under long-duration runs
- Regime scoring methodology quality (bar-time vs dollar-weighted) was identified by the Blind Spot Hunter but not formally validated with test data
- No cross-validation of TECL price history against an independent data source

Any of these could be fine or could be where the worst problems hide.

---

## This Run

**Argus v6 — Project Montauk — Apr 04, 2026**

Specialists: 5 | Debates: 4 | Alien Critics: 3 | Execution PoCs: 5

**Findings:**
- PROVEN (execution confirmed): 4
- HIGH confidence (>75%): 9
- MODERATE confidence (40-75%): 5
- SUSPECTED (<40%): 8
- KILLED (disproven or counter-evidence): 2
- CONTESTED (resolved via debate): 2

**Red Team:** 10 exploit findings | 2 RED-TEAM-CONFIRMED

**World Model:** 11 new findings added to registry | 0 recurring | 0 resolved (first run)

**Top 3 by Priority Score:**
1. RSI Regime 4.7x Is Wrong — 18.0 — 99%
2. Charter Is Dead Letter — 13.5 — 96%
3. Zero Tests on Financial Code — 13.5 — 78%

**The one thing to fix first:** Fix the montauk_821 baseline EMA (30→500), apply the three other quick fixes, run the overnight optimizer. 90 minutes of active work produces the project's first trustworthy numbers.

**The most interesting discovery:** The Blind Spot Hunter and Compiler Writer independently found that regime scoring — the PRIMARY optimization target — measures bar-time overlap with regimes, not actual economic participation. A strategy that captures 90% of a bull run's bars but only the flat consolidation portion scores 0.90. All 5 specialists discussed regime scoring extensively without questioning whether it measures the right thing. This is the deepest blind spot in the analysis and should be investigated before treating any regime score as meaningful.

**The biggest uncertainty:** Is the v4 architecture permanent or a prototype? The answer determines whether the engine merge (2 weeks) is needed or whether the quick fixes (90 minutes) are sufficient. A 30-minute conversation resolves this.

---

*End of Argus v6 final report. All verdicts trace to specific specialist findings, debate transcripts, execution PoCs, or adversarial reports as cited. Finding IDs ARG-2026-001 through ARG-2026-011 registered for world model tracking.*
