"""
Commands

Commands describe the input the account can do to the game.

Player-facing gameplay commands (Phase 16) are defined here and
registered in ``default_cmdsets.CharacterCmdSet``.

"""

from evennia.commands.command import Command as BaseCommand


class Command(BaseCommand):
    """
    Base command (you may see this if a child command had no help text defined)

    Note that the class's `__doc__` string is used by Evennia to create the
    automatic help entry for the command, so make sure to document consistently
    here. Without setting one, the parent's docstring will show (like now).

    """

    pass


# ==========================================================================
# Phase 16 — Player Gameplay Commands
# ==========================================================================


class CmdScore(Command):
    """
    Display your character sheet.

    Usage:
        score
        info
    """

    key = "score"
    aliases = ["info"]

    def func(self):
        caller = self.caller
        game = caller.game

        lines = [
            f"|w{game.name}|n  |cLevel {game.level}|n  "
            f"|m{game.race_id.title()}|n  |y{game.profession_id.title()}|n",
        ]
        if game.faction:
            lines.append(f"Faction: |r{game.faction.value.title()}|n")
        lines.append("")
        lines.append(f"|gHP:|n       {game.hp}/{game.max_hp}")
        lines.append(f"|bMana:|n     {game.mana}/{game.max_mana}")
        lines.append(f"|yStamina:|n  {game.stamina}/{game.max_stamina}")
        lines.append("")
        lines.append(f"XP: {game.xp}  (to next: {caller.xp_to_next()})")
        lines.append("")
        lines.append("|wBase Stats:|n")
        stats = game.base_stats
        lines.append(
            f"  STR {stats.get('str', 0):>3}  INT {stats.get('int', 0):>3}  "
            f"WIS {stats.get('wis', 0):>3}  DEX {stats.get('dex', 0):>3}  "
            f"CON {stats.get('con', 0):>3}"
        )
        lines.append("")
        lines.append(f"State: {game.state.value}")
        from world.data.economy import to_display
        lines.append(f"Currency: {to_display(game.currency)}")
        lines.append(f"Skills Unlocked: {len(game.unlocked_skills)}")
        active = sum(
            1 for p in game.quest_progress.values()
            if p.get("state") == "active"
        )
        lines.append(f"Quests Active: {active}")
        lines.append("")

        # Phase 19 — Guild / Sect / PvP status.
        from world.data.socials import get_guild_name, get_sect_name
        if game.guild_id:
            gname = get_guild_name(game.guild_id) or game.guild_id
            lines.append(f"Guild: {gname}")
        if game.sect_id:
            sname = get_sect_name(game.sect_id) or game.sect_id
            lines.append(f"Sect: {sname}")
        lines.append(f"War Points: {game.war_points}")
        lines.append(f"PvP Kills: {game.pvp_kills}  |  PvP Deaths: {game.pvp_deaths}")

        self.caller.msg("\n".join(lines))


class CmdInventory(Command):
    """
    List items in your inventory.

    Usage:
        inventory
        inv
        i
    """

    key = "inventory"
    aliases = ["inv", "i"]

    def func(self):
        game = self.caller.game
        inv = game.inventory

        if not inv:
            self.caller.msg("Your inventory is empty.")
            return

        lines = ["|wInventory:|n"]
        from world.data.items import get_item
        for item_id, qty in sorted(inv.items()):
            item_def = get_item(item_id)
            name = item_def["name"] if item_def else item_id
            lines.append(f"  {name:<24} x{qty}")
        lines.append(f"\n{len(inv)} unique item(s).")
        self.caller.msg("\n".join(lines))


