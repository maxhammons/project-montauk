from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.daily import comparable_signal, compute_current_signal, load_active_champion
from ops.events import append_event, utc_now_iso
from ops.paths import LEADERBOARD_PATH, LIVE_HOLDOUT_PATH, RUNS_DIR, SIGNALS_DIR, ensure_ops_dirs
from ops.versioning import version_info

# --- Live demotion thresholds (2026-06-09 live-demotion rule) -----------------
# Forward evidence outranks backtest claims: once enough live snapshots exist,
# a champion that is losing to buy-and-hold in real time gets demoted rather
# than defended. Thresholds are documented in docs/validation-thresholds.md
# ("Live demotion rule (2026-06-09)").
#
# ~1 trading month of live snapshots before performance-based demotion can
# fire — with fewer, the live multiple is mostly noise.
DEMOTION_MIN_SNAPSHOTS = 21
# Live trust proxy floor — same 0.85x floor governance already uses for
# manual review; at demotion it becomes a blocker instead of an advisory.
DEMOTION_LIVE_VS_BAH_FLOOR = 0.85
# NOTE (2026-06-17): the former backtest-vs-live degradation trigger
# (DEMOTION_DEGRADATION_FLOOR = -0.15) was removed. It compared the live trust
# proxy — a ~6-week relative-return ratio that is ~1.0 by construction — against
# the certified *full-history* share multiple (decades of cumulative
# accumulation, e.g. 35x). Those are incommensurable quantities: the check fired
# on every leveraged Gold champion at 21 snapshots no matter how well it was
# tracking live (avoiding it would require beating B&H ~30x in six weeks), and
# anchoring on a full-history multiple violates the project's "full-history
# numbers are diagnostic-only" principle. Forward falsification now rests on the
# live_vs_bah floor and replay divergence. The full-history degradation is still
# reported as a pure diagnostic in the live-holdout payload.

# Forward-survival evidence stream consumed by the confidence_vintage harness
# (runs/confidence_v2/) to calibrate Conviction against reality.
LIVE_OUTCOMES_PATH = RUNS_DIR / "confidence_v2" / "live_outcomes.jsonl"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def load_signal_snapshots(signals_dir: Path = SIGNALS_DIR) -> list[dict[str, Any]]:
    if not signals_dir.exists():
        return []
    snapshots = []
    for path in sorted(signals_dir.glob("*.json")):
        payload = _load_json(path)
        payload["_path"] = str(path)
        snapshots.append(payload)
    return snapshots


