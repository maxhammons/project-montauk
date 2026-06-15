"""Display-name assignment for leaderboard entries.

Rule:
  - Each strategy family (the codename, e.g. ``gc_n8``) is bound to one **animal**.
  - Each entry within that family gets a unique **adjective** so siblings
    are visually distinct (``Velvet Jaguar`` vs ``Amber Jaguar``).
  - **Reserved families** (see ``RESERVED_NAMES``) skip the animal scheme and
    render under a fixed display name instead — the Chimera committee is an
    ensemble *of* strategies, not one beast, so it is named ``Chimera`` rather
    than borrowing a single member's animal.

The animal pool is intentionally large (any recognizable animal is fair game)
so the one-animal-per-family invariant effectively never collides.

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
import re
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
    # Original pool (kept first so existing hash positions are stable).
    "Jaguar", "Heron", "Fox", "Otter", "Lynx", "Falcon", "Ibex", "Stag",
    "Marten", "Badger", "Osprey", "Kestrel", "Hare", "Wolverine", "Caracal",
    "Serval", "Gannet", "Pangolin", "Okapi", "Tanager", "Gecko", "Shrike",
    "Civet", "Bonobo", "Tapir",
    # Expanded pool — large enough that one-animal-per-family effectively
    # never collides. Any recognizable animal is fair game.
    "Aardvark", "Albatross", "Alpaca", "Anteater", "Antelope", "Armadillo",
    "Axolotl", "Baboon", "Bandicoot", "Barracuda", "Bison", "Bittern",
    "Bobcat", "Bongo", "Booby", "Buffalo", "Bushbuck", "Capybara", "Cassowary",
    "Cheetah", "Chinchilla", "Cobra", "Condor", "Cormorant", "Cougar",
    "Coyote", "Crane", "Curlew", "Dingo", "Dormouse", "Dugong", "Eagle",
    "Echidna", "Egret", "Eland", "Elk", "Ermine", "Ferret", "Finch",
    "Flamingo", "Fossa", "Gazelle", "Gerbil", "Gibbon", "Giraffe", "Gnu",
    "Goshawk", "Grebe", "Grison", "Grouse", "Guanaco", "Harrier", "Hedgehog",
    "Hornbill", "Hyena", "Ibis", "Impala", "Jackal", "Jackrabbit", "Jay",
    "Jerboa", "Kakapo", "Kangaroo", "Kinkajou", "Kite", "Kiwi", "Koala",
    "Kookaburra", "Kowari", "Kudu", "Lapwing", "Lemming", "Lemur", "Leopard",
    "Loris", "Macaque", "Magpie", "Mamba", "Mandrill", "Manticore", "Markhor",
    "Meerkat", "Merlin", "Mink", "Mongoose", "Moorhen", "Moose", "Mouflon",
    "Muntjac", "Narwhal", "Nightjar", "Nilgai", "Numbat", "Nuthatch", "Nyala",
    "Ocelot", "Onager", "Opossum", "Oribi", "Oriole", "Oryx", "Ouzel",
    "Panther", "Partridge", "Peccary", "Petrel", "Pika", "Pintail", "Plover",
    "Polecat", "Porpoise", "Possum", "Pronghorn", "Ptarmigan", "Puffin",
    "Puma", "Quail", "Quokka", "Quoll", "Raccoon", "Raven", "Reedbuck",
    "Rhea", "Roan", "Saiga", "Salamander", "Sandpiper", "Sasquatch",
    "Seriema", "Sika", "Sitatunga", "Skua", "Sloth", "Snipe", "Springbok",
    "Starling", "Stilt", "Stoat", "Stork", "Sunbird", "Swift", "Takin",
    "Tahr", "Teal", "Tern", "Topi", "Toucan", "Vervet", "Vicuna", "Vole",
    "Vulture", "Wallaby", "Wapiti", "Warbler", "Waxwing", "Weasel", "Whimbrel",
    "Wigeon", "Wombat", "Woodlark", "Wryneck", "Yak", "Zebu", "Zorilla",
]

RESERVED_NAMES: dict[str, str] = {
    # Committee / ensemble families render as a plain reserved name instead of
    # the adjective+animal scheme. Matched as exact codename or ``<prefix>_*``.
    "chimera": "Chimera",
}


def _reserved_base(strategy: str) -> str | None:
    """Return the reserved display label for a family, or ``None``.

    Matches an exact codename or a ``<prefix>_…`` versioned codename and folds
    the version number into the label, so each Chimera generation is
    distinguishable:
      ``chimera_v1_2026_05_26`` → ``Chimera 1``
      ``chimera_v2_…``          → ``Chimera 2``
      bare ``chimera``          → ``Chimera``
    """
    for prefix, label in RESERVED_NAMES.items():
        if strategy == prefix or strategy.startswith(prefix + "_"):
            m = re.search(r"_v(\d+)", strategy)
            return f"{label} {int(m.group(1))}" if m else label
    return None


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
    raw = json.dumps(params or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _load_registry(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return data
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
    reserved = _reserved_base(strategy)
    fam = fams.get(strategy)

    if reserved is not None and (
        fam is None or not fam.get("reserved") or fam.get("animal") != reserved
    ):
        # New reserved family, a legacy animal-scheme family being healed onto
        # its reserved name (chimera was once "Jade Bonobo"), or a reserved
        # label that changed (e.g. "Chimera" → "Chimera 1" after versioning).
        fam = {"animal": reserved, "assignments": {}, "adjectives_used": [],
               "reserved": True}
        fams[strategy] = fam
    elif fam is None:
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

    if fam.get("reserved"):
        # First sibling renders as the bare reserved label ("Chimera"); any
        # additional sibling gets a disambiguating adjective ("Jade Chimera").
        if fam["assignments"]:
            adj = _pick_adjective(f"{strategy}:{pk}", fam["adjectives_used"])
            fam["adjectives_used"].append(adj)
            name = f"{adj} {fam['animal']}"
        else:
            name = fam["animal"]
    else:
        adj = _pick_adjective(f"{strategy}:{pk}", fam["adjectives_used"])
        fam["adjectives_used"].append(adj)
        name = f"{adj} {fam['animal']}"
    fam["assignments"][pk] = name
    _save_registry(registry_path, registry)
    return name
