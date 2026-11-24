# Robot Coordinator (small version)

    pip3 install pygame
    python3 main.py

Click a pickup cell, then a delivery cell = one task. Repeat as often as you like
then press Start. The engine picks the robot for every task.
Keys: Space start/pause, W wall mode, R reset, Esc cancel.

world.py   map, robots, tasks        search.py  BFS, Dijkstra, Greedy, A*
mapf.py    no-collision planning     csp.py     task -> robot assignment
engine.py  one tick of everything    ui.py      Pygame window      main.py  settings
