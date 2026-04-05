# Risk Specialist Addendum — Cross-Pollination — Apr-03

**Specialist**: Risk & Failure
**Phase**: Cross-pollination (responding to all 4 specialist digests)

---

## Part 1: Answering Other Specialists' Open Questions

### ARCHITECTURE Open Q: Could ADX implementation differences cause material divergence in strategies using DMI?

**Answer: YES — confirmed material divergence. Confidence 90%.**

The two engines implement ADX differently:

1. **backtest_engine.py** (lines 196-235): Uses Wilder's classical summation seed. Initializes smoothed TR/DM+ /DM- at index `period` with `np.nansum(arr[1:period+1])`, then applies `sm[i] = sm[i-1] - sm[i-1]/period + val[i]`. ADX itself seeds at `period * 2` with `np.nanmean(dx[period:first_valid+1])`. This is the traditional Wilder method.

2. **strategy_engine.py** (lines 434-456): Uses `_rma()` directly on dm_plus, dm_minus, and tr arrays (which uses the generic RMA seeded with SMA of first `length` values). Then computes DX and smooths it again with `_rma()` via `nan_to_num(dx, nan=0.0)` — replacing NaN with 0.0 before smoothing. This NaN-to-zero substitution corrupts the ADX warm-up period, pulling early values toward zero.

**Material impact**: The NaN-to-zero hack in strategy_engine.py means ADX will read systematically lower during the warm-up period (first ~2x period bars). For DMI-based strategy filtering (e.g., `adx_min=20` threshold), this could suppress entries that backtest_engine.py would allow, or vice versa. On a 14-period ADX, the first ~28-56 bars will diverge. For strategies that trade infrequently (like RSI Regime at 0.7 trades/year), even a few bars of divergence near a regime change can shift an entry by weeks.

Currently no registered strategy in `strategies.py` uses ADX directly, so the divergence is latent. But `backtest_engine.py` has `enable_adx_filter` as an optional parameter for 8.2.1, meaning any sweep that enables it will produce different results depending on which engine runs it.

---

### DATA-INTEGRITY Open Q: Does Pine RSI boundary condition (<=) vs Python (<) cause signal divergence?

**Answer: YES — confirmed signal divergence. Confidence 95%.**

Examined all three implementations:

1. **Pine Script** (Montauk RSI Regime.txt, line 46): `ta.crossover(rsi, entryRsi)` — Pine's `ta.crossover(a, b)` returns true when `a[1] <= b` and `a > b`. Note the `<=` on the previous bar.

2. **Python strategies.py** (line 133): `rsi[i-1] < entry_level and rsi[i] >= entry_level` — Uses strict `<` on previous bar and `>=` on current bar.

3. **The boundary case**: When `rsi[i-1]` is exactly equal to `entry_level` (e.g., RSI = 35.000):
   - Pine: `crossover` considers this as "was at or below" (<=), so the NEXT bar above triggers entry.
   - Python: `rsi[i-1] < entry_level` is FALSE when exactly equal, so the crossover is NOT detected.

**Material impact**: RSI values are continuous floats, so exact equality is rare on real data. However, with integer RSI lengths and round entry thresholds (35.0), the probability is non-zero. On 17 years of daily data with 10-period RSI, I estimate 1-3 missed/phantom signals from this boundary alone. For a strategy that makes only 10-12 trades total, losing even 1 trade is a 8-10% change in the trade count and could materially shift win rate and fitness.

Additionally, the Python RSI calculation itself diverges from Pine. `strategy_engine.py` line 95 uses `np.diff(series, prepend=series[0])`, which means `delta[0] = 0` (the first element minus itself). Pine's `ta.rsi()` computes `delta = close - close[1]`, which is `na` on bar 0. The Python approach feeds a zero into the RMA seed window, slightly biasing the initial gain/loss averages downward. After ~50 bars the bias decays, but for the first few RSI values, there is measurable divergence. This interacts with the boundary condition to make exact parity unlikely.

