# Alien Critics Report -- Apr-03

Three domain-alien critics examine Project Montauk independently. Each brings a lens from outside quantitative trading.

---

## Critic 1: Financial Auditor

**Perspective**: "I audit financial systems. I look for control failures, reconciliation gaps, audit trails."

### AUDIT EXCEPTION AE-01: No Reconciliation Between Two Independent Backtest Engines

**Severity**: Material Weakness

The codebase contains two entirely separate backtest engines:

1. `scripts/backtest_engine.py` -- the primary engine used by `run_optimization.py`, `spike_auto.py`, and `validation.py`. It implements the full Montauk 8.2.1 bar-by-bar simulation with all entry/exit logic inline.

2. `scripts/strategy_engine.py` -- a modular engine used by `scripts/strategies.py` and `scripts/evolve.py`. It pre-computes indicators via an `Indicators` class and runs a separate `backtest()` function that processes boolean signal arrays.

These two engines implement overlapping but **not identical** logic. The `montauk_821()` function in `strategies.py` (lines 26-78) is a simplified replica of the backtest_engine logic -- it lacks sell confirmation window logic (`barssince(crossunder) < confirmBars`), sideways filter exit suppression, trailing stop, TEMA slope exit, volume spike exit, asymmetric ATR exit, bear guard, ADX filter, ATR ratio filter, ROC filter, and cooldown. It uses raw `ema_s < ema_m * (1 - sell_buffer/100)` instead of the proper cross+confirmation+allBelow logic.

The `evolve.py` optimizer uses `strategy_engine.backtest()` but the `spike_auto.py` optimizer uses `backtest_engine.run_backtest()`. Results from these two optimization paths are **not comparable** yet both write to the same `remote/best-ever.json` file. A "best-ever" found by `evolve.py` using the simplified engine could be loaded and treated as a real result by `spike_auto.py` or `validation.py`, which use the full engine.

The `parity_check.py` script compares the Python engine against TradingView but **only checks `backtest_engine.py`** -- there is no parity check for `strategy_engine.py`.

**Audit finding**: Two books of record exist for the same system. No reconciliation process ensures they agree. Results flow between them without controls.

---

### AUDIT EXCEPTION AE-02: Fitness Function Inconsistency Across Optimizers

**Severity**: Significant Deficiency

Three different fitness functions exist:

1. `spike_auto.py` fitness (line 194): `bah * dd_penalty * regime_bonus` with quality guards (min 5 trades, max 6 trades/yr, min 20 bars held, false signal rate penalty, 85% DD cap).

2. `evolve.py` fitness (line 49): `bah * dd_penalty * freq_penalty` with different guards (min 3 trades, max 3 trades/yr hard cap).

3. `validation.py` pass criteria (line 313): `regime_score >= baseline AND avg_test_trades >= 1 AND avg_test_mar > 0.05`.

A parameter set can be "fit" under one definition and unfit under another. The evolve.py optimizer penalizes >3 trades/year while spike_auto.py allows up to 6. Evolve.py requires only 3 trades minimum; spike_auto.py requires 5. The validation framework uses regime_score as its primary criterion but evolve.py does not compute regime_score at all (it uses `strategy_engine.backtest()` which does not include regime scoring).

**Audit finding**: No single consistent definition of "good" exists. Optimization results cannot be compared across tools because they were evaluated against different standards.

---

### AUDIT EXCEPTION AE-03: No Audit Trail for Optimization Decisions

**Severity**: Deficiency

When `spike_auto.py` or `evolve.py` runs, it saves:
- The final best result (`remote/best-ever.json`)
- A timestamped results file (`remote/spike-results-YYYY-MM-DD.json`)
- A progress snapshot (`remote/spike-progress.json`)

What it does NOT save:
- The full population at each generation (only the best survives)
- Which parameters were tested and rejected
- The equity curves of any candidate
- Trade-level details for non-winning candidates
- The random seed used (evolve.py uses `random` with no seed; spike_auto.py also)

This means an optimization result cannot be audited after the fact. If `best-ever.json` reports fitness 0.85, there is no way to verify this was actually the best across all candidates tested -- the losing candidates are discarded. There is also no way to reproduce an optimization run because the random state is not saved.

**Audit finding**: Optimization results are non-reproducible and non-auditable. Only the claimed winner survives; the denominator is lost.

---

### AUDIT EXCEPTION AE-04: Uncontrolled Data Pipeline

**Severity**: Significant Deficiency

