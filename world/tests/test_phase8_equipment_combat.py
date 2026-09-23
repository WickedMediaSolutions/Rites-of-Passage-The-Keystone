"""
Phase 8 — Equipment → Combat Integration Tests

Tests:
  * unarmed damage
  * equipped weapon damage
  * different weapon values affect damage
  * armor mitigation
  * multiple equipped armor pieces
  * damage minimum/floor
  * invalid equipment safety
  * lethal equipped attack
  * death lifecycle unchanged
  * inventory/equipment persistence unaffected
  * XP/level unchanged

All tests operate on CharacterData via the plain-Python combat functions.
"""

import unittest

from world.data.character_data import CharacterData
from world.data.combat import (
    BASE_DAMAGE,
    UNARMED_DAMAGE,
    STR_DAMAGE_MULTIPLIER,
    ARMOR_MITIGATION_PER_POINT,
    calculate_physical_damage,
    resolve_attack,
    _calculate_total_armor,
)
from world.data.constants import MINIMUM_DAMAGE
from world.data.enums import CharacterState, EquipmentSlot
from world.data import items as _items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Test", race="human", prof="warrior"):
    """Create a fresh CharacterData with full resources."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    return cd


def _give_and_equip_weapon(cd, item_id, slot=EquipmentSlot.MAIN_HAND):
    """Add a weapon item to inventory and equip it to the given slot."""
    cd.add_item(item_id)
    return cd.equip(item_id, slot)


def _give_and_equip_armor(cd, item_id, slot):
    """Add an armor item to inventory and equip it to the given slot."""
    cd.add_item(item_id)
    return cd.equip(item_id, slot)


# ---------------------------------------------------------------------------
# Unarmed Damage
# ---------------------------------------------------------------------------


class TestUnarmedDamage(unittest.TestCase):
    """Damage when no weapon is equipped."""

    def test_unarmed_damage_uses_constant(self):
        a = _make_cd()
        t = _make_cd()
        dmg = calculate_physical_damage(a, t)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)

    def test_unarmed_damage_without_any_equipment(self):
        a = _make_cd()
        t = _make_cd()
        self.assertIsNone(a.equipment[EquipmentSlot.MAIN_HAND])
        dmg = calculate_physical_damage(a, t)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)

    def test_unarmed_damage_is_predictable_with_known_str(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 10
        dmg = calculate_physical_damage(a, t)
        # UNARMED_DAMAGE(5) + int(10 * 0.5) = 5 + 5 = 10
        self.assertEqual(dmg, 10)


# ---------------------------------------------------------------------------
# Equipped Weapon Damage
# ---------------------------------------------------------------------------


class TestEquippedWeaponDamage(unittest.TestCase):
    """Damage when a weapon is equipped in MAIN_HAND."""

    def test_equipped_rusty_sword_deals_sword_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "rusty_sword")
        dmg = calculate_physical_damage(a, t)
        # rusty_sword base_damage=5, STR=0 → 5
        self.assertEqual(dmg, 5)

    def test_equipped_short_bow_deals_bow_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "short_bow")
        dmg = calculate_physical_damage(a, t)
        # short_bow base_damage=4, STR=0 → 4
        self.assertEqual(dmg, 4)

    def test_equipped_hunting_whip_deals_whip_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "hunting_whip")
        dmg = calculate_physical_damage(a, t)
        # hunting_whip base_damage=3, STR=0 → 3
        self.assertEqual(dmg, 3)

    def test_equipped_weapon_with_strength_adds_bonus(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 10
        _give_and_equip_weapon(a, "rusty_sword")
        dmg = calculate_physical_damage(a, t)
        # rusty_sword base=5 + int(10 * 0.5) = 5 + 5 = 10
        self.assertEqual(dmg, 10)


# ---------------------------------------------------------------------------
# Different Weapon Values
# ---------------------------------------------------------------------------


class TestDifferentWeaponValues(unittest.TestCase):
    """Different weapons produce different damage values."""

    def test_weaker_weapon_deals_less_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "hunting_whip")
        dmg_whip = calculate_physical_damage(a, t)

        a2 = _make_cd()
        a2.base_stats["str"] = 0
        _give_and_equip_weapon(a2, "rusty_sword")
        dmg_sword = calculate_physical_damage(a2, t)

        # hunting_whip(3) < rusty_sword(5)
        self.assertLess(dmg_whip, dmg_sword)

    def test_stronger_weapon_deals_more_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "short_bow")
        dmg_bow = calculate_physical_damage(a, t)

        a2 = _make_cd()
        a2.base_stats["str"] = 0
        _give_and_equip_weapon(a2, "hunting_whip")
        dmg_whip = calculate_physical_damage(a2, t)

        # short_bow(4) > hunting_whip(3)
        self.assertGreater(dmg_bow, dmg_whip)


# ---------------------------------------------------------------------------
# Armor Mitigation
# ---------------------------------------------------------------------------


class TestArmorMitigation(unittest.TestCase):
    """Equipped armor reduces incoming damage."""

    def test_no_armor_no_mitigation(self):
        t = _make_cd()
        armor = _calculate_total_armor(t)
        self.assertEqual(armor, 0)

    def test_cloth_vest_reduces_damage(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "rusty_sword")

        # No armor: rusty_sword base=5
        dmg_no_armor = calculate_physical_damage(a, t)
        self.assertEqual(dmg_no_armor, 5)

        # Add armor to target
        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)
        dmg_with_armor = calculate_physical_damage(a, t)
        # cloth_vest armor_class=2.  5 - 2 = 3
        self.assertEqual(dmg_with_armor, 3)
        self.assertLess(dmg_with_armor, dmg_no_armor)

    def test_armor_calculated_from_target_only(self):
        """Armor on the attacker does NOT reduce damage they deal."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "rusty_sword")
        # Put armor on the attacker — should NOT affect damage dealt
        _give_and_equip_armor(a, "cloth_vest", EquipmentSlot.CHEST)

        dmg = calculate_physical_damage(a, t)
        # Target has no armor, so damage = rusty_sword base(5)
        self.assertEqual(dmg, 5)


