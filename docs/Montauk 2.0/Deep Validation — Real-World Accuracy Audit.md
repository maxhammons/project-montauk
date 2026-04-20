# Deep Validation — Real-World Accuracy Audit

*Companion to [Verification Plan](./Montauk%202.0%20-%20Verification%20Plan.md). That document verifies internal consistency — tests pass, code is wired correctly, artifacts exist. This document answers a harder question:*

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
| D1.1 | Yahoo vs Tiingo close prices (TECL, real period) | Fetch TECL daily closes from Tiingo API for 2008-12-17 to present. Align by date. Compute per-bar `abs(yahoo_close - tiingo_close) / tiingo_close`. | Max divergence < 0.02% on adjusted close. Flag any day > 0.1%. | CRITICAL |
| D1.2 | Yahoo vs broker actual fills (spot check) | Pull 10+ actual TECL trades from Max's brokerage statement. Compare the fill price against `data/TECL.csv` close on the same date. | Fill price within 20 bps of CSV close on every checked trade. Document the average gap. | CRITICAL |
| D1.3 | Yahoo vs Alpha Vantage (third source) | Fetch TECL dailies from Alpha Vantage (free tier, 25 req/day). Align real period. | Max divergence < 0.02%. Any 3-source disagreement > 0.05% on the same day gets individually investigated. | MATERIAL |
| D1.4 | VIX close verification | Cross-check `data/VIX.csv` against CBOE's published VIX history (cboe.com/tradable_products/vix/vix_historical_data/). | Max divergence < 0.5% (VIX is less precise across sources due to settlement calc differences). | MINOR |
| D1.5 | Macro data verification (Treasury spread, Fed Funds) | Compare local CSVs against FRED website downloads for 20 random dates spanning the full history. | Exact match on every checked date (FRED is the canonical source for both). | MATERIAL |

### 1b. Adjusted close integrity

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D1.6 | Split adjustment correctness | Identify all known TECL splits (ProShares filings). For each split date, check that `close[split_date] / close[split_date - 1]` reflects the split-adjusted ratio, not a raw jump. | No raw split jumps in adjusted close series. | CRITICAL |
| D1.7 | Retroactive adjustment drift | Re-download TECL full history from Yahoo today. Diff against `data/TECL.csv`. | <0.01% max close divergence on bars that haven't changed. If Yahoo retroactively changed old adjusted closes (they do this), document which dates and by how much. | MATERIAL |
| D1.8 | Dividend adjustment (TECL) | TECL occasionally pays small distributions. Verify that Yahoo's adjusted close accounts for these. Cross-reference ProShares distribution history. | Adjusted close reflects all distributions. If any are missed, quantify the cumulative drag. | MINOR |

### 1c. Known Yahoo data anomalies

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D1.9 | Ghost holiday bars | Scan for dates in `TECL.csv` that fall on NYSE market holidays (use `pandas_market_calendars` or the NYSE holiday list). | Zero trading bars on market holidays. If any exist, they're carrying stale OHLCV from the prior session and will cause wrong signals. | CRITICAL |
| D1.10 | Zero-volume real bars | Count bars in the real period (post-2008-12-17) where `volume == 0`. | Zero instances. A zero-volume bar on a real ETF means bad data. | MATERIAL |
| D1.11 | Negative or zero close | Scan full history for `close <= 0`. | Zero instances. | CRITICAL |
| D1.12 | Intraday OHLC consistency | Check all bars: `low <= open <= high` and `low <= close <= high`. | Zero violations. Violations indicate corrupt or unadjusted data. | MATERIAL |
| D1.13 | Timestamp timezone consistency | Verify all dates are market-close dates (no intraday timestamps, no UTC midnight drift). | All dates are date-only (no time component) and correspond to NYSE trading days. | MINOR |

---

## §2. Synthetic Data Model Fidelity

The pre-IPO synthetic TECL (1993–2008) is constructed as `3× daily XLK return - daily expense`. This is a first-order approximation of a leveraged ETF. Real leveraged ETFs have additional mechanics that this model does not capture.

