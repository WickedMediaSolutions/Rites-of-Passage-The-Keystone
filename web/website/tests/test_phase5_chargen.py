"""
Phase 5 chargen tests — login required, one-character enforcement,
name validation, authoritative race/faction, stat-roll delegation,
reroll limit, client-stats-not-authoritative, final creation.
"""

from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage

User = get_user_model()


def _session_request(method="get", path="/chargen/"):
    rf = RequestFactory()
    if method == "post":
        req = rf.post(path)
    else:
        req = rf.get(path)
    sm = SessionMiddleware(lambda r: None)
    sm.process_request(req)
    mm = MessageMiddleware(lambda r: None)
    mm.process_request(req)
    req.session.save()
    req._messages = FallbackStorage(req)
    return req


class ChargenAuthRequired(TestCase):
    def test_unauthenticated_redirects_to_login(self):
        from web.website.views.chargen import CharGenView
        req = _session_request()
        req.user = AnonymousUser()
        resp = CharGenView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url.lower())


class ChargenExistingCharacterBlocked(TestCase):
    @patch("web.website.views.chargen.account_has_character", return_value=True)
    def test_existing_character_redirects_to_dashboard(self, _mock):
        from web.website.views.chargen import CharGenView
        user = User.objects.create_user(username="testchar", password="pw")
        req = _session_request()
        req.user = user
        resp = CharGenView.as_view()(req)
