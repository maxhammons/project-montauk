from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ops.events import utc_now_iso
from ops.paths import PROJECT_ROOT


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def app_version(root: Path = PROJECT_ROOT) -> str | None:
    package = _load_json(root / "app/package.json", {})
    tauri = _load_json(root / "app/src-tauri/tauri.conf.json", {})
    return package.get("version") or tauri.get("version")


def git_commit(root: Path = PROJECT_ROOT) -> str | None:
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:  # noqa: BLE001
        return None
    if output.returncode != 0:
        return None
    return output.stdout.strip() or None


def git_dirty(root: Path = PROJECT_ROOT) -> bool | None:
    try:
        output = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:  # noqa: BLE001
        return None
    if output.returncode != 0:
        return None
    return bool(output.stdout.strip())


def version_info(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    commit = git_commit(root)
    return {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "app_version": app_version(root),
        "git_commit": commit,
        "git_dirty": git_dirty(root),
        "strategy_code_version": commit,
    }
