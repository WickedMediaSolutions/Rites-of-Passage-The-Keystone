"""
Rites of Passage — Mob Spawner & Respawn Manager

Plain-Python spawn lifecycle management.  Creates and monitors live mob
``CharacterData`` instances, detects death, and schedules respawns.

All functions are directly testable without an Evennia server.

Design constraints (Phase 11 foundation only):
    • No loot
    • No XP/rewards
    • No quests
    • No shops
    • No pathfinding
    • No advanced AI beyond Phase 10
"""

from world.data.character_data import CharacterData
from world.data.enums import CharacterState
from world.data.mob_ai import force_end_combat
from world.data.mobs import create_mob_data, get_mob_definition


# ---------------------------------------------------------------------------
# Respawn Constants [PLACEHOLDER]
# ---------------------------------------------------------------------------

# Default seconds between mob death and respawn.  [PLACEHOLDER]
DEFAULT_RESPAWN_SECONDS = 300

# Sentinel value — setting respawn_seconds to this disables respawn.
RESPAWN_DISABLED = -1


# ---------------------------------------------------------------------------
# Internal Spawn Registry
# ---------------------------------------------------------------------------

# module-level spawn registry:  spawn_id -> dict (SpawnRecord)
_spawns: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# SpawnRecord shape (documented; not a class)
# ---------------------------------------------------------------------------
#
#   spawn_id         — str, stable identifier for this spawn point
#   mob_id           — str, canonical mob definition ID
#   location_id      — str, identifier for the room/area this mob belongs to
#   live_mob         — CharacterData | None, the current live mob instance
#   respawn_seconds  — int, seconds to wait before respawning (or RESPAWN_DISABLED)
#   is_dead          — bool, True if the current mob has died
#   death_at         — float | None, monotonic timestamp when mob died
#   active           — bool, False if the spawn has been removed
#   quantity         — int, number of mobs this spawn point represents (default 1)
#


def _monotonic() -> float:
    """Return a monotonic timestamp (seconds).  Replaceable for testing."""
    import time
    return time.monotonic()


# ---------------------------------------------------------------------------
# Spawn Management
# ---------------------------------------------------------------------------


def create_spawn(
    spawn_id: str,
    mob_id: str,
    location_id: str = "unknown",
    respawn_seconds: int = DEFAULT_RESPAWN_SECONDS,
    quantity: int = 1,
    enabled: bool = True,
) -> CharacterData | list[CharacterData] | str:
    """Create a new spawn point and immediately instantiate the mob(s).

    Args:
        spawn_id: Stable identifier for this spawn (e.g. "rat_01").
        mob_id: Canonical mob definition ID (must be in MOB_REGISTRY).
        location_id: Room/area identifier for respawn location.
        respawn_seconds: Respawn delay in seconds, or RESPAWN_DISABLED.
        quantity: Number of mobs this spawn point represents (default 1).
        enabled: Whether this spawn is active from the start (default True).

    Returns:
        The live ``CharacterData`` instance on success (quantity=1), a
        list of ``CharacterData`` instances (quantity>1), or an error string.
    """
    # ---- Duplicate prevention ------------------------------------------
    existing = _spawns.get(spawn_id)
    if existing is not None and existing.get("active", False):
        return f"Spawn '{spawn_id}' already exists."

    # ---- Validate mob definition ---------------------------------------
    if get_mob_definition(mob_id) is None:
        return f"Unknown mob_id: '{mob_id}'."

    # ---- Create mob(s) -------------------------------------------------
    mobs: list[CharacterData] = []
    for _ in range(max(quantity, 1)):
        mob_cd = create_mob_data(mob_id)
        if mob_cd is None:
            return f"Failed to create mob from '{mob_id}'."
        mobs.append(mob_cd)

    # ---- Build spawn record --------------------------------------------
    _spawns[spawn_id] = {
        "spawn_id": spawn_id,
        "mob_id": mob_id,
        "location_id": location_id,
        "live_mob": mobs[0],
        "live_mobs": mobs,
        "respawn_seconds": respawn_seconds,
        "is_dead": False,
        "death_at": None,
        "active": enabled,
        "quantity": quantity,
    }

    return mobs[0] if quantity == 1 else mobs


def remove_spawn(spawn_id: str) -> str | None:
    """Permanently remove a spawn point.  Cleans up AI state.

    Returns None on success, or an error string if not found.
    """
    record = _spawns.get(spawn_id)
    if record is None or not record.get("active", False):
        return f"Spawn '{spawn_id}' not found."

    # Clean AI state on live mob(s)
    live_mobs = record.get("live_mobs")
    if live_mobs is not None:
        for mob in live_mobs:
            force_end_combat(mob)
    else:
        live = record.get("live_mob")
        if live is not None:
            force_end_combat(live)

    del _spawns[spawn_id]
    return None


def get_spawn(spawn_id: str) -> dict | None:
    """Return the spawn record dict for a spawn_id, or None."""
    record = _spawns.get(spawn_id)
    if record is None or not record.get("active", False):
        return None
    return record


