"""
Rites of Passage — Enums

Centralised enumeration types used throughout the game.  Using string-based
enums ensures serialisability and readability in database attributes.
"""

from enum import Enum


class Faction(Enum):
    """Player / NPC faction alignment."""

    GOOD = "good"
    EVIL = "evil"


class DamageType(Enum):
    """Every attack, skill, spell, and DOT must specify a damage type."""

    # Physical
    PIERCING = "piercing"
    SLASHING = "slashing"
    CONCUSSION = "concussion"
    WHIPPING = "whipping"

    # Elemental
    AIR = "air"
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"

    # Special
    POISON = "poison"
    DISEASE = "disease"
    HOLY = "holy"
    UNHOLY = "unholy"
    PSYCHIC = "psychic"
    BLEED = "bleed"


class CharacterState(Enum):
    """High-level character activity state used by regeneration and combat."""

    STANDING = "standing"
    RESTING = "resting"
    MEDITATING = "meditating"
    COMBAT = "combating"
    DEAD = "dead"


class EquipmentSlot(Enum):
    """Named equipment slots (order matches the spec)."""

    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    HANDS = "hands"
    FEET = "feet"
    WRISTS = "wrists"
    LEFT_FINGER = "left_finger"
    RIGHT_FINGER = "right_finger"
    NECK = "neck"
    LEFT_EAR = "left_ear"
    RIGHT_EAR = "right_ear"
    WAIST = "waist"
    BACK = "back"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"


class PvPMode(Enum):
    """Area-level PvP behaviour."""

    SAFE = "safe"
    CONTESTED = "contested"
    ARENA = "arena"
    FREE_FOR_ALL = "free_for_all"


class CorpseState(Enum):
    """Track what has been done to a corpse."""

    FRESH = "fresh"            # normal loot available
    LOOTED = "looted"          # normal currency/items taken
    BUTCHERED = "butchered"    # butcher used
    EXTRACTED = "extracted"    # extraction used
    SACRIFICED = "sacrificed"  # corpse destroyed


class Stat(Enum):
    """Core character stats."""

    STRENGTH = "strength"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"


class Resource(Enum):
    """Character resource pools."""

    HP = "hp"
    MANA = "mana"
    STAMINA = "stamina"


class SkillCategory(Enum):
    """Broad classification for skill data organisation."""

    UNIVERSAL = "universal"
    PROFESSION = "profession"
    WEAPON = "weapon"


class WeatherCondition(Enum):
    """Regional weather states."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    FOG = "fog"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    WIND = "wind"
    HEAVY_WIND = "heavy_wind"
    LIGHT_SNOW = "light_snow"
    SNOW = "snow"
    HEAVY_SNOW = "heavy_snow"
    BLIZZARD = "blizzard"


class Season(Enum):
    """Game calendar seasons."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class TimeOfDay(Enum):
    """Day period."""

    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


class QuestState(Enum):
    """Per-character quest progression state."""

    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    LOCKED = "locked"


class StackPolicy(Enum):
    """How a status effect handles re-application."""

    REFRESH = "refresh"              # extends duration
    STACK = "stack"                  # increase intensity (up to max)
    INDEPENDENT = "independent"      # separate instances


# ---------------------------------------------------------------------------
# Derived helper mappings
# ---------------------------------------------------------------------------

PHYSICAL_DAMAGE_TYPES = frozenset({
    DamageType.PIERCING,
    DamageType.SLASHING,
    DamageType.CONCUSSION,
    DamageType.WHIPPING,
})

ELEMENTAL_DAMAGE_TYPES = frozenset({
    DamageType.AIR,
    DamageType.FIRE,
    DamageType.WATER,
    DamageType.EARTH,
})

SPECIAL_DAMAGE_TYPES = frozenset({
    DamageType.POISON,
    DamageType.DISEASE,
    DamageType.HOLY,
    DamageType.UNHOLY,
    DamageType.PSYCHIC,
    DamageType.BLEED,
})