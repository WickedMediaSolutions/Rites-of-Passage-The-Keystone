"""Phase 10 — Final Integration & Production Polish Tests.

Covers the bounded portal integration surface: checks that Phase 1–9
operate as one coherent finished portal.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings

from web.website.models import Ban, AuditLog


User = get_user_model()


# =====================================================================
# 1.  Template & Static Configuration
# =====================================================================

class TemplatePrecedenceTests(TestCase):
    """Project web/templates/ comes first in production DIRS."""

    def test_project_templates_dir_is_first(self):
        dirs = settings.TEMPLATES[0]["DIRS"]
        self.assertTrue(len(dirs) >= 1, "TEMPLATES DIRS must not be empty")
        first_dir = dirs[0]
        self.assertIn("web/templates", first_dir)

    def test_staticfiles_dirs_does_not_reference_nonexistent(self):
        for d in settings.STATICFILES_DIRS:
            self.assertNotIn("web/static", d)

    def test_game_name_is_rites_of_passage(self):
        self.assertEqual(settings.SERVERNAME, "Rites of Passage")
# =====================================================================
# 2.  Public Page Reachability
# =====================================================================

class PublicPageReachabilityTests(TestCase):
    """Public pages return 200 for anonymous visitors."""

    def setUp(self):
        self.client = Client()

    def test_home_reachable(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

    def test_getting_started_reachable(self):
        resp = self.client.get(reverse("getting-started"))
        self.assertEqual(resp.status_code, 200)

    def test_game_guide_reachable(self):
        resp = self.client.get(reverse("game-guide"))
        self.assertEqual(resp.status_code, 200)

    def test_lore_reachable(self):
        resp = self.client.get(reverse("lore"))
        self.assertEqual(resp.status_code, 200)

    def test_news_reachable(self):
        resp = self.client.get(reverse("news"))
        self.assertEqual(resp.status_code, 200)

    def test_downloads_reachable(self):
        resp = self.client.get(reverse("downloads"))
        self.assertEqual(resp.status_code, 200)

    def test_commands_reachable(self):
        resp = self.client.get(reverse("commands"))
        self.assertEqual(resp.status_code, 200)


# =====================================================================
# 3.  Branding & Visible Text
# =====================================================================

class BrandingTests(TestCase):
    """User-facing branding is Rites of Passage, not Evennia defaults."""

    def setUp(self):
        self.client = Client()

    def test_rites_of_passage_in_homepage_title(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Rites of Passage")

    def test_no_default_evennia_tagline(self):
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "The Python MUD")
        self.assertNotContains(resp, "MU* creation system")

    def test_footer_has_rites_of_passage(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Rites of Passage")

    def test_no_traceback_in_public_pages(self):
        pages = ["home", "getting-started", "game-guide", "lore", "news",
                 "downloads"]
        for url_name in pages:
            resp = self.client.get(reverse(url_name))
            content = resp.content.decode()
            self.assertNotIn("Traceback (most recent call last)", content)
            self.assertNotIn("DJANGO_DEBUG", content)
# =====================================================================
# 4.  Navigation Visibility by Auth State
# =====================================================================

class NavigationVisibilityTests(TestCase):
    """Menu items correctly show/hide by auth state."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="navigator", password="testpass123"
        )
        self.admin = User.objects.create_superuser(
            username="navadmin", password="testpass123"
        )

    # --- Anonymous ---

    def test_anonymous_sees_public_nav(self):
        resp = self.client.get(reverse("home"))
        content = resp.content.decode()
        self.assertIn("Home", content)
        self.assertIn("Getting Started", content)
        self.assertIn("Game Guide", content)

    def test_anonymous_does_not_see_dashboard(self):
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Dashboard")

    def test_anonymous_does_not_see_portal_admin(self):
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Portal Admin")

    # --- Authenticated normal user ---

    def test_authenticated_sees_dashboard(self):
        self.client.login(username="navigator", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Dashboard")

    def test_authenticated_sees_armory(self):
        self.client.login(username="navigator", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Armory")

    def test_authenticated_sees_account_settings(self):
        self.client.login(username="navigator", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Account Settings")

    def test_normal_user_does_not_see_portal_admin(self):
        self.client.login(username="navigator", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Portal Admin")

    # --- Superuser ---

    def test_superuser_sees_portal_admin(self):
        self.client.login(username="navadmin", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Portal Admin")
# =====================================================================
# 5.  Dashboard Access
# =====================================================================

class DashboardAccessTests(TestCase):
    """Dashboard is login-required."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("rop-dashboard")
        self.user = User.objects.create_user(
            username="dashguy", password="testpass123"
        )

    def test_dashboard_redirects_anonymous(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, (301, 302))

    def test_dashboard_works_authenticated(self):
        self.client.login(username="dashguy", password="testpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


# =====================================================================
# 6.  Armory Accessk
# =====================================================================

class ArmoryAccessTests(TestCase):
    """Armory is login-required and functional."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="armoryguy", password="testpass123"
        )
        self.armory_url = reverse("rop-armory")

    def test_armory_redirects_anonymous(self):
        resp = self.client.get(self.armory_url)
        self.assertIn(resp.status_code, (301, 302))

    def test_armory_works_authenticated(self):
        self.client.login(username="armoryguy", password="testpass123")
        resp = self.client.get(self.armory_url)
        self.assertEqual(resp.status_code, 200)

    def test_armory_has_search_form(self):
        self.client.login(username="armoryguy", password="testpass123")
        resp = self.client.get(self.armory_url)
        self.assertContains(resp, 'name="q"')


# ======================================================================
# 7.  Portal Admin Access
# ======================================================================

class PortalAdminAccessTests(TestCase):
    """Portal Admin is superuser-only."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="paadmin", password="testpass123"
        )
        self.normal = User.objects.create_user(
            username="pauser", password="testpass123"
        )
        self.admin_url = reverse("rop-admin-index")
        self.audit_url = reverse("rop-admin-audit")

    def test_anonymous_redirected_from_admin(self):
        resp = self.client.get(self.admin_url)
        self.assertIn(resp.status_code, (301, 302))

    def test_normal_user_gets_403_on_admin(self):
        self.client.login(username="pauser", password="testpass123")
        resp = self.client.get(self.admin_url)
        self.assertEqual(resp.status_code, 403)

    def test_normal_user_gets_403_on_audit(self):
        self.client.login(username="pauser", password="testpass123")
        resp = self.client.get(self.audit_url)
        self.assertEqual(resp.status_code, 403)

    def test_superuser_accesses_admin(self):
        self.client.login(username="paadmin", password="testpass123")
        resp = self.client.get(self.admin_url)
        self.assertEqual(resp.status_code, 200)

    def test_superuser_accesses_audit(self):
        self.client.login(username="paadmin", password="testpass123")
        resp = self.client.get(self.audit_url)
        self.assertEqual(resp.status_code, 200)
# ======================================================================
# 8.  URL Reversals
# ======================================================================

class URLReversalTests(TestCase):
    """Critical portal URL names reverse successfully."""

    URLS = [
        ("home", [], {}),
        ("rop-login", [], {}),
        ("rop-register", [], {}),
        ("rop-logout", [], {}),
        ("rop-dashboard", [], {}),
        ("rop-chargen", [], {}),
        ("rop-account-settings", [], {}),
        ("rop-password-change", [], {}),
        ("rop-character-delete", [], {}),
        ("rop-account-delete", [], {}),
        ("getting-started", [], {}),
        ("game-guide", [], {}),
        ("lore", [], {}),
        ("news", [], {}),
        ("downloads", [], {}),
        ("commands", [], {}),
        ("rop-armory", [], {}),
        ("rop-armory-character", [], {"character_name": "TestHero"}),
        ("rop-admin-index", [], {}),
        ("rop-admin-audit", [], {}),
    ]

    def test_all_key_urls_reverse(self):
        for name, args, kwargs in self.URLS:
            with self.subTest(url_name=name):
                url = reverse(name, args=args, kwargs=kwargs)
                self.assertTrue(
                    url.startswith("/"), f"{name} must be absolute")


# ======================================================================
# 9.  GET Idempotency — No State Mutation
# ======================================================================

class GETNoMutationTests(TestCase):
    """GET requests on critical pages do not mutate state."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="etadmin", password="testpass123"
        )
        self.client.login(username="etadmin", password="testpass123")

    def test_GET_admin_index_no_ban_creation(self):
        count_before = Ban.objects.count()
        self.client.get(reverse("rop-admin-index"))
        self.assertEqual(Ban.objects.count(), count_before)

    def test_GET_admin_audit_no_audit_creation(self):
        count_before = AuditLog.objects.count()
        self.client.get(reverse("rop-admin-audit"))
        self.assertEqual(AuditLog.objects.count(), count_before)

    def test_GET_admin_account_no_side_effect(self):
        count_before = Ban.objects.count()
        self.client.get(reverse(
            "rop-admin-account", kwargs={"username": "etadmin"}))
        self.assertEqual(Ban.objects.count(), count_before)

    def test_GET_ban_URL_does_not_ban(self):
        count_before = Ban.objects.count()
        self.client.get(reverse(
            "rop-admin-ban", kwargs={"username": "etadmin"}))
        self.assertEqual(Ban.objects.count(), count_before)

    def test_GET_unban_URL_does_not_unban(self):
        """GET request to unban URL must not affect state."""
        target = User.objects.create_user(username="banme", password="pass")
        self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "banme"}),
            {"reason": "Testing GET idempotence"},
        )
        count_before = Ban.objects.count()
        self.client.get(reverse(
            "rop-admin-unban", kwargs={"username": "banme"}))
        self.assertEqual(Ban.objects.count(), count_before)


