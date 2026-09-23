"""
Phase 5 — Combat Foundation Tests

Tests attack resolution, hit/miss, damage application, HP clamping,
lethal damage / death behaviour, dead-target rejection, self-attack
rejection, invalid-target rejection, combat state management, and
regression checks against Phases 2–4.

All tests operate on CharacterData via the plain-Python ``resolve_attack()``
function — no Evennia server required.
"""

import unittest

from world.data.character_data import CharacterData
from world.data.combat import (
    BASE_DAMAGE,
    STR_DAMAGE_MULTIPLIER,
    calculate_physical_damage,
    end_combat,
    enter_combat,
    resolve_attack,
    roll_hit,
    validate_attack,
)
from world.data.constants import (
    BASE_HIT_CHANCE,
    MINIMUM_DAMAGE,
    REGEN_HP_PER_TICK,
    REGEN_MANA_PER_TICK,
    REGEN_STAMINA_PER_TICK,
)
from world.data.enums import CharacterState, DamageType, PHYSICAL_DAMAGE_TYPES
from world.data.regeneration import regen_tick


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
# Attack Validation
# ---------------------------------------------------------------------------


class TestAttackValidation(unittest.TestCase):
    """Pre-attack validation rules."""

    def test_valid_attack_passes(self):
        a = _make_cd()
        t = _make_cd()
        self.assertIsNone(validate_attack(a, t))

    def test_self_attack_rejected(self):
        a = _make_cd()
        err = validate_attack(a, a)
        self.assertIsNotNone(err)
        self.assertIn("yourself", err.lower())

    def test_dead_target_rejected(self):
        a = _make_cd()
        t = _make_cd()
        t.state = CharacterState.DEAD
        t.hp = 0
        err = validate_attack(a, t)
        self.assertIsNotNone(err)
        self.assertIn("dead", err.lower())

    def test_none_target_rejected(self):
        a = _make_cd()
        err = validate_attack(a, None)
        self.assertIsNotNone(err)

    def test_dead_attacker_rejected(self):
        a = _make_cd()
        a.state = CharacterState.DEAD
        a.hp = 0
        t = _make_cd()
        err = validate_attack(a, t)
        self.assertIsNotNone(err)
        self.assertIn("dead", err.lower())


# ---------------------------------------------------------------------------
# Hit / Miss
# ---------------------------------------------------------------------------


class TestHitMiss(unittest.TestCase):
    """Hit-roll logic."""

    def test_hit_at_or_below_chance(self):
        """With 75% base chance, many rolls should hit."""
        a = _make_cd()
        t = _make_cd()
        hits = sum(1 for _ in range(500) if roll_hit(a, t))
        # With 75 % chance, 500 trials should produce 300–450 hits.
        self.assertGreater(hits, 300)
        self.assertLess(hits, 450)

    def test_miss_above_base_chance(self):
        """Verify roll_hit uses the BASE_HIT_CHANCE threshold."""
        # Monkey-patch random.randint to control the roll.
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: BASE_HIT_CHANCE + 1
            a = _make_cd()
            t = _make_cd()
            self.assertFalse(roll_hit(a, t))
        finally:
            random.randint = orig

    def test_hit_at_base_chance(self):
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: BASE_HIT_CHANCE
            a = _make_cd()
            t = _make_cd()
            self.assertTrue(roll_hit(a, t))
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Damage Calculation
# ---------------------------------------------------------------------------


class TestDamageCalculation(unittest.TestCase):
    """Physical damage formula."""

    def test_minimum_damage(self):
        a = _make_cd()
        a.base_stats = {"str": 0, "int": 0, "wis": 0, "dex": 0, "con": 0}
        t = _make_cd()
        dmg = calculate_physical_damage(a, t)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)

    def test_strength_increases_damage(self):
        a_weak = _make_cd()
        a_weak.base_stats["str"] = 10
        a_strong = _make_cd()
        a_strong.base_stats["str"] = 50
        t = _make_cd()
        dmg_weak = calculate_physical_damage(a_weak, t)
        dmg_strong = calculate_physical_damage(a_strong, t)
        self.assertGreater(dmg_strong, dmg_weak)

    def test_damage_is_positive(self):
        a = _make_cd()
        t = _make_cd()
        dmg = calculate_physical_damage(a, t)
        self.assertGreater(dmg, 0)

    def test_physical_damage_types_valid(self):
        a = _make_cd()
        t = _make_cd()
        for dt in PHYSICAL_DAMAGE_TYPES:
            dmg = calculate_physical_damage(a, t, dt)
            self.assertGreater(dmg, 0)


