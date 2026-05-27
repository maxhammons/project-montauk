from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import (
    EVENTS_PATH,
    GOVERNANCE_PATH,
    IDEAS_DIR,
    LATEST_PATH,
    LIVE_HOLDOUT_PATH,
    RESEARCH_QUEUE_PATH,
    RUNS_DIR,
    ensure_ops_dirs,
)
from ops.versioning import version_info

DIAGNOSTICS_BY_TEST = {
    "family_confidence_leaderboard": ["runs/family_confidence_leaderboard.json"],
    "gold_hybrid_lab": ["spike/leaderboard.json", "runs/operations/governance.json"],
    "overlay_champion_matrix": ["spike/leaderboard.json"],
    "near_miss_autopsy": ["runs/near_miss_autopsy.json"],
    "diversity_prefilter_search": ["runs/family_confidence_leaderboard.json"],
    "recertify_leaderboard": ["spike/leaderboard.json", "docs/validation-thresholds.md"],
    "live_holdout_review": ["runs/operations/live_holdout.json", "signals/*.json"],
    "cross_asset_recheck": ["runs/gold_diversity_report.json"],
    "focused_grid_search": ["runs/operations/latest.json", "docs/design-guide.md"],
    "grid_search_simple_families": ["runs/family_confidence_leaderboard.json", "docs/design-guide.md"],
    "named_window_recheck": ["runs/cycle_diagnostics.json", "runs/operations/latest.json"],
    "generated_hypothesis_test": ["runs/research_queue/ideas/<idea_id>.json"],
}

ARTIFACTS_BY_TEST = {
    "family_confidence_leaderboard": ["runs/family_confidence_leaderboard.json"],
    "gold_hybrid_lab": ["runs/gold_hybrid_lab.json"],
    "overlay_champion_matrix": ["runs/overlay_champion_matrix.json"],
    "near_miss_autopsy": ["runs/near_miss_autopsy.json"],
    "diversity_prefilter_search": ["runs/diversity_prefilter_search.json"],
    "recertify_leaderboard": ["spike/leaderboard.json"],
    "live_holdout_review": ["runs/operations/live_holdout.json"],
    "cross_asset_recheck": ["runs/gold_diversity_report.json"],
    "focused_grid_search": ["runs/search/*.json"],
    "grid_search_simple_families": ["runs/search/*.json"],
    "named_window_recheck": ["runs/cycle_diagnostics.json"],
    "generated_hypothesis_test": ["runs/research_queue/hypotheses/<idea_id>.json"],
}

STOP_CONDITIONS_BY_TEST = {
    "family_confidence_leaderboard": ["no new family leader improves Future Confidence and Trust"],
    "gold_hybrid_lab": ["hybrid candidate fails Gold all-era economics or Future Confidence"],
    "overlay_champion_matrix": ["overlay worsens drawdown or live-era share multiple"],
    "near_miss_autopsy": ["near-Gold candidate repeats known Gold contract failures"],
    "diversity_prefilter_search": ["candidate family remains crowded or redundant"],
    "recertify_leaderboard": ["candidate fails the authority certification gates"],
    "live_holdout_review": ["drift is not reproducible from point-in-time snapshots"],
    "cross_asset_recheck": ["same-param portability remains below threshold"],
    "focused_grid_search": ["quick grid has no candidate worth full certification"],
    "grid_search_simple_families": ["simple family fails the named-window or parsimony gates"],
    "named_window_recheck": ["targeted window still fails after timing repair"],
    "generated_hypothesis_test": ["hypothesis cannot be mapped to bounded diagnostics"],
}

EXTERNAL_IDEAS_PATH = RESEARCH_QUEUE_PATH.parent / "external_strategy_ideas.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def _idea_id(kind: str, rationale: str) -> str:
    raw = f"{kind}|{rationale}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _merged_metadata(tests: list[str], table: dict[str, list[str]], extra: list[str] | None = None) -> list[str]:
    values: list[str] = []
    for test_name in tests:
        values.extend(table.get(test_name, []))
    if extra:
        values.extend(extra)
    return list(dict.fromkeys(values))


