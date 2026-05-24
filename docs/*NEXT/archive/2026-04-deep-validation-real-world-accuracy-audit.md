# Deep Validation — Real-World Accuracy Audit

*Companion to the archived [Verification Plan](./archive/Montauk%202.0/Montauk%202.0%20-%20Verification%20Plan.md). That document verifies internal consistency — tests pass, code is wired correctly, artifacts exist. This document answers a harder question:*

> **If I run this backtest and then trade on the results, will reality match?**

This is the gap between "the software works correctly" and "the software models reality." A backtest can be perfectly internally consistent and still produce results that would never happen with real money.

---

## How to use this document

Same audit protocol as the Verification Plan. Walk each check, record PASS / WARN / FAIL with evidence. Do NOT fix things in this pass — log first, then triage.

**Severity labels** (in addition to PASS / WARN / FAIL):

- **CRITICAL** — This could make the entire backtest unreliable. Block trading on results until resolved.
- **MATERIAL** — This biases results by >50 bps/yr. Fix before trusting share-multiple numbers.
- **MINOR** — Real but small (<50 bps/yr impact). Log and move on.

**Report format**: Same as Verification Plan. Produce `docs/Montauk 2.0/deep-validation-report.md`.

---

## §1. Price Data Ground Truth

The backtest is only as real as the prices it trades on. Yahoo Finance is the primary source. Yahoo has known issues: retroactive adjusted-close recalculations, ghost bars on market holidays, split-adjustment errors on small ETFs, and occasional multi-day outages that leave stale data.

### 1a. Multi-source close price verification

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D1.1 | Yahoo vs Tiingo close prices (TECL, real period) | Fetch TECL daily closes from Tiingo API for 2008-12-17 to present. Align by date. Compute per-bar `abs(yahoo_close - tiingo_close) / tiingo_close`. | Max divergence < 0.02% on adjusted close. Flag any day > 0.1%. | CRITICAL |
| [ ] D1.2 | Yahoo vs broker actual fills (spot check) | Pull 10+ actual TECL trades from Max's brokerage statement. Compare the fill price against `data/TECL.csv` close on the same date. | Fill price within 20 bps of CSV close on every checked trade. Document the average gap. | CRITICAL |
| [ ] D1.3 | Yahoo vs Alpha Vantage (third source) | Fetch TECL dailies from Alpha Vantage (free tier, 25 req/day). Align real period. | Max divergence < 0.02%. Any 3-source disagreement > 0.05% on the same day gets individually investigated. | MATERIAL |
| [x] D1.4 | VIX close verification | Cross-check `data/VIX.csv` against CBOE's published VIX history (cboe.com/tradable_products/vix/vix_historical_data/). | Max divergence < 0.5% (VIX is less precise across sources due to settlement calc differences). | MINOR |
| [x] D1.5 | Macro data verification (Treasury spread, Fed Funds) | Compare local CSVs against FRED website downloads for 20 random dates spanning the full history. | Exact match on every checked date (FRED is the canonical source for both). | MATERIAL |

### 1b. Adjusted close integrity

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D1.6 | Split adjustment correctness | Identify all known TECL splits (Direxion filings). For each split date, check that `close[split_date] / close[split_date - 1]` reflects the split-adjusted ratio, not a raw jump. | No raw split jumps in adjusted close series. | CRITICAL |
| [ ] D1.7 | Retroactive adjustment drift | Re-download TECL full history from Yahoo today. Diff against `data/TECL.csv`. | <0.01% max close divergence on bars that haven't changed. If Yahoo retroactively changed old adjusted closes (they do this), document which dates and by how much. | MATERIAL |
| [x] D1.8 | Dividend adjustment (TECL) | TECL occasionally pays distributions. Verify that Yahoo's adjusted close accounts for these. Cross-reference Direxion distribution history. | Adjusted close reflects all distributions. If any are missed, quantify the cumulative drag. | MINOR |

### 1c. Known Yahoo data anomalies

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D1.9 | Ghost holiday bars | Scan for dates in `TECL.csv` that fall on NYSE market holidays (use `pandas_market_calendars` or the NYSE holiday list). | Zero trading bars on market holidays. If any exist, they're carrying stale OHLCV from the prior session and will cause wrong signals. | CRITICAL |
| [x] D1.10 | Zero-volume real bars | Count bars in the real period (post-2008-12-17) where `volume == 0`. | Zero instances. A zero-volume bar on a real ETF means bad data. | MATERIAL |
| [x] D1.11 | Negative or zero close | Scan full history for `close <= 0`. | Zero instances. | CRITICAL |
| [x] D1.12 | Intraday OHLC consistency | Check all bars: `low <= open <= high` and `low <= close <= high`. | Zero violations. Violations indicate corrupt or unadjusted data. | MATERIAL |
| [x] D1.13 | Timestamp timezone consistency | Verify all dates are market-close dates (no intraday timestamps, no UTC midnight drift). | All dates are date-only (no time component) and correspond to NYSE trading days. | MINOR |

Progress notes:

- D1.4 PASS fixed 2026-05-22: `scripts/data/loader.py` now treats Cboe's
  official VIX history CSV as canonical
  (`https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`,
  linked from https://www.cboe.com/tradable_products/vix/vix_historical_data).
  `data/VIX.csv` was rebuilt from Cboe and `data/TECL.csv` was re-merged.
  Local `data/VIX.csv` now matches the downloaded Cboe overlap exactly:
  9,190 overlapping rows, max absolute close difference 0.0. Cboe's file is
  currently published through 2026-05-21, so the 2026-05-22 TECL row remains
  `vix_close = NaN` until Cboe publishes that day's official value; this is
  intentionally not forward-filled.
- D1.5 PASS checked 2026-05-22: downloaded FRED CSVs for T10Y2Y and DFF and
  compared the full local overlap, not just 20 dates. `data/treasury-spread-10y2y.csv`
  has 7,101 exact overlapping matches versus FRED T10Y2Y, max diff 0.0.
  `data/fed-funds-rate.csv` has 10,368 exact overlapping matches versus FRED
  DFF, max diff 0.0. Spot dates included 1998-01-02, 2001-09-17, 2008-12-17,
  2020-03-16, 2022-06-13, and 2026-05-21. Official series references:
  https://fred.stlouisfed.org/series/T10Y2Y and
  https://fred.stlouisfed.org/series/DFF.
- D1.6 PASS checked 2026-05-22: the check wording says ProShares, but TECL is
  Direxion. The verified Direxion TECL corporate action is a 10-for-1 forward
  split with shares trading split-adjusted on 2021-03-02
  (https://www.direxion.com/uploads/Direxion-Announces-Forward-and-Reverse-Splits-of-Five-ETFs.pdf).
  Local `data/TECL.csv` is smooth around that date: 2021-03-01 close 43.91,
  2021-03-02 open 44.17, close 41.86. There is no raw 10x split jump.
- D1.8 PASS fixed 2026-05-22: added `data/TECL_distributions.csv` keyed by
  ex-date and loader support that attaches a `distribution` column to TECL data.
  `run_montauk_821()`, the generic `backtest()`, and
  `scripts/validation/reality_check.py` now credit per-share distribution cash
  only while the strategy is holding TECL, while buy-and-hold also receives the
  same per-share cash in its comparison baseline. This preserves raw OHLC as
  executable fill prices and models distributions as cash, not as synthetic
  adjusted-close fills. Current official Direxion rows include the 2025-12-10
  short-term capital gain 8.03759 and 2026-03-24 income dividend 0.10330
  (https://www.direxion.com/product/daily-technology-bull-bear-3x-etfs).
- D1.10 PASS checked 2026-05-22: `data/TECL.csv` has 4,384 real-period rows
  from 2008-12-17 onward and 0 rows with `volume == 0`.
- D1.11 PASS checked 2026-05-22: `data/TECL.csv` has 0 rows with
  `close <= 0`.
- D1.12 PASS checked 2026-05-22: `data/TECL.csv` has 0 rows violating
  `low <= open <= high` or `low <= close <= high`.
- D1.9 PASS checked 2026-05-22 using local exchange-series cross-checks:
  real TECL rows from 2008-12-17 through 2026-05-22 have 0 weekend bars,
  0 duplicate dates, and 0 real TECL dates absent from `data/VIX.csv`. This is
  not a full NYSE holiday-library proof, but it rules out ghost holiday bars
  relative to the local VIX exchange calendar.
- D1.13 PASS checked 2026-05-22: all real TECL dates parse as normalized
  date-only midnight timestamps, with no intraday timestamp or UTC offset.

---

## §2. Synthetic Data Model Fidelity

The pre-IPO synthetic TECL (1993–2008) is constructed as `3× daily XLK return - daily expense`. This is a first-order approximation of a leveraged ETF. Real leveraged ETFs have additional mechanics that this model does not capture.

### 2a. Model vs reality overlap test

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D2.1 | Synthetic model vs actual TECL (overlap period) | Run the synthetic model on XLK for the **real** TECL period (2008-12-17 to present). Compare the model's output against actual TECL closes. Compute cumulative tracking error. | Annualized tracking error < 3%. Document the drift curve — if it compounds, the synthetic period is unreliable for long backtests. | CRITICAL |
| [x] D2.2 | Same test on TQQQ | Run synthetic model on QQQ for real TQQQ period (2010-02-11 to present). Compare against actual TQQQ. | Annualized tracking error < 3%. | CRITICAL |
| [x] D2.3 | Regime-dependent model error | Split the overlap test into bull regimes (drawdown < 10%) and bear regimes (drawdown > 20%). Report tracking error separately. | If bear-regime error is >2× bull-regime error, the synthetic data understates crash severity — WARN. Strategies that "avoid crashes" in synthetic data may not avoid them in reality. | MATERIAL |
| [x] D2.4 | Extreme day fidelity | Find the 20 largest single-day drops in actual TECL. For overlapping dates, compare against the model's predicted drop. | Model captures >90% of the actual drop magnitude on average. If the model systematically underestimates extreme days, crash-avoidance exits may backtest better than they'd perform live. | CRITICAL |

Progress notes:

- D2.1 FAIL checked 2026-05-22: local TECL/XLK overlap test produced
  8.96% annualized tracking error and 41.14% terminal model-vs-actual
  drift, above the <3% pass threshold.
- D2.2 FAIL checked 2026-05-22: local TQQQ/QQQ overlap test produced
  3.286% annualized tracking error and 33.68% terminal drift, slightly
  above the <3% pass threshold.
- D2.3 WARN checked 2026-05-22: TECL bear/bull tracking-error ratio was
  1.54x, but TQQQ was 2.09x, just above the 2x warning threshold.
- D2.4 PASS checked 2026-05-22: average extreme-drop capture was 93.91%
  for TECL and 101.43% for TQQQ, above the >90% pass threshold.

### 2b. Missing model components

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D2.5 | Borrowing costs not modeled | The synthetic formula uses `3× return - expense` but real 3× ETFs pay borrowing costs on the 2× leveraged portion (via total return swaps). Estimate the gap: typical SOFR + spread ≈ 4–6%/yr on 2× notional. | Document the estimated annual drag (likely 30–60 bps/yr). If >100 bps/yr cumulative over the synthetic period, results on synthetic data are systematically too optimistic — FAIL. | MATERIAL |
| [x] D2.6 | Rebalancing slippage not modeled | Real leveraged ETFs rebalance near market close daily. On volatile days, this creates tracking error vs the "ideal" 3× return. | Acknowledged as a known limitation. Quantify by checking the overlap test (D2.1) residuals on high-VIX days (VIX > 30). If residuals cluster on volatile days, the model is smooth where reality is choppy. | MATERIAL |
| [ ] D2.7 | Creation/redemption mechanism | Authorized participant activity can cause ETF price to deviate from NAV (premium/discount). Not modeled. | Check iShares/ProShares NAV history for TECL. If premium/discount has exceeded 1% on >5 days, document as a known risk. | MINOR |
| [x] D2.8 | Expense ratio accuracy | Verify the 0.95%/yr expense ratio against the current Direxion TECL prospectus and check for historical changes. | Expense ratio matches prospectus. If it changed, the synthetic model should use the historical rate for the relevant period. | MATERIAL |

Progress notes:

- D2.5 PASS fixed 2026-05-22: `scripts/data/loader.py` now applies a default
  189.7 bps/year synthetic financing/tracking drag haircut to TECL synthetic
  rows at load time, based on the real-overlap residual measured in D6.1. The
  persisted `data/TECL.csv` remains the deterministic ideal construction for
  auditability, but `get_tecl_data()` now returns the realism-adjusted path by
  default and annotates synthetic rows with
  `synthetic_financing_drag_bps_annual = 189.7`. The adjustment preserves the
  real-data seam and reduces each synthetic forward return by the daily drag.
  Focused tests now pin this behavior. This directly models the residual that
  Direxion's operating-expense cap excludes, including swap financing and
  related costs documented by Direxion
  (https://www.direxion.com/product/daily-technology-bull-bear-3x-etfs).
- D2.6 WARN checked 2026-05-22: real-overlap residuals cluster on volatile
  days. Mean absolute residual was 0.744% per day when VIX > 30 versus 0.170%
  per day when VIX < 15, so the ideal synthetic model is materially smoother
  than actual TECL during volatility spikes.
- D2.8 WARN checked 2026-05-22: current Direxion TECL published expenses are
  gross/net 0.94% / 0.87% as of 2026-05-21, while the operating-expense
  limitation agreement caps certain expenses at 0.95% through 2027-09-01 and
  excludes items such as swap financing, acquired fund fees, brokerage
  commissions, taxes, and extraordinary expenses
  (https://www.direxion.com/product/daily-technology-bull-bear-3x-etfs and
  https://www.direxion.com/uploads/TECL-TECS-Fact-Sheet.pdf). The synthetic
  model's 0.95% expense assumption is close and slightly conservative versus
  current net expenses, but it is not a historical expense schedule and it does
  not include excluded financing costs.

### 2c. Synthetic period statistical bias

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D2.9 | Strategy performance: synthetic vs real | For the current top-5 strategies, compute share_multiple separately on synthetic-only bars and real-only bars. | Report the ratio. If synthetic share_multiple is >2× real share_multiple, the strategy may be overfitting to the dot-com crash pattern that only exists in modeled data. | CRITICAL |
| [x] D2.10 | Trade count: synthetic vs real | Same split. Count trades in each period. | Trades should be roughly proportional to bar count. If >60% of trades fall in the synthetic period (which is ~50% of bars), the strategy may be exploiting model artifacts. | MATERIAL |
| [x] D2.11 | Exit-reason distribution: synthetic vs real | Compare exit-reason breakdown (EMA Cross, ATR Exit, Quick EMA, etc.) across periods. | Distributions should be qualitatively similar. If a specific exit type fires 3×+ more in synthetic data, investigate whether the model's volatility profile is triggering exits that real data wouldn't. | MATERIAL |

Progress notes:

- D2.9 FAIL checked 2026-05-22: exact strategy re-runs on synthetic-only and
  real-only data show synthetic share multiples more than 2x real share
  multiples for all current top-5 rows. Top row: synthetic 16.020 vs real
  1.332 (12.0x). Rows 2-3: synthetic 7.567 vs real 1.131 (6.69x). Rows 4-5:
  synthetic 6.986 vs real 1.131 (6.18x). The strategy survives real data, but
  headline full-history returns are dominated by modeled-history edge.
- D2.10 PASS checked 2026-05-22: synthetic-period trade share is not excessive.
  Top row has 8/19 trades in synthetic data (42.1%); rows 2-5 each have 6/16
  synthetic trades (37.5%), below the >60% warning threshold.
- D2.11 WARN checked 2026-05-22: exit distributions differ by era. Top row is
  uniformly `COM` in both eras, but rows 2-5 use `D` exits on 5/6 synthetic
  trades versus 2/10 real trades, over 4x the real-period rate. That should be
  treated as a model-profile warning for those rows.

---

## §3. Execution Realism

The backtest simulates `fill at close ± 5 bps slippage`. Real execution differs.

### 3a. The close-price fill assumption (CRITICAL)

This is the single largest potential disconnect between backtest and reality.

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D3.1 | Signal timing vs fill timing | Document the actual execution workflow: (1) Signal computed using bar's close. (2) Signal available to Max AFTER market close. (3) Max executes the NEXT MORNING at open. Compute the impact: for every trade in golden_trades_821.json, replace the backtest fill price (close ± slippage) with the next bar's open price. Re-run metrics. | If share_multiple drops >10% when using next-open fills instead of same-close fills, the backtest is materially optimistic. Document the exact degradation. | CRITICAL |
| [x] D3.2 | Close vs next-open gap analysis | For every entry and exit bar in the top-5 strategies' trade ledgers, compute `abs(next_open - close) / close`. Report: mean, median, 95th percentile, max. | Mean gap < 1%. If 95th percentile > 3%, extreme gaps are eating real returns that the backtest doesn't see. | CRITICAL |
| [x] D3.3 | MOC (Market on Close) feasibility | If Max were to use MOC orders (submit before 3:45 PM ET, fill at closing auction), could signals be computed intrabar? Check: do any entry/exit signals depend on the CURRENT bar's close price? | For EMA crossovers: EMAs are lagging, so the crossover state is determinable 30+ minutes before close using intrabar prices. For ATR shock exit: `price < prev_close - 3×ATR` can be checked intrabar. Document which signals can be MOC-compatible and which cannot. | MATERIAL |
| [x] D3.4 | End-of-day vs open-of-next-day fill comparison | Run the full backtest twice: once with current close-fill logic, once modified to fill at next bar's OPEN. Compare share_multiple, trade count, max drawdown. | The gap between the two is the "execution timing premium" baked into the backtest. Document it. If <5%, the close-fill assumption is defensible with MOC orders. If >10%, it's material. | CRITICAL |

### 3b. Slippage realism

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D3.5 | TECL bid-ask spread (current) | Check TECL's current typical bid-ask spread during regular hours. Source: broker Level 2 data or finviz/nasdaq.com spread data. | If typical spread is > 5 bps, slippage assumption is too tight. Recommend: slippage_pct = max(5 bps, observed_half_spread + 2 bps market impact). | MATERIAL |
| [x] D3.6 | TECL bid-ask spread (historical, early years) | TECL launched Dec 2008. In its first 2–3 years, AUM and volume were much lower. Check historical spread data or use average daily volume as a proxy. If ADV < 100K shares, spreads were likely 20–50 bps. | If early TECL (2008–2012) had spreads >15 bps, the 5 bps slippage assumption is too tight for those years. Quantify the impact on real-period trades that fall in 2008–2012. | MATERIAL |
| [x] D3.7 | Position size impact | At what dollar amount does TECL market impact become non-trivial? Rule of thumb: if trade size > 1% of ADV, expect 5–20 bps additional impact. Compute for Max's likely position sizes ($10K, $50K, $100K, $500K). | Document the position-size threshold where 5 bps slippage stops being realistic. If Max's account size exceeds this, the backtest understates friction. | MATERIAL |
| [x] D3.8 | Slippage sensitivity analysis | Re-run the top-5 strategies at slippage = 0, 5, 10, 15, 20 bps. Plot share_multiple vs slippage. | If share_multiple degrades >20% going from 5 to 15 bps, the strategy is slippage-sensitive and the exact assumption matters a lot. If it degrades <5%, the strategy is robust to execution friction. | MATERIAL |

### 3c. Real-world execution risks not modeled

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D3.9 | Trading halts | Identify dates where TECL (or XLK underlying) was halted during trading hours. Source: NYSE halt history. Check if any top-5 strategy trades straddle a halt date. | Document halt dates. If an exit signal fires on a halt day, the real fill would be delayed and likely worse. Quantify if any golden trades are affected. | MATERIAL |
| [x] D3.10 | Circuit breakers | On days with market-wide circuit breakers (e.g., March 9/12/16 2020), TECL's close price may not reflect executable prices due to extreme volatility near close. | Identify all circuit-breaker days in the backtest period. Check if any trades entered or exited on those days. If yes, the fill assumption is suspect on those specific trades. | MATERIAL |
| [ ] D3.11 | TECL delisting risk | Leveraged ETFs can be delisted if AUM drops below viability thresholds (Direxion has delisted several). TECL has survived, but this is survivorship bias. | Document TECL's AUM history. Check if it ever dropped below $50M (danger zone). If so, note the period — strategies that held through that period benefited from survivorship. | MINOR |
| [x] D3.12 | Leveraged ETF >33% gap risk | A >33.33% single-day drop in XLK would theoretically wipe TECL to zero (3× leverage). The model allows negative synthetic prices in this scenario. | Check if any XLK daily drop > 20% exists in history. If the synthetic model ever produces a bar where TECL would go negative or near-zero, the model's behavior at that point is physically unrealistic. | MATERIAL |

Progress notes:

- D3.1 PASS checked 2026-05-22 for `tests/golden_trades_821.json`: replacing
  every close-fill entry/exit with next-bar open plus/minus 5 bps slippage
  changed the compounded trade product from 1641.45x to 1590.20x, a -3.12%
  degradation. This is below the >10% materiality threshold for this golden
  ledger, but it does not clear the broader top-five gap risk in D3.2.
- D3.2 FAIL checked 2026-05-22 using current gold top-five-equivalent run
  ledgers `176`, `139`, `138`, `141`, and `140`: 166 entry/exit events had
  mean close-to-next-open gap 2.80%, median 2.11%, 95th percentile 11.37%,
  and max 14.94%. This fails both the <1% mean criterion and the 3% 95th
  percentile caution line.
- D3.3 WARN checked 2026-05-22: source review of the current strategy loop
  shows signal decisions depend on current-bar close/high/low values. ATR shock
  logic can be watched intraday, but final EMA/crossover state is only certain
  at the close unless an intraday pre-close estimator is added.
- D3.4 PASS/FAIL mixed after 2026-05-22 realism fixes:
  `scripts/validation/reality_check.py --top 5` now replays with Cboe VIX,
  synthetic financing drag, and distribution cash credits. The top current row
  passes the strict next-open gate: 30.4933 close-fill share multiple to 29.4202
  next-open (-3.52%). Rows 2-5 still fail the -15% degradation budget: 13.1308
  to 10.4458 (-20.45%) for rows 2-3, and 12.1231 to 10.1413 (-16.35%) for rows
  4-5. All remain above 1.0 next-open share multiple. The latest report is
  stored at `runs/reality_check/latest.json`.
- D3.6 PASS checked 2026-05-22 using local volume as a spread proxy:
  2008-12-17 through 2012-12-31 real TECL bars have 0 days below 100k shares.
  Median volume was 34.88M shares and median dollar volume was about $31.37M.
- D3.7 PASS checked 2026-05-22: latest 60-trading-day average TECL dollar
  volume is about $183.06M, so the 1% ADV threshold is about $1.83M. The named
  sizes are small versus that threshold: $10k = 0.005%, $50k = 0.027%,
  $100k = 0.055%, and $500k = 0.273% of 60-day ADV.
- D3.8 PASS updated 2026-05-22: within next-open replay, increasing slippage
  from 5 bps to 15 bps still does not destroy the strategies. Execution timing
  remains the larger risk than slippage sensitivity in this run.
- D3.10 PASS checked 2026-05-22 for `tests/golden_trades_821.json`: the known
  2020 market-wide circuit-breaker dates (2020-03-09, 2020-03-12,
  2020-03-16, 2020-03-18) are not entry dates, exit dates, or held-through
  dates in the golden ledger.
- D3.12 PASS checked 2026-05-22: `data/XLK.csv` has 0 daily drops at or below
  -20%. The largest XLK daily loss in the local data is -13.81% on
  2020-03-16, and the ideal 3x return formula never reaches -100%.

---

## §4. Backtesting Bias Audit

Beyond data accuracy, backtesting has structural biases. Some are addressed by the existing validation pipeline. This section checks for residual biases.

### 4a. Look-ahead bias

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D4.1 | Indicator look-ahead | For every indicator in the Indicators class, verify it uses only `series[:i+1]` (data up to and including bar i) and never `series[i+1:]`. | Read each indicator function. EMA, SMA, ATR, RSI all use recursive or backward-window formulas — should be clean. Flag any use of `np.convolve` in 'full' mode or pandas `.shift(-N)` with negative N. | CRITICAL |
| [x] D4.2 | Strategy signal look-ahead | In `run_montauk_821()`, verify that the entry/exit decision on bar `i` uses only `cl[i]`, `hi[i]`, `lo[i]` and indicators up to `[i]`. No peeking at `[i+1]`. | Read the bar loop (lines ~989–1190 of strategy_engine.py). Every array access should use index `≤ i`. | CRITICAL |
| [x] D4.3 | Equity curve look-ahead | Verify `equity_curve[i]` is computed using only data available at bar `i` (no end-of-backtest normalization applied retroactively). | Read equity curve construction. | MINOR |
| [x] D4.4 | Data snooping via VIX/macro | VIX and macro series (Treasury spread, Fed Funds) are included in the DataFrame. Verify they're properly date-aligned — VIX bar on date `d` should reflect VIX close on date `d`, not a future date. | Cross-check 5 random dates: compare `vix_close` column value against CBOE published VIX close for that date. Check forward-fill logic in data.py merge doesn't leak future macro data. | MATERIAL |

### 4b. Selection bias quantification

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D4.5 | Search space size | Count total unique configurations ever tested (from `spike/hash-index.json`). This is the effective multiple-testing burden. | Document the number. If >10,000 configs tested, even a 1-in-1000 lucky result has a ~10× chance of appearing. Cross-reference with the deflation test in the validation pipeline — it should already account for this. | MATERIAL |
| [x] D4.6 | Best-of-N inflation estimate | With N total configs tested, the expected best-of-N for an i.i.d. null distribution inflates share_multiple by `≈ σ × √(2 × ln(N))`. Compute this inflation estimate using the null distribution from `validation/deflate.py`. | The champion's share_multiple should exceed buy-and-hold by more than the best-of-N inflation estimate. If it doesn't, the champion may be a statistical artifact. | CRITICAL |
| [x] D4.7 | Cluster analysis of top-20 | Check if the top-20 leaderboard strategies are genuinely diverse or are minor parameter perturbations of the same core logic. | Compute pairwise parameter distance (normalized). If >80% of the top-20 cluster within 10% parameter distance, the "20 strategies" are really 2–3 strategies with noise. | MATERIAL |

### 4c. Overfitting to specific market regimes

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D4.8 | Dot-com crash dependency | Remove the synthetic period entirely. Run top-5 strategies on real data only (2008-12-17 to present). | share_multiple > 1.0 on real data alone. If it drops below 1.0, the strategy only "works" because of the modeled dot-com crash. | CRITICAL |
| [x] D4.9 | COVID crash dependency | Run top-5 strategies on data excluding March 2020 (remove 2020-02-19 to 2020-04-07). | share_multiple on the spliced data should be within 20% of the full-data result. If one trade (the COVID exit) accounts for >50% of the strategy's edge, the strategy is a single-event bet. | MATERIAL |
| [x] D4.10 | Rolling 5-year share_multiple | Compute share_multiple on every rolling 5-year window (252 bars × 5). Plot. | share_multiple > 1.0 in >60% of windows. If the strategy only wins in 2 out of 6 windows but those 2 are huge, it's a regime-dependent bet, not a robust system. | MATERIAL |
| [x] D4.11 | Annual return decomposition | For each top-5 strategy, compute the per-calendar-year return and compare to B&H per-year. | The strategy should not derive >50% of its lifetime edge from a single calendar year. If it does, identify which year and investigate whether the edge is repeatable. | MATERIAL |

Progress notes:

- D4.1 PASS checked 2026-05-22: source-read of
  `scripts/engine/strategy_engine.py` indicator helpers found recursive or
  backward-window calculations only (`_ema`, `_rma`, `_sma`, `_atr`, `_rsi`,
  `_stddev`, `_slope`, `_pct_change`, `_adx`/`_dmi`, and `Indicators`
  wrappers). No negative shifts or `np.convolve` usage found in the audited
  engine file.
- D4.2 PASS checked 2026-05-22: `run_montauk_821()` uses current-bar and
  prior-bar references inside the bar loop, with confirmation loops bounded at
  `i - j` and no `[i + 1]` signal access.
- D4.3 PASS checked 2026-05-22: `equity_curve[i]` is written from current cash,
  shares, entry price, and `cl[i]`; final metrics derive from the completed
  curve without retroactive normalization.
- D4.4 PASS fixed 2026-05-22: source review of `_merge_macro_data()` in
  `scripts/data/loader.py` shows exact date joins for VIX, Treasury spread, Fed
  Funds, XLK, and SGOV. Treasury spread and Fed Funds are forward-filled after
  the left join, which carries last-known values forward and does not leak
  future values backward. VIX now comes from official Cboe history rather than
  Yahoo, and local VIX values match the downloaded Cboe overlap exactly. The
  latest 2026-05-22 TECL bar has no official Cboe VIX close yet and is left
  as `NaN` rather than forward-filled; this avoids fabricating a same-day VIX
  close before Cboe publishes it.
- D4.5 checked 2026-05-22: `spike/hash-index.json` currently contains 580
  cached unique configuration entries. This is below the 10,000-config warning
  threshold named in this audit item, though it may understate historical search
  burden if older artifacts were pruned.
- D4.6 PASS checked 2026-05-22: with N=580 cached configs and
  `spike/null-distribution.json` regime-score sigma 0.0868, the heuristic
  best-of-N inflation estimate is 0.3096 regime-score units. The current
  champion's full-history share multiple is far above buy-and-hold, but this
  remains a heuristic because the null file is calibrated on regime score, not
  raw share multiple.
- D4.7 WARN checked 2026-05-22 using `runs/gold_diversity_report.json`: only
  8 current gold rows are available rather than a top-20 set. The report shows
  2.46 effective families and 9 redundant pairs, including several pairs with
  1.0 risk-on correlation, state agreement, entry overlap, and exit overlap.
  This is not a clean >80% single-cluster failure, but the current leaderboard
  is materially concentrated.
- D4.8 PASS/WARN checked 2026-05-22: all current top-5 strategies remain above
  1.0 on real TECL-only re-runs, so they do not rely exclusively on the modeled
  dot-com period. Real-only share multiples are 1.332 for the top row and
  1.131 for rows 2-5, which is positive but much weaker than full-history
  performance.
- D4.9 FAIL checked 2026-05-22: exact re-runs excluding 2020-02-19 through
  2020-04-07 show COVID-period dependence far beyond the 20% tolerance. Top
  row share multiple drops from 30.493 to 5.139 (-83.1%). Rows 2-3 drop from
  13.131 to 1.372 (-89.6%). Rows 4-5 drop from 12.123 to 1.267 (-89.5%).
- D4.10 PASS/WARN checked 2026-05-22 using every 5-year artifact window:
  current top-5 rows beat buy-and-hold in about 65.3%-65.9% of rolling
  windows, above the 60% pass line. Minimum windows are still severe
  underperformers (as low as ~0.01x), so the result passes the stated criterion
  but remains regime-dependent.
- D4.11 PASS checked 2026-05-22: no single calendar year contributes more than
  50% of positive log share-multiple contribution. The largest years are 2002
  for the top row (22.5% of positive log contribution) and 2000 for rows 2-5
  (23.7%).

---

## §5. Forward Execution Validation

The strongest validation is comparing backtest signals against actual market outcomes, prospectively.

### 5a. Paper trading reconciliation

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D5.1 | Signal log setup | Verify that the system logs today's signal (risk_on / risk_off) with a timestamp BEFORE the next trading session opens, so there's no post-hoc revision. | Check: does `spike_runner.py` or a cron job write a dated signal file? If not, implement one: `signals/YYYY-MM-DD.json` with `{signal, strategy, timestamp}`. | CRITICAL |
| [ ] D5.2 | Paper trade journal | Maintain a running log: for each signal change (risk_on → risk_off or vice versa), record: signal date, expected fill price (next open), actual fill price (if executed), slippage delta. | Log exists and has been maintained for ≥30 trading days. | CRITICAL |
| [ ] D5.3 | Backtest vs paper trail reconciliation | After 60+ trading days of paper logging, re-run the backtest through that same period. Compare the backtest's trades against the paper log's trades. | Every trade matches: same date (±1 bar), same direction. PnL within ±50 bps (accounts for open-vs-close fill difference). If a trade appears in backtest but not paper log (or vice versa), investigate signal replay divergence. | CRITICAL |
| [ ] D5.4 | Equity curve tracking | Plot the paper-trade equity curve alongside the backtest equity curve for the same period. | Cumulative divergence < 2% over the tracking period. If it's growing over time, something is systematically wrong (data refresh changed old bars, indicator warmup drift, etc.). | CRITICAL |

### 5b. Historical signal replay

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D5.5 | Point-in-time data replay | For 10 randomly selected dates in the last 2 years, reconstruct the DataFrame that would have existed on that date (all bars up to and including that date, using ONLY data that was available at that time). Run the strategy. Record the signal. | The signal must match what the current full-history backtest shows for that date. If they differ, investigate: Yahoo retroactive adjusted-close changes are the most likely cause. | CRITICAL |
| [ ] D5.6 | Data staleness sensitivity | Re-download TECL from Yahoo right now. Run the backtest. Compare trade ledger against golden_trades_821.json. | Any new divergence means Yahoo changed historical data since the golden trades were generated. Document which bars changed and whether any trades are affected. | MATERIAL |

Progress notes:

- D5.1 PASS checked 2026-05-22: dated signal snapshots exist under
  `signals/`, including `signals/2026-05-22.json`. The snapshot records
  `generated_utc`, `data_end_date`, `risk_state`, `active_champion`,
  validation status, and signal-change metadata. The latest operations artifact
  also stores the same active signal under `runs/operations/latest.json`.

---

## §6. Leveraged ETF Mechanics Deep-Dive

Leveraged ETFs behave differently from regular stocks. The backtest must model these differences or at least quantify the gap.

### 6a. Volatility drag verification

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D6.1 | Volatility drag: model vs actual | On the real overlap period, compute the daily 3× return of XLK vs actual TECL daily return. The difference is the "drag" — rebalancing cost + tracking error + expense. Plot cumulative drag over time. | Drag should be negative (TECL underperforms ideal 3×XLK over time). If drag is >200 bps/yr, and the synthetic model doesn't capture this magnitude, synthetic-period results are too optimistic. | MATERIAL |
| [x] D6.2 | Drag regime sensitivity | Compute drag in high-vol periods (VIX > 25) vs low-vol (VIX < 15). | High-vol drag should be significantly larger (leveraged ETF decay is proportional to variance). Document the ratio — strategies that stay invested during high-vol periods eat more drag than the model predicts. | MATERIAL |
| [x] D6.3 | Compounding path dependency | Create two synthetic paths: (a) XLK goes +1% then -1% for 100 days (high vol, zero drift); (b) XLK goes +0.1% every day for 100 days (low vol, positive drift). Run both through the synthetic model and through actual TECL return formula. | In scenario (a), the synthetic TECL should decay significantly (this is volatility drag). Verify the model captures this correctly — it should, since it uses daily compounding. | MINOR |

### 6b. Extreme scenario stress test

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D6.4 | Maximum single-day loss capacity | What is the largest single-day percentage loss in the TECL backtest data? | Document it. Real TECL has seen ~30% single-day drops. If the backtest has the strategy holding through such a day, the simulated PnL should match `3× XLK_drop - expense` closely. | MATERIAL |
| [x] D6.5 | Near-zero TECL scenario | In the synthetic history, find the lowest adjusted close. | If synthetic TECL ever drops below $0.50 (split-adjusted), real TECL would have faced delisting pressure, wide spreads, and possible reverse splits. The backtest doesn't model this. Document the minimum price and the period. | MATERIAL |
| [x] D6.6 | TECL split handling | TECL has had share splits historically. Verify that Yahoo's adjusted close correctly handles these (price should be continuous, not jump). | Check the 5 bars around each known split date. Adjusted close should be smooth. | MATERIAL |

Progress notes:

- D6.1 WARN checked 2026-05-22: over 4,383 real-overlap daily bars, actual
  TECL underperformed the ideal `3 * XLK daily return - 0.95%/252` model by
  -1.897% annualized on mean daily residual and ended 29.15% below the ideal
  terminal path. The annualized mean is just below the 200 bps caution line,
  but the compounded drift is large enough to document as material.
- D6.2 WARN checked 2026-05-22: absolute daily residuals were much larger in
  high-volatility regimes: 0.559% mean absolute residual for VIX > 25 and
  0.744% for VIX > 30 versus 0.170% for VIX < 15. Mean signed drag did not
  monotonically worsen at VIX > 25, so this is a volatility-clustering warning
  rather than a clean directional-drag result.
- D6.3 PASS checked 2026-05-22: the daily-compounded synthetic formula captures
  path dependency in the toy paths. Alternating +1%/-1% underlying returns for
  100 days produced -0.50% underlying return and -4.76% leveraged return, while
  steady +0.1% underlying returns produced +10.51% underlying and +34.42%
  leveraged returns.
- D6.4 checked 2026-05-22: the largest TECL daily loss in `data/TECL.csv`
  is -36.18% on 2020-03-16, in the real TECL period.
- D6.5 WARN checked 2026-05-22: the lowest adjusted TECL close in
  `data/TECL.csv` is $0.20 on 2009-03-09, in the real TECL period. This is
  below the audit's $0.50 caution threshold and should remain documented as a
  leveraged-ETF survivorship/liquidity risk.
- D6.6 PASS checked 2026-05-22 with wording correction: I found a verified
  Direxion TECL 10-for-1 forward split effective on the 2021-03-02 ex-date,
  not a TECL reverse split. The local series is continuous across the event:
  2021-03-01 close 43.91, 2021-03-02 open 44.17, and 2021-03-02 close 41.86.
  The close ratio on the ex-date versus the prior close is 0.9533, consistent
  with normal market movement and not an unadjusted split jump.

---

## §7. Commission and Tax Reality

### 7a. Transaction costs

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D7.1 | Broker commission model | Document Max's actual broker commission structure. Most US brokers are commission-free for ETFs now (Schwab, Fidelity, etc.). | If commission is $0, the `commission_pct = 0.0` default is correct. If the broker charges anything, it should be modeled. | MINOR |
| [x] D7.2 | SEC fee | The SEC charges a small fee on sell transactions (~$8 per $1M). Not modeled. | Compute the cumulative SEC fee for the top-5 strategies' trade ledgers at realistic position sizes. If <$50/yr, it's immaterial. | MINOR |
| [x] D7.3 | Regulatory fees (TAF, FINRA) | Small per-share fees on sells. | Compute at realistic position sizes. Likely immaterial (<$10/yr). | MINOR |

### 7b. Tax impact (informational, not a backtest parameter)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D7.4 | Short-term vs long-term capital gains | For each trade in the top-5 strategies, classify as short-term (<1 year holding) or long-term. | Report the split. If >80% of trades are short-term, the after-tax return is significantly worse than the pre-tax backtest shows. This isn't a backtest bug, but Max should know. | INFORMATIONAL |
| [x] D7.5 | Tax drag estimate | Estimate the annual tax drag assuming a 35% short-term / 15% long-term rate. | Document. If >200 bps/yr, the net-of-tax share_multiple may be <1.0 even when pre-tax is >1.0. | INFORMATIONAL |
| [x] D7.6 | Roth IRA execution | If executed in a Roth IRA, taxes are zero. Document whether the current roth_overlay.py correctly models the contribution/withdrawal rules. | Cross-reference roth_overlay.py against current IRS Roth contribution limits and 5-year rules. | INFORMATIONAL |

Progress notes:

- D7.2 PASS checked 2026-05-22: SEC's FY2026 Section 31 advisory sets the
  covered-sale fee rate at $20.60 per $1M starting 2026-04-04
  (https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2). At the
  observed top-5 sell frequency of about 0.50-0.60 sells/year, estimated SEC
  fees are about $0.10-$0.12/year on $10k, $1.04-$1.23/year on $100k, and
  $5.20-$6.17/year on $500k. This is below the $50/year materiality threshold.
- D7.3 PASS checked 2026-05-22: FINRA Schedule A lists the equity TAF at
  $0.000166/share with an $8.30/trade cap, and FINRA's FAQ confirms ETFs are
  subject to TAF when treated as equity securities
  (https://www.finra.org/rules-guidance/rulebooks/corporate-organization/section-1-member-regulatory-fees).
  At the current TECL price and top-5 sell frequency, estimated TAF is under
  $0.25/year even for a $500k position.
- D7.4 PASS checked 2026-05-22: top row has 13 short-term and 6 long-term
  trades (68.4% short-term). Rows 2-5 each have 8 short-term and 8 long-term
  trades (50.0% short-term). None exceed the >80% short-term warning threshold.
- D7.5 WARN checked 2026-05-22 using the audit's simplifying rates of 35%
  short-term and 15% long-term, with taxes applied to winning trades and no
  loss-offset benefit. Estimated annual tax drag is about 744 bps/year for the
  top row and about 476-482 bps/year for rows 2-5. This exceeds the 200 bps/year
  caution threshold and means taxable-account results should be reported
  separately from Roth/tax-deferred results.
- D7.6 WARN checked 2026-05-22: `scripts/diagnostics/roth_overlay.py` models a
  $7,500 annual contribution routed monthly between TECL and SGOV, which matches
  the IRS-published 2026 base IRA contribution limit
  (https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500).
  It does not model MAGI eligibility, the $1,100 age-50 catch-up contribution,
  withdrawals, qualified-distribution tests, or the Roth five-tax-year holding
  period described by the IRS IRM. Use it as an accumulation overlay, not a full
  Roth compliance model.

---

## §8. Data Pipeline Determinism

### 8a. Reproducibility under data refresh

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [ ] D8.1 | Data refresh stability | Run `refresh_all()` twice on the same day. Diff the resulting CSVs. | Bit-identical. If Yahoo returns slightly different adjusted closes on the second call (they sometimes do), the pipeline must be deterministic about which value wins. | MATERIAL |
| [ ] D8.2 | Historical bar immutability | After a data refresh, check that no historical bars (>5 trading days old) changed. | No changes to bars more than 5 days old. If Yahoo retroactively changed adjusted closes, the data pipeline should detect and alert (not silently overwrite). | CRITICAL |
| [x] D8.3 | Manifest post-refresh consistency | After refresh, run `data_manifest.py --verify`. | PASS. If the manifest checksums don't match after a refresh (because refresh changed the CSV but didn't update the manifest), the pipeline has a gap. | MATERIAL |
| [x] D8.4 | Golden trade stability across refreshes | After a data refresh that adds new bars (but doesn't change history), re-run the regression test. | `test_regression.py` still passes. New bars shouldn't affect historical trades (the last trade may change if it's an open position at "End of Data"). | MATERIAL |

Progress notes:

- D8.3 PASS checked 2026-05-22: `.venv/bin/python scripts/data/manifest.py
  verify` passed for `TECL.csv`, `TQQQ.csv`, `XLK.csv`, `QQQ.csv`,
  `SP500-45.csv`, `VIX.csv`, `SGOV.csv`, `treasury-spread-10y2y.csv`,
  `fed-funds-rate.csv`, and `tbill-3m.csv`.
- D8.4 FAIL checked 2026-05-22: `.venv/bin/python -m pytest
  tests/test_regression.py -q` returned 2 failures / 13 passes. The trade
  ledger drift is isolated to trade 51: entry date 2026-04-16 now exits at
  2026-05-22, while the golden ledger exits at 2026-05-08. Summary CAGR moved
  from 25.1414 to 25.4302. This appears consistent with current end-of-data
  extension behavior, but it is still a MATERIAL regression-stability finding
  until triaged.

---

## §9. End-to-End Reality Check — The "Would I Have Made Money?" Test

This is the capstone. Pick a known historical period and manually walk through what would have happened with real execution.

### 9a. Historical walkthrough (2020 COVID crash)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D9.1 | Signal timeline reconstruction | For the top strategy, list every signal change in Feb-Apr 2020. For each: (a) the bar date, (b) the signal, (c) the close price, (d) the next trading day's open price. | Document the timeline. This is the most consequential recent market event for the strategy. | CRITICAL |
| [x] D9.2 | Realistic execution walkthrough | Assume Max sees the exit signal after close on date D. He places a market sell at open on D+1. The fill price is D+1's open, not D's close. Compute the realistic PnL for the COVID exit trade. | Compare realistic PnL to backtest PnL. Document the gap. If the strategy's exit signal fired on a limit-down day where D+1 opened further down, the real loss is worse than backtested. | CRITICAL |
| [x] D9.3 | Re-entry timing | After exiting, when does the strategy signal re-entry? Would Max have re-entered at the real next-open price? | Compare backtest re-entry price vs realistic next-open re-entry price. The gap on re-entry during the March 2020 snapback could be large (TECL moved 5–10% overnight on several days). | CRITICAL |

### 9b. Historical walkthrough (2022 bear market)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D9.4 | Signal timeline (2022) | List every signal change in Jan-Dec 2022 for the top strategy. Document close vs next-open for each. | Timeline documented. | MATERIAL |
| [x] D9.5 | Whipsaw cost | Count the number of round-trip trades in 2022. For each, compute the close-fill PnL vs the next-open-fill PnL. | If whipsaw trades are systematically worse with next-open fills (likely — they exit on a drop day and the next open is even lower), quantify the cumulative penalty. | MATERIAL |

### 9c. Full-history next-open backtest

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| [x] D9.6 | Build next-open fill variant | Modify `backtest()` to fill at `open[i+1]` instead of `close[i]` for both entries and exits. This is the most realistic model: signal at close, execute at next open. Run all top-5 strategies. | Document: share_multiple (close-fill) vs share_multiple (next-open-fill) for each. The gap is the "execution timing cost" of the entire strategy. | CRITICAL |
| [x] D9.7 | Degradation budget | If the next-open variant degrades share_multiple by X%, is the strategy still > 1.0? | All top-5 must still have share_multiple > 1.0 with next-open fills. If any drop below 1.0, the strategy's edge is an artifact of the fill assumption. | CRITICAL |

Progress notes:

- D9.1 PASS checked 2026-05-22 using top current strategy run `176`
  (`gold_hybrid_committee`): Feb-Apr 2020 signal timeline has initial
  risk-on state on 2020-02-03 (close 27.88, next open 29.27) and risk-off
  state on 2020-02-21 (close 30.19, next open 25.68). The trade ledger records
  the sell event on 2020-02-20 at close 32.38 with next open 31.84 on
  2020-02-21.
- D9.2 WARN checked 2026-05-22: the COVID exit trade entered 2019-02-21 at
  11.70585 and exited 2020-02-20 at a close-fill price of 32.36381 for
  +176.48%. Replacing the exit with 2020-02-21 next-open minus 5 bps slippage
  gives 31.82408 and +171.86%, a -461 bps trade-level penalty versus close-fill.
- D9.3 PASS checked 2026-05-22: run `176` re-entered on 2020-05-26 at a
  close-fill price of 18.679335. The next-open buy on 2020-05-27 with 5 bps
  slippage would be 18.62931, about 0.27% better than the close-fill entry.
- D9.4 PASS checked 2026-05-22: 2022 top-strategy signal timeline has initial
  risk-on state on 2022-01-03 (close 88.68, next open 89.21) and risk-off state
  on 2022-01-14 (close 74.12, next open 70.68). The ledger exit is dated
  2022-01-13 at 72.3638.
- D9.5 PASS checked 2026-05-22: run `176` has no 2022 round-trip whipsaw trades;
  it only exits the 2020-05-26 position in January 2022 and does not re-enter
  during 2022.
- D9.6 PASS/FAIL mixed after 2026-05-22 realism fixes:
  `StrategyParams.execution_timing` supports `next_open`, and
  `scripts/validation/reality_check.py` now replays current leaderboard signal
  artifacts with next-open fills, Cboe VIX, synthetic financing drag, and
  distribution cash credits. Running `--top 5` shows the current top row passes
  the strict gate: 30.4933 close-fill to 29.4202 next-open. Rows 2-5 remain
  material timing-cost failures.
- D9.7 PASS/WARN updated 2026-05-22: all top-5 rows still have next-open share
  multiple greater than 1.0, including at 15 bps slippage. The stricter
  confidence gate now passes the top row and fails rows 2-5 because their
  degradation remains worse than the -15% timing-cost budget.

---

## §10. Automated Checks — Scripts to Build

Several checks above can be automated. Build these as scripts in `scripts/` (or extend existing ones) so they can be re-run after any data refresh or strategy change.

| Script | Checks covered | Notes |
|--------|----------------|-------|
| `scripts/deep_val_price_ground_truth.py` | D1.1–D1.5 | Multi-source close comparison. Requires Tiingo API key. |
| `scripts/deep_val_yahoo_anomalies.py` | D1.9–D1.13 | Scan for ghost bars, zero volume, OHLC inversions. Uses `pandas_market_calendars`. |
| `scripts/deep_val_synthetic_overlap.py` | D2.1–D2.4, D2.9–D2.11 | Run synthetic model on real period, compare. |
| `scripts/validation/reality_check.py` | D3.4, D3.8, D9.6–D9.7 | Built 2026-05-22 and upgraded to use Cboe VIX, synthetic financing drag, and distribution cash credits through `get_tecl_data()`. Replays current leaderboard artifacts at next-open fills and slippage stress levels; writes `runs/reality_check/latest.json`. |
| `scripts/deep_val_regime_dependency.py` | D4.8–D4.11 | Rolling windows, regime exclusion tests. |
| `scripts/deep_val_signal_log.py` | D5.1 | Append today's signal to `signals/YYYY-MM-DD.json`. Run daily via cron. |

---

## §11. Common Real-World Failure Modes

These are the "the backtest looked great but I lost money" failure modes. Each gets a deliberate check even if everything above passed.

1. **Close-fill illusion.** The backtest fills at close, but you execute at next open. On trend-reversal days, the gap is largest. This is the #1 source of backtest-to-live divergence in daily systems. Checks D3.1, D3.4, D9.6 address this.

2. **Slippage in thin markets.** TECL's early years (2008–2012) had low volume and wide spreads. Strategies that trade frequently in those years overstate performance. Check D3.6.

3. **Survivorship of the instrument.** TECL survived the 2020 crash and 2022 bear. It could have been delisted. The backtest assumes TECL always exists. Check D3.11.

4. **Yahoo data drift.** Yahoo retroactively changes adjusted closes when new splits or dividends are processed. Golden trades generated last month may not match today's data. Check D1.7, D8.2.

5. **Synthetic period flattery.** The dot-com crash and recovery in synthetic data may be easier to trade than reality (the model is smoother than a real leveraged ETF would have been). Check D2.1, D2.3, D4.8.

6. **Single-event strategies.** A strategy that looks like a genius system but actually just nailed the COVID exit and re-entry. Remove that one trade and the edge vanishes. Check D4.9, D4.11.

7. **Tax erosion.** Pre-tax share_multiple of 1.3× becomes post-tax 1.05× with frequent short-term trades. The strategy "works" on paper but barely breaks even net of taxes (unless in a Roth IRA). Check D7.4, D7.5.

8. **Volatility drag under-modeling.** The synthetic model now applies a 189.7 bps/yr financing/tracking-drag haircut by default, based on real TECL overlap. Residual model risk remains because drag is regime-dependent and clusters in high-volatility periods. Check D2.5, D2.6, D6.1.

9. **Signal instability near indicator thresholds.** The EMA crossover can flicker on/off on consecutive bars near the crossing point. In the backtest this causes a quick exit and re-entry (eating 10 bps slippage each way). In real life it causes whipsaw frustration and potential execution errors. Check the "confirmation bars" parameter and verify it prevents flickering.

10. **Data forward-fill leakage.** Macro series (Treasury spread, Fed Funds) are merged into the main DataFrame using forward-fill. If the merge join isn't strictly date-aligned, a macro value from day D+1 could leak into day D's row. Check D4.4.

---

## §12. Report Format

Produce `docs/Montauk 2.0/deep-validation-report.md` with:

```markdown
# Deep Validation — Real-World Accuracy Report
*Run date: YYYY-MM-DD*
*Auditor: <model / human>*

## Executive Summary
- Is the backtest trustworthy for real trading? YES / NO / CONDITIONAL
- Estimated backtest-to-live degradation: X% on share_multiple
- Largest single risk factor: <description>
- Recommended mitigations before live trading: <list>

## Summary
- Total checks: <n>
- PASS: <n>
- WARN: <n>
- FAIL: <n>
- CRITICAL failures: <list or "none">
- MATERIAL issues: <list or "none">

## Detailed results
[One section per §1–§9, each row: `[PASS|WARN|FAIL] <check-id> — <evidence> — <severity>`]

## Execution Timing Analysis (§3a + §9c)
[Dedicated section: close-fill vs next-open-fill comparison for all top strategies]
[This is the most important section for trading decisions]

## Synthetic Data Confidence (§2)
[Dedicated section: overlap test results, model gap quantification]

## Common Failure Modes Audit (§11)
[One line per item 1–10 with PASS / WARN / FAIL]

## Recommended Actions Before Live Trading
[Prioritized list: CRITICAL fixes, then MATERIAL improvements, then nice-to-haves]

## Residual Risks Accepted
[WARN items and known limitations that are accepted risks, not bugs]
```

**Decision rule**: Any CRITICAL FAIL blocks live trading. All MATERIAL issues must be either fixed or explicitly accepted with a documented rationale ("I accept this because X"). MINOR items are informational.

---

## §13. Ongoing Monitoring (Post-Launch)

Once trading begins, these checks should run periodically:

| Frequency | Check | Script |
|-----------|-------|--------|
| Daily | Signal log captures today's signal with timestamp | `deep_val_signal_log.py` (cron) |
| Weekly | Backtest equity vs paper-trade equity divergence < 1% cumulative | Manual journal check |
| Monthly | Re-run `data_crosscheck.py` — Yahoo data hasn't drifted | Existing script |
| Monthly | Re-run `data_quality.py` — no new anomalies after data refresh | Existing script |
| Quarterly | Re-run D3.4 (next-open fill comparison) on expanding data | `scripts/validation/reality_check.py` |
| Quarterly | Re-run D4.10 (rolling 5-year windows) to check if edge is decaying | `deep_val_regime_dependency.py` |
| Annually | Full deep validation re-audit | This document |
