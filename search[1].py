"""Single-robot path finding. Dijkstra, Greedy and A* are the SAME loop;
only the priority f differs. BFS uses a plain queue."""
import heapq
from collections import deque


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_from(parent, goal):
    path = []
    while goal is not None:
        path.append(goal)
        goal = parent[goal]
    return path[::-1]


def bfs(world, start, goal):
    """Level by level. Shortest when every step costs the same."""
    parent, queue = {start: None}, deque([start])
    while queue:
        p = queue.popleft()
        if p == goal:
            return path_from(parent, goal)
        for n in world.neighbors(p):
            if n not in parent:
                parent[n] = p
                queue.append(n)


def best_first(world, start, goal, mode="astar"):
    """mode 'dijkstra': f = g   |   'greedy': f = h   |   'astar': f = g + h
    g = steps so far, h = Manhattan distance to the goal. Returns a path or None."""
    g, parent, heap = {start: 0}, {start: None}, [(0, start)]
    while heap:
        _, p = heapq.heappop(heap)
        if p == goal:
            return path_from(parent, goal)
        for n in world.neighbors(p):
            if g[p] + 1 < g.get(n, 1e9):
                g[n], parent[n] = g[p] + 1, p
                h = manhattan(n, goal)
                heapq.heappush(heap, ({"dijkstra": g[n], "greedy": h, "astar": g[n] + h}[mode], n))
