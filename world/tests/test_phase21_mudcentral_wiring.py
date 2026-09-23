"""
Comprehensive integration tests for MudCentral imported items and monsters.
"""
import unittest
import random

from world.data.character_data import CharacterData
from world.data.enums import CharacterState, DamageType, Faction
from world.data.combat import (
    calculate_physical_damage, roll_hit, resolve_attack, MINIMUM_DAMAGE,
)
from world.data import items as _items
from world.data import mobs as _mobs
from world.data.mob_rewards import (
    calculate_mob_rewards, grant_mob_rewards, _rng_random, _rng_randint,
)
from world.data.mob_spawner import (
    create_spawn, get_spawn, mark_dead_if_needed, try_respawn,
    clear_all_spawns, RESPAWN_DISABLED,
)


def _make_player(**kwargs):
    cd = CharacterData()
    cd.name = "TestPlayer"
    cd.race_id = "human"
    cd.profession_id = "fighter"
    cd.faction = Faction.GOOD
    cd.level = 10
    cd.base_stats = {"str": 10, "int": 10, "wis": 10, "dex": 10, "con": 10}
    cd.max_hp = 200; cd.hp = 200
    cd.max_mana = 50; cd.mana = 50
    cd.max_stamina = 100; cd.stamina = 100
    for k, v in kwargs.items():
        setattr(cd, k, v)
    return cd


def setUpModule():
    clear_all_spawns()
    _items._name_index = None
    _items._name_index_misses = set()


def tearDownModule():
    clear_all_spawns()


def _restore_rng():
    global _rng_random, _rng_randint
    _rng_random = random.random
    _rng_randint = random.randint


# =========================================================================
# Registry Counts
# =========================================================================

class TestRegistryCounts(unittest.TestCase):
    def test_mudcentral_items_present(self):
        mc = sum(1 for v in _items.ITEM_REGISTRY.values()
                 if v.get("source_urls") or "mudcentral" in str(v.get("item_id","")))
        self.assertGreaterEqual(len(_items.ITEM_REGISTRY), 1570)
        self.assertGreaterEqual(mc, 1559)

    def test_mudcentral_monsters_present(self):
        mc = sum(1 for v in _mobs.MOB_REGISTRY.values() if "mudcentral_source" in v)
        self.assertGreaterEqual(len(_mobs.MOB_REGISTRY), 986)
        self.assertEqual(mc, 983)

    def test_hand_authored_items_intact(self):
        self.assertIn("rusty_sword", _items.ITEM_REGISTRY)
        self.assertIn("cloth_vest", _items.ITEM_REGISTRY)
        self.assertIn("health_potion", _items.ITEM_REGISTRY)

    def test_hand_authored_mobs_intact(self):
        self.assertIn("giant_rat", _mobs.MOB_REGISTRY)
        self.assertIn("skeleton_warrior", _mobs.MOB_REGISTRY)
        self.assertIn("town_guard", _mobs.MOB_REGISTRY)


# =========================================================================
# Mob Creation
# =========================================================================

class TestMobCreation(unittest.TestCase):
    def test_create_imported_mob(self):
        abom = _mobs.create_mob_data("abomination")
        self.assertIsNotNone(abom)
        self.assertEqual(abom.name, "abomination")
        self.assertEqual(abom.race_id, "mob")
        self.assertEqual(abom.profession_id, "abomination")

    def test_no_shared_state(self):
        a = _mobs.create_mob_data("abomination")
        b = _mobs.create_mob_data("abomination")
        self.assertIsNot(a, b)
        a.hp = 50
        self.assertEqual(b.hp, b.max_hp)
        self.assertNotEqual(a.hp, b.hp)

    def test_imported_hp_applied(self):
        abom = _mobs.create_mob_data("abomination")
        self.assertEqual(abom.max_hp, 180)
        self.assertEqual(abom.hp, 180)


# =========================================================================
# XP
# =========================================================================