`data.py` merges two data sources:
1. A static CSV file (`reference/TECL Price History (2-23-26).csv`)
2. Live data from Yahoo Finance API

The merge logic (line 96) filters by `yf_df["date"] > csv_last_date` to avoid overlap, but there is:
- No hash or checksum of the CSV file to detect tampering
- No validation that Yahoo Finance prices for overlapping dates match the CSV
- No logging of which data source contributed which bars
- No handling of adjusted vs unadjusted prices (splits, dividends)
- No data quality checks (negative prices, zero volume, gaps)

If the CSV is modified (accidentally or deliberately), all backtest results change silently. If Yahoo returns stale, missing, or adjusted data differently than the CSV, the merge creates a discontinuity at the seam.

**Audit finding**: The data pipeline has no integrity controls. The foundation of all backtest results is unverified.

---

### AUDIT EXCEPTION AE-05: Commission and Slippage Set to Zero

**Severity**: Deficiency

Both the Pine Script strategy (line 10-11: `commission_value=0, slippage=0`) and the Python engine (`commission_pct: float = 0.0` in StrategyParams) model zero transaction costs. While TECL trades are commission-free on most brokers, there is no slippage modeling despite TECL being a leveraged ETF that can have meaningful bid-ask spreads during volatile periods -- precisely when the ATR shock exit fires.

The system optimizes for exact close-price fills (`process_orders_on_close=true`), which is an idealization. In live trading, market-on-close orders may fill at a different price.

**Audit finding**: Backtest results overstate achievable returns by ignoring execution friction at the exact moments (high volatility exits) where friction is highest.

---

## Critic 2: Airline Safety Engineer

**Perspective**: "I design systems where failure costs lives. I look for failure modes, cascades, single points of failure."

### SAFETY FINDING SF-01: Silent Engine Divergence -- No Cross-Check

**Failure mode**: The two backtest engines (`backtest_engine.py` and `strategy_engine.py`) diverge without any mechanism to detect it.

**Smoke in the cockpit**: There is none. Both engines produce results. Neither checks the other. A bug introduced in one engine (say, an off-by-one in EMA seeding) would silently corrupt all results produced through that path. The `parity_check.py` tool only validates one engine against TradingView -- the other engine has never been validated.

**Risk**: Decisions about which parameters to deploy in live trading could be based on results from the wrong engine. This is the equivalent of having two altimeters that read different values with no flag to the pilot.

**Recommendation**: Either eliminate one engine entirely, or implement a continuous cross-check that runs both engines on the same inputs and asserts results match within tolerance.

---

### SAFETY FINDING SF-02: Sideways Filter Suppresses All Exits -- Including Crash Protection

**Failure mode**: In `backtest_engine.py` line 804: `allow_exit = not (params.enable_sideways_filter and sideways)`. When the sideways filter is enabled (default: True) and the market is in a sideways range, ALL exits are suppressed -- including the ATR shock exit.

The ATR shock exit is described in the Charter as "the crash-catcher" (line 18). The Charter explicitly warns (line 28): "Sideways suppression of exits can defer a necessary sell if a sideways window precedes a breakdown. Keep ATR exit enabled as a backstop."

But the code does not implement this backstop. The ATR exit is suppressed alongside all other exits during sideways periods. If the market enters a narrow range and then flash-crashes through it, the strategy will hold through the crash because the sideways filter is blocking the ATR exit from firing.

**Cascading failure**: Sideways range detected -> all exits blocked -> crash begins within the range -> ATR shock cannot fire -> strategy rides the crash to full depth -> eventual EMA cross exit fires only after the range expands beyond the sideways threshold.

**This is a fail-catastrophic design, not fail-safe.**

**Recommendation**: ATR shock exit should ALWAYS be allowed to fire regardless of sideways filter state. This is explicitly called out in the Charter but not implemented.

---

### SAFETY FINDING SF-03: Exception Swallowing in Fitness Evaluation

**Failure mode**: Both `evolve.py` (line 118) and `spike_auto.py` (line 236) catch all exceptions during fitness evaluation:

```python
except Exception:
    return 0.0, None
```

This means if a parameter combination causes a division by zero, an index out of bounds, a NaN propagation, or any other computational error, it is silently scored as 0.0 and discarded. The optimizer never learns that its search space contains pathological regions.

**Smoke in the cockpit**: There is none. Errors are invisible. If 30% of candidates crash, the optimizer simply thinks 30% of the search space is empty. If a bug causes ALL evaluations to throw (e.g., a data loading error), the optimizer would see a population of all-zeros, select from the "best" of them (all 0.0), and run indefinitely without producing any useful result.