# ---------------------------------------------------------------------------
# Multiple Equipped Armor Pieces
# ---------------------------------------------------------------------------


class TestMultipleArmorPieces(unittest.TestCase):
    """Multiple armor pieces stack their armor_class values."""

    def test_total_armor_sums_all_pieces(self):
        cd = _make_cd()
        _give_and_equip_armor(cd, "cloth_vest", EquipmentSlot.CHEST)   # armor_class=2
        _give_and_equip_armor(cd, "leather_cap", EquipmentSlot.HEAD)   # armor_class=1
        total = _calculate_total_armor(cd)
        self.assertEqual(total, 3)  # 2 + 1

    def test_multiple_armor_reduces_damage_more(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "rusty_sword")  # base=5

        # No armor
        dmg_bare = calculate_physical_damage(a, t)
        self.assertEqual(dmg_bare, 5)

        # One piece: cloth_vest(2) → 5-2=3
        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)
        dmg_one = calculate_physical_damage(a, t)
        self.assertEqual(dmg_one, 3)

        # Two pieces: +leather_cap(1) → 5-3=2
        _give_and_equip_armor(t, "leather_cap", EquipmentSlot.HEAD)
        dmg_two = calculate_physical_damage(a, t)
        self.assertEqual(dmg_two, 2)

        self.assertLess(dmg_two, dmg_one)
        self.assertLess(dmg_one, dmg_bare)


# ---------------------------------------------------------------------------
# Damage Minimum / Floor
# ---------------------------------------------------------------------------


class TestDamageFloor(unittest.TestCase):
    """Damage never goes below MINIMUM_DAMAGE on a successful hit."""

    def test_armor_cannot_reduce_damage_below_minimum(self):
        """hunting_whip(3) vs cloth_vest(2)+leather_cap(1)=3 → 0 → floored to 1"""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "hunting_whip")  # base=3

        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)  # 2
        _give_and_equip_armor(t, "leather_cap", EquipmentSlot.HEAD)  # 1
        # Total armor=3, whip=3 → 3-3=0 → MINIMUM_DAMAGE
        dmg = calculate_physical_damage(a, t)
        self.assertEqual(dmg, MINIMUM_DAMAGE)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)

    def test_damage_never_negative(self):
        """Even with unarmed(5) vs heavy armor, damage stays >= MINIMUM_DAMAGE."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        # No weapon → UNARMED_DAMAGE=5
        # Armor: 2+1=3 → 5-3=2 (above floor)
        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)
        _give_and_equip_armor(t, "leather_cap", EquipmentSlot.HEAD)

        dmg = calculate_physical_damage(a, t)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)
        self.assertGreater(dmg, 0)

    def test_floor_applies_regardless_of_weapon(self):
        """Floor is always applied."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "hunting_whip")  # base=3

        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)  # 2
        _give_and_equip_armor(t, "leather_cap", EquipmentSlot.HEAD)  # 1

        dmg = calculate_physical_damage(a, t)
        self.assertGreaterEqual(dmg, MINIMUM_DAMAGE)


