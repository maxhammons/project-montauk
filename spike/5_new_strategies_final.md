# 5 New Strategies for Project Montauk — Final Selection

Selected from two independent ideation runs (Claude Opus + Codex) on 2026-04-06.
Criteria: novelty vs existing roster, TECL-specific fit, trade frequency, param manageability, regime-score alignment.

---

## 1. `flow_exhaustion_reclaim`

**Source:** Codex

**Core thesis**

TECL bear endings are usually panic-volume events followed by a quiet but persistent accumulation phase before price fully heals. This strategy buys only when money flow recovers from capitulation, on-balance volume has already turned constructive, and realized volatility has stopped expanding. That should filter out thin-volume RSI-style bounces and focus on true post-crash regime repair.

**Entry logic**

- `mfi = ind.mfi(p.get("mfi_len", 14))`
- `obv = ind.obv()`
- `obv_ema = ind.ema_of("obv", obv, p.get("obv_ema_len", 55))`
- `tema = ind.tema(p.get("tema_len", 120))`
- `tema_slope = ind.slope("flow_tema", tema, p.get("tema_slope_lb", 10))`
- `vol_short = ind.realized_vol(p.get("vol_short", 15))`
- `vol_long = ind.realized_vol(p.get("vol_long", 60))`
- Enter when all are true:
  - `mfi[i-1] < entry_mfi` and `mfi[i] >= entry_mfi`
  - `obv[i] > obv_ema[i]`
  - `tema_slope[i] > 0`
  - `vol_long[i] > 0` and `vol_short[i] / vol_long[i] < vol_ratio_max`

**Exit logic**

1. `mfi[i] >= exit_mfi` -> `labels[i] = "MFI Overbought"`
2. `obv[i] < obv_ema[i] and ind.close[i] < ind.ema(p.get("exit_ema_len", 80))[i]` -> `labels[i] = "Flow Breakdown"`
3. `vol_long[i] > 0 and vol_short[i] / vol_long[i] > vol_exit_ratio` -> `labels[i] = "Vol Spike"`

**Why it's different**

No tested strategy uses MFI or OBV in live entry logic. Unlike `rsi_vol_regime`, the oversold trigger is price-volume exhaustion rather than price-only oscillator recovery, and unlike `recovery_momentum`, it does not rely on a fixed crash-depth/bounce template.

**Expected trade frequency:** 0.6–1.2 trades/year.

**Risk assessment**

Slow distribution phases can leave OBV elevated longer than price deserves, so the strategy may exit later than ideal in rolling tops. It also depends on volume quality, which matters more here than in the current RSI-heavy winners.

**Parameter space**

- `mfi_len`: `(10, 24, 2, int)`
- `entry_mfi`: `(20, 45, 5, float)`
- `exit_mfi`: `(70, 90, 5, float)`
- `obv_ema_len`: `(30, 100, 10, int)`
- `tema_len`: `(80, 180, 20, int)`
- `tema_slope_lb`: `(5, 20, 5, int)`
- `vol_short`: `(10, 25, 5, int)`
- `vol_long`: `(40, 90, 10, int)`
- `vol_ratio_max`: `(0.75, 1.0, 0.05, float)`
- `vol_exit_ratio`: `(1.2, 1.8, 0.1, float)`
- `exit_ema_len`: `(50, 120, 10, int)`
- `cooldown`: `(5, 20, 5, int)`

---

## 2. `stoch_drawdown_recovery`

**Source:** Claude Opus

**Core thesis**

TECL experiences massive 40–80% drawdowns. This strategy explicitly measures the drawdown from the highest high over the last year. It allows entries *only* if TECL has fallen deeply or if it's securely above a long-term trend. It uses the Slow Stochastic crossover from extreme oversold to catch the pivot, which is smoother than RSI.

**Entry logic**

