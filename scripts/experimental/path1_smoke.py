#!/usr/bin/env python3
"""Path-#1 smoke test — "empty box" hypotheses.

Target (from the exhaustive investigation): beat B&H in the REAL and MODERN
eras with exit timing UNCORRELATED to gc_vjatr, using only point-in-time signals
(no era/calendar knowledge). Design: mostly-long trend base (high modern-bull
exposure) + a light de-risk trigger ORTHOGONAL to VJ's ATR-of-price shock + fast
re-entry.

This is a throwaway smoke test (60-second test from docs/design-guide.md). It
registers nothing. Survivors get promoted into the library afterward.
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
import json


def trend_rvol_airbag(ind, p):
    """EMA-trend base + realized-RETURN-volatility shock exit (not ATR-of-range)."""
    n = ind.n; cl = ind.close
    fast = int(p.get("fast_ema", 50)); slow = int(p.get("slow_ema", 100))
    vol_short = int(p.get("vol_short", 20)); vol_long = int(p.get("vol_long", 100))
    vol_expand = float(p.get("vol_expand", 1.8)); confirm = int(p.get("confirm", 3))
    ef = ind.ema(fast); es = ind.ema(slow)
    rv_s = ind.realized_vol(vol_short); rv_l = ind.realized_vol(vol_long)
    entries = np.zeros(n, bool); exits = np.zeros(n, bool); labels = np.array([""] * n, object)
    for i in range(max(slow, vol_long, confirm) + 1, n):
        if np.isnan(ef[i]) or np.isnan(es[i]):
            continue
        if ef[i] > es[i] and cl[i] > es[i]:
            entries[i] = True
        if (not np.isnan(rv_s[i]) and not np.isnan(rv_l[i]) and rv_l[i] > 0
                and rv_s[i] / rv_l[i] > vol_expand and cl[i] < cl[i - confirm]):
            exits[i] = True; labels[i] = "RV"
    return entries, exits, labels


def vix_panic_participation(ind, p):
    """Trend base; step aside ONLY in rare top-percentile VIX panics (implied vol)."""
    n = ind.n; cl = ind.close
    fast = int(p.get("fast_ema", 50)); slow = int(p.get("slow_ema", 100))
    vix_len = int(p.get("vix_len", 252)); vix_pct = float(p.get("vix_pct", 90.0))
    confirm = int(p.get("confirm", 2))
    ef = ind.ema(fast); es = ind.ema(slow)
    vp = ind.vix_percentile(vix_len)
    entries = np.zeros(n, bool); exits = np.zeros(n, bool); labels = np.array([""] * n, object)
    for i in range(max(slow, vix_len, confirm) + 1, n):
        if np.isnan(ef[i]) or np.isnan(es[i]):
            continue
        if ef[i] > es[i] and cl[i] > es[i]:
            entries[i] = True
        if not np.isnan(vp[i]) and vp[i] >= vix_pct and cl[i] < cl[i - confirm]:
            exits[i] = True; labels[i] = "V"
    return entries, exits, labels


def underlying_anchor_regime(ind, p):
    """Trade TECL off the UN-LEVERAGED underlying (XLK) trend, not TECL's own price."""
    n = ind.n; cl = ind.close
    anchor_len = int(p.get("anchor_len", 100)); slope_w = int(p.get("slope_window", 10))
    xe = ind.xlk_ema(anchor_len); xc = ind.xlk_close
    use_xlk = xe is not None and xc is not None
    base = xc if use_xlk else cl
    base_ema = xe if use_xlk else ind.ema(anchor_len)
    sl = ind.slope("anchor", base_ema, slope_w)
    entries = np.zeros(n, bool); exits = np.zeros(n, bool); labels = np.array([""] * n, object)
    for i in range(anchor_len + slope_w + 1, n):
        if np.isnan(base_ema[i]) or np.isnan(base[i]) or np.isnan(sl[i]):
            continue
        if base[i] > base_ema[i] and sl[i] > 0:
            entries[i] = True
        if base[i] < base_ema[i]:
            exits[i] = True; labels[i] = "U"
    return entries, exits, labels


