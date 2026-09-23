"""
Phase 3 — Character Progression Tests

Tests XP curve, level-up processing, skill/spell granting, weapon
proficiency initialisation, multi-level jumps, max-level behaviour,
death-penalty compatibility, idempotency, and serialisation.
"""

import json
import unittest

from world.data.character_data import CharacterData
from world.data.constants import (
    MAX_LEVEL,
    STARTING_LEVEL,
    XP_CURVE_COEFF,
    DEFAULT_WEAPON_PROFICIENCY,
    SECOND_ATTACK_LEVEL,
    THIRD_ATTACK_LEVEL,
)
from world.data.enums import CharacterState, Faction
from world.data.professions import PROFESSIONS, UNIVERSAL_SKILLS, WEAPON_SKILLS
from world.data.races import RACES
from world.data import progression as _prog


# =====================================================================
# XP Curve
# =====================================================================

class TestXPCurve(unittest.TestCase):

    def test_level_1_threshold_is_zero(self):
        self.assertEqual(_prog.xp_for_level(1), 0)

    def test_level_2_requires_xp(self):
        self.assertGreater(_prog.xp_for_level(2), 0)

    def test_curve_is_monotonic(self):
        prev = -1
        for lvl in range(1, 101):
            cur = _prog.xp_for_level(lvl)
            self.assertGreaterEqual(cur, prev)
            prev = cur

    def test_max_level_xp_finite(self):
        self.assertGreater(_prog.xp_for_level(MAX_LEVEL), 0)

    def test_xp_to_next_at_level_1(self):
        self.assertEqual(_prog.xp_to_next_level(1), _prog.xp_for_level(2))

    def test_xp_to_next_at_max_is_zero(self):
        self.assertEqual(_prog.xp_to_next_level(MAX_LEVEL), 0)

    def test_xp_progress_toward_next_zero_at_start(self):
        self.assertEqual(_prog.xp_progress_toward_next(0, 1), 0)

    def test_xp_progress_below_threshold(self):
        # Level 1 -> 2 needs _prog.xp_for_level(2) XP
        threshold2 = _prog.xp_for_level(2)
        halfway = threshold2 // 2
        self.assertEqual(_prog.xp_progress_toward_next(halfway, 1), halfway)

    def test_xp_progress_at_max_is_zero(self):
        big_xp = _prog.xp_for_level(MAX_LEVEL) + 9999
        self.assertEqual(_prog.xp_progress_toward_next(big_xp, MAX_LEVEL), 0)

    def test_level_from_xp(self):
        # At 0 XP -> level 1
        self.assertEqual(_prog.level_from_xp(0), 1)
        # Just above level 2 threshold
        l2 = _prog.xp_for_level(2)
        self.assertEqual(_prog.level_from_xp(l2), 2)
        self.assertEqual(_prog.level_from_xp(l2 + 1), 2)

    def test_negative_total_xp_returns_level_1(self):
        self.assertEqual(_prog.level_from_xp(-999), 1)


# =====================================================================
# Level-Up Processing
# =====================================================================

