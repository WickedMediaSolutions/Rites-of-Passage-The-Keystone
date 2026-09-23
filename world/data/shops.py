"""
Rites of Passage — Shop Definitions & Transaction Logic

Static shop definitions kept separate from character state.  Every shop
has a stable string ID, a display name, and a dict of stocked items with
buy/sell prices and optional stock limits.

Design constraints (Phase 14 foundation):
    • Shop definitions with stable IDs
    • Shop inventory (item_id -> price + stock)
    • Buy / sell with fund / stock / item validation
    • Quantity handling
    • Non-sellable / quest-item protection
    • Configurable buy/sell prices (marked [PLACEHOLDER])
    • Structured TransactionResult returns
    • No haggle / dynamic pricing / banking / auction house / player trading
    • No Phase 15+
"""

from __future__ import annotations

from world.data.economy import (
    add_currency,
    get_currency,
    has_funds,
    spend_currency,
    TransactionResult,
)
from world.data.items import get_item, item_exists


# ---------------------------------------------------------------------------
# Shop Definition Helper
# ---------------------------------------------------------------------------


def _make_shop_def(shop_id: str, name: str, items: dict) -> dict:
    """Construct a consistent shop-definition dict.

    *items* maps item_id -> {
        "buy_price":  int (copper) | None,
        "sell_price": int (copper) | None,
        "stock":      int | None,
    }

    All prices are [PLACEHOLDER] pending final game-design tuning.
    """
    shop = {"shop_id": shop_id, "name": name, "items": {}}
    for item_id, stock_def in items.items():
        entry = dict(stock_def)
        entry.setdefault("buy_price", None)
        entry.setdefault("sell_price", None)
        entry.setdefault("stock", None)
        shop["items"][item_id] = entry
    return shop


# ---------------------------------------------------------------------------
# Placeholder Shop Catalog
# ---------------------------------------------------------------------------

# ALL PRICES ARE [PLACEHOLDER] — not final balance.

PLACEHOLDER_SHOPS = {
    "general_store": _make_shop_def(
        "general_store", "General Store",
        {
            "health_potion":  {"buy_price": 500, "sell_price": 250, "stock": None},
            "mana_potion":    {"buy_price": 500, "sell_price": 250, "stock": None},
            "stamina_potion": {"buy_price": 500, "sell_price": 250, "stock": None},
            "torch":          {"buy_price": 100, "sell_price":  50, "stock": None},
            "wooden_plank":   {"buy_price":  50, "sell_price":  25, "stock": None},
        },
    ),
    "blacksmith": _make_shop_def(
        "blacksmith", "Blacksmith",
        {
            "rusty_sword":  {"buy_price": 1000, "sell_price": 500, "stock": 3},
            "short_bow":   {"buy_price":  800, "sell_price": 400, "stock": 2},
            "leather_cap":  {"buy_price":  600, "sell_price": 300, "stock": 5},
            "wooden_plank": {"buy_price":   60, "sell_price":  30, "stock": 10},
        },
    ),
    "alchemist": _make_shop_def(
        "alchemist", "Alchemist's Shop",
        {
            "health_potion":  {"buy_price": 450, "sell_price": 225, "stock": None},
            "mana_potion":    {"buy_price": 450, "sell_price": 225, "stock": None},
            "stamina_potion": {"buy_price": 450, "sell_price": 225, "stock": None},
        },
    ),
}
# ---------------------------------------------------------------------------
# Shop Registry
# ---------------------------------------------------------------------------

SHOP_REGISTRY = dict(PLACEHOLDER_SHOPS)


def get_shop(shop_id: str) -> dict | None:
    """Return the static shop definition for *shop_id*, or None."""
    return SHOP_REGISTRY.get(shop_id)


def shop_exists(shop_id: str) -> bool:
    """Return True if *shop_id* is a known shop."""
    return shop_id in SHOP_REGISTRY

def register_shop(shop_id: str, name: str, npc_id: str | None = None, description: str = "") -> dict:
    """Register or update a shop in SHOP_REGISTRY.

    Creates a new entry with an empty ``items`` dict when *shop_id* is
    unknown.  Updates the name / npc_id / description on an existing
    shop while preserving its current inventory.

    Returns the shop definition dict.
    """
    if shop_id in SHOP_REGISTRY:
        shop = SHOP_REGISTRY[shop_id]
        shop["name"] = name
        shop["npc_id"] = npc_id
        shop["description"] = description
    else:
        SHOP_REGISTRY[shop_id] = {
            "shop_id": shop_id,
            "name": name,
            "npc_id": npc_id,
            "description": description,
            "items": {},
        }
    return SHOP_REGISTRY[shop_id]


def register_shop_item(
    shop_id: str,
    item_id: str,
    buy_price: int | None = None,
    sell_price: int | None = None,
    stock: int | None = None,
    enabled: bool = True,
) -> dict | None:
    """Register or update an item's pricing/stock in *shop_id*.

    Returns the item entry dict on success, or ``None`` if the shop does
    not exist or *enabled* is ``False``.
    """
    if not enabled:
        return None

    shop = SHOP_REGISTRY.get(shop_id)
    if shop is None:
        return None

    entry = shop["items"].get(item_id)
    if entry is None:
        entry = {}
        shop["items"][item_id] = entry

    entry["buy_price"] = buy_price
    entry["sell_price"] = sell_price
    entry["stock"] = stock
    return entry

# ---------------------------------------------------------------------------
# Shop Queries
# ---------------------------------------------------------------------------


