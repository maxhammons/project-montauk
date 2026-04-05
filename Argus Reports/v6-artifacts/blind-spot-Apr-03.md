# Blind Spot Report — Apr-03

**Author**: Blind Spot Hunter
**Argus Version**: v6
**Method**: Independent source code analysis completed before reading any specialist output. Comparison follows.

---

## Phase 1: Independent Findings (formed before reading specialist output)

These 9 concerns were identified solely from reading the Python source in `scripts/` and the Pine Script in `src/strategy/active/`, with context from CLAUDE.md and the scout manifest.

---

### BSH-01: Bull/Bear Regime Scoring Uses Bar-Time Fraction, Not Return Fraction

The `score_regime_capture()` function in `backtest_engine.py` (lines 432-511) measures bull capture and bear avoidance as the **fraction of bars** the strategy was in/out of the market during each regime period. This is a fundamentally flawed proxy for what it claims to measure.

A strategy could be "in" for 90% of a bull period but enter late and miss the explosive opening leg -- capturing 90% of the bars but only 40% of the return. Conversely, a strategy could be "in" for only 30% of a bear period but happen to be in during the worst three days, avoiding 70% of the bars but suffering 60% of the loss.

The correct metric is dollar-weighted: what fraction of the regime's price move did the strategy actually participate in (for bulls) or avoid (for bears)? The current bar-counting approach systematically overrates strategies that are "in" during flat portions of bull markets and "out" during mild portions of bear markets. This distorts the primary optimization target.

**Severity**: HIGH -- this is the primary fitness metric for the entire optimization pipeline. If the metric itself is miscalibrated, all optimization results are suspect regardless of whether the engine, validation, or fitness function are correct.

---

### BSH-02: Two Completely Different BacktestResult Dataclasses Coexist

`backtest_engine.py` defines `BacktestResult` with fields like `regime_score`, `false_signal_rate_pct`, `worst_10_bar_loss_pct`, `bah_return_pct`, and `bah_final_equity`. `strategy_engine.py` defines its own `BacktestResult` with a different field set -- it has `vs_bah_multiple` and `strategy_name` but lacks `regime_score`, `false_signal_rate_pct`, `worst_10_bar_loss_pct`. The two dataclasses have overlapping but incompatible field sets.

Any code that consumes a `BacktestResult` must know which engine produced it. `evolve.py` imports from `strategy_engine` and accesses `vs_bah_multiple` (which exists there). `run_optimization.py` imports from `backtest_engine` and accesses `regime_score` (which exists there). If anyone tries to cross-wire these, they get silent `AttributeError` at runtime.

---

### BSH-03: The `strategies.py` montauk_821 Ignores 6+ Features of the Production Strategy

The `montauk_821()` function in `strategies.py` is a simplified version that lacks: TEMA entry filters, sideways market filter, sell confirmation window logic (barssince crossunder), sell cooldown, trailing stop exit, TEMA slope exit, volume spike exit, bear depth guard, ATR ratio filter, ADX filter, and ROC filter. It only implements the 3 core exits (ATR shock, quick EMA, EMA cross) and 2 entry conditions (short > med, trend slope). The production strategy in `backtest_engine.py` has 17 parameter groups; the v4 version has effectively 6.

This means any "vs 8.2.1 baseline" comparison from `evolve.py` is comparing new strategies against a gutted version of 8.2.1, not the real one.

---

### BSH-04: `evolve.py` Stagnation Tracker References an Attribute That Is Never Set

Line 234 of `evolve.py`: `stag = generation - getattr(evolve, '_last_improve', {}).get(strat_name, 0)`. The `evolve` function never sets `evolve._last_improve` anywhere. This means `getattr(evolve, '_last_improve', {})` always returns `{}`, `.get(strat_name, 0)` always returns `0`, and `stag` always equals `generation`. The mutation rate escalation (lines 235-236) triggers at generation 30 and 80 but is based on generation count, not actual stagnation. The adaptive mutation mechanism is broken.

---

### BSH-05: `evolve.py` and `spike_auto.py` Use Different Fitness Functions

`evolve.py` fitness (line 49-70): `bah * dd_penalty * freq_penalty`. Primary target is `vs_bah_multiple`. Drawdown penalty is `max(0.3, 1.0 - DD/200)`. Hard cap on 3 trades/year.

