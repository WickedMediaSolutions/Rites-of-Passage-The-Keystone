"""
Phase 4 — Authenticated Dashboard, Account→Character Fix,
           One-Character Enforcement & Access Control Tests
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


# ==========================================================================
# HELPER UNIT TESTS — get_evennia_account, get_account_character,
#                       account_has_character
# ==========================================================================


class TestGetEvenniaAccount(TestCase):
    """Unit tests for the new get_evennia_account helper."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_returns_none_for_none_user(self):
        from web.website.views.portal import get_evennia_account
        result = get_evennia_account(None)
        self.assertIsNone(result)

    def test_returns_none_for_anonymous_user(self):
        from web.website.views.portal import get_evennia_account
        anon = MagicMock()
        anon.is_authenticated = False
        result = get_evennia_account(anon)
        self.assertIsNone(result)

    @patch("evennia.accounts.models.AccountDB")
    def test_returns_account_when_found(self, MockAccountDB):
        from web.website.views.portal import get_evennia_account
        mock_acct = MagicMock()
        MockAccountDB.objects.filter.return_value.first.return_value = mock_acct
        result = get_evennia_account(self.user)
        self.assertEqual(result, mock_acct)
        MockAccountDB.objects.filter.assert_called_with(id=self.user.id)

    @patch("evennia.accounts.models.AccountDB")
    def test_returns_none_when_no_account_found(self, MockAccountDB):
        from web.website.views.portal import get_evennia_account
        MockAccountDB.objects.filter.return_value.first.return_value = None
        result = get_evennia_account(self.user)
        self.assertIsNone(result)

    @patch("evennia.accounts.models.AccountDB")
    def test_returns_none_on_exception(self, MockAccountDB):
        from web.website.views.portal import get_evennia_account
        MockAccountDB.objects.filter.side_effect = RuntimeError("DB down")
        result = get_evennia_account(self.user)
        self.assertIsNone(result)


class TestGetAccountCharacter(TestCase):
    """get_account_character must safely handle all account states."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="charuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_evennia_account")
    def test_returns_none_when_no_evennia_account(self, mock_gea):
        from web.website.views.portal import get_account_character
        mock_gea.return_value = None
        result = get_account_character(self.user)
        self.assertIsNone(result)

    @patch("web.website.views.portal.get_evennia_account")
    def test_returns_none_when_zero_characters(self, mock_gea):
        from web.website.views.portal import get_account_character
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = []
        mock_gea.return_value = mock_acct
        result = get_account_character(self.user)
        self.assertIsNone(result)

    @patch("web.website.views.portal.get_evennia_account")
    def test_returns_character_when_one_exists(self, mock_gea):
        from web.website.views.portal import get_account_character
        mock_char = MagicMock()
        mock_char.key = "DarkKnight"
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct
        result = get_account_character(self.user)
        self.assertEqual(result, mock_char)

    @patch("web.website.views.portal.get_evennia_account")
    def test_returns_first_character_when_multiple_exist(self, mock_gea):
        from web.website.views.portal import get_account_character
        mock_char1 = MagicMock()
        mock_char1.key = "First"
        mock_char2 = MagicMock()
        mock_char2.key = "Second"
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char1, mock_char2]
        mock_gea.return_value = mock_acct
        result = get_account_character(self.user)
        self.assertEqual(result, mock_char1)

    @patch("web.website.views.portal.get_evennia_account")
    def test_returns_none_when_characters_raises(self, mock_gea):
        from web.website.views.portal import get_account_character
        mock_acct = MagicMock()
        mock_acct.characters.all.side_effect = AttributeError("no .characters")
        mock_gea.return_value = mock_acct
        result = get_account_character(self.user)
        self.assertIsNone(result)

    @patch("web.website.views.portal.get_evennia_account")
    def test_handles_account_without_characters_attr(self, mock_gea):
        """Direct test: account object has no .characters attribute."""
        from web.website.views.portal import get_account_character

        class BadAccount:
            pass

        mock_gea.return_value = BadAccount()
        result = get_account_character(self.user)
        self.assertIsNone(result)


class TestAccountHasCharacter(TestCase):
    """One-character rule helper tests."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ruleuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_account_character")
    def test_returns_false_when_no_character(self, mock_gac):
        from web.website.views.portal import account_has_character
        mock_gac.return_value = None
        self.assertFalse(account_has_character(self.user))

    @patch("web.website.views.portal.get_account_character")
    def test_returns_true_when_character_exists(self, mock_gac):
        from web.website.views.portal import account_has_character
        mock_gac.return_value = MagicMock()
        self.assertTrue(account_has_character(self.user))


