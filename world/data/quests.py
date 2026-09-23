"""
Rites of Passage — Quest Definitions & Service

Static quest definitions are kept separate from per-character quest progress.
Quest progress is stored inside CharacterData.quest_progress.

Design constraints (Phase 13 foundation only):
    • No quest NPC dialogue
    • No quest commands/UI
    • No escort quests
    • No timed quests
    • No daily/repeatable quests
    • No party sharing
    • No shops/economy
    • No Phase 14+
"""

from world.data.economy import add_currency
from world.data.enums import QuestState
from world.data.items import item_exists
from world.data.mob_rewards import get_loot_table, _roll_loot_table
from world.data.mobs import mob_exists
from world.data.progression import award_xp


# ---------------------------------------------------------------------------
# Objective Types
# ---------------------------------------------------------------------------

OBJECTIVE_KILL = "kill"
OBJECTIVE_COLLECT = "collect"
# ---------------------------------------------------------------------------
# Quest Definition Helper
# ---------------------------------------------------------------------------


def _make_quest_def(
    quest_id: str,
    name: str,
    description: str,
    objectives: list[dict],
    xp_reward: int = 0,
    item_rewards: list[dict] | None = None,
    currency_reward: int = 0,
    level_required: int = 1,
    prerequisites: list[str] | None = None,
) -> dict:
    """Construct a consistent quest-definition dict.

    objectives: list of dicts like:
        {"type": "kill", "mob_id": "giant_rat", "count": 5}
        {"type": "collect", "item_id": "health_potion", "count": 3}

    item_rewards: list of dicts like:
        {"item_id": "health_potion", "quantity": 2}
    """
    if item_rewards is None:
        item_rewards = []
    if prerequisites is None:
        prerequisites = []

    return {
        "quest_id": quest_id,
        "name": name,
        "description": description,
        "objectives": objectives,
        "xp_reward": xp_reward,
        "item_rewards": item_rewards,
        "currency_reward": currency_reward,
        "level_required": level_required,
        "prerequisites": prerequisites,
    }
# ---------------------------------------------------------------------------
# Placeholder Quest Catalog
# ---------------------------------------------------------------------------

# ALL VALUES ARE [PLACEHOLDER] — not final balance.

PLACEHOLDER_QUESTS = {
    "rat_slayer": _make_quest_def(
        "rat_slayer",
        "Rat Slayer",
        "[PLACEHOLDER] Kill 3 Giant Rats infesting the cellar.",
        objectives=[
            {"type": OBJECTIVE_KILL, "mob_id": "giant_rat", "count": 3},
        ],
        xp_reward=50,
        item_rewards=[
            {"item_id": "health_potion", "quantity": 2},
        ],
        level_required=1,
    ),
    "bone_collector": _make_quest_def(
        "bone_collector",
        "Bone Collector",
        "[PLACEHOLDER] Defeat 2 Skeleton Warriors and collect a health potion.",
        objectives=[
            {"type": OBJECTIVE_KILL, "mob_id": "skeleton_warrior", "count": 2},
            {"type": OBJECTIVE_COLLECT, "item_id": "health_potion", "count": 1},
        ],
        xp_reward=150,
        item_rewards=[
            {"item_id": "health_potion", "quantity": 1},
            {"item_id": "leather_cap", "quantity": 1},
        ],
        level_required=2,
    ),
    "spider_hunt": _make_quest_def(
        "spider_hunt",
        "Spider Hunt",
        "[PLACEHOLDER] Hunt down 2 Forest Spiders.",
        objectives=[
            {"type": OBJECTIVE_KILL, "mob_id": "forest_spider", "count": 2},
        ],
        xp_reward=100,
        item_rewards=[
            {"item_id": "health_potion", "quantity": 3},
        ],
        level_required=1,
    ),
    "potion_collector": _make_quest_def(
        "potion_collector",
        "Potion Collector",
        "[PLACEHOLDER] Gather 5 health potions.",
        objectives=[
            {"type": OBJECTIVE_COLLECT, "item_id": "health_potion", "count": 5},
        ],
        xp_reward=30,
        item_rewards=[
            {"item_id": "health_potion", "quantity": 2},
        ],
        level_required=1,
    ),
    "guardian_trial": _make_quest_def(
        "guardian_trial",
        "Guardian Trial",
        "[PLACEHOLDER] Defeat a Royal Guard. Requires 'Rat Slayer' completed.",
        objectives=[
            {"type": OBJECTIVE_KILL, "mob_id": "royal_guard", "count": 1},
        ],
        xp_reward=500,
        item_rewards=[
            {"item_id": "rusty_sword", "quantity": 1},
            {"item_id": "health_potion", "quantity": 5},
        ],
        level_required=3,
        prerequisites=["rat_slayer"],
    ),
}
# ---------------------------------------------------------------------------
# Quest Registry
# ---------------------------------------------------------------------------

