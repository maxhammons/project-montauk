# Execution Verdicts -- Apr 03, 2026

**Author**: Execution Agent
**Argus Version**: v6
**Method**: Isolated PoC scripts run in /tmp/ sandboxes. Read-only on project files. 30-second timeouts. No network requests.
**Inputs**: meta-synthesis-Apr-03.md, devils-advocate-Apr-03.md, project source files

---

## Summary Table

| # | Finding | Verdict | Confidence | Notes |
|---|---------|---------|------------|-------|
| 1 | montauk_821 wrong EMA exit (30 vs 500) | **PROVEN** | 100% | Code-level proof. No ambiguity. |
| 2 | RSI Regime overfitting stats | **PROVEN** (with correction) | 100% | Core concern valid. Meta-synthesis specific numbers wrong. |
| 3 | Stagnation detection broken | **PROVEN** (latent) | 100% | Bug confirmed. Zero impact on recorded results. |
| 4 | Walk-forward validation disconnected | **PROVEN** | 100% | Structural impossibility. Zero bridge code exists. |
| 5 | Indicator divergence (EMA computation) | **DISPROVEN** | 100% | EMA functions are byte-identical in logic. |

**Score: 4 PROVEN, 0 INCONCLUSIVE, 1 DISPROVEN**

---

## PoC #1: montauk_821 Wrong EMA Exit

**File**: `poc-ema-exit.py`
**Claim**: strategies.py montauk_821 uses 30-bar EMA for exit; backtest_engine.py uses 500-bar EMA (matching Pine 8.2.1).

**Evidence**:

```
strategies.py montauk_821:
  Line 34: ema_m = ind.ema(p.get("med_ema", 30))
  Line 74: if ema_s[i] < ema_m[i] * (1 - p.get("sell_buffer", 0.2) / 100):
  EXIT compares short EMA against 30-bar MEDIUM EMA

backtest_engine.py:
  Line 36: long_ema_len: int = 500
  Line 618: ema_long = ema(cl, params.long_ema_len)
  Line 736: if ema_short[idx_prev] >= ema_long[idx_prev] and ema_short[idx] < ema_long[idx]:
  EXIT compares short EMA against 500-bar LONG EMA
```

**Additional finding**: `STRATEGY_PARAMS["montauk_821"]` has no `long_ema` parameter at all. The `med_ema` search range is (15, 60). There is no way for the v4 montauk_821 to produce the correct 500-bar exit behavior.

**Verdict**: **PROVEN**. The 30-bar vs 500-bar discrepancy is unambiguous. strategies.py montauk_821 is a fundamentally different strategy from Pine 8.2.1. This directly invalidates the baseline used for the 4.79x fitness ratio.

---

## PoC #2: RSI Regime Overfitting Stats

