"""
Rites of Passage — Item & Equipment Definitions

Plain-Python item/equipment data and validation.  No Evennia imports.

Every item/weapon/armor piece is defined by a stable string ID — no DBREFs.
Item definitions are dict-based for easy serialization and future expansion.

Design constraints (Phase 7 foundation only):
    • No full item catalog — only structural definitions exist
    • No shops / economy / loot drops / crafting
    • No consumable effects / durability / quest items beyond type support
    • No combat equipment bonuses — just stat access plumbing
    • No Phase 8+
"""

from world.data.enums import EquipmentSlot, DamageType


# ---------------------------------------------------------------------------
# Item Category
# ---------------------------------------------------------------------------

ITEM_CATEGORIES = [
    "weapon",
    "armor",
    "consumable",
    "quest",
    "misc",
]

EQUIPPABLE_CATEGORIES = {"weapon", "armor"}

STACKABLE_CATEGORIES = {"consumable", "quest", "misc"}

# ---------------------------------------------------------------------------
# Slot → allowed categories
# ---------------------------------------------------------------------------

SLOT_CATEGORIES = {
    EquipmentSlot.MAIN_HAND:     {"weapon"},
    EquipmentSlot.OFF_HAND:      {"weapon"},
    EquipmentSlot.HEAD:          {"armor"},
    EquipmentSlot.CHEST:         {"armor"},
    EquipmentSlot.LEGS:          {"armor"},
    EquipmentSlot.HANDS:         {"armor"},
    EquipmentSlot.FEET:          {"armor"},
    EquipmentSlot.WRISTS:        {"armor"},
    EquipmentSlot.LEFT_FINGER:   {"armor"},
    EquipmentSlot.RIGHT_FINGER:  {"armor"},
    EquipmentSlot.NECK:          {"armor"},
    EquipmentSlot.LEFT_EAR:      {"armor"},
    EquipmentSlot.RIGHT_EAR:     {"armor"},
    EquipmentSlot.WAIST:         {"armor"},
    EquipmentSlot.BACK:          {"armor"},
}


# ---------------------------------------------------------------------------
# Item Definition Helper
# ---------------------------------------------------------------------------


def _make_item_def(
    item_id, category, name,
    stackable=None, slot=None,
    damage_type=None, base_damage=0,
    armor_class=0, max_stack=1,
    **kwargs,
):
    """Construct a consistent item-definition dict."""
    if stackable is None:
        stackable = category in STACKABLE_CATEGORIES

    definition = {
        "item_id": item_id,
        "category": category,
        "name": name,
        "stackable": stackable,
        "max_stack": max_stack if stackable else 1,
        "slot": slot,
    }
    if damage_type is not None:
        definition["damage_type"] = damage_type
        definition["base_damage"] = base_damage
    if armor_class > 0 or category == "armor":
        definition["armor_class"] = armor_class
    definition.update(kwargs)
    return definition


# ---------------------------------------------------------------------------
# Placeholder Item Catalog
# ---------------------------------------------------------------------------

PLACEHOLDER_ITEMS = {
    "rusty_sword": _make_item_def(
        "rusty_sword", "weapon", "Rusty Sword",
        slot=EquipmentSlot.MAIN_HAND.value,
        damage_type=DamageType.SLASHING.value,
        base_damage=5,  # [PLACEHOLDER]
    ),
    "short_bow": _make_item_def(
        "short_bow", "weapon", "Short Bow",
        slot=EquipmentSlot.MAIN_HAND.value,
        damage_type=DamageType.PIERCING.value,
        base_damage=4,  # [PLACEHOLDER]
    ),
    "wooden_club": _make_item_def(
        "wooden_club", "weapon", "Wooden Club",
        slot=EquipmentSlot.MAIN_HAND.value,
        damage_type=DamageType.CONCUSSION.value,
        base_damage=4,  # [PLACEHOLDER]
    ),
    "hunting_whip": _make_item_def(
        "hunting_whip", "weapon", "Hunting Whip",
        slot=EquipmentSlot.MAIN_HAND.value,
        damage_type=DamageType.WHIPPING.value,
        base_damage=3,  # [PLACEHOLDER]
    ),
    "cloth_vest": _make_item_def(
        "cloth_vest", "armor", "Cloth Vest",
        slot=EquipmentSlot.CHEST.value,
        armor_class=2,  # [PLACEHOLDER]
    ),
    "leather_cap": _make_item_def(
        "leather_cap", "armor", "Leather Cap",
        slot=EquipmentSlot.HEAD.value,
        armor_class=1,  # [PLACEHOLDER]
    ),
    "health_potion": _make_item_def(
        "health_potion", "consumable", "Health Potion",
        stackable=True, max_stack=20,
    ),
    "old_letter": _make_item_def(
        "old_letter", "quest", "Old Letter",
        stackable=False,
    ),
    "wooden_plank": _make_item_def(
        "wooden_plank", "misc", "Wooden Plank",
        stackable=True, max_stack=50,
    ),
    "mana_potion": _make_item_def(
        "mana_potion", "consumable", "Mana Potion",
        stackable=True, max_stack=20,
    ),
    "stamina_potion": _make_item_def(
        "stamina_potion", "consumable", "Stamina Potion",
        stackable=True, max_stack=20,
    ),
    "torch": _make_item_def(
        "torch", "misc", "Torch",
        stackable=True, max_stack=10,
    ),
}


