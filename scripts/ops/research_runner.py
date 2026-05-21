from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event, utc_now_iso
from ops.paths import EVENTS_PATH, PROJECT_ROOT, RESEARCH_QUEUE_PATH, RESEARCH_RUNS_DIR, ensure_ops_dirs
from ops.run_job import default_python

TEST_COMMANDS = {
    "family_confidence_leaderboard": ["scripts/diagnostics/family_confidence_leaderboard.py"],
    "gold_hybrid_lab": ["scripts/diagnostics/gold_hybrid_lab.py"],
    "overlay_champion_matrix": ["scripts/diagnostics/overlay_champion_matrix.py"],
    "near_miss_autopsy": ["scripts/diagnostics/near_miss_autopsy.py"],
    "diversity_prefilter_search": ["scripts/diagnostics/diversity_prefilter_search.py"],
    "recertify_leaderboard": ["scripts/certify/recertify_leaderboard.py"],
    "live_holdout_review": ["scripts/ops/live_holdout.py"],
    "cross_asset_recheck": ["scripts/diagnostics/gold_diversity_report.py"],
    "focused_grid_search": ["scripts/search/grid_search.py", "--quick"],
    "grid_search_simple_families": ["scripts/search/grid_search.py", "--quick"],
    "named_window_recheck": ["scripts/diagnostics/cycle_diagnostics.py"],
}


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


def approved_ideas(queue: dict[str, Any], idea_id: str | None = None) -> list[dict[str, Any]]:
    ideas = []
    for item in queue.get("ideas") or []:
        if idea_id and item.get("id") != idea_id:
            continue
        if item.get("status") == "approved":
            ideas.append(item)
    return ideas


def build_research_plan(idea: dict[str, Any], *, python: str | None = None) -> dict[str, Any]:
    py = python or default_python()
    steps = []
    for test_name in idea.get("suggested_tests") or []:
        relative = TEST_COMMANDS.get(test_name)
        if not relative:
            steps.append(
                {
                    "name": test_name,
                    "status": "manual_review",
                    "reason": "No bounded command is registered for this test yet.",
                }
            )
            continue
        steps.append(
            {
                "name": test_name,
                "status": "planned",
                "command": [py, str(PROJECT_ROOT / relative[0]), *relative[1:]],
            }
        )
    return {
        "schema_version": 1,
        "idea_id": idea.get("id"),
        "kind": idea.get("kind"),
        "rationale": idea.get("rationale"),
        "validation_tier": idea.get("validation_tier"),
        "time_budget": idea.get("time_budget"),
        "expected_failure_mode": idea.get("expected_failure_mode"),
        "steps": steps,
    }


def run_step(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    started = utc_now_iso()
    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        return {
            "status": "ok" if result.returncode == 0 else "failed",
            "started_utc": started,
            "finished_utc": utc_now_iso(),
            "returncode": result.returncode,
            "stdout_tail": (result.stdout or "")[-4000:],
            "stderr_tail": (result.stderr or "")[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "started_utc": started,
            "finished_utc": utc_now_iso(),
            "returncode": None,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def create_research_run(
    idea: dict[str, Any],
    *,
    execute: bool = False,
    timeout_seconds: int = 15 * 60,
    runs_dir: Path = RESEARCH_RUNS_DIR,
    events_path: Path = EVENTS_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    generated = utc_now_iso()
    run_id = f"{generated.replace(':', '').replace('-', '')}-{idea['id']}"
    record_path = runs_dir / f"{run_id}.json"
    record = {
        "schema_version": 1,
        "run_id": run_id,
        "created_utc": generated,
        "status": "planned",
        "execute": execute,
        "plan": build_research_plan(idea),
    }
    if execute:
        results = []
        for step in record["plan"]["steps"]:
            if step.get("status") != "planned":
                results.append(step)
                continue
            result = run_step(step["command"], timeout_seconds=timeout_seconds)
            results.append({**step, **result})
        record["plan"]["steps"] = results
        statuses = {step.get("status") for step in results}
        record["status"] = "failed" if statuses & {"failed", "timeout"} else "ok"
        record["finished_utc"] = utc_now_iso()
    _write_json(record_path, record)
    record["record_path"] = str(record_path)
    append_event(
        "research_run_created",
        f"Research run created for idea '{idea['id']}'.",
        severity="info",
        payload={"idea_id": idea["id"], "run_id": run_id, "record_path": str(record_path), "execute": execute},
        events_path=events_path,
    )
    return record


def create_runs_for_approved(
    *,
    idea_id: str | None = None,
    execute: bool = False,
    timeout_seconds: int = 15 * 60,
    queue_path: Path = RESEARCH_QUEUE_PATH,
) -> dict[str, Any]:
    queue = _load_json(queue_path, {"ideas": []})
    ideas = approved_ideas(queue, idea_id)
    records = [
        create_research_run(idea, execute=execute, timeout_seconds=timeout_seconds)
        for idea in ideas
    ]
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "approved_count": len(ideas),
        "run_count": len(records),
        "runs": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create bounded research runs from approved ideas.")
    parser.add_argument("--idea-id", help="Only create a run for one approved idea.")
    parser.add_argument("--execute", action="store_true", help="Execute registered bounded commands immediately.")
    parser.add_argument("--timeout-seconds", type=int, default=15 * 60)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    payload = create_runs_for_approved(
        idea_id=args.idea_id,
        execute=args.execute,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"research runs created: {payload['run_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