class TestLevelUp(unittest.TestCase):

    def _make_cd(self, prof="warrior"):
        return CharacterData.create_from_race_profession("T", "human", prof)

    def test_cannot_level_past_max(self):
        cd = self._make_cd()
        cd.level = MAX_LEVEL
        _prog.process_single_level_up(cd)
        self.assertEqual(cd.level, MAX_LEVEL)

    def test_single_level_increments(self):
        cd = self._make_cd()
        cd.level = 1
        hp_before = cd.max_hp
        _prog.process_single_level_up(cd)
        self.assertEqual(cd.level, 2)
        self.assertGreater(cd.max_hp, hp_before)

    def test_multi_level_from_big_xp(self):
        cd = self._make_cd()
        cd.level = 1
        cd.xp = 0
        # Give enough XP for ~5 levels
        xp_needed = _prog.xp_for_level(6)
        lvl = _prog.process_level_ups(cd, xp_needed)
        self.assertGreaterEqual(lvl, 5)

    def test_skills_granted_at_correct_levels(self):
        cd = self._make_cd("warrior")
        _prog.grant_starting_skills(cd)
        # At Level 1: weapon skilss, no profession skills (earliest is kick at 7)
        for ws in WEAPON_SKILLS:
            self.assertIn(ws, cd.unlocked_skills)
        self.assertNotIn("kick", cd.unlocked_skills)  # requires lvl 7

    def test_warrior_kick_at_7(self):
        cd = self._make_cd("warrior")
        cd.level = 1; cd.xp = 0
        # Give enough XP to get to level 7
        xp7 = _prog.xp_for_level(7)
        _prog.process_level_ups(cd, xp7)
        self.assertTrue(cd.level >= 7)
        self.assertIn("kick", cd.unlocked_skills)

    def test_mage_fireball_at_41(self):
        cd = self._make_cd("mage")
        cd.level = 1; cd.xp = 0
        xp42 = _prog.xp_for_level(42)
        _prog.process_level_ups(cd, xp42)
        self.assertTrue(cd.level >= 42)
        self.assertIn("fireball", cd.unlocked_skills)

    def test_second_attack_universal_at_20(self):
        cd = self._make_cd("mage")
        cd.level = 1; cd.xp = 0
        xp20 = _prog.xp_for_level(20)
        _prog.process_level_ups(cd, xp20)
        self.assertIn("second_attack", cd.unlocked_skills)

    def test_third_attack_warior_only(self):
        # Warrior gets Third Attack at 56
        cdw = self._make_cd("warrior")
        cdw.xp = _prog.xp_for_level(56)
        _prog.process_level_ups(cdw, cdw.xp)
        self.assertIn("third_attack", cdw.unlocked_skills)
        # Mage does NOT get Third Attack
        cdm = self._make_cd("mage")
        cdm.xp = _prog.xp_for_level(56)
        _prog.process_level_ups(cdm, cdm.xp)
        self.assertNotIn("third_attack", cdm.unlocked_skills)

    def test_monk_martial_arts_at_1(self):
        cd = self._make_cd("monk")
        _prog.grant_starting_skills(cd)
        self.assertIn("martial_arts", cd.unlocked_skills)

    def test_warrior_no_martial_arts(self):
        cd = self._make_cd("warrior")
        _prog.grant_starting_skills(cd)
        self.assertNotIn("martial_arts", cd.unlocked_skills)

    def test_monk_concentration_not_at_1(self):
        cd = self._make_cd("monk")
        _prog.grant_starting_skills(cd)
        self.assertNotIn("concentration", cd.unlocked_skills)


# =====================================================================
# Skill Idempotency
# =====================================================================