QUEST_REGISTRY = dict(PLACEHOLDER_QUESTS)


def get_quest(quest_id: str) -> dict | None:
    """Return the static quest definition for quest_id, or None."""
    return QUEST_REGISTRY.get(quest_id)


def quest_exists(quest_id: str) -> bool:
    """Return True if quest_id is a known quest definition."""
    return quest_id in QUEST_REGISTRY


def register_quest_definition(
    quest_id: str,
    name: str,
    description: str = "",
    objectives: list[dict] | None = None,
    xp_reward: int = 0,
    currency_reward: int = 0,
    item_rewards: list[dict] | None = None,
    reward_loot_table_id: str | None = None,
    giver_npc_id: str | None = None,
    turn_in_npc_id: str | None = None,
) -> None:
    """Create or update a quest definition in QUEST_REGISTRY.

    Preserves any existing fields not explicitly provided (e.g. level_required,
    prerequisites from placeholder quests).
    """
    if objectives is None:
        objectives = []
    if item_rewards is None:
        item_rewards = []

    existing = QUEST_REGISTRY.get(quest_id, {})

    QUEST_REGISTRY[quest_id] = {
        **existing,
        "quest_id": quest_id,
        "name": name,
        "description": description,
        "objectives": objectives,
        "xp_reward": xp_reward,
        "currency_reward": currency_reward,
        "item_rewards": item_rewards,
        "reward_loot_table_id": reward_loot_table_id,
        "giver_npc_id": giver_npc_id,
        "turn_in_npc_id": turn_in_npc_id,
    }


# ---------------------------------------------------------------------------
# Quest Progress Helpers
# ---------------------------------------------------------------------------


def _init_quest_progress(quest_id: str) -> dict:
    """Create a fresh progress dict for a newly-accepted quest."""
    quest_def = get_quest(quest_id)
    if quest_def is None:
        return {}
    objectives_progress = {}
    for i, _obj in enumerate(quest_def["objectives"]):
        objectives_progress[str(i)] = 0
    return {
        "state": QuestState.ACTIVE.value,
        "objectives": objectives_progress,
    }


def get_quest_state(cd, quest_id: str) -> QuestState | None:
    """Return the current QuestState for this character+quest, or None if untouched."""
    progress = cd.quest_progress.get(quest_id)
    if progress is None:
        return None
    raw = progress.get("state", "available")
    try:
        return QuestState(raw)
    except ValueError:
        return None


def is_quest_completed(cd, quest_id: str) -> bool:
    """Return True if the quest is marked completed for this character."""
    return get_quest_state(cd, quest_id) == QuestState.COMPLETED


def is_quest_active(cd, quest_id: str) -> bool:
    """Return True if the quest is currently active for this character."""
    return get_quest_state(cd, quest_id) == QuestState.ACTIVE
# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def can_accept(cd, quest_id: str) -> tuple[bool, str]:
    """Return (can_accept: bool, reason: str)."""
    quest_def = get_quest(quest_id)
    if quest_def is None:
        return False, f"Unknown quest: '{quest_id}'."

    # Already completed?
    if is_quest_completed(cd, quest_id):
        return False, f"Quest '{quest_id}' has already been completed."

    # Already active?
    if is_quest_active(cd, quest_id):
        return False, f"Quest '{quest_id}' is already active."

    # Level requirement
    if cd.level < quest_def.get("level_required", 1):
        return False, (
            f"Requires level {quest_def['level_required']} "
            f"(you are level {cd.level})."
        )

    # Prerequisites
    for prereq_id in quest_def.get("prerequisites", []):
        if not is_quest_completed(cd, prereq_id):
            prereq_def = get_quest(prereq_id)
            prereq_name = prereq_def["name"] if prereq_def else prereq_id
            return False, f"Requires quest '{prereq_name}' to be completed first."

    return True, ""


def can_abandon(cd, quest_id: str) -> tuple[bool, str]:
    """Return (can_abandon: bool, reason: str)."""
    quest_def = get_quest(quest_id)
    if quest_def is None:
        return False, f"Unknown quest: '{quest_id}'."

    if is_quest_completed(cd, quest_id):
        return False, f"Quest '{quest_id}' is already completed — cannot abandon."

    if not is_quest_active(cd, quest_id):
        return False, f"Quest '{quest_id}' is not active."

    return True, ""


def can_complete(cd, quest_id: str) -> tuple[bool, str]:
    """Return (can_complete: bool, reason: str)."""
    quest_def = get_quest(quest_id)
    if quest_def is None:
        return False, f"Unknown quest: '{quest_id}'."

    if is_quest_completed(cd, quest_id):
        return False, f"Quest '{quest_id}' has already been completed."

    if not is_quest_active(cd, quest_id):
        return False, f"Quest '{quest_id}' is not active."

    # Check each objective
    progress = cd.quest_progress.get(quest_id, {})
    obj_progress = progress.get("objectives", {})
    for i, obj in enumerate(quest_def["objectives"]):
        current = obj_progress.get(str(i), 0)
        required = obj["count"]
        if current < required:
            obj_type = obj["type"]
            target = obj.get("mob_id") or obj.get("item_id")
            return False, (
                f"Objective {i+1}: {obj_type} '{target}' — "
                f"{current}/{required} completed."
            )

    return True, ""
# ---------------------------------------------------------------------------
# Quest Actions
# ---------------------------------------------------------------------------


def accept_quest(cd, quest_id: str) -> tuple[bool, str]:
    """Accept a quest.  Returns (success: bool, message: str)."""
    ok, reason = can_accept(cd, quest_id)
    if not ok:
        return False, reason

    quest_def = get_quest(quest_id)
    cd.quest_progress[quest_id] = _init_quest_progress(quest_id)
    return True, f"Quest accepted: '{quest_def['name']}'."


def abandon_quest(cd, quest_id: str) -> tuple[bool, str]:
    """Abandon an active quest.  Returns (success: bool, message: str)."""
    ok, reason = can_abandon(cd, quest_id)
    if not ok:
        return False, reason

    quest_def = get_quest(quest_id)
    cd.quest_progress.pop(quest_id, None)
    return True, f"Quest abandoned: '{quest_def['name']}'."


