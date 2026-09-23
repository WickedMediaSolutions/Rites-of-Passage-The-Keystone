# Silvermere Cardinal-Exit Connectivity Audit

Date: 2026-09-05
Map source: world/silvermere.txt (lines 46-90)
Parser: world/silvermere_parser.py
Dataset: world/silvermere_data.py

## Summary

| Metric | Value |
|--------|-------|
| Total physical rooms detected | 285 |
| Cardinally reachable from Town Square | 243 |
| Disconnected rooms | 42 |
| Connected componnts (total) | 22 |
| Bidirectional exit pairs | All verified correct |

## Classification Keys

- **A** - Correctly disconneted: special-access room/area
- **B** - Correctly disconnected: upper/lower/special transition area
- **C** - Parser alignment problem: ASCII-art column shift
- **D** - Actual missing cardinal connection in parser logic
- **E** - Map overlay/error represented by ? or #
- **F** - Uncertan; preserve as-is

---

## Component 2 - Northern boundary (3 rooms)

Silvermere Upper / Sheriff Lionheart zone. These rooms sit between the Sheriff
txt (l46-47, stripped by text contamination) and the main street grid that
begins on l50 with the K-chain.

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l46_c25 | 46 | 25 | * | B | Topmost room. Pipe on l47 at c24 (shift -1). Upper Silvermere boundary. |
| silvermere_l48_c21 | 48 | 21 | * | B | l49 pipes at c19,c23 (shift -2 vs rooms c21,c25). K-chain on l50/l51 uses different alignment. |
| silvermere_l48_c25 | 48 | 25 | S | B | Same island pattern. |

Parser note: The -2 shift on l49 is a real ASCII-art artifact but given the
separate upper-area context, connecting these rooms would not be faithful.

Verdict: Preserve as disconnected.

## Component 3 - l56 island (4 rooms)

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l56_c32 | 56 | 32 | * | F | Four-room E/W chain. No N/S pipe alignment. Possible mezzanine/elevated corridor. |
| silvermere_l56_c36 | 56 | 36 | * | F | Ditto. |
| silvermere_l56_c44 | 56 | 44 | * | F | Ditto. |
| silvermere_l56_c84 | 56 | 84 | * | F | Connects south to l64c84 (itself disconnected). |

Verdict: Preserve as disconnected.

## Component 4 - l64 eastern edge (1 room)

silvermere_l64_c84 | 64 | 84 | * | F | Connected north to l56c84. No south room at c85 on l66. Far-eastern hallway fragment.

Verdict: Preserve as disconnected.

## Component 5 - l68 mid-section east (11 rooms, c51-c83)

These rooms occupy the section past the mid-point of line 68, interspersed
with D (down-transition) markers and # barriers.

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l68_c51 | 68 | 51 | * | F | c51-c63 rooms in D-marker zone. l67 pipes at c53,c61; l68 rooms at c51,c55,c59,c63 -- intentionally interspersed. |
| silvermere_l68_c55 | 68 | 55 | S | F | Ditto. |
| silvermere_l68_c59 | 68 | 59 | * | F | Ditto. |
| silvermere_l68_c63 | 68 | 63 | * | F | Ditto. |
| silvermere_l68_c71 | 68 | 71 | * | F | c71-c83 rooms past second D marker and # barriers. |
| silvermere_l68_c75 | 68 | 75 | L | F | Ditto. |
| silvermere_l68_c79 | 68 | 79 | I | A | Insane Mage (legend: I). Special NPC/encounter room. |
| silvermere_l68_c83 | 68 | 83 | * | F | Easternmost on l68. No pipe at c83 on l69. |

Verdict: Preserve as disconnected. The D markers and # annotations confirm this is a special-transition zone.