class CmdEquipment(Command):
    """
    Display your currently equipped items.

    Usage:
        equipment
        eq
    """

    key = "equipment"
    aliases = ["eq"]

    def func(self):
        game = self.caller.game
        eq_data = game.equipment

        lines = ["|wEquipment:|n"]
        from world.data.items import get_item
        from world.data.enums import EquipmentSlot

        slot_labels = {
            EquipmentSlot.MAIN_HAND: "Main Hand",
            EquipmentSlot.OFF_HAND: "Off Hand",
            EquipmentSlot.HEAD: "Head",
            EquipmentSlot.CHEST: "Chest",
            EquipmentSlot.LEGS: "Legs",
            EquipmentSlot.HANDS: "Hands",
            EquipmentSlot.FEET: "Feet",
            EquipmentSlot.WRISTS: "Wrists",
            EquipmentSlot.LEFT_FINGER: "L. Finger",
            EquipmentSlot.RIGHT_FINGER: "R. Finger",
            EquipmentSlot.NECK: "Neck",
            EquipmentSlot.LEFT_EAR: "L. Ear",
            EquipmentSlot.RIGHT_EAR: "R. Ear",
            EquipmentSlot.WAIST: "Waist",
            EquipmentSlot.BACK: "Back",
        }

        equipped_count = 0
        for slot in EquipmentSlot:
            item_id = eq_data.get(slot)
            label = slot_labels.get(slot, slot.value)
            if item_id:
                item_def = get_item(item_id)
                name = item_def["name"] if item_def else item_id
                lines.append(f"  {label:<12} : {name}")
                equipped_count += 1
            else:
                lines.append(f"  {label:<12} : |d(empty)|n")

        lines.append(f"\n{equipped_count} item(s) equipped.")
        self.caller.msg("\n".join(lines))


class CmdEquip(Command):
    """
    Equip an item into a specified slot.

    Usage:
        equip <item> [slot]
        wear <item> [slot]
    """

    key = "equip"
    aliases = ["wear"]

    def parse(self):
        self.args = self.args.strip()
        parts = self.args.split()
        self.item_name = parts[0] if parts else ""
        self.slot_name = parts[1] if len(parts) > 1 else None

    def func(self):
        caller = self.caller
        game = caller.game

        if not self.item_name:
            self.caller.msg("Usage: equip <item> [slot]")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot equip items.")
            return

        from world.data.items import get_item
        from world.data.enums import EquipmentSlot

        item_id = _resolve_item(self.item_name)
        if item_id is None:
            self.caller.msg(f"Unknown item: '{self.item_name}'.")
            return

        item_def = get_item(item_id)

        slot = None
        if self.slot_name:
            slot = _resolve_slot(self.slot_name)
            if slot is None:
                self.caller.msg(
                    f"Unknown equipment slot: '{self.slot_name}'."
                )
                return
        else:
            slot_value = item_def.get("slot")
            if slot_value:
                for es in EquipmentSlot:
                    if es.value == slot_value:
                        slot = es
                        break
            if slot is None:
                self.caller.msg(
                    f"Cannot determine slot for '{item_def['name']}'."
                    " Please specify: equip <item> <slot>"
                )
                return

        error = game.equip(item_id, slot)
        if error is not None:
            self.caller.msg(error)
            return

        caller.save()
        self.caller.msg(
            f"You equip {item_def['name']} in the {slot.value} slot."
        )


class CmdUnequip(Command):
    """
    Remove an equipped item, returning it to your inventory.

    Usage:
        unequip <item>
        remove <item>
    """

    key = "unequip"
    aliases = ["remove"]

    def parse(self):
        self.item_name = self.args.strip()

    def func(self):
        caller = self.caller
        game = caller.game

        if not self.item_name:
            self.caller.msg("Usage: unequip <item>")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot unequip items.")
            return

        item_id = _resolve_item(self.item_name)
        if item_id is None:
            self.caller.msg(f"Unknown item: '{self.item_name}'.")
            return

        from world.data.items import get_item
        equipped_slot = None
        for slot, eq_id in game.equipment.items():
            if eq_id == item_id:
                equipped_slot = slot
                break

        error = game.unequip(item_id, equipped_slot)
        if error is not None:
            self.caller.msg(error)
            return

        caller.save()
        item_def = get_item(item_id)
        item_name = item_def["name"] if item_def else item_id
        self.caller.msg(f"You unequip {item_name}.")