# ==========================================================================
# DASHBOARD ACCESS CONTROL TESTS
# ==========================================================================


class TestDashboardAccessControl(TestCase):
    """Dashboard must require authentication."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="dashuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_evennia_account")
    @patch("web.website.views.portal.get_server_status")
    def test_dashboard_redirects_anonymous_to_login(
        self, mock_status, mock_gea
    ):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("rop-dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    @patch("web.website.views.portal.get_evennia_account")
    @patch("web.website.views.portal.get_server_status")
    def test_dashboard_accessible_when_authenticated(
        self, mock_status, mock_gea
    ):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="dashuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        self.assertEqual(response.status_code, 200)


# ==========================================================================
# DASHBOARD — ZERO-CHARACTER STATE
# ==========================================================================


class TestDashboardZeroCharacter(TestCase):
    """Dashboard behaviour with authenticated account, zero characters."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="zerochar", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_zero_char_shows_username(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="zerochar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("zerochar", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_zero_char_shows_no_character_yet(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="zerochar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("No Character Yet", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_zero_char_shows_create_character_action(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="zerochar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Create Character", content)
        self.assertIn(reverse("rop-chargen"), content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_zero_char_does_not_show_character_section(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="zerochar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertNotIn("Your Character", content)


# ==========================================================================
# DASHBOARD — ONE-CHARACTER STATE
# ==========================================================================


class TestDashboardOneCharacter(TestCase):
    """Dashboard behaviour with authenticated account, one character."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="onechar", password="testpass123"
        )
        # Build a mock character with authoritative game data
        self.mock_char = MagicMock()
        self.mock_char.key = "DarkKnight"
        self.mock_char.level = 42
        self.mock_char.race_id = "human"
        self.mock_char.profession_id = "mage"
        # Mock faction as Faction enum or similar
        mock_faction = MagicMock()
        mock_faction.value = "good"
        self.mock_char.faction = mock_faction
        # Game data for guild/sect
        mock_game = MagicMock()
        mock_game.guild_id = "The Shadow Order"
        mock_game.sect_id = None
        self.mock_char.game = mock_game

        self.mock_acct = MagicMock()
        self.mock_acct.characters.all.return_value = [self.mock_char]

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_displays_character_name(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("DarkKnight", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_shows_character_section(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Your Character", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_shows_level(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("42", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_shows_faction(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Good", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_shows_guild(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("The Shadow Order", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_no_sect_renders_dash(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("—", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_one_char_does_not_show_no_character_yet(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_gea.return_value = self.mock_acct
        self.client.login(username="onechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertNotIn("No Character Yet", content)


# ==========================================================================
# DASHBOARD — MISSING OPTIONAL DATA
# ==========================================================================


class TestDashboardMissingOptionalData(TestCase):
    """Gracefully handle characters with missing optional fields."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="barechar", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_character_without_faction_renders(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_char = MagicMock()
        mock_char.key = "Minimal"
        mock_char.level = 1
        mock_char.race_id = None
        mock_char.profession_id = None
        mock_char.faction = None
        mock_char.game = None
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct

        self.client.login(username="barechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_character_without_race_profession_renders(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_char = MagicMock()
        mock_char.key = "Nameless"
        mock_char.level = 1
        mock_char.race_id = ""
        mock_char.profession_id = ""
        mock_faction = MagicMock()
        mock_faction.value = "good"
        mock_char.faction = mock_faction
        mock_char.game = MagicMock()
        mock_char.game.guild_id = None
        mock_char.game.sect_id = None
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct

        self.client.login(username="barechar", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("—", content)


# ==========================================================================
# DASHBOARD — ART HOOK
# ==========================================================================


class TestDashboardArtHook(TestCase):
    """Dashboard-header art hook must degrade gracefully."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="artuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_dashboard_renders_without_artwork(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="artuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("dashboard-header.png", content)


# ==========================================================================
# DASHBOARD ACTIONS
# ==========================================================================


class TestDashboardActions(TestCase):
    """Action cards: Play in Browser, Atlas, Account Settings, Deletion."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="actuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_play_in_browser_links_to_webclient(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="actuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Play in Browser", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_atlas_disabled_no_protocol(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="actuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Launch Evennia Atlas", content)
        self.assertIn("disabled", content)
        self.assertIn("Unavailable", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_account_settings_accessible(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="actuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Account Settings", content)
        self.assertIn(reverse("rop-account-settings"), content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_deletion_not_shown_for_zero_char(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="actuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertNotIn("Delete Character", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_deletion_disabled_for_one_char(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_char.level = 1
        mock_char.race_id = "human"
        mock_char.profession_id = "mage"
        mock_faction = MagicMock()
        mock_faction.value = "good"
        mock_char.faction = mock_faction
        mock_char.game = MagicMock()
        mock_char.game.guild_id = None
        mock_char.game.sect_id = None
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct

        self.client.login(username="actuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Delete Character", content)
        self.assertIn("disabled", content)
        self.assertIn("Unavailable", content)


# ==========================================================================
# ONE-CHARACTER RULE ENFORCEMENT
# ==========================================================================


class TestOneCharacterEnforcement(TestCase):
    """One-character-per-account rule must be enforced at portal layer."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ruleuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_chargen_placeholder_accessible_without_char(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="ruleuser", password="testpass123")
        response = self.client.get(reverse("rop-chargen"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_chargen_redirects_when_already_has_character(
        self, mock_gea, mock_status
    ):
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_char = MagicMock()
        mock_char.key = "ExistingChar"
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct

        self.client.login(username="ruleuser", password="testpass123")
        response = self.client.get(reverse("rop-chargen"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard/", response.url)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_second_character_workflow_not_exposed(self, mock_gea, mock_status):
        """Dashboard for one-char account must not show Create Character."""
        mock_status.return_value = {"online": True, "player_count": 1}
        mock_char = MagicMock()
        mock_char.key = "OnlyChar"
        mock_char.level = 5
        mock_char.race_id = "dwarf"
        mock_char.profession_id = "warrior"
        mock_faction = MagicMock()
        mock_faction.value = "evil"
        mock_char.faction = mock_faction
        mock_char.game = MagicMock()
        mock_char.game.guild_id = None
        mock_char.game.sect_id = None
        mock_acct = MagicMock()
        mock_acct.characters.all.return_value = [mock_char]
        mock_gea.return_value = mock_acct

        self.client.login(username="ruleuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        # "Your Character" section is shown; "Create Character" NOT shown
        self.assertIn("Your Character", content)
        # The zero-char Create Character link should not appear
        self.assertNotIn("No Character Yet", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_chargen_requires_authentication(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        response = self.client.get(reverse("rop-chargen"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


# ==========================================================================
# DASHBOARD SERVER STATUS
# ==========================================================================


class TestDashboardServerStatus(TestCase):
    """Server status must render on dashboard."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="statuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_server_status_online(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 5}
        mock_gea.return_value = None
        self.client.login(username="statuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Online", content)
        self.assertIn(">5<", content)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_server_status_offline(self, mock_gea, mock_status):
        mock_status.return_value = {"online": False, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="statuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("Offline", content)


# ==========================================================================
# PHASE 3 REGRESSION — existing auth behaviour must stay intact
# ==========================================================================


class TestPhase4Phase3Regression(TestCase):
    """Phase 3 authentication behaviour directly affected by Phase 4
    changes must remain working."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="regressuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_login_redirects_to_dashboard(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        response = self.client.post(
            reverse("rop-login"),
            {"username": "regressuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard/", response.url)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_logout_redirects_to_home(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="regressuser", password="testpass123")
        response = self.client.post(reverse("rop-logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_account_settings_still_accessible(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="regressuser", password="testpass123")
        response = self.client.get(reverse("rop-account-settings"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_login_page_still_renders(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        response = self.client.get(reverse("rop-login"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    def test_homepage_still_renders(self, mock_status):
        """Homepage must still render without auth."""
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)


# ==========================================================================
# NEWS SECTION ON DASHBOARD
# ==========================================================================


class TestDashboardNewsSection(TestCase):
    """News/updates area renders on dashboard."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="newsuser", password="testpass123"
        )

    @patch("web.website.views.portal.get_server_status")
    @patch("web.website.views.portal.get_evennia_account")
    def test_news_section_renders(self, mock_gea, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        mock_gea.return_value = None
        self.client.login(username="newsuser", password="testpass123")
        response = self.client.get(reverse("rop-dashboard"))
        content = response.content.decode("utf-8")
        self.assertIn("News", content)
        self.assertIn("Welcome to Rites of Passage", content)