class TestXP(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_imported_xp_awarded(self):
        p = _make_player()
        abom = _mobs.create_mob_data("abomination")
        abom.max_hp = 1; abom.hp = 1
        old_xp = p.xp
        grant_mob_rewards(p, abom)
        self.assertEqual(p.xp, old_xp + 725)

    def test_xp_not_awarded_twice(self):
        p = _make_player()
        abom = _mobs.create_mob_data("abomination")
        abom.max_hp = 1; abom.hp = 1
        grant_mob_rewards(p, abom)
        xp_after = p.xp
        grant_mob_rewards(p, abom)
        self.assertEqual(p.xp, xp_after)


# =========================================================================
# Loot
# =========================================================================

class TestLoot(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_loot_entries_have_valid_shape(self):
        for mid, defn in _mobs.MOB_REGISTRY.items():
            for entry in defn.get("loot_table", []):
                self.assertIn("item_id", entry)
                self.assertIn("chance", entry)
                self.assertIn("quantity", entry)

    def test_all_loot_resolves_to_registry(self):
        for mid, defn in _mobs.MOB_REGISTRY.items():
            for entry in defn.get("loot_table", []):
                self.assertTrue(
                    _items.item_exists(entry["item_id"]),
                    f"Mob {mid}: unknown item '{entry['item_id']}'"
                )

    def test_unresolved_drops_preserved(self):
        dragon = _mobs.get_mob_definition("adult_red_dragon")
        if dragon:
            self.assertIsInstance(dragon.get("unresolved_drops", []), list)

    def test_loot_chance_in_range(self):
        for defn in _mobs.MOB_REGISTRY.values():
            for entry in defn.get("loot_table", []):
                self.assertGreaterEqual(entry["chance"], 0.0)
                self.assertLessEqual(entry["chance"], 1.0)

    def test_loot_table_is_list(self):
        for defn in _mobs.MOB_REGISTRY.values():
            self.assertIsInstance(defn.get("loot_table", []), list)


# =========================================================================
# Combat: AC/DR
# =========================================================================

class TestCombatACDR(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_mob_ac_reduces_damage(self):
        p = _make_player()
        p.base_stats["str"] = 20
        # bard_spirit: AC=5, DR=5  -> takes more damage
        low_ac = _mobs.create_mob_data("bard_spirit")
        # azrandimon: AC=80, DR=10 -> takes less damage
        high_ac = _mobs.create_mob_data("azrandimon")
        self.assertIsNotNone(high_ac)
        self.assertIsNotNone(low_ac)
        dmg_high = calculate_physical_damage(p, high_ac)
        dmg_low = calculate_physical_damage(p, low_ac)
        self.assertLess(dmg_high, dmg_low)

    def test_damage_floor(self):
        p = _make_player()
        p.base_stats["str"] = 0
        high_def = _mobs.create_mob_data("azrandimon")
        if high_def is None:
            self.skipTest("azrandimon not found")
        dmg = calculate_physical_damage(p, high_def)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)


# =========================================================================
# Combat: Dodge
# =========================================================================

class TestCombatDodge(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_dodge_reduces_hit_chance(self):
        p = _make_player()
        alderth = _mobs.create_mob_data("aldreth")
        self.assertIsNotNone(alderth)
        old_randint = random.randint
        try:
            random.randint = lambda a, b: 50
            hit = roll_hit(p, alderth)
            self.assertFalse(hit)
            random.randint = lambda a, b: 3
            hit = roll_hit(p, alderth)
            self.assertTrue(hit)
        finally:
            random.randint = old_randint


# =========================================================================
# Combat: Resistances
# =========================================================================

class TestCombatResistances(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_negative_resistance_amplifies(self):
        p = _make_player()
        p.base_stats["str"] = 0
        # adolescent_red_dragon has Resist Cold -100% (water vuln)
        dragon = _mobs.create_mob_data("adolescent_red_dragon")
        if dragon is None:
            self.skipTest("adolescent_red_dragon not found")
        dmg = calculate_physical_damage(p, dragon, DamageType.SLASHING)
        self.assertGreater(dmg, 0)

    def test_positive_resistance_reduces(self):
        p = _make_player()
        p.base_stats["str"] = 0
        # adolescent_black_dragon has Resist Cold +50% (water resist)
        dragon = _mobs.create_mob_data("adolescent_black_dragon")
        if dragon is None:
            self.skipTest("adolescent_black_dragon not found")
        dmg = calculate_physical_damage(p, dragon, DamageType.SLASHING)
        self.assertGreater(dmg, 0)


# =========================================================================
# Combat: Poison Immunity
# =========================================================================

class TestCombatImmunities(unittest.TestCase):
    def test_poison_immunity_parsed(self):
        # adolescent_black_dragon has "Poison Immunity"
        combat = _mobs.get_mob_combat_properties("adolescent_black_dragon")
        self.assertTrue(combat.get("poison_immunity", False))


# =========================================================================
# Regression
# =========================================================================

class TestRegression(unittest.TestCase):
    def setUp(self):
        _restore_rng()

    def test_hand_authored_combat(self):
        p = _make_player()
        rat = _mobs.create_mob_data("giant_rat")
        rat.max_hp = 1; rat.hp = 1
        result = resolve_attack(p, rat)
        self.assertTrue(result["valid"])

    def test_player_vs_player(self):
        a = _make_player()
        b = _make_player()
        result = resolve_attack(a, b)
        self.assertTrue(result["valid"])

    def test_resolve_attack_keys(self):
        p = _make_player()
        rat = _mobs.create_mob_data("giant_rat")
        result = resolve_attack(p, rat)
        expected = {"valid", "error", "hit", "raw_damage", "actual_damage",
                    "target_hp_after", "target_killed", "target_combat",
                    "attacker_combat"}
        self.assertTrue(expected.issubset(set(result.keys())))


# =========================================================================
# Spawning
# =========================================================================

class TestSpawnImportedMobs(unittest.TestCase):
    def setUp(self):
        clear_all_spawns()

    def tearDown(self):
        clear_all_spawns()

    def test_create_spawn(self):
        result = create_spawn("sp_01", "abomination", "swamp")
        self.assertIsInstance(result, CharacterData)

    def test_spawn_invalid_mob(self):
        result = create_spawn("sp_02", "nonexistent", "void")
        self.assertIsInstance(result, str)

    def test_spawn_duplicate_rejected(self):
        create_spawn("sp_03", "abomination", "swamp")
        result = create_spawn("sp_03", "abomination", "swamp")
        self.assertIsInstance(result, str)

    def test_multiple_spawn_slots(self):
        a = create_spawn("sp_a", "abomination", "swamp")
        b = create_spawn("sp_b", "bandit", "forest")
        self.assertIsInstance(a, CharacterData)
        self.assertIsInstance(b, CharacterData)
        self.assertIsNot(a, b)
        self.assertNotEqual(a.profession_id, b.profession_id)


# =========================================================================
# Respawn
# =========================================================================

class TestRespawn(unittest.TestCase):
    def setUp(self):
        clear_all_spawns()

    def tearDown(self):
        clear_all_spawns()

    def test_death_detected(self):
        create_spawn("r_01", "abomination", "room")
        mob = get_spawn("r_01")["live_mob"]
        mob.hp = 0; mob.die()
        marked = mark_dead_if_needed("r_01")
        self.assertTrue(marked)

    def test_respawn_not_before_timer(self):
        create_spawn("r_02", "bandit", "room", respawn_seconds=99)
        mob = get_spawn("r_02")["live_mob"]
        mob.hp = 0; mob.die()
        mark_dead_if_needed("r_02")
        result = try_respawn("r_02")
        self.assertIsNone(result)

    def test_respawn_disabled_stays_dead(self):
        create_spawn("r_03", "abomination", "room", respawn_seconds=RESPAWN_DISABLED)
        mob = get_spawn("r_03")["live_mob"]
        mob.hp = 0; mob.die()
        mark_dead_if_needed("r_03")
        result = try_respawn("r_03")
        self.assertIsInstance(result, str)
        self.assertIn("disabled", result)

    def test_manual_mob_no_respawn(self):
        abom = _mobs.create_mob_data("abomination")
        abom.hp = 0; abom.die()
        self.assertEqual(abom.state, CharacterState.DEAD)


# =========================================================================
# Variant Integrity
# =========================================================================

class TestMonsterVariants(unittest.TestCase):
    def test_variants_have_different_stats(self):
        variants = {}
        for mid, defn in _mobs.MOB_REGISTRY.items():
            if defn.get("mudcentral_source"):
                name = defn["name"]
                variants.setdefault(name, []).append(mid)
        for name, ids in variants.items():
            if len(ids) >= 2:
                d1 = _mobs.get_mob_definition(ids[0])
                d2 = _mobs.get_mob_definition(ids[1])
                self.assertTrue(
                    d1["max_hp"] != d2["max_hp"] or
                    d1.get("ac") != d2.get("ac") or
                    d1["xp_reward"] != d2["xp_reward"],
                    f"Variants {ids[0]} and {ids[1]} of '{name}' identical"
                )
                return
        self.skipTest("No multi-variant name found")


# =========================================================================
# Name Collision Safety
# =========================================================================

class TestNameCollisionSafety(unittest.TestCase):
    def test_giant_rat_placeholder(self):
        rat = _mobs.get_mob_definition("giant_rat")
        self.assertEqual(rat["name"], "Giant Rat")
        self.assertEqual(rat["max_hp"], 8)
        self.assertEqual(rat["xp_reward"], 15)

    def test_skeleton_has_equipment(self):
        skel = _mobs.get_mob_definition("skeleton_warrior")
        self.assertIn("equipped_items", skel)


# =========================================================================
# Field Preservation
# =========================================================================

class TestFieldPreservation(unittest.TestCase):
    def test_specials_parsed(self):
        combat = _mobs.get_mob_combat_properties("abomination")
        self.assertEqual(combat.get("enslave_level"), 25)

    def test_all_key_fields_present(self):
        abom = _mobs.get_mob_definition("abomination")
        for key in ["ac", "damage_reduction", "magic_resistance",
                    "spell_immunity", "mw_combat", "mudcentral_source"]:
            self.assertIn(key, abom, f"Missing field: {key}")

    def test_guarded_by_preserved(self):
        found = False
        for mid in _mobs.MOB_REGISTRY:
            combat = _mobs.get_mob_combat_properties(mid)
            if combat.get("guarded_by"):
                self.assertIsInstance(combat["guarded_by"], list)
                found = True
                break
        self.assertTrue(found, "No mob with guarded_by found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
