"""Maintenance orchestrator for the Mac app's one-button Run Maintenance flow.

Runs the maintenance sequence in order and writes per-phase progress to
runs/operations/maintenance_status.json so the app can poll for live updates.

Phases:
  1. daily             — scripts/ops/daily.py (data refresh, signal compute, viz rebuild)
  2. doctor            — scripts/ops/doctor.py (health checks)
  3. research          — scripts/ops/research_runner.py for ONE approved idea
                        (or empty if the queue has none)

Exits 0 on a clean run, 1 on any failure. The status file is the source of
truth; the app polls it rather than parsing stdout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import append_event
from ops.paths import (
    OPERATIONS_DIR,
    PROJECT_ROOT,
    RESEARCH_QUEUE_PATH,
    ensure_ops_dirs,
)
from ops.run_job import default_python

STATUS_PATH = OPERATIONS_DIR / "maintenance_status.json"
RESEARCH_MARKER_PATH = OPERATIONS_DIR / "last_research_drain.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _daily_done_today() -> tuple[bool, dict[str, Any]]:
    """True if daily.py already refreshed data today (local calendar day).

    Reads the once-per-day marker daily.py writes (runs/operations/last_refresh.json)
    so a repeat run the same day can skip the network pull + signal recompute.
    """
    from ops.daily import REFRESH_MARKER_PATH, _local_today

    if not REFRESH_MARKER_PATH.exists():
        return False, {}
    try:
        marker = json.loads(REFRESH_MARKER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, {}
    return marker.get("date") == _local_today(), marker


def _research_done_today() -> tuple[bool, dict[str, Any]]:
    """True if a research idea was already drained today (local calendar day)."""
    from ops.daily import _local_today

    if not RESEARCH_MARKER_PATH.exists():
        return False, {}
    try:
        marker = json.loads(RESEARCH_MARKER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, {}
    return marker.get("date") == _local_today(), marker


def _mark_research_drained(idea: dict[str, Any]) -> None:
    from ops.daily import _local_today

    RESEARCH_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESEARCH_MARKER_PATH.write_text(
        json.dumps(
            {
                "date": _local_today(),
                "drained_utc": utc_now_iso(),
                "idea_id": idea.get("id"),
                "kind": idea.get("kind"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _phase(key: str, label: str, detail: str) -> dict[str, Any]:
    return {"key": key, "label": label, "detail": detail, "status": "pending"}


def _initial_status(phases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "running",
        "started_utc": utc_now_iso(),
        "finished_utc": None,
        "phases": phases,
        "current_phase": phases[0]["key"] if phases else None,
        "summary": None,
        "error": None,
    }


def _write_status(status: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, default=str)
        f.write("\n")
    tmp.replace(STATUS_PATH)


def _update_phase(state: dict[str, Any], key: str, **fields: Any) -> None:
    for phase in state["phases"]:
        if phase["key"] == key:
            phase.update(fields)
            break
    state["current_phase"] = key
    _write_status(state)


def _run_step(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
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
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "started_utc": started,
            "finished_utc": utc_now_iso(),
            "stdout_tail": (result.stdout or "")[-2000:],
            "stderr_tail": (result.stderr or "")[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "started_utc": started,
            "finished_utc": utc_now_iso(),
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
            "error": "timeout",
        }


def _load_queue() -> dict[str, Any]:
    if not RESEARCH_QUEUE_PATH.exists():
        return {"ideas": []}
    with RESEARCH_QUEUE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _first_approved(queue: dict[str, Any]) -> dict[str, Any] | None:
    for item in queue.get("ideas") or []:
        if item.get("status") == "approved":
            return item
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Montauk maintenance sequence.")
    parser.add_argument("--skip-research", action="store_true",
                        help="Skip the research-drain phase (data + viz + doctor only).")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Force the daily data pull even if it already ran today.")
    parser.add_argument("--timeout-seconds", type=int, default=15 * 60,
                        help="Per-phase timeout. Default 900s.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the final status JSON to stdout when done.")
    args = parser.parse_args(argv)

    ensure_ops_dirs()
    py = default_python()

    phases = [
        _phase("daily", "Refresh data & recompute signal",
               "scripts/ops/daily.py — pull TECL/VIX/macro, verify manifest, write a fresh signal snapshot, rebuild the viz bundle."),
        _phase("doctor", "Run health checks",
               "scripts/ops/doctor.py — verify app bundle, ops artifacts, scheduler config, and local launchd state."),
    ]
    if not args.skip_research:
        phases.append(_phase("research", "Drain one approved research idea",
                              "scripts/ops/research_runner.py — execute the next status=approved idea, if any."))

    status = _initial_status(phases)
    _write_status(status)

    overall_ok = True
    research_summary: dict[str, Any] | None = None

    # Phase 1 — daily. Skip entirely if it already completed today (data +
    # signal are once-per-day work), unless --force-refresh is set.
    done_today, marker = _daily_done_today()
    if done_today and not args.force_refresh:
        _update_phase(
            status, "daily",
            status="skipped",
            started_utc=utc_now_iso(),
            finished_utc=utc_now_iso(),
            detail=f"Data & signal already refreshed today ({marker.get('date')}); skipped.",
        )
        daily_result = {"ok": True, "returncode": 0, "stderr_tail": "", "skipped": True}
        append_event(
            "daily_skipped",
            f"Daily already completed today ({marker.get('date')}); skipped the refresh.",
            severity="info",
            payload={"date": marker.get("date"), "data_end_date": marker.get("data_end_date")},
        )
    else:
        _update_phase(status, "daily", status="running", started_utc=utc_now_iso())
        daily_cmd = [py, str(PROJECT_ROOT / "scripts/ops/daily.py"), "--json"]
        if args.force_refresh:
            daily_cmd.append("--force-refresh")
        daily_result = _run_step(
            daily_cmd,
            timeout_seconds=args.timeout_seconds,
        )
        _update_phase(
            status, "daily",
            status="ok" if daily_result["ok"] else "failed",
            finished_utc=daily_result["finished_utc"],
            returncode=daily_result["returncode"],
            stderr_tail=daily_result["stderr_tail"],
        )
        if not daily_result["ok"]:
            overall_ok = False
            status["error"] = daily_result.get("stderr_tail") or daily_result.get("stdout_tail") or "daily.py failed"

    # Phase 2 — doctor (always runs, even if daily failed — useful diagnostic)
    _update_phase(status, "doctor", status="running", started_utc=utc_now_iso())
    doctor_result = _run_step(
        [py, str(PROJECT_ROOT / "scripts/ops/doctor.py"), "--json"],
        timeout_seconds=args.timeout_seconds,
    )
    _update_phase(
        status, "doctor",
        status="ok" if doctor_result["ok"] else "failed",
        finished_utc=doctor_result["finished_utc"],
        returncode=doctor_result["returncode"],
        stderr_tail=doctor_result["stderr_tail"],
    )
    if not doctor_result["ok"] and overall_ok:
        overall_ok = False
        status["error"] = doctor_result.get("stderr_tail") or "doctor.py failed"

    # Phase 3 — research. Drain at most one approved idea per local day, unless
    # --force-refresh (the manual Refresh button) asks for it now.
    if not args.skip_research:
        research_done, rmarker = _research_done_today()
        if research_done and not args.force_refresh:
            _update_phase(
                status, "research",
                status="skipped",
                started_utc=utc_now_iso(),
                finished_utc=utc_now_iso(),
                detail=f"Already drained a research idea today ({rmarker.get('date')}); skipped.",
            )
            research_summary = {"status": "skipped", "reason": "already_drained_today", "date": rmarker.get("date")}
            append_event(
                "research_skipped",
                f"Research already drained today ({rmarker.get('date')}); skipped.",
                severity="info",
                payload={"date": rmarker.get("date"), "idea_id": rmarker.get("idea_id")},
            )
        else:
            _update_phase(status, "research", status="running", started_utc=utc_now_iso())
            idea = _first_approved(_load_queue())
            if idea is None:
                _update_phase(
                    status, "research",
                    status="empty",
                    finished_utc=utc_now_iso(),
                    detail="No approved strategy ideas are queued. Research was skipped; the app is ready to use.",
                )
                research_summary = {"status": "empty", "reason": "no_approved_strategy_ideas"}
            else:
                research_result = _run_step(
                    [
                        py,
                        str(PROJECT_ROOT / "scripts/ops/research_runner.py"),
                        "--idea-id",
                        str(idea["id"]),
                        "--execute",
                        "--timeout-seconds",
                        str(args.timeout_seconds),
                        "--json",
                    ],
                    timeout_seconds=args.timeout_seconds + 60,
                )
                research_summary = {
                    "status": "ran" if research_result["ok"] else "failed",
                    "idea_id": idea.get("id"),
                    "kind": idea.get("kind"),
                }
                _update_phase(
                    status, "research",
                    status="ok" if research_result["ok"] else "failed",
                    finished_utc=research_result["finished_utc"],
                    returncode=research_result["returncode"],
                    stderr_tail=research_result["stderr_tail"],
                    idea_id=idea.get("id"),
                    idea_kind=idea.get("kind"),
                )
                if research_result["ok"]:
                    _mark_research_drained(idea)
                elif overall_ok:
                    overall_ok = False
                    status["error"] = research_result.get("stderr_tail") or "research_runner.py failed"

    status["status"] = "ok" if overall_ok else "failed"
    status["finished_utc"] = utc_now_iso()
    status["summary"] = {
        "daily_ok": daily_result["ok"],
        "doctor_ok": doctor_result["ok"],
        "research": research_summary,
    }
    _write_status(status)

    append_event(
        "maintenance_run",
        f"Maintenance {'ok' if overall_ok else 'failed'}.",
        severity="info" if overall_ok else "warning",
        payload={"summary": status["summary"]},
    )

    # Refresh the agent intervention inbox so an LLM can read the current
    # work order directly from runs/operations/agent_inbox.json.
    try:
        from ops.agent_report import write_agent_report

        write_agent_report()
    except Exception:  # noqa: BLE001 — never let reporting break maintenance
        pass

    if args.json:
        print(json.dumps(status, indent=2, default=str))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
