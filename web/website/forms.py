"""ROP Website Forms."""

from django import forms
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm

from .naming import (
    validate_name_format,
    is_name_reserved,
    validate_name_unique_account,
    validate_name_unique_character,
    MIN_LENGTH,
    MAX_LENGTH,
)


class ROPAccountCreationForm(forms.Form):
    """Custom registration form with ROP naming rules."""
    username = forms.CharField(min_length=MIN_LENGTH, max_length=MAX_LENGTH)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean_username(self):
        u = self.cleaned_data.get("username", "").strip()
        for e in validate_name_format(u):
            raise forms.ValidationError(e)
        reserved, reason = is_name_reserved(u)
        if reserved:
            raise forms.ValidationError(reason)
        for e in validate_name_unique_account(u):
            raise forms.ValidationError(e)
        return u

    def clean(self):
        c = super().clean()
        if c.get("password1") != c.get("password2"):
            raise forms.ValidationError({"password2": "Passwords do not match."})
        return c


class ROPPasswordResetForm(DjangoPasswordResetForm):
    """Password reset form."""
    email = forms.EmailField(label="Email", max_length=254)


class ROPAccountEmailForm(forms.Form):
    """Change account email."""
    email = forms.EmailField(required=True)


class ROPAccountPasswordForm(forms.Form):
    """Change account password."""
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password1 = forms.CharField(widget=forms.PasswordInput, label="New Password")
    new_password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm New Password")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        cur = self.cleaned_data.get("current_password")
        if not self.user.check_password(cur):
            raise forms.ValidationError("Current password is incorrect.")
        return cur

    def clean(self):
        c = super().clean()
        if c.get("new_password1") != c.get("new_password2"):
            raise forms.ValidationError({"new_password2": "Passwords do not match."})
        return c


class CharacterFactionForm(forms.Form):
    """Faction selection."""
    faction = forms.ChoiceField(choices=[], widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faction"].choices = [("good", "Good"), ("evil", "Evil")]


class CharacterRaceForm(forms.Form):
    """Race selection."""
    faction = forms.CharField(widget=forms.HiddenInput)
    race = forms.ChoiceField(choices=[], widget=forms.HiddenInput)

    def set_races(self, races):
        self.fields["race"].choices = races

    def clean_race(self):
        from world.data.races import RACES
        race = self.cleaned_data.get("race")
        faction = self.cleaned_data.get("faction")
        if race not in RACES:
            raise forms.ValidationError("Invalid race.")
        if RACES[race]["faction"].value != faction:
            raise forms.ValidationError("Invalid race for this faction.")
        return race


class CharacterProfessionForm(forms.Form):
    """Profession selection."""
    faction = forms.CharField(widget=forms.HiddenInput)
    race = forms.CharField(widget=forms.HiddenInput)
    profession = forms.ChoiceField(choices=[], widget=forms.HiddenInput)

    def set_professions(self, professions):
        self.fields["profession"].choices = professions

    def clean_profession(self):
        from world.data.professions import PROFESSIONS
        prof = self.cleaned_data.get("profession")
        if prof not in PROFESSIONS:
            raise forms.ValidationError("Invalid profession.")
        return prof

class CharacterStatsForm(forms.Form):
    """Stats review during chargen."""
    faction = forms.CharField(widget=forms.HiddenInput)
    race = forms.CharField(widget=forms.HiddenInput)
    profession = forms.CharField(widget=forms.HiddenInput)


class CharacterFinalForm(forms.Form):
    """Final review and confirmation step."""
    faction = forms.CharField(widget=forms.HiddenInput)
    race = forms.CharField(widget=forms.HiddenInput)
    profession = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(min_length=MIN_LENGTH, max_length=MAX_LENGTH)
    confirm = forms.BooleanField(
        required=True,
        label=(
            "I confirm that name, faction, race, profession, "
            "and stats are PERMANENT and cannot be changed."
        ),
    )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        for e in validate_name_format(name):
            raise forms.ValidationError(e)
        reserved, reason = is_name_reserved(name)
        if reserved:
            raise forms.ValidationError(reason)
        for e in validate_name_unique_character(name):
            raise forms.ValidationError(e)
        return name


class CharacterDeletionForm(forms.Form):
    """Type character name to confirm permanent deletion."""
    confirmation = forms.CharField(
        label="Type your character name to confirm permanent deletion:"
    )

    def __init__(self, character, *args, **kwargs):
        self.character = character
        super().__init__(*args, **kwargs)

    def clean_confirmation(self):
        inp = self.cleaned_data.get("confirmation", "").strip()
        if inp != self.character.key:
            raise forms.ValidationError("Confirmation does not match character name.")
        return inp


class AccountDeletionForm(forms.Form):
    """Type username to confirm permanent account deletion."""
    confirmation = forms.CharField(
        label="Type your username to confirm permanent account deletion:"
    )

    def __init__(self, account, *args, **kwargs):
        self.account = account
        super().__init__(*args, **kwargs)

    def clean_confirmation(self):
        inp = self.cleaned_data.get("confirmation", "").strip()
        if inp != self.account.username:
            raise forms.ValidationError("Confirmation does not match account name.")
        return inp


class BanCreationForm(forms.Form):
    """Superuser ban creation."""
    account_name = forms.CharField(label="Account name")
    reason = forms.CharField(widget=forms.Textarea, label="Ban reason")


class ArmorySearchForm(forms.Form):
    """Simple armory character search."""
    query = forms.CharField(required=False, label="Search characters")