# ---------------------------------------------------------------------------
# Item Registry
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Master Item Registry
# ---------------------------------------------------------------------------

ITEM_REGISTRY = dict(PLACEHOLDER_ITEMS)


def _load_mudcentral_catalog():
    """Load the converted MajorMUD catalog into the ROP item registry."""
    import json
    from pathlib import Path

    catalog_path = Path(__file__).with_name("mudcentral_items.json")

    if not catalog_path.exists():
        return

    try:
        with catalog_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError) as err:
        print(f"WARNING: Could not load MudCentral item catalog: {err}")
        return

    items = data.get("items", {})

    if not isinstance(items, dict):
        print("WARNING: MudCentral item catalog has invalid items section.")
        return

    for item_id, source in items.items():
        if not isinstance(source, dict):
            continue

        # If a MudCentral item shares an ID with an existing hand-authored
        # ROP item, keep the ROP gameplay fields authoritative but merge in
        # all MudCentral source/stat fields that are not already present.
        if item_id in ITEM_REGISTRY:
            existing = ITEM_REGISTRY[item_id]

            for key, value in source.items():
                if key not in existing or existing.get(key) in (None, "", []):
                    existing[key] = value

            continue

        category = source.get("category", "misc")

        # Convert imported categories to categories understood by ROP.
        if category not in ITEM_CATEGORIES:
            category = "misc"

        definition = dict(source)

        definition["item_id"] = item_id
        definition["category"] = category
        definition.setdefault("name", item_id.replace("_", " ").title())

        # Current ROP inventory rules.
        if category in EQUIPPABLE_CATEGORIES:
            definition["stackable"] = False
            definition["max_stack"] = 1
        else:
            definition.setdefault("stackable", True)
            definition.setdefault("max_stack", 99)

        # Translate imported equipment slots to ROP slots where possible.
        imported_slot = definition.get("equipment_slot")

        slot_map = {
            "main_hand": "main_hand",
            "off_hand": "off_hand",
            "head": "head",
            "chest": "chest",
            "arms": "arms",
            "hands": "hands",
            "legs": "legs",
            "feet": "feet",
            "back": "back",
            "neck": "neck",
            "waist": "waist",
            "wrist": "wrist",
            "ears": "ears",
            "fingers": "fingers",
            "worn": "worn",
        }

        if category == "weapon":
            definition["slot"] = slot_map.get(
                imported_slot,
                "main_hand",
            )

            # Preserve the real damage range while also supplying the
            # scalar base_damage expected by the current combat code.
            damage_min = definition.get("damage_min")
            damage_max = definition.get("damage_max")

            if isinstance(damage_min, (int, float)) and isinstance(
                damage_max, (int, float)
            ):
                definition["base_damage"] = int(
                    round((damage_min + damage_max) / 2)
                )
            elif isinstance(damage_max, (int, float)):
                definition["base_damage"] = int(damage_max)
            elif isinstance(damage_min, (int, float)):
                definition["base_damage"] = int(damage_min)
            else:
                definition["base_damage"] = 0

            definition.setdefault("damage_type", None)

        elif category == "armor":
            definition["slot"] = slot_map.get(imported_slot)

            armor_ac = definition.get("armor_ac")

            if isinstance(armor_ac, (int, float)):
                definition["armor_class"] = armor_ac
            else:
                definition["armor_class"] = 0

        else:
            definition["slot"] = None

        ITEM_REGISTRY[item_id] = definition


_load_mudcentral_catalog()



# ---------------------------------------------------------------------------
# Item Name → Item ID Index (for loot-table resolution)
# ---------------------------------------------------------------------------

# Built lazily; cleared when ITEM_REGISTRY is mutated externally.
_name_index: dict[str, str] | None = None
_name_index_misses: set[str] = set()