def proposal(
    kind: str,
    rationale: str,
    tests: list[str],
    *,
    tier: str = "T1",
    expected_failure_mode: str | None = None,
    extra_diagnostics: list[str] | None = None,
    expected_artifact_paths: list[str] | None = None,
    stop_conditions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": _idea_id(kind, rationale),
        "created_utc": utc_now_iso(),
        "status": "proposed",
        "kind": kind,
        "rationale": rationale,
        "validation_tier": tier,
        "suggested_tests": tests,
        "time_budget": "bounded local diagnostic first",
        "expected_failure_mode": expected_failure_mode or "fails Gold all-era economics or Future Confidence before promotion",
        "input_diagnostics": _merged_metadata(tests, DIAGNOSTICS_BY_TEST, extra_diagnostics),
        "expected_artifact_paths": _merged_metadata(tests, ARTIFACTS_BY_TEST, expected_artifact_paths),
        "stop_conditions": _merged_metadata(tests, STOP_CONDITIONS_BY_TEST, stop_conditions),
    }


def external_strategy_proposals(path: Path = EXTERNAL_IDEAS_PATH) -> list[dict[str, Any]]:
    raw = _load_json(path, [])
    if not isinstance(raw, list):
        return []
    ideas: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        tests = [str(test) for test in item.get("suggested_tests") or [] if str(test).strip()]
        if not kind or not rationale or not tests:
            continue
        ideas.append(proposal(
            kind,
            rationale,
            tests,
            tier=str(item.get("validation_tier") or "T1"),
            expected_failure_mode=str(item.get("expected_failure_mode") or "") or None,
            stop_conditions=[str(stop) for stop in item.get("stop_conditions") or [] if str(stop).strip()],
        ))
    return ideas


def enrich_idea(item: dict[str, Any]) -> dict[str, Any]:
    tests = list(item.get("suggested_tests") or [])
    enriched = dict(item)
    enriched["input_diagnostics"] = enriched.get("input_diagnostics") or _merged_metadata(tests, DIAGNOSTICS_BY_TEST)
    enriched["expected_artifact_paths"] = enriched.get("expected_artifact_paths") or _merged_metadata(tests, ARTIFACTS_BY_TEST)
    enriched["stop_conditions"] = enriched.get("stop_conditions") or _merged_metadata(tests, STOP_CONDITIONS_BY_TEST)
    return enriched


