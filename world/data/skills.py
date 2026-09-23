"""
Rites of Passage — Skill & Spell Definitions and Use System

Data-driven skill/spell registry with structured use resolution.
ALL NUMERIC VALUES ARE [PLACEHOLDER] pending final game-design tuning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from world.data.enums import CharacterState, DamageType, SkillCategory
from world.data.combat import calculate_skill_damage

if TYPE_CHECKING:
    from world.data.character_data import CharacterData


@dataclass
class SkillDefinition:
    """Static metadata for a single skill or spell."""
    skill_id: str
    name: str
    category: SkillCategory
    description: str = ""
    cost_type: str | None = None       # "mana", "stamina", or None
    cost_amount: int = 0               # [PLACEHOLDER]
    target_required: bool = False
    target_enemy: bool = False
    damage_type: DamageType | None = None
    base_damage: int | None = None     # None = non-damaging
    self_heal_amount: int | None = None
    is_passive: bool = False


# =============================================================================
# Compact skill data — parsed by _build_registry() at module load
# =============================================================================

_SKILL_DATA_TUPLES = [
    ('acid_blast', 'Acid Blast', 'PROFESSION', 'mana', 25, True, True, 'POISON', 30, None, False, 'Corrosive blast. [PLACEHOLDER]'),
    ('advanced_tracking', 'Adv Tracking', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Track with precision.'),
    ('agony', 'Agony', 'PROFESSION', 'mana', 30, True, True, 'PSYCHIC', 30, None, False, 'Mental agony. [PLACEHOLDER]'),
    ('armor_penetration', 'Armor Penetration', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Bypass armor. [PLACEHOLDER]'),
    ('avalanche', 'Avalanche', 'PROFESSION', 'mana', 50, True, True, 'EARTH', 60, None, False, 'Bury in rock. [PLACEHOLDER]'),
    ('backstab', 'Backstab', 'PROFESSION', 'stamina', 15, True, True, 'PIERCING', 25, None, False, 'Strike from behind. [PLACEHOLDER]'),
    ('barkskin', 'Barkskin', 'PROFESSION', 'mana', 20, True, False, 'EARTH', None, None, False, 'Toughen skin. [PLACEHOLDER]'),
    ('barrier', 'Barrier', 'PROFESSION', 'mana', 20, False, False, None, None, None, False, 'Magical barrier. [PLACEHOLDER]'),
    ('bash', 'Bash', 'PROFESSION', 'stamina', 15, True, True, 'CONCUSSION', 15, None, False, 'Bash target. [PLACEHOLDER]'),
    ('battle_tactics', 'Battle Tactics', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Tactical advantage. [PLACEHOLDER]'),
    ('black_mantle', 'Black Mantle', 'PROFESSION', 'mana', 30, True, True, 'UNHOLY', None, None, False, 'Shroud in darkness. [PLACEHOLDER]'),
    ('black_tentacles', 'Black Tentacles', 'PROFESSION', 'mana', 30, True, True, 'UNHOLY', 35, None, False, 'Summon tentacles. [PLACEHOLDER]'),
    ('bless', 'Bless', 'PROFESSION', 'mana', 15, True, False, 'HOLY', None, None, False, 'Bless target. [PLACEHOLDER]'),
    ('blink', 'Blink', 'PROFESSION', 'mana', 15, False, False, None, None, None, False, 'Short teleport. [PLACEHOLDER]'),
    ('body_control', 'Body Control', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Resist effects. [PLACEHOLDER]'),
    ('butcher', 'Butcher', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Butcher a corpse.'),
    ('circle', 'Circle', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Better position. [PLACEHOLDER]'),
    ('coat', 'Coat Weapon', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Apply poison. [PLACEHOLDER]'),
    ('concentration', 'Concentration', 'PROFESSION', 'mana', 10, False, False, 'PSYCHIC', None, None, False, 'Focus mind. [PLACEHOLDER]'),
    ('concussion_weapons', 'Concussion Weapons', 'WEAPON', None, 0, False, False, None, None, None, True, 'Proficiency with concussion weapons.'),
    ('creeping_doom', 'Creeping Doom', 'PROFESSION', 'mana', 50, True, True, 'DISEASE', 60, None, False, 'Creeping doom. [PLACEHOLDER]'),
    ('disarm', 'Disarm', 'PROFESSION', 'stamina', 20, True, True, None, None, None, False, 'Disarm target. [PLACEHOLDER]'),
    ('disease_spell', 'Disease', 'PROFESSION', 'mana', 20, True, True, 'DISEASE', 20, None, False, 'Afflict with disease. [PLACEHOLDER]'),
    ('dispel', 'Dispel', 'PROFESSION', 'mana', 20, True, True, None, None, None, False, 'Remove magic effects. [PLACEHOLDER]'),
    ('displacement', 'Displacement', 'PROFESSION', 'mana', 20, False, False, None, None, None, False, 'Shift position. [PLACEHOLDER]'),
    ('divine_favor', 'Divine Favor', 'PROFESSION', 'mana', 25, True, False, 'HOLY', None, None, False, 'Divine favor. [PLACEHOLDER]'),
    ('dodge', 'Dodge', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Evade attack. [PLACEHOLDER]'),
    ('dual_daggers', 'Dual Daggers', 'PROFESSION', 'stamina', 20, False, False, None, None, None, False, 'Wield two daggers. [PLACEHOLDER]'),
    ('dual_wield', 'Dual Wield', 'PROFESSION', 'stamina', 20, False, False, None, None, None, False, 'Wield two weapons. [PLACEHOLDER]'),
    ('earthen_hammer', 'Earthen Hammer', 'PROFESSION', 'mana', 25, True, True, 'EARTH', 35, None, False, 'Stone hammer. [PLACEHOLDER]'),
    ('elbow', 'Elbow', 'PROFESSION', 'stamina', 10, True, True, 'CONCUSSION', 12, None, False, 'Elbow strike. [PLACEHOLDER]'),
    ('endurance', 'Endurance', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Reduce stamina costs. [PLACEHOLDER]'),
    ('enhanced_backstab', 'Enhanced Backstab', 'PROFESSION', 'stamina', 25, True, True, 'PIERCING', 35, None, False, 'Devastating backstab. [PLACEHOLDER]'),
    ('enhanced_circle', 'Enhanced Circle', 'PROFESSION', 'stamina', 25, False, False, None, None, None, False, 'Faster circling. [PLACEHOLDER]'),
    ('enhanced_damage', 'Enhanced Damage', 'PROFESSION', 'stamina', 20, False, False, None, None, None, False, 'Extra force. [PLACEHOLDER]'),
    ('enhanced_kick', 'Enhanced Kick', 'PROFESSION', 'stamina', 20, True, True, 'CONCUSSION', 25, None, False, 'Powerful kick. [PLACEHOLDER]'),
    ('enlarge', 'Enlarge', 'PROFESSION', 'mana', 25, False, False, None, None, None, False, 'Grow in size. [PLACEHOLDER]'),
    ('enrage', 'Enrage', 'PROFESSION', 'mana', 15, False, False, None, None, None, False, 'Fly into rage. [PLACEHOLDER]'),
    ('entangle', 'Entangle', 'PROFESSION', 'mana', 15, True, True, 'EARTH', None, None, False, 'Root target. [PLACEHOLDER]'),
    ('entropy_shield', 'Entropy Shield', 'PROFESSION', 'mana', 30, False, False, None, None, None, False, 'Entropy shield. [PLACEHOLDER]'),
    ('essence_of_spirit', 'Essence of Spirit', 'PROFESSION', 'mana', 25, True, False, 'HOLY', None, None, False, 'Spiritual essence. [PLACEHOLDER]'),
    ('evasive_attack', 'Evasive Attack', 'PROFESSION', 'stamina', 20, True, True, 'PIERCING', 20, None, False, 'Attack while dodging. [PLACEHOLDER]'),
    ('extraction', 'Extraction', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Extract components.'),
    ('eye_gouge', 'Eye Gouge', 'PROFESSION', 'stamina', 15, True, True, 'PIERCING', 15, None, False, 'Blind target. [PLACEHOLDER]'),
    ('falling_star', 'Falling Star', 'PROFESSION', 'mana', 50, True, True, 'FIRE', 60, None, False, 'Falling star. [PLACEHOLDER]'),
    ('feeblemind', 'Feeblemind', 'PROFESSION', 'mana', 20, True, True, 'PSYCHIC', None, None, False, 'Cloud mind. [PLACEHOLDER]'),
    ('fire_shield', 'Fire Shield', 'PROFESSION', 'mana', 20, False, False, 'FIRE', 10, None, False, 'Fire shield. [PLACEHOLDER]'),
    ('fireball', 'Fireball', 'PROFESSION', 'mana', 30, True, True, 'FIRE', 40, None, False, 'Hurl fireball. [PLACEHOLDER]'),
    ('fists_of_speed', 'Fists of Speed', 'PROFESSION', 'stamina', 25, True, True, 'CONCUSSION', 30, None, False, 'Flurry of punches. [PLACEHOLDER]'),
    ('flame_blade', 'Flame Blade', 'PROFESSION', 'mana', 20, True, True, 'FIRE', 25, None, False, 'Imbue weapon with fire. [PLACEHOLDER]'),
    ('flamestrike', 'Flamestrike', 'PROFESSION', 'mana', 20, True, True, 'FIRE', 25, None, False, 'Pillar of flame. [PLACEHOLDER]'),
    ('frost_lance', 'Frost Lance', 'PROFESSION', 'mana', 30, True, True, 'WATER', 40, None, False, 'Lance of ice. [PLACEHOLDER]'),
    ('grapple', 'Grapple', 'PROFESSION', 'stamina', 20, True, True, 'CONCUSSION', 15, None, False, 'Grapple target. [PLACEHOLDER]'),
    ('group_stealth', 'Group Stealth', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Extend stealth to allies.'),
    ('guard', 'Guard', 'PROFESSION', 'stamina', 15, True, False, None, None, None, False, 'Guard ally. [PLACEHOLDER]'),
    ('haggle', 'Haggle', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Negotiate better prices.'),
    ('haste', 'Haste', 'PROFESSION', 'mana', 15, False, False, None, None, None, False, 'Increase speed. [PLACEHOLDER]'),
    ('heal_critical', 'Heal Critical', 'PROFESSION', 'mana', 25, True, False, 'HOLY', None, 25, False, 'Heal critical wounds. [PLACEHOLDER]'),
    ('healing', 'Healing', 'PROFESSION', 'mana', 20, True, False, 'HOLY', None, 20, False, 'Restore health. [PLACEHOLDER]'),
    ('hide', 'Hide', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Conceal self. [PLACEHOLDER]'),
    ('holy_light', 'Holy Light', 'PROFESSION', 'mana', 35, True, True, 'HOLY', 40, None, False, 'Blast with holy light. [PLACEHOLDER]'),
    ('holy_ward', 'Holy Ward', 'PROFESSION', 'mana', 15, False, False, None, None, None, False, 'Protective ward. [PLACEHOLDER]'),
    ('identify', 'Identify', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Identify items.'),
    ('investigation', 'Investigation', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Examine details.'),
    ('invisibility', 'Invisibility', 'PROFESSION', 'mana', 30, False, False, None, None, None, False, 'Turn invisible. [PLACEHOLDER]'),
    ('iron_skin', 'Iron Skin', 'PROFESSION', 'mana', 25, False, False, None, None, None, False, 'Harden skin. [PLACEHOLDER]'),
    ('kick', 'Kick', 'PROFESSION', 'stamina', 10, True, True, 'CONCUSSION', 10, None, False, 'Quick kick. [PLACEHOLDER]'),
    ('leadership', 'Leadership', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Inspire allies.'),
    ('life_drain', 'Life Drain', 'PROFESSION', 'mana', 30, True, True, 'UNHOLY', 40, 20, False, 'Drain target life. [PLACEHOLDER]'),
    ('locksmithy', 'Locksmithy', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Pick locks.'),
    ('martial_arts', 'Martial Arts', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Martial arts stance. [PLACEHOLDER]'),
    ('mass_healing', 'Mass Healing', 'PROFESSION', 'mana', 40, False, False, 'HOLY', None, None, False, 'Heal all allies. [PLACEHOLDER]'),
    ('mass_refresh', 'Mass Refresh', 'PROFESSION', 'mana', 40, False, False, 'HOLY', None, None, False, 'Refresh allies. [PLACEHOLDER]'),
    ('meditation', 'Meditation', 'PROFESSION', 'mana', 10, False, False, None, None, None, False, 'Enter meditation. [PLACEHOLDER]'),
    ('mix', 'Mix', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Combine ingredients.'),
    ('parry', 'Parry', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Deflect attack. [PLACEHOLDER]'),
    ('peek', 'Peek', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Look into containers.'),
    ('piercing_weapons', 'Piercing Weapons', 'WEAPON', None, 0, False, False, None, None, None, True, 'Proficiency with piercing weapons.'),
    ('poison_lore', 'Poison Lore', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Poison knowledge.'),
    ('potion_lore', 'Potion Lore', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Potion knowledge.'),
    ('prayer', 'Prayer', 'PROFESSION', 'mana', 10, False, False, 'HOLY', None, None, False, 'Offer prayer. [PLACEHOLDER]'),
    ('primal_roar', 'Primal Roar', 'PROFESSION', 'mana', 30, True, True, 'AIR', 40, None, False, 'Primal roar. [PLACEHOLDER]'),
    ('psionic_blast', 'Psionic Blast', 'PROFESSION', 'mana', 25, True, True, 'PSYCHIC', 30, None, False, 'Psionic blast. [PLACEHOLDER]'),
    ('psychic_blade', 'Psychic Blade', 'PROFESSION', 'mana', 30, True, True, 'PSYCHIC', 35, None, False, 'Psychic blade. [PLACEHOLDER]'),
    ('pummel', 'Pummel', 'PROFESSION', 'stamina', 20, True, True, 'CONCUSSION', 20, None, False, 'Rapid blows. [PLACEHOLDER]'),
    ('rescue', 'Rescue', 'PROFESSION', 'stamina', 15, True, False, None, None, None, False, 'Intercept attacks. [PLACEHOLDER]'),
    ('restore_voice', 'Restore Voice', 'PROFESSION', 'mana', 15, True, False, None, None, None, False, 'Restore voice. [PLACEHOLDER]'),
    ('retreat', 'Retreat', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Disengage. [PLACEHOLDER]'),
    ('righteousness', 'Righteousness', 'PROFESSION', 'mana', 20, False, False, 'HOLY', None, None, False, 'Righteous fury. [PLACEHOLDER]'),
    ('riposte', 'Riposte', 'PROFESSION', 'stamina', 20, True, True, 'PIERCING', 25, None, False, 'Counter-attack. [PLACEHOLDER]'),
    ('sanctuary', 'Sanctuary', 'PROFESSION', 'mana', 30, False, False, 'HOLY', None, None, False, 'Create sanctuary. [PLACEHOLDER]'),
    ('searching', 'Searching', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Search the surroundings.'),
    ('searing_orb', 'Searing Orb', 'PROFESSION', 'mana', 25, True, True, 'FIRE', 35, None, False, 'Searing energy orb. [PLACEHOLDER]'),
    ('second_attack', 'Second Attack', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Grants second attack per round.'),
    ('second_punch', 'Second Punch', 'PROFESSION', 'stamina', 15, True, True, 'CONCUSSION', 15, None, False, 'Rapid second punch. [PLACEHOLDER]'),
    ('seed_of_grove', 'Seed of Grove', 'PROFESSION', 'mana', 30, False, False, 'EARTH', None, None, False, 'Protective grove. [PLACEHOLDER]'),
    ('self_healing', 'Self Healing', 'PROFESSION', 'mana', 15, False, False, 'HOLY', None, 20, False, 'Heal self. [PLACEHOLDER]'),
    ('set_trap', 'Set Trap', 'PROFESSION', 'stamina', 20, False, False, 'PIERCING', 25, None, False, 'Set a trap. [PLACEHOLDER]'),
    ('sharpen', 'Sharpen', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Sharpen weapon. [PLACEHOLDER]'),
    ('shield_block', 'Shield Block', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Block attacks. [PLACEHOLDER]'),
    ('shield_rush', 'Shield Rush', 'PROFESSION', 'stamina', 20, True, True, 'CONCUSSION', 20, None, False, 'Shield charge. [PLACEHOLDER]'),
    ('siphon_life', 'Siphon Life', 'PROFESSION', 'mana', 15, True, True, 'UNHOLY', 15, 8, False, 'Drain life. [PLACEHOLDER]'),
    ('slashing_weapons', 'Slashing Weapons', 'WEAPON', None, 0, False, False, None, None, None, True, 'Proficiency with slashing weapons.'),
    ('sneak', 'Sneak', 'PROFESSION', 'stamina', 10, False, False, None, None, None, False, 'Move quietly. [PLACEHOLDER]'),
    ('soul_harvest', 'Soul Harvest', 'PROFESSION', 'mana', 50, True, True, 'UNHOLY', 50, None, False, 'Tear out soul. [PLACEHOLDER]'),
    ('spellshield', 'Spellshield', 'PROFESSION', 'mana', 20, False, False, None, None, None, False, 'Absorb spells. [PLACEHOLDER]'),
    ('stealth', 'Stealth', 'PROFESSION', 'stamina', 20, False, False, None, None, None, False, 'Undetectable movement. [PLACEHOLDER]'),
    ('stone_skin', 'Stone Skin', 'PROFESSION', 'mana', 20, True, False, 'EARTH', None, None, False, 'Harden skin. [PLACEHOLDER]'),
    ('strangle', 'Strangle', 'PROFESSION', 'stamina', 20, True, True, 'CONCUSSION', 20, None, False, 'Silence target. [PLACEHOLDER]'),
    ('stun', 'Stun', 'PROFESSION', 'mana', 15, True, True, 'CONCUSSION', 10, None, False, 'Stun target. [PLACEHOLDER]'),
    ('summon', 'Summon', 'PROFESSION', 'mana', 50, False, False, None, None, None, False, 'Summon ally. [PLACEHOLDER]'),
    ('swim', 'Swim', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Swim through water.'),
    ('system_purge', 'System Purge', 'PROFESSION', 'mana', 30, False, False, 'HOLY', None, None, False, 'Purge toxins. [PLACEHOLDER]'),
    ('teleport', 'Teleport', 'PROFESSION', 'mana', 40, False, False, None, None, None, False, 'Teleport. [PLACEHOLDER]'),
    ('third_attack', 'Third Attack', 'PROFESSION', 'stamina', 25, False, False, None, None, None, False, 'Third attack. [PLACEHOLDER]'),
    ('thorn_shield', 'Thorn Shield', 'PROFESSION', 'mana', 20, False, False, 'PIERCING', 10, None, False, 'Damaging thorns. [PLACEHOLDER]'),
    ('thunderbolt', 'Thunderbolt', 'PROFESSION', 'mana', 40, True, True, 'AIR', 50, None, False, 'Call thunderbolt. [PLACEHOLDER]'),
    ('tinker', 'Tinker', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Repair equipment.'),
    ('touch_of_gaia', 'Touch of Gaia', 'PROFESSION', 'mana', 25, True, False, 'EARTH', None, None, False, 'Heal and restore. [PLACEHOLDER]'),
    ('tracking', 'Tracking', 'UNIVERSAL', None, 0, False, False, None, None, None, False, 'Track creatures.'),
    ('tumbling', 'Tumbling', 'PROFESSION', 'stamina', 15, False, False, None, None, None, False, 'Acrobatic evade. [PLACEHOLDER]'),
    ('turn_undead', 'Turn Undead', 'PROFESSION', 'mana', 20, True, True, 'HOLY', 30, None, False, 'Repel undead. [PLACEHOLDER]'),
    ('vampiric_touch', 'Vampiric Touch', 'PROFESSION', 'mana', 20, True, True, 'UNHOLY', 20, 10, False, 'Drain life force. [PLACEHOLDER]'),
    ('vital_strike', 'Vital Strike', 'PROFESSION', 'stamina', 30, True, True, 'PIERCING', 40, None, False, 'Strike vitals. [PLACEHOLDER]'),
    ('vortex', 'Vortex', 'PROFESSION', 'mana', 20, True, True, 'AIR', 25, None, False, 'Swirling vortex. [PLACEHOLDER]'),
    ('waters_of_grove', 'Waters of Grove', 'PROFESSION', 'mana', 30, False, False, 'WATER', None, None, False, 'Healing waters. [PLACEHOLDER]'),
    ('whip_lash', 'Whip Lash', 'PROFESSION', 'mana', 10, True, True, 'WHIPPING', 15, None, False, 'Dark energy lash. [PLACEHOLDER]'),
    ('whipping_weapons', 'Whipping Weapons', 'WEAPON', None, 0, False, False, None, None, None, True, 'Proficiency with whipping weapons.'),
    ('whirlwind', 'Whirlwind', 'PROFESSION', 'mana', 20, True, True, 'AIR', 20, None, False, 'Summon whirlwind. [PLACEHOLDER]'),
    ('winds_of_chaos', 'Winds of Chaos', 'PROFESSION', 'mana', 30, True, True, 'AIR', 35, None, False, 'Chaotic winds. [PLACEHOLDER]'),
    ('wrath_of_nature', 'Wrath of Nature', 'PROFESSION', 'mana', 35, True, True, 'EARTH', 45, None, False, 'Nature fury. [PLACEHOLDER]'),
]


def _build_registry() -> dict[str, SkillDefinition]:
    """Construct SKILL_REGISTRY from the compact data tuples."""
    reg = {}
    for (sid, name, cat, ct, cost, tr, te, dt_s, bd, sh, ip, desc) in _SKILL_DATA_TUPLES:
        dt = DamageType[dt_s] if dt_s else None
        cat_enum = SkillCategory[cat]
        reg[sid] = SkillDefinition(
            skill_id=sid, name=name, category=cat_enum,
            description=desc,
            cost_type=ct, cost_amount=cost,
            target_required=tr, target_enemy=te,
            damage_type=dt, base_damage=bd,
            self_heal_amount=sh, is_passive=ip,
        )
    return reg


SKILL_REGISTRY: dict[str, SkillDefinition] = _build_registry()



# =============================================================================
# Skill lookup
# =============================================================================

def get_skill_definition(skill_id: str) -> SkillDefinition | None:
    """Return the SkillDefinition for *skill_id*, or None if unknown."""
    return SKILL_REGISTRY.get(skill_id)


def skill_exists(skill_id: str) -> bool:
    """Return True if *skill_id* is a known skill/spell."""
    return skill_id in SKILL_REGISTRY


def get_skill_name(skill_id: str) -> str:
    """Return a human-readable name for display, or the raw ID if unknown."""
    defn = SKILL_REGISTRY.get(skill_id)
    return defn.name if defn else skill_id


# =============================================================================
# Skill Use Result
# =============================================================================

@dataclass
class SkillUseResult:
    """Structured result from a skill/spell use attempt."""

    success: bool = False
    error: str | None = None
    skill_id: str = ""

    caster_hp_before: int = 0
    caster_hp_after: int = 0
    caster_mana_before: int = 0
    caster_mana_after: int = 0
    caster_stamina_before: int = 0
    caster_stamina_after: int = 0

    resource_cost_paid: int = 0
    resource_type: str | None = None

    target_hp_before: int | None = None
    target_hp_after: int | None = None
    damage_dealt: int = 0
    target_killed: bool = False
    healing_applied: int = 0

    caster_entered_combat: bool = False
    target_entered_combat: bool = False


# =============================================================================
# Validation
# =============================================================================

def validate_skill_use(
    caster_cd: CharacterData,
    skill_id: str,
    target_cd: CharacterData | None = None,
) -> str | None:
    """Return an error string if the skill cannot be used, or None if valid."""
    if caster_cd.state == CharacterState.DEAD or not caster_cd.is_alive():
        return "You are dead and cannot use skills."

    defn = SKILL_REGISTRY.get(skill_id)
    if defn is None:
        return f"Unknown skill: '{skill_id}'."

    if defn.is_passive:
        return f"'{defn.name}' is a passive skill and cannot be activated."

    if skill_id not in caster_cd.unlocked_skills:
        return f"You have not unlocked '{defn.name}'."

    if defn.cost_type == "mana":
        if caster_cd.mana < defn.cost_amount:
            return (f"Not enough mana to use '{defn.name}' "
                    f"(need {defn.cost_amount}, have {caster_cd.mana}).")
    elif defn.cost_type == "stamina":
        if caster_cd.stamina < defn.cost_amount:
            return (f"Not enough stamina to use '{defn.name}' "
                    f"(need {defn.cost_amount}, have {caster_cd.stamina}).")

    if defn.target_required:
        if target_cd is None:
            return f"'{defn.name}' requires a target."
        if target_cd is caster_cd:
            return f"You cannot target yourself with '{defn.name}'."
        if target_cd.state == CharacterState.DEAD or not target_cd.is_alive():
            return "Your target is already dead."

    return None


# =============================================================================
# Skill Use
# =============================================================================

def use_skill(
    caster_cd: CharacterData,
    skill_id: str,
    target_cd: CharacterData | None = None,
) -> SkillUseResult:
    """Execute a skill/spell from *caster_cd* against an optional *target_cd*."""
    from world.data.combat import enter_combat

    defn = SKILL_REGISTRY.get(skill_id)
    result = SkillUseResult(skill_id=skill_id)

    result.caster_hp_before = caster_cd.hp
    result.caster_mana_before = caster_cd.mana
    result.caster_stamina_before = caster_cd.stamina

    error = validate_skill_use(caster_cd, skill_id, target_cd)
    if error is not None:
        result.error = error
        result.caster_hp_after = caster_cd.hp
        result.caster_mana_after = caster_cd.mana
        result.caster_stamina_after = caster_cd.stamina
        return result

    result.resource_type = defn.cost_type
    if defn.cost_type == "mana":
        caster_cd.mana -= defn.cost_amount
        result.resource_cost_paid = defn.cost_amount
    elif defn.cost_type == "stamina":
        caster_cd.stamina -= defn.cost_amount
        result.resource_cost_paid = defn.cost_amount

    if caster_cd.state != CharacterState.COMBAT:
        enter_combat(caster_cd)
        result.caster_entered_combat = True

    if target_cd is not None and defn.base_damage is not None and defn.base_damage > 0:
        result.target_hp_before = target_cd.hp
        damage = calculate_skill_damage(
            defn.base_damage,
            defn.damage_type,
            target_cd,
        )
        result.damage_dealt = damage
        killed = target_cd.take_damage(damage)
        result.target_hp_after = target_cd.hp
        result.target_killed = killed
        if killed:
            target_cd.die()
            result.target_hp_after = 0
        else:
            if target_cd.state != CharacterState.COMBAT:
                enter_combat(target_cd)
                result.target_entered_combat = True

    if defn.self_heal_amount is not None and defn.self_heal_amount > 0:
        healed = caster_cd.heal(defn.self_heal_amount)
        result.healing_applied = healed

    result.success = True
    result.caster_hp_after = caster_cd.hp
    result.caster_mana_after = caster_cd.mana
    result.caster_stamina_after = caster_cd.stamina

    return result
