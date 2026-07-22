# Montauk 3.0 Research — Stream 5: TECL data, B&H, and opening execution

## 1. One-page plain-English conclusion

Montauk's Gold claim rests on one sentence: "a signal formed after a verified close, filled at the next regular-session open, would have beaten matched TECL buy-and-hold." Every word is a place the backtest can quietly diverge from what any owner could actually obtain at a broker. This stream makes each word airtight — as a property of the data/execution contract, not of any specific strategy's parameters.

**"Verified close."** Yahoo Finance — the repo's only real-data source (`data/manifest.json`) — is a data *aggregator*, not the exchange; it republishes a consolidated-tape feed under undocumented adjustment logic and is not itself primary for "the official close." NYSE Arca's rulebook defines an Official Closing Price from its Closing Auction (Rule 7.35) [Evidence: primary, SEC EDGAR Exhibit 5], and that is the number a verification step must agree with. `scripts/data/crosscheck.py` (Yahoo vs. Stooq) is aggregator-vs-aggregator, not aggregator-vs-exchange — it cannot catch a bug both vendors share. **Recommendation: keep vendor-vs-vendor agreement as a daily tripwire, necessary but not sufficient, paired with a periodic spot-check against an exchange/SIP-derived reference (§3, Experiment 1).**

**"Next regular-session open."** TECL trades on NYSE Arca, which runs a rule-governed Core Open Auction (Rule 7.35), not "whatever prints first" [Evidence: primary]. A retail order only reaches that auction if the broker's order type routes there, and this is genuinely broker-specific: Interactive Brokers' TWS API documentation states a Market-on-Open order "combines a market order with the OPG time in force" [Evidence: primary, IBKR TWS API docs, directly fetched]. Fidelity's "On the Open" TIF cancels any unfilled remainder rather than converting to a live order [Evidence: primary, Fidelity FAQ, directly fetched] — but Fidelity's page never says "auction," so **treating "On the Open" as reaching the Arca Core Open Auction specifically, rather than a fast market fill shortly after 9:30:00, is our own inference layered on Fidelity's vaguer language, not something the citation establishes [Inference].** Schwab's public documentation states no explicit MOO/OPG behavior at all — an **insufficient-evidence** state under the charter's three-way verdict vocabulary (§4.3), not a "no."

**A hard gate, stated once, consistently.** Which broker actually submits the order, and whether it demonstrably reaches the Arca Core Open Auction, must be confirmed before *any* Gold row's execution assumption is treated as live-tradeable — not merely before Experiment 4's cost number is finalized (§8, Decision 1). If a broker "converts to a plain market order a few seconds after 9:30:00" instead, the fill could differ from the auction print by the post-auction spread's width — often wider than the auction itself for a 3x leveraged sector ETF. This specific "silently downgrades to 9:30:01" mechanism is our own illustrative hypothetical, not a documented Schwab behavior — disclosed as such here and in §2.

**Splits and dividends.** TECL executed a real 10-for-1 forward split effective March 2, 2021 [Evidence: primary, Direxion/Rafferty SEC Form 497]. `data/TECL.csv` shows a continuous series across that date with no 10x jump — confirming Yahoo's real-segment history is **split**-adjusted. It is *not* shown to be dividend/total-return adjusted: `data/TECL_distributions.csv` exists separately (13 ex-dates, 2021–2026) and nothing in `TECL.csv` folds those in. Building a true total-return series is Experiment 2's job — a direct stated finding, not left implicit.