## Component 6 - l68 mid-section west (3 rooms, c36-c44)

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l68_c36 | 68 | 36 | S | C | Pipes at l67c33/l69c33 (offset -3) connect to l66c33/l70c33 (both reachable). Offset too large for tolerance fix. |
| silvermere_l68_c40 | 68 | 40 | S | C | South pipe at l69c37 (offset -3) connects to l70c37 (reachable). Same -3 issue. |
| silvermere_l68_c44 | 68 | 44 | L | C | CLEAREST PARSER-ALIGNMENT CASE. l67c45=| and l69c45=| (offset +1). Connects north to l66c45 and south to l70c45, both reachable street-grid rooms. A +/-1 column tolerance would fix this room. |

Recommendation for l68c44: Apply +/-1 column tolerance in find_vertical_connection.
This room is in the same street grid as c45 rooms; the ASCII artist drew pipes
at c45 but placed the room marker at c44. HIGH-CONFIDENCE FIX.

Recommendation for l68c36/c40: The -3 offset is too large. Preserve as disconnected.

## Component 7 - l70 special (1 room)

silvermere_l70_c65 | 70 | 65 | Y | A | Practice Dummy And Up (legend: Y). Surrounded by U, #, L annotations. Correctly disconnected.

## Component 8 - l72 eastern edge (1 room)

silvermere_l72_c88 | 72 | 88 | L | F | Last room on Town Square row, past # barrier at c86. Right-edge fragment. Preserve.

## Component 9 - Bank Vault (1 room)

silvermere_l74_c37 | 74 | 37 | V | A | Bank Vaut (legend: V). Adjacent to # barriers. Restricted-access. Correctly disconnected.

## Component 10 - Far-east edge fragment (2 rooms)

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l78_c85 | 78 | 85 | * | F | Connects south to l80c85. Isolated 2-room vertical stack. |
n| silvermere_l80_c85 | 80 | 85 | * | F | Connects north to l78c85. Pip at l81c85 but no room at l82c85. Edge fragmet. |

Verdict: Preseve as disconnected.

## Component 11 - Southern cluster (18 rooms, lines 84-90)

This is the largest disconnected component: 18 rooms that form a coherent
sub-grid but are cut off from the main component at l83.

### Column-shift analysis

The connector-pipe rows in this section exhibit progressive column drift:

Row  | Pipe columns
-----+----------------------------------------------
l81  | 45   61   65   69   73   77   85   (correct)
l83  | 43   51   59   63   67   71   75   (-2 shift)
l85  | 44   52   64   68   72   76   84   (-1 vs rooms)
l87  | 45   57   65   69   73   85       (back to correct)

Rooms on l84 and l86 are at the STANDARD columns (c45,c53,c61,c65,c69,c73,
c77,c85). The disconnection is caused by l83 pipes drawn at -2 offset and
l85 pipes at -1 offset.

### Room listing

| Room ID | Ln | Col | Sym | Cat | Reason |
|---------|----|-----|-----|-----|--------|
| silvermere_l84_c45 | 84 | 45 | * | C | l83 pipe at c44 (-1). No connection upward. |
| silvermere_l84_c53 | 84 | 53 | * | C | l83 pipe at c51 (-2). No connection upward. |
| silvermere_l84_c85 | 84 | 85 | * | F | Right-edge room. No pipe match upward. |
| silvermere_l86_c53 | 86 | 53 | * | C | l85 pipe at c52 (-1). Connected south. |
| silvermere_l86_c57 | 86 | 57 | * | C | Connected south to l88c57. |
| silvermere_l86_c65 | 86 | 65 | L | C | l85 pipe at c64 (-1). Connected south. |
| silvermere_l86_c69 | 86 | 69 | * | C | l85 pipe at c68 (-1). Connected south. |
| silvermere_l86_c73 | 86 | 73 | L | C | l85 pipe at c72 (-1). Connected south. |
| silvermere_l86_c77 | 86 | 77 | * | C | l85 pipe at c76 (-1). No south room. |
| silvermere_l86_c85 | 86 | 85 | * | F | Right-edge. |
| silvermere_l88_c57 | 88 | 57 | * | C | Connected north to l86c57. |
| silvermere_l88_c61 | 88 | 61 | * | C | Connected south to l90c61. |
| silvermere_l88_c65 | 88 | 65 | L | C | Connected north to l86c65. |
| silvermere_l88_c69 | 88 | 69 | L | C | Connected north to l86c69. |
| silvermere_l88_c73 | 88 | 73 | * | C | Connected north to l86c73. |
| silvermere_l88_c81 | 88 | 81 | L | F | Connected east to l88c85. |
| silvermere_l88_c85 | 88 | 85 | * | F | Right-edge. |
| silvermere_l90_c61 | 90 | 61 | M | C | Manhole (legend: M). Connected north via l89c61=| to l88c61. Standard street room with special transition. Should be reachable. |

