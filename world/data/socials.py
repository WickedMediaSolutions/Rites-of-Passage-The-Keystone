"""
Rites of Passage — Socials, Guilds, Sects (Phase 19)

Data-driven registries for social emotes, guild membership, and sect
membership.  All registries are plain dictionaries that can be extended
by adding entries without changing command logic.

Guild / sect registries use stable string IDs internally and display
names for player-facing output.
"""

# =============================================================================
# Social / Emote Registry
# =============================================================================
# Each entry maps a social name (used as the command key) to a dict of
# message templates:
#     self_msg  — shown to the acting player when no target is given
#     target_msg — shown to the target (use {actor} and {target})
#     room_msg   — shown to everyone else in the room (use {actor} and {target})
#     self_target_msg — shown to the actor when a target is provided
#
# New socials can be added by inserting entries; command logic does not
# need to change.
#
# NOTE: These two entries are INITIAL / SAMPLE definitions only.
#       They are NOT the complete Rites of Passage social catalog.

SOCIAL_REGISTRY: dict[str, dict[str, str]] = {
    "wave": {
        "self_msg": "You wave.",
        "self_target_msg": "You wave at {target}.",
        "target_msg": "{actor} waves at you.",
        "room_msg": "{actor} waves at {target}.",
    },
    "bow": {
        "self_msg": "You bow gracefully.",
        "self_target_msg": "You bow to {target}.",
        "target_msg": "{actor} bows to you.",
        "room_msg": "{actor} bows to {target}.",
    },
}


def resolve_social(name: str) -> str | None:
    """
    Find a social key by case-insensitive name match.

    Returns the canonical social key (lowercase) or None if not found.
    """
    name_lower = name.lower().strip()
    if name_lower in SOCIAL_REGISTRY:
        return name_lower
    return None


def social_exists(name: str) -> bool:
    """Return True if the named social is defined."""
    return resolve_social(name) is not None


# =============================================================================
# Guild Registry
# =============================================================================
# Maps stable guild IDs to display names.

GUILD_REGISTRY: dict[str, str] = {
    "mercenaries_guild": "Mercenaries Guild",
    "merchants_guild": "Merchants Guild",
    "adventurers_guild": "Adventurers Guild",
    "shadow_syndicate": "Shadow Syndicate",
}


def resolve_guild(name: str) -> str | None:
    """
    Find a guild ID by case-insensitive name match.

    Matches against both the stable ID and the display name.
    Returns the canonical guild ID or None.
    """
    name_lower = name.lower().strip()
    if name_lower in GUILD_REGISTRY:
        return name_lower
    for gid, display in GUILD_REGISTRY.items():
        if display.lower() == name_lower:
            return gid
    for gid, display in GUILD_REGISTRY.items():
        if name_lower in display.lower():
            return gid
    return None


def guild_exists(guild_id: str) -> bool:
    """Return True if the guild ID is registered."""
    return guild_id in GUILD_REGISTRY


def get_guild_name(guild_id: str) -> str | None:
    """Return the display name for a guild ID, or None."""
    return GUILD_REGISTRY.get(guild_id)


# =============================================================================
# Sect Registry
# =============================================================================
# Maps stable sect IDs to display names.

SECT_REGISTRY: dict[str, str] = {
    "order_of_light": "Order of Light",
    "keepers_of_flame": "Keepers of the Flame",
    "house_of_shadow": "House of Shadow",
    "crimson_circle": "Crimson Circle",
}


def resolve_sect(name: str) -> str | None:
    """
    Find a sect ID by case-insensitive name match.

    Matches against both the stable ID and the display name.
    Returns the canonical sect ID or None.
    """
    name_lower = name.lower().strip()
    if name_lower in SECT_REGISTRY:
        return name_lower
    for sid, display in SECT_REGISTRY.items():
        if display.lower() == name_lower:
            return sid
    for sid, display in SECT_REGISTRY.items():
        if name_lower in display.lower():
            return sid
    return None


def sect_exists(sect_id: str) -> bool:
    """Return True if the sect ID is registered."""
    return sect_id in SECT_REGISTRY


def get_sect_name(sect_id: str) -> str | None:
    """Return the display name for a sect ID, or None."""
    return SECT_REGISTRY.get(sect_id)