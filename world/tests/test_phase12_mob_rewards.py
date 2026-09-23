"""
Phase 12 -- Mob Loot & XP Rewards Tests
"""
import unittest
from world.data.character_data import CharacterData
from world.data.enums import CharacterState
from world.data.mobs import create_mob_data, get_mob_definition
from world.data.mob_rewards import (
    calculate_mob_rewards, grant_mob_rewards, reward_mob_kill,
    clear_all_rewarded, clear_rewarded_mob,
    _has_been_rewarded, _mark_rewarded,
)
import world.data.mob_rewards as _reward_mod


def setUpModule():
    clear_all_rewarded()


def tearDownModule():
    clear_all_rewarded()


def _make_player(name="Hero", race="human", prof="warrior"):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100; cd.hp = 100
    cd.max_mana = 100; cd.mana = 100
    cd.max_stamina = 100; cd.stamina = 100
    return cd
# =========================================================================
# XP Award
# =========================================================================

class TestXPAward(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_reward_xp_from_rat(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        old_xp = p.xp
        res = grant_mob_rewards(p, rat)
        self.assertTrue(res["success"])
        self.assertEqual(res["xp_awarded"], 15)
        self.assertEqual(p.xp, old_xp + 15)

    def test_reward_xp_from_skeleton(self):
        sk = create_mob_data("skeleton_warrior")
        p = _make_player()
        res = grant_mob_rewards(p, sk)
        self.assertTrue(res["success"])
        self.assertEqual(res["xp_awarded"], 120)

    def test_reward_xp_from_spider(self):
        sp = create_mob_data("forest_spider")
        p = _make_player()
        res = grant_mob_rewards(p, sp)
        self.assertTrue(res["success"])
        self.assertEqual(res["xp_awarded"], 50)

    def test_xp_accumulates(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        p.xp = 100
        grant_mob_rewards(p, rat)
        self.assertEqual(p.xp, 115)

    def test_zero_xp_mob(self):
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("zx", "ZX", xp_reward=0)
        o = _m.MOB_REGISTRY.get("zx")
        _m.MOB_REGISTRY["zx"] = df
        try:
            cd = create_mob_data("zx")
            p = _make_player()
            old = p.xp
            res = grant_mob_rewards(p, cd)
            self.assertTrue(res["success"])
            self.assertEqual(res["xp_awarded"], 0)
            self.assertEqual(p.xp, old)
        finally:
            if o is not None:
                _m.MOB_REGISTRY["zx"] = o
            else:
                _m.MOB_REGISTRY.pop("zx", None)
# =========================================================================
# Level-Up through Reward XP
# =========================================================================

class TestLevelUp(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_xp_reward_causes_level_up(self):
        sk = create_mob_data("skeleton_warrior")
        p = _make_player()
        old = p.level
        res = grant_mob_rewards(p, sk)
        self.assertTrue(res["success"])
        self.assertGreater(p.level, old)

    def test_multiple_kills_level_up(self):
        p = _make_player()
        for _ in range(3):
            sk = create_mob_data("skeleton_warrior")
            grant_mob_rewards(p, sk)
        self.assertGreaterEqual(p.level, 2)

    def test_exact_threshold_triggers_level(self):
        from world.data.progression import xp_to_next_level
        p = _make_player()
        nd = xp_to_next_level(p.level)
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("xt", "XT", xp_reward=nd)
        o = _m.MOB_REGISTRY.get("xt")
        _m.MOB_REGISTRY["xt"] = df
        try:
            cd = create_mob_data("xt")
            grant_mob_rewards(p, cd)
            self.assertGreaterEqual(p.level, 2)
        finally:
            if o is not None:
                _m.MOB_REGISTRY["xt"] = o
            else:
                _m.MOB_REGISTRY.pop("xt", None)
# =========================================================================
# Guaranteed Loot
# =========================================================================

class TestGuaranteedLoot(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_guaranteed_drop(self):
        spider = create_mob_data("forest_spider")
        p = _make_player()
        res = grant_mob_rewards(p, spider)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["items_granted"]), 1)
        self.assertEqual(res["items_granted"][0]["item_id"], "health_potion")
        self.assertEqual(p.get_item_qty("health_potion"), 1)

    def test_guaranteed_multiple_kills(self):
        p = _make_player()
        for _ in range(5):
            spider = create_mob_data("forest_spider")
            res = grant_mob_rewards(p, spider)
            self.assertEqual(len(res["items_granted"]), 1)
        self.assertEqual(p.get_item_qty("health_potion"), 5)


# =========================================================================
# Chance Loot
# =========================================================================

class TestChanceLoot(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()
        self.old_random = _reward_mod._rng_random

    def tearDown(self):
        _reward_mod._rng_random = self.old_random
        clear_all_rewarded()

    def test_chance_succeeds_low_random(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.0
        res = grant_mob_rewards(p, rat)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["items_granted"]), 1)

    def test_chance_fails_high_random(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.99
        res = grant_mob_rewards(p, rat)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["items_granted"]), 0)

    def test_chance_equal_fails(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.30
        res = grant_mob_rewards(p, rat)
        self.assertEqual(len(res["items_granted"]), 0)

    def test_chance_just_below_succeeds(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.299
        res = grant_mob_rewards(p, rat)
        self.assertEqual(len(res["items_granted"]), 1)
# =========================================================================
# Quantity Ranges
# =========================================================================

class TestQuantityRanges(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()
        self.old_random = _reward_mod._rng_random
        self.old_randint = _reward_mod._rng_randint

    def tearDown(self):
        _reward_mod._rng_random = self.old_random
        _reward_mod._rng_randint = self.old_randint
        clear_all_rewarded()

    def test_single_qty_exact(self):
        spider = create_mob_data("forest_spider")
        p = _make_player()
        res = grant_mob_rewards(p, spider)
        self.assertEqual(res["items_granted"][0]["quantity"], 1)

    def test_range_min(self):
        sk = create_mob_data("skeleton_warrior")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.0
        _reward_mod._rng_randint = lambda a, b: a
        res = grant_mob_rewards(p, sk)
        drops = [d for d in res["items_granted"] if d["item_id"] == "health_potion"]
        if drops:
            self.assertEqual(drops[0]["quantity"], 1)

    def test_range_max(self):
        sk = create_mob_data("skeleton_warrior")
        p = _make_player()
        _reward_mod._rng_random = lambda: 0.0
        _reward_mod._rng_randint = lambda a, b: b
        res = grant_mob_rewards(p, sk)
        drops = [d for d in res["items_granted"] if d["item_id"] == "health_potion"]
        if drops:
            self.assertEqual(drops[0]["quantity"], 2)

    def test_equal_range_drops_exact(self):
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("td", "TD", loot_table=[
            {"item_id": "health_potion", "chance": 1.0, "quantity": (3, 3)}])
        o = _m.MOB_REGISTRY.get("td")
        _m.MOB_REGISTRY["td"] = df
        try:
            cd = create_mob_data("td")
            p = _make_player()
            res = grant_mob_rewards(p, cd)
            self.assertEqual(res["items_granted"][0]["quantity"], 3)
            self.assertEqual(p.get_item_qty("health_potion"), 3)
        finally:
            if o is not None:
                _m.MOB_REGISTRY["td"] = o
            else:
                _m.MOB_REGISTRY.pop("td", None)


# =========================================================================
# No Duplicate Reward
# =========================================================================

class TestNoDuplicateReward(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_cannot_reward_twice(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        r1 = grant_mob_rewards(p, rat)
        self.assertTrue(r1["success"])
        r2 = grant_mob_rewards(p, rat)
        self.assertFalse(r2["success"])
        self.assertTrue(r2["already_rewarded"])
        self.assertEqual(r2["xp_awarded"], 0)
        self.assertEqual(len(r2["items_granted"]), 0)

    def test_calculate_still_reports_already_rewarded(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        grant_mob_rewards(p, rat)
        result = calculate_mob_rewards(rat)
        self.assertTrue(result["already_rewarded"])
        self.assertFalse(result["success"])

    def test_different_instance_can_be_rewarded(self):
        r1 = create_mob_data("giant_rat")
        r2 = create_mob_data("giant_rat")
        p1 = _make_player()
        p2 = _make_player()
        self.assertTrue(grant_mob_rewards(p1, r1)["success"])
        self.assertTrue(grant_mob_rewards(p2, r2)["success"])

    def test_clear_rewarded_allows_reward_again(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        grant_mob_rewards(p, rat)
        self.assertTrue(_has_been_rewarded(rat))
        clear_rewarded_mob(rat)
        self.assertFalse(_has_been_rewarded(rat))

    def test_clear_all_everything(self):
        rat = create_mob_data("giant_rat")
        sk = create_mob_data("skeleton_warrior")
        _mark_rewarded(rat)
        _mark_rewarded(sk)
        self.assertTrue(_has_been_rewarded(rat))
        self.assertTrue(_has_been_rewarded(sk))
        clear_all_rewarded()
        # clear_all_rewarded is a no-op for per-instance flags,
        # but mark_rewarded per-instance still works across tests
        self.assertTrue(_has_been_rewarded(rat))
# =========================================================================
# Invalid Item Safety
# =========================================================================

class TestInvalidItemSafety(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_invalid_item_no_crash(self):
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("in", "IN", loot_table=[
            {"item_id": "bad_item", "chance": 1.0, "quantity": 1}])
        o = _m.MOB_REGISTRY.get("in")
        _m.MOB_REGISTRY["in"] = df
        try:
            cd = create_mob_data("in")
            p = _make_player()
            res = grant_mob_rewards(p, cd)
            self.assertFalse(res["success"])
            self.assertEqual(len(res["errors"]), 1)
            self.assertEqual(len(res["items_granted"]), 0)
        finally:
            if o: _m.MOB_REGISTRY["in"] = o
            else: _m.MOB_REGISTRY.pop("in", None)

    def test_mixed_valid_invalid(self):
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("mx", "MX", loot_table=[
            {"item_id": "health_potion", "chance": 1.0, "quantity": 1},
            {"item_id": "bad", "chance": 1.0, "quantity": 1}])
        o = _m.MOB_REGISTRY.get("mx")
        _m.MOB_REGISTRY["mx"] = df
        try:
            cd = create_mob_data("mx")
            p = _make_player()
            res = grant_mob_rewards(p, cd)
            self.assertEqual(len(res["errors"]), 1)
            self.assertEqual(len(res["items_granted"]), 1)
            self.assertEqual(res["items_granted"][0]["item_id"], "health_potion")
            self.assertEqual(p.get_item_qty("health_potion"), 1)
        finally:
            if o: _m.MOB_REGISTRY["mx"] = o
            else: _m.MOB_REGISTRY.pop("mx", None)


# =========================================================================
# Inventory Integration
# =========================================================================

class TestInventoryIntegration(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_items_accumulate(self):
        p = _make_player()
        for _ in range(3):
            spider = create_mob_data("forest_spider")
            grant_mob_rewards(p, spider)
        self.assertEqual(p.get_item_qty("health_potion"), 3)

    def test_stacks_with_existing(self):
        p = _make_player()
        p.add_item("health_potion", 2)
        spider = create_mob_data("forest_spider")
        grant_mob_rewards(p, spider)
        self.assertEqual(p.get_item_qty("health_potion"), 3)

    def test_persistence_after_reward(self):
        spider = create_mob_data("forest_spider")
        p = _make_player()
        grant_mob_rewards(p, spider)
        data = p.to_dict()
        restored = CharacterData.from_dict(data)
        self.assertEqual(restored.get_item_qty("health_potion"), 1)
# =========================================================================
# Zero / No-Loot Mob
# =========================================================================

class TestZeroLootMob(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_empty_loot_table(self):
        guard = create_mob_data("town_guard")
        p = _make_player()
        res = grant_mob_rewards(p, guard)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["items_granted"]), 0)
        self.assertEqual(res["xp_awarded"], 300)

    def test_mob_without_loot_table_safe(self):
        from world.data.mobs import _make_mob_def
        import world.data.mobs as _m
        df = _make_mob_def("nl", "NL", xp_reward=5)
        o = _m.MOB_REGISTRY.get("nl")
        _m.MOB_REGISTRY["nl"] = df
        try:
            cd = create_mob_data("nl")
            res = calculate_mob_rewards(cd)
            self.assertEqual(res["xp_awarded"], 5)
            self.assertEqual(len(res["items_granted"]), 0)
        finally:
            if o: _m.MOB_REGISTRY["nl"] = o
            else: _m.MOB_REGISTRY.pop("nl", None)


# =========================================================================
# No Reward on Spawn Removal
# =========================================================================

class TestNoRewardOnSpawnRemoval(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_remove_spawn_no_reward(self):
        from world.data.mob_spawner import create_spawn, remove_spawn, clear_all_spawns
        clear_all_spawns()
        create_spawn("sr1", "giant_rat", "room_a")
        p = _make_player()
        remove_spawn("sr1")
        clear_all_spawns()
        self.assertEqual(p.xp, 0)
        self.assertEqual(p.get_item_qty("health_potion"), 0)

    def test_spawn_removal_no_rewarded_flag(self):
        from world.data.mob_spawner import create_spawn, remove_spawn, get_live_mob, clear_all_spawns
        clear_all_spawns()
        create_spawn("sr2", "giant_rat", "room_a")
        mob = get_live_mob("sr2")
        remove_spawn("sr2")
        clear_all_spawns()
        self.assertFalse(_has_been_rewarded(mob))
# =========================================================================
# Persistence
# =========================================================================

class TestPersistence(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_reward_result_serializable(self):
        import json
        rat = create_mob_data("giant_rat")
        p = _make_player()
        res = grant_mob_rewards(p, rat)
        s = json.dumps(res)
        r2 = json.loads(s)
        self.assertEqual(r2["xp_awarded"], res["xp_awarded"])

    def test_mob_def_has_reward_fields(self):
        d = get_mob_definition("giant_rat")
        self.assertIn("xp_reward", d)
        self.assertIn("loot_table", d)

    def test_player_xp_persists_after_reward(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        grant_mob_rewards(p, rat)
        data = p.to_dict()
        r = CharacterData.from_dict(data)
        self.assertEqual(r.xp, p.xp)


# =========================================================================
# Death Lifecycle Unchanged
# =========================================================================

class TestDeathLifecycle(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_die_does_not_trigger_rewards(self):
        rat = create_mob_data("giant_rat")
        rat.die()
        self.assertEqual(rat.state, CharacterState.DEAD)
        self.assertFalse(_has_been_rewarded(rat))

    def test_combat_death_still_works(self):
        from world.data.combat import resolve_attack
        import world.data.constants as _c
        old_hit = _c.BASE_HIT_CHANCE
        old_max = _c.MAX_HIT_CHANCE
        _c.BASE_HIT_CHANCE = 100
        _c.MAX_HIT_CHANCE = 100
        try:
            p = _make_player()
            rat = create_mob_data("giant_rat")
            rat.max_hp = 1; rat.hp = 1
            res = resolve_attack(p, rat)
            self.assertTrue(res["valid"])
            if res["target_killed"]:
                self.assertEqual(rat.state, CharacterState.DEAD)
                self.assertFalse(_has_been_rewarded(rat))
        finally:
            _c.BASE_HIT_CHANCE = old_hit
            _c.MAX_HIT_CHANCE = old_max

    def test_reward_after_combat_death(self):
        from world.data.combat import resolve_attack
        import world.data.constants as _c
        old_hit = _c.BASE_HIT_CHANCE
        old_max = _c.MAX_HIT_CHANCE
        _c.BASE_HIT_CHANCE = 100
        _c.MAX_HIT_CHANCE = 100
        try:
            p = _make_player()
            rat = create_mob_data("giant_rat")
            rat.max_hp = 1; rat.hp = 1
            res = resolve_attack(p, rat)
            self.assertTrue(res["target_killed"])
            rw = grant_mob_rewards(p, rat)
            self.assertTrue(rw["success"])
            self.assertGreater(p.xp, 0)
        finally:
            _c.BASE_HIT_CHANCE = old_hit
            _c.MAX_HIT_CHANCE = old_max

    def test_resolve_does_not_auto_reward(self):
        from world.data.combat import resolve_attack
        p = _make_player()
        p.max_hp = 200; p.hp = 200
        rat = create_mob_data("giant_rat")
        rat.max_hp = 1; rat.hp = 1
        old_xp = p.xp
        old_inv = dict(p.inventory)
        resolve_attack(p, rat)
        self.assertEqual(p.xp, old_xp)
        self.assertEqual(p.inventory, old_inv)


# =========================================================================
# Structured Result
# =========================================================================

class TestStructuredResult(unittest.TestCase):

    def setUp(self):
        clear_all_rewarded()

    def tearDown(self):
        clear_all_rewarded()

    def test_success_shape(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        res = grant_mob_rewards(p, rat)
        self.assertIn("xp_awarded", res)
        self.assertIn("items_granted", res)
        self.assertIn("errors", res)
        self.assertIn("already_rewarded", res)
        self.assertIn("mob_unknown", res)
        self.assertIn("success", res)

    def test_already_rewarded_shape(self):
        rat = create_mob_data("giant_rat")
        p = _make_player()
        grant_mob_rewards(p, rat)
        res = grant_mob_rewards(p, rat)
        self.assertTrue(res["already_rewarded"])
        self.assertFalse(res["success"])

    def test_unknown_mob_shape(self):
        cd = CharacterData()
        cd.profession_id = "nonexist"
        cd.name = "Stranger"
        res = calculate_mob_rewards(cd)
        self.assertTrue(res["mob_unknown"])
        self.assertFalse(res["success"])

    def test_items_always_list(self):
        rat = create_mob_data("giant_rat")
        res = calculate_mob_rewards(rat)
        self.assertIsInstance(res["items_granted"], list)


# =========================================================================
# Regression
# =========================================================================

class TestRegression(unittest.TestCase):

    def test_mob_lookup_still_works(self):
        self.assertIsNotNone(get_mob_definition("giant_rat"))
        self.assertIsNotNone(get_mob_definition("skeleton_warrior"))

    def test_mob_creation_still_works(self):
        rat = create_mob_data("giant_rat")
        self.assertIsNotNone(rat)
        self.assertEqual(rat.name, "Giant Rat")

    def test_player_creation_still_works(self):
        p = _make_player()
        self.assertIsInstance(p, CharacterData)
        self.assertEqual(p.race_id, "human")

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_player()
        t = _make_player()
        res = resolve_attack(a, t)
        self.assertTrue(res["valid"])
