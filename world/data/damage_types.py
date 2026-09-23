"""
Rites of Passage — Damage-Type Registry

A centralised dictionary of every recognised damage type — both the built-in
types defined in the DamageType enum and custom types added at runtime (e.g.,
by a Forge builder or an importer).

The registry is seeded at import time from every member of the existing
DamageType enum.  Registry entries are plain dicts with at least:

    id          – damage_type_id string  (e.g. "piercing")
    name        – human-readable label   (e.g. "Piercing")
    description – flavour / design text  (default "")

Use the module-level functions to interact with the registry rather than
touching DAMAGE_TYPE_REGISTRY directly.
"""

from __future__ import annotations

from world.data.enums import DamageType


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DAMAGE_TYPE_REGISTRY: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def register_damage_type(
    damage_type_id: str,
    name: str,
    description: str = "",
) -> dict:
    """Create a new damage-type entry or update an existing one.

    When an entry already exists for *damage_type_id*, only *name* and
    *description* are overwritten — any other fields already present on
    the entry are preserved.
    """
    entry = DAMAGE_TYPE_REGISTRY.get(damage_type_id)
    if entry is None:
        entry = {}
        DAMAGE_TYPE_REGISTRY[damage_type_id] = entry

    entry["id"] = damage_type_id
    entry["name"] = name
    entry["description"] = description
    return entry


def get_damage_type(damage_type_id: str) -> dict | None:
    """Return the registry entry for *damage_type_id*, or ``None``."""
    return DAMAGE_TYPE_REGISTRY.get(damage_type_id)


def damage_type_exists(damage_type_id: str) -> bool:
    """Return ``True`` if *damage_type_id* is present in the registry."""
    return damage_type_id in DAMAGE_TYPE_REGISTRY


# ---------------------------------------------------------------------------
# Seed from the built-in DamageType enum
# ---------------------------------------------------------------------------

def _seed_builtins() -> None:
    """Populate DAMAGE_TYPE_REGISTRY from every DamageType enum member.

    For each member:
        id          = member.value           (e.g.  "piercing")
        name        = member.name converted to readable title case
                      (e.g. "PIERCING" → "Piercing")
        description = ""
    """
    for member in DamageType:
        # "PIERCING"  → "Piercing"
        # "UNHOLY"    → "Unholy"
        readable_name = member.name.replace("_", " ").title()
        DAMAGE_TYPE_REGISTRY[member.value] = {
            "id": member.value,
            "name": readable_name,
            "description": "",
        }


_seed_builtins()
del _seed_builtins  # one-shot helper; not part of the public API