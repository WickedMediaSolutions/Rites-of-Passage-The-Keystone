"""
ROP Portal — Data-driven command documentation.

All command definitions are derived exclusively from the actual
command implementations in ``commands/command.py`` and their
registrations in ``commands/default_cmdsets.py``.

DO NOT add commands that are not registered in those files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CommandDoc:
    """Documentation entry for a single implemented command."""

    key: str
    aliases: List[str] = field(default_factory=list)
    category: str = "General"
    summary: str = ""
    usage: List[str] = field(default_factory=list)
    subcommands: Optional[List[str]] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Command documentation catalogue — verified against commands/command.py
# and commands/default_cmdsets.py
# ---------------------------------------------------------------------------

COMMAND_DOCS: Dict[str, CommandDoc] = {
    # ------------------------------------------------------------------
    # CHARACTER SHEET
    # ------------------------------------------------------------------
    "score": CommandDoc(
        key="score",
        aliases=["info"],
        category="Character",
        summary=(
            "Display your full character sheet including level, race, "
            "profession, faction, base stats (STR/INT/WIS/DEX/CON), "
            "HP/Mana/Stamina, XP, currency, unlocked skills, active "
            "quests, guild/sect membership, and PvP statistics."
        ),
        usage=["score", "info"],
        examples=[
            "score",
            "info",
        ],
        related=["who", "equipment", "currency", "guild", "pvp"],
    ),

    # ------------------------------------------------------------------
    # INVENTORY / EQUIPMENT
    # ------------------------------------------------------------------
    "inventory": CommandDoc(
        key="inventory",
        aliases=["inv", "i"],
        category="Items",
        summary="List all items currently in your inventory with quantities.",
        usage=["inventory", "inv", "i"],
        examples=[
            "inventory",
            "i",
        ],
        related=["equipment", "equip", "unequip", "buy", "sell"],
    ),
    "equipment": CommandDoc(
        key="equipment",
        aliases=["eq"],
        category="Items",
        summary=(
            "Display every equipment slot (Main Hand, Off Hand, Head, "
            "Chest, Legs, Hands, Feet, Wrists, Fingers, Neck, Ears, "
            "Waist, Back) and what is currently equipped in each."
        ),
        usage=["equipment", "eq"],
        examples=[
            "equipment",
            "eq",
        ],
        related=["inventory", "equip", "unequip", "score"],
    ),
    "equip": CommandDoc(
        key="equip",
        aliases=["wear"],
        category="Items",
        summary=(
            "Equip an item from your inventory into a specific equipment "
            "slot.  If no slot is given the system will try to determine "
            "the slot from the item definition."
        ),
        usage=["equip <item> [slot]", "wear <item> [slot]"],
        arguments=[
            "<item> — name or partial name of an item in your inventory",
            "[slot] — equipment slot name (main_hand, off_hand, head, "
            "chest, legs, hands, feet, wrists, left_finger, right_finger, "
            "neck, left_ear, right_ear, waist, back)",
        ],
        examples=[
            "equip rusty_sword",
            "wear iron_helm head",
            "equip ring_of_power left_finger",
        ],
        related=["unequip", "equipment", "inventory"],
    ),
    "unequip": CommandDoc(
        key="unequip",
        aliases=["remove"],
        category="Items",
        summary="Remove an equipped item and return it to your inventory.",
        usage=["unequip <item>", "remove <item>"],
        arguments=["<item> — name of an equipped item"],
        examples=[
            "unequip rusty_sword",
            "remove iron_helm",
        ],
        related=["equip", "equipment", "inventory"],
    ),

    # ------------------------------------------------------------------
    # COMBAT
    # ------------------------------------------------------------------
    "attack": CommandDoc(
        key="attack",
        aliases=["kill"],
        category="Combat",
        summary="Attack a target in the same room.",
        usage=["attack <target>", "kill <target>"],
        arguments=["<target> — name of a character or creature in your current room"],
        examples=[
            "attack goblin",
            "kill dark_knight",
        ],
        related=["use", "equip", "score"],
        notes="You must be alive to attack.  Damage is calculated based on equipped weapon and stats.",
    ),
    "use": CommandDoc(
        key="use",
        aliases=["cast"],
        category="Combat",
        summary="Use a skill or spell, optionally targeting another character.",
        usage=[
            "use <skill> [on <target>]",
            "cast <skill> [on <target>]",
        ],
        arguments=[
            "<skill> — name of a skill or spell you have unlocked",
            "[on <target>] — optional target for skills that need one",
        ],
        examples=[
            "use fireball on goblin",
            "cast heal",
            "use slash on orc",
        ],
        related=["attack", "score"],
        notes="You must be alive to use skills.  Skills consume mana or stamina depending on the skill.",
    ),

    # ------------------------------------------------------------------
    # QUESTS
    # ------------------------------------------------------------------
    "quest": CommandDoc(
        key="quest",
        aliases=[],
        category="Quests",
        summary="Manage your quests — list, accept, abandon, complete, or check status.",
        usage=[
            "quest list",
            "quest accept <quest>",
            "quest abandon <quest>",
            "quest complete <quest>",
            "quest status <quest>",
        ],
        subcommands=["list", "accept", "abandon", "complete", "status"],
        arguments=[
            "<quest> — name or partial name of a quest",
        ],
        examples=[
            "quest list",
            "quest accept the_dark_tower",
            "quest status goblin_threat",
            "quest abandon lost_artifact",
            "quest complete first_steps",
        ],
        related=["score"],
    ),

    # ------------------------------------------------------------------
    # ECONOMY
    # ------------------------------------------------------------------
    "currency": CommandDoc(
        key="currency",
        aliases=["money", "gold"],
        category="Economy",
        summary="Display your current currency balance in the game's display format and in copper.",
        usage=["currency", "money", "gold"],
        examples=[
            "currency",
            "money",
            "gold",
        ],
        related=["shop", "buy", "sell"],
    ),
    "shop": CommandDoc(
        key="shop",
        aliases=[],
        category="Economy",
        summary="Browse a shop's inventory, or list all known shops.",
        usage=["shop list", "shop <shop>"],
        arguments=["<shop> — name or partial name of a shop"],
        subcommands=["list"],
        examples=[
            "shop list",
            "shop general_store",
            "shop blacksmith",
        ],
        related=["buy", "sell", "currency"],
    ),
    "buy": CommandDoc(
        key="buy",
        aliases=[],
        category="Economy",
        summary="Purchase an item from a shop. Optionally specify a quantity.",
        usage=[
            "buy <quantity> <item> from <shop>",
            "buy <item> from <shop>",
        ],
        arguments=[
            "<quantity> — number of items to buy (default 1)",
            "<item> — name of the item to purchase",
            "<shop> — name of the shop",
        ],
        examples=[
            "buy 3 health_potion from general_store",
            "buy rusty_sword from blacksmith",
        ],
        related=["sell", "shop", "currency", "equip"],
        notes="You must have enough currency to cover the purchase.",
    ),
    "sell": CommandDoc(
        key="sell",
        aliases=[],
        category="Economy",
        summary="Sell an item from your inventory to a shop. Optionally specify a quantity.",
        usage=[
            "sell [quantity] <item> to <shop>",
        ],
        arguments=[
            "[quantity] — number of items to sell (default 1)",
            "<item> — name of the item to sell",
            "<shop> — name of the shop",
        ],
        examples=[
            "sell rusty_sword to blacksmith",
            "sell 5 iron_ore to general_store",
        ],
        related=["buy", "shop", "currency", "inventory"],
        notes="You must be alive to sell items.",
    ),

    # ------------------------------------------------------------------
    # SOCIAL / GUILD / SECT / PVP
    # ------------------------------------------------------------------
    "social": CommandDoc(
        key="social",
        aliases=["emote"],
        category="Social",
        summary=(
            "Perform a social emote, optionally directed at another "
            "character.  The target will not see the emote if you have "
            "them on your ignore list."
        ),
        usage=["social <action> [target]", "emote <action> [target]"],
        arguments=[
            "<action> — a social action name (e.g. wave, bow)",
            "[target] — optional target character",
        ],
        examples=[
            "social wave",
            "emote bow knight",
        ],
        related=["guild", "sect", "who"],
    ),
    "guild": CommandDoc(
        key="guild",
        aliases=[],
        category="Social",
        summary="View or manage your guild membership.",
        usage=[
            "guild",
            "guild info",
            "guild join <name>",
            "guild leave",
        ],
        subcommands=["join", "leave", "info"],
        arguments=["<name> — name of the guild to join"],
        examples=[
            "guild",
            "guild info",
            "guild join Shadow_Wardens",
            "guild leave",
        ],
        related=["sect", "social", "who", "score"],
    ),
    "sect": CommandDoc(
        key="sect",
        aliases=[],
        category="Social",
        summary="View or manage your sect membership.",
        usage=[
            "sect",
            "sect info",
            "sect join <name>",
            "sect leave",
        ],
        subcommands=["join", "leave", "info"],
        arguments=["<name> — name of the sect to join"],
        examples=[
            "sect",
            "sect info",
            "sect join Order_of_Flame",
            "sect leave",
        ],
        related=["guild", "social", "who", "score"],
    ),
    "pvp": CommandDoc(
        key="pvp",
        aliases=[],
        category="Combat",
        summary=(
            "Display your PvP statistics: War Points, player kills, "
            "and player deaths.  PvP eligibility is based on faction "
            "alignment and the current room's PvP mode."
        ),
        usage=["pvp"],
        examples=["pvp"],
        related=["score", "attack", "who"],
    ),

    # ------------------------------------------------------------------
    # WHO
    # ------------------------------------------------------------------
    "who": CommandDoc(
        key="who",
        aliases=["doing"],
        category="Social",
        summary=(
            "List all characters currently online in a formatted table "
            "showing name, level, race, profession, faction, guild, and "
            "sect affiliation.  Sorted by level (highest first), then "
            "alphabetically."
        ),
        usage=["who", "doing"],
        examples=[
            "who",
            "doing",
        ],
        related=["score", "guild", "sect", "pvp"],
    ),
}


# ---------------------------------------------------------------------------
# Category ordering and grouping for the command index page
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "Character",
    "Items",
    "Combat",
    "Economy",
    "Quests",
    "Social",
]


def get_commands_by_category() -> Dict[str, List[tuple]]:
    """Return commands grouped by category in display order."""
    grouped: Dict[str, List[tuple]] = {}
    for cmd_key, doc in COMMAND_DOCS.items():
        grouped.setdefault(doc.category, []).append((cmd_key, doc))
    # Sort keys in category order, unknown categories at end
    result: Dict[str, List[tuple]] = {}
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            result[cat] = grouped.pop(cat)
    for cat in sorted(grouped):
        result[cat] = grouped[cat]
    return result


def get_command(key: str) -> Optional[CommandDoc]:
    """Look up a command by key or alias."""
    key_lower = key.lower()
    # Direct key match
    if key_lower in COMMAND_DOCS:
        return COMMAND_DOCS[key_lower]
    # Alias match
    for cmd_key, doc in COMMAND_DOCS.items():
        for alias in doc.aliases:
            if alias.lower() == key_lower:
                return doc
    return None


def search_commands(query: str) -> List[tuple]:
    """Client-side-friendly search across all commands.

    Returns a list of (key, doc) where query appears in key, aliases,
    summary, or usage strings.
    """
    q = query.lower()
    results: List[tuple] = []
    for cmd_key, doc in COMMAND_DOCS.items():
        searchable = (
            cmd_key.lower() + " "
            + " ".join(a.lower() for a in doc.aliases) + " "
            + doc.summary.lower() + " "
            + " ".join(u.lower() for u in doc.usage) + " "
            + " ".join(s.lower() for s in (doc.subcommands or []))
        )
        if q in searchable:
            results.append((cmd_key, doc))
    return results
