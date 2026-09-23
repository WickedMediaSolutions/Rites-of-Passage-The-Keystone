"""
ROP Naming Validation — Shared between account usernames and character names.

Centralised configurable reserved-name checks using the ReservedName model.
"""

import re

NAME_PATTERN = re.compile(r"^[a-zA-Z-]+$")
MIN_LENGTH = 3
MAX_LENGTH = 14

# Hardcoded reserved names that are ALWAYS blocked.
# 'odin' is the only hardcoded entry; everything else goes in the DB model.
HARD_RESERVED = frozenset({"odin"})


def _normalize(name: str) -> str:
    """Return a lowercase, stripped version for comparison."""
    return name.lower().strip()


def validate_name_format(name: str) -> list[str]:
    """
    Validate name format independently of uniqueness/reserved checks.

    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []

    if not name:
        errors.append("Name is required.")
        return errors

    name = name.strip()

    if len(name) < MIN_LENGTH:
        errors.append(f"Name must be at least {MIN_LENGTH} characters.")
    if len(name) > MAX_LENGTH:
        errors.append(f"Name must be at most {MAX_LENGTH} characters.")
    if not NAME_PATTERN.match(name):
        errors.append("Name may contain only letters and hyphens.")
    if "--" in name:
        errors.append("Name may not contain consecutive hyphens.")
    if name.startswith("-") or name.endswith("-"):
        errors.append("Name may not start or end with a hyphen.")

    return errors


def is_hard_reserved(name: str) -> bool:
    """Check the minimal hardcoded reserved set."""
    return _normalize(name) in HARD_RESERVED


def get_db_reserved_names() -> set[str]:
    """
    Load the lowercased reserved-name set from the DB.
    Returns an empty set if the table doesn't exist yet (e.g. pre-migration).
    """
    try:
        from web.website.models import ReservedName
        return set(ReservedName.objects.values_list("name", flat=True))
    except Exception:
        return set()


def is_name_reserved(name: str) -> tuple[bool, str]:
    """
    Return (True, reason) if the name is reserved via hardcoded set
    or the centralised ReservedName table.
    """
    norm = _normalize(name)
    if norm in HARD_RESERVED:
        return True, "This name is permanently reserved."
    db_reserved = get_db_reserved_names()
    if norm in db_reserved:
        return True, "This name is reserved."
    return False, ""


def validate_name_unique_account(name: str) -> list[str]:
    """
    Check that the name isn't already taken as an Evennia account username
    (case-insensitive).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    norm = _normalize(name)
    if User.objects.filter(username__iexact=norm).exists():
        return ["An account with this name already exists."]
    return []


def validate_name_unique_character(name: str) -> list[str]:
    """
    Check that the name isn't already taken as a character name (case-insensitive).
    """
    from evennia.objects.models import ObjectDB
    norm = _normalize(name)
    if ObjectDB.objects.filter(db_key__iexact=norm).exists():
        return ["A character with this name already exists."]
    return []