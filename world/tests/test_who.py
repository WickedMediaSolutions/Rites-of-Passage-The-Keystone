"""
Post-Phase-20 — Professional WHO List Tests

Tests cover:
- Table formatting with one player
- Table formatting with multiple players (sorted by level desc, name asc)
- Empty character list handling
- Missing optional data (None faction, guild, sect)
- ANSI-safe output (using regex stripping, no Evennia import)
- Long value truncation
"""

import re
import unittest

from world.data.character_data import CharacterData
from world.data.enums import Faction


def _strip_ansi(text: str) -> str:
    """Remove Evennia |x colour codes for readability checks."""
    return re.sub(r"\|[a-zA-Z]", "", text)


def _stub_guild_name(guild_id: str) -> str | None:
    registry = {
        "mercenaries_guild": "Mercenaries Guild",
        "merchants_guild": "Merchants Guild",
        "adventurers_guild": "Adventurers Guild",
        "shadow_syndicate": "Shadow Syndicate",
    }
    return registry.get(guild_id)


def _stub_sect_name(sect_id: str) -> str | None:
    registry = {
        "order_of_light": "Order of Light",
        "keepers_of_flame": "Keepers of the Flame",
        "house_of_shadow": "House of Shadow",
        "crimson_circle": "Crimson Circle",
    }
    return registry.get(sect_id)


def _make_cd(name="Hero", race="human", prof="warrior", level=10):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.level = level
    cd.max_hp = 100; cd.hp = 100
    cd.max_mana = 100; cd.mana = 100
    cd.max_stamina = 100; cd.stamina = 100
    return cd


def _make_characters(*specs):
    result = []
    for spec in specs:
        name, race, prof, level = spec[0], spec[1], spec[2], spec[3]
        faction = spec[4] if len(spec) > 4 else None
        guild = spec[5] if len(spec) > 5 else None
        sect = spec[6] if len(spec) > 6 else None
        cd = _make_cd(name, race, prof, level)
        cd.faction = faction
        cd.guild_id = guild
        cd.sect_id = sect
        result.append((None, cd))
    return result