class CmdAttack(Command):
    """
    Attack a target in the same room.

    Usage:
        attack <target>
        kill <target>
    """

    key = "attack"
    aliases = ["kill"]

    def parse(self):
        self.target_name = self.args.strip()

    def func(self):
        caller = self.caller

        if not self.target_name:
            self.caller.msg("Usage: attack <target>")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot attack.")
            return

        target = caller.search(self.target_name)
        if not target:
            return

        result = caller.attack_target(target)

        if result.get("error"):
            self.caller.msg(result["error"])
            return

        target_name = target.key
        if result["hit"]:
            dmg = result["actual_damage"]
            self.caller.msg(f"You hit {target_name} for {dmg} damage!")
            if hasattr(target, "msg"):
                target.msg(f"{caller.key} hits you for {dmg} damage!")
            if result["target_killed"]:
                self.caller.msg(f"You have slain {target_name}!")
                if hasattr(target, "msg"):
                    target.msg(f"You have been slain by {caller.key}!")
        else:
            self.caller.msg(f"You miss {target_name}.")
            if hasattr(target, "msg"):
                target.msg(f"{caller.key} misses you.")


class CmdUse(Command):
    """
    Use a skill or spell.

    Usage:
        use <skill> [on <target>]
        cast <skill> [on <target>]
    """

    key = "use"
    aliases = ["cast"]

    def parse(self):
        raw = self.args.strip()
        self.skill_name = ""
        self.target_name = ""

        lower_parts = raw.lower().split()
        on_idx = None
        for i, w in enumerate(lower_parts):
            if w == "on":
                on_idx = i
                break
        if on_idx is not None:
            parts = raw.split()
            self.skill_name = " ".join(parts[:on_idx])
            self.target_name = " ".join(parts[on_idx + 1:])
        else:
            parts = raw.split(None, 1)
            self.skill_name = parts[0] if parts else ""
            self.target_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller
        game = caller.game

        if not self.skill_name:
            self.caller.msg("Usage: use <skill> [on <target>]")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot use skills.")
            return

        from world.data.skills import (
            get_skill_definition, validate_skill_use, use_skill,
        )

        skill_id = _resolve_skill(self.skill_name)
        if skill_id is None:
            self.caller.msg(f"Unknown skill or spell: '{self.skill_name}'.")
            return

        defn = get_skill_definition(skill_id)
        if defn is None:
            self.caller.msg(f"Unknown skill or spell: '{self.skill_name}'.")
            return

        target_cd = None
        if self.target_name:
            target = caller.search(self.target_name)
            if not target:
                return
            target_cd = target.game
        elif defn.target_required:
            self.caller.msg(
                f"'{defn.name}' requires a target. "
                f"Usage: use {skill_id} on <target>"
            )
            return

        error = validate_skill_use(game, skill_id, target_cd)
        if error is not None:
            self.caller.msg(error)
            return

        result = use_skill(game, skill_id, target_cd)
        caller.save()

        if result.error:
            self.caller.msg(result.error)
            return

        msg_parts = [f"You use |y{defn.name}|n."]
        if result.resource_cost_paid:
            cost_type = result.resource_type or "resource"
            msg_parts.append(f" (-{result.resource_cost_paid} {cost_type})")
        if result.damage_dealt:
            msg_parts.append(f" Deals {result.damage_dealt} damage.")
            if result.target_killed:
                msg_parts.append(" Target killed!")
        if result.healing_applied:
            msg_parts.append(f" Healed for {result.healing_applied} HP.")
        if result.caster_entered_combat:
            msg_parts.append(" You enter combat!")

        self.caller.msg("".join(msg_parts))