# ---------------------------------------------------------------------------
# Damage Application
# ---------------------------------------------------------------------------


class TestDamageApplication(unittest.TestCase):
    """Damage applied via resolve_attack."""

    def test_hit_reduces_hp(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 100
        hp_before = t.hp
        result = resolve_attack(a, t)
        if result["hit"]:
            self.assertLess(t.hp, hp_before)
            self.assertGreater(result["actual_damage"], 0)

    def test_hp_never_below_zero(self):
        a = _make_cd()
        a.base_stats["str"] = 200  # huge damage
        t = _make_cd()
        t.hp = 1
        # Render target killable in one hit by setting up strong attacker
        result = resolve_attack(a, t)
        if result["hit"]:
            self.assertGreaterEqual(t.hp, 0)

    def test_miss_applies_no_damage(self):
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: BASE_HIT_CHANCE + 1  # always miss
            a = _make_cd()
            t = _make_cd()
            hp_before = t.hp
            result = resolve_attack(a, t)
            self.assertFalse(result["hit"])
            self.assertEqual(t.hp, hp_before)
            self.assertEqual(result["actual_damage"], 0)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Lethal Damage / Death
# ---------------------------------------------------------------------------


class TestLethalDamage(unittest.TestCase):
    """Death behaviour triggered by lethal damage."""

    def test_kill_sets_state_dead(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        # Force hit + high damage
        import random
        orig = random.randint
        try:
            # roll 1 → hit; strength 200 → damage ~110
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            result = resolve_attack(a, t)
            self.assertTrue(result["hit"])
            self.assertTrue(result["target_killed"])
            self.assertEqual(t.state, CharacterState.DEAD)
            self.assertEqual(t.hp, 0)
        finally:
            random.randint = orig

    def test_target_combat_cleared_on_death(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            result = resolve_attack(a, t)
            self.assertTrue(result["target_killed"])
            self.assertFalse(result["target_combat"])
            self.assertEqual(t.state, CharacterState.DEAD)
        finally:
            random.randint = orig

    def test_attacker_stays_in_combat_after_kill(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            result = resolve_attack(a, t)
            self.assertTrue(result["attacker_combat"])
            self.assertEqual(a.state, CharacterState.COMBAT)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Invalid Attack Rejection
# ---------------------------------------------------------------------------


class TestInvalidAttackRejection(unittest.TestCase):
    """resolve_attack rejects invalid targets."""

    def test_dead_target_rejected_by_resolve(self):
        a = _make_cd()
        t = _make_cd()
        t.state = CharacterState.DEAD
        t.hp = 0
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])

    def test_self_attack_rejected_by_resolve(self):
        a = _make_cd()
        result = resolve_attack(a, a)
        self.assertFalse(result["valid"])
        self.assertIn("yourself", result["error"].lower())

    def test_dead_attacker_rejected_by_resolve(self):
        a = _make_cd()
        a.state = CharacterState.DEAD
        a.hp = 0
        t = _make_cd()
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])


# ---------------------------------------------------------------------------
# Combat State Management
# ---------------------------------------------------------------------------


class TestCombatStateManagement(unittest.TestCase):
    """Combat state is set and cleared correctly."""

    def test_enter_combat_sets_state(self):
        a = _make_cd()
        self.assertEqual(a.state, CharacterState.STANDING)
        enter_combat(a)
        self.assertEqual(a.state, CharacterState.COMBAT)

    def test_end_combat_clears_state(self):
        a = _make_cd()
        a.state = CharacterState.COMBAT
        end_combat(a)
        self.assertEqual(a.state, CharacterState.STANDING)

    def test_end_combat_does_not_clear_dead(self):
        a = _make_cd()
        a.state = CharacterState.DEAD
        end_combat(a)
        self.assertEqual(a.state, CharacterState.DEAD)

    def test_combat_state_set_on_valid_attack(self):
        a = _make_cd()
        t = _make_cd()
        self.assertEqual(a.state, CharacterState.STANDING)
        self.assertEqual(t.state, CharacterState.STANDING)
        result = resolve_attack(a, t)
        self.assertTrue(result["attacker_combat"])
        self.assertEqual(a.state, CharacterState.COMBAT)
        if not result["target_killed"]:
            self.assertTrue(result["target_combat"])
            self.assertEqual(t.state, CharacterState.COMBAT)

    def test_combat_state_not_set_on_invalid_attack(self):
        a = _make_cd()
        t = _make_cd()
        t.state = CharacterState.DEAD
        t.hp = 0
        a.state = CharacterState.STANDING
        resolve_attack(a, t)
        self.assertEqual(a.state, CharacterState.STANDING)


