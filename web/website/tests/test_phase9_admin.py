"""Phase 9 — Superuser Portal Admin, Bans, and Audit Log Tests."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from web.website.models import AuditLog, Ban


User = get_user_model()


class AdminAccessControlTests(TestCase):
    """Admin pages enforce superuser-only access."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.invalid", password="adminpass123"
        )
        self.normal_user = User.objects.create_user(
            username="normal", password="normalpass123"
        )
        self.admin_index_url = reverse("rop-admin-index")
        self.admin_audit_url = reverse("rop-admin-audit")

    # --- Anonymous ---

    def test_admin_index_requires_login(self):
        resp = self.client.get(self.admin_index_url)
        self.assertIn(resp.status_code, (301, 302))

    def test_audit_requires_login(self):
        resp = self.client.get(self.admin_audit_url)
        self.assertIn(resp.status_code, (301, 302))

    # --- Non-superuser ---

    def test_normal_user_gets_403_on_admin_index(self):
        self.client.login(username="normal", password="normalpass123")
        resp = self.client.get(self.admin_index_url)
        self.assertEqual(resp.status_code, 403)

    def test_normal_user_gets_403_on_account_detail(self):
        self.client.login(username="normal", password="normalpass123")
        resp = self.client.get(
            reverse("rop-admin-account", kwargs={"username": "admin"}))
        self.assertEqual(resp.status_code, 403)

    def test_normal_user_gets_403_on_audit(self):
        self.client.login(username="normal", password="normalpass123")
        resp = self.client.get(self.admin_audit_url)
        self.assertEqual(resp.status_code, 403)

    # --- Superuser ---

    def test_superuser_can_access_admin_index(self):
        self.client.login(username="admin", password="adminpass123")
        resp = self.client.get(self.admin_index_url)
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_access_account_detail(self):
        self.client.login(username="admin", password="adminpass123")
        resp = self.client.get(
            reverse("rop-admin-account", kwargs={"username": "normal"}))
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_access_audit(self):
        self.client.login(username="admin", password="adminpass123")
class AdminSearchTests(TestCase):
    """Account search on admin index."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.a = User.objects.create_user(username="Alice", password="pw")
        self.b = User.objects.create_user(username="Bob", password="pw")
        self.c = User.objects.create_user(username="AlphaUser", password="pw")
        self.client.login(username="admin", password="adminpass123")

    def test_search_case_insensitive(self):
        resp = self.client.get(reverse("rop-admin-index") + "?q=alice")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_search_partial_username(self):
        resp = self.client.get(reverse("rop-admin-index") + "?q=alp")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AlphaUser")
        self.assertNotContains(resp, "Bob")

    def test_empty_search_lists_all(self):
        resp = self.client.get(reverse("rop-admin-index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Bob")
        self.assertContains(resp, "AlphaUser")
        self.assertContains(resp, "admin")

    def test_no_private_data_exposed(self):
        resp = self.client.get(reverse("rop-admin-index"))
        content = resp.content.decode()
        # Sentinel value that should never leak
        self.assertNotIn("PRIVATE_ARMORY_INTERNAL_SENTINEL", content)
        # The admin's actual encoded password hash must never appear
        self.assertNotIn(self.admin.password, content)


class BanUnbanTests(TestCase):
    """Ban and unban actions."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.target = User.objects.create_user(
            username="target_user", password="pw"
        )
        self.client.login(username="admin", password="adminpass123")

    def _ban(self, username="target_user", reason="Misconduct"):
        return self.client.post(
            reverse("rop-admin-ban", kwargs={"username": username}),
            {"reason": reason},
        )

    def _unban(self, username="target_user"):
        return self.client.post(
            reverse("rop-admin-unban", kwargs={"username": username}),
        )

    # --- Basic ban / unban ---

    def test_ban_requires_post(self):
        resp = self.client.get(
            reverse("rop-admin-ban", kwargs={"username": "target_user"}))
        self.assertIn(resp.status_code, (301, 302, 405))

    def test_ban_requires_reason(self):
        resp = self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "target_user"}),
            {"reason": ""},
            follow=True,
        )
        self.assertContains(resp, "ban reason is required")

    def test_whitespace_only_reason_rejected(self):
        resp = self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "target_user"}),
            {"reason": "   "},
            follow=True,
        )
        self.assertContains(resp, "ban reason is required")

    def test_successful_ban(self):
        resp = self._ban(reason="Cheating detected")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Ban.objects.filter(account_id=self.target.id).exists())
        ban = Ban.objects.get(account_id=self.target.id)
        self.assertEqual(ban.reason, "Cheating detected")
        self.assertEqual(ban.banned_by_id, self.admin.id)

    def test_ban_preserves_account(self):
        self._ban(reason="Test ban")
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, "target_user")

    def test_self_ban_rejected(self):
        resp = self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "admin"}),
            {"reason": "self-ban attempt"},
            follow=True,
        )
        self.assertContains(resp, "cannot ban your own account")
        self.assertFalse(
            Ban.objects.filter(account_id=self.admin.id).exists())

    def test_double_ban_is_idempotent(self):
        self._ban(reason="First reason")
        self._ban(reason="Second reason")
        self.assertEqual(Ban.objects.filter(account_id=self.target.id).count(), 1)

    # --- Unban ---

    def test_unban_requires_post(self):
        resp = self.client.get(
            reverse("rop-admin-unban", kwargs={"username": "target_user"}))
        self.assertIn(resp.status_code, (301, 302, 405))

    def test_successful_unban(self):
        self._ban(reason="To unban later")
        self.assertTrue(
            Ban.objects.filter(account_id=self.target.id).exists())
        resp = self._unban()
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            Ban.objects.filter(account_id=self.target.id).exists())

    def test_unban_non_banned(self):
        resp = self.client.post(
            reverse("rop-admin-unban", kwargs={"username": "target_user"}),
            follow=True,
        )
        self.assertContains(resp, "not currently banned")
