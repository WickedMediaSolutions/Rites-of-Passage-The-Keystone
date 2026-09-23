"""
Rites of Passage — Mob / NPC Definitions

Static mob definitions and a factory for creating live ``CharacterData``
instances from those definitions.

Mobs reuse the existing ``CharacterData`` model — combat, death, resources,
and equipment all work without any new logic.  Each call to
``create_mob_data()`` produces an independent ``CharacterData`` instance
(no shared mutable state).

Design constraints (Phase 9 foundation only):
    • No autonomous AI
    • No automatic combat rounds
    • No aggro scanning
    • No mob respawning
    • No loot drops
    • No XP/rewards
    • No quests
    • No shops
"""

from world.data.character_data import CharacterData
from world.data.enums import EquipmentSlot, Faction


# ---------------------------------------------------------------------------
# Mob Definition Helper
# ---------------------------------------------------------------------------


def _make_mob_def(
    mob_id: str,
    name: str,
    description: str = "",
    level: int = 1,
    base_stats: dict | None = None,
    max_hp: int = 20,
    max_mana: int = 0,
    max_stamina: int = 0,
    hostile: bool = True,
    faction: Faction = Faction.EVIL,
    equipped_items: dict | None = None,
    xp_reward: int = 0,
    loot_table: list[dict] | None = None,
) -> dict:
    """Construct a consistent mob-definition dict."""
    if base_stats is None:
        base_stats = {"str": 5, "int": 5, "wis": 5, "dex": 5, "con": 5}
    if equipped_items is None:
        equipped_items = {}
    if loot_table is None:
        loot_table = []

    return {
        "mob_id": mob_id,
        "name": name,
        "description": description,
        "level": level,
        "base_stats": dict(base_stats),
        "max_hp": max_hp,
        "max_mana": max_mana,
        "max_stamina": max_stamina,
        "hostile": hostile,
        "faction": faction,
        "equipped_items": dict(equipped_items),
        "xp_reward": xp_reward,
        "loot_table": loot_table,
    }


# ---------------------------------------------------------------------------
# Placeholder Mob Catalog
# ---------------------------------------------------------------------------

# ALL NUMERIC VALUES ARE [PLACEHOLDER] — not final balance.
PLACEHOLDER_MOBS = {
    "giant_rat": _make_mob_def(
        "giant_rat", "Giant Rat",
        description="A filthy, overgrown rat with yellowed fangs.",
        level=1,
        base_stats={"str": 3, "int": 1, "wis": 1, "dex": 8, "con": 4},
        max_hp=8,       # [PLACEHOLDER]
        max_mana=0,     # [PLACEHOLDER]
        max_stamina=10, # [PLACEHOLDER]
        hostile=True,
        faction=Faction.EVIL,
        xp_reward=15,                      # [PLACEHOLDER]
        loot_table=[                       # [PLACEHOLDER]
            {"item_id": "health_potion", "chance": 0.3, "quantity": 1},
        ],
    ),
    "skeleton_warrior": _make_mob_def(
        "skeleton_warrior", "Skeleton Warrior",
        description="An ancient skeleton rattling in rusted armor.",
        level=3,
        base_stats={"str": 8, "int": 2, "wis": 2, "dex": 6, "con": 6},
        max_hp=25,      # [PLACEHOLDER]
        max_mana=0,     # [PLACEHOLDER]
        max_stamina=15, # [PLACEHOLDER]
        hostile=True,
        faction=Faction.EVIL,
        equipped_items={
            EquipmentSlot.MAIN_HAND: "rusty_sword",
            EquipmentSlot.CHEST: "cloth_vest",
        },
        xp_reward=120,                     # [PLACEHOLDER]
        loot_table=[                       # [PLACEHOLDER]
            {"item_id": "rusty_sword", "chance": 0.2, "quantity": 1},
            {"item_id": "health_potion", "chance": 0.4, "quantity": (1, 2)},
        ],
    ),
    "forest_spider": _make_mob_def(
        "forest_spider", "Forest Spider",
        description="A venomous spider the size of a small dog.",
        level=2,
        base_stats={"str": 4, "int": 2, "wis": 3, "dex": 10, "con": 5},
        max_hp=12,      # [PLACEHOLDER]
        max_mana=5,     # [PLACEHOLDER]
        max_stamina=12, # [PLACEHOLDER]
        hostile=True,
        faction=Faction.EVIL,
        xp_reward=50,                      # [PLACEHOLDER]
        loot_table=[                       # [PLACEHOLDER]
            {"item_id": "health_potion", "chance": 1.0, "quantity": 1},
        ],
    ),
    "town_guard": _make_mob_def(
        "town_guard", "Town Guard",
        description="A stern-looking guard keeping watch over the town.",
        level=5,
        base_stats={"str": 10, "int": 5, "wis": 5, "dex": 8, "con": 8},
        max_hp=50,      # [PLACEHOLDER]
        max_mana=10,    # [PLACEHOLDER]
        max_stamina=20, # [PLACEHOLDER]
        hostile=False,
        faction=Faction.GOOD,
        equipped_items={
            EquipmentSlot.MAIN_HAND: "rusty_sword",
            EquipmentSlot.CHEST: "cloth_vest",
            EquipmentSlot.HEAD: "leather_cap",
        },
        xp_reward=300,                     # [PLACEHOLDER]
        loot_table=[],                     # [PLACEHOLDER] guards drop nothing
    ),
    "friendly_merchant": _make_mob_def(
        "friendly_merchant", "Friendly Merchant",
        description="A cheerful merchant hawking his wares.",
        level=1,
        base_stats={"str": 3, "int": 7, "wis": 8, "dex": 5, "con": 4},
        max_hp=15,      # [PLACEHOLDER]
        max_mana=20,    # [PLACEHOLDER]
        max_stamina=10, # [PLACEHOLDER]
        hostile=False,
        faction=Faction.GOOD,
        xp_reward=10,                      # [PLACEHOLDER]
        loot_table=[                       # [PLACEHOLDER]
            {"item_id": "health_potion", "chance": 0.1, "quantity": 1},
        ],
    ),
}


