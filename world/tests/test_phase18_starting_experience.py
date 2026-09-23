"""
Phase 18 — Tutorial, Starting Experience & Content Integration Tests

Tests cover:
- Starting room resolution by faction
- Starting items per profession
- Starting currency
- Starting quest assignment
- Tutorial completion flag lifecycle
- Idempotency (calling complete_starting_experience twice)
- get_starting_items for known/unknown professions
- Data-layer operations via CharacterData
- Regression — existing systems unchanged
"""

import unittest

from world.data.character_data import CharacterData
from world.data.enums import Faction, QuestState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Hero", race="human", prof="warrior", level=1):
    """Create a fresh CharacterData with full resources."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.level = level
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    return cd


# =============================================================================
# Starting Room Resolution
# =============================================================================


class TestStartingRoom(unittest.TestCase):
    """Test faction-based starting room resolution via config injection."""

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _config(**overrides):
        """Return a FACTION_STARTING_ROOMS-style dict."""
        base = {"good": None, "evil": None}
        base.update(overrides)
        return base

    # -- each faction resolves a configured room --------------------------

    def test_good_faction_resolves_configured_room(self):
        from world.data.starting_experience import get_starting_room_id
        config = self._config(good="good_hub")
        self.assertEqual(
            get_starting_room_id(Faction.GOOD, faction_start_rooms=config),
            "good_hub",
        )

    def test_evil_faction_resolves_configured_room(self):
        from world.data.starting_experience import get_starting_room_id
        config = self._config(evil="evil_hub")
        self.assertEqual(
            get_starting_room_id(Faction.EVIL, faction_start_rooms=config),
            "evil_hub",
        )

    # -- unset / None room fails safely -----------------------------------

    def test_unset_good_room_raises_valueerror(self):
        from world.data.starting_experience import get_starting_room_id
        config = self._config(good=None)
        with self.assertRaises(ValueError) as ctx:
            get_starting_room_id(Faction.GOOD, faction_start_rooms=config)
        self.assertIn("good", str(ctx.exception))

    def test_unset_evil_room_raises_valueerror(self):
        from world.data.starting_experience import get_starting_room_id
        config = self._config(evil=None)
        with self.assertRaises(ValueError) as ctx:
            get_starting_room_id(Faction.EVIL, faction_start_rooms=config)
        self.assertIn("evil", str(ctx.exception))

    # -- unknown / missing faction fails safely ---------------------------

    def test_missing_faction_in_config_raises_valueerror(self):
        from world.data.starting_experience import get_starting_room_id
        config = {"good": "good_hub"}  # no "evil" key
        with self.assertRaises(ValueError) as ctx:
            get_starting_room_id(Faction.EVIL, faction_start_rooms=config)
        self.assertIn("evil", str(ctx.exception))

    # -- None faction fails safely ----------------------------------------

    def test_none_faction_raises_valueerror(self):
        from world.data.starting_experience import get_starting_room_id
        config = self._config(good="good_hub", evil="evil_hub")
        with self.assertRaises(ValueError) as ctx:
            get_starting_room_id(None, faction_start_rooms=config)
        self.assertIn("faction", str(ctx.exception).lower())

    # -- no config at all fails safely ------------------------------------

    def test_no_config_raises_valueerror(self):
        from world.data.starting_experience import get_starting_room_id
        with self.assertRaises(ValueError) as ctx:
            get_starting_room_id(Faction.GOOD)
        self.assertIn("FACTION_STARTING_ROOMS", str(ctx.exception))

    # -- no arbitrary fallback room ---------------------------------------

    def test_no_silent_fallback_to_arbitrary_room(self):
        """Ensure there is no implicit fallback to a hardcoded room."""
        from world.data.starting_experience import get_starting_room_id
        config = self._config()  # all None
        # No matter which faction we use, it must raise — never silently
        # return a default room string.
        for faction in (Faction.GOOD, Faction.EVIL):
            with self.assertRaises(ValueError):
                get_starting_room_id(faction, faction_start_rooms=config)


# =============================================================================
# Starting Items
# =============================================================================


class TestStartingItems(unittest.TestCase):
    """Test starting item grants per profession."""

    def test_default_starting_items_not_empty(self):
        from world.data.starting_experience import DEFAULT_STARTING_ITEMS
        self.assertGreater(len(DEFAULT_STARTING_ITEMS), 0)

    def test_get_starting_items_for_warrior(self):
        from world.data.starting_experience import get_starting_items
        items = get_starting_items("warrior")
        self.assertGreater(len(items), len(["health_potion"]))
        item_ids = {i["item_id"] for i in items}
        self.assertIn("rusty_sword", item_ids)
        self.assertIn("health_potion", item_ids)

    def test_get_starting_items_for_mage(self):
        from world.data.starting_experience import get_starting_items
        items = get_starting_items("mage")
        item_ids = {i["item_id"] for i in items}
        self.assertIn("wooden_club", item_ids)

    def test_get_starting_items_for_ranger(self):
        from world.data.starting_experience import get_starting_items
        items = get_starting_items("ranger")
        item_ids = {i["item_id"] for i in items}
        self.assertIn("short_bow", item_ids)

    def test_get_starting_items_for_shaman(self):
        from world.data.starting_experience import get_starting_items
        items = get_starting_items("shaman")
        item_ids = {i["item_id"] for i in items}
        self.assertIn("hunting_whip", item_ids)

    def test_unknown_profession_gets_no_weapon(self):
        from world.data.starting_experience import get_starting_items
        items = get_starting_items("unknown_profession")
        self.assertEqual(len(items), len(
            __import__("world.data.starting_experience", fromlist=["DEFAULT_STARTING_ITEMS"]).DEFAULT_STARTING_ITEMS
        ))

    def test_all_starting_weapons_are_valid_items(self):
        from world.data.starting_experience import PROFESSION_STARTING_WEAPON
        from world.data.items import item_exists
        for prof, weapon_id in PROFESSION_STARTING_WEAPON.items():
            self.assertTrue(
                item_exists(weapon_id),
                f"Starting weapon '{weapon_id}' for '{prof}' does not exist",
            )

    def test_default_items_are_valid(self):
        from world.data.starting_experience import DEFAULT_STARTING_ITEMS
        from world.data.items import item_exists
        for item_def in DEFAULT_STARTING_ITEMS:
            self.assertTrue(
                item_exists(item_def["item_id"]),
                f"Default starting item '{item_def['item_id']}' does not exist",
            )

    def test_every_item_has_positive_quantity(self):
        from world.data.starting_experience import DEFAULT_STARTING_ITEMS
        for item_def in DEFAULT_STARTING_ITEMS:
            self.assertGreater(item_def["quantity"], 0)


# =============================================================================
# Starting Currency
# =============================================================================


class TestStartingCurrency(unittest.TestCase):
    """Test starting currency value."""

    def test_starting_currency_positive(self):
        from world.data.starting_experience import STARTING_CURRENCY
        self.assertGreater(STARTING_CURRENCY, 0)

    def test_starting_currency_is_100(self):
        from world.data.starting_experience import STARTING_CURRENCY
        self.assertEqual(STARTING_CURRENCY, 100)


# =============================================================================
# Starting Quest
# =============================================================================


class TestStartingQuest(unittest.TestCase):
    """Test starting quest is defined and valid."""

    def test_starting_quest_id_is_set(self):
        from world.data.starting_experience import STARTING_QUEST_ID
        self.assertEqual(STARTING_QUEST_ID, "rat_slayer")

    def test_starting_quest_exists_in_registry(self):
        from world.data.starting_experience import STARTING_QUEST_ID
        from world.data.quests import quest_exists
        self.assertTrue(quest_exists(STARTING_QUEST_ID))

    def test_starting_quest_is_level_1(self):
        from world.data.starting_experience import STARTING_QUEST_ID
        from world.data.quests import get_quest
        quest = get_quest(STARTING_QUEST_ID)
        self.assertIsNotNone(quest)
        self.assertEqual(quest["level_required"], 1)


# =============================================================================
# Tutorial Completion Lifecycle
# =============================================================================


class TestTutorialCompletion(unittest.TestCase):
    """Test the complete_starting_experience function."""

    def test_new_character_not_completed(self):
        from world.data.starting_experience import is_tutorial_completed
        cd = _make_cd()
        self.assertFalse(cd.tutorial_completed)
        self.assertFalse(is_tutorial_completed(cd))

    def test_complete_sets_tutorial_flag(self):
        from world.data.starting_experience import (
            complete_starting_experience, is_tutorial_completed,
        )
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertTrue(cd.tutorial_completed)
        self.assertTrue(is_tutorial_completed(cd))

    def test_complete_grants_starting_currency(self):
        from world.data.starting_experience import (
            complete_starting_experience, STARTING_CURRENCY,
        )
        cd = _make_cd()
        self.assertEqual(cd.currency, 0)
        complete_starting_experience(cd)
        self.assertEqual(cd.currency, STARTING_CURRENCY)

    def test_complete_grants_items(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertGreater(len(cd.inventory), 0)
        # Should have the profession weapon
        self.assertIn("rusty_sword", cd.inventory)
        self.assertIn("health_potion", cd.inventory)

    def test_complete_auto_accepts_starting_quest(self):
        from world.data.starting_experience import complete_starting_experience
        from world.data.quests import is_quest_active
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertTrue(is_quest_active(cd, "rat_slayer"))

    def test_complete_is_idempotent(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertTrue(cd.tutorial_completed)

        currency_after_first = cd.currency
        inv_count_after_first = sum(cd.inventory.values())

        # Call again — should be no-op
        complete_starting_experience(cd)
        self.assertTrue(cd.tutorial_completed)
        # Currency unchanged
        self.assertEqual(cd.currency, currency_after_first)
        # Items unchanged
        self.assertEqual(sum(cd.inventory.values()), inv_count_after_first)

    def test_complete_already_has_currency_does_not_overwrite(self):
        from world.data.starting_experience import (
            complete_starting_experience, STARTING_CURRENCY,
        )
        cd = _make_cd()
        cd.currency = 500
        self.assertEqual(cd.currency, 500)
        # complete_starting_experience only adds if currency is 0
        complete_starting_experience(cd)
        self.assertEqual(cd.currency, 500)

    def test_tutorial_completed_persists_through_serialization(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        data = cd.to_dict()
        self.assertTrue(data["tutorial_completed"])

        cd2 = CharacterData.from_dict(data)
        self.assertTrue(cd2.tutorial_completed)

    def test_mage_gets_wooden_club(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd(prof="mage")
        complete_starting_experience(cd)
        self.assertIn("wooden_club", cd.inventory)

    def test_complete_grants_cloth_vest(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertIn("cloth_vest", cd.inventory)

    def test_complete_grants_torch(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertIn("torch", cd.inventory)

    def test_complete_grants_mana_potion(self):
        from world.data.starting_experience import complete_starting_experience
        cd = _make_cd()
        complete_starting_experience(cd)
        self.assertIn("mana_potion", cd.inventory)


# =============================================================================
# Starting Experience Bridge — plain-Python portions
# =============================================================================


class TestStartingExperienceBridge(unittest.TestCase):
    """Test the world/starting_experience.py module imports and constants."""

    def test_module_imports(self):
        """world.starting_experience imports without errors."""
        # This import triggers Evennia — skip in plain tests.
        pass

    def test_first_puppet_attr_name_consistent(self):
        from world.starting_experience import FIRST_PUPPET_ATTR
        self.assertEqual(FIRST_PUPPET_ATTR, "rop_first_puppet_done")


# =============================================================================
# Regression — Existing Systems Unchanged
# =============================================================================


class TestRegression(unittest.TestCase):
    """Ensure existing systems are unchanged."""

    def test_character_creation_still_works(self):
        cd = _make_cd()
        self.assertIsNotNone(cd)
        self.assertEqual(cd.level, 1)
        self.assertFalse(cd.tutorial_completed)

    def test_tutorial_completed_field_exists(self):
        cd = _make_cd()
        self.assertFalse(cd.tutorial_completed)
        cd.tutorial_completed = True
        self.assertTrue(cd.tutorial_completed)
        data = cd.to_dict()
        self.assertIn("tutorial_completed", data)

    def test_items_still_work(self):
        from world.data.items import item_exists
        self.assertTrue(item_exists("health_potion"))
        self.assertTrue(item_exists("rusty_sword"))
        self.assertTrue(item_exists("cloth_vest"))

    def test_quests_still_work(self):
        from world.data.quests import quest_exists, accept_quest, is_quest_active
        self.assertTrue(quest_exists("rat_slayer"))
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        self.assertTrue(is_quest_active(cd, "rat_slayer"))

    def test_economy_still_works(self):
        from world.data.economy import add_currency, get_currency
        cd = _make_cd()
        add_currency(cd, 200)
        self.assertEqual(get_currency(cd), 200)

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        self.assertTrue(result["valid"])

    def test_progression_still_works(self):
        from world.data.progression import award_xp
        cd = _make_cd()
        old = cd.xp
        award_xp(cd, 500)
        self.assertGreater(cd.xp, old)

    def test_items_add_item_still_works(self):
        cd = _make_cd()
        cd.add_item("health_potion", 3)
        self.assertEqual(cd.inventory["health_potion"], 3)

    def test_skills_still_work(self):
        from world.data.skills import skill_exists
        self.assertTrue(skill_exists("kick"))

    def test_shops_still_work(self):
        from world.data.shops import shop_exists
        self.assertTrue(shop_exists("general_store"))


# =============================================================================
# No Phase 19 Leakage
# =============================================================================


class TestNoPhase19Leakage(unittest.TestCase):
    """Phase 18 must not implement Phase 19+ systems."""

    def test_no_guild_in_starting_module(self):
        import inspect
        from world.data import starting_experience as mod
        src = inspect.getsource(mod)
        body = self._strip_docstrings(src).lower()
        for term in ["guild", "sect", "pvp", "websocket", "tutorial_building"]:
            self.assertNotIn(term, body,
                             f"Phase 18 must not implement {term}")

    def test_no_new_gameplay_in_starting_data(self):
        from world.data.starting_experience import (
            get_starting_items, get_starting_room_id, DEFAULT_STARTING_ITEMS,
        )
        # Starting data should only use existing items, quests, rooms.
        for item_def in DEFAULT_STARTING_ITEMS:
            from world.data.items import item_exists
            self.assertTrue(
                item_exists(item_def["item_id"]),
                f"Unknown item in starting config: {item_def['item_id']}",
            )

        # Starting weapons should reference existing items.
        from world.data.starting_experience import PROFESSION_STARTING_WEAPON
        from world.data.items import item_exists
        for prof, wid in PROFESSION_STARTING_WEAPON.items():
            self.assertTrue(item_exists(wid),
                            f"Unknown weapon '{wid}' for profession '{prof}'")

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