class ChargenNameValidation(TestCase):
    """Name-step validation uses authoritative naming module."""

    def setUp(self):
        self.user = User.objects.create_user(username="cnamer", password="pw")

    def _req(self):
        req = _session_request()
        req.user = self.user
        return req

    def test_name_too_short_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"name": "ab"}
        CharGenView.as_view()(req)
        self.assertNotEqual(req.session.get("chargen_step"), "faction")

    def test_name_with_numbers_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"name": "test123"}
        CharGenView.as_view()(req)
        self.assertNotEqual(req.session.get("chargen_step"), "faction")

    def test_valid_name_advances_to_faction(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"name": "TestName"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_step"], "faction")


class ChargenFactionSelection(TestCase):
    """Faction selection step — must choose good or evil."""

    def setUp(self):
        self.user = User.objects.create_user(username="cfactioner", password="pw")

    def _req(self):
        req = _session_request()
        req.user = self.user
        req.session["chargen_step"] = "faction"
        req.session["chargen_name"] = "TestFaction"
        return req

    def test_faction_get_renders(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "GET"
        resp = CharGenView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Valroian", content)
        self.assertIn("Mordrath", content)

    def test_faction_missing_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {}
        CharGenView.as_view()(req)
        self.assertEqual(req.session.get("chargen_step"), "faction")

    def test_faction_invalid_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"faction": "neutral"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session.get("chargen_step"), "faction")

    def test_faction_valroian_accepted(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"faction": "good"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_step"], "race")
        self.assertEqual(req.session["chargen_faction"], "good")

    def test_faction_mordrath_accepted(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"faction": "evil"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_step"], "race")
        self.assertEqual(req.session["chargen_faction"], "evil")

class ChargenNewChargenNoDefaultFaction(TestCase):
    """TEST 1 — Brand-new chargen MUST have no default faction."""

    def setUp(self):
        self.user = User.objects.create_user(username="cnewfaction", password="pw")

    def _fresh_req(self):
        """A request that mimics a brand-new chargen (no prior session keys)."""
        req = _session_request()
        req.user = self.user
        # Explicitly do NOT set chargen_step, chargen_faction, etc.
        return req

    def test_fresh_session_has_no_faction(self):
        """On a brand-new chargen, faction should be absent from session."""
        from web.website.views.chargen import CharGenView
        req = self._fresh_req()
        req.method = "GET"
        CharGenView.as_view()(req)
        # After dispatch, step defaults to "name"; no faction should be set
        self.assertNotIn("chargen_faction", req.session)
        self.assertEqual(req.session.get("chargen_step"), "name")

    def test_faction_page_has_no_preselection(self):
        """The faction GET page must NOT have either radio checked by default."""
        from web.website.views.chargen import CharGenView
        req = self._fresh_req()
        req.session["chargen_step"] = "faction"
        req.session["chargen_name"] = "TestNoDefault"
        req.method = "GET"
        resp = CharGenView.as_view()(req)
        content = resp.content.decode()
        # Neither radio input should have a checked="checked" HTML attribute.
        # (The JS source contains "input[name=\"faction\"]:checked" — that is a
        # CSS selector, not an HTML attribute, so we check for the attribute form.)
        self.assertNotIn('checked="checked"', content)
        self.assertNotIn("checked='checked'", content)
        self.assertNotIn(" checked>", content)
        # Both faction names must be present
        self.assertIn("Valroian", content)
        self.assertIn("Mordrath", content)

    def test_race_step_cannot_be_entered_without_faction(self):
        """Direct access to the race step without faction must redirect."""
        from web.website.views.chargen import CharGenView
class ChargenStaleSessionNoCarryover(TestCase):
    """TEST 5 — Stale faction from a previous chargen MUST NOT carry into a new one."""

    def setUp(self):
        self.user = User.objects.create_user(username="cstale", password="pw")

    def test_mordrath_does_not_carry_into_new_chargen(self):
        """Select Mordrath in one session, then simulate a fresh chargen."""
        from web.website.views.chargen import CharGenView

        # Step 1: Simulate completing faction selection as Mordrath
        req1 = _session_request(method="post")
        req1.user = self.user
        req1.session["chargen_step"] = "faction"
        req1.session["chargen_name"] = "StaleChar"
        req1.POST = {"faction": "evil"}
        CharGenView.as_view()(req1)
        self.assertEqual(req1.session["chargen_faction"], "evil")
        self.assertEqual(req1.session["chargen_step"], "race")

        # Step 2: Simulate a completely new chargen using a fresh request
        # with an invalid step to trigger the full session clear
        req2 = _session_request()
        req2.user = self.user
        req2.session["chargen_step"] = "garbage_step"  # invalid → triggers clear
        req2.method = "GET"
        CharGenView.as_view()(req2)
        # After dispatch, step resets to "name" and stale data is cleared
        self.assertEqual(req2.session.get("chargen_step"), "name")
        self.assertNotIn("chargen_faction", req2.session)
        self.assertNotIn("chargen_name", req2.session)

    def test_valroian_does_not_carry_into_new_chargen(self):
        """Select Valroian in one session, then simulate a fresh chargen."""
        from web.website.views.chargen import CharGenView

        # Step 1: Simulate completing faction selection as Valroian
        req1 = _session_request(method="post")
        req1.user = self.user
        req1.session["chargen_step"] = "faction"
        req1.session["chargen_name"] = "StaleGood"
        req1.POST = {"faction": "good"}
        CharGenView.as_view()(req1)
        self.assertEqual(req1.session["chargen_faction"], "good")

        # Step 2: Fresh chargen with invalid step
        req2 = _session_request()
        req2.user = self.user
        req2.session["chargen_step"] = "badstep"  # invalid
        req2.method = "GET"
        CharGenView.as_view()(req2)
class ChargenDirectRaceWithoutFaction(TestCase):
    """TEST 6 — Manually visiting the race URL without choosing faction redirects."""

    def setUp(self):
        self.user = User.objects.create_user(username="cdirectrace", password="pw")

    def test_get_race_step_without_faction_redirects(self):
        """GET request to race step without faction must redirect to faction step."""
        from web.website.views.chargen import CharGenView
        req = _session_request()
        req.user = self.user
        req.session["chargen_step"] = "race"
        req.session["chargen_name"] = "TestName"
        # NO chargen_faction set
        req.method = "GET"
        resp = CharGenView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/chargen/", resp.url)
        # Session step should now be "faction"
        self.assertEqual(req.session.get("chargen_step"), "faction")

    def test_post_race_step_without_faction_rejected(self):
        """POST request to race step without faction must be rejected."""
        from web.website.views.chargen import CharGenView
        req = _session_request(method="post")
        req.user = self.user
        req.session["chargen_step"] = "race"
        req.session["chargen_name"] = "TestName"
        req.POST = {"race": "human"}
        # NO chargen_faction set
        CharGenView.as_view()(req)
        # Should still be redirected to faction
        self.assertEqual(req.session.get("chargen_step"), "faction")
        self.assertNotIn("chargen_race", req.session)

    def test_no_default_faction_created_on_redirect(self):
        """When redirected from race to faction, no default faction is created."""
        from web.website.views.chargen import CharGenView
        req = _session_request()
        req.user = self.user
        req.session["chargen_step"] = "race"
        req.session["chargen_name"] = "TestName"
        req.method = "GET"
        CharGenView.as_view()(req)
        # Faction must NOT have been created silently
        self.assertNotIn("chargen_faction", req.session)

class ChargenRaceFactionAuthoritative(TestCase):
    """Race selection stores faction from authoritative RACES data."""

    def setUp(self):
        self.user = User.objects.create_user(username="cracer", password="pw")

    def _req(self):
        req = _session_request()
        req.user = self.user
        req.session["chargen_step"] = "race"
        req.session["chargen_name"] = "TestRacer"
        req.session["chargen_faction"] = "good"
        return req

    def test_race_human_gives_good_faction(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"race": "human"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_race"], "human")
        self.assertEqual(req.session["chargen_faction"], "good")

    def test_race_orc_gives_evil_faction(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.session["chargen_faction"] = "evil"
        req.method = "POST"
        req.POST = {"race": "orc"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_race"], "orc")
        self.assertEqual(req.session["chargen_faction"], "evil")

    def test_invalid_race_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"race": "not_a_race"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session.get("chargen_step"), "race")
class ChargenProfessionSelection(TestCase):
    """Profession selection advances to stats step with generated stats."""

    def setUp(self):
        self.user = User.objects.create_user(username="cprofer", password="pw")

    def _req(self):
        req = _session_request()
        req.user = self.user
        req.session["chargen_step"] = "profession"
        req.session["chargen_name"] = "TestProfer"
        req.session["chargen_race"] = "human"
        req.session["chargen_faction"] = "good"
        return req

    def test_valid_profession_advances_and_generates_stats(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"profession": "warrior"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_profession"], "warrior")
        self.assertEqual(req.session["chargen_step"], "stats")
        stats = req.session.get("chargen_stats", {})
        for k in ("str", "int", "wis", "dex", "con"):
            self.assertIn(k, stats)
            self.assertIsInstance(stats[k], int)

    def test_invalid_profession_rejected(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.method = "POST"
        req.POST = {"profession": "not_real"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session.get("chargen_step"), "profession")
class ChargenStatRollUsesAuthoritative(TestCase):
    """_generate_stats delegates to CharacterData._roll_stats."""

    def setUp(self):
        self.user = User.objects.create_user(username="cstater", password="pw")

    def _req(self):
        req = _session_request()
        req.user = self.user
        req.session["chargen_race"] = "human"
        return req

    @patch("world.data.character_data.CharacterData._roll_stats")
    def test_generate_stats_calls_roll_stats(self, mock_roll):
        from web.website.views.chargen import CharGenView
        req = self._req()
        CharGenView()._generate_stats(req)
        mock_roll.assert_called_once()
        self.assertIn("chargen_stats", req.session)

    def test_reroll_produces_variance(self):
        from web.website.views.chargen import CharGenView
        v = CharGenView()
        req = self._req()
        v._generate_stats(req)
        first = dict(req.session["chargen_stats"])
        any_diff = False
        for _ in range(15):
            v._generate_stats(req)
            if dict(req.session["chargen_stats"]) != first:
                any_diff = True
                break
        self.assertTrue(any_diff, "15 stat rolls all identical — near-impossible")


class ChargenMaxThreeRerolls(TestCase):
    """Reroll capped at 3 (authoritative MAX_STAT_REROLLS)."""

    def setUp(self):
        self.user = User.objects.create_user(username="creroll", password="pw")

    def _req(self):
        req = _session_request(method="post")
        req.user = self.user
        req.session["chargen_step"] = "stats"
        req.session["chargen_name"] = "TestReroll"
        req.session["chargen_race"] = "human"
        req.session["chargen_faction"] = "good"
        req.session["chargen_profession"] = "warrior"
        req.session["chargen_stats"] = {"str": 25, "int": 25, "wis": 25, "dex": 25, "con": 25}
        return req

    def test_three_rerolls_accepted(self):
        from web.website.views.chargen import CharGenView
        for i in range(3):
            req = self._req()
            req.session["chargen_rolls"] = i
            req.POST = {"action": "reroll"}
            CharGenView.as_view()(req)
            self.assertEqual(req.session["chargen_rolls"], i + 1)

    def test_fourth_reroll_blocked(self):
        from web.website.views.chargen import CharGenView
        req = self._req()
        req.session["chargen_rolls"] = 3
        req.POST = {"action": "reroll"}
        CharGenView.as_view()(req)
        self.assertEqual(req.session["chargen_rolls"], 3)
class ChargenClientStatsNotAuthoritative(TestCase):
    """Client-supplied stat values are ignored; only server-generated stats used."""

    def test_accept_action_does_not_read_posted_stat_values(self):
        from web.website.views.chargen import CharGenView
        user = User.objects.create_user(username="cnoclient", password="pw")
        req = _session_request(method="post")
        req.user = user
        req.session["chargen_step"] = "stats"
        req.session["chargen_name"] = "TestNoClient"
        req.session["chargen_race"] = "human"
        req.session["chargen_faction"] = "good"
        req.session["chargen_profession"] = "warrior"
        req.session["chargen_stats"] = {"str": 99, "int": 99, "wis": 99, "dex": 99, "con": 99}
        req.session["chargen_rolls"] = 0
        # Client attempts to inject bogus stats
        req.POST = {"action": "accept", "str": "999", "int": "999",
                     "wis": "999", "dex": "999", "con": "999"}
        CharGenView.as_view()(req)
        stats = req.session.get("chargen_stats", {})
        self.assertEqual(stats.get("str"), 99)
        self.assertNotEqual(stats.get("str"), 999)


class ChargenFinalCreationAuthoritative(TestCase):
    """Final creation uses account.create_character + init_character."""

    def setUp(self):
        self.user = User.objects.create_user(username="cfinal", password="pw")

    def _req(self):
        req = _session_request(method="post")
        req.user = self.user
        req.session["chargen_step"] = "review"
        req.session["chargen_name"] = "FinalChar"
        req.session["chargen_race"] = "human"
        req.session["chargen_faction"] = "good"
        req.session["chargen_profession"] = "warrior"
        req.session["chargen_stats"] = {"str": 25, "int": 25, "wis": 25, "dex": 25, "con": 25}
        req.session["chargen_rolls"] = 0
        return req

    @patch("web.website.views.chargen.account_has_character", return_value=False)
    @patch("evennia.accounts.models.AccountDB")
    def test_creation_calls_account_create_character_then_init(
        self, mock_db, _mock_has_char
    ):
        from web.website.views.chargen import CharGenView
        mock_acct = Mock()
        mock_char = Mock()
        mock_char.save = Mock()
        mock_char.init_character = Mock()
        mock_acct.create_character.return_value = (mock_char, None)
        mock_db.objects.get.return_value = mock_acct
        req = self._req()
        resp = CharGenView.as_view()(req)
        mock_acct.create_character.assert_called_once_with(key="FinalChar")
        mock_char.init_character.assert_called_once_with("human", "warrior")
        self.assertEqual(resp.status_code, 302)


class ChargenOneCharacterAfterCreation(TestCase):
    """Once a character exists, chargen is blocked."""

    def setUp(self):
        self.user = User.objects.create_user(username="cone", password="pw")

    @patch("web.website.views.chargen.account_has_character", return_value=True)
    def test_blocked_after_creation(self, _mock):
        from web.website.views.chargen import CharGenView
        req = _session_request()
        req.user = self.user
        resp = CharGenView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/", resp.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/", resp.url)


class ChargenDateCreatedRegression(TestCase):
    """Verify db_date_created is never None after at_object_creation,
    preventing the 'NoneType' object has no attribute 'strftime' crash
    in Evennia's _TO_DATESTRING serialization."""

    def test_at_object_creation_populates_db_date_created_when_none(self):
        """If db_date_created is None, at_object_creation sets it to a datetime."""
        import datetime as _dt
        from unittest.mock import Mock, patch
        from typeclasses.characters import Character

        char = Character.__new__(Character)

        # Force db_date_created to None to reproduce the bug scenario
        object.__setattr__(char, "db_date_created", None)

        with patch.object(Character, "_init_game_data"):
            with patch.object(Character, "attributes") as mock_attrs:
                mock_attrs.has.return_value = True
                Character.at_object_creation(char)

        # Verify db_date_created was set to a real datetime
        created = object.__getattribute__(char, "db_date_created")
        self.assertIsNotNone(created)
        self.assertIsInstance(created, _dt.datetime)

    def test_at_object_creation_preserves_existing_db_date_created(self):
        """If db_date_created is already set, at_object_creation leaves it alone."""
        from unittest.mock import Mock, patch
        from django.utils import timezone as _tz
        from typeclasses.characters import Character

        char = Character.__new__(Character)
        original = _tz.now()
        object.__setattr__(char, "db_date_created", original)

        with patch.object(Character, "_init_game_data"):
            with patch.object(Character, "attributes") as mock_attrs:
                mock_attrs.has.return_value = True
                Character.at_object_creation(char)

        created = object.__getattribute__(char, "db_date_created")
        self.assertIs(created, original)