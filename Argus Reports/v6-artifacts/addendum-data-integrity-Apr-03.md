# Data-Integrity Addendum — Apr-03

**Specialist:** Data-Integrity
**Phase:** Cross-Pollination
**Inputs:** Digests from Architecture, Risk, Vision-Drift, Velocity

---

## Part 1: Answers to Open Questions

### Architecture: "Could ADX implementations differ materially?"

**YES — they differ materially.** I compared both implementations line-by-line.

**v3** (`backtest_engine.py` lines 196-235): Uses manual Wilder's smoothing with a running sum approach. Seeds smoothed TR/DM+/DM- at index `period` using `np.nansum(arr[1:period+1])`. Seeds ADX at index `period*2` using `np.nanmean(dx[period:period*2+1])`. This matches the classic Wilder formulation.

**v4** (`strategy_engine.py` lines 434-456): Delegates to `_rma()` for all smoothing. `_rma()` (line 41-50) seeds at index `length-1` using `np.mean(series[:length])`, then applies exponential smoothing with alpha=1/length. Critically, the v4 `_adx()` function calls `_rma(np.nan_to_num(dx, nan=0.0), period)` — it replaces NaN DX values with **zero** before smoothing. The v3 version skips NaN values via conditional checks.

**Material differences:**
1. **NaN handling**: v4 treats NaN DX values as 0.0 (bearish bias — zero DX pulls the ADX average down). v3 skips them entirely. During the warmup period where DI+/DI- are NaN, this creates a ~20-bar window where the two engines produce different ADX values.
2. **Seed window**: v3 seeds smoothed TR at index `period` from bars 1 through period. v4 seeds at index `period-1` from bars 0 through period-1. One-bar offset in the seed window.
3. **ADX double-smoothing**: v3 explicitly computes DX first, then applies a second Wilder's smooth to get ADX. v4 does the same but the NaN-to-zero substitution before the second smooth means different input arrays.

**Impact**: For the default `adx_len=14`, the divergence is largest in bars 14-42 (the warmup zone). After ~50 bars, both converge to effectively identical values. Since the ADX filter is off by default (`enable_adx_filter=False`), this only matters when the optimizer enables it. But when it does enable ADX, the v3 and v4 engines will disagree on ADX values for the first ~50 bars, potentially producing different entry decisions near the start of the dataset.

---

### Risk: "Does process_orders_on_close match Python fill timing?"

**YES for v3, NO for v4 — with a specific edge case.**

Both Pine Script and Python fill on the same bar's close price. Pine's `process_orders_on_close=true` means `strategy.entry()` and `strategy.close()` called during bar N's calculation execute at bar N's close. Both Python engines use `cl[i]` as the fill price.

**However**, the v4 engine has a same-bar exit+entry ordering issue I documented in Finding 11. When both entry and exit signals fire on bar N with `cooldown_bars=0`:
- **Pine**: Both `strategy.close()` and `strategy.entry()` are processed. The position flips.
- **v4 Python**: Exit runs first (line 538), sets `last_sell_bar = i`. Entry runs second (line 557), checks `(i - last_sell_bar) > cooldown_bars` which evaluates to `0 > 0 = False`. Entry is blocked.

This is a confirmed parity gap for cooldown=0 strategies. The v3 engine (line 846) uses `<=` instead of `>` with the sense inverted, which has the same effect but different boundary behavior.

**Quantified impact**: For montauk_821, `sell_cooldown_bars=2` by default, so this edge case does not fire. For golden_cross and breakout variants with cooldown=0, it could suppress 1-3 trades over the full dataset.

---

### Risk: "Is TECL leverage decay modeled?"

**NO — and this is by design, but with consequences nobody is tracking.**

Neither Python engine models TECL's daily leverage reset (volatility decay/drag). Both engines treat TECL's historical OHLCV prices as a simple equity — buy at close, sell at close, compute return as `exit_price / entry_price - 1`. This is correct for backtesting because the CSV contains TECL's actual historical prices, which already incorporate the leverage decay that occurred.

**The gap**: The Charter acknowledges leverage drag (line 28: "expect volatility drag in prolonged chop") but no code quantifies it. When the optimizer selects parameters that keep the strategy in the market during choppy sideways periods, the backtest correctly captures the historical drag. BUT: the regime scoring system (bear_threshold=30%) misidentifies leverage-driven drawdowns as bear markets (my Finding 6). A 10% SPY correction causes ~30% TECL drawdown purely from leverage mechanics, not a regime change.

**Bottom line**: The backtest itself is valid (uses real prices). The regime *interpretation* is not (treats leverage-amplified corrections as bear markets).

---

### Vision-Drift: "Is RSI paradigm shift deliberate or unconscious?"

**Data-Integrity perspective: the code comment says deliberate, the data says unconscious.**

Line 111 of `strategies.py` explicitly states: "Leveraged ETFs tend to mean-revert hard -- this exploits that." This is a conscious design decision to add a mean-reversion strategy to the evolutionary pool.