# ---------------------------------------------------------------------------
# Mob Registry
# ---------------------------------------------------------------------------

MOB_REGISTRY = dict(PLACEHOLDER_MOBS)


def _load_mudcentral_monsters() -> None:
    """Load the converted MudCentral MajorMUD monster catalog into ROP."""
    import json
    import re

    from pathlib import Path

    # ---- Parse specials into structured combat properties ------------------
    def _parse_specials(specials: list) -> dict:
        import re as _re
        result: dict = {
            "elemental_resistances": {},
            "poison_immunity": False,
            "dodge_modifier": 0,
            "enslave_level": 0,
            "required_to_hit": 0,
            "damaging_shield": 0,
            "nonliving": False,
            "undead": False,
            "animal": False,
            "freedom": False,
            "antimagic": False,
            "see_hidden": False,
            "illuminte": 0,
            "magebind": False,
            "shock": 0,
            "drain": 0,
            "protection_from_good": 0,
            "shadow_form": False,
            "room_illuminate": 0,
            "guarded_by": [],
            "negate_ability": [],
            "_raw_specials": list(specials),
        }
        resist_map = {"fire": "fire", "cold": "water",
                       "lightning": "air", "water": "water", "stone": "earth"}
        if not specials:
            return result

        for entry in specials:
            parts = [p.strip() for p in str(entry).split(",") if p.strip()]
            for part in parts:
                low = part.lower()
                if "poison immunity" in low:
                    m = _re.search(r"poison immunity\s*\+?(\d+)", low)
                    result["poison_immunity"] = True  # any value = immune
                    continue
                m = _re.match(r"dodge\s*\+(\d+)", low)
                if m:
                    result["dodge_modifier"] = int(m.group(1)); continue
                m = _re.match(r"enslave level\s*(\d+)", low)
                if m:
                    result["enslave_level"] = int(m.group(1)); continue
                m = _re.match(r"required to hit\s*\+(\d+)", low)
                if m:
                    result["required_to_hit"] = int(m.group(1)); continue
                m = _re.match(r"damaging shield\s*\+(\d+)", low)
                if m:
                    result["damaging_shield"] = int(m.group(1)); continue
                if low in ("nonliving", "nonliving +1"):
                    result["nonliving"] = True; continue
                if low == "undead":
                    result["undead"] = True; continue
                if low in ("animal", "animal +1"):
                    result["animal"] = True; continue
                if low == "freedom":
                    result["freedom"] = True; continue
                if low == "antimagic":
                    result["antimagic"] = True; continue
                if low == "see hidden":
                    result["see_hidden"] = True; continue
                if low == "shadowform":
                    result["shadow_form"] = True; continue
                if low == "magebind":
                    result["magebind"] = True; continue
                m = _re.match(r"illuminte\s*\+(\d+)", low)
                if m:
                    result["illuminte"] = int(m.group(1)); continue
                m = _re.match(r"room illuminate\s*([+-]?\d+)", low)
                if m:
                    result["room_illuminate"] = int(m.group(1)); continue
                m = _re.match(r"shock\s*\+(\d+)", low)
                if m:
                    result["shock"] = int(m.group(1)); continue
                m = _re.match(r"drain\s*\+(\d+)", low)
                if m:
                    result["drain"] = int(m.group(1)); continue
                m = _re.match(r"protection from good\s*\+(\d+)", low)
                if m:
                    result["protection_from_good"] = int(m.group(1)); continue
                m = _re.match(r"resist\s+(fire|cold|lightning|water|stone)\s*([+-]\d+)%?", low)
                if m:
                    elem = resist_map.get(m.group(1), m.group(1))
                    result["elemental_resistances"][elem] = int(m.group(2))
                    continue
                if low.startswith("guarded by "):
                    guard = part[len("guarded by "):].strip()
                    if guard:
                        result["guarded_by"].append(guard)
                    continue
                if low.startswith("negate ability "):
                    ability = part[len("negate ability "):].strip().strip('"')
                    if ability:
                        result["negate_ability"].append(ability)
                    continue
        return result

    # ---- Build loot table from imported drops ------------------------------
    def _build_loot_table(drops: list) -> tuple[list[dict], list[str]]:
        from world.data.items import resolve_item_name as _resolve_item_name
        loot: list[dict] = []
        unresolved: list[str] = []
        for drop_entry in (drops or []):
            if not isinstance(drop_entry, dict):
                continue
            drop_name = drop_entry.get("item_name", "").strip()
            if not drop_name:
                continue
            chance_pct = drop_entry.get("chance_percent", 100)
            if isinstance(chance_pct, str):
                chance_pct = float(chance_pct) if chance_pct else 0.0
            chance = max(0.0, min(1.0, float(chance_pct) / 100.0))
            item_id = _resolve_item_name(drop_name)
            if item_id is None:
                unresolved.append(drop_name)
                continue
            loot.append({"item_id": item_id, "chance": chance, "quantity": 1})
        return loot, unresolved

    catalog_path = Path(__file__).with_name("mudcentral_monsters.json")
    if not catalog_path.exists():
        return

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARNING: Could not load MudCentral monsters: {exc}")
        return

    monsters = data.get("monsters", {})
    if isinstance(monsters, list):
        iterable = []
        for index, source in enumerate(monsters, 1):
            if not isinstance(source, dict):
                continue
            source_id = source.get("mob_id") or source.get("id") or f"mudcentral_monster_{index}"
            iterable.append((source_id, source))
    elif isinstance(monsters, dict):
        iterable = monsters.items()
    else:
        return

    def as_int(value, default=0):
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)

        match = re.search(r"-?\d[\d,]*", str(value))
        if not match:
            return default

        try:
            return int(match.group(0).replace(",", ""))
        except ValueError:
            return default

    unresolved_drops: list[str] = []

    for source_id, source in iterable:
        if not isinstance(source, dict):
            continue

        mob_id = str(
            source.get("mob_id")
            or source.get("id")
            or source_id
        ).strip()

        if not mob_id:
            continue

        name = str(source.get("name") or mob_id.replace("_", " ").title())

        # Preserve hand-authored ROP mobs if an ID happens to collide.
        if mob_id in MOB_REGISTRY:
            existing = MOB_REGISTRY[mob_id]
            existing.setdefault("mudcentral_source", dict(source))
            continue

        hp = as_int(
            source.get("hp", source.get("max_hp")),
            20,
        )

        xp = as_int(
            source.get("xp", source.get("xp_reward", source.get("exp"))),
            0,
        )

        level = as_int(source.get("level"), 1)
        if level < 1:
            level = 1

        # The source does not provide ROP STR/INT/WIS/DEX/CON values.
        # Keep neutral defaults rather than inventing MajorMUD stats.
        base_stats = {
            "str": 5,
            "int": 5,
            "wis": 5,
            "dex": 5,
            "con": 5,
        }

        # Parse specials into structured combat properties.
        raw_specials = source.get("special", [])
        parsed_specials = _parse_specials(raw_specials)

        # Build loot table from imported drops.
        imported_drops = source.get("drops", [])
        loot_table, unresolved = _build_loot_table(imported_drops)
        unresolved_drops.extend(unresolved)

        definition = _make_mob_def(
            mob_id=mob_id,
            name=name,
            description=str(
                source.get("description")
                or source.get("special")
                or source.get("notes")
                or ""
            ),
            level=level,
            base_stats=base_stats,
            max_hp=max(1, hp),
            max_mana=0,
            max_stamina=0,
            hostile=True,
            faction=Faction.EVIL,
            equipped_items={},
            xp_reward=max(0, xp),
            loot_table=loot_table,
        )

        # Preserve EVERY converted MajorMUD field on the definition.
        # ROP can progressively consume these fields as its mob/combat
        # systems gain support for them.
        for key, value in source.items():
            if key not in definition:
                definition[key] = value

        definition["mudcentral_source"] = dict(source)

        # Store parsed combat properties under a namespaced key.
        definition["mw_combat"] = parsed_specials

        # Preserve unresolved drops so they are never silently discarded.
        if unresolved:
            definition["unresolved_drops"] = list(unresolved)

        MOB_REGISTRY[mob_id] = definition

    # Print unresolved drop diagnostics.
    if unresolved_drops:
        unique = sorted(set(unresolved_drops))
        print(
            f"WARNING: {len(unique)} MudCentral item names could not be "
            f"resolved to ITEM_REGISTRY entries: "
            f"{', '.join(unique[:20])}{'...' if len(unique) > 20 else ''}"
        )