`spike_auto.py` fitness (line 194-235): `bah * dd_penalty * regime_bonus` plus quality guard multipliers for num_trades, trades_per_year, avg_bars_held, false_signal_rate, and extreme drawdown. Regime score is used as a secondary bonus factor. More guards, different formula.

These two fitness functions will rank the same strategies differently. Results from one optimizer are not comparable to results from the other.

---

### BSH-06: No Slippage or Transaction Cost Modeling

The Pine Script strategy header explicitly declares `slippage=0` and `commission_value=0`. The Python `StrategyParams` defaults `commission_pct=0.0`. TECL is a 3x leveraged ETF with average daily volume that can thin significantly during market stress. The strategy trades 100% of equity on each position. For a real deployment, even small slippage on entry/exit of a full-equity leveraged ETF position would compound significantly across 19+ trades over 17 years, especially during the high-volatility exits (ATR Shock, Quick EMA) where spreads widen.

The absence of any friction modeling means all backtest returns are systematically overstated, and strategies with more frequent or stress-timed trading are disproportionately favored.

---

### BSH-07: Yahoo Finance API Data Fetcher Has No Rate Limiting or Retry Logic

`data.py` `fetch_yahoo()` makes a single request with a 15-second timeout and a generic `except Exception` catch-all. If Yahoo returns a 429 (rate limit), a partial JSON response, or a temporary network error, the function silently falls back to CSV-only with no retry. The User-Agent spoofing (`Mozilla/5.0`) is fragile -- Yahoo has historically blocked programmatic access from non-browser user agents. There is no caching of successfully fetched data to disk, so every run re-fetches.

---

### BSH-08: `_NumpyEncoder` Class Is Duplicated Three Times

`evolve.py`, `spike_auto.py`, and `run_optimization.py` each define their own identical `_NumpyEncoder` / `_Enc` class for JSON serialization of numpy types. This is a minor DRY violation but symptomatic of the copy-paste development pattern.

---

### BSH-09: Walk-Forward Validation Windows Are Hardcoded and Will Expire

`validation.py` defines `NAMED_WINDOWS` with a hard stop at `"2024_onward": ("2024-06-01", "2026-12-31")` and `split_walk_forward` boundaries ending at `"2027-01-01"`. After December 2026, the expanding-window logic produces the same splits regardless of new data. After January 2027, the final boundary stops expanding. These dates need to be relative to the dataset's actual date range, not hardcoded.

---

## Phase 2: Comparison

After forming the above findings, I read the full meta-synthesis including all 25 ranked findings, 6 contradictions, 5 emerging patterns, and the succession-of-explanations section.

---

### Blind Spots (found by me, missed by specialists)

**BSH-01 (Regime Scoring Uses Bar-Time, Not Dollar-Weighted Returns)** -- This is the most significant blind spot. All 5 specialists discuss regime scoring extensively -- Risk frames it as the primary metric, Data-Integrity questions the thresholds, Architecture notes its absence from strategy_engine.py. But not one specialist questioned whether the regime scoring *methodology itself* is sound. The meta-synthesis treats regime score as a reliable metric that simply needs to be wired to the right engine. In reality, bar-time fraction is a crude proxy that can materially mislead the optimizer. A strategy that is "in" for 80% of a bull run's bars but enters after the first 40% gain scores 0.80 bull capture -- but it captured far less than 80% of the actual return. This is not a subtle point. It is the primary optimization target, and it measures the wrong thing.

The meta-synthesis's "Cascade of Unreliable Numbers" (Pattern B) identifies 6 links in the chain but does not include "regime scoring methodology is a poor proxy for actual regime capture" as one of the links. This should be link 4.5, between strategy signals and fitness scoring.

**BSH-06 (Zero Slippage/Transaction Cost Modeling)** -- No specialist mentions this. The meta-synthesis discusses the fitness function's drawdown penalty, the RSI Regime's 75% drawdown, and trade frequency limits, but never questions whether the raw backtest returns are realistic. For a 3x leveraged ETF with 100% equity position sizing, real-world slippage during stress exits (the exact conditions where ATR Shock and Quick EMA fire) could easily be 0.5-2% per round trip. Over 19 trades across 17 years, this is material. The optimization is comparing strategies on differences of a few percent return while ignoring a systematic bias that could be larger than those differences.

**BSH-09 (Hardcoded Validation Windows Will Expire)** -- No specialist mentions the hardcoded date boundaries in `validation.py`. This is a time bomb: the code will silently produce fewer and eventually zero validation windows as time passes beyond 2027. Not urgent today, but it is the kind of latent defect that causes confusion when it activates months from now with no obvious cause.

