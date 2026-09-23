"""
Rites of Passage — Faction Registry

Plain-Python faction data and lookups.  No Evennia imports.

Faction definitions are dicts keyed by string faction_id.  The registry is
seeded from the Faction enum and supports custom (non-enum) Forge faction IDs.
"""

from world.data.enums import Faction

# ---------------------------------------------------------------------------
# Built-in faction display names (seeded from Faction enum values)
# ---------------------------------------------------------------------------

_BUILTIN_FACTIONS = {
    Faction.GOOD.value: "Valroian",
    Faction.EVIL.value: "Mordrath",
}

# ---------------------------------------------------------------------------
# Faction Registry
# ---------------------------------------------------------------------------

FACTION_REGISTRY: dict[str, dict] = {}

# Seed from every existing Faction enum member.
for _member in Faction:
    _fid = _member.value
    FACTION_REGISTRY[_fid] = {
        "id": _fid,
        "name": _BUILTIN_FACTIONS.get(_fid, _fid.title()),
        "description": "",
    }

# ---------------------------------------------------------------------------
# Registry Accessors
# ---------------------------------------------------------------------------


def register_faction(faction_id: str, name: str, description: str = "") -> None:
    """Create or update a faction entry in FACTION_REGISTRY.

    When ``faction_id`` already exists, only *name* and *description* are
    overwritten — all other existing fields are left untouched.  This allows
    custom Forge faction IDs that are not members of the :class:`Faction` enum.
    """
    if faction_id in FACTION_REGISTRY:
        FACTION_REGISTRY[faction_id]["name"] = name
        FACTION_REGISTRY[faction_id]["description"] = description
        return

    FACTION_REGISTRY[faction_id] = {
        "id": faction_id,
        "name": name,
        "description": description,
    }


def get_faction(faction_id: str) -> dict:
    """Return the faction definition dict for *faction_id*.

    Raises :exc:`KeyError` when the faction is not in the registry.
    """
    return FACTION_REGISTRY[faction_id]


def faction_exists(faction_id: str) -> bool:
    """Return ``True`` if *faction_id* is registered."""
    return faction_id in FACTION_REGISTRY