### 2a. Model vs reality overlap test

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D2.1 | Synthetic model vs actual TECL (overlap period) | Run the synthetic model on XLK for the **real** TECL period (2008-12-17 to present). Compare the model's output against actual TECL closes. Compute cumulative tracking error. | Annualized tracking error < 3%. Document the drift curve — if it compounds, the synthetic period is unreliable for long backtests. | CRITICAL |
| D2.2 | Same test on TQQQ | Run synthetic model on QQQ for real TQQQ period (2010-02-11 to present). Compare against actual TQQQ. | Annualized tracking error < 3%. | CRITICAL |
| D2.3 | Regime-dependent model error | Split the overlap test into bull regimes (drawdown < 10%) and bear regimes (drawdown > 20%). Report tracking error separately. | If bear-regime error is >2× bull-regime error, the synthetic data understates crash severity — WARN. Strategies that "avoid crashes" in synthetic data may not avoid them in reality. | MATERIAL |
| D2.4 | Extreme day fidelity | Find the 20 largest single-day drops in actual TECL. For overlapping dates, compare against the model's predicted drop. | Model captures >90% of the actual drop magnitude on average. If the model systematically underestimates extreme days, crash-avoidance exits may backtest better than they'd perform live. | CRITICAL |

### 2b. Missing model components

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D2.5 | Borrowing costs not modeled | The synthetic formula uses `3× return - expense` but real 3× ETFs pay borrowing costs on the 2× leveraged portion (via total return swaps). Estimate the gap: typical SOFR + spread ≈ 4–6%/yr on 2× notional. | Document the estimated annual drag (likely 30–60 bps/yr). If >100 bps/yr cumulative over the synthetic period, results on synthetic data are systematically too optimistic — FAIL. | MATERIAL |
| D2.6 | Rebalancing slippage not modeled | Real leveraged ETFs rebalance near market close daily. On volatile days, this creates tracking error vs the "ideal" 3× return. | Acknowledged as a known limitation. Quantify by checking the overlap test (D2.1) residuals on high-VIX days (VIX > 30). If residuals cluster on volatile days, the model is smooth where reality is choppy. | MATERIAL |
| D2.7 | Creation/redemption mechanism | Authorized participant activity can cause ETF price to deviate from NAV (premium/discount). Not modeled. | Check iShares/ProShares NAV history for TECL. If premium/discount has exceeded 1% on >5 days, document as a known risk. | MINOR |
| D2.8 | Expense ratio accuracy | Verify the 0.95%/yr expense ratio against the current ProShares TECL prospectus and check for historical changes. | Expense ratio matches prospectus. If it changed (e.g., was 1.08% before 2020), the synthetic model should use the historical rate for the relevant period. | MATERIAL |

### 2c. Synthetic period statistical bias

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D2.9 | Strategy performance: synthetic vs real | For the current top-5 strategies, compute share_multiple separately on synthetic-only bars and real-only bars. | Report the ratio. If synthetic share_multiple is >2× real share_multiple, the strategy may be overfitting to the dot-com crash pattern that only exists in modeled data. | CRITICAL |
| D2.10 | Trade count: synthetic vs real | Same split. Count trades in each period. | Trades should be roughly proportional to bar count. If >60% of trades fall in the synthetic period (which is ~50% of bars), the strategy may be exploiting model artifacts. | MATERIAL |
| D2.11 | Exit-reason distribution: synthetic vs real | Compare exit-reason breakdown (EMA Cross, ATR Exit, Quick EMA, etc.) across periods. | Distributions should be qualitatively similar. If a specific exit type fires 3×+ more in synthetic data, investigate whether the model's volatility profile is triggering exits that real data wouldn't. | MATERIAL |

---

## §3. Execution Realism

The backtest simulates `fill at close ± 5 bps slippage`. Real execution differs.

### 3a. The close-price fill assumption (CRITICAL)

