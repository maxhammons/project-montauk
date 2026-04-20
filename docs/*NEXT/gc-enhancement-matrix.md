# GC Enhancement Matrix — Systematic Addon Testing

*Goal: take the proven golden-cross pre-cross entry and systematically test every plausible addon filter/exit modification to find the next VIX-level improvement.*

---

## Context

The golden cross (gc) pre-cross entry is the engine's proven core. The leaderboard is 20/20 gc_* variants. The single biggest improvement in Montauk's history was adding the **VIX panic circuit breaker** as an exit — it pushed gc_pre_vix from ~16x to ~26x fitness by catching black-swan bears the death cross was too slow for.

This document defines every plausible addon to test next. The approach is **combinatorial**: implement each addon as an independent boolean modifier, then grid-search all combinations on top of the best gc_precross base.

### What the cycle diagnostics tell us

From the champion `gc_strict_vix` (fitness 28.08, 77.29x share, 19 trades):

| Metric | Value | Implication |
|--------|-------|-------------|
| Avg bull capture | 65.6% | Room to capture more upside |
| Avg bear avoidance | 37.2% | **Primary bottleneck** — gets caught in bears |
| "D" exit fires during bulls | 58% | **Biggest leak** — death cross cuts bull gains |
| "V" exit fires during bears | 83% | VIX panic works — model for new addons |
| Misses Bulls #1, #9-12 | 0% capture | EMA(200) warmup too slow for early data |
| Rides through Bears #2-4 | 0% avoidance | Slow EMAs miss 2-6 month bears (1995-1997) |

**Priority order**: Fix the D-exit-in-bull leak (58%) > improve short-bear avoidance (37%) > improve entry timing.

---

## How to use this document

### For a Claude session

Point Claude at this file and say: "implement and test everything in gc-enhancement-matrix.md"

Claude should:

1. **Read this file** to understand all addons and the testing protocol
2. **Implement each addon** as a standalone gc_* variant in `scripts/strategies.py`
3. **Add canonical grids** in `scripts/grid_search.py`
4. **Smoke test** each addon individually (single canonical config, verify signal/trades)
5. **Grid search** all addons: `python scripts/grid_search.py --concepts <new_concepts> --top-n 30`
6. **Run cycle diagnostics** on any that beat the current champion's fitness (28.08)
7. **Report**: which addons improved fitness, which hurt, which were neutral

### Implementation pattern

Every addon is a variant of `gc_precross` or `gc_strict_vix` with ONE additional filter. Name them `gc_<addon_name>`. Each variant should:

- Copy the gc_precross or gc_strict_vix entry logic verbatim
- Add the addon as a filter on entry, exit, or both (as specified)
- Keep the VIX panic circuit breaker (it works, never remove it)
- Have <=6 tunable params (gc base params + addon params)

```python
def gc_<addon>(ind, p):
    """T1: gc_precross + <addon description>.
    Diagnosis: <which weakness this targets>.
    Entry: <base gc entry> + <addon filter if entry-side>.
    Exit: <modified exit logic> + VIX panic."""
```

---

## EXIT ADDONS — Fix the death-cross-in-bull leak

These modify or replace the death cross ("D") exit to reduce false exits during bull markets. This is the highest-impact category.

### E1. XLK trend confirmation on death cross

**Targets**: D exit fires 58% during bulls
**Hypothesis**: TECL's 3x leverage creates death crosses from normal pullbacks that are totally benign on the underlying XLK. If XLK's EMA is still rising, the death cross is noise.
**Implementation**: Only honor the death cross if XLK's EMA(slow) is also declining. If XLK trend is intact, suppress the D exit.
**Data**: `ind.xlk_close` (already available in Indicators)
**Addon params**: `xlk_ema_len` (50, 100, 200) — the EMA period to check on XLK
**Grid**: 3 values = 3x multiplier on base grid

```
Exit rule: (death_cross AND xlk_ema_declining) OR vix_panic
```

### E2. RSI exit gate

**Targets**: D exit fires 58% during bulls
**Hypothesis**: Death cross + RSI > 50 = bull pullback (suppress exit). Death cross + RSI < threshold = real momentum loss (honor exit). RSI is an orthogonal momentum signal that can disambiguate.
**Implementation**: Only honor death cross if RSI is below `rsi_exit_threshold`.
**Data**: `ind.rsi(rsi_len)`
**Addon params**: `rsi_len` (7, 14, 21), `rsi_exit_threshold` (40, 45, 50)
**Grid**: 3 x 3 = 9x multiplier

```
Exit rule: (death_cross AND rsi < threshold) OR vix_panic
```

### E3. Volume-confirmed death cross

**Targets**: D exit fires 58% during bulls
**Hypothesis**: Death cross on expanding volume = real selling conviction. Death cross on declining/normal volume = low-conviction pullback. Volume is the one signal that can't be replicated by price alone.
**Implementation**: Only honor death cross if volume > `vol_mult` x EMA(volume, vol_ema_len).
**Data**: `ind.vol_ema(vol_ema_len)`, `ind.volume`
**Addon params**: `vol_mult` (1.5, 2.0, 2.5), `vol_ema_len` (20, 50)
**Grid**: 3 x 2 = 6x multiplier

```
Exit rule: (death_cross AND volume > vol_mult * vol_ema) OR vix_panic
```

### E4. ATR-scaled death cross buffer

**Targets**: D exit fires 58% during bulls
**Hypothesis**: Fixed 0.2% buffer on the death cross is too rigid. In low-vol bull markets, a wider buffer avoids noise. In high-vol bear markets, a tighter buffer exits faster.
**Implementation**: Replace fixed `sell_buffer` with `atr_buffer_mult * ATR / close * 100`. Death cross fires when `fast < slow * (1 - dynamic_buffer/100)`.
**Data**: `ind.atr(atr_period)`
**Addon params**: `atr_buffer_mult` (0.5, 1.0, 1.5), `atr_period` (14, 20)
**Grid**: 3 x 2 = 6x multiplier

```
Exit rule: (fast < slow * (1 - atr_buffer_mult * atr / close)) OR vix_panic
```

### E5. Gap-widening acceleration filter

**Targets**: D exit fires 58% during bulls
**Hypothesis**: Currently exits when gap < 0 AND gap widening. Slow widening = normal oscillation. Fast/accelerating widening = real trend break. Check second derivative.
**Implementation**: Track gap_delta = gap - prev_gap. Exit only when gap_delta < -threshold (gap widening accelerating). Use absolute or ATR-scaled threshold.
**Addon params**: `accel_threshold` (0.1, 0.5, 1.0) — minimum gap acceleration
**Grid**: 3x multiplier

```
Exit rule: (death_cross AND gap_accel < -threshold) OR vix_panic
```

### E6. ATR trailing stop (replace death cross entirely)

**Targets**: D exit fires 58% during bulls
**Hypothesis**: What if we remove the death cross exit entirely and replace it with a pure ATR trailing stop from peak? The trailing stop adapts to volatility and won't fire during normal bull pullbacks. Already implemented as `gc_atr_trail` — include in the matrix for comparison.
**Addon params**: `atr_period` (7, 14, 20), `atr_mult` (2.0, 2.5, 3.0)
**Grid**: 3 x 3 = 9x multiplier

```
Exit rule: (close < peak - atr_mult * atr) OR vix_panic
(NO death cross at all)
```

---

## EXIT ADDONS — Improve short-bear avoidance

These add new exit signals to catch the 2-6 month bears that the death cross misses. The VIX panic catches black swans; these catch slow bleeds.

### E7. Treasury yield curve inversion exit

**Targets**: Bear avoidance 37%, misses Bears #2-4 (1995-1997)
**Hypothesis**: 10Y-2Y spread inversion precedes every recession. When inverted, tighten all exit logic. When positive, be more tolerant.
**Data**: `ind.treasury_spread`
**Implementation (two modes)**:
- **Mode A (exit trigger)**: Exit immediately when spread < 0 AND death cross has fired within last N bars.
- **Mode B (exit tightener)**: When spread < 0, reduce the death cross buffer to 0 (any cross = exit). When spread > 0, keep normal buffer.
**Addon params**: `curve_mode` (A, B), `lookback` (5, 10, 20) for Mode A
**Grid**: 2 x 3 = 6x multiplier

```
Mode A: (death_cross_within_lookback AND spread < 0) → exit
Mode B: if spread < 0, death_cross_buffer = 0 (instant exit on any cross)
```

### E8. Fed funds rate direction exit

**Targets**: Bear avoidance 37%
**Hypothesis**: When the Fed is actively hiking (fed_funds rising), TECL bears follow. Tighten exits during hike cycles, loosen during cuts.
**Data**: `ind.fed_funds_rate`
**Implementation**: When fed_funds has risen over `rate_lookback` bars, reduce death cross buffer. When declining, widen it.
**Addon params**: `rate_lookback` (20, 50, 100)
**Grid**: 3x multiplier

```
if fed_funds[i] > fed_funds[i - rate_lookback]:  # hiking cycle
    use tighter exit thresholds
else:
    use normal exit thresholds
```

### E9. SGOV relative flow exit

**Targets**: Bear avoidance 37%
**Hypothesis**: Money flowing into SGOV (short treasuries) = risk-off rotation. If SGOV is outperforming TECL over a lookback window, it signals institutional risk-off before price indicators catch it.
**Data**: `ind.sgov_close`
**Implementation**: Compute TECL/SGOV ratio EMA. If ratio declining for N bars AND death cross is close (gap < 0), exit early.
**Addon params**: `sgov_lookback` (20, 50)
**Grid**: 2x multiplier

### E10. Realized vol expansion exit

**Targets**: Bear avoidance 37%
**Hypothesis**: When TECL's own short-term ATR / long-term ATR ratio crosses above a threshold, vol is expanding — leading indicator of regime change on 3x leverage.
**Data**: `ind.atr(short)`, `ind.atr(long)`
**Implementation**: Exit when atr_short / atr_long > `vol_ratio_threshold` regardless of EMA state.
**Addon params**: `atr_short` (7, 14), `atr_long` (50, 100), `vol_ratio_threshold` (1.5, 2.0, 2.5)
**Grid**: 2 x 2 x 3 = 12x multiplier

```
Exit rule: normal_exits OR (atr_short / atr_long > threshold)
```

### E11. Drawdown percentage exit

**Targets**: Bear avoidance 37%
**Hypothesis**: Simple but potentially effective — exit when drawdown from recent peak exceeds a fixed percentage. Different from ATR trailing stop because it's percentage-based (doesn't adapt to vol). May catch slow bleeds the ATR stop misses.
**Addon params**: `dd_pct` (15, 20, 25, 30), `dd_lookback` (50, 100, 200) — window for peak
**Grid**: 4 x 3 = 12x multiplier

```
Exit rule: normal_exits OR (close < peak_over_lookback * (1 - dd_pct/100))
```

---

## ENTRY ADDONS — Better entry timing

Lower priority than exit fixes, but some could improve share accumulation by entering at slightly better prices.

### N1. VIX level entry gate

**Targets**: Entering during already-stressed markets
**Hypothesis**: Currently VIX is exit-only. If VIX > threshold, the market is already stressed — the gc pre-cross signal may be a false start. Delay entry until VIX settles.
**Data**: `ind.vix`
**Addon params**: `entry_vix_max` (20, 25, 30)
**Grid**: 3x multiplier

```
Entry: (normal_gc_precross) AND (vix < entry_vix_max)
```

### N2. ADX trend strength gate

**Targets**: Whipsaw entries in ranging markets
**Hypothesis**: ADX > 20 means a directional trend exists. ADX < 20 means ranging/choppy — the gc_precross will whipsaw. Only enter when trend is established.
**Data**: `ind.adx(adx_len)` (need to add to Indicators — use `_adx` from strategy_engine)
**Addon params**: `adx_len` (7, 14, 20), `adx_threshold` (15, 20, 25)
**Grid**: 3 x 3 = 9x multiplier

```
Entry: (normal_gc_precross) AND (adx > adx_threshold)
```

### N3. XLK momentum confirmation on entry

**Targets**: Entering TECL when underlying isn't trending
**Hypothesis**: If XLK (the underlying) isn't also in an uptrend, TECL's 3x leverage will just amplify noise. Require XLK EMA to be rising before entering TECL.
**Data**: `ind.xlk_close`
**Addon params**: `xlk_ema_len` (50, 100, 200) — can share with E1 if both used
**Grid**: 3x multiplier

```
Entry: (normal_gc_precross) AND (xlk_ema[i] > xlk_ema[i - slope_window])
```

### N4. Post-crash recovery gate

**Targets**: False bottoms after major bears
**Hypothesis**: After a >40% drawdown, the first gc_precross is often a dead cat bounce. Require price to be >N% above the bear trough before entering. Confirms the bottom is real.
**Addon params**: `min_recovery_pct` (15, 20, 30), `crash_threshold` (30, 40, 50)
**Grid**: 3 x 3 = 9x multiplier

```
Entry: (normal_gc_precross) AND (NOT in_crash_recovery OR recovered_enough)
where in_crash_recovery = drawdown_from_ATH > crash_threshold
      recovered_enough = close > recent_low * (1 + min_recovery_pct/100)
```

### N5. Momentum acceleration (second derivative of gap)

**Targets**: Weak pre-cross signals that don't have conviction
**Hypothesis**: Instead of just "gap narrowing for N bars," require the *rate* of narrowing to be increasing (gap closing faster). Sharper convergence = stronger signal, more likely a real trend transition.
**Addon params**: none new (uses existing entry_bars, just modifies the condition)
**Grid**: 0x multiplier (replaces, doesn't add params)

```
Entry: (normal gap narrowing) AND (gap_narrowing_rate > prev_gap_narrowing_rate)
```

### N6. Seasonality filter

**Targets**: Historically weaker May-September period
**Hypothesis**: "Sell in May" has some historical basis on tech. Could suppress entries during May-September unless the signal is very strong (multi-bar confirmed).
**Addon params**: `seasonal_months_off` (May-Sep vs Jun-Sep)
**Grid**: 2x multiplier

```
Entry: (normal_gc_precross) AND (month NOT in seasonal_off OR extra_confirmation)
```

### N7. Volume surge on entry

**Targets**: Low-conviction entries
**Hypothesis**: Pre-cross convergence with above-average volume = buying conviction. Below-average volume = drift without conviction. Require volume confirmation.
**Addon params**: `vol_entry_mult` (1.2, 1.5, 2.0), `vol_ema_len` (20, 50)
**Grid**: 3 x 2 = 6x multiplier

```
Entry: (normal_gc_precross) AND (volume > vol_entry_mult * vol_ema)
```

### N8. MACD zero-line confirmation on entry

**Targets**: Weak/early pre-cross entries that lack momentum confirmation
**Hypothesis**: MACD crossing above zero is an independent bullish signal. Requiring it alongside the gc_precross narrows entries to moments where two different momentum measures agree.
**Data**: Compute MACD(12,26,9) from close — `_ema(cl,12) - _ema(cl,26)`, signal = `_ema(macd,9)`
**Addon params**: none (MACD triple is canonical: 12/26/9)
**Grid**: 1x multiplier (on/off toggle)

```
Entry: (normal_gc_precross) AND (macd > 0)
```

### N9. Bollinger Band squeeze entry confirmation

**Targets**: Entries during low-conviction ranging periods
**Hypothesis**: When Bollinger Band width (stddev/SMA) is at an N-bar low, the market is coiling. A gc_precross during a squeeze has higher breakout conviction than one during wide bands.
**Data**: `ind.stddev(bb_len)`, `ind.sma(bb_len)`
**Addon params**: `bb_len` (14, 20, 50), `squeeze_lookback` (50, 100)
**Grid**: 3 x 2 = 6x multiplier

```
bb_width = stddev / sma
Entry: (normal_gc_precross) AND (bb_width < min(bb_width over squeeze_lookback))
```

### N10. Bullish bar confirmation

**Targets**: Entries on uncertain/bearish bars
**Hypothesis**: Simple but effective — only enter if the entry bar itself is bullish (close > open). Filters out bars where the gc_precross condition is met but the actual bar was a selloff.
**Addon params**: none
**Grid**: 1x multiplier (on/off)

```
Entry: (normal_gc_precross) AND (close > open)
```

### N11. VIX slope entry filter

**Targets**: Entering while fear is still building
**Hypothesis**: Not just VIX level but VIX *direction*. Declining VIX = fear subsiding = better entry. Rising VIX even if below threshold = risk increasing. More nuanced than N1 (level only).
**Data**: `ind.vix`
**Addon params**: `vix_slope_window` (3, 5, 10)
**Grid**: 3x multiplier

```
Entry: (normal_gc_precross) AND (vix[i] < vix[i - vix_slope_window])
```

### N12. Treasury spread positive entry gate

**Targets**: Entering during recession-risk environments
**Hypothesis**: Only enter when 10Y-2Y spread > 0 (no recession signal). Every major TECL bear was preceded or accompanied by yield curve stress. Cheap macro filter.
**Data**: `ind.treasury_spread`
**Addon params**: none
**Grid**: 1x multiplier (on/off)

```
Entry: (normal_gc_precross) AND (treasury_spread > 0)
```

### N13. Multi-horizon return confirmation

**Targets**: Entries where short-term momentum doesn't match medium-term
**Hypothesis**: Require positive returns over both a short and medium horizon. If 20-day return > 0 AND 60-day return > 0, the trend is confirmed at multiple scales. Different from multi_tf_momentum (which failed as standalone) because it's a *filter* on the proven gc_precross, not a standalone signal.
**Addon params**: `short_ret_lb` (10, 20), `med_ret_lb` (50, 100)
**Grid**: 2 x 2 = 4x multiplier

```
Entry: (normal_gc_precross) AND (close > close[i - short_ret_lb]) AND (close > close[i - med_ret_lb])
```

### N14. 50-day high proximity entry gate

**Targets**: Catching falling knives during downtrends
**Hypothesis**: Only enter when price is within N% of its 50-day high. Confirms the uptrend is intact and we're not buying into a decline that happens to have a converging EMA gap.
**Addon params**: `high_proximity_pct` (85, 90, 95), `high_lookback` (50, 100)
**Grid**: 3 x 2 = 6x multiplier

```
Entry: (normal_gc_precross) AND (close > highest(high_lookback) * high_proximity_pct / 100)
```

---

## EXIT ADDONS (continued) — Additional exit signals

### E12. MACD histogram divergence exit

**Targets**: D exit fires 58% during bulls; catching trend exhaustion earlier
**Hypothesis**: When MACD histogram turns negative (MACD crosses below signal line) while price is still elevated, momentum is fading before price follows. Leading indicator of trend breaks.
**Data**: MACD(12,26,9) histogram
**Addon params**: `macd_exit_bars` (2, 3, 5) — consecutive bars of negative histogram
**Grid**: 3x multiplier

```
Exit rule: (macd_histogram < 0 for N bars AND death_cross_gap narrowing) OR vix_panic
```

### E13. Slow EMA slope flattening exit

**Targets**: D exit fires 58% during bulls — replace death cross with slope signal
**Hypothesis**: Instead of waiting for fast < slow (death cross), exit when the slow EMA's slope goes flat or negative. Catches trend exhaustion before the cross happens, avoiding the lag that makes D fire too late.
**Addon params**: `slope_exit_window` (5, 10, 20), `slope_threshold` (0, -0.001)
**Grid**: 3 x 2 = 6x multiplier

```
Exit rule: (slow_ema_slope < slope_threshold over slope_exit_window) OR vix_panic
```

### E14. Consecutive bearish bars exit

**Targets**: Bear avoidance 37% — catching sustained selling pressure
**Hypothesis**: N consecutive bars where close < open signals persistent selling. Unlike the death cross (lagging averages), this reads real-time price action.
**Addon params**: `bear_bars` (3, 5, 7)
**Grid**: 3x multiplier

```
Exit rule: normal_exits OR (N consecutive bars close < open)
```

### E15. Gap-down exit

**Targets**: Bear avoidance 37% — catching overnight shock events
**Hypothesis**: If today's open is significantly below yesterday's close (gap down > threshold), exit immediately. Gap downs on TECL are devastating due to 3x leverage. This is complementary to VIX panic (which uses VIX level, not price gaps).
**Addon params**: `gap_down_pct` (3.0, 5.0, 8.0) — minimum gap-down % to trigger
**Grid**: 3x multiplier

```
Exit rule: normal_exits OR (open < prev_close * (1 - gap_down_pct / 100))
```

### E16. Relative strength vs QQQ deterioration exit

**Targets**: D exit fires 58% during bulls; bear avoidance
**Hypothesis**: If the TECL/QQQ ratio starts declining, 3x leverage is actively destroying value vs the underlying index. Exit before the EMA death cross catches up. Uses cross-asset data that's uncorrelated with the EMA signal.
**Data**: Requires QQQ close merged into the dataframe (similar to XLK)
**Addon params**: `ratio_lookback` (10, 20, 50), `ratio_ema` (20, 50)
**Grid**: 3 x 2 = 6x multiplier

```
Exit rule: normal_exits OR (tecl/qqq ratio EMA declining for ratio_lookback bars)
```

### E17. Profit-lock trailing tightener

**Targets**: Giving back gains during extended bull topping patterns
**Hypothesis**: After a trade gains > N%, tighten the ATR trailing stop multiplier (e.g., from 3x to 1.5x ATR). Locks in gains on big winners instead of riding them back down to a wide stop. Asymmetric: let small trades breathe, protect big wins.
**Addon params**: `profit_lock_pct` (50, 100, 200) — profit threshold to tighten, `tight_atr_mult` (1.0, 1.5, 2.0)
**Grid**: 3 x 3 = 9x multiplier

```
if trade_pnl > profit_lock_pct:
    trailing_stop = peak - tight_atr_mult * atr  (tighter)
else:
    trailing_stop = peak - normal_atr_mult * atr  (wider)
```

### E18. Time-in-trade maximum

**Targets**: Holding through long topping patterns
**Hypothesis**: After N bars in a single trade, if the slow EMA slope is no longer positive, exit. Prevents riding through extended distribution / topping patterns where the death cross hasn't fired yet but the trend is clearly exhausted.
**Addon params**: `max_bars` (200, 300, 500), requires slow EMA slope check
**Grid**: 3x multiplier

```
Exit rule: normal_exits OR (bars_in_trade > max_bars AND slow_ema_slope <= 0)
```

### E19. VIX term structure proxy exit

**Targets**: Bear avoidance — detecting fear buildup before it spikes
**Hypothesis**: VIX above its own EMA = fear is building relative to recent norm. This is a regime signal: VIX below its EMA = complacent (hold), VIX above = cautious (tighten exits). Different from the VIX panic (which needs VIX > 30 + 75% spike — too extreme for slow bears).
**Data**: `ind.vix`, compute vix_ema internally
**Addon params**: `vix_ema_len` (20, 50, 100), `vix_above_pct` (10, 20) — VIX must be >N% above its EMA
**Grid**: 3 x 2 = 6x multiplier

```
Exit rule: (death_cross AND vix > vix_ema * (1 + vix_above_pct/100)) OR vix_panic
```

---

## STRUCTURAL ADDONS — Modify the trade lifecycle itself

### S1. Adaptive cooldown

**Targets**: Re-entry timing after exits
**Hypothesis**: Fixed cooldown (2-5 bars) is too rigid. After exiting in high-vol (bear), wait longer (dust settling). After exiting in low-vol (normal pullback), re-enter quickly. Scale cooldown by ATR.
**Addon params**: `base_cooldown` (2, 5), `vol_cooldown_mult` (1, 2, 3) — multiply by atr_short/atr_long ratio
**Grid**: 2 x 3 = 6x multiplier

```
cooldown = base_cooldown * max(1, int(atr_short / atr_long * vol_cooldown_mult))
```

### S2. Bear regime memory

**Targets**: Getting sucked back into bear-market rallies
**Hypothesis**: After a major bear (>50% drawdown from ATH), require extra entry confirmation for the next N bars. Double the entry_bars requirement. Avoids the classic trap of buying bear-market rallies that fail.
**Addon params**: `bear_memory_bars` (50, 100, 200), `bear_threshold_pct` (40, 50)
**Grid**: 3 x 2 = 6x multiplier

```
if recent_drawdown_from_ATH > bear_threshold:
    required_entry_bars = entry_bars * 2  (extra confirmation)
else:
    required_entry_bars = entry_bars  (normal)
```

### S3. Asymmetric re-entry after VIX exit

**Targets**: VIX panic exits are correct but re-entry timing is poor
**Hypothesis**: After a VIX panic exit, the market is in crisis mode. Don't re-enter on the normal gc_precross — require VIX to actually drop below a re-entry threshold first. The gc_precross may fire during a dead cat bounce while VIX is still elevated.
**Addon params**: `vix_reentry_below` (20, 25, 30)
**Grid**: 3x multiplier

```
if last_exit_reason == "V":
    Entry: (normal_gc_precross) AND (vix < vix_reentry_below)
else:
    Entry: (normal_gc_precross)  # normal
```

---

## COMBO ADDONS — Multiple filters stacked

After testing each addon individually, test the best-performing ones in combination.

### C1. XLK exit + VIX entry gate

The two most promising independent addons combined:
```
Entry: gc_precross + VIX < 25
Exit: (death_cross AND xlk_declining) OR vix_panic
```

### C2. RSI exit gate + treasury curve tightener

Orthogonal exit signals stacked:
```
Exit: (death_cross AND rsi < 45 AND (spread < 0 → buffer=0)) OR vix_panic
```

### C3. XLK exit + realized vol exit + VIX panic (triple exit)

Three independent bear-detection mechanisms:
```
Exit: (death_cross AND xlk_declining) OR (vol_ratio > 2.0) OR vix_panic
```

### C4. Full stack: best entry + best exit addons

Once individual results are in, combine the top-performing entry addon with the top-performing exit addon.

### C5. XLK exit + profit-lock tightener

Address both the D-in-bull problem AND the "give back gains" problem:
```
Exit: (death_cross AND xlk_declining) OR (if profit > N%, tight trailing stop) OR vix_panic
```

### C6. RSI exit gate + VIX term structure proxy

Two orthogonal momentum-loss detectors:
```
Exit: (death_cross AND rsi < 45 AND vix > vix_ema * 1.1) OR vix_panic
```

### C7. Best exit addon + bear regime memory + adaptive cooldown

Combine the best exit filter with smarter re-entry timing:
```
Exit: best_from_phase1
Entry: gc_precross + (if post-bear, require 2x confirm) + (adaptive cooldown)
```

### C8. Full defense stack

Every proven exit filter layered:
```
Exit: (death_cross gated by best filter) OR (vol expansion) OR (profit lock) OR vix_panic
Entry: gc_precross + VIX entry gate + post-crash recovery gate
```

---

## Testing protocol

### Phase 1: Individual addon testing

For each addon (E1-E11, N1-N7):

1. Implement as `gc_<addon_id>` in `scripts/strategies.py`
2. Add grid in `scripts/grid_search.py` — base gc grid x addon grid
3. Grid search: `python scripts/grid_search.py --concepts gc_<addon_id> --top-n 10`
4. Record: best fitness, best share_multiple, number of charter-passing combos

**Success criterion**: fitness > 28.08 (current champion) OR share_multiple > 77.29x

### Phase 2: Diagnostic analysis

For any addon that beats the champion:

1. Run `cycle_diagnostics.diagnose_strategy()` on the best combo
2. Compare bull capture, bear avoidance, and exit-reason-in-bull stats vs champion
3. Verify the addon actually fixed the targeted weakness (not just lucky params)

### Phase 3: Combo testing

Take the top 3 individual addons and test all 2-way and 3-way combinations:

1. Implement combo variants
2. Grid search
3. Validate through full pipeline

### Phase 4: Validation

Any candidate that survives Phase 1-3:

1. Full tier-routed validation via `grid_search.py --top-n 30`
2. Walk-forward across 4 time windows
3. Cross-asset on TQQQ + QQQ
4. Must beat champion on fitness (not just share_multiple)

---

## Addon inventory

| Category | IDs | Count | Description |
|----------|-----|-------|-------------|
| Exit — fix D-in-bull | E1-E6 | 6 | Modify/replace death cross to stop cutting bull gains |
| Exit — bear avoidance | E7-E11 | 5 | New exit signals for 2-6 month bears |
| Exit — additional | E12-E19 | 8 | MACD divergence, slope flattening, gap-down, profit lock, etc. |
| Entry — filters | N1-N14 | 14 | VIX gate, ADX, XLK, post-crash, MACD, BB squeeze, etc. |
| Structural — lifecycle | S1-S3 | 3 | Adaptive cooldown, bear memory, VIX re-entry |
| Combos | C1-C8 | 8 | Stacked multi-addon variants |
| **TOTAL** | | **44** | |

## Expected outcome

The VIX panic exit was a ~60% fitness improvement. Realistically, the next addon will be smaller — maybe 5-15%. The most likely winners:

1. **E1 (XLK exit confirmation)** — directly addresses the 58% D-in-bull problem with an orthogonal signal we already have
2. **E2 (RSI exit gate)** — fast, simple, orthogonal to EMAs, 14-bar warmup
3. **E17 (profit-lock tightener)** — addresses the "give back gains" problem on big winners
4. **E10 (realized vol exit)** — catches slow bears the death cross misses
5. **E19 (VIX term structure proxy)** — subtler fear detection than the VIX panic threshold
6. **N1 (VIX entry gate)** — simple, prevents entering into stressed markets
7. **S3 (asymmetric VIX re-entry)** — fixes the post-panic re-entry timing problem

The least likely to help:
- **N6 (seasonality)** — too crude, likely overfits to historical calendar patterns
- **E8 (fed funds)** — changes too slowly to matter at bar-level resolution
- **E9 (SGOV flow)** — SGOV data only starts 2020, too short for validation
- **E18 (time-in-trade)** — arbitrary cutoff, could hurt the best trades which are long holds

---

## Reference: Current champion params

```
gc_strict_vix  fitness=28.08  share=77.29x  trades=19  tpy=0.6
params: fast_ema=90, slow_ema=200, slope_window=3, entry_bars=2, cooldown=2
```

## Reference: Available data in Indicators

| Field | Source | Coverage |
|-------|--------|----------|
| `close, open, high, low, volume` | TECL.csv | 1993-2026 |
| `vix` | VIX.csv merged | 1993-2026 |
| `treasury_spread` | treasury-spread-10y2y.csv | 1976-2026 (if merged) |
| `fed_funds_rate` | fed-funds-rate.csv | 1954-2026 (if merged) |
| `xlk_close` | XLK.csv | 1998-2026 (if merged) |
| `sgov_close` | SGOV.csv | 2020-2026 (if merged) |

Note: `treasury_spread`, `fed_funds_rate`, `xlk_close`, and `sgov_close` require merging into the TECL dataframe before Indicators can see them. The `data.py` loader or `spike_runner.py` handles this. Verify the merge is happening for each data source before testing addons that depend on it.