# ======================================================================
# 10.  Menu Template Precedence
# ======================================================================

class MenuRenderTests(TestCase):
    """Project _menu.html is rendered, not Evennia defaults."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="menuguy", password="testpass123"
        )

    def test_project_menu_served_on_homepage(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Getting Started")

    def test_project_menu_shows_logout_form(self):
        self.client.login(username="menuguy", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Log Out")

    def test_logout_uses_POST_not_GET(self):
        """Menu logout must use POST, not GET."""
        self.client.login(username="menuguy", password="testpass123")
        resp = self.client.get(reverse("home"))
        content = resp.content.decode()
        self.assertTrue(
            'method="post"' in content.lower()
            or 'method="POST"' in content)

    def test_no_duplicated_logout_controls(self):
        self.client.login(username="menuguy", password="testpass123")
        resp = self.client.get(reverse("home"))
        content = resp.content.decode()
        logout_count = content.count("Log Out")
        self.assertEqual(logout_count, 1,
                         f"Expected 1 Log Out, found {logout_count}")


# ======================================================================
# 11.  Migration Readiness — Structural Check
# ======================================================================

class MigrationAlignmentTests(TestCase):
    """Phase 9 migration 0001_initial.py aligns with current models."""

    def test_models_exist_in_app_config(self):
        from django.apps import apps
        app_conf = apps.get_app_config("website")
        model_names = [m.__name__ for m in app_conf.get_models()]
        self.assertIn("AuditLog", model_names)
        self.assertIn("Ban", model_names)
        self.assertIn("ReservedName", model_names)
        