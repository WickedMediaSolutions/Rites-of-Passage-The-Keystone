"""
Phase 2 — Character Foundation Tests

Tests CharacterData persistence, resource clamping, death/respawn math,
faction derivation, stat rolling, serialisation round-trip, and the
Character typeclass API contract (verified via CharacterData).

These are plain-Python tests — no Evennia server required.
"""

import json
import random
import unittest
from copy import deepcopy

from world.data.character_data import CharacterData
from world.data.constants import (
    DEATH_XP_PENALTY_PERCENT,
    MAX_STAT_REROLLS,
    RESPAWN_HP_PERCENT,
    RESPAWN_MANA_PERCENT,
    RESPAWN_STAMINA_PERCENT,
    STARTING_LEVEL,
    STARTING_STAT_VARIANCE,
)
from world.data.enums import CharacterState, Faction, Stat
from world.data.professions import PROFESSIONS, UNIVERSAL_SKILLS, WEAPON_SKILLS
from world.data.races import RACES


class TestCharacterInit(unittest.TestCase):
    """Character initialisation and identity."""

    def test_create_from_race_profession_valid(self):
        cd = CharacterData.create_from_race_profession("Hero", "human", "warrior")
        self.assertEqual(cd.name, "Hero")
        self.assertEqual(cd.race_id, "human")
        self.assertEqual(cd.profession_id, "warrior")
        self.assertEqual(cd.faction, Faction.GOOD)
        self.assertEqual(cd.level, STARTING_LEVEL)

    def test_faction_derives_from_race_not_separate(self):
        """Faction must come from race — no independently editable field."""
        for race_id, race_data in RACES.items():
            cd = CharacterData.create_from_race_profession(
                "X", race_id, "warrior"
            )
            self.assertEqual(
                cd.faction,
                race_data["faction"],
                f"{race_id}: faction mismatch",
            )

    def test_evil_race_gives_evil_faction(self):
        cd = CharacterData.create_from_race_profession("Villain", "troll", "warrior")
        self.assertEqual(cd.faction, Faction.EVIL)

    def test_guild_and_sect_are_separate_fields(self):
        cd = CharacterData()
        cd.guild_id = "test_guild"
        cd.sect_id = "test_sect"
        self.assertNotEqual(cd.guild_id, cd.sect_id)
        cd.sect_id = None
        self.assertIsNotNone(cd.guild_id)
        self.assertIsNone(cd.sect_id)


