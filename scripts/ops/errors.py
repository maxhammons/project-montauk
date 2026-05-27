from __future__ import annotations

from typing import Any


ERROR_CODES = {
    "ok": "OK",
    "unknown_job": "OPS_UNKNOWN_JOB",
    "job_locked": "OPS_JOB_LOCKED",
    "job_failed": "OPS_JOB_FAILED",
    "missing_artifact": "OPS_MISSING_ARTIFACT",
    "invalid_json": "OPS_INVALID_JSON",
    "launch_agent_missing": "OPS_LAUNCH_AGENT_MISSING",
    "launch_agent_not_loaded": "OPS_LAUNCH_AGENT_NOT_LOADED",
    "app_bundle_missing": "APP_BUNDLE_MISSING",
    "app_bundle_unsigned": "APP_BUNDLE_UNSIGNED",
    "network_unavailable": "DATA_NETWORK_UNAVAILABLE",
    "data_stale": "DATA_STALE",
    "market_closed": "MARKET_CLOSED",
}


def error_payload(code: str, message: str, *, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "detail": detail or {},
    }


def classify_process_failure(returncode: int | None, stderr: str = "", stdout: str = "") -> str:
    text = f"{stderr}\n{stdout}".lower()
    if "network" in text or "timed out" in text or "connection" in text or "name resolution" in text:
        return ERROR_CODES["network_unavailable"]
    if returncode is None:
        return ERROR_CODES["job_failed"]
    return ERROR_CODES["job_failed"]
