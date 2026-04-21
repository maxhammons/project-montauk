"""Display-name assignment for leaderboard entries.

Rule:
  - Each strategy family (the codename, e.g. ``gc_n8``) is bound to one **animal**.
  - Each entry within that family gets a unique **adjective** so siblings
    are visually distinct (``Velvet Jaguar`` vs ``Amber Jaguar``).

The binding is persisted to ``spike/name_registry.json`` so names are stable
across re-runs. A params-hash keys the per-entry adjective, so the same
(family, params) pair always gets the same display name.

Seeded bindings (2026-04-20):
  gc_n8               -> Jaguar   (Velvet)
  gc_precross_strict  -> Heron    (Copper)
  gc_precross_roc     -> Fox      (Slate)
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

ADJECTIVES = [
    "Velvet",
    "Amber",
    "Copper",
    "Slate",
    "Midnight",
    "Ivory",
    "Ember",
    "Crimson",
    "Jade",
    "Onyx",
    "Pewter",
    "Russet",
    "Saffron",
    "Obsidian",
    "Cobalt",
    "Gilded",
    "Ashen",
    "Indigo",
    "Umber",
    "Silver",
    "Scarlet",
    "Tawny",
    "Cerulean",
    "Verdant",
    "Dusky",
    "Bronze",
    "Hazel",
    "Brindled",
    "Marbled",
    "Sable",
]

ANIMALS = [
    "Jaguar",
    "Heron",
    "Fox",
    "Otter",
    "Lynx",
    "Falcon",
    "Ibex",
    "Stag",
    "Marten",
    "Badger",
    "Osprey",
    "Kestrel",
    "Hare",
    "Wolverine",
    "Caracal",
    "Serval",
    "Gannet",
    "Pangolin",
    "Okapi",
    "Tanager",
    "Gecko",
    "Shrike",
    "Civet",
    "Bonobo",
    "Tapir",
]

SEED_ANIMALS: dict[str, str] = {
    "gc_n8": "Jaguar",
    "gc_precross_strict": "Heron",
    "gc_precross_roc": "Fox",
}

SEED_ASSIGNMENTS: dict[str, dict[str, str]] = {
    "gc_n8": {"__any__": "Velvet Jaguar"},
    "gc_precross_strict": {"__any__": "Copper Heron"},
    "gc_precross_roc": {"__any__": "Slate Fox"},
}


def _params_hash(params: dict[str, Any]) -> str:
    raw = json.dumps(params or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _load_registry(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"families": {}, "used_animals": []}


def _save_registry(path: str, registry: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(registry, f, indent=2, sort_keys=True)


def _seed_if_empty(registry: dict[str, Any]) -> None:
    """Seed brand-new families only. Never mutates an existing family —
    otherwise popped ``__any__`` fallbacks would resurrect on every call."""
    fams = registry.setdefault("families", {})
    used = set(registry.setdefault("used_animals", []))
    for fam, animal in SEED_ANIMALS.items():
        if fam in fams:
            continue
        assigns = dict(SEED_ASSIGNMENTS.get(fam, {}))
        adjectives_used: list[str] = []
        for name in assigns.values():
            adj = name.split(" ", 1)[0]
            if adj not in adjectives_used:
                adjectives_used.append(adj)
        fams[fam] = {
            "animal": animal,
            "assignments": assigns,
            "adjectives_used": adjectives_used,
        }
        used.add(animal)
    registry["used_animals"] = sorted(used)


def _pick_animal(family: str, registry: dict[str, Any]) -> str:
    used = set(registry.get("used_animals", []))
    # Deterministic-ish: hash family name to rotate into the pool.
    h = int(hashlib.md5(family.encode()).hexdigest(), 16)
    for i in range(len(ANIMALS)):
        candidate = ANIMALS[(h + i) % len(ANIMALS)]
        if candidate not in used:
            return candidate
    # Pool exhausted — recycle deterministically.
    return ANIMALS[h % len(ANIMALS)]


def _pick_adjective(params_key: str, used_adjectives: list[str]) -> str:
    h = int(hashlib.md5(params_key.encode()).hexdigest(), 16)
    used = set(used_adjectives)
    for i in range(len(ADJECTIVES)):
        candidate = ADJECTIVES[(h + i) % len(ADJECTIVES)]
        if candidate not in used:
            return candidate
    return ADJECTIVES[h % len(ADJECTIVES)]


def assign_display_name(
    strategy: str, params: dict[str, Any], registry_path: str
) -> str:
    """Return a stable "Adjective Animal" name for ``(strategy, params)``.

    Loads / initializes / persists the registry at ``registry_path``.
    Same strategy family always gets the same animal; each distinct params
    set within that family gets a distinct adjective.
    """
    registry = _load_registry(registry_path)
    _seed_if_empty(registry)

    fams = registry["families"]
    fam = fams.get(strategy)
    if fam is None:
        animal = _pick_animal(strategy, registry)
        fam = {"animal": animal, "assignments": {}, "adjectives_used": []}
        fams[strategy] = fam
        used = set(registry.get("used_animals", []))
        used.add(animal)
        registry["used_animals"] = sorted(used)

    pk = _params_hash(params)
    existing = fam["assignments"].get(pk) or fam["assignments"].get("__any__")
    if existing and pk not in fam["assignments"]:
        # Promote the seeded "__any__" entry to this specific params hash.
        fam["assignments"][pk] = existing
        fam["assignments"].pop("__any__", None)
    if fam["assignments"].get(pk):
        _save_registry(registry_path, registry)
        return fam["assignments"][pk]

    adj = _pick_adjective(f"{strategy}:{pk}", fam["adjectives_used"])
    name = f"{adj} {fam['animal']}"
    fam["assignments"][pk] = name
    fam["adjectives_used"].append(adj)
    _save_registry(registry_path, registry)
    return name