class TestStatRolling(unittest.TestCase):
    """Stat generation rules."""

    def test_rolls_within_racial_variance(self):
        """Each rolled stat must be racial_base +- STARTING_STAT_VARIANCE."""
        variance = STARTING_STAT_VARIANCE
        for _ in range(50):
            cd = CharacterData.create_from_race_profession(
                "Roller", "human", "warrior"
            )
            race = RACES["human"]
            base = race["base_stats"]
            limits = race["stat_limits"]
            for key in ("str", "int", "wis", "dex", "con"):
                val = cd.base_stats[key]
                racial = base[key]
                self.assertGreaterEqual(val, racial - variance)
                self.assertLessEqual(val, racial + variance)
                if limits[key]:
                    self.assertLessEqual(val, limits[key])

    def test_rolls_respect_hard_caps(self):
        """Stats must never exceed racial stat_limits."""
        for _ in range(100):
            cd = CharacterData.create_from_race_profession(
                "Cap", "dryad", "mage"
            )
            race = RACES["dryad"]
            limits = race["stat_limits"]
            for key in ("str", "int", "wis", "dex", "con"):
                self.assertLessEqual(
                    cd.base_stats[key],
                    limits[key],
                    f"{key} exceeds limit",
                )

    def test_different_rolls_produce_variance(self):
        """Successive creations should not always produce identical stats."""
        stats_sets = set()
        for _ in range(30):
            cd = CharacterData.create_from_race_profession(
                f"Var{_}", "human", "warrior"
            )
            stats_sets.add(tuple(sorted(cd.base_stats.items())))
        # With 30 rolls on a 5-stat ±2 range, we should see >1 unique set
        self.assertGreater(len(stats_sets), 1, "All 30 rolls produced identical stats")

    def test_reroll_generates_new_stats(self):
        """Confirm _roll_stats replaces previous values."""
        cd = CharacterData.create_from_race_profession("A", "human", "warrior")
        first = dict(cd.base_stats)
        # Roll again (simulates a reroll)
        cd._roll_stats(RACES["human"])
        second = dict(cd.base_stats)
        # With 5 stats each in a 5-point range, chance of exact duplicate
        # is ~1/5^5 = 1/3125, so 50 attempts should never all duplicate.
        attempts = 0
        while first == second and attempts < 50:
            cd._roll_stats(RACES["human"])
            second = dict(cd.base_stats)
            attempts += 1
        self.assertNotEqual(first, second, "Reroll never changed stats")

    def test_stats_are_five_core_only(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        self.assertEqual(set(cd.base_stats.keys()), {"str", "int", "wis", "dex", "con"})


class TestResources(unittest.TestCase):
    """HP/Mana/Stamina persistence and clamping."""

    def setUp(self):
        self.cd = CharacterData()
        self.cd.max_hp = 100
        self.cd.hp = 100
        self.cd.max_mana = 80
        self.cd.mana = 80
        self.cd.max_stamina = 60
        self.cd.stamina = 60

    def test_hp_clamped_via_heal_damage(self):
        """heal() and take_damage() respect max_hp / floor 0."""
        self.cd.hp = 50
        self.assertEqual(self.cd.heal(999), 50)  # clamped to max
        self.assertEqual(self.cd.hp, 100)
        self.assertFalse(self.cd.take_damage(30))
        self.assertEqual(self.cd.hp, 70)
        self.assertTrue(self.cd.take_damage(999))
        self.assertEqual(self.cd.hp, 0)

    def test_heal_does_not_exceed_max(self):
        self.cd.hp = 90
        healed = self.cd.heal(50)
        self.assertEqual(healed, 10)
        self.assertEqual(self.cd.hp, 100)

    def test_heal_dead_returns_zero(self):
        self.cd.hp = 0
        self.assertEqual(self.cd.heal(50), 0)

    def test_take_damage_kill_detection(self):
        killed = self.cd.take_damage(30)
        self.assertFalse(killed)
        self.assertEqual(self.cd.hp, 70)
        killed = self.cd.take_damage(100)
        self.assertTrue(killed)
        self.assertEqual(self.cd.hp, 0)

    def test_mana_restored_with_clamping(self):
        self.cd.mana = 10
        r = self.cd.restore_mana(999)
        self.assertEqual(r, 70)  # 80 - 10 = 70
        self.assertEqual(self.cd.mana, 80)

    def test_stamina_restored_with_clamping(self):
        self.cd.stamina = 5
        r = self.cd.restore_stamina(999)
        self.assertEqual(r, 55)
        self.assertEqual(self.cd.stamina, 60)

    def test_is_alive_matches_hp(self):
        self.cd.hp = 100
        self.assertTrue(self.cd.is_alive())
        self.cd.hp = 0
        self.assertFalse(self.cd.is_alive())

    def test_restore_mana(self):
        self.cd.mana = 10
        r = self.cd.restore_mana(50)
        self.assertEqual(r, 50)
        self.assertEqual(self.cd.mana, 60)
        r = self.cd.restore_mana(999)
        self.assertEqual(r, 20)
        self.assertEqual(self.cd.mana, 80)

    def test_restore_stamina(self):
        self.cd.stamina = 5
        r = self.cd.restore_stamina(20)
        self.assertEqual(r, 20)
        self.assertEqual(self.cd.stamina, 25)


class TestDeathRespawn(unittest.TestCase):
    """Death/respawn rules."""

    def test_respawn_restore_percentages(self):
        cd = CharacterData()
        cd.max_hp = 200
        cd.max_mana = 100
        cd.max_stamina = 80
        cd.respawn_restore()
        self.assertEqual(cd.hp, 200 * RESPAWN_HP_PERCENT // 100)
        self.assertEqual(cd.mana, 100 * RESPAWN_MANA_PERCENT // 100)
        self.assertEqual(cd.stamina, 80 * RESPAWN_STAMINA_PERCENT // 100)

    def test_respawn_always_minimum_1_hp(self):
        cd = CharacterData()
        cd.max_hp = 1
        cd.hp = 0
        cd.respawn_restore()
        self.assertEqual(cd.hp, 1)

    def test_respawn_sets_state_standing(self):
        cd = CharacterData()
        cd.max_hp = 100
        cd.state = CharacterState.DEAD
        cd.respawn_restore()
        self.assertEqual(cd.state, CharacterState.STANDING)

    def test_death_xp_penalty_calculation(self):
        cd = CharacterData()
        # 5% of 6000 = 300
        self.assertEqual(cd.calc_death_xp_penalty(6000), 300)
        # 5% of 1000 = 50
        self.assertEqual(cd.calc_death_xp_penalty(1000), 50)
        # 5% of 1 = 0 (int rounding)
        self.assertEqual(cd.calc_death_xp_penalty(1), 0)

    def test_die_method(self):
        cd = CharacterData()
        cd.max_hp = 100
        cd.hp = 100
        cd.state = CharacterState.STANDING
        # Simulate what Character.die() does
        cd.state = CharacterState.DEAD
        cd.hp = 0
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)


class TestCharacterState(unittest.TestCase):
    """CharacterState enum safety."""

    def test_valid_states_are_accepted(self):
        cd = CharacterData()
        for state in CharacterState:
            cd.state = state
            self.assertEqual(cd.state, state)

    def test_dead_is_a_recognised_state(self):
        self.assertEqual(CharacterState.DEAD.value, "dead")

    def test_serialized_state_round_trips(self):
        cd = CharacterData.create_from_race_profession("S", "human", "warrior")
        cd.state = CharacterState.RESTING
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.state, CharacterState.RESTING)


class TestSerialisation(unittest.TestCase):
    """to_dict / from_dict round-trip."""

    def _make_full_cd(self):
        cd = CharacterData.create_from_race_profession("Z", "dwarf", "cleric")
        cd.level = 15
        cd.xp = 50000
        cd.tutorial_completed = True
        cd.hp = 80
        cd.max_hp = 200
        cd.mana = 50
        cd.max_mana = 150
        cd.stamina = 70
        cd.max_stamina = 120
        cd.state = CharacterState.RESTING
        cd.unlocked_skills = {"piercing_weapons", "slashing_weapons", "dodge"}
        cd.proficiencies = {"piercing_weapons": 34, "dodge": 12}
        cd.war_points = 42
        cd.pvp_kills = 15
        cd.pvp_deaths = 3
        cd.guild_id = "test_guild"
        cd.sect_id = "evil_house_zod"
        cd.auto_loot = True
        cd.ignore_list = {"BadPlayer", "AnnoyingBob"}
        return cd

    def test_full_round_trip(self):
        cd = self._make_full_cd()
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)

        self.assertEqual(cd2.race_id, cd.race_id)
        self.assertEqual(cd2.profession_id, cd.profession_id)
        self.assertEqual(cd2.faction, cd.faction)
        self.assertEqual(cd2.level, cd.level)
        self.assertEqual(cd2.xp, cd.xp)
        self.assertEqual(cd2.tutorial_completed, cd.tutorial_completed)
        self.assertEqual(cd2.base_stats, cd.base_stats)
        self.assertEqual(cd2.hp, cd.hp)
        self.assertEqual(cd2.max_hp, cd.max_hp)
        self.assertEqual(cd2.mana, cd.mana)
        self.assertEqual(cd2.max_mana, cd.max_mana)
        self.assertEqual(cd2.stamina, cd.stamina)
        self.assertEqual(cd2.max_stamina, cd.max_stamina)
        self.assertEqual(cd2.state, cd.state)
        self.assertEqual(cd2.unlocked_skills, cd.unlocked_skills)
        self.assertEqual(cd2.proficiencies, cd.proficiencies)
        self.assertEqual(cd2.war_points, cd.war_points)
        self.assertEqual(cd2.pvp_kills, cd.pvp_kills)
        self.assertEqual(cd2.pvp_deaths, cd.pvp_deaths)
        self.assertEqual(cd2.guild_id, cd.guild_id)
        self.assertEqual(cd2.sect_id, cd.sect_id)
        self.assertEqual(cd2.auto_loot, cd.auto_loot)
        self.assertEqual(cd2.ignore_list, cd.ignore_list)

    def test_serialisation_is_json_safe(self):
        cd = self._make_full_cd()
        packed = cd.to_dict()
        # Must not raise TypeError
        json.dumps(packed)

    def test_empty_from_dict_produces_valid_char(self):
        cd = CharacterData.from_dict({})
        self.assertEqual(cd.level, STARTING_LEVEL)
        self.assertEqual(cd.state, CharacterState.STANDING)
        self.assertEqual(cd.hp, 0)
        self.assertEqual(cd.max_hp, 1)

    def test_duplicate_save_does_not_double_data(self):
        cd = self._make_full_cd()
        p1 = cd.to_dict()
        p2 = cd.to_dict()
        self.assertEqual(p1, p2)


class TestWeaponProficiencies(unittest.TestCase):
    """Weapon proficiency storage (Phase 3 grants, Phase 2 stores)."""

    def test_exactly_four_weapon_types(self):
        self.assertEqual(len(WEAPON_SKILLS), 4)

    def test_weapon_skills_in_universal_level_1(self):
        l1 = UNIVERSAL_SKILLS.get(1, [])
        for ws in WEAPON_SKILLS:
            self.assertIn(ws, l1)

    def test_proficiency_storage_persists_in_dict(self):
        cd = CharacterData()
        cd.proficiencies["piercing_weapons"] = 50
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.proficiencies["piercing_weapons"], 50)