This is the single largest potential disconnect between backtest and reality.

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D3.1 | Signal timing vs fill timing | Document the actual execution workflow: (1) Signal computed using bar's close. (2) Signal available to Max AFTER market close. (3) Max executes the NEXT MORNING at open. Compute the impact: for every trade in golden_trades_821.json, replace the backtest fill price (close ± slippage) with the next bar's open price. Re-run metrics. | If share_multiple drops >10% when using next-open fills instead of same-close fills, the backtest is materially optimistic. Document the exact degradation. | CRITICAL |
| D3.2 | Close vs next-open gap analysis | For every entry and exit bar in the top-5 strategies' trade ledgers, compute `abs(next_open - close) / close`. Report: mean, median, 95th percentile, max. | Mean gap < 1%. If 95th percentile > 3%, extreme gaps are eating real returns that the backtest doesn't see. | CRITICAL |
| D3.3 | MOC (Market on Close) feasibility | If Max were to use MOC orders (submit before 3:45 PM ET, fill at closing auction), could signals be computed intrabar? Check: do any entry/exit signals depend on the CURRENT bar's close price? | For EMA crossovers: EMAs are lagging, so the crossover state is determinable 30+ minutes before close using intrabar prices. For ATR shock exit: `price < prev_close - 3×ATR` can be checked intrabar. Document which signals can be MOC-compatible and which cannot. | MATERIAL |
| D3.4 | End-of-day vs open-of-next-day fill comparison | Run the full backtest twice: once with current close-fill logic, once modified to fill at next bar's OPEN. Compare share_multiple, trade count, max drawdown. | The gap between the two is the "execution timing premium" baked into the backtest. Document it. If <5%, the close-fill assumption is defensible with MOC orders. If >10%, it's material. | CRITICAL |

### 3b. Slippage realism

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D3.5 | TECL bid-ask spread (current) | Check TECL's current typical bid-ask spread during regular hours. Source: broker Level 2 data or finviz/nasdaq.com spread data. | If typical spread is > 5 bps, slippage assumption is too tight. Recommend: slippage_pct = max(5 bps, observed_half_spread + 2 bps market impact). | MATERIAL |
| D3.6 | TECL bid-ask spread (historical, early years) | TECL launched Dec 2008. In its first 2–3 years, AUM and volume were much lower. Check historical spread data or use average daily volume as a proxy. If ADV < 100K shares, spreads were likely 20–50 bps. | If early TECL (2008–2012) had spreads >15 bps, the 5 bps slippage assumption is too tight for those years. Quantify the impact on real-period trades that fall in 2008–2012. | MATERIAL |
| D3.7 | Position size impact | At what dollar amount does TECL market impact become non-trivial? Rule of thumb: if trade size > 1% of ADV, expect 5–20 bps additional impact. Compute for Max's likely position sizes ($10K, $50K, $100K, $500K). | Document the position-size threshold where 5 bps slippage stops being realistic. If Max's account size exceeds this, the backtest understates friction. | MATERIAL |
| D3.8 | Slippage sensitivity analysis | Re-run the top-5 strategies at slippage = 0, 5, 10, 15, 20 bps. Plot share_multiple vs slippage. | If share_multiple degrades >20% going from 5 to 15 bps, the strategy is slippage-sensitive and the exact assumption matters a lot. If it degrades <5%, the strategy is robust to execution friction. | MATERIAL |

### 3c. Real-world execution risks not modeled

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D3.9 | Trading halts | Identify dates where TECL (or XLK underlying) was halted during trading hours. Source: NYSE halt history. Check if any top-5 strategy trades straddle a halt date. | Document halt dates. If an exit signal fires on a halt day, the real fill would be delayed and likely worse. Quantify if any golden trades are affected. | MATERIAL |
| D3.10 | Circuit breakers | On days with market-wide circuit breakers (e.g., March 9/12/16 2020), TECL's close price may not reflect executable prices due to extreme volatility near close. | Identify all circuit-breaker days in the backtest period. Check if any trades entered or exited on those days. If yes, the fill assumption is suspect on those specific trades. | MATERIAL |
| D3.11 | TECL delisting risk | Leveraged ETFs can be delisted if AUM drops below viability thresholds (Direxion has delisted several). TECL has survived, but this is survivorship bias. | Document TECL's AUM history. Check if it ever dropped below $50M (danger zone). If so, note the period — strategies that held through that period benefited from survivorship. | MINOR |
| D3.12 | Leveraged ETF >33% gap risk | A >33.33% single-day drop in XLK would theoretically wipe TECL to zero (3× leverage). The model allows negative synthetic prices in this scenario. | Check if any XLK daily drop > 20% exists in history. If the synthetic model ever produces a bar where TECL would go negative or near-zero, the model's behavior at that point is physically unrealistic. | MATERIAL |

