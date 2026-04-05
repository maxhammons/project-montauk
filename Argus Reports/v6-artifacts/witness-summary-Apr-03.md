# Witness Summary — Apr-03

## Artifacts Reviewed

| Artifact | Status | Size |
|---|---|---|
| scratchpad-architecture-Apr-03.md | Read in full | 11.4K |
| scratchpad-risk-Apr-03.md | Read in full | 5.5K |
| scratchpad-data-integrity-Apr-03.md | Read in full | 8.8K |
| scratchpad-vision-drift-Apr-03.md | Read in full | 6.8K |
| scratchpad-velocity-Apr-03.md | Read in full | 6.7K |
| findings-*-Apr-03.md (all 5) | Not yet produced | N/A |

**Note**: All 5 specialist scratchpads were available for review. No findings files had been written at time of evaluation. This summary evaluates scratchpad quality only. If findings files are produced later, a follow-up witness pass should review them.

---

## Per-Specialist Quality Scores

| Specialist | Depth (1-5) | Independence (1-5) | Rigor (1-5) | Coverage (%) | Notes |
|---|---|---|---|---|---|
| Architecture | 5 | 4 | 5 | 95% | Catalogued 57 non-reference files with specific signals. 23+ running observations with file/line references. Hypothesis confidence trajectories tracked. Identified 3 EMA implementations. Minor overlap with Risk on dual-engine schism. |
| Risk | 5 | 4 | 5 | 90% | Read all 12 Python files, active Pine, Charter. 6 hypotheses with specific confidence scores. Found Breakout strategy cross-contamination bug and montauk_821 EMA cross exit fidelity bug (ema_m vs ema_long). Counted error handlers (4). |
| Data-Integrity | 4 | 3 | 4 | 80% | Read ~45/88 files. 23 running observations. Good catches on RSI warmup divergence, bear regime 30% threshold bias, CAGR denominator overestimation, and equity curve double-update. Some hypotheses overlap heavily with Risk and Architecture. |
| Vision-Drift | 5 | 5 | 5 | 85% | 14 hypotheses, all with evidence trails back to Charter section numbers. Strongest independence score — only specialist to systematically compare every Charter section against actual codebase behavior. Found Charter S8 violation, metric drift, Python blind spot in coding rules. |
| Velocity | 4 | 4 | 4 | 85% | Git log analysis, commit timelines, churn rates, dead code percentages all quantified. Good "39% dead code" metric. Spike rewrite lifecycle analysis (7 mods in 3 days, ~10hr lifespan each) is unique to this lens. |

---

## Groupthink Incidents

### 1. Dual Backtesting Engine Schism (ALL 5 specialists)
Every specialist flagged the `backtest_engine.py` vs `strategy_engine.py` split as a primary finding. This is valid convergence on a real structural problem, but the sheer unanimity means no specialist offered a contrarian view (e.g., "the duplication is intentional and healthy for a rapid-prototyping phase"). The convergence is data, not noise, but the lack of any devil's advocate weakens the finding.

### 2. RSI Regime Overfitting (4 of 5: Risk, Architecture, Data-Integrity, Velocity)
Four specialists flagged the RSI Regime winner as overfitted (100% win rate, 10 trades, 75% DD, 0.01-hour search). Vision-Drift did not directly flag overfitting but noted the Charter violation. Again, this is valid convergence. The risk is that the finding is stated 4 times without any specialist attempting to actually TEST the hypothesis (e.g., run a walk-forward validation or compute the degrees-of-freedom ratio).

### 3. Dead Code / spike_auto.py Orphaned (4 of 5: Architecture, Risk, Data-Integrity, Velocity)
Four specialists flagged spike_auto.py (601 lines) as dead code. Velocity provided the most useful quantification (39% dead code ratio). The others merely noted its existence.

### 4. Parity Gap Growing (4 of 5: Architecture, Risk, Data-Integrity, Velocity)
Four specialists noted the Python-TradingView parity gap (34.9% vs 31.19% CAGR) and that v4 strategies have zero parity validation. Vision-Drift covered this indirectly via H10 and H11. Convergence is justified but no specialist quantified the expected magnitude of the gap for RSI Regime specifically.