class CmdQuest(Command):
    """
    Manage your quests.

    Usage:
        quest                    — list all known quests
        quest accept <quest>     — accept a quest
        quest abandon <quest>    — abandon an active quest
        quest complete <quest>   — complete a quest
        quest status <quest>     — view objective progress
    """

    key = "quest"
    aliases = ["quests"]

    def parse(self):
        raw = self.args.strip()
        parts = raw.split(None, 1)
        self.subcommand = parts[0].lower() if parts else ""
        self.quest_arg = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller

        if not self.subcommand or (
            self.subcommand in ("list", "status") and not self.quest_arg
        ):
            self._cmd_list()
        elif self.subcommand == "accept":
            self._cmd_accept()
        elif self.subcommand == "abandon":
            self._cmd_abandon()
        elif self.subcommand == "complete":
            self._cmd_complete()
        elif self.subcommand == "status":
            self._cmd_status()
        else:
            self.caller.msg(
                "Usage: quest [accept <id>|abandon <id>|"
                "complete <id>|status <id>]"
            )

    def _cmd_list(self):
        from world.data.quests import QUEST_REGISTRY, get_quest_state
        game = self.caller.game

        lines = ["|wQuests:|n"]
        for qid, qdef in sorted(QUEST_REGISTRY.items()):
            state = get_quest_state(game, qid)
            state_map = {
                None: "|dAvailable|n",
                "available": "|dAvailable|n",
                "active": "|yActive|n",
                "completed": "|gCompleted|n",
                "locked": "|rLocked|n",
            }
            state_str = state_map.get(
                state.value if state else None, str(state)
            )
            lines.append(
                f"  [{state_str}] {qdef['name']} "
                f"(Lv {qdef.get('level_required', 1)}) — {qdef['description']}"
            )

        self.caller.msg("\n".join(lines))

    def _cmd_accept(self):
        from world.data.quests import accept_quest
        game = self.caller.game

        quest_id = _resolve_quest(self.quest_arg)
        if quest_id is None:
            self.caller.msg(f"Unknown quest: '{self.quest_arg}'.")
            return

        ok, msg = accept_quest(game, quest_id)
        self.caller.save()
        self.caller.msg(msg)

    def _cmd_abandon(self):
        from world.data.quests import abandon_quest
        game = self.caller.game

        quest_id = _resolve_quest(self.quest_arg)
        if quest_id is None:
            self.caller.msg(f"Unknown quest: '{self.quest_arg}'.")
            return

        ok, msg = abandon_quest(game, quest_id)
        self.caller.save()
        self.caller.msg(msg)

    def _cmd_complete(self):
        from world.data.quests import complete_quest
        game = self.caller.game

        quest_id = _resolve_quest(self.quest_arg)
        if quest_id is None:
            self.caller.msg(f"Unknown quest: '{self.quest_arg}'.")
            return

        ok, msg = complete_quest(game, quest_id)
        self.caller.save()
        self.caller.msg(msg)

    def _cmd_status(self):
        from world.data.quests import (
            get_quest, get_objective_progress, get_quest_state,
        )
        game = self.caller.game

        quest_id = _resolve_quest(self.quest_arg)
        if quest_id is None:
            self.caller.msg(f"Unknown quest: '{self.quest_arg}'.")
            return

        qdef = get_quest(quest_id)
        state = get_quest_state(game, quest_id)

        lines = [f"|w{qdef['name']}|n — {qdef['description']}"]
        lines.append(
            f"State: {state.value if state else 'not started'}"
        )
        lines.append("")

        progress = get_objective_progress(game, quest_id)
        if progress:
            lines.append("|wObjectives:|n")
            for i, obj in enumerate(progress, 1):
                done = (
                    "|gDone|n" if obj["current"] >= obj["required"]
                    else ""
                )
                lines.append(
                    f"  {i}. {obj['type'].title()} '{obj['target']}' — "
                    f"{obj['current']}/{obj['required']} {done}"
                )
        else:
            lines.append("No objectives tracked yet.")

        self.caller.msg("\n".join(lines))


class CmdCurrency(Command):
    """
    Display your current currency balance.

    Usage:
        currency
        money
        gold
    """

    key = "currency"
    aliases = ["money", "gold"]

    def func(self):
        from world.data.economy import to_display
        amount = self.caller.game.currency
        display = to_display(amount)
        self.caller.msg(f"You have |y{display}|n ({amount} copper).")