---

### VISION-DRIFT Open Q: Is RSI Regime paradigm shift deliberate or unconscious?

**Answer from Risk lens: Immaterial to risk, but the unconscious hypothesis is more dangerous.**

If deliberate: someone evaluated the Charter's mean-reversion ban, decided RSI Regime was different enough (it uses RSI as an entry timer, not a mean-reversion bet), and proceeded. Risk: moderate and contained because the decision was conscious.

If unconscious: the optimizer blindly tested all 7 strategies including RSI Regime, it won on fitness, and nobody noticed it violates Section 8 of the Charter. Risk: high, because it means the guardrail system (Charter -> Feature Acceptance Checklist -> Validation) is not functioning. The Feature Acceptance Checklist (Charter S5) asks "Can it be explained as a trend or risk control — not an unrelated signal?" RSI Regime's answer is clearly "no" — it is an oscillator-based mean-reversion entry.

From the evidence, I lean 80% toward unconscious: (a) the Charter has been frozen for 31 days per Vision-Drift, (b) no amendment or exception was recorded, (c) the evolve.py code tests all registered strategies mechanically with no Charter compliance check.

**Risk implication**: The system has no Charter compliance gate. Any strategy registered in `STRATEGY_REGISTRY` can win, regardless of whether it violates the governing document.

---

### VELOCITY Open Q: Will a full 8-hour run change RSI Regime ranking?

**Answer: Likely no for ranking, likely yes for parameters. Confidence 70%.**

Risk assessment of a longer run:

1. **RSI Regime will likely remain #1** because its structural advantage is real: RSI entry + trend EMA filter + high exit threshold keeps it out of the market ~96% of the time (0.7 trades/year), which on a 3x leveraged ETF means avoiding most volatility drag. The 3.49x vs buy-and-hold edge is too large for other strategies to overcome given the fitness function's weak drawdown penalty.

2. **Parameters will likely shift** because 19 generations with pop=40 is insufficient to explore the RSI Regime parameter space (6 params, ~180K possible combinations at grid resolution). A longer run will find variants with slightly different RSI thresholds that may trade more or less. The risk is that longer runs could find even MORE overfitted variants (e.g., RSI entry=37, exit=82, panic=17) that happen to align with specific historical events.

3. **The real danger**: A full 8-hour run (~150K evaluations) will give RSI Regime enough optimization pressure to perfectly fit the 12 regime transitions in the TECL data. With only 10-12 trades, each trade is ~10% of the signal. The optimizer can tune 6 parameters to "predict" each of 12 trades, which is 2 parameters per trade — exactly the overfitting boundary.

**Bottom line**: More compute makes the overfitting problem worse, not better, unless walk-forward validation is running in-loop. Currently it is not.

---

## Part 2: Score Revisions Based on New Information

### R-03 (RSI Regime Overfitting): CRITICAL -> **CRITICAL+ (upgraded)**

New information from cross-pollination:
- Vision-Drift confirms Charter violation (S8 mean-reversion ban) — adds governance risk on top of financial risk
- Data-Integrity confirms RSI calculation divergence from Pine — the "best-ever" was found using an RSI that doesn't match TradingView
- Velocity confirms the 36-second, 1,330-eval run is statistically meaningless — insufficient to distinguish signal from noise
- Architecture confirms the strategy cannot be validated (validation.py incompatible) or deployed (generate_pine.py incompatible)

This strategy is simultaneously: overfitted (10 trades), ungoverned (Charter violation), unvalidatable (wrong engine), undeployable (no Pine generation), and computed with divergent RSI. Every layer of defense has failed.

**Revised confidence**: 95% (up from 90%)

### R-01 (Dual Engine Divergence): CRITICAL (maintained, confidence raised)

Architecture's confirmation of triple-duplicated indicators with subtle divergences reinforces this. The ADX divergence analysis above adds a concrete mechanism. Data-Integrity's finding that RSI calculation diverges from Pine means the parity gap is THREE-way: strategy_engine.py vs backtest_engine.py vs TradingView.

