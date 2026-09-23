"""
Silvermere path audit helper.

Finds shortest cardinal movement paths from Town Square through the verified
Silvermere dataset.

DATA ONLY.
No Evennia database changes are made.
"""

from collections import deque

from world.silvermere_data import build_silvermere_dataset


START_ROOM_ID = "silvermere_town_square"


def shortest_paths(dataset, start_room_id):
    """
    Breadth-first search from the starting room.
    Returns:
        paths[room_id] = ["north", "west", ...]
    """

    paths = {
        start_room_id: []
    }

    queue = deque([start_room_id])

    while queue:
        current_id = queue.popleft()
        current_path = paths[current_id]

        exits = dataset[current_id]["exits"]

        for direction, destination_id in exits.items():
            if destination_id in paths:
                continue

            paths[destination_id] = (
                current_path + [direction]
            )

            queue.append(destination_id)

    return paths


def compress_path(path):
    """
    Turn:
        ["east", "east", "east", "south"]

    into:
        "3 east, south"
    """

    if not path:
        return "HERE"

    parts = []
    current = path[0]
    count = 1

    for direction in path[1:]:
        if direction == current:
            count += 1
        else:
            if count == 1:
                parts.append(current)
            else:
                parts.append(f"{count} {current}")

            current = direction
            count = 1

    if count == 1:
        parts.append(current)
    else:
        parts.append(f"{count} {current}")

    return ", ".join(parts)


def print_named_rooms(dataset, paths):
    print()
    print("Named locations from Town Square")
    print("=" * 80)

    for room_id, data in dataset.items():
        # Ignore generic temporary Silvermere coordinate names.
        if data["name"].startswith("Silvermere ("):
            continue

        path = paths.get(room_id)

        if path is None:
            path_text = "UNREACHABLE"
        else:
            path_text = compress_path(path)

        print(
            f"{room_id:<24} "
            f"{path_text:<28} "
            f"{data['name']}"
        )


def print_special_symbols(dataset, paths):
    print()
    print("Special-symbol rooms from Town Square")
    print("=" * 80)

    special_symbols = {
        "L",
        "S",
        "K",
        "M",
        "N",
        "V",
        "W",
        "Y",
        "F",
        "I",
    }

    rows = []

    for room_id, data in dataset.items():
        if data["symbol"] not in special_symbols:
            continue

        path = paths.get(room_id)

        if path is None:
            path_text = "UNREACHABLE"
            distance = 999999
        else:
            path_text = compress_path(path)
            distance = len(path)

        rows.append(
            (
                distance,
                data["source_line"],
                data["source_col"],
                room_id,
                data["symbol"],
                path_text,
                data["name"],
            )
        )

    rows.sort()

    for (
        distance,
        line,
        col,
        room_id,
        symbol,
        path_text,
        name,
    ) in rows:
        print(
            f"{room_id:<24} "
            f"sym={symbol:<2} "
            f"path={path_text:<30} "
            f"line={line:<3} "
            f"col={col:<3} "
            f"name={name}"
        )


def print_nearby_rooms(dataset, paths, max_distance=8):
    print()
    print(
        f"Rooms within {max_distance} moves of Town Square"
    )
    print("=" * 80)

    rows = []

    for room_id, path in paths.items():
        if len(path) > max_distance:
            continue

        data = dataset[room_id]

        rows.append(
            (
                len(path),
                compress_path(path),
                room_id,
                data["symbol"],
                data["name"],
            )
        )

    rows.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2],
        )
    )

    for distance, path_text, room_id, symbol, name in rows:
        print(
            f"{distance:02d} "
            f"{path_text:<30} "
            f"{room_id:<24} "
            f"sym={symbol:<2} "
            f"{name}"
        )


def main():
    dataset = build_silvermere_dataset()

    paths = shortest_paths(
        dataset,
        START_ROOM_ID,
    )

    print()
    print("Silvermere path audit")
    print("=" * 80)
    print(f"Dataset rooms:   {len(dataset)}")
    print(f"Reachable rooms: {len(paths)}")

    unreachable = [
        room_id
        for room_id in dataset
        if room_id not in paths
    ]

    print(f"Unreachable:     {len(unreachable)}")

    if unreachable:
        print()
        print("Unreachable room IDs:")
        for room_id in unreachable:
            print(f"  {room_id}")

    print_named_rooms(
        dataset,
        paths,
    )

    print_special_symbols(
        dataset,
        paths,
    )

    print_nearby_rooms(
        dataset,
        paths,
        max_distance=8,
    )

    print()
    print("DATA ONLY")
    print(
        "No Evennia database objects were "
        "created or modified."
    )


if __name__ == "__main__":
    main()
