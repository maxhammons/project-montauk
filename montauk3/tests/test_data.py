"""Charter §16 study 2a's four required tests, plus the view separation.

The study names exactly four failures the data layer must detect: missing
distributions, early cash availability, future-action leakage, and
double-counting against an adjusted price series. Each gets a test that fails
loudly rather than a comment saying it was considered.
"""

from __future__ import annotations

import csv
from datetime import date

import pytest

from montauk3.core import data as D
from montauk3.core.data import Bar, DataError, Distribution, TeclData


def _bars(*rows: tuple[str, float]) -> list[Bar]:
    return [
        Bar(day=date.fromisoformat(d), open=p, high=p, low=p, close=p,
            volume=1_000, is_synthetic=False)
        for d, p in rows
    ]


def _dist(ex: str, pay: str, amount: float) -> Distribution:
    return Distribution(
        ex_date=date.fromisoformat(ex), pay_date=date.fromisoformat(pay),
        amount=amount, source="test", pay_date_basis="reported",
    )


# --- required test 1: missing distributions ----------------------------------

def test_ledger_covers_the_whole_real_history():
    """A ledger that starts after inception silently understates both legs.

    This is the defect study 2a was written to find: 2.0's ledger began
    2021-12-09 while TECL has paid since 2009-03-24, so twelve years of cash
    were missing from every backtest.
    """
    dists = D.load_distributions()
    assert dists, "distribution ledger is empty"
    assert dists[0].ex_date <= date(2009, 3, 24), (
        f"ledger starts {dists[0].ex_date}; TECL has paid since 2009-03-24. "
        "A ledger that begins later understates both the strategy and B&H."
    )


def test_every_distribution_lands_inside_the_real_era():
    """Nothing may be dated before the product existed."""
    for dist in D.load_distributions():
        assert dist.ex_date >= D.TECL_INCEPTION, (
            f"distribution dated {dist.ex_date}, before TECL inception "
            f"{D.TECL_INCEPTION}"
        )


def test_missing_price_for_a_pay_date_raises_rather_than_skipping():
    """Silently skipping an unpriceable distribution loses real money from the
    comparison. It has to be an error."""
    tecl = TeclData(
        bars=_bars(("2020-01-02", 100.0), ("2020-01-03", 101.0)),
        distributions=[_dist("2020-01-03", "2099-01-01", 1.0)],
    )
    with pytest.raises(DataError, match="pay date"):
        tecl.total_return_shares(start=date(2020, 1, 2))


# --- required test 2: early cash availability --------------------------------

def test_cash_is_not_spendable_before_the_pay_date():
    """Entitlement is the ex-date; availability is the pay date.

    Reinvesting at the ex-date close instead is worth a few days of drift on
    every distribution, free and fictional. Here the price rises between the
    two dates, so reinvesting early buys more shares — the test pins that we
    take the later, correct, smaller number.
    """
    tecl = TeclData(
        bars=_bars(
            ("2020-01-02", 100.0),   # ex-date: cheap
            ("2020-01-09", 200.0),   # pay date: expensive
        ),
        distributions=[_dist("2020-01-02", "2020-01-09", 10.0)],
    )
    shares = tecl.total_return_shares(start=date(2020, 1, 2), initial_shares=1.0)

    assert shares == pytest.approx(1 + 10.0 / 200.0)      # bought at pay-date price
    assert shares != pytest.approx(1 + 10.0 / 100.0)      # not the ex-date price


def test_pay_date_on_a_non_trading_day_looks_backward_not_forward():
    """A pay date on a weekend must resolve to the prior close.

    Resolving forward would price the reinvestment at a bar that had not
    happened when the cash arrived — lookahead, in the one place it is easy to
    write by accident.
    """
    tecl = TeclData(
        bars=_bars(("2020-01-03", 100.0), ("2020-01-06", 999.0)),
        distributions=[_dist("2020-01-02", "2020-01-04", 10.0)],  # Saturday
    )
    shares = tecl.total_return_shares(start=date(2020, 1, 1), initial_shares=1.0)
    assert shares == pytest.approx(1 + 10.0 / 100.0), "resolved forward to the 6th"


# --- required test 3: future-action leakage ----------------------------------

