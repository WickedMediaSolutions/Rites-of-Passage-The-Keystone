"""
Rites of Passage — Resource Regeneration

Centralised regeneration logic for HP, Mana, and Stamina.

This module is plain Python — no Evennia imports — so it can be unit-tested
without a running server.  The Evennia-side scheduler (TickerHandler) lives
in ``typeclasses/characters.py`` and calls ``regen_tick()`` here.

Regeneration is simple periodic recovery:
    • HP recovers by REGEN_HP_PER_TICK each tick
    • Mana recovers by REGEN_MANA_PER_TICK each tick
    • Stamina recovers by REGEN_STAMINA_PER_TICK each tick

Dead characters (state == DEAD or hp <= 0) do NOT regenerate.
Resources never exceed their maximums.
Zero-max resources are safe (no division by zero, no negative regen).
"""

from world.data.constants import (
    REGEN_HP_PER_TICK,
    REGEN_MANA_PER_TICK,
    REGEN_STAMINA_PER_TICK,
)
from world.data.enums import CharacterState


def regen_tick(cd: "CharacterData") -> dict[str, int]:
    """
    Apply one regeneration tick to a character's resources.

    Args:
        cd: A ``CharacterData`` instance.

    Returns:
        Dict with keys ``hp``, ``mana``, ``stamina`` indicating how much
        of each resource was actually restored this tick (0 if none).

    Rules:
        * Dead characters (state == DEAD or hp <= 0) skip all regen.
        * Each resource is clamped to its maximum.
        * Zero-max resources are safe — no regen is applied when max <= 0.
    """
    result = {"hp": 0, "mana": 0, "stamina": 0}

    # Dead characters do not regenerate.
    if cd.state == CharacterState.DEAD or cd.hp <= 0:
        return result

    # HP regen
    if cd.max_hp > 0 and cd.hp < cd.max_hp:
        amount = min(REGEN_HP_PER_TICK, cd.max_hp - cd.hp)
        cd.hp += amount
        result["hp"] = amount

    # Mana regen
    if cd.max_mana > 0 and cd.mana < cd.max_mana:
        amount = min(REGEN_MANA_PER_TICK, cd.max_mana - cd.mana)
        cd.mana += amount
        result["mana"] = amount

    # Stamina regen
    if cd.max_stamina > 0 and cd.stamina < cd.max_stamina:
        amount = min(REGEN_STAMINA_PER_TICK, cd.max_stamina - cd.stamina)
        cd.stamina += amount
        result["stamina"] = amount

    return result