"""One step() = one tick: assign tasks (CSP) -> plan paths (MAPF) -> move robots -> update."""
import csp
from world import Task
from search import best_first
from mapf import Reservations, plan_path

STUCK = 40       # this many ticks with no progress = deadlock, the clock stops


class Engine:
    def __init__(self, world, robots):
        self.world, self.robots, self.tasks = world, robots, []
        self.tick = self.fails = self.no_progress = 0
        self.replan, self.error = False, ""

    def dist(self, a, b):
        path = best_first(self.world, a, b)
        return None if path is None else len(path) - 1

    def add_task(self, pickup, delivery, weight=1):
        """Queue a task. The engine decides later which robot takes it."""
        if not (self.world.free(pickup) and self.world.free(delivery)) or pickup == delivery:
            self.error = "Pickup and delivery must be two different free cells."
        elif weight > max(r.cap for r in self.robots):
            self.error = "Too heavy for every robot."
        elif self.dist(pickup, delivery) is None:
            self.error = "There is no route between those cells."
        else:
            self.error, self.no_progress = "", 0
            self.tasks.append(Task(len(self.tasks) + 1, pickup, delivery, weight, self.tick))
            return self.tasks[-1]

    def toggle_wall(self, p):
        """Add / remove a wall. Robots re-plan on the next tick."""
        busy = {c for t in self.tasks if t.status in ("PENDING", "ASSIGNED", "PICKED")
                for c in (t.pickup, t.delivery)}
        if p in self.world.walls or p in self.world.furniture or p in busy \
                or any(r.pos == p for r in self.robots):
            return False
        self.world.user ^= {p}
        self.replan, self.no_progress = True, 0
        return True

    def count(self, *statuses):
        return sum(t.status in statuses for t in self.tasks)

    def stuck(self):
        return self.no_progress >= STUCK

    def busy(self):
        """False when nothing is happening: the clock stops until you add work."""
        return not self.stuck() and (self.replan or self.count("PENDING") > 0
                                     or any(r.goal() for r in self.robots))

    def step(self):
        self.tick += 1
        before = tuple(t.status for t in self.tasks)
        self.assign()
        if self.replan:
            self.plan()
        moved = self.move()
        self.arrive()
        progress = moved or before != tuple(t.status for t in self.tasks)
        self.no_progress = 0 if progress else self.no_progress + 1

    def assign(self):
        """Waiting tasks (oldest first) go to free robots, cheapest total driving distance."""
        free = [r for r in self.robots if r.status == "IDLE"]
        batch, cost = [], {}
        for t in self.tasks:
            if len(batch) == len(free):
                break
            if t.status != "PENDING":
                continue
            for r in free:
                d = self.dist(r.pos, t.pickup) if r.cap >= t.weight else None
                if d is not None:
                    cost[(t.id, r.id)] = d
            if any((t.id, r.id) in cost for r in free):
                batch.append(t)
            elif all(self.dist(r.pos, t.pickup) is None for r in self.robots):
                t.status = "UNREACHABLE"                  # a wall cut it off
        while batch:
            result = csp.solve(batch, free, cost)
            if result:
                for t in batch:
                    result[t.id].take(t)
                self.replan = True
                return
            batch = batch[:-1]                            # cannot fit all: drop newest, retry

    def plan(self):
        """Busy robots plan first (priority = id); idle robots step aside if they are in the way."""
        res, busy = Reservations(), [r for r in self.robots if r.goal()]
        k = (self.fails // 3) % len(busy) if busy else 0   # stuck for a while? rotate priority
        failed = False
        for r in busy[k:] + busy[:k] + [r for r in self.robots if not r.goal()]:
            path = plan_path(self.world, r.pos, r.goal(), res, r.id)
            failed |= path is None
            r.path, r.i = path or [r.pos], 0
            res.reserve(r.path, r.id)
        self.replan = failed                              # failed robots wait and retry next tick
        self.fails = self.fails + 1 if failed else 0

    def move(self):
        """Work out every robot's next cell FIRST, validate, then move everybody together."""
        for r in self.robots:
            r.prev = r.pos
        want = {r.id: r.next() for r in self.robots}
        go, changed = dict(want), True
        while changed:
            changed = False
            for a in self.robots:
                for b in self.robots:
                    if go[a.id] != a.pos and b is not a and (
                            (go[b.id] == go[a.id] and b.id < a.id)            # same cell
                            or (go[a.id] == b.pos and go[b.id] in (a.pos, b.pos))):  # swap / blocked
                        go[a.id], changed = a.pos, True
        for r in self.robots:
            if go[r.id] != want[r.id]:
                self.replan = True                        # held back: the plan is stale
            else:
                r.i = min(r.i + 1, len(r.path) - 1)
                r.dist += go[r.id] != r.pos
                r.pos = go[r.id]
        return any(r.pos != r.prev for r in self.robots)

    def arrive(self):
        for r in self.robots:
            if r.goal() != r.pos:
                continue
            if r.status == "TO_PICKUP":
                r.status, r.task.status = "TO_DELIVERY", "PICKED"
            else:                                         # delivered: stay here, free for the next task
                r.task.status, r.task.done_at = "DONE", self.tick
                r.status, r.task, r.done = "IDLE", None, r.done + 1
            self.replan = True