def generate_proposals(
    latest_operation: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    live_holdout: dict[str, Any] | None = None,
    family_confidence: dict[str, Any] | None = None,
    near_miss: dict[str, Any] | None = None,
    reality_check: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    latest_operation = latest_operation or {}
    signal = latest_operation.get("active_signal") or {}
    warnings = " ".join(signal.get("warnings") or [])
    governance = governance or {}
    live_holdout = live_holdout or {}
    family_confidence = family_confidence or {}
    near_miss = near_miss or {}
    reality_check = reality_check or {}
    ideas: list[dict[str, Any]] = []

    if "2023_rebound" in warnings or "rebound" in warnings.lower():
        ideas.append(proposal(
            "rebound_capture_repair",
            "Current warnings point to weak rebound participation.",
            ["near_miss_autopsy", "focused_grid_search", "generated_hypothesis_test", "named_window_recheck"],
        ))
    if "bootstrap downside" in warnings.lower() or "max_dd" in warnings.lower():
        ideas.append(proposal(
            "drawdown_resilience_probe",
            "Current champion has downside or drawdown trust pressure.",
            ["gold_hybrid_lab", "overlay_champion_matrix", "live_holdout_review"],
        ))
    if "n_params" in warnings:
        ideas.append(proposal(
            "parsimony_challenger",
            "Current champion is complex enough to justify a simpler challenger lane.",
            ["family_confidence_leaderboard", "grid_search_simple_families", "generated_hypothesis_test"],
            tier="T0/T1",
        ))
    if "QQQ" in warnings or "cross" in warnings.lower():
        ideas.append(proposal(
            "portability_repair",
            "Cross-asset portability warning suggests testing more general signal shapes.",
            ["cross_asset_recheck", "diversity_prefilter_search"],
        ))
    if governance.get("state") == "active_blocked":
        ideas.append(proposal(
            "replacement_candidate_search",
            "Governance blocked the active champion, so a replacement review lane is needed.",
            ["recertify_leaderboard", "family_confidence_leaderboard", "gold_hybrid_lab"],
            tier="T2",
        ))
    if "marker" in warnings.lower() or "timing" in warnings.lower():
        ideas.append(proposal(
            "marker_timing_repair",
            "Current diagnostics point to marker timing misses around entry or exit transitions.",
            ["named_window_recheck", "near_miss_autopsy", "focused_grid_search", "generated_hypothesis_test"],
        ))
    if live_holdout.get("status") == "attention" or int(live_holdout.get("diverged_count") or 0) > 0:
        ideas.append(proposal(
            "live_drift_repair",
            "Live holdout drift is present in point-in-time replay diagnostics.",
            ["live_holdout_review", "near_miss_autopsy", "generated_hypothesis_test"],
            extra_diagnostics=["runs/operations/governance.json"],
        ))
    close_return = live_holdout.get("close_return_since_start_pct")
    if isinstance(close_return, (int, float)) and abs(close_return) >= 8:
        ideas.append(proposal(
            "recent_market_movement_stress",
            f"Recent live-window market movement is {close_return:.2f}%, high enough to stress timing assumptions.",
            ["live_holdout_review", "focused_grid_search", "generated_hypothesis_test"],
        ))
    leaders = family_confidence.get("strategy_family_leaders") or []
    concentrated = [
        item for item in leaders
        if isinstance(item, dict) and int(item.get("family_size") or 0) >= 3
    ]
    if concentrated:
        family = concentrated[0].get("family") or "unknown"
        size = concentrated[0].get("family_size")
        ideas.append(proposal(
            "family_concentration_repair",
            f"Family confidence diagnostics show concentration in {family} with {size} sibling rows.",
            ["family_confidence_leaderboard", "diversity_prefilter_search", "grid_search_simple_families"],
            tier="T0/T1",
        ))
    autopsies = near_miss.get("autopsies") or []
    if autopsies:
        ideas.append(proposal(
            "near_gold_autopsy_retest",
            "Near-Gold autopsies exist and should be converted into bounded falsification tests.",
            ["near_miss_autopsy", "focused_grid_search", "generated_hypothesis_test"],
        ))
    reality_summary = reality_check.get("summary") or {}
    gate_fail = int(reality_summary.get("gate_fail") or 0)
    if gate_fail:
        ideas.append(proposal(
            "near_open_reality_repair",
            f"Reality check reports {gate_fail} gate failures in current candidate behavior.",
            ["near_miss_autopsy", "focused_grid_search", "generated_hypothesis_test"],
            extra_diagnostics=["runs/reality_check/latest.json"],
        ))
    if leaders:
        ideas.extend([
            proposal(
                "breadth_thrust_family_probe",
                "Family confidence diagnostics need an independent breadth-thrust style family instead of another EMA or VJATR sibling.",
                ["family_confidence_leaderboard", "diversity_prefilter_search", "focused_grid_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "candidate does not improve independence from Gold anchors",
                    "candidate misses rebound participation after breadth thrusts",
                ],
            ),
            proposal(
                "volatility_decompression_family_probe",
                "Chimera and champion warnings point to rebound softness, so test a family that enters after volatility compression following a shock.",
                ["near_miss_autopsy", "focused_grid_search", "named_window_recheck", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "candidate remains late after high-volatility bear exits",
                    "candidate improves rebound capture by overfitting one named window",
                ],
            ),
            proposal(
                "relative_strength_rotation_family_probe",
                "QQQ portability softness suggests testing relative-strength rotation signals rather than TECL-only trend timing.",
                ["cross_asset_recheck", "diversity_prefilter_search", "focused_grid_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "same-parameter QQQ/TQQQ portability stays below the warning threshold",
                    "relative-strength filter is redundant with existing Gold risk states",
                ],
            ),
            proposal(
                "liquidity_rate_regime_family_probe",
                "Gold memory is concentrated in price/volatility families, so test rate-liquidity regime shapes as an independent source.",
                ["family_confidence_leaderboard", "cross_asset_recheck", "grid_search_simple_families", "generated_hypothesis_test"],
                tier="T0/T1",
                stop_conditions=[
                    "macro proxy does not add independent timing versus price-only anchors",
                    "rate-liquidity signal fails modern-era share accumulation",
                ],
            ),
            proposal(
                "breakout_after_squeeze_family_probe",
                "Weak rebound diagnostics justify a breakout-after-compression family that tries to re-enter faster without staying always-on.",
                ["focused_grid_search", "named_window_recheck", "diversity_prefilter_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "squeeze breakout behaves like an always-on trend clone",
                    "candidate whipsaws in 2021-2022 or fails 2023 rebound",
                ],
            ),
            proposal(
                "drawdown_reclaim_family_probe",
                "Bootstrap downside warnings justify testing drawdown-reclaim entries that wait for repair evidence instead of pure trend recapture.",
                ["near_miss_autopsy", "focused_grid_search", "overlay_champion_matrix", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "reclaim trigger exits too late during bear continuation",
                    "candidate improves drawdown but loses real-era or modern-era economics",
                ],
            ),
            proposal(
                "gap_reversal_family_probe",
                "Recent and historical shock windows justify testing gap-reversal logic that distinguishes panic exhaustion from trend failure.",
                ["near_miss_autopsy", "focused_grid_search", "named_window_recheck", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "gap reversal trigger overfits isolated crash lows",
                    "candidate improves rebound windows but worsens bear avoidance",
                ],
            ),
            proposal(
                "trend_quality_erosion_family_probe",
                "Existing Gold rows rely heavily on direction, so test trend-quality erosion signals that exit when trend strength decays before price crosses.",
                ["family_confidence_leaderboard", "focused_grid_search", "diversity_prefilter_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "trend-quality signal is redundant with EMA/VJATR exits",
                    "candidate exits early in melt-up or rebound windows",
                ],
            ),
            proposal(
                "vix_acceleration_family_probe",
                "Bootstrap downside warnings justify a VIX acceleration/deceleration family that reacts to volatility impulse rather than volatility level.",
                ["cross_asset_recheck", "focused_grid_search", "named_window_recheck", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "VIX acceleration proxy triggers too late in crash windows",
                    "candidate remains TECL-specific and fails portability checks",
                ],
            ),
            proposal(
                "multi_horizon_vote_family_probe",
                "Chimera v1 shows static committee value, so test a simpler single-strategy multi-horizon vote family before relying on member-level committees.",
                ["focused_grid_search", "family_confidence_leaderboard", "generated_hypothesis_test"],
                tier="T0/T1",
                stop_conditions=[
                    "multi-horizon vote collapses into the existing Gold majority state",
                    "vote threshold improves full history but loses modern-era economics",
                ],
            ),
            proposal(
                "cash_relative_strength_family_probe",
                "Rate and cash-proxy data can test whether TECL should stand down when cash strength beats risk-asset recovery.",
                ["cross_asset_recheck", "grid_search_simple_families", "diversity_prefilter_search", "generated_hypothesis_test"],
                tier="T0/T1",
                stop_conditions=[
                    "cash-relative signal is too defensive in 2020 or 2023 rebound",
                    "candidate fails to add independence from Gold anchor states",
                ],
            ),
            proposal(
                "range_expansion_followthrough_family_probe",
                "Weak rebound capture suggests testing range-expansion follow-through entries that require a large up day to persist instead of fade.",
                ["focused_grid_search", "named_window_recheck", "near_miss_autopsy", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "range expansion buys exhaustion instead of durable rebounds",
                    "candidate passes one rebound window but fails all-era economics",
                ],
            ),
            proposal(
                "failed_breakdown_reclaim_family_probe",
                "Bear-to-recovery transitions can be tested with failed-breakdown reclaim logic rather than pure momentum recapture.",
                ["focused_grid_search", "named_window_recheck", "diversity_prefilter_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "failed-breakdown trigger fires repeatedly in chop",
                    "candidate cannot retain bear avoidance while improving rebound capture",
                ],
            ),
            proposal(
                "volatility_targeted_exposure_family_probe",
                "Chimera still has large drawdown, so test binary timing families that only allow risk-on when realized volatility is in a targetable band.",
                ["near_miss_autopsy", "focused_grid_search", "overlay_champion_matrix", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "volatility band is just a disguised calm-market filter",
                    "candidate reduces drawdown but loses share accumulation versus B&H",
                ],
            ),
            proposal(
                "calendar_turnaround_family_probe",
                "If marker misses cluster near recurring recovery windows, test simple calendar-aware turnaround hypotheses as T0/T1 diagnostics only.",
                ["named_window_recheck", "grid_search_simple_families", "generated_hypothesis_test"],
                tier="T0/T1",
                stop_conditions=[
                    "calendar condition is not robust outside one historical episode",
                    "candidate needs too many exceptions to remain a simple hypothesis",
                ],
            ),
            proposal(
                "correlation_regime_switch_family_probe",
                "Gold and Chimera concentration risk justify testing whether TECL behaves differently when tech-risk correlation regimes shift.",
                ["cross_asset_recheck", "diversity_prefilter_search", "focused_grid_search", "generated_hypothesis_test"],
                tier="T1",
                stop_conditions=[
                    "correlation-regime proxy is redundant with QQQ same-parameter behavior",
                    "candidate improves portability but loses TECL share accumulation",
                ],
            ),
        ])
    ideas.extend(external_strategy_proposals())

    unique = {}
    for item in ideas:
        unique[item["id"]] = item
    return list(unique.values())


def write_proposals(
    proposals: list[dict[str, Any]],
    *,
    ideas_dir: Path = IDEAS_DIR,
    queue_path: Path = RESEARCH_QUEUE_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    existing = _load_json(queue_path, {"ideas": []})
    by_id = {item["id"]: item for item in existing.get("ideas") or []}
    for item in proposals:
        path = ideas_dir / f"{item['id']}.json"
        if item["id"] not in by_id:
            _write_json(path, item)
            by_id[item["id"]] = item
        else:
            existing_item = by_id[item["id"]]
            merged = dict(item)
            for field in ("created_utc", "status", "reviewed_utc"):
                if existing_item.get(field) is not None:
                    merged[field] = existing_item[field]
            _write_json(path, merged)
            by_id[item["id"]] = merged
    for idea_id, item in list(by_id.items()):
        enriched = enrich_idea(item)
        if enriched != item:
            _write_json(ideas_dir / f"{idea_id}.json", enriched)
            by_id[idea_id] = enriched
    queue = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "idea_count": len(by_id),
        "ideas": list(by_id.values()),
    }
    _write_json(queue_path, queue)
    return queue


def update_idea_status(
    idea_id: str,
    status: str,
    *,
    queue_path: Path = RESEARCH_QUEUE_PATH,
    ideas_dir: Path = IDEAS_DIR,
    events_path: Path = EVENTS_PATH,
) -> dict[str, Any]:
    if status not in {"approved", "dismissed", "proposed", "paused"}:
        raise ValueError(f"unsupported idea status: {status}")

    ensure_ops_dirs()
    queue = _load_json(queue_path, {"ideas": []})
    updated = False
    ideas = []
    for item in queue.get("ideas") or []:
        if item.get("id") == idea_id:
            item = dict(item)
            item["status"] = status
            item["reviewed_utc"] = utc_now_iso()
            _write_json(ideas_dir / f"{idea_id}.json", item)
            updated = True
        ideas.append(item)
    if not updated:
        raise KeyError(f"unknown research idea: {idea_id}")

    queue = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "idea_count": len(ideas),
        "ideas": ideas,
    }
    _write_json(queue_path, queue)
    append_event(
        "research_idea_reviewed",
        f"Research idea '{idea_id}' marked {status}.",
        severity="info",
        payload={"idea_id": idea_id, "status": status},
        events_path=events_path,
    )
    return queue