def complete_quest(cd, quest_id: str) -> tuple[bool, str]:
    """Complete a quest and grant rewards.  Returns (success: bool, message: str)."""
    ok, reason = can_complete(cd, quest_id)
    if not ok:
        return False, reason

    quest_def = get_quest(quest_id)

    # Grant XP reward
    xp_awarded = quest_def.get("xp_reward", 0)
    if xp_awarded > 0:
        award_xp(cd, xp_awarded)

    # Grant item rewards
    items_granted = []
    for reward in quest_def.get("item_rewards", []):
        item_id = reward["item_id"]
        quantity = reward.get("quantity", 1)
        if item_exists(item_id):
            cd.add_item(item_id, quantity)
            items_granted.append(f"{quantity}x {item_id}")

    # Grant loot-table reward (rolled from registered loot table)
    loot_table_id = quest_def.get("reward_loot_table_id")
    if loot_table_id:
        loot_table = get_loot_table(loot_table_id)
        if loot_table:
            drops = _roll_loot_table(loot_table)
            for drop in drops:
                drop_item_id = drop["item_id"]
                drop_qty = drop.get("quantity", 1)
                if item_exists(drop_item_id):
                    cd.add_item(drop_item_id, drop_qty)
                    items_granted.append(f"{drop_qty}x {drop_item_id}")

    # Grant currency reward
    currency_reward = quest_def.get("currency_reward", 0)
    if currency_reward > 0:
        add_currency(cd, currency_reward)

    # Mark as completed
    cd.quest_progress[quest_id]["state"] = QuestState.COMPLETED.value

    msg = f"Quest completed: '{quest_def['name']}'! Awarded {xp_awarded} XP."
    if items_granted:
        msg += f" Items: {', '.join(items_granted)}."
    if currency_reward > 0:
        msg += f" Currency: {currency_reward}c."
    return True, msg
# ---------------------------------------------------------------------------
# Objective Tracking
# ---------------------------------------------------------------------------


def update_kill_objective(cd, mob_id: str) -> list[str]:
    """Notify quest system that a mob was killed.

    Increments kill-objective counts for all active quests that track mob_id.
    Returns a list of quest_ids whose objectives were updated.

    Does NOT auto-complete quests — that is a separate call.
    """
    updated = []
    for quest_id, progress in list(cd.quest_progress.items()):
        if progress.get("state") != QuestState.ACTIVE.value:
            continue

        quest_def = get_quest(quest_id)
        if quest_def is None:
            continue

        obj_progress = progress.get("objectives", {})
        for i, obj in enumerate(quest_def["objectives"]):
            if obj["type"] != OBJECTIVE_KILL:
                continue
            if obj.get("mob_id") != mob_id:
                continue

            key = str(i)
            current = obj_progress.get(key, 0)
            required = obj["count"]
            if current < required:
                obj_progress[key] = current + 1
                updated.append(quest_id)

    return updated


def update_collect_objective(cd, item_id: str, quantity: int = 1) -> list[str]:
    """Notify quest system that items were collected.

    Looks at current inventory count of item_id and updates collect-objective
    counts for all active quests that track item_id.

    This is called after the item has been added to inventory.

    Returns a list of quest_ids whose objectives were updated.
    """
    updated = []
    for quest_id, progress in list(cd.quest_progress.items()):
        if progress.get("state") != QuestState.ACTIVE.value:
            continue

        quest_def = get_quest(quest_id)
        if quest_def is None:
            continue

        obj_progress = progress.get("objectives", {})
        for i, obj in enumerate(quest_def["objectives"]):
            if obj["type"] != OBJECTIVE_COLLECT:
                continue
            if obj.get("item_id") != item_id:
                continue

            key = str(i)
            required = obj["count"]
            # Collect progress is based on what the player currently has,
            # capped at the required count.
            current_inventory = cd.inventory.get(item_id, 0)
            current_inventory = min(current_inventory, required)
            obj_progress[key] = current_inventory
            updated.append(quest_id)

    return updated


def get_objective_progress(cd, quest_id: str) -> list[dict]:
    """Return a list of {type, target, current, required} for each objective."""
    quest_def = get_quest(quest_id)
    if quest_def is None:
        return []

    progress = cd.quest_progress.get(quest_id)
    if progress is None:
        return []  # quest not yet accepted

    obj_progress = progress.get("objectives", {})

    result = []
    for i, obj in enumerate(quest_def["objectives"]):
        target = obj.get("mob_id") or obj.get("item_id") or "unknown"
        current = obj_progress.get(str(i), 0)
        result.append({
            "type": obj["type"],
            "target": target,
            "current": current,
            "required": obj["count"],
        })
    return result