def _build_item_name_index() -> dict[str, str]:
    """Build a case-normalised name → item_id lookup from ITEM_REGISTRY."""
    index: dict[str, str] = {}
    for item_id, definition in ITEM_REGISTRY.items():
        name = str(definition.get("name", "")).strip().lower()
        if name:
            index[name] = item_id
    return index


def resolve_item_name(name: str) -> str | None:
    """Given a raw item name string, return the corresponding ITEM_REGISTRY
    item_id, or None if no match can be found.

    The search is:
        1. Exact case-normalised match.
        2. Normalised match (strip special chars, collapse whitespace).
        3. Fallback: partial-substring match (first deterministic ID wins).

    Unresolved names are tracked for diagnostic reporting.
    """
    global _name_index

    if _name_index is None:
        _name_index = _build_item_name_index()

    name = name.strip()
    if not name:
        return None

    name_lower = name.lower()

    # 1. Exact match.
    item_id = _name_index.get(name_lower)
    if item_id is not None:
        return item_id

    # 2. Normalised match — strip parentheses suffixes, collapse whitespace.
    import re as _re
    normalised = _re.sub(r"\([^)]*\)", "", name_lower)
    normalised = _re.sub(r"\s+", " ", normalised).strip()
    if normalised and normalised != name_lower:
        item_id = _name_index.get(normalised)
        if item_id is not None:
            return item_id

    # 3. Partial match — search through all names.
    for idx_name, idx_id in _name_index.items():
        if name_lower in idx_name or idx_name in name_lower:
            return idx_id

    _name_index_misses.add(name)
    return None


def get_name_index_misses() -> set[str]:
    """Return the set of names that could not be resolved to ITEM_REGISTRY."""
    return set(_name_index_misses)


def clear_name_index() -> None:
    """Clear the cached name index (for test teardown)."""
    global _name_index, _name_index_misses
    _name_index = None
    _name_index_misses = set()
def get_item(item_id):
    """Return the item definition for an item_id, or None."""
    return ITEM_REGISTRY.get(item_id)


def item_exists(item_id):
    """Return True if item_id is a known item definition."""
    return item_id in ITEM_REGISTRY


# ---------------------------------------------------------------------------
# Equipment Validation
# ---------------------------------------------------------------------------


def validate_equip(item_id, slot, equipment, inventory):
    """Return an error string if equipping is invalid, or None if valid."""
    definition = get_item(item_id)
    if definition is None:
        return f"No such item: '{item_id}'."

    category = definition.get("category", "")
    if category not in EQUIPPABLE_CATEGORIES:
        return f"'{item_id}' is not equippable."

    allowed = SLOT_CATEGORIES.get(slot, set())
    if category not in allowed:
        return f"'{item_id}' cannot be equipped in the '{slot.value}' slot."

    current = equipment.get(slot)
    if current == item_id:
        return None  # already equipped — no-op is valid

    if not owns_item(item_id, equipment, inventory):
        return f"You do not have '{item_id}'."

    return None


def owns_item(item_id, equipment, inventory):
    """Return True if the character possesses this item."""
    qty = inventory.get(item_id, 0)
    if qty > 0:
        return True
    for eq_id in equipment.values():
        if eq_id == item_id:
            return True
    return False


def validate_unequip(item_id, slot, equipment):
    """Return an error string if unequipping is invalid, or None if valid."""
    if slot is not None:
        current = equipment.get(slot)
        if current != item_id:
            return f"'{item_id}' is not equipped in the '{slot.value}' slot."
    else:
        found = False
        for eq_id in equipment.values():
            if eq_id == item_id:
                found = True
                break
        if not found:
            return f"'{item_id}' is not equipped."
    return None


# ---------------------------------------------------------------------------
# Stat Accessors
# ---------------------------------------------------------------------------


def get_weapon_damage(item_id):
    """Return the base damage of a weapon, or 0 if not a weapon."""
    definition = get_item(item_id)
    if definition is None or definition.get("category") != "weapon":
        return 0
    return definition.get("base_damage", 0)


def get_weapon_damage_type(item_id):
    """Return the damage type string of a weapon, or None."""
    definition = get_item(item_id)
    if definition is None or definition.get("category") != "weapon":
        return None
    return definition.get("damage_type")


def get_armor_class(item_id):
    """Return the armor class of an armor piece, or 0 if not armor."""
    definition = get_item(item_id)
    if definition is None or definition.get("category") != "armor":
        return 0
    return definition.get("armor_class", 0)
