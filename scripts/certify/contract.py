#!/usr/bin/env python3
"""Canonical certification and leaderboard-admission contract.

This module is the single authority for the relationship between:
  - `promotion_ready`
  - `certified_not_overfit`
  - `backtest_certified`
  - required certification checks
  - leaderboard eligibility

Contract:
  - `certified_not_overfit=True` means the strategy passed the tier-appropriate
    validation verdict (`promotion_ready=True`) and every required anti-overfit
    certification check passed.
  - `backtest_certified=True` is stricter: it additionally requires the
    champion's artifact bundle to exist.
  - `gold_status=True` means the row is certified, artifact-backed, and beats
    B&H in the full, real, and modern eras.
  - Leaderboard eligibility is exactly `gold_status=True`.
  - Artifact generation must never upgrade a WARN / non-promotion-ready row to
    `backtest_certified=True`.
"""

from __future__ import annotations

import copy
import os
from typing import Any

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

REQUIRED_CERTIFICATION_CHECKS = (
    "engine_integrity",
    "golden_regression",
    "shadow_comparator",
    "data_quality_precheck",
)

REQUIRED_RUN_ARTIFACTS = (
    "trade_ledger",
    "signal_series",
    "equity_curve",
    "validation_summary",
    "dashboard_data",
)

ARTIFACT_PENDING_ADVISORY = "artifact completeness pending"
ARTIFACT_FAILED_ADVISORY = "artifact completeness failed"
GOLD_STATUS_LABEL = "Gold Status"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def resolve_artifact_path(path: str) -> str:
    """Rebase an artifact path onto this machine's project root.

    Leaderboard rows persist absolute artifact paths, which go stale whenever
    the repo moves (different machine, renamed home dir). The run directory
    layout under `spike/` is stable, so an unresolvable absolute path is
    re-anchored via its `/spike/` suffix. Returns the original path unchanged
    if it exists or cannot be rebased — the existence check then fails
    honestly instead of trusting a stamp.
    """
    if os.path.exists(path):
        return path
    marker = f"{os.sep}spike{os.sep}"
    if marker in path:
        candidate = os.path.join(PROJECT_ROOT, "spike", path.split(marker, 1)[1])
        if os.path.exists(candidate):
            return candidate
    return path


def verify_artifact_bundle(
    artifact_paths: dict[str, str] | None,
) -> tuple[bool, dict[str, str]]:
    """Verify the five-artifact bundle by content, not by stored stamp.

    Each required artifact must resolve to an existing, non-empty file on
    this machine. Returns (ok, resolved_paths).
    """
    resolved = {
        name: resolve_artifact_path(path)
        for name, path in (artifact_paths or {}).items()
        if name in REQUIRED_RUN_ARTIFACTS
    }
    ok = len(resolved) == len(REQUIRED_RUN_ARTIFACTS) and all(
        os.path.exists(path) and os.path.getsize(path) > 0 for path in resolved.values()
    )
    return ok, resolved


def _normalized_check(
    check: dict[str, Any] | None,
    *,
    default_status: str,
    **extra: Any,
) -> dict[str, Any]:
    payload = dict(check or {})
    payload["passed"] = bool(payload.get("passed", False))
    payload["status"] = str(payload.get("status") or default_status)
    payload.update(extra)
    return payload


def required_certification_failures(validation: dict[str, Any] | None) -> list[str]:
    checks = (validation or {}).get("certification_checks") or {}
    return [
        name
        for name in REQUIRED_CERTIFICATION_CHECKS
        if not bool((checks.get(name) or {}).get("passed", False))
    ]


def all_eras_beat_bh(metrics: dict[str, Any] | None) -> bool:
    """Return True when full, real, and modern share multipliers all beat B&H."""

    metrics = metrics or {}
    required = ("share_multiple", "real_share_multiple", "modern_share_multiple")
    try:
        return all(float(metrics.get(key, 0.0)) >= 1.0 for key in required)
    except (TypeError, ValueError):
        return False


