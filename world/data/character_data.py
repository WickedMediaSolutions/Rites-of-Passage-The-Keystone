"""
Rites of Passage — Character Data Handler

Centralised character data management.  The Character typeclass delegates
game-data operations here so combat, progression, resources, and stats
all read from a single authoritative sorce.

This module does NOT import Evennia — it is plain Python so it can be
unit-tested without a running server.
"""

import random

from world.data.constants import (
    STARTING_LEVEL,
    STARTING_STAT_VARIANCE,
    MAX_STAT_REROLLS,
    RESPAWN_HP_PERCENT,
    RESPAWN_MANA_PERCENT,
    RESPAWN_STAMINA_PERCENT,
    DEATH_XP_PENALTY_PERCENT,
)
from world.data.enums import CharacterState, EquipmentSlot, Faction, Stat


class CharacterData:
    """
    Owns all gameplay data for a single character.
    Intended to be instatiated once and attached to the Character
    typeclass via `.game_data` or simlar.
    """

    def __init__(self):
        # identity
        self.name: str = ""
        self.race_id: str = ""
        self.profession_id: str = ""
        self.faction: Faction | None = None

        # progression
        self.level: int = STARTING_LEVEL
        self.xp: int = 0
        self.tutorial_completed: bool = False

        # core stats
        self.base_stats: dict[str, int] = {
            "str": 0, "int": 0, "wis": 0, "dex": 0, "con": 0,
        }

        # resources
        self.hp: int = 0
        self.max_hp: int = 1
        self.mana: int = 0
        self.max_mana: int = 1
        self.stamina: int = 0
        self.max_stamina: int = 1

        # state
        self.state: CharacterState = CharacterState.STANDING

        # skill/spel unlocks
        self.unlocked_skills: set[str] = set()
        self.proficiencies: dict[str, int] = {}

        # PvP
        self.war_points: int = 0
        self.pvp_kills: int = 0
        self.pvp_deaths: int = 0

        # affiliations
        self.guild_id: str | None = None
        self.sect_id: str | None = None

        # preferences
        self.auto_loot: bool = False
        self.ignore_list: set[str] = set()

        # inventory & equipment
        # inventory: item_id -> quantity
        self.inventory: dict[str, int] = {}
        # equipment: slot -> item_id (None = empty)
        self.equipment: dict[EquipmentSlot, str | None] = {
            slot: None for slot in EquipmentSlot
        }

        # quest progress — quest_id -> {state, objectives: {idx: count}}
        self.quest_progress: dict[str, dict] = {}

        # currency — stored as integer (copper pieces)
        self.currency: int = 0

    # ==================================================================
    # Factory
    # ==================================================================

    @classmethod
    def create(cls, name: str, race_data: dict, prof_data: dict) -> "CharacterData":
        """Create fresh CharacterData for a new Lv-1 character."""
        cd = cls()
        cd.name = name
        cd.race_id = race_data["name"].lower().replace(" ", "_")
        cd.faction = race_data["faction"]
        cd.profession_id = prof_data["name"].lower().replace(" ", "_")
        cd._roll_stats(race_data)
        return cd

    def _roll_stats(self, race_data: dict) -> None:
        """Re-roll base stats from racial base +- variance."""
        base = race_data.get("base_stats", {})
        limits = race_data.get("stat_limits", {})
        stats = {}
        variance = STARTING_STAT_VARIANCE
        for key in ("str", "int", "wis", "dex", "con"):
            racial = base.get(key, 20)
            low = max(1, racial - variance)
            high = racial + variance
            rolled = random.randint(low, high)
            limit = limits.get(key)
            if limit is not None:
                rolled = min(rolled, limit)
            stats[key] = rolled
        self.base_stats = stats

    # ==================================================================
    # Stat access
    # ==================================================================

    def get_stat(self, stat: Stat | str) -> int:
        """Return BASE stat value."""
        key = stat.value if isinstance(stat, Stat) else stat
        return self.base_stats.get(key, 0)

    def effective_stat(self, stat: Stat | str,
                        _equipment=None, _buffs=None) -> int:
        """Return EFFECTIVE stat (base + equipment + buffs). Stub."""
        return self.get_stat(stat)

    # ==================================================================
    # Resources
    # ==================================================================

    def heal(self, amount: int) -> int:
        """Add HP, clamped to max. Returns actual healed."""
        if self.hp <= 0 or self.hp >= self.max_hp:
            return 0
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    def take_damage(self, amount: int) -> bool:
        """Apply raw damage. Returns True if killed."""
        self.hp = max(0, self.hp - amount)
        return self.hp <= 0

    def restore_mana(self, amount: int) -> int:
        """Restore mana, clamped to max."""
        if self.mana >= self.max_mana:
            return 0
        actual = min(amount, self.max_mana - self.mana)
        self.mana += actual
        return actual

    def restore_stamina(self, amount: int) -> int:
        """Restore stamina, clamped to max."""
        if self.stamina >= self.max_stamina:
            return 0
        actual = min(amount, self.max_stamina - self.stamina)
        self.stamina += actual
        return actual

    def is_alive(self) -> bool:
        return self.hp > 0

    # ==================================================================
    # Death / Respawn
    # ==================================================================

    def die(self) -> None:
        """Set character to dead state — authoritative data-layer death.

        All death paths (combat, commands, environment, etc.) MUST route
        through this single method so that death behaviour is consistent
        and no competing death logic exists.
        """
        self.state = CharacterState.DEAD
        self.hp = 0

    def respawn_restore(self) -> None:
        """Restore resources to respawn percentages."""
        self.hp = max(1, self.max_hp * RESPAWN_HP_PERCENT // 100)
        self.mana = self.max_mana * RESPAWN_MANA_PERCENT // 100
        self.stamina = self.max_stamina * RESPAWN_STAMINA_PERCENT // 100
        self.state = CharacterState.STANDING
    def calc_death_xp_penalty(self, xp_toward_next: int) -> int:
        """Return XP loss for death (5% of progress toward next level)."""
        return int(xp_toward_next * DEATH_XP_PENALTY_PERCENT / 100)

    # ==================================================================
    # Inventory & Equipment
    # ==================================================================

    def add_item(self, item_id: str, quantity: int = 1) -> int:
        """Add items to inventory.  Returns the quantity actually added.

        Validation:
            • item_id must be a known item definition.
            • quantity must be > 0.
            • Non-stackable items cap at 1; stackable items cap at max_stack.
            • If the item is already in inventory (non-stackable), returns 0.
        """
        from world.data.items import get_item as _get_item

        if quantity <= 0:
            return 0

        definition = _get_item(item_id)
        if definition is None:
            return 0

        current = self.inventory.get(item_id, 0)

        if not definition.get("stackable", False):
            if current >= 1:
                return 0  # non-stackable, already owned
            self.inventory[item_id] = 1
            return 1

        max_stack = definition.get("max_stack", 1)
        can_add = min(quantity, max_stack - current)
        if can_add <= 0:
            return 0
        self.inventory[item_id] = current + can_add
        return can_add

    def remove_item(self, item_id: str, quantity: int = 1) -> int:
        """Remove items from inventory.  Returns the quantity actually removed.

        Does NOT unequip — if the item is worn, it stays equipped.
        Uses take_damage-style semantics: returns actual count removed.
        """
        if quantity <= 0:
            return 0

        current = self.inventory.get(item_id, 0)
        if current <= 0:
            return 0

        removed = min(quantity, current)
        new_qty = current - removed
        if new_qty <= 0:
            del self.inventory[item_id]
        else:
            self.inventory[item_id] = new_qty
        return removed

    def has_item(self, item_id: str) -> bool:
        """Return True if this item is in inventory or equipped."""
        if self.inventory.get(item_id, 0) > 0:
            return True
        for eq_id in self.equipment.values():
            if eq_id == item_id:
                return True
        return False

    def get_item_qty(self, item_id: str) -> int:
        """Return total owned quantity (inventory only, not counting equipped)."""
        return self.inventory.get(item_id, 0)

    def equip(self, item_id: str, slot: EquipmentSlot) -> str | None:
        """Equip an item into a slot.  Returns None on success, or an error string.

        Moves the item from inventory to the equipment slot.
        If the slot is already occupied, the old item is unequipped first
        (returned to inventory).
        """
        from world.data.items import validate_equip as _validate_equip

        error = _validate_equip(item_id, slot, self.equipment, self.inventory)
        if error is not None:
            return error

        # Already equipped here — no-op.
        if self.equipment.get(slot) == item_id:
            return None

        # Unequip whatever is currently in this slot first.
        current = self.equipment.get(slot)
        if current is not None:
            self.add_item(current, 1)

        # Move the item from inventory to the slot.
        self.remove_item(item_id, 1)
        self.equipment[slot] = item_id
        return None

    def unequip(self, item_id: str, slot: EquipmentSlot | None = None) -> str | None:
        """Unequip an item.  Returns None on success, or an error string.

        The item goes back to inventory.
        """
        from world.data.items import validate_unequip as _validate_unequip

        error = _validate_unequip(item_id, slot, self.equipment)
        if error is not None:
            return error

        if slot is not None:
            self.equipment[slot] = None
        else:
            # Find and clear any slot holding this item.
            for eq_slot, eq_id in list(self.equipment.items()):
                if eq_id == item_id:
                    self.equipment[eq_slot] = None
                    break

        self.add_item(item_id, 1)
        return None

    def get_equipment(self, slot: EquipmentSlot) -> str | None:
        """Return the item_id equipped in the given slot, or None."""
        return self.equipment.get(slot)

    # ==================================================================
    # Persistence — read/write from a dict of serialisable values.
    # The Evennia typeclass calls these to bridge between db attributes
    # and the plain-Python data object.
    # ==================================================================

    def to_dict(self) -> dict:
        """Export all persistent fields to a json-safe dict."""
        return {
            "race_id": self.race_id,
            "profession_id": self.profession_id,
            "faction": self.faction.value if self.faction else None,
            "level": self.level,
            "xp": self.xp,
            "tutorial_completed": self.tutorial_completed,
            "base_stats": dict(self.base_stats),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "state": self.state.value if self.state else None,
            "unlocked_skills": sorted(self.unlocked_skills),
            "proficiencies": dict(self.proficiencies),
            "war_points": self.war_points,
            "pvp_kills": self.pvp_kills,
            "pvp_deaths": self.pvp_deaths,
            "guild_id": self.guild_id,
            "sect_id": self.sect_id,
            "auto_loot": self.auto_loot,
            "ignore_list": sorted(self.ignore_list),
            # inventory — item_id -> quantity
            "inventory": dict(self.inventory),
            # equipment — slot value -> item_id or None
            "equipment": {
                slot.value: item_id
                for slot, item_id in self.equipment.items()
            },
            # quest progress — quest_id -> progress dict
            "quest_progress": dict(self.quest_progress),
            # currency
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterData":
        """Restore from a dict previously produced by to_dict()."""
        cd = cls()
        cd.race_id = data.get("race_id", "")
        cd.profession_id = data.get("profession_id", "")
        faction_raw = data.get("faction")
        cd.faction = Faction(faction_raw) if faction_raw else None
        cd.level = data.get("level", STARTING_LEVEL)
        cd.xp = data.get("xp", 0)
        cd.tutorial_completed = data.get("tutorial_completed", False)
        cd.base_stats = dict(data.get("base_stats", {}))
        cd.hp = data.get("hp", 0)
        cd.max_hp = data.get("max_hp", 1)
        cd.mana = data.get("mana", 0)
        cd.max_mana = data.get("max_mana", 1)
        cd.stamina = data.get("stamina", 0)
        cd.max_stamina = data.get("max_stamina", 1)
        state_raw = data.get("state")
        cd.state = CharacterState(state_raw) if state_raw else CharacterState.STANDING
        cd.unlocked_skills = set(data.get("unlocked_skills", []))
        cd.proficiencies = dict(data.get("proficiencies", {}))
        cd.war_points = data.get("war_points", 0)
        cd.pvp_kills = data.get("pvp_kills", 0)
        cd.pvp_deaths = data.get("pvp_deaths", 0)
        cd.guild_id = data.get("guild_id")
        cd.sect_id = data.get("sect_id")
        cd.auto_loot = data.get("auto_loot", False)
        cd.ignore_list = set(data.get("ignore_list", []))

        # inventory & equipment
        cd.inventory = dict(data.get("inventory", {}))
        raw_eq = data.get("equipment", {})
        cd.equipment = {}
        for slot in EquipmentSlot:
            cd.equipment[slot] = raw_eq.get(slot.value)

        # quest progress
        cd.quest_progress = dict(data.get("quest_progress", {}))
        # currency
        cd.currency = data.get("currency", 0)
        return cd

    @classmethod
    def create_from_race_profession(
        cls, name: str, race_id: str, profession_id: str,
    ) -> "CharacterData":
        """Shortcut: create from stable race/profession IDs (used by chargen)."""
        from world.data.races import RACES
        from world.data.professions import PROFESSIONS

        race_data = RACES[race_id]
        prof_data = PROFESSIONS[profession_id]
        cd = cls.create(name, race_data, prof_data)

        # Override race/profession IDs with the stable keys.
        cd.race_id = race_id
        cd.profession_id = profession_id

        return cd