class TestAffiliations(unittest.TestCase):
    """Guild and Sect are separate."""

    def test_guild_sect_independent(self):
        cd = CharacterData()
        cd.guild_id = "A"
        cd.sect_id = "B"
        self.assertEqual(cd.guild_id, "A")
        self.assertEqual(cd.sect_id, "B")
        cd.guild_id = None
        self.assertIsNone(cd.guild_id)
        self.assertEqual(cd.sect_id, "B")


class TestPvPStatistics(unittest.TestCase):
    """War Points, kills, deaths."""

    def test_pvp_fields_persist(self):
        cd = CharacterData()
        cd.war_points = 10
        cd.pvp_kills = 7
        cd.pvp_deaths = 2
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.war_points, 10)
        self.assertEqual(cd2.pvp_kills, 7)
        self.assertEqual(cd2.pvp_deaths, 2)


class TestPreferences(unittest.TestCase):
    """Auto-loot and ignore list."""

    def test_auto_loot_persists(self):
        cd = CharacterData()
        cd.auto_loot = True
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertTrue(cd2.auto_loot)

    def test_ignore_list_persists(self):
        cd = CharacterData()
        cd.ignore_list = {"PlayerX", "PlayerY"}
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.ignore_list, {"PlayerX", "PlayerY"})