- Calculate Drawdown: `dd = (cl[i] - ind.highest(dd_lookback)[i]) / ind.highest(dd_lookback)[i] * 100`
- Context filter: `dd <= dd_thresh` OR `cl[i] > ind.ema(trend_len)[i]`
- Stoch crossover: `stoch_k[i-1] <= stoch_d[i-1]` AND `stoch_k[i] > stoch_d[i]`
- Stoch level filter: `stoch_k[i] < entry_stoch`

**Exit logic**

- Primary: `stoch_k[i] >= exit_stoch` (Stoch Overbought)
- Secondary: `cl[i] < cl[i-1] - ind.atr(atr_period)[i] * atr_mult` (ATR Shock)

**Why it's different**

Introduces explicit drawdown-aware logic to the entry criteria (`ind.highest()`), ensuring the system handles a 40% structural crash differently than a 5% dip. Utilizes the Slow Stochastic oscillator (`stoch_k` and `stoch_d`), which provides a cleaner, lagged signal than RSI to avoid false starts.

**Expected trade frequency:** 1.0–2.0 trades/year.

**Risk assessment**

The 252-day highest high lookback might miss trades if the market grinds up slowly and doesn't trigger the DD threshold, which is why the trend EMA bypass is critical.

**Parameter space**

- `dd_lookback`: `(100, 300, 50, int)`
- `dd_thresh`: `(-50.0, -20.0, 5.0, float)`
- `stoch_len`: `(14, 40, 4, int)`
- `smooth_k`: `(3, 10, 2, int)`
- `smooth_d`: `(3, 10, 2, int)`
- `entry_stoch`: `(15, 35, 5, float)`
- `exit_stoch`: `(70, 90, 5, float)`
- `trend_len`: `(100, 200, 25, int)`
- `atr_period`: `(15, 40, 5, int)`
- `atr_mult`: `(2.5, 5.0, 0.5, float)`

---

## 3. `williams_midline_reclaim`

**Source:** Codex

**Core thesis**

The best TECL washout entries often happen after downside momentum has already broken, but before the move becomes a full breakout. Instead of buying near the channel floor like `mean_revert_channel`, this strategy waits for Williams %R to escape deep oversold and for price to reclaim the Donchian midpoint. That should trade fewer, higher-conviction regime transitions.

**Entry logic**

- `wr = ind.willr(p.get("willr_len", 21))`
- `don_mid = ind.donchian_mid(p.get("channel_len", 60))`
- `trend_ema = ind.ema(p.get("trend_len", 150))`
- `vol_short = ind.realized_vol(p.get("vol_short", 15))`
- `vol_long = ind.realized_vol(p.get("vol_long", 60))`
- Enter when all are true:
  - `wr[i-1] < entry_wr` and `wr[i] >= entry_wr`
  - `ind.close[i] > don_mid[i]`
  - `ind.close[i] > trend_ema[i]`
  - `vol_long[i] > 0` and `vol_short[i] / vol_long[i] < vol_ratio_max`

**Exit logic**

1. `wr[i] >= exit_wr` -> `labels[i] = "Williams Overbought"`
2. `ind.close[i] < don_mid[i] and wr[i] < rebreak_wr` -> `labels[i] = "Midline Lost"`
3. `vol_long[i] > 0 and vol_short[i] / vol_long[i] > vol_exit_ratio` -> `labels[i] = "Vol Spike"`

**Why it's different**

It is not a lower-channel bounce strategy, not an RSI oversold strategy, and not the removed `donchian_trend` price-breakout idea. The distinctive piece is buying the midpoint reclaim after momentum damage has already reversed, using Williams %R rather than RSI or ROC.

**Expected trade frequency:** 0.6–1.4 trades/year.

**Risk assessment**

Fast V-bottoms can leave the strategy waiting for a midline reclaim after a large chunk of the first leg is gone. In extended sideways recoveries, Williams %R can oscillate around the entry threshold and create delayed entries.

**Parameter space**

