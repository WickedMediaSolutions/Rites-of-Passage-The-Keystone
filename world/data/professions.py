"""
Rites of Passage — Profession Definitions

Data-driven profession tables keyed by level. The progression engine reads
these to auto-grant skills/spells when a character reaches the required level.

Each profession now includes:
  resource_gains = (hp_per_level, mana_per_level, stamina_per_level)

ALL RESOURCE VALUES ARE TEMPORARY PLACEHOLDERS pending final balancing.
"""

from world.data.enums import Stat

PROFESSIONS = {

    # =====================================================================
    # MAGE — Intelligence-based arcane caster
    # =====================================================================
    "mage": {
        "name": "Mage",
        "mana_stat": Stat.INTELLIGENCE,
        "resource_gains": (5, 10, 5),   # [PLACEHOLDER]
        "skills": {
            13: ["dodge"],
            15: ["concentration"],
            25: ["vortex"],
            27: ["meditation"],
            30: ["flamestrike"],
            32: ["entangle"],
            33: ["enlarge"],
            35: ["whirlwind"],
            39: ["acid_blast"],
            40: ["blink", "invisibility"],
            41: ["fireball"],
            46: ["searing_orb"],
            50: ["frost_lance"],
            51: ["feeblemind"],
            52: ["winds_of_chaos"],
            56: ["teleport"],
            60: ["thunderbolt"],
            66: ["avalanche"],
            68: ["falling_star"],
        },
    },

    # =====================================================================
    # WARLOCK — Intelligence-based dark caster
    # =====================================================================
    "warlock": {
        "name": "Warlock",
        "mana_stat": Stat.INTELLIGENCE,
        "resource_gains": (7, 6, 8),    # [PLACEHOLDER]
        "skills": {
            13: ["dodge"],
            15: ["concentration"],
            20: ["siphon_life"],
            21: ["enrage"],
            22: ["whip_lash"],
            27: ["meditation"],
            32: ["entangle"],
            33: ["vampiric_touch"],
            38: ["fire_shield"],
            40: ["enhanced_damage"],
            41: ["black_tentacles"],
            50: ["flame_blade"],
            51: ["feeblemind"],
            55: ["black_mantle", "agony"],
            61: ["life_drain"],
            66: ["soul_harvest"],
        },
    },

    # =====================================================================
    # WARRIOR — pure melee, no mana stat
    # =====================================================================
    "warrior": {
        "name": "Warrior",
        "mana_stat": None,
        "resource_gains": (10, 2, 10),   # [PLACEHOLDER]
        "skills": {
            7:  ["kick"],
            10: ["bash"],
            12: ["parry"],
            15: ["rescue"],
            25: ["elbow"],
            27: ["disarm"],
            31: ["armor_penetration"],
            35: ["shield_block"],
            40: ["enhanced_damage"],
            42: ["endurance"],
            45: ["pummel"],
            50: ["sharpen"],
            56: ["third_attack"],
            60: ["dual_wield"],
            65: ["riposte", "shield_rush"],
        },
    },

    # =====================================================================
    # CLERIC — Wisdom-based divine caster
    # =====================================================================
    "cleric": {
        "name": "Cleric",
        "mana_stat": Stat.WISDOM,
        "resource_gains": (5, 10, 5),    # [PLACEHOLDER]
        "skills": {
            15: ["concentration"],
            21: ["holy_ward"],
            23: ["barrier"],
            25: ["turn_undead"],
            27: ["heal_critical", "meditation"],
            30: ["restore_voice"],
            35: ["dispel"],
            37: ["bless"],
            38: ["stone_skin"],
            41: ["healing"],
            45: ["sanctuary"],
            52: ["disease_spell"],
            57: ["divine_favor"],
            58: ["entropy_shield"],
            60: ["essence_of_spirit"],
            65: ["holy_light"],
            66: ["mass_healing"],
        },
    },

    # =====================================================================
    # THIEF — Dexterity-based rogue
    # =====================================================================
    "thief": {
        "name": "Thief",
        "mana_stat": None,
        "resource_gains": (8, 3, 9),     # [PLACEHOLDER]
        "skills": {
            5:  ["sneak"],
            7:  ["backstab", "kick"],
            12: ["hide"],
            13: ["dodge"],
            15: ["locksmithy"],
            18: ["coat", "poison_lore"],
            20: ["investigation"],
            28: ["peek"],
            30: ["stealth"],
            31: ["armor_penetration"],
            35: ["circle"],
            40: ["advanced_tracking"],
            45: ["set_trap"],
            56: ["tumbling"],
            60: ["group_stealth", "dual_daggers"],
        },
    },

    # =====================================================================
    # TEMPLAR — Strength/Wisdom hybrid
    # =====================================================================
    "templar": {
        "name": "Templar",
        "mana_stat": Stat.WISDOM,
        "resource_gains": (8, 6, 8),     # [PLACEHOLDER]
        "skills": {
            12: ["parry"],
            15: ["prayer", "rescue"],
            21: ["holy_ward"],
            23: ["barrier"],
            25: ["leadership"],
            29: ["guard"],
            31: ["armor_penetration"],
            35: ["shield_block", "dispel"],
            37: ["self_healing"],
            40: ["enhanced_damage"],
            45: ["pummel"],
            50: ["grapple"],
            53: ["righteousness"],
            60: ["battle_tactics"],
            65: ["summon"],
        },
    },

    # =====================================================================
    # MONK — Strength/Dexterity hybrid, Wisdom-based mana
    # =====================================================================
    "monk": {
        "name": "Monk",
        "mana_stat": Stat.WISDOM,
        "resource_gains": (8, 6, 10),    # [PLACEHOLDER]
        "skills": {
            1:  ["martial_arts"],
            7:  ["kick"],
            13: ["dodge"],
            15: ["rescue"],
            20: ["second_punch"],
            23: ["barrier"],
            25: ["elbow"],
            27: ["meditation"],
            33: ["stun"],
            35: ["psionic_blast"],
            39: ["haste"],
            40: ["body_control"],
            45: ["displacement"],
            48: ["enhanced_kick"],
            51: ["iron_skin"],
            55: ["psychic_blade"],
            60: ["fists_of_speed"],
            66: ["system_purge"],
        },
    },

    # =====================================================================
    # ALCHEMIST — Intelligence-based crafter
    # =====================================================================
    "alchemist": {
        "name": "Alchemist",
        "mana_stat": Stat.INTELLIGENCE,
        "resource_gains": (6, 7, 6),     # [PLACEHOLDER]
        "skills": {
            13: ["dodge"],
            15: ["concentration"],
            18: ["mix", "potion_lore"],
            25: ["vortex"],
            27: ["meditation"],
            30: ["flamestrike"],
            32: ["entangle"],
            35: ["whirlwind"],
            36: ["identify"],
            39: ["acid_blast"],
            41: ["fireball"],
            43: ["spellshield"],
            46: ["searing_orb"],
            56: ["teleport"],
        },
    },

    # =====================================================================
    # NINJA — Dexterity-based assassin
    # =====================================================================
    "ninja": {
        "name": "Ninja",
        "mana_stat": None,
        "resource_gains": (7, 2, 10),    # [PLACEHOLDER]
        "skills": {
            5:  ["sneak"],
            7:  ["backstab", "kick"],
            12: ["hide"],
            13: ["dodge"],
            15: ["locksmithy"],
            30: ["stealth"],
            31: ["armor_penetration"],
            35: ["circle"],
            40: ["retreat"],
            45: ["evasive_attack"],
            47: ["eye_gouge"],
            49: ["strangle"],
            50: ["enhanced_backstab"],
            56: ["enhanced_circle"],
            60: ["dual_daggers"],
            65: ["vital_strike"],
        },
    },

    # =====================================================================
    # DRUID — Wisdom/Intelligence nature caster
    # =====================================================================
    "druid": {
        "name": "Druid",
        "mana_stat": Stat.WISDOM,
        "resource_gains": (6, 8, 7),     # [PLACEHOLDER]
        "skills": {
            13: ["dodge"],
            15: ["concentration"],
            23: ["thorn_shield"],
            25: ["vortex"],
            27: ["heal_critical", "meditation"],
            30: ["barkskin"],
            32: ["entangle"],
            35: ["touch_of_gaia", "whirlwind"],
            38: ["earthen_hammer"],
            41: ["healing"],
            45: ["waters_of_grove"],
            48: ["wrath_of_nature"],
            52: ["seed_of_grove"],
            58: ["primal_roar"],
            63: ["mass_refresh"],
            68: ["creeping_doom"],
        },
    },
}