class TestWhoEmptyList(unittest.TestCase):
    def test_empty_list_returns_empty_rows(self):
        from commands import build_who_rows
        rows = build_who_rows(
            [], _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertEqual(len(rows), 0)


class TestWhoSinglePlayer(unittest.TestCase):
    def test_single_player_basic_fields(self):
        from commands import build_who_rows
        chars = _make_characters(("Aldric", "human", "warrior", 10))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(len(row), 7)
        self.assertEqual(row[0], "Aldric")
        self.assertEqual(row[1], "10")
        self.assertEqual(row[2], "Human")
        self.assertEqual(row[3], "Warrior")

    def test_missing_faction_renders_dash(self):
        from commands import build_who_rows
        chars = _make_characters(("Nemo", "human", "warrior", 1, None))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertIn("\u2014", rows[0][4])

    def test_faction_good_blue_evil_red(self):
        from commands import build_who_rows
        good_rows = build_who_rows(
            _make_characters(("Goodie", "human", "cleric", 1, Faction.GOOD)),
            _stub_guild_name, _stub_sect_name, Faction,
        )
        evil_rows = build_who_rows(
            _make_characters(("Baddy", "drow", "warlock", 1, Faction.EVIL)),
            _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertIn("Good", good_rows[0][4])
        self.assertIn("Evil", evil_rows[0][4])
        self.assertIn("|b", good_rows[0][4])
        self.assertIn("|r", evil_rows[0][4])

    def test_with_guild_and_sect(self):
        from commands import build_who_rows
        chars = _make_characters(("Aldric", "human", "warrior", 10,
                                   Faction.GOOD, "mercenaries_guild", "order_of_light"))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        # Guild may be truncated at 14 chars; check prefix.
        self.assertTrue(rows[0][5].startswith("|mMercenaries"))
        self.assertIn("Order of Light", rows[0][6])


class TestWhoMultiplePlayers(unittest.TestCase):
    def test_sorted_by_level_desc_then_name_asc(self):
        from commands import build_who_rows
        chars = _make_characters(
            ("Bob", "human", "warrior", 3),
            ("Alice", "high_elf", "mage", 5),
            ("Charlie", "dwarf", "cleric", 5),
            ("Zara", "goblin", "thief", 1),
        )
        chars.sort(key=lambda c: (-c[1].level, c[1].name.lower()))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        names = [row[0] for row in rows]
        self.assertEqual(names, ["Alice", "Charlie", "Bob", "Zara"])


class TestWhoMissingOptionalData(unittest.TestCase):
    def test_missing_race_and_profession(self):
        from commands import build_who_rows
        cd = CharacterData()
        cd.name = "Ghost"
        cd.race_id = ""
        cd.profession_id = ""
        cd.level = 1
        cd.max_hp = 1; cd.hp = 1
        rows = build_who_rows(
            [(None, cd)], _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertEqual(rows[0][2], "?")
        self.assertEqual(rows[0][3], "?")

    def test_missing_name_falls_back(self):
        from commands import build_who_rows
        cd = CharacterData()
        cd.name = ""
        cd.race_id = "human"
        cd.profession_id = "warrior"
        cd.level = 1
        cd.max_hp = 1; cd.hp = 1
        rows = build_who_rows(
            [(None, cd)], _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertEqual(rows[0][0], "Unknown")

    def test_unregistered_guild_shows_fallback(self):
        from commands import build_who_rows
        chars = _make_characters(("Zed", "human", "warrior", 1,
                                   None, "some_unknown_guild", None))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        # May be truncated at 14 chars; check tiles-cased prefix.
        self.assertTrue(rows[0][5].startswith("|mSome Unknown"))

    def test_unregistered_sect_shows_fallback(self):
        from commands import build_who_rows
        chars = _make_characters(("Zed", "human", "warrior", 1,
                                   None, None, "some_unknown_sect"))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        # May be truncated at 14 chars; check title-cased prefix.
        self.assertTrue(rows[0][6].startswith("|cSome Unknown"))


class TestWhoAnsiSafe(unittest.TestCase):
    """Output remains usable without ANSI — no Evennia imports needed."""

    def test_faction_label_readable_without_ansi(self):
        from commands import build_who_rows
        chars = _make_characters(("A", "human", "warrior", 1, Faction.GOOD))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        clean = _strip_ansi(rows[0][4])
        self.assertEqual(clean, "Good")

    def test_no_faction_renders_em_dash(self):
        from commands import build_who_rows
        chars = _make_characters(("A", "human", "warrior", 1, None))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        clean = _strip_ansi(rows[0][4])
        self.assertEqual(clean, "\u2014")

    def test_guild_sect_missing_render_dash(self):
        from commands import build_who_rows
        chars = _make_characters(("A", "human", "warrior", 1, None, None, None))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        self.assertIn("\u2014", _strip_ansi(rows[0][5]))
        self.assertIn("\u2014", _strip_ansi(rows[0][6]))


class TestWhoLongValueTruncation(unittest.TestCase):
    def test_long_name_truncated(self):
        from commands import build_who_rows
        cd = CharacterData()
        cd.name = "Sir Reginald The Third"
        cd.race_id = "human"
        cd.profession_id = "warrior"
        cd.level = 1
        cd.max_hp = 1; cd.hp = 1
        rows = build_who_rows(
            [(None, cd)], _stub_guild_name, _stub_sect_name, Faction,
        )
        name = rows[0][0]
        self.assertLessEqual(len(name), 14)
        self.assertTrue(name.endswith("."))

    def test_long_race_truncated(self):
        from commands import build_who_rows
        cd = CharacterData()
        cd.name = "Test"
        cd.race_id = "mountain_giant_elder"
        cd.profession_id = "warrior"
        cd.level = 1
        cd.max_hp = 1; cd.hp = 1
        rows = build_who_rows(
            [(None, cd)], _stub_guild_name, _stub_sect_name, Faction,
        )
        race = rows[0][2]
        self.assertLessEqual(len(race), 12)
        self.assertTrue(race.endswith("."))

    def test_normal_race_not_truncated(self):
        from commands import build_who_rows
        chars = _make_characters(("A", "human", "warrior", 1))
        rows = build_who_rows(
            chars, _stub_guild_name, _stub_sect_name, Faction,
        )
        race = rows[0][2]
        self.assertEqual(race, "Human")
        self.assertFalse(race.endswith("."))
