"""
Phase 7 — Item & Equipment Foundation Tests

Tests item definitions, categories, inventory management, equipment
slots, equip/unequip, validation, stack quantities, persistence
round-trip, JSON safety, and regression against Phases 2–6.
"""

import json
import unittest

from world.data.character_data import CharacterData
from world.data.enums import (
    CharacterState,
    EquipmentSlot,
    DamageType,
)
from world.data import items as _items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Test", race="human", prof="warrior"):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100; cd.hp = 100
    cd.max_mana = 100; cd.mana = 100
    cd.max_stamina = 100; cd.stamina = 100
    return cd


# ---------------------------------------------------------------------------
# Item Registry & Definitions
# ---------------------------------------------------------------------------


class TestItemRegistry(unittest.TestCase):
    """Item definitions and registry operations."""

    def test_placeholder_items_exist(self):
        self.assertIn("rusty_sword", _items.ITEM_REGISTRY)
        self.assertIn("cloth_vest", _items.ITEM_REGISTRY)
        self.assertIn("health_potion", _items.ITEM_REGISTRY)

    def test_get_item_returns_definition(self):
        definition = _items.get_item("rusty_sword")
        self.assertIsInstance(definition, dict)
        self.assertEqual(definition["item_id"], "rusty_sword")
        self.assertEqual(definition["category"], "weapon")

    def test_get_item_unknown_returns_none(self):
        self.assertIsNone(_items.get_item("nonexistent_item"))

    def test_item_exists(self):
        self.assertTrue(_items.item_exists("rusty_sword"))
        self.assertFalse(_items.item_exists("not_real"))


# ---------------------------------------------------------------------------
# Item Categories
# ---------------------------------------------------------------------------


class TestItemCategories(unittest.TestCase):
    """Category constants and classifications."""

    def test_all_placeholder_items_have_valid_category(self):
        for item_id, definition in _items.ITEM_REGISTRY.items():
            self.assertIn(
                definition["category"],
                _items.ITEM_CATEGORIES,
                f"{item_id}: invalid category '{definition['category']}'",
            )

    def test_weapons_have_damage_type(self):
        sword = _items.get_item("rusty_sword")
        self.assertIn("damage_type", sword)
        self.assertIn("base_damage", sword)

    def test_armor_has_armor_class(self):
        vest = _items.get_item("cloth_vest")
        self.assertIn("armor_class", vest)

    def test_consumables_are_stackable(self):
        potion = _items.get_item("health_potion")
        self.assertTrue(potion["stackable"])

    def test_quest_items_may_be_nonstackable(self):
        letter = _items.get_item("old_letter")
        self.assertFalse(letter["stackable"])


# ---------------------------------------------------------------------------
# Equipment Slots
# ---------------------------------------------------------------------------


class TestEquipmentSlots(unittest.TestCase):
    """EquipmentSlot enum integrity."""

    def test_all_slots_have_category_mapping(self):
        for slot in EquipmentSlot:
            self.assertIn(slot, _items.SLOT_CATEGORIES)
            self.assertIsInstance(_items.SLOT_CATEGORIES[slot], (set, frozenset))

    def test_main_hand_accepts_weapons(self):
        self.assertIn("weapon", _items.SLOT_CATEGORIES[EquipmentSlot.MAIN_HAND])

    def test_chest_accepts_armor(self):
        self.assertIn("armor", _items.SLOT_CATEGORIES[EquipmentSlot.CHEST])

    def test_all_weapons_have_valid_slots(self):
        for item_id, definition in _items.ITEM_REGISTRY.items():
            if definition["category"] == "weapon":
                slot_val = definition.get("slot")
                self.assertIsNotNone(slot_val,
                                     f"Weapon {item_id} missing slot")
                slot = EquipmentSlot(slot_val)
                permitted = _items.SLOT_CATEGORIES.get(slot, set())
                self.assertIn("weapon", permitted,
                              f"Weapon {item_id} slot {slot_val} not a weapon slot")


# ---------------------------------------------------------------------------
# Inventory Management
# ---------------------------------------------------------------------------


