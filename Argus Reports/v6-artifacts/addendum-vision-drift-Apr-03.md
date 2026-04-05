# Vision-Drift Addendum — Apr 03, 2026

**Specialist**: Vision-Drift
**Phase**: Cross-Pollination
**Inputs**: Digests from Architecture, Risk, Data-Integrity, Velocity; open questions from all specialists

---

## Part 1: Open Questions Answered

### Q1 (from others): ADX implementations differ materially?

**Vision-Drift perspective**: Yes, and this matters to my lens. Architecture found that `backtest_engine.py` uses running-sum Wilder's smoothing while `strategy_engine.py` uses `_rma()` on DX directly. From a vision-drift standpoint, the Charter (S4) specifies Pine Script v6 as the authoritative implementation language. Pine's `ta.adx()` uses Wilder's smoothing (RMA). If either Python engine diverges from Pine's ADX, the drift is not just between the two engines -- it is between the project's code and its constitutional reference implementation. The fact that neither engine has been parity-tested against Pine's ADX output means the Charter's implicit requirement ("code must match Pine behavior") is unverifiable for ADX-dependent strategies. This is a vision gap, not just a calculation gap.

### Q2 (from others): process_orders_on_close match Python?

**Vision-Drift perspective**: The Charter (S4) mandates `process_orders_on_close=true`, which means Pine fills orders at the current bar's close, not the next bar's open. Risk found that `strategy_engine.py` processes exits before entries on the same bar (lines 538-556). Whether this matches `process_orders_on_close` semantics depends on whether the Python engine fills at `close[i]` or `open[i+1]`. I did not read the backtest loop line-by-line (noted as a coverage gap in my original findings). However, from a vision-drift standpoint: the Charter specifies this as a coding rule, not a guideline. If Python fills at a different price than Pine, every optimization result is running against a different market than TradingView sees. The Charter's authority on execution semantics is absolute and unambiguous -- this is one area where the Charter is NOT stale.

### Q3 (from others): TECL leverage decay modeled?

**Vision-Drift perspective**: The Charter's "Known trade-offs" section explicitly acknowledges TECL's 3x daily-reset volatility drag and states "the system's job is to maximize time in strong trends and minimize chop exposure." The Charter does NOT require the Python engine to model leverage decay explicitly -- it treats it as a known property of the instrument that the strategy design accounts for implicitly (by avoiding chop). Neither Python engine models daily leverage reset. This is consistent with the Charter's framing. However, Data-Integrity's finding that the regime scoring uses a 30% bear threshold (appropriate for unleveraged instruments, not 3x ETFs) reveals a gap: the Charter's awareness of leverage decay did not translate into the regime scoring implementation. The Charter should have specified TECL-appropriate thresholds.

### Q4 (from others): Will 8-hour run change rankings?

**Vision-Drift perspective**: Irrelevant to my lens in isolation, but critical through it. The spike.md skill describes 8-hour overnight runs targeting 500,000+ evaluations. The Apr 3 run was 1,330 evaluations in 54 seconds. If an 8-hour run produces a different winner (not RSI Regime), then the current Charter crisis -- "do we update the Charter to accommodate mean-reversion?" -- may resolve itself. If EMA-based strategies win at scale, the Charter stays valid. If RSI Regime or another non-EMA strategy wins at scale AND passes walk-forward validation, the Charter must update. The answer to the Charter question depends on this run happening. **Recommendation: do NOT update the Charter until a full-duration run with walk-forward validation completes.**

### Q5 (from others): Is rewrite pattern convergence or indecision?

**Vision-Drift perspective**: Velocity found 4 full rewrites in 3 days. From the vision-drift lens, each rewrite expanded the project's identity further from the Charter: v1 (optimize 8.2.1 params) -> v2 (add regime scoring) -> v3 (automated overnight loop) -> v4 (multi-strategy discovery platform). Each iteration was a deliberate expansion of scope. This is convergence toward a different project than the Charter describes, not indecision about how to build the Charter's project. The rewrites are not circling -- they are climbing a ladder away from the original identity. The direction is consistent even if the implementation keeps changing.

### Q6 (mine): Is the RSI paradigm shift deliberate or unconscious?