### 5. generate_pine.py Only Maps 8.2.1 (3 of 5: Architecture, Data-Integrity, Vision-Drift)
Three specialists noted this. Vision-Drift added the most value by noting that CLAUDE.md's claim of "ready-to-paste Pine Script" is aspirational for non-8.2.1 strategies.

**Assessment**: The groupthink is largely justified -- these are genuine structural issues. However, the repeated flagging without differentiated analysis means findings will feel redundant in the debate chamber. Recommend the moderator force each specialist to contribute UNIQUE evidence or a UNIQUE angle on shared findings rather than re-stating the same observation.

---

## Lens Bleed Incidents

### 1. Data-Integrity into Architecture
The Data-Integrity scratchpad devotes significant space to "TWO SEPARATE BACKTEST ENGINES" (observation #1), duplicate code structures, and dead code analysis (observations #2, #4). These are architectural concerns, not data integrity concerns. The specialist should have focused on whether the CALCULATIONS in each engine are correct, not whether having two engines is architecturally problematic. Coverage of actual numerical correctness (RSI warmup, CAGR denominator, bear regime thresholds) was good but diluted by the architecture commentary.

### 2. Data-Integrity into Velocity
The Data-Integrity manifest tags run_optimization.py, spike_auto.py, spike_state.py, and signal_queue.json as "dead-code" -- this is a velocity/churn concern, not a data integrity one. The specialist should have asked "does this dead code produce incorrect data if accidentally invoked?" rather than just "is this dead?"

### 3. Risk into Architecture
The Risk scratchpad's H1 ("dual-engine divergence") and observations #1-2 are architecturally framed. The risk framing ("will produce catastrophically wrong decisions") is appropriate for the Risk lens, but the analysis of cross-imports and code organization bleeds into Architecture territory.

### 4. Architecture into Vision-Drift
The Architecture scratchpad observation #4 ("Charter explicitly says 'EMA-trend system' — RSI Regime violates this") is a clean vision-drift finding presented inside the architecture manifest. This was a minor bleed since it appeared as a single observation rather than a developed hypothesis.

**Assessment**: The most significant bleed is Data-Integrity spending effort on architectural taxonomy rather than numerical verification. The specialist's unique value is checking whether calculations are correct, and some of that potential was spent re-discovering structural issues that Architecture had already catalogued more thoroughly.

---

## Coverage Metrics

| Specialist | Files Read | Total Files | Coverage | Skipped Categories |
|---|---|---|---|---|
| Architecture | 57 | 88 | 65% (all non-reference) | Pine v6 reference docs (30), .DS_Store (11) -- appropriate exclusions |
| Risk | ~35 | 88 | 40% | Focused on Python source + active Pine + results files. Skipped archived Pine scripts and reference docs. Appropriate for risk lens. |
| Data-Integrity | ~45 | 88 | 51% | Skipped Pine reference docs and .DS_Store. Read CSV metadata. |
| Vision-Drift | ~33 | 88 | 38% | Read Charter, CLAUDE.md, spike.md, all Python sources, key Pine scripts. Skipped archived Pine (reasonable -- Charter compliance doesn't require reading v1.0). Some files noted as "first 50/100 lines" only. |
| Velocity | ~20 | 88 | 23% | Relied heavily on git log analysis rather than file reading. Read all Python sources in full. Skipped Pine scripts entirely (appropriate for velocity lens). |

**Notes on Coverage**:
- No specialist read the full Pine Script v6 reference docs (30 files, ~210K tokens). This is correct -- they are reference material, not project code.
- Architecture had the best raw coverage with a complete 57-file manifest.
- Vision-Drift's partial file reads (e.g., "backtest_engine.py first 100 lines", "spike_auto.py first 50 lines") are a minor concern. For drift analysis you need to understand what the file DOES, but 100 lines of a 990-line file is only 10%.
- Velocity's lower file count is offset by deep git log analysis which is appropriate for the lens.

---

## Depth Assessment

### Architecture: EXEMPLARY
- 57-file manifest with per-file signal classification (RED FLAG / INTERESTING / TRIVIAL / CLEAN)
- 5 hypotheses with confidence trajectories
- 23+ running observations with specific file/line references
- Correctly identified THREE separate EMA implementations (not just two)
- Caught the Indicators cache key type mismatch (tuple key with int vs float)

### Risk: EXEMPLARY
- 6 hypotheses, all with specific confidence scores and evidence
- Found two genuine bugs: (1) Breakout strategy cross-contamination via stateful peak_since_entry, (2) montauk_821 in strategies.py uses ema_m (30-bar) instead of ema_long (500-bar) for cross exit
- Counted all 4 exception handlers and classified each
- Correctly noted validation.py cannot validate v4 strategies

### Data-Integrity: GOOD
- 23 running observations, most with specific technical detail
- Good unique catches: RSI np.diff warmup vs Pine SMA warmup, CAGR denominator overestimation, bear regime 30% threshold sensitivity for 3x ETF
- Weaker on follow-through: identified potential CSV issues (change_pct unvalidated, no split-adjustment check) but did not attempt to verify
- Lost some depth budget on architectural observations outside its lane

### Vision-Drift: EXEMPLARY
- 14 hypotheses, each mapped to specific Charter sections (S3, S4, S5, S6, S7, S8)
- Strongest independence -- the only specialist whose findings are not restatements of other specialists
- Key unique finding: Charter S8 scope guardrails are DIRECTLY violated by RSI Regime (mean-reversion / countertrend)
- Caught that Charter is stale (H14) -- no other specialist framed it this way
- Phase gate self-check at the end shows process discipline

### Velocity: GOOD
- Strong quantitative analysis: 39% dead code, 7 spike.md modifications in 3 days, ~10hr version lifespan
- Good git forensics: 5 active days out of 31, burst pattern identified
- The "100:0 build-to-maintain ratio" is a sharp framing
- Could have gone deeper on which files changed together (co-change analysis) and whether any commit introduced regressions

---

## Process Recommendations for Next Run

### 1. Enforce Lens Boundaries More Strictly
Data-Integrity spent ~30% of its scratchpad on architectural observations. In the next run, the specialist prompt should explicitly state: "Do not comment on code organization or dead code. Your job is to verify CALCULATIONS are correct."

### 2. Require At Least One Contrarian Hypothesis Per Specialist
All 5 specialists converged on the same top-3 findings. Require each specialist to propose at least one hypothesis that contradicts the consensus (e.g., "The dual-engine split is actually beneficial because..." or "RSI Regime may NOT be overfitted because..."). This prevents groupthink from producing a monoculture of findings.

### 3. Incentivize Unique Findings
Vision-Drift was the standout because nearly all its findings were unique to its lens. Architecture and Risk produced excellent work but with significant overlap. Consider scoring specialists on the DELTA they add beyond what other specialists found.

### 4. Require Executable Verification for Top Hypotheses
Four specialists flagged RSI Regime overfitting. None attempted to run the validation tools that already exist in the codebase (`python3 scripts/run_optimization.py validate`). The next run should require specialists to attempt verification of their top hypothesis before writing findings.

### 5. Track Findings File Production
At the time of this review, all 5 scratchpads were complete but 0 findings files existed. Either the specialists are still working or they stalled between scratchpad and findings. The witness should be scheduled to run AFTER findings are expected, not concurrently.

### 6. Standardize Confidence Scoring
Risk uses specific decimals (0.85, 0.92). Architecture uses percentages (95%, 85%). Vision-Drift uses percentages. Data-Integrity uses percentages. Velocity uses percentages. Minor inconsistency but should be standardized.

### 7. First-Run Calibration Note
This is Argus run #1 for Project Montauk (per calibration context). The breadth-first approach was appropriate. Future runs should use this witness summary to calibrate: Vision-Drift and Architecture delivered the highest value per token. Data-Integrity should be instructed to stay in its lane. Risk and Architecture should coordinate to avoid duplicate findings on the engine schism.
