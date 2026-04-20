from __future__ import annotations

"""Compatibility helpers for the share-count performance metric."""

from collections.abc import Mapping
from typing import Any

LEGACY_SHARE_MULTIPLE_KEY = "vs_" "bah"


def read_share_multiple(metrics: Mapping[str, Any] | None) -> float:
    """Read the canonical share-count multiplier from a metrics mapping."""
    if not metrics:
        return 0.0
    value = metrics.get("share_multiple")
    if value is None:
        value = metrics.get(LEGACY_SHARE_MULTIPLE_KEY, 0.0)
    return float(value or 0.0)