class CmdShop(Command):
    """
    Browse a shop's inventory.

    Usage:
        shop list          — list all known shops
        shop <shop>        — browse a shop's wares
    """

    key = "shop"

    def parse(self):
        self.shop_arg = self.args.strip().lower()

    def func(self):
        from world.data.shops import SHOP_REGISTRY, get_shop, get_shop_inventory
        from world.data.items import get_item

        if not self.shop_arg or self.shop_arg == "list":
            lines = ["|wShops:|n"]
            for sid, sdef in sorted(SHOP_REGISTRY.items()):
                lines.append(f"  {sdef['name']} ({sid})")
            self.caller.msg("\n".join(lines))
            return

        shop_id = _resolve_shop(self.shop_arg)
        if shop_id is None:
            self.caller.msg(
                f"Unknown shop: '{self.shop_arg}'. "
                "Use 'shop list' to see available shops."
            )
            return

        shop = get_shop(shop_id)
        inventory = get_shop_inventory(shop_id)

        lines = [f"|w{shop['name']}|n"]
        if not inventory:
            lines.append("  (empty)")
        else:
            for item_id, info in sorted(inventory.items()):
                item_def = get_item(item_id)
                item_name = item_def["name"] if item_def else item_id
                buy_price = info.get("buy_price")
                sell_price = info.get("sell_price")
                stock = info.get("stock")
                price_str = ""
                if buy_price is not None:
                    price_str += f"Buy: {buy_price}c"
                if sell_price is not None:
                    if price_str:
                        price_str += " | "
                    price_str += f"Sell: {sell_price}c"
                stock_str = (
                    f" (Stock: {stock})" if stock is not None else ""
                )
                lines.append(
                    f"  {item_name:<24} {price_str}{stock_str}"
                )

        self.caller.msg("\n".join(lines))


class CmdBuy(Command):
    """
    Buy an item from a shop.

    Usage:
        buy <quantity> <item> from <shop>
        buy <item> from <shop>

    Examples:
        buy 3 health_potion from general_store
        buy rusty_sword from blacksmith
    """

    key = "buy"

    def parse(self):
        raw = self.args.strip()
        self.quantity = 1
        self.item_name = ""
        self.shop_name = ""

        lower_raw = raw.lower()
        if " from " in lower_raw:
            idx = lower_raw.index(" from ")
            before = raw[:idx].strip()
            self.shop_name = raw[idx + 6:].strip()
        else:
            self.item_name = raw
            return

        parts = before.split(None, 1)
        if len(parts) == 0:
            return
        if parts[0].isdigit():
            self.quantity = int(parts[0])
            self.item_name = parts[1] if len(parts) > 1 else ""
        else:
            self.item_name = before

    def func(self):
        caller = self.caller
        game = caller.game

        if not self.item_name or not self.shop_name:
            self.caller.msg("Usage: buy [quantity] <item> from <shop>")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot buy items.")
            return

        from world.data.shops import buy_item

        shop_id = _resolve_shop(self.shop_name)
        if shop_id is None:
            self.caller.msg(f"Unknown shop: '{self.shop_name}'.")
            return

        item_id = _resolve_item(self.item_name)
        if item_id is None:
            self.caller.msg(f"Unknown item: '{self.item_name}'.")
            return

        if self.quantity <= 0:
            self.caller.msg("Quantity must be positive.")
            return

        result = buy_item(game, shop_id, item_id, self.quantity)
        caller.save()

        if result.success:
            self.caller.msg(result.message)
            from world.data.economy import to_display
            self.caller.msg(
                f"New balance: {to_display(result.new_balance)}"
            )
        else:
            self.caller.msg(result.message)


