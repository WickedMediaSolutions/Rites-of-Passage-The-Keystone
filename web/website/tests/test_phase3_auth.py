"""
Phase 3 - Registration, Authentication, Account Settings,
          Password Reset & Centralized Name Validation Tests
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from web.website.naming import (
    MIN_LENGTH,
    MAX_LENGTH,
    is_name_reserved,
    validate_name_format,
)


# -- NAMING VALIDATOR TESTS --


class TestNameFormatValidation(TestCase):
    """Centralized naming validator unit tests."""

    def test_empty_name_rejected(self):
        errors = validate_name_format("")
        self.assertTrue(errors)

    def test_too_short_rejected(self):
        errors = validate_name_format("Jo")
        self.assertTrue(any("at least" in e for e in errors))

    def test_min_length_accepted(self):
        errors = validate_name_format("Joe")
        self.assertEqual(errors, [])

    def test_too_long_rejected(self):
        errors = validate_name_format("A" * (MAX_LENGTH + 1))
        self.assertTrue(any("at most" in e for e in errors))

    def test_max_length_accepted(self):
        errors = validate_name_format("A" * MAX_LENGTH)
        self.assertEqual(errors, [])

    def test_numbers_rejected(self):
        errors = validate_name_format("Josh123")
        self.assertTrue(errors)

    def test_spaces_rejected(self):
        errors = validate_name_format("Dirty South")
        self.assertTrue(errors)

    def test_underscores_rejected(self):
        errors = validate_name_format("Dirty_South")
        self.assertTrue(errors)

    def test_punctuation_rejected(self):
        errors = validate_name_format("Josh!")
        self.assertTrue(errors)

    def test_hyphen_accepted(self):
        errors = validate_name_format("Dirty-South")
        self.assertEqual(errors, [])

    def test_consecutive_hyphens_rejected(self):
        errors = validate_name_format("Dark--Knight")
        self.assertTrue(errors)

    def test_leading_hyphen_rejected(self):
        errors = validate_name_format("-DarkKnight")
        self.assertTrue(errors)

    def test_trailing_hyphen_rejected(self):
        errors = validate_name_format("DarkKnight-")
        self.assertTrue(errors)

    def test_mixed_case_accepted(self):
        errors = validate_name_format("DarkKnight")
        self.assertEqual(errors, [])


class TestReservedNames(TestCase):
    """Odin and configured reserved names must be blocked."""

    def test_odin_is_reserved(self):
        reserved, reason = is_name_reserved("Odin")
        self.assertTrue(reserved)

    def test_odin_lowercase_reserved(self):
        reserved, reason = is_name_reserved("odin")
        self.assertTrue(reserved)

    def test_odin_uppercase_reserved(self):
        reserved, reason = is_name_reserved("ODIN")
        self.assertTrue(reserved)

    def test_normal_name_not_reserved(self):
        reserved, reason = is_name_reserved("DarkKnight")
        self.assertFalse(reserved)


# -- REGISTRATION TESTS --


class TestRegistrationPage(TestCase):
    """Registration page must render and function correctly."""

    def setUp(self):
        self.client = Client()

    def test_register_page_returns_200(self):
        response = self.client.get(reverse("rop-register"))
        self.assertEqual(response.status_code, 200)

    def test_register_page_has_csrf(self):
        response = self.client.get(reverse("rop-register"))
        self.assertContains(response, "csrfmiddlewaretoken")

    @patch("evennia.utils.create.create_account")
    def test_valid_registration_creates_account(self, mock_create):
        """Valid registration creates one proper Evennia account."""
        User = get_user_model()
        def _create_account(username, email, password, **kw):
            return User.objects.create_user(
                username=username, email=email, password=password)
        mock_create.side_effect = _create_account
        initial_count = User.objects.count()
        response = self.client.post(
            reverse("rop-register"),
            {"username": "DarkKnight", "email": "dark@example.com",
             "password1": "testpass123", "password2": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)
        new_count = User.objects.count()
        self.assertEqual(new_count, initial_count + 1)
        user = User.objects.get(username="DarkKnight")
        self.assertTrue(user.check_password("testpass123"))
        self.assertEqual(user.email, "dark@example.com")

    @patch("evennia.utils.create.create_account")
    def test_registration_does_not_create_character(self, mock_create):
        from evennia.objects.models import ObjectDB
        User = get_user_model()
        def _create_account(username, email, password, **kw):
            return User.objects.create_user(
                username=username, email=email, password=password)
        mock_create.side_effect = _create_account
        initial_chars = ObjectDB.objects.filter(
            db_typeclass_path__icontains="character"
        ).count()
        self.client.post(
            reverse("rop-register"),
            {"username": "NoCharTest", "email": "nochar@example.com",
             "password1": "testpass123", "password2": "testpass123"},
        )
        final_chars = ObjectDB.objects.filter(
            db_typeclass_path__icontains="character"
        ).count()
        self.assertEqual(final_chars, initial_chars)

    def test_username_too_short_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Jo", "email": "jo@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_username_too_long_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "A" * (MAX_LENGTH + 1), "email": "long@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_username_with_numbers_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Josh123", "email": "josh@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_username_with_spaces_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Dirty South", "email": "ds@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_username_with_underscores_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Dirty_South", "email": "ds@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_username_with_punctuation_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Josh!", "email": "josh@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    @patch("evennia.utils.create.create_account")
    def test_username_with_hyphen_accepted(self, mock_create):
        User = get_user_model()
        def _create_account(username, email, password, **kw):
def test_register_form_has_csrf_input(self):
        """Registration form must contain the csrfmiddlewaretoken hidden input."""
        response = self.client.get(reverse("rop-register"))
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'method="post"')
        # Verify token is INSIDE a form tag
        content = response.content.decode("utf-8")
        csrf_pos = content.find("csrfmiddlewaretoken")
        form_start = content.rfind("<form", 0, csrf_pos)
        form_end = content.find("</form>", csrf_pos)
        self.assertGreater(form_start, -1, "csrfmiddlewaretoken must be inside a <form>")
        self.assertGreater(form_end, -1, "csrfmiddlewaretoken must be inside a </form>")

    def test_register_page_has_no_fallback_art(self):
        """Registration page must not use fallback artwork in marketing positions."""
        response = self.client.get(reverse("rop-register"))
        content = response.content.decode("utf-8")
        self.assertNotIn("rop-card-fallback", content)
            return User.objects.create_user(
                username=username, email=email, password=password)
        mock_create.side_effect = _create_account
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Dirty-South", "email": "ds@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 302)
        User = get_user_model()
        self.assertTrue(User.objects.filter(username="Dirty-South").exists())

    def test_odin_rejected_case_insensitive(self):
        for name in ["Odin", "odin", "ODIN"]:
            response = self.client.post(
                reverse("rop-register"),
                {"username": name, "email": f"{name}@x.com",
                 "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "ValidName", "email": "v@x.com",
             "password1": "StR0ng!Pass99", "password2": "different"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)


class TestCaseInsensitiveUniqueness(TestCase):
    """Username uniqueness must be case-insensitive at server side."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        User.objects.create_user(
            username="Josh", password="testpass123", email="josh@x.com"
        )

    def test_exact_case_duplicate_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "Josh", "email": "josh2@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertTrue(response.context["form"].errors)

    def test_lowercase_duplicate_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "josh", "email": "josh3@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertTrue(response.context["form"].errors)

    def test_uppercase_duplicate_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "JOSH", "email": "josh4@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertTrue(response.context["form"].errors)

    def test_mixed_case_duplicate_rejected(self):
        response = self.client.post(
            reverse("rop-register"),
            {"username": "JoSh", "email": "josh5@x.com",
             "password1": "StR0ng!Pass99", "password2": "StR0ng!Pass99"},
        )
        self.assertTrue(response.context["form"].errors)


