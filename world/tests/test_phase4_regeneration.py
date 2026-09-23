"""
Phase 4 — Resource Regeneration Tests

Tests periodic HP/Mana/Stamina regeneration, max clamping, dead-character
guard, duplicate scheduler prevention, persistence, and interaction with
level-up / respawn / XP.

All tests operate on CharacterData via the plain-Python ``regen_tick()``
function — no Evennia server required.
"""

import unittest

from world.data.character_data import CharacterData
from world.data.constants import REGEN_HP_PER_TICK, REGEN_MANA_PER_TICK, REGEN_STAMINA_PER_TICK
from world.data.enums import CharacterState
from world.data.regeneration import regen_tick


class TestHPRegen(unittest.TestCase):
    def _make_cd(self, hp=50, max_hp=100):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = max_hp; cd.hp = hp
        cd.mana = cd.max_mana; cd.stamina = cd.max_stamina
        return cd

    def test_hp_regen_below_max(self):
        cd = self._make_cd(hp=50, max_hp=100)
        result = regen_tick(cd)
        self.assertGreater(result["hp"], 0)
        self.assertEqual(cd.hp, 50 + result["hp"])

    def test_hp_regen_clamps_to_max(self):
        cd = self._make_cd(hp=98, max_hp=100)
        regen_tick(cd)
        self.assertEqual(cd.hp, 100)

    def test_hp_full_no_regen(self):
        cd = self._make_cd(hp=100, max_hp=100)
        result = regen_tick(cd)
        self.assertEqual(result["hp"], 0)


class TestManaRegen(unittest.TestCase):
    def _make_cd(self, mana=50, max_mana=100):
        cd = CharacterData.create_from_race_profession("T", "human", "mage")
        cd.max_hp = 100; cd.hp = 100
        cd.max_mana = max_mana; cd.mana = mana
        cd.stamina = cd.max_stamina
        return cd

    def test_mana_regen_below_max(self):
        cd = self._make_cd(mana=50, max_mana=100)
        result = regen_tick(cd)
        self.assertGreater(result["mana"], 0)

    def test_mana_regen_clamps_to_max(self):
        cd = self._make_cd(mana=97, max_mana=100)
        regen_tick(cd)
        self.assertEqual(cd.mana, 100)

    def test_mana_full_no_regen(self):
        cd = self._make_cd(mana=100, max_mana=100)
        result = regen_tick(cd)
        self.assertEqual(result["mana"], 0)


class TestStaminaRegen(unittest.TestCase):
    def _make_cd(self, stamina=50, max_stamina=100):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.mana = cd.max_mana
        cd.max_stamina = max_stamina; cd.stamina = stamina
        return cd

    def test_stamina_regen_below_max(self):
        cd = self._make_cd(stamina=50, max_stamina=100)
        result = regen_tick(cd)
        self.assertGreater(result["stamina"], 0)

    def test_stamina_regen_clamps_to_max(self):
        cd = self._make_cd(stamina=98, max_stamina=100)
        regen_tick(cd)
        self.assertEqual(cd.stamina, 100)

    def test_stamina_full_no_regen(self):
        cd = self._make_cd(stamina=100, max_stamina=100)
        result = regen_tick(cd)
        self.assertEqual(result["stamina"], 0)


