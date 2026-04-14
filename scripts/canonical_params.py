#!/usr/bin/env python3
"""
Strict canonical parameter set for T0 (Hypothesis) strategies.

T0 strategies are hand-authored from a hypothesis. Their parameter values must
come from this fixed list — the point is to force hypotheses to be argued from
first principles, not param-fiddled into existence. "200-day moving average"
is a thing in the world. "EMA-187" is a search result.

See `reference/spirit-guide/VALIDATION-PHILOSOPHY.md` Section 5.
"""

from __future__ import annotations

from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Canonical value sets by parameter family
# ─────────────────────────────────────────────────────────────────────────────

MA_PERIODS = {7, 9, 14, 20, 21, 30, 50, 100, 150, 200, 300}
RSI_PERIODS = {7, 14, 21}
ATR_PERIODS = {7, 14, 20, 40}
ATR_MULTIPLIERS = {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}
LOOKBACK_PERIODS = {5, 10, 20, 50, 100, 150, 200}
SLOPE_CONFIRM_BARS = {1, 2, 3, 5}
COOLDOWN_BARS = {0, 1, 2, 3, 5, 10}
PCT_THRESHOLDS = {5.0, 8.0, 10.0, 15.0, 20.0, 25.0}
MACD_TRIPLES = {(12, 26, 9), (8, 17, 9)}


# ─────────────────────────────────────────────────────────────────────────────
# Parameter name → family mapping
#
# Param names are matched by substring. Order matters — more specific names
# should be checked before more general ones.
# ─────────────────────────────────────────────────────────────────────────────

_NAME_FAMILY_RULES: list[tuple[str, set]] = [
    # Most specific first
    ("atr_mult", ATR_MULTIPLIERS),
    ("atr_period", ATR_PERIODS),
    ("rsi_len", RSI_PERIODS),
    ("rsi_period", RSI_PERIODS),
    ("cooldown", COOLDOWN_BARS),
    ("slope_window", SLOPE_CONFIRM_BARS),
    ("slope_lookback", SLOPE_CONFIRM_BARS),
    ("entry_bars", SLOPE_CONFIRM_BARS),
    ("exit_bars", SLOPE_CONFIRM_BARS),
    ("entry_confirm", SLOPE_CONFIRM_BARS),
    ("exit_confirm", SLOPE_CONFIRM_BARS),
    ("confirm_bars", SLOPE_CONFIRM_BARS),
    # MA/EMA/SMA/TEMA period families
    ("short_ema", MA_PERIODS),
    ("med_ema", MA_PERIODS),
    ("long_ema", MA_PERIODS),
    ("fast_ema", MA_PERIODS),
    ("slow_ema", MA_PERIODS),
    ("trend_ema", MA_PERIODS),
    ("quick_ema", MA_PERIODS),
    ("ema_len", MA_PERIODS),
    ("sma_len", MA_PERIODS),
    ("tema_len", MA_PERIODS),
    ("trend_len", MA_PERIODS),
    ("tenkan_len", MA_PERIODS),
    ("kijun_len", MA_PERIODS),
    ("cloud_len", MA_PERIODS),
    # Lookback windows
    ("lookback", LOOKBACK_PERIODS),
    ("entry_len", LOOKBACK_PERIODS),
    ("exit_len", LOOKBACK_PERIODS),
    # Percent thresholds
    ("trail_pct", PCT_THRESHOLDS),
    ("breakout_pct", PCT_THRESHOLDS),
    ("drop_pct", PCT_THRESHOLDS),
    ("drawdown_pct", PCT_THRESHOLDS),
]


def family_for_param(name: str) -> set | None:
    """Return the canonical value set for a param name, or None if unmapped.

    Matching is by substring; the first rule that matches wins. An unmapped
    name means the T0 canonical check can't be enforced for this param — the
    strategy cannot be T0-eligible.
    """
    n = name.lower()
    for key, family in _NAME_FAMILY_RULES:
        if key in n:
            return family
    return None


def is_canonical_value(name: str, value: Any) -> bool:
    """Is a single (name, value) pair drawn from the canonical set for its family?"""
    family = family_for_param(name)
    if family is None:
        return False
    # Numeric comparison tolerant of int/float
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        for allowed in family:
            if isinstance(allowed, tuple):
                continue
            if abs(float(allowed) - float(value)) < 1e-9:
                return True
    return False


def check_canonical(params: dict) -> tuple[bool, list[str]]:
    """Check whether every tunable param in a dict is canonical.

    Returns (is_canonical, list_of_violations). Each violation is a
    human-readable string like 'entry_rsi=47.5 not in canonical set'.

    Non-numeric values (bools, strings) are treated as violations because
    they are not recognised canonical param families. MACD triples are not
    yet supported at this granularity — strategies using MACD params should
    register as T1.
    """
    violations: list[str] = []
    for name, value in params.items():
        # Ignore obvious non-tunables
        if name in {"cooldown"} and isinstance(value, (int, float)) and float(value) in COOLDOWN_BARS:
            continue
        if isinstance(value, bool):
            violations.append(f"{name}={value} (boolean not canonical)")
            continue
        if not isinstance(value, (int, float)):
            violations.append(f"{name}={value!r} (non-numeric not canonical)")
            continue
        family = family_for_param(name)
        if family is None:
            violations.append(f"{name}={value} (no canonical family mapped)")
            continue
        if not is_canonical_value(name, value):
            sample = sorted(v for v in family if not isinstance(v, tuple))[:6]
            violations.append(f"{name}={value} not in canonical set (sample: {sample})")
    return (len(violations) == 0, violations)


def count_tunable_params(params: dict) -> int:
    """Tunable param count for tier-size gates. Mirrors evolve._count_tunable_params
    but kept here so tier logic has no cross-dependency on the optimizer."""
    return sum(
        1
        for k, v in params.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "cooldown"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tier eligibility
#
# T0: ≤ 5 tunable params AND all canonical AND strategy registered as T0
# T1: ≤ 8 tunable params AND strategy registered as T0 or T1
# T2: everything else (and anything optimizer-touched)
# ─────────────────────────────────────────────────────────────────────────────

T0_MAX_PARAMS = 5
T1_MAX_PARAMS = 8


def effective_tier(declared_tier: str, params: dict) -> tuple[str, list[str]]:
    """Compute the effective tier given a declared tier and concrete params.

    A strategy registered as T0 that has non-canonical params or too many
    params is auto-promoted to T1 or T2. The declared tier is the upper
    bound on leniency; the effective tier is what validation actually uses.

    Returns (effective_tier, reasons). `reasons` explains any auto-promotion.
    """
    declared = (declared_tier or "T2").upper()
    if declared not in {"T0", "T1", "T2"}:
        declared = "T2"
    n_params = count_tunable_params(params)
    reasons: list[str] = []

    if declared == "T0":
        if n_params > T0_MAX_PARAMS:
            reasons.append(f"T0 declared but {n_params} tunable params > {T0_MAX_PARAMS}")
            declared = "T1"
        else:
            ok, violations = check_canonical(params)
            if not ok:
                reasons.extend(f"T0 canonical violation: {v}" for v in violations)
                declared = "T1"

    if declared == "T1":
        if n_params > T1_MAX_PARAMS:
            reasons.append(f"T1 effective but {n_params} tunable params > {T1_MAX_PARAMS}")
            declared = "T2"

    return declared, reasons