# ---------------------------------------------------------------------------
# Invalid Equipment Safety
# ---------------------------------------------------------------------------


class TestInvalidEquipmentSafety(unittest.TestCase):
    """Combat safely handles invalid/missing equipment data."""

    def test_equipped_invalid_item_id_does_not_crash(self):
        """A slot with an item_id not in the registry falls back to unarmed."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        a.equipment[EquipmentSlot.MAIN_HAND] = "nonexistent_weapon"
        dmg = calculate_physical_damage(a, t)
        self.assertEqual(dmg, UNARMED_DAMAGE)

    def test_equipped_armor_in_weapon_slot_does_not_crash(self):
        """Armor equipped in MAIN_HAND is ignored for damage purposes."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        a.equipment[EquipmentSlot.MAIN_HAND] = "cloth_vest"
        dmg = calculate_physical_damage(a, t)
        self.assertEqual(dmg, UNARMED_DAMAGE)

    def test_none_equipped_is_safe(self):
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        a.equipment[EquipmentSlot.MAIN_HAND] = None
        dmg = calculate_physical_damage(a, t)
        self.assertEqual(dmg, UNARMED_DAMAGE)

    def test_armor_on_invalid_item_id_contributes_zero(self):
        t = _make_cd()
        t.equipment[EquipmentSlot.CHEST] = "nonexistent_armor"
        armor = _calculate_total_armor(t)
        self.assertEqual(armor, 0)

    def test_weapon_on_target_does_not_reduce_damage(self):
        """Weapons in target's equipment don't act as armor."""
        a = _make_cd()
        t = _make_cd()
        a.base_stats["str"] = 0
        _give_and_equip_weapon(a, "rusty_sword")  # base=5
        _give_and_equip_weapon(t, "wooden_club")   # target has weapon

        dmg = calculate_physical_damage(a, t)
        # Target has only weapon (not armor), so no mitigation
        # rusty_sword=5, no armor → 5
        self.assertEqual(dmg, 5)


# ---------------------------------------------------------------------------
# Lethal Equipped Attack
# ---------------------------------------------------------------------------


