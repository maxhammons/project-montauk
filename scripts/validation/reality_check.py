#!/usr/bin/env python3
"""Replay leaderboard signal artifacts with realistic next-open fills.

This is the execution-reality gate for the audit question:

    If the signal is known after the close, what would the current leaderboard
    have done when filled at the next session's open?

The script does not re-optimize or regenerate signals. It consumes existing
`spike/runs/*/dashboard_data.json` artifacts, replays their buy/sell events
against local TECL opens, and writes a compact JSON report.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEADERBOARD_PATH = PROJECT_ROOT / "spike" / "leaderboard.json"
RUNS_DIR = PROJECT_ROOT / "spike" / "runs"
TECL_PATH = PROJECT_ROOT / "data" / "TECL.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "runs" / "reality_check" / "latest.json"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from data.loader import get_tecl_data  # noqa: E402


@dataclass(frozen=True)
class PriceBar:
    date: str
    open: float
    close: float
    distribution: float = 0.0


def _load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def _params_key(params: dict[str, Any]) -> str:
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))


def _load_prices() -> tuple[list[PriceBar], dict[str, int]]:
    rows: list[PriceBar] = []
    df = get_tecl_data(use_yfinance=False)
    for row in df.to_dict("records"):
        rows.append(
            PriceBar(
                date=str(row["date"])[:10],
                open=float(row["open"]),
                close=float(row["close"]),
                distribution=float(row.get("distribution") or 0.0),
            )
        )
    return rows, {row.date: i for i, row in enumerate(rows)}


def _run_sort_key(path: Path) -> int:
    try:
        return int(path.parent.name)
    except ValueError:
        return -1


def _index_dashboard_artifacts() -> dict[tuple[str, str], Path]:
    indexed: dict[tuple[str, str], Path] = {}
    for path in sorted(
        RUNS_DIR.glob("*/dashboard_data.json"),
        key=_run_sort_key,
        reverse=True,
    ):
        try:
            payload = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        strategy = payload.get("strategy")
        if not strategy:
            continue
        key = (strategy, _params_key(payload.get("params") or {}))
        indexed.setdefault(key, path)
    return indexed


def _has_explicit_events(signal_series: list[dict[str, Any]]) -> bool:
    return any(row.get("buy_event") or row.get("sell_event") for row in signal_series)


def _state_is_on(row: dict[str, Any]) -> bool:
    if "risk_on" in row:
        return bool(row["risk_on"])
    return row.get("risk_state") == "risk_on"


def _signal_events(signal_series: list[dict[str, Any]]) -> dict[str, str]:
    events: dict[str, str] = {}
    explicit_events = _has_explicit_events(signal_series)
    prior_state = _state_is_on(signal_series[0]) if signal_series else False

    for row in signal_series:
        date = row.get("date")
        if not date:
            continue
        if explicit_events:
            buy_event = bool(row.get("buy_event"))
            sell_event = bool(row.get("sell_event"))
        else:
            state = _state_is_on(row)
            buy_event = state and not prior_state
            sell_event = prior_state and not state
            prior_state = state

        if sell_event:
            events[date] = "sell"
        elif buy_event:
            events[date] = "buy"
    return events


def _replay_next_open(
    signal_series: list[dict[str, Any]],
    prices: list[PriceBar],
    price_index: dict[str, int],
    *,
    slippage_bps: float,
    initial_capital: float = 1000.0,
) -> dict[str, Any]:
    slippage = slippage_bps / 10_000.0
    events = _signal_events(signal_series)

    equity = initial_capital
    shares = 0.0
    in_trade = False
    entry_price = 0.0
    entry_date = ""
    trades: list[dict[str, Any]] = []
    skipped_events: list[dict[str, Any]] = []
    equity_curve: list[float] = []
    distribution_cash = 0.0
    pending_action = ""
    pending_signal_date = ""

    for i, bar in enumerate(prices):
        if in_trade and bar.distribution > 0:
            cash = shares * bar.distribution
            equity += cash
            distribution_cash += cash

        if pending_action == "sell" and in_trade:
            exit_price = bar.open * (1.0 - slippage)
            equity += shares * (exit_price - entry_price)
            trades.append(
                {
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": bar.date,
                    "exit_price": exit_price,
                    "pnl_pct": (exit_price / entry_price - 1.0) * 100.0,
                    "signal_date": pending_signal_date,
                }
            )
            shares = 0.0
            entry_price = 0.0
            entry_date = ""
            in_trade = False
        elif pending_action == "buy" and not in_trade:
            entry_price = bar.open * (1.0 + slippage)
            if entry_price > 0:
                shares = equity / entry_price
                entry_date = bar.date
                in_trade = True
        pending_action = ""
        pending_signal_date = ""

        mark_equity = equity + shares * (bar.close - entry_price) if in_trade else equity
        equity_curve.append(mark_equity)

        action = events.get(bar.date)
        if not action or i + 1 >= len(prices):
            continue
        if action == "sell" and in_trade:
            pending_action = "sell"
            pending_signal_date = bar.date
        elif action == "sell":
            skipped_events.append({"date": bar.date, "event": "sell", "reason": "flat"})
        elif action == "buy" and not in_trade:
            pending_action = "buy"
            pending_signal_date = bar.date
        elif action == "buy":
            skipped_events.append({"date": bar.date, "event": "buy", "reason": "long"})

    if in_trade:
        final_bar = prices[-1]
        exit_price = final_bar.close
        equity += shares * (exit_price - entry_price)
        trades.append(
            {
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_date": final_bar.date,
                "exit_price": exit_price,
                "pnl_pct": (exit_price / entry_price - 1.0) * 100.0,
                "signal_date": final_bar.date,
                "forced_exit": "end_of_data",
            }
        )
        equity_curve[-1] = equity

    first_close = prices[0].close
    last_close = prices[-1].close
    if first_close > 0:
        bah_shares = initial_capital / first_close
        bah_distribution_cash = bah_shares * sum(bar.distribution for bar in prices[1:])
        bah_final = bah_shares * last_close + bah_distribution_cash
    else:
        bah_distribution_cash = math.nan
        bah_final = math.nan
    share_multiple = equity / bah_final if bah_final and bah_final > 0 else math.nan
    max_drawdown_pct = 0.0
    peak = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak - value) / peak * 100.0)

    return {
        "slippage_bps": slippage_bps,
        "terminal_equity": round(equity, 6),
        "share_multiple": round(share_multiple, 6),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "num_trades": len(trades),
        "distribution_cash": round(distribution_cash, 6),
        "bah_distribution_cash": round(bah_distribution_cash, 6),
        "trades": trades,
        "skipped_events": skipped_events,
    }


def _find_close_share_multiple(leaderboard_entry: dict[str, Any], artifact: dict[str, Any]) -> float | None:
    for source in (artifact.get("metrics") or {}, leaderboard_entry.get("metrics") or {}):
        value = source.get("share_multiple")
        if value is not None:
            return float(value)
    return None


def _find_metric(
    leaderboard_entry: dict[str, Any],
    artifact: dict[str, Any],
    name: str,
) -> float | None:
    for source in (artifact.get("metrics") or {}, leaderboard_entry.get("metrics") or {}):
        value = source.get(name)
        if value is None and name == "max_drawdown_pct":
            value = source.get("max_dd")
        if value is not None:
            return float(value)
    return None


def build_report(top: int, *, slippage_bps: list[float]) -> dict[str, Any]:
    leaderboard = _load_json(LEADERBOARD_PATH)
    if not isinstance(leaderboard, list):
        raise ValueError("spike/leaderboard.json must contain a list")

    prices, price_index = _load_prices()
    artifacts = _index_dashboard_artifacts()
    rows: list[dict[str, Any]] = []

    for rank, entry in enumerate(leaderboard[:top], start=1):
        strategy = entry.get("strategy")
        params = entry.get("params") or {}
        key = (strategy, _params_key(params))
        artifact_path = artifacts.get(key)
        if artifact_path is None:
            rows.append(
                {
                    "rank": rank,
                    "strategy": strategy,
                    "display_name": entry.get("display_name"),
                    "status": "missing_artifact",
                    "gate_pass": False,
                }
            )
            continue

        artifact = _load_json(artifact_path)
        signal_series = artifact.get("signal_series") or []
        close_sm = _find_close_share_multiple(entry, artifact)
        close_max_dd = _find_metric(entry, artifact, "max_drawdown_pct")
        stress = {
            str(int(bps) if float(bps).is_integer() else bps): _replay_next_open(
                signal_series,
                prices,
                price_index,
                slippage_bps=bps,
            )
            for bps in slippage_bps
        }
        base = stress[str(int(slippage_bps[0]) if float(slippage_bps[0]).is_integer() else slippage_bps[0])]
        stress_15 = stress.get("15")
        next_sm = base["share_multiple"]
        degradation_pct = (
            (next_sm / close_sm - 1.0) * 100.0
            if close_sm is not None and close_sm > 0
            else math.nan
        )
        gate_pass = bool(
            close_sm is not None
            and next_sm > 1.0
            and degradation_pct >= -15.0
            and (stress_15 is None or stress_15["share_multiple"] > 1.0)
        )

        rows.append(
            {
                "rank": rank,
                "strategy": strategy,
                "display_name": entry.get("display_name"),
                "artifact": str(artifact_path.relative_to(PROJECT_ROOT)),
                "status": "checked",
                "close_fill_share_multiple": close_sm,
                "close_fill_max_drawdown_pct": close_max_dd,
                "next_open_share_multiple": next_sm,
                "next_open_max_drawdown_pct": base["max_drawdown_pct"],
                "next_open_degradation_pct": round(degradation_pct, 4),
                "next_open_num_trades": base["num_trades"],
                "stress": {
                    key: {
                        "share_multiple": value["share_multiple"],
                        "max_drawdown_pct": value["max_drawdown_pct"],
                        "num_trades": value["num_trades"],
                    }
                    for key, value in stress.items()
                },
                "gate_pass": gate_pass,
            }
        )

    checked = [row for row in rows if row.get("status") == "checked"]
    gate_failures = [row for row in rows if not row.get("gate_pass")]
    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "scripts/validation/reality_check.py",
        "leaderboard": str(LEADERBOARD_PATH.relative_to(PROJECT_ROOT)),
        "price_data": str(TECL_PATH.relative_to(PROJECT_ROOT)),
        "top": top,
        "gate": {
            "next_open_share_multiple_min": 1.0,
            "max_degradation_pct": -15.0,
            "stress_15bps_share_multiple_min": 1.0,
        },
        "summary": {
            "checked": len(checked),
            "gate_pass": sum(1 for row in rows if row.get("gate_pass")),
            "gate_fail": len(gate_failures),
            "missing_artifacts": sum(1 for row in rows if row.get("status") == "missing_artifact"),
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay leaderboard signal artifacts at next-open fills."
    )
    parser.add_argument("--top", type=int, default=5, help="Leaderboard rows to check.")
    parser.add_argument(
        "--slippage-bps",
        default="5,10,15,20",
        help="Comma-separated per-fill slippage stress values in basis points.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Report path.")
    parser.add_argument(
        "--fail-on-gate",
        action="store_true",
        help="Exit non-zero when any checked row fails the confidence gate.",
    )
    args = parser.parse_args()

    slippage_bps = [float(item.strip()) for item in args.slippage_bps.split(",") if item.strip()]
    if not slippage_bps:
        raise ValueError("--slippage-bps must include at least one value")

    report = build_report(args.top, slippage_bps=slippage_bps)
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    summary = report["summary"]
    print(
        "[reality] checked={checked} pass={gate_pass} fail={gate_fail} "
        "missing={missing_artifacts} output={output}".format(
            output=os.path.relpath(output, PROJECT_ROOT),
            **summary,
        )
    )
    for row in report["rows"]:
        if row.get("status") != "checked":
            print(f"[reality] #{row['rank']} {row['strategy']}: {row['status']}")
            continue
        print(
            "[reality] #{rank} {strategy}: close={close:.4f} next_open={next:.4f} "
            "degradation={degradation:+.2f}% gate={gate}".format(
                rank=row["rank"],
                strategy=row["strategy"],
                close=row["close_fill_share_multiple"],
                next=row["next_open_share_multiple"],
                degradation=row["next_open_degradation_pct"],
                gate="PASS" if row["gate_pass"] else "FAIL",
            )
        )

    if args.fail_on_gate and summary["gate_fail"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
