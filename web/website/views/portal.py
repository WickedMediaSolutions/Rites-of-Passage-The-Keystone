"""ROP Portal — helpers, home, auth, dashboard, public pages."""

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import TemplateView, FormView, View
from django import forms as django_forms

import evennia

from ..forms import ROPAccountCreationForm
from ..models import Ban


class LoginForm(django_forms.Form):
    username = django_forms.CharField()
    password = django_forms.CharField(widget=django_forms.PasswordInput)


def get_server_status():
    """Return public server status from authoritative Evennia session state.

    Returns:
        dict: ``{"online": bool, "player_count": int}``.
        ``online`` is True when the Evennia server is running and the
        session handler is available.
        ``player_count`` is the number of *unique connected accounts*
        (not raw sessions), avoiding double-counting of players with
        multiple connections.
    """
    try:
        handler = evennia.SESSION_HANDLER
        if handler is None:
            return {"online": False, "player_count": 0}
        # account_count() deduplicates by uid — counts unique players
        count = handler.account_count()
        return {"online": True, "player_count": count}
    except Exception:
        return {"online": False, "player_count": 0}


def get_evennia_account(user):
    """Resolve a Django User to the authoritative Evennia Account typeclass.

    Uses ``AccountDB.objects.get(id=user.id)`` — the canonical Evennia link
    because AccountDB shares its primary key with the Django User model.

    Returns:
        The Evennia Account typeclass instance, or ``None`` if no
        corresponding Evennia account exists.
    """
    if user is None or not user.is_authenticated:
        return None
    try:
        from evennia.accounts.models import AccountDB
        return AccountDB.objects.filter(id=user.id).first()
    except Exception:
        return None


def get_account_character(user):
    """Return the portal account's single character, or ``None``.

    Uses the canonical Evennia AccountDB → .characters API path.
    Gracefully handles accounts with no characters, missing attributes,
    or any unexpected account-state edge cases.

    IMPORTANT: this is the SINGLE authoritative helper for obtaining
    the portal account's character. Do not create alternative paths.
    """
    account = get_evennia_account(user)
    if account is None:
        return None
    try:
        chars = account.characters.all()
        return chars[0] if chars else None
    except Exception:
        return None


def account_has_character(user) -> bool:
    """Centralised helper: does this authenticated account own a character?

    Use everywhere the one-character-per-account rule must be enforced
    or checked within the portal layer.
    """
    return get_account_character(user) is not None


def is_banned(user):
    if not user.is_authenticated:
        return False, None
    try:
        return True, Ban.objects.get(account_id=user.id)
    except Ban.DoesNotExist:
        return False, None


def portal_context(request=None):
    """Build the common portal template context.

    For authenticated users, injects the account's character (if any),
    ban status, and superuser flag.  Character data comes exclusively
    from the authoritative Evennia typeclass / CharacterData handler.
    """
    ctx = {"server_status": get_server_status()}
    if request and request.user.is_authenticated:
        ctx["rop_character"] = get_account_character(request.user)
        ctx["has_character"] = account_has_character(request.user)
        ctx["is_banned"], ctx["ban"] = is_banned(request.user)
        ctx["is_superuser"] = request.user.is_superuser
    return ctx


# Canonical DB-key → image-filename mapping for races.
# Most follow race-{key}.jpg but some DB keys use underscores
# while filenames use hyphens.
_RACE_IMAGE_OVERRIDES = {
    "stone_giant": "race-stone-giant.webp",
    "wild_elf": "race-wild-elf.webp",
    "high_elf": "race-high-elf.webp",
}


def get_race_image(race_id: str) -> str:
    """Return the image filename for a race DB key.

    Returns a path relative to ``website/images/``, e.g.
    ``race-human.jpg`` or ``race-stone-giant.webp``.
    """
    return _RACE_IMAGE_OVERRIDES.get(race_id, f"race-{race_id}.webp")


def get_profession_image(prof_id: str) -> str:
    """Return the image filename for a profession DB key."""
    return f"profession-{prof_id}.webp"