# -- LOGIN / LOGOUT TESTS --


class TestLogin(TestCase):
    """Login must work with valid credentials and fail safely."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="TestLogin", password="testpass123",
            email="testlogin@x.com")

    def test_login_page_returns_200(self):
        response = self.client.get(reverse("rop-login"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_has_csrf(self):
        response = self.client.get(reverse("rop-login"))
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_login_succeeds_with_valid_credentials(self):
        response = self.client.post(
            reverse("rop-login"),
            {"username": "TestLogin", "password": "testpass123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_fails_with_wrong_password(self):
        response = self.client.post(
            reverse("rop-login"),
            {"username": "TestLogin", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_fails_with_nonexistent_user(self):
        response = self.client.post(
            reverse("rop-login"),
            {"username": "NobodyHere", "password": "StR0ng!Pass99"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("rop-login"),
            {"username": "TestLogin", "password": "testpass123"},
        )
        self.assertRedirects(response, reverse("rop-dashboard"))


class TestLogout(TestCase):
    """Logout must clear session and redirect appropriately."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="TestLogout", password="testpass123",
            email="logout@x.com")

    def test_logout_works(self):
        self.client.login(username="TestLogout", password="testpass123")
        response = self.client.post(reverse("rop-logout"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_redirects_to_home(self):
        self.client.login(username="TestLogout", password="testpass123")
        response = self.client.post(reverse("rop-logout"))
        self.assertRedirects(response, reverse("home"))


class TestAuthenticatedNavigation(TestCase):
    """Menu must reflect authenticated state correctly."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="NavUser", password="testpass123", email="nav@x.com")

    def test_unauthenticated_sees_login_register(self):
        response = self.client.get(reverse("rop-register"))
        content = response.content.decode("utf-8")
        self.assertIn('">Log In</a>', content)

    def test_authenticated_sees_dashboard_logout(self):
        self.client.login(username="NavUser", password="testpass123")
        response = self.client.get(reverse("rop-register"))
        content = response.content.decode("utf-8")
        self.assertIn('">Dashboard</a>', content)
        self.assertIn('">Account Settings</a>', content)
        self.assertIn('">Log Out</button>', content)
        self.assertNotIn('">Log In</a>', content)


# -- ACCOUNT SETTINGS TESTS --


class TestAccountSettingsAccess(TestCase):
    """Account settings must be protected from anonymous access."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="SettingsUser", password="testpass123",
            email="settings@x.com")

    def test_anonymous_cannot_access_settings(self):
        response = self.client.get(reverse("rop-account-settings"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_can_access_settings(self):
        self.client.login(username="SettingsUser", password="testpass123")
        response = self.client.get(reverse("rop-account-settings"))
        self.assertEqual(response.status_code, 200)

    def test_settings_page_displays_username(self):
        self.client.login(username="SettingsUser", password="testpass123")
        response = self.client.get(reverse("rop-account-settings"))
        self.assertContains(response, "SettingsUser")

    def test_username_is_readonly_not_editable(self):
        self.client.login(username="SettingsUser", password="testpass123")
        response = self.client.get(reverse("rop-account-settings"))
        content = response.content.decode("utf-8")
        self.assertIn("readonly", content)
        self.assertIn("disabled", content)


class TestEmailChange(TestCase):
    """Email change must work server-side."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="EmailUser", password="testpass123", email="old@x.com")

    def test_email_can_be_changed(self):
        self.client.login(username="EmailUser", password="testpass123")
        response = self.client.post(
            reverse("rop-email-change"),
            {"email": "new@example.com"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

    def test_invalid_email_rejected(self):
        self.client.login(username="EmailUser", password="testpass123")
        response = self.client.post(
            reverse("rop-email-change"),
            {"email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["email_form"].errors)


class TestPasswordChange(TestCase):
    """Password change must use supported APIs and not corrupt session."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="PassUser", password="oldpass123", email="pass@x.com")

    def test_password_can_be_changed(self):
        self.client.login(username="PassUser", password="oldpass123")
        response = self.client.post(
            reverse("rop-password-change"),
            {"current_password": "oldpass123",
             "new_password1": "newpass456",
             "new_password2": "newpass456"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))

    def test_old_password_no_longer_authenticates(self):
        self.client.login(username="PassUser", password="oldpass123")
        self.client.post(
            reverse("rop-password-change"),
            {"current_password": "oldpass123",
             "new_password1": "newpass456",
             "new_password2": "newpass456"},
            follow=True,
        )
        self.client.logout()
        ok = self.client.login(username="PassUser", password="oldpass123")
        self.assertFalse(ok)

    def test_new_password_authenticates(self):
        self.client.login(username="PassUser", password="oldpass123")
        self.client.post(
            reverse("rop-password-change"),
            {"current_password": "oldpass123",
             "new_password1": "newpass456",
             "new_password2": "newpass456"},
            follow=True,
        )
        self.client.logout()
        ok = self.client.login(username="PassUser", password="newpass456")
        self.assertTrue(ok)

    def test_wrong_current_password_rejected(self):
        self.client.login(username="PassUser", password="oldpass123")
        response = self.client.post(
            reverse("rop-password-change"),
            {"current_password": "wrongpass",
             "new_password1": "newpass456",
             "new_password2": "newpass456"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["password_form"].errors)

    def test_mismatched_new_passwords_rejected(self):
        self.client.login(username="PassUser", password="oldpass123")
        response = self.client.post(
            reverse("rop-password-change"),
            {"current_password": "oldpass123",
             "new_password1": "newpass456",
             "new_password2": "different"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["password_form"].errors)

    def test_password_change_has_csrf(self):
        self.client.login(username="PassUser", password="oldpass123")
        response = self.client.get(reverse("rop-account-settings"))
        self.assertContains(response, "csrfmiddlewaretoken")


# -- PASSWORD RESET TESTS --


class TestPasswordResetFlow(TestCase):
    """Password reset routes and templates operate with test backend."""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ResetUser", password="testpass123",
            email="reset@example.com")

    def test_password_reset_page_renders(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_page_has_csrf(self):
        response = self.client.get(reverse("password_reset"))
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_password_reset_request_does_not_require_smtp(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "reset@example.com"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_done_page_renders(self):
        response = self.client.get(reverse("password_reset_done"))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_complete_page_renders(self):
        response = self.client.get(reverse("password_reset_complete"))
        self.assertEqual(response.status_code, 200)


# -- PHASE 1-2 REGRESSION TESTS --


class TestPhase3Regression(TestCase):
    """Existing Phase 1-2 features must remain intact."""

    def setUp(self):
        self.client = Client()

    @patch("web.website.views.portal.get_server_status")
    def test_homepage_still_renders(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 1}
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    @patch("web.website.views.portal.get_server_status")
    def test_server_status_still_renders(self, mock_status):
        mock_status.return_value = {"online": True, "player_count": 5}
        response = self.client.get(reverse("home"))
        content = response.content.decode("utf-8")
        self.assertIn("rop-status__dot--online", content)
        self.assertIn("Online", content)
        self.assertIn(">5<", content)
