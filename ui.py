"""Pygame window: the map on the left, a small control panel on the right."""
import pygame

CELL, OX, OY, PW = 50, 36, 36, 250
SPEEDS = [2, 4, 8, 16, 32]                      # ticks per second
COLORS = [(230, 120, 50), (120, 100, 220), (30, 160, 130), (210, 80, 130), (60, 130, 200)]


class App:
    def __init__(self, make_engine):
        pygame.init()
        self.make_engine = make_engine
        self.engine = make_engine()
        w = self.engine.world
        self.gw, self.gh = w.cols * CELL, w.rows * CELL
        self.px = OX + self.gw + 24
        self.screen = pygame.display.set_mode((self.px + PW + 16, OY + self.gh + 110))
        pygame.display.set_caption("Robot Coordinator")
        self.fonts = {n: pygame.font.SysFont("helvetica,arial", n) for n in (14, 17, 24)}
        self.speed, self.acc, self.running = 1, 0.0, False
        self.wall_mode, self.pick, self.msg = False, None, "Click a pickup cell, then a delivery cell."
        names = ["Start", "Reset", "Wall mode", "Speed"]
        self.buttons = [(pygame.Rect(self.px + (i % 2) * (PW // 2), 56 + (i // 2) * 38, PW // 2 - 6, 32), n)
                        for i, n in enumerate(names)]

    # ---------- actions ----------
    def reset(self):
        self.engine = self.make_engine()
        self.running, self.pick, self.wall_mode, self.acc = False, None, False, 0
        self.msg = "New random robot positions. Add tasks, then press Start."

    def click_cell(self, cell):
        e = self.engine
        if self.wall_mode:
            if not e.toggle_wall(cell):
                self.msg = "Can't put a wall there."
        elif self.pick is None:                          # 1st click = pickup
            if e.world.free(cell):
                self.pick = cell
        else:                                            # 2nd click = delivery
            task = e.add_task(self.pick, cell)
            self.msg = f"T{task.id}: {task.pickup} -> {task.delivery} queued." if task else e.error
            self.pick = None if task else self.pick

    def press(self, name):
        actions = {"Start": lambda: setattr(self, "running", not self.running), "Reset": self.reset,
                   "Wall mode": lambda: setattr(self, "wall_mode", not self.wall_mode),
                   "Speed": lambda: setattr(self, "speed", (self.speed + 1) % len(SPEEDS))}
        actions[name]()
        self.pick = None

    def handle(self, ev):
        keys = {pygame.K_SPACE: "Start", pygame.K_r: "Reset", pygame.K_w: "Wall mode"}
        if ev.type == pygame.KEYDOWN and ev.key in keys:
            self.press(keys[ev.key])
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.pick = None
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.pick = None
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for rect, name in self.buttons:
                if rect.collidepoint(ev.pos):
                    return self.press(name)
            cell = self.cell_at(ev.pos)
            if cell:
                self.click_cell(cell)

    def cell_at(self, pos):
        r, c, w = (pos[1] - OY) // CELL, (pos[0] - OX) // CELL, self.engine.world
        return (r, c) if 0 <= r < w.rows and 0 <= c < w.cols else None

    # ---------- drawing ----------
    def text(self, s, x, y, size=14, color=(40, 40, 40), center=False):
        img = self.fonts[size].render(s, True, color)
        self.screen.blit(img, img.get_rect(center=(x, y)) if center else (x, y))

    def box(self, cell, shrink=0, color=(0, 0, 0), label=None):
        rect = pygame.Rect(OX + cell[1] * CELL, OY + cell[0] * CELL, CELL, CELL).inflate(-shrink, -shrink)
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        if label:
            self.text(label, *rect.center, color=(255, 255, 255), center=True)

    def draw(self, alpha):
        s, e, w = self.screen, self.engine, self.engine.world
        s.fill((245, 245, 243))
        pygame.draw.rect(s, (228, 228, 224), (OX, OY, self.gw, self.gh))
        for c in range(w.cols):
            self.text(str(c), OX + c * CELL + CELL // 2, OY - 14, center=True)
        for r in range(w.rows):
            self.text(str(r), OX - 14, OY + r * CELL + CELL // 2, center=True)
        for p in w.walls | w.user:
            self.box(p, 0, (80, 80, 78))
        for p in w.furniture:
            self.box(p, 6, (200, 140, 60))
        for r in range(w.rows + 1):                          # coordinate grid
            pygame.draw.line(s, (170, 170, 165), (OX, OY + r * CELL), (OX + self.gw, OY + r * CELL))
        for c in range(w.cols + 1):
            pygame.draw.line(s, (170, 170, 165), (OX + c * CELL, OY), (OX + c * CELL, OY + self.gh))
        for p, name in w.labels.items():
            self.text(name, OX + p[1] * CELL + CELL // 2, OY + p[0] * CELL + CELL // 2, color=(120, 120, 115), center=True)

        waiting = [t for t in e.tasks if t.status == "PENDING"][:20]     # keep the map readable
        for t in waiting + [t for t in e.tasks if t.status in ("ASSIGNED", "PICKED")]:
            big = t.status != "PENDING"
            if t.status != "PICKED":
                self.box(t.pickup, 20 if big else 32, (55, 138, 221), f"T{t.id}" if big else None)
            self.box(t.delivery, 20 if big else 32, (99, 153, 34), f"T{t.id}" if big else None)
        if self.pick:
            pygame.draw.rect(s, (24, 95, 165), (OX + self.pick[1] * CELL, OY + self.pick[0] * CELL, CELL, CELL), 4)

        for r in e.robots:                                    # planned path, then the robot itself
            color = COLORS[(r.id - 1) % len(COLORS)]
            pts = [(OX + (c + .5) * CELL, OY + (rr + .5) * CELL) for rr, c in r.path[r.i:]]
            if r.goal() and len(pts) > 1:
                pygame.draw.lines(s, tuple((v * 2 + 255) // 3 for v in color), False, pts, 3)
            x = OX + (r.prev[1] + (r.pos[1] - r.prev[1]) * alpha + .5) * CELL     # smooth movement
            y = OY + (r.prev[0] + (r.pos[0] - r.prev[0]) * alpha + .5) * CELL
            pygame.draw.circle(s, (255, 255, 255), (x, y), 19)
            pygame.draw.circle(s, color, (x, y), 17)
            self.text(f"R{r.id}", x, y, 17, (255, 255, 255), True)
            if r.status == "TO_DELIVERY":
                pygame.draw.rect(s, (250, 199, 117), (x + 7, y + 7, 10, 10))
            if r.goal() and r.pos != r.goal() and r.next() == r.pos:
                self.text("wait", x, y - 26, 14, (170, 100, 10), True)

        base = OY + self.gh
        if e.stuck():
            hint = "Robots are stuck (a wall blocks them?). Remove it or press Reset."
        elif self.wall_mode:
            hint = "WALL MODE: click a cell to add / remove a wall."
        elif self.pick:
            hint = f"Pickup = {self.pick}. Now click the DELIVERY cell."
        else:
            hint = "Click a PICKUP cell, then a DELIVERY cell. Repeat, then press Start."
        mouse = self.cell_at(pygame.mouse.get_pos())
        self.text(f"cell (row, col): {mouse}" if mouse else "cell (row, col): -", OX, base + 10, 14, (110, 110, 105))
        self.text(hint, OX, base + 32, 17, (24, 95, 165))
        self.text(self.msg, OX, base + 58, 17, (60, 110, 20))
        self.text("Keys: Space start/pause   W wall   R reset   Esc cancel", OX, base + 84, 14, (110, 110, 105))
        self.panel()

    def panel(self):
        s, e = self.screen, self.engine
        self.text("Robot Coordinator", self.px, 16, 24)
        for rect, name in self.buttons:
            label = {"Start": "Pause" if self.running else "Start", "Speed": f"Speed {SPEEDS[self.speed]}/s",
                     "Wall mode": "Wall: ON" if self.wall_mode else "Wall: off"}.get(name, name)
            pygame.draw.rect(s, (255, 240, 205) if label in ("Pause", "Wall: ON") else (255, 255, 255), rect, border_radius=6)
            pygame.draw.rect(s, (150, 150, 145), rect, 1, border_radius=6)
            self.text(label, *rect.center, 17, center=True)
        done = e.count("DONE")
        state = "STUCK" if e.stuck() else "paused" if not self.running else "running" if e.busy() else "all done"
        avg = sum(t.done_at - t.created for t in e.tasks if t.status == "DONE") / done if done else 0
        lines = [f"Tick {e.tick}   [{state}]", f"Done {done}   Running {e.count('ASSIGNED', 'PICKED')}   Queued {e.count('PENDING')}",
                 f"Distance driven: {sum(r.dist for r in e.robots)}", f"Avg task time: {avg:.1f} ticks"]
        y = 140
        for line in lines:
            self.text(line, self.px, y, 17)
            y += 22
        self.text("Robots", self.px, y + 8, 24)
        y += 40
        for r in e.robots:
            pygame.draw.circle(s, COLORS[(r.id - 1) % len(COLORS)], (self.px + 6, y + 8), 6)
            self.text(f"R{r.id}  {r.status.lower()}  {('T%d' % r.task.id) if r.task else '-'}  done {r.done}", self.px + 18, y, 14)
            y += 20
        self.text("Next tasks", self.px, y + 8, 24)
        y += 40
        for t in [t for t in e.tasks if t.status in ("ASSIGNED", "PICKED", "PENDING")][:6]:
            self.text(f"T{t.id} {t.pickup}->{t.delivery}  {t.status.lower()}", self.px, y, 14)
            y += 18

    def run(self):
        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(60) / 1000
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return pygame.quit()
                self.handle(ev)
            interval = 1 / SPEEDS[self.speed]
            if self.running:
                self.acc += dt
                steps = 0
                while self.acc >= interval and steps < 8:
                    if not self.engine.busy():             # nothing to do: the clock stops
                        break
                    self.acc -= interval
                    self.engine.step()
                    steps += 1
                self.acc = min(self.acc, interval)
            self.draw(min(1.0, self.acc / interval) if self.running else 1.0)
            pygame.display.flip()
