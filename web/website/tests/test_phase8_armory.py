"""Phase 8 — Login-Required Armory Tests."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import Client, TestCase
from django.urls import reverse


def _make_mock_char(name, race_id=None, prof_id=None, level=1, xp=0,
                    faction="good", hp=100, max_hp=100, mana=100,
                    max_mana=100, stamina=100, max_stamina=100,
                    base_stats=None, guild_id=None, sect_id=None):
    """Create a mock Evennia Character with armory-appropriate attributes.

    The returned mock is configured so that Django template variable
    resolution (which tries dict-style ``__getitem__`` before attribute
    access) correctly resolves to the concrete attribute values rather
    than creating nested MagicMock instances.
    """
    if base_stats is None:
        base_stats = {"str": 25, "int": 25, "wis": 25, "dex": 25, "con": 25}
    char = MagicMock()
    char.key = name
    char.race_id = race_id
    char.profession_id = prof_id
    char.level = level
    char.xp = xp
    char.hp = hp
    char.max_hp = max_hp
    char.mana = mana
    char.max_mana = max_mana
    char.stamina = stamina
    char.max_stamina = max_stamina
    char.war_points = 0
    char.pvp_kills = 0
    char.pvp_deaths = 0

    # Affiliations — set on char directly because _build_armory_display
    # reads char.guild_id / char.sect_id, not char.game.guild_id.
    char.guild_id = guild_id
    char.sect_id = sect_id

    from world.data.enums import Faction
    char.faction = Faction(faction) if faction else None

    mock_game = MagicMock()
    mock_game.base_stats = base_stats
    mock_game.state = None
    mock_game.guild_id = guild_id
    mock_game.sect_id = sect_id
    mock_game.unlocked_skills = set()
    mock_game.proficiencies = {}
    mock_game.equipment = {}
    char.game = mock_game

    # Prevent Django template resolution from short-circuiting on
    # MagicMock.__getitem__ (which returns a fresh MagicMock for
    # *every* key lookup).  Raising KeyError makes the template
    # engine fall through to attribute access.
    char.__getitem__.side_effect = KeyError

    return char


class ArmoryLoginRequiredTests(TestCase):
    """Armory pages require authentication."""

    def setUp(self):
        self.client = Client()

    def test_armory_index_requires_login(self):
        response = self.client.get(reverse("rop-armory"))
        self.assertIn(response.status_code, (302, 301))

    def test_armory_profile_requires_login(self):
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "someone"}))
        self.assertIn(response.status_code, (302, 301))

    def test_authenticated_can_access_armory_index(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="armoryuser", password="testpass123")
        self.client.login(username="armoryuser", password="testpass123")
        response = self.client.get(reverse("rop-armory"))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_can_access_armory_profile(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="armoryprof", password="testpass123")
        self.client.login(username="armoryprof", password="testpass123")
        with patch("web.website.views.armory._resolve_character_by_name") as mock_resolve:
            mock_char = _make_mock_char("TestChar", race_id="human")
            mock_resolve.return_value = mock_char
            response = self.client.get(
                reverse("rop-armory-character", kwargs={"character_name": "TestChar"}))
            self.assertEqual(response.status_code, 200)


class ArmoryIndexTests(TestCase):
    """Armory index browse and search behaviour."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        user = User.objects.create_user(
            username="armoryindex", password="testpass123")
        self.client.login(username="armoryindex", password="testpass123")

    @patch("web.website.views.armory.ObjectDB")
    def test_default_browse_alphabetical(self, mock_ObjectDB):
        """Default armory browse is sorted case-insensitively by name."""
        # Characters in deliberately unsorted order — trust the production
        # _resolve_characters() sorted() call to produce the right order.
        chars = [
            _make_mock_char("Bob", race_id="human"),
            _make_mock_char("Alice", race_id="human"),
            _make_mock_char("charlie", race_id="human"),
        ]
        # Mock the ObjectDB.objects.filter().order_by() chain to return
        # the raw unsorted list, allowing the real _resolve_characters()
        # sorting logic to execute.
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = chars
        mock_ObjectDB.objects.filter.return_value = mock_qs

        response = self.client.get(reverse("rop-armory"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        alice_idx = content.index("Alice")
        bob_idx = content.index("Bob")
        self.assertLess(alice_idx, bob_idx)
        # Sanity: lowercase charlie should appear after both
        charlie_idx = content.index("charlie")
        self.assertLess(bob_idx, charlie_idx)

    @patch("web.website.views.armory._resolve_characters")
    def test_only_player_characters_appear(self, mock_resolve):
        mock_resolve.return_value = [
            _make_mock_char("PlayerOne", race_id="human"),
        ]
        response = self.client.get(reverse("rop-armory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PlayerOne")

    @patch("web.website.views.armory._resolve_characters")
    def test_search_case_insensitive(self, mock_resolve):
        mock_resolve.return_value = [
            _make_mock_char("Abc", race_id="human"),
            _make_mock_char("XYZ", race_id="human"),
        ]
        response = self.client.get(reverse("rop-armory") + "?q=abc")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abc")
        self.assertNotContains(response, "XYZ")

    @patch("web.website.views.armory._resolve_characters")
    def test_search_partial_name(self, mock_resolve):
        mock_resolve.return_value = [
            _make_mock_char("TestCharacter", race_id="human"),
            _make_mock_char("Other", race_id="human"),
        ]
        response = self.client.get(reverse("rop-armory") + "?q=estCh")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestCharacter")
        self.assertNotContains(response, "Other")

    @patch("web.website.views.armory._resolve_characters")
    def test_empty_search_returns_browse(self, mock_resolve):
        mock_resolve.return_value = [
            _make_mock_char("A", race_id="human"),
        ]
        response = self.client.get(reverse("rop-armory") + "?q=")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A")

    @patch("web.website.views.armory._resolve_characters")
    def test_search_no_expose_private_data(self, mock_resolve):
        """Search results must never leak private account/character sentinels."""
        char = _make_mock_char("TestChar", race_id="human")
        # Inject unmistakable private sentinel data that should NEVER be rendered
        char.email = "private-armory-email@example.invalid"
        char._password_hash = "PRIVATE_ARMORY_PASSWORD_SENTINEL"
        char._internal = "PRIVATE_ARMORY_INTERNAL_SENTINEL"
        mock_resolve.return_value = [char]
        response = self.client.get(reverse("rop-armory") + "?q=Test")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Confirm the character IS visible (proves the page rendered correctly)
        self.assertContains(response, "TestChar")
        # Verify none of the private sentinel values leak into the output
        self.assertNotIn("private-armory-email@example.invalid", content)
        self.assertNotIn("PRIVATE_ARMORY_PASSWORD_SENTINEL", content)
        self.assertNotIn("PRIVATE_ARMORY_INTERNAL_SENTINEL", content)


class ArmoryProfileTests(TestCase):
    """Single-character profile rendering."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        user = User.objects.create_user(
            username="armoryprofile", password="testpass123")
        self.client.login(username="armoryprofile", password="testpass123")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_valid_character_profile_renders(self, mock_resolve):
        char = _make_mock_char(
            "Thorin", race_id="dwarf", prof_id="warrior",
            level=10, xp=5000, hp=250, max_hp=250,
            mana=50, max_mana=50, stamina=180, max_stamina=200,
            guild_id="The Iron Brotherhood")
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "Thorin"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thorin")
        self.assertContains(response, "Level 10")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_unknown_character_returns_404(self, mock_resolve):
        mock_resolve.side_effect = Http404("Character not found.")
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "Nobody"}))
        self.assertEqual(response.status_code, 404)

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_deleted_character_returns_404(self, mock_resolve):
        mock_resolve.side_effect = Http404("Character not found.")
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "DeletedOne"}))
        self.assertEqual(response.status_code, 404)

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_profile_uses_authoritative_values(self, mock_resolve):
        char = _make_mock_char(
            "AuthChar", race_id="human", prof_id="mage",
            level=5, xp=1200, hp=200, max_hp=200,
            mana=150, max_mana=150, stamina=80, max_stamina=100,
            base_stats={"str": 25, "int": 30, "wis": 20, "dex": 22, "con": 24},
        )
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "AuthChar"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "200 / 200")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_profile_no_private_data(self, mock_resolve):
        """Armory profile construction must never expose private data."""
        char = _make_mock_char("SafeChar", race_id="human")
        # Inject unmistakable private sentinel values
        char.email = "private-armory-email@example.invalid"
        char._password_hash = "PRIVATE_ARMORY_PASSWORD_SENTINEL"
        char._internal = "PRIVATE_ARMORY_INTERNAL_SENTINEL"
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "SafeChar"}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Confirm the character IS visible (proves the page rendered correctly)
        self.assertContains(response, "SafeChar")
        # Verify none of the private sentinel values leak into the output
        self.assertNotIn("private-armory-email@example.invalid", content)
        self.assertNotIn("PRIVATE_ARMORY_PASSWORD_SENTINEL", content)
        self.assertNotIn("PRIVATE_ARMORY_INTERNAL_SENTINEL", content)

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_race_portrait_uses_filename_convention(self, mock_resolve):
        char = _make_mock_char("PortraitChar", race_id="dwarf")
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "PortraitChar"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "race-dwarf.png")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_missing_race_has_fallback(self, mock_resolve):
        char = _make_mock_char("NoRaceChar", race_id=None)
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "NoRaceChar"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "armory-character-fallback.png")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_guild_sect_empty_safe(self, mock_resolve):
        char = _make_mock_char("NoGuild", race_id="human", guild_id=None, sect_id=None)
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "NoGuild"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "—")

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_equipment_display_is_readonly(self, mock_resolve):
        char = _make_mock_char(
            "EqChar", race_id="human", prof_id="warrior",
            level=3, hp=80, max_hp=100,
        )
        mock_resolve.return_value = char
        response = self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "EqChar"}))
        self.assertEqual(response.status_code, 200)
        char.save.assert_not_called()

    @patch("web.website.views.armory._resolve_character_by_name")
    def test_armory_get_does_not_mutate(self, mock_resolve):
        char = _make_mock_char("Immutable", race_id="human", prof_id="mage")
        mock_resolve.return_value = char
        self.client.get(
            reverse("rop-armory-character", kwargs={"character_name": "Immutable"}))
        char.save.assert_not_called()
