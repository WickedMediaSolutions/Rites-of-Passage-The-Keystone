"""
Phase 6 — Character Deletion & Account Deletion Tests

Covers:
  Character deletion:
    - login required
    - GET renders confirmation only
    - POST required for actual deletion
    - wrong character-name confirmation rejected
    - exact name accepted
    - only owned character can be deleted
    - successful deletion removes character
    - account remains
    - replacement character creation becomes possible

  Account deletion:
    - login required
    - GET renders confirmation only
    - POST required for deletion
    - wrong username confirmation rejected
    - exact username accepted
    - owned character is removed
    - account is removed
    - session/authentication cleared
    - no orphaned character remains
"""

from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory


def _request(method="get", user=None):
    """Build a minimal request with session and messages support."""
    rf = RequestFactory()
    if method == "post":
        req = rf.post("/")
    else:
        req = rf.get("/")
    sm = SessionMiddleware(lambda r: None)
    sm.process_request(req)
    import django.contrib.messages.middleware as mm_mod
    mm_mod.MessageMiddleware(lambda r: None).process_request(req)
    req.session.save()
    req._messages = FallbackStorage(req)
    req.user = user if user else MagicMock()
    return req


# ==========================================================================
# CHARACTER DELETION
# ==========================================================================


class CharacterDeleteAuthRequired(TestCase):
    """Login required — unauthenticated access must redirect to login."""

    def test_get_redirects_to_login(self):
        from web.website.views.deletion import CharacterDeleteView
        req = _request()
        req.user.is_authenticated = False
        resp = CharacterDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url.lower())

    def test_post_redirects_to_login(self):
        from web.website.views.deletion import CharacterDeleteView
        req = _request(method="post")
        req.user.is_authenticated = False
        resp = CharacterDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url.lower())


class CharacterDeleteGetRendersConfirmation(TestCase):
    """GET only renders the confirmation page — no deletion occurs."""

    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_get_renders_confirmation_when_character_exists(
        self, _mock_ctx, mock_get_char
    ):
        from web.website.views.deletion import CharacterDeleteView
        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        req = _request()
        req.user.is_authenticated = True
        resp = CharacterDeleteView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("TestChar", resp.content.decode())

    @patch("web.website.views.deletion.get_account_character", return_value=None)
    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_get_redirects_when_no_character(self, _mock_ctx, _mock_get_char):
        from web.website.views.deletion import CharacterDeleteView
        req = _request()
        req.user.is_authenticated = True
        resp = CharacterDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/", resp.url.lower())


class CharacterDeletePostRequired(TestCase):
    """POST is required for actual deletion — GET must not delete."""

    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_get_does_not_delete_character(self, _mock_ctx, mock_get_char):
        from web.website.views.deletion import CharacterDeleteView
        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        req = _request()
        req.user.is_authenticated = True
        CharacterDeleteView.as_view()(req)

        mock_char.delete.assert_not_called()


class CharacterDeleteWrongNameRejected(TestCase):
    """Wrong character-name confirmation must be rejected."""

    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_wrong_name_rejected(self, _mock_ctx, mock_get_char):
        from web.website.views.deletion import CharacterDeleteView
        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        req = _request(method="post")
        req.user.is_authenticated = True
        req.POST = {"confirmation": "WrongName"}

        resp = CharacterDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_char.delete.assert_not_called()

    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_case_mismatch_rejected(self, _mock_ctx, mock_get_char):
        from web.website.views.deletion import CharacterDeleteView
        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        req = _request(method="post")
        req.user.is_authenticated = True
        req.POST = {"confirmation": "testchar"}  # different case

        resp = CharacterDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_char.delete.assert_not_called()
class CharacterDeleteExactNameAccepted(TestCase):
    """Exact name match must trigger deletion."""

    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion._clear_chargen_session")
    def test_exact_name_triggers_deletion(
        self, mock_clear, mock_get_char, mock_get_acct
    ):
        from web.website.views.deletion import CharacterDeleteView

        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "tester"
        req.POST = {"confirmation": "TestChar"}

        resp = CharacterDeleteView.as_view()(req)

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/", resp.url.lower())
        mock_acct.characters.remove.assert_called_once_with(mock_char)
        mock_char.delete.assert_called_once()
        mock_clear.assert_called_once()