def _build_character_display(ctx):
    """Build dashboard character-display context from the authoritative
    Evennia character object.

    Reads only properties that exist on the Character typeclass / its
    CharacterData game handler.  Gracefully displays unavailable or
    missing optional values (guild, sect) as ``None`` so the template
    can render a fallback dash.
    """
    char = ctx.get("rop_character")
    if char is None:
        return

    display = {
        "name": getattr(char, "key", None),
        "level": getattr(char, "level", None),
        "race_id": getattr(char, "race_id", None),
    }

    # Race — look up display name from existing RACES data when available.
    race_id = getattr(char, "race_id", None)
    if race_id:
        try:
            from world.data.races import RACES
            race_def = RACES.get(race_id, {})
            display["race"] = race_def.get("name", race_id)
            display["race_image"] = get_race_image(race_id)
        except Exception:
            display["race"] = race_id
    else:
        display["race"] = None

    # Profession — look up display name from existing PROFESSIONS data.
    prof_id = getattr(char, "profession_id", None)
    if prof_id:
        try:
            from world.data.professions import PROFESSIONS
            prof_def = PROFESSIONS.get(prof_id, {})
            display["profession"] = prof_def.get("name", prof_id)
        except Exception:
            display["profession"] = prof_id
    else:
        display["profession"] = None

    # Faction — canonical Valroian (Good) / Mordrath (Evil)
    faction = getattr(char, "faction", None)
    if faction is not None:
        try:
            display["faction"] = faction.value
            display["faction_label"] = "Valroian" if faction.value == "good" else "Mordrath"
        except Exception:
            display["faction"] = str(faction)
            display["faction_label"] = str(faction)
    else:
        display["faction"] = None
        display["faction_label"] = None

    # Optional affiliations — None if not set, template renders dash.
    try:
        display["guild_id"] = char.game.guild_id if char.game else None
    except Exception:
        display["guild_id"] = None
    try:
        display["sect_id"] = char.game.sect_id if char.game else None
    except Exception:
        display["sect_id"] = None

    ctx["char_display"] = display


# ==========================================================================
# Views
# ==========================================================================


class HomeView(TemplateView):
    template_name = "website/portal/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Rites of Passage"
        return ctx


class RegisterView(FormView):
    template_name = "website/portal/register.html"
    form_class = ROPAccountCreationForm
    success_url = "/"

    def form_valid(self, form):
        from django.conf import settings
        from evennia.utils import class_from_module

        account_class = class_from_module(
            settings.BASE_ACCOUNT_TYPECLASS,
            fallback=settings.FALLBACK_ACCOUNT_TYPECLASS,
        )
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password1"]
        email = form.cleaned_data["email"]
        account, errs = account_class.create(
            username=username, password=password, email=email
        )
        if not account:
            for e in errs:
                form.add_error("username", e)
            return self.form_invalid(form)
        user = authenticate(self.request, username=username, password=password)
        if user:
            auth_login(self.request, user)
            messages.success(self.request, f"Welcome to Rites of Passage, {username}!")
        return HttpResponseRedirect(self.success_url)


class LoginView(FormView):
    template_name = "website/portal/login.html"
    form_class = LoginForm
    success_url = "/dashboard/"

    def form_valid(self, form):
        u = form.cleaned_data["username"]
        p = form.cleaned_data["password"]
        user = authenticate(self.request, username=u, password=p)
        if user:
            banned, ban = is_banned(user)
            if banned:
                messages.error(self.request, f"Account suspended: {ban.reason}")
                return self.form_invalid(form)
            auth_login(self.request, user)
            return HttpResponseRedirect(self.success_url)
        messages.error(self.request, "Invalid username or password.")
        return self.form_invalid(form)


def logout_view(request):
    """POST-only logout — the _menu.html template always submits via POST
    with CSRF protection.  Reject GET to prevent accidental/anchor-click
    logouts that bypass CSRF."""
    if request.method != "POST":
        return redirect("/")
    auth_logout(request)
    return redirect("/")