---

### Shallow Coverage (specialists mentioned but didn't go deep enough)

**BSH-02 (Incompatible BacktestResult Dataclasses)** -- The specialists extensively cover the "dual engine schism" (AGR-01, 5/5 agreement, highest-confidence finding). But they focus on the macro problem (two engines, duplicated indicators, validation disconnect) without drilling into the specific API incompatibility of the `BacktestResult` dataclass itself. The meta-synthesis says "port regime scoring and validation from backtest_engine.py" but does not flag that the BacktestResult contracts are different. Porting is not just about moving code -- the data contract must be unified, or downstream consumers will break.

**BSH-03 (strategies.py montauk_821 Is Gutted)** -- Data-Integrity F1 identifies "6+ features missing." Architecture F6 identifies the 30-bar vs 500-bar EMA issue. But the analysis treats these as discrete bugs rather than recognizing the systematic pattern: the v4 montauk_821 is not a faithful port with a few bugs; it is a fundamentally different strategy that shares a name with the production version. The meta-synthesis's "crippled baseline" framing captures this partially, but the recommended fix (fix the EMA, estimated at 1 hour) understates the scope. Porting the full 17-group parameter set of the production strategy into the `strategies.py` function format is a significant implementation task, not a 1-hour fix.

**BSH-05 (Competing Fitness Functions)** -- Risk R-14 mentions spike_auto.py's different fitness function as part of the "dead code" analysis, and AGR-07 covers the orphaned code. But the competing fitness functions are never analyzed as a *correctness* problem. If someone loads `best-ever.json` (written by spike_auto.py's fitness) and interprets it through evolve.py's fitness, they will misrank strategies. The meta-synthesis pattern about "alternative realities" (AGR-07 synthesis) gestures at this but does not make the specific comparison I made above.

---

### Structural Critique (what the specialist lens design itself missed)

**1. No "Financial Engineering" Lens.** The 5 specialist lenses (Architecture, Risk, Data-Integrity, Vision-Drift, Velocity) are generic software engineering lenses applied to a quantitative finance project. None of them embody domain expertise in backtesting methodology, survivorship bias, leveraged ETF mechanics, or quantitative strategy evaluation. As a result:

- No specialist questioned whether bar-time regime scoring is a valid proxy for dollar-weighted capture (BSH-01).
- No specialist flagged the zero slippage/transaction cost assumption (BSH-06).
- No specialist analyzed whether the 30% bear threshold and 20% bull threshold in `detect_bear_regimes()` / `detect_bull_regimes()` are appropriate for a 3x leveraged ETF that routinely has 50-80% drawdowns and 200-500% rallies. A 30% drawdown on TECL is a mild correction, not a bear market. The thresholds may be detecting too many "bear" periods and diluting the scoring.
- No specialist questioned whether "100% of equity per trade" is a reasonable sizing assumption for optimization, or whether the absence of partial position sizing distorts strategy comparison.

A "Quant Methodology" specialist would have caught all of these. The Risk lens came closest (R-10 on drawdown penalty, R-02 on 75% DD financial impact) but approached the problem from a software risk perspective, not a financial modeling perspective.

**2. All specialists focused on the Python layer; almost none examined Pine Script parity at the semantic level.** The meta-synthesis identifies the 30-bar vs 500-bar EMA mismatch and the RSI boundary condition, but these are surface-level checks. A deeper analysis would compare the bar-by-bar execution semantics: Does the Python backtest handle the same edge cases as Pine Script's `strategy.entry` / `strategy.close` functions? What happens when entry and exit signals fire on the same bar in each system? How does Pine Script's `process_orders_on_close=true` actually work when an entry and exit condition are both true simultaneously? The Python engine's same-bar handling (exit first, then entry) may or may not match Pine Script's internal priority.

**3. The specialist structure looked backward at existing code but did not evaluate the signal_queue.json roadmap.** `signal_queue.json` contains 20 planned signal implementations (12 queued, 8 implemented). This is the project's forward roadmap. None of the specialist findings address whether the queued signals have sound financial logic, whether the implementation descriptions are correct, or whether the planned expansion will compound the existing dual-engine and validation problems. The project is about to add 12 more signals to an already-broken infrastructure. A forward-looking analysis would have flagged this as a priority concern: fix the foundation before building more on it.

---

*End of blind spot report. All findings reference specific file paths and line numbers in the codebase as read during Phase 1.*
