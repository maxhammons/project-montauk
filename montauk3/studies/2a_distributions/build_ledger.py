"""Phase 1 study 2a — rebuild the TECL distribution ledger.

Montauk 2.0's ledger (``data/TECL_distributions.csv``) begins 2021-12-09 and
holds 13 rows. TECL has paid 28 distributions since 2009-03-24, so roughly half
the history is absent. Every missing payment is cash both the strategy and
matched buy-and-hold should have received, which means "beats B&H" is currently
computed on incomplete data.

This script rebuilds the ledger from scratch and writes it to a 3.0-owned path.
It never touches 2.0's file: ``scripts/data/loader.py::_merge_tecl_distributions``
reads that one, and changing it would move 2.0's backtest results, which D121
forbids.

Sources, in precedence order:

1. **Direxion** (issuer, primary) via 2.0's existing ledger — full precision plus
   the income / short-term / long-term breakdown and real record and pay dates.
   Authoritative wherever it has a row.
2. **Yahoo chart API** (``events=div|split``) — the project's standard price
   source, so units already agree with ``data/TECL.csv``. Supplies ex-date and
   amount only, at reduced precision. Used for the pre-2022 rows Direxion's
   export does not cover.

Both agree on the count (28) and the earliest ex-date (2009-03-24); the
independent corroboration is what lets the Yahoo rows carry weight.

Units: Yahoo returns dividends already divided by every later split, and
``data/TECL.csv`` stores split-adjusted prices, so amounts and prices are in the
same units and no rescaling is applied. TECL has split 4:1 (2010-05-05), 4:1
(2015-05-20), and 10:1 (2021-03-02) — 160:1 combined. That factor is why the
2009 rows look implausibly small in isolation.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
LEGACY_LEDGER = os.path.join(REPO, "data", "TECL_distributions.csv")
OUT = os.path.join(REPO, "montauk3", "data", "tecl_distributions.csv")

# 2008-12-17 (TECL inception) through today, widened at both ends.
YAHOO = (
    "https://query1.finance.yahoo.com/v8/finance/chart/TECL"
    "?period1=1229472000&period2={end}&interval=1d&events=div%7Csplit"
)

# Observed on all 13 Direxion rows: pay date is ex-date + 7 calendar days, or 8
# when the settlement window crosses a holiday. 7 is the modal value and the
# conservative one — it makes cash available no later than reality, never
# earlier, which is the direction that cannot manufacture return.
INFERRED_PAY_LAG_DAYS = 7

FIELDS = [
    "ex_date", "record_date", "pay_date", "amount",
    "income_dividend", "short_term_capital_gain", "long_term_capital_gain",
    "pay_date_basis", "source",
]


def fetch_yahoo() -> tuple[dict[str, float], list[tuple[str, str]]]:
    """Return {ex_date: amount} and [(date, split_ratio)] from the chart API."""
    url = YAHOO.format(end=int(dt.datetime.now().timestamp()) + 86400)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)

    events = payload["chart"]["result"][0].get("events", {})

    def day(ts: int) -> str:
        return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")

    divs = {day(v["date"]): float(v["amount"])
            for v in events.get("dividends", {}).values()}
    splits = sorted((day(v["date"]), v.get("splitRatio", "?"))
                    for v in events.get("splits", {}).values())
    return divs, splits


def load_legacy() -> dict[str, dict[str, str]]:
    """Direxion-sourced rows from 2.0's ledger, keyed by ex-date."""
    with open(LEGACY_LEDGER, newline="") as fh:
        return {r["ex_date"]: r for r in csv.DictReader(fh)}


def build() -> list[dict[str, str]]:
    yahoo, splits = fetch_yahoo()
    legacy = load_legacy()

    rows: list[dict[str, str]] = []
    for ex in sorted(set(yahoo) | set(legacy)):
        if ex in legacy:
            src = legacy[ex]
            rows.append({
                "ex_date": ex,
                "record_date": src["record_date"],
                "pay_date": src["pay_date"],
                "amount": src["amount"],
                "income_dividend": src["income_dividend"],
                "short_term_capital_gain": src["short_term_capital_gain"],
                "long_term_capital_gain": src["long_term_capital_gain"],
                "pay_date_basis": "reported",
                "source": "direxion",
            })
        else:
            pay = (dt.date.fromisoformat(ex)
                   + dt.timedelta(days=INFERRED_PAY_LAG_DAYS)).isoformat()
            rows.append({
                "ex_date": ex,
                "record_date": "",          # not published by Yahoo
                "pay_date": pay,
                "amount": f"{yahoo[ex]:.5f}",
                "income_dividend": "",      # Yahoo does not break out the character
                "short_term_capital_gain": "",
                "long_term_capital_gain": "",
                "pay_date_basis": "inferred_ex_plus_7d",
                "source": "yahoo",
            })
    return rows, yahoo, legacy, splits


def main() -> None:
    rows, yahoo, legacy, splits = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    added = [r["ex_date"] for r in rows if r["source"] == "yahoo"]
    print(f"wrote {OUT}")
    print(f"  {len(rows)} distributions, {rows[0]['ex_date']} -> {rows[-1]['ex_date']}")
    print(f"  {len(legacy)} from direxion (reported pay dates)")
    print(f"  {len(added)} from yahoo (inferred pay dates)")
    print(f"  splits on record: {', '.join(f'{d} {r}' for d, r in splits)}")

    overlap = [ex for ex in legacy if ex in yahoo]
    disagree = [ex for ex in overlap
                if abs(float(legacy[ex]["amount"]) - yahoo[ex]) > 0.01]
    print(f"  cross-check: {len(overlap)} rows in both sources, "
          f"{len(disagree)} disagree by more than $0.01")


if __name__ == "__main__":
    main()
