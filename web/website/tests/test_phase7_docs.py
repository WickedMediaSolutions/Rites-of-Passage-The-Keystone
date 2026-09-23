"""
Phase 7 — Public Documentation & Content Pages Tests

Covers:
  - All Phase 7 pages are public (no login required)
  - Expected templates render (200)
  - Command index contains actual implemented commands
  - Nonexistent command returns 404
  - Command detail contains syntax and description
  - Docs search/filter behaves safely
  - Downloads contains no active download link
  - News page renders safe empty state
  - Lore page is public
  - Play in Browser link uses existing webclient route
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, Client
from django.urls import reverse


# ==========================================================================
# PUBLIC ACCESS — All Phase 7 pages must be accessible without login
# ==========================================================================


class Phase7PagesArePublic(TestCase):
    """Every Phase 7 doc page must return 200 for anonymous users."""

    def setUp(self):
        self.client = Client()

    def test_getting_started_public(self):
        url = reverse("getting-started")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_game_guide_public(self):
        url = reverse("game-guide")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_lore_public(self):
        url = reverse("lore")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_news_public(self):
        url = reverse("news")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_downloads_public(self):
        url = reverse("downloads")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_commands_index_public(self):
        url = reverse("commands")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_command_detail_public(self):
        url = reverse("command-detail", kwargs={"command_key": "score"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


# ==========================================================================
# TEMPLATE RENDERING — all expected templates should render successfully
# ==========================================================================


class TemplateRenderingTests(TestCase):
    """Verify that all Phase 7 templates render without errors."""

    def setUp(self):
        self.client = Client()

    def test_getting_started_renders(self):
        resp = self.client.get(reverse("getting-started"))
        content = resp.content.decode()
        self.assertIn("Getting Started", content)
        self.assertIn("Create Your Account", content)

    def test_game_guide_renders(self):
        resp = self.client.get(reverse("game-guide"))
        content = resp.content.decode()
        self.assertIn("Game Guide", content)
        self.assertIn("Character Basics", content)

    def test_lore_renders(self):
        resp = self.client.get(reverse("lore"))
        content = resp.content.decode()
        self.assertIn("Lore", content)
        self.assertIn("Factions", content)

    def test_news_renders(self):
        resp = self.client.get(reverse("news"))
        content = resp.content.decode()
        self.assertIn("News", content)

    def test_downloads_renders(self):
        resp = self.client.get(reverse("downloads"))
        content = resp.content.decode()
        self.assertIn("Downloads", content)

    def test_commands_index_renders(self):
        resp = self.client.get(reverse("commands"))
        content = resp.content.decode()
        self.assertIn("Command Reference", content)

    def test_command_detail_renders(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "score"})
        )
        content = resp.content.decode()
        self.assertIn("score", content.lower())


# ==========================================================================
# COMMAND INDEX — contains actual implemented commands
# ==========================================================================


class CommandIndexContainsImplementedCommands(TestCase):
    """The command index page must list commands that are actually
    registered in commands/default_cmdsets.py."""

    def setUp(self):
        self.client = Client()

    IMPLEMENTED_COMMANDS = [
        "score", "inventory", "equipment", "equip", "unequip",
        "attack", "use", "quest", "currency", "shop", "buy", "sell",
        "social", "guild", "sect", "pvp", "who",
    ]

    def test_all_implemented_commands_present(self):
        resp = self.client.get(reverse("commands"))
        content = resp.content.decode()
        for cmd in self.IMPLEMENTED_COMMANDS:
            self.assertIn(cmd, content,
                          f"Command '{cmd}' should appear on command index")

    def test_no_fabricated_commands(self):
        """Commands we know are NOT implemented must not appear."""
        resp = self.client.get(reverse("commands"))
        content = resp.content.decode().lower()
        # Commands the task explicitly said NOT to invent
        fabricated = ["trade", "party", "raid", "mount", "pet"]
        for cmd in fabricated:
            self.assertNotIn(
                f">/commands/{cmd}/".lower(),
                content,
                f"Fabricated command '{cmd}' should not have a documentation link"
            )


# ==========================================================================
# NONEXISTENT COMMAND — returns 404 or safe response
# ==========================================================================


class NonexistentCommandReturns404(TestCase):
    """Requesting a command that is not documented must return 404."""

    def setUp(self):
        self.client = Client()

    def test_nonexistent_command_404(self):
        url = reverse(
            "command-detail",
            kwargs={"command_key": "definitely_not_a_real_command"}
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_command_shows_not_found(self):
        url = reverse(
            "command-detail",
            kwargs={"command_key": "fabricated_cmd"}
        )
        resp = self.client.get(url)
        content = resp.content.decode()
        self.assertIn("Not Found", content)


# ==========================================================================
# COMMAND DETAIL — contains documented syntax and description
# ==========================================================================


class CommandDetailContentTests(TestCase):
    """Command detail pages must show syntax, description, and examples."""

    def setUp(self):
        self.client = Client()

    def test_score_detail_has_syntax(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "score"})
        )
        content = resp.content.decode()
        self.assertIn("Syntax", content)
        self.assertIn("score", content)
        self.assertIn("character", content.lower())

    def test_attack_detail_has_syntax(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "attack"})
        )
        content = resp.content.decode()
        self.assertIn("Syntax", content)
        self.assertIn("attack", content)

    def test_buy_detail_shows_examples(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "buy"})
        )
        content = resp.content.decode()
        self.assertIn("Examples", content)

    def test_quest_detail_shows_subcommands(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "quest"})
        )
        content = resp.content.decode()
        self.assertIn("accept", content)
        self.assertIn("abandon", content)
        self.assertIn("complete", content)

    def test_alias_resolution_works(self):
        """alias 'info' should resolve to score doc."""
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "info"})
        )
        content = resp.content.decode()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("score", content.lower())

    def test_equip_detail_has_arguments(self):
        resp = self.client.get(
            reverse("command-detail", kwargs={"command_key": "equip"})
        )
        content = resp.content.decode()
        self.assertIn("Arguments", content)


# ==========================================================================
# SEARCH / FILTER — behaves safely
# ==========================================================================


class CommandSearchTests(TestCase):
    """Search/filter must return safe results (no errors, no injections)."""

    def setUp(self):
        self.client = Client()

    def test_search_empty_query_returns_all(self):
        resp = self.client.get(reverse("commands"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("score", content)
        self.assertIn("who", content)

    def test_search_with_query_finds_matches(self):
        resp = self.client.get(reverse("commands") + "?q=attack")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("attack", content.lower())

    def test_search_with_no_match_safe(self):
        resp = self.client.get(reverse("commands") + "?q=zzz_nothing_zzz")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("No Commands Found", content)

    def test_search_with_special_characters_safe(self):
        """Special characters in search should not crash."""
        resp = self.client.get(reverse("commands") + "?q=<script>alert(1)</script>")
        self.assertEqual(resp.status_code, 200)

    def test_search_with_empty_string(self):
        resp = self.client.get(reverse("commands") + "?q=")
        self.assertEqual(resp.status_code, 200)


# ==========================================================================
# DOWNLOADS — no fabricated active download link
# ==========================================================================


class DownloadsNoActiveLinkTests(TestCase):
    """Downloads page must NOT contain an active Atlas download link."""

    def setUp(self):
        self.client = Client()

    def test_downloads_no_active_download_href(self):
        resp = self.client.get(reverse("downloads"))
        content = resp.content.decode()
        # Check for common patterns that would indicate a live download link
        self.assertNotIn(".exe", content.lower())
        self.assertNotIn(".msi", content.lower())
        self.assertNotIn("download/", content.lower())

    def test_downloads_mentions_not_released(self):
        resp = self.client.get(reverse("downloads"))
        content = resp.content.decode()
        self.assertIn("Not Yet Released", content)

    def test_downloads_links_to_webclient(self):
        """Downloads page should suggest browser play as alternative."""
        resp = self.client.get(reverse("downloads"))
        content = resp.content.decode()
        self.assertIn("Play in Browser", content)


# ==========================================================================
# NEWS — safe empty state when no real news source exists
# ==========================================================================


class NewsEmptyStateTests(TestCase):
    """News page must render a safe empty state without fabricated articles."""

    def setUp(self):
        self.client = Client()

    def test_news_shows_empty_state(self):
        resp = self.client.get(reverse("news"))
        content = resp.content.decode()
        self.assertIn("Official Updates Appear Here", content)

    def test_news_has_no_dates(self):
        """No fabricated article dates should appear."""
        resp = self.client.get(reverse("news"))
        content = resp.content.decode()
        # No 2025/2026 dates indicating fake articles
        self.assertNotIn("2025", content)
        self.assertNotIn("2026", content)

    def test_news_has_no_versions(self):
        """No fabricated version numbers should appear."""
        resp = self.client.get(reverse("news"))
        content = resp.content.decode()
        self.assertNotIn("v1.", content.lower())
        self.assertNotIn("version ", content.lower())
        self.assertNotIn("patch ", content.lower())


# ==========================================================================
# LORE — no required login
# ==========================================================================


class LorePagePublicTests(TestCase):
    """Lore page must be fully public — no redirect to login."""

    def setUp(self):
        self.client = Client()

    def test_lore_no_redirect(self):
        resp = self.client.get(reverse("lore"))
        self.assertEqual(resp.status_code, 200)
        # Must not redirect
        self.assertNotEqual(resp.status_code, 302)

    def test_lore_contains_factions(self):
        resp = self.client.get(reverse("lore"))
        content = resp.content.decode()
        self.assertIn("Factions", content)
        self.assertIn("Good", content)
        self.assertIn("Evil", content)

    def test_lore_no_fabricated_history(self):
        """No invented kingdom names, gods, wars, or faction lore."""
        resp = self.client.get(reverse("lore"))
        content = resp.content.decode()
        fabricated = ["Dragonia", "Eltheria", "God of", "Great War",
                       "Kingdom of", "Valoria", "Mordrath"]
        for term in fabricated:
            self.assertNotIn(term.lower(), content.lower(),
                             f"Fabricated lore '{term}' should not appear")


# ==========================================================================
# PLAY IN BROWSER — uses existing webclient route
# ==========================================================================


class PlayInBrowserLinkTests(TestCase):
    """Play in Browser links must point to the existing webclient route."""

    def setUp(self):
        self.client = Client()

    def test_getting_started_links_webclient(self):
        resp = self.client.get(reverse("getting-started"))
        content = resp.content.decode()
        webclient_url = reverse("webclient:index")
        self.assertIn(webclient_url, content)

    def test_downloads_links_webclient(self):
        resp = self.client.get(reverse("downloads"))
        content = resp.content.decode()
        webclient_url = reverse("webclient:index")
        self.assertIn(webclient_url, content)
