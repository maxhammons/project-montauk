# Devil's Advocate Report -- Apr 03, 2026

**Author**: Devil's Advocate Agent
**Purpose**: Actively seek counter-evidence against the top 10 findings in the Argus v6 meta-synthesis priority stack rank. Each finding is challenged with adversarial investigation of the actual codebase.
**Method**: For each finding, identify what evidence would disprove it, search for that evidence, and render a verdict.

---

## Finding #1: Dual Engine Schism (Score: 36)

**Claim**: Two backtesting engines (backtest_engine.py and strategy_engine.py) with no cross-imports, creating structural fracture.

**Counter-evidence sought**: Any import between the two engines, any shared abstraction layer, any wrapper that unifies them.

**Investigation**:
- `grep` for cross-imports found: `backtest_engine.py` is imported by `validation.py`, `parity_check.py`, `generate_pine.py`, `run_optimization.py`, `spike_auto.py`. `strategy_engine.py` is imported by `strategies.py` and `evolve.py`. Zero cross-imports between the two engines.
- No shared module, no common base class, no adapter pattern.
- They define different data structures: `backtest_engine.py` uses `StrategyParams` dataclass with 30+ fields; `strategy_engine.py` uses `BacktestResult` with a different shape and `Indicators` class.
- `strategy_engine.py` has zero regime scoring code. `backtest_engine.py` has `detect_bear_regimes()` and `score_regime_capture()` -- neither of which can be reached from the v4 path.

**Counter-evidence found**: None.

**Verdict**: **SURVIVES-TESTED**. The schism is exactly as described. Two entirely separate worlds with zero integration points.

---

## Finding #2: RSI Regime Unreliable Winner (Score: 36)

**Claim**: The 4.7x fitness claim rests on a crippled baseline, in-sample-only evaluation, and insufficient search (36 seconds, 2.7% of parameter space).

**Counter-evidence sought**: Evidence that the 4.7x is real -- e.g., the baseline is actually faithful, the win stats are better than claimed, or there is some out-of-sample validation.

