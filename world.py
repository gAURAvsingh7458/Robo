"""The house map, robots and tasks."""

MAP = [                      # F = furniture, # = wall, . = free floor
    "FFF.#....#..FF",
    "....#....#....",
    "..............",         # rows 2-3 and 7-8 are doors
    "..............",
    "....#.FF.#....",
    "#####.FF.#####",
    "....#....#....",
    "..............",
    "..............",
    "FF..#....#..FF",
]
LABELS = {(2, 1): "Kitchen", (7, 1): "Mom", (1, 6): "Hall", (2, 11): "Dad", (7, 11): "Me"}


class World:
    def __init__(self):
        self.rows, self.cols = len(MAP), len(MAP[0])
        cells = {(r, c): ch for r, row in enumerate(MAP) for c, ch in enumerate(row)}
        self.walls = {p for p, ch in cells.items() if ch == "#"}
        self.furniture = {p for p, ch in cells.items() if ch == "F"}
        self.user = set()                    # walls added while running
        self.labels = LABELS

    def free(self, p):
        return (0 <= p[0] < self.rows and 0 <= p[1] < self.cols and p not in self.walls
                and p not in self.furniture and p not in self.user)

    def neighbors(self, p):
        r, c = p
        return [q for q in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)] if self.free(q)]

    def cells(self):
        return [(r, c) for r in range(self.rows) for c in range(self.cols) if self.free((r, c))]


class Task:
    def __init__(self, tid, pickup, delivery, weight, created):
        self.id, self.pickup, self.delivery, self.weight, self.created = tid, pickup, delivery, weight, created
        self.status = "PENDING"      # PENDING -> ASSIGNED -> PICKED -> DONE  (or UNREACHABLE)
        self.robot, self.done_at = None, None


class Robot:
    def __init__(self, rid, pos, cap):
        self.id, self.pos, self.prev, self.cap = rid, pos, pos, cap
        self.task, self.status = None, "IDLE"          # IDLE, TO_PICKUP, TO_DELIVERY
        self.path, self.i = [pos], 0                   # path[i] = where the robot is i ticks after planning
        self.dist = self.done = 0

    def goal(self):
        if self.status == "TO_PICKUP":
            return self.task.pickup
        if self.status == "TO_DELIVERY":
            return self.task.delivery

    def next(self):
        return self.path[self.i + 1] if self.i + 1 < len(self.path) else self.pos

    def take(self, task):
        self.task, self.status = task, "TO_PICKUP"
        task.status, task.robot = "ASSIGNED", self.id