def get_shop_item_info(shop_id: str, item_id: str) -> dict | None:
    """Return the shop's stock entry for *item_id*, or None."""
    shop = get_shop(shop_id)
    if shop is None:
        return None
    return shop.get("items", {}).get(item_id)


def get_shop_inventory(shop_id: str) -> dict | None:
    """Return the shop's full items dict, or None if shop unknown."""
    shop = get_shop(shop_id)
    if shop is None:
        return None
    return dict(shop.get("items", {}))


def get_buy_price(shop_id: str, item_id: str) -> int | None:
    """Return the cost to buy one unit, or None if not sold."""
    info = get_shop_item_info(shop_id, item_id)
    if info is None:
        return None
    return info.get("buy_price")


def get_sell_price(shop_id: str, item_id: str) -> int | None:
    """Return the refund for selling one unit, or None."""
    info = get_shop_item_info(shop_id, item_id)
    if info is None:
        return None
    return info.get("sell_price")


def get_stock(shop_id: str, item_id: str) -> int | None:
    """Return current stock level, or None if unlimited."""
    info = get_shop_item_info(shop_id, item_id)
    if info is None:
        return None
    return info.get("stock")
# ---------------------------------------------------------------------------
# Buy / Sell Internals
# ---------------------------------------------------------------------------

_NONSELLABLE_CATEGORIES = {"quest"}


def _is_sellable(item_id: str) -> bool:
    """Return True if this item type can be sold to a shop."""
    if not item_exists(item_id):
        return False
    item_def = get_item(item_id)
    return item_def.get("category") not in _NONSELLABLE_CATEGORIES


def _reduce_stock(shop: dict, item_id: str, qty: int) -> None:
    """Reduce stock for a limited-stock shop entry."""
    entry = shop["items"][item_id]
    if entry.get("stock") is not None:
        entry["stock"] -= qty


# ===================================================================
# Buy
# ===================================================================


def buy_item(cd, shop_id: str, item_id: str, quantity: int = 1) -> TransactionResult:
    """Attempt to purchase *quantity* units of *item_id* from *shop_id*.

    Returns a TransactionResult.  Mutates *cd* only on success.
    """
    shop = get_shop(shop_id)
    if shop is None:
        return TransactionResult.fail(f"Unknown shop: '{shop_id}'.")

    if not item_exists(item_id):
        return TransactionResult.fail(f"Unknown item: '{item_id}'.")

    stock_entry = shop.get("items", {}).get(item_id)
    if stock_entry is None:
        return TransactionResult.fail(
            f"'{item_id}' is not available at '{shop['name']}'."
        )

    buy_price = stock_entry.get("buy_price")
    if buy_price is None:
        return TransactionResult.fail(
            f"'{item_id}' cannot be purchased at '{shop['name']}'."
        )

    if quantity <= 0:
        return TransactionResult.fail("Quantity must be positive.")

    stock = stock_entry.get("stock")
    if stock is not None and quantity > stock:
        return TransactionResult.fail(
            f"Only {stock} unit(s) of '{item_id}' in stock."
        )

    total_cost = buy_price * quantity

    if not has_funds(cd, total_cost):
        current = get_currency(cd)
        return TransactionResult.fail(
            f"Insufficient funds: need {total_cost}c, have {current}c."
        )

    # -- execute transaction
    spend_currency(cd, total_cost)
    cd.inventory[item_id] = cd.inventory.get(item_id, 0) + quantity
    _reduce_stock(shop, item_id, quantity)

    new_balance = get_currency(cd)
    return TransactionResult.ok(
        message=f"Bought {quantity}x {item_id} for {total_cost}c.",
        item_id=item_id,
        quantity=quantity,
        total_cost=total_cost,
        new_balance=new_balance,
    )
# ===================================================================
# Sell
# ===================================================================


def sell_item(cd, shop_id: str, item_id: str, quantity: int = 1) -> TransactionResult:
    """Attempt to sell *quantity* units of *item_id* to *shop_id*.

    Returns a TransactionResult.  Mutates *cd* only on success.
    """
    shop = get_shop(shop_id)
    if shop is None:
        return TransactionResult.fail(f"Unknown shop: '{shop_id}'.")

    if not item_exists(item_id):
        return TransactionResult.fail(f"Unknown item: '{item_id}'.")

    if not _is_sellable(item_id):
        return TransactionResult.fail(f"'{item_id}' cannot be sold.")

    stock_entry = shop.get("items", {}).get(item_id)
    if stock_entry is None:
        return TransactionResult.fail(
            f"'{item_id}' cannot be sold to '{shop['name']}'."
        )

    sell_price = stock_entry.get("sell_price")
    if sell_price is None:
        return TransactionResult.fail(
            f"'{item_id}' cannot be sold to '{shop['name']}'."
        )

    if quantity <= 0:
        return TransactionResult.fail("Quantity must be positive.")

    owned = cd.inventory.get(item_id, 0)
    if owned < quantity:
        return TransactionResult.fail(
            f"You only have {owned} x {item_id} (need {quantity})."
        )

    total_value = sell_price * quantity

    # -- execute transaction
    cd.inventory[item_id] -= quantity
    if cd.inventory[item_id] <= 0:
        del cd.inventory[item_id]

    add_currency(cd, total_value)

    new_balance = get_currency(cd)
    return TransactionResult.ok(
        message=f"Sold {quantity}x {item_id} for {total_value}c.",
        item_id=item_id,
        quantity=quantity,
        total_cost=total_value,
        new_balance=new_balance,
    )