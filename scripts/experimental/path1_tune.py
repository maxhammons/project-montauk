#!/usr/bin/env python3
"""Grid-tune the two promising path-#1 hypotheses.

Searches param grids for `dual_confirm_stay_long` and `trend_rvol_airbag`,
scoring every config on the real/modern eras (the wall) and flagging any that
beats B&H >= 1.0 in BOTH. Also reports correlation to the gc_vjatr champion so
we know whether a survivor is actually diverse. Research only.
"""
from __future__ import annotations
import itertools, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import candidate_risk_state_from_trades
from search.fitness import weighted_era_fitness
from experimental.path1_smoke import dual_confirm_stay_long, trend_rvol_airbag

GRIDS = {
    "dual_confirm_stay_long": (dual_confirm_stay_long, {
        "slow_ema": [50, 70, 100, 120, 150, 200],
        "vol_short": [10, 20],
        "vol_long": [60, 100],
        "vol_expand": [1.2, 1.4, 1.6, 1.8, 2.0],
    }),
    "trend_rvol_airbag": (trend_rvol_airbag, {
        "fast_ema": [20, 30, 50],
        "slow_ema": [80, 100, 150],
        "vol_short": [10, 20],
        "vol_long": [60, 100],
        "vol_expand": [1.5, 1.8, 2.2],
        "confirm": [2, 3, 5],
    }),
}


def _combos(grid):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def main():
    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    lb = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "spike", "leaderboard.json")))
    vj = [e for e in lb if e["strategy"] == "gc_vjatr"][0]
    e, x, l = STRATEGY_REGISTRY["gc_vjatr"](ind, vj["params"])
    vjr = backtest(df, e, x, l, cooldown_bars=vj["params"].get("cooldown", 0), strategy_name="gc_vjatr")
    vj_state = candidate_risk_state_from_trades(ind.n, vjr.trades).astype(float)
    print(f"VJ-ATR ref: full={vjr.share_multiple:.1f} real={vjr.real_share_multiple:.2f} "
          f"modern={vjr.modern_share_multiple:.2f}\n")

    for name, (fn, grid) in GRIDS.items():
        combos = list(_combos(grid))
        rows = []
        for p in combos:
            try:
                e, x, l = fn(ind, p)
                r = backtest(df, e, x, l, cooldown_bars=p.get("cooldown", 3), strategy_name=name)
            except Exception:
                continue
            if r.num_trades < 5 or r.trades_per_year > 5.0:
                continue
            st = candidate_risk_state_from_trades(ind.n, r.trades).astype(float)
            corr = float(np.corrcoef(st, vj_state)[0, 1]) if st.std() > 0 else 1.0
            wef = weighted_era_fitness(r.share_multiple, r.real_share_multiple, r.modern_share_multiple)
            rows.append({
                "p": p, "full": r.share_multiple, "real": r.real_share_multiple,
                "modern": r.modern_share_multiple, "maxdd": r.max_drawdown_pct,
                "trd": r.num_trades, "tyr": r.trades_per_year, "wef": wef, "corr": corr,
                "era_beat": r.real_share_multiple >= 1.0 and r.modern_share_multiple >= 1.0,
            })
        charter = [r for r in rows if r["wef"] >= 1.0]
        era = [r for r in rows if r["era_beat"]]
        target = [r for r in era if r["corr"] < 0.6]
        print(f"=== {name}: {len(combos)} combos, {len(rows)} with valid trade-count ===")
        print(f"    charter-pass (wef>=1): {len(charter)}   beat-B&H-both-eras: {len(era)}   "
              f"AND diverse(corr<0.6): {len(target)}")
        rows.sort(key=lambda r: (r["era_beat"], r["wef"]), reverse=True)
        print(f"    {'wef':>5}{'full':>8}{'real':>6}{'modern':>7}{'maxDD':>7}{'trd':>4}{'corr':>6}  era?  params")
        for r in rows[:8]:
            flag = "BOTH" if r["era_beat"] else ""
            print(f"    {r['wef']:>5.2f}{r['full']:>8.2f}{r['real']:>6.2f}{r['modern']:>7.2f}"
                  f"{r['maxdd']:>7.0f}{r['trd']:>4}{r['corr']:>6.2f}  {flag:>4}  {r['p']}")
        if target:
            print("    >>> DIVERSE + BEATS B&H BOTH ERAS:")
            for r in sorted(target, key=lambda r: -r["wef"])[:5]:
                print(f"        real={r['real']:.2f} modern={r['modern']:.2f} corr={r['corr']:.2f} {r['p']}")
        print()


if __name__ == "__main__":
    main()