_load_mudcentral_monsters()


def get_mob_definition(mob_id: str) -> dict | None:
    """Return the static definition dict for a mob_id, or None."""
    return MOB_REGISTRY.get(mob_id)


def mob_exists(mob_id: str) -> bool:
    """Return True if mob_id is a known mob definition."""
    return mob_id in MOB_REGISTRY


def register_mob_definition(
    mob_id: str,
    name: str,
    loot_table_id: str | None = None,
) -> dict:
    """Register or update a mob definition in ``MOB_REGISTRY``.

    Forge NPC bridge: external content systems can declare a mob without
    going through the MudCentral importer or the placeholder catalog.

    Any existing definition fields are preserved; only ``mob_id``, ``name``,
    and ``loot_table_id`` are (re)assigned.  Inline ``loot_table`` entries and
    reward fields (e.g. ``xp_reward``) are left untouched.
    """
    definition = MOB_REGISTRY.get(mob_id)
    if definition is None:
        definition = {}
        MOB_REGISTRY[mob_id] = definition

    definition["mob_id"] = mob_id
    definition["name"] = name
    definition["loot_table_id"] = loot_table_id

    return definition


def get_mob_combat_properties(mob_id: str) -> dict:
    """Return the parsed MudCentral combat properties for a mob_id.

    Returns an empty dict if the mob has no MudCentral combat data
    (e.g., a hand-authored ROP mob).

    Keys include:
        elemental_resistances, poison_immunity, dodge_modifier,
        enslave_level, required_to_hit, damaging_shield, nonliving,
        undead, animal, freedom, antimagic, see_hidden, shock, drain,
        guarded_by, negate_ability, and _raw_specials.
    """
    definition = get_mob_definition(mob_id)
    if definition is None:
        return {}
    return definition.get("mw_combat", {})


