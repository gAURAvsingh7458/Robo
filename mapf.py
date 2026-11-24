"""Many robots, no collisions: reservation table + time-aware A*.
A state is (cell, time). A robot may also WAIT in its cell."""
import heapq
from search import manhattan

HORIZON = 100


class Reservations:
    def __init__(self):
        self.cells = {}      # (cell, t)        -> robot id
        self.moves = {}      # (from, to, t)    -> robot id

    def reserve(self, path, rid):
        for t, p in enumerate(path):
            self.cells[(p, t)] = rid
        for t in range(len(path) - 1):
            self.moves[(path[t], path[t + 1], t)] = rid
        for t in range(len(path), HORIZON + 1):          # the robot stays parked at the end
            self.cells[(path[-1], t)] = rid

    def last(self, p, rid):
        """Last time another robot needs cell p (-1 if never)."""
        return max([t for (q, t), o in self.cells.items() if q == p and o != rid], default=-1)


def plan_path(world, start, goal, res, rid):
    """Shortest path in time that avoids the reservations (None if impossible).
    goal=None: find the nearest cell where the robot can stand still for good (idle robots)."""
    last = res.last(goal, rid) if goal else None
    h = (lambda p: manhattan(p, goal)) if goal else (lambda p: 0)
    heap, parent = [(h(start), 0, start)], {(start, 0): None}
    while heap:
        _, t, p = heapq.heappop(heap)
        if (p == goal and t > last) if goal else res.last(p, rid) < t:
            path, s = [], (p, t)
            while s:
                path.append(s[0])
                s = parent[s]
            return path[::-1]
        if t >= HORIZON:
            continue
        for q in world.neighbors(p) + [p]:               # [p] = wait
            s = (q, t + 1)
            if s in parent or res.cells.get(s, rid) != rid:
                continue                                 # cell taken by someone else
            if q != p and res.moves.get((q, p, t), rid) != rid:
                continue                                 # would swap places with someone
            parent[s] = (p, t)
            heapq.heappush(heap, (t + 1 + h(q), t + 1, q))
