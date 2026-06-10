"""Paper/live fills journal + signal reconciliation (Phase 3.2, 2026-06-09).

WHY this exists: Montauk's daily risk_on/risk_off signal is executed manually
in a brokerage account, so the engine's same-close fill assumption is never
exactly what happens in the account. This module keeps an append-only journal
of the fills that actually happened (`runs/ops/fills.jsonl`) and reconciles
them against the immutable signal snapshots in `signals/` — measuring realized
slippage against the next-snapshot-close execution proxy (the same convention
`ops.live_holdout.execution_proxy` uses) and flagging signal events that were
never executed at all (execution-discipline gaps, deep-val D5.2-D5.4).

The journal is append-only on purpose: like the signal snapshots, it is an
immutable point-in-time record — corrections are new entries, not edits.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import RUNS_DIR, SIGNALS_DIR

OPS_RUNS_DIR = RUNS_DIR / "ops"
FILLS_PATH = OPS_RUNS_DIR / "fills.jsonl"
FILL_RECONCILIATION_PATH = OPS_RUNS_DIR / "fill_reconciliation.json"

VALID_ACTIONS = ("buy", "sell")

# A fill is credited to a signal if it lands within this many trading days
# after the signal date (same-day manual execution after the close counts
# too). Three days is deliberately forgiving — the point is to catch *missed*
# executions, not to punish a one-day delay.
MATCH_WINDOW_TRADING_DAYS = 3


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def _validate_date(value: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"trade_date must be YYYY-MM-DD, got {value!r}") from exc


def record_fill(
    *,
    trade_date: str,
    action: str,
    shares: float,
    price: float,
    fees: float = 0.0,
    ticker: str = "TECL",
    note: str | None = None,
    fills_path: Path = FILLS_PATH,
) -> dict[str, Any]:
    """Validate and append one executed fill to the append-only journal."""

    trade_date = _validate_date(trade_date)
    action = str(action).lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f"action must be one of {VALID_ACTIONS}, got {action!r}")
    try:
        shares = float(shares)
        price = float(price)
        fees = float(fees)
    except (TypeError, ValueError) as exc:
        raise ValueError("shares, price, and fees must be numeric") from exc
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")
    if price <= 0:
        raise ValueError(f"price must be positive, got {price}")
    if fees < 0:
        raise ValueError(f"fees must be >= 0, got {fees}")

    entry = {
        "recorded_utc": utc_now_iso(),
        "trade_date": trade_date,
        "action": action,
        "ticker": str(ticker or "TECL"),
        "shares": shares,
        "price": price,
        "fees": fees,
        "note": str(note) if note else None,
    }
    fills_path.parent.mkdir(parents=True, exist_ok=True)
    with fills_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=False, default=str))
        f.write("\n")
    return entry


def read_fills(fills_path: Path = FILLS_PATH) -> list[dict[str, Any]]:
    if not fills_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with fills_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_snapshots(signals_dir: Path) -> list[dict[str, Any]]:
    # Local, dependency-light loader (vs ops.live_holdout.load_signal_snapshots)
    # so the fills CLI never drags the engine import chain in just to read JSON.
    if not signals_dir.exists():
        return []
    snapshots = []
    for path in sorted(signals_dir.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            snapshots.append(json.load(f))
    snapshots.sort(key=lambda s: str(s.get("data_end_date") or ""))
    return snapshots


def _window_end(snapshot_dates: list[str], index: int) -> str:
    """Last acceptable fill date for the signal at ``index``.

    Trading days are proxied by the snapshot calendar itself (one snapshot per
    trading day). Near the live edge — where the later snapshots don't exist
    yet — the remainder is covered by calendar days plus a 2-day weekend
    buffer, so a just-fired signal is never instantly "missed".
    """

    forward = snapshot_dates[index + 1 : index + 1 + MATCH_WINDOW_TRADING_DAYS]
    if len(forward) == MATCH_WINDOW_TRADING_DAYS:
        return forward[-1]
    base = date.fromisoformat(forward[-1] if forward else snapshot_dates[index])
    remaining = MATCH_WINDOW_TRADING_DAYS - len(forward)
    return (base + timedelta(days=remaining + 2)).isoformat()


def _slippage_bps(action: str, proxy_close: float | None, fill_price: float | None) -> float | None:
    """Signed execution cost vs the proxy, in basis points.

    Positive = the fill was worse than the assumed execution (paid more on a
    buy, received less on a sell); negative = price improvement. Keeping the
    sign cost-oriented lets mean/worst aggregate across both actions.
    """

    if not proxy_close or not fill_price:
        return None
    if action == "buy":
        return (fill_price - proxy_close) / proxy_close * 10000.0
    return (proxy_close - fill_price) / proxy_close * 10000.0


def reconcile(
    signals_dir: Path = SIGNALS_DIR,
    fills_path: Path = FILLS_PATH,
) -> dict[str, Any]:
    """Match journal fills against signal buy/sell events and grade execution."""

    snapshots = _load_snapshots(signals_dir)
    snapshot_dates = [str(s.get("data_end_date") or "") for s in snapshots]
    fills = sorted(read_fills(fills_path), key=lambda f: str(f.get("trade_date") or ""))
    used_fills: set[int] = set()
    matched: list[dict[str, Any]] = []
    unmatched_signals: list[dict[str, Any]] = []

    for i, snapshot in enumerate(snapshots):
        if snapshot.get("buy_event"):
            action = "buy"
        elif snapshot.get("sell_event"):
            action = "sell"
        else:
            continue
        signal_date = snapshot_dates[i]
        window_end = _window_end(snapshot_dates, i)
        # Assumed execution = next snapshot's close after the signal date —
        # the same next-open proxy convention as live_holdout.execution_proxy.
        proxy_date = snapshot_dates[i + 1] if i + 1 < len(snapshots) else None
        proxy_close = snapshots[i + 1].get("close") if i + 1 < len(snapshots) else None

        fill_index = None
        for j, fill in enumerate(fills):
            if j in used_fills or fill.get("action") != action:
                continue
            fill_date = str(fill.get("trade_date") or "")
            if signal_date <= fill_date <= window_end:
                fill_index = j
                break
        event = {
            "signal_date": signal_date,
            "action": action,
            "signal_close": snapshot.get("close"),
            "proxy_execution_date": proxy_date,
            "proxy_execution_close": proxy_close,
            "match_window_end": window_end,
        }
        if fill_index is None:
            unmatched_signals.append(event)
            continue
        used_fills.add(fill_index)
        fill = fills[fill_index]
        slippage = _slippage_bps(action, _as_float(proxy_close), _as_float(fill.get("price")))
        matched.append(
            {
                **event,
                "fill": fill,
                "slippage_bps": round(slippage, 4) if slippage is not None else None,
            }
        )

    unmatched_fills = [fill for j, fill in enumerate(fills) if j not in used_fills]
    n_signal_events = len(matched) + len(unmatched_signals)
    slippages = [m["slippage_bps"] for m in matched if m["slippage_bps"] is not None]
    summary = {
        "n_signal_events": n_signal_events,
        "n_fills": len(fills),
        "n_matched": len(matched),
        "mean_slippage_bps": round(sum(slippages) / len(slippages), 4) if slippages else None,
        "worst_slippage_bps": round(max(slippages), 4) if slippages else None,
        "discipline_rate": round(len(matched) / n_signal_events, 4) if n_signal_events else None,
    }
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "signals_dir": str(signals_dir),
        "fills_path": str(fills_path),
        "matched": matched,
        "unmatched_signals": unmatched_signals,
        "unmatched_fills": unmatched_fills,
        "summary": summary,
    }


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Montauk paper/live fills journal + reconciliation.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Append one executed fill to the journal.")
    record.add_argument("--date", required=True, help="Trade date (YYYY-MM-DD).")
    record.add_argument("--action", required=True, choices=VALID_ACTIONS)
    record.add_argument("--shares", required=True, type=float)
    record.add_argument("--price", required=True, type=float)
    record.add_argument("--fees", type=float, default=0.0)
    record.add_argument("--ticker", default="TECL")
    record.add_argument("--note", default=None)
    record.add_argument("--journal", type=Path, default=FILLS_PATH, help="Journal path override (testing).")

    rec = sub.add_parser("reconcile", help="Reconcile journal fills against signal snapshots.")
    rec.add_argument("--signals-dir", type=Path, default=SIGNALS_DIR)
    rec.add_argument("--journal", type=Path, default=FILLS_PATH)
    rec.add_argument("--output", type=Path, default=FILL_RECONCILIATION_PATH)
    rec.add_argument("--json", action="store_true", help="Emit full JSON report.")

    args = parser.parse_args(argv)

    if args.command == "record":
        entry = record_fill(
            trade_date=args.date,
            action=args.action,
            shares=args.shares,
            price=args.price,
            fees=args.fees,
            ticker=args.ticker,
            note=args.note,
            fills_path=args.journal,
        )
        print(f"recorded: {entry['action']} {entry['shares']} {entry['ticker']} @ {entry['price']} on {entry['trade_date']}")
        return 0

    report = reconcile(signals_dir=args.signals_dir, fills_path=args.journal)
    _write_json(args.output, report)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        summary = report["summary"]
        print(
            f"fill reconciliation: {summary['n_matched']} matched / "
            f"{summary['n_signal_events']} signal events "
            f"(discipline_rate={summary['discipline_rate']})"
        )
        if summary["mean_slippage_bps"] is not None:
            print(
                f"slippage vs next-close proxy: mean={summary['mean_slippage_bps']} bps, "
                f"worst={summary['worst_slippage_bps']} bps"
            )
        for gap in report["unmatched_signals"]:
            print(f"- MISSED: {gap['action']} signal on {gap['signal_date']} has no journal fill")
        for stray in report["unmatched_fills"]:
            print(f"- STRAY: {stray['action']} fill on {stray['trade_date']} matches no signal event")
        print(f"report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
