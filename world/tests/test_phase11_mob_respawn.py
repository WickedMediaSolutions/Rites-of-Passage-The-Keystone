"""
Phase 11 — Mob Spawning & Respawning Tests

Tests:
  * spawning from mob_id
  * duplicate spawn prevention
  * death detection / mark_dead_if_needed
  * respawn after timer
  * 300s default respawn
  * custom respawn time
  * disabled respawn (RESPAWN_DISABLED)
  * force_respawn
  * fresh state on respawn
  * original location preserved
  * AI cleanup on death/respawn
  * remove_spawn cleanup
  * bulk tick_all_spawns
  * invalid mob_id handling
  * regression — existing systems unchanged
"""

import time
import unittest

from world.data.character_data import CharacterData
from world.data.enums import CharacterState
from world.data.mobs import create_mob_data
from world.data.mob_spawner import (
    create_spawn,
    remove_spawn,
    get_spawn,
    get_live_mob,
    set_respawn_seconds,
    mark_dead_if_needed,
    is_spawn_dead,
    try_respawn,
    force_respawn,
    tick_all_spawns,
    get_active_spawns,
    clear_all_spawns,
    DEFAULT_RESPAWN_SECONDS,
    RESPAWN_DISABLED,
    _spawns,
    _monotonic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORIG_MONOTONIC = _monotonic


def setUpModule():
    clear_all_spawns()


def tearDownModule():
    clear_all_spawns()


class _SpawnTestBase(unittest.TestCase):

    def setUp(self):
        clear_all_spawns()
        self._fake_time = [1000.0]
        self._orig_monotonic = _monotonic
        # Override _monotonic for deterministic time
        import world.data.mob_spawner as _mod
        _mod._monotonic = lambda: self._fake_time[0]

    def tearDown(self):
        import world.data.mob_spawner as _mod
        _mod._monotonic = self._orig_monotonic
        clear_all_spawns()

    def _advance(self, seconds):
        self._fake_time[0] += seconds


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------


class TestSpawning(_SpawnTestBase):

    def test_create_spawn_returns_character_data(self):
        result = create_spawn("r1", "giant_rat", "room_a")
        self.assertIsInstance(result, CharacterData)
        self.assertEqual(result.name, "Giant Rat")

    def test_create_spawn_populates_registry(self):
        create_spawn("r1", "giant_rat", "room_a")
        record = get_spawn("r1")
        self.assertIsNotNone(record)
        self.assertEqual(record["mob_id"], "giant_rat")
        self.assertEqual(record["location_id"], "room_a")

    def test_create_spawn_sets_active(self):
        create_spawn("r1", "giant_rat", "room_a")
        self.assertTrue(get_spawn("r1")["active"])

    def test_create_spawn_not_dead_initially(self):
        create_spawn("r1", "giant_rat", "room_a")
        self.assertFalse(get_spawn("r1")["is_dead"])

    def test_create_spawn_default_respawn_seconds(self):
        create_spawn("r1", "giant_rat", "room_a")
        self.assertEqual(get_spawn("r1")["respawn_seconds"], DEFAULT_RESPAWN_SECONDS)

    def test_create_spawn_custom_respawn(self):
        create_spawn("r1", "giant_rat", "room_a", respawn_seconds=60)
        self.assertEqual(get_spawn("r1")["respawn_seconds"], 60)


# ---------------------------------------------------------------------------
# Duplicate Prevention
# ---------------------------------------------------------------------------


class TestDuplicatePrevention(_SpawnTestBase):

    def test_duplicate_spawn_id_returns_error(self):
        create_spawn("r1", "giant_rat", "room_a")
        result = create_spawn("r1", "forest_spider", "room_b")
        self.assertIsInstance(result, str)
        self.assertIn("already exists", result)

    def test_duplicate_does_not_overwrite(self):
        create_spawn("r1", "giant_rat", "room_a")
        create_spawn("r1", "forest_spider", "room_b")
        record = get_spawn("r1")
        self.assertEqual(record["mob_id"], "giant_rat")

    def test_different_spawn_ids_are_independent(self):
        r1 = create_spawn("r1", "giant_rat", "room_a")
        r2 = create_spawn("r2", "forest_spider", "room_b")
        self.assertIsInstance(r1, CharacterData)
        self.assertIsInstance(r2, CharacterData)
        self.assertIsNot(r1, r2)
        self.assertEqual(r1.name, "Giant Rat")
        self.assertEqual(r2.name, "Forest Spider")

    def test_removed_spawn_can_be_recreated(self):
        create_spawn("r1", "giant_rat", "room_a")
        remove_spawn("r1")
        result = create_spawn("r1", "forest_spider", "room_b")
        self.assertIsInstance(result, CharacterData)
        self.assertEqual(result.name, "Forest Spider")


# ---------------------------------------------------------------------------
# remove_spawn
# ---------------------------------------------------------------------------


class TestRemoveSpawn(_SpawnTestBase):

    def test_remove_clears_from_registry(self):
        create_spawn("r1", "giant_rat", "room_a")
        err = remove_spawn("r1")
        self.assertIsNone(err)
        self.assertIsNone(get_spawn("r1"))

    def test_remove_nonexistent_returns_error(self):
        err = remove_spawn("nonexistent")
        self.assertIsNotNone(err)

    def test_remove_twice_returns_error(self):
        create_spawn("r1", "giant_rat", "room_a")
        remove_spawn("r1")
        err = remove_spawn("r1")
        self.assertIsNotNone(err)


# ---------------------------------------------------------------------------
# Death Detection
# ---------------------------------------------------------------------------


class TestDeathDetection(_SpawnTestBase):

    def test_mark_dead_detects_dead_mob(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        result = mark_dead_if_needed("r1")
        self.assertTrue(result)
        self.assertTrue(is_spawn_dead("r1"))

    def test_mark_dead_returns_false_if_already_dead(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")
        result = mark_dead_if_needed("r1")
        self.assertFalse(result)

    def test_mark_dead_returns_false_for_alive(self):
        create_spawn("r1", "giant_rat", "room_a")
        result = mark_dead_if_needed("r1")
        self.assertFalse(result)
        self.assertFalse(is_spawn_dead("r1"))

    def test_mark_dead_nonexistent_returns_false(self):
        result = mark_dead_if_needed("nonexistent")
        self.assertFalse(result)

    def test_is_spawn_dead_nonexistent_returns_false(self):
        self.assertFalse(is_spawn_dead("nonexistent"))


# ---------------------------------------------------------------------------
# Respawn Timer (300s default)
# ---------------------------------------------------------------------------


class TestRespawnTimer(_SpawnTestBase):

    def test_default_respawn_is_300_seconds(self):
        self.assertEqual(DEFAULT_RESPAWN_SECONDS, 300)

    def test_respawn_not_before_timer(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")
        # Only 1 second elapsed — not yet
        self._advance(1)
        result = try_respawn("r1")
        self.assertIsNone(result)
        self.assertTrue(is_spawn_dead("r1"))

    def test_respawn_after_timer(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        old_id = id(mob)
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        result = try_respawn("r1")
        self.assertIsInstance(result, CharacterData)
        self.assertNotEqual(id(result), old_id)
        self.assertFalse(is_spawn_dead("r1"))

    def test_respawn_after_timer_plus_some(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(500)
        result = try_respawn("r1")
        self.assertIsInstance(result, CharacterData)
        self.assertFalse(is_spawn_dead("r1"))


# ---------------------------------------------------------------------------
# Custom Respawn Time
# ---------------------------------------------------------------------------


class TestCustomRespawnTime(_SpawnTestBase):

    def test_custom_10_seconds_respawns_after_10(self):
        create_spawn("r1", "giant_rat", "room_a", respawn_seconds=10)
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(5)
        self.assertIsNone(try_respawn("r1"))

        self._advance(5)  # total 10
        result = try_respawn("r1")
        self.assertIsInstance(result, CharacterData)

    def test_custom_60_seconds_not_before_60(self):
        create_spawn("r1", "giant_rat", "room_a", respawn_seconds=60)
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(30)
        self.assertIsNone(try_respawn("r1"))

        self._advance(30)  # total 60
        result = try_respawn("r1")
        self.assertIsInstance(result, CharacterData)

    def test_set_respawn_seconds_after_creation(self):
        create_spawn("r1", "giant_rat", "room_a")
        err = set_respawn_seconds("r1", 30)
        self.assertIsNone(err)
        self.assertEqual(get_spawn("r1")["respawn_seconds"], 30)

    def test_set_respawn_seconds_invalid_spawn(self):
        err = set_respawn_seconds("nonexistent", 30)
        self.assertIsNotNone(err)


# ---------------------------------------------------------------------------
# Disabled Respawn
# ---------------------------------------------------------------------------


class TestDisabledRespawn(_SpawnTestBase):

    def test_respawn_disabled_sentinel(self):
        self.assertEqual(RESPAWN_DISABLED, -1)

    def test_disabled_respawn_never_respawns(self):
        create_spawn("r1", "giant_rat", "room_a", respawn_seconds=RESPAWN_DISABLED)
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(9999)
        result = try_respawn("r1")
        self.assertIsInstance(result, str)
        self.assertIn("disabled", result)
        self.assertTrue(is_spawn_dead("r1"))


# ---------------------------------------------------------------------------
# force_respawn
# ---------------------------------------------------------------------------


class TestForceRespawn(_SpawnTestBase):

    def test_force_respawn_replaces_dead_mob(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        new_mob = force_respawn("r1")
        self.assertIsInstance(new_mob, CharacterData)
        self.assertIsNot(new_mob, mob)
        self.assertFalse(is_spawn_dead("r1"))

    def test_force_respawn_replaces_alive_mob(self):
        create_spawn("r1", "giant_rat", "room_a")
        old_mob = get_live_mob("r1")
        new_mob = force_respawn("r1")
        self.assertIsInstance(new_mob, CharacterData)
        self.assertIsNot(new_mob, old_mob)
        self.assertFalse(is_spawn_dead("r1"))

    def test_force_respawn_invalid_spawn_returns_error(self):
        result = force_respawn("nonexistent")
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# Fresh State on Respawn
# ---------------------------------------------------------------------------


class TestFreshStateOnRespawn(_SpawnTestBase):

    def test_respawned_mob_has_full_hp(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.take_damage(5)
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        new_mob = try_respawn("r1")
        self.assertEqual(new_mob.hp, new_mob.max_hp)

    def test_respawned_mob_has_correct_stats(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.base_stats["str"] = 99  # mutate
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        new_mob = try_respawn("r1")
        self.assertEqual(new_mob.base_stats["str"], 3)  # canonical

    def test_respawned_mob_has_original_equipment(self):
        create_spawn("r1", "skeleton_warrior", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        new_mob = try_respawn("r1")
        from world.data.enums import EquipmentSlot
        self.assertEqual(
            new_mob.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword"
        )

    def test_respawned_mob_is_standing(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        new_mob = try_respawn("r1")
        self.assertEqual(new_mob.state, CharacterState.STANDING)


# ---------------------------------------------------------------------------
# Original Location Preserved
# ---------------------------------------------------------------------------


class TestLocationPreserved(_SpawnTestBase):

    def test_location_preserved_after_respawn(self):
        create_spawn("r1", "giant_rat", "sewer_entrance")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        try_respawn("r1")
        self.assertEqual(get_spawn("r1")["location_id"], "sewer_entrance")

    def test_location_preserved_after_force_respawn(self):
        create_spawn("r1", "giant_rat", "town_square")
        force_respawn("r1")
        self.assertEqual(get_spawn("r1")["location_id"], "town_square")

    def test_mob_id_preserved_after_respawn(self):
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        mob.die()
        mark_dead_if_needed("r1")

        self._advance(300)
        try_respawn("r1")
        self.assertEqual(get_spawn("r1")["mob_id"], "giant_rat")


# ---------------------------------------------------------------------------
# AI Cleanup
# ---------------------------------------------------------------------------


class TestAICleanup(_SpawnTestBase):

    def test_mark_dead_cleans_ai_state(self):
        from world.data.mob_ai import engage_target, _ai_state
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        # Simulate AI engagement
        dummy = CharacterData()
        dummy.max_hp = 100; dummy.hp = 100
        dummy.max_mana = 100; dummy.mana = 100
        dummy.max_stamina = 100; dummy.stamina = 100
        engage_target(mob, dummy)
        self.assertTrue(_ai_state(mob)["combat_active"])

        mob.die()
        mark_dead_if_needed("r1")
        self.assertFalse(_ai_state(mob)["combat_active"])
        self.assertIsNone(_ai_state(mob)["current_target"])

    def test_force_respawn_cleans_ai_state(self):
        from world.data.mob_ai import engage_target, _ai_state
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        dummy = CharacterData()
        dummy.max_hp = 100; dummy.hp = 100
        dummy.max_mana = 100; dummy.mana = 100
        dummy.max_stamina = 100; dummy.stamina = 100
        engage_target(mob, dummy)

        new_mob = force_respawn("r1")
        # Old mob should have had AI cleaned
        self.assertFalse(_ai_state(mob)["combat_active"])
        # New mob has no AI state
        self.assertFalse(hasattr(new_mob, "_ai_state"))

    def test_remove_spawn_cleans_ai_state(self):
        from world.data.mob_ai import engage_target, _ai_state
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        dummy = CharacterData()
        dummy.max_hp = 100; dummy.hp = 100
        dummy.max_mana = 100; dummy.mana = 100
        dummy.max_stamina = 100; dummy.stamina = 100
        engage_target(mob, dummy)

        remove_spawn("r1")
        self.assertFalse(_ai_state(mob)["combat_active"])


# ---------------------------------------------------------------------------
# Bulk Operations (tick_all_spawns)
# ---------------------------------------------------------------------------


class TestTickAllSpawns(_SpawnTestBase):

    def test_tick_all_detects_death(self):
        create_spawn("r1", "giant_rat", "room_a")
        create_spawn("r2", "forest_spider", "room_b")
        get_live_mob("r1").die()

        results = tick_all_spawns()
        actions = [r["action"] for r in results if r["spawn_id"] == "r1"]
        self.assertIn("marked_dead", actions)

    def test_tick_all_respawns_timed_out_mobs(self):
        create_spawn("r1", "giant_rat", "room_a")
        get_live_mob("r1").die()
        mark_dead_if_needed("r1")

        self._advance(300)
        results = tick_all_spawns()
        actions = [r["action"] for r in results if r["spawn_id"] == "r1"]
        self.assertIn("respawned", actions)
        self.assertFalse(is_spawn_dead("r1"))

    def test_tick_all_ignores_non_dead_mobs(self):
        create_spawn("r1", "giant_rat", "room_a")
        create_spawn("r2", "forest_spider", "room_b")
        results = tick_all_spawns()
        # Both alive — no actions
        self.assertEqual(len(results), 0)

    def test_tick_all_multiple_spawns(self):
        create_spawn("r1", "giant_rat", "room_a", respawn_seconds=5)
        create_spawn("r2", "forest_spider", "room_b", respawn_seconds=10)

        # Kill both
        get_live_mob("r1").die()
        get_live_mob("r2").die()

        # First tick detects death
        results = tick_all_spawns()
        deaths = [r for r in results if r["action"] == "marked_dead"]
        self.assertEqual(len(deaths), 2)

        # Advance 5s — only r1 should respawn
        self._advance(5)
        results = tick_all_spawns()
        respawns = [r for r in results if r["action"] == "respawned"]
        self.assertEqual(len(respawns), 1)
        self.assertEqual(respawns[0]["spawn_id"], "r1")

        # Advance 5 more — r2 should respawn
        self._advance(5)
        results = tick_all_spawns()
        respawns = [r for r in results if r["action"] == "respawned"]
        self.assertEqual(len(respawns), 1)
        self.assertEqual(respawns[0]["spawn_id"], "r2")

    def test_get_active_spawns(self):
        create_spawn("r1", "giant_rat", "a")
        create_spawn("r2", "forest_spider", "b")
        active = get_active_spawns()
        self.assertEqual(len(active), 2)
        remove_spawn("r1")
        active = get_active_spawns()
        self.assertEqual(len(active), 1)


# ---------------------------------------------------------------------------
# Invalid / Edge Cases
# ---------------------------------------------------------------------------


class TestInvalidEdgeCases(_SpawnTestBase):

    def test_create_spawn_unknown_mob_id(self):
        result = create_spawn("r1", "dragon", "room_a")
        self.assertIsInstance(result, str)
        self.assertIn("Unknown", result)

    def test_get_spawn_nonexistent(self):
        self.assertIsNone(get_spawn("nonexistent"))

    def test_get_live_mob_nonexistent(self):
        self.assertIsNone(get_live_mob("nonexistent"))

    def test_mark_dead_removed_spawn(self):
        create_spawn("r1", "giant_rat", "room_a")
        remove_spawn("r1")
        result = mark_dead_if_needed("r1")
        self.assertFalse(result)

    def test_try_respawn_removed_spawn(self):
        create_spawn("r1", "giant_rat", "room_a")
        remove_spawn("r1")
        result = try_respawn("r1")
        self.assertIsInstance(result, str)

    def test_try_respawn_already_alive(self):
        create_spawn("r1", "giant_rat", "room_a")
        result = try_respawn("r1")
        self.assertIsNone(result)

    def test_multiple_spawns_same_mob_id_different_live_instances(self):
        r1 = create_spawn("a", "giant_rat", "room_a")
        r2 = create_spawn("b", "giant_rat", "room_b")
        self.assertIsNot(r1, r2)
        r1.take_damage(3)
        self.assertNotEqual(r1.hp, r2.hp)


# ---------------------------------------------------------------------------
# Regression — existing systems unchanged
# ---------------------------------------------------------------------------


class TestRegression(_SpawnTestBase):

    def test_mob_creation_still_works(self):
        rat = create_mob_data("giant_rat")
        self.assertIsNotNone(rat)
        self.assertEqual(rat.name, "Giant Rat")

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        p = CharacterData.create_from_race_profession("H", "human", "warrior")
        p.max_hp = 100; p.hp = 100
        p.max_mana = 100; p.mana = 100
        p.max_stamina = 100; p.stamina = 100
        rat = create_mob_data("giant_rat")
        result = resolve_attack(p, rat)
        self.assertTrue(result["valid"])

    def test_spawn_not_in_mob_registry(self):
        """Spawn registry is separate from static MOB_REGISTRY."""
        from world.data.mobs import MOB_REGISTRY
        self.assertNotIn("_spawns", MOB_REGISTRY)
        # _spawns is a module-level dict in mob_spawner
        self.assertIsInstance(_spawns, dict)

    def test_ai_state_not_serialized(self):
        """AI state (_ai_state) is not persisted into CharacterData.to_dict()."""
        from world.data.mob_ai import engage_target, _ai_state
        create_spawn("r1", "giant_rat", "room_a")
        mob = get_live_mob("r1")
        dummy = CharacterData()
        dummy.max_hp = 100; dummy.hp = 100
        dummy.max_mana = 100; dummy.mana = 100
        dummy.max_stamina = 100; dummy.stamina = 100
        engage_target(mob, dummy)

        data = mob.to_dict()
        self.assertNotIn("_ai_state", data)
        self.assertNotIn("combat_active", str(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