### Recommendation

Category C - Parser Alignment. These rooms are physically part of the same
Silvermere street grid. A +/-1 tolerance would fix l85 connections (allowing
l84<->l86 internal links) but NOT the l83 connections (-2 shift). The southern
cluster would remain internally consistent but still isolated from the main grid.

Do NOT apply a +/-2 tolerance globally. A targeted per-row mapping for l83
may be needed in future work.

## Parser Column-Shift Evidence

### Evidence FOR +/-1 tolerance

1. l68c44: pipes at l67c45/l69c45 (+1 offset). Room at c44 in same grid as c45 rooms. HIGH CONFIDENCE.
2. l85 connectors: Consistent -1 shift between l85 pipes and l84/l86 rooms at c45,c53,c65,c69,c73,c77,c85. HIGH CONFIDENCE.
3. l78c85: N_offset[-1] pipe at l77c84. MODERATE CONFIDENCE.

### Evidence AGAINST +/-1 tolerance

1. l83 shift: -2 offset, not fixed by +/-1 tolerance.
2. l68c36/c40: -3 offset, far too large.
3. l68 c51-c63: Pipes intentionally interspersed between rooms (D-marker zone).
o
### Verdict

A limited +/-1 column tolerance in the vertical pipe-detection fallback is
warranted for specific cases but will NOT connect the souther cluster to the
main grid.

## Proposed Parser Correction

In find_vertical_connection, after the existing same-column trace fails:

1. Try +/-1 column offset.
2. Only succeed if:
   - The offset column has a | at the adjacent row.
n   - A room exists at the offset column on the target row.
   - The connection is bidirectional (reverse trace also succeeds).
o
### Expected impact (estimated)

| Before | After |
o|--------|-------|
o| 243 reachable | ~250-255 reachable |
o| 42 disconnected | ~30-35 disconnected |
o| l68c44 connected | Yes |
o| Southern cluster internaly consistent | Yes |
o| Southern cluster joins main grid | No (-2 shift on l83) |
o
## Rooms That Should Remain Disconnected
o
| Room | Reason |
o|------|--------|
o| l46c25,l48c21,l48c25 | Upper Silvermere / Sheriff zone |
o| l68c79 (I) | Insane Mage -- special NPC |
o| l70c65 (Y) | Practice Dummy / Up -- speial |
o| l74c37 (V) | Bank Vault -- restricted |
o| l56c32-c44 | Uncertan -- possible mezzanine |
o| l68c51-c83 | D-marker zone / special transition |
o| l90c61 (M) | Manole -- special (but should be reachable) |

## Final Recommendations

1. Apply +/-1 column tolerance to find_vertical_connection with the guardrails described above.
2. Do NOT apply +/-2 tolerance unless a per-row mapping for l83 is created.
3. Revisit the southern cluster after the +/-1 fix. If the southern rooms remain isolated from the main grid, a future per-row alignment table may be needed.
4. Preserve all Category A and B rooms exactly as they are.
5. Do NOT modify the Evennia database.
6. Rerun python -m world.silvermere_paths after any change and verfy bidirectionality.
7. Do NOT run APPLY=True.
