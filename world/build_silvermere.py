"""
Idempotent Evennia builder for Silvermere.

Normal run:
    python world/build_silvermere.py

This performs a DRY RUN only.

Apply changes:
    evennia shell -c "exec(open('world/build_silvermere.py').read())"

The APPLY flag below must also be set True before database changes are allowed.

This builder:
- creates/updates Silvermere rooms
- creates/updates cardinal exits
- uses stable room IDs
- tags everything as Silvermere
- does not touch unrelated areas
"""

from evennia import create_object, search_object

from world.silvermere_data import (
    build_silvermere_dataset,
    validate_dataset,
)


APPLY = False

ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"

ZONE_TAG = "silvermere"
ROOM_ID_CATEGORY = "world_room_id"
ZONE_CATEGORY = "world_zone"


OPPOSITE = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}


def find_room_by_world_id(room_id):
    """
    Find an existing room using our permanent Silvermere ID.
    """

    matches = search_object(
        room_id,
        attribute_name="world_room_id",
    )

    exact = [
        obj
        for obj in matches
        if obj.attributes.get("world_room_id") == room_id
    ]

    if len(exact) > 1:
        raise RuntimeError(
            f"Duplicate world_room_id detected: {room_id}"
        )

    return exact[0] if exact else None


def create_or_update_room(data):
    """
    Create a room if missing, otherwise update the existing one.
    """

    room_id = data["room_id"]

    room = find_room_by_world_id(room_id)

    created = False

    if room is None:
        room = create_object(
            typeclass=ROOM_TYPECLASS,
            key=data["name"],
        )
        created = True

    # Stable identity.
    room.attributes.add(
        "world_room_id",
        room_id,
    )

    room.attributes.add(
        "world_zone",
        ZONE_TAG,
    )

    # Display data.
    room.key = data["name"]
    room.db.desc = data["description"]

    # Source-map information.
    room.attributes.add(
        "source_line",
        data["source_line"],
    )

    room.attributes.add(
        "source_col",
        data["source_col"],
    )

    room.attributes.add(
        "source_symbol",
        data["symbol"],
    )

    room.attributes.add(
        "street",
        data.get("street"),
    )

    # Useful future metadata.
    room.attributes.add(
        "planned_npc",
        data.get("npc"),
    )

    # Zone tag.
    room.tags.add(
        ZONE_TAG,
        category=ZONE_CATEGORY,
    )

    # Feature tags.
    for tag in data.get("tags", []):
        room.tags.add(
            tag,
            category="silvermere_feature",
        )

    return room, created


def find_directional_exit(source_room, direction):
    """
    Find an existing cardinal exit on a room.
    """

    matches = []

    for obj in source_room.contents:
        if (
            obj.destination is not None
            and obj.key.lower() == direction.lower()
        ):
            matches.append(obj)

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple '{direction}' exits found in "
            f"{source_room.key} ({source_room.dbref})"
        )

    return matches[0] if matches else None


def create_or_update_exit(
    source_room,
    direction,
    destination_room,
):
    """
    Create/update one cardinal exit.
    """

    exit_obj = find_directional_exit(
        source_room,
        direction,
    )

    created = False

    if exit_obj is None:
        exit_obj = create_object(
            typeclass=EXIT_TYPECLASS,
            key=direction,
            location=source_room,
            destination=destination_room,
        )
        created = True

    else:
        exit_obj.key = direction
        exit_obj.location = source_room
        exit_obj.destination = destination_room

    exit_obj.tags.add(
        ZONE_TAG,
        category=ZONE_CATEGORY,
    )

    exit_obj.attributes.add(
        "world_zone",
        ZONE_TAG,
    )

    return exit_obj, created


