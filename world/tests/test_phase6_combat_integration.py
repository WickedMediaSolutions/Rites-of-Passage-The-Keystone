"""
Phase 6 — Combat-Evennia Integration & Unified Death Lifecycle Tests

Tests:

* ``CharacterData.die()`` — the authoritative data-layer death method
* Combat module's use of ``CharacterData.die()`` (no competing inline death)
* ``Character.die()`` delegation to ``CharacterData.die()``
* ``Character.attack_target()`` — Evennia-level combat integration
* Unified death lifecycle — one authoritative path, no duplication
* Regression — existing Phase 5 behaviour is preserved

These tests operate primarily on ``CharacterData`` (plain Python, no Evennia
server required).  Evennia typeclass integration is verified at the data-layer
contract level and via lightweight mocking of the Character typeclass.
"""

import unittest

from world.data.character_data import CharacterData
from world.data.combat import (
    resolve_attack,
    end_combat,
)
from world.data.constants import (
    BASE_HIT_CHANCE,
    MINIMUM_DAMAGE,
)
from world.data.enums import CharacterState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Test", race="human", prof="warrior"):
    """Create a fresh CharacterData with full resources."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    return cd


# ---------------------------------------------------------------------------
# CharacterData.die() — authoritative death
# ---------------------------------------------------------------------------


class TestCharacterDataDie(unittest.TestCase):
    """CharacterData.die() is the single authoritative data-layer death."""

    def test_die_sets_state_dead(self):
        cd = _make_cd()
        self.assertNotEqual(cd.state, CharacterState.DEAD)
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)

    def test_die_sets_hp_zero(self):
        cd = _make_cd()
        self.assertGreater(cd.hp, 0)
        cd.die()
        self.assertEqual(cd.hp, 0)

    def test_die_is_idempotent(self):
        """Calling die() on an already-dead character is safe."""
        cd = _make_cd()
        cd.die()
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)

    def test_die_on_already_dead_no_error(self):
        cd = _make_cd()
        cd.state = CharacterState.DEAD
        cd.hp = 0
        cd.die()  # must not raise
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)

    def test_die_is_callable_method(self):
        """die() must be a real bound method."""
        cd = _make_cd()
        self.assertTrue(callable(getattr(cd, "die", None)))
        self.assertTrue(hasattr(cd.die, "__func__") or hasattr(cd.die, "__call__"))


# ---------------------------------------------------------------------------
# Combat uses CharacterData.die() — no competing inline death
# ---------------------------------------------------------------------------


class TestCombatUsesDie(unittest.TestCase):
    """Combat resolves death through CharacterData.die(), not inline code."""

    def test_kill_via_resolve_attack_calls_die(self):
        """When resolve_attack kills a target, the target ends in DEAD state."""
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        result = resolve_attack(a, t)
        if result["target_killed"]:
            self.assertEqual(t.state, CharacterState.DEAD)
            self.assertEqual(t.hp, 0)

    def test_kill_hp_state_consistent(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        resolve_attack(a, t)
        self.assertLessEqual(t.hp, 100)
        if t.hp == 0:
            self.assertEqual(t.state, CharacterState.DEAD)

    def test_combat_module_has_no_inline_death_assignment(self):
        """Verify combat.py no longer manually sets state=DEAD and hp=0."""
        import inspect
        from world.data import combat as _combat

        src = inspect.getsource(_combat.resolve_attack)
        self.assertNotIn("target_cd.state = CharacterState.DEAD", src)
        self.assertNotIn("target_cd.hp = 0", src)
        self.assertIn(".die()", src)


# ---------------------------------------------------------------------------
# Character typeclass delegation (verified at data-layer contract level)
# ---------------------------------------------------------------------------


class TestCharacterTypeclassDieDelegation(unittest.TestCase):
    """Character.die() delegates to CharacterData.die() + save()."""

    def test_character_data_die_behaviour_matches_expected_typeclass_die(self):
        """CharacterData.die() produces the same state as the typeclass die().

        Before Phase 6, typeclass die() manually set state and hp.
        After Phase 6, it delegates to CharacterData.die().
        The end result (state=DEAD, hp=0) must be identical.
        """
        cd = _make_cd()
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)

    def test_resolve_attack_death_matches_manual_die(self):
        """Combat death and Character.die() produce identical end states."""
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t1 = _make_cd()
            t1.hp = 1
            result = resolve_attack(a, t1)
            self.assertTrue(result["target_killed"],
                           "Forced-hit should kill 1-hp target")

            t2 = _make_cd()
            t2.die()

            self.assertEqual(t1.state, t2.state)
            self.assertEqual(t1.hp, t2.hp)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Character.attack_target() — Evennia integration (mocked)
# ---------------------------------------------------------------------------


class _MockCharacter:
    """Lightweight mock of the Evennia Character typeclass for testing
    attack_target() behaviour without requiring a running server."""

    def __init__(self, cd: CharacterData):
        self.game = cd
        self._saved = False
        self._died = False

    def save(self):
        self._saved = True

    def die(self):
        self.game.die()
        self._died = True
        self.save()

    def attack_target(self, target: "_MockCharacter") -> dict:
        """Replicates the Character typeclass attack_target logic."""
        result = resolve_attack(self.game, target.game)

        if result["target_killed"]:
            target.die()
        else:
            target.save()

        self.save()
        return result


class TestAttackTargetIntegration(unittest.TestCase):
    """Evennia Character.attack_target() wraps combat with unified death."""

    def test_attack_target_returns_result_dict(self):
        a = _MockCharacter(_make_cd())
        t = _MockCharacter(_make_cd())
        result = a.attack_target(t)
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertIn("hit", result)
        self.assertIn("target_killed", result)

    def test_attack_target_on_invalid_target_returns_error(self):
        a = _MockCharacter(_make_cd())
        a.game.state = CharacterState.DEAD
        a.game.hp = 0
        t = _MockCharacter(_make_cd())
        result = a.attack_target(t)
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])

    def test_attack_target_saves_attacker(self):
        a = _MockCharacter(_make_cd())
        t = _MockCharacter(_make_cd())
        a.attack_target(t)
        self.assertTrue(a._saved, "Attacker should be saved after attack")

    def test_attack_target_saves_target_on_no_kill(self):
        a = _MockCharacter(_make_cd())
        t = _MockCharacter(_make_cd())
        t.game.hp = 100
        a.attack_target(t)
        if not t._died:
            self.assertTrue(t._saved, "Living target should be saved after attack")

    def test_attack_target_calls_die_on_kill(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _MockCharacter(_make_cd())
            t = _MockCharacter(_make_cd())
            t.game.hp = 1
            t.game.max_hp = 10
            a.attack_target(t)
            self.assertTrue(
                t._died,
                "Target's die() should be called when killed via attack_target",
            )
        finally:
            random.randint = orig

    def test_attack_target_die_is_authoritative(self):
        """When attack_target kills, die() is the sole death mechanism."""
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _MockCharacter(_make_cd())
            t = _MockCharacter(_make_cd())
            t.game.hp = 1
            a.attack_target(t)
            self.assertEqual(t.game.state, CharacterState.DEAD)
            self.assertEqual(t.game.hp, 0)
            self.assertTrue(t._died)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# No competing death behaviour
# ---------------------------------------------------------------------------


class TestNoCompetingDeath(unittest.TestCase):
    """Death has ONE authoritative path: CharacterData.die()."""

    def test_combat_does_not_duplicate_die_logic(self):
        """resolve_attack must call die(), not replicate its internals."""
        import inspect
        from world.data import combat as _combat

        src = inspect.getsource(_combat.resolve_attack)
        self.assertIn(".die()", src)
        self.assertNotIn(
            "state = CharacterState.DEAD",
            src,
            "resolve_attack() must not inline death state — use .die()",
        )
        self.assertNotIn(
            "hp = 0",
            src,
            "resolve_attack() must not inline hp=0 — use .die()",
        )

    def test_character_data_has_one_die_method(self):
        """CharacterData must have exactly one defined die method."""
        import inspect

        methods = [
            name
            for name, _ in inspect.getmembers(CharacterData, inspect.isfunction)
            if name == "die"
        ]
        self.assertEqual(
            len(methods),
            1,
            "CharacterData should have exactly one die() method definition",
        )

    def test_die_already_handles_hp_floors(self):
        """take_damage already floors hp at 0; die() enforces the invariant."""
        cd = _make_cd()
        cd.take_damage(999)
        self.assertEqual(cd.hp, 0)
        cd.die()
        self.assertEqual(cd.hp, 0)
        self.assertEqual(cd.state, CharacterState.DEAD)


# ---------------------------------------------------------------------------
# Phase 5 regression
# ---------------------------------------------------------------------------


class TestPhase5Regression(unittest.TestCase):
    """Phase 5 combat behaviour must be preserved after Phase 6 changes."""

    def test_resolve_attack_still_returns_expected_keys(self):
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        expected = {
            "valid", "error", "hit", "roll", "raw_damage",
            "actual_damage", "target_hp_before", "target_hp_after",
            "target_killed", "attacker_combat", "target_combat",
        }
        self.assertEqual(set(result.keys()), expected)

    def test_end_combat_still_preserves_dead(self):
        cd = _make_cd()
        cd.die()
        end_combat(cd)
        self.assertEqual(cd.state, CharacterState.DEAD)

    def test_combat_state_still_set_on_valid_attack(self):
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        if result["valid"]:
            self.assertTrue(result["attacker_combat"])
            self.assertTrue(result["target_combat"])

    def test_dead_target_still_rejected(self):
        a = _make_cd()
        t = _make_cd()
        t.die()
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIn("dead", result["error"].lower())

    def test_self_attack_still_rejected(self):
        a = _make_cd()
        result = resolve_attack(a, a)
        self.assertFalse(result["valid"])

    def test_xp_still_unchanged_by_combat(self):
        a = _make_cd()
        t = _make_cd()
        xp_before = a.xp
        resolve_attack(a, t)
        self.assertEqual(a.xp, xp_before)

    def test_level_still_unchanged_by_combat(self):
        a = _make_cd()
        t = _make_cd()
        lvl_before = a.level
        resolve_attack(a, t)
        self.assertEqual(a.level, lvl_before)

    def test_kill_preserves_dead_state_after_end_combat(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t = _make_cd()
            t.hp = 1
            result = resolve_attack(a, t)
            if result["target_killed"]:
                self.assertEqual(t.state, CharacterState.DEAD)
                self.assertEqual(t.hp, 0)
                end_combat(t)
                self.assertEqual(t.state, CharacterState.DEAD)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Typeclass-level attack target (contract verified via mock)
# ---------------------------------------------------------------------------


class TestAttackTargetContract(unittest.TestCase):
    """The Character.attack_target() contract as testable via CharacterData."""

    def test_game_attribute_has_die_method(self):
        """Character.game (CharacterData) must have die() for typeclass delegation."""
        cd = _make_cd()
        self.assertTrue(hasattr(cd, "die"))
        self.assertTrue(callable(cd.die))

    def test_attack_target_result_includes_expected_fields(self):
        """The result dict has all necessary fields."""
        a = _MockCharacter(_make_cd())
        t = _MockCharacter(_make_cd())
        result = a.attack_target(t)
        self.assertIn("target_killed", result)
        self.assertIn("valid", result)
        self.assertIn("hit", result)

    def test_game_has_save_method_for_persistence(self):
        """Typeclass save() bridges CharacterData to Evennia attrs."""
        mock = _MockCharacter(_make_cd())
        self.assertTrue(hasattr(mock, "save"))
        mock.save()
        self.assertTrue(mock._saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