**Revised confidence**: 95% (up from 92%)

### R-04 (Silent Exception Swallowing): HIGH -> **HIGH (confidence raised)**

Data-Integrity's finding that `evolve.py` stagnation detection references `getattr(evolve, '_last_improve', {})` — a non-existent attribute — confirms the silent failure pattern extends beyond just the evaluate function. The mutation rate escalation (0.15 -> 0.30 -> 0.50) is based on stagnation detection that NEVER WORKS because `_last_improve` is never set. This means `stag` always equals `generation` (since 0 is the default), so mutation rate escalates to 0.50 almost immediately (after generation 80). The optimizer is running at maximum mutation rate for the entire run, which explains both: (a) why it finds extreme outliers like RSI Regime, and (b) why convergence is so fast (54 seconds) — it is essentially random search, not evolution.

**Revised confidence**: 98% (up from 95%)

### R-10 (Fitness Function Under-Penalizes DD): MEDIUM -> **HIGH (upgraded)**

Architecture's and Velocity's confirmation that the RSI Regime result is the basis for all strategic decisions makes this more severe. The gentle drawdown penalty is not a theoretical concern — it is actively promoting the system's "best" result. Combined with the broken stagnation detection (R-04 revision above), the optimizer is doing maximum-mutation random search scored by a function that barely penalizes 75% drawdowns. This is a recipe for finding catastrophic configs.

**Revised severity**: HIGH

### R-09 (Breakout State Contamination): MEDIUM (maintained, reduced concern)

Looking at the evolve results, breakout ranks #2 with fitness 0.5049 — far below RSI Regime's 2.18. Even if the state contamination inflates breakout's score, it doesn't change strategic decisions. The bug is real but not decision-material.

**Revised confidence**: 85% (unchanged) but **practical impact lowered**

---

## Part 3: Cross-Lens Findings (Risk x Other Lens)

### CROSS-01: Risk x Architecture — The Mutation Death Spiral

**Components**: R-04 (silent exceptions) + Architecture #8 (trivial evolve run) + Velocity #3 (4x rewrites)

The broken stagnation detection (`_last_improve` never set) means the mutation rate jumps to 0.50 (maximum) by generation 80, and stays there. With a population of 40 across 7 strategies, generation 80 is reached in approximately:
- 40 evals/strategy x 7 strategies = 280 evals/generation
- 280 x 80 = 22,400 evals

At ~74 evals/second (1,330 evals in ~18 seconds), generation 80 arrives in ~5 minutes. After that, the "evolutionary" optimizer is just doing random search with a slight elite bias.

**Risk implication**: The optimizer cannot actually evolve — it cannot gradually refine parameters toward an optimum. It finds whatever random search surfaces in the first few minutes, then churns. This explains why the 54-second run found something and a longer run would likely find the same thing or something equally random.

**Confidence**: 92%
**Severity**: HIGH
**Connects to**: R-03 (overfitting), R-04 (silent failure), Architecture #8

---

### CROSS-02: Risk x Data-Integrity — The Three-Way Parity Gap

**Components**: R-01 (dual engine), R-02 (wrong EMA), Data-Integrity #1 (6 missing features), Data-Integrity #3 (RSI divergence)

There are now three separate systems that should agree but don't:

