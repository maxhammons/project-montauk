"""TECL price and distribution data, as three deliberately separate views.

Charter §16 study 2a requires that tradable OHLC, split-adjusted feature prices,
and total-return wealth stay separate, "so a distribution is neither omitted nor
double-counted." Collapsing them is the classic way a backtest quietly grows an
edge it never had: features computed on a total-return series see dividend
adjustments that were not observable at the time, and fills priced off an
adjusted series execute at prices nobody could have traded.

The three views:

``tradable``
    What you could actually buy and sell that day. Split-adjusted so a share
    count is continuous across the 160:1 of splits TECL has had, but *never*
    dividend-adjusted. This is the only view fills may be priced from.

``feature``
    What indicators are computed on. Identical to ``tradable`` today. It exists
    as a separate name because the moment someone wants a dividend-adjusted or
    otherwise-transformed input for signal logic, it must not silently become
    the series fills are priced from.

``total_return``
    Wealth, not price. A share count that grows as distributions are reinvested.
    Only this view answers "would $1,000 have done better." It is never a price
    and may never be used as one.

Distributions follow the symmetric convention D86 and study 2a require:
entitlement on the **ex-date**, cash usable on the **pay-date**. The gap is real
money that is owed but not yet spendable, and treating it as spendable early is
a small, free, entirely fictional return.
"""

from __future__ import annotations

import bisect
import csv
import os
from dataclasses import dataclass, field
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRICES_CSV = os.path.join(REPO, "data", "TECL.csv")
DISTRIBUTIONS_CSV = os.path.join(REPO, "montauk3", "data", "tecl_distributions.csv")

#: First day TECL existed as a real product. Bars before this are synthetic
#: reconstruction and carry only the limited calibrated weight of D106 — they
#: are never real-market passage.
TECL_INCEPTION = date(2008, 12, 17)


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_synthetic: bool


@dataclass(frozen=True)
class Distribution:
    ex_date: date
    pay_date: date
    amount: float
    source: str
    pay_date_basis: str

    @property
    def pay_date_is_inferred(self) -> bool:
        return self.pay_date_basis != "reported"


class DataError(Exception):
    """Raised when the data cannot support an honest answer.

    Deliberately not a warning. Charter §4: a configuration with missing
    required data or insufficient evidence cannot be Gold, and the failure must
    be visible rather than absorbed.
    """


@dataclass
class TeclData:
    """Loaded TECL bars and distributions, with the three views over them."""

    bars: list[Bar]
    distributions: list[Distribution]
    _index: dict[date, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._index = {b.day: i for i, b in enumerate(self.bars)}
        self._days = [b.day for b in self.bars]

    # --- lookup --------------------------------------------------------------

    def bar_on(self, day: date) -> Bar | None:
        i = self._index.get(day)
        return self.bars[i] if i is not None else None

    def bar_on_or_before(self, day: date) -> Bar | None:
        """The most recent bar at or before ``day``.

        Used for dates that are not trading days — a pay date landing on a
        weekend, for instance. Looking *forward* here would be lookahead, so
        this only ever looks back.
        """
        i = bisect.bisect_right(self._days, day) - 1
        return self.bars[i] if i >= 0 else None

    def next_bar_after(self, day: date) -> Bar | None:
        """The first bar strictly after ``day``.

        This is the execution primitive: a signal formed after the verified
        close of day D fills at the open of the bar this returns.
        """
        i = bisect.bisect_right(self._days, day)
        return self.bars[i] if i < len(self.bars) else None

    def bars_from(self, start: date) -> list[Bar]:
        i = bisect.bisect_left(self._days, start)
        return self.bars[i:]

    # --- view: tradable ------------------------------------------------------

    def tradable(self, day: date) -> Bar | None:
        """The only view fills may be priced from. Never dividend-adjusted."""
        return self.bar_on(day)

    # --- view: feature -------------------------------------------------------

    def feature_closes(self, start: date | None = None) -> list[tuple[date, float]]:
        """Closes for indicator computation.

        Identical to tradable closes today. Kept as its own accessor so that a
        future transformed input cannot silently leak into fill pricing.
        """
        bars = self.bars_from(start) if start else self.bars
        return [(b.day, b.close) for b in bars]

    # --- view: total return --------------------------------------------------

    def total_return_shares(
        self,
        start: date,
        end: date | None = None,
        initial_shares: float = 1.0,
    ) -> float:
        """Shares held at ``end`` after reinvesting every distribution.

        Entitlement is fixed on the ex-date: you must already hold the shares
        when the market opens ex-dividend. The cash is not usable until the pay
        date, so reinvestment happens at the pay-date close — the first price at
        which the money genuinely could have been spent.

        Reinvesting at the ex-date close instead would be worth a few days of
        market drift on every distribution, compounded across seventeen years,
        for free.
        """
        shares = initial_shares
        for dist in self.distributions:
            if dist.ex_date < start:
                continue
            if end is not None and dist.pay_date > end:
                continue
            # A pay date past the end of the data cannot be priced. Falling back
            # to the last available bar would reinvest at a stale price and
            # quietly invent shares — so this is an error, not a best effort.
            # Under D92 this is "insufficient evidence", which is never a pass.
            if dist.pay_date > self._days[-1]:
                raise DataError(
                    f"pay date {dist.pay_date} (ex-date {dist.ex_date}) is past the "
                    f"last available bar {self._days[-1]}; cannot price the "
                    f"reinvestment. Refresh prices or exclude this distribution."
                )
            pay_bar = self.bar_on_or_before(dist.pay_date)
            if pay_bar is None:
                raise DataError(
                    f"no price on or before pay date {dist.pay_date} "
                    f"for the distribution with ex-date {dist.ex_date}"
                )
            shares += shares * dist.amount / pay_bar.close
        return shares

    def distributions_between(self, start: date, end: date) -> list[Distribution]:
        return [d for d in self.distributions if start <= d.ex_date <= end]


# --- loading -----------------------------------------------------------------


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"true", "1", "yes"}


def load_bars(path: str = PRICES_CSV) -> list[Bar]:
    bars: list[Bar] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if not row.get("close"):
                continue
            bars.append(Bar(
                day=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"] or 0),
                is_synthetic=_parse_bool(row.get("is_synthetic", "")),
            ))
    bars.sort(key=lambda b: b.day)
    return bars


def load_distributions(path: str = DISTRIBUTIONS_CSV) -> list[Distribution]:
    dists: list[Distribution] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            dists.append(Distribution(
                ex_date=date.fromisoformat(row["ex_date"]),
                pay_date=date.fromisoformat(row["pay_date"]),
                amount=float(row["amount"]),
                source=row["source"],
                pay_date_basis=row["pay_date_basis"],
            ))
    dists.sort(key=lambda d: d.ex_date)
    return dists


def load(
    prices: str = PRICES_CSV,
    distributions: str = DISTRIBUTIONS_CSV,
) -> TeclData:
    return TeclData(bars=load_bars(prices), distributions=load_distributions(distributions))
