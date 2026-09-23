"""
Rites of Passage — Combat Resolution

Centralised combat logic for attack resolution, hit/miss determination,
physical damage calculation, and combat-state management.

This module is plain Python — no Evennia imports — so it can be
unit-tested without a running server.  The Evennia-side command layer
will call ``resolve_attack()`` here with two ``CharacterData`` instances.

Design constraints (Phase 5 foundation only):
    • No NPC AI
    • No automatic combat rounds/tickers
    • No skills / spells / buffs / debuffs / status effects
    • No loot / XP rewards / mob respawning / PvP rewards
    • No advanced weapon effects
"""

import random

from world.data.constants import (
    BASE_HIT_CHANCE,
    MIN_HIT_CHANCE,
    MAX_HIT_CHANCE,
    MINIMUM_DAMAGE,
)
from world.data.enums import CharacterState, DamageType, EquipmentSlot, PHYSICAL_DAMAGE_TYPES
from world.data.items import get_weapon_damage, get_weapon_damage_type, get_armor_class

# ---------------------------------------------------------------------------
# Damage calculation [PLACEHOLDER] — NOT final balance
# ---------------------------------------------------------------------------

# Base damage for a successful physical attack. [PLACEHOLDER]
BASE_DAMAGE = 10

# Base damage for an unarmed attack (no weapon equipped). [PLACEHOLDER]
UNARMED_DAMAGE = 5

# Fraction of attacker's strength added to physical damage. [PLACEHOLDER]
STR_DAMAGE_MULTIPLIER = 0.5

# Armor mitigation formula: direct flat reduction per point of armor_class. [PLACEHOLDER]
#   mitigated = max(MINIMUM_DAMAGE, raw_damage - total_armor)
# This is the simplest possible formula; will be replaced with percentage-based
# or diminishing-returns formulas during balancing.
ARMOR_MITIGATION_PER_POINT = 1  # [PLACEHOLDER] 1:1 flat reduction

# ---------------------------------------------------------------------------
# Hit calculation
# ---------------------------------------------------------------------------


def _get_mob_combat_info(cd: "CharacterData") -> dict:
    """Extract combat properties for a mob CharacterData.

    Returns an empty dict for non-mob characters (players).
    """
    if cd.race_id != "mob":
        return {}
    from world.data.mobs import get_mob_definition
    definition = get_mob_definition(cd.profession_id)
    if definition is None:
        return {}
    return definition.get("mw_combat", {})


def _clamp_hit_chance(chance: int) -> int:
    """Clamp a hit chance into [MIN_HIT_CHANCE .. MAX_HIT_CHANCE]."""
    return max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, chance))


def roll_hit(attacker_cd: "CharacterData",
             target_cd: "CharacterData") -> bool:
    """
    Determine whether a physical attack lands.

    Uses BASE_HIT_CHANCE (75 %) as the baseline.  Target dodge
    modifiers reduce hit chance (e.g. Dodge +40 -> -40 to hit chance).
    """
    hit_chance = BASE_HIT_CHANCE

    # Apply target dodge modifier (mobs only).
    target_combat = _get_mob_combat_info(target_cd)
    dodge = target_combat.get("dodge_modifier", 0)
    hit_chance -= dodge

    hit_chance = _clamp_hit_chance(hit_chance)
    roll = random.randint(1, 100)
    return roll <= hit_chance


# ---------------------------------------------------------------------------
# Damage calculation
# ---------------------------------------------------------------------------


