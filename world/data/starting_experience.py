"""
Rites of Passage — Starting Experience Data

Plain-Python data module defining what a new character receives at
first login: starting items, currency, quests, and starting room.

NO Evennia imports — fully unit-testable.
"""

from __future__ import annotations

from world.data.constants import (
    TOWN_GOOD_START,
    TOWN_EVIL_START,
)
from world.data.enums import Faction


# ---------------------------------------------------------------------------
# Starting Room Resolution
# ---------------------------------------------------------------------------
#
# Starting rooms are configured via server.conf.settings.FACTION_STARTING_ROOMS.
# The mapping is injected into get_starting_room_id() by the bridge layer so
# this module remains plain-Python and unit-testable without Evennia imports.
#
# No hardcoded room IDs live here — all configuration is centralized in settings.

# Tag that the builder sets on the town-square room.
ROOM_TAG_GOOD_START = TOWN_GOOD_START
ROOM_TAG_EVIL_START = TOWN_EVIL_START


def get_starting_room_id(
    faction: Faction | None,
    *,
    faction_start_rooms: dict[str, str | None] | None = None,
) -> str:
    """
    Return the canonical room_id for a new character's start room.

    Args:
        faction: The character's faction, or None.
        faction_start_rooms: Per-faction room_id mapping (injected from
            server.conf.settings.FACTION_STARTING_ROOMS).  Values of None
            mean "not yet configured".

    Returns:
        The room_id string.

    Raises:
        ValueError: If faction is None, faction is unknown, or the
            configured room for that faction is None (not yet built).
    """
    if faction_start_rooms is None:
        raise ValueError(
            "FACTION_STARTING_ROOMS is not configured. "
            "Please set it in server/conf/settings.py."
        )

    if faction is None:
        raise ValueError(
            "Character has no faction assigned. "
            "Choose a faction (good/evil) at character creation, "
            "or configure a default room for factionless characters in settings."
        )

    room_id = faction_start_rooms.get(faction.value)
    if room_id is None:
        raise ValueError(
            f"No starting room is configured for faction '{faction.value}'. "
            f"Set FACTION_STARTING_ROOMS['{faction.value}'] in "
            f"server/conf/settings.py to a valid room world ID."
        )

    return room_id


# ---------------------------------------------------------------------------
# Starting Items
# ---------------------------------------------------------------------------
#
# Every new character receives these items regardless of profession.
# ALL VALUES ARE [PLACEHOLDER] pending final game-design tuning.

DEFAULT_STARTING_ITEMS: list[dict] = [
    {"item_id": "health_potion", "quantity": 2},
    {"item_id": "mana_potion", "quantity": 1},
    {"item_id": "torch", "quantity": 1},
    {"item_id": "cloth_vest", "quantity": 1},
]

# Profession-specific starting weapon.  [PLACEHOLDER]
PROFESSION_STARTING_WEAPON: dict[str, str] = {
    "warrior": "rusty_sword",
    "mage": "wooden_club",
    "warlock": "wooden_club",
    "cleric": "wooden_club",
    "thief": "rusty_sword",
    "ninja": "rusty_sword",
    "druid": "wooden_club",
    "ranger": "short_bow",
    "paladin": "rusty_sword",
    "shaman": "hunting_whip",
    "monk": "wooden_club",  # [PLACEHOLDER]
    "bard": "rusty_sword",  # [PLACEHOLDER]
    "beserker": "rusty_sword",  # [PLACEHOLDER]
}


def get_starting_items(profession_id: str) -> list[dict]:
    """
    Return the complete list of starting items for a profession.

    Includes default items plus a profession-appropriate weapon.
    """
    items = list(DEFAULT_STARTING_ITEMS)

    weapon_id = PROFESSION_STARTING_WEAPON.get(profession_id)
    if weapon_id is not None:
        items.append({"item_id": weapon_id, "quantity": 1})

    return items


# ---------------------------------------------------------------------------
# Starting Currency
# ---------------------------------------------------------------------------

# Copper pieces given to new characters.  [PLACEHOLDER]
STARTING_CURRENCY: int = 100


# ---------------------------------------------------------------------------
# Starting Quest
# ---------------------------------------------------------------------------

# Quest auto-accepted on first login.  None = no auto-quest.
STARTING_QUEST_ID: str | None = "rat_slayer"


# ---------------------------------------------------------------------------
# Tutorial Completion
# ---------------------------------------------------------------------------

def is_tutorial_completed(cd: "CharacterData") -> bool:
    """Return True if the character has completed the starting flow."""
    return cd.tutorial_completed


def complete_starting_experience(cd: "CharacterData") -> None:
    """
    Apply all starting rewards to a freshly-created CharacterData.

    This is idempotent — if tutorial_completed is already True,
    nothing happens.

    Mutations:
        - Adds starting currency
        - Adds default + profession items to inventory
        - Auto-accepts the starting quest (if defined)
        - Sets tutorial_completed = True
    """
    from world.data.economy import add_currency
    from world.data.quests import accept_quest, get_quest

    if cd.tutorial_completed:
        return

    # ---- Currency ----
    if STARTING_CURRENCY > 0 and cd.currency == 0:
        try:
            add_currency(cd, STARTING_CURRENCY)
        except ValueError:
            pass  # already has currency — don't overwrite

    # ---- Items ----
    items = get_starting_items(cd.profession_id)
    for item_def in items:
        cd.add_item(item_def["item_id"], item_def["quantity"])

    # ---- Starting quest ----
    if STARTING_QUEST_ID is not None:
        quest = get_quest(STARTING_QUEST_ID)
        if quest is not None:
            # Only accept if not already accepted/completed.
            from world.data.quests import get_quest_state
            state = get_quest_state(cd, STARTING_QUEST_ID)
            if state is None:
                accept_quest(cd, STARTING_QUEST_ID)

    # ---- Mark complete ----
    cd.tutorial_completed = True