**Risk**: A systematic error (like a NaN in the data causing all ATR calculations to fail) would not be detected until someone manually inspects results and notices all fitness scores are suspiciously low or zero.

**Recommendation**: Log exceptions with the parameter set that caused them. Halt if the exception rate exceeds a threshold (e.g., >10% of evaluations). Never silently swallow errors in a system that makes financial decisions.

---

### SAFETY FINDING SF-04: No Bounds Checking on Generated Parameters

**Failure mode**: The evolutionary operators (`mutate`, `crossover`) in both `evolve.py` and `spike_auto.py` generate parameter combinations that can violate structural invariants. For example:

- `spike_auto.py` `enforce_constraints()` checks `short_ema_len < med_ema_len` but does NOT check `med_ema_len < long_ema_len` (500 is the default but sweepable to as low as 200). If med_ema > long_ema, the EMA cross exit logic (which compares short vs long) becomes inverted.
- `evolve.py` has NO `enforce_constraints()` function at all. Parameters are generated and used raw. `crossover_params()` can produce `short_ema=25, med_ema=15` (inverted) which would cause the entry condition `short > med` to trigger in the opposite regime.
- Neither optimizer bounds-checks lookback parameters against data length. Setting `long_ema_len=800` with only 500 bars of data produces an all-NaN indicator that silently disables the EMA cross exit.

**Risk**: Parameter combinations that violate the strategy's structural assumptions can produce backtests that "work" (positive fitness) for pathological reasons (e.g., never entering because all indicators are NaN, or entering on every bar because conditions are inverted).

---

### SAFETY FINDING SF-05: No Kill Switch or Circuit Breaker

**Failure mode**: The evolutionary optimizers (`spike_auto.py`, `evolve.py`) run for a user-specified duration (up to 8+ hours) with no mechanism to:

- Detect that results have converged and stop early
- Detect that the data file has changed during the run
- Detect that best-ever.json has been modified externally during the run (race condition with concurrent sessions)
- Pause and resume safely (spike_state.py exists but is not used by spike_auto.py or evolve.py)

If two optimization sessions run concurrently (e.g., spike_auto.py and evolve.py), both will read and write `remote/best-ever.json` without locking. Last writer wins. The spike_state.py atomic write (tempfile + os.replace) protects against crash corruption but not concurrent access.

---

### SAFETY FINDING SF-06: Single Data Source -- No Redundancy

**Failure mode**: All backtesting depends on a single CSV file plus a single API endpoint (Yahoo Finance). There is no secondary data source to cross-validate prices. If the CSV contains errors (e.g., split-adjusted prices where raw prices should be, or a data vendor error on a specific date), every backtest result is wrong.

The system optimizes parameters to maximize performance on this specific price series. If the price series itself is wrong, the optimization is fitting to noise in the data error, not market reality.

---

## Critic 3: Compiler Writer

**Perspective**: "I build systems that reason formally about code. I look for undefined behavior, invariant violations, fragile contracts."

### INVARIANT FINDING IF-01: Two Engines Have Different Execution Models

**Invariant**: "The Python backtest engine faithfully replicates the Pine Script logic."

This invariant is **stated** in the `backtest_engine.py` docstring (line 4: "faithful replica of Project Montauk 8.2.1") but **not enforced**.

The `strategy_engine.py` + `strategies.py` combination implements a different execution model:
- `strategy_engine.py` `backtest()` processes exits BEFORE entries on each bar (line 537-540 in strategy_engine, lines 534-556). The `backtest_engine.py` also processes exits before entries (lines 806-860). This matches -- but the **signal generation** differs.
- In `backtest_engine.py`, exit signals are computed on the current bar considering position state (e.g., trailing stop tracks peak_since_entry). In `strategies.py`, signals are pre-computed for ALL bars without position awareness (the `montauk_821()` function at line 26 sets exit signals on every bar where the condition is true, regardless of whether the strategy is in a position).
- The `strategy_engine.py` `backtest()` then filters these pre-computed signals through position state. But the pre-computation means stateful exits (like trailing stop) cannot be implemented.

**Consequence**: The contract "both engines produce equivalent results for the same parameters" is violated. This is not a bug -- it is a fundamental architectural difference. But nothing in the code documents or enforces this distinction.

---

### INVARIANT FINDING IF-02: Regime Score Uses Bar-Count Proxy Instead of Return-Weighted Measurement

**Invariant assumed**: "Regime score measures how well the strategy captures bull gains and avoids bear losses."

