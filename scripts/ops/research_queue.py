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
from ops.paths import EVENTS_PATH, GOVERNANCE_PATH, IDEAS_DIR, LATEST_PATH, RESEARCH_QUEUE_PATH, ensure_ops_dirs


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


def proposal(kind: str, rationale: str, tests: list[str], *, tier: str = "T1") -> dict[str, Any]:
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
        "expected_failure_mode": "fails Gold all-era economics or Future Confidence before promotion",
    }


def generate_proposals(
    latest_operation: dict[str, Any] | None,
    governance: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    latest_operation = latest_operation or {}
    signal = latest_operation.get("active_signal") or {}
    warnings = " ".join(signal.get("warnings") or [])
    governance = governance or {}
    ideas: list[dict[str, Any]] = []

    if "2023_rebound" in warnings or "rebound" in warnings.lower():
        ideas.append(proposal(
            "rebound_capture_repair",
            "Current warnings point to weak rebound participation.",
            ["near_miss_autopsy", "focused_grid_search", "named_window_recheck"],
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
            ["family_confidence_leaderboard", "grid_search_simple_families"],
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
    queue = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
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
    if status not in {"approved", "dismissed", "proposed"}:
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
) -> dict[str, Any]:
    proposals = generate_proposals(
        _load_json(latest_path, {}),
        _load_json(governance_path, {}),
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
    parser.add_argument("cmd", nargs="?", default="propose", choices=["propose", "list", "approve", "dismiss", "reset"])
    parser.add_argument("idea_id", nargs="?", help="Research idea id for review commands.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    if args.cmd == "propose":
        queue = propose_from_artifacts()
    elif args.cmd in {"approve", "dismiss", "reset"}:
        if not args.idea_id:
            parser.error(f"{args.cmd} requires idea_id")
        status = {"approve": "approved", "dismiss": "dismissed", "reset": "proposed"}[args.cmd]
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