---

## §4. Backtesting Bias Audit

Beyond data accuracy, backtesting has structural biases. Some are addressed by the existing validation pipeline. This section checks for residual biases.

### 4a. Look-ahead bias

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D4.1 | Indicator look-ahead | For every indicator in the Indicators class, verify it uses only `series[:i+1]` (data up to and including bar i) and never `series[i+1:]`. | Read each indicator function. EMA, SMA, ATR, RSI all use recursive or backward-window formulas — should be clean. Flag any use of `np.convolve` in 'full' mode or pandas `.shift(-N)` with negative N. | CRITICAL |
| D4.2 | Strategy signal look-ahead | In `run_montauk_821()`, verify that the entry/exit decision on bar `i` uses only `cl[i]`, `hi[i]`, `lo[i]` and indicators up to `[i]`. No peeking at `[i+1]`. | Read the bar loop (lines ~989–1190 of strategy_engine.py). Every array access should use index `≤ i`. | CRITICAL |
| D4.3 | Equity curve look-ahead | Verify `equity_curve[i]` is computed using only data available at bar `i` (no end-of-backtest normalization applied retroactively). | Read equity curve construction. | MINOR |
| D4.4 | Data snooping via VIX/macro | VIX and macro series (Treasury spread, Fed Funds) are included in the DataFrame. Verify they're properly date-aligned — VIX bar on date `d` should reflect VIX close on date `d`, not a future date. | Cross-check 5 random dates: compare `vix_close` column value against CBOE published VIX close for that date. Check forward-fill logic in data.py merge doesn't leak future macro data. | MATERIAL |

### 4b. Selection bias quantification

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D4.5 | Search space size | Count total unique configurations ever tested (from `spike/hash-index.json`). This is the effective multiple-testing burden. | Document the number. If >10,000 configs tested, even a 1-in-1000 lucky result has a ~10× chance of appearing. Cross-reference with the deflation test in the validation pipeline — it should already account for this. | MATERIAL |
| D4.6 | Best-of-N inflation estimate | With N total configs tested, the expected best-of-N for an i.i.d. null distribution inflates share_multiple by `≈ σ × √(2 × ln(N))`. Compute this inflation estimate using the null distribution from `validation/deflate.py`. | The champion's share_multiple should exceed buy-and-hold by more than the best-of-N inflation estimate. If it doesn't, the champion may be a statistical artifact. | CRITICAL |
| D4.7 | Cluster analysis of top-20 | Check if the top-20 leaderboard strategies are genuinely diverse or are minor parameter perturbations of the same core logic. | Compute pairwise parameter distance (normalized). If >80% of the top-20 cluster within 10% parameter distance, the "20 strategies" are really 2–3 strategies with noise. | MATERIAL |

### 4c. Overfitting to specific market regimes

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D4.8 | Dot-com crash dependency | Remove the synthetic period entirely. Run top-5 strategies on real data only (2008-12-17 to present). | share_multiple > 1.0 on real data alone. If it drops below 1.0, the strategy only "works" because of the modeled dot-com crash. | CRITICAL |
| D4.9 | COVID crash dependency | Run top-5 strategies on data excluding March 2020 (remove 2020-02-19 to 2020-04-07). | share_multiple on the spliced data should be within 20% of the full-data result. If one trade (the COVID exit) accounts for >50% of the strategy's edge, the strategy is a single-event bet. | MATERIAL |
| D4.10 | Rolling 5-year share_multiple | Compute share_multiple on every rolling 5-year window (252 bars × 5). Plot. | share_multiple > 1.0 in >60% of windows. If the strategy only wins in 2 out of 6 windows but those 2 are huge, it's a regime-dependent bet, not a robust system. | MATERIAL |
| D4.11 | Annual return decomposition | For each top-5 strategy, compute the per-calendar-year return and compare to B&H per-year. | The strategy should not derive >50% of its lifetime edge from a single calendar year. If it does, identify which year and investigate whether the edge is repeatable. | MATERIAL |