def test_distributions_before_the_start_are_not_credited():
    """A strategy cannot collect a payment from before it was eligible."""
    tecl = TeclData(
        bars=_bars(("2019-01-02", 50.0), ("2020-01-02", 100.0),
                   ("2020-06-01", 120.0), ("2020-06-08", 120.0)),
        distributions=[_dist("2019-01-02", "2019-01-09", 5.0),
                       _dist("2020-06-01", "2020-06-08", 5.0)],
    )
    shares = tecl.total_return_shares(start=date(2020, 1, 2), initial_shares=1.0)
    assert shares == pytest.approx(1 + 5.0 / 120.0), "credited the 2019 payment"


def test_next_bar_after_never_returns_the_same_day():
    """The execution primitive. A signal formed after the close of D must fill
    on a strictly later bar; returning D would be same-bar lookahead."""
    tecl = TeclData(bars=_bars(("2020-01-02", 1.0), ("2020-01-03", 2.0)), distributions=[])
    nxt = tecl.next_bar_after(date(2020, 1, 2))
    assert nxt is not None and nxt.day == date(2020, 1, 3)


def test_bar_on_or_before_never_returns_a_future_bar():
    tecl = TeclData(bars=_bars(("2020-01-02", 1.0), ("2020-01-10", 2.0)), distributions=[])
    got = tecl.bar_on_or_before(date(2020, 1, 5))
    assert got is not None and got.day == date(2020, 1, 2)


# --- required test 4: double-counting against an adjusted series -------------

def test_price_series_is_not_dividend_adjusted():
    """If the price series were already total-return, applying the ledger on
    top would count every distribution twice.

    Detected behaviourally: on a large ex-date the raw series gaps down by
    roughly the distribution, while an adjusted series would not. The
    2025-12-10 payment was 5.9% of the prior close — far outside noise.
    """
    tecl = D.load()
    ex = date(2025, 12, 10)
    dist = next(d for d in tecl.distributions if d.ex_date == ex)

    bar = tecl.bar_on(ex)
    prev = tecl.bar_on_or_before(date(2025, 12, 9))
    assert bar and prev

    gap_pct = 100 * (bar.open - prev.close) / prev.close
    dist_pct = 100 * dist.amount / prev.close

    assert dist_pct > 3, "test premise: this should be a large distribution"
    assert gap_pct < -1, (
        f"ex-date gap was {gap_pct:+.2f}% against a {dist_pct:.2f}% distribution. "
        "No gap suggests the price series is already dividend-adjusted, in which "
        "case applying the ledger double-counts."
    )


def test_splits_are_already_applied_to_prices():
    """Dividend amounts are split-adjusted, so prices must be too, or the two
    are in different units and reinvestment is wrong by up to 160x."""
    tecl = D.load()
    for split_day in (date(2010, 5, 5), date(2015, 5, 20), date(2021, 3, 2)):
        bar = tecl.bar_on(split_day)
        prev = tecl.bar_on_or_before(date.fromordinal(split_day.toordinal() - 1))
        if not bar or not prev:
            continue
        ratio = prev.close / bar.close
        assert 0.5 < ratio < 2.0, (
            f"{split_day}: close moved {ratio:.2f}x across a split date. "
            "A 4x or 10x jump means prices are raw while dividends are "
            "split-adjusted."
        )


def test_no_duplicate_ex_dates():
    """A duplicated row pays the same distribution twice."""
    dists = D.load_distributions()
    seen = [d.ex_date for d in dists]
    assert len(seen) == len(set(seen)), "duplicate ex-dates in the ledger"


# --- view separation ---------------------------------------------------------

def test_tradable_view_is_never_the_total_return_view():
    """Fills priced off a wealth series execute at prices nobody could trade."""
    tecl = D.load()
    day = date(2025, 12, 10)
    tradable = tecl.tradable(day)
    assert tradable is not None
    shares = tecl.total_return_shares(start=D.TECL_INCEPTION, end=day)
    assert shares > 1.0, "total-return shares should have grown by 2025"
    assert not isinstance(shares, Bar), "the wealth view must not be a price"


def test_pay_date_basis_is_recorded_for_every_row():
    """Inferred pay dates must stay visibly inferred. An inference that loses
    its label becomes a fact nobody remembers assuming."""
    with open(D.DISTRIBUTIONS_CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    for row in rows:
        assert row["pay_date_basis"] in {"reported", "inferred_ex_plus_7d"}, row
        assert row["source"] in {"direxion", "yahoo"}, row


def test_inferred_pay_dates_are_never_before_their_ex_date():
    for dist in D.load_distributions():
        assert dist.pay_date > dist.ex_date, (
            f"{dist.ex_date}: pay date {dist.pay_date} is not after the ex-date"
        )
