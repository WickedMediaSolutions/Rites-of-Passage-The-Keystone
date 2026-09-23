"""
Phase 15 — Skills & Spells Integration Tests

Covers skill registry, validation, resource costs, skill use, damage,
self-heal, combat state, structured results, and persistence.
"""

import unittest

from world.data.character_data import CharacterData
from world.data.enums import CharacterState, DamageType, SkillCategory
from world.data.skills import (
    SKILL_REGISTRY,
    SkillDefinition,
    SkillUseResult,
    get_skill_definition,
    get_skill_name,
    skill_exists,
    use_skill,
    validate_skill_use,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cd(name="Test", race="human", prof="warrior", level=50):
    """Create a CharacterData with full resources and unlocked skills."""
    cd = CharacterData.create_from_race_profession(name, race, prof)
    cd.level = level
    cd.max_hp = 100
    cd.hp = 100
    cd.max_mana = 100
    cd.mana = 100
    cd.max_stamina = 100
    cd.stamina = 100
    return cd


def _unlock(cd, *skill_ids):
    """Unlock the given skill IDs on the character."""
    for sid in skill_ids:
        cd.unlocked_skills.add(sid)


# =============================================================================
# Skill Registry
# =============================================================================

class TestSkillRegistry(unittest.TestCase):
    """Skill definitions and lookup."""

    def test_registry_has_131_skills(self):
        self.assertEqual(len(SKILL_REGISTRY), 131)

    def test_get_skill_definition_known(self):
        d = get_skill_definition("fireball")
        self.assertIsNotNone(d)
        self.assertEqual(d.name, "Fireball")
        self.assertEqual(d.cost_type, "mana")
        self.assertEqual(d.base_damage, 40)

    def test_get_skill_definition_unknown(self):
        self.assertIsNone(get_skill_definition("nonexistent_skill"))

    def test_skill_exists_true(self):
        self.assertTrue(skill_exists("kick"))

    def test_skill_exists_false(self):
        self.assertFalse(skill_exists("made_up_skill"))

    def test_get_skill_name_known(self):
        self.assertEqual(get_skill_name("bash"), "Bash")

    def test_get_skill_name_unknown(self):
        self.assertEqual(get_skill_name("nope"), "nope")

    def test_weapon_proficiencies_are_passive(self):
        for wid in ("piercing_weapons", "slashing_weapons",
                     "concussion_weapons", "whipping_weapons"):
            d = get_skill_definition(wid)
            self.assertIsNotNone(d)
            self.assertTrue(d.is_passive, f"{wid} should be passive")

    def test_spells_cost_mana(self):
        for sid in ("fireball", "healing", "vortex", "flamestrike",
                     "siphon_life", "psionic_blast"):
            d = get_skill_definition(sid)
            self.assertEqual(d.cost_type, "mana", f"{sid} should cost mana")

    def test_physical_skills_cost_stamina(self):
        for sid in ("kick", "bash", "backstab", "dodge", "parry",
                     "pummel", "riposte"):
            d = get_skill_definition(sid)
            self.assertEqual(d.cost_type, "stamina", f"{sid} should cost stamina")

    def test_utility_skills_have_no_cost(self):
        for sid in ("swim", "searching", "haggle", "tracking", "butcher"):
            d = get_skill_definition(sid)
            self.assertIsNone(d.cost_type)
            self.assertEqual(d.cost_amount, 0)

    def test_healing_skills_have_self_heal(self):
        d = get_skill_definition("heal_critical")
        self.assertIsNotNone(d.self_heal_amount)
        self.assertGreater(d.self_heal_amount, 0)

    def test_vampiric_skills_have_self_heal(self):
        d = get_skill_definition("siphon_life")
        self.assertIsNotNone(d.self_heal_amount)
        self.assertGreater(d.self_heal_amount, 0)

    def test_non_damaging_skill_no_base_damage(self):
        d = get_skill_definition("meditation")
        self.assertIsNone(d.base_damage)

    def test_registry_contains_all_categories(self):
        cats = {d.category for d in SKILL_REGISTRY.values()}
        self.assertIn(SkillCategory.WEAPON, cats)
        self.assertIn(SkillCategory.UNIVERSAL, cats)
        self.assertIn(SkillCategory.PROFESSION, cats)

# =============================================================================
# Validation — validate_skill_use
# =============================================================================

class TestValidateSkillUse(unittest.TestCase):
    """Pre-use validation rules."""

    def test_dead_caster_rejected(self):
        cd = _make_cd()
        cd.state = CharacterState.DEAD
        cd.hp = 0
        _unlock(cd, "kick")
        err = validate_skill_use(cd, "kick")
        self.assertIsNotNone(err)
        self.assertIn("dead", err.lower())

    def test_unknown_skill_rejected(self):
        cd = _make_cd()
        err = validate_skill_use(cd, "made_up")
        self.assertIsNotNone(err)
        self.assertIn("unknown", err.lower())

    def test_passive_skill_rejected(self):
        cd = _make_cd()
        _unlock(cd, "piercing_weapons")
        err = validate_skill_use(cd, "piercing_weapons")
        self.assertIsNotNone(err)
        self.assertIn("passive", err.lower())

    def test_not_unlocked_rejected(self):
        cd = _make_cd()
        # kick not in unlocked_skills
        err = validate_skill_use(cd, "kick")
        self.assertIsNotNone(err)
        self.assertIn("not unlocked", err.lower())

    def test_insufficient_mana_rejected(self):
        cd = _make_cd()
        cd.mana = 5
        _unlock(cd, "fireball")  # costs 30 mana
        err = validate_skill_use(cd, "fireball")
        self.assertIsNotNone(err)
        self.assertIn("mana", err.lower())

    def test_insufficient_stamina_rejected(self):
        cd = _make_cd()
        cd.stamina = 3
        _unlock(cd, "kick")  # costs 10 stamina
        err = validate_skill_use(cd, "kick")
        self.assertIsNotNone(err)
        self.assertIn("stamina", err.lower())

    def test_target_required_but_none(self):
        cd = _make_cd()
        _unlock(cd, "fireball")
        err = validate_skill_use(cd, "fireball", None)
        self.assertIsNotNone(err)
        self.assertIn("target", err.lower())

    def test_self_target_rejected(self):
        cd = _make_cd()
        _unlock(cd, "fireball")
        err = validate_skill_use(cd, "fireball", cd)
        self.assertIsNotNone(err)
        self.assertIn("yourself", err.lower())

    def test_dead_target_rejected(self):
        cd = _make_cd()
        target = _make_cd()
        target.state = CharacterState.DEAD
        target.hp = 0
        _unlock(cd, "fireball")
        err = validate_skill_use(cd, "fireball", target)
        self.assertIsNotNone(err)
        self.assertIn("dead", err.lower())

    def test_valid_use_passes(self):
        cd = _make_cd()
        target = _make_cd()
        _unlock(cd, "fireball")
        err = validate_skill_use(cd, "fireball", target)
        self.assertIsNone(err)

    def test_no_target_skill_passes_without_target(self):
        cd = _make_cd()
        _unlock(cd, "meditation")  # no target required
        err = validate_skill_use(cd, "meditation")
        self.assertIsNone(err)

    def test_enough_resource_passes(self):
        cd = _make_cd()
        cd.mana = 50
        _unlock(cd, "fireball")  # costs 30
        target = _make_cd()
        err = validate_skill_use(cd, "fireball", target)
        self.assertIsNone(err)


# =============================================================================
# Skill Use — use_skill
# =============================================================================

class TestUseSkillDamage(unittest.TestCase):
    """Using damaging skills against targets."""

    def test_use_skill_deducts_mana(self):
        cd = _make_cd()
        cd.mana = 50
        target = _make_cd()
        _unlock(cd, "fireball")  # 30 mana
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertEqual(result.caster_mana_before, 50)
        self.assertEqual(result.caster_mana_after, 20)
        self.assertEqual(result.resource_cost_paid, 30)
        self.assertEqual(result.resource_type, "mana")

    def test_use_skill_deducts_stamina(self):
        cd = _make_cd()
        cd.stamina = 50
        target = _make_cd()
        _unlock(cd, "kick")  # 10 stamina
        result = use_skill(cd, "kick", target)
        self.assertTrue(result.success)
        self.assertEqual(result.caster_stamina_before, 50)
        self.assertEqual(result.caster_stamina_after, 40)
        self.assertEqual(result.resource_cost_paid, 10)
        self.assertEqual(result.resource_type, "stamina")

    def test_use_skill_deals_damage(self):
        cd = _make_cd()
        target = _make_cd()
        target.hp = 100
        _unlock(cd, "fireball")  # 40 base_damage
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertEqual(result.damage_dealt, 40)
        self.assertEqual(result.target_hp_before, 100)
        self.assertEqual(result.target_hp_after, 60)
        self.assertFalse(result.target_killed)

    def test_use_skill_kills_target(self):
        cd = _make_cd()
        target = _make_cd()
        target.hp = 10
        _unlock(cd, "fireball")  # 40 damage
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertTrue(result.target_killed)
        self.assertEqual(result.target_hp_after, 0)
        self.assertEqual(target.state, CharacterState.DEAD)

    def test_use_unknown_skill_returns_error(self):
        cd = _make_cd()
        result = use_skill(cd, "nonexistent")
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_use_locked_skill_returns_error(self):
        cd = _make_cd()
        result = use_skill(cd, "fireball")  # not unlocked
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_use_skill_no_resource_deducted_on_failure(self):
        cd = _make_cd()
        cd.mana = 100
        result = use_skill(cd, "fireball")  # fails: not unlocked
        self.assertFalse(result.success)
        self.assertEqual(cd.mana, 100)  # unchanged
        self.assertEqual(result.resource_cost_paid, 0)

    def test_use_skill_insufficient_mana(self):
        cd = _make_cd()
        cd.mana = 10
        target = _make_cd()
        _unlock(cd, "fireball")  # costs 30
        result = use_skill(cd, "fireball", target)
        self.assertFalse(result.success)
        self.assertIn("mana", result.error.lower())

    def test_use_skill_dead_caster(self):
        cd = _make_cd()
        cd.state = CharacterState.DEAD
        cd.hp = 0
        _unlock(cd, "kick")
        result = use_skill(cd, "kick")
        self.assertFalse(result.success)
        self.assertIn("dead", result.error.lower())

    def test_use_skill_dead_target(self):
        cd = _make_cd()
        target = _make_cd()
        target.state = CharacterState.DEAD
        target.hp = 0
        _unlock(cd, "fireball")
        result = use_skill(cd, "fireball", target)
        self.assertFalse(result.success)
        self.assertIn("dead", result.error.lower())

    def test_use_skill_enters_combat(self):
        cd = _make_cd()
        target = _make_cd()
        self.assertEqual(cd.state, CharacterState.STANDING)
        _unlock(cd, "fireball")
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertTrue(result.caster_entered_combat)
        self.assertEqual(cd.state, CharacterState.COMBAT)

    def test_use_skill_target_enters_combat(self):
        cd = _make_cd()
        target = _make_cd()
        target.hp = 100
        self.assertEqual(target.state, CharacterState.STANDING)
        _unlock(cd, "fireball")
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertTrue(result.target_entered_combat)
        self.assertEqual(target.state, CharacterState.COMBAT)


# =============================================================================
# Self-Heal / Vampiric Skills
# =============================================================================

class TestSelfHeal(unittest.TestCase):
    """Skills that heal the caster on use."""

    def test_vampiric_skill_heals_caster(self):
        cd = _make_cd()
        cd.hp = 50  # not full
        target = _make_cd()
        _unlock(cd, "siphon_life")  # self_heal=8
        result = use_skill(cd, "siphon_life", target)
        self.assertTrue(result.success)
        self.assertGreater(result.healing_applied, 0)
        self.assertEqual(cd.hp, 50 + result.healing_applied)

    def test_self_heal_does_not_exceed_max(self):
        cd = _make_cd()
        cd.hp = 98
        _unlock(cd, "self_healing")  # self_heal=20, no target
        result = use_skill(cd, "self_healing")
        self.assertTrue(result.success)
        self.assertLessEqual(cd.hp, cd.max_hp)

    def test_heal_at_full_hp_does_nothing(self):
        cd = _make_cd()
        cd.hp = cd.max_hp
        _unlock(cd, "self_healing")
        result = use_skill(cd, "self_healing")
        self.assertTrue(result.success)
        self.assertEqual(result.healing_applied, 0)

    def test_non_heal_skill_heals_zero(self):
        cd = _make_cd()
        target = _make_cd()
        _unlock(cd, "fireball")  # no self_heal
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertEqual(result.healing_applied, 0)


# =============================================================================
# Utility / No-Cost / No-Target Skills
# =============================================================================

class TestUtilitySkills(unittest.TestCase):
    """Skills that cost no resources and need no target."""

    def test_no_cost_skill_succeeds(self):
        cd = _make_cd()
        _unlock(cd, "swim")  # no cost, no target
        result = use_skill(cd, "swim")
        self.assertTrue(result.success)
        self.assertEqual(result.resource_cost_paid, 0)
        self.assertIsNone(result.resource_type)

    def test_no_cost_skill_no_resource_change(self):
        cd = _make_cd()
        cd.mana = 50
        cd.stamina = 50
        _unlock(cd, "swim")
        result = use_skill(cd, "swim")
        self.assertTrue(result.success)
        self.assertEqual(cd.mana, 50)
        self.assertEqual(cd.stamina, 50)

    def test_no_target_non_damaging_skill(self):
        cd = _make_cd()
        _unlock(cd, "meditation")  # mana cost but no target, no damage
        result = use_skill(cd, "meditation")
        self.assertTrue(result.success)
        self.assertEqual(result.damage_dealt, 0)
        self.assertIsNone(result.target_hp_before)

    def test_passive_skill_cannot_be_used(self):
        cd = _make_cd()
        _unlock(cd, "piercing_weapons")
        result = use_skill(cd, "piercing_weapons")
        self.assertFalse(result.success)
        self.assertIn("passive", result.error.lower())


# =============================================================================
# SkillUseResult structure
# =============================================================================

class TestSkillUseResult(unittest.TestCase):
    """SkillUseResult dataclass structure."""

    def test_result_defaults_false(self):
        r = SkillUseResult()
        self.assertFalse(r.success)
        self.assertIsNone(r.error)
        self.assertEqual(r.skill_id, "")
        self.assertEqual(r.damage_dealt, 0)
        self.assertFalse(r.target_killed)

    def test_result_captures_skill_id(self):
        cd = _make_cd()
        target = _make_cd()
        _unlock(cd, "kick")
        result = use_skill(cd, "kick", target)
        self.assertEqual(result.skill_id, "kick")

    def test_result_snapshots_before_values(self):
        cd = _make_cd()
        cd.hp = 80
        cd.mana = 60
        cd.stamina = 40
        target = _make_cd()
        _unlock(cd, "fireball")
        result = use_skill(cd, "fireball", target)
        self.assertEqual(result.caster_hp_before, 80)
        self.assertEqual(result.caster_mana_before, 60)
        self.assertEqual(result.caster_stamina_before, 40)

    def test_result_snapshots_after_values(self):
        cd = _make_cd()
        cd.mana = 60
        target = _make_cd()
        _unlock(cd, "fireball")  # costs 30
        result = use_skill(cd, "fireball", target)
        self.assertTrue(result.success)
        self.assertEqual(result.caster_mana_after, 30)
        self.assertEqual(result.caster_hp_after, cd.hp)
        self.assertEqual(result.caster_stamina_after, cd.stamina)


# =============================================================================
# Persistence — unlocked_skills survive to_dict / from_dict
# =============================================================================

class TestPersistence(unittest.TestCase):
    """Skill unlocks persist through serialization."""

    def test_unlocked_skills_survive_round_trip(self):
        cd = _make_cd()
        _unlock(cd, "fireball", "kick", "swim", "dodge")
        data = cd.to_dict()
        restored = CharacterData.from_dict(data)
        self.assertIn("fireball", restored.unlocked_skills)
        self.assertIn("kick", restored.unlocked_skills)
        self.assertIn("swim", restored.unlocked_skills)
        self.assertIn("dodge", restored.unlocked_skills)

    def test_empty_unlocked_skills_round_trip(self):
        cd = _make_cd()
        cd.unlocked_skills = set()
        data = cd.to_dict()
        restored = CharacterData.from_dict(data)
        self.assertEqual(len(restored.unlocked_skills), 0)

    def test_unlocked_skills_after_round_trip_still_usable(self):
        cd = _make_cd()
        _unlock(cd, "fireball")
        data = cd.to_dict()
        restored = CharacterData.from_dict(data)
        restored.max_hp = 100
        restored.hp = 100
        restored.max_mana = 100
        restored.mana = 100
        restored.max_stamina = 100
        restored.stamina = 100
        target = _make_cd()
        result = use_skill(restored, "fireball", target)
        self.assertTrue(result.success, f"Should succeed, got: {result.error}")


# =============================================================================
# Profession/Level Eligibility
# =============================================================================

class TestEligibility(unittest.TestCase):
    """Skills are unlocked through the existing progression system."""

    def test_warrior_has_kick_at_level_7(self):
        from world.data.progression import grant_all_skills_for_level
        cd = _make_cd(prof="warrior", level=7)
        grant_all_skills_for_level(cd, 7)
        self.assertIn("kick", cd.unlocked_skills)

    def test_warrior_does_not_have_fireball(self):
        from world.data.progression import grant_all_skills_for_level
        cd = _make_cd(prof="warrior", level=50)
        grant_all_skills_for_level(cd, 50)
        self.assertNotIn("fireball", cd.unlocked_skills)

    def test_mage_has_fireball_at_level_41(self):
        from world.data.progression import grant_all_skills_for_level
        cd = _make_cd(prof="mage", level=41)
        grant_all_skills_for_level(cd, 41)
        self.assertIn("fireball", cd.unlocked_skills)

    def test_mage_does_not_have_fireball_before_41(self):
        from world.data.progression import grant_all_skills_for_level
        cd = _make_cd(prof="mage", level=40)
        grant_all_skills_for_level(cd, 40)
        self.assertNotIn("fireball", cd.unlocked_skills)

    def test_universal_skills_granted_to_all(self):
        from world.data.progression import grant_all_skills_for_level
        for prof in ("warrior", "mage", "cleric", "thief", "ninja", "druid"):
            cd = _make_cd(prof=prof, level=5)
            grant_all_skills_for_level(cd, 5)
            self.assertIn("swim", cd.unlocked_skills, f"{prof} should have swim at level 5")

    def test_no_duplicate_unlocks(self):
        from world.data.progression import grant_all_skills_for_level
        cd = _make_cd(prof="warrior", level=10)
        grant_all_skills_for_level(cd, 10)
        count_before = len(cd.unlocked_skills)
        grant_all_skills_for_level(cd, 10)  # idempotent
        self.assertEqual(len(cd.unlocked_skills), count_before)


# =============================================================================
# Skill Cost Consistency
# =============================================================================

class TestSkillCosts(unittest.TestCase):
    """Verify skill costs are consistent."""

    def test_all_mana_skills_have_positive_cost(self):
        for sid, defn in SKILL_REGISTRY.items():
            if defn.cost_type == "mana":
                self.assertGreater(defn.cost_amount, 0,
                    f"{sid} has mana cost but cost_amount={defn.cost_amount}")

    def test_all_stamina_skills_have_positive_cost(self):
        for sid, defn in SKILL_REGISTRY.items():
            if defn.cost_type == "stamina":
                self.assertGreater(defn.cost_amount, 0,
                    f"{sid} has stamina cost but cost_amount={defn.cost_amount}")

    def test_no_cost_skills_have_zero_cost(self):
        for sid, defn in SKILL_REGISTRY.items():
            if defn.cost_type is None:
                self.assertEqual(defn.cost_amount, 0,
                    f"{sid} has no cost_type but cost_amount={defn.cost_amount}")

    def test_all_damaging_skills_have_damage_type(self):
        for sid, defn in SKILL_REGISTRY.items():
            if defn.base_damage is not None and defn.base_damage > 0:
                self.assertIsNotNone(defn.damage_type,
                    f"{sid} has damage but no damage_type")

    def test_all_registry_skills_have_valid_skill_id(self):
        for sid, defn in SKILL_REGISTRY.items():
            self.assertEqual(sid, defn.skill_id)

    def test_no_duplicate_skill_ids(self):
        ids = list(SKILL_REGISTRY.keys())
        self.assertEqual(len(ids), len(set(ids)))