---

## §5. Forward Execution Validation

The strongest validation is comparing backtest signals against actual market outcomes, prospectively.

### 5a. Paper trading reconciliation

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D5.1 | Signal log setup | Verify that the system logs today's signal (risk_on / risk_off) with a timestamp BEFORE the next trading session opens, so there's no post-hoc revision. | Check: does `spike_runner.py` or a cron job write a dated signal file? If not, implement one: `signals/YYYY-MM-DD.json` with `{signal, strategy, timestamp}`. | CRITICAL |
| D5.2 | Paper trade journal | Maintain a running log: for each signal change (risk_on → risk_off or vice versa), record: signal date, expected fill price (next open), actual fill price (if executed), slippage delta. | Log exists and has been maintained for ≥30 trading days. | CRITICAL |
| D5.3 | Backtest vs paper trail reconciliation | After 60+ trading days of paper logging, re-run the backtest through that same period. Compare the backtest's trades against the paper log's trades. | Every trade matches: same date (±1 bar), same direction. PnL within ±50 bps (accounts for open-vs-close fill difference). If a trade appears in backtest but not paper log (or vice versa), investigate signal replay divergence. | CRITICAL |
| D5.4 | Equity curve tracking | Plot the paper-trade equity curve alongside the backtest equity curve for the same period. | Cumulative divergence < 2% over the tracking period. If it's growing over time, something is systematically wrong (data refresh changed old bars, indicator warmup drift, etc.). | CRITICAL |

### 5b. Historical signal replay

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D5.5 | Point-in-time data replay | For 10 randomly selected dates in the last 2 years, reconstruct the DataFrame that would have existed on that date (all bars up to and including that date, using ONLY data that was available at that time). Run the strategy. Record the signal. | The signal must match what the current full-history backtest shows for that date. If they differ, investigate: Yahoo retroactive adjusted-close changes are the most likely cause. | CRITICAL |
| D5.6 | Data staleness sensitivity | Re-download TECL from Yahoo right now. Run the backtest. Compare trade ledger against golden_trades_821.json. | Any new divergence means Yahoo changed historical data since the golden trades were generated. Document which bars changed and whether any trades are affected. | MATERIAL |

---

## §6. Leveraged ETF Mechanics Deep-Dive

Leveraged ETFs behave differently from regular stocks. The backtest must model these differences or at least quantify the gap.

### 6a. Volatility drag verification

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D6.1 | Volatility drag: model vs actual | On the real overlap period, compute the daily 3× return of XLK vs actual TECL daily return. The difference is the "drag" — rebalancing cost + tracking error + expense. Plot cumulative drag over time. | Drag should be negative (TECL underperforms ideal 3×XLK over time). If drag is >200 bps/yr, and the synthetic model doesn't capture this magnitude, synthetic-period results are too optimistic. | MATERIAL |
| D6.2 | Drag regime sensitivity | Compute drag in high-vol periods (VIX > 25) vs low-vol (VIX < 15). | High-vol drag should be significantly larger (leveraged ETF decay is proportional to variance). Document the ratio — strategies that stay invested during high-vol periods eat more drag than the model predicts. | MATERIAL |
| D6.3 | Compounding path dependency | Create two synthetic paths: (a) XLK goes +1% then -1% for 100 days (high vol, zero drift); (b) XLK goes +0.1% every day for 100 days (low vol, positive drift). Run both through the synthetic model and through actual TECL return formula. | In scenario (a), the synthetic TECL should decay significantly (this is volatility drag). Verify the model captures this correctly — it should, since it uses daily compounding. | MINOR |

