# /spike Session Report — 2026-04-02

**Session duration:** ~7.4 hours  
**Baseline:** Montauk 8.2.1 defaults (RS=0.548, MAR=0.525, vs_bah=0.922×)  
**Goal:** Improve Regime Score; achieve vs_bah_multiple > 1.0  

---

## Session Result: GOAL ACHIEVED

**Primary recommendation: Combo G**  
`sell_cooldown_bars=8, sell_confirm_bars=1, atr_period=50, enable_vol_exit=True, vol_spike_mult=2.3`

| Metric | 8.2.1 Baseline | Combo G | Change |
|--------|---------------|---------|--------|
| Regime Score | 0.548 | **0.603** | +10.1% |
| Bull Capture | 0.555 | 0.541 | -2.5% |
| Bear Avoidance | 0.541 | **0.665** | +22.9% |
| vs_bah Multiple | 0.922× | **1.135×** | +23.1% |
| MAR | 0.525 | **0.554** | +5.5% |
| CAGR | 33.9% | **35.8%** | +5.6% |
| Max Drawdown | 64.6% | 64.6% | flat |
| Trades/yr | 1.1 | 1.4 | within floor |
| Avg Bars Held | 180 | 142 | within floor |
| False Signal Rate | 5.9% | **0.0%** | improved |

**Validation:** PASS — all 4 walk-forward windows improve RS (+8.9% avg)  
**Bootstrap:** 39% percentile (not significant — expected for timing params)

---

## Walk-Forward Window Results (Combo G)

| Window | Baseline RS | Candidate RS | Change |
|--------|------------|--------------|--------|
| walk_forward_0 | 0.530 | 0.560 | +5.7% ✓ |
| walk_forward_1 | 0.546 | 0.588 | +7.7% ✓ |
| walk_forward_2 | 0.571 | 0.609 | +6.7% ✓ |
| walk_forward_3 | 0.548 | 0.603 | +10.0% ✓ |
| 2020_meltup | 0.625 | 0.706 | +13.0% ✓ |
| 2021_2022_bear | 0.462 | 0.509 | +10.2% ✓ |
| 2023_rebound | 0.643 | 0.643 | flat |
| 2024_onward | 0.397 | **0.496** | +24.9% ✓ |

---

## Candidate Progression

| Label | Params | RS | vs_bah | Notes |
|-------|--------|----|--------|-------|
| Baseline | 8.2.1 defaults | 0.548 | 0.922× | — |
| Combo A | cooldown=8 | 0.562 | 0.922× | Single improvement, WF PASS |
| Combo B | cooldown=8, confirm=1 | 0.564 | 0.922× | All 4 WF windows improve |
| Combo E | +atr_period=50 | 0.570 | 0.829× | 2024_onward improves |
| Combo F | +vol_exit mult=2.5 | 0.575 | 0.837× | 3 vol exits, robust |
| **Combo G** | +vol_exit mult=2.3 | **0.603** | **1.135×** | **Session winner** |

---

## Conservative Fallback: Combo F (8.3)

`sell_cooldown_bars=8, sell_confirm_bars=1, atr_period=50, enable_vol_exit=True, vol_spike_mult=2.5`

- RS=0.575, vs_bah=0.837×, MAR=0.511
- All 4 WF windows improve
- Plateau width ≥ 1 for vol_spike_mult (2.5 fires 3 times; at 3.0 reverts)
- No MAR issues in any named window
- **Recommended if vs_bah < 1.0 is acceptable in exchange for cleaner bear-window behavior**

---

## Cautions and Risk Flags

### Combo G — Narrow vol_spike_mult Plateau
- mult=2.3 fires vol exit 8 times (out of 20 trades); mult=2.5 fires only 3 times
- The 5 extra exits at 2.3 vs 2.5 are specific historical events near the threshold boundary
- **Plateau width = 1** for the vol spike improvement — fragile to small parameter shifts
- Tested range: 1.5 (63 trades/yr — FAIL), 2.0 (29 trades), 2.3 (20 trades), 2.5 (18 trades), 3.0 (16 trades)