class CmdSell(Command):
    """
    Sell an item to a shop.

    Usage:
        sell <quantity> <item> to <shop>
        sell <item> to <shop>

    Examples:
        sell 3 health_potion to general_store
        sell rusty_sword to blacksmith
    """

    key = "sell"

    def parse(self):
        raw = self.args.strip()
        self.quantity = 1
        self.item_name = ""
        self.shop_name = ""

        lower_raw = raw.lower()
        if " to " in lower_raw:
            idx = lower_raw.index(" to ")
            before = raw[:idx].strip()
            self.shop_name = raw[idx + 4:].strip()
        else:
            self.item_name = raw
            return

        parts = before.split(None, 1)
        if len(parts) == 0:
            return
        if parts[0].isdigit():
            self.quantity = int(parts[0])
            self.item_name = parts[1] if len(parts) > 1 else ""
        else:
            self.item_name = before

    def func(self):
        caller = self.caller
        game = caller.game

        if not self.item_name or not self.shop_name:
            self.caller.msg("Usage: sell [quantity] <item> to <shop>")
            return

        if not caller.is_alive():
            self.caller.msg("You are dead and cannot sell items.")
            return

        from world.data.shops import sell_item

        shop_id = _resolve_shop(self.shop_name)
        if shop_id is None:
            self.caller.msg(f"Unknown shop: '{self.shop_name}'.")
            return

        item_id = _resolve_item(self.item_name)
        if item_id is None:
            self.caller.msg(f"Unknown item: '{self.item_name}'.")
            return

        if self.quantity <= 0:
            self.caller.msg("Quantity must be positive.")
            return

        result = sell_item(game, shop_id, item_id, self.quantity)
        caller.save()

        if result.success:
            self.caller.msg(result.message)
            from world.data.economy import to_display
            self.caller.msg(
                f"New balance: {to_display(result.new_balance)}"
            )
        else:
            self.caller.msg(result.message)


# ==========================================================================
# Phase 19 — Socials, Guild/Sect/PvP Commands
# ==========================================================================


class CmdSocial(Command):
    """
    Perform a social emote, optionally directed at a target.

    Usage:
        social <action> [target]
        emote <action> [target]

    Socials available: wave, bow (sample definitions — extendable via data).

    If the target is on your ignore list, the target will not see the
    social (but you and the room still will).
    """

    key = "social"
    aliases = ["emote"]

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            self.caller.msg("Usage: social <action> [target]")
            return

        from world.data.socials import SOCIAL_REGISTRY, resolve_social

        parts = args.split(None, 1)
        action_name = parts[0].lower()
        target_name = parts[1] if len(parts) > 1 else None

        social_key = resolve_social(action_name)
        if social_key is None:
            self.caller.msg(
                f"Unknown social: '{action_name}'. "
                f"Available: {', '.join(sorted(SOCIAL_REGISTRY.keys()))}"
            )
            return

        social_def = SOCIAL_REGISTRY[social_key]
        actor_name = caller.key

        if target_name:
            target = caller.search(target_name)
            if not target:
                return

            target_key = target.key

            self.caller.msg(
                social_def["self_target_msg"].format(
                    actor=actor_name, target=target_key
                )
            )

            caller_game = caller.game
            target_ignored = target_key.lower() in {
                name.lower() for name in caller_game.ignore_list
            }

            if not target_ignored:
                target.msg(
                    social_def["target_msg"].format(
                        actor=actor_name, target=target_key
                    )
                )

            room_msg = social_def["room_msg"].format(
                actor=actor_name, target=target_key
            )
            caller.location.msg_contents(
                room_msg,
                exclude=[caller, target] if not target_ignored else [caller],
            )
        else:
            self.caller.msg(social_def["self_msg"])
            room_msg = social_def["self_msg"].format(actor=actor_name)
            caller.location.msg_contents(room_msg, exclude=[caller])


class CmdGuild(Command):
    """
    View or manage your guild membership.

    Usage:
        guild                    — show current guild
        guild join <name>        — join a guild
        guild leave              — leave your current guild
        guild info               — show detailed guild information

    Use 'guild join <name>' with a valid guild name.
    """

    key = "guild"

    def func(self):
        caller = self.caller
        game = caller.game
        args = self.args.strip().lower()

        from world.data.socials import (
            resolve_guild, get_guild_name, GUILD_REGISTRY,
        )

        if not args or args == "info":
            if game.guild_id:
                display = get_guild_name(game.guild_id) or game.guild_id
                self.caller.msg(f"|wGuild:|n {display}  [{game.guild_id}]")
            else:
                self.caller.msg(
                    "You are not a member of any guild.\n"
                    f"Available guilds: {', '.join(GUILD_REGISTRY.values())}"
                )
                self.caller.msg("Use: guild join <name>")
            return

        if args.startswith("join "):
            name = self.args.strip()[5:].strip()
            if not name:
                self.caller.msg("Usage: guild join <guild name>")
                return
            guild_id = resolve_guild(name)
            if guild_id is None:
                self.caller.msg(
                    f"Unknown guild: '{name}'. "
                    f"Available: {', '.join(GUILD_REGISTRY.values())}"
                )
                return
            display = get_guild_name(guild_id)
            game.guild_id = guild_id
            caller.save()
            self.caller.msg(f"You have joined |w{display}|n.")
            return

        if args == "leave":
            if game.guild_id is None:
                self.caller.msg("You are not a member of any guild.")
                return
            old_display = get_guild_name(game.guild_id) or game.guild_id
            game.guild_id = None
            caller.save()
            self.caller.msg(f"You have left |w{old_display}|n.")
            return

        self.caller.msg(
            "Usage: guild [join <name>|leave|info]"
        )


