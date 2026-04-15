# 10 New Strategy Hypotheses for Project Montauk (TECL)

This document outlines 10 high-quality strategy concepts designed specifically for TECL (a 3x leveraged ETF) to be tested in the `/spike` environment. These strategies leverage the project's available datasets, focusing on combating volatility drag, identifying macro regimes, and optimizing entry/exit logic.

## 1. VIX Regime Filter + Golden Cross
**Concept:** Trend-following strategies get chopped to pieces in volatile bear markets, which is exceptionally damaging to 3x leveraged ETFs. This strategy uses a standard EMA crossover (e.g., 50/200 or 30/100) but requires the VIX to be below a specific historical threshold (e.g., < 25) to permit a long entry.
**Parameters:** Fast EMA, Slow EMA, VIX Threshold.
**Exit:** Fast EMA crosses below Slow EMA, or VIX spikes above a critical danger threshold (e.g., > 30).

## 2. Treasury Yield Curve Overlay (T10Y2Y)
**Concept:** Uses the 10-Year minus 2-Year Treasury spread (`treasury-spread-10y2y.csv`) as a macroeconomic regime filter. When the yield curve is inverted, recession risk is high and tech growth is heavily discounted.
**Entry:** A medium EMA (e.g., 20) slope is positive AND the T10Y2Y spread is > 0 (not inverted or steepening post-inversion).
**Exit:** Pure trend exit (e.g., close below 20 EMA) or ATR trailing stop.

## 3. Underlying Index Relative Strength (XLK/QQQ)
**Concept:** TECL is a derivative. This strategy ignores TECL's price action for trend confirmation and looks exclusively at the underlying index (XLK or QQQ). 
**Entry:** XLK's 50-day EMA > 200-day EMA AND TECL's short-term momentum (15-day EMA slope) is positive.
**Exit:** XLK's 50-day crosses below 200-day, OR TECL hits a strict 3x ATR trailing stop.

## 4. Fed Funds Pivot Capitulation
**Concept:** Mean reversion strategy designed for macro turning points. Leveraged ETFs suffer in sustained bear markets, but buying the absolute bottom when the Fed stops hiking can yield massive returns.
**Entry:** TECL RSI(14) drops below 30 (extreme oversold) AND the Fed Funds Rate (`fed-funds-rate.csv`) 3-month slope is <= 0 (rates have peaked/paused).
**Exit:** RSI(14) > 70, or a fixed time-based exit (e.g., 20 bars).

## 5. Keltner Channel Squeeze Breakout
**Concept:** Moving averages lag. Keltner Channels adapt to volatility. A "squeeze" (when the channels narrow) indicates compression, which usually precedes a massive move.
**Entry:** Keltner Channel width falls below its 100-day SMA, followed by a daily close above the Upper Keltner Band.
**Exit:** Close below the Middle Keltner Band (the baseline EMA).

## 6. VIX Term Structure Proxy (VIX vs SMA)
**Concept:** Approximates contango/backwardation by comparing the VIX spot price against its own 30-day SMA.
**Entry:** TECL 15-day EMA slope > 0 AND VIX < VIX 30-day SMA. (This confirms that market fear is subsiding relative to recent history).
**Exit:** VIX spikes > VIX 30-day SMA + 5%, triggering an immediate risk-off exit before the TECL trend officially breaks.

## 7. MACD Zero-Line Crossover in Bull Regime
**Concept:** A purely momentum-driven approach that seeks to catch intermediate waves inside a secular bull market.
**Entry:** Daily MACD line crosses above the MACD Signal line, BUT only if the 200-day SMA of QQQ is sloping upwards.
**Exit:** MACD line crosses below the Signal line.

## 8. Dual-Timeframe TEMA Breakout
**Concept:** TEMA (Triple EMA) reduces lag but increases noise. This uses a dual-timeframe approach to filter out the noise.
**Entry:** Weekly TEMA (calculated synthetically on daily bars using a 5x multiplier) slope is positive AND Daily TEMA slope turns positive.
**Exit:** Daily TEMA slope turns negative. (The weekly trend ensures we only take the daily signals in the direction of the macro trend).

## 9. Volume-Weighted Donchian Breakout
**Concept:** Standard Donchian breakouts suffer from false starts in low-liquidity chop. This strategy requires institutional participation.
**Entry:** Price closes at a 20-day high (Donchian upper band) AND the day's volume is > 150% of the 20-day Volume SMA.
**Exit:** Price closes below the 10-day Donchian low.

## 10. The SGOV Flight-to-Safety Switch
**Concept:** Pairs a standard momentum strategy on TECL with capital flow analysis from a risk-free asset (SGOV / 3-month T-bills).
**Entry:** TECL 15-day EMA > 30-day EMA AND SGOV 10-day Rate of Change is negative or flat (capital is not fleeing to safety).
**Exit:** TECL drops below its 15-day EMA OR SGOV experiences a sudden positive volume/price surge (indicating a sudden flight to safety).