**Answer: Deliberate at the tactical level, unconscious at the constitutional level.**

Evidence for deliberate: spike.md v4 explicitly says "Use ANY combination. There are no restrictions on what indicators or logic you can use." This was a conscious decision to open the search space. The RSI Regime strategy was not an accident -- it was the intended output of a system designed to find non-EMA strategies.

Evidence for unconscious at the constitutional level: The Charter was never consulted, amended, or even referenced during the transition. There is no commit, no comment, no document that says "We are overriding Charter S8 because..." The spike.md skill was written as if the Charter did not exist. The developer did not consciously decide to violate the Charter -- they simply forgot it was there, or treated it as a historical document rather than a governing one.

**Verdict**: The paradigm shift was a deliberate engineering decision wrapped in an unconscious governance failure. The developer knew they were opening the search space. They did not realize (or did not care) that this contradicted their own Charter. This is the most common pattern in vision drift: the exciting work outruns the boring documentation.

### Q7 (mine): Should the Charter update, or should the code rein in?

**Answer: The Charter should update. But not yet, and not unconditionally.**

Reasoning:

1. **The Charter's core insight is still valid.** "Capture multi-month bull legs and exit swiftly on regime change" is a sound investment thesis for TECL regardless of what indicators implement it. RSI Regime, if it works, does exactly this -- it enters when RSI signals a regime bottom and rides the subsequent bull. The THESIS is intact even if the IMPLEMENTATION has changed.

2. **The Charter's guardrails failed for a reason.** The mean-reversion ban (S8) was written when the project had one strategy and one developer editing Pine Script by hand. In that context, "don't add mean-reversion" is a good guardrail against scope creep. But in a multi-strategy discovery platform, banning entire categories of strategies defeats the purpose of the platform. The guardrail was designed for a different architecture.

3. **However, the RSI Regime result is unvalidated.** Risk, Data-Integrity, and Architecture all converge on this: 100% win rate, 10 trades, 75% DD, no walk-forward, disconnected validation, wrong EMA baseline in the comparator. Updating the Charter to accommodate a strategy that may be overfitted would be premature. The Charter should not be rewritten to celebrate a result that hasn't survived scrutiny.

4. **Recommended path**: 
   - Freeze the Charter as-is until RSI Regime (or any non-EMA winner) passes walk-forward validation with a properly implemented 8.2.1 baseline.
   - If validation passes: write Charter v2 that preserves the investment thesis (long TECL, capture trends, avoid bears) but replaces the implementation constraints (EMA-only, no oscillators) with an open-architecture framework and a validation gate.
   - If validation fails: the Charter was right all along, and the code should be reined in to EMA-variant strategies only.

---

## Part 2: Revised Scores

Cross-pollination with other specialists' findings changes the severity and confidence of several of my original findings.

### Finding 2 (Charter S8 Violated) -- Confidence RAISED from 98% to 99%

Risk's discovery that montauk_821 in strategy_engine uses the wrong EMA (30 vs 500) means the RSI Regime's 4.7x fitness advantage is against a broken baseline. The Charter violation is real, but the MAGNITUDE of the violation is overstated. RSI Regime may not actually be 4.7x better than real 8.2.1. This paradoxically increases my confidence that the violation matters -- if the comparison is invalid, the justification for overriding the Charter ("but the results are so good!") collapses.

### Finding 7 (Two Backtesting Engines) -- Severity RAISED from 90% to 97%

All five specialists flagged this. Architecture provided the most detailed evidence. Risk found the wrong-EMA bug that proves the engines diverge materially, not just theoretically. Data-Integrity confirmed 6 missing features in the v4 montauk_821. This is not a potential problem -- it is an active, confirmed, consequential fracture.

### Finding 9 (RSI Overfitting Red Flags) -- Severity RAISED from 85% to 95%

Risk's quantification (75% DD, 10 trades, 100% win rate) and Data-Integrity's finding that RSI calculation diverges from Pine (np.diff prepend issue) compound the overfitting risk. The RSI Regime winner is not just unvalidated -- it may be producing different signals than the Pine Script version would. The overfitting concern is no longer speculative; it is structural.

### Finding 3 (Metrics Silently Replaced) -- Severity RAISED from 95% to 97%

