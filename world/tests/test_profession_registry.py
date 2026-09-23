"""
Unit tests for the extensible Profession Registry.

Verifies:
- All 10 built-in professions are pre-seeded with correct IDs and names.
- register_profession() creates new custom entries.
- register_profession() updates name/description on existing entries without
  destroying unrelated fields.
- get_profession() raises KeyError for unknown IDs.
- profession_exists() returns True/False correctly.
"""

from world.data.professions import (
    PROFESSION_REGISTRY,
    register_profession,
    get_profession,
    profession_exists,
)


class TestProfessionRegistryBuiltin:
    """All 10 built-in professions must be pre-seeded."""

    def test_all_ten_builtin_professions_are_registered(self):
        expected = {
            "mage", "warlock", "warrior", "cleric", "thief",
            "templar", "monk", "alchemist", "ninja", "druid",
        }
        registered = set(PROFESSION_REGISTRY.keys())
        assert expected <= registered  # all built-ins present

    def test_builtin_professions_have_correct_name(self):
        assert PROFESSION_REGISTRY["mage"]["name"] == "Mage"
        assert PROFESSION_REGISTRY["warlock"]["name"] == "Warlock"
        assert PROFESSION_REGISTRY["warrior"]["name"] == "Warrior"
        assert PROFESSION_REGISTRY["cleric"]["name"] == "Cleric"
        assert PROFESSION_REGISTRY["thief"]["name"] == "Thief"
        assert PROFESSION_REGISTRY["templar"]["name"] == "Templar"
        assert PROFESSION_REGISTRY["monk"]["name"] == "Monk"
        assert PROFESSION_REGISTRY["alchemist"]["name"] == "Alchemist"
        assert PROFESSION_REGISTRY["ninja"]["name"] == "Ninja"
        assert PROFESSION_REGISTRY["druid"]["name"] == "Druid"

    def test_builtin_profession_id_field_matches_key(self):
        for prof_id, entry in PROFESSION_REGISTRY.items():
            assert entry["id"] == prof_id


class TestRegisterProfession:
    """register_profession() create / update behaviour."""

    def test_register_creates_new_custom_profession(self):
        assert "pyromancer" not in PROFESSION_REGISTRY

        register_profession("pyromancer", "Pyromancer", "Master of flame")
        assert "pyromancer" in PROFESSION_REGISTRY

        entry = PROFESSION_REGISTRY["pyromancer"]
        assert entry["id"] == "pyromancer"
        assert entry["name"] == "Pyromancer"
        assert entry["description"] == "Master of flame"

    def test_register_updates_existing_name_description(self):
        register_profession("mage", "Archmage", "A master of the arcane")

        entry = PROFESSION_REGISTRY["mage"]
        assert entry["name"] == "Archmage"
        assert entry["description"] == "A master of the arcane"
        assert entry["id"] == "mage"  # unchanged

    def test_register_preserves_unrelated_existing_fields(self):
        # Add a synthetic extra field, then update — field should survive.
        PROFESSION_REGISTRY["mage"]["bonus_field"] = 42

        register_profession("mage", "Mage", "Updated desc")

        assert PROFESSION_REGISTRY["mage"]["bonus_field"] == 42

    def test_register_with_empty_description(self):
        register_profession("frost_warden", "Frost Warden")
        entry = PROFESSION_REGISTRY["frost_warden"]
        assert entry["name"] == "Frost Warden"
        assert entry["description"] == ""


class TestGetProfession:
    """get_profession() raises KeyError for unknowns."""

    def test_get_known_profession_returns_dict(self):
        entry = get_profession("warrior")
        assert isinstance(entry, dict)
        assert entry["id"] == "warrior"
        assert entry["name"] == "Warrior"

    def test_get_unknown_profession_raises_keyerror(self):
        try:
            get_profession("battle_mage")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError for unknown profession")


class TestProfessionExists:
    """profession_exists() returns True/False."""

    def test_exists_for_builtin(self):
        assert profession_exists("mage") is True
        assert profession_exists("cleric") is True

    def test_not_exists_for_unknown(self):
        assert profession_exists("void_knight") is False

    def test_exists_after_register(self):
        assert profession_exists("void_knight") is False
        register_profession("void_knight", "Void Knight")
        assert profession_exists("void_knight") is True