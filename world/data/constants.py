"""
Rites of Passage — Game Constants

All tunable game constants live here.  No value is treated as final balance;
every constant is explicitly configurable for playtesting.

Do NOT duplicate these values in individual commands or typeclasses.
"""

# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------
COMBAT_ROUND_SECONDS = 5                # duration of one combat round
# ---------------------------------------------------------------------------
# Resource Regeneration  [PLACEHOLDER VALUES — NOT final balance]
# ---------------------------------------------------------------------------
REGENERATION_TICK_SECONDS = 30          # 6 combat rounds per regen tick

# Amount regenerated per tick for each resource.  These are DEVELOPMENT
# PLACEHOLDERS pending final game-design tuning.
REGEN_HP_PER_TICK = 5      # [PLACEHOLDER] HP recovered per regeneration tick
REGEN_MANA_PER_TICK = 5    # [PLACEHOLDER] Mana recovered per regeneration tick
REGEN_STAMINA_PER_TICK = 5 # [PLACEHOLDER] Stamina recovered per regeneration tick
REST_ACTIVATION_DELAY_SECONDS = 20      # rest / meditation activation delay
BASE_HIT_CHANCE = 75                    # pre-modifier hit chance (%)
MIN_HIT_CHANCE = 5                      # minimum normal hit chance (%)
MAX_HIT_CHANCE = 95                     # maximum normal hit chance (%)
MINIMUM_DAMAGE = 1                      # floor for successful damaging hits

# ---------------------------------------------------------------------------
# Level / Progression
# ---------------------------------------------------------------------------
MAX_LEVEL = 100
GROUP_XP_MAX_LEVEL_DIFF = 10
BASE_ATTACKS_PER_ROUND = 1
SECOND_ATTACK_LEVEL = 20
THIRD_ATTACK_LEVEL = 56

# ---------------------------------------------------------------------------
# Death / Respawn
# ---------------------------------------------------------------------------
DEATH_XP_PENALTY_PERCENT = 5
RESPAWN_HP_PERCENT = 50
RESPAWN_MANA_PERCENT = 50
RESPAWN_STAMINA_PERCENT = 50

# ---------------------------------------------------------------------------
# Character Creation
# ---------------------------------------------------------------------------
STARTING_LEVEL = 1
STARTING_STAT_VARIANCE = 2
# ---------------------------------------------------------------------------
# Rest / Meditation
# ---------------------------------------------------------------------------
MEDITATION_MANA_MULTIPLIER = 2          # multiplier on resting mana regen

# ---------------------------------------------------------------------------
# Concentration
# ---------------------------------------------------------------------------
CONCENTRATION_INTERRUPT_MANA_FRACTION = 0.5  # mana cost when interrupted

# ---------------------------------------------------------------------------
# Siphone Life / Life Drain
# ---------------------------------------------------------------------------
SIPHON_LIFE_HEAL_FRACTION = 0.5          # fraction of damage healed

# ---------------------------------------------------------------------------
# Buff Durations (seconds) — defaults, may be overridden per ability
# ---------------------------------------------------------------------------
DEFAULT_SHARPEN_DURATION = 600           # 10 minutes
DEFAULT_PRAYER_DURATION = 300           #  5 minutes
DEFAULT_PSYCHIC_BLADE_DURATION = 300    #  5 minutes

# ---------------------------------------------------------------------------
# Status Effects
# ---------------------------------------------------------------------------
DEFAULT_STUN_DURATION = 5               # seconds
DEFAULT_DOT_TICK = 5                    # seconds

# ---------------------------------------------------------------------------
# Currency (base values in copper)
# ---------------------------------------------------------------------------
COPPER = 1
SILVER = 100
GOLD = 10_000
PLATINUM = 1_000_000
DIRTY_SHECKLE = 1_000_000_000

# ---------------------------------------------------------------------------
# Corpse
# ---------------------------------------------------------------------------
SACRIFICE_GOLD_REWARD = 1               # gold per sacrificed valid mob corpse

# ---------------------------------------------------------------------------
# Weather / Game Time
# ---------------------------------------------------------------------------
SECONDS_PER_GAME_HOUR = 150             # 2.5 real min per game hour
SECONDS_PER_GAME_DAY = SECONDS_PER_GAME_HOUR * 24  # 3600s = 1 real hr per game day

# ---------------------------------------------------------------------------
# Directional Abbreviations (core)
# ---------------------------------------------------------------------------
# Maps full direction names to their abbreviation aliases so that players
# can use "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d" instead of
# typing the full direction name.
DIRECTION_ABBREVIATIONS: dict[str, list[str]] = {
    "north":     ["n"],
    "south":     ["s"],
    "east":      ["e"],
    "west":      ["w"],
    "northeast": ["ne"],
    "northwest": ["nw"],
    "southeast": ["se"],
    "southwest": ["sw"],
    "up":        ["u"],
    "down":      ["d"],
}
# ---------------------------------------------------------------------------
# Tutorial / Spawn tags
# ---------------------------------------------------------------------------
TUTORIAL_GOOD_START = "good_tutorial_start"
TUTORIAL_EVIL_START = "evil_tutorial_start"
TUTORIAL_GOOD_RESPAWN = "good_tutorial_respawn"
TUTORIAL_EVIL_RESPAWN = "evil_tutorial_respawn"
TOWN_GOOD_START = "good_start"
TOWN_EVIL_START = "evil_start"

# ---------------------------------------------------------------------------
# Groups / PvP
# ---------------------------------------------------------------------------
MAX_GROUP_SIZE = 6
WAR_POINTS_PER_KILL = 1
# ============================== TEMPORARY VALUES ==============================
# The constants in this block are DEVELOPMENT PLACEHOLDERS, NOT final balance.
# They will be replaced with approved game-design values during playtesting.
# Architecture is complete; only the numbers are provisional.
# =============================================================================

# XP curve coefficient — XP for level N = COEFF * (N-1)^2  [PLACEHOLDER]
XP_CURVE_COEFF = 100

# Default starting proficiency for weapon skills.  [PLACEHOLDER]
DEFAULT_WEAPON_PROFICIENCY = 1

# Resource gains per level are now data-driven from profession definitions
# (see PROFESSIONS[prof_id]["resource_gains"]).  The values below are
# fallback defaults only — replace when profession data is finalised.

# Default HP / Mana / Stamina gain per level — per-archetype fallbacks.
DEFAULT_HP_PER_LEVEL = 8
DEFAULT_MANA_PER_LEVEL = 5
DEFAULT_STAMINA_PER_LEVEL = 7
MAX_STAT_REROLLS = 3

def get_resource_gains(profession_id: str) -> tuple[int, int, int]:
    """
    Return (hp_per_level, mana_per_level, stamina_per_level) for a
    profession.  Sources profession data first; falls back to defaults.

    ALL VALUES ARE TEMPORARY PLACEHOLDERS pending final balancing.
    """
    from world.data.professions import PROFESSIONS
    prof = PROFESSIONS.get(profession_id, {})
    gains = prof.get("resource_gains")
    if gains is not None and len(gains) == 3:
        return tuple(gains)
    return (DEFAULT_HP_PER_LEVEL, DEFAULT_MANA_PER_LEVEL, DEFAULT_STAMINA_PER_LEVEL)
