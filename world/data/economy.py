"""
Rites of Passage — Economy & Currency Module

Currency operations and structured transaction results for the Phase 14
economy foundation.  Currency is stored as a single integer (copper pieces)
on CharacterData.currency — denominations are for presentation only.

Design constraints (Phase 14 foundation):
    • Persistent character currency
    • Add / spend / check balance with negative-balance prevention
    • Structured TransactionResult for buy/sell feedback
    • No dynamic economy / haggle / banking / auction house / player trading
    • No Phase 15+
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Denominations (for display / conversion — storage is always copper)
# ---------------------------------------------------------------------------

# All conversion constants are [PLACEHOLDER] pending final game-design tuning.
COPPER_PER_SILVER = 100         # [PLACEHOLDER]
COPPER_PER_GOLD = 10_000        # [PLACEHOLDER]
COPPER_PER_PLATINUM = 1_000_000 # [PLACEHOLDER]

DENOMINATIONS = [
    ("platinum", COPPER_PER_PLATINUM),
    ("gold",     COPPER_PER_GOLD),
    ("silver",   COPPER_PER_SILVER),
    ("copper",   1),
]


def to_display(amount: int) -> str:
    """Convert a copper-piece integer to a human-readable string.

    Example:  12_345 → '1g 2s 3s 45c'  (exact split is place-holder logic).
    """
    if amount == 0:
        return "0c"
    parts = []
    remaining = amount
    for name, denom in DENOMINATIONS:
        count = remaining // denom
        if count > 0:
            abbr = name[0]  # p / g / s / c
            parts.append(f"{count}{abbr}")
            remaining %= denom
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Currency Operations on CharacterData
# ---------------------------------------------------------------------------


def get_currency(cd) -> int:
    """Return the character's current currency balance (copper)."""
    return cd.currency


def has_funds(cd, amount: int) -> bool:
    """Return True if the character has at least *amount* copper."""
    if amount < 0:
        return False
    return cd.currency >= amount


def add_currency(cd, amount: int) -> int:
    """Add copper to the character's balance.

    Returns the new balance.  Negative amounts and zero are rejected — use
    spend_currency to subtract.
    """
    if amount <= 0:
        raise ValueError("add_currency requires a positive amount.")
    cd.currency += amount
    return cd.currency


def spend_currency(cd, amount: int) -> int:
    """Subtract copper from the character's balance.

    Raises ValueError if amount <= 0 or the character cannot afford it.
    Returns the new balance.
    """
    if amount <= 0:
        raise ValueError("spend_currency requires a positive amount.")
    if cd.currency < amount:
        raise ValueError(
            f"Insufficient funds: need {amount}c, have {cd.currency}c."
        )
    cd.currency -= amount
    return cd.currency


# ---------------------------------------------------------------------------
# Transaction Result
# ---------------------------------------------------------------------------


@dataclass
class TransactionResult:
    """Structured result returned by every buy / sell operation."""

    success: bool
    message: str
    item_id: str = ""
    quantity: int = 0
    total_cost: int = 0
    new_balance: int = 0

    @staticmethod
    def ok(
        message: str = "Transaction complete.",
        item_id: str = "",
        quantity: int = 0,
        total_cost: int = 0,
        new_balance: int = 0,
    ) -> "TransactionResult":
        return TransactionResult(
            success=True,
            message=message,
            item_id=item_id,
            quantity=quantity,
            total_cost=total_cost,
            new_balance=new_balance,
        )

    @staticmethod
    def fail(message: str) -> "TransactionResult":
        return TransactionResult(success=False, message=message)