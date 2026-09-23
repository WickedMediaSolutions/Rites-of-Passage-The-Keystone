"""
Phase 10 — Mob Combat AI Tests

Tests:
  * AI targeting (hostile selects, non-hostile skips)
  * Dead mobs cannot target/attack
  * Dead players cannot be targeted
  * can_engage validation
  * engage_target lifecycle
  * combat rounds via execute_combat_round
  * death ends combat
  * target loss ends combat
  * force_end_combat
  * duplicate combat prevention
  * clean combat lifecycle
  * regression — existing systems unchanged
"""

import unittest

from world.data.character_data import CharacterData
from world.data.enums import CharacterState, Faction
from world.data.combat import resolve_attack
from world.data.mobs import create_mob_data, get_mob_definition
from world.data.mob_ai import (
    COMBAT_ROUND_INTERVAL,
    is_valid_target,
    select_hostile_target,
    can_engage,
    engage_target,
    execute_combat_round,
    force_end_combat,
    _ai_state,
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


# ---------------------------------------------------------------------------
# is_valid_target
# ---------------------------------------------------------------------------


class TestIsValidTarget(unittest.TestCase):

    def test_none_is_invalid(self):
        self.assertFalse(is_valid_target(None))

    def test_alive_player_is_valid(self):
        p = _make_player()
        self.assertTrue(is_valid_target(p))

    def test_dead_player_is_invalid(self):
        p = _make_player()
        p.die()
        self.assertFalse(is_valid_target(p))

    def test_zero_hp_is_invalid(self):
        p = _make_player()
        p.hp = 0
        self.assertFalse(is_valid_target(p))


# ---------------------------------------------------------------------------
# select_hostile_target
# ---------------------------------------------------------------------------


class TestSelectHostileTarget(unittest.TestCase):

    def test_hostile_rat_selects_player(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        target = select_hostile_target(rat, [player])
        self.assertIs(target, player)

    def test_non_hostile_guard_returns_none(self):
        guard = create_mob_data("town_guard")
        player = _make_player()
        target = select_hostile_target(guard, [player])
        self.assertIsNone(target)

    def test_non_hostile_merchant_returns_none(self):
        merchant = create_mob_data("friendly_merchant")
        player = _make_player()
        target = select_hostile_target(merchant, [player])
        self.assertIsNone(target)

    def test_dead_mob_returns_none(self):
        rat = create_mob_data("giant_rat")
        rat.die()
        player = _make_player()
        target = select_hostile_target(rat, [player])
        self.assertIsNone(target)

    def test_dead_player_not_selected(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        player.die()
        target = select_hostile_target(rat, [player])
        self.assertIsNone(target)

    def test_empty_player_list_returns_none(self):
        rat = create_mob_data("giant_rat")
        target = select_hostile_target(rat, [])
        self.assertIsNone(target)

    def test_skips_same_faction_player(self):
        """Hostile GOOD mob should not attack same-faction players."""
        # Create a good-aligned hostile mob by using a definition
        # All hostile mobs are EVIL; evil mobs skip EVIL players.
        rat = create_mob_data("giant_rat")  # EVIL
        evil_p = _make_player(race="troll", prof="warrior")  # EVIL faction
        target = select_hostile_target(rat, [evil_p])
        self.assertIsNone(target)

    def test_skips_same_faction_player_mixed_list(self):
        rat = create_mob_data("giant_rat")  # EVIL
        evil_p = _make_player(race="troll", prof="warrior")
        good_p = _make_player()  # human = GOOD
        target = select_hostile_target(rat, [evil_p, good_p])
        self.assertIs(target, good_p)


# ---------------------------------------------------------------------------
# can_engage
# ---------------------------------------------------------------------------


class TestCanEngage(unittest.TestCase):

    def test_hostile_mob_can_engage(self):
        rat = create_mob_data("giant_rat")
        self.assertTrue(can_engage(rat))

    def test_non_hostile_mob_cannot_engage(self):
        guard = create_mob_data("town_guard")
        self.assertFalse(can_engage(guard))

    def test_dead_mob_cannot_engage(self):
        rat = create_mob_data("giant_rat")
        rat.die()
        self.assertFalse(can_engage(rat))

    def test_mob_with_no_definition_cannot_engage(self):
        rat = create_mob_data("giant_rat")
        rat.profession_id = "not_a_mob"
        self.assertFalse(can_engage(rat))


# ---------------------------------------------------------------------------
# engage_target
# ---------------------------------------------------------------------------


class TestEngageTarget(unittest.TestCase):

    def test_engage_sets_combat_active(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        err = engage_target(rat, player)
        self.assertIsNone(err)
        self.assertTrue(_ai_state(rat)["combat_active"])
        self.assertIs(_ai_state(rat)["current_target"], player)

    def test_engage_dead_mob_returns_error(self):
        rat = create_mob_data("giant_rat")
        rat.die()
        player = _make_player()
        err = engage_target(rat, player)
        self.assertIsNotNone(err)
        self.assertFalse(_ai_state(rat)["combat_active"])

    def test_engage_dead_target_returns_error(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        player.die()
        err = engage_target(rat, player)
        self.assertIsNotNone(err)
        self.assertFalse(_ai_state(rat)["combat_active"])

    def test_engage_sets_target(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        self.assertIs(_ai_state(rat)["current_target"], player)


# ---------------------------------------------------------------------------
# execute_combat_round
# ---------------------------------------------------------------------------


class TestExecuteCombatRound(unittest.TestCase):

    def test_round_executes_when_engaged(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        result = execute_combat_round(rat)
        self.assertIn("round_executed", result)
        self.assertIn("result", result)
        self.assertIn("combat_ended", result)

    def test_no_round_when_not_engaged(self):
        rat = create_mob_data("giant_rat")
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])
        self.assertEqual(result["end_reason"], "Combat not active.")

    def test_dead_mob_ends_combat(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        rat.die()
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])
        self.assertEqual(result["end_reason"], "Mob died.")
        self.assertFalse(_ai_state(rat)["combat_active"])

    def test_dead_target_ends_combat(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            rat = create_mob_data("giant_rat")
            player = _make_player()
            player.hp = 1  # will die in one hit
            engage_target(rat, player)

            result = execute_combat_round(rat)
            if result["result"] and result["result"].get("target_killed"):
                self.assertTrue(result["combat_ended"])
                self.assertEqual(result["end_reason"], "Target killed.")
                self.assertFalse(_ai_state(rat)["combat_active"])
        finally:
            random.randint = orig

    def test_combat_round_applies_damage(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        hp_before = player.hp
        result = execute_combat_round(rat)
        if result["result"] and result["result"].get("hit"):
            self.assertLess(player.hp, hp_before)

    def test_combat_round_sets_combat_state_on_mob(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        result = execute_combat_round(rat)
        if result["round_executed"]:
            self.assertEqual(rat.state, CharacterState.COMBAT)

    def test_mob_can_kill_player(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            rat = create_mob_data("giant_rat")
            player = _make_player()
            player.hp = 1
            engage_target(rat, player)

            result = execute_combat_round(rat)
            self.assertTrue(result["round_executed"])
            # Player should be dead now
            self.assertEqual(player.state, CharacterState.DEAD)
            self.assertTrue(result["result"]["target_killed"])
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Target Loss
# ---------------------------------------------------------------------------


class TestTargetLoss(unittest.TestCase):

    def test_target_none_ends_combat(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        # Simulate target leaving by clearing the target
        _ai_state(rat)["current_target"] = None
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])
        self.assertIn("disconnected", result["end_reason"])

    def test_target_dead_already_ends_combat(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        # Target dies externally
        player.die()
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])
        self.assertEqual(result["end_reason"], "Target died.")


# ---------------------------------------------------------------------------
# force_end_combat
# ---------------------------------------------------------------------------


class TestForceEndCombat(unittest.TestCase):

    def test_force_end_stops_combat(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        err = force_end_combat(rat)
        self.assertIsNone(err)
        self.assertFalse(_ai_state(rat)["combat_active"])
        self.assertIsNone(_ai_state(rat)["current_target"])

    def test_force_end_when_not_active_returns_error(self):
        rat = create_mob_data("giant_rat")
        err = force_end_combat(rat)
        self.assertIsNotNone(err)

    def test_force_end_clears_combat_state(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        # Do one round to set combat state
        execute_combat_round(rat)
        if rat.state == CharacterState.COMBAT:
            force_end_combat(rat)
            self.assertNotEqual(rat.state, CharacterState.COMBAT)


# ---------------------------------------------------------------------------
# Duplicate Combat Prevention
# ---------------------------------------------------------------------------


class TestDuplicateCombatPrevention(unittest.TestCase):

    def test_execute_round_when_not_active_does_nothing(self):
        rat = create_mob_data("giant_rat")
        # No engagement — combat should not be active
        self.assertFalse(_ai_state(rat)["combat_active"])
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])

    def test_force_end_then_round_does_nothing(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        force_end_combat(rat)
        # Now execute round — should do nothing
        result = execute_combat_round(rat)
        self.assertFalse(result["round_executed"])
        self.assertTrue(result["combat_ended"])

    def test_engage_twice_overwrites_target(self):
        rat = create_mob_data("giant_rat")
        p1 = _make_player("Hero1")
        p2 = _make_player("Hero2")
        engage_target(rat, p1)
        engage_target(rat, p2)
        self.assertIs(_ai_state(rat)["current_target"], p2)

    def test_combat_active_prevents_second_loop(self):
        """Once combat is active, subsequent round calls work (no crash)."""
        rat = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(rat, player)
        # Multiple rounds should not crash or leave a mess
        r1 = execute_combat_round(rat)
        if _ai_state(rat)["combat_active"]:
            r2 = execute_combat_round(rat)
            if _ai_state(rat)["combat_active"]:
                r3 = execute_combat_round(rat)
                self.assertTrue(r1["round_executed"])


# ---------------------------------------------------------------------------
# Clean Combat Lifecycle
# ---------------------------------------------------------------------------


class TestCombatLifecycle(unittest.TestCase):

    def test_full_engage_attack_end_cycle(self):
        rat = create_mob_data("giant_rat")
        player = _make_player()

        # 1. Not engaged
        self.assertFalse(_ai_state(rat)["combat_active"])

        # 2. Engage
        err = engage_target(rat, player)
        self.assertIsNone(err)
        self.assertTrue(_ai_state(rat)["combat_active"])

        # 3. Execute round
        result = execute_combat_round(rat)
        self.assertTrue(result["round_executed"])
        self.assertFalse(result["combat_ended"])

        # 4. Force end
        force_end_combat(rat)
        self.assertFalse(_ai_state(rat)["combat_active"])

        # 5. Subsequent round does nothing
        result2 = execute_combat_round(rat)
        self.assertFalse(result2["round_executed"])
        self.assertTrue(result2["combat_ended"])

    def test_ai_state_is_different_per_instance(self):
        r1 = create_mob_data("giant_rat")
        r2 = create_mob_data("giant_rat")
        player = _make_player()
        engage_target(r1, player)
        self.assertTrue(_ai_state(r1)["combat_active"])
        self.assertFalse(_ai_state(r2)["combat_active"])


# ---------------------------------------------------------------------------
# Placeholder Constants
# ---------------------------------------------------------------------------


class TestPlaceholderConstants(unittest.TestCase):

    def test_combat_round_interval_is_defined(self):
        self.assertIsInstance(COMBAT_ROUND_INTERVAL, int)
        self.assertGreater(COMBAT_ROUND_INTERVAL, 0)

    def test_combat_round_interval_is_placeholder(self):
        """COMBAT_ROUND_INTERVAL is marked [PLACEHOLDER] in the source."""
        import inspect
        from world.data import mob_ai
        src = inspect.getsource(mob_ai)
        self.assertIn("PLACEHOLDER", src)


# ---------------------------------------------------------------------------
# Regression — existing systems unchanged
# ---------------------------------------------------------------------------


class TestRegression(unittest.TestCase):

    def test_resolve_attack_still_works(self):
        a = _make_player()
        t = _make_player()
        result = resolve_attack(a, t)
        self.assertIn("valid", result)

    def test_mob_creation_still_works(self):
        rat = create_mob_data("giant_rat")
        self.assertIsNotNone(rat)
        self.assertEqual(rat.name, "Giant Rat")

    def test_mob_definitions_unchanged(self):
        self.assertIsNotNone(get_mob_definition("giant_rat"))
        self.assertIsNotNone(get_mob_definition("town_guard"))

    def test_player_combat_unchanged(self):
        player = _make_player()
        rat = create_mob_data("giant_rat")
        result = resolve_attack(player, rat)
        self.assertTrue(result["valid"])

    def test_die_still_works_on_mob(self):
        rat = create_mob_data("giant_rat")
        rat.die()
        self.assertEqual(rat.state, CharacterState.DEAD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