def get_live_mob(spawn_id: str) -> CharacterData | None:
    """Return the live mob CharacterData for a spawn, or None."""
    record = get_spawn(spawn_id)
    if record is None:
        return None
    return record.get("live_mob")


def set_respawn_seconds(spawn_id: str, seconds: int) -> str | None:
    """Change the respawn delay for a spawn point.

    Use RESPAWN_DISABLED to prevent respawning.  Does not affect an
    already-in-progress respawn timer.

    Returns None on success, or an error string.
    """
    record = get_spawn(spawn_id)
    if record is None:
        return f"Spawn '{spawn_id}' not found."
    record["respawn_seconds"] = seconds
    return None


# ---------------------------------------------------------------------------
# Death Detection & Respawn
# ---------------------------------------------------------------------------


def mark_dead_if_needed(spawn_id: str) -> bool:
    """Check if a spawn's live mob is dead and mark its record.

    Call this periodically (or after combat events) to keep the spawn
    record in sync with the live CharacterData.

    Returns True if the mob was just detected as dead this call.
    """
    record = get_spawn(spawn_id)
    if record is None:
        return False

    if record.get("is_dead"):
        return False  # already marked

    # ---- Single mob fallback ----------------------------------------------
    mobs = record.get("live_mobs")
    if mobs is None:
        # Preserve existing behaviour for records without live_mobs
        live = record.get("live_mob")
        if live is None:
            return False
        if not live.is_alive() or live.state == CharacterState.DEAD:
            force_end_combat(live)
            record["is_dead"] = True
            record["death_at"] = _monotonic()
            return True
        return False

    # ---- Quantity > 1 — evaluate every mob --------------------------------
    all_dead = True
    for mob in mobs:
        if not mob.is_alive() or mob.state == CharacterState.DEAD:
            force_end_combat(mob)
        else:
            all_dead = False

    if all_dead:
        record["is_dead"] = True
        record["death_at"] = _monotonic()
        return True

    return False


def is_spawn_dead(spawn_id: str) -> bool:
    """Return True if the spawn's live mob is dead."""
    record = get_spawn(spawn_id)
    if record is None:
        return False
    return record.get("is_dead", False)


def try_respawn(spawn_id: str) -> CharacterData | list[CharacterData] | str | None:
    """Attempt to respawn a dead mob.

    Checks whether the respawn timer has elapsed and the spawn is
    configured for respawning.  If so, creates fresh CharacterData
    instances from the canonical mob definition and replaces the live
    mob(s).  For quantity=1 the new mob is returned; for quantity>1 a
    list of the new mobs is returned.

    Returns:
        The new ``CharacterData`` on successful respawn (quantity=1).
        A list of new ``CharacterData`` instances (quantity>1).
        An error string for configuration issues.
        None if not yet time to respawn (or not dead).
    """
    record = get_spawn(spawn_id)
    if record is None:
        return f"Spawn '{spawn_id}' not found."

    # ---- Already alive? ------------------------------------------------
    if not record.get("is_dead", False):
        # Double-check the live mob hasn't died without being marked
        mark_dead_if_needed(spawn_id)
        if not record.get("is_dead", False):
            return None  # still alive, nothing to do

    # ---- Respawn disabled? --------------------------------------------
    delay = record.get("respawn_seconds", DEFAULT_RESPAWN_SECONDS)
    if delay == RESPAWN_DISABLED:
        return "Respawn is disabled for this spawn."

    # ---- Timer check ---------------------------------------------------
    death_at = record.get("death_at")
    if death_at is not None:
        elapsed = _monotonic() - death_at
        if elapsed < delay:
            return None  # not yet time

    # ---- Respawn — create fresh mob(s) from definition -----------------
    mob_id = record["mob_id"]
    qty = max(record.get("quantity", 1), 1)
    new_mobs: list[CharacterData] = []
    for _ in range(qty):
        new_mob = create_mob_data(mob_id)
        if new_mob is None:
            # Mob definition may have been removed since spawn was created.
            return f"Cannot respawn: mob definition '{mob_id}' no longer exists."
        new_mobs.append(new_mob)

    record["live_mob"] = new_mobs[0]
    record["live_mobs"] = new_mobs
    record["is_dead"] = False
    record["death_at"] = None

    return new_mobs[0] if qty == 1 else new_mobs


def force_respawn(spawn_id: str) -> CharacterData | list[CharacterData] | str:
    """Respawn a mob immediately, bypassing the respawn timer.

    Works even if the mob is not yet dead (replaces the current live
    mob with a fresh one).

    Returns the new CharacterData on success (quantity=1), a list of
    CharacterData instances (quantity>1), or an error string.
    """
    record = get_spawn(spawn_id)
    if record is None:
        return f"Spawn '{spawn_id}' not found."

    # Clean old mobs' AI state
    mobs = record.get("live_mobs")
    if mobs is None:
        old = record.get("live_mob")
        if old is not None:
            force_end_combat(old)
    else:
        for mob in mobs:
            force_end_combat(mob)

    mob_id = record["mob_id"]
    qty = max(record.get("quantity", 1), 1)
    new_mobs: list[CharacterData] = []
    for _ in range(qty):
        new_mob = create_mob_data(mob_id)
        if new_mob is None:
            return f"Cannot respawn: mob definition '{mob_id}' no longer exists."
        new_mobs.append(new_mob)

    record["live_mob"] = new_mobs[0]
    record["live_mobs"] = new_mobs
    record["is_dead"] = False
    record["death_at"] = None

    return new_mobs[0] if qty == 1 else new_mobs


