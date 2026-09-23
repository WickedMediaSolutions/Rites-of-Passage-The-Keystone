"""
Rites of Passage — Mob Combat AI

Plain-Python AI decision logic for mob combat behaviour.
All functions operate on ``CharacterData`` instances and are directly
testable without an Evennia server.

An Evennia-side scheduler (e.g., TickerHandler) calls
``execute_combat_round()`` at regular intervals.

Design constraints (Phase 10 foundation only):
    • No autonomous aggro scanning
    • No advanced threat/aggro tables
    • No pathfinding
    • No mob respawning
    • No loot / XP / rewards
    • No skills / spells
"""

from world.data.character_data import CharacterData
from world.data.combat import resolve_attack, end_combat
from world.data.enums import CharacterState, Faction
from world.data.mobs import get_mob_definition

# ---------------------------------------------------------------------------
# Timing constants [PLACEHOLDER]
# ---------------------------------------------------------------------------

# Seconds between mob combat rounds.  [PLACEHOLDER]
COMBAT_ROUND_INTERVAL = 5

# ---------------------------------------------------------------------------
# AI State Flags (attached to CharacterData at runtime)
# ---------------------------------------------------------------------------

# We use a minimal ai_state dict that lives on the CharacterData instance
# to track mob AI state without modifying the CharacterData class itself.
# Keys:
#   "combat_active"  — bool, True while the mob is in an active combat loop
#   "current_target" — CharacterData | None


def _ai_state(cd: CharacterData) -> dict:
    """Return (and create if needed) the ai_state dict attached to a
    CharacterData instance."""
    if not hasattr(cd, "_ai_state"):
        cd._ai_state = {"combat_active": False, "current_target": None}
    return cd._ai_state


# ---------------------------------------------------------------------------
# Target Validation
# ---------------------------------------------------------------------------


def is_valid_target(target_cd: CharacterData | None) -> bool:
    """Return True if the target is alive and not the same instance."""
    if target_cd is None:
        return False
    if target_cd.state == CharacterState.DEAD:
        return False
    if not target_cd.is_alive():
        return False
    return True


# ---------------------------------------------------------------------------
# Hostile Target Selection
# ---------------------------------------------------------------------------


def select_hostile_target(
    mob_cd: CharacterData,
    player_cds: list[CharacterData],
) -> CharacterData | None:
    """Select a valid hostile target from a list of player CharacterData.

    A hostile mob selects the first alive player whose faction opposes the
    mob's faction.  Non-hostile mobs always return None.

    Returns None if no valid target is found.
    """
    # Dead mobs cannot acquire targets.
    if not mob_cd.is_alive() or mob_cd.state == CharacterState.DEAD:
        return None

    # Only hostile mobs auto-target.
    definition = get_mob_definition(mob_cd.profession_id)
    if definition is None or not definition.get("hostile", False):
        return None

    for player in player_cds:
        if not is_valid_target(player):
            continue
        # Hostile mobs attack opposite faction.
        # If mob faction is None (shouldn't happen), default to hostile.
        if mob_cd.faction is not None and player.faction == mob_cd.faction:
            continue
        return player

    return None


# ---------------------------------------------------------------------------
# Can Engage
# ---------------------------------------------------------------------------


def can_engage(mob_cd: CharacterData) -> bool:
    """Return True if the mob is capable of engaging in combat.

    Checks:
        • Mob is alive
        • Mob definition exists and is marked hostile
    """
    if not mob_cd.is_alive() or mob_cd.state == CharacterState.DEAD:
        return False

    definition = get_mob_definition(mob_cd.profession_id)
    if definition is None:
        return False
    if not definition.get("hostile", False):
        return False

    return True


# ---------------------------------------------------------------------------
# Combat Engagement
# ---------------------------------------------------------------------------


def engage_target(mob_cd: CharacterData,
                  target_cd: CharacterData) -> str | None:
    """Begin an AI-driven combat engagement between a mob and a target.

    Sets the mob's ai_state to track the active combat.  Does NOT start
    a ticker — that is the Evennia layer's responsibility.

    Returns an error string if engagement is invalid, or None on success.
    """
    if not mob_cd.is_alive() or mob_cd.state == CharacterState.DEAD:
        return "Mob is dead."

    if not is_valid_target(target_cd):
        return "Invalid target."

    ai = _ai_state(mob_cd)
    ai["combat_active"] = True
    ai["current_target"] = target_cd

    return None


# ---------------------------------------------------------------------------
# Combat Round Execution
# ---------------------------------------------------------------------------


def execute_combat_round(mob_cd: CharacterData) -> dict:
    """Execute a single round of AI-driven combat for a mob.

    This is the core plain-Python function called by the Evennia-side
    scheduler every COMBAT_ROUND_INTERVAL seconds.

    The mob attacks its current target via ``resolve_attack()``.
    Combat automatically ends if:
        • The mob is dead
        • The target is dead / invalid
        • The mob's combat flag is not set

    Returns a dict with keys:
        round_executed  — bool, True if an attack round actually ran
        result          — the resolve_attack result dict, or None
        combat_ended    — bool, True if combat ended this round
        end_reason      — str or None describing why combat ended
    """
    ai = _ai_state(mob_cd)

    outcome = {
        "round_executed": False,
        "result": None,
        "combat_ended": False,
        "end_reason": None,
    }

    # ---- Already not in combat? ---------------------------------------
    if not ai.get("combat_active"):
        outcome["combat_ended"] = True
        outcome["end_reason"] = "Combat not active."
        return outcome

    # ---- Mob dead? ----------------------------------------------------
    if not mob_cd.is_alive() or mob_cd.state == CharacterState.DEAD:
        _end_combat_internal(mob_cd, ai, outcome, "Mob died.")
        return outcome

    # ---- Target still valid? ------------------------------------------
    target = ai.get("current_target")
    if not is_valid_target(target):
        reason = "Target lost (dead or invalid)."
        if target is not None and target.state == CharacterState.DEAD:
            reason = "Target died."
        elif target is None:
            reason = "Target disconnected or left."
        _end_combat_internal(mob_cd, ai, outcome, reason)
        return outcome

    # ---- Execute the attack -------------------------------------------
    result = resolve_attack(mob_cd, target)
    outcome["round_executed"] = True
    outcome["result"] = result

    # ---- Check if target died -----------------------------------------
    if result.get("target_killed"):
        _end_combat_internal(mob_cd, ai, outcome, "Target killed.")
        return outcome

    return outcome


# ---------------------------------------------------------------------------
# Force End Combat
# ---------------------------------------------------------------------------


def force_end_combat(mob_cd: CharacterData) -> str | None:
    """Externally end the mob's AI-driven combat (e.g., target disconnected,
    moved away, GM intervention).

    Returns an error string if combat was not active, or None on success.
    """
    ai = _ai_state(mob_cd)
    if not ai.get("combat_active"):
        return "Combat not active."

    ai["combat_active"] = False
    ai["current_target"] = None
    # Ensure mob leaves COMBAT state if it is still in it.
    if mob_cd.state == CharacterState.COMBAT:
        end_combat(mob_cd)
    return None


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _end_combat_internal(mob_cd: CharacterData, ai: dict,
                         outcome: dict, reason: str) -> None:
    """Clean up mob AI state and combat state."""
    ai["combat_active"] = False
    ai["current_target"] = None
    outcome["combat_ended"] = True
    outcome["end_reason"] = reason
    if mob_cd.state == CharacterState.COMBAT:
        end_combat(mob_cd)
