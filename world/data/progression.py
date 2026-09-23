"""
Rites of Passage — Character Progression Service

Centralised XP curve, level-up processing, and skill-grant logic.
All progression rules live here so the Character typeclass can delegate.

This module does NOT import Evennia — plain Python, fully testable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT — XP curve is a TEMPORARY PLACEHOLDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The exact Rites of Passage XP progression numbers have NOT been finalised.
The current quadratic formula  XP = COEFF * (N-1)²  is a development
placeholder that provides sensible-shaped test data.

The architecture requires:
  •  centralised configurable XP thresholds (this module owns all XP math)
  •  Level 1 → Level 100 support
  •  early levels quick, mid levels slower, high levels substantially slower
  •  sequential multi-level processing (no skipped unlocks)
  •  automatic leveling (no trainers)

Final XP curve numbers will be determined through playtesting.  When that
happens, replace the xp_for_level() body — every other system in the game
already calls through this single function.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from world.data.constants import (
    MAX_LEVEL,
    STARTING_LEVEL,
    XP_CURVE_COEFF,
    DEFAULT_WEAPON_PROFICIENCY,
    get_resource_gains,
)
from world.data.enums import CharacterState
from world.data.professions import PROFESSIONS, UNIVERSAL_SKILLS, WEAPON_SKILLS


# ---------------------------------------------------------------------------
# XP Curve  —  TEMPORARY PLACEHOLDER VALUES
#
# Replace xp_for_level() body when final balance numbers are decided.
# Every other system in the project calls through these functions — the
# internal formula can be swapped without changing any caller.
# ---------------------------------------------------------------------------

def xp_for_level(level: int) -> int:
    """
    Total accumulated XP needed to *qualify* for `level`.

    Level 1 always requires 0 XP.

    CURRENT PLACEHOLDER FORMULA (NOT FINAL BALANCE):
        XP = XP_CURVE_COEFF * (level - 1) ** 2
    where XP_CURVE_COEFF = 100 (configurable in constants.py).
    """
    if level <= STARTING_LEVEL:
        return 0
    return XP_CURVE_COEFF * (level - 1) ** 2


def xp_to_next_level(current_level: int) -> int:
    """XP required to advance from `current_level` to the next level."""
    if current_level >= MAX_LEVEL:
        return 0
    return xp_for_level(current_level + 1) - xp_for_level(current_level)


def xp_progress_toward_next(total_xp: int, current_level: int) -> int:
    """
    How much XP has been earned toward the next level.
    Used by the death-penalty system.
    """
    if current_level >= MAX_LEVEL:
        return 0
    threshold = xp_for_level(current_level)
    xp_earned = total_xp - threshold
    return max(0, xp_earned)


def level_from_xp(total_xp: int) -> int:
    """
    MIGRATION / VALIDATION UTILITY ONLY.

    Determine the highest level for which the XP threshold has been met.
    Used for sanity-checking loaded characters or one-off reconciliation.
    NOT used by normal gameplay — the authoritive level field in
    CharacterData should NEVER be derived downward from XP loss.
    """
    for level in range(MAX_LEVEL, STARTING_LEVEL - 1, -1):
        if total_xp >= xp_for_level(level):
            return level
    return STARTING_LEVEL


# ---------------------------------------------------------------------------
# Skill / Progression Granting
# ---------------------------------------------------------------------------

def _collect_skills_for_level(
    profession_id: str | None, level: int,
) -> list[str]:
    """
    Return all skill IDs a character of `profession_id` should have
    unlocked by the time they reach `level`.  Combines universal skills
    and profession-specific skills.
    """
    skills: list[str] = []

    # Universal skills for levels <= `level`
    for lvl, skill_list in sorted(UNIVERSAL_SKILLS.items()):
        if lvl <= level:
            skills.extend(skill_list)

    # Profession-specific skills for levels <= `level`
    if profession_id and profession_id in PROFESSIONS:
        prof_data = PROFESSIONS[profession_id]
        for lvl, skill_list in sorted(prof_data.get("skills", {}).items()):
            if lvl <= level:
                skills.extend(skill_list)

    return skills


def grant_all_skills_for_level(cd, level: int) -> list[str]:
    """
    Grant every skill/spell the character should have at `level`.
    Returns list of newly-granted skill IDs (idempotent — never duplicates).

    `cd` is a CharacterData instance.
    """
    newly_granted: list[str] = []
    eligible = _collect_skills_for_level(cd.profession_id, level)

    for skill_id in eligible:
        if skill_id not in cd.unlocked_skills:
            cd.unlocked_skills.add(skill_id)
            newly_granted.append(skill_id)

    # Weapon proficiencies — ensure every eligible weapon skill has a
    # proficiency entry (default value if never touched before).
    for skill_id in WEAPON_SKILLS:
        if skill_id not in cd.proficiencies:
            cd.proficiencies[skill_id] = DEFAULT_WEAPON_PROFICIENCY

    return newly_granted


# ---------------------------------------------------------------------------
# Level-Up Processing
# ---------------------------------------------------------------------------

def process_single_level_up(cd) -> None:
    """
    Advance `cd` by exactly one level — grant skills, bump resources.
    Does NOT touch XP.  Caller is responsible for ensuring the character
    actually qualifies.
    """
    if cd.level >= MAX_LEVEL:
        return

    cd.level += 1
    new_level = cd.level

    # Increase resource maximums (current resources are NOT refilled).
    hp_pl, mana_pl, st_pl = get_resource_gains(cd.profession_id)
    cd.max_hp += hp_pl
    cd.max_mana += mana_pl
    cd.max_stamina += st_pl

    # Grant skills/spells for the new level.
    grant_all_skills_for_level(cd, new_level)


def process_level_ups(cd, new_total_xp: int) -> int:
    """
    Apply XP, then process any level-ups earned.  Handles multi-level
    jumps sequentially so no profession unlocks are skipped.

    `cd.level` is authoritative — level NEVER decreases; it only
    advances when the XP threshold for the next level has been met.

    Returns the final level reached.
    """
    if cd.level >= MAX_LEVEL:
        # At cap — accumulate XP without further leveling.
        cd.xp = max(cd.xp, new_total_xp)
        return cd.level

    cd.xp = new_total_xp

    # Process levels sequentially.
    while cd.level < MAX_LEVEL:
        next_threshold = xp_for_level(cd.level + 1)
        if cd.xp >= next_threshold:
            process_single_level_up(cd)
        else:
            break

    return cd.level


def award_xp(cd, amount: int) -> tuple[int, list[str]]:
    """
    Award XP to a character and process any resulting level-ups.

    Returns (new_level, []).
    `cd` is a CharacterData instance.
    Skill granting happens inside process_single_level_up.
    """
    if amount <= 0:
        return cd.level, []

    old_level = cd.level
    process_level_ups(cd, cd.xp + amount)

    return cd.level, []


# ---------------------------------------------------------------------------
# Initial Character Grants (call once at character creation)
# ---------------------------------------------------------------------------

def grant_starting_skills(cd) -> list[str]:
    """
    Grant all Level-1 skills to a newly-created character.
    Call AFTER init_character has set race_id and profession_id.
    Returns list of skill IDs granted.
    """
    newly = grant_all_skills_for_level(cd, STARTING_LEVEL)
    return newly


# ---------------------------------------------------------------------------
# Reconciliation — bring an existing character up to date
# ---------------------------------------------------------------------------

def reconcile_character_skills(cd) -> list[str]:
    """
    Idempotent: grant every skill the character should have at their
    current level.  Safe to call on existing/loaded characters.
    Returns newly-granted skills if any were missing.
    """
    return grant_all_skills_for_level(cd, cd.level)