# ---------------------------------------------------------------------------
# Bulk Operations
# ---------------------------------------------------------------------------


def tick_all_spawns() -> list[dict]:
    """Run one tick across all spawns: detect death, try respawn.

    Called periodically by an Evennia-side scheduler or game loop.

    Returns a list of result dicts describing what happened:
        {spawn_id, action: "marked_dead"|"respawned"|"nothing"}
    """
    results = []
    for spawn_id in list(_spawns.keys()):
        record = _spawns.get(spawn_id)
        if record is None or not record.get("active", False):
            continue

        # Step 1: detect death
        newly_dead = mark_dead_if_needed(spawn_id)
        if newly_dead:
            results.append({"spawn_id": spawn_id, "action": "marked_dead"})
            # No respawn attempt this tick — death was just detected
            continue

        # Step 2: try respawn if dead
        if record.get("is_dead"):
            result = try_respawn(spawn_id)
            if isinstance(result, (CharacterData, list)):
                results.append({"spawn_id": spawn_id, "action": "respawned"})
            # else: not yet time or disabled — nothing to report

    return results


def get_active_spawns() -> list[dict]:
    """Return a list of all active spawn records (shallow copies)."""
    return [dict(r) for r in _spawns.values() if r.get("active", False)]


# ---------------------------------------------------------------------------
# Internal Item Spawn Registry
# ---------------------------------------------------------------------------

# module-level item spawn registry:  spawn_id -> dict (ItemSpawnRecord)
_item_spawns: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# ItemSpawnRecord shape (documented; not a class)
# ---------------------------------------------------------------------------
#
#   spawn_id         — str, stable identifier for this item spawn point
#   location_id      — str, identifier for the room/area this item belongs to
#   item_id          — str, Forge item identity (canonical item definition ID)
#   quantity         — int, number of items produced on each spawn cycle
#   respawn_seconds  — int, seconds to wait before respawning (or RESPAWN_DISABLED)
#   enabled          — bool, whether this spawn is currently active
#


# ---------------------------------------------------------------------------
# Item Spawn Management
# ---------------------------------------------------------------------------


def create_item_spawn(
    spawn_id: str,
    location_id: str,
    item_id: str,
    quantity: int = 1,
    respawn_seconds: int = DEFAULT_RESPAWN_SECONDS,
    enabled: bool = True,
) -> dict | str:
    """Create a new item-spawn record.

    Does **not** create a live Evennia item — this is a data-only record
    kept separate from the NPC ``_spawns`` registry.

    Args:
        spawn_id: Stable identifier for this item spawn point.
        location_id: Room/area identifier where the item should appear.
        item_id: Forge item identity (canonical item definition ID).
        quantity: Number of items produced on each spawn cycle (default 1).
        respawn_seconds: Seconds between respawns, or RESPAWN_DISABLED.
        enabled: Whether this spawn is active from the start (default True).

    Returns:
        The item-spawn record dict on success, or an error string.
    """
    # ---- Duplicate prevention ------------------------------------------
    existing = _item_spawns.get(spawn_id)
    if existing is not None and existing.get("enabled", False):
        return f"Item spawn '{spawn_id}' already exists."

    # ---- Build item-spawn record ---------------------------------------
    record = {
        "spawn_id": spawn_id,
        "location_id": location_id,
        "item_id": item_id,
        "quantity": quantity,
        "respawn_seconds": respawn_seconds,
        "enabled": enabled,
    }
    _item_spawns[spawn_id] = record

    return record


def get_item_spawn(spawn_id: str) -> dict | None:
    """Return the item-spawn record dict for a spawn_id, or None.

    Only returns records whose ``enabled`` flag is True.
    """
    record = _item_spawns.get(spawn_id)
    if record is None or not record.get("enabled", False):
        return None
    return record


def remove_item_spawn(spawn_id: str) -> str | None:
    """Permanently remove an item-spawn record.

    Returns None on success, or an error string if not found.
    """
    record = _item_spawns.get(spawn_id)
    if record is None or not record.get("enabled", False):
        return f"Item spawn '{spawn_id}' not found."

    del _item_spawns[spawn_id]
    return None


# ---------------------------------------------------------------------------
# Bulk Operations
# ---------------------------------------------------------------------------


def clear_all_spawns() -> None:
    """Remove all spawns.  Useful for testing teardown."""
    for record in list(_spawns.values()):
        live_mobs = record.get("live_mobs")
        if live_mobs is not None:
            for mob in live_mobs:
                force_end_combat(mob)
        else:
            live = record.get("live_mob")
            if live is not None:
                force_end_combat(live)
    _spawns.clear()
