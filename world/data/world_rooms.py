"""
Rites of Passage — World Room Data & Spawn Configuration

Stable room identifiers and spawn tables that map mob spawns to
specific Silvermere rooms.  DATA ONLY — no Evennia imports.

This module is used by the world-integration layer to determine
which mobs should populate which rooms.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Stable Room Identifiers
# ---------------------------------------------------------------------------
#
# These are the canonical room_id values used throughout the game.
# They match the world_room_id attribute set by build_silvermere.py
# on Evennia Room objects.

# Central hub
ROOM_TOWN_SQUARE = "silvermere_town_square"

# Named shop / landmark rooms (subset of the 285-room dataset)
ROOM_IRON_SKULL = "silvermere_l70_c41"          # head/foot armor shop
ROOM_BLACKENED_PLATE = "silvermere_l70_c37"     # body armor shop
ROOM_BROKEN_AEGIS = "silvermere_l60_c37"        # shield shop
ROOM_BLACK_IRON_BANK = "silvermere_l74_c41"     # bank

# Stable room-id lookup by functional name
NAMED_ROOMS: dict[str, str] = {
    "town_square": ROOM_TOWN_SQUARE,
    "iron_skull": ROOM_IRON_SKULL,
    "blackened_plate": ROOM_BLACKENED_PLATE,
    "broken_aegis": ROOM_BROKEN_AEGIS,
    "black_iron_bank": ROOM_BLACK_IRON_BANK,
}


# ---------------------------------------------------------------------------
# Spawn Configuration
# ---------------------------------------------------------------------------
#
# Each entry defines a spawn point: which mob_id, in which room, and
# how many seconds before the mob respawns after death.
#
# ALL VALUES ARE [PLACEHOLDER] pending final game-design tuning.

# A single spawn entry: {spawn_id, mob_id, room_id, respawn_seconds}

SILVERMERE_SPAWNS: list[dict] = [
    # ---- Town Square & surroundings ----
    {
        "spawn_id": "svr_town_square_rat_01",
        "mob_id": "giant_rat",
        "room_id": "silvermere_town_square",
        "respawn_seconds": 300,  # 5-min default [PLACEHOLDER]
    },
    {
        "spawn_id": "svr_town_square_rat_02",
        "mob_id": "giant_rat",
        "room_id": "silvermere_town_square",
        "respawn_seconds": 300,
    },
    # ---- Near the Black Iron Bank ----
    {
        "spawn_id": "svr_bank_skeleton_01",
        "mob_id": "skeleton_warrior",
        "room_id": "silvermere_l74_c41",
        "respawn_seconds": 300,
    },
    # ---- Guard patrol near Town Square east exit ----
    {
        "spawn_id": "svr_guard_01",
        "mob_id": "town_guard",
        "room_id": "silvermere_l72_c48",
        "respawn_seconds": 300,
    },
    # ---- Merchant near Town Square west ----
    {
        "spawn_id": "svr_merchant_01",
        "mob_id": "friendly_merchant",
        "room_id": "silvermere_l72_c41",
        "respawn_seconds": 300,
    },
]


# ---------------------------------------------------------------------------
# Spawn Table Queries
# ---------------------------------------------------------------------------


def get_spawns_for_room(room_id: str) -> list[dict]:
    """Return all spawn configs assigned to a given room_id."""
    return [s for s in SILVERMERE_SPAWNS if s["room_id"] == room_id]


def get_all_spawn_room_ids() -> set[str]:
    """Return the set of room_ids that have at least one spawn configured."""
    return {s["room_id"] for s in SILVERMERE_SPAWNS}


def room_has_spawns(room_id: str) -> bool:
    """Return True if the room has at least one spawn configured."""
    return any(s["room_id"] == room_id for s in SILVERMERE_SPAWNS)


def get_named_room(alias: str) -> str | None:
    """Return the canonical room_id for a named room alias, or None."""
    return NAMED_ROOMS.get(alias.lower().replace(" ", "_"))


def is_known_room_id(room_id: str) -> bool:
    """Return True if the room_id appears in the named rooms or spawn table."""
    if room_id in NAMED_ROOMS.values():
        return True
    return room_has_spawns(room_id)