**Calendar, timezone, and DST.** All Arca auction/session times are Eastern Time; "next regular-session open" must resolve via an exchange holiday calendar (no session on NYSE holidays) plus tz-aware `America/New_York` arithmetic, not a fixed UTC offset — a fixed offset misaligns by an hour across the March/November DST transitions. Early-close days (1:00pm ET) affect the *close*-verification step (Experiment 1 must land on the 1:00pm bar), not the open — the Core Open Auction still runs at its normal time. [Evidence: primary for calendar dates, NYSE Group Holiday and Early-Closing Calendar release; the DST-handling recommendation is standard engineering practice, not a separate external claim.]

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| TECL executed a 10-for-1 forward split, record date 2021-02-26, ex-date 2021-03-02 | Primary (regulatory filing) | [Direxion Shares ETF Trust, Form 497 supplement, filed 2021-01-29](https://www.sec.gov/Archives/edgar/data/1424958/000119312521022676/d59468d497.htm) | Strong | Yes — exact product | Corroborated by [MIAX corporate-action alert](https://www.miaxglobal.com/sites/default/files/alert-files/TECL_Split_48246.pdf) |
| TECL.csv shows no discontinuity at the split date; not shown to be dividend/total-return adjusted | Primary (internal inspection) | `data/TECL.csv`, `data/TECL_distributions.csv` (13 ex-dates, 2021–2026) | Strong for split-adjustment; total-return question open | Yes — exact files | Stated as a direct finding, not left implicit |
| TECL net expense ratio is 0.87% (0.83% ex-AFFE); gross 0.94% | Product-primary | [Direxion Fact Sheet](https://www.direxion.com/uploads/TECL-TECS-Fact-Sheet.pdf), as of 2026-03-31 | Strong | Yes | manifest.json's "0.95%" is the Operating Expense Limitation *cap* (through 2027-09-01), not the disclosed net ratio — internal inconsistency (§8, Decision 3) |
| MOO/LOO orders are Arca auction-only; unexecuted quantity is cancelled, not held | Primary (rule text) | [NYSE Arca Rule 7.31(c)(1)-(2)](https://www.sec.gov/files/rules/sro/nysearca/2016/34-79107-ex5.pdf) | Strong | Yes | Verified by direct PDF extraction |
| Core Open Auction Collar: ≤$25 → 10%, $25–$50 → 5%, >$50 → 3% of Reference Price | Primary (rule text) | Same Rule 7.35(a)(10)(A) filing | Strong | Yes, amended repeatedly since 2016 — re-verify current text before implementation | Trading Halt Auction uses a separate formula: Ref. Price × 5%, $0.15 floor if ≤$3 |
| An unresolved Core Open imbalance is handled via halt/reopening-auction machinery, reopening time extended until an in-collar print is possible | Primary (federal order), not re-fetched this session | [SEC order re: Rule 7.35/7.11 amendments](https://www.federalregister.gov/documents/2017/01/26/2017-01718/self-regulatory-organizations-nyse-arca-inc-order-granting-approval-of-proposed-rule-change-as) | Moderate (found via search, not line-by-line re-verified) | Yes | **Delayed open is distinct from an intraday halt** — same recovery mechanics, different trigger, different fill-timing implication (§4, §7) |
| IBKR Market-on-Open order = market order + OPG time-in-force | Primary (vendor API docs) | [IBKR TWS API — Basic Orders](https://interactivebrokers.github.io/tws-api/basic_orders.html) | Strong | Yes if IBKR | **Corrected citation** — the prior IBKR Campus glossary link lacked this detail; this page, directly retrieved, quotes "Market On Open (MOO) combines a market order with the OPG time in force" verbatim |
| Fidelity's "On the Open" TIF cancels unfilled remainder rather than converting to a live order | Product-primary | [Fidelity FAQs](https://www.fidelity.com/trading/faqs-order-types) | Strong for cancellation; **"reaches the Arca auction" is our inference, not the source's language** [Inference] | Yes if Fidelity | Source says "as close as possible to the opening price... canceled" — never "auction" |
| Schwab's support for a true opening-auction order type is not publicly documented | Insufficient evidence (charter §4.3) | Schwab order-type pages; primary pages 403'd | N/A | Unknown | Single most operationally important unresolved fact (§8) |
| CRSP-style adjustment: A(t) = P(t)/C(t), chained factor | Base formula Primary; the field-level total-return expression (divamt/cumfacpr/facpr) **not verified verbatim in the cited excerpt** — treat as a worked reconstruction, not a quote | [CRSP Data Description Guide, Ch. 5](https://leiq.bus.umich.edu/docs/crsp_calculations_splits.pdf) | Moderate (downgraded to Inference for field-level expression) | Methodology transfers; TECL not CRSP-covered | Experiment 2 must independently derive and validate the formula |
| Leveraged sector ETFs typically show wider spreads than large-cap index ETFs | Secondary, general-category | [Longbridge](https://longbridge.com/en/academy/etf/blog/liquidity-analysis-of-u-s-listed-etfs-how-the-bid-ask-spread-affects-your-trading-costs-100362); [Direxion "ETF Liquidity"](https://www.direxion.com/education/etf-liquidity-four-rules-to-trade-by) | Weak–Moderate | Directional only | **Insufficient evidence** (charter §4.3) for a TECL-specific, dated number — weakest input; exactly what Experiment 4 calibrates |
| Exchange calendar governs "next trading day" and 1:00pm early closes | Primary (exchange-parent release) | [NYSE Group Holiday Calendar](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx) | Strong for dates; DST handling is engineering practice | Yes | Now covered in body text (§1, §7), not just a reference entry |
| A material product-contract change forces a methodology break/recertification, never automatic ETF substitution | Owner-ratified decision | Questionnaire 6, Q5 | Strong (policy) | N/A | Stream 5 implements detection mechanics only |

## 3. Recommended Montauk experiment(s)

**Experiment 1 — Official-close agreement study.**
*Estimand:* the daily rate at which Montauk's vendor(s) disagree with NYSE Arca's Official Closing Price by more than a **tolerance derived from TECL's own tick size**, over every real-TECL day where a reference feed is obtainable, plus the vendor-vs-vendor (Yahoo vs. Stooq) rate at the same tolerance.
*Tolerance derivation (fixes an imported threshold):* Reg NMS Rule 612 sets TECL's minimum price variation at $0.01 (or $0.005 under the 2024 tick-size amendment, effective 2025-11-03) [Evidence: primary]. A flat 1 bp tolerance is at or below one tick above ~$100 and below one half-tick through most of TECL's $10–150 range — ordinary tick-rounding would trip it, making the "disagreement rate" mostly rounding convention. **Revised tolerance: max(2 × current MPV in dollars, 3 bp of that day's close)** — derived from TECL's own price/tick relationship, not imported from rates/FX/large-cap convention.
*Stopping rule:* fixed sample, every real-TECL day in the frozen window; no early stopping, no re-running with a new tolerance after seeing results.
*Frozen before looking:* tolerance formula, reference feed, day list, comparison logic.
*Why it matters:* the charter requires the signal to form "only after the official daily bar is verified" — today only vendor-vs-vendor agreement is checked, which cannot catch a shared vendor bug.

**Experiment 2 — Adjusted-series reconstruction parity check.**
*Estimand:* the maximum absolute daily percentage difference between (a) Montauk's own reconstructed total-return series, built from raw OHLC plus `TECL_distributions.csv` via an independently-derived (not citation-assumed) factor-chain formula, and (b) a second vendor's adjusted series, over the full real-history window.
*Stopping rule:* single pass; report the full distribution, not just the max; do not iterate the formula after seeing results.
*Frozen before looking:* the adjustment formula, distributions-file version, comparison vendor.

**Experiment 3 — Broker opening-order obtainability audit.**
*Estimand:* per broker Max might realistically use, a categorical answer (obtainable / not obtainable / partially obtainable) to "can an after-close order reach the Core Open Auction and fill at the print, with documented behavior for any unfilled remainder?" — sourced from broker documentation or a direct account check, never marketing copy.
*Stopping rule:* one documented answer per broker, or an explicit **insufficient-evidence** verdict where documentation doesn't resolve it — frozen either way.
*Frozen before looking:* the broker list (exactly Max's actual broker(s), not an industry survey).

**Experiment 4 — Execution-cost calibration across the $10,000–$100,000 band.**
*Estimand:* a conservative (upper-bound) calibrated opening-execution cost in bps, one-sided, across the fixed notional band, from whatever TECL-specific spread/impact evidence is obtainable.
*Stopping rule:* one frozen cost number (or piecewise schedule by notional) per cycle; recalibration only on a versioned schedule, never triggered by underperformance.
*Frozen before looking:* the notional band (D59), data source, conservatism rule (e.g., 90th-percentile spread, not median). Until a TECL-specific quote source exists, this experiment's honest output is **insufficient evidence for a point estimate** plus a documented conservative range (§6).

## 4. Null, defect, and planted-signal controls

- **Split-blindness control:** insert a synthetic fake split into a *copy* of raw data; the loader must re-derive a continuous adjusted series or fail loudly.
- **Stale-vendor control:** freeze one vendor's feed for N days while the other updates; confirm cross-vendor agreement flags staleness rather than trusting the frozen copy.
- **Auction-vs-continuous-trade planted signal:** mislabel a same-day continuous-session print as the opening auction print on known-halt/imbalance dates; confirm execution-realism checks detect the mismatch.
- **Vendor-revision/backfill control (new):** distinct from the look-ahead control below — seed a copy of history where a vendor silently restates an *ordinary* historical bar (no split/dividend involved) days later, simulating a backfill; confirm the pipeline flags a bar that changed post-ingestion rather than trusting it forever.
- **Delayed-open control (new):** seed a date where the Core Open Auction cannot resolve at 9:30:00 (simulated unresolved imbalance); confirm the fill-timing model treats this as a distinct state from both a normal open and an intraday halt, not "first print of the day" regardless of timing.
- **Broker-fallback defect control:** if Experiment 3 finds a broker silently downgrades a MOO-style order, seed a day with an unusually wide open-to-first-continuous-trade gap and confirm the backtest's fill assumption is distinguishable from the actual auction print.
- **Look-ahead-through-adjustment control:** confirm a historical date's adjusted series used only distribution/split information *knowable* as of that date — a synthetic "just learned about this 2019 dividend" case must not retroactively change a signal that already fired.
- **What must pass:** all six controls produce a logged failure signal when the defect is present, clean silence when absent.
- **What must fail (correctly reject):** any control where the synthetic defect is *not* detected blocks Gold eligibility for the execution/data layer until fixed.

## 5. False-Gold and false-rejection consequences

A **false Gold** is a configuration certified as beating B&H under a fill/data assumption not actually obtainable — an assumed MOO fill a real broker downgrades, or a mis-adjusted vendor series consumed silently. The cost is direct and asymmetric: real capital deployed against a return path the method never earns, and because 3x leveraged ETFs compound daily, a persistent few-bp underestimate compounds into a materially different terminal wealth path, not a rounding error. This is the most dangerous failure mode here because it is invisible by construction — a broker-fallback defect produces a clean backtest and a worse live result.

A **false rejection** treats an obtainable execution assumption as unobtainable, or miscalibrates a verification check too tight, flagging ordinary vendor rounding as a defect. The cost — missed upside, unnecessary halt noise — is real but bounded and reversible, unlike a false Gold, which surfaces only after capital is already committed.

This asymmetry argues for conservative defaults everywhere this stream controls: a documented, slightly pessimistic cost assumption over an optimistic one; a check that occasionally over-flags over one that ever silently passes a real defect.

## 6. Assumptions and power/limits

- **Sample ceiling.** Real TECL history is ~15–17 years (inception 2008-12-17) with only a handful of independent macro regimes. Any calibrated cost or verification rate has real sampling uncertainty a point estimate understates — report a range, always.
- **No intraday/quote data exists in the repo.** Only daily OHLCV plus distributions; no bid-ask, imbalance, or consolidated-tape history. Experiment 4 is currently **insufficient-evidence for a TECL-specific point estimate**, blocked on acquiring that data.
- **TECL.csv is confirmed split-adjusted, not confirmed total-return-adjusted** — a stated finding (§1, §2), not left to the reader; Experiment 2 must build and validate the total-return series from scratch.
- **Vendor OHLC revision behavior is untested.** Whether Yahoo/Stooq can silently restate an ordinary historical bar after ingestion (distinct from known corporate actions) is not currently monitored; the new vendor-revision control (§4) is the mitigation, but no historical audit of past revisions has been performed.
- **Delayed opens are a distinct, currently under-specified failure mode.** The halt/reopening-auction mechanics were identified via a federal-register search result, not independently re-verified against the live rule text this session (rate-limited on refetch) — treat the §2 delayed-open row as Moderate confidence pending a direct re-check before implementation.
- **Corporate-action detection is retrospective;** a future split, ticker change, or index change requires a live feed or manual watch process this stream specifies (Questionnaire 6, Q5) but cannot itself guarantee.
- **Broker behavior is account- and time-specific** — Experiment 3's answer is a snapshot; re-verify on any broker or platform change.
- **Rule text drifts** — NYSE Arca's rulebook has been amended repeatedly (2015–2026 filings); re-verify current rule numbers/values against the live rulebook before any threshold ships.
- **Where inference is not warranted.** None of this evidence supports future TECL behavior, spread regimes, or broker policy — only "as of mid-2026, here is the documented mechanism." Every number here needs a refresh cadence, not permanence.

## 7. Required fixtures and durable artifacts

**Fixtures:**
- Positive: frozen OHLC slice spanning 2021-03-02 (split), expected split-adjusted series hand-computed from the 10-for-1 ratio, golden file.
- Positive: frozen slice spanning a real distribution ex-date (e.g., 2021-12-09), expected total-return-adjusted value hand-computed, golden file.
- Negative (split-blindness): fake 3-for-1 split copy; expect "FAIL / discontinuity detected."
- Negative (vendor staleness): truncated-feed copy; expect "FAIL / staleness detected."
- Negative (auction mislabeling): mislabeled continuous-print-as-auction case; expect "FAIL / execution-realism check fires."
- Negative (vendor revision): silently-restated ordinary bar; expect "FAIL / post-ingestion change detected."
- Negative (delayed open): simulated unresolved imbalance at 9:30:00; expect `state = delayed_open`, distinct from `normal_open` and `intraday_halt`.

**Executable source registry** (data type → primary endpoint → fallback → refresh cadence → verification method):

| Data type | Primary endpoint | Fallback | Refresh cadence | Verification method |
|---|---|---|---|---|
| Daily OHLCV | Yahoo Finance (current repo source) | Stooq | Per data-refresh run | Vendor-vs-vendor agreement (Exp. 1 tolerance) + monthly exchange/SIP spot-check |
| Official close (spot-check) | Exchange/SIP-derived reference feed (TBD — none in repo today) | N/A until acquired | Monthly (proposed) | Direct comparison to vendor close, per Exp. 1 |
| Corporate actions (splits) | Issuer SEC filing (Form 497 / 8-K) | Exchange SRO alert (e.g., MIAX/OCC memo) | On announcement + periodic backward scan | Manual hand-computed golden-file match |
| Distributions | `data/TECL_distributions.csv` (currently sourced from stockanalysis.com / direxion.com) | Direxion fund-distribution history page | Per ex-date announcement | Cross-check amount against Direxion's own posted distribution history |
| Expense ratio | Direxion current Fact Sheet / prospectus | N/A (single issuer) | Each periodic data refresh | Version-stamp figure + effective date (§8, Decision 3) |
| Order-type/TIF support | Broker's own order-type documentation or account-feature check | Direct support inquiry | On broker/platform change | Experiment 3 audit, re-run on any change |
| Exchange calendar/holidays | NYSE Group Holiday and Early-Closing Calendar | N/A (single authority) | Annually (calendar published ahead) | Diff against prior year's frozen calendar |
| Auction/collar/halt rule text | NYSE Arca rulebook (current, via nyse.com) | SEC EDGAR rule-filing history | Before each implementation change | Diff against the dated snapshot below |

**Failure-state table** (failure mode → detection method → resulting system state → recovery path):

| Failure mode | Detection method | Resulting system state | Recovery path |
|---|---|---|---|
| Vendor close disagrees with exchange reference beyond tolerance | Exp. 1 monthly spot-check | Integrity-halt | Manual reconciliation |
| Two vendors disagree beyond tolerance | Daily cross-vendor check | Integrity-halt, affected day | Escalate to manual check; prefer neither vendor blindly |
| Silent split/corporate-action discontinuity | Split-blindness control | Load rejected, loud failure | Re-derive factor from primary filing; re-run golden fixture |
| Vendor silently restates an ordinary bar | Vendor-revision control (§4) | Flagged "post-ingestion change," quarantined | Confirm against second vendor/exchange reference; accept or reject explicitly |
| Broker downgrades MOO to plain market order | Experiment 3 audit / fallback control | Conservative "first minutes" fill assumed, not auction print | Re-audit broker; else keep conservative assumption |
| Core Open Auction delayed (unresolved imbalance) | Delayed-open control (§4) | `state = delayed_open`, distinct from `normal_open`/`intraday_halt` | Wait for actual auction print, not first available print |
| Intraday trading halt (LULD/regulatory) | Rule 7.11 / LULD monitoring | `state = intraday_halt` | Resume only after confirmed reopening print |
| Product-contract change (ticker, index, leverage) | Manual watch + Questionnaire 6 Q5 policy | Methodology break, recertification required | No automatic ETF substitution |

**Retained acceptance artifacts:**
- A versioned "execution contract" document (Experiment 3's actual output): per broker, exact order type/TIF submitted, documented fill behavior, date last verified.
- A dated snapshot of the NYSE Arca Rule 7.31/7.35/7.11 text actually relied upon at implementation time (not just this report's 2016-vintage PDF), so future amendments can be diffed against what Montauk assumed.

## 8. Unresolved owner decisions

1. **Which broker(s) will actually submit the after-close order, and does that broker demonstrably reach the Arca Core Open Auction?** Highest-priority unresolved fact — a hard gate on trusting *any* Gold row's execution assumption, stated consistently with §1 (not merely a precondition for Experiment 4's cost number). *Default:* confirm order-type support directly before treating any Gold-certified strategy as live-tradeable; if unresolved or negative, fall back to a documented conservative "first minutes of continuous trading" fill model instead of the auction print. *Tradeoff:* trivial effort, blocks only live deployment; skipping it risks certifying a fill nobody can obtain.

2. **What counts as "verified" for the daily close?** *Default:* keep vendor-vs-vendor agreement as the daily gate; add a monthly spot-check against a primary/SIP-derived reference, since two aggregators can share an upstream bug. *Tradeoff:* needs a modest paid source or manual sampling; the alternative leaves a blind spot the "verified close" claim doesn't currently earn.

3. **How should the manifest's expense-ratio ambiguity (0.95% cap vs. 0.87% disclosed net) be resolved?** *Default:* use the currently disclosed net ratio from the latest fact sheet at each refresh, version-stamped with figure and effective date. *Tradeoff:* small recurring maintenance step; prevents silent staleness.

4. **Should Montauk acquire intraday/quote data, or accept execution-cost calibration as a documented conservative range?** *Default:* accept the conservative-range approach for now (no new paid source), labeling Experiment 4's output as **insufficient evidence for a precise point estimate** in every activation review. *Tradeoff:* real quote history would sharpen calibration but is a scope/cost decision only the owner can authorize.

## References

- [NYSE Arca Rule 7.31 & 7.35 (Auctions; Orders and Modifiers), SEC EDGAR Exhibit 5](https://www.sec.gov/files/rules/sro/nysearca/2016/34-79107-ex5.pdf) — Primary, directly fetched/quoted
- [NYSE Arca Rule 7.11 (LULD Trading Pauses), same Exhibit 5](https://www.sec.gov/files/rules/sro/nysearca/2016/34-79107-ex5.pdf) — Primary
- [SEC order approving Rule 7.35/7.11 amendments (delayed-opening/reopening mechanics)](https://www.federalregister.gov/documents/2017/01/26/2017-01718/self-regulatory-organizations-nyse-arca-inc-order-granting-approval-of-proposed-rule-change-as) — Primary; found via search, re-verify live text before implementation
- [Limit Up-Limit Down Plan overview](https://www.luldplan.com/) — Secondary summary of an SEC-approved primary Plan
- [SEC Reg NMS Rule 612 tick-size compliance guide](https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/tick-sizes) — Primary; used to derive Experiment 1's tolerance
- [Direxion Form 497 supplement re: TECL 10-for-1 split (2021-01-29)](https://www.sec.gov/Archives/edgar/data/1424958/000119312521022676/d59468d497.htm) — Primary
- [MIAX corporate-action alert: TECL split](https://www.miaxglobal.com/sites/default/files/alert-files/TECL_Split_48246.pdf) — Primary/regulatory-adjacent
- [Direxion TECL/TECS Fact Sheet](https://www.direxion.com/uploads/TECL-TECS-Fact-Sheet.pdf) — Product-primary, directly fetched
- [CRSP Data Description Guide, Ch. 5](https://leiq.bus.umich.edu/docs/crsp_calculations_splits.pdf) — Primary for base formula only; field-level expression downgraded to Inference (§2)
- [Fidelity Trading FAQs: Order Types](https://www.fidelity.com/trading/faqs-order-types) — Product-primary, directly fetched/quoted
- [Interactive Brokers TWS API docs — Basic Orders](https://interactivebrokers.github.io/tws-api/basic_orders.html) — Primary, directly fetched; **replaces** the prior IBKR Campus glossary link, which lacked the MKT+OPG detail
- [NYSE Group Holiday and Early-Closing Calendar](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx) — Primary
- [Direxion "ETF Liquidity — Four Rules to Trade By"](https://www.direxion.com/education/etf-liquidity-four-rules-to-trade-by) — Product-primary but general
- [Longbridge: U.S. ETF liquidity and bid-ask spreads](https://longbridge.com/en/academy/etf/blog/liquidity-analysis-of-u-s-listed-etfs-how-the-bid-ask-spread-affects-your-trading-costs-100362) — Secondary
- Internal: `data/manifest.json`, `data/TECL.csv`, `data/TECL_distributions.csv` — Primary, directly inspected
- Internal: `charter.md` (§4.2–4.3, §16), `decisions.md` (D29–D30, D46–D59), `Questionnaire 6` (Q5) — Primary, ratified governance
