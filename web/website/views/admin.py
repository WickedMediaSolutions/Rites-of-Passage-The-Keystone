"""ROP Portal Phase 9 — Superuser-Only Admin Views.

Ban / Unban / Account browsing / Audit log.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View

from .portal import portal_context, is_banned
from ..models import Ban, AuditLog


User = get_user_model()


# ------------------------------------------------------------------
# Access-control helpers
# ------------------------------------------------------------------

def _require_superuser(request):
    """Return a redirect response if the user is not a superuser."""
    if not request.user.is_authenticated:
        return redirect(reverse_lazy("rop-login"))
    if not request.user.is_superuser:
        return render(request, "website/portal/admin_403.html", {
            **portal_context(request),
            "page_title": "Access Denied",
        }, status=403)
    return None
# ------------------------------------------------------------------
# Admin index — account list / search
# ------------------------------------------------------------------

class AdminIndexView(View):
    """Superuser-only account directory with search."""

    template_name = "website/portal/admin_index.html"

    def dispatch(self, request, *args, **kwargs):
        blocked = _require_superuser(request)
        if blocked is not None:
            return blocked
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        if query:
            q_lower = query.lower()
            users = User.objects.filter(
                Q(username__icontains=q_lower) | Q(email__icontains=q_lower)
            ).order_by("username")
        else:
            users = User.objects.all().order_by("username")

        accounts = []
        for u in users:
            banned, ban_record = is_banned(u)
            accounts.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_superuser": u.is_superuser,
                "is_banned": banned,
                "ban_reason": ban_record.reason if ban_record else None,
            })

        ctx = portal_context(request)
        ctx["page_title"] = "Portal Administration"
        ctx["accounts"] = accounts
        ctx["search_query"] = query
        ctx["total_count"] = len(accounts)
        return render(request, self.template_name, ctx)
# ------------------------------------------------------------------
# Account detail + ban / unban
# ------------------------------------------------------------------

class AdminAccountView(View):
    """Superuser-only account detail page with ban/unban actions."""

    template_name = "website/portal/admin_account.html"

    def dispatch(self, request, *args, **kwargs):
        blocked = _require_superuser(request)
        if blocked is not None:
            return blocked
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        target_user = get_object_or_404(User, username=kwargs["username"])
        banned, ban_record = is_banned(target_user)

        ctx = portal_context(request)
        ctx["page_title"] = f"Admin — {target_user.username}"
        ctx["target_user"] = target_user
        ctx["is_banned"] = banned
        ctx["ban_record"] = ban_record
        return render(request, self.template_name, ctx)


class AdminBanView(View):
    """POST-only ban action.  Requires non-empty reason."""

    def dispatch(self, request, *args, **kwargs):
        blocked = _require_superuser(request)
        if blocked is not None:
            return blocked
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        target_user = get_object_or_404(User, username=kwargs["username"])

        # Self-ban safety
        if target_user.id == request.user.id:
            messages.error(request, "You cannot ban your own account.")
            return redirect(reverse_lazy(
                "rop-admin-account",
                kwargs={"username": target_user.username}))

        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "A ban reason is required.")
            return redirect(reverse_lazy(
                "rop-admin-account",
                kwargs={"username": target_user.username}))

        # Check if already banned — idempotent
        banned, _existing = is_banned(target_user)
        if banned:
            messages.info(request,
                          f"{target_user.username} is already banned.")
            return redirect(reverse_lazy(
                "rop-admin-account",
                kwargs={"username": target_user.username}))

        Ban.objects.create(
            account_id=target_user.id,
            account_name=target_user.username,
            reason=reason,
            banned_by_id=request.user.id,
            banned_by_name=request.user.username,
        )

        AuditLog.objects.create(
            actor_id=request.user.id,
            actor_name=request.user.username,
            action="BAN_ACCOUNT",
            target_type="account",
            target_id=target_user.id,
            target_name=target_user.username,
            details=reason,
        )

        messages.success(request, f"{target_user.username} has been banned.")
        return redirect(reverse_lazy(
            "rop-admin-account",
            kwargs={"username": target_user.username}))


class AdminUnbanView(View):
    """POST-only unban action."""

    def dispatch(self, request, *args, **kwargs):
        blocked = _require_superuser(request)
        if blocked is not None:
            return blocked
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        target_user = get_object_or_404(User, username=kwargs["username"])

        banned, _existing = is_banned(target_user)
        if not banned:
            messages.info(request,
                          f"{target_user.username} is not currently banned.")
            return redirect(reverse_lazy(
                "rop-admin-account",
                kwargs={"username": target_user.username}))

        Ban.objects.filter(account_id=target_user.id).delete()

        AuditLog.objects.create(
            actor_id=request.user.id,
            actor_name=request.user.username,
            action="UNBAN_ACCOUNT",
            target_type="account",
            target_id=target_user.id,
            target_name=target_user.username,
            details="Manual unban by superuser.",
        )

        messages.success(request, f"{target_user.username} has been unbanned.")
        return redirect(reverse_lazy(
            "rop-admin-account",
            kwargs={"username": target_user.username}))


# ------------------------------------------------------------------
# Audit log
# ------------------------------------------------------------------

class AdminAuditView(View):
    """Superuser-only audit log viewer — newest first, read-only."""

    template_name = "website/portal/admin_audit.html"

    def dispatch(self, request, *args, **kwargs):
        blocked = _require_superuser(request)
        if blocked is not None:
            return blocked
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        entries = AuditLog.objects.all().order_by("-timestamp")
        ctx = portal_context(request)
        ctx["page_title"] = "Audit Log"
        ctx["audit_entries"] = entries
        return render(request, self.template_name, ctx)