### Combo G — 2021_2022_bear MAR Negative
- In the 2021-2022 bear window: CAGR = -5.6% (vs baseline +4.7%)
- RS improves (0.462 → 0.509) because bear avoidance improves, but vol spike exits trigger re-entries into continued downtrend
- 5 trades in that window vs 2 in baseline
- Increasing sell_cooldown to 10 does not fix this (structural to vol exit behavior in that period)

### General (all combos)
- ~18-20 trades over 16 years — small sample; each regime transition is highly weighted
- >+10% RS improvement over baseline warrants skepticism (anti-overfitting rule flags >20%)
- Bootstrap not informative for timing params (same trades, reordered)

---

## Pine Script Changes (apply to 8.2.1)

### Combo G (9.0-candidate) — diff file: `remote/diff-2026-04-02-9.0-candidate.txt`

**Changed parameters (already in 8.2.1 inputs):**
```
sellCooldownBars   2 → 8
sellConfirmBars    2 → 1
atrPeriod         40 → 50
```

**New parameters (must be added to Pine Script manually):**
```pine
// Group 17 — Volume Spike Exit
enable_vol_exit = input.bool(true, "Enable Vol Spike Exit", group="Vol Spike Exit")
vol_spike_mult  = input.float(2.3, "Vol Spike Multiplier", step=0.1, group="Vol Spike Exit")
vol_spike_len   = input.int(20, "Vol EMA Length", group="Vol Spike Exit")
```

**Exit logic to add (after EMA cross exit block):**
```pine
// Vol Spike Exit
vol_ema = ta.ema(volume, vol_spike_len)
is_vol_exit = enable_vol_exit and strategy.position_size > 0 and
              volume > vol_ema * vol_spike_mult and close < close[1]
if is_vol_exit
    strategy.close("Long", comment="Vol Spike Exit")
```

### Combo F (8.3-conservative) — diff file: `remote/diff-2026-04-02-8.3-conservative.txt`

Same Pine changes except `vol_spike_mult = 2.5`

---

## New Python Engine Capabilities Added This Session

6 new parameter groups implemented in `scripts/backtest_engine.py`:

| Group | Parameters | Purpose |
|-------|-----------|---------|
| 12 | `enable_atr_ratio_filter`, `atr_ratio_len`, `atr_ratio_max` | Entry filter: ATR/ATR-EMA ratio |
| 13 | `enable_adx_filter`, `adx_len`, `adx_min` | Entry filter: ADX trend strength |
| 14 | `enable_roc_filter`, `roc_len` | Entry filter: rate-of-change momentum |
| 15 | `enable_bear_guard`, `bear_guard_pct`, `bear_guard_lookback` | Entry gate: rolling equity drawdown |
| 16 | `enable_asymmetric_exit`, `asym_atr_ratio_threshold`, `asym_exit_multiplier` | Tighter ATR exit in high-vol regimes |
| 17 | `enable_vol_exit`, `vol_spike_len`, `vol_spike_mult` | Exit: high volume + price decline |

Bug fixes:
- Integer parameter casting for sweep/grid now uses dataclass type introspection (`dataclasses.fields()`) — fixes `atr_period` and `slope_lookback` float-slice errors
- Bear guard rolling-window fix (was using all-time peak, now uses `bear_guard_lookback` window)

---

## Files Written This Session

| File | Description |
|------|-------------|
| `remote/spike-2026-04-02.md` | This report |
| `remote/best-ever.json` | Updated to Combo G (RS=0.603, vs_bah=1.135×) |
| `remote/diff-2026-04-02-9.0-candidate.txt` | Pine Script diff for Combo G |
| `remote/diff-2026-04-02-8.3-conservative.txt` | Pine Script diff for Combo F |
| `scripts/backtest_engine.py` | +6 new parameter groups, bug fixes |
| `scripts/run_optimization.py` | Integer casting fix via dataclass introspection |

---

## Recommendation

**Deploy Combo G (9.0-candidate) for forward testing in TradingView.**  
The vol spike exit at mult=2.3 is the key new parameter — set it carefully. If live forward tests show poor 2021-2022-style bear behavior (whipsaw re-entries after vol exits), fall back to Combo F (mult=2.5) which is more conservative but well-validated.

The `sell_cooldown_bars=8, sell_confirm_bars=1, atr_period=50` parameters (Combo E core) have the broadest plateau support and are recommended regardless of vol exit multiplier choice.
