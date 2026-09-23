"""ROP Portal Phase 6 — Character deletion + Account deletion views.

Both deletion flows require:
- login
- server-side authorization (ownership verified through request.user)
- GET → confirmation page only
- POST → destructive action with exact-name confirmation
- CSRF protection
"""
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .portal import get_evennia_account, get_account_character, portal_context


def _clear_chargen_session(request):
    """Remove any stale chargen wizard state from the session."""
    for key in ("name", "race", "profession", "faction", "stats", "rerolls", "step"):
        request.session.pop(f"chargen_{key}", None)


class CharacterDeleteView(View):
    """GET = confirmation page.  POST = permanent, immediate deletion.

    The authenticated account must own the character.  The user must type
    the exact current character name to confirm.  Comparison is
    case-sensitive.
    """

    template_name = "website/portal/delete_character.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        character = get_account_character(request.user)
        if character is None:
            messages.info(request, "You do not have a character to delete.")
            return redirect(reverse_lazy("rop-dashboard"))

        ctx = portal_context(request)
        ctx["page_title"] = "Delete Character"
        ctx["character_name"] = character.key
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        character = get_account_character(request.user)
        if character is None:
            messages.info(request, "You do not have a character to delete.")
            return redirect(reverse_lazy("rop-dashboard"))

        confirmation = request.POST.get("confirmation", "").strip()

        # Case-sensitive, exact-name comparison
        if confirmation != character.key:
            messages.error(request, "Confirmation does not match your character name. Deletion cancelled.")
            ctx = portal_context(request)
            ctx["page_title"] = "Delete Character"
            ctx["character_name"] = character.key
            return render(request, self.template_name, ctx)

        char_name = character.key

        # Remove from account's CharactersHandler first, then delete the object
        account = get_evennia_account(request.user)
        if account is not None:
            try:
                account.characters.remove(character)
            except Exception:
                pass

        try:
            character.delete()
        except Exception as exc:
            messages.error(request, f"An error occurred while deleting your character: {exc}")
            return redirect(reverse_lazy("rop-dashboard"))

        # Clear any stale chargen state so a replacement character can be created
        _clear_chargen_session(request)

        messages.success(request, f"Character '{char_name}' has been permanently deleted.")
        return redirect(reverse_lazy("rop-dashboard"))


class AccountDeleteView(View):
    """GET = confirmation page.  POST = permanent, immediate account deletion.

    Deleting the account also removes its owned character.  After
    deletion the user is logged out and redirected to the homepage.
    """

    template_name = "website/portal/delete_account.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        ctx = portal_context(request)
        ctx["page_title"] = "Delete Account"
        ctx["account_username"] = request.user.username
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        confirmation = request.POST.get("confirmation", "").strip()

        # Case-sensitive, exact-username comparison
        if confirmation != request.user.username:
            messages.error(request, "Confirmation does not match your username. Deletion cancelled.")
            ctx = portal_context(request)
            ctx["page_title"] = "Delete Account"
            ctx["account_username"] = request.user.username
            return render(request, self.template_name, ctx)

        # 1. Delete owned character first (if any), using authoritative path
        character = get_account_character(request.user)
        if character is not None:
            char_name = character.key
            account = get_evennia_account(request.user)
            if account is not None:
                try:
                    account.characters.remove(character)
                except Exception:
                    pass
            try:
                character.delete()
            except Exception:
                pass  # best-effort; continue to account deletion

        # 2. Delete the account via Evennia's authoritative delete()
        account = get_evennia_account(request.user)
        if account is not None:
            account.delete()

        # 3. Log the user out and clear the session
        auth_logout(request)
        request.session.flush()

        # Store a one-time message in a new session for the redirect
        messages.success(request, "Your account has been permanently deleted. Farewell, traveler.")
        return redirect(reverse_lazy("home"))