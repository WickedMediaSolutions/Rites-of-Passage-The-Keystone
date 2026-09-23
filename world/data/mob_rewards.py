"""
Rites of Passage — Mob Loot & XP Rewards

Plain-Python reward calculation and granting for mob kills.
Separate from mob spawning — called by combat death handlers.

Design constraints (Phase 12 foundation only):
    • No corpse objects
    • No loot commands/UI
    • No group/party XP splitting
    • No quest credit
    • No shops/economy
    • No rare-drop announcements
    • No Phase 13+
"""

import random

from world.data.character_data import CharacterData
from world.data.items import item_exists
from world.data.mobs import get_mob_definition
from world.data.progression import award_xp

# ---------------------------------------------------------------------------
# Loot-Table Registry
# ---------------------------------------------------------------------------

LOOT_TABLE_REGISTRY: dict[str, list[dict]] = {}


def register_loot_table(table_id: str, entries: list[dict]) -> None:
    """Store a loot table in the registry under *table_id*.

    ``entries`` is stored unchanged — a list of dicts with ``item_id``,
    ``chance``, and ``quantity`` as expected by ``_roll_loot_table``.
    """
    LOOT_TABLE_REGISTRY[table_id] = entries


def get_loot_table(table_id: str) -> list[dict] | None:
    """Return the loot table registered under *table_id*, or ``None``."""
    return LOOT_TABLE_REGISTRY.get(table_id)

# ---------------------------------------------------------------------------
# Reward Result — structured return value
# ---------------------------------------------------------------------------

def _make_reward_result(
    xp_awarded: int = 0,
    items_granted: list[dict] | None = None,
    errors: list[str] | None = None,
    already_rewarded: bool = False,
    mob_unknown: bool = False,
) -> dict:
    """Construct a consistent reward-result dict."""
    return {
        "xp_awarded": xp_awarded,
        "items_granted": items_granted if items_granted is not None else [],
        "errors": errors if errors is not None else [],
        "already_rewarded": already_rewarded,
        "mob_unknown": mob_unknown,
        "success": len(errors or []) == 0 and not already_rewarded and not mob_unknown,
    }
# ---------------------------------------------------------------------------
# Duplicate-Prevention
# ---------------------------------------------------------------------------

# Track rewarded via instance attribute (not id(), which CPython reuses).


def _has_been_rewarded(mob_cd: CharacterData) -> bool:
    """Return True if this mob instance has already yielded rewards."""
    return getattr(mob_cd, "_rewarded", False)


def _mark_rewarded(mob_cd: CharacterData) -> None:
    """Mark a mob instance as rewarded so it cannot be looted twice."""
    mob_cd._rewarded = True


def clear_rewarded_mob(mob_cd: CharacterData) -> None:
    """Clear the rewarded flag for a mob instance (e.g. on respawn)."""
    mob_cd._rewarded = False


def clear_all_rewarded() -> None:
    """No-op kept for interface compat — flags are per-instance."""
    pass


# ---------------------------------------------------------------------------
# RNG hooks — replaceable for deterministic testing
# ---------------------------------------------------------------------------

_rng_random: callable = random.random
_rng_randint: callable = random.randint


def _random() -> float:
    """Return a float in [0.0, 1.0).  Hook for test RNG injection."""
    return _rng_random()


def _randint(a: int, b: int) -> int:
    """Return an int in [a, b] inclusive.  Hook for test RNG injection."""
    return _rng_randint(a, b)

# ---------------------------------------------------------------------------
# Loot Roll
# ---------------------------------------------------------------------------

def _roll_loot_entry(entry: dict) -> dict | None:
    """Evaluate a single loot-table entry.

    entry keys:
        item_id   — str
        chance    — float in [0.0, 1.0]; 1.0 = guaranteed
        quantity  — int, or (min, max) tuple for range

    Returns:
        {item_id, quantity} if the drop succeeds, or None.
    """
    chance = entry.get("chance", 1.0)
    if chance < 1.0:
        if _random() >= chance:
            return None  # failed chance roll

    qty = entry.get("quantity", 1)
    if isinstance(qty, (list, tuple)):
        low, high = qty
        if low == high:
            qty = low
        else:
            qty = _randint(low, high)

    return {"item_id": entry["item_id"], "quantity": max(1, int(qty))}


def _roll_loot_table(loot_table: list[dict]) -> list[dict]:
    """Roll every entry in a loot table. Returns list of successful drops."""
    drops = []
    for entry in loot_table:
        result = _roll_loot_entry(entry)
        if result is not None:
            drops.append(result)
    return drops
# ---------------------------------------------------------------------------
# Reward Calculation & Granting
# ---------------------------------------------------------------------------

def calculate_mob_rewards(mob_cd: CharacterData) -> dict:
    """Calculate the rewards (XP + loot) a mob would yield on death.

    Does NOT apply rewards — just computes what they would be.

    Returns the structured reward result dict.
    """
    # Already rewarded?
    if _has_been_rewarded(mob_cd):
        return _make_reward_result(already_rewarded=True)

    # Look up mob definition via profession_id (which stores the mob_id).
    mob_id = mob_cd.profession_id
    definition = get_mob_definition(mob_id)
    if definition is None:
        return _make_reward_result(mob_unknown=True)

    # XP reward
    xp_reward = definition.get("xp_reward", 0)

    # Loot table
    # Precedence:
    #   1. mob_cd.loot_table_id  →  get_loot_table()  (named registry table)
    #   2. definition["loot_table"]                     (inline mob-definition table)
    loot_table_id = getattr(mob_cd, "loot_table_id", None)
    if loot_table_id:
        resolved = get_loot_table(loot_table_id)
        if resolved is not None:
            loot_table = resolved
        else:
            loot_table = definition.get("loot_table", [])
    else:
        loot_table = definition.get("loot_table", [])
    drops = _roll_loot_table(loot_table)

    # Validate item_ids — collect errors but still return valid items
    errors = []
    valid_drops = []
    for drop in drops:
        if item_exists(drop["item_id"]):
            valid_drops.append(drop)
        else:
            errors.append(f"Unknown item_id in loot table: '{drop['item_id']}'")

    return _make_reward_result(
        xp_awarded=xp_reward,
        items_granted=valid_drops,
        errors=errors,
    )


def grant_mob_rewards(
    killer_cd: CharacterData,
    mob_cd: CharacterData,
) -> dict:
    """Calculate and grant rewards for killing a mob.

    Awards XP through the progression API and adds items to the
    killer's inventory.

    Marks the mob as rewarded so it cannot be looted twice.

    Returns the structured reward result dict.
    """
    result = calculate_mob_rewards(mob_cd)

    if result["already_rewarded"] or result["mob_unknown"]:
        return result

    # Award XP
    if result["xp_awarded"] > 0:
        award_xp(killer_cd, result["xp_awarded"])

    # Grant items
    for drop in result["items_granted"]:
        killer_cd.add_item(drop["item_id"], drop["quantity"])

    # Mark as rewarded
    _mark_rewarded(mob_cd)

    return result


def reward_mob_kill(
    killer_cd: CharacterData,
    mob_cd: CharacterData,
) -> dict:
    """Convenience: calculate + grant rewards for a mob kill.

    Returns the same structured result as grant_mob_rewards.
    """
    return grant_mob_rewards(killer_cd, mob_cd)
    return _rng_randint(a, b)