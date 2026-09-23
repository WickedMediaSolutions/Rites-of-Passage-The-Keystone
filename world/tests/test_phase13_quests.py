"""
Phase 13 -- Quest Foundation Tests
"""
import json
import unittest

from world.data.character_data import CharacterData
from world.data.enums import QuestState
from world.data.quests import (
    QUEST_REGISTRY,
    get_quest,
    quest_exists,
    OBJECTIVE_KILL,
    OBJECTIVE_COLLECT,
    get_quest_state,
    is_quest_completed,
    is_quest_active,
    can_accept,
    can_abandon,
    can_complete,
    accept_quest,
    abandon_quest,
    complete_quest,
    update_kill_objective,
    update_collect_objective,
    get_objective_progress,
)


def _make_player(name="Hero", race="human", prof="warrior"):
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.max_hp = 100; cd.hp = 100
    cd.max_mana = 100; cd.mana = 100
    cd.max_stamina = 100; cd.stamina = 100
    return cd

# =========================================================================
# Quest Registry & Definitions
# =========================================================================


class TestQuestRegistry(unittest.TestCase):

    def test_quest_registry_exists(self):
        self.assertIsInstance(QUEST_REGISTRY, dict)
        self.assertGreater(len(QUEST_REGISTRY), 0)

    def test_get_quest_valid(self):
        q = get_quest("rat_slayer")
        self.assertIsNotNone(q)
        self.assertEqual(q["quest_id"], "rat_slayer")
        self.assertEqual(q["name"], "Rat Slayer")

    def test_get_quest_invalid(self):
        self.assertIsNone(get_quest("nonexistent_quest"))

    def test_quest_exists_true(self):
        self.assertTrue(quest_exists("rat_slayer"))

    def test_quest_exists_false(self):
        self.assertFalse(quest_exists("nonexistent_quest"))

    def test_all_quests_have_required_fields(self):
        for qid, qdef in QUEST_REGISTRY.items():
            with self.subTest(qid=qid):
                self.assertIn("quest_id", qdef)
                self.assertIn("name", qdef)
                self.assertIn("description", qdef)
                self.assertIn("objectives", qdef)
                self.assertIsInstance(qdef["objectives"], list)
                self.assertIn("xp_reward", qdef)
                self.assertIn("item_rewards", qdef)
                self.assertIn("level_required", qdef)
                self.assertIsInstance(qdef["prerequisites"], list)

    def test_all_objectives_have_valid_type(self):
        for qid, qdef in QUEST_REGISTRY.items():
            for i, obj in enumerate(qdef["objectives"]):
                with self.subTest(qid=qid, obj_index=i):
                    self.assertIn(obj["type"], [OBJECTIVE_KILL, OBJECTIVE_COLLECT])
                    self.assertIn("count", obj)
                    self.assertGreater(obj["count"], 0)
                    if obj["type"] == OBJECTIVE_KILL:
                        self.assertIn("mob_id", obj)
                    elif obj["type"] == OBJECTIVE_COLLECT:
                        self.assertIn("item_id", obj)

    def test_quest_definitions_are_json_serializable(self):
        for qid, qdef in QUEST_REGISTRY.items():
            with self.subTest(qid=qid):
                s = json.dumps(qdef)
                restored = json.loads(s)
                self.assertEqual(restored["quest_id"], qdef["quest_id"])


# =========================================================================
# Quest State Transitions
# =========================================================================


