"""
Rites of Passage — Starting Experience Bridge

Evennia-side integration that provides the first-puppet experience:
places the character in the correct start room, grants starting
items/currency/quests, and marks the tutorial as complete.

Idempotent — safe to call on reconnect or server reload.
"""

from __future__ import annotations

# Evennia attribute keys (match the Character typeclass conventions).
FIRST_PUPPET_ATTR = "rop_first_puppet_done"


def handle_first_puppet(character) -> bool:
    """
    Called from Character.at_post_puppet().

    If this is the character's first-ever puppet (or the first since
    the attribute flag was cleared), set up the starting experience:

    1. Grant starting items, currency, quest via data-layer.
    2. Move the character to the correct starting room.
    3. Mark the character as having completed the starting flow.

    Returns True if actions were performed; False if already done.
    """
    if character.attributes.has(FIRST_PUPPET_ATTR):
        return False

    game = character.game

    # ---- Apply starting rewards (idempotent at the data layer) ----
    from world.data.starting_experience import (
        complete_starting_experience,
        get_starting_room_id,
    )
    complete_starting_experience(game)
    character.save()

    # ---- Move to starting room ----
    try:
        from server.conf.settings import FACTION_STARTING_ROOMS
        room_id = get_starting_room_id(
            game.faction,
            faction_start_rooms=FACTION_STARTING_ROOMS,
        )
    except ValueError as exc:
        character.msg(f"|r[System]|n {exc}")
        room_id = None

    if room_id is not None:
        room = _find_room_by_world_id(room_id)
        if room is not None:
            # Only move if currently in Limbo or None.
            current_location = character.location
            if current_location is None or _is_limbo(current_location):
                character.move_to(room, quiet=False)
        else:
            # Room configured but not built yet.
            current_location = character.location
            if current_location is None:
                character.msg(
                    "|y[System]|n The world has not been built yet. "
                    "Use |w@build_silvermere|n then reconnect, or ask an admin."
                )

    # ---- Mark first-puppet done ----
    character.attributes.add(FIRST_PUPPET_ATTR, True)

    return True


def is_first_puppet_done(character) -> bool:
    """Return True if the first-puppet flow has been completed."""
    return character.attributes.has(FIRST_PUPPET_ATTR)


def reset_first_puppet_flag(character) -> None:
    """
    Clear the first-puppet flag so the experience runs again.

    Useful for testing or admin intervention.
    Does NOT revert items/currency/quests already granted.
    """
    try:
        character.attributes.remove(FIRST_PUPPET_ATTR)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _find_room_by_world_id(room_id: str):
    """
    Resolve a configured starting room.

    Accepts:
    - Evennia DBREF strings such as "#885"
    - legacy world_room_id values
    - Atlas room IDs stored in atlas_id
    """
    from evennia import search_object

    # Direct Evennia DBREF lookup.
    if isinstance(room_id, str) and room_id.startswith("#"):
        matches = search_object(room_id)
        if matches:
            return matches[0]

    # Legacy world_room_id lookup.
    matches = search_object(
        room_id,
        attribute_name="world_room_id",
    )
    for obj in matches:
        if obj.attributes.get("world_room_id") == room_id:
            return obj

    # Atlas-imported room lookup.
    matches = search_object(
        room_id,
        attribute_name="atlas_id",
    )
    for obj in matches:
        if obj.attributes.get("atlas_id") == room_id:
            return obj

    return None


def _is_limbo(room) -> bool:
    """
    Return True if the room is Limbo (dbref #2, the default start).
    """
    try:
        return str(room.dbref) == "#2" or room.key == "Limbo"
    except Exception:
        return False
