"""
Rites of Passage — Race Definitions

24 races (12 Good, 12 Evil). Each race defines faction, base stats, stat
limits (hard caps at 10% above listed), and inherent trait tags.
"""

from world.data.enums import Faction

# ---------------------------------------------------------------------------
# Race catalogue — race_id -> definition
# ---------------------------------------------------------------------------

RACES = {

    # =====================================================================
    # GOOD RACES
    # =====================================================================

    "human": {
        "name": "Human",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 25, "int": 25, "wis": 25, "dex": 25, "con": 25},
        "stat_limits": {"str": 25, "int": 25, "wis": 25, "dex": 25, "con": 25},
        "traits": [],
    },

    "stone_giant": {
        "name": "Stone-Giant",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 30, "int": 20, "wis": 20, "dex": 24, "con": 30},
        "stat_limits": {"str": 30, "int": 20, "wis": 20, "dex": 24, "con": 30},
        "traits": ["stone_skin"],
    },

    "azer": {
        "name": "Azer",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 28, "int": 21, "wis": 21, "dex": 26, "con": 28},
        "stat_limits": {"str": 28, "int": 21, "wis": 21, "dex": 26, "con": 28},
        "traits": ["fire_resistance", "enhanced_energy_regen"],
    },

    "dwarf": {
        "name": "Dwarf",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 28, "int": 20, "wis": 27, "dex": 20, "con": 29},
        "stat_limits": {"str": 28, "int": 20, "wis": 27, "dex": 20, "con": 29},
        "traits": ["tough_skin", "poison_resistance"],
    },

    "atomie": {
        "name": "Atomie",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 24, "int": 21, "wis": 23, "dex": 30, "con": 26},
        "stat_limits": {"str": 24, "int": 21, "wis": 23, "dex": 30, "con": 26},
        "traits": ["enhanced_energy_regen"],
    },

    "wild_elf": {
        "name": "Wild-Elf",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 25, "int": 27, "wis": 20, "dex": 28, "con": 24},
        "stat_limits": {"str": 25, "int": 27, "wis": 20, "dex": 28, "con": 24},
        "traits": ["night_vision", "enhanced_energy_regen"],
    },

    "dryad": {
        "name": "Dryad",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 20, "int": 30, "wis": 27, "dex": 28, "con": 19},
        "stat_limits": {"str": 20, "int": 30, "wis": 27, "dex": 28, "con": 19},
        "traits": ["holy_protection"],
    },

    "high_elf": {
        "name": "High-Elf",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 20, "int": 29, "wis": 28, "dex": 26, "con": 21},
        "stat_limits": {"str": 20, "int": 29, "wis": 28, "dex": 26, "con": 21},
        "traits": ["night_vision"],
    },

    "dragonkin": {
        "name": "Dragonkin",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 26, "int": 25, "wis": 27, "dex": 20, "con": 26},
        "stat_limits": {"str": 26, "int": 25, "wis": 27, "dex": 20, "con": 26},
        "traits": ["flight", "scaled_skin"],
    },

    "svirfneblin": {
        "name": "Svirfneblin",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 22, "int": 25, "wis": 30, "dex": 23, "con": 24},
        "stat_limits": {"str": 22, "int": 25, "wis": 30, "dex": 23, "con": 24},
        "traits": ["plague_immunity"],
    },

    "centaur": {
        "name": "Centaur",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 28, "int": 27, "wis": 23, "dex": 19, "con": 27},
        "stat_limits": {"str": 28, "int": 27, "wis": 23, "dex": 19, "con": 27},
        "traits": ["conditioned_flesh", "swift_regen"],
    },

    "halfling": {
        "name": "Halfling",
        "description": "",
        "faction": Faction.GOOD,
        "base_stats": {"str": 26, "int": 24, "wis": 20, "dex": 29, "con": 25},
        "stat_limits": {"str": 26, "int": 24, "wis": 20, "dex": 29, "con": 25},
        "traits": ["night_vision"],
    },

    # =====================================================================
    # EVIL RACES
    # =====================================================================

    "troll": {
        "name": "Troll",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 30, "int": 19, "wis": 19, "dex": 26, "con": 30},
        "stat_limits": {"str": 30, "int": 19, "wis": 19, "dex": 26, "con": 30},
        "traits": ["regeneration", "rubbery_hide"],
    },

    "ogre": {
        "name": "Ogre",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 29, "int": 18, "wis": 27, "dex": 22, "con": 28},
        "stat_limits": {"str": 29, "int": 18, "wis": 27, "dex": 22, "con": 28},
        "traits": ["thick_skin"],
    },

    "duergar": {
        "name": "Duergar",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 28, "int": 23, "wis": 21, "dex": 24, "con": 28},
        "stat_limits": {"str": 28, "int": 23, "wis": 21, "dex": 24, "con": 28},
        "traits": ["conditioned_skin", "poison_resistance"],
    },

    "orc": {
        "name": "Orc",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 27, "int": 22, "wis": 20, "dex": 28, "con": 27},
        "stat_limits": {"str": 27, "int": 22, "wis": 20, "dex": 28, "con": 27},
        "traits": ["thick_skin", "quick_recovery"],
    },

    "skaven": {
        "name": "Skaven",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 26, "int": 26, "wis": 18, "dex": 29, "con": 25},
        "stat_limits": {"str": 26, "int": 26, "wis": 18, "dex": 29, "con": 25},
        "traits": ["poison_resistance", "enhanced_energy_regen"],
    },

    "illithid": {
        "name": "Illithid",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 21, "int": 30, "wis": 28, "dex": 26, "con": 19},
        "stat_limits": {"str": 21, "int": 30, "wis": 28, "dex": 26, "con": 19},
        "traits": ["enhanced_energy_regen"],
    },

    "drow": {
        "name": "Drow",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 21, "int": 29, "wis": 27, "dex": 26, "con": 21},
        "stat_limits": {"str": 21, "int": 29, "wis": 27, "dex": 26, "con": 21},
        "traits": ["night_vision"],
    },

    "lich": {
        "name": "Lich",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 21, "int": 27, "wis": 30, "dex": 22, "con": 24},
        "stat_limits": {"str": 21, "int": 27, "wis": 30, "dex": 22, "con": 24},
        "traits": ["unholy_protection"],
    },

    "kenku": {
        "name": "Kenku",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 25, "int": 26, "wis": 26, "dex": 21, "con": 26},
        "stat_limits": {"str": 25, "int": 26, "wis": 26, "dex": 21, "con": 26},
        "traits": ["flight"],
    },

    "revenant": {
        "name": "Revenant",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 23, "int": 24, "wis": 28, "dex": 22, "con": 27},
        "stat_limits": {"str": 23, "int": 24, "wis": 28, "dex": 22, "con": 27},
        "traits": ["night_vision", "disease_immunity"],
    },

    "minotaur": {
        "name": "Minotaur",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 29, "int": 26, "wis": 19, "dex": 22, "con": 28},
        "stat_limits": {"str": 29, "int": 26, "wis": 19, "dex": 22, "con": 28},
        "traits": ["hairy_hide", "quick_recovery"],
    },

    "goblin": {
        "name": "Goblin",
        "description": "",
        "faction": Faction.EVIL,
        "base_stats": {"str": 26, "int": 21, "wis": 21, "dex": 30, "con": 26},
        "stat_limits": {"str": 26, "int": 21, "wis": 21, "dex": 30, "con": 26},
        "traits": ["enhanced_energy_regen", "disease_immunity"],
    },
}

def update_species_metadata(species_id, name=None, description=None):
    """Update display metadata for an existing race entry.

    Preserves all gameplay data (faction, base_stats, stat_limits, traits).
    Only updates name and/or description when non-None values are provided.
    Returns True if the species_id exists and was updated, False otherwise.
    """
    if species_id not in RACES:
        return False

    race = RACES[species_id]

    if name is not None:
        race["name"] = name
    if description is not None:
        race["description"] = description

    return True

# Trait tags — referenced by race data.  Actual mechanical effects are
# applied by the combat/stat/resistance systems when a character has the
# corresponding trait tag.
# Values deferred until gameplay systems are wired up.
