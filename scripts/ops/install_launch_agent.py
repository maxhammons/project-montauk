from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.paths import PROJECT_ROOT
from ops.run_job import default_python
from ops.scheduler import load_config, list_jobs

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LABEL_PREFIX = "com.project-montauk"


def launch_agent_label(job_key: str) -> str:
    safe = job_key.replace("_", "-")
    return f"{LABEL_PREFIX}.{safe}"


def launch_agent_path(job_key: str, *, launch_agents_dir: Path = LAUNCH_AGENTS_DIR) -> Path:
    return launch_agents_dir / f"{launch_agent_label(job_key)}.plist"


def build_plist(
    job_key: str,
    *,
    python: str | None = None,
    schedule: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loaded_config = config or load_config()
    job_cfg = (loaded_config.get("jobs") or {}).get(job_key)
    if not job_cfg:
        raise KeyError(f"unknown scheduled job key '{job_key}'")
    job_name = job_cfg["job"]
    return {
        "Label": launch_agent_label(job_key),
        "ProgramArguments": [
            python or default_python(),
            str(PROJECT_ROOT / "scripts" / "ops" / "run_job.py"),
            "--job",
            job_name,
        ],
        "WorkingDirectory": str(PROJECT_ROOT),
        "StartCalendarInterval": schedule or job_cfg.get("schedule") or {},
        "StandardOutPath": f"/tmp/project-montauk-{job_key}.out.log",
        "StandardErrorPath": f"/tmp/project-montauk-{job_key}.err.log",
        "RunAtLoad": False,
    }


def write_plist(
    job_key: str,
    *,
    launch_agents_dir: Path = LAUNCH_AGENTS_DIR,
    python: str | None = None,
) -> Path:
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    path = launch_agent_path(job_key, launch_agents_dir=launch_agents_dir)
    payload = build_plist(job_key, python=python)
    with path.open("wb") as f:
        plistlib.dump(payload, f, sort_keys=False)
    return path


def remove_plist(
    job_key: str,
    *,
    launch_agents_dir: Path = LAUNCH_AGENTS_DIR,
) -> bool:
    path = launch_agent_path(job_key, launch_agents_dir=launch_agents_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def job_keys(*, enabled_only: bool = False, config: dict[str, Any] | None = None) -> list[str]:
    loaded_config = config or load_config()
    keys = []
    for item in list_jobs(loaded_config):
        if enabled_only and not item.get("enabled"):
            continue
        keys.append(item["key"])
    return keys


def status_for_job(
    job_key: str,
    *,
    launch_agents_dir: Path = LAUNCH_AGENTS_DIR,
) -> dict[str, Any]:
    path = launch_agent_path(job_key, launch_agents_dir=launch_agents_dir)
    return {
        "job_key": job_key,
        "label": launch_agent_label(job_key),
        "path": str(path),
        "installed": path.exists(),
    }


def launchctl_command(action: str, plist_path: Path) -> list[str]:
    uid = os.getuid()
    if action == "load":
        return ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)]
    if action == "unload":
        return ["launchctl", "bootout", f"gui/{uid}", str(plist_path)]
    raise ValueError(f"unknown launchctl action: {action}")


def run_launchctl(action: str, plist_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        launchctl_command(action, plist_path),
        text=True,
        capture_output=True,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or install a macOS LaunchAgent for Montauk jobs."
    )
    parser.add_argument("--job-key", default="daily", help="Scheduler job key.")
    parser.add_argument("--all-enabled", action="store_true", help="Apply action to every enabled scheduler job.")
    parser.add_argument("--status", action="store_true", help="Print LaunchAgent install status.")
    parser.add_argument("--print", action="store_true", help="Print plist XML to stdout.")
    parser.add_argument("--install", action="store_true", help="Write plist to ~/Library/LaunchAgents.")
    parser.add_argument("--load", action="store_true", help="Install and load the LaunchAgent with launchctl.")
    parser.add_argument("--unload", action="store_true", help="Unload the LaunchAgent with launchctl.")
    parser.add_argument("--uninstall", action="store_true", help="Remove plist from ~/Library/LaunchAgents.")
    parser.add_argument("--json", action="store_true", help="Emit JSON for status or actions.")
    args = parser.parse_args(argv)
    keys = job_keys(enabled_only=True) if args.all_enabled else [args.job_key]

    if args.status:
        payload = {
            "schema_version": 1,
            "jobs": [status_for_job(key) for key in keys],
        }
        if args.json:
            print(json.dumps(payload, indent=2, default=str))
        else:
            for item in payload["jobs"]:
                state = "installed" if item["installed"] else "missing"
                print(f"{item['job_key']}: {state} {item['path']}")
        return 0

    if len(keys) > 1 and args.print:
        print("--print supports one --job-key at a time", file=sys.stderr)
        return 2

    if args.unload and not args.uninstall:
        results = []
        for key in keys:
            path = launch_agent_path(key)
            result = run_launchctl("unload", path)
            if result.returncode != 0:
                print(result.stderr or result.stdout, file=sys.stderr)
                return result.returncode
            results.append({"job_key": key, "path": str(path), "action": "unload"})
        print(json.dumps({"jobs": results}, indent=2) if args.json else "\n".join(item["path"] for item in results))
        return 0

    if args.uninstall:
        results = []
        if args.unload:
            for key in keys:
                path = launch_agent_path(key)
                if not path.exists():
                    continue
                result = run_launchctl("unload", path)
                if result.returncode != 0:
                    print(result.stderr or result.stdout, file=sys.stderr)
                    return result.returncode
        for key in keys:
            removed = remove_plist(key)
            results.append({"job_key": key, "removed": removed, "path": str(launch_agent_path(key))})
        print(json.dumps({"jobs": results}, indent=2) if args.json else "\n".join(
            f"removed={item['removed']} {item['path']}" for item in results
        ))
        return 0

    payload = build_plist(args.job_key)
    if args.print or (not args.install and not args.load):
        sys.stdout.buffer.write(plistlib.dumps(payload, sort_keys=False))
        return 0

    results = []
    for key in keys:
        path = write_plist(key)
        item = {"job_key": key, "path": str(path), "action": "install"}
        if args.load:
            result = run_launchctl("load", path)
            if result.returncode != 0:
                print(result.stderr or result.stdout, file=sys.stderr)
                return result.returncode
            item["action"] = "load"
        results.append(item)
    print(json.dumps({"jobs": results}, indent=2) if args.json else "\n".join(item["path"] for item in results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
