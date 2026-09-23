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
