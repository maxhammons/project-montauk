from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import PROJECT_ROOT
from ops.versioning import version_info

LOCAL_BUNDLE = PROJECT_ROOT / "app/src-tauri/target/release/bundle/macos/Montauk.app"
DEFAULT_TARGET = Path("/Applications/Montauk.app")


def codesign_status(candidate: Path) -> dict[str, Any]:
    if not candidate.exists():
        return {"ok": False, "reason": "candidate bundle does not exist"}
    result = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(candidate)],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stderr": result.stderr.strip(),
    }


def build_update_plan(
    *,
    candidate: Path = LOCAL_BUNDLE,
    target: Path = DEFAULT_TARGET,
    allow_unsigned: bool = False,
) -> dict[str, Any]:
    signature = codesign_status(candidate)
    can_install = candidate.exists() and (allow_unsigned or signature["ok"])
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "candidate_bundle": str(candidate),
        "target_bundle": str(target),
        "candidate_exists": candidate.exists(),
        "target_exists": target.exists(),
        "signature": signature,
        "allow_unsigned": allow_unsigned,
        "can_install": can_install,
        "preserved_paths": [
            "runs/",
            "signals/",
            "data/",
            "spike/",
            "spirit-memory/",
            "~/Library/LaunchAgents/com.project-montauk.*.plist",
        ],
    }


def install_bundle(candidate: Path, target: Path, *, allow_unsigned: bool = False) -> dict[str, Any]:
    plan = build_update_plan(candidate=candidate, target=target, allow_unsigned=allow_unsigned)
    if not plan["can_install"]:
        raise RuntimeError("candidate bundle is missing or unsigned")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(candidate, target, symlinks=True)
    plan["installed"] = True
    plan["installed_utc"] = utc_now_iso()
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or install a signed Montauk app-shell update.")
    parser.add_argument("--candidate", type=Path, default=LOCAL_BUNDLE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--allow-unsigned", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    payload = (
        install_bundle(args.candidate, args.target, allow_unsigned=args.allow_unsigned)
        if args.install
        else build_update_plan(
            candidate=args.candidate,
            target=args.target,
            allow_unsigned=args.allow_unsigned,
        )
    )
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"update candidate: {'ready' if payload['can_install'] else 'not ready'}")
    return 0 if payload["can_install"] or not args.install else 1


if __name__ == "__main__":
    raise SystemExit(main())