### 6b. Extreme scenario stress test

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D6.4 | Maximum single-day loss capacity | What is the largest single-day percentage loss in the TECL backtest data? | Document it. Real TECL has seen ~30% single-day drops. If the backtest has the strategy holding through such a day, the simulated PnL should match `3× XLK_drop - expense` closely. | MATERIAL |
| D6.5 | Near-zero TECL scenario | In the synthetic history, find the lowest adjusted close. | If synthetic TECL ever drops below $0.50 (split-adjusted), real TECL would have faced delisting pressure, wide spreads, and possible reverse splits. The backtest doesn't model this. Document the minimum price and the period. | MATERIAL |
| D6.6 | TECL reverse split handling | TECL has done reverse splits historically. Verify that Yahoo's adjusted close correctly handles these (price should be continuous, not jump). | Check the 5 bars around each known reverse split date. Adjusted close should be smooth. | MATERIAL |

---

## §7. Commission and Tax Reality

### 7a. Transaction costs

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D7.1 | Broker commission model | Document Max's actual broker commission structure. Most US brokers are commission-free for ETFs now (Schwab, Fidelity, etc.). | If commission is $0, the `commission_pct = 0.0` default is correct. If the broker charges anything, it should be modeled. | MINOR |
| D7.2 | SEC fee | The SEC charges a small fee on sell transactions (~$8 per $1M). Not modeled. | Compute the cumulative SEC fee for the top-5 strategies' trade ledgers at realistic position sizes. If <$50/yr, it's immaterial. | MINOR |
| D7.3 | Regulatory fees (TAF, FINRA) | Small per-share fees on sells. | Compute at realistic position sizes. Likely immaterial (<$10/yr). | MINOR |

### 7b. Tax impact (informational, not a backtest parameter)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D7.4 | Short-term vs long-term capital gains | For each trade in the top-5 strategies, classify as short-term (<1 year holding) or long-term. | Report the split. If >80% of trades are short-term, the after-tax return is significantly worse than the pre-tax backtest shows. This isn't a backtest bug, but Max should know. | INFORMATIONAL |
| D7.5 | Tax drag estimate | Estimate the annual tax drag assuming a 35% short-term / 15% long-term rate. | Document. If >200 bps/yr, the net-of-tax share_multiple may be <1.0 even when pre-tax is >1.0. | INFORMATIONAL |
| D7.6 | Roth IRA execution | If executed in a Roth IRA, taxes are zero. Document whether the current roth_overlay.py correctly models the contribution/withdrawal rules. | Cross-reference roth_overlay.py against current IRS Roth contribution limits and 5-year rules. | INFORMATIONAL |

---

## §8. Data Pipeline Determinism