| System | RSI implementation | ADX implementation | EMA cross exit | Position management |
|--------|-------------------|-------------------|----------------|-------------------|
| strategy_engine.py | np.diff prepend, < boundary | _rma + nan_to_num | short vs med (30) | exit before entry same bar |
| backtest_engine.py | (not present) | Wilder's summation | short vs long (500) | exit then entry, different priority |
| TradingView Pine | ta.rsi, <= boundary | ta.adx (Wilder's) | short vs long (500) | process_orders_on_close |

For RSI Regime specifically: the optimizer found its params using strategy_engine.py's RSI, but the Pine Script in testing/ uses TradingView's ta.rsi(). The boundary condition difference (< vs <=) plus the prepend-zero bias mean the two systems can disagree on entry timing by 1-2 bars on specific RSI crossovers. On a strategy with only 10-12 trades over 17 years, shifting even one trade by 1 bar on a 3x leveraged ETF can change PnL by several percent.

**Risk implication**: The "best-ever" fitness of 2.18 was computed in a system (strategy_engine.py) that does not match the deployment target (TradingView). There is no evidence the RSI Regime would achieve the same results on TradingView.

**Confidence**: 93%
**Severity**: CRITICAL
**Connects to**: R-01, R-02, Data-Integrity #1, #3, #5

---

### CROSS-03: Risk x Vision-Drift — Unguarded Strategy Promotion

**Components**: R-07 (no deployment guardrails), R-08 (validation gap), Vision-Drift #1 (identity metamorphosis), Vision-Drift #2 (S8 violation), Vision-Drift #5 (checklist not applied)

The system has undergone an identity change (from single-strategy Montauk 8.2.1 to multi-strategy optimizer) without updating its governance. The Charter (Section 8) explicitly bans oscillators and mean-reversion, yet the optimizer tested and crowned an RSI-based mean-reversion strategy as "best-ever." The Feature Acceptance Checklist (Section 5) was never applied. The validation framework cannot validate the winner. The deployment pipeline cannot generate the winner's Pine Script.

This is not a single failure — it is a cascade of every governance layer failing simultaneously:

1. **Charter** did not prevent registration of RSI Regime in STRATEGY_REGISTRY
2. **Feature Acceptance Checklist** was never run
3. **Validation** cannot run on the winner (wrong engine)
4. **Parity check** cannot run on the winner (wrong engine)
5. **Deployment** cannot auto-generate Pine Script for the winner
6. **Fitness function** does not penalize Charter violations
7. **Human review** has not caught the violation (31 days of Charter freeze)

**Risk implication**: The entire governance stack from Charter to deployment has a bypass. Any strategy can be registered, optimized, crowned "best-ever," and hand-written as Pine Script with zero automated checks. The current RSI Regime in testing/ has `slippage=0`, `commission_value=0`, no walk-forward validation, no parity check, and violates the governing document. If someone copies it to active/, real capital is at risk.

**Confidence**: 95%
**Severity**: CRITICAL
**Connects to**: R-03, R-07, R-08, Vision-Drift #1-#5

---

### CROSS-04: Risk x Velocity — Zero Safety Net Under High Churn

**Components**: R-05 (zero tests), Velocity #3 (4x rewrites), Velocity #4 (zero tests), Velocity #6 (burst development)

The spike skill has been rewritten 4 times (9.5x churn ratio). Each rewrite is a full-codebase change with zero tests to catch regressions. The burst development pattern (26 idle days, then 22 commits in 3 days) means changes are made under time pressure without safeguards.

In a system that manages trading strategy parameters for a 3x leveraged ETF, this pattern is uniquely dangerous:

- A regression in indicator calculation silently changes which strategies "win"
- A regression in position management silently changes PnL computation
- A regression in the fitness function silently changes what the optimizer selects
- Any of these regressions persist undetected because there are no tests

The montauk_821 wrong-EMA bug (R-02) is almost certainly a regression from one of these rewrites: someone moved from backtest_engine.py (which correctly uses ema_long/500) to strategy_engine.py/strategies.py (which incorrectly uses ema_m/30) and the mapping was wrong. Without tests, nobody noticed.

**Risk implication**: Every rewrite has an unknown probability of introducing bugs like R-02. With 4 rewrites and 0 tests, the expected number of latent bugs is unknowable. The system's outputs cannot be trusted without a comprehensive parity check between the latest code and known-good historical results.

**Confidence**: 88%
**Severity**: HIGH
**Connects to**: R-02, R-05, Velocity #3, #4, #6

---

### CROSS-05: Risk x Data-Integrity — Evolve Run Is Not Optimization

**Components**: R-04 (silent exceptions), Data-Integrity #10 (stagnation detection broken), Architecture #8 (36 seconds)

Combining findings: the evolve.py run that produced the current "best-ever" result was:
- 36 seconds long (0.01 hours)
- 1,330 evaluations across 7 strategies (~190 per strategy)
- 19 generations with population 40
- Running at maximum mutation rate (0.50) from approximately generation 80 onward — but the run only lasted 19 generations, so mutation was at 0.15 the entire time (stag < 30)

Wait — re-examining: with only 19 generations, `stag` = `generation - 0` = `generation`. At generation 19, `stag = 19 < 30`, so mutation rate was 0.15 the entire run. This is actually BELOW the intended adaptive rate. The stagnation detection bug means that on a LONGER run (>80 generations), mutation jumps to 0.50 and stays there permanently, because `_last_improve` is never updated.

**Revised risk assessment**: Short runs (~19 gen) are actually using the intended base rate (0.15). Long runs (>80 gen) degenerate into random search. This means:
- The 54-second result used proper mutation but had laughably few evaluations
- A recommended 8-hour run would use broken mutation for ~99% of its duration

Both scenarios are bad, but for different reasons. The short run found RSI Regime by luck with too few evaluations. A long run would search randomly with too much mutation.

**Confidence**: 90%
**Severity**: HIGH
**Connects to**: R-03, R-04, Data-Integrity #10, Architecture #8

---

## Part 4: Revised Risk Priority Stack

Taking all cross-pollination into account, the revised priority order:

| Priority | Finding | Severity | Why |
|----------|---------|----------|-----|
| 1 | CROSS-03 (Governance Cascade Failure) | CRITICAL | Every safety layer has a bypass; RSI Regime is proof |
| 2 | CROSS-02 (Three-Way Parity Gap) | CRITICAL | No result from any engine can be trusted |
| 3 | R-03+ (RSI Regime Overfitting) | CRITICAL+ | Simultaneously overfitted, ungoverned, unvalidatable, undeployable |
| 4 | R-02 (Wrong EMA in montauk_821) | CRITICAL | Baseline comparison is against a phantom strategy |
| 5 | CROSS-01 (Mutation Death Spiral) | HIGH | Optimizer cannot actually evolve on long runs |
| 6 | R-10 (revised) (DD Penalty Too Weak) | HIGH | Actively promotes ruinous configs |
| 7 | CROSS-04 (Zero Tests + High Churn) | HIGH | Unknown count of latent bugs from 4 rewrites |
| 8 | R-04 (revised) (Silent Exception + Broken Stagnation) | HIGH | Optimizer internals are flying blind |
| 9 | R-06 (Stale Data) | HIGH | 39 days missing; optimizer explicitly disables refresh |
| 10 | R-08 (Validation Gap) | HIGH | Walk-forward only works on the strategy that needs it least |

---

## Part 5: Recommended Immediate Actions (Risk-Ordered)

1. **DO NOT deploy RSI Regime to production.** It violates the Charter, was found in a trivial run, uses divergent RSI, has 75% DD, and has zero validation. Move from testing/ to archive/ or add a prominent warning header.

2. **Fix the montauk_821 EMA cross exit** in strategies.py. Add `ema_l = ind.ema(p.get("long_ema", 500))` and use it for the cross exit. This is a one-line fix that makes the optimizer's baseline actually represent 8.2.1.

3. **Hard-cap max drawdown in fitness function** at 50%. Any config with DD > 50% gets fitness = 0. This prevents the optimizer from promoting ruinous strategies.

4. **Fix stagnation detection** in evolve.py. Replace `getattr(evolve, '_last_improve', {}).get(strat_name, 0)` with an actual dictionary that gets updated when a strategy improves. This is a 3-line fix that makes the optimizer actually adaptive.

5. **Add minimum 5 parity tests** covering indicator calculations (EMA, RSI, ATR) across both engines and against known Pine Script values.