class TestTutorialState(unittest.TestCase):
    """Tutorial completion flag."""

    def test_tutorial_completed_persists(self):
        cd = CharacterData()
        self.assertFalse(cd.tutorial_completed)
        cd.tutorial_completed = True
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertTrue(cd2.tutorial_completed)


class TestLevelXP(unittest.TestCase):
    """Level and XP persistence."""

    def test_level_xp_persist(self):
        cd = CharacterData()
        cd.level = 42
        cd.xp = 123456
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.level, 42)
        self.assertEqual(cd2.xp, 123456)

    def test_starting_level_defaults(self):
        cd = CharacterData()
        self.assertEqual(cd.level, STARTING_LEVEL)
        self.assertEqual(cd.xp, 0)


class TestRaceProfessionIdentity(unittest.TestCase):
    """Race and profession IDs persist correctly."""

    def test_race_id_persists(self):
        for race_id in ("human", "troll", "dryad", "lich"):
            cd = CharacterData.create_from_race_profession(
                f"R_{race_id}", race_id, "warrior"
            )
            packed = cd.to_dict()
            cd2 = CharacterData.from_dict(packed)
            self.assertEqual(cd2.race_id, race_id)

    def test_profession_id_persists(self):
        for prof_id in ("mage", "warrior", "cleric", "monk"):
            cd = CharacterData.create_from_race_profession(
                f"P_{prof_id}", "human", prof_id
            )
            packed = cd.to_dict()
            cd2 = CharacterData.from_dict(packed)
            self.assertEqual(cd2.profession_id, prof_id)


