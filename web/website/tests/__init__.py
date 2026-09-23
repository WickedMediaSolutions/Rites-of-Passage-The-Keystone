"""
Phase 2 — Portal Homepage Live Status & CTA Tests

Tests homepage server-status rendering, player count, failure handling,
CTA links, and privacy guarantees using mocks for Evennia session state.
"""

from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse


class TestHomepageRenders(TestCase):
    """Homepage must return HTTP 200 regardless of server state."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_homepage_returns_200_online(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 5}
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    def test_homepage_returns_200_offline(self, mock_status):
        mock_status.return_value = {"online": False, "player_count": 0}
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.evennia")
    def test_homepage_returns_200_on_internal_failure(self, mock_evennia):
        """Homepage must not 500 when Evennia session handler fails."""
        mock_evennia.SESSION_HANDLER = None
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)


class TestOnlineStatusRendering(TestCase):
    """Online state must render green indicator and Online label."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_online_renders_green_dot(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 3}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertIn("rop-status__dot--online", content)
        self.assertNotIn("rop-status__dot--offline", content)
        self.assertIn("Online", content)

    @patch("web.website.views.portal.get_server_status")
    def test_online_shows_player_count(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 7}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertIn(">7<", content)

    @patch("web.website.views.portal.get_server_status")
    def test_online_shows_zero_players(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertIn(">0<", content)


class TestOfflineStatusRendering(TestCase):
    """Offline state must render distinct offline indicator."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_offline_renders_red_dot(self, mock_status):
        mock_status.return_value = {"online": False, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertIn("rop-status__dot--offline", content)
        self.assertNotIn("rop-status__dot--online", content)
        self.assertIn("Offline", content)


class TestPrivacyGuarantees(TestCase):
    """Public page must never expose character names or session-sensitive info."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_no_character_names_exposed(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("Gandalf", content)

    @patch("web.website.views.portal.get_server_status")
    def test_no_usernames_in_status_area(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 2}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("testuser", content.lower())

    @patch("web.website.views.portal.get_server_status")
    def test_no_ip_addresses_exposed(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("127.0.0.1", content)
        self.assertNotIn("10.", content)

    @patch("web.website.views.portal.get_server_status")
    def test_no_session_protocol_info(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("websocket", content.lower())
class TestPlayInBrowserLink(TestCase):
    """Play in Browser CTA must point to Evennia webclient route."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_play_in_browser_links_to_webclient(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        webclient_url = reverse("webclient:index")
        self.assertIn(webclient_url, content)


class TestCTAButtonsPresent(TestCase):
    """Existing Phase 1 CTA / nav buttons must still render."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_getting_started_link(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        gs_url = reverse("getting-started")
        self.assertIn(gs_url, content)
        self.assertIn("Getting Started", content)

    @patch("web.website.views.portal.get_server_status")
    def test_game_guide_link(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        gg_url = reverse("game-guide")
        self.assertIn(gg_url, content)

    @patch("web.website.views.portal.get_server_status")
    def test_downloads_link(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        dl_url = reverse("downloads")
        self.assertIn(dl_url, content)

    @patch("web.website.views.portal.get_server_status")
    def test_register_link_when_unauthenticated(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 0}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        reg_url = reverse("rop-register")
        self.assertIn(reg_url, content)
        self.assertIn("Create Account", content)


class TestPlaceholderTextRemoved(TestCase):
    """Phase 1 placeholder wording must be gone from the status panel."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_no_placeholder_wording_in_status(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertNotIn("Live status will appear", content)
        self.assertNotIn("Player count will appear", content)
        self.assertNotIn("Server uptime will appear", content)


class TestGetServerStatusHelper(TestCase):
    """Unit tests for the get_server_status helper directly."""

    @patch("web.website.views.portal.evennia")
    def test_returns_online_with_count_when_handler_available(self, mock_evennia):
        mock_handler = MagicMock()
        mock_handler.account_count.return_value = 3
        mock_evennia.SESSION_HANDLER = mock_handler

        from web.website.views.portal import get_server_status

        result = get_server_status()
        self.assertTrue(result["online"])
        self.assertEqual(result["player_count"], 3)
        mock_handler.account_count.assert_called_once()

    @patch("web.website.views.portal.evennia")
    def test_returns_offline_when_handler_is_none(self, mock_evennia):
        mock_evennia.SESSION_HANDLER = None

        from web.website.views.portal import get_server_status

        result = get_server_status()
        self.assertFalse(result["online"])
        self.assertEqual(result["player_count"], 0)

    @patch("web.website.views.portal.evennia")
    def test_returns_offline_on_handler_exception(self, mock_evennia):
        mock_handler = MagicMock()
        mock_handler.account_count.side_effect = RuntimeError("boom")
        mock_evennia.SESSION_HANDLER = mock_handler

        from web.website.views.portal import get_server_status

        result = get_server_status()
        self.assertFalse(result["online"])
        self.assertEqual(result["player_count"], 0)


class TestNavigationShellPages(TestCase):
    """Phase 1 shell pages must still render."""

    def setUp(self):
        self.client = Client()

    def test_getting_started_shell_renders(self):
        response = self.client.get(reverse("getting-started"))
        self.assertEqual(response.status_code, 200)

    def test_game_guide_shell_renders(self):
        response = self.client.get(reverse("game-guide"))
        self.assertEqual(response.status_code, 200)

    def test_lore_shell_renders(self):
        response = self.client.get(reverse("lore"))
        self.assertEqual(response.status_code, 200)

    def test_news_shell_renders(self):
        response = self.client.get(reverse("news"))
        self.assertEqual(response.status_code, 200)

    def test_downloads_shell_renders(self):
        response = self.client.get(reverse("downloads"))
        self.assertEqual(response.status_code, 200)