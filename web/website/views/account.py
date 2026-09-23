"""ROP Account Settings — email change, password change, account landing."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, UpdateView

from ..forms import ROPAccountEmailForm, ROPAccountPasswordForm
from ..naming import validate_name_format, MIN_LENGTH, MAX_LENGTH


class AccountSettingsView(TemplateView):
    """Display-only username + links to email/password change forms."""

    template_name = "website/portal/account_settings.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Account Settings"
        ctx["min_length"] = MIN_LENGTH
        ctx["max_length"] = MAX_LENGTH
        return ctx


class EmailChangeView(FormView):
    """Change the authenticated account's email address."""

    template_name = "website/portal/account_settings.html"
    form_class = ROPAccountEmailForm
    success_url = reverse_lazy("rop-account-settings")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.request.user
        user.email = form.cleaned_data["email"]
        user.save(update_fields=["email"])
        messages.success(self.request, "Your email address has been updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Account Settings"
        ctx["email_form"] = ctx.pop("form", None)
        return ctx


class PasswordChangeView(FormView):
    """Change the authenticated account's password via supported APIs."""

    template_name = "website/portal/account_settings.html"
    form_class = ROPAccountPasswordForm
    success_url = reverse_lazy("rop-account-settings")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data["new_password1"])
        user.save(update_fields=["password"])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Account Settings"
        ctx["password_form"] = ctx.pop("form", None)
        return ctx