def drawdown_velocity_trend(ind, p):
    """EMA base + fast-drawdown (crash-velocity) exit + RSI-reclaim re-entry."""
    n = ind.n; cl = ind.close
    fast = int(p.get("fast_ema", 50)); slow = int(p.get("slow_ema", 100))
    look = int(p.get("dd_lookback", 20)); dd_pct = float(p.get("dd_pct", 12.0))
    rsi_len = int(p.get("rsi_len", 14)); rsi_reclaim = float(p.get("rsi_reclaim", 45.0))
    ef = ind.ema(fast); es = ind.ema(slow)
    hi = ind.highest(look); rsi = ind.rsi(rsi_len)
    entries = np.zeros(n, bool); exits = np.zeros(n, bool); labels = np.array([""] * n, object)
    for i in range(max(slow, look, rsi_len) + 1, n):
        if np.isnan(ef[i]) or np.isnan(es[i]):
            continue
        if ef[i] > es[i] and not np.isnan(rsi[i]) and rsi[i] > rsi_reclaim:
            entries[i] = True
        if not np.isnan(hi[i]) and hi[i] > 0 and (hi[i] - cl[i]) / hi[i] * 100.0 > dd_pct:
            exits[i] = True; labels[i] = "DV"
    return entries, exits, labels


def dual_confirm_stay_long(ind, p):
    """Max-exposure base: exit ONLY when BOTH trend breaks AND realized vol spikes."""
    n = ind.n; cl = ind.close
    slow = int(p.get("slow_ema", 120))
    vol_short = int(p.get("vol_short", 20)); vol_long = int(p.get("vol_long", 100))
    vol_z = float(p.get("vol_expand", 1.5))
    es = ind.ema(slow)
    rv_s = ind.realized_vol(vol_short); rv_l = ind.realized_vol(vol_long)
    entries = np.zeros(n, bool); exits = np.zeros(n, bool); labels = np.array([""] * n, object)
    for i in range(max(slow, vol_long) + 1, n):
        if np.isnan(es[i]):
            continue
        if cl[i] > es[i]:
            entries[i] = True
        trend_break = cl[i] < es[i]
        vol_spike = (not np.isnan(rv_s[i]) and not np.isnan(rv_l[i]) and rv_l[i] > 0
                     and rv_s[i] / rv_l[i] > vol_z)
        if trend_break and vol_spike:
            exits[i] = True; labels[i] = "DC"
    return entries, exits, labels


CANDIDATES = {
    "trend_rvol_airbag": (trend_rvol_airbag, {}),
    "vix_panic_participation": (vix_panic_participation, {}),
    "underlying_anchor_regime": (underlying_anchor_regime, {}),
    "drawdown_velocity_trend": (drawdown_velocity_trend, {}),
    "dual_confirm_stay_long": (dual_confirm_stay_long, {}),
}


def _state(n, trades):
    st = np.zeros(n, bool)
    for t in trades:
        a = getattr(t, "entry_idx", None); b = getattr(t, "exit_idx", None)
        if a is None:
            continue
        st[a: (b if b is not None else n)] = True
    return st


def main():
    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    # VJ-ATR champion state for correlation
    lb = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "spike", "leaderboard.json")))
    vj = [e for e in lb if e["strategy"] == "gc_vjatr"][0]
    e, x, l = STRATEGY_REGISTRY["gc_vjatr"](ind, vj["params"])
    vj_res = backtest(df, e, x, l, cooldown_bars=vj["params"].get("cooldown", 0), strategy_name="gc_vjatr")
    vj_state = _state(ind.n, vj_res.trades).astype(float)
    print(f"reference VJ-ATR: full={vj_res.share_multiple:.2f} real={vj_res.real_share_multiple:.2f} "
          f"modern={vj_res.modern_share_multiple:.2f} maxDD={vj_res.max_drawdown_pct:.0f} trd={vj_res.num_trades}\n")
    print(f"  {'strategy':26} {'full':>7}{'real':>6}{'modern':>7}{'maxDD':>7}{'trd':>5}{'t/yr':>6}{'VJcorr':>7}  flags")
    for name, (fn, params) in CANDIDATES.items():
        try:
            e, x, l = fn(ind, params)
            r = backtest(df, e, x, l, cooldown_bars=params.get("cooldown", 3), strategy_name=name)
            st = _state(ind.n, r.trades).astype(float)
            corr = float(np.corrcoef(st, vj_state)[0, 1]) if st.std() > 0 else float("nan")
            era_ok = r.real_share_multiple >= 1.0 and r.modern_share_multiple >= 1.0
            diverse = (not np.isnan(corr)) and corr < 0.6
            flags = []
            if era_ok: flags.append("ERA✓")
            if diverse: flags.append("DIVERSE✓")
            if era_ok and diverse: flags.append("*** TARGET ***")
            print(f"  {name:26} {r.share_multiple:>7.2f}{r.real_share_multiple:>6.2f}{r.modern_share_multiple:>7.2f}"
                  f"{r.max_drawdown_pct:>7.0f}{r.num_trades:>5}{r.trades_per_year:>6.2f}{corr:>7.2f}  {' '.join(flags)}")
        except Exception as exc:
            print(f"  {name:26}  ERROR: {exc}")


if __name__ == "__main__":
    main()