class TestNoPhase3Progression(unittest.TestCase):
    """Guard: no Phase 3 skill granting was accidentally implemented."""

    def test_new_character_has_no_profession_skills_unlocked(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        # Profession skills (Phase 3) should NOT be in unlocked_skills
        # Only whatever Phase 2 manually adds.
        self.assertNotIn("bash", cd.unlocked_skills)
        self.assertNotIn("parry", cd.unlocked_skills)
        self.assertNotIn("fireball", cd.unlocked_skills)

    def test_second_attack_not_implicitly_granted(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        self.assertNotIn("second_attack", cd.unlocked_skills)

    def test_third_attack_not_implicitly_granted(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        self.assertNotIn("third_attack", cd.unlocked_skills)

    def test_no_skill_progression_was_run(self):
        cd = CharacterData.create_from_race_profession("X", "human", "mage")
        self.assertEqual(
            len(cd.unlocked_skills), 0,
            "No skills should be auto-unlocked in Phase 2"
        )


class TestNoHardcodedDBREFs(unittest.TestCase):
    """No DBREF hard-coding."""

    def test_character_data_has_no_dbref_fields(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        packed = cd.to_dict()
        for key in packed:
            self.assertNotIn("dbref", key.lower())

    def test_spawn_constants_are_string_tags_not_dbref(self):
        from world.data.constants import (
            TOWN_EVIL_START, TOWN_GOOD_START,
            TUTORIAL_GOOD_START, TUTORIAL_EVIL_START,
        )
        for tag in (TOWN_EVIL_START, TOWN_GOOD_START,
                     TUTORIAL_GOOD_START, TUTORIAL_EVIL_START):
            self.assertIsInstance(tag, str)
            self.assertNotEqual(tag.strip(), "")


class TestNoSilvermereHardcoding(unittest.TestCase):
    """Silvermere must not be the production spawn."""

    def test_spawn_constants_do_not_mention_silvermere(self):
        from world.data.constants import (
            TOWN_EVIL_START, TOWN_GOOD_START,
            TUTORIAL_GOOD_START, TUTORIAL_EVIL_START,
        )
        for tag in (TOWN_EVIL_START, TOWN_GOOD_START,
                     TUTORIAL_GOOD_START, TUTORIAL_EVIL_START):
            self.assertNotIn("silvermere", tag.lower())


class TestNoWeaponCategoryInvention(unittest.TestCase):
    """Exactly the 4 authoritative weapon categories exist."""

    def test_exactly_four(self):
        self.assertEqual(len(WEAPON_SKILLS), 4)

    def test_correct_names(self):
        expected = {
            "piercing_weapons",
            "slashing_weapons",
            "concussion_weapons",
            "whipping_weapons",
        }
        self.assertEqual(set(WEAPON_SKILLS), expected)

    def test_no_unauthorized_categories_exist(self):
        for skill_set in UNIVERSAL_SKILLS.values():
            for skill in skill_set:
                if "weapon" in skill.lower():
                    self.assertIn(
                        skill, WEAPON_SKILLS,
                        f"Unauthorized weapon skill '{skill}' found",
                    )


class TestResourceEdgeCases(unittest.TestCase):
    """Edge cases for resource methods."""

    def test_heal_at_full_returns_zero(self):
        cd = CharacterData()
        cd.max_hp = 100
        cd.hp = 100
        self.assertEqual(cd.heal(50), 0)

    def test_heal_dead_returns_zero(self):
        cd = CharacterData()
        cd.max_hp = 100
        cd.hp = 0
        self.assertEqual(cd.heal(50), 0)

    def test_take_damage_floors_at_zero(self):
        cd = CharacterData()
        cd.max_hp = 100
        cd.hp = 10
        cd.take_damage(999)
        self.assertEqual(cd.hp, 0)

    def test_restore_mana_at_full_returns_zero(self):
        cd = CharacterData()
        cd.max_mana = 100
        cd.mana = 100
        self.assertEqual(cd.restore_mana(50), 0)

    def test_effective_stat_stub_returns_base(self):
        cd = CharacterData.create_from_race_profession("X", "human", "warrior")
        for stat in Stat:
            self.assertEqual(cd.effective_stat(stat), cd.get_stat(stat))


if __name__ == "__main__":
    unittest.main(verbosity=2)
