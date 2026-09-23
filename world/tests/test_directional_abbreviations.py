"""
Directional Movement Abbreviation Tests

Verify that the custom Exit typeclass automatically injects directional
abbreviation aliases (n, s, e, w, ne, nw, se, sw, u, d) into every
ExitCommand cmdset.
"""

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newworld.server.conf.test_settings")
django.setup()

import unittest
from unittest.mock import Mock, patch

from evennia.utils import create as evennia_create
from evennia.commands import cmdset as cmdset_module

from world.data.constants import DIRECTION_ABBREVIATIONS as DIRECTION_MAP


# Use the ROP Exit typeclass (the one with our override).
EXIT_TYPECLASS = "typeclasses.exits.Exit"
ROOM_TYPECLASS = "typeclasses.rooms.Room"


class TestDirectionalAbbreviations(unittest.TestCase):
    """Test that create_exit_cmdset injects abbreviation aliases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure the custom Exit typeclass is loaded.
        cls.exit_typeclass = EXIT_TYPECLASS

    # ── full-name tests ──────────────────────────────────────────

    def test_north_full(self):
        self._assert_cmdset_has_key("north")

    def test_south_full(self):
        self._assert_cmdset_has_key("south")

    def test_east_full(self):
        self._assert_cmdset_has_key("east")

    def test_west_full(self):
        self._assert_cmdset_has_key("west")

    def test_northeast_full(self):
        self._assert_cmdset_has_key("northeast")

    def test_northwest_full(self):
        self._assert_cmdset_has_key("northwest")

    def test_southeast_full(self):
        self._assert_cmdset_has_key("southeast")

    def test_southwest_full(self):
        self._assert_cmdset_has_key("southwest")

    def test_up_full(self):
        self._assert_cmdset_has_key("up")

    def test_down_full(self):
        self._assert_cmdset_has_key("down")

    # ── abbreviation alias tests ─────────────────────────────────

    def test_n_alias(self):
        self._assert_cmdset_has_alias("north", "n")

    def test_s_alias(self):
        self._assert_cmdset_has_alias("south", "s")

    def test_e_alias(self):
        self._assert_cmdset_has_alias("east", "e")

    def test_w_alias(self):
        self._assert_cmdset_has_alias("west", "w")

    def test_ne_alias(self):
        self._assert_cmdset_has_alias("northeast", "ne")

    def test_nw_alias(self):
        self._assert_cmdset_has_alias("northwest", "nw")

    def test_se_alias(self):
        self._assert_cmdset_has_alias("southeast", "se")

    def test_sw_alias(self):
        self._assert_cmdset_has_alias("southwest", "sw")

    def test_u_alias(self):
        self._assert_cmdset_has_alias("up", "u")

    def test_d_alias(self):
        self._assert_cmdset_has_alias("down", "d")

    # ── helpers ──────────────────────────────────────────────────

    def _create_exit(self, direction):
        """Create an in-memory exit with given direction key."""
        dest = evennia_create.create_object(
            ROOM_TYPECLASS, key=f"Room_{direction}",
        )
        room = evennia_create.create_object(
            ROOM_TYPECLASS, key="TestRoom",
        )
        exit_obj = evennia_create.create_object(
            self.exit_typeclass,
            key=direction,
            location=room,
            destination=dest,
        )
        # Force exit to rebuild its cmdset for the test.
        exit_obj.at_cmdset_get(force_init=True)
        return exit_obj

    def _get_cmd_keys_and_aliases(self, exit_obj):
        """Return (key, aliases) for the first command in ExitCmdSet."""
        exit_cmdsets = [
            cs for cs in exit_obj.cmdset.cmdset_stack
            if cs.key == "ExitCmdSet"
        ]
        self.assertTrue(exit_cmdsets, "No ExitCmdSet found on exit object")
        cmds = exit_cmdsets[0].commands
        self.assertTrue(cmds, "ExitCmdSet has no commands")
        cmd = cmds[0]
        return cmd.key, list(cmd.aliases)

    def _assert_cmdset_has_key(self, direction):
        exit_obj = self._create_exit(direction)
        key, _ = self._get_cmd_keys_and_aliases(exit_obj)
        self.assertEqual(
            key, direction,
            f"Exit key should be '{direction}', got '{key}'",
        )

    def _assert_cmdset_has_alias(self, direction, abbreviation):
        exit_obj = self._create_exit(direction)
        _, aliases = self._get_cmd_keys_and_aliases(exit_obj)
        self.assertIn(
            abbreviation, aliases,
            f"'{direction}' exit should have alias '{abbreviation}' "
            f"(aliases={aliases})",
        )


class TestNonDirectionalExit(unittest.TestCase):
    """Non-directional exits should NOT get bogus aliases."""

    def test_custom_exit_no_alias_injection(self):
        room = evennia_create.create_object(
            ROOM_TYPECLASS, key="Room",
        )
        dest = evennia_create.create_object(
            ROOM_TYPECLASS, key="Dest",
        )
        exit_obj = evennia_create.create_object(
            EXIT_TYPECLASS,
            key="doorway",
            location=room,
            destination=dest,
        )
        exit_obj.at_cmdset_get(force_init=True)
        exit_cmdsets = [
            cs for cs in exit_obj.cmdset.cmdset_stack
            if cs.key == "ExitCmdSet"
        ]
        cmd = exit_cmdsets[0].commands[0]
        self.assertEqual(cmd.key, "doorway")
        self.assertEqual(
            cmd.aliases, [],
            "Non-directional exits should not receive direction aliases",
        )