Architecture confirmed that the two engines use fundamentally different fitness functions (regime_score vs vs_bah_multiple), and Risk confirmed the two "best-ever" records are incompatible. The metric drift is not just a documentation problem -- it means the project has two contradictory definitions of "best" that cannot be reconciled without deciding which engine is authoritative.

### Finding 6 (TradingView Backtesting Clause Obsolete) -- No change (90%)

Confirmed by all specialists but no new information that changes severity.

### Finding 11 (Dead Code) -- Confidence RAISED from 90% to 95%

Velocity's quantification (39% dead code, 1,819 lines) is more precise than my original estimate. Architecture identified the exact confusion vector (Claude sessions could invoke spike_auto.py instead of evolve.py). Risk flagged it as a deployment hazard. The convergence is definitive.

### Finding 14 (Composite Oscillator Orphaned) -- No change (85%)

No other specialist examined the oscillator. This remains a unique vision-drift finding without corroboration or contradiction.

---

## Part 3: Cross-Lens Findings

These findings emerge only from combining my vision-drift analysis with other specialists' discoveries.

### Cross-Finding 1: The Charter Cannot Self-Correct Because Its Enforcement Mechanism Is Broken

**Source lenses**: Vision-Drift (F4: Charter is frozen) + Architecture (F1: dual engines) + Risk (R-08: validation disconnected)

The Charter was supposed to be enforced through a chain: Charter defines rules -> code follows rules -> validation checks code -> parity confirms TradingView match. Every link in this chain is broken:

- The Charter defines EMA-trend rules; the code uses RSI mean-reversion. (Vision-Drift F2)
- The validation framework (validation.py) cannot reach the code that needs validating (strategy_engine.py). (Architecture F1, Risk R-08)
- The parity checker only validates 8.2.1, not the strategies that actually need checking. (Vision-Drift F8)
- CLAUDE.md (the living spec) evolved 7 times; the Charter (the constitution) evolved 0 times. (Vision-Drift F4)

The result is a governance vacuum. The Charter exists but has no mechanism to influence the code. The code evolved but has no mechanism to update the Charter. Neither document has a trigger that says "when these diverge, stop and reconcile." This is not just stale documentation -- it is a failed feedback loop.

**Proposed fix**: Add a "Charter Compliance Gate" to the spike.md skill. Before any strategy is promoted from evolve.py to `testing/`, require: (1) walk-forward validation passes, (2) parity check against TradingView passes, (3) either the strategy conforms to the Charter OR a Charter amendment is written and committed. This makes the Charter a living gate rather than a dead document.

### Cross-Finding 2: The 4.7x Fitness Gap Is a Triple Illusion

**Source lenses**: Vision-Drift (F2: RSI Regime violates Charter) + Risk (R-02: wrong EMA baseline) + Data-Integrity (F1: v4 montauk_821 missing 6 features) + Data-Integrity (F3: RSI calc diverges from Pine)

The claim that "RSI Regime is 4.7x better than 8.2.1" is built on three compounding errors:

1. **The baseline is a strawman.** The v4 montauk_821 is missing 6 features (sideways filter, TEMA filters, sell confirmation, trailing stop, TEMA slope exit, volume spike exit) AND uses the wrong EMA for its cross exit (30-bar instead of 500-bar). This is not 8.2.1 -- it is a crippled approximation. Real 8.2.1 likely scores significantly higher. (Risk R-02, Data-Integrity F1)

2. **The winner's signals are wrong.** The RSI calculation uses `np.diff(series, prepend=series[0])` which shifts the delta array by one index relative to Pine's implementation. For a strategy with only 10-12 trades, shifting entry timing by even 1 bar changes the trade list. The Pine Script version of RSI Regime may produce entirely different trades. (Data-Integrity F3)

3. **The evaluation is in-sample only.** No walk-forward validation, no out-of-sample testing, only 1,330 evaluations in 54 seconds. A proper evaluation requires the validation infrastructure that is disconnected from the v4 engine. (Risk R-03, Data-Integrity F4)

