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
from ops.versioning import version_info

TEST_COMMANDS = {
    "family_confidence_leaderboard": ["scripts/diagnostics/family_confidence_leaderboard.py"],
    "gold_hybrid_lab": ["scripts/diagnostics/gold_hybrid_lab.py"],
    "overlay_champion_matrix": [
        "scripts/diagnostics/overlay_champion_matrix.py",
        "--overlay",
        "gc_vjatr_reclaimer",
        "--params-json",
        "{}",
        "--output",
        "runs/overlay_champion_matrix.json",
    ],
    "near_miss_autopsy": ["scripts/diagnostics/near_miss_autopsy.py"],
    "diversity_prefilter_search": ["scripts/diagnostics/diversity_prefilter_search.py"],
    "recertify_leaderboard": ["scripts/certify/recertify_leaderboard.py"],
    "live_holdout_review": ["scripts/ops/live_holdout.py"],
    "cross_asset_recheck": ["scripts/diagnostics/gold_diversity_report.py"],
    "focused_grid_search": ["scripts/search/grid_search.py", "--quick"],
    "grid_search_simple_families": ["scripts/search/grid_search.py", "--quick"],
    "named_window_recheck": ["scripts/diagnostics/cycle_diagnostics.py"],
    "generated_hypothesis_test": ["scripts/ops/generated_hypothesis_test.py", "--idea-id", "{idea_id}", "--json"],
}

NATIVE_STRATEGY_BY_KIND = {
    "move_index_regime": "move_index_regime",
    "credit_spread_velocity": "credit_spread_velocity",
    "overnight_gap_exhaustion": "overnight_gap_exhaustion",
    "consecutive_down_gap_capitulation": "consecutive_down_gap_capitulation",
    "put_call_panic_reversion": "put_call_panic_reversion",
    "defensive_sector_divergence": "defensive_sector_divergence",
}


def _native_artifact_path(idea_id: str, suffix: str) -> str:
    return str(PROJECT_ROOT / "runs" / "research_queue" / "hypotheses" / f"{idea_id}-{suffix}.json")


def _command_for_test(test_name: str, idea: dict[str, Any], py: str) -> list[str] | None:
    idea_id = str(idea.get("id") or "")
    native_concept = NATIVE_STRATEGY_BY_KIND.get(str(idea.get("kind") or ""))
    if test_name == "native_concept_grid" and native_concept:
        return [
            py,
            str(PROJECT_ROOT / "scripts/search/grid_search.py"),
            "--quick",
            "--concepts",
            native_concept,
            "--no-validate",
            "--no-admit",
            "--output",
            _native_artifact_path(idea_id, "grid"),
        ]
    if test_name in {"focused_grid_search", "grid_search_simple_families"} and native_concept:
        return [
            py,
            str(PROJECT_ROOT / "scripts/search/grid_search.py"),
            "--quick",
            "--concepts",
            native_concept,
            "--no-validate",
            "--no-admit",
            "--output",
            _native_artifact_path(idea_id, "grid"),
        ]
    if test_name == "diversity_prefilter_search" and native_concept:
        return [
            py,
            str(PROJECT_ROOT / "scripts/diagnostics/diversity_prefilter_search.py"),
            "--concepts",
            native_concept,
            "--output",
            _native_artifact_path(idea_id, "diversity"),
        ]
    relative = TEST_COMMANDS.get(test_name)
    if not relative:
        return None
    return [
        py,
        str(PROJECT_ROOT / relative[0]),
        *[arg.replace("{idea_id}", idea_id) for arg in relative[1:]],
    ]


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
    idea_id = str(idea.get("id") or "")
    tests = list(idea.get("suggested_tests") or [])
    native_concept = NATIVE_STRATEGY_BY_KIND.get(str(idea.get("kind") or ""))
    if native_concept and not any(
        test_name in tests
        for test_name in ("native_concept_grid", "focused_grid_search", "grid_search_simple_families", "diversity_prefilter_search")
    ):
        tests = ["native_concept_grid", *tests]
    steps = []
    for test_name in tests:
        command = _command_for_test(test_name, idea, py)
        if not command:
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
                "command": command,
                "input_diagnostics": idea.get("input_diagnostics") or [],
                "expected_artifact_paths": idea.get("expected_artifact_paths") or [],
                "stop_conditions": idea.get("stop_conditions") or [],
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
        "input_diagnostics": idea.get("input_diagnostics") or [],
        "expected_artifact_paths": idea.get("expected_artifact_paths") or [],
        "stop_conditions": idea.get("stop_conditions") or [],
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
        "version_info": version_info(),
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
