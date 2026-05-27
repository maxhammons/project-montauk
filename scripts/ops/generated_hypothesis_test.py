from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import IDEAS_DIR, RESEARCH_HYPOTHESES_DIR, RESEARCH_QUEUE_PATH, ensure_ops_dirs


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


def load_idea(idea_id: str, *, ideas_dir: Path = IDEAS_DIR, queue_path: Path = RESEARCH_QUEUE_PATH) -> dict[str, Any]:
    direct = _load_json(ideas_dir / f"{idea_id}.json", {})
    if direct:
        return direct
    queue = _load_json(queue_path, {"ideas": []})
    for item in queue.get("ideas") or []:
        if item.get("id") == idea_id:
            return item
    raise KeyError(f"unknown research idea: {idea_id}")


def build_hypothesis(idea: dict[str, Any]) -> dict[str, Any]:
    kind = idea.get("kind") or "research_idea"
    rationale = idea.get("rationale") or "No rationale was supplied."
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "idea_id": idea.get("id"),
        "kind": kind,
        "status": "planned",
        "hypothesis": (
            f"If {kind.replace('_', ' ')} is valid, the bounded tests should improve the motivating "
            f"diagnostic without weakening Gold Status economics. Rationale: {rationale}"
        ),
        "input_diagnostics": idea.get("input_diagnostics") or [],
        "suggested_tests": idea.get("suggested_tests") or [],
        "expected_artifact_paths": idea.get("expected_artifact_paths") or [],
        "stop_conditions": idea.get("stop_conditions") or [],
        "expected_failure_mode": idea.get("expected_failure_mode"),
    }


def write_hypothesis(
    idea_id: str,
    *,
    ideas_dir: Path = IDEAS_DIR,
    queue_path: Path = RESEARCH_QUEUE_PATH,
    output_dir: Path = RESEARCH_HYPOTHESES_DIR,
) -> dict[str, Any]:
    ensure_ops_dirs()
    idea = load_idea(idea_id, ideas_dir=ideas_dir, queue_path=queue_path)
    payload = build_hypothesis(idea)
    path = output_dir / f"{idea_id}.json"
    _write_json(path, payload)
    payload["artifact_path"] = str(path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a bounded hypothesis artifact for a research idea.")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    payload = write_hypothesis(args.idea_id)
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"hypothesis written: {payload['artifact_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
