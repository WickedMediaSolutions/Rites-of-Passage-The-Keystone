"""
Rites of Passage — World Integration Layer

Bridges the plain-Python data layer (spawner, mobs, rooms) to actual
Evennia database objects.  This module is responsible for:

* Managing the spawn registry lifecycle tied to Evennia rooms
* Creating and removing NPC objects in rooms
* Running the spawn ticker
* Idempotent world initialization (safe to call on server reload)

This module imports Evennia — it is NOT plain-Python testable on its own.
Core logic that can be unit-tested lives in world/data/world_rooms.py.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Spawn Registry Bridge
# ---------------------------------------------------------------------------

def init_spawn_registry_from_config(configs: list[dict] | None = None) -> dict[str, list]:
    """
    Initialise the mob_spawner registry from a list of spawn configs.

    Returns a dict mapping room_id -> list of spawn_ids that were created.

    Idempotent: if a spawn_id already exists, it is skipped.
    """
    from world.data.mob_spawner import create_spawn, clear_all_spawns
    from world.data.world_rooms import SILVERMERE_SPAWNS

    if configs is None:
        configs = SILVERMERE_SPAWNS

    room_map: dict[str, list] = {}

    for cfg in configs:
        spawn_id = cfg["spawn_id"]
        mob_id = cfg["mob_id"]
        room_id = cfg["room_id"]
        respawn_seconds = cfg.get("respawn_seconds", 300)

        result = create_spawn(spawn_id, mob_id, room_id, respawn_seconds)
        if isinstance(result, str):
            # Already exists or error — skip quietly
            # Still track the room for idempotency
            if spawn_id_already_exists(spawn_id):
                room_map.setdefault(room_id, []).append(spawn_id)
            continue

        room_map.setdefault(room_id, []).append(spawn_id)

    return room_map


def spawn_id_already_exists(spawn_id: str) -> bool:
    """Check whether a spawn_id is already registered (idempotency guard)."""
    from world.data.mob_spawner import get_spawn
    return get_spawn(spawn_id) is not None


def clear_all_integration_spawns() -> None:
    """Remove all spawns from the registry.  Safe for test teardown."""
    from world.data.mob_spawner import clear_all_spawns
    clear_all_spawns()


# ---------------------------------------------------------------------------
# Evennia NPC Bridge
# ---------------------------------------------------------------------------

def create_npc_from_spawn(spawn_id: str, room) -> object | None:
    """
    Create (or retrieve) an Evennia NPC Character object for a spawn.

    The NPC's game data is synchronised with the spawn's live mob
    CharacterData so combat/ai work seamlessly.

    Args:
        spawn_id: The stable spawn identifier.
        room: An Evennia Room object where the NPC should be placed.

    Returns:
        The Evennia Character/NPC object, or None on failure.
    """
    from evennia import create_object
    from world.data.mob_spawner import get_live_mob, get_spawn
    from world.data.mobs import get_mob_definition

    record = get_spawn(spawn_id)
    if record is None:
        return None

    mob_cd = get_live_mob(spawn_id)
    if mob_cd is None:
        return None

    # Propagate the mob definition's loot_table_id onto the live mob so
    # reward resolution can pick it up via mob_cd.loot_table_id.
    mob_id = record.get("mob_id")
    definition = get_mob_definition(mob_id)
    if definition is not None and definition.get("loot_table_id") is not None:
        mob_cd.loot_table_id = definition["loot_table_id"]

    # Check if an NPC already exists for this spawn.
    npc = _find_npc_for_spawn(spawn_id, room)
    if npc is not None:
        # Sync game data from the live mob CharacterData.
        _sync_npc_game_data(npc, mob_cd)
        return npc

    # Create a new NPC.
    npc = create_object(
        typeclass="typeclasses.characters.Character",
        key=mob_cd.name,
        location=room,
    )
    if npc is None:
        return None

    # Tag it as a world-spawned NPC.
    npc.attributes.add("world_spawn_id", spawn_id)
    npc.attributes.add("world_npc", True)
    npc.tags.add("world_npc", category="world_role")

    # Sync game data.
    _sync_npc_game_data(npc, mob_cd)
    try_start_mob_combat(npc, spawn_id)

    return npc


def create_item_from_spawn(room, forge_identity: str) -> object | None:
    """
    Create an Evennia world-item Object from a Forge item identity.

    The item is placed in the given room and tagged as a persistent
    world item so the world system can track and manage it.

    Args:
        room: An Evennia Room object where the item should be placed.
        forge_identity: The Forge item identity (recipe key, template
                        name, etc.) used to identify this item type.

    Returns:
        The Evennia Object, or None on failure.
    """
    from evennia import create_object

    if room is None:
        return None

    obj = create_object(
        typeclass="typeclasses.objects.Object",
        key=forge_identity,
        location=room,
    )
    if obj is None:
        return None

    # Tag and mark as a world-spawned item.
    obj.attributes.add("world_item", True)
    obj.tags.add("world_item", category="world_role")

    # Store the forge identity for later lookup.
    obj.attributes.add("forge_identity", forge_identity)

    return obj


def place_item_spawn(record: dict) -> list:
    """
    Resolve and place world-item objects from an item-spawn record.

    Args:
        record: An item-spawn record dict with keys:
            spawn_id, location_id, item_id, quantity,
            respawn_seconds, enabled.

    Returns:
        A list of Evennia Object(s) created.  Empty list when:
        - enabled is False
        - the target room cannot be found
        - item creation fails for every copy
    """
    # ---- Enabled guard ------------------------------------------------
    if not record.get("enabled", False):
        return []

    # ---- Resolve target room ------------------------------------------
    location_id = record.get("location_id")
    if location_id is None:
        return []

    room = _default_room_search(location_id)
    if room is None:
        return []

    # ---- Create item copies -------------------------------------------
    item_id: str = record.get("item_id", record.get("spawn_id", ""))
    quantity: int = record.get("quantity", 1)

    created: list = []
    for _ in range(max(quantity, 1)):
        obj = create_item_from_spawn(room, item_id)
        if obj is not None:
            created.append(obj)

    return created


def remove_dead_npc(spawn_id: str, room) -> None:
    """
    Remove a dead NPC from a room.  Called when the spawn system
    detects the mob has died.

    Does NOT delete the Evennia object — just moves it to None-location
    so it no longer appears in the room.
    """
    npc = _find_npc_for_spawn(spawn_id, room)
    if npc is not None:
        npc.location = None


def respawn_npc_in_room(spawn_id: str, room) -> object | None:
    """
    After a respawn, create a fresh NPC in the room for the new live mob.

    Removes any orphaned NPC first, then creates the new one.
    """
    remove_dead_npc(spawn_id, room)
    return create_npc_from_spawn(spawn_id, room)


# ---------------------------------------------------------------------------
# Room Population
# ---------------------------------------------------------------------------

def populate_room(room) -> list:
    """
    Populate a single Evennia Room with all configured NPC spawns.

    Uses the spawn registry — spawns must already be created via
    init_spawn_registry_from_config() before calling this.

    Returns a list of spawn_ids that were successfully placed.
    """
    from world.data.world_rooms import get_spawns_for_room

    room_id = _get_room_world_id(room)
    if room_id is None:
        return []

    configs = get_spawns_for_room(room_id)
    if not configs:
        return []

    placed = []
    for cfg in configs:
        spawn_id = cfg["spawn_id"]
        npc = create_npc_from_spawn(spawn_id, room)
        if npc is not None:
            placed.append(spawn_id)

    return placed


def populate_all_configured_rooms(room_search_fn=None) -> dict[str, list]:
    """
    Populate every room that has spawn configs.

    Args:
        room_search_fn: Optional function(room_id) -> Room object.
            If None, uses Evennia's search_object.

    Returns:
        Dict mapping room_id -> list of spawn_ids placed.
    """
    from world.data.world_rooms import get_all_spawn_room_ids

    if room_search_fn is None:
        room_search_fn = _default_room_search

    results: dict[str, list] = {}
    processed_spawns: set[str] = set()

    for room_id in sorted(get_all_spawn_room_ids()):
        room = room_search_fn(room_id)
        if room is None:
            continue
        placed = populate_room(room)
        if placed:
            # Deduplicate — each spawn should only live in one room
            unique = [s for s in placed if s not in processed_spawns]
            if unique:
                results[room_id] = unique
                processed_spawns.update(unique)

    return results


# ---------------------------------------------------------------------------
# Spawn Ticker
# ---------------------------------------------------------------------------

def world_spawn_tick(room_search_fn=None) -> list[dict]:
    """
    Run one tick of the world spawn system.

    1. Detects dead mobs and marks spawn records.
    2. Removes dead NPCs from rooms.
    3. Respawns mobs whose timer has elapsed.
    4. Creates new NPCs in rooms for respawned mobs.

    Returns a list of action dicts describing what happened.
    """
    from world.data.mob_spawner import tick_all_spawns, get_spawn

    if room_search_fn is None:
        room_search_fn = _default_room_search

    results = tick_all_spawns()
    actions = []

    for result in results:
        spawn_id = result["spawn_id"]
        action = result["action"]
        record = get_spawn(spawn_id)
        room_id = record["location_id"] if record else None

        if action == "marked_dead" and room_id is not None:
            room = room_search_fn(room_id)
            if room is not None:
                remove_dead_npc(spawn_id, room)
                actions.append({
                    "spawn_id": spawn_id,
                    "action": "npc_removed",
                    "room_id": room_id,
                })

        elif action == "respawned" and room_id is not None:
            room = room_search_fn(room_id)
            if room is not None:
                npc = respawn_npc_in_room(spawn_id, room)
                actions.append({
                    "spawn_id": spawn_id,
                    "action": "npc_respawned",
                    "room_id": room_id,
                    "success": npc is not None,
                })

    return actions


# ---------------------------------------------------------------------------
# Full Initialization (call once on server start/reload)
# ---------------------------------------------------------------------------

def initialize_world_population(room_search_fn=None) -> dict:
    """
    Full idempotent world population initialisation.

    1. Clears any stale spawn registry entries.
    2. Creates spawn points from config.
    3. Populates rooms with NPCs.

    Safe to call on server start or reload — existing NPCs are
    left alone; only new ones are created.

    Returns a summary dict with keys:
        spawns_created, rooms_populated, npcs_placed, errors.
    """
    from world.data.mob_spawner import clear_all_spawns
    from world.data.world_rooms import SILVERMERE_SPAWNS

    summary = {
        "spawns_created": 0,
        "rooms_populated": 0,
        "npcs_placed": 0,
        "errors": [],
    }

    if room_search_fn is None:
        room_search_fn = _default_room_search

    # Always start fresh to avoid stale spawns from prior server runs.
    clear_all_spawns()

    # Create spawn registry entries.
    room_map = init_spawn_registry_from_config(SILVERMERE_SPAWNS)
    summary["spawns_created"] = sum(len(v) for v in room_map.values())

    # Populate rooms.
    for room_id, spawn_ids in room_map.items():
        room = room_search_fn(room_id)
        if room is None:
            summary["errors"].append(
                f"Room '{room_id}' not found — "
                f"skipping {len(spawn_ids)} spawn(s)."
            )
            continue

        placed = populate_room(room)
        summary["rooms_populated"] += 1
        summary["npcs_placed"] += len(placed)

        missing = len(spawn_ids) - len(placed)
        if missing > 0:
            summary["errors"].append(
                f"Room '{room_id}': {missing}/{len(spawn_ids)} "
                f"NPCs could not be placed."
            )

    return summary


# ---------------------------------------------------------------------------
# Mob Combat Ticker
# ---------------------------------------------------------------------------

_COMBAT_TICKER_IDSTRING = "rop_combat"

# Maps spawn_id -> Evennia NPC object so the combat tick callback can
# synchronise game data back to the database object every round.
_combat_npcs: dict[str, object] = {}

# Maps spawn_id -> callback instance so TICKER_HANDLER.add / .remove
# receive the exact same callable object and produce matching store keys.
_combat_callbacks: dict[str, object] = {}


class _CombatTickerCallback:
    """Callable wrapper whose ``__name__`` is stable for Evennia's
    TickerHandler store-key generation."""

    __name__ = "_combat_tick_callback"

    def __init__(self, spawn_id: str) -> None:
        self.spawn_id = spawn_id

    def __call__(self) -> None:
        _combat_tick_callback(self.spawn_id)


# ---------------------------------------------------------------------------
# Tick identity helpers
# ---------------------------------------------------------------------------


def _combat_ticker_id(spawn_id: str) -> str:
    """Return the unique Evennia TickerHandler idstring for a spawn."""
    return f"{_COMBAT_TICKER_IDSTRING}_{spawn_id}"


# ---------------------------------------------------------------------------
# NPC registry (used by the tick callback to sync game data)
# ---------------------------------------------------------------------------


def _set_combat_npc(spawn_id: str, npc: object) -> None:
    """Register the Evennia NPC object that backs *spawn_id*."""
    _combat_npcs[spawn_id] = npc


def _get_combat_npc(spawn_id: str) -> object | None:
    """Return the registered Evennia NPC for *spawn_id*, or None."""
    return _combat_npcs.get(spawn_id)


def _clear_combat_npc(spawn_id: str) -> None:
    """Remove the registered Evennia NPC for *spawn_id*."""
    _combat_npcs.pop(spawn_id, None)


# ---------------------------------------------------------------------------
# Interval calculation
# ---------------------------------------------------------------------------


def _combat_interval_for_spawn(spawn_id: str) -> float:
    """Calculate the effective combat-round interval for *spawn_id*.

    Reads ``attackSpeed`` from the mob definition's ``mw_combat`` block.
    AttackSpeed is a multiplier:

        * 1.0  → normal speed
        * >1.0 → faster (shorter interval)
        * 0 < value < 1.0 → slower (longer interval)

    Effective interval = ``COMBAT_ROUND_INTERVAL / attackSpeed``,
    clamped to a minimum of **1 second**.

    Missing, invalid, or ≤0 ``attackSpeed`` defaults to **1.0**.
    """
    from world.data.mob_spawner import get_live_mob
    from world.data.mobs import get_mob_definition
    from world.data.mob_ai import COMBAT_ROUND_INTERVAL

    attack_speed: float = 1.0

    live_mob = get_live_mob(spawn_id)
    if live_mob is not None:
        definition = get_mob_definition(live_mob.profession_id)
        if definition is not None:
            mw_combat = definition.get("mw_combat", {})
            if isinstance(mw_combat, dict):
                raw = mw_combat.get("attackSpeed")
                if isinstance(raw, (int, float)) and raw > 0:
                    attack_speed = float(raw)

    interval = COMBAT_ROUND_INTERVAL / attack_speed
    return max(interval, 1.0)


# ---------------------------------------------------------------------------
# Ticker lifecycle
# ---------------------------------------------------------------------------


def try_start_mob_combat(npc, spawn_id: str) -> bool:
    """Attempt to start AI-driven combat for the mob identified by *spawn_id*.

    This is the single entry-point that wires together the plain-Python
    mob AI layer (can_engage / select_hostile_target / engage_target) and
    the Evennia ticker lifecycle (start_mob_combat_ticker).

    The authoritative mob state is always resolved from the spawn registry
    via ``get_live_mob(spawn_id)`` — the *npc* parameter is only used for
    room-location (player lookup) and ticker registration.

    Returns True when a valid hostile target was acquired and the combat
    ticker was successfully started; False otherwise (no live mob, already
    in combat, mob cannot engage, no valid target, or ticker failure).
    """
    from world.data.character_data import CharacterData
    from world.data.mob_spawner import get_live_mob
    from world.data.mob_ai import (
        can_engage,
        select_hostile_target,
        engage_target,
        force_end_combat,
    )

    # 1. Resolve the authoritative live mob.
    live_mob = get_live_mob(spawn_id)
    if live_mob is None:
        return False

    # 2. Already in combat?
    if _combat_ticker_active(spawn_id):
        return False

    # 3. Mob capable of engaging?
    if not can_engage(live_mob):
        return False

    # 4. Collect valid PLAYER CharacterData objects from the room.
    player_cds: list[CharacterData] = []
    for obj in npc.location.contents:
        # Skip the NPC itself.
        if obj is npc:
            continue
        # Skip objects marked as world NPCs (no mob-vs-mob).
        if obj.attributes.get("world_npc"):
            continue
        # Skip objects without a usable .game CharacterData.
        try:
            cd = obj.game
        except Exception:
            continue
        if cd is None or not isinstance(cd, CharacterData):
            continue
        # Do not include dead players.
        if not cd.is_alive():
            continue
        player_cds.append(cd)

    # 5. Select a hostile target.
    target_cd = select_hostile_target(live_mob, player_cds)
    if target_cd is None:
        return False

    # 6. Begin AI engagement.
    err = engage_target(live_mob, target_cd)
    if err is not None:
        return False

    # 7. Start the combat ticker.
    try:
        ticker_ok = start_mob_combat_ticker(npc, spawn_id)
    except Exception:
        # Roll back the AI engagement so the mob isn't left in a
        # half-engaged state with no ticker driving its rounds.
        force_end_combat(live_mob)
        raise
    if not ticker_ok:
        # Roll back the AI engagement so the mob isn't left in a
        # half-engaged state with no ticker driving its rounds.
        force_end_combat(live_mob)
        return False

    return True


def start_mob_combat_ticker(npc, spawn_id: str) -> bool:
    """Start the combat ticker for *spawn_id*.

    Returns True if the ticker was successfully subscribed;
    False if no live mob exists or a ticker is already active.
    """
    from world.data.mob_spawner import get_live_mob
    from evennia import TICKER_HANDLER

    live_mob = get_live_mob(spawn_id)
    if live_mob is None:
        return False

    if _combat_ticker_active(spawn_id):
        return False

    interval = _combat_interval_for_spawn(spawn_id)

    cb = _CombatTickerCallback(spawn_id)

    _combat_callbacks[spawn_id] = cb
    _set_combat_npc(spawn_id, npc)

    try:
        TICKER_HANDLER.add(
            interval=interval,
            callback=cb,
            idstring=_combat_ticker_id(spawn_id),
            persistent=False,
        )
    except Exception:
        _combat_callbacks.pop(spawn_id, None)
        _clear_combat_npc(spawn_id)
        raise

    return True


def _combat_ticker_active(spawn_id: str) -> bool:
    """Return True if a combat ticker is currently subscribed for *spawn_id*."""
    try:
        from evennia import TICKER_HANDLER
    except ImportError:
        return False

    ticker_id = _combat_ticker_id(spawn_id)
    interval = _combat_interval_for_spawn(spawn_id)
    store_key = TICKER_HANDLER._store_key(
        spawn_id,
        None,
        interval,
        "_combat_tick_callback",
        ticker_id,
        False,
    )
    return store_key in TICKER_HANDLER.ticker_storage


def _combat_tick_callback(spawn_id: str) -> None:
    """Execute one combat round for *spawn_id*.

    Called by the Evennia TickerHandler at the spawn's effective combat
    interval.  Automatically stops the ticker when the live mob is gone
    or the combat round signals ``combat_ended``.
    """
    from world.data.mob_spawner import get_live_mob
    from world.data.mob_ai import execute_combat_round

    live_mob = get_live_mob(spawn_id)
    if live_mob is None:
        _stop_combat_ticker(spawn_id)
        return

    outcome = execute_combat_round(live_mob)

    # Sync the updated CharacterData back to the Evennia NPC so that
    # database attributes (HP, state, etc.) stay in sync.
    npc = _get_combat_npc(spawn_id)
    if npc is not None:
        _sync_npc_game_data(npc, live_mob)

    if outcome.get("combat_ended"):
        _stop_combat_ticker(spawn_id)


def _stop_combat_ticker(spawn_id: str) -> bool:
    """Stop the combat ticker for *spawn_id*.

    Returns True if a ticker was removed; False if none was running.
    """
    try:
        from evennia import TICKER_HANDLER
    except ImportError:
        return False

    if not _combat_ticker_active(spawn_id):
        return False

    try:
        interval = _combat_interval_for_spawn(spawn_id)
        ticker_id = _combat_ticker_id(spawn_id)
        callback = _combat_callbacks.pop(spawn_id, None)
        TICKER_HANDLER.remove(
            interval=interval,
            callback=callback,
            idstring=ticker_id,
        )
        _clear_combat_npc(spawn_id)
        return True
    except KeyError:
        return False


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _get_room_world_id(room) -> str | None:
    """Extract the stable world_room_id from an Evennia Room object."""
    if room is None:
        return None
    try:
        return room.attributes.get("world_room_id")
    except Exception:
        return getattr(room, "room_id", None)


def _find_npc_for_spawn(spawn_id: str, room) -> object | None:
    """
    Find an existing NPC in a room that belongs to the given spawn_id.

    Searches the room's contents for an object tagged with
    world_spawn_id == spawn_id.
    """
    if room is None:
        return None
    try:
        for obj in room.contents:
            if obj.attributes.get("world_spawn_id") == spawn_id:
                return obj
    except Exception:
        pass
    return None


def _sync_npc_game_data(npc, mob_cd) -> None:
    """
    Synchronise an Evennia NPC's game data from a mob CharacterData.

    The NPC's persistent game-data attribute is overwritten with
    the spawn's live mob data so combat resolution uses the correct
    HP/stats/equipment.
    """
    try:
        npc.attributes.add("rop_game_data", mob_cd.to_dict())
        # Invalidate any cached CharacterData so the next .game access
        # reloads from the attribute we just set.
        if hasattr(npc, "_game_cache"):
            del npc._game_cache
    except Exception:
        pass


def _default_room_search(room_id: str):
    """
    Default Evennia room search by world_room_id attribute.

    Used as the fallback when no room_search_fn is provided.
    """
    from evennia import search_object
    matches = search_object(
        room_id,
        attribute_name="world_room_id",
    )
    for obj in matches:
        if obj.attributes.get("world_room_id") == room_id:
            return obj
    return None