def calculate_physical_damage(
    attacker_cd: "CharacterData",
    target_cd: "CharacterData",
    damage_type: DamageType | str = DamageType.SLASHING,
) -> int:
    """
    Calculate physical damage for a successful hit, incorporating
    equipped weapon damage, target armor, damage reduction (DR),
    and elemental resistances.

    Formula:
        weapon_damage = equipped MAIN_HAND base_damage, or UNARMED_DAMAGE
        raw = weapon_damage + STR * STR_DAMAGE_MULTIPLIER
        total_armor = equipped armor_class + mob definition AC
        after_ac = max(MINIMUM_DAMAGE, raw - total_armor * ARMOR_MITIGATION_PER_POINT)
        after_dr = max(MINIMUM_DAMAGE, after_ac - mob_dr)
        final = after_dr * (1.0 - resistance_pct / 100.0)
    """
    # Validate / coerce damage_type.
    if isinstance(damage_type, str):
        try:
            damage_type = DamageType(damage_type)
        except ValueError:
            pass  # keep the custom string as-is
    elif isinstance(damage_type, DamageType) and damage_type not in PHYSICAL_DAMAGE_TYPES:
        damage_type = DamageType.SLASHING

    # ---- Weapon damage ------------------------------------------------
    weapon_id = attacker_cd.equipment.get(EquipmentSlot.MAIN_HAND)
    weapon_damage = UNARMED_DAMAGE  # default unarmed

    if weapon_id is not None:
        wd = get_weapon_damage(weapon_id)
        if wd > 0:
            weapon_damage = wd
        wt = get_weapon_damage_type(weapon_id)
        if wt is not None:
            damage_type = wt

    # ---- Strength bonus -----------------------------------------------
    strength = attacker_cd.base_stats.get("str", 0)
    raw = weapon_damage + int(strength * STR_DAMAGE_MULTIPLIER)

    # ---- Armor mitigation ---------------------------------------------
    total_armor = _calculate_total_armor(target_cd)
    mitigated = raw - total_armor * ARMOR_MITIGATION_PER_POINT

    # ---- Mob Damage Reduction (DR) ------------------------------------
    combat_info = _get_mob_combat_info(target_cd)
    mob_dr = 0
    if combat_info:
        from world.data.mobs import get_mob_definition
        definition = get_mob_definition(target_cd.profession_id)
        if definition:
            mob_dr = definition.get("damage_reduction", 0) or 0
            if isinstance(mob_dr, (int, float)):
                mob_dr = int(mob_dr)
            else:
                mob_dr = 0
    mitigated = max(MINIMUM_DAMAGE, mitigated - mob_dr)

    # ---- Elemental / damage-type resistances --------------------------
    # Map ROP DamageType to resistance element name used in combat info.
    _type_to_element = {
        "fire": "fire",
        "air": "air",
        "water": "water",
        "earth": "earth",
        "piercing": None,
        "slashing": None,
        "concussion": None,
        "whipping": None,
        "poison": None,
    }
    dt_value = damage_type.value if isinstance(damage_type, DamageType) else damage_type
    element = _type_to_element.get(dt_value, None)
    if element and combat_info:
        res_pct = combat_info.get("elemental_resistances", {}).get(element, 0)
        if isinstance(res_pct, (int, float)):
            mitigated = int(mitigated * (1.0 - res_pct / 100.0))

    return max(MINIMUM_DAMAGE, mitigated)


def calculate_skill_damage(
    base_damage: int,
    damage_type: DamageType,
    target_cd: "CharacterData",
) -> int:
    """Calculate skill damage incorporating mob elemental resistances.

    Does NOT use calculate_physical_damage() — no weapon/strength/armor
    logic is applied.  Only the mob's elemental_resistances are consulted.

    Returns at least 1 damage.
    """
    damage = base_damage

    # Coerce string damage_type to enum when possible.
    if isinstance(damage_type, str):
        try:
            damage_type = DamageType(damage_type)
        except ValueError:
            pass  # unknown type — proceed with raw base_damage

    combat_info = _get_mob_combat_info(target_cd)
    if combat_info and isinstance(damage_type, DamageType):
        resistances = combat_info.get("elemental_resistances", {})
        res_pct = resistances.get(damage_type.value, 0)
        if isinstance(res_pct, (int, float)) and res_pct != 0:
            damage = int(damage * (1.0 - res_pct / 100.0))

    return max(1, damage)


# ---- Armor helpers -------------------------------------------------------


def _calculate_total_armor(cd: "CharacterData") -> int:
    """Sum the armor_class values of all equipped armor on a character,
    plus the mob definition AC for imported MudCentral monsters.

    Safely handles None slots, missing item definitions, and non-armor
    items — only items whose definition reports armor_class > 0 contribute.
    """
    total = 0
    for slot, item_id in cd.equipment.items():
        if item_id is not None:
            total += get_armor_class(item_id)

    # Add mob definition AC (imported MudCentral monsters have raw AC
    # stored on their definition; they typically don't wear equipment).
    if cd.race_id == "mob":
        from world.data.mobs import get_mob_definition
        definition = get_mob_definition(cd.profession_id)
        if definition:
            mob_ac = definition.get("ac")
            if isinstance(mob_ac, (int, float)) and mob_ac is not None:
                total += int(mob_ac)

    return total


# ---------------------------------------------------------------------------
# Combat state management
# ---------------------------------------------------------------------------


def enter_combat(cd: "CharacterData") -> None:
    """Mark a character as in-combat."""
    cd.state = CharacterState.COMBAT


def end_combat(cd: "CharacterData") -> None:
    """Remove a character from combat state.

    Does NOT change state on dead characters — death state is final.
    """
    if cd.state == CharacterState.COMBAT:
        cd.state = CharacterState.STANDING


# ---------------------------------------------------------------------------
# Attack validation
# ---------------------------------------------------------------------------


def validate_attack(attacker_cd: "CharacterData",
                    target_cd: "CharacterData | None") -> str | None:
    """
    Return an error string if the attack is invalid, or None if valid.

    Validation rules (Phase 5):
        • Attacker must be alive (state != DEAD, hp > 0).
        • Target must exist (not None).
        • Target must not be the same CharacterData instance.
        • Target must be alive (state != DEAD, hp > 0).
    """
    if not attacker_cd.is_alive() or attacker_cd.state == CharacterState.DEAD:
        return "You are dead and cannot attack."

    if target_cd is None:
        return "No valid target."

    if target_cd is attacker_cd:
        return "You cannot attack yourself."

    if not target_cd.is_alive() or target_cd.state == CharacterState.DEAD:
        return "Your target is already dead."

    return None