- `willr_len`: `(14, 34, 4, int)`
- `entry_wr`: `(-90.0, -60.0, 5.0, float)`
- `exit_wr`: `(-20.0, -5.0, 5.0, float)`
- `rebreak_wr`: `(-70.0, -40.0, 5.0, float)`
- `channel_len`: `(40, 100, 10, int)`
- `trend_len`: `(100, 200, 25, int)`
- `vol_short`: `(10, 25, 5, int)`
- `vol_long`: `(40, 90, 10, int)`
- `vol_ratio_max`: `(0.75, 1.0, 0.05, float)`
- `vol_exit_ratio`: `(1.2, 1.8, 0.1, float)`
- `cooldown`: `(5, 20, 5, int)`

---

## 4. `cci_flow_reacceleration`

**Source:** Codex

**Core thesis**

CCI is useful on TECL because it measures statistical displacement, not just bounded oscillator state. The opportunity here is not simple oversold recovery; it is re-acceleration after a washed-out correction, but only when participation is expanding again. That targets the "second derivative" turn where a new bull leg starts to gather sponsorship.

**Entry logic**

- `cci = ind.cci(p.get("cci_len", 30))`
- `trend_ema = ind.ema(p.get("trend_len", 125))`
- `tema = ind.tema(p.get("tema_len", 100))`
- `tema_slope = ind.slope("cci_tema", tema, p.get("tema_slope_lb", 10))`
- `vol_fast = ind.vol_ema(p.get("vol_fast_len", 10))`
- `vol_slow = ind.vol_ema(p.get("vol_slow_len", 40))`
- Enter when all are true:
  - `cci[i-1] < entry_cci` and `cci[i] >= entry_cci`
  - `ind.close[i] > trend_ema[i]`
  - `tema_slope[i] > 0`
  - `vol_slow[i] > 0` and `vol_fast[i] / vol_slow[i] > volume_ratio_min`

**Exit logic**

1. `cci[i] >= exit_cci` -> `labels[i] = "CCI Overheat"`
2. `cci[i] < fail_cci and ind.close[i] < trend_ema[i]` -> `labels[i] = "CCI Failure"`
3. `ind.close[i] < ind.close[i-1] - ind.atr(p.get("atr_period", 20))[i] * atr_mult` -> `labels[i] = "ATR Shock"`

**Why it's different**

This is not `roc_momentum`, not `macd_zero_cross`, and not an RSI variant. It uses CCI for mean-deviation re-acceleration and a volume-EMA expansion test to demand renewed participation, which none of the tested strategies currently do.

**Expected trade frequency:** 0.8–2.0 trades/year.

**Risk assessment**

CCI can snap around violently in chop, so the volume and trend gates have to do real work. The volume expansion requirement may also bias the strategy toward higher-volatility rebounds, which can help entries but sometimes hurt drawdown.

**Parameter space**

- `cci_len`: `(20, 50, 5, int)`
- `entry_cci`: `(-150.0, -25.0, 25.0, float)`
- `exit_cci`: `(100.0, 250.0, 25.0, float)`
- `fail_cci`: `(-50.0, 25.0, 25.0, float)`
- `trend_len`: `(100, 175, 25, int)`
- `tema_len`: `(80, 140, 20, int)`
- `tema_slope_lb`: `(5, 20, 5, int)`
- `vol_fast_len`: `(5, 20, 5, int)`
- `vol_slow_len`: `(30, 60, 10, int)`
- `volume_ratio_min`: `(1.0, 1.5, 0.1, float)`
- `atr_period`: `(10, 30, 5, int)`
- `atr_mult`: `(2.5, 5.0, 0.5, float)`
- `cooldown`: `(5, 20, 5, int)`

---

## 5. `accumulation_breakout`

**Source:** Codex

**Core thesis**

The existing `breakout` strategy proves TECL can pay for buying strength, but its weakness is that price-only highs on a leveraged ETF are easy to fake. This version only accepts a breakout when the move is also supported by accumulation and fresh participation. It then exits on structural distribution rather than a blind percentage trailing stop.

