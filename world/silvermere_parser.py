from pathlib import Path

MAP_FILE = Path("/root/newworld/newworld/world/silvermere.txt")

ROOM_MARKERS = {
    "*",
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

NON_ROOM_MARKERS = {
    "#",
    "$",
    "U",
    "D",
    "@",
    "?",
}

MAIN_START_LINE = 46
MAIN_END_LINE = 90

TOWN_SQUARE_LINE = 72
TOWN_SQUARE_COL = 45


def load_lines():
    return MAP_FILE.read_text().splitlines()


def get_char(lines, line_number, col_number):
    if line_number < 1 or line_number > len(lines):
        return " "

    line = lines[line_number - 1]

    if col_number < 1 or col_number > len(line):
        return " "

    return line[col_number - 1]


def collect_main_rooms(lines):
    rooms = []

    for line_number in range(MAIN_START_LINE, MAIN_END_LINE + 1):
        line = lines[line_number - 1]

        for col_index, ch in enumerate(line):
            if ch in ROOM_MARKERS:
                rooms.append(
                    {
                        "source_line": line_number,
                        "source_col": col_index + 1,
                        "symbol": ch,
                    }
                )

    return rooms


def remove_text_contamination(rooms):
    clean = []

    for room in rooms:
        line = room["source_line"]
        col = room["source_col"]

        # Ignore Mayor Godfrey / Sheriff Lionheart text.
        if line in (46, 47) and col >= 31:
            continue

        clean.append(room)

    return clean


def assign_room_ids(rooms):
    for room in rooms:
        line = room["source_line"]
        col = room["source_col"]

        if line == TOWN_SQUARE_LINE and col == TOWN_SQUARE_COL:
            room["room_id"] = "silvermere_town_square"
            room["name"] = "Town Square"
        else:
            room["room_id"] = f"silvermere_l{line}_c{col}"
            room["name"] = None

    return rooms


def make_room_lookup(rooms):
    return {
        (room["source_line"], room["source_col"]): room
        for room in rooms
    }


def find_horizontal_connection(lines, room_lookup, room, direction):
    line = room["source_line"]
    col = room["source_col"]

    step = 1 if direction == "east" else -1
    current_col = col + step

    saw_connector = False

    while 1 <= current_col <= 200:
        ch = get_char(lines, line, current_col)

        if (line, current_col) in room_lookup:
            if saw_connector:
                return room_lookup[(line, current_col)]
            return None

        if ch == "-":
            saw_connector = True

        elif ch == "$":
            # $ replaces the normal horizontal passage marker.
            # It represents a restricted passage, but the two rooms
            # are still physically connected.
            saw_connector = True

        elif ch in NON_ROOM_MARKERS:
            # Other annotations do not by themselves create
            # a cardinal connection.
            pass

        elif ch == " ":
            # Spaces may exist in old ASCII formatting.
            pass

        elif ch == "|":
            return None

        else:
            return None

        current_col += step

    return None


def _trace_vertical_column(lines, room_lookup, line, col, step):
    """Trace vertically at a specific column.  Returns a room dict or None."""
    saw_connector = False
    current_line = line + step

    while MAIN_START_LINE <= current_line <= MAIN_END_LINE:
        ch = get_char(lines, current_line, col)

        if (current_line, col) in room_lookup:
            if saw_connector:
                return room_lookup[(current_line, col)]
            return None

        if ch == "|":
            saw_connector = True

        elif ch in NON_ROOM_MARKERS:
            pass

        elif ch == " ":
            pass

        elif ch == "-":
            return None

        else:
            return None

        current_line += step

    return None


def find_vertical_connection(lines, room_lookup, room, direction):
    line = room["source_line"]
    col = room["source_col"]

    step = 1 if direction == "south" else -1

    # Primary: exact same column.
    result = _trace_vertical_column(
        lines, room_lookup, line, col, step,
    )

    if result is not None:
        return result

    # Fallback: +/-1 column tolerance for legacy ASCII-art column drift.
    #
    # The Silvermere map occasionally shifts vertical-pipe columns
    # one position left or right of the room markers they connect.
    # This is a verified pattern at l68c44 (pipe at c45 for room
    # at c44) and across the l85 connector row (pipes at c44, c52,
    # c64, c68, c72, c76, c84 for rooms at c45, c53, c65, c69,
    # c73, c77, c85).
    #
    # We only accept the fallback when the offset column has a pipe
    # AND a room exists at both ends.

    for offset in (-1, 1):
        candidate_col = col + offset
        result = _trace_vertical_column(
            lines, room_lookup, line, candidate_col, step,
        )

        if result is not None:
            return result

    return None


def detect_exits(lines, rooms):
    room_lookup = make_room_lookup(rooms)

    for room in rooms:
        exits = {}

        north = find_vertical_connection(
            lines, room_lookup, room, "north"
        )
        south = find_vertical_connection(
            lines, room_lookup, room, "south"
        )
        east = find_horizontal_connection(
            lines, room_lookup, room, "east"
        )
        west = find_horizontal_connection(
            lines, room_lookup, room, "west"
        )

        if north:
            exits["north"] = north["room_id"]

        if south:
            exits["south"] = south["room_id"]

        if east:
            exits["east"] = east["room_id"]

        if west:
            exits["west"] = west["room_id"]

        room["exits"] = exits

    return rooms


def print_summary(rooms):
    total_exits = sum(len(room["exits"]) for room in rooms)

    print()
    print("Silvermere MAIN MAP dry-run")
    print("=" * 72)
    print(f"Physical rooms detected: {len(rooms)}")
    print(f"Directional exits detected: {total_exits}")
    print()

    counts = {}

    for room in rooms:
        symbol = room["symbol"]
        counts[symbol] = counts.get(symbol, 0) + 1

    print("Physical room counts by symbol:")

    for symbol in sorted(counts):
        print(f"  {symbol!r}: {counts[symbol]}")


def print_town_square(rooms):
    print()
    print("Town Square")
    print("=" * 72)

    match = next(
        (
            room
            for room in rooms
            if room["room_id"] == "silvermere_town_square"
        ),
        None,
    )

    if not match:
        print("FAIL: Town Square not found.")
        return

    print("PASS")
    print(f"  ID:      {match['room_id']}")
    print(f"  Line:    {match['source_line']}")
    print(f"  Column:  {match['source_col']}")
    print("  Exits:")

    if not match["exits"]:
        print("    NONE")
    else:
        for direction, destination in match["exits"].items():
            print(f"    {direction:<5} -> {destination}")


def print_connection_errors(rooms):
    room_lookup = {
        room["room_id"]: room
        for room in rooms
    }

    opposite = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }

    errors = []

    for room in rooms:
        for direction, destination_id in room["exits"].items():
            destination = room_lookup[destination_id]
            reverse = opposite[direction]

            if destination["exits"].get(reverse) != room["room_id"]:
                errors.append(
                    (
                        room["room_id"],
                        direction,
                        destination_id,
                        reverse,
                    )
                )

    print()
    print("Bidirectional exit audit")
    print("=" * 72)

    if not errors:
        print("PASS: Every detected exit has a matching reverse exit.")
    else:
        print(f"FAIL: {len(errors)} mismatched exits found.")

        for error in errors:
            source, direction, destination, reverse = error

            print(
                f"  {source} --{direction}--> {destination} "
                f"but reverse {reverse} is missing"
            )


def print_room_inventory(rooms):
    print()
    print("Room inventory with exits")
    print("=" * 72)

    for number, room in enumerate(rooms, 1):
        exits = ", ".join(
            f"{direction}={destination}"
            for direction, destination in room["exits"].items()
        )

        if not exits:
            exits = "NONE"

        print(
            f"{number:03d} "
            f"{room['room_id']:<24} "
            f"symbol={room['symbol']!r:<4} "
            f"line={room['source_line']:3d} "
            f"col={room['source_col']:3d} "
            f"exits=[{exits}]"
        )


def main():
    lines = load_lines()

    rooms = collect_main_rooms(lines)
    rooms = remove_text_contamination(rooms)
    rooms = assign_room_ids(rooms)
    rooms = detect_exits(lines, rooms)

    print_summary(rooms)
    print_town_square(rooms)
    print_connection_errors(rooms)
    print_room_inventory(rooms)

    print()
    print("DRY RUN ONLY")
    print("No Evennia database objects were created or modified.")


if __name__ == "__main__":
    main()