# ---------------------------------------------------------------------------
# Attack resolution — main entry point
# ---------------------------------------------------------------------------


def resolve_attack(attacker_cd: "CharacterData",
                   target_cd: "CharacterData") -> dict:
    """
    Execute a single physical attack from ``attacker_cd`` against
    ``target_cd``.

    This is the primary public API for Phase 5 combat.

    Returns a dict with keys:
        valid, error, hit, roll, raw_damage, actual_damage,
        target_hp_before, target_hp_after, target_killed,
        attacker_combat, target_combat.
    """
    result = {
        "valid": False,
        "error": None,
        "hit": False,
        "roll": None,
        "raw_damage": None,
        "actual_damage": 0,
        "target_hp_before": 0,
        "target_hp_after": 0,
        "target_killed": False,
        "attacker_combat": False,
        "target_combat": False,
    }

    # ---- Validation ------------------------------------------------
    error = validate_attack(attacker_cd, target_cd)
    if error is not None:
        result["error"] = error
        return result

    result["valid"] = True
    result["target_hp_before"] = target_cd.hp

    # ---- Enter combat state for both participants ------------------
    enter_combat(attacker_cd)
    enter_combat(target_cd)
    result["attacker_combat"] = True
    result["target_combat"] = True

    # ---- Hit / Miss ------------------------------------------------
    roll = random.randint(1, 100)
    result["roll"] = roll

    # Apply target dodge modifier (from mob combat properties).
    target_combat = _get_mob_combat_info(target_cd)
    dodge = target_combat.get("dodge_modifier", 0)
    hit_chance = _clamp_hit_chance(BASE_HIT_CHANCE - dodge)

    if roll <= hit_chance:
        result["hit"] = True
        damage = calculate_physical_damage(attacker_cd, target_cd)
        result["raw_damage"] = damage

        # Apply damage through the existing CharacterData API.
        killed = target_cd.take_damage(damage)
        result["actual_damage"] = damage
        result["target_hp_after"] = target_cd.hp
        result["target_killed"] = killed

        if killed:
            # Apply death through the authoritative data-layer method.
            target_cd.die()
            result["target_hp_after"] = 0
            result["target_combat"] = False
            end_combat(target_cd)
    else:
        # Miss — no damage applied.
        result["target_hp_after"] = target_cd.hp

    return result


# ---------------------------------------------------------------------------
# PvP kill recording (Phase 19 — corrected: faction-based eligibility)
# ---------------------------------------------------------------------------


def is_pvp_eligible(attacker_cd: "CharacterData",
                    target_cd: "CharacterData",
                    room_pvp_mode) -> bool:
    """
    Return True if ``attacker_cd`` is allowed to PvP ``target_cd``
    given the room's PvP mode.

    Rules (authoritative single source for all PvP gating):
        * Same faction → never valid (unless an existing rule says otherwise,
          and no such rule exists yet).
        * Opposing factions + CONTESTED / ARENA / FREE_FOR_ALL → valid.
        * Opposing factions + SAFE → NOT valid.
    """
    from world.data.enums import PvPMode

    # Resolve to enum if a plain string was passed.
    if isinstance(room_pvp_mode, str):
        try:
            room_pvp_mode = PvPMode(room_pvp_mode)
        except ValueError:
            room_pvp_mode = PvPMode.SAFE

    # Both participants must have a faction to be PvP-eligible.
    if attacker_cd.faction is None or target_cd.faction is None:
        return False

    # Same faction — not valid.
    if attacker_cd.faction == target_cd.faction:
        return False

    # Opposing factions — valid only in non-SAFE rooms.
    if room_pvp_mode == PvPMode.SAFE:
        return False

    # CONTESTED, ARENA, FREE_FOR_ALL — opposing-faction PvP is allowed.
    return True


def record_pvp_kill(killer_cd: "CharacterData",
                    victim_cd: "CharacterData",
                    room_pvp_mode) -> bool:
    """
    Record PvP statistics when a player kill occurs.

    Only awards stats when ``is_pvp_eligible`` returns True for the
    killer, victim, and room mode.  This is the same eligibility rule
    used by attack validation — kills are never double-awarded because
    eligibility is idempotent.

    On a valid PvP kill:
        * Increment killer ``pvp_kills``.
        * Increment victim ``pvp_deaths``.
        * Add ``WAR_POINTS_PER_KILL`` to killer ``war_points``.

    Returns:
        True if PvP stats were recorded, False otherwise.
    """
    if not is_pvp_eligible(killer_cd, victim_cd, room_pvp_mode):
        return False

    from world.data.constants import WAR_POINTS_PER_KILL

    killer_cd.pvp_kills += 1
    victim_cd.pvp_deaths += 1
    killer_cd.war_points += WAR_POINTS_PER_KILL
    return True
