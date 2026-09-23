"""ROP Character Creation — multi-step wizard (Phase 5).

Steps:
  1. Name
  2. Faction   (player explicitly chooses Valroian or Mordrath)
  3. Race       (filtered by selected faction)
  4. Profession
  5. Stats / Rerolls  (max 3 total stat sets)
  6. Final Review & Create
"""

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from ..naming import (
    validate_name_format,
    is_name_reserved,
    validate_name_unique_character,
)
from .portal import account_has_character, portal_context, get_race_image, get_profession_image


class ChargenNameForm(forms.Form):
    """Character name entry."""
    name = forms.CharField(
        min_length=3,
        max_length=14,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter character name",
            "class": "rop-input",
            "autofocus": True,
        }),
    )


class CharGenView(View):
    """Multi-step character-creation wizard.

    Temporary wizard state is stored in ``request.session`` under the
    ``chargen_`` prefix and cleared on successful creation or abandonment.

    Authoritative flow:  name → faction → race → profession → stats → review
    """

    STEPS = ("name", "faction", "race", "profession", "stats", "review")
    MAX_ROLLS = 3          # total stat sets the player may ever see
    SESSION_PREFIX = "chargen_"

    # ------------------------------------------------------------------
    # Dispatch / auth guards
    # ------------------------------------------------------------------

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy("rop-login"))
        if account_has_character(request.user):
            messages.info(request, "You already have a character.")
            return redirect(reverse_lazy("rop-dashboard"))
        step = request.session.get(f"{self.SESSION_PREFIX}step", "name")
        if step not in self.STEPS:
            # Corrupted or stale session — clear all chargen state and restart
            self._clear_session(request)
            step = "name"
            request.session[f"{self.SESSION_PREFIX}step"] = step
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        step = self._current_step(request)
        ctx = self._build_context(request, step)
        if ctx.get("_redirect_to_faction"):
            messages.error(request, "You must select a faction first.")
            return redirect(reverse_lazy("rop-chargen"))
        return render(request, f"website/portal/chargen/{step}.html", ctx)

    def post(self, request, *args, **kwargs):
        step = self._current_step(request)
        handler = getattr(self, f"_handle_{step}", None)
        if handler is None:
            messages.error(request, "Invalid chargen step.")
            return redirect(reverse_lazy("rop-chargen"))
        return handler(request)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_step(self, request):
        step = request.session.get(f"{self.SESSION_PREFIX}step", "")
        if not step or step not in self.STEPS:
            step = "name"
            request.session[f"{self.SESSION_PREFIX}step"] = step
        return step

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    def _build_context(self, request, step):
        ctx = portal_context(request)
        ctx["page_title"] = "Character Creation"
        ctx["chargen_step"] = step
        ctx["chargen_steps"] = self.STEPS
        session = request.session
        ctx["chargen_name"] = session.get(f"{self.SESSION_PREFIX}name", "")
        ctx["chargen_faction"] = session.get(f"{self.SESSION_PREFIX}faction", "")

        # Faction step needs faction image paths
        if step == "faction":
            ctx["faction_good_image"] = "faction-good.webp"
            ctx["faction_evil_image"] = "faction-evil.webp"
            ctx["faction_good_emblem"] = "faction-good-emblem.webp"
            ctx["faction_evil_emblem"] = "faction-evil-emblem.webp"

        # Race data — filtered by selected faction
        if step in ("race", "profession", "stats", "review"):
            from world.data.races import RACES
            from world.data.enums import Faction
            sel_faction = session.get(f"{self.SESSION_PREFIX}faction", "")
            # Guard: if we are on the race page but have no faction,
            # redirect back to the faction step (GET safety).
            if step == "race" and not sel_faction:
                session[f"{self.SESSION_PREFIX}step"] = "faction"
                # (The caller must handle the redirect; we signal via ctx)
                ctx["_redirect_to_faction"] = True
                return ctx
            filtered = {}
            all_races = {}
            for rid, rdef in RACES.items():
                rdef_copy = dict(rdef)
                rdef_copy["image"] = get_race_image(rid)
                all_races[rid] = rdef_copy
                if sel_faction:
                    faction_val = rdef["faction"]
                    if (sel_faction == Faction.GOOD.value and faction_val == Faction.GOOD) or \
                       (sel_faction == Faction.EVIL.value and faction_val == Faction.EVIL):
                        filtered[rid] = rdef_copy
            ctx["available_races"] = filtered
            ctx["all_races"] = all_races
            ctx["chargen_race"] = session.get(f"{self.SESSION_PREFIX}race", "")

        # Profession data
        if step in ("profession", "stats", "review"):
            from world.data.professions import PROFESSIONS
            profs_copy = {}
            for pid, pdef in PROFESSIONS.items():
                pdef_copy = dict(pdef)
                pdef_copy["image"] = get_profession_image(pid)
                profs_copy[pid] = pdef_copy
            ctx["professions"] = profs_copy
            ctx["chargen_profession"] = session.get(
                f"{self.SESSION_PREFIX}profession", ""
            )

        # Stats data
        ctx["chargen_stats"] = session.get(f"{self.SESSION_PREFIX}stats", {})
        roll_num = session.get(f"{self.SESSION_PREFIX}rolls", 1)
        ctx["chargen_roll_number"] = roll_num
        ctx["max_rolls"] = self.MAX_ROLLS

        if step == "review":
            self._build_review_context(ctx, request)
        return ctx

    def _build_review_context(self, ctx, request):
        session = request.session
        race_id = session.get(f"{self.SESSION_PREFIX}race", "")
        prof_id = session.get(f"{self.SESSION_PREFIX}profession", "")
        faction = session.get(f"{self.SESSION_PREFIX}faction", "")
        if race_id:
            try:
                from world.data.races import RACES
                from world.data.enums import Faction
                rdef = RACES.get(race_id, {})
                ctx["race_display"] = {
                    "id": race_id,
                    "name": rdef.get("name", race_id),
                    "faction": faction,
                    "faction_label": (
                        "Valroian" if faction == Faction.GOOD.value
                        else "Mordrath" if faction == Faction.EVIL.value
                        else "\u2014"  # em-dash when faction is missing
                    ),
                    "traits": rdef.get("traits", []),
                    "image": get_race_image(race_id),
                }
            except Exception:
                ctx["race_display"] = {"id": race_id, "name": race_id}
        if prof_id:
            try:
                from world.data.professions import PROFESSIONS
                pdef = PROFESSIONS.get(prof_id, {})
                ctx["profession_display"] = {
                    "id": prof_id,
                    "name": pdef.get("name", prof_id),
                }
            except Exception:
                ctx["profession_display"] = {"id": prof_id, "name": prof_id}
        ctx["stat_labels"] = {
            "str": "Strength", "int": "Intelligence", "wis": "Wisdom",
            "dex": "Dexterity", "con": "Constitution",
        }

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------

    def _handle_name(self, request):
        name = request.POST.get("name", "").strip()
        fmt_errors = validate_name_format(name)
        if fmt_errors:
            for e in fmt_errors:
                messages.error(request, e)
            return redirect(reverse_lazy("rop-chargen"))
        reserved, reason = is_name_reserved(name)
        if reserved:
            messages.error(request, reason)
            return redirect(reverse_lazy("rop-chargen"))
        char_errors = validate_name_unique_character(name)
        if char_errors:
            for e in char_errors:
                messages.error(request, e)
            return redirect(reverse_lazy("rop-chargen"))
        request.session[f"{self.SESSION_PREFIX}name"] = name
        request.session[f"{self.SESSION_PREFIX}step"] = "faction"
        return redirect(reverse_lazy("rop-chargen"))

    def _handle_faction(self, request):
        faction = request.POST.get("faction", "").strip()
        from world.data.enums import Faction
        valid_factions = {Faction.GOOD.value, Faction.EVIL.value}
        if faction not in valid_factions:
            messages.error(request, "Please select a valid faction.")
            return redirect(reverse_lazy("rop-chargen"))
        request.session[f"{self.SESSION_PREFIX}faction"] = faction
        request.session[f"{self.SESSION_PREFIX}step"] = "race"
        return redirect(reverse_lazy("rop-chargen"))

    def _handle_race(self, request):
        faction = request.session.get(f"{self.SESSION_PREFIX}faction", "")
        if not faction:
            messages.error(request, "You must select a faction first.")
            request.session[f"{self.SESSION_PREFIX}step"] = "faction"
            return redirect(reverse_lazy("rop-chargen"))
        race_id = request.POST.get("race", "").strip()
        from world.data.races import RACES
        from world.data.enums import Faction
        if race_id not in RACES:
            messages.error(request, "Invalid race selection.")
            return redirect(reverse_lazy("rop-chargen"))
        race_faction = RACES[race_id]["faction"]
        if (faction == Faction.GOOD.value and race_faction != Faction.GOOD) or \
           (faction == Faction.EVIL.value and race_faction != Faction.EVIL):
            messages.error(
                request, "That race does not belong to your chosen faction."
            )
            return redirect(reverse_lazy("rop-chargen"))
        request.session[f"{self.SESSION_PREFIX}race"] = race_id
        request.session[f"{self.SESSION_PREFIX}step"] = "profession"
        return redirect(reverse_lazy("rop-chargen"))

    def _handle_profession(self, request):
        # Guard: require prior steps
        session = request.session
        if not session.get(f"{self.SESSION_PREFIX}faction"):
            messages.error(request, "Please complete the previous steps first.")
            session[f"{self.SESSION_PREFIX}step"] = "faction"
            return redirect(reverse_lazy("rop-chargen"))
        if not session.get(f"{self.SESSION_PREFIX}race"):
            messages.error(request, "Please select a race first.")
            session[f"{self.SESSION_PREFIX}step"] = "race"
            return redirect(reverse_lazy("rop-chargen"))
        prof_id = request.POST.get("profession", "").strip()
        from world.data.professions import PROFESSIONS
        if prof_id not in PROFESSIONS:
            messages.error(request, "Invalid profession selection.")
            return redirect(reverse_lazy("rop-chargen"))
        session[f"{self.SESSION_PREFIX}profession"] = prof_id
        self._generate_stats(request)
        session[f"{self.SESSION_PREFIX}rolls"] = 1
        session[f"{self.SESSION_PREFIX}step"] = "stats"
        return redirect(reverse_lazy("rop-chargen"))

    def _generate_stats(self, request):
        """Roll stats using the authoritative ROP CharacterData method."""
        from world.data.races import RACES
        from world.data.character_data import CharacterData
        race_id = request.session.get(f"{self.SESSION_PREFIX}race", "")
        if not race_id or race_id not in RACES:
            raise ValueError("Cannot generate stats: race not selected or invalid")
        race_data = RACES[race_id]
        cd = CharacterData()
        cd._roll_stats(race_data)
        request.session[f"{self.SESSION_PREFIX}stats"] = dict(cd.base_stats)

    def _handle_stats(self, request):
        # Guard: require prior steps
        session = request.session
        if not session.get(f"{self.SESSION_PREFIX}faction"):
            messages.error(request, "Please complete the previous steps first.")
            session[f"{self.SESSION_PREFIX}step"] = "faction"
            return redirect(reverse_lazy("rop-chargen"))
        if not session.get(f"{self.SESSION_PREFIX}race"):
            messages.error(request, "Please select a race first.")
            session[f"{self.SESSION_PREFIX}step"] = "race"
            return redirect(reverse_lazy("rop-chargen"))
        if not session.get(f"{self.SESSION_PREFIX}profession"):
            messages.error(request, "Please select a profession first.")
            session[f"{self.SESSION_PREFIX}step"] = "profession"
            return redirect(reverse_lazy("rop-chargen"))
        action = request.POST.get("action", "").strip()
        if action == "reroll":
            roll_num = request.session.get(f"{self.SESSION_PREFIX}rolls", 1)
            if roll_num >= self.MAX_ROLLS:
                messages.error(
                    request, "No more rolls available (max %d total stat sets)."
                    % self.MAX_ROLLS
                )
            else:
                self._generate_stats(request)
                roll_num += 1
                request.session[f"{self.SESSION_PREFIX}rolls"] = roll_num
                if roll_num >= self.MAX_ROLLS:
                    messages.info(
                        request,
                        "Roll #%d of %d — FINAL. You must use these stats."
                        % (roll_num, self.MAX_ROLLS),
                    )
                else:
                    messages.success(
                        request,
                        "Roll #%d of %d. %d roll(s) remaining."
                        % (
                            roll_num, self.MAX_ROLLS,
                            self.MAX_ROLLS - roll_num,
                        ),
                    )
            return redirect(reverse_lazy("rop-chargen"))
        if action == "accept":
            request.session[f"{self.SESSION_PREFIX}step"] = "review"
            return redirect(reverse_lazy("rop-chargen"))
        messages.error(request, "Invalid action.")
        return redirect(reverse_lazy("rop-chargen"))

    def _handle_review(self, request):
        # Cancel / Start Over
        if request.POST.get("cancel") == "1":
            self._clear_session(request)
            messages.info(request, "Character creation progress has been cleared. Start anew.")
            return redirect(reverse_lazy("rop-chargen"))

        session = request.session
        name = session.get(f"{self.SESSION_PREFIX}name", "")
        faction = session.get(f"{self.SESSION_PREFIX}faction", "")
        race_id = session.get(f"{self.SESSION_PREFIX}race", "")
        prof_id = session.get(f"{self.SESSION_PREFIX}profession", "")
        stats = session.get(f"{self.SESSION_PREFIX}stats", {})
        if account_has_character(request.user):
            self._clear_session(request)
            messages.error(request, "You already have a character.")
            return redirect(reverse_lazy("rop-dashboard"))
        err = self._validate_final(request, name, faction, race_id, prof_id, stats)
        if err:
            return err
        char = None
        try:
            from evennia.accounts.models import AccountDB
            account = AccountDB.objects.get(id=request.user.id)
            char, errs = account.create_character(key=name)
            if not char:
                msg = errs[0] if errs else "Character creation failed."
                messages.error(request, msg)
                return redirect(reverse_lazy("rop-chargen"))
            if errs:
                # Evennia reported errors during creation — the character
                # may exist but be unusable.  Clean it up so the player
                # can retry without hitting the one-character guard.
                try:
                    char.delete()
                except Exception:
                    pass
                msg = errs[0] if errs else "Character creation failed."
                messages.error(request, msg)
                return redirect(reverse_lazy("rop-chargen"))
            char.init_character(race_id, prof_id)
            char.game.base_stats = dict(stats)
            # Store faction on CharacterData
            from world.data.enums import Faction as FactionEnum
            if faction == FactionEnum.GOOD.value:
                char.game.faction = FactionEnum.GOOD
            elif faction == FactionEnum.EVIL.value:
                char.game.faction = FactionEnum.EVIL
            else:
                # Should be unreachable after validation, but never silently default
                raise ValueError("Invalid faction value: %s" % faction)
            char.save()
            self._clear_session(request)
            messages.success(
                request,
                "Character '%s' has been forged. Welcome to Rites of Passage!"
                % name,
            )
            return redirect(reverse_lazy("rop-dashboard"))
        except Exception as exc:
            # Delete any partially-created character so the player can retry.
            if char is not None:
                try:
                    char.delete()
                except Exception:
                    pass
            messages.error(
                request,
                "An error occurred during character creation: %s" % exc,
            )
            return redirect(reverse_lazy("rop-chargen"))

    def _validate_final(self, request, name, faction, race_id, prof_id, stats):
        from world.data.enums import Faction as FactionEnum
        from world.data.races import RACES
        from world.data.professions import PROFESSIONS
        fmt_errors = validate_name_format(name)
        if fmt_errors or not name:
            messages.error(
                request, fmt_errors[0] if fmt_errors else "Name required."
            )
            return redirect(reverse_lazy("rop-chargen"))
        reserved, reason = is_name_reserved(name)
        if reserved:
            messages.error(request, reason)
            return redirect(reverse_lazy("rop-chargen"))
        char_errs = validate_name_unique_character(name)
        if char_errs:
            messages.error(request, char_errs[0])
            return redirect(reverse_lazy("rop-chargen"))
        valid_factions = {FactionEnum.GOOD.value, FactionEnum.EVIL.value}
        if faction not in valid_factions:
            messages.error(request, "Invalid faction.")
            return redirect(reverse_lazy("rop-chargen"))
        if race_id not in RACES:
            messages.error(request, "Invalid race.")
            return redirect(reverse_lazy("rop-chargen"))
        race_faction = RACES[race_id]["faction"]
        if (faction == FactionEnum.GOOD.value and race_faction != FactionEnum.GOOD) or \
           (faction == FactionEnum.EVIL.value and race_faction != FactionEnum.EVIL):
            messages.error(request, "Race does not belong to selected faction.")
            return redirect(reverse_lazy("rop-chargen"))
        if prof_id not in PROFESSIONS:
            messages.error(request, "Invalid profession.")
            return redirect(reverse_lazy("rop-chargen"))
        expected_keys = {"str", "int", "wis", "dex", "con"}
        if not stats or set(stats.keys()) != expected_keys:
            messages.error(request, "Stats have not been generated.")
            return redirect(reverse_lazy("rop-chargen"))
        return None

    def _clear_session(self, request):
        for key in (
            "name", "faction", "race", "profession", "stats", "rolls", "step",
        ):
            request.session.pop(f"{self.SESSION_PREFIX}{key}", None)