However, the data tells a different story:
1. The RSI Regime "winner" has 10 trades, 75% max drawdown, and 100% win rate — these are not the hallmarks of a deliberately validated strategy. They are the hallmarks of a strategy that accidentally fit a handful of data points.
2. The Charter (Section 8) explicitly bans mean-reversion: "If asked to add mean-reversion, countertrend, multi-asset, or other out-of-scope features, flag it clearly." RSI Regime entering on oversold recovery is textbook mean-reversion.
3. No walk-forward validation was run on the RSI Regime result (my Finding 4).

**My read**: The addition of `rsi_regime` to `strategies.py` was a deliberate exploratory move ("what if we tried this?"). The elevation of its 2.18 fitness result to `best-ever.json` was unconscious drift — the optimizer declared it a winner, and nobody checked whether it violated the Charter or whether 10 trades was statistically meaningful. **The code should rein in, not the Charter should update.** The Charter's mean-reversion ban exists for a sound reason (TECL trends are the alpha source; mean-reversion on a 3x leveraged instrument is structurally dangerous).

---

## Part 2: Revised Finding Scores

Cross-pollination data from other specialists changes several confidence scores.

| Finding | Original Score | Revised Score | Reason |
|---------|---------------|---------------|--------|
| F1: Dual engine divergence | 95% HIGH | **98% CRITICAL** | Architecture independently confirmed 6+ missing features. Risk rates this CRITICAL. All five specialists converge. |
| F2: RSI overfitting | 90% HIGH | **95% CRITICAL** | Risk confirms CRITICAL. Vision-Drift confirms Charter violation. 75% drawdown + 10 trades + no validation = not deployable. |
| F3: RSI calculation divergence | 75% MEDIUM | **80% HIGH** | Elevated because Risk notes the `< vs <=` crossover boundary difference in generate_pine.py (my Finding 12) compounds with this. Two separate RSI parity issues stack. |
| F4: Validation disconnect | 90% HIGH | **95% CRITICAL** | Risk confirms HIGH. Velocity confirms zero tests. No guardrail exists anywhere in the pipeline. |
| F5: Parity tolerances | 80% HIGH | **85% HIGH** | Unchanged tier. Architecture ruled out data.py merge logic, so the gap is in the engine itself, not the data layer. Narrows the search. |
| F6: Regime thresholds | 70% MEDIUM | **80% HIGH** | Elevated. Risk confirms regime_score vs vs_bah mismatch (MEDIUM). Architecture confirms bear threshold interacts with the 30-bar EMA exit bug (wrong EMA = wrong trade boundaries = wrong regime score). |
| F7: Breakout peak leak | 90% HIGH | **90% HIGH** | Unchanged. Architecture independently found this ("breakout peak leak bug"). |
| F8: No CSV validation | HIGH | **HIGH** | Unchanged. Risk confirms stale data (CSV Feb 23) as HIGH. |
| F9: Merge overlap gap | MEDIUM | **HIGH** | Elevated. Risk's "stale data" finding means the CSV-to-Yahoo merge point is even more critical — 13 months of data comes from Yahoo with no overlap check. |
| F10: Stagnation bug | HIGH | **HIGH** | Unchanged. Velocity's note about the 36-sec evolve run means this bug hasn't been stress-tested in longer runs. |
| F11: Same-bar entry/exit | MEDIUM | **HIGH** | Elevated. Now confirmed via the process_orders_on_close analysis (Part 1 above) that this creates a real parity gap with Pine. |
| F12: Pine generation gap | HIGH | **CRITICAL** | Elevated. Velocity confirms generate_pine is a bottleneck. Architecture confirms it only works for 8.2.1. Combined: no v4 strategy can be deployed to production. |
| F13: Bear avoidance default | MEDIUM | **MEDIUM** | Unchanged. |

---

## Part 3: Cross-Lens Findings

### Cross-Finding A: Data-Integrity x Architecture — "The 30-bar EMA Exit Makes Parity Measurement Impossible"

**Claim**: Architecture found that v4 montauk_821 uses `ema_m` (30-bar) for its EMA cross exit, while v3 and Pine both use `ema_long` (500-bar). My Finding 5 documented that the parity check tolerances of 10-30% are too wide. These two findings interact destructively.

**Evidence**: The v4 montauk_821 exit condition (strategies.py line 74) is:
```python
ema_s[i] < ema_m[i] * (1 - buffer)   # 15-bar vs 30-bar
```

The v3 exit condition (backtest_engine.py line 736) is:
```python
ema_short[idx_prev] >= ema_long[idx_prev] and ema_short[idx] < ema_long[idx]  # 15-bar vs 500-bar
```

A 500-bar EMA is dramatically smoother than a 30-bar EMA. The 30-bar EMA will cross the 15-bar EMA far more frequently, producing more exits (shorter hold times, more trades). The 500-bar EMA barely moves, so crossunders are rare and only happen during genuine trend reversals.