def audit_existing_silvermere(dataset):
    """
    Report what would happen without modifying the database.
    """

    existing = 0
    missing = 0

    print()
    print("Silvermere builder dry run")
    print("=" * 72)

    for room_id, data in dataset.items():
        room = find_room_by_world_id(room_id)

        if room:
            existing += 1
        else:
            missing += 1

    total_directional_exits = sum(
        len(data["exits"])
        for data in dataset.values()
    )

    print(f"Dataset rooms:              {len(dataset)}")
    print(f"Existing Silvermere rooms: {existing}")
    print(f"Rooms that would be made:  {missing}")
    print(
        f"Directional exits expected: "
        f"{total_directional_exits}"
    )

    town_square = dataset["silvermere_town_square"]

    print()
    print("Town Square")
    print("=" * 72)
    print(f"Name: {town_square['name']}")
    print(
        f"Map: line {town_square['source_line']}, "
        f"column {town_square['source_col']}"
    )

    for direction, destination in (
        town_square["exits"].items()
    ):
        print(
            f"  {direction:<5} -> {destination}"
        )

    print()
    print("DRY RUN ONLY")
    print("No Evennia database objects were modified.")


def build_rooms(dataset):
    """
    First pass: create/update every room.
    """

    room_objects = {}

    created = 0
    updated = 0

    print()
    print("Building Silvermere rooms")
    print("=" * 72)

    for room_id, data in dataset.items():
        room, was_created = create_or_update_room(
            data
        )

        room_objects[room_id] = room

        if was_created:
            created += 1
            action = "CREATE"
        else:
            updated += 1
            action = "UPDATE"

        print(
            f"{action:<6} "
            f"{room_id:<24} "
            f"{room.key}"
        )

    print()
    print(f"Rooms created: {created}")
    print(f"Rooms updated: {updated}")

    return room_objects


def build_exits(dataset, room_objects):
    """
    Second pass: create/update all cardinal exits.
    """

    created = 0
    updated = 0

    print()
    print("Building Silvermere exits")
    print("=" * 72)

    for room_id, data in dataset.items():
        source_room = room_objects[room_id]

        for direction, destination_id in (
            data["exits"].items()
        ):
            destination_room = (
                room_objects[destination_id]
            )

            exit_obj, was_created = (
                create_or_update_exit(
                    source_room,
                    direction,
                    destination_room,
                )
            )

            if was_created:
                created += 1
            else:
                updated += 1

    print(f"Exits created: {created}")
    print(f"Exits updated: {updated}")


def verify_built_world(dataset, room_objects):
    """
    Verify the resulting database objects.
    """

    errors = []

    if len(room_objects) != len(dataset):
        errors.append(
            "Room object count does not match dataset."
        )

    for room_id, data in dataset.items():
        room = room_objects[room_id]

        if (
            room.attributes.get("world_room_id")
            != room_id
        ):
            errors.append(
                f"{room_id}: world_room_id mismatch."
            )

        for direction, destination_id in (
            data["exits"].items()
        ):
            exit_obj = find_directional_exit(
                room,
                direction,
            )

            if exit_obj is None:
                errors.append(
                    f"{room_id}: missing "
                    f"{direction} exit."
                )
                continue

            expected_destination = (
                room_objects[destination_id]
            )

            if (
                exit_obj.destination
                != expected_destination
            ):
                errors.append(
                    f"{room_id}: {direction} "
                    f"points to wrong destination."
                )

    print()
    print("Database verification")
    print("=" * 72)

    if errors:
        print(
            f"FAIL: {len(errors)} problem(s)"
        )

        for error in errors:
            print(f"  - {error}")

        return False

    print(
        "PASS: Silvermere rooms and exits "
        "match the dataset."
    )

    return True


def main():
    dataset = build_silvermere_dataset()

    errors = validate_dataset(dataset)

    if errors:
        print()
        print("ABORTED")
        print("=" * 72)

        for error in errors:
            print(f"  - {error}")

        raise RuntimeError(
            "Silvermere dataset failed validation."
        )

    if not APPLY:
        audit_existing_silvermere(dataset)
        return

    print()
    print("APPLY MODE ENABLED")
    print("=" * 72)
    print(
        "Silvermere database objects will now "
        "be created or updated."
    )

    room_objects = build_rooms(dataset)

    build_exits(
        dataset,
        room_objects,
    )

    success = verify_built_world(
        dataset,
        room_objects,
    )

    if not success:
        raise RuntimeError(
            "Silvermere database verification failed."
        )

    town_square = (
        room_objects["silvermere_town_square"]
    )

    print()
    print("Silvermere build complete")
    print("=" * 72)
    print(f"Rooms: {len(room_objects)}")
    print(
        f"Town Square: "
        f"{town_square.key} "
        f"({town_square.dbref})"
    )


if __name__ == "__main__":
    main()