class AuditLogTests(TestCase):
    """Audit log records and viewing."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.target = User.objects.create_user(
            username="testplayer", password="pw"
        )
        self.client.login(username="admin", password="adminpass123")

    def test_ban_creates_audit_record(self):
        self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "testplayer"}),
            {"reason": "Spamming"},
        )
        self.assertEqual(
            AuditLog.objects.filter(action="BAN_ACCOUNT").count(), 1)
        entry = AuditLog.objects.filter(action="BAN_ACCOUNT").first()
        self.assertEqual(entry.actor_name, "admin")
        self.assertEqual(entry.target_name, "testplayer")
        self.assertEqual(entry.details, "Spamming")

    def test_unban_creates_audit_record(self):
        Ban.objects.create(
            account_id=self.target.id,
            account_name=self.target.username,
            reason="Was bad",
            banned_by_id=self.admin.id,
            banned_by_name=self.admin.username,
        )
        self.client.post(
            reverse("rop-admin-unban", kwargs={"username": "testplayer"}),
        )
        self.assertEqual(
            AuditLog.objects.filter(action="UNBAN_ACCOUNT").count(), 1)

    def test_audit_log_newest_first(self):
        AuditLog.objects.create(
            actor_id=self.admin.id, actor_name="admin",
            action="BAN_ACCOUNT", target_name="old",
        )
        AuditLog.objects.create(
            actor_id=self.admin.id, actor_name="admin",
            action="BAN_ACCOUNT", target_name="new",
        )
        resp = self.client.get(reverse("rop-admin-audit"))
        content = resp.content.decode()
        old_idx = content.index("old")
        new_idx = content.index("new")
        self.assertLess(new_idx, old_idx)

    def test_audit_history_preserved_after_unban(self):
        self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "testplayer"}),
            {"reason": "Ban first"},
        )
        self.client.post(
            reverse("rop-admin-unban", kwargs={"username": "testplayer"}),
        )
        self.assertEqual(
            AuditLog.objects.filter(action="BAN_ACCOUNT").count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action="UNBAN_ACCOUNT").count(), 1)

    def test_audit_requires_superuser(self):
        self.client.logout()
        self.client.login(username="testplayer", password="pw")
class LoginEnforcementTests(TestCase):
    """Website login enforcement of bans."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.target = User.objects.create_user(
            username="bannedguy", password="testpass123"
        )

    def test_banned_account_cannot_login_portal(self):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "bannedguy"}),
            {"reason": "Testing login block"},
            follow=True,
        )
        self.client.logout()

        resp = self.client.post(
            reverse("rop-login"),
            {"username": "bannedguy", "password": "testpass123"},
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Account suspended", content)

    def test_same_authoritative_ban_state(self):
        """Both portal login and game auth share one ban source."""
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse("rop-admin-ban", kwargs={"username": "bannedguy"}),
            {"reason": "Shared ban test"},
        )
        ban = Ban.objects.get(account_id=self.target.id)
        self.assertEqual(ban.account_id, self.target.id)
        self.assertEqual(ban.account_name, "bannedguy")


class NavigationTests(TestCase):
    """Admin navigation visibility."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.normal = User.objects.create_user(
            username="normal", password="pw"
        )

    def test_superuser_sees_admin_nav(self):
        self.client.login(username="admin", password="adminpass123")
        resp = self.client.get(reverse("rop-dashboard"))
        self.assertContains(resp, "Portal Admin")

    def test_normal_user_does_not_see_admin_nav(self):
        self.client.login(username="normal", password="pw")
        resp = self.client.get(reverse("rop-dashboard"))
        self.assertNotContains(resp, "Portal Admin")

    def test_anonymous_does_not_see_admin_nav(self):
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Portal Admin")


class GetNoMutationTests(TestCase):
    """GET requests on admin pages do not mutate state."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")

    def test_get_admin_index_no_side_effect(self):
        count_before = Ban.objects.count()
        self.client.get(reverse("rop-admin-index"))
        self.assertEqual(Ban.objects.count(), count_before)

    def test_get_account_detail_no_side_effect(self):
        count_before = Ban.objects.count()
        self.client.get(
            reverse("rop-admin-account", kwargs={"username": "admin"}))
        self.assertEqual(Ban.objects.count(), count_before)

    def test_get_audit_no_side_effect(self):
        count_before = AuditLog.objects.count()
        self.client.get(reverse("rop-admin-audit"))
        self.assertEqual(AuditLog.objects.count(), count_before)