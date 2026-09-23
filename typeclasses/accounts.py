"""
Account

The Account represents the game "account" and each login has only one
Account object.

One character per account — Rites of Passage rule.
"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the
    game, but puppets characters.
    """

    def get_character_slots(self) -> int:
        """Enforce one character per account."""
        return 1

    @classmethod
    def authenticate(cls, username, password, ip="", **kwargs):
        """Authenticate and enforce account bans via the Ban model.

        Wraps the parent authenticate().  If the parent succeeds but
        a Ban row exists for the account, authentication is rejected
        with an appropriate error.
        """
        account, errors = super().authenticate(
            username, password, ip=ip, **kwargs
        )
        if account is not None:
            try:
                from web.website.models import Ban
            except Exception:
                # Models not available (e.g. early startup) — allow
                return account, errors
            if Ban.objects.filter(account_id=account.id).exists():
                return None, ["This account has been suspended."]
        return account, errors


class Guest(DefaultGuest):
    """
    Guest accounts are simple low-level accounts that are created/deleted
    on the fly.
    """

    pass