class TestLethalEquippedAttack(unittest.TestCase):
    """A lethal attack with an equipped weapon kills correctly."""

    def test_equipped_weapon_can_kill(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t = _make_cd()
            a.base_stats["str"] = 0
            _give_and_equip_weapon(a, "rusty_sword")  # base=5
            t.hp = 3  # will die from one hit

            result = resolve_attack(a, t)
            self.assertTrue(result["valid"])
            self.assertTrue(result["hit"])
            self.assertTrue(result["target_killed"])
            self.assertEqual(t.state, CharacterState.DEAD)
            self.assertEqual(t.hp, 0)
        finally:
            random.randint = orig

    def test_unarmed_can_kill(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t = _make_cd()
            a.base_stats["str"] = 0
            t.hp = 3  # unarmed damage=5 → kills

            result = resolve_attack(a, t)
            self.assertTrue(result["valid"])
            self.assertTrue(result["hit"])
            self.assertTrue(result["target_killed"])
            self.assertEqual(t.state, CharacterState.DEAD)
            self.assertEqual(t.hp, 0)
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Death Lifecycle Unchanged
# ---------------------------------------------------------------------------


class TestDeathLifecycleUnchanged(unittest.TestCase):
    """Phase 8 does not alter the authoritative death lifecycle."""

    def test_die_is_still_authoritative(self):
        cd = _make_cd()
        self.assertTrue(callable(cd.die))
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)

    def test_die_is_still_idempotent(self):
        cd = _make_cd()
        cd.die()
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)

    def test_combat_kill_still_uses_die(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t = _make_cd()
            _give_and_equip_weapon(a, "rusty_sword")
            t.hp = 1

            result = resolve_attack(a, t)
            if result["target_killed"]:
                self.assertEqual(t.state, CharacterState.DEAD)
                self.assertEqual(t.hp, 0)
        finally:
            random.randint = orig

    def test_combat_killed_target_blocked_from_attacking(self):
        import random
        orig = random.randint

        def _force_hit(lo, hi):
            return 1

        try:
            random.randint = _force_hit
            a = _make_cd()
            t = _make_cd()
            _give_and_equip_weapon(a, "rusty_sword")
            t.hp = 1

            resolve_attack(a, t)

            result = resolve_attack(t, a)
            self.assertFalse(result["valid"])
            self.assertIsNotNone(result["error"])
        finally:
            random.randint = orig


# ---------------------------------------------------------------------------
# Inventory / Equipment Persistence Unaffected
# ---------------------------------------------------------------------------


class TestInventoryEquipmentPersistence(unittest.TestCase):
    """Combat does not mutate inventory or equipment."""

    def test_combat_does_not_change_inventory(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_weapon(a, "rusty_sword")
        a.add_item("health_potion", 5)

        inv_before = dict(a.inventory)
        resolve_attack(a, t)
        self.assertEqual(a.inventory, inv_before)

    def test_combat_does_not_change_equipment(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_weapon(a, "rusty_sword")

        eq_before = dict(a.equipment)
        resolve_attack(a, t)
        self.assertEqual(a.equipment, eq_before)

    def test_combat_does_not_change_target_equipment(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_armor(t, "cloth_vest", EquipmentSlot.CHEST)

        eq_before = dict(t.equipment)
        resolve_attack(a, t)
        self.assertEqual(t.equipment, eq_before)

    def test_combat_does_not_change_target_inventory(self):
        a = _make_cd()
        t = _make_cd()
        t.add_item("health_potion", 3)

        inv_before = dict(t.inventory)
        resolve_attack(a, t)
        self.assertEqual(t.inventory, inv_before)


# ---------------------------------------------------------------------------
# XP / Level Unchanged
# ---------------------------------------------------------------------------


class TestXPLevelUnchanged(unittest.TestCase):
    """Combat still does not award XP or change level."""

    def test_xp_unchanged_by_equipped_combat(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_weapon(a, "short_bow")
        xp_before = a.xp
        resolve_attack(a, t)
        self.assertEqual(a.xp, xp_before)

    def test_level_unchanged_by_equipped_combat(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_weapon(a, "wooden_club")
        lvl_before = a.level
        resolve_attack(a, t)
        self.assertEqual(a.level, lvl_before)

    def test_target_xp_unchanged_by_combat(self):
        a = _make_cd()
        t = _make_cd()
        _give_and_equip_weapon(a, "rusty_sword")
        xp_before = t.xp
        resolve_attack(a, t)
        self.assertEqual(t.xp, xp_before)


# ---------------------------------------------------------------------------
# Regression: Phase 5/6 behavior preserved
# ---------------------------------------------------------------------------


class TestPhase5Regression(unittest.TestCase):
    """Existing Phase 5/6 combat behavior is unchanged."""

    def test_valid_attack_still_passes(self):
        from world.data.combat import validate_attack
        a = _make_cd()
        t = _make_cd()
        self.assertIsNone(validate_attack(a, t))

    def test_self_attack_still_rejected(self):
        a = _make_cd()
        result = resolve_attack(a, a)
        self.assertFalse(result["valid"])

    def test_dead_target_still_rejected(self):
        a = _make_cd()
        t = _make_cd()
        t.die()
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIn("dead", result["error"].lower())

    def test_result_still_has_all_keys(self):
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        expected_keys = {
            "valid", "error", "hit", "roll", "raw_damage",
            "actual_damage", "target_hp_before", "target_hp_after",
            "target_killed", "attacker_combat", "target_combat",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_combat_still_preserves_faction(self):
        a = _make_cd()
        t = _make_cd()
        a_faction = a.faction
        t_faction = t.faction
        resolve_attack(a, t)
        self.assertEqual(a.faction, a_faction)
        self.assertEqual(t.faction, t_faction)

    def test_combat_still_preserves_race_profession(self):
        a = _make_cd(race="human", prof="warrior")
        t = _make_cd(race="high_elf", prof="mage")
        resolve_attack(a, t)
        self.assertEqual(a.race_id, "human")
        self.assertEqual(a.profession_id, "warrior")
        self.assertEqual(t.race_id, "high_elf")
        self.assertEqual(t.profession_id, "mage")


if __name__ == "__main__":
    unittest.main(verbosity=2)