class CmdSect(Command):
    """
    View or manage your sect membership.

    Usage:
        sect                     — show current sect
        sect join <name>         — join a sect
        sect leave               — leave your current sect
        sect info                — show detailed sect information

    Use 'sect join <name>' with a valid sect name.
    """

    key = "sect"

    def func(self):
        caller = self.caller
        game = caller.game
        args = self.args.strip().lower()

        from world.data.socials import (
            resolve_sect, get_sect_name, SECT_REGISTRY,
        )

        if not args or args == "info":
            if game.sect_id:
                display = get_sect_name(game.sect_id) or game.sect_id
                self.caller.msg(f"|wSect:|n {display}  [{game.sect_id}]")
            else:
                self.caller.msg(
                    "You are not a member of any sect.\n"
                    f"Available sects: {', '.join(SECT_REGISTRY.values())}"
                )
                self.caller.msg("Use: sect join <name>")
            return

        if args.startswith("join "):
            name = self.args.strip()[5:].strip()
            if not name:
                self.caller.msg("Usage: sect join <sect name>")
                return
            sect_id = resolve_sect(name)
            if sect_id is None:
                self.caller.msg(
                    f"Unknown sect: '{name}'. "
                    f"Available: {', '.join(SECT_REGISTRY.values())}"
                )
                return
            display = get_sect_name(sect_id)
            game.sect_id = sect_id
            caller.save()
            self.caller.msg(f"You have joined |w{display}|n.")
            return

        if args == "leave":
            if game.sect_id is None:
                self.caller.msg("You are not a member of any sect.")
                return
            old_display = get_sect_name(game.sect_id) or game.sect_id
            game.sect_id = None
            caller.save()
            self.caller.msg(f"You have left |w{old_display}|n.")
            return

        self.caller.msg(
            "Usage: sect [join <name>|leave|info]"
        )


class CmdPvP(Command):
    """
    Display your PvP statistics.

    Usage:
        pvp        — show PvP statistics (war points, kills, deaths)

    PvP eligibility is determined by faction alignment and the
    current room's PvP mode.  Opposing-faction characters may
    fight in contested areas.
    """

    key = "pvp"

    def func(self):
        caller = self.caller
        game = caller.game

        self.caller.msg(
            f"|wPvP Statistics|n\n"
            f"  War Points: {game.war_points}\n"
            f"  PvP Kills:  {game.pvp_kills}\n"
            f"  PvP Deaths: {game.pvp_deaths}"
        )


class CmdTalk(Command):
    """
    Speak with an NPC.

    Usage:
        talk <npc name>

    Initiates a dialogue with the named NPC if they have one.
    """

    key = "talk"

    def func(self):
        caller = self.caller

        # Clear any previous dialogue state.
        for _attr in ("dialogue_id", "current_node_id"):
            try:
                delattr(caller.ndb, _attr)
            except AttributeError:
                pass

        args = self.args.strip()

        if not args:
            caller.msg("Talk to whom?")
            return

        target = caller.search(args)
        if not target:
            return

        dialogue_id = target.db.dialogue_id if hasattr(target, "db") else None
        if not dialogue_id:
            caller.msg("They have nothing to say.")
            return

        from world.data.dialogues import start_dialogue

        node = start_dialogue(dialogue_id)
        if node is None:
            caller.msg("They have nothing to say.")
            return

        lines = [node.get("text", "")]
        responses = node.get("responses", [])
        if responses:
            lines.append("")
            for idx, response in enumerate(responses, 1):
                lines.append(f"  {idx}. {response.get('text', '')}")

        caller.msg("\n".join(lines))

        # Store dialogue state for reply command.
        caller.ndb.dialogue_id = dialogue_id
        caller.ndb.current_node_id = node["id"]