def compute_gold_status(
    validation: dict[str, Any] | None,
    metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Strict display status for fully certified, artifact-backed all-era winners."""

    validation = validation or {}
    era_ok = all_eras_beat_bh(metrics)
    status = bool(
        validation.get("verdict") == "PASS"
        and validation.get("certified_not_overfit", False)
        and validation.get("backtest_certified", False)
        and era_ok
    )
    blockers = []
    if validation.get("verdict") != "PASS":
        blockers.append("validation verdict is not PASS")
    if not validation.get("certified_not_overfit", False):
        blockers.append("not certified_not_overfit")
    if not validation.get("backtest_certified", False):
        blockers.append("not backtest_certified / artifact-verified")
    if not era_ok:
        blockers.append("does not beat B&H in every era")
    return {
        "gold_status": status,
        "gold_status_label": GOLD_STATUS_LABEL if status else "Not Gold",
        "all_eras_beat_bh": era_ok,
        "gold_status_blockers": blockers,
    }


def sync_validation_contract(
    validation: dict[str, Any] | None,
    *,
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a deep-copied, normalized validation dict.

    The input is not mutated; a `copy.deepcopy` of `validation` is taken and
    all canonical contract fields (`promotion_ready`, `certified_not_overfit`,
    `backtest_certified`, `clean_pass`, `certification_checks`, `advisories`,
    and the mirrored `gates.gate7` block) are recomputed from the inputs and
    written onto the copy before it is returned.
    """

    normalized = copy.deepcopy(validation or {})
    checks = dict(normalized.get("certification_checks") or {})

    for name in REQUIRED_CERTIFICATION_CHECKS:
        checks[name] = _normalized_check(
            checks.get(name),
            default_status="pass" if (checks.get(name) or {}).get("passed") else "fail",
        )

    artifact_check = dict(checks.get("artifact_completeness") or {})
    # Stored stamps are never trusted: if the check carries recorded paths,
    # re-verify the bundle on disk every sync (2026-06-09 — previously a
    # stored passed=True survived even when the files no longer existed).
    if artifact_paths is None and artifact_check.get("paths"):
        artifact_paths = dict(artifact_check["paths"])

    if artifact_paths is None:
        if artifact_check:
            # No paths recorded anywhere — a bare stamp cannot be verified,
            # so it cannot count as artifact-complete.
            checks["artifact_completeness"] = _normalized_check(
                artifact_check,
                default_status="unverifiable",
            )
            checks["artifact_completeness"]["passed"] = False
            checks["artifact_completeness"]["status"] = (
                "pending"
                if artifact_check.get("status") == "pending"
                else "unverifiable"
            )
        else:
            checks["artifact_completeness"] = {
                "passed": False,
                "status": "pending",
                "pending_reason": "run artifacts are generated after validation",
            }
    else:
        artifact_ok, resolved_paths = verify_artifact_bundle(artifact_paths)
        checks["artifact_completeness"] = _normalized_check(
            artifact_check,
            default_status="pass" if artifact_ok else "fail",
            paths=resolved_paths,
        )
        checks["artifact_completeness"]["passed"] = artifact_ok
        checks["artifact_completeness"]["status"] = "pass" if artifact_ok else "fail"

    gate7 = dict((normalized.get("gates") or {}).get("gate7") or {})
    promotion_ready = bool(
        normalized.get(
            "promotion_ready",
            gate7.get("promotion_ready", normalized.get("promotion_eligible", False)),
        )
    )
    required_ok = not required_certification_failures({"certification_checks": checks})
    artifact_ok = bool((checks.get("artifact_completeness") or {}).get("passed", False))
    certified_not_overfit = promotion_ready and required_ok
    backtest_certified = certified_not_overfit and artifact_ok

    existing_clean_pass = bool(normalized.get("clean_pass", False))
    clean_pass = existing_clean_pass
    if artifact_paths is not None:
        clean_pass = existing_clean_pass and backtest_certified

    advisories = list(normalized.get("advisories") or gate7.get("advisories") or [])
    advisories = [
        item
        for item in advisories
        if item not in {ARTIFACT_PENDING_ADVISORY, ARTIFACT_FAILED_ADVISORY}
    ]
    artifact_status = (checks.get("artifact_completeness") or {}).get("status")
    if artifact_status == "pending":
        advisories.append(ARTIFACT_PENDING_ADVISORY)
    elif artifact_status == "fail":
        advisories.append(ARTIFACT_FAILED_ADVISORY)

    normalized["promotion_ready"] = promotion_ready
    normalized["certified_not_overfit"] = certified_not_overfit
    normalized["backtest_certified"] = backtest_certified
    normalized["clean_pass"] = clean_pass
    normalized["certification_checks"] = checks
    normalized["advisories"] = _dedupe(advisories)

    gates = dict(normalized.get("gates") or {})
    gate7["promotion_ready"] = promotion_ready
    gate7["certified_not_overfit"] = certified_not_overfit
    gate7["backtest_certified"] = backtest_certified
    gate7["clean_pass"] = clean_pass
    gate7["certification_checks"] = checks
    gate7["advisories"] = normalized["advisories"]
    gates["gate7"] = gate7
    normalized["gates"] = gates

    return normalized


def stamp_montauk_score(
    entry: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the Montauk Score + its three pillars onto an entry, in place.

    The Montauk Score is the single leaderboard-ranking / active-strategy score
    (Conviction 0.55 × Performance 0.30 × Durability 0.15). Stamping it here means
    every certified row carries it for free — the leaderboard sorts by it and the
    viz reads it directly, with no re-derivation. Uses the process-cached
    enrichment context so the persisted value is calibrated and consistent across
    every call site.
    """
    # Lazy import: search.montauk_score pulls in validation.confidence_v2, which
    # itself lazily imports this module. Importing at module load is avoidable.
    from search.montauk_score import compute_montauk_score, default_context

    score = compute_montauk_score(
        entry, context=context if context is not None else default_context()
    )
    entry["montauk_score"] = score["montauk_score"]
    entry["montauk_score_100"] = score["montauk_score_100"]
    entry["conviction"] = score["conviction"]
    entry["conviction_100"] = score["conviction_100"]
    entry["performance"] = score["performance"]
    entry["performance_100"] = score["performance_100"]
    entry["durability"] = score["durability"]
    entry["durability_100"] = score["durability_100"]
    entry["montauk_calibration_state"] = score["calibration_state"]
    entry["montauk_pillars"] = score["pillars"]
    return entry


def sync_entry_contract(
    entry: dict[str, Any],
    *,
    artifact_paths: dict[str, str] | None = None,
    montauk_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronize top-level entry fields with the canonical validation block."""

    validation = sync_validation_contract(
        entry.get("validation"),
        artifact_paths=artifact_paths,
    )
    entry["validation"] = validation
    entry["promotion_ready"] = validation["promotion_ready"]
    entry["certified_not_overfit"] = validation["certified_not_overfit"]
    entry["backtest_certified"] = validation["backtest_certified"]
    entry["certification_checks"] = validation["certification_checks"]
    gold = compute_gold_status(validation, entry.get("metrics"))
    validation.update(gold)
    gates = dict(validation.get("gates") or {})
    gate7 = dict(gates.get("gate7") or {})
    gate7.update(gold)
    gates["gate7"] = gate7
    validation["gates"] = gates
    entry["validation"] = validation
    entry.update(gold)
    stamp_montauk_score(entry, context=montauk_context)
    return entry


def is_leaderboard_eligible(entry: dict[str, Any]) -> tuple[bool, str]:
    """Return whether an entry may be persisted to the authority leaderboard."""

    validation = sync_validation_contract(entry.get("validation"))
    if not validation:
        return False, "missing validation"
    gold = compute_gold_status(validation, entry.get("metrics"))
    if not bool(gold.get("gold_status", False)):
        blockers = gold.get("gold_status_blockers") or ["gold_status=False"]
        return False, f"gold_status=False ({'; '.join(blockers)})"
    if not bool(validation.get("certified_not_overfit", False)):
        verdict = validation.get("verdict", "?")
        if not bool(validation.get("promotion_ready", False)):
            return False, f"promotion_ready=False (verdict={verdict})"
        failing = required_certification_failures(validation)
        if failing:
            return False, f"certification checks failing: {', '.join(failing)}"
        return False, "certified_not_overfit=False"
    return True, "ok"