class TestInventoryAdd(unittest.TestCase):
    """Adding items to inventory."""

    def test_add_valid_item_returns_one(self):
        cd = _make_cd()
        added = cd.add_item("rusty_sword")
        self.assertEqual(added, 1)
        self.assertEqual(cd.inventory.get("rusty_sword"), 1)

    def test_add_unknown_item_returns_zero(self):
        cd = _make_cd()
        added = cd.add_item("not_real")
        self.assertEqual(added, 0)

    def test_add_zero_quantity_returns_zero(self):
        cd = _make_cd()
        self.assertEqual(cd.add_item("rusty_sword", 0), 0)

    def test_add_negative_quantity_returns_zero(self):
        cd = _make_cd()
        self.assertEqual(cd.add_item("rusty_sword", -5), 0)

    def test_nonstackable_cannot_exceed_one(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        added = cd.add_item("rusty_sword")
        self.assertEqual(added, 0)
        self.assertEqual(cd.inventory.get("rusty_sword"), 1)

    def test_stackable_items_accumulate(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        cd.add_item("health_potion", 3)
        self.assertEqual(cd.inventory.get("health_potion"), 8)

    def test_stackable_respects_max_stack(self):
        cd = _make_cd()
        added = cd.add_item("wooden_plank", 60)
        self.assertEqual(added, 50)
        self.assertEqual(cd.inventory.get("wooden_plank"), 50)

    def test_add_multiple_nonstackable_only_first_succeeds(self):
        cd = _make_cd()
        added = cd.add_item("old_letter", 5)
        self.assertEqual(added, 1)
        self.assertEqual(cd.inventory.get("old_letter"), 1)


class TestInventoryRemove(unittest.TestCase):
    """Removing items from inventory."""

    def test_remove_existing_item(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        removed = cd.remove_item("health_potion", 2)
        self.assertEqual(removed, 2)
        self.assertEqual(cd.inventory.get("health_potion"), 3)

    def test_remove_more_than_owned(self):
        cd = _make_cd()
        cd.add_item("health_potion", 3)
        removed = cd.remove_item("health_potion", 10)
        self.assertEqual(removed, 3)
        self.assertFalse("health_potion" in cd.inventory)

    def test_remove_zero_returns_zero(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        self.assertEqual(cd.remove_item("health_potion", 0), 0)

    def test_remove_negative_returns_zero(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        self.assertEqual(cd.remove_item("health_potion", -1), 0)

    def test_remove_missing_item_returns_zero(self):
        cd = _make_cd()
        self.assertEqual(cd.remove_item("nonexistent"), 0)

    def test_remove_clears_entry_when_empty(self):
        cd = _make_cd()
        cd.add_item("health_potion", 1)
        cd.remove_item("health_potion", 1)
        self.assertNotIn("health_potion", cd.inventory)

    def test_remove_does_not_affect_equipped(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        # Sword moved to equipment; inventory should be empty for it.
        self.assertEqual(cd.get_item_qty("rusty_sword"), 0)
        self.assertTrue(cd.has_item("rusty_sword"))  # still has via equip


# ---------------------------------------------------------------------------
# Equipment — Equip / Unequip
# ---------------------------------------------------------------------------


class TestEquipUnequip(unittest.TestCase):
    """Equipping and unequipping items."""

    def test_equip_weapon_to_main_hand(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        error = cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNone(error)
        self.assertEqual(cd.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword")

    def test_equip_unknown_item_fails(self):
        cd = _make_cd()
        error = cd.equip("fake_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_equip_unowned_item_fails(self):
        cd = _make_cd()
        error = cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_equip_wrong_slot_fails(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        error = cd.equip("rusty_sword", EquipmentSlot.CHEST)
        self.assertIsNotNone(error)

    def test_equip_non_equippable_fails(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        error = cd.equip("health_potion", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_unequip_removes_from_slot(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        error = cd.unequip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNone(error)
        self.assertIsNone(cd.equipment[EquipmentSlot.MAIN_HAND])

    def test_unequip_returns_to_inventory(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.unequip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.get_item_qty("rusty_sword"), 1)

    def test_unequip_wrong_slot_fails(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        error = cd.unequip("rusty_sword", EquipmentSlot.CHEST)
        self.assertIsNotNone(error)
        self.assertEqual(
            cd.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword",
        )

    def test_unequip_nonexistent_fails(self):
        cd = _make_cd()
        error = cd.unequip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_reequip_swaps_items(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.add_item("short_bow")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.equip("short_bow", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.equipment[EquipmentSlot.MAIN_HAND], "short_bow")
        # Old item returns to inventory
        self.assertEqual(cd.get_item_qty("rusty_sword"), 1)

    def test_equip_already_equipped_noop(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        # Re-equip same item in same slot — should be fine
        error = cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNone(error)

    def test_equip_armor_to_chest(self):
        cd = _make_cd()
        cd.add_item("cloth_vest")
        error = cd.equip("cloth_vest", EquipmentSlot.CHEST)
        self.assertIsNone(error)
        self.assertEqual(cd.equipment[EquipmentSlot.CHEST], "cloth_vest")

    def test_get_equipment(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.get_equipment(EquipmentSlot.MAIN_HAND), "rusty_sword")
        self.assertIsNone(cd.get_equipment(EquipmentSlot.CHEST))

    def test_unequip_without_slot_finds_item(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        error = cd.unequip("rusty_sword")  # no slot specified
        self.assertIsNone(error)
        self.assertIsNone(cd.equipment[EquipmentSlot.MAIN_HAND])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestEquipmentValidation(unittest.TestCase):
    """Validation guards."""

    def test_validate_equip_unknown_item(self):
        err = _items.validate_equip(
            "nope", EquipmentSlot.MAIN_HAND, {}, {})
        self.assertIsNotNone(err)

    def test_validate_equip_not_equippable(self):
        err = _items.validate_equip(
            "health_potion", EquipmentSlot.MAIN_HAND,
            {s: None for s in EquipmentSlot}, {})
        self.assertIsNotNone(err)

    def test_validate_equip_wrong_slot(self):
        err = _items.validate_equip(
            "rusty_sword", EquipmentSlot.CHEST,
            {s: None for s in EquipmentSlot},
            {"rusty_sword": 1})
        self.assertIsNotNone(err)

    def test_validate_equip_not_owned(self):
        err = _items.validate_equip(
            "rusty_sword", EquipmentSlot.MAIN_HAND,
            {s: None for s in EquipmentSlot}, {})
        self.assertIsNotNone(err)

    def test_validate_equip_owned_in_equipment(self):
        equipment = {s: None for s in EquipmentSlot}
        equipment[EquipmentSlot.MAIN_HAND] = "rusty_sword"
        err = _items.validate_equip(
            "rusty_sword", EquipmentSlot.MAIN_HAND, equipment, {})
        self.assertIsNone(err)  # already equipped

    def test_validate_equip_valid(self):
        equipment = {s: None for s in EquipmentSlot}
        err = _items.validate_equip(
            "rusty_sword", EquipmentSlot.MAIN_HAND,
            equipment, {"rusty_sword": 1})
        self.assertIsNone(err)


# ---------------------------------------------------------------------------
# Weapon / Armor Stat Accessors
# ---------------------------------------------------------------------------


class TestStatAccessors(unittest.TestCase):
    """Weapon/armor stat accessor functions."""

    def test_get_weapon_damage(self):
        self.assertEqual(_items.get_weapon_damage("rusty_sword"), 5)

    def test_get_weapon_damage_non_weapon(self):
        self.assertEqual(_items.get_weapon_damage("cloth_vest"), 0)

    def test_get_weapon_damage_unknown(self):
        self.assertEqual(_items.get_weapon_damage("nope"), 0)

    def test_get_weapon_damage_type(self):
        self.assertEqual(
            _items.get_weapon_damage_type("rusty_sword"),
            DamageType.SLASHING.value,
        )

    def test_get_weapon_damage_type_non_weapon(self):
        self.assertIsNone(_items.get_weapon_damage_type("cloth_vest"))

    def test_get_armor_class(self):
        self.assertEqual(_items.get_armor_class("cloth_vest"), 2)

    def test_get_armor_class_non_armor(self):
        self.assertEqual(_items.get_armor_class("rusty_sword"), 0)


# ---------------------------------------------------------------------------
# has_item / get_item_qty
# ---------------------------------------------------------------------------


class TestItemQuery(unittest.TestCase):
    """Inventory query methods."""

    def test_has_item_in_inventory(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        self.assertTrue(cd.has_item("rusty_sword"))

    def test_has_item_equipped(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertTrue(cd.has_item("rusty_sword"))

    def test_has_item_nonexistent(self):
        cd = _make_cd()
        self.assertFalse(cd.has_item("not_real"))

    def test_get_item_qty_inventory_only(self):
        cd = _make_cd()
        cd.add_item("health_potion", 7)
        self.assertEqual(cd.get_item_qty("health_potion"), 7)

    def test_get_item_qty_zero_for_missing(self):
        cd = _make_cd()
        self.assertEqual(cd.get_item_qty("nonexistent"), 0)


# ---------------------------------------------------------------------------
# Persistence — Serialization Round-Trip
# ---------------------------------------------------------------------------


class TestPersistence(unittest.TestCase):
    """Inventory/equipment survives to_dict/from_dict round-trip."""

    def test_empty_round_trip(self):
        cd = _make_cd()
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(cd2.inventory, {})
        for slot in EquipmentSlot:
            self.assertIsNone(cd2.equipment[slot])

    def test_inventory_round_trip(self):
        cd = _make_cd()
        cd.add_item("health_potion", 10)
        cd.add_item("rusty_sword")
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(cd2.inventory.get("health_potion"), 10)
        self.assertEqual(cd2.inventory.get("rusty_sword"), 1)

    def test_equipment_round_trip(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.add_item("cloth_vest")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.equip("cloth_vest", EquipmentSlot.CHEST)
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(
            cd2.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword",
        )
        self.assertEqual(
            cd2.equipment[EquipmentSlot.CHEST], "cloth_vest",
        )

    def test_full_round_trip_preserves_inventory_count(self):
        cd = _make_cd()
        cd.add_item("wooden_plank", 25)
        cd.add_item("health_potion", 7)
        cd.add_item("old_letter")
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(cd2.inventory.get("wooden_plank"), 25)
        self.assertEqual(cd2.inventory.get("health_potion"), 7)
        self.assertEqual(cd2.inventory.get("old_letter"), 1)
        self.assertEqual(cd2.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword")
        # Sword was moved to equipment; not in inventory
        self.assertEqual(cd2.inventory.get("rusty_sword", 0), 0)

    def test_to_dict_is_json_safe(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        data = cd.to_dict()
        dumped = json.dumps(data)
        restored = json.loads(dumped)
        cd2 = CharacterData.from_dict(restored)
        self.assertEqual(cd2.inventory.get("health_potion"), 5)
        self.assertEqual(
            cd2.equipment[EquipmentSlot.MAIN_HAND], "rusty_sword",
        )

    def test_equipment_slot_never_empty_after_roundtrip(self):
        """All 15 equipment slots must exist after from_dict, even if None."""
        cd = _make_cd()
        data = cd.to_dict()
        cd2 = CharacterData.from_dict(data)
        self.assertEqual(len(cd2.equipment), len(EquipmentSlot))
        for slot in EquipmentSlot:
            self.assertIn(slot, cd2.equipment)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases(unittest.TestCase):
    """Corner cases for inventory/equipment."""

    def test_all_slots_start_none(self):
        cd = _make_cd()
        for slot in EquipmentSlot:
            self.assertIsNone(cd.equipment[slot])

    def test_equip_after_equip_swaps_correctly(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.add_item("short_bow")
        cd.add_item("wooden_club")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.equip("short_bow", EquipmentSlot.OFF_HAND)
        cd.equip("wooden_club", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.equipment[EquipmentSlot.MAIN_HAND], "wooden_club")
        self.assertEqual(cd.equipment[EquipmentSlot.OFF_HAND], "short_bow")
        self.assertEqual(cd.get_item_qty("rusty_sword"), 1)

    def test_no_cross_contamination_between_characters(self):
        cd1 = _make_cd()
        cd2 = _make_cd()
        cd1.add_item("rusty_sword")
        cd1.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd2.get_item_qty("rusty_sword"), 0)
        self.assertIsNone(cd2.equipment[EquipmentSlot.MAIN_HAND])

    def test_equip_preserves_character_state(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        original_state = cd.state
        original_hp = cd.hp
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.state, original_state)
        self.assertEqual(cd.hp, original_hp)

    def test_no_dbref_strings_in_inventory(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        import json
        dumped = json.dumps(cd.to_dict())
        self.assertNotIn("#", dumped)
        self.assertNotIn("dbref", dumped.lower())

    def test_no_dbref_strings_in_equipment(self):
        cd = _make_cd()
        cd.add_item("cloth_vest")
        cd.equip("cloth_vest", EquipmentSlot.CHEST)
        import json
        dumped = json.dumps(cd.to_dict())
        self.assertNotIn("#", dumped)
        self.assertNotIn("dbref", dumped.lower())


# ---------------------------------------------------------------------------
# Regression — no Phase 5/6 breakage
# ---------------------------------------------------------------------------


class TestRegression(unittest.TestCase):
    """Phase 7 additions must not break existing systems."""

    def test_die_still_works(self):
        cd = _make_cd()
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)

    def test_respawn_restore_still_works(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        cd.die()
        cd.respawn_restore()
        self.assertEqual(cd.state, CharacterState.STANDING)
        self.assertGreater(cd.hp, 0)
        self.assertEqual(cd.inventory.get("health_potion"), 5)

    def test_regen_still_works(self):
        from world.data.regeneration import regen_tick
        cd = _make_cd()
        cd.hp = 50
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        result = regen_tick(cd)
        self.assertGreaterEqual(result["hp"], 0)

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        a.add_item("rusty_sword")
        a.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        result = resolve_attack(a, t)
        self.assertIn("valid", result)
        self.assertIn("hit", result)

    def test_xp_still_unchanged_by_items(self):
        cd = _make_cd()
        xp_before = cd.xp
        cd.add_item("rusty_sword")
        cd.add_item("health_potion", 10)
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.unequip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.xp, xp_before)

    def test_level_still_unchanged_by_items(self):
        cd = _make_cd()
        lvl_before = cd.level
        cd.add_item("rusty_sword")
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertEqual(cd.level, lvl_before)


# ---------------------------------------------------------------------------
# No Phase 8+ leakage
# ---------------------------------------------------------------------------


class TestNoPhase8Leakage(unittest.TestCase):
    """Phase 7 scope boundary enforcement."""

    def test_no_durability_in_items(self):
        for definition in _items.ITEM_REGISTRY.values():
            self.assertNotIn("durability", definition)

    def test_no_consumable_effect(self):
        for definition in _items.ITEM_REGISTRY.values():
            self.assertNotIn("effect", definition)
            self.assertNotIn("on_use", definition)

    def test_no_economy_in_items(self):
        import inspect
        src = inspect.getsource(_items)
        # Exclude comment/docstring lines — the docstring itself says "no shops".
        lines = [l for l in src.split("\n")
                 if not l.strip().startswith("#")
                 and '"""' not in l]
        body = "\n".join(lines).lower()
        for term in ["buy_price", "sell_price", "shop_item", "currency"]:
            self.assertNotIn(term, body,
                             f"Phase 7 must not implement economy: found {term}")

    def test_no_crafting_in_items(self):
        import inspect
        src = inspect.getsource(_items)
        lines = [l for l in src.split("\n")
                 if not l.strip().startswith("#")
                 and '"""' not in l]
        body = "\n".join(lines).lower()
        for term in ["craft_item", "recipe", "crafting_skill"]:
            self.assertNotIn(term, body,
                             f"Phase 7 must not implement crafting: found {term}")

    def test_no_loot_tables_in_items(self):
        import inspect
        src = inspect.getsource(_items).lower()
        self.assertNotIn("loot_table", src)
        self.assertNotIn("drop_rate", src)

    def test_no_enchantment_in_items(self):
        for definition in _items.ITEM_REGISTRY.values():
            self.assertNotIn("enchantment", definition)
            self.assertNotIn("magical", definition)


if __name__ == "__main__":
    unittest.main(verbosity=2)