class CmdReply(Command):
    """
    Reply to an ongoing NPC conversation.

    Usage:
        reply <number>

    Selects a numbered response from the current dialogue node.
    """

    key = "reply"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        # Read the stored dialogue state.
        dialogue_id = getattr(caller.ndb, "dialogue_id", None)
        current_node_id = getattr(caller.ndb, "current_node_id", None)

        if dialogue_id is None or current_node_id is None:
            caller.msg("You are not in a conversation.")
            return

        # Require a numeric response number.
        if not args:
            caller.msg("Reply with which number?")
            return

        try:
            response_number = int(args)
        except ValueError:
            caller.msg("Usage: reply <number>")
            return

        # Convert 1-based player input to 0-based response index.
        response_index = response_number - 1

        from world.data.dialogues import choose_response

        response, next_node = choose_response(
            dialogue_id,
            current_node_id,
            response_index,
            cd=caller.game,
        )

        # Invalid response (out of range or missing node).
        if response is None:
            caller.msg("Invalid response.")
            return

        if next_node is not None:
            # Update stored node and display the next node.
            caller.ndb.current_node_id = next_node["id"]

            lines = [next_node.get("text", "")]
            responses = next_node.get("responses", [])
            if responses:
                lines.append("")
                for idx, r in enumerate(responses, 1):
                    lines.append(f"  {idx}. {r.get('text', '')}")

            caller.msg("\n".join(lines))
        else:
            # End of conversation — clear state.
            del caller.ndb.dialogue_id
            del caller.ndb.current_node_id


# ==========================================================================
# Post-Phase-20 — Professional WHO List
# ==========================================================================


class CmdWho(Command):
    """
    List all characters currently online.

    Usage:
        who

    Displays a professionally formatted table of every puppeted
    character currently connected to the game, showing their name,
    level, race, profession, faction, guild, and sect affiliation.
    """

    key = "who"
    aliases = ["doing"]
    locks = "cmd:all()"
    account_caller = True

    def func(self):
        """Execute the WHO command."""
        import evennia

        from commands import build_who_rows
        from world.data.socials import get_guild_name, get_sect_name
        from world.data.enums import Faction

        sessions = evennia.SESSION_HANDLER.get_sessions()

        # Collect each unique puppeted character that has CharacterData.
        seen = set()
        characters = []
        for session in sessions:
            if not session.logged_in:
                continue
            puppet = session.get_puppet()
            if puppet is None:
                continue
            # Only include our Rites-of-Passage Character typeclass.
            if not hasattr(puppet, "game"):
                continue
            char_id = id(puppet)
            if char_id in seen:
                continue
            seen.add(char_id)
            characters.append((puppet, puppet.game))

        if not characters:
            self.msg("No characters are currently online.")
            return

        # Sort: highest level first, then alphabetically by name.
        characters.sort(key=lambda c: (-c[1].level, c[1].name.lower()))

        rows = build_who_rows(
            characters, get_guild_name, get_sect_name, Faction,
        )

        table = self.styled_table(
            "Name", "Lv", "Race", "Profession", "Faction", "Guild", "Sect",
            width=78,
        )
        for row in rows:
            table.add_row(*row)

        count = len(characters)
        header = "|wRites of Passage — Players Online|n"
        footer = (
            f"|w{count} character{' is' if count == 1 else 's are'} online.|n"
        )

        self.msg(f"{header}\n\n{table}\n\n{footer}")


# ==========================================================================
# Shared resolution helpers (imported from commands package)
# ==========================================================================

from commands import (
    resolve_item as _resolve_item,
    resolve_slot as _resolve_slot,
    resolve_skill as _resolve_skill,
    resolve_quest as _resolve_quest,
    resolve_shop as _resolve_shop,
)