# ---------------------------------------------------------------------------
# XP Unchanged
# ---------------------------------------------------------------------------


class TestXPUnchanged(unittest.TestCase):
    """Combat must not affect XP (Phase 5 foundation)."""

    def test_xp_unchanged_by_attack(self):
        a = _make_cd()
        t = _make_cd()
        a_xp = a.xp
        t_xp = t.xp
        resolve_attack(a, t)
        self.assertEqual(a.xp, a_xp)
        self.assertEqual(t.xp, t_xp)

    def test_xp_unchanged_by_kill(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        a_xp = a.xp
        t_xp = t.xp
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            resolve_attack(a, t)
            self.assertEqual(a.xp, a_xp)
            self.assertEqual(t.xp, t_xp)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Progression Unchanged
# ---------------------------------------------------------------------------


class TestProgressionUnchanged(unittest.TestCase):
    """Combat must not affect level or unlocked skills."""

    def test_level_unchanged_by_attack(self):
        a = _make_cd()
        t = _make_cd()
        a_lvl = a.level
        t_lvl = t.level
        resolve_attack(a, t)
        self.assertEqual(a.level, a_lvl)
        self.assertEqual(t.level, t_lvl)

    def test_level_unchanged_by_kill(self):
        a = _make_cd()
        t = _make_cd()
        t.hp = 1
        a_lvl = a.level
        t_lvl = t.level
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            resolve_attack(a, t)
            self.assertEqual(a.level, a_lvl)
            self.assertEqual(t.level, t_lvl)
        finally:
            random.randint = orig

    def test_unlocked_skills_unchanged(self):
        a = _make_cd()
        t = _make_cd()
        a_skills = set(a.unlocked_skills)
        t_skills = set(t.unlocked_skills)
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: 1
            a.base_stats["str"] = 200
            t.hp = 1
            resolve_attack(a, t)
            self.assertEqual(a.unlocked_skills, a_skills)
            self.assertEqual(t.unlocked_skills, t_skills)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Regen Regression — Phase 4 compatibility
# ---------------------------------------------------------------------------


class TestRegenRegression(unittest.TestCase):
    """Combat does not break Phase 4 regeneration."""

    def test_regen_still_works_after_combat(self):
        a = _make_cd()
        a.hp = 50
        a.state = CharacterState.COMBAT
        result = regen_tick(a)
        # Regen still fires (it doesn't check COMBAT state).
        self.assertGreaterEqual(result["hp"], 0)

    def test_dead_char_no_regen(self):
        t = _make_cd()
        t.state = CharacterState.DEAD
        t.hp = 0
        result = regen_tick(t)
        self.assertEqual(result, {"hp": 0, "mana": 0, "stamina": 0})

    def test_combat_state_does_not_block_regen(self):
        """Regen is independent of COMBAT state (existing design)."""
        a = _make_cd()
        a.hp = 50
        a.state = CharacterState.COMBAT
        hp_before = a.hp
        regen_tick(a)
        self.assertGreaterEqual(a.hp, hp_before)

    def test_regen_values_unchanged_by_combat_module(self):
        """Combat module does not redefine regen constants."""
        self.assertEqual(REGEN_HP_PER_TICK, 5)
        self.assertEqual(REGEN_MANA_PER_TICK, 5)
        self.assertEqual(REGEN_STAMINA_PER_TICK, 5)


# ---------------------------------------------------------------------------
# No Phase 6 Leakage
# ---------------------------------------------------------------------------


class TestNoPhase6Leakage(unittest.TestCase):
    """Verify combat module contains no Phase 6 systems."""

    @staticmethod
    def _src() -> str:
        """Return module source WITHOUT the docstring (which lists exclusions)."""
        import inspect
        from world.data import combat as combat_mod
        src = inspect.getsource(combat_mod)
        # Strip the module docstring: find the first line after the docstring.
        # The docstring starts with """ and ends with """
        if '"""' in src:
            first = src.index('"""')
            # Find the closing """
            second = src.index('"""', first + 3)
            src = src[:first] + src[second + 3:]
        # Phase 19 adds record_pvp_kill — exclude it from Phase 5 checks.
        phase19_marker = "# PvP kill recording (Phase 19)"
        if phase19_marker in src:
            src = src[:src.index(phase19_marker)]
        return src.lower()

    def test_no_skills_in_combat_module(self):
        src = self._src()
        self.assertNotIn("spell", src)
        self.assertNotIn("cast", src)

    def test_no_buffs_or_debuffs(self):
        src = self._src()
        self.assertNotIn("buff", src)
        self.assertNotIn("debuff", src)

    def test_no_status_effects(self):
        src = self._src()
        self.assertNotIn("stun", src)
        self.assertNotIn("dot", src)

    def test_no_loot(self):
        src = self._src()
        self.assertNotIn("loot", src)

    def test_no_xp_reward(self):
        """resolve_attack does not award XP."""
        src = self._src()
        self.assertNotIn("award_xp", src)
        self.assertNotIn("xp +=", src)
        self.assertNotIn("xp+=", src)

    def test_no_npc_ai(self):
        src = self._src()
        self.assertNotIn("npc", src)
        self.assertNotIn("npc_ai", src)
        self.assertNotIn("ai_module", src)
        self.assertNotIn("ai_handler", src)

    def test_no_pvp_rewards(self):
        """Phase 5 resolve_attack does not contain PvP stat recording
        inline.  Phase 19 is_pvp_eligible/record_pvp_kill are separate
        functions added later to the same file."""
        src = self._src()
        # Only the pre-Phase-19 portion of the file must be free of PvP.
        pre_pvp = src.split("def is_pvp_eligible")[0]
        self.assertNotIn("pvp_kill", pre_pvp)
        self.assertNotIn("war_point", pre_pvp)

    def test_no_combat_round_ticker(self):
        src = self._src()
        self.assertNotIn("ticker", src)
        self.assertNotIn("round", src)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestCombatEdgeCases(unittest.TestCase):
    """Edge-case behaviour."""

    def test_non_physical_damage_type_falls_back_to_slashing(self):
        a = _make_cd()
        t = _make_cd()
        dmg = calculate_physical_damage(a, t, DamageType.FIRE)
        self.assertGreater(dmg, 0)

    def test_miss_result_structure(self):
        import random
        orig = random.randint
        try:
            random.randint = lambda a, b: BASE_HIT_CHANCE + 1
            a = _make_cd()
            t = _make_cd()
            result = resolve_attack(a, t)
            self.assertTrue(result["valid"])
            self.assertFalse(result["hit"])
            self.assertEqual(result["actual_damage"], 0)
            self.assertIsNotNone(result["roll"])
            self.assertTrue(result["attacker_combat"])
            self.assertTrue(result["target_combat"])
        finally:
            random.randint = orig

    def test_result_has_all_keys(self):
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        expected_keys = {
            "valid", "error", "hit", "roll", "raw_damage",
            "actual_damage", "target_hp_before", "target_hp_after",
            "target_killed", "attacker_combat", "target_combat",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_combat_preserves_faction(self):
        a = _make_cd()
        t = _make_cd()
        a_faction = a.faction
        t_faction = t.faction
        resolve_attack(a, t)
        self.assertEqual(a.faction, a_faction)
        self.assertEqual(t.faction, t_faction)

    def test_combat_preserves_race_profession(self):
        a = _make_cd(race="human", prof="warrior")
        t = _make_cd(race="high_elf", prof="mage")
        resolve_attack(a, t)
        self.assertEqual(a.race_id, "human")
        self.assertEqual(a.profession_id, "warrior")
        self.assertEqual(t.race_id, "high_elf")
        self.assertEqual(t.profession_id, "mage")


if __name__ == "__main__":
    unittest.main(verbosity=2)