# ---------------------------------------------------------------------------
# Mob Factory — creates live CharacterData from definitions
# ---------------------------------------------------------------------------


def create_mob_data(mob_id: str) -> CharacterData | None:
    """Create a fresh, independent ``CharacterData`` instance from a mob
    definition.

    Each call produces a **new** instance — no shared mutable state.
    The returned ``CharacterData`` is immediately compatible with the
    existing combat API (``resolve_attack()``, ``calculate_physical_damage()``,
    etc.).

    Returns ``None`` if ``mob_id`` is not a known definition.
    """
    definition = get_mob_definition(mob_id)
    if definition is None:
        return None

    cd = CharacterData()
    _apply_mob_definition(cd, definition)
    return cd


def _apply_mob_definition(cd: CharacterData, definition: dict) -> None:
    """Populate a CharacterData instance from a mob definition dict."""
    cd.name = definition["name"]
    cd.level = definition["level"]
    cd.base_stats = dict(definition["base_stats"])
    cd.faction = definition["faction"]

    # Synthetic race/profession IDs so the mob is identifiable as a mob.
    cd.race_id = "mob"
    cd.profession_id = definition["mob_id"]

    # Resources — start at full
    cd.max_hp = definition["max_hp"]
    cd.hp = cd.max_hp
    cd.max_mana = definition["max_mana"]
    cd.mana = cd.max_mana
    cd.max_stamina = definition["max_stamina"]
    cd.stamina = cd.max_stamina

    # Equipment — set directly (mobs don't use inventory for starting gear)
    equipped = definition.get("equipped_items", {})
    for slot, item_id in equipped.items():
        cd.equipment[slot] = item_id
