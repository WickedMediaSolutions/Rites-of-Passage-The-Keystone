"""ROP portal URL patterns — placed BEFORE Evennia defaults so they take precedence"""

from django.urls import path

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

from .views.portal import (
    HomeView,
    LoginView,
    RegisterView,
    logout_view,
    DashboardView,
    GettingStartedView,
    GameGuideView,
    LoreView,
    NewsView,
    DownloadsView,
    CommandIndexView,
    CommandDetailView,
    RacesView,
    ProfessionsView,
)
from .views.account import AccountSettingsView, EmailChangeView, PasswordChangeView
from .views.chargen import CharGenView
from .views.armory import ArmoryIndexView, ArmoryCharacterView
from .views.deletion import CharacterDeleteView, AccountDeleteView
from .views.admin import (
    AdminIndexView,
    AdminAccountView,
    AdminBanView,
    AdminUnbanView,
    AdminAuditView,
)

# ROP portal URL patterns — placed BEFORE Evennia defaults so they take precedence
urlpatterns = [
    # Homepage (overrides Evennia default index)
    path("", HomeView.as_view(), name="home"),

    # Auth (unique names to avoid collision with Django auth / Evennia defaults)
    path("login/", LoginView.as_view(), name="rop-login"),
    path("register/", RegisterView.as_view(), name="rop-register"),
    path("logout/", logout_view, name="rop-logout"),
    path("dashboard/", DashboardView.as_view(), name="rop-dashboard"),

    # Character creation (Phase 5 — full multi-step wizard)
    path("chargen/", CharGenView.as_view(), name="rop-chargen"),

    # Account settings
    path("account/settings/", AccountSettingsView.as_view(), name="rop-account-settings"),
    path("account/email/", EmailChangeView.as_view(), name="rop-email-change"),
    path("account/password/", PasswordChangeView.as_view(), name="rop-password-change"),

    # Deletion (Phase 6)
    path("character/delete/", CharacterDeleteView.as_view(), name="rop-character-delete"),
    path("account/delete/", AccountDeleteView.as_view(), name="rop-account-delete"),

    # Public portal pages (Phase 1 shells — Phase 7 content)
    path("getting-started/", GettingStartedView.as_view(), name="getting-started"),
    path("game-guide/", GameGuideView.as_view(), name="game-guide"),
    path("lore/", LoreView.as_view(), name="lore"),
    path("races/", RacesView.as_view(), name="races"),
    path("professions/", ProfessionsView.as_view(), name="professions"),
    path("news/", NewsView.as_view(), name="news"),
    path("downloads/", DownloadsView.as_view(), name="downloads"),

    # Phase 7 — Public command documentation
    path("commands/", CommandIndexView.as_view(), name="commands"),
    path("commands/<str:command_key>/", CommandDetailView.as_view(), name="command-detail"),

    # Phase 8 — Login-required Armory (character directory/profiles)
    path("armory/", ArmoryIndexView.as_view(), name="rop-armory"),
    path("armory/<str:character_name>/", ArmoryCharacterView.as_view(), name="rop-armory-character"),

    # Phase 9 — Superuser-only portal administration
    path("portal-admin/", AdminIndexView.as_view(), name="rop-admin-index"),
    path("portal-admin/account/<str:username>/", AdminAccountView.as_view(), name="rop-admin-account"),
    path("portal-admin/account/<str:username>/ban/", AdminBanView.as_view(), name="rop-admin-ban"),
    path("portal-admin/account/<str:username>/unban/", AdminUnbanView.as_view(), name="rop-admin-unban"),
    path("portal-admin/audit/", AdminAuditView.as_view(), name="rop-admin-audit"),
]

# Evennia default URLs come after ROP patterns
urlpatterns = urlpatterns + evennia_website_urlpatterns
