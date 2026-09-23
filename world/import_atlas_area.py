import json

from django.conf import settings
from evennia.utils.create import create_object

from world.data.mob_spawner import create_spawn, create_item_spawn, DEFAULT_RESPAWN_SECONDS
from world.data.shops import register_shop, register_shop_item
from world.data.mob_rewards import register_loot_table
from world.data.mobs import register_mob_definition
from world.data.quests import register_quest_definition
from world.data.damage_types import register_damage_type
from world.data.dialogues import register_dialogue
from world.data.factions import register_faction


def import_area(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    area_id = data["areaId"]
    area_name = data["areaName"]

    created = {}

    print(f"Importing {area_name}...")

    for room_data in data.get("rooms", []):
        typeclass_path = room_data.get("typeclassPath") or settings.BASE_ROOM_TYPECLASS
        room = create_object(
            typeclass=typeclass_path,
            key=room_data["title"],
        )

        room.db.desc = room_data.get("description", "")
        room.db.atlas_id = room_data["id"]
        room.db.area_id = area_id
        room.db.area_name = area_name
        room.db.map_x = room_data.get("x", 0)
        room.db.map_y = room_data.get("y", 0)
        room.db.map_z = room_data.get("z", 0)

        # --- new imported fields (when present) ---

        room_type = room_data.get("roomType")
        if room_type is not None:
            room.db.room_type = room_type

        forge_tags = room_data.get("tags")
        if forge_tags:
            for tag in forge_tags:
                room.tags.add(tag, category="forge")

        aliases = room_data.get("aliases")
        if aliases:
            for alias in aliases:
                room.aliases.add(alias["key"], category=alias.get("category"))

        evennia_tags = room_data.get("evenniaTags")
        if evennia_tags:
            for tag in evennia_tags:
                room.tags.add(tag["key"], category=tag.get("category") or "evennia", data=tag.get("data"))

        attributes = room_data.get("attributes")
        if attributes:
            for attr in attributes:
                room.attributes.add(
                    attr["key"],
                    attr.get("value"),
                    category=attr.get("category"),
                    lockstring=attr.get("lockString"),
                )

        permissions = room_data.get("permissions")
        if permissions:
            for perm in permissions:
                room.permissions.add(perm)

        lock_string = room_data.get("lockString")
        if lock_string:
            room.locks.add(lock_string)

        # --- end new fields ---

        room.tags.add(area_id, category="area")

        created[room_data["id"]] = room

        print(f"ROOM #{room.id}: {room.key}")

    for item_data in data.get("items", []):
        typeclass = item_data.get("typeclassPath") or "typeclasses.objects.Object"
        key = item_data["key"]
        item = create_object(
            typeclass=typeclass,
            key=key,
        )

        forge_id = item_data.get("id")
        if forge_id is not None:
            item.db.forge_id = forge_id

        desc = item_data.get("description")
        if desc is not None:
            item.db.desc = desc

        item_type = item_data.get("itemType")
        if item_type is not None:
            item.db.item_type = item_type

        equipment_slot = item_data.get("equipmentSlot")
        if equipment_slot is not None:
            item.db.equipment_slot = equipment_slot

        level_requirement = item_data.get("levelRequirement")
        if level_requirement is not None:
            item.db.level_requirement = level_requirement

        encumbrance = item_data.get("encumbrance")
        if encumbrance is not None:
            item.db.encumbrance = encumbrance

        item_limit = item_data.get("itemLimit")
        if item_limit is not None:
            item.db.item_limit = item_limit

        base_value = item_data.get("baseValue")
        if base_value is not None:
            item.db.base_value = base_value

        is_gettable = item_data.get("isGettable")
        if is_gettable is not None:
            item.db.is_gettable = is_gettable

        is_droppable = item_data.get("isDroppable")
        if is_droppable is not None:
            item.db.is_droppable = is_droppable

        is_sellable = item_data.get("isSellable")
        if is_sellable is not None:
            item.db.is_sellable = is_sellable

        is_tradeable = item_data.get("isTradeable")
        if is_tradeable is not None:
            item.db.is_tradeable = is_tradeable

        is_unique = item_data.get("isUnique")
        if is_unique is not None:
            item.db.is_unique = is_unique

        is_quest_item = item_data.get("isQuestItem")
        if is_quest_item is not None:
            item.db.is_quest_item = is_quest_item

        is_magical = item_data.get("isMagical")
        if is_magical is not None:
            item.db.is_magical = is_magical

        magic_level = item_data.get("magicLevel")
        if magic_level is not None:
            item.db.magic_level = magic_level

        weapon_data = item_data.get("weaponData")
        if weapon_data is not None:
            item.db.weapon_data = weapon_data

        armor_data = item_data.get("armorData")
        if armor_data is not None:
            item.db.armor_data = armor_data

        aliases = item_data.get("aliases")
        if aliases:
            for alias in aliases:
                item.aliases.add(alias["key"], category=alias.get("category"))

        evennia_tags = item_data.get("evenniaTags")
        if evennia_tags:
            for tag in evennia_tags:
                item.tags.add(tag["key"], category=tag.get("category") or "evennia", data=tag.get("data"))

        attributes = item_data.get("attributes")
        if attributes:
            for attr in attributes:
                item.attributes.add(
                    attr["key"],
                    attr.get("value"),
                    category=attr.get("category"),
                    lockstring=attr.get("lockString"),
                )

        permissions = item_data.get("permissions")
        if permissions:
            for perm in permissions:
                item.permissions.add(perm)

        lock_string = item_data.get("lockString")
        if lock_string:
            item.locks.add(lock_string)

        requirements = item_data.get("requirements")
        if requirements:
            item.db.requirements = requirements

        modifiers = item_data.get("modifiers")
        if modifiers:
            item.db.modifiers = modifiers

        effects = item_data.get("effects")
        if effects:
            item.db.effects = effects

        sources = item_data.get("sources")
        if sources:
            item.db.sources = sources

        crafting_components = item_data.get("craftingComponents")
        if crafting_components:
            item.db.crafting_components = crafting_components

        print(f"ITEM #{item.id}: {item.key}")

    for exit_data in data.get("exits", []):
        source = created[exit_data["sourceRoomId"]]
        destination = created[exit_data["destinationRoomId"]]

        key = exit_data.get("key") or exit_data["direction"]

        typeclass_path = exit_data.get("typeclassPath") or settings.BASE_EXIT_TYPECLASS
        exit_obj = create_object(
            typeclass=typeclass_path,
            key=key,
            location=source,
            destination=destination,
        )

        exit_obj.db.desc = exit_data.get("description", "")

        reverse_direction = exit_data.get("reverseDirection")
        if reverse_direction is not None:
            exit_obj.db.reverse_direction = reverse_direction

        is_one_way = exit_data.get("isOneWay")
        if is_one_way is not None:
            exit_obj.db.is_one_way = is_one_way

        exit_type = exit_data.get("exitType")
        if exit_type is not None:
            exit_obj.db.exit_type = exit_type

        aliases_list = exit_data.get("aliasesList")
        if aliases_list:
            for alias in aliases_list:
                exit_obj.aliases.add(alias["key"], category=alias.get("category"))

        evennia_tags = exit_data.get("evenniaTags")
        if evennia_tags:
            for tag in evennia_tags:
                exit_obj.tags.add(tag["key"], category=tag.get("category") or "evennia", data=tag.get("data"))

        attributes = exit_data.get("attributes")
        if attributes:
            for attr in attributes:
                exit_obj.attributes.add(
                    attr["key"],
                    attr.get("value"),
                    category=attr.get("category"),
                    lockstring=attr.get("lockString"),
                )

        permissions = exit_data.get("permissions")
        if permissions:
            for perm in permissions:
                exit_obj.permissions.add(perm)

        lock_string = exit_data.get("lockString")
        if lock_string:
            exit_obj.locks.add(lock_string)

        door_data = exit_data.get("door")
        if door_data:
            name = door_data.get("name")
            if name is not None:
                exit_obj.attributes.add("name", name, category="door")

            starts_open = door_data.get("startsOpen")
            if starts_open is not None:
                exit_obj.attributes.add("startsOpen", starts_open, category="door")

            starts_closed = door_data.get("startsClosed")
            if starts_closed is not None:
                exit_obj.attributes.add("startsClosed", starts_closed, category="door")

            starts_locked = door_data.get("startsLocked")
            if starts_locked is not None:
                exit_obj.attributes.add("startsLocked", starts_locked, category="door")

            key_id = door_data.get("keyId")
            if key_id is not None:
                exit_obj.attributes.add("keyId", key_id, category="door")

            shared_door_id = door_data.get("sharedDoorId")
            if shared_door_id is not None:
                exit_obj.attributes.add("sharedDoorId", shared_door_id, category="door")

            door_typeclass = door_data.get("typeclass")
            if door_typeclass is not None:
                exit_obj.attributes.add("typeclass", door_typeclass, category="door")

            lockable = door_data.get("lockable")
            if lockable is not None:
                exit_obj.attributes.add("lockable", lockable, category="door")

            synchronize_opposite = door_data.get("synchronizeOpposite")
            if synchronize_opposite is not None:
                exit_obj.attributes.add("synchronizeOpposite", synchronize_opposite, category="door")

            traverse_lock_string = door_data.get("traverseLockString")
            if traverse_lock_string is not None:
                exit_obj.attributes.add("traverseLockString", traverse_lock_string, category="door")

            locked_failure_message = door_data.get("lockedFailureMessage")
            if locked_failure_message is not None:
                exit_obj.attributes.add("lockedFailureMessage", locked_failure_message, category="door")

            closed_failure_message = door_data.get("closedFailureMessage")
            if closed_failure_message is not None:
                exit_obj.attributes.add("closedFailureMessage", closed_failure_message, category="door")

            door_description = door_data.get("description")
            if door_description is not None:
                exit_obj.attributes.add("description", door_description, category="door")

            door_aliases = door_data.get("doorAliases")
            if door_aliases:
                for alias in door_aliases:
                    exit_obj.aliases.add(alias["key"], category=alias.get("category"))

            door_tags = door_data.get("doorTags")
            if door_tags:
                for tag in door_tags:
                    exit_obj.tags.add(tag["key"], category=tag.get("category") or "door", data=tag.get("data"))

            door_attributes = door_data.get("doorAttributes")
            if door_attributes:
                for attr in door_attributes:
                    exit_obj.attributes.add(
                        attr["key"],
                        attr.get("value"),
                        category=attr.get("category"),
                        lockstring=attr.get("lockString"),
                    )

            door_permissions = door_data.get("doorPermissions")
            if door_permissions:
                for perm in door_permissions:
                    exit_obj.permissions.add(perm)

        print(f"EXIT: {source.key} --{key}--> {destination.key}")

    for npc_data in data.get("npcs", []):
        typeclass = npc_data.get("typeclassPath") or "typeclasses.characters.Character"
        key = npc_data["key"]
        npc = create_object(
            typeclass=typeclass,
            key=key,
        )

        forge_id = npc_data.get("id")
        if forge_id is not None:
            npc.db.forge_id = forge_id

        desc = npc_data.get("description")
        if desc is not None:
            npc.db.desc = desc

        loot_table_id = npc_data.get("lootTableId")
        if loot_table_id is not None:
            npc.db.loot_table_id = loot_table_id

        register_mob_definition(
            npc_data["id"],
            npc_data["key"],
            loot_table_id=npc_data.get("lootTableId"),
        )

        dialogue_id = npc_data.get("dialogueId")
        if dialogue_id is not None:
            npc.db.dialogue_id = dialogue_id

        classification = npc_data.get("classification")
        if classification is not None:
            npc.db.classification = classification

        stats = npc_data.get("stats")
        if stats is not None:
            npc.db.stats = stats

        aliases = npc_data.get("aliases")
        if aliases:
            for alias in aliases:
                npc.aliases.add(alias["key"], category=alias.get("category"))

        evennia_tags = npc_data.get("evenniaTags")
        if evennia_tags:
            for tag in evennia_tags:
                npc.tags.add(tag["key"], category=tag.get("category") or "evennia", data=tag.get("data"))

        attributes = npc_data.get("attributes")
        if attributes:
            for attr in attributes:
                npc.attributes.add(
                    attr["key"],
                    attr.get("value"),
                    category=attr.get("category"),
                    lockstring=attr.get("lockString"),
                )

        permissions = npc_data.get("permissions")
        if permissions:
            for perm in permissions:
                npc.permissions.add(perm)

        lock_string = npc_data.get("lockString")
        if lock_string:
            npc.locks.add(lock_string)

        combat = npc_data.get("combat")
        if combat is not None:
            npc.db.combat = combat

        abilities = npc_data.get("abilities")
        if abilities is not None:
            npc.db.abilities = abilities

        resistances = npc_data.get("resistances")
        if resistances:
            npc.db.resistances = resistances

        behavior = npc_data.get("behavior")
        if behavior is not None:
            npc.db.behavior = behavior

        equipment = npc_data.get("equipment")
        if equipment:
            npc.db.equipment = equipment

        inventory = npc_data.get("inventory")
        if inventory:
            npc.db.inventory = inventory

        patrol = npc_data.get("patrol")
        if patrol is not None:
            npc.db.patrol = patrol

        # Mark as world NPC (same pattern as create_npc_from_spawn)
        npc.attributes.add("world_npc", True)
        npc.tags.add("world_npc", category="world_role")

        print(f"NPC #{npc.id}: {npc.key}")

    for spawn_data in data.get("spawns", []):
        entity_type = spawn_data.get("entityType")
        if entity_type == "npc":
            quantity = spawn_data.get("quantity", 1)
            enabled = spawn_data.get("enabled", True)
            result = create_spawn(
                spawn_id=spawn_data["id"],
                mob_id=spawn_data["entityId"],
                location_id=spawn_data.get("roomId", "unknown"),
                respawn_seconds=spawn_data.get("respawnSeconds", DEFAULT_RESPAWN_SECONDS),
                quantity=quantity,
                enabled=enabled,
            )
            if isinstance(result, str):
                print(f"SPAWN ERROR: {result}")
            else:
                print(f"NPC SPAWN #{spawn_data['id']}: {spawn_data.get('entityId')}")
        elif entity_type == "item":
            result = create_item_spawn(
                spawn_id=spawn_data["id"],
                location_id=spawn_data.get("roomId", "unknown"),
                item_id=spawn_data["entityId"],
                quantity=spawn_data.get("quantity", 1),
                respawn_seconds=spawn_data.get("respawnSeconds", DEFAULT_RESPAWN_SECONDS),
                enabled=spawn_data.get("enabled", True),
            )
            if isinstance(result, str):
                print(f"ITEM SPAWN ERROR: {result}")
            else:
                print(f"ITEM SPAWN #{spawn_data['id']}: {spawn_data.get('entityId')} x{spawn_data.get('quantity', 1)}")
        else:
            print(f"SPAWN SKIP: unknown entityType '{entity_type}' for spawn '{spawn_data.get('id')}'")

    for shop_data in data.get("shops", []):
        shop = register_shop(
            shop_data["id"],
            shop_data["key"],
            npc_id=shop_data.get("npcId"),
            description=shop_data.get("description", ""),
        )

        # --- imported fields for shop ---
        shop["aliases"] = shop_data.get("aliases")
        shop["evennia_tags"] = shop_data.get("evenniaTags")
        shop["attributes"] = shop_data.get("attributes")
        shop["permissions"] = shop_data.get("permissions")
        shop["lock_string"] = shop_data.get("lockString")
        shop["typeclass_path"] = shop_data.get("typeclassPath")
        # --- end imported fields ---

        for entry in shop_data.get("inventory", []):
            stock = None if entry.get("isUnlimited") else entry.get("quantity")
            register_shop_item(
                shop_data["id"],
                entry["itemId"],
                buy_price=entry.get("buyPrice"),
                sell_price=entry.get("sellPrice"),
                stock=stock,
                enabled=entry.get("isEnabled", True),
            )
        print(f"SHOP: {shop_data['key']} ({shop_data['id']})")

    for table_data in data.get("lootTables", []):
        entries = []
        for entry in table_data.get("entries", []):
            if not entry.get("isEnabled", True):
                continue
            converted = {
                "item_id": entry["itemId"],
                "chance": entry["chancePercent"] / 100.0,
            }
            qmin = entry.get("quantityMin", 1)
            qmax = entry.get("quantityMax", 1)
            if qmin == qmax:
                converted["quantity"] = int(qmin)
            else:
                converted["quantity"] = (int(qmin), int(qmax))
            entries.append(converted)
        register_loot_table(table_data["id"], entries)

    for quest_data in data.get("quests", []):
        objectives = []
        for obj in quest_data.get("objectives", []):
            obj_type = obj.get("objectiveType", "")
            target_id = obj.get("targetId", "")
            count = obj.get("requiredCount", 1)
            if obj_type == "killnpc":
                objectives.append({
                    "type": "kill",
                    "mob_id": target_id,
                    "count": count,
                })
            elif obj_type == "collectitem":
                objectives.append({
                    "type": "collect",
                    "item_id": target_id,
                    "count": count,
                })

        item_rewards = []
        for ir in quest_data.get("itemRewards", []):
            item_rewards.append({
                "item_id": ir["itemId"],
                "quantity": ir.get("quantity", 1),
            })

        register_quest_definition(
            quest_id=quest_data["id"],
            name=quest_data["key"],
            description=quest_data.get("description", ""),
            objectives=objectives,
            xp_reward=quest_data.get("experienceReward", 0),
            currency_reward=int(quest_data.get("currencyReward", 0)),
            item_rewards=item_rewards,
            reward_loot_table_id=quest_data.get("rewardLootTableId") or None,
            giver_npc_id=quest_data.get("giverNpcId") or None,
            turn_in_npc_id=quest_data.get("turnInNpcId") or None,
        )
        print(f"QUEST: {quest_data['key']} ({quest_data['id']})")

    for dialogue_data in data.get("dialogues", []):
        nodes = []
        for node in dialogue_data.get("nodes", []):
            responses = []
            for resp in node.get("responses", []):
                responses.append({
                    "text": resp.get("text", ""),
                    "nextNodeId": resp.get("nextNodeId"),
                    "startsQuestId": resp.get("startsQuestId"),
                    "completesQuestId": resp.get("completesQuestId"),
                })
            nodes.append({
                "id": node.get("id"),
                "text": node.get("text", ""),
                "speakerNpcId": node.get("speakerNpcId"),
                "speakerName": node.get("speakerName", ""),
                "responses": responses,
            })

        register_dialogue(
            dialogue_id=dialogue_data["id"],
            name=dialogue_data["key"],
            description=dialogue_data.get("description", ""),
            start_node_id=dialogue_data.get("startNodeId"),
            nodes=nodes,
        )
        print(f"DIALOGUE: {dialogue_data['key']} ({dialogue_data['id']})")

    for damage_type_data in data.get("damageTypes", []):
        register_damage_type(
            damage_type_data["id"],
            damage_type_data["name"],
            description=damage_type_data.get("description", ""),
        )
        print(f"DAMAGE TYPE: {damage_type_data['name']} ({damage_type_data['id']})")

    for faction_data in data.get("factions", []):
        register_faction(
            faction_data["id"],
            faction_data["name"],
            description=faction_data.get("description", ""),
        )
        print(f"FACTION: {faction_data['name']} ({faction_data['id']})")

    print()
    print(f"{area_name} import complete.")

    for room in created.values():
        if room.key == "Dawnreach Sanctuary":
            print(f"Dawnreach Sanctuary DBREF: #{room.id}")
            break


if __name__ == "__main__":
    raise SystemExit("Run this through Evennia shell.")