**Entry logic**

- `don_high = ind.donchian_upper(p.get("breakout_len", 120))`
- `trend_ema = ind.ema(p.get("trend_len", 150))`
- `obv = ind.obv()`
- `obv_ema = ind.ema_of("accum_obv", obv, p.get("obv_ema_len", 55))`
- `vol_fast = ind.vol_ema(p.get("vol_fast_len", 10))`
- `vol_slow = ind.vol_ema(p.get("vol_slow_len", 40))`
- Enter when all are true:
  - `ind.close[i] >= don_high[i] * breakout_buffer`
  - `ind.close[i] > trend_ema[i]`
  - `obv[i] > obv_ema[i]`
  - `vol_slow[i] > 0` and `vol_fast[i] / vol_slow[i] > volume_ratio_min`

**Exit logic**

1. `ind.close[i] < ind.donchian_mid(p.get("exit_len", 80))[i] and obv[i] < obv_ema[i]` -> `labels[i] = "Distribution Break"`
2. `ind.mfi(p.get("mfi_len", 14))[i] >= exit_mfi` -> `labels[i] = "MFI Overbought"`
3. `ind.close[i] < trend_ema[i] * (1 - trend_buffer / 100)` -> `labels[i] = "Below Trend"`

**Why it's different**

This is materially different from `breakout` and the older `donchian_trend`. The current breakout entry is price-only and exits via trailing stop/ATR. This proposal requires accumulation confirmation on the way in and distribution confirmation on the way out, which is a different thesis entirely.

**Expected trade frequency:** 0.5–1.2 trades/year.

**Risk assessment**

Strong low-volume breakouts can be missed entirely, especially right after crash lows when volume often normalizes before price fully escapes. MFI-based exits may also take profits earlier than ideal in secular bull legs if the threshold is set too low.

**Parameter space**

- `breakout_len`: `(80, 180, 20, int)`
- `breakout_buffer`: `(0.98, 1.0, 0.01, float)`
- `trend_len`: `(100, 200, 25, int)`
- `obv_ema_len`: `(30, 100, 10, int)`
- `vol_fast_len`: `(5, 20, 5, int)`
- `vol_slow_len`: `(30, 60, 10, int)`
- `volume_ratio_min`: `(1.0, 1.6, 0.1, float)`
- `exit_len`: `(50, 100, 10, int)`
- `mfi_len`: `(10, 24, 2, int)`
- `exit_mfi`: `(75, 90, 5, float)`
- `trend_buffer`: `(0.0, 4.0, 0.5, float)`
- `cooldown`: `(5, 20, 5, int)`

---

## Selection Summary

| # | Strategy | Source | Oscillator | Novel Signal | Entry Thesis | Est. Trades/Yr |
|---|----------|--------|-----------|-------------|-------------|----------------|
| 1 | `flow_exhaustion_reclaim` | Codex | MFI | OBV + vol ratio | Capitulation exhaustion | 0.6–1.2 |
| 2 | `stoch_drawdown_recovery` | Claude | Stochastic | Drawdown depth | Crash-aware dip buy | 1.0–2.0 |
| 3 | `williams_midline_reclaim` | Codex | Williams %R | Donchian midpoint | Midpoint reclaim after damage | 0.6–1.4 |
| 4 | `cci_flow_reacceleration` | Codex | CCI | Volume expansion | Re-acceleration with participation | 0.8–2.0 |
| 5 | `accumulation_breakout` | Codex | — | OBV + vol expansion | Volume-confirmed breakout | 0.5–1.2 |

**Diversity:** 4 different oscillators (MFI, Stochastic, Williams %R, CCI — none RSI). 3 entry theses (capitulation recovery, midpoint reclaim, confirmed breakout). All use indicators absent from the kept roster. No redundancy with the top-3 RSI strategies.