def propose_from_artifacts(
    *,
    latest_path: Path = LATEST_PATH,
    governance_path: Path = GOVERNANCE_PATH,
    live_holdout_path: Path = LIVE_HOLDOUT_PATH,
    family_confidence_path: Path = RUNS_DIR / "family_confidence_leaderboard.json",
    near_miss_path: Path = RUNS_DIR / "near_miss_autopsy.json",
    reality_check_path: Path = RUNS_DIR / "reality_check/latest.json",
) -> dict[str, Any]:
    proposals = generate_proposals(
        _load_json(latest_path, {}),
        _load_json(governance_path, {}),
        _load_json(live_holdout_path, {}),
        _load_json(family_confidence_path, {}),
        _load_json(near_miss_path, {}),
        _load_json(reality_check_path, {}),
    )
    queue = write_proposals(proposals)
    if proposals:
        append_event(
            "research_ideas_proposed",
            f"{len(proposals)} research ideas are ready for review.",
            severity="info",
            payload={"idea_ids": [item["id"] for item in proposals]},
        )
    return queue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Montauk research queue.")
    parser.add_argument(
        "cmd",
        nargs="?",
        default="propose",
        choices=["propose", "list", "approve", "dismiss", "pause", "resume", "reset"],
    )
    parser.add_argument("idea_id", nargs="?", help="Research idea id for review commands.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    if args.cmd == "propose":
        queue = propose_from_artifacts()
    elif args.cmd in {"approve", "dismiss", "pause", "resume", "reset"}:
        if not args.idea_id:
            parser.error(f"{args.cmd} requires idea_id")
        status = {
            "approve": "approved",
            "dismiss": "dismissed",
            "pause": "paused",
            "resume": "approved",
            "reset": "proposed",
        }[args.cmd]
        queue = update_idea_status(args.idea_id, status)
    else:
        queue = _load_json(RESEARCH_QUEUE_PATH, {"ideas": []})
    if args.json:
        print(json.dumps(queue, indent=2, default=str))
    else:
        print(f"research ideas: {len(queue.get('ideas') or [])}")
        for item in queue.get("ideas") or []:
            print(f"- {item['id']} {item['kind']} [{item['status']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