**Impact**: The parity check (parity_check.py) compares v3 backtest output against TradingView. It does NOT compare v4 against v3 or v4 against TradingView. So the v4 engine's 30-bar exit is completely unvalidated. When the optimizer runs montauk_821 in the v4 engine and compares it against RSI Regime, the montauk_821 baseline is crippled by the wrong EMA — it exits too early, holds too short, and produces artificially low returns. This makes EVERY other strategy look better by comparison.

**Severity**: CRITICAL. This is the single most damaging data-integrity issue in the system. The optimizer's entire ranking is built on a broken baseline.

---

### Cross-Finding B: Data-Integrity x Vision-Drift — "Charter Violation Creates Unfalsifiable Winner"

**Claim**: Vision-Drift found that RSI Regime violates Charter Section 8 (mean-reversion ban). My Findings 2 and 4 found that RSI Regime has overfitting signatures and no walk-forward validation. These combine to create a finding that is worse than either alone.

**Evidence chain**:
1. Charter bans mean-reversion (Section 8) -- Vision-Drift
2. RSI Regime is explicitly mean-reversion (strategies.py line 111: "Leveraged ETFs tend to mean-revert hard") -- Vision-Drift
3. RSI Regime "won" with fitness 2.18 on 10 trades and 75% max drawdown -- my Finding 2
4. No walk-forward validation can reach v4 strategies -- my Finding 4
5. The parity check cannot validate v4 strategies against TradingView -- my Finding 5
6. generate_pine.py cannot produce Pine for RSI Regime -- my Finding 12

**The unfalsifiability trap**: There is currently NO mechanism in the codebase that can challenge the RSI Regime result. Validation can't reach it (Finding 4). Parity can't check it (Finding 5). Pine generation can't reproduce it (Finding 12). The Charter bans it but the code ignores the Charter (Vision-Drift). And the result itself is statistically meaningless (10 trades, Finding 2). The strategy exists in a validation vacuum where it cannot be disproven, and it sits in `best-ever.json` as the declared winner.

**Severity**: CRITICAL. Not because of any single issue, but because the combination means a Charter-violating, unvalidated, statistically insignificant strategy has been crowned the system's best-ever result with zero checks capable of overturning it.

---

### Cross-Finding C: Data-Integrity x Velocity — "Dead Code Masks Data Flow Bugs"

**Claim**: Velocity found 39% dead code (1,819 lines) and 4x rewrite churn on the spike system. My Findings 10 (stagnation bug) and 7 (breakout peak leak) are both bugs that survive because the surrounding code is too dense to audit easily.

**Evidence**: The stagnation bug (Finding 10) references `evolve._last_improve`, an attribute that is never set. This is a 1-line bug in a 300-line function. The breakout peak tracking bug (Finding 7) is a state management error in a 44-line strategy function surrounded by 6 other strategy functions. Both bugs are the kind that code review catches in a clean, well-tested codebase — but in a codebase with 39% dead code and zero tests, they become invisible.

**Impact**: MEDIUM. The dead code doesn't directly cause data corruption, but it creates the conditions where data-integrity bugs persist undetected. Every line of dead code is a line that a reviewer must mentally skip, increasing the chance of missing a real bug in the adjacent live code.

---

### Cross-Finding D: Data-Integrity x Risk — "Stale CSV + No Validation = Invisible Regime Drift"

**Claim**: Risk found the CSV data is stale (dated Feb 23, 2026 -- 39 days old). My Finding 8 documented no CSV validation, and Finding 9 documented no overlap check on the Yahoo merge. These combine.

**Evidence**: The data pipeline is: CSV (through Feb 23) -> Yahoo API (Feb 24 onward) -> concatenated DataFrame. Risk is correct that 39 days of stale CSV means all recent backtests use Yahoo data for the last ~39 bars. My findings add: (1) No validation that the CSV data is internally consistent (Finding 8), and (2) no overlap check at the merge point (Finding 9).

**The compounding risk**: If Yahoo retroactively adjusted TECL prices (which happens when Yahoo recalculates split adjustments), there could be a price discontinuity at the Feb 23/24 boundary. No code checks for this. The most recent 39 bars are the ones that matter most for current regime detection and live signal generation. A phantom price gap at the merge point would shift EMA values for all 39 Yahoo bars, potentially flipping the current regime classification.

**Severity**: HIGH. The merge point sits exactly where data accuracy matters most -- at the recent end where trading decisions are made.

---

## Summary of Score Changes

| Tier | Original Count | Revised Count | Net |
|------|---------------|---------------|-----|
| CRITICAL | 0 | 4 (F1, F2, F4, F12) | +4 |
| HIGH | 7 (F1, F2, F4, F5, F7, F8, F10) | 7 (F5, F6, F7, F8, F9, F10, F11) | +0 |
| MEDIUM | 4 (F3, F6, F9, F11, F13) | 2 (F3, F13) | -3 |

Cross-findings added: 2 CRITICAL (A, B), 1 HIGH (D), 1 MEDIUM (C).

**Total finding count**: 13 original + 4 cross-lens = 17.