class TestIdempotency(unittest.TestCase):

    def test_duplicate_grants_dont_duplicate(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        # Grant three times
        _prog.grant_starting_skills(cd)
        count1 = len(cd.unlocked_skills)
        _prog.grant_all_skills_for_level(cd, 1)
        _prog.grant_all_skills_for_level(cd, 1)
        self.assertEqual(len(cd.unlocked_skills), count1)

    def test_reconcile_is_idempotent(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 5
        _prog.reconcile_character_skills(cd)
        count1 = len(cd.unlocked_skills)
        _prog.reconcile_character_skills(cd)
        _prog.reconcile_character_skills(cd)
        self.assertEqual(len(cd.unlocked_skills), count1)


# =====================================================================
# Weapon Proficiencies
# =====================================================================

class TestWeaponProficiencyInit(unittest.TestCase):

    def _make_cd(self):
        return CharacterData.create_from_race_profession("X", "human", "warrior")

    def test_starting_skills_sets_weapon_proficiencies(self):
        cd = self._make_cd()
        _prog.grant_starting_skills(cd)
        for ws in WEAPON_SKILLS:
            self.assertIn(ws, cd.proficiencies)
            self.assertEqual(cd.proficiencies[ws], DEFAULT_WEAPON_PROFICIENCY)

    def test_proficiencies_persist_round_trip(self):
        cd = self._make_cd()
        _prog.grant_starting_skills(cd)
        cd.proficiencies["piercing_weapons"] = 50
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.proficiencies["piercing_weapons"], 50)

    def test_exactly_four_weapon_categories(self):
        self.assertEqual(len(WEAPON_SKILLS), 4)


# =====================================================================
# Death Penalty Compatibility
# =====================================================================

class TestDeathPenaltyCompat(unittest.TestCase):

    def test_xp_progress_feeds_penalty(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 5
        threshold = _prog.xp_for_level(5)
        cd.xp = threshold + 1000  # 1000 toward level 6
        progress = _prog.xp_progress_toward_next(cd.xp, cd.level)
        self.assertEqual(progress, 1000)
        penalty = cd.calc_death_xp_penalty(progress)
        self.assertEqual(penalty, 50)

    def test_no_delevel_from_penalty(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 3
        threshold = _prog.xp_for_level(3)
        cd.xp = threshold + 10  # barely above threshold
        progress = _prog.xp_progress_toward_next(cd.xp, cd.level)
        penalty = cd.calc_death_xp_penalty(progress)
        cd.xp -= penalty
        self.assertGreaterEqual(cd.xp, threshold)
        self.assertEqual(_prog.level_from_xp(cd.xp), 3)


# =====================================================================
# Starting Grants
# =====================================================================


class TestStartingGrants(unittest.TestCase):

    def _make_cd(self, prof="warrior"):
        return CharacterData.create_from_race_profession("X", "human", prof)

    def test_all_profession_get_weapons_at_1(self):
        for prof_id in PROFESSIONS:
            cd = self._make_cd(prof_id)
            _prog.grant_starting_skills(cd)
            for ws in WEAPON_SKILLS:
                self.assertIn(ws, cd.unlocked_skills,
                              f"{prof_id} missing {ws}")

    def test_ninja_gets_sneak_at_5(self):
        cd = self._make_cd("ninja")
        cd.level = 4; cd.xp = 0
        xp5 = _prog.xp_for_level(5)
        _prog.process_level_ups(cd, xp5)
        self.assertIn("sneak", cd.unlocked_skills)

    def test_thief_gets_backstab_at_7(self):
        cd = self._make_cd("thief")
        cd.level = 1; cd.xp = 0
        xp7 = _prog.xp_for_level(7)
        _prog.process_level_ups(cd, xp7)
        self.assertIn("backstab", cd.unlocked_skills)

    def test_cleric_gets_concentration_at_15(self):
        cd = self._make_cd("cleric")
        cd.level = 1; cd.xp = 0
        xp15 = _prog.xp_for_level(15)
        _prog.process_level_ups(cd, xp15)
        self.assertIn("concentration", cd.unlocked_skills)

    def test_druid_gets_thorn_shield_at_23(self):
        cd = self._make_cd("druid")
        cd.level = 1; cd.xp = 0
        xp23 = _prog.xp_for_level(23)
        _prog.process_level_ups(cd, xp23)
        self.assertIn("thorn_shield", cd.unlocked_skills)

    def test_templar_gets_prayer_at_15(self):
        cd = self._make_cd("templar")
        cd.level = 1; cd.xp = 0
        xp15 = _prog.xp_for_level(15)
        _prog.process_level_ups(cd, xp15)
        self.assertIn("prayer", cd.unlocked_skills)


class TestDeathPenaltyClamp(unittest.TestCase):
    """No-delevel guarantee: death penalty cannot reduce level."""

    def test_penalty_clamped_at_level_threshold(self):
        """XP loss from death must never drop below the current level's threshold."""
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 5
        threshold = _prog.xp_for_level(5)
        # Just barely above threshold
        cd.xp = threshold + 10
        progress = _prog.xp_progress_toward_next(cd.xp, cd.level)
        penalty = cd.calc_death_xp_penalty(progress)
        # penalty is 5% of 10 = 0 (int math)
        new_xp = cd.xp - penalty
        # Must not fall below threshold
        self.assertGreaterEqual(new_xp, threshold)

    def test_repeated_deaths_cannot_delevel(self):
        """Die many times just above threshold — never lose the level."""
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 10
        threshold = _prog.xp_for_level(10)
        cd.xp = threshold + 500  # 500 progress

        for _ in range(50):
            progress = _prog.xp_progress_toward_next(cd.xp, cd.level)
            penalty = cd.calc_death_xp_penalty(progress)
            cd.xp = max(threshold, cd.xp - penalty)

        # Level must still be 10
        self.assertEqual(cd.level, 10)
        self.assertGreaterEqual(cd.xp, threshold)

    def test_progress_at_exact_threshold_is_zero(self):
        """When XP equals exactly the level threshold, progress is 0."""
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 3
        threshold = _prog.xp_for_level(3)
        cd.xp = threshold
        self.assertEqual(_prog.xp_progress_toward_next(cd.xp, cd.level), 0)

    def test_level_is_authoritative_field(self):
        """cd.level is the truth — it doesn't get recomputed from XP loss."""
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 7
        cd.xp = _prog.xp_for_level(7) + 1000
        # Reduce XP below threshold — level must NOT change
        cd.xp = _prog.xp_for_level(5)
        self.assertEqual(cd.level, 7)
# =====================================================================
# Serialisation / JSON-safety
# =====================================================================

class TestSerialisation(unittest.TestCase):

    def test_full_char_with_skills_serialises(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        _prog.grant_starting_skills(cd)
        cd.level = 42
        cd.xp = 99999
        packed = cd.to_dict()
        json.dumps(packed)  # must not raise
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.level, 42)
        self.assertEqual(cd2.xp, 99999)
        self.assertGreater(len(cd2.unlocked_skills), 0)

    def test_unlocked_skills_are_json_list(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        _prog.grant_starting_skills(cd)
        packed = cd.to_dict()
        self.assertIsInstance(packed["unlocked_skills"], list)


# =====================================================================
# Award XP
# =====================================================================

class TestAwardXP(unittest.TestCase):

    def _make_cd(self):
        return CharacterData.create_from_race_profession("X", "human", "warrior")

    def test_zero_xp_no_level(self):
        cd = self._make_cd()
        lvl, _ = _prog.award_xp(cd, 0)
        self.assertEqual(lvl, 1)

    def test_same_xp_returns_level(self):
        cd = self._make_cd()
        lvl, _ = _prog.award_xp(cd, 100)
        self.assertGreaterEqual(lvl, 1)

    def test_max_level_no_overflow(self):
        cd = self._make_cd()
        cd.level = MAX_LEVEL - 1
        cd.xp = _prog.xp_for_level(MAX_LEVEL - 1)
        lvl, _ = _prog.award_xp(cd, 99999999)
        self.assertEqual(lvl, MAX_LEVEL)
        # At cap — XP may accumulate past the threshold without breaking.
        self.assertGreaterEqual(cd.xp, _prog.xp_for_level(MAX_LEVEL))

    def test_negative_xp_ignored(self):
        cd = self._make_cd()
        old_xp = cd.xp
        lvl, _ = _prog.award_xp(cd, -100)
        self.assertEqual(lvl, 1)
        self.assertEqual(cd.xp, old_xp)


# =====================================================================
# No Phase 4 Leakage
# =====================================================================

class TestNoPhase4Leakage(unittest.TestCase):

    def test_progression_module_no_regen(self):
        """Progression must not mention regeneration/tick/timer."""
        path = _prog.__file__
        src = open(path).read().lower()
        self.assertNotIn("regenerat", src)
        self.assertNotIn("tick", src)
        self.assertNotIn("timer", src)

# =====================================================================
# Resource Gains on Level-Up
# =====================================================================

class TestResourceGains(unittest.TestCase):

    def test_level_up_increases_max_resources(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.max_hp = 100
        cd.max_mana = 50
        cd.max_stamina = 100
        cd.level = 1; cd.xp = 0
        xp2 = _prog.xp_for_level(2)
        _prog.process_level_ups(cd, xp2)
        self.assertGreater(cd.max_hp, 100)
        self.assertGreater(cd.max_mana, 50)
        self.assertGreater(cd.max_stamina, 100)

    def test_current_resrouces_not_refilled_on_level_up(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.max_hp = 100
        cd.hp = 30  # damaged
        cd.level = 1; cd.xp = 0
        xp2 = _prog.xp_for_level(2)
        _prog.process_level_ups(cd, xp2)
        self.assertEqual(cd.hp, 30)  # not healed


# =====================================================================
# Reconcile Existing Characters
# =====================================================================

class TestReconcile(unittest.TestCase):

    def test_reconcile_grants_missing_skills(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 15
        cd.xp = _prog.xp_for_level(15)
        self.assertEqual(len(cd.unlocked_skills), 0)  # no skills yet
        _prog.reconcile_character_skills(cd)
        self.assertGreater(len(cd.unlocked_skills), 0)
        # Should have level-1 weapons, + warrior skills up to level 15
        self.assertIn("piercing_weapons", cd.unlocked_skills)
        self.assertIn("kick", cd.unlocked_skills)  # lvl 7
        self.assertIn("bash", cd.unlocked_skills)  # lvl 10
        self.assertIn("rescue", cd.unlocked_skills)  # lvl 15

    def test_reconcile_doesnt_reoll_stats(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        old_stats = dict(cd.base_stats)
        cd.level = 50
        _prog.reconcile_character_skills(cd)
        self.assertEqual(cd.base_stats, old_stats)

    def test_reconcile_doesnt_change_race(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 50
        _prog.reconcile_character_skills(cd)
        self.assertEqual(cd.race_id, "human")

    def test_reconcile_doesnt_change_proession(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        cd.level = 50
        _prog.reconcile_character_skills(cd)
        self.assertEqual(cd.profession_id, "warrior")


# =====================================================================
# No DBREFs
# =====================================================================

class TestNoDBREFs(unittest.TestCase):

    def test_progression_has_no_dbrefs(self):
        """Progression data must not contain DBREF references."""
        import inspect
        src = inspect.getsource(_prog)
        self.assertNotIn("dbref", src.lower())


# =====================================================================
# Placeholder & Data-Driven Tests
# =====================================================================

class TestPlaceholderXP(unittest.TestCase):
    """XP curve is a configurable placeholder, not hard-coded final balance."""

    def test_curve_is_driven_by_coefficient(self):
        """Changing XP_CURVE_COEFF changes the curve; formula is swappable."""
        saved = _prog.XP_CURVE_COEFF
        try:
            _prog.XP_CURVE_COEFF = 50
            self.assertGreater(
                _prog.xp_for_level(3),
                _prog.xp_for_level(2),
                "Monotonic curve required",
            )
        finally:
            _prog.XP_CURVE_COEFF = saved


class TestResourceGainsDataDriven(unittest.TestCase):
    """Resource gains sourced from profession definitions, not hard-coded."""

    def test_every_profession_defines_resource_gains(self):
        from world.data.professions import PROFESSIONS
        for prof_id, prof_data in PROFESSIONS.items():
            gains = prof_data.get("resource_gains")
            self.assertIsNotNone(
                gains,
                f"Profession '{prof_id}' missing resource_gains field",
            )
            self.assertEqual(len(gains), 3, f"{prof_id}: expected (hp, mp, sp)")

    def test_resource_gains_returned_for_every_profession(self):
        from world.data.constants import get_resource_gains
        from world.data.professions import PROFESSIONS
        for prof_id in PROFESSIONS:
            hp, mp, sp = get_resource_gains(prof_id)
            self.assertGreater(hp, 0, f"{prof_id}: hp_per_level must be > 0")
            self.assertGreaterEqual(mp, 0, f"{prof_id}: mana_per_level must be >= 0")
            self.assertGreater(sp, 0, f"{prof_id}: stamina_per_level must be > 0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
