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

from ops.errors import ERROR_CODES
from ops.events import utc_now_iso
from ops.paths import GOVERNANCE_PATH, LATEST_PATH, LIVE_HOLDOUT_PATH, NOTIFICATIONS_PATH, PROJECT_ROOT, RESEARCH_QUEUE_PATH

LOCAL_BUNDLE = PROJECT_ROOT / "app/src-tauri/target/release/bundle/macos/Montauk.app"
INSTALLED_BUNDLE = Path("/Applications/Montauk.app")
FRONTEND_DIST = PROJECT_ROOT / "app/dist/index.html"
APP_JS = PROJECT_ROOT / "app/src/main.js"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def file_check(path: Path, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "path": str(path),
        "ok": path.exists(),
        "error_code": None if path.exists() else ERROR_CODES["missing_artifact"],
    }


def json_check(path: Path, label: str, required_keys: list[str] | None = None) -> dict[str, Any]:
    payload = _load_json(path)
    ok = isinstance(payload, dict)
    missing = [key for key in required_keys or [] if not (isinstance(payload, dict) and key in payload)]
    if missing:
        ok = False
    return {
        "label": label,
        "path": str(path),
        "ok": ok,
        "missing_keys": missing,
        "error_code": None if ok else ERROR_CODES["invalid_json"],
    }


def signature_check(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "label": label,
            "path": str(path),
            "ok": False,
            "error_code": ERROR_CODES["app_bundle_missing"],
        }
    result = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "label": label,
        "path": str(path),
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stderr": result.stderr.strip(),
        "error_code": None if result.returncode == 0 else ERROR_CODES["app_bundle_unsigned"],
    }


def build_app_smoke_report() -> dict[str, Any]:
    checks = [
        file_check(APP_JS, "frontend_source"),
        file_check(FRONTEND_DIST, "frontend_dist"),
        file_check(LOCAL_BUNDLE, "local_app_bundle"),
        signature_check(INSTALLED_BUNDLE, "installed_app_bundle_signature"),
        json_check(LATEST_PATH, "latest_operations", ["schema_version", "active_signal", "version_info"]),
        json_check(GOVERNANCE_PATH, "governance", ["schema_version", "state", "version_info"]),
        json_check(LIVE_HOLDOUT_PATH, "live_holdout", ["schema_version", "status", "version_info"]),
        json_check(NOTIFICATIONS_PATH, "notifications", ["schema_version", "pending_count", "version_info"]),
        json_check(RESEARCH_QUEUE_PATH, "research_queue", ["schema_version", "ideas", "version_info"]),
    ]
    failures = [check for check in checks if not check.get("ok")]
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "status": "ok" if not failures else "needs_attention",
        "check_count": len(checks),
        "failure_count": len(failures),
        "checks": checks,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a local Montauk app smoke check.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_app_smoke_report()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"app smoke: {report['status']} ({report['failure_count']} failures)")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
