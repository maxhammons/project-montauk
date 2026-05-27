from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.errors import ERROR_CODES, classify_process_failure
from ops.events import utc_now_iso
from ops.paths import PROJECT_ROOT
from ops.run_job import job_command
from ops.scheduler import load_config, list_jobs


def fresh_env() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", ""),
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "MONTAUK_PROJECT_ROOT": str(PROJECT_ROOT),
        "PYTHONPATH": str(PROJECT_ROOT / "scripts"),
    }


def command_probe(job_key: str, job_name: str, *, execute: bool = False) -> dict[str, Any]:
    try:
        command = job_command(job_name)
    except KeyError as exc:
        return {
            "job_key": job_key,
            "job": job_name,
            "ok": False,
            "error_code": ERROR_CODES["unknown_job"],
            "error": str(exc),
        }
    executable = Path(command[0])
    scripts_exist = all(Path(arg).exists() for arg in command[1:] if arg.endswith(".py") or "/" in arg)
    result: dict[str, Any] = {
        "job_key": job_key,
        "job": job_name,
        "command": command,
        "executable_exists": executable.exists(),
        "scripts_exist": scripts_exist,
        "ok": executable.exists() and scripts_exist,
        "error_code": None if executable.exists() and scripts_exist else ERROR_CODES["missing_artifact"],
    }
    if execute and result["ok"]:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=fresh_env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        result.update(
            {
                "returncode": completed.returncode,
                "stdout_tail": (completed.stdout or "")[-2000:],
                "stderr_tail": (completed.stderr or "")[-2000:],
                "ok": completed.returncode == 0,
                "error_code": None
                if completed.returncode == 0
                else classify_process_failure(completed.returncode, completed.stderr or "", completed.stdout or ""),
            }
        )
    return result


def build_fresh_shell_report(*, execute: bool = False, enabled_only: bool = True) -> dict[str, Any]:
    jobs = [
        item
        for item in list_jobs(load_config())
        if not enabled_only or item.get("enabled")
    ]
    checks = [command_probe(str(item.get("key")), str(item.get("job")), execute=execute) for item in jobs]
    failures = [check for check in checks if not check.get("ok")]
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "execute": execute,
        "enabled_only": enabled_only,
        "status": "ok" if not failures else "needs_attention",
        "check_count": len(checks),
        "failure_count": len(failures),
        "checks": checks,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify scheduled jobs resolve from a fresh shell environment.")
    parser.add_argument("--execute", action="store_true", help="Execute each probe command from a minimal environment.")
    parser.add_argument("--all", action="store_true", help="Include disabled scheduled jobs.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_fresh_shell_report(execute=args.execute, enabled_only=not args.all)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"fresh shell: {report['status']} ({report['failure_count']} failures)")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
