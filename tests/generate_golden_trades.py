"""Generate `tests/golden_trades_821.json` — the Phase 1b regression anchor.

Runs `strategy_engine.run_montauk_821()` with default 8.2.1 StrategyParams on
the current `data/TECL.csv` and writes every trade to a JSON file. The
companion `tests/test_regression.py` re-runs the same backtest on every
`pytest` and asserts exact trade-by-trade agreement.

Re-run this script ONLY when the engine semantics change intentionally (e.g.,
Phase 7 consolidation) and the new trade ledger is the authoritative baseline
going forward. Record *why* the golden was refreshed in the commit message.

Usage:
    python tests/generate_golden_trades.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from engine.strategy_engine import StrategyParams, run_montauk_821  # noqa: E402
from data.loader import get_tecl_data  # noqa: E402


def main() -> None:
    df = get_tecl_data(use_yfinance=False)
    params = StrategyParams()
    result = run_montauk_821(df, params, score_regimes=False)

    trades = [
        {
            "entry_date": t.entry_date,
            "entry_price": round(float(t.entry_price), 6),
            "exit_date": t.exit_date,
            "exit_price": round(float(t.exit_price), 6),
            "exit_reason": t.exit_reason,
            "pnl_pct": round(float(t.pnl_pct), 6),
            "bars_held": int(t.bars_held),
        }
        for t in result.trades
    ]

    payload = {
        "metadata": {
            "generator": "tests/generate_golden_trades.py",
            "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "data_file": "data/TECL.csv",
            "data_rows": int(len(df)),
            "data_first_date": str(df["date"].iloc[0])[:10],
            "data_last_date": str(df["date"].iloc[-1])[:10],
            "slippage_pct": params.slippage_pct,
            "commission_pct": params.commission_pct,
            "num_trades": len(trades),
            "share_multiple": round(float(result.share_multiple), 6),
            "total_return_pct": round(float(result.total_return_pct), 4),
            "cagr_pct": round(float(result.cagr_pct), 4),
            "max_drawdown_pct": round(float(result.max_drawdown_pct), 2),
        },
        "params": params.to_dict(),
        "trades": trades,
    }

    out_path = _ROOT / "tests" / "golden_trades_821.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(trades)} trades to {out_path.relative_to(_ROOT)}")
    print(f"  share_multiple: {result.share_multiple:.4f}")
    print(f"  cagr_pct:       {result.cagr_pct:.2f}")
    print(f"  max_drawdown:   {result.max_drawdown_pct:.1f}%")


if __name__ == "__main__":
    main()
