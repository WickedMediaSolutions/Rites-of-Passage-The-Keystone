"""
Phase 16 — Player Commands & Gameplay Interfaces Tests

Tests cover:
- Resolution helpers (item, slot, skill, quest, shop name lookups)
- Data-layer APIs exercised as commands would call them
- Dead-state guards on mutating actions
- Skill/spell use through data-layer APIs
- Shop buy/sell through data-layer APIs
- Quest accept/abandon/complete/status through data-layer APIs
- Equipment/inventory through data-layer APIs
- Score/info data-layer output
"""

import unittest

from world.data.character_data import CharacterData
from world.data.enums import CharacterState, EquipmentSlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cd(name="Hero", race="human", prof="warrior", level=10, currency=0):
    """Create a CharacterData with full resources."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.level = level
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    cd.currency = currency
    return cd


def _unlock(cd, *skill_ids):
    for sid in skill_ids:
        cd.unlocked_skills.add(sid)


# =============================================================================
# Resolution Helpers
# =============================================================================


class TestResolveItem(unittest.TestCase):
    """Test resolve_item helper used by equip/unequip/buy/sell."""

    def test_exact_id_match(self):
        from commands import resolve_item
        self.assertEqual(resolve_item("rusty_sword"), "rusty_sword")

    def test_name_match_lowercase(self):
        from commands import resolve_item
        self.assertEqual(resolve_item("rusty sword"), "rusty_sword")

    def test_partial_match(self):
        from commands import resolve_item
        result = resolve_item("rusty")
        self.assertEqual(result, "rusty_sword")

    def test_unknown_item_returns_none(self):
        from commands import resolve_item
        self.assertIsNone(resolve_item("nonexistent_item_xyz"))

    def test_case_insensitive_id_match(self):
        from commands import resolve_item
        self.assertEqual(
            resolve_item("Rusty_Sword"), "rusty_sword"
        )


class TestResolveSlot(unittest.TestCase):
    """Test resolve_slot helper."""

    def test_enum_value_match(self):
        from commands import resolve_slot
        self.assertEqual(
            resolve_slot("main_hand"), EquipmentSlot.MAIN_HAND
        )

    def test_alias_match(self):
        from commands import resolve_slot
        self.assertEqual(
            resolve_slot("mainhand"), EquipmentSlot.MAIN_HAND
        )

    def test_head_slot(self):
        from commands import resolve_slot
        self.assertEqual(resolve_slot("head"), EquipmentSlot.HEAD)

    def test_unknown_slot_returns_none(self):
        from commands import resolve_slot
        self.assertIsNone(resolve_slot("nonexistent_slot"))

    def test_all_slots_resolvable_by_value(self):
        from commands import resolve_slot
        for slot in EquipmentSlot:
            self.assertEqual(
                resolve_slot(slot.value),
                slot,
                f"Failed to resolve {slot.value}",
            )


class TestResolveSkill(unittest.TestCase):
    """Test resolve_skill helper."""

    def test_exact_id_match(self):
        from commands import resolve_skill
        self.assertEqual(resolve_skill("kick"), "kick")

    def test_name_match(self):
        from commands import resolve_skill
        self.assertEqual(resolve_skill("Kick"), "kick")

    def test_partial_match(self):
        from commands import resolve_skill
        result = resolve_skill("fire")
        self.assertIsNotNone(result)
        self.assertIn("fire", result)

    def test_unknown_skill_returns_none(self):
        from commands import resolve_skill
        self.assertIsNone(resolve_skill("nonexistent_skill_xyz"))


class TestResolveQuest(unittest.TestCase):
    """Test resolve_quest helper."""

    def test_exact_id_match(self):
        from commands import resolve_quest
        self.assertEqual(resolve_quest("rat_slayer"), "rat_slayer")

    def test_name_match(self):
        from commands import resolve_quest
        self.assertEqual(resolve_quest("Rat Slayer"), "rat_slayer")

    def test_partial_match(self):
        from commands import resolve_quest
        self.assertEqual(resolve_quest("rat"), "rat_slayer")

    def test_unknown_quest_returns_none(self):
        from commands import resolve_quest
        self.assertIsNone(resolve_quest("nonexistent_quest_xyz"))


class TestResolveShop(unittest.TestCase):
    """Test resolve_shop helper."""

    def test_exact_id_match(self):
        from commands import resolve_shop
        self.assertEqual(
            resolve_shop("general_store"), "general_store"
        )

    def test_name_match(self):
        from commands import resolve_shop
        self.assertEqual(
            resolve_shop("General Store"), "general_store"
        )

    def test_partial_match(self):
        from commands import resolve_shop
        self.assertEqual(
            resolve_shop("general"), "general_store"
        )

    def test_unknown_shop_returns_none(self):
        from commands import resolve_shop
        self.assertIsNone(resolve_shop("nonexistent_shop_xyz"))


# =============================================================================
# Score / Info — Character status data-layer
# =============================================================================


class TestScoreData(unittest.TestCase):
    """Test the data that CmdScore would display."""

    def test_score_basic_fields(self):
        cd = _make_cd()
        self.assertEqual(cd.name, "Hero")
        self.assertEqual(cd.race_id, "human")
        self.assertEqual(cd.profession_id, "warrior")
        self.assertGreater(cd.level, 0)

    def test_score_resources(self):
        cd = _make_cd()
        self.assertEqual(cd.hp, 100)
        self.assertEqual(cd.max_hp, 100)
        self.assertEqual(cd.mana, 100)
        self.assertEqual(cd.stamina, 100)

    def test_score_base_stats_present(self):
        cd = _make_cd()
        for stat in ("str", "int", "wis", "dex", "con"):
            self.assertIn(stat, cd.base_stats)
            self.assertGreater(cd.base_stats[stat], 0)

    def test_score_state(self):
        cd = _make_cd()
        self.assertEqual(cd.state, CharacterState.STANDING)

    def test_score_currency_display(self):
        from world.data.economy import to_display
        cd = _make_cd(currency=54321)
        display = to_display(cd.currency)
        self.assertIn("5g", display)

    def test_dead_character_shows_dead_state(self):
        cd = _make_cd()
        cd.die()
        self.assertEqual(cd.state, CharacterState.DEAD)
        self.assertEqual(cd.hp, 0)


# =============================================================================
# Inventory — Data-layer
# =============================================================================


class TestInventoryData(unittest.TestCase):
    """Test data-layer inventory operations used by CmdInventory."""

    def test_empty_inventory(self):
        cd = _make_cd()
        self.assertEqual(cd.inventory, {})

    def test_add_item_to_inventory(self):
        cd = _make_cd()
        added = cd.add_item("health_potion", 3)
        self.assertEqual(added, 3)
        self.assertEqual(cd.inventory["health_potion"], 3)

    def test_get_item_qty(self):
        cd = _make_cd()
        cd.add_item("torch", 5)
        self.assertEqual(cd.get_item_qty("torch"), 5)

    def test_has_item(self):
        cd = _make_cd()
        cd.add_item("rusty_sword", 1)
        self.assertTrue(cd.has_item("rusty_sword"))

    def test_remove_item(self):
        cd = _make_cd()
        cd.add_item("health_potion", 5)
        removed = cd.remove_item("health_potion", 3)
        self.assertEqual(removed, 3)
        self.assertEqual(cd.inventory["health_potion"], 2)

    def test_remove_item_clears_when_zero(self):
        cd = _make_cd()
        cd.add_item("torch", 1)
        cd.remove_item("torch", 1)
        self.assertNotIn("torch", cd.inventory)


# =============================================================================
# Equipment / Unequip — Data-layer
# =============================================================================


class TestEquipmentData(unittest.TestCase):
    """Test data-layer equipment operations."""

    def test_initial_equipment_empty(self):
        cd = _make_cd()
        for slot in EquipmentSlot:
            self.assertIsNone(cd.get_equipment(slot))

    def test_equip_item(self):
        cd = _make_cd()
        cd.add_item("rusty_sword", 1)
        error = cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNone(error)
        self.assertEqual(
            cd.get_equipment(EquipmentSlot.MAIN_HAND), "rusty_sword"
        )
        self.assertNotIn("rusty_sword", cd.inventory)

    def test_unequip_item(self):
        cd = _make_cd()
        cd.add_item("rusty_sword", 1)
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        error = cd.unequip("rusty_sword", EquipmentSlot.MAIN_HAND)
        self.assertIsNone(error)
        self.assertIsNone(cd.get_equipment(EquipmentSlot.MAIN_HAND))
        self.assertIn("rusty_sword", cd.inventory)

    def test_equip_unknown_item_fails(self):
        cd = _make_cd()
        error = cd.equip("nonexistent", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_equip_wrong_slot_fails(self):
        cd = _make_cd()
        cd.add_item("health_potion", 1)
        error = cd.equip("health_potion", EquipmentSlot.MAIN_HAND)
        self.assertIsNotNone(error)

    def test_equip_replaces_existing(self):
        cd = _make_cd()
        cd.add_item("rusty_sword", 1)
        cd.add_item("short_bow", 1)
        cd.equip("rusty_sword", EquipmentSlot.MAIN_HAND)
        cd.equip("short_bow", EquipmentSlot.MAIN_HAND)
        self.assertEqual(
            cd.get_equipment(EquipmentSlot.MAIN_HAND), "short_bow"
        )
        self.assertIn("rusty_sword", cd.inventory)


# =============================================================================
# Combat Attack — Data-layer
# =============================================================================


class TestAttackData(unittest.TestCase):
    """Test attack resolution as CmdAttack would use it."""

    def test_attack_valid(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    def test_attack_dead_attacker_fails(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        a.die()
        t = _make_cd()
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])

    def test_attack_dead_target_fails(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        t.die()
        result = resolve_attack(a, t)
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])

    def test_attack_self_fails(self):
        from world.data.combat import validate_attack
        cd = _make_cd()
        error = validate_attack(cd, cd)
        self.assertIsNotNone(error)

    def test_attack_result_has_expected_keys(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        result = resolve_attack(a, t)
        for key in (
            "valid", "error", "hit", "roll",
            "raw_damage", "actual_damage",
            "target_hp_before", "target_hp_after",
            "target_killed",
        ):
            self.assertIn(key, result)

    def test_attack_can_kill_target(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        t.hp = 5
        t.max_hp = 100
        killed = False
        for _ in range(50):
            result = resolve_attack(a, t)
            if result["target_killed"]:
                killed = True
                break
            if t.hp <= 0:
                killed = True
                break
        self.assertTrue(killed, "Should be able to kill target")


# =============================================================================
# Skill / Spell Use — Data-layer
# =============================================================================


class TestSkillUseData(unittest.TestCase):
    """Test skill use as CmdUse would call it."""

    def test_use_skill_valid(self):
        from world.data.skills import (
            validate_skill_use, use_skill,
        )
        caster = _make_cd()
        _unlock(caster, "kick")
        target = _make_cd()

        error = validate_skill_use(caster, "kick", target)
        self.assertIsNone(error)

        result = use_skill(caster, "kick", target)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_use_skill_not_unlocked_fails(self):
        from world.data.skills import validate_skill_use
        caster = _make_cd()
        target = _make_cd()
        error = validate_skill_use(caster, "kick", target)
        self.assertIsNotNone(error)

    def test_use_skill_not_enough_resource_fails(self):
        from world.data.skills import validate_skill_use
        caster = _make_cd()
        _unlock(caster, "fireball")
        caster.mana = 5
        target = _make_cd()
        error = validate_skill_use(caster, "fireball", target)
        self.assertIsNotNone(error)

    def test_use_skill_no_target_when_required_fails(self):
        from world.data.skills import validate_skill_use
        caster = _make_cd()
        _unlock(caster, "kick")
        error = validate_skill_use(caster, "kick", None)
        self.assertIsNotNone(error)

    def test_use_skill_dead_target_fails(self):
        from world.data.skills import validate_skill_use
        caster = _make_cd()
        _unlock(caster, "kick")
        target = _make_cd()
        target.die()
        error = validate_skill_use(caster, "kick", target)
        self.assertIsNotNone(error)

    def test_use_passive_skill_fails(self):
        from world.data.skills import validate_skill_use
        caster = _make_cd()
        _unlock(caster, "concussion_weapons")
        error = validate_skill_use(caster, "concussion_weapons", None)
        self.assertIsNotNone(error)

    def test_use_skill_result_has_expected_fields(self):
        from world.data.skills import use_skill
        caster = _make_cd()
        _unlock(caster, "kick")
        target = _make_cd()
        result = use_skill(caster, "kick", target)
        for field in (
            "success", "error", "skill_id",
            "caster_hp_before", "caster_hp_after",
            "caster_mana_before", "caster_mana_after",
            "caster_stamina_before", "caster_stamina_after",
            "resource_type", "resource_cost_paid",
        ):
            self.assertTrue(
                hasattr(result, field),
                f"SkillUseResult missing field: {field}",
            )

    def test_use_skill_consumes_resource(self):
        from world.data.skills import use_skill, get_skill_definition
        caster = _make_cd()
        _unlock(caster, "kick")
        target = _make_cd()
        defn = get_skill_definition("kick")
        stamina_before = caster.stamina
        result = use_skill(caster, "kick", target)
        self.assertTrue(result.success)
        self.assertEqual(
            caster.stamina, stamina_before - defn.cost_amount
        )

    def test_use_damaging_skill_kills_target(self):
        from world.data.skills import use_skill
        caster = _make_cd()
        _unlock(caster, "fireball")
        target = _make_cd()
        target.hp = 10
        target.max_hp = 100
        result = use_skill(caster, "fireball", target)
        self.assertTrue(result.success)
        self.assertTrue(result.target_killed)
        self.assertEqual(target.state, CharacterState.DEAD)

    def test_use_self_heal_skill(self):
        from world.data.skills import use_skill
        caster = _make_cd()
        _unlock(caster, "healing")
        caster.hp = 50
        # healing requires a target but heals the caster
        ally = _make_cd(name="Ally")
        result = use_skill(caster, "healing", ally)
        self.assertTrue(result.success)
        self.assertGreater(result.healing_applied, 0)
        self.assertGreater(caster.hp, 50)

    def test_use_skill_enters_combat(self):
        from world.data.skills import use_skill
        caster = _make_cd()
        _unlock(caster, "kick")
        target = _make_cd()
        result = use_skill(caster, "kick", target)
        self.assertTrue(result.success)
        self.assertTrue(result.caster_entered_combat)


# =============================================================================
# Currency — Data-layer
# =============================================================================


class TestCurrencyData(unittest.TestCase):
    """Test currency operations used by CmdCurrency/CmdBuy/CmdSell."""

    def test_initial_currency_zero(self):
        cd = _make_cd()
        self.assertEqual(cd.currency, 0)

    def test_add_currency(self):
        from world.data.economy import add_currency
        cd = _make_cd()
        add_currency(cd, 1000)
        self.assertEqual(cd.currency, 1000)

    def test_spend_currency(self):
        from world.data.economy import spend_currency
        cd = _make_cd(currency=1000)
        spend_currency(cd, 300)
        self.assertEqual(cd.currency, 700)

    def test_has_funds(self):
        from world.data.economy import has_funds
        cd = _make_cd(currency=500)
        self.assertTrue(has_funds(cd, 500))
        self.assertFalse(has_funds(cd, 501))

    def test_currency_display(self):
        from world.data.economy import to_display
        cd = _make_cd(currency=12345)
        display = to_display(cd.currency)
        self.assertIn("1g", display)


# =============================================================================
# Shop Buy / Sell — Data-layer
# =============================================================================


class TestShopBuySellData(unittest.TestCase):
    """Test buy/sell as CmdBuy/CmdSell would call them."""

    def test_buy_item_success(self):
        from world.data.shops import buy_item
        cd = _make_cd(currency=5000)
        result = buy_item(cd, "general_store", "health_potion", 2)
        self.assertTrue(result.success)
        self.assertEqual(result.item_id, "health_potion")
        self.assertEqual(result.quantity, 2)
        self.assertIn("health_potion", cd.inventory)

    def test_buy_item_insufficient_funds(self):
        from world.data.shops import buy_item
        cd = _make_cd(currency=10)
        result = buy_item(cd, "general_store", "health_potion", 1)
        self.assertFalse(result.success)
        self.assertIn("Insufficient", result.message)

    def test_buy_item_unknown_shop(self):
        from world.data.shops import buy_item
        cd = _make_cd(currency=5000)
        result = buy_item(cd, "nonexistent", "health_potion", 1)
        self.assertFalse(result.success)

    def test_buy_item_unknown_item(self):
        from world.data.shops import buy_item
        cd = _make_cd(currency=5000)
        result = buy_item(cd, "general_store", "nonexistent", 1)
        self.assertFalse(result.success)

    def test_sell_item_success(self):
        from world.data.shops import sell_item
        cd = _make_cd(currency=100)
        cd.inventory["health_potion"] = 5
        result = sell_item(cd, "general_store", "health_potion", 2)
        self.assertTrue(result.success)
        self.assertEqual(cd.inventory.get("health_potion", 0), 3)
        self.assertGreater(cd.currency, 100)

    def test_sell_item_not_enough_owned(self):
        from world.data.shops import sell_item
        cd = _make_cd(currency=100)
        cd.inventory["health_potion"] = 1
        result = sell_item(cd, "general_store", "health_potion", 5)
        self.assertFalse(result.success)

    def test_buy_sell_roundtrip(self):
        from world.data.shops import buy_item, sell_item
        cd = _make_cd(currency=5000)
        buy_item(cd, "general_store", "torch", 5)
        self.assertEqual(cd.inventory["torch"], 5)
        sell_item(cd, "general_store", "torch", 3)
        self.assertEqual(cd.inventory["torch"], 2)

    def test_buy_respects_stock_limits(self):
        from world.data.shops import buy_item
        cd = _make_cd(currency=10000)
        result = buy_item(cd, "blacksmith", "rusty_sword", 4)
        self.assertFalse(result.success)  # stock is 3


# =============================================================================
# Shop Browse — Data-layer
# =============================================================================


class TestShopBrowseData(unittest.TestCase):
    """Test shop browsing as CmdShop would use it."""

    def test_shop_exists(self):
        from world.data.shops import shop_exists
        self.assertTrue(shop_exists("general_store"))
        self.assertTrue(shop_exists("blacksmith"))
        self.assertTrue(shop_exists("alchemist"))

    def test_get_shop_inventory(self):
        from world.data.shops import get_shop_inventory
        inv = get_shop_inventory("general_store")
        self.assertIsNotNone(inv)
        self.assertIn("health_potion", inv)

    def test_get_shop_item_info(self):
        from world.data.shops import get_shop_item_info
        info = get_shop_item_info("general_store", "health_potion")
        self.assertIsNotNone(info)
        self.assertIn("buy_price", info)
        self.assertIn("sell_price", info)

    def test_get_unknown_shop_returns_none(self):
        from world.data.shops import get_shop
        self.assertIsNone(get_shop("nonexistent"))


# =============================================================================
# Quest — Data-layer
# =============================================================================


class TestQuestData(unittest.TestCase):
    """Test quest operations as CmdQuest would call them."""

    def test_quest_list(self):
        from world.data.quests import QUEST_REGISTRY
        self.assertGreater(len(QUEST_REGISTRY), 0)

    def test_accept_quest(self):
        from world.data.quests import accept_quest, is_quest_active
        cd = _make_cd()
        ok, msg = accept_quest(cd, "rat_slayer")
        self.assertTrue(ok)
        self.assertTrue(is_quest_active(cd, "rat_slayer"))

    def test_accept_quest_twice_fails(self):
        from world.data.quests import accept_quest
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        ok, msg = accept_quest(cd, "rat_slayer")
        self.assertFalse(ok)

    def test_abandon_quest(self):
        from world.data.quests import (
            accept_quest, abandon_quest, is_quest_active,
        )
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        ok, msg = abandon_quest(cd, "rat_slayer")
        self.assertTrue(ok)
        self.assertFalse(is_quest_active(cd, "rat_slayer"))

    def test_complete_quest(self):
        from world.data.quests import (
            accept_quest, complete_quest, is_quest_completed,
            update_kill_objective,
        )
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        for _ in range(3):
            update_kill_objective(cd, "giant_rat")
        ok, msg = complete_quest(cd, "rat_slayer")
        self.assertTrue(ok)
        self.assertTrue(is_quest_completed(cd, "rat_slayer"))

    def test_complete_quest_without_objectives_fails(self):
        from world.data.quests import accept_quest, complete_quest
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        ok, msg = complete_quest(cd, "rat_slayer")
        self.assertFalse(ok)

    def test_quest_status_progress(self):
        from world.data.quests import (
            accept_quest, get_objective_progress, update_kill_objective,
        )
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        update_kill_objective(cd, "giant_rat")
        progress = get_objective_progress(cd, "rat_slayer")
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["current"], 1)
        self.assertEqual(progress[0]["required"], 3)

    def test_quest_level_requirement(self):
        from world.data.quests import can_accept
        cd = _make_cd(level=1)
        ok, _ = can_accept(cd, "bone_collector")
        self.assertFalse(ok)

    def test_quest_prerequisite_requirement(self):
        from world.data.quests import can_accept
        cd = _make_cd(level=5)
        ok, reason = can_accept(cd, "guardian_trial")
        self.assertFalse(ok)
        self.assertIn("rat", reason.lower())

    def test_complete_quest_grants_xp(self):
        from world.data.quests import (
            accept_quest, complete_quest, update_kill_objective,
        )
        cd = _make_cd()
        old_xp = cd.xp
        accept_quest(cd, "rat_slayer")
        for _ in range(3):
            update_kill_objective(cd, "giant_rat")
        ok, _ = complete_quest(cd, "rat_slayer")
        self.assertTrue(ok)
        self.assertGreater(cd.xp, old_xp)

    def test_complete_quest_grants_items(self):
        from world.data.quests import (
            accept_quest, complete_quest, update_kill_objective,
        )
        cd = _make_cd()
        accept_quest(cd, "rat_slayer")
        for _ in range(3):
            update_kill_objective(cd, "giant_rat")
        ok, _ = complete_quest(cd, "rat_slayer")
        self.assertTrue(ok)
        self.assertGreater(
            cd.inventory.get("health_potion", 0), 0
        )


# =============================================================================
# Dead-State Guards on Mutating Actions
# =============================================================================


class TestDeadStateGuards(unittest.TestCase):
    """Verify that dead characters cannot perform mutating actions."""

    def test_dead_character_changes_state_to_dead(self):
        cd = _make_cd()
        cd.die()
        self.assertFalse(cd.is_alive())
        self.assertEqual(cd.state, CharacterState.DEAD)

    def test_dead_cannot_attack(self):
        from world.data.combat import validate_attack
        a = _make_cd()
        a.die()
        t = _make_cd()
        error = validate_attack(a, t)
        self.assertIsNotNone(error)

    def test_dead_target_cannot_be_attacked(self):
        from world.data.combat import validate_attack
        a = _make_cd()
        t = _make_cd()
        t.die()
        error = validate_attack(a, t)
        self.assertIsNotNone(error)

    def test_alive_character_is_alive(self):
        cd = _make_cd()
        self.assertTrue(cd.is_alive())


# =============================================================================
# Regression — Existing Systems Intact
# =============================================================================


class TestRegression(unittest.TestCase):
    """Ensure existing systems are unchanged."""

    def test_character_creation_still_works(self):
        cd = _make_cd()
        self.assertIsNotNone(cd)
        self.assertEqual(cd.level, 10)

    def test_items_still_work(self):
        from world.data.items import item_exists
        self.assertTrue(item_exists("health_potion"))
        self.assertTrue(item_exists("rusty_sword"))

    def test_mobs_still_work(self):
        from world.data.mobs import mob_exists
        self.assertTrue(mob_exists("giant_rat"))

    def test_progression_still_works(self):
        from world.data.progression import award_xp
        cd = _make_cd()
        old = cd.xp
        award_xp(cd, 500)
        self.assertGreater(cd.xp, old)

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_cd()
        t = _make_cd()
        res = resolve_attack(a, t)
        self.assertTrue(res["valid"])

    def test_skills_still_work(self):
        from world.data.skills import skill_exists
        self.assertTrue(skill_exists("kick"))
        self.assertTrue(skill_exists("fireball"))

    def test_shops_still_work(self):
        from world.data.shops import shop_exists
        self.assertTrue(shop_exists("general_store"))

    def test_quests_still_work(self):
        from world.data.quests import quest_exists
        self.assertTrue(quest_exists("rat_slayer"))


if __name__ == "__main__":
    unittest.main()