**Investigation**:
- **The 4.7x number checks out**: `evolve-results-2026-04-03.json` shows RSI Regime at fitness 2.1803, montauk_821 at 0.4556. Ratio = 4.79x. Confirmed.
- **The crippled baseline is confirmed**: `strategies.py` montauk_821 uses `ema_m` (default 30-bar) for the EMA cross exit (line 74: `ema_s[i] < ema_m[i] * (1 - ...)`). Pine Script 8.2.1 uses `emaLong` (500-bar). This is a 30-bar vs 500-bar discrepancy. The entire exit behavior is different.
- **Meta-synthesis cites "100% win / 10 trades"** but actual results show 75% win / 12 trades / 75.1% max DD. This is a factual error in the meta-synthesis (likely citing a different run or a specialist's mistake), but the core argument still holds: the result is unvalidated.
- **No out-of-sample validation exists**: `validation.py` imports from `backtest_engine`, not `strategy_engine`. No code path can validate RSI Regime.
- **Walk-forward was never run**: `evolve.py` runs pure in-sample. No `validation.py` call exists in the v4 code path.

**Counter-evidence found**: The meta-synthesis's specific numbers (100% win / 10 trades) are wrong -- actual data shows 75% win / 12 trades. However, this does NOT weaken the finding; it slightly changes the severity profile (75% DD with 75% win rate is still dangerous, and the core argument about crippled baseline + no validation is independently confirmed).

**Verdict**: **SURVIVES-TESTED** on the core claim. Minor factual correction: the meta-synthesis cites "100% win / 10 trades" which does not match the actual results file (75% win / 12 trades). The underlying argument is unaffected.

---

## Finding #3: Validation Framework Disconnected from v4 Strategies (Score: 36)

**Claim**: validation.py cannot validate v4 strategies because it imports from backtest_engine, not strategy_engine.

**Counter-evidence sought**: Any code path that connects validation to strategy_engine, evolve.py, or strategies.py. Any validate function that accepts generic strategies.

**Investigation**:
- `validation.py` line 16: `from backtest_engine import StrategyParams, BacktestResult, run_backtest`
- Zero imports from `strategy_engine` or `strategies` in validation.py.
- `validate_candidate()` (line 192) takes `StrategyParams` objects -- a backtest_engine type. It cannot accept the dict-based params used by strategy_engine.
- `evolve.py` never imports from `validation.py`.
- There is no `validate_v4()` or equivalent function anywhere in the codebase.

**Counter-evidence found**: None.

**Verdict**: **SURVIVES-TESTED**. The disconnect is structural and absolute. validation.py is physically incapable of reaching v4 strategies.

---

## Finding #4: montauk_821 Wrong EMA Exit -- 30-bar vs 500-bar (Score: 24)

**Claim**: The montauk_821 function in strategies.py uses a 30-bar EMA for the cross exit instead of the 500-bar long EMA used by Pine Script 8.2.1.

**Counter-evidence sought**: Evidence that the 30-bar usage is intentional, or that some other mechanism compensates for it.

**Investigation**:
- Pine Script 8.2.1 (line 20): `longEmaLen = input.int(500, ...)` and the exit uses `emaLong` (line 157-158).
- `backtest_engine.py` (line 36): `long_ema_len: int = 500` and exit uses `ema_long` -- matches Pine.
- `strategies.py` montauk_821 (line 34): `ema_m = ind.ema(p.get("med_ema", 30))` and exit (line 74): `ema_s[i] < ema_m[i] * (1 - ...)`. Uses the 30-bar medium EMA, not the 500-bar long EMA.
- The `STRATEGY_PARAMS` for montauk_821 (line 358) defines `med_ema: (15, 60, 5, int)` -- range 15-60. There is no `long_ema` parameter at all.
- There is no 500-bar EMA anywhere in strategies.py. The function literally cannot produce the correct exit behavior.

**Counter-evidence found**: None. Not even a comment suggesting the simplification was intentional.

**Verdict**: **SURVIVES-TESTED**. The 30-bar vs 500-bar discrepancy is unambiguous. The strategies.py montauk_821 is a fundamentally different strategy from Pine 8.2.1. This directly poisons the baseline used to calculate the 4.7x claim.

---

## Finding #5: Fitness Function Under-Penalizes Catastrophic DD (Score: 18)

**Claim**: Linear penalty `1 - DD/200` is too gentle; 75% DD gets only a 0.625x penalty.

**Counter-evidence sought**: Evidence that the penalty is sufficient, or that additional guards exist elsewhere.

**Investigation**:
- Confirmed formula: `dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)` (evolve.py line 62)
- At 75.1% DD: `1.0 - 75.1/200 = 0.6245`. RSI Regime's vs_bah of 3.49 becomes `3.49 * 0.6245 = 2.18`. A 75% drawdown (which requires 300% to recover) receives only a 37.5% penalty.
- The `max(0.3, ...)` floor means even 100% DD only gets a 0.5x penalty (and is clamped to 0.3x). A total wipeout strategy could still score 0.3x * vs_bah.
- There is a minimum trade count guard (`num_trades < 3` returns 0.0), but no maximum drawdown guard.
- **Possible counter-argument**: The fitness function is a discovery tool, not a deployment gate. Gentle penalties let you see the full frontier. The human reviews output and decides what is acceptable. This is a legitimate design philosophy for an exploration phase.

**Counter-evidence found**: Partial. The design-intent argument (gentle penalty for exploration) has merit, and `spike.md` explicitly says there are "no restrictions." However, the finding's core concern is valid: the function ranks a 75% DD strategy as the #1 winner with no warning flag.

**Verdict**: **WEAKENED** slightly. The fitness function may be intentionally exploratory. However, the meta-synthesis's specific concern -- that it crowned RSI Regime as the undisputed winner despite catastrophic risk -- is factually correct. The penalty is objectively gentle by any quantitative finance standard.

---

## Finding #6: Zero Test Coverage (Score: 27)

**Claim**: Zero tests across ~4,387 lines. No CI, no automated regression protection.

**Counter-evidence sought**: Any test file, any unittest/pytest import, any CI configuration, any automated check.

**Investigation**:
- `find` for `test_*`, `*_test.py`, `tests/` directories: zero results.
- `grep` for `unittest`, `pytest`, `assert`: found only 1 assertion in data.py (column existence check, line 116). No test frameworks imported anywhere.
- No `.github/`, no `Makefile`, no `tox.ini`, no `pytest.ini`, no CI config of any kind.
- **parity_check.py exists** as a manual validation script. It compares Python backtest output against hardcoded TradingView reference numbers. This IS a form of testing, but it is not automated, not in a test framework, and only covers backtest_engine (not strategy_engine).
- **validation.py** is a walk-forward validation framework. This IS a form of anti-overfitting check, but it only works for backtest_engine strategies and must be manually invoked.

**Counter-evidence found**: `parity_check.py` and `validation.py` are testing-adjacent tools that demonstrate the developer values correctness. They are not zero effort -- they are deliberately built verification mechanisms. However, they are manual, single-engine, and have no regression protection.

**Verdict**: **WEAKENED** marginally. The claim "zero tests" is technically accurate (no test framework, no CI, no automated regression suite). But characterizing it as a complete absence of correctness concern is unfair. `parity_check.py` is a real validation tool; it just doesn't scale and can't reach v4. The finding should say "zero automated tests; manual validation exists but is limited to one engine."

---

## Finding #7: Charter Violation / Governance Gap (Score: 27)

**Claim**: RSI Regime violates the Charter's Section 2 ("Do not propose oscillators") and Section 8 (mean-reversion ban). spike.md contradicts the Charter.

**Counter-evidence sought**: Evidence that the Charter was intended to evolve, or that spike.md formally supersedes it.

**Investigation**:
- Charter S2: "Do not propose oscillators or countertrend buys as primary logic." RSI Regime uses RSI (an oscillator) as its primary entry logic. Clear violation.
- Charter S8: "If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly." RSI Regime is a mean-reversion strategy (buy oversold, sell overbought). No flagging occurred.
- `spike.md` line 75: "There are no restrictions on what indicators or logic you can use." Direct contradiction of Charter S2 and S8.
- CLAUDE.md references the Charter but does not state spike.md supersedes it.
- No version history, no amendment record, no "Charter v2" exists.
- **Possible counter-argument**: The Charter was written for Pine Script development (it talks about code changes in Pine v6). The Python optimizer is a different activity not governed by the Charter. This is a reasonable interpretation -- the Charter's language ("proposing code changes," "Pine Script v6 only") suggests it governs TradingView strategy edits, not Python research.

**Counter-evidence found**: The Charter's language is narrowly scoped to Pine Script development workflows (Section 4: "Pine Script v6 only"; Section 7: response format for code changes). It could be argued the Charter was never intended to govern Python-based strategy discovery. However, Section 2's identity statement ("Core entry: emaShort > emaMed") and Section 8's scope guardrails read as project-wide identity constraints, not just Pine-specific rules.

**Verdict**: **SURVIVES-TESTED** but with nuance. The violation is real and unambiguous against a literal reading. The counter-argument (Charter governs Pine edits, not Python research) has some textual support but does not overcome the identity-level statements in S2 and S8.

---

## Finding #8: Pine Script Generation Only Supports 8.2.1 (Score: 27)

**Claim**: generate_pine.py's PARAM_MAP only has 8.2.1 entries; non-Montauk strategies have no deployment path.

**Counter-evidence sought**: Any template system, any multi-strategy Pine generation, any deployment tool for v4 strategies.

**Investigation**:
- `generate_pine.py` PARAM_MAP (line 26): maps Python param names to Pine variable names. All entries are 8.2.1 params (`short_ema_len`, `med_ema_len`, `long_ema_len`, etc.).
- No RSI, no breakout, no bollinger params in PARAM_MAP.
- The hand-written `src/strategy/testing/Montauk RSI Regime.txt` Pine file exists with hardcoded parameters (not generated).
- No template system, no strategy-type parameter in generate_pine.py.
- **However**: A hand-written Pine file for RSI Regime DOES exist and is functional. The deployment path is manual but not nonexistent. The claim "6 of 7 strategies have broken deployment layer" conflates "no automated path" with "no path at all."

**Counter-evidence found**: Partial. The RSI Regime Pine file exists in `src/strategy/testing/`. Manual translation is a viable (if error-prone) deployment path. The finding overstates the problem by implying strategies cannot be deployed at all -- they can, manually.

**Verdict**: **WEAKENED** slightly. The automated generation gap is real. But framing it as "only supports 8.2.1" ignores that manual Pine writing is the current (working) workflow. The real risk is translation errors (confirmed by the < vs <= boundary bug), not impossibility.

---

## Finding #9: Stagnation Detection Bug (Score: 18)

**Claim**: `evolve._last_improve` is never set, so stagnation detection is broken -- mutation rate never escalates when it should, or always escalates.

**Counter-evidence sought**: Code that sets `_last_improve`, or evidence the bug has no practical impact.

**Investigation**:
- `evolve.py` line 234: `stag = generation - getattr(evolve, '_last_improve', {}).get(strat_name, 0)`
- Full codebase search for `_last_improve` assignment: zero results. It is only read, never written.
- Since `getattr(evolve, '_last_improve', {})` returns empty dict, `.get(strat_name, 0)` always returns 0.
- Therefore `stag = generation - 0 = generation`. Stagnation equals the generation number, regardless of whether improvements occurred.
- At gen 0-29: mut_rate = 0.15 (correct base rate)
- At gen 30-79: mut_rate = 0.30 (escalated even if improving every generation)
- At gen 80+: mut_rate = 0.50 (max escalation regardless of improvement)
- **Practical impact**: The only recorded run was 19 generations. At gen 19, stag=19 < 30, so the bug had zero effect on the actual results. The bug would only matter for runs lasting 30+ generations.

**Counter-evidence found**: Partial. The bug is confirmed as real, but its practical impact on the only recorded run (19 gens) was zero. The mutation rate was 0.15 for the entire run, which is exactly what it should have been (base rate for early exploration). The bug exists but had no effect on any results that currently exist.

**Verdict**: **WEAKENED** on impact, **SURVIVES-TESTED** on correctness. The code is definitively buggy, but the bug did not influence any existing results. It would only matter for longer optimization runs that have not yet occurred.

---

## Finding #10: Stale Data Pipeline -- 39-Day CSV, No Validation (Score: 12)

**Claim**: CSV is from Feb 23 (39 days old), evolve.py disables Yahoo refresh, and there is no overlap validation at the merge point.

**Counter-evidence sought**: Evidence the CSV has been updated, or that the staleness is irrelevant.

**Investigation**:
- The CSV filename is `TECL Price History (2-23-26).csv` -- suggesting Feb 23, 2026.
- **CRITICAL COUNTER-EVIDENCE**: The actual CSV content extends through April 1, 2026. The last 3 rows are: `2026-03-30`, `2026-03-31`, `2026-04-01`. The file contains 4,340 data rows.
- The filename is misleading -- it was likely created on Feb 23 but has been updated since then. As of April 3, the data is only 2 days stale (the most recent trading day), not 39 days.
- `evolve.py` does set `use_yfinance=False` (line 134), which is still a choice to not auto-refresh. But with a 2-day gap, this is a non-issue for backtesting purposes.
- **Merge validation**: `data.py` line 96 filters by `yf_df["date"] > csv_last_date`, which prevents date overlap but does not validate price continuity at the merge point. This concern remains technically valid but is moot when the CSV is nearly current.
- The "39 days old" claim was likely accurate at the time of analysis if the specialists only looked at the filename, not the actual data content.

**Counter-evidence found**: **Strong**. The CSV is 2 days stale, not 39 days. The filename is stale but the data is current. The core claim about data staleness is factually wrong as of the current file state. The secondary claim about missing merge validation is technically valid but practically irrelevant with current data.

**Verdict**: **KILLED**. The CSV data extends to April 1, 2026. The "39 days stale" claim is based on the filename, not the actual data. The finding's primary concern (stale data distorting results) does not apply. The secondary concern (no price continuity check at merge point) is a minor code quality issue, not a data integrity emergency.

---

## Summary Table

| Rank | Finding | Verdict | Notes |
|------|---------|---------|-------|
| 1 | Dual engine schism | **SURVIVES-TESTED** | Zero cross-imports confirmed. Absolute structural isolation. |
| 2 | RSI Regime unreliable winner | **SURVIVES-TESTED** | Crippled baseline + no validation confirmed. Minor stat correction (75% win, not 100%). |
| 3 | Validation disconnected from v4 | **SURVIVES-TESTED** | validation.py physically cannot reach v4 strategies. |
| 4 | montauk_821 wrong EMA (30 vs 500) | **SURVIVES-TESTED** | 30-bar vs 500-bar confirmed in code. No ambiguity. |
| 5 | Fitness under-penalizes DD | **WEAKENED** | Formula confirmed. But gentle penalty may be intentional for exploration. |
| 6 | Zero test coverage | **WEAKENED** | Technically accurate. But parity_check.py is a real verification tool, not nothing. |
| 7 | Charter violation | **SURVIVES-TESTED** | Clear violation of S2 and S8. Counter-argument (Charter = Pine only) has limited merit. |
| 8 | Pine gen only supports 8.2.1 | **WEAKENED** | Automated gap is real, but manual Pine writing works. RSI Regime Pine file exists. |
| 9 | Stagnation detection bug | **WEAKENED** | Bug is real but had zero impact on the only recorded run (19 gens < 30 threshold). |
| 10 | Stale data pipeline | **KILLED** | CSV data goes through Apr 1, 2026 (2 days stale, not 39). Filename is misleading. |

---

## Overall Assessment

**7 of 10 findings survive adversarial testing.** The top 4 findings (dual engine, RSI reliability, validation disconnect, wrong EMA) are rock-solid -- code-level evidence confirms each one with no ambiguity. These represent the genuine structural problems in the codebase.

**3 findings are weakened** but not killed. The fitness function, test coverage, and Pine generation findings are real concerns but have legitimate counter-arguments that the meta-synthesis did not consider (exploration-phase design choices, manual verification tools, manual deployment paths).

**1 finding is killed.** The stale data claim is factually wrong. The CSV has been updated since the filename was created and contains data through April 1, 2026.

The meta-synthesis's core narrative -- that the v4 architecture is structurally disconnected from validation, and that RSI Regime's superiority claim rests on a crippled comparison -- is strongly confirmed by direct code inspection. The Argus v6 analysis got the big things right.