**Invariant violated**: The `score_regime_capture()` function (backtest_engine.py line 432) measures **bars in market** during bull/bear periods, not **returns captured/avoided**:

```python
# Bull capture (line 489)
bars_in = np.sum(in_market[s:e])
capture = bars_in / bull_bars

# Bear avoidance (line 472)
bars_out = np.sum(~in_market[s:e])
avoidance = bars_out / bear_bars
```

This means a strategy that is in the market for 90% of a bull period but only during the flat consolidation phase (missing the actual upswing) scores identically to one that captures the real move. Similarly, a strategy that exits a bear market but re-enters at the exact trough and rides it back down scores the same "avoidance" as one that stays out entirely.

The metric optimizes for **temporal overlap** with regimes, not **economic participation** in them. This is a fundamental mismatch between what the metric claims to measure and what it actually measures.

---

### INVARIANT FINDING IF-03: StrategyParams.from_dict() Silently Drops Unknown Keys

**Invariant assumed**: Parameter dictionaries are well-formed and complete.

**Invariant violated**: `StrategyParams.from_dict()` (backtest_engine.py line 123):

```python
@classmethod
def from_dict(cls, d: dict) -> "StrategyParams":
    valid = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{k: v for k, v in d.items() if k in valid})
```

This silently drops any key not in the dataclass. If an optimizer produces a parameter like `"cooldown": 5` (used in evolve.py/strategies.py) or `"atr_mult": 3.0` (used in strategies.py `montauk_821()`), these are silently ignored when the dict is passed to `StrategyParams.from_dict()`. The actual StrategyParams field names are `sell_cooldown_bars` and `atr_multiplier`.

This means the parameter names used in `strategies.py` (`short_ema`, `med_ema`, `trend_ema`, `atr_mult`, `quick_thresh`, `sell_buffer`, `cooldown`) are **not** the same as the parameter names in `StrategyParams` (`short_ema_len`, `med_ema_len`, `trend_ema_len`, `atr_multiplier`, `quick_delta_pct_thresh`, `sell_buffer_pct`, `sell_cooldown_bars`). If anyone attempts to feed `evolve.py` results into `backtest_engine.py`, all strategy-specific parameters would be dropped and replaced with defaults.

---

### INVARIANT FINDING IF-04: EMA Cross Exit Window Has Off-By-One Sensitivity

**Invariant**: The EMA cross exit fires within the confirmation window, matching Pine Script's `barssince(crossunder(...)) < sellConfirmBars`.

The Python implementation (backtest_engine.py lines 728-756) scans backward from the current bar:

```python
for j in range(params.sell_confirm_bars):
    idx = i - j
    idx_prev = idx - 1
```

With `sell_confirm_bars=2` (default), this checks bars `i` and `i-1`. In Pine Script, `barssince` returns 0 on the bar of the event, so `barssince(...) < 2` means bars 0 and 1 (the event bar and the next bar). Whether these align depends on whether the Python `j=0` iteration (checking bar `i` for a cross at `i-1 -> i`) corresponds to Pine's `barssince=0`.

If there is an off-by-one here, the primary structural exit fires one bar too early or too late. Given that this exit governs most trades (the EMA Cross is the most common exit reason), a single bar offset systematically shifts every exit. The `parity_check.py` tolerances are quite wide (10-30% on most metrics), which could mask a systematic 1-bar shift.

---

### INVARIANT FINDING IF-05: Equity Curve Updated Multiple Times Per Bar

**Invariant**: Equity curve[i] should represent the strategy's equity at bar i's close.

In `backtest_engine.py`, equity_curve[i] is written at:
- Line 655: Start of the bar (before any exit/entry logic)
- Line 712: After bear_guard_ok computation
- Line 866: End of the bar (after exit/entry logic)

The first write uses stale position state (before exits are processed). The second write is inside a conditional block (only if bear guard is enabled). The third write is the correct final value. This means equity_curve values during the warmup period and for bars where position changes occur may be inconsistent within the bar's processing. The final write (line 866) fixes it for the bar, but intermediate reads of equity_curve (like the bear_guard_ok rolling peak at line 715) may see values from an earlier write within the same bar.

Specifically, the bear guard checks `np.max(equity_curve[lookback_start:i + 1])` at line 715, but equity_curve[i] at that point was set at line 655 (before exits), not at line 866 (the correct final value). This means the bear guard's rolling peak may include stale values.

---

### INVARIANT FINDING IF-06: Indicator Cache Keys Are Fragile

