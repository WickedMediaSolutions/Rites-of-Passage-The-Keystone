"""
Phase 14 -- Economy, Currency & Shops Tests
"""

import json
import unittest

from world.data.character_data import CharacterData
from world.data.economy import (
    TransactionResult,
    add_currency,
    get_currency,
    has_funds,
    spend_currency,
    to_display,
)
from world.data.shops import (
    PLACEHOLDER_SHOPS,
    SHOP_REGISTRY,
    _is_sellable,
    buy_item,
    get_buy_price,
    get_sell_price,
    get_shop,
    get_shop_inventory,
    get_shop_item_info,
    get_stock,
    sell_item,
    shop_exists,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(name="Hero", race="human", prof="warrior", currency=0):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    cd.currency = currency
    return cd
# =========================================================================
# Currency Model
# =========================================================================


class TestCurrencyModel(unittest.TestCase):

    def test_initial_currency_zero(self):
        p = _make_player()
        self.assertEqual(get_currency(p), 0)

    def test_add_currency(self):
        p = _make_player()
        add_currency(p, 500)
        self.assertEqual(get_currency(p), 500)
        add_currency(p, 250)
        self.assertEqual(get_currency(p), 750)

    def test_add_currency_zero_raises(self):
        p = _make_player()
        with self.assertRaises(ValueError):
            add_currency(p, 0)

    def test_add_currency_negative_raises(self):
        p = _make_player()
        with self.assertRaises(ValueError):
            add_currency(p, -100)

    def test_spend_currency(self):
        p = _make_player(currency=1000)
        spend_currency(p, 300)
        self.assertEqual(get_currency(p), 700)

    def test_spend_currency_insufficient_raises(self):
        p = _make_player(currency=100)
        with self.assertRaises(ValueError):
            spend_currency(p, 101)

    def test_spend_currency_zero_raises(self):
        p = _make_player(currency=100)
        with self.assertRaises(ValueError):
            spend_currency(p, 0)

    def test_spend_currency_negative_raises(self):
        p = _make_player(currency=100)
        with self.assertRaises(ValueError):
            spend_currency(p, -50)

    def test_has_funds(self):
        p = _make_player(currency=500)
        self.assertTrue(has_funds(p, 500))
        self.assertTrue(has_funds(p, 1))
        self.assertFalse(has_funds(p, 501))

    def test_has_funds_negative_amount(self):
        p = _make_player(currency=100)
        self.assertFalse(has_funds(p, -10))

    def test_currency_persistence(self):
        p = _make_player(currency=1234)
        data = p.to_dict()
        self.assertIn("currency", data)
        self.assertEqual(data["currency"], 1234)

    def test_currency_json_roundtrip(self):
        p = _make_player(currency=9876)
        data = p.to_dict()
        j = json.dumps(data)
        restored_data = json.loads(j)
        p2 = CharacterData.from_dict(restored_data)
        self.assertEqual(get_currency(p2), 9876)

    def test_to_display_zero(self):
        self.assertEqual(to_display(0), "0c")

    def test_to_display_copper_only(self):
        self.assertIn("c", to_display(50))
        self.assertNotIn("g", to_display(50))

    def test_to_display_gold(self):
        display = to_display(12345)
        self.assertIn("g", display)
# =========================================================================
# Transaction Result
# =========================================================================


class TestTransactionResult(unittest.TestCase):

    def test_ok_struct(self):
        r = TransactionResult.ok(
            message="Done", item_id="torch", quantity=2,
            total_cost=200, new_balance=800,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.message, "Done")
        self.assertEqual(r.item_id, "torch")
        self.assertEqual(r.quantity, 2)
        self.assertEqual(r.total_cost, 200)
        self.assertEqual(r.new_balance, 800)

    def test_fail_struct(self):
        r = TransactionResult.fail("No money")
        self.assertFalse(r.success)
        self.assertEqual(r.message, "No money")
        self.assertEqual(r.item_id, "")
        self.assertEqual(r.quantity, 0)
        self.assertEqual(r.total_cost, 0)
        self.assertEqual(r.new_balance, 0)


# =========================================================================
# Shop Registry & Definitions
# =========================================================================


class TestShopRegistry(unittest.TestCase):

    def test_registry_exists(self):
        self.assertIsInstance(SHOP_REGISTRY, dict)
        self.assertGreater(len(SHOP_REGISTRY), 0)

    def test_get_shop_valid(self):
        s = get_shop("general_store")
        self.assertIsNotNone(s)
        self.assertEqual(s["shop_id"], "general_store")
        self.assertEqual(s["name"], "General Store")

    def test_get_shop_invalid(self):
        self.assertIsNone(get_shop("nonexistent"))

    def test_shop_exists(self):
        self.assertTrue(shop_exists("blacksmith"))
        self.assertFalse(shop_exists("nonexistent"))

    def test_all_shops_required_fields(self):
        for sid, shop in SHOP_REGISTRY.items():
            with self.subTest(shop_id=sid):
                self.assertIn("shop_id", shop)
                self.assertIn("name", shop)
                self.assertIn("items", shop)
                self.assertIsInstance(shop["items"], dict)

    def test_all_stock_entries_consistent(self):
        for sid, shop in SHOP_REGISTRY.items():
            for item_id, entry in shop["items"].items():
                with self.subTest(shop_id=sid, item_id=item_id):
                    self.assertIn("buy_price", entry)
                    self.assertIn("sell_price", entry)
                    self.assertIn("stock", entry)

    def test_shop_definitions_json_serializable(self):
        for sid, shop in SHOP_REGISTRY.items():
            with self.subTest(shop_id=sid):
                s = json.dumps(shop)
                restored = json.loads(s)
                self.assertEqual(restored["shop_id"], shop["shop_id"])
# =========================================================================
# Shop Queries
# =========================================================================


class TestShopQueries(unittest.TestCase):

    def test_get_shop_item_info_found(self):
        info = get_shop_item_info("blacksmith", "rusty_sword")
        self.assertIsNotNone(info)
        self.assertEqual(info["buy_price"], 1000)
        self.assertEqual(info["sell_price"], 500)

    def test_get_shop_item_info_not_found(self):
        self.assertIsNone(get_shop_item_info("blacksmith", "torch"))

    def test_get_shop_item_info_bad_shop(self):
        self.assertIsNone(get_shop_item_info("nope", "rusty_sword"))

    def test_get_buy_price(self):
        self.assertEqual(get_buy_price("general_store", "torch"), 100)
        self.assertIsNone(get_buy_price("general_store", "rusty_sword"))

    def test_get_sell_price(self):
        self.assertEqual(get_sell_price("general_store", "torch"), 50)

    def test_get_stock(self):
        self.assertIsNone(get_stock("general_store", "torch"))
        self.assertEqual(get_stock("blacksmith", "rusty_sword"), 3)

    def test_get_shop_inventory(self):
        inv = get_shop_inventory("alchemist")
        self.assertIsNotNone(inv)
        self.assertIn("health_potion", inv)
        self.assertNotIn("rusty_sword", inv)


# =========================================================================
# Buy
# =========================================================================


class TestBuyItem(unittest.TestCase):

    def test_buy_simple(self):
        p = _make_player(currency=2000)
        result = buy_item(p, "general_store", "torch", 2)
        self.assertTrue(result.success)
        self.assertEqual(result.quantity, 2)
        self.assertEqual(result.total_cost, 200)
        self.assertEqual(result.new_balance, 1800)
        self.assertEqual(get_currency(p), 1800)
        self.assertEqual(p.inventory.get("torch"), 2)

    def test_buy_no_currency_change_on_failure(self):
        p = _make_player(currency=50)
        orig = get_currency(p)
        result = buy_item(p, "blacksmith", "rusty_sword", 1)
        self.assertFalse(result.success)
        self.assertEqual(get_currency(p), orig)
        self.assertNotIn("rusty_sword", p.inventory)

    def test_buy_stacked_item(self):
        p = _make_player(currency=2000)
        p.inventory["torch"] = 3
        result = buy_item(p, "general_store", "torch", 2)
        self.assertTrue(result.success)
        self.assertEqual(p.inventory["torch"], 5)

    def test_buy_insufficient_funds(self):
        p = _make_player(currency=10)
        result = buy_item(p, "general_store", "torch", 1)
        self.assertFalse(result.success)
        self.assertIn("Insufficient funds", result.message)

    def test_buy_unknown_shop(self):
        p = _make_player(currency=1000)
        result = buy_item(p, "no_such_shop", "torch", 1)
        self.assertFalse(result.success)
        self.assertIn("Unknown shop", result.message)

    def test_buy_unknown_item(self):
        p = _make_player(currency=1000)
        result = buy_item(p, "general_store", "photon_cannon", 1)
        self.assertFalse(result.success)
        self.assertIn("Unknown item", result.message)

    def test_buy_not_available_at_shop(self):
        p = _make_player(currency=2000)
        result = buy_item(p, "alchemist", "rusty_sword", 1)
        self.assertFalse(result.success)
        self.assertIn("not available", result.message)

    def test_buy_zero_quantity(self):
        p = _make_player(currency=1000)
        result = buy_item(p, "general_store", "torch", 0)
        self.assertFalse(result.success)
        self.assertIn("Quantity", result.message)

    def test_buy_negative_quantity(self):
        p = _make_player(currency=1000)
        result = buy_item(p, "general_store", "torch", -1)
        self.assertFalse(result.success)

    def test_buy_exactly_enough_funds(self):
        p = _make_player(currency=100)
        result = buy_item(p, "general_store", "torch", 1)
        self.assertTrue(result.success)
        self.assertEqual(get_currency(p), 0)
        self.assertEqual(p.inventory.get("torch"), 1)

    def test_buy_from_limited_stock(self):
        p = _make_player(currency=5000)
        result = buy_item(p, "blacksmith", "rusty_sword", 2)
        self.assertTrue(result.success)
        self.assertEqual(get_stock("blacksmith", "rusty_sword"), 1)

    def test_buy_exceeds_limited_stock(self):
        p = _make_player(currency=5000)
        result = buy_item(p, "blacksmith", "rusty_sword", 10)
        self.assertFalse(result.success)
        self.assertIn("in stock", result.message)

    def test_buy_from_unlimited_stock(self):
        p = _make_player(currency=10000)
        result = buy_item(p, "general_store", "torch", 50)
        self.assertTrue(result.success)
        self.assertIsNone(get_stock("general_store", "torch"))
# =========================================================================
# Sell
# =========================================================================


class TestSellItem(unittest.TestCase):

    def test_sell_simple(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 5
        result = sell_item(p, "general_store", "torch", 2)
        self.assertTrue(result.success)
        self.assertEqual(result.quantity, 2)
        self.assertEqual(result.total_cost, 100)
        self.assertEqual(get_currency(p), 200)
        self.assertEqual(p.inventory.get("torch"), 3)

    def test_sell_removes_item_when_zero(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 1
        result = sell_item(p, "general_store", "torch", 1)
        self.assertTrue(result.success)
        self.assertNotIn("torch", p.inventory)

    def test_sell_no_currency_change_on_failure(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 1
        orig = get_currency(p)
        orig_inv = p.inventory["torch"]
        result = sell_item(p, "general_store", "torch", 99)
        self.assertFalse(result.success)
        self.assertEqual(get_currency(p), orig)
        self.assertEqual(p.inventory["torch"], orig_inv)

    def test_sell_insufficient_quantity(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 1
        result = sell_item(p, "general_store", "torch", 5)
        self.assertFalse(result.success)
        self.assertIn("only have", result.message)

    def test_sell_quest_item_protected(self):
        p = _make_player(currency=100)
        p.inventory["old_letter"] = 1
        result = sell_item(p, "general_store", "old_letter", 1)
        self.assertFalse(result.success)
        self.assertIn("cannot be sold", result.message)
        self.assertEqual(p.inventory["old_letter"], 1)

    def test_sell_unknown_shop(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 1
        result = sell_item(p, "nope", "torch", 1)
        self.assertFalse(result.success)
        self.assertIn("Unknown shop", result.message)

    def test_sell_unknown_item(self):
        p = _make_player(currency=100)
        p.inventory["no_such_item"] = 1
        result = sell_item(p, "general_store", "no_such_item", 1)
        self.assertFalse(result.success)
        self.assertIn("Unknown item", result.message)

    def test_sell_item_not_accepted_by_shop(self):
        p = _make_player(currency=100)
        p.inventory["rusty_sword"] = 1
        result = sell_item(p, "alchemist", "rusty_sword", 1)
        self.assertFalse(result.success)
        self.assertIn("cannot be sold to", result.message)

    def test_sell_zero_quantity(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 1
        result = sell_item(p, "general_store", "torch", 0)
        self.assertFalse(result.success)
        self.assertIn("Quantity", result.message)


# =========================================================================
# Sellability / Quest Protection
# =========================================================================


class TestSellability(unittest.TestCase):

    def test_is_sellable_quest_false(self):
        self.assertFalse(_is_sellable("old_letter"))

    def test_is_sellable_weapon_true(self):
        self.assertTrue(_is_sellable("rusty_sword"))

    def test_is_sellable_consumable_true(self):
        self.assertTrue(_is_sellable("health_potion"))

    def test_is_sellable_misc_true(self):
        self.assertTrue(_is_sellable("wooden_plank"))


# =========================================================================
# Transaction Atomicity
# =========================================================================


class TestTransactionAtomicity(unittest.TestCase):

    def test_buy_does_not_partially_mutate_on_failure(self):
        p = _make_player(currency=500)
        orig_currency = get_currency(p)
        orig_inv = dict(p.inventory)
        result = buy_item(p, "blacksmith", "rusty_sword", 1)
        self.assertFalse(result.success)
        self.assertEqual(get_currency(p), orig_currency)
        self.assertEqual(p.inventory, orig_inv)

    def test_sell_does_not_partially_mutate_on_failure(self):
        p = _make_player(currency=100)
        p.inventory["torch"] = 2
        orig_currency = get_currency(p)
        orig_inv = dict(p.inventory)
        result = sell_item(p, "general_store", "torch", 99)
        self.assertFalse(result.success)
        self.assertEqual(get_currency(p), orig_currency)
        self.assertEqual(p.inventory, orig_inv)
# =========================================================================
# Inventory Integration
# =========================================================================


class TestInventoryIntegration(unittest.TestCase):

    def test_buy_adds_to_inventory(self):
        p = _make_player(currency=2000)
        self.assertNotIn("short_bow", p.inventory)
        buy_item(p, "blacksmith", "short_bow", 1)
        self.assertEqual(p.inventory["short_bow"], 1)

    def test_sell_removes_from_inventory(self):
        p = _make_player(currency=100)
        p.inventory["health_potion"] = 3
        sell_item(p, "general_store", "health_potion", 2)
        self.assertEqual(p.inventory["health_potion"], 1)

    def test_buy_and_sell_roundtrip(self):
        p = _make_player(currency=5000)
        buy_item(p, "general_store", "torch", 5)
        self.assertEqual(p.inventory["torch"], 5)
        sell_item(p, "general_store", "torch", 3)
        self.assertEqual(p.inventory["torch"], 2)

    def test_sell_all_potions_empty_slot(self):
        p = _make_player(currency=100)
        p.inventory["health_potion"] = 2
        sell_item(p, "general_store", "health_potion", 2)
        self.assertNotIn("health_potion", p.inventory)


# =========================================================================
# Currency Edge Cases
# =========================================================================


class TestCurrencyEdgeCases(unittest.TestCase):

    def test_add_large_amount(self):
        p = _make_player()
        add_currency(p, 999999999)
        self.assertEqual(get_currency(p), 999999999)

    def test_display_large_amount(self):
        display = to_display(1234567)
        self.assertIn("p", display.lower())


# =========================================================================
# JSON Round-Trip
# =========================================================================


class TestJsonRoundTrip(unittest.TestCase):

    def test_currency_survives_roundtrip(self):
        p = _make_player(currency=42000)
        p.inventory["torch"] = 5
        p.inventory["health_potion"] = 10
        data = json.dumps(p.to_dict())
        p2 = CharacterData.from_dict(json.loads(data))
        self.assertEqual(get_currency(p2), 42000)
        self.assertEqual(p2.inventory.get("torch"), 5)
        self.assertEqual(p2.inventory.get("health_potion"), 10)

    def test_zero_currency_survives_roundtrip(self):
        p = _make_player(currency=0)
        data = json.dumps(p.to_dict())
        p2 = CharacterData.from_dict(json.loads(data))
        self.assertEqual(get_currency(p2), 0)

    def test_currency_survives_to_from_dict(self):
        p = _make_player(currency=7890)
        p2 = CharacterData.from_dict(p.to_dict())
        self.assertEqual(get_currency(p2), 7890)


# =========================================================================
# No Phase 15 Leakage
# =========================================================================


class TestNoPhase15Leakage(unittest.TestCase):

    def test_no_haggle_in_shops(self):
        import inspect
        from world.data import shops
        src = inspect.getsource(shops)
        # Strip the module docstring (everything between first and second """)
        # and all comment-only lines.
        in_docstring = False
        clean_lines = []
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            clean_lines.append(line)
        body = "\n".join(clean_lines).lower()
        for term in ["haggle", "auction", "bank", "craft", "dynamic_pricing"]:
            self.assertNotIn(term, body,
                             f"Phase 14 must not implement {term}")


if __name__ == "__main__":
    unittest.main()