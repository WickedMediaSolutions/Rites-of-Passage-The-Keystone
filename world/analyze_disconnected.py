"""Analyze disconnected rooms to find column offsets for vertical connections."""
lines = open("/root/newworld/newworld/world/silvermere.txt").readlines()

ROOM_M = {"*","L","S","K","M","N","V","W","Y","F","I"}
NON_M = {"#","$","U","D","@","?"}

def gc(l, c):
    if l < 1 or l > len(lines): return " "
    line = lines[l-1]
    if c < 1 or c > len(line): return " "
    return line[c-1]

rooms = []
for ln in range(46, 91):
    line = lines[ln-1]
    for ci, ch in enumerate(line):
        if ch in ROOM_M:
            if ln in (46,47) and (ci+1) >= 31:
                continue
            rooms.append((ln, ci+1, ch))

lookup = {(l, c) for (l, c, _) in rooms}

def trace_v(l, c, step):
    cur = l + step
    saw = False
    while 46 <= cur <= 90:
        ch = gc(cur, c)
        if (cur, c) in lookup:
            return True if saw else False
        if ch == "|":
            saw = True
        elif ch == "-":
            return False
        elif ch in NON_M:
            pass
        elif ch == " ":
            pass
        else:
            return False
        cur += step
    return False

def trace_h(l, c, step):
    cur = c + step
    saw = False
    while 1 <= cur <= 200:
        ch = gc(l, cur)
        if (l, cur) in lookup:
            return True if saw else False
        if ch in ("-", "$"):
            saw = True
        elif ch == "|":
            return False
        elif ch in NON_M:
            pass
        elif ch == " ":
            pass
        else:
            return False
        cur += step
    return False

disc_ids = [
    "silvermere_l46_c25","silvermere_l48_c21","silvermere_l48_c25",
    "silvermere_l56_c32","silvermere_l56_c36","silvermere_l56_c44","silvermere_l56_c84",
    "silvermere_l64_c84",
    "silvermere_l68_c36","silvermere_l68_c40","silvermere_l68_c44",
    "silvermere_l68_c51","silvermere_l68_c55","silvermere_l68_c59","silvermere_l68_c63",
    "silvermere_l68_c71","silvermere_l68_c75","silvermere_l68_c79","silvermere_l68_c83",
    "silvermere_l70_c65",
    "silvermere_l72_c88",
    "silvermere_l74_c37",
    "silvermere_l78_c85","silvermere_l80_c85",
    "silvermere_l84_c45","silvermere_l84_c53","silvermere_l84_c85",
    "silvermere_l86_c53","silvermere_l86_c57","silvermere_l86_c65","silvermere_l86_c69",
    "silvermere_l86_c73","silvermere_l86_c77","silvermere_l86_c85",
    "silvermere_l88_c57","silvermere_l88_c61","silvermere_l88_c65","silvermere_l88_c69",
    "silvermere_l88_c73","silvermere_l88_c81","silvermere_l88_c85",
    "silvermere_l90_c61",
]

def parse_id(id):
    parts = id.split("_")
    return int(parts[1][1:]), int(parts[2][1:])

def count_connects(l, c):
    directions = []
    if trace_v(l, c, -1):
        directions.append("N")
    if trace_v(l, c, 1):
        directions.append("S")
    if trace_h(l, c, 1):
        directions.append("E")
    if trace_h(l, c, -1):
        directions.append("W")
    return directions

print("Offset analysis for disconnected rooms")
print("=" * 80)
for rid in sorted(disc_ids):
    l, c = parse_id(rid)
    sym = gc(l, c)
    cur_dirs = count_connects(l, c)

    offsets_n = []
    offsets_s = []
    for off in range(-3, 4):
        if off == 0:
            continue
        if trace_v(l, c + off, -1):
            offsets_n.append(off)
        if trace_v(l, c + off, 1):
            offsets_s.append(off)

    info = []
    if offsets_n:
        info.append("N_offset=" + str(offsets_n))
    if offsets_s:
        info.append("S_offset=" + str(offsets_s))

    info_str = " ".join(info) if info else "NO_ADJ_CONNECTIONS"
    cur_str = " ".join(cur_dirs) if cur_dirs else "NONE"
    print(f"{rid:<28s} sym={sym:<2s} cur=[{cur_str:<12s}] {info_str}")