# ---------------------------------------------------------------------------
# Profession Registry — extensible profession identity store.
#
# Seeded from the built-in PROFESSIONS dict above and supports custom
# (non-built-in) profession IDs registered at runtime (e.g. from Forge).
# ---------------------------------------------------------------------------

PROFESSION_REGISTRY: dict[str, dict] = {}

# Seed from every existing built-in profession.
_BUILTIN_PROFESSION_NAMES = {
    "mage": "Mage",
    "warlock": "Warlock",
    "warrior": "Warrior",
    "cleric": "Cleric",
    "thief": "Thief",
    "templar": "Templar",
    "monk": "Monk",
    "alchemist": "Alchemist",
    "ninja": "Ninja",
    "druid": "Druid",
}

for _prof_id in PROFESSIONS:
    PROFESSION_REGISTRY[_prof_id] = {
        "id": _prof_id,
        "name": _BUILTIN_PROFESSION_NAMES.get(_prof_id, _prof_id.title()),
        "description": "",
    }


def register_profession(profession_id: str, name: str, description: str = "") -> None:
    """Create or update a profession entry in PROFESSION_REGISTRY.

    When ``profession_id`` already exists, only *name* and *description* are
    overwritten — all other existing fields are left untouched.  This allows
    custom Forge profession IDs that are not members of the built-in set.
    """
    if profession_id in PROFESSION_REGISTRY:
        PROFESSION_REGISTRY[profession_id]["name"] = name
        PROFESSION_REGISTRY[profession_id]["description"] = description
        return

    PROFESSION_REGISTRY[profession_id] = {
        "id": profession_id,
        "name": name,
        "description": description,
    }


def get_profession(profession_id: str) -> dict:
    """Return the profession definition dict for *profession_id*.

    Raises :exc:`KeyError` when the profession is not in the registry.
    """
    return PROFESSION_REGISTRY[profession_id]


def profession_exists(profession_id: str) -> bool:
    """Return ``True`` if *profession_id* is registered."""
    return profession_id in PROFESSION_REGISTRY


# ---------------------------------------------------------------------------
# Universal skills — automatically granted to every profession at the
# specified level.
# ---------------------------------------------------------------------------

UNIVERSAL_SKILLS = {
    1:  ["piercing_weapons", "slashing_weapons", "concussion_weapons",
         "whipping_weapons"],
    3:  ["searching"],
    5:  ["swim"],
    9:  ["butcher"],
    10: ["extraction"],
    20: ["tracking", "second_attack", "haggle"],
    30: ["tinker"],
}


# ---------------------------------------------------------------------------
# All 4 universal weapon proficiencies (granted at level 1 universally).
# ---------------------------------------------------------------------------

WEAPON_SKILLS = [
    "piercing_weapons",
    "slashing_weapons",
    "concussion_weapons",
    "whipping_weapons",
]