class TestMaxClamping(unittest.TestCase):
    def test_hp_never_exceeds_max(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 99
        cd.mana = cd.max_mana; cd.stamina = cd.max_stamina
        regen_tick(cd)
        self.assertLessEqual(cd.hp, cd.max_hp)

    def test_mana_never_exceeds_max(self):
        cd = CharacterData.create_from_race_profession("T", "human", "mage")
        cd.max_hp = 100; cd.hp = 100
        cd.max_mana = 100; cd.mana = 99
        cd.stamina = cd.max_stamina
        regen_tick(cd)
        self.assertLessEqual(cd.mana, cd.max_mana)

    def test_stamina_never_exceeds_max(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.mana = cd.max_mana
        cd.max_stamina = 100; cd.stamina = 99
        regen_tick(cd)
        self.assertLessEqual(cd.stamina, cd.max_stamina)


class TestResourceAlreadyFull(unittest.TestCase):
    def test_all_full_returns_zero(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.max_mana = 100; cd.mana = 100
        cd.max_stamina = 100; cd.stamina = 100
        result = regen_tick(cd)
        self.assertEqual(result, {"hp": 0, "mana": 0, "stamina": 0})


class TestZeroMaxResource(unittest.TestCase):
    def test_zero_max_hp_safe(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 0; cd.hp = 0
        cd.mana = cd.max_mana; cd.stamina = cd.max_stamina
        result = regen_tick(cd)
        self.assertEqual(result["hp"], 0)

    def test_zero_max_mana_safe(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.max_mana = 0; cd.mana = 0
        cd.stamina = cd.max_stamina
        result = regen_tick(cd)
        self.assertEqual(result["mana"], 0)

    def test_zero_max_stamina_safe(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.mana = cd.max_mana
        cd.max_stamina = 0; cd.stamina = 0
        result = regen_tick(cd)
        self.assertEqual(result["stamina"], 0)

    def test_negative_max_handled_safely(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.mana = cd.max_mana
        cd.max_stamina = -5; cd.stamina = 0
        result = regen_tick(cd)
        self.assertEqual(result["stamina"], 0)


class TestDeadCharacterNoRegen(unittest.TestCase):
    def test_dead_by_state_skips_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 50
        cd.max_mana = 100; cd.mana = 50
        cd.max_stamina = 100; cd.stamina = 50
        cd.state = CharacterState.DEAD
        result = regen_tick(cd)
        self.assertEqual(result, {"hp": 0, "mana": 0, "stamina": 0})
        self.assertEqual(cd.hp, 50)

    def test_dead_by_zero_hp_skips_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 0
        cd.max_mana = 100; cd.mana = 50
        cd.max_stamina = 100; cd.stamina = 50
        cd.state = CharacterState.STANDING
        result = regen_tick(cd)
        self.assertEqual(result, {"hp": 0, "mana": 0, "stamina": 0})

    def test_dead_cannot_revive_from_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 0
        cd.state = CharacterState.DEAD
        for _ in range(100):
            regen_tick(cd)
        self.assertEqual(cd.hp, 0)
        self.assertEqual(cd.state, CharacterState.DEAD)


class TestRespawnThenRegen(unittest.TestCase):
    def test_respawn_allows_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.max_mana = 100; cd.max_stamina = 100
        cd.hp = 0; cd.mana = 20; cd.stamina = 20
        cd.state = CharacterState.DEAD
        cd.respawn_restore()
        self.assertEqual(cd.state, CharacterState.STANDING)
        self.assertGreater(cd.hp, 0)
        hp_before = cd.hp
        regen_tick(cd)
        self.assertGreater(cd.hp, hp_before)

    def test_multiple_ticks_after_respawn_reach_full(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.max_mana = 100; cd.max_stamina = 100
        cd.hp = 0; cd.state = CharacterState.DEAD
        cd.respawn_restore()
        for _ in range(100):
            regen_tick(cd)
        self.assertEqual(cd.hp, cd.max_hp)
        self.assertEqual(cd.mana, cd.max_mana)
        self.assertEqual(cd.stamina, cd.max_stamina)


class TestXPUnchanged(unittest.TestCase):
    def test_xp_unchanged_by_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 50
        cd.mana = cd.max_mana; cd.stamina = cd.max_stamina
        cd.xp = 500
        regen_tick(cd)
        self.assertEqual(cd.xp, 500)
        for _ in range(50):
            regen_tick(cd)
        self.assertEqual(cd.xp, 500)


class TestLevelUnchanged(unittest.TestCase):
    def test_level_unchanged_by_regen(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 50
        cd.mana = cd.max_mana; cd.stamina = cd.max_stamina
        cd.level = 5
        for _ in range(50):
            regen_tick(cd)
        self.assertEqual(cd.level, 5)


class TestRegenPersistence(unittest.TestCase):
    def test_regen_survives_round_trip(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 20
        cd.max_mana = 80; cd.mana = 30
        cd.max_stamina = 90; cd.stamina = 40
        regen_tick(cd)
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(cd2.hp, cd.hp)
        self.assertEqual(cd2.mana, cd.mana)
        self.assertEqual(cd2.stamina, cd.stamina)

    def test_full_regen_serialises_properly(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 50; cd.hp = 10
        cd.max_mana = 50; cd.mana = 10
        cd.max_stamina = 50; cd.stamina = 10
        for _ in range(20):
            regen_tick(cd)
        self.assertEqual(cd.hp, 50)
        data = cd.to_dict()
        self.assertEqual(data["hp"], 50)
        self.assertEqual(data["mana"], 50)
        self.assertEqual(data["stamina"], 50)


class TestDuplicateSchedulerPrevention(unittest.TestCase):
    _CHAR_PATH = None

    @classmethod
    def _get_char_path(cls):
        if cls._CHAR_PATH is None:
            import os
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cls._CHAR_PATH = os.path.join(base, "..", "typeclasses", "characters.py")
        return cls._CHAR_PATH

    def test_regeneration_methods_exist(self):
        """Verify Character has regen methods by inspecting the source."""
        import ast
        path = self._get_char_path()
        tree = ast.parse(open(path).read())
        methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Character":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.add(item.name)
        for method in ("regeneration_active", "start_regeneration",
                       "stop_regeneration", "_regen_tick_callback"):
            self.assertIn(method, methods, f"{method} missing from Character")

    def test_idstring_constant(self):
        """Verify _REGEN_IDSTRING exists by inspecting the source."""
        import ast
        path = self._get_char_path()
        tree = ast.parse(open(path).read())
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Character":
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "_REGEN_IDSTRING":
                                found = True
                                if isinstance(item.value, ast.Constant):
                                    self.assertIn("rop", str(item.value.value).lower())
        self.assertTrue(found, "_REGEN_IDSTRING not found in Character class")

    def test_duplicate_guard_uses_regeneration_active(self):
        """start_regeneration checks regeneration_active() to prevent duplicates."""
        path = self._get_char_path()
        src = open(path).read()
        self.assertIn("regeneration_active", src)
        self.assertIn("start_regeneration", src)
        self.assertIn("TICKER_HANDLER", src)

    def test_stop_guards_with_regeneration_active(self):
        """stop_regeneration checks regeneration_active() before removing."""
        path = self._get_char_path()
        src = open(path).read()
        self.assertIn("def stop_regeneration", src)
        self.assertIn("regeneration_active()", src)


class TestRegenAfterLevelUp(unittest.TestCase):
    def test_regen_works_after_increased_max(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 80
        cd.max_mana = 100; cd.mana = 80
        cd.max_stamina = 100; cd.stamina = 80
        cd.max_hp += 10; cd.max_mana += 5; cd.max_stamina += 7
        regen_tick(cd)
        self.assertGreater(cd.hp, 80)
        self.assertGreater(cd.mana, 80)
        self.assertGreater(cd.stamina, 80)

    def test_regen_fills_to_new_max(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 100
        cd.max_mana = 100; cd.mana = 100
        cd.max_stamina = 100; cd.stamina = 100
        cd.max_hp += 20; cd.max_mana += 20; cd.max_stamina += 20
        for _ in range(20):
            regen_tick(cd)
        self.assertEqual(cd.hp, cd.max_hp)
        self.assertEqual(cd.mana, cd.max_mana)
        self.assertEqual(cd.stamina, cd.max_stamina)


class TestRegenTickReturnValue(unittest.TestCase):
    def test_returns_dict_with_correct_keys(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 50
        cd.max_mana = 100; cd.mana = 50
        cd.max_stamina = 100; cd.stamina = 50
        result = regen_tick(cd)
        self.assertEqual(set(result.keys()), {"hp", "mana", "stamina"})

    def test_all_values_non_negative(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.max_hp = 100; cd.hp = 50
        cd.max_mana = 100; cd.mana = 50
        cd.max_stamina = 100; cd.stamina = 50
        result = regen_tick(cd)
        for key in ("hp", "mana", "stamina"):
            self.assertGreaterEqual(result[key], 0)

    def test_dead_returns_all_zeros(self):
        cd = CharacterData.create_from_race_profession("T", "human", "warrior")
        cd.state = CharacterState.DEAD; cd.hp = 0
        result = regen_tick(cd)
        self.assertEqual(result, {"hp": 0, "mana": 0, "stamina": 0})


class TestNoPhase5Leakage(unittest.TestCase):
    def test_no_combat_in_regen_module(self):
        import inspect
        from world.data import regeneration as regen_mod
        src = inspect.getsource(regen_mod).lower()
        self.assertNotIn("combat", src)
        self.assertNotIn("buff", src)

    def test_no_resting_bonus(self):
        import inspect
        src = inspect.getsource(regen_tick).lower()
        self.assertNotIn("resting", src)
        self.assertNotIn("meditat", src)

    def test_no_hunger_thirst(self):
        import inspect
        from world.data import regeneration as regen_mod
        src = inspect.getsource(regen_mod).lower()
        self.assertNotIn("hunger", src)
        self.assertNotIn("thirst", src)
        self.assertNotIn("consumable", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
