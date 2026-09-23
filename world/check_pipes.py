"""Show pipe positions on key connector rows."""
lines = open("/root/newworld/newworld/world/silvermere.txt").readlines()

ROOM_M = {"*","L","S","K","M","N","V","W","Y","F","I"}

for ln in [67, 69, 71, 73, 81, 83, 85, 87, 89]:
    line = lines[ln-1]
    pipes = [(i+1) for i, ch in enumerate(line) if ch == '|']
    rooms = [(i+1, ch) for i, ch in enumerate(line) if ch in ROOM_M]
    print(f"l{ln}: | at cols={pipes}")
    if rooms:
        print(f"l{ln}: rooms={rooms}")
    print()