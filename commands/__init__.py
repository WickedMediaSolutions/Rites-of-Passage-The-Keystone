"""
Rites of Passage — Command Helpers

Shared resolution helpers used by player commands.
These are kept separate from command classes so they
can be unit-tested without a running Evennia server.
"""


def resolve_item(name: str) -> str | None:
    """Find an item_id by case-insensitive name or partial match."""
    from world.data.items import ITEM_REGISTRY
    name_lower = name.lower().replace("_", " ").replace("-", " ")
    if name_lower in ITEM_REGISTRY:
        return name_lower
    for item_id, item_def in ITEM_REGISTRY.items():
        if item_def["name"].lower() == name_lower:
            return item_id
    for item_id, item_def in ITEM_REGISTRY.items():
        if name_lower in item_def["name"].lower():
            return item_id
    return None


def resolve_slot(name: str):
    """Find an EquipmentSlot by value or label."""
    from world.data.enums import EquipmentSlot
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for slot in EquipmentSlot:
        if slot.value == name_lower:
            return slot
    aliases = {
        "mainhand": EquipmentSlot.MAIN_HAND,
        "main_hand": EquipmentSlot.MAIN_HAND,
        "offhand": EquipmentSlot.OFF_HAND,
        "off_hand": EquipmentSlot.OFF_HAND,
        "head": EquipmentSlot.HEAD,
        "chest": EquipmentSlot.CHEST,
        "legs": EquipmentSlot.LEGS,
        "hands": EquipmentSlot.HANDS,
        "feet": EquipmentSlot.FEET,
        "wrists": EquipmentSlot.WRISTS,
        "ring1": EquipmentSlot.LEFT_FINGER,
        "ring2": EquipmentSlot.RIGHT_FINGER,
        "left_finger": EquipmentSlot.LEFT_FINGER,
        "right_finger": EquipmentSlot.RIGHT_FINGER,
        "neck": EquipmentSlot.NECK,
        "ear1": EquipmentSlot.LEFT_EAR,
        "ear2": EquipmentSlot.RIGHT_EAR,
        "left_ear": EquipmentSlot.LEFT_EAR,
        "right_ear": EquipmentSlot.RIGHT_EAR,
        "waist": EquipmentSlot.WAIST,
        "back": EquipmentSlot.BACK,
    }
    return aliases.get(name_lower)


def resolve_skill(name: str) -> str | None:
    """Find a skill_id by case-insensitive name match."""
    from world.data.skills import SKILL_REGISTRY
    name_lower = name.lower().replace("_", " ").replace("-", " ")
    if name_lower in SKILL_REGISTRY:
        return name_lower
    for sid, defn in SKILL_REGISTRY.items():
        if defn.name.lower() == name_lower:
            return sid
    for sid, defn in SKILL_REGISTRY.items():
        if name_lower in defn.name.lower():
            return sid
    return None


def resolve_quest(name: str) -> str | None:
    """Find a quest_id by name or partial match."""
    from world.data.quests import QUEST_REGISTRY
    name_lower = name.lower().replace("_", " ").replace("-", " ")
    if name_lower in QUEST_REGISTRY:
        return name_lower
    for qid, qdef in QUEST_REGISTRY.items():
        if qdef["name"].lower() == name_lower:
            return qid
    for qid, qdef in QUEST_REGISTRY.items():
        if name_lower in qdef["name"].lower():
            return qid
    return None


def resolve_shop(name: str) -> str | None:
    """Find a shop_id by name or partial match."""
    from world.data.shops import SHOP_REGISTRY
    name_lower = name.lower().replace("_", " ").replace("-", " ")
    if name_lower in SHOP_REGISTRY:
        return name_lower
    for sid, sdef in SHOP_REGISTRY.items():
        if sdef["name"].lower() == name_lower:
            return sid
    for sid, sdef in SHOP_REGISTRY.items():
        if name_lower in sdef["name"].lower():
            return sid
    return None


def build_who_rows(characters, get_guild_name_fn, get_sect_name_fn, Faction):
    """Yield rows for the WHO table.

    Args:
        characters: list of (puppet, game) tuples.
        get_guild_name_fn: callable guild_id -> display_name | None.
        get_sect_name_fn: callable sect_id -> display_name | None.
        Faction: Faction enum (imported by caller to avoid Evennia deps).

    Returns:
        list of lists — each inner list is [Name, Lv, Race, Profession,
        Faction, Guild, Sect].
    """
    rows = []
    for _puppet, game in characters:
        # --- Name ---
        name = game.name if game.name else "Unknown"
        name = name[:14] if len(name) <= 15 else name[:13] + "."

        # --- Level ---
        lv = str(game.level)

        # --- Race ---
        race = (
            game.race_id.replace("_", " ").title()
            if game.race_id else "?"
        )
        if len(race) > 12:
            race = race[:11] + "."

        # --- Profession ---
        prof = (
            game.profession_id.replace("_", " ").title()
            if game.profession_id else "?"
        )
        if len(prof) > 12:
            prof = prof[:11] + "."

        # --- Faction ---
        if game.faction is None:
            faction = "|w\u2014|n"
        elif game.faction == Faction.GOOD:
            faction = "|bGood|n"
        else:
            faction = "|rEvil|n"

        # --- Guild ---
        if game.guild_id:
            gname = get_guild_name_fn(game.guild_id) or (
                game.guild_id.replace("_", " ").title()
            )
            if len(gname) > 14:
                gname = gname[:13] + "."
            guild = f"|m{gname}|n"
        else:
            guild = "|w\u2014|n"

        # --- Sect ---
        if game.sect_id:
            sname = get_sect_name_fn(game.sect_id) or (
                game.sect_id.replace("_", " ").title()
            )
            if len(sname) > 14:
                sname = sname[:13] + "."
            sect = f"|c{sname}|n"
        else:
            sect = "|w\u2014|n"

        rows.append([name, lv, race, prof, faction, guild, sect])

    return rows
