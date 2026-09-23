"""ROP Portal Phase 8 — Login-Required Character Armory.

Browse, search, and view existing player-character profiles.
All routes require authentication.
"""

from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import TemplateView

from evennia.objects.models import ObjectDB

from .portal import portal_context


def _resolve_characters():
    """Return all existing player-character objects alphabetically by name.

    Uses Evennia's ObjectDB to filter by the authoritative Character
    typeclass path, then sorts case-insensitively by ``key``.
    Objects whose typeclass path does not match the ROP Character
    typeclass are excluded (NPCs, rooms, etc.).

    Returns:
        list[ObjectDB]: Ordered character objects.
    """
    chars = ObjectDB.objects.filter(
        db_typeclass_path__contains="characters.Character",
    ).order_by("db_key")
    # Evennia ORDER BY is case-sensitive; enforce case-insensitive
    # secondary sort in Python to guarantee correct result.
    return sorted(chars, key=lambda c: c.key.lower())


def _resolve_character_by_name(name: str):
    """Return a single character object by exact name or raise Http404.

    Only matches player-character typeclass instances; deleted
    characters are already absent from the database.

    Args:
        name: Case-insensitive character name to look up.

    Returns:
        ObjectDB: The matching character instance.

    Raises:
        Http404: No match or non-character match.
    """
    chars = ObjectDB.objects.filter(
        db_typeclass_path__contains="characters.Character",
        db_key__iexact=name,
    )
    if not chars.exists():
        raise Http404("Character not found.")
    return chars.first()


def _build_armory_display(char):
    """Build safe, read-only Armory display context from authoritative
    character typeclass and its CharacterData handler.

    Returns a dict ready for template rendering.  Does NOT modify
    the character.  Omits fields without authoritative backing.

    Args:
        char: Evennia Character typeclass instance.

    Returns:
        dict: Armory profile display dictionary.
    """
    display = {}
    game = char.game if hasattr(char, "game") else None

    # --- Identity ---
    display["name"] = getattr(char, "key", None)
    display["level"] = getattr(char, "level", None)

    # Race display name from authoritative RACES registry
    race_id = getattr(char, "race_id", None)
    display["race_id"] = race_id
    if race_id:
        try:
            from world.data.races import RACES
            race_def = RACES.get(race_id, {})
            display["race"] = race_def.get("name", race_id)
            from web.website.views.portal import get_race_image
            display["race_image"] = get_race_image(race_id)
        except Exception:
            display["race"] = race_id
    else:
        display["race"] = None

    # Profession display name from authoritative PROFESSIONS registry
    prof_id = getattr(char, "profession_id", None)
    display["profession_id"] = prof_id
    if prof_id:
        try:
            from world.data.professions import PROFESSIONS
            prof_def = PROFESSIONS.get(prof_id, {})
            display["profession"] = prof_def.get("name", prof_id)
        except Exception:
            display["profession"] = prof_id
    else:
        display["profession"] = None

    # Faction (authoritative internal identifiers preserved)
    faction = getattr(char, "faction", None)
    if faction is not None:
        try:
            faction_value = faction.value
            display["faction"] = faction_value
            display["faction_label"] = "Valroian" if faction_value == "good" else "Mordrath"
        except Exception:
            display["faction"] = str(faction)
            display["faction_label"] = str(faction)
    else:
        display["faction"] = None
        display["faction_label"] = None

    # --- Affiliations ---
    try:
        display["guild_id"] = char.guild_id if game else None
    except Exception:
        display["guild_id"] = None
    try:
        display["sect_id"] = char.sect_id if game else None
    except Exception:
        display["sect_id"] = None

    # --- Progression ---
    display["xp"] = getattr(char, "xp", None)
    display["tutorial_completed"] = getattr(char, "tutorial_completed", False)
    display["state"] = None
    if game is not None:
        try:
            state = game.state
            display["state"] = state.value if state else None
        except Exception:
            pass

    # --- Stats ---
    display["base_stats"] = None
    if game is not None:
        try:
            display["base_stats"] = dict(game.base_stats)
        except Exception:
            pass

    # --- Resources ---
    display["hp"] = getattr(char, "hp", None)
    display["max_hp"] = getattr(char, "max_hp", None)
    display["mana"] = getattr(char, "mana", None)
    display["max_mana"] = getattr(char, "max_mana", None)
    display["stamina"] = getattr(char, "stamina", None)
    display["max_stamina"] = getattr(char, "max_stamina", None)

    # --- PvP ---
    display["war_points"] = getattr(char, "war_points", None)
    display["pvp_kills"] = getattr(char, "pvp_kills", None)
    display["pvp_deaths"] = getattr(char, "pvp_deaths", None)

    # --- Skills / Proficiencies ---
    display["unlocked_skills"] = None
    display["proficiencies"] = None
    if game is not None:
        try:
            skills = getattr(game, "unlocked_skills", None)
            if skills:
                display["unlocked_skills"] = sorted(skills)
        except Exception:
            pass
        try:
            profs = getattr(game, "proficiencies", None)
            if profs:
                display["proficiencies"] = dict(profs)
        except Exception:
            pass

    # --- Equipment ---
    display["equipment"] = None
    if game is not None:
        try:
            eq = getattr(game, "equipment", None)
            if eq:
                from world.data.enums import EquipmentSlot
                display["equipment"] = {
                    slot.value: eq.get(slot) for slot in EquipmentSlot
                }
        except Exception:
            pass

    return display


# ==========================================================================
# Views
# ==========================================================================


class ArmoryIndexView(TemplateView):
    """Armory character directory — login required.

    GET  /armory/         → alphabetical character list
    GET  /armory/?q=name  → filtered search
    """

    template_name = "website/portal/armory.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))
        ctx["page_title"] = "Armory"

        chars = _resolve_characters()
        query = self.request.GET.get("q", "").strip()

        if query:
            query_lower = query.lower()
            chars = [c for c in chars if query_lower in c.key.lower()]
            ctx["search_query"] = query

        ctx["characters"] = chars
        ctx["character_count"] = len(chars)
        ctx["total_count"] = len(_resolve_characters())

        # Attach race_image to each character for template use
        from web.website.views.portal import get_race_image
        for c in chars:
            c.race_image = get_race_image(getattr(c, "race_id", "") or "")

        return ctx


class ArmoryCharacterView(TemplateView):
    """Single-character Armory profile — login required.

    GET  /armory/<character-name>/  → character profile
    """

    template_name = "website/portal/armory_character.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(portal_context(self.request))

        char_name = self.kwargs.get("character_name", "")
        character = _resolve_character_by_name(char_name)
        if character is None:
            raise Http404("Character not found.")

        display = _build_armory_display(character)
        ctx["page_title"] = f"Armory — {display.get('name', 'Unknown')}"
        ctx["profile"] = display

        return ctx