class DashboardView(TemplateView):
    """Logged-in dashboard — zero-char and one-char states."""

    template_name = "website/portal/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")
        banned, ban = is_banned(request.user)
        if banned:
            messages.error(request, f"Account suspended: {ban.reason}")
            auth_logout(request)
            return redirect("/login/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Dashboard"
        _build_character_display(ctx)
        return ctx


# ------------------------------------------------------------------
# Placeholder character-creation route (authenticated shell only)
# ------------------------------------------------------------------

class CharCreatePlaceholderView(TemplateView):
    """Minimal authenticated placeholder for the future character creator.

    Phase 5 will replace this with the full chargen workflow.
    This view exists so the Create Character dashboard action has
    a valid route.
    """

    template_name = "website/portal/chargen_placeholder.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")
        # Enforce one-character rule at the portal layer.
        if account_has_character(request.user):
            messages.info(request, "You already have a character.")
            return redirect("/dashboard/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Character Creation"
        return ctx


# ------------------------------------------------------------------
# Public portal pages (Phase 1 shells — unchanged)
# ------------------------------------------------------------------

class GettingStartedView(TemplateView):
    template_name = "website/portal/getting_started.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Getting Started"
        return ctx


class GameGuideView(TemplateView):
    template_name = "website/portal/game_guide.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Game Guide"
        return ctx


class LoreView(TemplateView):
    template_name = "website/portal/lore.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Lore & World"
        return ctx


class NewsView(TemplateView):
    template_name = "website/portal/news.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "News & Updates"
        return ctx


class DownloadsView(TemplateView):
    template_name = "website/portal/downloads.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Downloads"
        return ctx

# ------------------------------------------------------------------
# Phase 7 — Public Command Documentation
# ------------------------------------------------------------------

from ..documentation import (
    COMMAND_DOCS, get_command, get_commands_by_category, search_commands,
)


class CommandIndexView(TemplateView):
    """Public command index — all documented commands grouped by category."""

    template_name = "website/portal/commands.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Command Reference"
        ctx["categories"] = get_commands_by_category()
        # Search / filter support
        query = self.request.GET.get("q", "").strip()
        ctx["search_query"] = query
        if query:
            ctx["search_results"] = search_commands(query)
        else:
            ctx["search_results"] = None
        return ctx


class CommandDetailView(TemplateView):
    """Public detail page for a single documented command."""

    template_name = "website/portal/command_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        command_key = self.kwargs.get("command_key", "")
        doc = get_command(command_key)
        if doc is None:
            ctx["command_doc"] = None
            ctx["not_found_key"] = command_key
            ctx["page_title"] = "Command Not Found"
        else:
            ctx["command_doc"] = doc
            ctx["page_title"] = f"Command: {doc.key}"
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if context.get("command_doc") is None:
            response = super().render_to_response(context, **response_kwargs)
            response.status_code = 404
            return response
        return super().render_to_response(context, **response_kwargs)


# ------------------------------------------------------------------
# Races — Public Compendium
# ------------------------------------------------------------------

class RacesView(TemplateView):
    """Public race compendium — all 24 races with Gothic presentation."""

    template_name = "website/portal/races.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Races of the Realm"

        from world.data.races import RACES
        from world.data.enums import Faction

        good_races = {}
        evil_races = {}
        for rid, rdef in RACES.items():
            entry = dict(rdef)
            entry["image"] = get_race_image(rid)
            if rdef["faction"] == Faction.GOOD:
                good_races[rid] = entry
            else:
                evil_races[rid] = entry

        ctx["good_races"] = good_races
        ctx["evil_races"] = evil_races
        ctx["total_races"] = len(RACES)
        return ctx


# ------------------------------------------------------------------
# Professions — Public Compendium
# ------------------------------------------------------------------

class ProfessionsView(TemplateView):
    """Public profession compendium — all 10 professions."""

    template_name = "website/portal/professions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Professions"

        from world.data.professions import PROFESSIONS

        profs = {}
        for pid, pdef in PROFESSIONS.items():
            entry = dict(pdef)
            entry["image"] = get_profession_image(pid)
            profs[pid] = entry

        ctx["professions"] = profs
        ctx["total_professions"] = len(PROFESSIONS)
        return ctx

