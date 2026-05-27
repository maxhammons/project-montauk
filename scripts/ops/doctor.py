from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.install_launch_agent import status_for_job
from ops.errors import ERROR_CODES
from ops.paths import GOVERNANCE_PATH, LATEST_PATH, LIVE_HOLDOUT_PATH, NOTIFICATIONS_PATH, PROJECT_ROOT
from ops.scheduler import scheduler_status

APP_BUNDLE = PROJECT_ROOT / "app/src-tauri/target/release/bundle/macos/Montauk.app"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check_file(path: Path, label: str) -> dict[str, Any]:
    ok = path.exists()
    return {
        "label": label,
        "path": str(path),
        "ok": ok,
        "error_code": None if ok else ERROR_CODES["missing_artifact"],
    }


def launchctl_state(label: str) -> dict[str, Any]:
    target = f"gui/{os.getuid()}/{label}"
    result = subprocess.run(
        ["launchctl", "print", target],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "loaded": False,
            "state": "missing",
            "runs": None,
            "last_exit_code": None,
            "error": (result.stderr or result.stdout or "")[-1000:],
        }
    output = result.stdout or ""
    state_match = re.search(r"^\s*state = (.+)$", output, re.MULTILINE)
    runs_match = re.search(r"^\s*runs = (.+)$", output, re.MULTILINE)
    exit_match = re.search(r"^\s*last exit code = (.+)$", output, re.MULTILINE)
    return {
        "loaded": True,
        "state": state_match.group(1).strip() if state_match else "unknown",
        "runs": runs_match.group(1).strip() if runs_match else None,
        "last_exit_code": exit_match.group(1).strip() if exit_match else None,
    }


def launch_agent_check(job_key: str) -> dict[str, Any]:
    item = status_for_job(job_key)
    launchd = launchctl_state(item["label"]) if item.get("installed") else {"loaded": False, "state": "not_installed"}
    return {
        "label": f"launch_agent:{item['job_key']}",
        "path": item["path"],
        "ok": bool(item["installed"]) and launchd.get("loaded") is not False,
        "installed": bool(item["installed"]),
        "launchd": launchd,
        "error_code": None
        if bool(item["installed"]) and launchd.get("loaded") is not False
        else (
            ERROR_CODES["launch_agent_missing"]
            if not item.get("installed")
            else ERROR_CODES["launch_agent_not_loaded"]
        ),
    }


def build_doctor_report() -> dict[str, Any]:
    scheduler = scheduler_status()
    enabled_jobs = [job for job in scheduler.get("jobs") or [] if job.get("enabled")]
    launch_agents = [launch_agent_check(job["key"]) for job in enabled_jobs]
    checks = [
        check_file(APP_BUNDLE, "mac_app_bundle"),
        check_file(LATEST_PATH, "latest_operations"),
        check_file(GOVERNANCE_PATH, "governance"),
        check_file(LIVE_HOLDOUT_PATH, "live_holdout"),
        check_file(NOTIFICATIONS_PATH, "notifications"),
    ]
    checks.extend(launch_agents)
    failures = [check for check in checks if not check.get("ok")]
    return {
        "schema_version": 1,
        "status": "ok" if not failures else "needs_attention",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "scheduler": scheduler,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Montauk app and operations readiness.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    report = build_doctor_report()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"doctor: {report['status']} ({report['failure_count']} failures)")
        for check in report["checks"]:
            state = "ok" if check["ok"] else "missing"
            print(f"- {state}: {check['label']} {check['path']}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