### 8a. Reproducibility under data refresh

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D8.1 | Data refresh stability | Run `refresh_all()` twice on the same day. Diff the resulting CSVs. | Bit-identical. If Yahoo returns slightly different adjusted closes on the second call (they sometimes do), the pipeline must be deterministic about which value wins. | MATERIAL |
| D8.2 | Historical bar immutability | After a data refresh, check that no historical bars (>5 trading days old) changed. | No changes to bars more than 5 days old. If Yahoo retroactively changed adjusted closes, the data pipeline should detect and alert (not silently overwrite). | CRITICAL |
| D8.3 | Manifest post-refresh consistency | After refresh, run `data_manifest.py --verify`. | PASS. If the manifest checksums don't match after a refresh (because refresh changed the CSV but didn't update the manifest), the pipeline has a gap. | MATERIAL |
| D8.4 | Golden trade stability across refreshes | After a data refresh that adds new bars (but doesn't change history), re-run the regression test. | `test_regression.py` still passes. New bars shouldn't affect historical trades (the last trade may change if it's an open position at "End of Data"). | MATERIAL |

---

## §9. End-to-End Reality Check — The "Would I Have Made Money?" Test

This is the capstone. Pick a known historical period and manually walk through what would have happened with real execution.

### 9a. Historical walkthrough (2020 COVID crash)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D9.1 | Signal timeline reconstruction | For the top strategy, list every signal change in Feb-Apr 2020. For each: (a) the bar date, (b) the signal, (c) the close price, (d) the next trading day's open price. | Document the timeline. This is the most consequential recent market event for the strategy. | CRITICAL |
| D9.2 | Realistic execution walkthrough | Assume Max sees the exit signal after close on date D. He places a market sell at open on D+1. The fill price is D+1's open, not D's close. Compute the realistic PnL for the COVID exit trade. | Compare realistic PnL to backtest PnL. Document the gap. If the strategy's exit signal fired on a limit-down day where D+1 opened further down, the real loss is worse than backtested. | CRITICAL |
| D9.3 | Re-entry timing | After exiting, when does the strategy signal re-entry? Would Max have re-entered at the real next-open price? | Compare backtest re-entry price vs realistic next-open re-entry price. The gap on re-entry during the March 2020 snapback could be large (TECL moved 5–10% overnight on several days). | CRITICAL |

### 9b. Historical walkthrough (2022 bear market)

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D9.4 | Signal timeline (2022) | List every signal change in Jan-Dec 2022 for the top strategy. Document close vs next-open for each. | Timeline documented. | MATERIAL |
| D9.5 | Whipsaw cost | Count the number of round-trip trades in 2022. For each, compute the close-fill PnL vs the next-open-fill PnL. | If whipsaw trades are systematically worse with next-open fills (likely — they exit on a drop day and the next open is even lower), quantify the cumulative penalty. | MATERIAL |

### 9c. Full-history next-open backtest

| # | Check | How | PASS criteria | Severity |
|---|-------|-----|---------------|----------|
| D9.6 | Build next-open fill variant | Modify `backtest()` to fill at `open[i+1]` instead of `close[i]` for both entries and exits. This is the most realistic model: signal at close, execute at next open. Run all top-5 strategies. | Document: share_multiple (close-fill) vs share_multiple (next-open-fill) for each. The gap is the "execution timing cost" of the entire strategy. | CRITICAL |
| D9.7 | Degradation budget | If the next-open variant degrades share_multiple by X%, is the strategy still > 1.0? | All top-5 must still have share_multiple > 1.0 with next-open fills. If any drop below 1.0, the strategy's edge is an artifact of the fill assumption. | CRITICAL |

---

## §10. Automated Checks — Scripts to Build

Several checks above can be automated. Build these as scripts in `scripts/` (or extend existing ones) so they can be re-run after any data refresh or strategy change.

| Script | Checks covered | Notes |
|--------|----------------|-------|
| `scripts/deep_val_price_ground_truth.py` | D1.1–D1.5 | Multi-source close comparison. Requires Tiingo API key. |
| `scripts/deep_val_yahoo_anomalies.py` | D1.9–D1.13 | Scan for ghost bars, zero volume, OHLC inversions. Uses `pandas_market_calendars`. |
| `scripts/deep_val_synthetic_overlap.py` | D2.1–D2.4, D2.9–D2.11 | Run synthetic model on real period, compare. |
| `scripts/deep_val_execution_timing.py` | D3.1, D3.2, D3.4, D9.6–D9.7 | Next-open fill variant backtest. The single most important script. |
| `scripts/deep_val_slippage_sensitivity.py` | D3.8 | Sweep slippage from 0–20 bps, report share_multiple curve. |
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

8. **Volatility drag under-modeling.** The synthetic model assumes ideal 3× daily returns minus expense. Real leveraged ETFs lose an additional 50–150 bps/yr to rebalancing friction, borrowing costs, and tracking error. This compounds over the 15-year synthetic period. Check D2.5, D2.6, D6.1.

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
| Quarterly | Re-run D3.4 (next-open fill comparison) on expanding data | `deep_val_execution_timing.py` |
| Quarterly | Re-run D4.10 (rolling 5-year windows) to check if edge is decaying | `deep_val_regime_dependency.py` |
| Annually | Full deep validation re-audit | This document |