def compute_replay_by_date(champion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute current replay signal for the latest available date.

    This is deliberately narrow for the first live-holdout slice. It detects
    whether today's point-in-time snapshot still agrees with the current engine
    and champion. Historical full-date replay can be added once the app has more
    live snapshots.
    """

    replay = compute_current_signal(champion)
    return {str(replay["data_end_date"]): replay}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_pct(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 100.0, 4)


def _snapshot_confidence(snapshot: dict[str, Any]) -> float | None:
    return _safe_float((snapshot.get("validation") or {}).get("composite_confidence"))


def execution_proxy(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for current, nxt in zip(snapshots, snapshots[1:]):
        event = None
        if current.get("buy_event") or current.get("entry_signal"):
            event = "entry"
        elif current.get("sell_event") or current.get("exit_signal"):
            event = "exit"
        if event is None:
            continue
        close = _safe_float(current.get("close"))
        next_close = _safe_float(nxt.get("close"))
        proxy_return = None
        if close and next_close:
            proxy_return = next_close / close - 1.0
        rows.append(
            {
                "event": event,
                "signal_date": current.get("data_end_date"),
                "signal_close": close,
                "proxy_execution_date": nxt.get("data_end_date"),
                "proxy_execution_close": next_close,
                "proxy_return_pct": _round_pct(proxy_return),
                "note": "Uses the next immutable signal snapshot close as a next-open execution proxy.",
            }
        )
    return rows


def live_performance(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if len(snapshots) < 2:
        return {
            "live_signal_return_since_start_pct": None,
            "buy_hold_return_since_start_pct": None,
            "live_vs_buy_hold_multiple_proxy": None,
            "backtest_share_multiple": None,
            "backtest_vs_live_degradation_pct": None,
            "confidence_start": _snapshot_confidence(snapshots[0]) if snapshots else None,
            "confidence_latest": _snapshot_confidence(snapshots[-1]) if snapshots else None,
            "confidence_drift": None,
        }

    signal_factor = 1.0
    buy_hold_factor = 1.0
    for previous, current in zip(snapshots, snapshots[1:]):
        previous_close = _safe_float(previous.get("close"))
        current_close = _safe_float(current.get("close"))
        if not previous_close or not current_close:
            continue
        period_factor = current_close / previous_close
        buy_hold_factor *= period_factor
        if previous.get("risk_on", previous.get("risk_state") == "risk_on"):
            signal_factor *= period_factor

    live_multiple = signal_factor / buy_hold_factor if buy_hold_factor else None
    latest = snapshots[-1]
    backtest_share = _safe_float(((latest.get("active_champion") or {}).get("metrics") or {}).get("share_multiple"))
    degradation_pct = None
    if live_multiple is not None and backtest_share and backtest_share > 0:
        degradation_pct = (live_multiple / backtest_share - 1.0) * 100.0

    first_confidence = _snapshot_confidence(snapshots[0])
    latest_confidence = _snapshot_confidence(latest)
    confidence_delta = None
    if first_confidence is not None and latest_confidence is not None:
        confidence_delta = latest_confidence - first_confidence

    return {
        "live_signal_return_since_start_pct": _round_pct(signal_factor - 1.0),
        "buy_hold_return_since_start_pct": _round_pct(buy_hold_factor - 1.0),
        "live_vs_buy_hold_multiple_proxy": round(live_multiple, 4) if live_multiple is not None else None,
        "backtest_share_multiple": backtest_share,
        "backtest_vs_live_degradation_pct": round(degradation_pct, 4) if degradation_pct is not None else None,
        "confidence_start": first_confidence,
        "confidence_latest": latest_confidence,
        "confidence_drift": round(confidence_delta, 4) if confidence_delta is not None else None,
    }


def evaluate_demotion(
    live_holdout: dict[str, Any],
    min_snapshots: int = DEMOTION_MIN_SNAPSHOTS,
) -> dict[str, Any]:
    """Decide whether live evidence demotes the active champion (Phase 3.3).

    WHY: certification is a backtest claim; the live holdout is the only
    evidence stream Montauk has never seen during search. Once that stream
    contradicts the claim, holding the champion is hope, not validation.
    Demotion fires when:
      - replay diverges from the immutable signal record (correctness
        violation — fires at any sample size), OR
      - with >= ``min_snapshots`` live snapshots: the live trust proxy falls
        below ``DEMOTION_LIVE_VS_BAH_FLOOR``.
    (The former backtest-vs-live degradation trigger was removed 2026-06-17 —
    see the module-level note; the full-history degradation remains a diagnostic
    in the payload but is no longer a demotion trigger.)
    With fewer than ``min_snapshots`` snapshots and no divergence, the verdict
    is always demote=False with an "insufficient live evidence" reason —
    performance noise on a handful of bars must not demote anyone.
    """

    live_holdout = live_holdout or {}
    n_snapshots = int(live_holdout.get("snapshot_count") or 0)
    diverged_count = int(live_holdout.get("diverged_count") or 0)
    live_multiple = _safe_float(
        (live_holdout.get("active_champion_performance_since_live_start") or {}).get(
            "live_vs_buy_hold_multiple_proxy"
        )
    )
    degradation_pct = _safe_float(
        (live_holdout.get("backtest_vs_live_degradation") or {}).get("degradation_pct")
    )
    degradation_fraction = degradation_pct / 100.0 if degradation_pct is not None else None

    reasons: list[str] = []
    if diverged_count > 0:
        reasons.append(
            f"replay diverged from immutable signal record on {diverged_count} snapshot(s)"
        )
    if n_snapshots >= min_snapshots:
        if live_multiple is not None and live_multiple < DEMOTION_LIVE_VS_BAH_FLOOR:
            reasons.append(
                f"live_vs_bah_multiple {live_multiple:.4f} < {DEMOTION_LIVE_VS_BAH_FLOOR} "
                f"with {n_snapshots} live snapshots"
            )
    demote = bool(reasons)
    if not demote and n_snapshots < min_snapshots:
        reasons.append(f"insufficient live evidence ({n_snapshots}/{min_snapshots})")
    return {
        "demote": demote,
        "reasons": reasons,
        "evidence": {
            "n_snapshots": n_snapshots,
            "min_snapshots": min_snapshots,
            "diverged_count": diverged_count,
            "live_vs_bah_multiple": live_multiple,
            # Reported for transparency only — no longer a demotion trigger
            # (full-history vs short-window comparison; see module note).
            "degradation_fraction_diagnostic": degradation_fraction,
            "thresholds": {
                "live_vs_bah_floor": DEMOTION_LIVE_VS_BAH_FLOOR,
            },
        },
        "checked_utc": utc_now_iso(),
    }


def stamp_live_demotion(
    leaderboard_path: Path,
    champion_identity: dict[str, Any],
    demotion: dict[str, Any],
) -> bool:
    """Write the demotion block onto the active champion's leaderboard row.

    WHY stamp instead of remove: this phase records the live evidence on the
    row (`live_demotion`) and blocks via governance; sync-time eligibility
    enforcement (excluding demoted rows from the active pick) arrives with the
    Phase-4 recertification pass. Returns True when a row was stamped.
    """

    if not leaderboard_path.exists():
        return False
    leaderboard = _load_json(leaderboard_path)
    if not isinstance(leaderboard, list):
        return False
    identity = champion_identity or {}
    strategy = identity.get("strategy")
    champion_date = identity.get("date")
    for row in leaderboard:
        if not strategy or row.get("strategy") != strategy:
            continue
        if champion_date and row.get("date") and row.get("date") != champion_date:
            continue
        row["live_demotion"] = demotion
        _write_json(leaderboard_path, leaderboard)
        return True
    return False


def clear_live_demotion(
    leaderboard_path: Path,
    champion_identity: dict[str, Any],
) -> bool:
    """Remove a stale ``live_demotion`` stamp once live evidence no longer demotes.

    WHY: ``stamp_live_demotion`` writes the demotion block but nothing removed it
    when the verdict later flips back to ``demote=False`` (e.g. after the
    2026-06-17 removal of the broken degradation trigger). A lingering stamp would
    misrepresent a healthy champion as demoted. Returns True when a stamp was
    cleared.
    """

    if not leaderboard_path.exists():
        return False
    leaderboard = _load_json(leaderboard_path)
    if not isinstance(leaderboard, list):
        return False
    identity = champion_identity or {}
    strategy = identity.get("strategy")
    champion_date = identity.get("date")
    cleared = False
    for row in leaderboard:
        if not strategy or row.get("strategy") != strategy:
            continue
        if champion_date and row.get("date") and row.get("date") != champion_date:
            continue
        if row.pop("live_demotion", None) is not None:
            cleared = True
    if cleared:
        _write_json(leaderboard_path, leaderboard)
    return cleared


def append_live_outcome(
    report: dict[str, Any],
    champion: dict[str, Any],
    latest_snapshot: dict[str, Any],
    *,
    path: Path = LIVE_OUTCOMES_PATH,
) -> bool:
    """Append one forward-survival evidence row per build (Phase 3.5).

    WHY: this is the forward-survival evidence stream the confidence_vintage
    harness consumes to calibrate Conviction against reality. Each line is a
    hindsight-free, date-stamped record of how the champion's live proxy
    performance compared with its certified scores on the day the evidence
    existed. Idempotent per data_end_date: re-running a build on the same data
    day must not double-count evidence. Returns True when a row was appended.
    """

    outcome_date = str(report.get("latest_snapshot_date") or "")
    if not outcome_date:
        return False
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(existing.get("date")) == outcome_date:
                    return False
    snapshot_champion = (latest_snapshot or {}).get("active_champion") or {}
    performance = report.get("active_champion_performance_since_live_start") or {}
    row = {
        "date": outcome_date,
        "strategy": snapshot_champion.get("strategy") or (champion or {}).get("strategy"),
        "params_hash": snapshot_champion.get("params_hash"),
        "montauk_score": (champion or {}).get("montauk_score"),
        "composite_confidence": (report.get("confidence_drift") or {}).get("latest"),
        "live_vs_bah_multiple": performance.get("live_vs_buy_hold_multiple_proxy"),
        "diverged_count": report.get("diverged_count"),
        "n_snapshots": report.get("snapshot_count"),
        "appended_utc": utc_now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=False, default=str))
        f.write("\n")
    return True


def build_live_holdout(
    *,
    signals_dir: Path = SIGNALS_DIR,
    output_path: Path = LIVE_HOLDOUT_PATH,
    leaderboard_path: Path = LEADERBOARD_PATH,
    live_outcomes_path: Path | None = None,
) -> dict[str, Any]:
    ensure_ops_dirs()
    snapshots = load_signal_snapshots(signals_dir)
    champion = load_active_champion()
    replay_by_date = compute_replay_by_date(champion)
    comparisons: list[dict[str, Any]] = []

    for snapshot in snapshots:
        date = str(snapshot.get("data_end_date") or "")
        replay = replay_by_date.get(date)
        if not replay:
            comparisons.append({
                "date": date,
                "status": "not_replayed",
                "snapshot_path": snapshot.get("_path"),
            })
            continue
        snapshot_cmp = comparable_signal(snapshot)
        replay_cmp = comparable_signal(replay)
        # Divergence semantics (2026-06-09 fix): the replay runs the CURRENT
        # champion. If the snapshot was recorded by a different strategy or
        # param set (champion changed since — e.g. a re-certification), a
        # signal mismatch is expected and is NOT a correctness violation.
        # True divergence — the demotion trigger — means the SAME strategy +
        # params no longer reproduces its own immutable record.
        same_identity = (
            snapshot_cmp.get("strategy") == replay_cmp.get("strategy")
            and snapshot_cmp.get("params_hash") == replay_cmp.get("params_hash")
        )
        if not same_identity:
            status = "champion_changed"
        elif snapshot_cmp == replay_cmp:
            status = "match"
        else:
            status = "diverged"
        comparisons.append({
            "date": date,
            "status": status,
            "snapshot_path": snapshot.get("_path"),
            "snapshot": snapshot_cmp,
            "replay": replay_cmp,
            "changed_fields": [
                key for key in sorted(snapshot_cmp) if snapshot_cmp.get(key) != replay_cmp.get(key)
            ],
        })

    matched = sum(1 for item in comparisons if item.get("status") == "match")
    diverged = sum(1 for item in comparisons if item.get("status") == "diverged")
    not_replayed = sum(1 for item in comparisons if item.get("status") == "not_replayed")
    first = snapshots[0] if snapshots else {}
    latest = snapshots[-1] if snapshots else {}
    start_close = float(first.get("close") or 0.0)
    latest_close = float(latest.get("close") or 0.0)
    close_return_pct = None
    if start_close > 0 and latest_close > 0 and len(snapshots) > 1:
        close_return_pct = round((latest_close / start_close - 1.0) * 100.0, 4)
    performance = live_performance(snapshots)

    report = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "status": "attention" if diverged else "ok",
        "snapshot_count": len(snapshots),
        "live_start_date": first.get("data_end_date"),
        "latest_snapshot_date": latest.get("data_end_date"),
        "matched_count": matched,
        "diverged_count": diverged,
        "not_replayed_count": not_replayed,
        "close_return_since_start_pct": close_return_pct,
        "expected_next_open_execution_proxy": execution_proxy(snapshots),
        "active_champion_performance_since_live_start": {
            "start_date": first.get("data_end_date"),
            "latest_date": latest.get("data_end_date"),
            "strategy": (latest.get("active_champion") or {}).get("strategy"),
            "signal_return_pct": performance["live_signal_return_since_start_pct"],
            "buy_hold_return_pct": performance["buy_hold_return_since_start_pct"],
            "live_vs_buy_hold_multiple_proxy": performance["live_vs_buy_hold_multiple_proxy"],
        },
        "backtest_vs_live_degradation": {
            "backtest_share_multiple": performance["backtest_share_multiple"],
            "live_vs_buy_hold_multiple_proxy": performance["live_vs_buy_hold_multiple_proxy"],
            "degradation_pct": performance["backtest_vs_live_degradation_pct"],
        },
        "confidence_drift": {
            "start": performance["confidence_start"],
            "latest": performance["confidence_latest"],
            "delta": performance["confidence_drift"],
        },
    }
    # Demotion is evaluated on the assembled report so the payload always
    # carries the verdict alongside the evidence it was computed from.
    report["demotion"] = evaluate_demotion(report)
    report["comparisons"] = comparisons
    _write_json(output_path, report)
    champion_identity = {"strategy": champion.get("strategy"), "date": champion.get("date")}
    if report["demotion"]["demote"]:
        stamp_live_demotion(leaderboard_path, champion_identity, report["demotion"])
    else:
        clear_live_demotion(leaderboard_path, champion_identity)
    # The calibration feed records production builds only: ad-hoc/test builds
    # against an overridden signals_dir must not contaminate the forward
    # evidence stream unless they opt in with an explicit live_outcomes_path.
    if live_outcomes_path is None and signals_dir == SIGNALS_DIR:
        live_outcomes_path = LIVE_OUTCOMES_PATH
    if live_outcomes_path is not None and snapshots:
        append_live_outcome(report, champion, latest, path=live_outcomes_path)
    if diverged:
        append_event(
            "live_holdout_drift",
            "Live holdout replay diverged from a point-in-time signal snapshot.",
            severity="warning",
            payload={"diverged_count": diverged, "output_path": str(output_path)},
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Montauk live holdout report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_live_holdout()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(
            f"live holdout: {report['status']} "
            f"({report['matched_count']} match, {report['diverged_count']} diverged)"
        )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
