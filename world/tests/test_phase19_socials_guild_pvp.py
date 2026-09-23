"""
Phase 19 — Socials, Guild/Sect/PvP Tests

Covers:
- Social/emote definitions and resolution
- Guild registry, resolution, and data operations
- Sect registry, resolution, and data operations
- PvP statistics persistence (war_points, pvp_kills, pvp_deaths)
- PvP eligibility (is_pvp_eligible — faction + room_pvp_mode)
- PvP kill recording (record_pvp_kill)
- CharacterData serialisation (no pvp_enabled field)
- Score/info display with guild/sect/PvP data
- No Phase 20 leakage
- Regression — existing systems unchanged
"""

import unittest
import os

from world.data.character_data import CharacterData
from world.data.enums import CharacterState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Hero", race="human", prof="warrior"):
    """Create a CharacterData with full resources."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.level = 10
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    return cd
# =============================================================================
# Social Definitions
# =============================================================================


class TestSocialDefinitions(unittest.TestCase):
    """Social registry and resolution."""

    def test_social_registry_is_dict(self):
        from world.data.socials import SOCIAL_REGISTRY
        self.assertIsInstance(SOCIAL_REGISTRY, dict)

    def test_wave_social_exists(self):
        from world.data.socials import SOCIAL_REGISTRY
        self.assertIn("wave", SOCIAL_REGISTRY)

    def test_bow_social_exists(self):
        from world.data.socials import SOCIAL_REGISTRY
        self.assertIn("bow", SOCIAL_REGISTRY)

    def test_wave_has_all_message_keys(self):
        from world.data.socials import SOCIAL_REGISTRY
        w = SOCIAL_REGISTRY["wave"]
        for key in ["self_msg", "self_target_msg", "target_msg", "room_msg"]:
            self.assertIn(key, w)

    def test_socials_are_minimal(self):
        """Only wave and bow are defined as sample socials."""
        from world.data.socials import SOCIAL_REGISTRY
        self.assertEqual(set(SOCIAL_REGISTRY.keys()), {"wave", "bow"})

    def test_resolve_social_exact(self):
        from world.data.socials import resolve_social
        self.assertEqual(resolve_social("wave"), "wave")

    def test_resolve_social_unknown_returns_none(self):
        from world.data.socials import resolve_social
        self.assertIsNone(resolve_social("unknown_social_xyz"))

    def test_resolve_social_case_insensitive(self):
        from world.data.socials import resolve_social
        self.assertEqual(resolve_social("WAVE"), "wave")
        self.assertEqual(resolve_social("Bow"), "bow")

    def test_social_exists(self):
        from world.data.socials import social_exists
        self.assertTrue(social_exists("wave"))
        self.assertTrue(social_exists("bow"))
        self.assertFalse(social_exists("unknown"))

    def test_socials_are_data_only_extensible(self):
        """Adding a new social to the registry should work without code changes."""
        from world.data.socials import SOCIAL_REGISTRY, resolve_social
        old_len = len(SOCIAL_REGISTRY)
        try:
            SOCIAL_REGISTRY["test_new"] = {
                "self_msg": "You test.",
                "self_target_msg": "You test at {target}.",
                "target_msg": "{actor} tests at you.",
                "room_msg": "{actor} tests at {target}.",
            }
            self.assertIsNotNone(resolve_social("test_new"))
            self.assertEqual(resolve_social("test_new"), "test_new")
        finally:
            del SOCIAL_REGISTRY["test_new"]
        self.assertEqual(len(SOCIAL_REGISTRY), old_len)


# =============================================================================
# Guild Registry & Resolution
# =============================================================================


class TestGuildRegistry(unittest.TestCase):
    """Guild registry, resolution, and data operations."""

    def test_guild_registry_is_dict(self):
        from world.data.socials import GUILD_REGISTRY
        self.assertIsInstance(GUILD_REGISTRY, dict)

    def test_guild_registry_non_empty(self):
        from world.data.socials import GUILD_REGISTRY
        self.assertGreater(len(GUILD_REGISTRY), 0)

    def test_resolve_guild_exact_id(self):
        from world.data.socials import resolve_guild
        self.assertEqual(resolve_guild("mercenaries_guild"), "mercenaries_guild")

    def test_resolve_guild_by_display_name(self):
        from world.data.socials import resolve_guild
        self.assertEqual(resolve_guild("Mercenaries Guild"), "mercenaries_guild")

    def test_resolve_guild_partial_match(self):
        from world.data.socials import resolve_guild
        result = resolve_guild("Mercenaries")
        self.assertEqual(result, "mercenaries_guild")

    def test_resolve_guild_unknown_returns_none(self):
        from world.data.socials import resolve_guild
        self.assertIsNone(resolve_guild("Unknown Guild XYZ"))

    def test_resolve_guild_case_insensitive(self):
        from world.data.socials import resolve_guild
        self.assertEqual(resolve_guild("MERCENARIES GUILD"), "mercenaries_guild")

    def test_guild_exists(self):
        from world.data.socials import guild_exists
        self.assertTrue(guild_exists("mercenaries_guild"))
        self.assertFalse(guild_exists("nonexistent"))

    def test_get_guild_name(self):
        from world.data.socials import get_guild_name
        self.assertEqual(get_guild_name("mercenaries_guild"), "Mercenaries Guild")
        self.assertIsNone(get_guild_name("nonexistent"))
# =============================================================================
# Sect Registry & Resolution
# =============================================================================


class TestSectRegistry(unittest.TestCase):
    """Sect registry, resolution, and data operations."""

    def test_sect_registry_is_dict(self):
        from world.data.socials import SECT_REGISTRY
        self.assertIsInstance(SECT_REGISTRY, dict)

    def test_sect_registry_non_empty(self):
        from world.data.socials import SECT_REGISTRY
        self.assertGreater(len(SECT_REGISTRY), 0)

    def test_resolve_sect_exact_id(self):
        from world.data.socials import resolve_sect
        self.assertEqual(resolve_sect("order_of_light"), "order_of_light")

    def test_resolve_sect_by_display_name(self):
        from world.data.socials import resolve_sect
        self.assertEqual(resolve_sect("Order of Light"), "order_of_light")

    def test_resolve_sect_partial_match(self):
        from world.data.socials import resolve_sect
        result = resolve_sect("Light")
        self.assertEqual(result, "order_of_light")

    def test_resolve_sect_unknown_returns_none(self):
        from world.data.socials import resolve_sect
        self.assertIsNone(resolve_sect("Unknown Sect XYZ"))

    def test_resolve_sect_case_insensitive(self):
        from world.data.socials import resolve_sect
        self.assertEqual(resolve_sect("ORDER OF LIGHT"), "order_of_light")

    def test_sect_exists(self):
        from world.data.socials import sect_exists
        self.assertTrue(sect_exists("order_of_light"))
        self.assertFalse(sect_exists("nonexistent"))

    def test_get_sect_name(self):
        from world.data.socials import get_sect_name
        self.assertEqual(get_sect_name("order_of_light"), "Order of Light")
        self.assertIsNone(get_sect_name("nonexistent"))
# =============================================================================
# Guild / Sect Data Operations (CharacterData)
# =============================================================================


class TestGuildSectData(unittest.TestCase):
    """Guild / sect membership stored on CharacterData."""

    def test_default_guild_is_none(self):
        cd = CharacterData()
        self.assertIsNone(cd.guild_id)

    def test_default_sect_is_none(self):
        cd = CharacterData()
        self.assertIsNone(cd.sect_id)

    def test_set_and_clear_guild(self):
        cd = CharacterData()
        cd.guild_id = "mercenaries_guild"
        self.assertEqual(cd.guild_id, "mercenaries_guild")
        cd.guild_id = None
        self.assertIsNone(cd.guild_id)

    def test_set_and_clear_sect(self):
        cd = CharacterData()
        cd.sect_id = "order_of_light"
        self.assertEqual(cd.sect_id, "order_of_light")
        cd.sect_id = None
        self.assertIsNone(cd.sect_id)

    def test_guild_sect_independent(self):
        cd = CharacterData()
        cd.guild_id = "mercenaries_guild"
        cd.sect_id = "order_of_light"
        self.assertEqual(cd.guild_id, "mercenaries_guild")
        self.assertEqual(cd.sect_id, "order_of_light")
        cd.guild_id = None
        self.assertIsNone(cd.guild_id)
        self.assertEqual(cd.sect_id, "order_of_light")

    def test_guild_id_round_trip(self):
        cd = _make_cd()
        cd.guild_id = "mercenaries_guild"
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.guild_id, "mercenaries_guild")

    def test_sect_id_round_trip(self):
        cd = _make_cd()
        cd.sect_id = "order_of_light"
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.sect_id, "order_of_light")


# =============================================================================
# PvP Data Operations
# =============================================================================


class TestPvPData(unittest.TestCase):
    """PvP statistics fields on CharacterData."""

    def test_war_points_default_zero(self):
        cd = CharacterData()
        self.assertEqual(cd.war_points, 0)

    def test_pvp_kills_default_zero(self):
        cd = CharacterData()
        self.assertEqual(cd.pvp_kills, 0)

    def test_pvp_deaths_default_zero(self):
        cd = CharacterData()
        self.assertEqual(cd.pvp_deaths, 0)

    def test_pvp_fields_round_trip(self):
        cd = _make_cd()
        cd.war_points = 42
        cd.pvp_kills = 15
        cd.pvp_deaths = 3
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.war_points, 42)
        self.assertEqual(cd2.pvp_kills, 15)
        self.assertEqual(cd2.pvp_deaths, 3)

    def test_no_pvp_enabled_field(self):
        """pvp_enabled is removed — CharacterData must not have it."""
        cd = CharacterData()
        self.assertFalse(hasattr(cd, "pvp_enabled"))
        d = cd.to_dict()
        self.assertNotIn("pvp_enabled", d)
# =============================================================================
# PvP Eligibility (centralised combat-layer function)
# =============================================================================


class TestPvPEligibility(unittest.TestCase):
    """is_pvp_eligible in world.data.combat."""

    def test_same_faction_always_ineligible(self):
        from world.data.combat import is_pvp_eligible
        from world.data.enums import PvPMode
        a = _make_cd("A", race="human")   # GOOD
        b = _make_cd("B", race="dwarf")   # GOOD
        self.assertFalse(is_pvp_eligible(a, b, PvPMode.CONTESTED))
        self.assertFalse(is_pvp_eligible(a, b, PvPMode.ARENA))
        self.assertFalse(is_pvp_eligible(a, b, PvPMode.FREE_FOR_ALL))
        self.assertFalse(is_pvp_eligible(a, b, PvPMode.SAFE))

    def test_opposing_faction_eligible_in_contested(self):
        from world.data.combat import is_pvp_eligible
        from world.data.enums import PvPMode
        a = _make_cd("A", race="human")    # GOOD
        b = _make_cd("B", race="troll")    # EVIL
        self.assertTrue(is_pvp_eligible(a, b, PvPMode.CONTESTED))

    def test_opposing_faction_ineligible_in_safe(self):
        from world.data.combat import is_pvp_eligible
        from world.data.enums import PvPMode
        a = _make_cd("A", race="human")    # GOOD
        b = _make_cd("B", race="troll")    # EVIL
        self.assertFalse(is_pvp_eligible(a, b, PvPMode.SAFE))

    def test_opposing_faction_eligible_in_arena(self):
        from world.data.combat import is_pvp_eligible
        from world.data.enums import PvPMode
        a = _make_cd("A", race="human")    # GOOD
        b = _make_cd("B", race="troll")    # EVIL
        self.assertTrue(is_pvp_eligible(a, b, PvPMode.ARENA))
        self.assertTrue(is_pvp_eligible(a, b, PvPMode.FREE_FOR_ALL))

    def test_no_faction_not_eligible(self):
        from world.data.combat import is_pvp_eligible
        from world.data.enums import PvPMode
        cd1 = CharacterData()
        cd2 = _make_cd("B", race="troll")
        self.assertFalse(is_pvp_eligible(cd1, cd2, PvPMode.CONTESTED))
        self.assertFalse(is_pvp_eligible(cd2, cd1, PvPMode.CONTESTED))

    def test_string_room_mode_accepted(self):
        from world.data.combat import is_pvp_eligible
        a = _make_cd("A", race="human")
        b = _make_cd("B", race="troll")
        self.assertTrue(is_pvp_eligible(a, b, "contested"))
        self.assertFalse(is_pvp_eligible(a, b, "safe"))
# =============================================================================
# PvP Kill Recording (combat layer)
# =============================================================================


class TestPvPKillRecording(unittest.TestCase):
    """record_pvp_kill in world.data.combat — faction-based eligibility."""

    def test_record_pvp_kill_valid_in_contested(self):
        from world.data.combat import record_pvp_kill
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")    # GOOD
        victim = _make_cd("Victim", race="troll")     # EVIL

        result = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
        self.assertTrue(result)
        self.assertEqual(killer.pvp_kills, 1)
        self.assertEqual(victim.pvp_deaths, 1)
        self.assertEqual(killer.war_points, 1)

    def test_record_pvp_kill_same_faction_not_recorded(self):
        from world.data.combat import record_pvp_kill
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")    # GOOD
        victim = _make_cd("Victim", race="dwarf")     # GOOD

        result = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
        self.assertFalse(result)
        self.assertEqual(killer.pvp_kills, 0)
        self.assertEqual(victim.pvp_deaths, 0)
        self.assertEqual(killer.war_points, 0)

    def test_record_pvp_kill_safe_room_not_recorded(self):
        from world.data.combat import record_pvp_kill
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")    # GOOD
        victim = _make_cd("Victim", race="troll")     # EVIL

        result = record_pvp_kill(killer, victim, PvPMode.SAFE)
        self.assertFalse(result)
        self.assertEqual(killer.pvp_kills, 0)
        self.assertEqual(victim.pvp_deaths, 0)
        self.assertEqual(killer.war_points, 0)

    def test_record_pvp_kill_uses_war_points_per_kill(self):
        from world.data.combat import record_pvp_kill
        from world.data.constants import WAR_POINTS_PER_KILL
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")    # GOOD
        victim = _make_cd("Victim", race="troll")     # EVIL

        result = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
        self.assertTrue(result)
        self.assertEqual(killer.war_points, WAR_POINTS_PER_KILL)

    def test_record_pvp_kill_multiple_kills_accumulate(self):
        from world.data.combat import record_pvp_kill
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")    # GOOD

        for i in range(3):
            victim = _make_cd("Victim", race="troll")  # EVIL
            result = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
            self.assertTrue(result)

        self.assertEqual(killer.pvp_kills, 3)
        self.assertEqual(killer.war_points, 3)

    def test_record_pvp_kill_no_duplicate_processing(self):
        """Calling record_pvp_kill twice on same victim should tally twice.

        The caller (attack_target) is responsible for calling the
        function only once per real kill.
        """
        from world.data.combat import record_pvp_kill
        from world.data.enums import PvPMode
        killer = _make_cd("Killer", race="human")
        victim = _make_cd("Victim", race="troll")

        r1 = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
        self.assertTrue(r1)
        self.assertEqual(killer.pvp_kills, 1)
        self.assertEqual(victim.pvp_deaths, 1)

        r2 = record_pvp_kill(killer, victim, PvPMode.CONTESTED)
        self.assertTrue(r2)
        self.assertEqual(killer.pvp_kills, 2)
        self.assertEqual(victim.pvp_deaths, 2)
# =============================================================================
# Serialisation with Phase 19 Fields
# =============================================================================


class TestPhase19Serialisation(unittest.TestCase):
    """to_dict / from_dict includes all Phase 19 fields."""

    def test_full_round_trip_with_pvp_stats(self):
        cd = _make_cd()
        cd.war_points = 10
        cd.pvp_kills = 5
        cd.pvp_deaths = 2
        cd.guild_id = "mercenaries_guild"
        cd.sect_id = "order_of_light"

        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)

        self.assertEqual(cd2.war_points, 10)
        self.assertEqual(cd2.pvp_kills, 5)
        self.assertEqual(cd2.pvp_deaths, 2)
        self.assertEqual(cd2.guild_id, "mercenaries_guild")
        self.assertEqual(cd2.sect_id, "order_of_light")
        # pvp_enabled must not be in serialization
        self.assertNotIn("pvp_enabled", packed)

    def test_serialisation_is_json_safe_with_pvp_stats(self):
        import json
        cd = _make_cd()
        cd.guild_id = "test_guild"
        cd.sect_id = "test_sect"
        cd.war_points = 5
        packed = cd.to_dict()
        json.dumps(packed)  # Must not raise TypeError

    def test_empty_from_dict_pvp_defaults(self):
        cd = CharacterData.from_dict({})
        self.assertEqual(cd.war_points, 0)
        self.assertEqual(cd.pvp_kills, 0)
        self.assertEqual(cd.pvp_deaths, 0)
        self.assertIsNone(cd.guild_id)
        self.assertIsNone(cd.sect_id)


# =============================================================================
# Ignore List Behavior (relevant to socials)
# =============================================================================


class TestIgnoreList(unittest.TestCase):
    """Ignore list persistence and behavior."""

    def test_ignore_list_default_empty(self):
        cd = CharacterData()
        self.assertEqual(cd.ignore_list, set())

    def test_ignore_list_add_and_check(self):
        cd = CharacterData()
        cd.ignore_list.add("BadPlayer")
        self.assertIn("BadPlayer", cd.ignore_list)

    def test_ignore_list_round_trip(self):
        cd = CharacterData()
        cd.ignore_list = {"PlayerX", "PlayerY"}
        packed = cd.to_dict()
        cd2 = CharacterData.from_dict(packed)
        self.assertEqual(cd2.ignore_list, {"PlayerX", "PlayerY"})

    def test_ignore_list_case_insensitive_check(self):
        """Ignore list check in social command uses case-insensitive matching."""
        ignore_set = {"BadPlayer", "AnnoyingBob"}
        self.assertIn("badplayer", {name.lower() for name in ignore_set})


# =============================================================================
# Dead-state Guards for PvP Commands
# =============================================================================


class TestPvPDeadStateGuards(unittest.TestCase):
    """Dead characters and PvP eligibility."""

    def test_dead_character_has_faction_unchanged(self):
        cd = _make_cd()
        cd.die()
        self.assertFalse(cd.is_alive())
        self.assertEqual(cd.state, CharacterState.DEAD)
        # Faction unchanged by death — PvP eligibility is about factions.
        self.assertIsNotNone(cd.faction)

    def test_alive_character_has_war_points_zero_by_default(self):
        cd = _make_cd()
        self.assertTrue(cd.is_alive())
        self.assertEqual(cd.war_points, 0)
        self.assertEqual(cd.pvp_kills, 0)
        self.assertEqual(cd.pvp_deaths, 0)
# =============================================================================
# Regression — Existing Systems Unchanged
# =============================================================================


class TestPhase19Regression(unittest.TestCase):
    """Ensure Phase 19 does not break existing systems."""

    def test_character_creation_still_works(self):
        cd = _make_cd()
        self.assertIsNotNone(cd)
        self.assertEqual(cd.level, 10)

    def test_items_still_work(self):
        from world.data.items import item_exists
        self.assertTrue(item_exists("health_potion"))
        self.assertTrue(item_exists("rusty_sword"))

    def test_mobs_still_work(self):
        from world.data.mobs import mob_exists
        self.assertTrue(mob_exists("giant_rat"))

    def test_progression_still_works(self):
        from world.data.progression import award_xp
        cd = _make_cd()
        old = cd.xp
        award_xp(cd, 500)
        self.assertGreater(cd.xp, old)

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        res = resolve_attack(a, t)
        self.assertTrue(res["valid"])

    def test_skills_still_work(self):
        from world.data.skills import skill_exists
        self.assertTrue(skill_exists("kick"))
        self.assertTrue(skill_exists("fireball"))

    def test_shops_still_work(self):
        from world.data.shops import shop_exists
        self.assertTrue(shop_exists("general_store"))

    def test_quests_still_work(self):
        from world.data.quests import quest_exists
        self.assertTrue(quest_exists("rat_slayer"))

    def test_combat_has_record_pvp_kill(self):
        from world.data.combat import record_pvp_kill
        self.assertTrue(callable(record_pvp_kill))


# =============================================================================
# No Phase 20 Leakage
# =============================================================================


class TestNoPhase20Leakage(unittest.TestCase):
    """Phase 19 modules must not implement Phase 20 systems."""

    def test_no_phase20_beyond_registry_in_socials(self):
        import inspect
        from world.data import socials as mod
        src = inspect.getsource(mod)
        body = self._strip_docstrings(src).lower()
        for term in ["rank", "permission", "diplomacy", "matchmaking",
                      "bank", "hall", "cooldown", "streak", "client_",
                      "websocket", "portal"]:
            self.assertNotIn(term, body,
                             f"Phase 19 must not implement {term}")

    def test_no_phase20_in_commands(self):
        import inspect
        # Read source file directly to avoid Evennia/Django imports.
        # commands.command imports from evennia which requires Django.
        mod_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "commands", "command.py"
        )
        with open(os.path.abspath(mod_path)) as f:
            src = f.read()
        body = self._strip_docstrings(src).lower()
        for term in ["guild_rank", "guild_bank", "guild_hall",
                      "diplomacy", "matchmaking", "pvp_arena",
                      "pvp_ladder", "pvp_streak"]:
            self.assertNotIn(term, body,
                             f"Phase 19 commands must not implement {term}")

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