class TestQuestStateTransitions(unittest.TestCase):

    def test_initial_state_none(self):
        p = _make_player()
        self.assertIsNone(get_quest_state(p, "rat_slayer"))

    def test_accept_moves_to_active(self):
        p = _make_player()
        ok, msg = accept_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertEqual(get_quest_state(p, "rat_slayer"), QuestState.ACTIVE)

    def test_abandon_moves_to_none(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        ok, msg = abandon_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertIsNone(get_quest_state(p, "rat_slayer"))

    def test_cannot_abandon_unaccepted(self):
        p = _make_player()
        ok, _ = can_abandon(p, "rat_slayer")
        self.assertFalse(ok)

    def test_complete_moves_to_completed(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        ok, msg = complete_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertEqual(get_quest_state(p, "rat_slayer"), QuestState.COMPLETED)

    def test_is_quest_completed(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        self.assertTrue(is_quest_completed(p, "rat_slayer"))

    def test_is_quest_active(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        self.assertTrue(is_quest_active(p, "rat_slayer"))
        self.assertFalse(is_quest_completed(p, "rat_slayer"))


# =========================================================================
# Acceptance Validation
# =========================================================================


class TestAcceptValidation(unittest.TestCase):

    def test_accept_valid_quest(self):
        p = _make_player()
        ok, msg = can_accept(p, "rat_slayer")
        self.assertTrue(ok)

    def test_accept_invalid_quest_id(self):
        p = _make_player()
        ok, msg = can_accept(p, "does_not_exist")
        self.assertFalse(ok)
        self.assertIn("Unknown", msg)

    def test_accept_already_completed(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        ok, msg = can_accept(p, "rat_slayer")
        self.assertFalse(ok)
        self.assertIn("already been completed", msg)

    def test_accept_already_active(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        ok, msg = can_accept(p, "rat_slayer")
        self.assertFalse(ok)
        self.assertIn("already active", msg)

    def test_accept_level_too_low(self):
        p = _make_player()
        p.level = 1
        ok, msg = can_accept(p, "bone_collector")
        self.assertFalse(ok)
        self.assertIn("Requires level", msg)

    def test_accept_level_high_enough(self):
        p = _make_player()
        p.level = 5
        ok, msg = can_accept(p, "bone_collector")
        self.assertTrue(ok)

    def test_accept_missing_prerequisite(self):
        p = _make_player()
        p.level = 5
        ok, msg = can_accept(p, "guardian_trial")
        self.assertFalse(ok)
        self.assertIn("Rat Slayer", msg)

    def test_accept_with_prerequisite_completed(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        ok, msg = can_accept(p, "guardian_trial")
        self.assertTrue(ok)

    def test_accept_sets_objective_progress(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        progress = p.quest_progress["rat_slayer"]
        self.assertEqual(progress["state"], "active")
        self.assertIn("0", progress["objectives"])
        self.assertEqual(progress["objectives"]["0"], 0)

    def test_accept_multi_objective_progress(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        progress = p.quest_progress["bone_collector"]
        self.assertEqual(progress["state"], "active")
        self.assertIn("0", progress["objectives"])
        self.assertIn("1", progress["objectives"])
        self.assertEqual(progress["objectives"]["0"], 0)
        self.assertEqual(progress["objectives"]["1"], 0)


# =========================================================================
# Abandonment
# =========================================================================


class TestAbandonment(unittest.TestCase):

    def test_abandon_removes_progress(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        self.assertIn("rat_slayer", p.quest_progress)
        abandon_quest(p, "rat_slayer")
        self.assertNotIn("rat_slayer", p.quest_progress)

    def test_cannot_abandon_completed(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        ok, msg = can_abandon(p, "rat_slayer")
        self.assertFalse(ok)

    def test_cannot_abandon_invalid_id(self):
        p = _make_player()
        ok, msg = can_abandon(p, "nonexistent")
        self.assertFalse(ok)
        self.assertIn("Unknown", msg)

    def test_abandon_then_reaccept(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        abandon_quest(p, "rat_slayer")
        ok, msg = can_accept(p, "rat_slayer")
        self.assertTrue(ok)
        ok2, _ = accept_quest(p, "rat_slayer")
        self.assertTrue(ok2)

    def test_abandon_resets_objective_progress_on_reaccept(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 2
        abandon_quest(p, "rat_slayer")
        accept_quest(p, "rat_slayer")
        self.assertEqual(p.quest_progress["rat_slayer"]["objectives"]["0"], 0)


# =========================================================================
# Kill Objective Tracking
# =========================================================================


class TestKillObjectives(unittest.TestCase):

    def test_kill_updates_correct_quest(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        updated = update_kill_objective(p, "giant_rat")
        self.assertIn("rat_slayer", updated)
        self.assertEqual(p.quest_progress["rat_slayer"]["objectives"]["0"], 1)

    def test_kill_does_not_overcount(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        updated = update_kill_objective(p, "giant_rat")
        self.assertNotIn("rat_slayer", updated)
        self.assertEqual(p.quest_progress["rat_slayer"]["objectives"]["0"], 3)

    def test_kill_only_updates_active_quests(self):
        p = _make_player()
        updated = update_kill_objective(p, "giant_rat")
        self.assertEqual(updated, [])

    def test_kill_does_not_update_completed_quests(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        updated = update_kill_objective(p, "giant_rat")
        self.assertNotIn("rat_slayer", updated)

    def test_kill_different_mob_not_counted(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        updated = update_kill_objective(p, "skeleton_warrior")
        self.assertNotIn("rat_slayer", updated)
        self.assertEqual(p.quest_progress["rat_slayer"]["objectives"]["0"], 0)

    def test_kill_progresses_to_required(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        for i in range(3):
            update_kill_objective(p, "giant_rat")
        self.assertEqual(p.quest_progress["rat_slayer"]["objectives"]["0"], 3)

    def test_multi_kill_objectives_tracked(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        updated = update_kill_objective(p, "skeleton_warrior")
        self.assertIn("bone_collector", updated)
        self.assertEqual(p.quest_progress["bone_collector"]["objectives"]["0"], 1)

    def test_same_mob_multiple_quests(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        self.assertTrue(is_quest_active(p, "rat_slayer"))


# =========================================================================
# Collect Objective Tracking
# =========================================================================


class TestCollectObjectives(unittest.TestCase):

    def test_collect_updates_based_on_inventory(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        p.add_item("health_potion", 3)
        updated = update_collect_objective(p, "health_potion")
        self.assertIn("potion_collector", updated)
        self.assertEqual(p.quest_progress["potion_collector"]["objectives"]["0"], 3)

    def test_collect_capped_at_required(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        p.add_item("health_potion", 10)
        updated = update_collect_objective(p, "health_potion")
        self.assertEqual(p.quest_progress["potion_collector"]["objectives"]["0"], 5)

    def test_collect_only_updates_matching_item(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        p.add_item("mana_potion", 3)
        updated = update_collect_objective(p, "mana_potion")
        self.assertNotIn("potion_collector", updated)

    def test_collect_only_updates_active_quests(self):
        p = _make_player()
        p.add_item("health_potion", 5)
        updated = update_collect_objective(p, "health_potion")
        self.assertEqual(updated, [])

    def test_collect_with_zero_inventory(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        updated = update_collect_objective(p, "health_potion")
        self.assertEqual(p.quest_progress["potion_collector"]["objectives"]["0"], 0)

    def test_bone_collector_collect_objective(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        p.add_item("health_potion", 2)
        update_collect_objective(p, "health_potion")
        self.assertEqual(p.quest_progress["bone_collector"]["objectives"]["1"], 1)


# =========================================================================
# Completion Validation
# =========================================================================


class TestCompletionValidation(unittest.TestCase):

    def test_cannot_complete_without_accepting(self):
        p = _make_player()
        ok, msg = can_complete(p, "rat_slayer")
        self.assertFalse(ok)

    def test_cannot_complete_without_objectives_met(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        ok, msg = can_complete(p, "rat_slayer")
        self.assertFalse(ok)

    def test_can_complete_when_objectives_met(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        ok, msg = can_complete(p, "rat_slayer")
        self.assertTrue(ok)

    def test_can_complete_partial_objectives(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        p.quest_progress["bone_collector"]["objectives"]["0"] = 2
        ok, msg = can_complete(p, "bone_collector")
        self.assertFalse(ok)

    def test_can_complete_all_multi_objectives(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        p.quest_progress["bone_collector"]["objectives"]["0"] = 2
        p.quest_progress["bone_collector"]["objectives"]["1"] = 1
        ok, msg = can_complete(p, "bone_collector")
        self.assertTrue(ok)

    def test_cannot_complete_already_completed(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        ok, msg = can_complete(p, "rat_slayer")
        self.assertFalse(ok)
        self.assertIn("already been completed", msg)

    def test_cannot_complete_invalid_id(self):
        p = _make_player()
        ok, msg = can_complete(p, "nonexistent")
        self.assertFalse(ok)
        self.assertIn("Unknown", msg)


# =========================================================================
# Completion & Rewards
# =========================================================================


class TestCompletionRewards(unittest.TestCase):

    def test_complete_quest_grants_xp(self):
        p = _make_player()
        old_xp = p.xp
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        ok, msg = complete_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertEqual(p.xp, old_xp + 50)

    def test_complete_quest_grants_items(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        old_hp_potions = p.inventory.get("health_potion", 0)
        ok, msg = complete_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertEqual(
            p.inventory.get("health_potion", 0),
            old_hp_potions + 2,
        )

    def test_complete_quest_with_multiple_item_rewards(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        p.quest_progress["bone_collector"]["objectives"]["0"] = 2
        p.quest_progress["bone_collector"]["objectives"]["1"] = 1
        ok, msg = complete_quest(p, "bone_collector")
        self.assertTrue(ok)
        self.assertEqual(p.inventory.get("health_potion", 0), 1)
        self.assertEqual(p.inventory.get("leather_cap", 0), 1)

    def test_complete_quest_grants_correct_xp_spider_hunt(self):
        p = _make_player()
        accept_quest(p, "spider_hunt")
        p.quest_progress["spider_hunt"]["objectives"]["0"] = 2
        old_xp = p.xp
        ok, msg = complete_quest(p, "spider_hunt")
        self.assertTrue(ok)
        self.assertEqual(p.xp, old_xp + 100)


# =========================================================================
# Duplicate Prevention
# =========================================================================


class TestDuplicatePrevention(unittest.TestCase):

    def test_cannot_complete_twice(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        ok1, _ = complete_quest(p, "rat_slayer")
        self.assertTrue(ok1)
        ok2, msg = complete_quest(p, "rat_slayer")
        self.assertFalse(ok2)

    def test_reward_xp_not_granted_twice(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        xp_after_first = p.xp
        complete_quest(p, "rat_slayer")
        self.assertEqual(p.xp, xp_after_first)

    def test_reward_items_not_granted_twice(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        hp_count = p.inventory.get("health_potion", 0)
        complete_quest(p, "rat_slayer")
        self.assertEqual(p.inventory.get("health_potion", 0), hp_count)

    def test_cannot_accept_after_completion(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        ok, msg = can_accept(p, "rat_slayer")
        self.assertFalse(ok)


# =========================================================================
# Invalid IDs
# =========================================================================


class TestInvalidIDs(unittest.TestCase):

    def test_accept_invalid_quest_id(self):
        p = _make_player()
        ok, msg = accept_quest(p, "fake_quest")
        self.assertFalse(ok)

    def test_abandon_invalid_quest_id(self):
        p = _make_player()
        ok, msg = abandon_quest(p, "fake_quest")
        self.assertFalse(ok)

    def test_complete_invalid_quest_id(self):
        p = _make_player()
        ok, msg = complete_quest(p, "fake_quest")
        self.assertFalse(ok)

    def test_get_quest_invalid(self):
        self.assertIsNone(get_quest(""))

    def test_get_objective_progress_invalid_quest(self):
        p = _make_player()
        result = get_objective_progress(p, "fake_quest")
        self.assertEqual(result, [])

    def test_update_kill_invalid_mob_does_nothing(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        updated = update_kill_objective(p, "fake_mob")
        self.assertEqual(updated, [])

    def test_update_collect_invalid_item_does_nothing(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        updated = update_collect_objective(p, "fake_item")
        self.assertEqual(updated, [])


# =========================================================================
# Objective Progress API
# =========================================================================


class TestObjectiveProgressAPI(unittest.TestCase):

    def test_get_objective_progress_valid(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        progress = get_objective_progress(p, "rat_slayer")
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["type"], "kill")
        self.assertEqual(progress[0]["target"], "giant_rat")
        self.assertEqual(progress[0]["current"], 0)
        self.assertEqual(progress[0]["required"], 3)

    def test_get_objective_progress_after_kills(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        update_kill_objective(p, "giant_rat")
        update_kill_objective(p, "giant_rat")
        progress = get_objective_progress(p, "rat_slayer")
        self.assertEqual(progress[0]["current"], 2)
        self.assertEqual(progress[0]["required"], 3)

    def test_get_objective_progress_multi_objective(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        progress = get_objective_progress(p, "bone_collector")
        self.assertEqual(len(progress), 2)
        self.assertEqual(progress[0]["type"], "kill")
        self.assertEqual(progress[1]["type"], "collect")

    def test_get_objective_progress_unaccepted(self):
        p = _make_player()
        result = get_objective_progress(p, "rat_slayer")
        self.assertEqual(result, [])

    def test_get_objective_progress_after_collect(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        p.add_item("health_potion", 3)
        update_collect_objective(p, "health_potion")
        progress = get_objective_progress(p, "potion_collector")
        self.assertEqual(progress[0]["current"], 3)
        self.assertEqual(progress[0]["required"], 5)


# =========================================================================
# Quest State Query
# =========================================================================


class TestQuestStateQuery(unittest.TestCase):

    def test_state_none_for_untouched_quest(self):
        p = _make_player()
        self.assertIsNone(get_quest_state(p, "rat_slayer"))

    def test_state_active_after_accept(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        self.assertEqual(get_quest_state(p, "rat_slayer"), QuestState.ACTIVE)

    def test_state_completed_after_complete(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        self.assertEqual(get_quest_state(p, "rat_slayer"), QuestState.COMPLETED)

    def test_state_returns_none_for_invalid_id(self):
        p = _make_player()
        self.assertIsNone(get_quest_state(p, "nonexistent"))

    def test_is_quest_completed_false_for_unaccepted(self):
        p = _make_player()
        self.assertFalse(is_quest_completed(p, "rat_slayer"))

    def test_is_quest_active_false_for_unaccepted(self):
        p = _make_player()
        self.assertFalse(is_quest_active(p, "rat_slayer"))


# =========================================================================
# Persistence - Round-trip Serialization
# =========================================================================


class TestPersistenceRoundtrip(unittest.TestCase):

    def test_quest_progress_survives_round_trip(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        update_kill_objective(p, "giant_rat")
        update_kill_objective(p, "giant_rat")
        d = p.to_dict()
        p2 = CharacterData.from_dict(d)
        self.assertIn("rat_slayer", p2.quest_progress)
        self.assertEqual(
            p2.quest_progress["rat_slayer"]["objectives"]["0"], 2,
        )
        self.assertEqual(
            p2.quest_progress["rat_slayer"]["state"], "active",
        )

    def test_completed_quest_survives_round_trip(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        p.quest_progress["rat_slayer"]["objectives"]["0"] = 3
        complete_quest(p, "rat_slayer")
        d = p.to_dict()
        p2 = CharacterData.from_dict(d)
        self.assertTrue(is_quest_completed(p2, "rat_slayer"))
        self.assertEqual(
            p2.quest_progress["rat_slayer"]["state"], "completed",
        )

    def test_multiple_quests_survive_round_trip(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "rat_slayer")
        update_kill_objective(p, "giant_rat")
        accept_quest(p, "bone_collector")
        update_kill_objective(p, "skeleton_warrior")
        d = p.to_dict()
        p2 = CharacterData.from_dict(d)
        self.assertIn("rat_slayer", p2.quest_progress)
        self.assertIn("bone_collector", p2.quest_progress)
        self.assertEqual(p2.quest_progress["rat_slayer"]["objectives"]["0"], 1)
        self.assertEqual(p2.quest_progress["bone_collector"]["objectives"]["0"], 1)

    def test_serialized_quest_progress_is_json_safe(self):
        p = _make_player()
        accept_quest(p, "rat_slayer")
        update_kill_objective(p, "giant_rat")
        d = p.to_dict()
        s = json.dumps(d)
        restored = json.loads(s)
        self.assertIn("quest_progress", restored)
        self.assertIn("rat_slayer", restored["quest_progress"])

    def test_empty_quest_progress_round_trip(self):
        p = _make_player()
        d = p.to_dict()
        p2 = CharacterData.from_dict(d)
        self.assertEqual(p2.quest_progress, {})


# =========================================================================
# Full Quest Flow - Acceptance through Completion
# =========================================================================


class TestFullQuestFlow(unittest.TestCase):

    def test_full_kill_quest_flow(self):
        p = _make_player()
        ok, _ = accept_quest(p, "rat_slayer")
        self.assertTrue(ok)
        self.assertTrue(is_quest_active(p, "rat_slayer"))
        for i in range(3):
            update_kill_objective(p, "giant_rat")
        self.assertEqual(
            p.quest_progress["rat_slayer"]["objectives"]["0"], 3,
        )
        ok2, _ = can_complete(p, "rat_slayer")
        self.assertTrue(ok2)
        old_xp = p.xp
        old_potions = p.inventory.get("health_potion", 0)
        ok3, _ = complete_quest(p, "rat_slayer")
        self.assertTrue(ok3)
        self.assertTrue(is_quest_completed(p, "rat_slayer"))
        self.assertEqual(p.xp, old_xp + 50)
        self.assertEqual(
            p.inventory.get("health_potion", 0),
            old_potions + 2,
        )
        ok4, _ = complete_quest(p, "rat_slayer")
        self.assertFalse(ok4)

    def test_full_collect_quest_flow(self):
        p = _make_player()
        accept_quest(p, "potion_collector")
        self.assertTrue(is_quest_active(p, "potion_collector"))
        p.add_item("health_potion", 5)
        update_collect_objective(p, "health_potion")
        self.assertEqual(
            p.quest_progress["potion_collector"]["objectives"]["0"], 5,
        )
        ok, _ = can_complete(p, "potion_collector")
        self.assertTrue(ok)
        ok2, _ = complete_quest(p, "potion_collector")
        self.assertTrue(ok2)
        self.assertTrue(is_quest_completed(p, "potion_collector"))
        self.assertEqual(p.xp, 30)
        # Started with 5 health potions, rewarded 2 more = 7
        self.assertEqual(p.inventory.get("health_potion", 0), 7)

    def test_full_multi_objective_flow(self):
        p = _make_player()
        p.level = 5
        accept_quest(p, "bone_collector")
        update_kill_objective(p, "skeleton_warrior")
        update_kill_objective(p, "skeleton_warrior")
        self.assertEqual(
            p.quest_progress["bone_collector"]["objectives"]["0"], 2,
        )
        p.add_item("health_potion", 1)
        update_collect_objective(p, "health_potion")
        self.assertEqual(
            p.quest_progress["bone_collector"]["objectives"]["1"], 1,
        )
        ok, _ = complete_quest(p, "bone_collector")
        self.assertTrue(ok)
        self.assertTrue(is_quest_completed(p, "bone_collector"))
        self.assertEqual(p.xp, 150)
        # 1 collected + 1 reward = 2
        self.assertEqual(p.inventory.get("health_potion", 0), 2)
        self.assertEqual(p.inventory.get("leather_cap", 0), 1)


# =========================================================================
# Regression - Existing Systems Intact
# =========================================================================


class TestRegression(unittest.TestCase):

    def test_character_creation_still_works(self):
        p = _make_player()
        self.assertIsNotNone(p)
        self.assertEqual(p.level, 1)
        self.assertIsInstance(p.quest_progress, dict)

    def test_items_still_work(self):
        from world.data.items import item_exists
        self.assertTrue(item_exists("health_potion"))
        self.assertTrue(item_exists("leather_cap"))

    def test_mobs_still_work(self):
        from world.data.mobs import mob_exists
        self.assertTrue(mob_exists("giant_rat"))
        self.assertTrue(mob_exists("skeleton_warrior"))

    def test_progression_still_works(self):
        from world.data.progression import award_xp
        p = _make_player()
        old = p.xp
        award_xp(p, 500)
        self.assertGreater(p.xp, old)

    def test_combat_still_works(self):
        from world.data.combat import resolve_attack
        a = _make_player()
        t = _make_player()
        res = resolve_attack(a, t)
        self.assertTrue(res["valid"])

    def test_new_character_has_empty_quest_progress(self):
        p = CharacterData()
        self.assertEqual(p.quest_progress, {})
