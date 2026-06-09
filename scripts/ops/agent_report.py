"""Agent intervention report.

Single source of truth for "things that need an LLM" — not just errors, but
maintenance, service, data, signal, research, automation, and governance
requests. Reads the on-disk operations artifacts, classifies every open item
into a categorized work order, and writes ``runs/operations/agent_inbox.json``.

An agent can pull the current state directly::

    .venv/bin/python scripts/ops/agent_report.py          # human summary + write file
    .venv/bin/python scripts/ops/agent_report.py --json    # full JSON to stdout
    cat runs/operations/agent_inbox.json                   # read what was last written

The app refreshes this file at the end of every maintenance run, so launching
the app keeps the inbox current without anyone copying an error code by hand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import read_events, utc_now_iso
from ops.paths import (
    GOVERNANCE_PATH,
    LATEST_PATH,
    LIVE_HOLDOUT_PATH,
    OPERATIONS_DIR,
    RESEARCH_QUEUE_PATH,
    STRATEGY_REVIEW_PATH,
    ensure_ops_dirs,
)

INBOX_PATH = OPERATIONS_DIR / "agent_inbox.json"
MAINTENANCE_STATUS_PATH = OPERATIONS_DIR / "maintenance_status.json"

# Severity ranking for sorting / "highest severity" rollup.
SEVERITY_RANK = {"critical": 3, "warning": 2, "advisory": 1, "info": 0}

# Events that already have a first-class surface elsewhere in this report and
# should not be re-listed from the raw event log as separate requests.
_EVENT_TYPES_SURFACED_ELSEWHERE = {
    "maintenance_run",
    "data_refreshed",
    "data_refresh_skipped",
    "research_idea_reviewed",
}


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _request_id(category: str, area: str, title: str) -> str:
    raw = f"{category}|{area}|{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _req(
    *,
    category: str,
    severity: str,
    area: str,
    title: str,
    detail: str,
    suggested_action: str,
    artifacts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": _request_id(category, area, title),
        "category": category,
        "severity": severity,
        "area": area,
        "title": title,
        "detail": detail,
        "suggested_action": suggested_action,
        "artifacts": artifacts or [],
    }


def _research_counts(queue: dict[str, Any]) -> dict[str, int]:
    counts = {"approved": 0, "proposed": 0, "paused": 0, "dismissed": 0, "total": 0}
    for item in (queue or {}).get("ideas") or []:
        key = str(item.get("status") or "proposed").lower()
        counts["total"] += 1
        if key in counts:
            counts[key] += 1
    return counts


def _signal_age_days(data_end_date: str | None) -> int | None:
    if not data_end_date:
        return None
    try:
        end = datetime.strptime(str(data_end_date), "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date.today() - end).days


def build_agent_report() -> dict[str, Any]:
    latest = _load_json(LATEST_PATH, {}) or {}
    maintenance = _load_json(MAINTENANCE_STATUS_PATH, {}) or {}
    governance = _load_json(GOVERNANCE_PATH, {}) or {}
    strategy_review = _load_json(STRATEGY_REVIEW_PATH, {}) or {}
    live = _load_json(LIVE_HOLDOUT_PATH, {}) or {}
    queue = _load_json(RESEARCH_QUEUE_PATH, {}) or {}
    events = read_events(limit=200)
    signal = latest.get("active_signal") or latest.get("computed_signal") or {}

    # Doctor report is built live so it always reflects current launchd/bundle state.
    try:
        from ops.doctor import build_doctor_report

        doctor = build_doctor_report()
    except Exception as exc:  # noqa: BLE001
        doctor = {"status": "unknown", "checks": [], "error": str(exc)}

    research = _research_counts(queue)
    requests: list[dict[str, Any]] = []

    # ── Errors: failed daily steps ──────────────────────────────────────
    for step_name, step in (latest.get("steps") or {}).items():
        if str((step or {}).get("status") or "").lower() in {"fail", "failed", "error"}:
            requests.append(_req(
                category="error",
                severity="critical",
                area=f"daily.{step_name}",
                title=f"Daily step '{step_name}' failed",
                detail=(step or {}).get("error") or (step or {}).get("stderr_tail")
                or f"The {step_name} step failed during the daily run.",
                suggested_action=(
                    f"Run `.venv/bin/python scripts/ops/daily.py --json` and inspect the "
                    f"'{step_name}' step; fix the underlying cause and re-run."
                ),
                artifacts=["runs/operations/latest.json", "scripts/ops/daily.py"],
            ))

    # ── Data quality ────────────────────────────────────────────────────
    quality = (signal.get("data_quality") or {}) or (
        (latest.get("steps") or {}).get("data_quality") or {}
    ).get("summary") or {}
    if int(quality.get("fail", 0) or 0) > 0:
        requests.append(_req(
            category="data",
            severity="critical",
            area="data_quality",
            title=f"{quality.get('fail')} data-quality checks failing",
            detail="One or more market-data integrity checks reported FAIL.",
            suggested_action=(
                "Run `.venv/bin/python scripts/data/quality.py` to see failing checks; "
                "refresh/repair the offending series and rebuild the manifest."
            ),
            artifacts=["scripts/data/quality.py", "data/manifest.json"],
        ))

    # ── Signal freshness ────────────────────────────────────────────────
    age = _signal_age_days(signal.get("data_end_date"))
    if age is not None and age > 5:
        requests.append(_req(
            category="signal",
            severity="warning",
            area="signal_freshness",
            title=f"Signal is {age} days stale",
            detail=f"Latest signal data ends {signal.get('data_end_date')} ({age} calendar days ago).",
            suggested_action=(
                "Run `.venv/bin/python scripts/ops/daily.py --force-refresh --json` to pull "
                "fresh market data and recompute the signal."
            ),
            artifacts=["scripts/ops/daily.py", "runs/operations/last_refresh.json"],
        ))

    # ── Maintenance run (only if the latest run actually failed) ─────────
    if str(maintenance.get("status") or "").lower() == "failed":
        failed_phases = [
            p.get("key") for p in (maintenance.get("phases") or [])
            if str(p.get("status") or "").lower() == "failed"
        ]
        requests.append(_req(
            category="maintenance",
            severity="critical",
            area="maintenance",
            title="Last maintenance run failed",
            detail=maintenance.get("error") or f"Failed phases: {', '.join(failed_phases) or 'unknown'}.",
            suggested_action=(
                "Run `.venv/bin/python scripts/ops/maintenance.py --json` and resolve the "
                "failing phase(s)."
            ),
            artifacts=["runs/operations/maintenance_status.json", "scripts/ops/maintenance.py"],
        ))

    # ── Doctor: critical failures vs advisories ─────────────────────────
    for check in doctor.get("checks") or []:
        if check.get("ok") is False and not check.get("advisory"):
            requests.append(_req(
                category="service_request",
                severity="warning",
                area=f"doctor.{check.get('label', 'check')}",
                title=f"Health check failed: {check.get('label')}",
                detail=check.get("path") or check.get("error") or "Doctor check failed.",
                suggested_action="Run `.venv/bin/python scripts/ops/doctor.py` and restore the missing artifact.",
                artifacts=["scripts/ops/doctor.py"],
            ))
    advisory_count = int(doctor.get("advisory_count", 0) or 0)
    if advisory_count > 0:
        requests.append(_req(
            category="automation",
            severity="advisory",
            area="automation.launch_agents",
            title=f"{advisory_count} background automation agent(s) not installed",
            detail="Opt-in launch agents are not installed; the daily jobs only run when you open the app.",
            suggested_action=(
                "Optional: install via the app's Doctor panel, or "
                "`.venv/bin/python scripts/ops/install_launch_agent.py`. Safe to ignore for manual use."
            ),
            artifacts=["scripts/ops/install_launch_agent.py"],
        ))

    # ── Governance ──────────────────────────────────────────────────────
    gov_state = str(governance.get("state") or "").lower()
    if gov_state and gov_state not in {"active_ok", "active_watch"}:
        requests.append(_req(
            category="governance",
            severity="warning",
            area="governance",
            title=f"Governance state: {gov_state}",
            detail="; ".join(governance.get("reasons") or []) or "Governance is not in a healthy state.",
            suggested_action="Review governance reasons and the active strategy before trading the signal.",
            artifacts=["runs/operations/governance.json"],
        ))

    # ── Strategy review ─────────────────────────────────────────────────
    if str(strategy_review.get("status") or "").lower() == "switch_candidate":
        requests.append(_req(
            category="strategy",
            severity="warning",
            area="strategy_review",
            title="A better certified strategy is available",
            detail=(
                f"Active: {strategy_review.get('active')} · "
                f"best certified: {strategy_review.get('best_certified')}."
            ),
            suggested_action="Review the switch candidate and decide whether to promote it.",
            artifacts=["runs/operations/strategy_review.json", "spike/leaderboard.json"],
        ))

    # ── Live holdout drift ──────────────────────────────────────────────
    if live and str(live.get("status") or "").lower() not in {"ok", ""}:
        requests.append(_req(
            category="strategy",
            severity="warning",
            area="live_holdout",
            title="Live holdout shows drift",
            detail=f"{live.get('diverged_count', '?')} of {live.get('snapshot_count', '?')} snapshots diverged.",
            suggested_action="Inspect the live holdout; investigate whether the strategy is degrading out-of-sample.",
            artifacts=["runs/operations/live_holdout.json"],
        ))

    # ── Research queue ──────────────────────────────────────────────────
    if research["approved"] > 0:
        requests.append(_req(
            category="research",
            severity="info",
            area="research.approved",
            title=f"{research['approved']} approved research idea(s) queued",
            detail="Approved ideas are ready to execute via the research drain.",
            suggested_action="Run the research drain (app Run/Skip controls) or `scripts/ops/research_runner.py`.",
            artifacts=["runs/research_queue/queue.json", "scripts/ops/research_runner.py"],
        ))
    elif research["proposed"] > 0:
        requests.append(_req(
            category="research",
            severity="info",
            area="research.proposed",
            title=f"{research['proposed']} proposed idea(s) need triage",
            detail="Proposed strategy ideas are awaiting approve / pause / dismiss triage.",
            suggested_action="Triage each idea against the design guide and data availability, then approve/pause/dismiss.",
            artifacts=["runs/research_queue/queue.json", "docs/design-guide.md"],
        ))

    # ── Recent actionable events (excluding already-surfaced types) ──────
    for event in events[-30:]:
        sev = str(event.get("severity") or "").lower()
        etype = str(event.get("event_type") or "").lower()
        if sev not in {"warning", "error", "critical"}:
            continue
        if etype in _EVENT_TYPES_SURFACED_ELSEWHERE:
            continue
        requests.append(_req(
            category="error" if sev in {"error", "critical"} else "service_request",
            severity="critical" if sev == "critical" else ("warning" if sev == "warning" else "warning"),
            area=f"event.{etype or 'unknown'}",
            title=event.get("message") or "Operations event needs review",
            detail=json.dumps(event.get("payload") or {}, default=str)[:600],
            suggested_action="Investigate the event payload and resolve the underlying condition.",
            artifacts=["runs/operations/events.jsonl"],
        ))

    # Sort: highest severity first, stable within severity.
    requests.sort(key=lambda r: -SEVERITY_RANK.get(r["severity"], 0))

    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for r in requests:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
    highest = max((r["severity"] for r in requests), key=lambda s: SEVERITY_RANK.get(s, 0), default="info")
    actionable = any(SEVERITY_RANK.get(r["severity"], 0) >= SEVERITY_RANK["warning"] for r in requests)

    ticket = None
    if requests:
        digest = hashlib.sha256(
            "|".join(sorted(r["id"] for r in requests)).encode("utf-8")
        ).hexdigest()[:8].upper()
        ticket = f"MONTAUK-{digest}"

    return {
        "schema_version": 3,
        "purpose": "agent_intervention_request",
        "instructions": (
            "Work order for an LLM agent. These are not only errors — they include "
            "maintenance, service, data, signal, research, automation, and governance "
            "requests. Each item carries a category, severity, suggested_action, and the "
            "relevant artifact paths. Resolve actionable (warning+) items using the "
            "referenced project files as the source of truth; info/advisory items are "
            "optional. The project's Python engine is authoritative for all strategy logic."
        ),
        "generated_utc": utc_now_iso(),
        "generated_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ticket": ticket,
        "summary": {
            "request_count": len(requests),
            "actionable": actionable,
            "highest_severity": highest if requests else "none",
            "by_category": by_category,
            "by_severity": by_severity,
        },
        "context": {
            "signal": {
                "data_end_date": signal.get("data_end_date"),
                "risk_state": signal.get("risk_state"),
                "age_days": age,
                "strategy": (signal.get("active_champion") or {}).get("strategy"),
            },
            "latest_operation_status": latest.get("status"),
            "maintenance_status": maintenance.get("status"),
            "doctor_status": doctor.get("status"),
            "governance_state": governance.get("state"),
            "strategy_review_status": strategy_review.get("status"),
            "live_holdout_status": live.get("status"),
            "research_queue": research,
        },
        "artifacts": {
            "latest_operation": "runs/operations/latest.json",
            "maintenance_status": "runs/operations/maintenance_status.json",
            "governance": "runs/operations/governance.json",
            "strategy_review": "runs/operations/strategy_review.json",
            "live_holdout": "runs/operations/live_holdout.json",
            "research_queue": "runs/research_queue/queue.json",
            "events": "runs/operations/events.jsonl",
            "design_guide": "docs/design-guide.md",
            "app_source": "app/",
        },
        "requests": requests,
    }


def write_agent_report(report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build (if needed) and persist the report to runs/operations/agent_inbox.json."""
    ensure_ops_dirs()
    report = report or build_agent_report()
    with INBOX_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
        f.write("\n")
    return report


def _print_human(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(f"Agent inbox: {summary['request_count']} request(s) "
          f"[{report.get('ticket') or 'no ticket'}] · highest={summary['highest_severity']}")
    if summary["by_category"]:
        cats = ", ".join(f"{k}={v}" for k, v in sorted(summary["by_category"].items()))
        print(f"  by category: {cats}")
    for r in report["requests"]:
        print(f"  [{r['severity']:<8}] {r['category']:<15} {r['title']}")
        print(f"             → {r['suggested_action']}")
    print(f"  written to {INBOX_PATH.relative_to(SCRIPTS_DIR.parent)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Montauk agent intervention report.")
    parser.add_argument("--json", action="store_true", help="Print the full report JSON to stdout.")
    parser.add_argument("--no-write", action="store_true", help="Do not write agent_inbox.json.")
    args = parser.parse_args(argv)

    report = build_agent_report()
    if not args.no_write:
        write_agent_report(report)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