**File**: `poc-rsi-overfitting.py`
**Claim (meta-synthesis)**: RSI Regime has "100% win / 10 trades"
**Claim (devil's advocate)**: Actual results show 75% win / 12 trades

**Evidence from `evolve-results-2026-04-03.json`**:

```
RSI Regime:
  Trades: 12
  Win Rate: 75.0%
  Max DD: 75.1%
  CAGR: 48.61%
  vs B&H: 3.4913x
  Fitness: 2.1803

montauk_821 (baseline):
  Fitness: 0.4556
  Ratio: 2.1803 / 0.4556 = 4.79x
```

**Run metadata**:
- Duration: 36 seconds (0.01 hours)
- Total evaluations: 1,330
- Generations: 19

**Verdict**: **PROVEN** (with factual correction). The meta-synthesis's specific claim of "100% win / 10 trades" is wrong -- actual data shows 75.0% win / 12 trades. The devil's advocate caught this correctly. The core concerns remain valid:
- 75.1% max drawdown (requires 301% gain to recover)
- 36-second run, 19 generations, 1,330 evals
- Pure in-sample, no walk-forward validation
- Baseline is crippled (see PoC #1)

---

## PoC #3: Stagnation Detection Broken

**File**: `poc-stagnation.py`
**Claim**: `evolve._last_improve` is never assigned, making stagnation detection broken.

**Evidence**:

```
evolve.py occurrences of '_last_improve':
  Line 234 [READ]: stag = generation - getattr(evolve, '_last_improve', {}).get(strat_name, 0)

  Total READ: 1
  Total WRITE: 0
```

**Consequence chain**:
1. `getattr(evolve, '_last_improve', {})` always returns `{}` (empty dict)
2. `.get(strat_name, 0)` always returns `0`
3. `stag = generation - 0 = generation`
4. Stagnation equals generation number regardless of actual improvement
5. At gen 30: mut_rate escalates to 0.30 even if improving every generation
6. At gen 80: mut_rate escalates to 0.50 unconditionally

**Impact on recorded run**: None. The only run was 19 generations (< 30 threshold). Mutation rate was 0.15 throughout, which happens to be correct. The bug is latent -- it would corrupt any run lasting 30+ generations.

**Verdict**: **PROVEN** (latent bug). The attribute is read but never written anywhere in the file. The bug is definitively present but had zero effect on existing results.

---

## PoC #4: Walk-Forward Validation Disconnected

**File**: `poc-validation-disconnect.py`
**Claim**: validation.py cannot validate v4 strategies (from strategy_engine/evolve).

**Evidence**:

```
validation.py imports:
  from backtest_engine import StrategyParams, BacktestResult, run_backtest
  Imports strategy_engine: False
  Imports strategies: False

evolve.py imports:
  from strategy_engine import Indicators, backtest, BacktestResult
  Imports validation: False

validate_candidate signature:
  def validate_candidate(df, candidate: StrategyParams, baseline: StrategyParams | None = None, ...)
  Requires: StrategyParams (backtest_engine dataclass with 30+ typed fields)
  v4 uses: plain dict with different key names (short_ema vs short_ema_len)

Bridge functions: None found anywhere in codebase
```

**Three-layer disconnect**:
1. **Import layer**: Zero cross-imports between validation.py and strategy_engine.py
2. **Type layer**: validate_candidate requires StrategyParams; v4 uses plain dicts
3. **Name layer**: Even dict keys differ (v4: `short_ema`; backtest_engine: `short_ema_len`)

**Verdict**: **PROVEN**. The disconnect is structural and absolute. There is no code path, no adapter, no bridge function that could connect validation.py to v4 strategies. The validation framework is physically incapable of reaching the strategies that need it.

---

## PoC #5: Indicator Divergence (EMA Computation)

**File**: `poc-ema-divergence.py`
**Claim**: EMA implementations may diverge between backtest_engine.py and strategy_engine.py.

**Evidence**:

```
EMA(15) on 1000-bar test series:
  Max absolute difference: 0.000000000000000e+00
  Numerically identical (atol=1e-12): True

EMA(500) on 1000-bar test series:
  Max absolute difference: 0.000000000000000e+00
  Numerically identical: True

Source code logic comparison:
  Logic lines match: 8 vs 8
  Logic identical: True
```

Both implementations use the exact same algorithm:
- SMA seed over first `length` bars
- Recursive EMA with `alpha = 2.0 / (length + 1)`
- Same NaN handling, same array initialization

**Verdict**: **DISPROVEN**. The EMA functions produce bit-identical output. The "indicator divergence" concern is unfounded at the computation level. The actual divergence is at the parameter level (PoC #1: using 30-bar vs 500-bar), not in the math.

---

## Cross-Finding Analysis

The five PoCs reveal a coherent failure pattern:

1. **PoC #1 + #2 compound**: The 4.79x fitness ratio is doubly unreliable. The numerator (RSI Regime) is unvalidated in-sample with 75% DD. The denominator (montauk_821) is a crippled version that uses the wrong exit EMA. The true ratio is unknown.

2. **PoC #3 + #4 compound**: Both safeguards (stagnation detection + walk-forward validation) are broken. One has a latent code bug, the other has a structural architecture gap. Neither can protect against overfitting.

3. **PoC #5 clarifies scope**: The computation layer is sound. The bugs are in parameter selection and architecture, not in math. This is actually good news -- fixing the EMA exit parameter and bridging the validation gap would address the core issues without requiring engine rewrites.

---

## Recommended Priority

Based on execution evidence:

| Priority | Fix | Impact | Effort |
|----------|-----|--------|--------|
| P0 | Fix montauk_821 exit to use 500-bar EMA | Corrects baseline, makes fitness ratios meaningful | 1 line change + add long_ema param |
| P0 | Add validate_v4() bridge function | Enables walk-forward for v4 strategies | ~50 lines |
| P1 | Fix _last_improve write in evolve.py | Prevents mutation rate corruption for longer runs | ~5 lines |
| P2 | Re-run evolve with corrected baseline | Get true fitness ratios | Re-run existing script |