The 4.7x number is the ratio of an inflated winner to a deflated baseline, measured by a metric that has never been validated against reality, on a dataset that was never split for out-of-sample testing. The actual superiority of RSI Regime over properly-implemented 8.2.1 is unknown. It could be 4.7x. It could be 0.7x.

**Why this matters to vision-drift**: The entire case for updating the Charter rests on "RSI Regime is so much better that the mean-reversion ban should be lifted." If the 4.7x number is illusory, the case for updating the Charter evaporates. This is why I recommend freezing the Charter until validated results exist (see Q7 above).

### Cross-Finding 3: spike.md Is Now the De Facto Charter

**Source lenses**: Vision-Drift (F4: Charter frozen, F13: ambiguity enables drift) + Velocity (F3: 4 rewrites in 3 days) + Architecture (F4: Charter violation)

The Montauk Charter has 0 commits since initial import. spike.md has had 7 modifications in 3 days. CLAUDE.md has had 7 commits. The Charter defines scope, strategy identity, coding rules, and evaluation metrics. spike.md overrides all four:

| Charter says | spike.md says | Who wins? |
|---|---|---|
| EMA-trend system | "Use ANY combination" | spike.md |
| No oscillators/countertrend | "No restrictions on what indicators" | spike.md |
| Pine Script v6 only | "Claude writes Python strategy functions" | spike.md |
| Backtest in TradingView | "Python tests them overnight" | spike.md |
| MAR as risk-adjusted return | vs_bah_multiple as fitness | spike.md (via evolve.py) |

spike.md is a 4-day-old skill file that has replaced a governance document without any formal process. Every Claude session reads spike.md as its operational instructions. No Claude session reads the Charter unless explicitly told to. spike.md is the de facto constitution of Project Montauk.

**This is not necessarily wrong.** spike.md may describe the better project. But the project now has two contradictory constitutions, and the one that actually governs behavior is the one with no version history, no rationale sections, no validation windows, and no guardrails. The Charter's strengths (explicit trade-offs, stress-test windows, parameter philosophy) were lost in the transition.

**Proposed fix**: Either (a) promote spike.md to a formal "Charter v2" by adding the governance sections it lacks (scope boundaries, validation requirements, what constitutes a deployable winner), or (b) add a preamble to spike.md that explicitly states "This skill operates under the Montauk Charter with the following exceptions: [list]." Either approach restores the link between operational instructions and governance.

### Cross-Finding 4: The Project Has an Unstated Phase Transition

**Source lenses**: Vision-Drift (F1: identity metamorphosis) + Velocity (F3: 4 rewrites) + Architecture (F3: dead code from superseded architectures)

Reading across all five specialists' findings, a pattern emerges that no single lens captured: the project underwent a phase transition around April 1-3 from "strategy editing" to "strategy discovery." This is not incremental drift -- it is a qualitative change in what the project IS:

| Before Apr 1 | After Apr 1 |
|---|---|
| Pine Script is the code | Python is the code; Pine is the deployment target |
| One strategy (8.2.1) with tunable params | Seven strategy architectures competing |
| Manual backtesting in TradingView | Automated backtesting with 500K+ eval target |
| Charter governs | spike.md governs |
| "How do we tune 8.2.1?" | "What beats 8.2.1?" |
| Editing | Discovering |

Phase transitions are normal in projects. What is abnormal is that the governance, validation, and quality infrastructure did not transition with it. The Charter, validation.py, parity_check.py, generate_pine.py, and the Composite Oscillator all belong to the pre-transition project. The post-transition project inherited them but cannot use them.

**Proposed fix**: Acknowledge the phase transition explicitly. Write a one-paragraph "Project Phase" section in CLAUDE.md that says: "As of April 3, Project Montauk is in Discovery Phase. The Charter governs the investment thesis and deployment constraints. spike.md governs the discovery process. Strategies discovered in this phase must pass [validation gate] before being promoted to production, at which point the Charter's coding rules (S4) and evaluation metrics (S6) apply."

---

## Manifest

| File | Purpose |
|------|---------|
| `Argus Reports/v6-artifacts/findings-vision-drift-Apr-03.md` | Original findings (14 items) |
| `Argus Reports/v6-artifacts/addendum-vision-drift-Apr-03.md` | This document -- cross-pollination addendum |