**Invariant assumed**: Cached indicator values are correctly keyed and never collide.

In `strategy_engine.py`, the `Indicators` class caches results by tuple key. The `slope()` method (line 176) takes a `series_key` string:

```python
def slope(self, series_key: str, series: np.ndarray, lookback: int) -> np.ndarray:
    return self._cached(("slope", series_key, lookback), lambda: _slope(series, lookback))
```

If two different strategies compute the slope of different series but use the same `series_key` string and lookback, they get the first strategy's cached result. This is a caller-controlled key with no enforcement -- it relies on the convention that callers choose unique keys. There is no mechanism to detect a collision.

Similarly, `ema_of()` and `sma_of()` accept a string key. If two callers pass the same key for different series, the cache returns wrong data silently.

---

### INVARIANT FINDING IF-07: Bootstrap Test Is Not Testing What It Claims

**Invariant claimed**: The bootstrap test (`cmd_bootstrap` in run_optimization.py line 275) tests statistical significance.

**Invariant violated**: The test shuffles the ORDER of trade returns but preserves their magnitudes. This tests whether the return sequence matters (it does, due to compounding), but it does NOT test whether the strategy's entry/exit timing is better than random.

A proper bootstrap for a trading strategy would randomize the entry/exit dates (or test against random entry/exit signals with similar trade frequency) to determine whether the strategy's timing adds value. Shuffling trade returns only tests whether the specific trade ordering matters -- which is a different question entirely. A strategy that makes its biggest winning trade first will rank high in the "actual percentile" simply because of compounding effects, not timing skill.

---

## Cross-Domain Synthesis

### [DOMAIN-CONVERGENT] Findings Flagged by 2+ Critics

**DC-01: Two-Engine Divergence** (AE-01 + SF-01 + IF-01)
All three critics independently identified the dual-engine problem. The auditor sees two books of record with no reconciliation. The safety engineer sees two altimeters reading different values. The compiler writer sees two execution models implementing different contracts. This is the single highest-confidence finding in the report.

**DC-02: Silent Failure / Error Swallowing** (AE-03 + SF-03 + IF-03)
The auditor sees non-auditable results (discarded candidates, no reproducibility). The safety engineer sees silently swallowed exceptions producing invisible failure. The compiler writer sees silent key dropping in parameter parsing. The common thread: the system optimizes for producing output rather than producing correct output.

**DC-03: Sideways Filter Blocks Safety Exits** (AE-02 via Charter violation + SF-02)
The Charter explicitly warns about this. The safety engineer identifies it as fail-catastrophic. This is a known, documented, unimplemented safety requirement.

**DC-04: Fitness Function Fragmentation** (AE-02 + IF-02)
The auditor sees three incompatible fitness definitions. The compiler writer sees the primary metric (regime score) measuring the wrong thing (bar-count instead of economic participation). Together: not only do the tools disagree on what "good" means, but the thing they're trying to measure is itself a proxy for the actual goal.

### [BLIND-SPOT] Findings Specialists Likely Missed

**BS-01: Parameter Name Mismatch Between Engines** (IF-03)
The strategies.py parameter names (`short_ema`, `atr_mult`, `quick_thresh`) do not match StrategyParams field names (`short_ema_len`, `atr_multiplier`, `quick_delta_pct_thresh`). Results from evolve.py cannot be fed to backtest_engine.py without manual translation. This is an integration defect that would only surface when trying to flow optimized parameters from one system to the other -- a path that sounds like it should work but silently does nothing.

**BS-02: Equity Curve Consistency Within a Bar** (IF-05)
The bear depth guard reads stale equity values from earlier in the same bar's processing loop. This is a subtle ordering dependency that would not surface in any high-level architectural analysis.

**BS-03: Bootstrap Test Measuring Wrong Thing** (IF-07)
The statistical significance test sounds rigorous but tests trade-order sensitivity, not timing skill. This could give false confidence that the strategy has genuine alpha when it may just benefit from favorable return compounding order.

**BS-04: Zero Slippage on Crisis Exits** (AE-05)
The ATR shock exit fires during extreme volatility -- exactly when slippage is highest and TECL's bid-ask spread widens most. Modeling zero slippage systematically overstates the exit that matters most for risk management.

**BS-05: No Data Integrity Validation** (AE-04 + SF-06)
The CSV file that underpins all backtesting has no checksum, no cross-validation against a second source, and no quality checks. Every optimization result, every regime score, and every parity check inherits whatever errors exist in this file.
