"""
Phase 17 — Rooms, World Integration & Population Tests

Tests cover:
- Room data module (stable IDs, spawn tables)
- Spawn configuration queries
- Mob spawner ↔ room integration logic
- World integration layer (plain-Python core logic)
- Idempotency / duplicate prevention
- Spawn lifecycle (create, mark dead, remove, respawn)
- Regression — existing systems unchanged
"""

import unittest

from world.data.character_data import CharacterData
from world.data.enums import CharacterState
from world.data.mob_spawner import (
    create_spawn,
    remove_spawn,
    get_spawn,
    get_live_mob,
    mark_dead_if_needed,
    is_spawn_dead,
    try_respawn,
    clear_all_spawns,
    tick_all_spawns,
    get_active_spawns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(name="Hero", race="human", prof="warrior"):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100; cd.hp = 100
    cd.max_mana = 100; cd.mana = 100
    cd.max_stamina = 100; cd.stamina = 100
    return cd


def setUpModule():
    clear_all_spawns()


def tearDownModule():
    clear_all_spawns()


class _CleanSpawnsMixin:
    def setUp(self):
        clear_all_spawns()

    def tearDown(self):
        clear_all_spawns()


# =============================================================================
# Room Data Module
# =============================================================================


class TestRoomData(unittest.TestCase):
    """Test world_rooms.py stable identifiers and spawn tables."""

    def test_spawn_config_count(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        self.assertGreaterEqual(len(SILVERMERE_SPAWNS), 1)
        for cfg in SILVERMERE_SPAWNS:
            self.assertIn("spawn_id", cfg)
            self.assertIn("mob_id", cfg)
            self.assertIn("room_id", cfg)
            self.assertIn("respawn_seconds", cfg)

    def test_named_rooms_exist(self):
        from world.data.world_rooms import NAMED_ROOMS
        self.assertIn("town_square", NAMED_ROOMS)
        self.assertEqual(NAMED_ROOMS["town_square"], "silvermere_town_square")

    def test_get_named_room(self):
        from world.data.world_rooms import get_named_room
        self.assertEqual(
            get_named_room("town_square"), "silvermere_town_square"
        )
        self.assertEqual(
            get_named_room("Town Square"), "silvermere_town_square"
        )

    def test_get_named_room_unknown(self):
        from world.data.world_rooms import get_named_room
        self.assertIsNone(get_named_room("nonexistent_room_alias"))

    def test_get_spawns_for_room(self):
        from world.data.world_rooms import get_spawns_for_room
        spawns = get_spawns_for_room("silvermere_town_square")
        self.assertGreaterEqual(len(spawns), 1)
        for s in spawns:
            self.assertEqual(s["room_id"], "silvermere_town_square")

    def test_get_spawns_for_room_none(self):
        from world.data.world_rooms import get_spawns_for_room
        spawns = get_spawns_for_room("nonexistent_room")
        self.assertEqual(spawns, [])

    def test_get_all_spawn_room_ids(self):
        from world.data.world_rooms import get_all_spawn_room_ids
        room_ids = get_all_spawn_room_ids()
        self.assertGreaterEqual(len(room_ids), 1)
        self.assertIn("silvermere_town_square", room_ids)

    def test_room_has_spawns(self):
        from world.data.world_rooms import room_has_spawns
        self.assertTrue(room_has_spawns("silvermere_town_square"))
        self.assertFalse(room_has_spawns("nonexistent_room"))

    def test_is_known_room_id(self):
        from world.data.world_rooms import is_known_room_id
        self.assertTrue(is_known_room_id("silvermere_town_square"))
        self.assertTrue(is_known_room_id("silvermere_l70_c41"))
        self.assertFalse(is_known_room_id("nonexistent"))

    def test_spawn_ids_are_unique(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        ids = [s["spawn_id"] for s in SILVERMERE_SPAWNS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_room_ids_valid_format(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        for s in SILVERMERE_SPAWNS:
            self.assertTrue(
                s["room_id"].startswith("silvermere_"),
                f"Invalid room_id format: {s['room_id']}",
            )

    def test_all_mob_ids_known(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        from world.data.mobs import mob_exists
        for s in SILVERMERE_SPAWNS:
            self.assertTrue(
                mob_exists(s["mob_id"]),
                f"Unknown mob_id in spawn config: {s['mob_id']}",
            )

    def test_all_respawn_default_is_300(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        for s in SILVERMERE_SPAWNS:
            self.assertEqual(
                s["respawn_seconds"], 300,
                f"{s['spawn_id']} has non-default respawn_seconds",
            )

    def test_silvermere_town_square_has_spawn(self):
        from world.data.world_rooms import get_spawns_for_room
        spawns = get_spawns_for_room("silvermere_town_square")
        mob_ids = {s["mob_id"] for s in spawns}
        self.assertIn("giant_rat", mob_ids)


# =============================================================================
# Spawn ↔ Room Integration (plain-Python core)
# =============================================================================


class TestSpawnRoomIntegration(_CleanSpawnsMixin, unittest.TestCase):
    """Test that spawn lifecycle integrates correctly with room location data."""

    def test_create_spawn_stores_location_id(self):
        result = create_spawn("rat_01", "giant_rat", "silvermere_town_square")
        self.assertIsInstance(result, CharacterData)
        record = get_spawn("rat_01")
        self.assertEqual(record["location_id"], "silvermere_town_square")

    def test_location_id_preserved_after_death(self):
        create_spawn("rat_01", "giant_rat", "silvermere_l74_c41")
        mob = get_live_mob("rat_01")
        mob.die()
        mark_dead_if_needed("rat_01")
        self.assertTrue(is_spawn_dead("rat_01"))
        # location_id still intact
        self.assertEqual(
            get_spawn("rat_01")["location_id"],
            "silvermere_l74_c41",
        )

    def test_location_id_preserved_after_respawn(self):
        create_spawn("rat_loc", "giant_rat", "silvermere_l74_c41",
                     respawn_seconds=60)
        mob = get_live_mob("rat_loc")
        mob.die()
        mark_dead_if_needed("rat_loc")
        # Force respawn (bypasses timer)
        from world.data.mob_spawner import force_respawn
        new_mob = force_respawn("rat_loc")
        self.assertIsInstance(new_mob, CharacterData)
        self.assertEqual(
            get_spawn("rat_loc")["location_id"],
            "silvermere_l74_c41",
        )

    def test_multiple_spawns_in_same_room(self):
        """Multiple spawns can share the same room_id."""
        r1 = create_spawn("a", "giant_rat", "silvermere_town_square")
        r2 = create_spawn("b", "giant_rat", "silvermere_town_square")
        self.assertIsInstance(r1, CharacterData)
        self.assertIsInstance(r2, CharacterData)
        self.assertIsNot(r1, r2)
        self.assertEqual(
            get_spawn("a")["location_id"],
            "silvermere_town_square",
        )
        self.assertEqual(
            get_spawn("b")["location_id"],
            "silvermere_town_square",
        )

    def test_duplicate_spawn_id_returns_error(self):
        create_spawn("unique_01", "giant_rat", "room_a")
        result = create_spawn("unique_01", "giant_rat", "room_b")
        self.assertIsInstance(result, str)
        self.assertIn("already exists", result)

    def test_get_active_spawns_returns_location(self):
        create_spawn("a", "giant_rat", "silvermere_town_square")
        create_spawn("b", "skeleton_warrior", "silvermere_l74_c41")
        active = get_active_spawns()
        self.assertEqual(len(active), 2)
        location_ids = {r["location_id"] for r in active}
        self.assertIn("silvermere_town_square", location_ids)
        self.assertIn("silvermere_l74_c41", location_ids)


# =============================================================================
# Spawn Lifecycle (death → cleanup → respawn)
# =============================================================================


class TestSpawnLifecycle(_CleanSpawnsMixin, unittest.TestCase):
    """End-to-end spawn lifecycle: live → dead → cleaned → respawned."""

    def test_full_lifecycle(self):
        import world.data.mob_spawner as _mod
        orig = _mod._monotonic
        fake = [1000.0]
        _mod._monotonic = lambda: fake[0]
        try:
            create_spawn("cycle_01", "giant_rat",
                         "silvermere_town_square", respawn_seconds=10)

            # Live
            self.assertFalse(is_spawn_dead("cycle_01"))
            mob = get_live_mob("cycle_01")
            self.assertIsNotNone(mob)
            self.assertTrue(mob.is_alive())

            # Kill
            mob.die()
            self.assertFalse(mob.is_alive())

            # Mark dead
            marked = mark_dead_if_needed("cycle_01")
            self.assertTrue(marked)
            self.assertTrue(is_spawn_dead("cycle_01"))

            # Respawn not yet (only 5s elapsed, need 10)
            fake[0] = 1005.0
            result = try_respawn("cycle_01")
            self.assertIsNone(result)  # not yet time

            # Advance past 10s
            fake[0] = 1011.0
            new_mob = try_respawn("cycle_01")
            self.assertIsInstance(new_mob, CharacterData)
            self.assertFalse(is_spawn_dead("cycle_01"))
            self.assertTrue(new_mob.is_alive())
        finally:
            _mod._monotonic = orig

    def test_mark_dead_clears_spawn_live_reference(self):
        create_spawn("md_01", "giant_rat", "room_a")
        mob = get_live_mob("md_01")
        mob.die()
        mark_dead_if_needed("md_01")
        self.assertTrue(is_spawn_dead("md_01"))
        # The record still holds the dead mob until respawn
        record = get_spawn("md_01")
        self.assertIsNotNone(record["live_mob"])

    def test_tick_all_spawns_detects_death(self):
        create_spawn("td_01", "giant_rat", "silvermere_town_square")
        mob = get_live_mob("td_01")
        mob.die()
        results = tick_all_spawns()
        self.assertGreaterEqual(len(results), 1)
        actions = {r["action"] for r in results}
        self.assertIn("marked_dead", actions)

    def test_tick_all_spawns_respawns_after_timer(self):
        import world.data.mob_spawner as _mod
        orig = _mod._monotonic
        fake = [1000.0]
        _mod._monotonic = lambda: fake[0]
        try:
            create_spawn("tr_01", "giant_rat",
                         "silvermere_town_square", respawn_seconds=5)
            mob = get_live_mob("tr_01")
            mob.die()
            # Tick 1: mark dead
            results = tick_all_spawns()
            self.assertTrue(any(
                r["spawn_id"] == "tr_01" and r["action"] == "marked_dead"
                for r in results
            ))
            # Advance past 5s
            fake[0] = 1006.0
            # Tick 2: respawn
            results = tick_all_spawns()
            self.assertTrue(any(
                r["spawn_id"] == "tr_01" and r["action"] == "respawned"
                for r in results
            ))
            self.assertFalse(is_spawn_dead("tr_01"))
        finally:
            _mod._monotonic = orig


# =============================================================================
# Duplicate Prevention & Idempotency
# =============================================================================


class TestDuplicatePrevention(_CleanSpawnsMixin, unittest.TestCase):
    """Verify that spawn creation is idempotent and duplicates are prevented."""

    def test_create_duplicate_spawn_id_fails(self):
        result1 = create_spawn("dup_01", "giant_rat", "room_a")
        self.assertIsInstance(result1, CharacterData)
        result2 = create_spawn("dup_01", "skeleton_warrior", "room_b")
        self.assertIsInstance(result2, str)

    def test_same_mob_different_spawn_ids_ok(self):
        r1 = create_spawn("a", "giant_rat", "room_a")
        r2 = create_spawn("b", "giant_rat", "room_a")
        self.assertIsInstance(r1, CharacterData)
        self.assertIsInstance(r2, CharacterData)
        self.assertIsNot(r1, r2)

    def test_remove_then_recreate_ok(self):
        create_spawn("re_01", "giant_rat", "room_a")
        remove_spawn("re_01")
        result = create_spawn("re_01", "giant_rat", "room_a")
        self.assertIsInstance(result, CharacterData)

    def test_get_spawn_after_remove_returns_none(self):
        create_spawn("rem_01", "giant_rat", "room_a")
        remove_spawn("rem_01")
        self.assertIsNone(get_spawn("rem_01"))

    def test_clear_all_spawns_idempotent(self):
        create_spawn("c1", "giant_rat", "room_a")
        create_spawn("c2", "skeleton_warrior", "room_b")
        clear_all_spawns()
        self.assertEqual(len(get_active_spawns()), 0)
        clear_all_spawns()  # idempotent
        self.assertEqual(len(get_active_spawns()), 0)


# =============================================================================
# World Integration Layer (plain-Python logic paths)
# =============================================================================


class TestWorldIntegrationLayer(_CleanSpawnsMixin, unittest.TestCase):
    """Test the world_integration module's core logic."""

    def test_init_spawn_registry_from_config(self):
        from world.world_integration import init_spawn_registry_from_config
        clear_all_spawns()
        configs = [
            {
                "spawn_id": "test_spawn_a",
                "mob_id": "giant_rat",
                "room_id": "silvermere_town_square",
                "respawn_seconds": 300,
            },
        ]
        room_map = init_spawn_registry_from_config(configs)
        self.assertIn("silvermere_town_square", room_map)
        self.assertIn("test_spawn_a", room_map["silvermere_town_square"])

    def test_init_spawn_registry_idempotent(self):
        from world.world_integration import init_spawn_registry_from_config
        configs = [
            {
                "spawn_id": "idem_spawn",
                "mob_id": "giant_rat",
                "room_id": "silvermere_town_square",
                "respawn_seconds": 300,
            },
        ]
        room_map1 = init_spawn_registry_from_config(configs)
        self.assertIn("idem_spawn", room_map1.get("silvermere_town_square", []))
        # Second call — same configs, should not create duplicates
        room_map2 = init_spawn_registry_from_config(configs)
        # The spawns should still be tracked
        active = get_active_spawns()
        self.assertEqual(len(active), 1)

    def test_spawn_id_already_exists(self):
        from world.world_integration import spawn_id_already_exists
        create_spawn("check_exists", "giant_rat", "room_a")
        self.assertTrue(spawn_id_already_exists("check_exists"))
        self.assertFalse(spawn_id_already_exists("nonexistent"))

    def test_clear_all_integration_spawns(self):
        from world.world_integration import clear_all_integration_spawns
        create_spawn("ci1", "giant_rat", "room_a")
        create_spawn("ci2", "skeleton_warrior", "room_b")
        clear_all_integration_spawns()
        self.assertEqual(len(get_active_spawns()), 0)

    def test_init_from_full_silvermere_config(self):
        from world.world_integration import init_spawn_registry_from_config
        from world.data.world_rooms import SILVERMERE_SPAWNS
        clear_all_spawns()  # ensure clean state
        room_map = init_spawn_registry_from_config(SILVERMERE_SPAWNS)
        self.assertGreaterEqual(len(room_map), 1)
        total_spawns = sum(len(v) for v in room_map.values())
        self.assertEqual(total_spawns, len(SILVERMERE_SPAWNS))

    def test_each_spawn_single_location(self):
        """Each spawn_id should map to exactly one room."""
        from world.world_integration import init_spawn_registry_from_config
        from world.data.world_rooms import SILVERMERE_SPAWNS
        room_map = init_spawn_registry_from_config(SILVERMERE_SPAWNS)
        seen = set()
        for room_id, spawn_ids in room_map.items():
            for sid in spawn_ids:
                self.assertNotIn(sid, seen, f"Duplicate spawn_id: {sid}")
                seen.add(sid)


# =============================================================================
# Regression — Existing Systems Intact
# =============================================================================


class TestRegression(_CleanSpawnsMixin, unittest.TestCase):
    """Ensure existing systems are unchanged."""

    def test_character_creation_still_works(self):
        cd = _make_player()
        self.assertIsNotNone(cd)
        self.assertEqual(cd.level, 1)

    def test_mob_creation_still_works(self):
        from world.data.mobs import create_mob_data
        rat = create_mob_data("giant_rat")
        self.assertIsNotNone(rat)
        self.assertEqual(rat.name, "Giant Rat")

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        p = _make_player()
        rat = _make_player()
        rat.name = "Giant Rat"
        result = resolve_attack(p, rat)
        self.assertTrue(result["valid"])

    def test_items_still_work(self):
        from world.data.items import item_exists
        self.assertTrue(item_exists("health_potion"))

    def test_shops_still_work(self):
        from world.data.shops import shop_exists
        self.assertTrue(shop_exists("general_store"))

    def test_quests_still_work(self):
        from world.data.quests import quest_exists
        self.assertTrue(quest_exists("rat_slayer"))

    def test_skills_still_work(self):
        from world.data.skills import skill_exists
        self.assertTrue(skill_exists("kick"))

    def test_spawner_still_works(self):
        result = create_spawn("reg_01", "giant_rat", "room_a")
        self.assertIsInstance(result, CharacterData)
        self.assertEqual(get_spawn("reg_01")["location_id"], "room_a")

    def test_spawner_remove_still_works(self):
        create_spawn("reg_02", "giant_rat", "room_a")
        remove_spawn("reg_02")
        self.assertIsNone(get_spawn("reg_02"))

    def test_spawn_tick_all_still_works(self):
        create_spawn("reg_tick", "giant_rat", "room_a")
        results = tick_all_spawns()
        self.assertIsInstance(results, list)


# =============================================================================
# No Phase 18 Leakage
# =============================================================================


class TestNoPhase18Leakage(unittest.TestCase):
    """Phase 17 must not implement Phase 18+ systems."""

    def test_no_websocket_in_room_module(self):
        import inspect
        from world.data import world_rooms as mod
        src = inspect.getsource(mod)
        body = self._strip_docstrings(src).lower()
        for term in ["websocket", "tutorial", "guild", "sect",
                      "social", "pvp", "map_editor"]:
            self.assertNotIn(term, body,
                             f"Phase 17 must not implement {term}")

    def test_spawns_reference_valid_mobs(self):
        from world.data.world_rooms import SILVERMERE_SPAWNS
        from world.data.mobs import mob_exists
        for s in SILVERMERE_SPAWNS:
            self.assertTrue(
                mob_exists(s["mob_id"]),
                f"Unknown mob_id: {s['mob_id']}",
            )

    @staticmethod
    def _strip_docstrings(src):
        in_docstring = False
        clean = []
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            clean.append(line)
        return "\n".join(clean)


if __name__ == "__main__":
    unittest.main()
