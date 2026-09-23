"""
ROP Website Models — Audit Log, Bans, Reserved Names

These models live alongside the Evennia typeclass system and
provide web-portal-specific persistent state.
"""

import datetime
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Record of important administrative/destructive actions."""

    actor_id = models.IntegerField(
        help_text="Account DB id of the acting admin/account."
    )
    actor_name = models.CharField(max_length=255, help_text="Username at time of action.")
    action = models.CharField(max_length=255, help_text="Short action category (ban, unban, etc.).")
    target_type = models.CharField(max_length=64, default="", blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    target_name = models.CharField(max_length=255, default="", blank=True)
    details = models.TextField(default="", blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "website"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log"

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.actor_name} / {self.action} → {self.target_name or 'N/A'}"


class Ban(models.Model):
    """Single authoritative ban record tied to an Account DB id."""

    account_id = models.IntegerField(unique=True, help_text="Account DB id of the banned account.")
    account_name = models.CharField(max_length=255, help_text="Username of the banned account, for display.")
    reason = models.TextField(help_text="Reason displayed to the banned player and stored for audit.")
    banned_by_id = models.IntegerField(help_text="Account DB id of the banning admin.")
    banned_by_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "website"
        verbose_name = "Ban"
        verbose_name_plural = "Bans"

    def __str__(self):
        return f"Ban #{self.pk} — {self.account_name} ({self.created_at.strftime('%Y-%m-%d')})"


class ReservedName(models.Model):
    """Centralised reserved/banned name list for accounts AND characters."""

    name = models.CharField(max_length=32, unique=True, help_text="Case-insensitive reserved name.")
    reason = models.CharField(max_length=255, default="Reserved", help_text="Why this name is reserved.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "website"
        verbose_name = "Reserved Name"
        verbose_name_plural = "Reserved Names"

    def __str__(self):
        return f"Reserved: {self.name}"

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super().save(*args, **kwargs)