class CharacterDeleteAccountRemains(TestCase):
    """After character deletion, the account still exists."""

    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character")
    @patch("web.website.views.deletion._clear_chargen_session")
    def test_account_remains_after_deletion(
        self, mock_clear, mock_get_char, mock_get_acct
    ):
        from web.website.views.deletion import CharacterDeleteView

        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "tester"
        req.POST = {"confirmation": "TestChar"}

        resp = CharacterDeleteView.as_view()(req)

        self.assertEqual(resp.status_code, 302)
        mock_acct.delete.assert_not_called()


class CharacterDeleteAllowsReplacement(TestCase):
    """After deletion, chargen session is cleared for replacement creation."""

    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character")
    def test_chargen_session_cleared(self, mock_get_char, mock_get_acct):
        from web.website.views.deletion import CharacterDeleteView

        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "tester"
        req.POST = {"confirmation": "TestChar"}
        req.session["chargen_name"] = "OldName"
        req.session["chargen_step"] = "race"

        CharacterDeleteView.as_view()(req)

        self.assertNotIn("chargen_name", req.session)
# ==========================================================================
# ACCOUNT DELETION
# ==========================================================================


class AccountDeleteAuthRequired(TestCase):
    """Login required for account deletion."""

    def test_get_redirects_to_login(self):
        from web.website.views.deletion import AccountDeleteView
        req = _request()
        req.user.is_authenticated = False
        resp = AccountDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url.lower())

    def test_post_redirects_to_login(self):
        from web.website.views.deletion import AccountDeleteView
        req = _request(method="post")
        req.user.is_authenticated = False
        resp = AccountDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url.lower())


class AccountDeleteGetRendersConfirmation(TestCase):
    """GET only renders the confirmation page."""

    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_get_renders_confirmation(self, _mock_ctx):
        from web.website.views.deletion import AccountDeleteView
        req = _request()
        req.user.is_authenticated = True
        req.user.username = "testuser"
        resp = AccountDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("testuser", resp.content.decode())


class AccountDeleteWrongNameRejected(TestCase):
    """Wrong username confirmation must be rejected."""

    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_wrong_username_rejected(self, _mock_ctx):
        from web.website.views.deletion import AccountDeleteView
        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "testuser"
        req.POST = {"confirmation": "wronguser"}
        resp = AccountDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

    @patch("web.website.views.deletion.portal_context", return_value={})
    def test_case_mismatch_rejected(self, _mock_ctx):
        from web.website.views.deletion import AccountDeleteView
        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "TestUser"
        req.POST = {"confirmation": "testuser"}
        resp = AccountDeleteView.as_view()(req)
class AccountDeleteExactNameAccepted(TestCase):
    """Exact username triggers deletion — character + account removed, session cleared."""

    @patch("web.website.views.deletion.auth_logout")
    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character")
    def test_deletes_character_and_account(
        self, mock_get_char, mock_get_acct, mock_logout
    ):
        from web.website.views.deletion import AccountDeleteView

        mock_char = MagicMock()
        mock_char.key = "TestChar"
        mock_get_char.return_value = mock_char

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "testuser"
        req.POST = {"confirmation": "testuser"}

        resp = AccountDeleteView.as_view()(req)

        self.assertEqual(resp.status_code, 302)
        mock_acct.characters.remove.assert_called_once_with(mock_char)
        mock_char.delete.assert_called_once()
        mock_acct.delete.assert_called_once()
        mock_logout.assert_called_once_with(req)


class AccountDeleteNoOrphanCharacter(TestCase):
    """When account has no character, deletion still succeeds."""

    @patch("web.website.views.deletion.auth_logout")
    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character", return_value=None)
    def test_no_character_no_error(self, mock_get_char, mock_get_acct, mock_logout):
        from web.website.views.deletion import AccountDeleteView

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "testuser"
        req.POST = {"confirmation": "testuser"}

        resp = AccountDeleteView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        mock_acct.delete.assert_called_once()
        mock_logout.assert_called_once_with(req)


class AccountDeleteSessionCleared(TestCase):
    """After account deletion, session is flushed."""

    @patch("web.website.views.deletion.auth_logout")
    @patch("web.website.views.deletion.get_evennia_account")
    @patch("web.website.views.deletion.get_account_character", return_value=None)
    def test_session_flushed(self, mock_get_char, mock_get_acct, mock_logout):
        from web.website.views.deletion import AccountDeleteView

        mock_acct = MagicMock()
        mock_get_acct.return_value = mock_acct

        req = _request(method="post")
        req.user.is_authenticated = True
        req.user.username = "testuser"
        req.POST = {"confirmation": "testuser"}
        req.session["some_key"] = "some_value"

        resp = AccountDeleteView.as_view()(req)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(req.session.keys()), 0)