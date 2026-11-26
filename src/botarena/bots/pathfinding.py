"""A* с эвристикой Манхэттена для клеточной карты."""

from __future__ import annotations

from heapq import heappop, heappush
from itertools import count

from botarena.core.models import Position, neighbors


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_path(start: Position, goal: Position, *, width: int, height: int,
               blocked: frozenset[Position] | set[Position]) -> tuple[Position, ...] | None:
    """Кратчайший путь (включая начало и цель); None при недостижимости."""
    if start in blocked or goal in blocked:
        return None
    if not (0 <= start[0] < width and 0 <= start[1] < height):
        return None
    if not (0 <= goal[0] < width and 0 <= goal[1] < height):
        return None
    tie = count()
    heap: list[tuple[int, int, int, Position]] = []
    heappush(heap, (manhattan(start, goal), 0, next(tie), start))
    g_score = {start: 0}
    parents: dict[Position, Position] = {}
    while heap:
        _, cost, _, current = heappop(heap)
        if cost != g_score[current]:
            continue
        if current == goal:
            path = [current]
            while current in parents:
                current = parents[current]
                path.append(current)
            return tuple(reversed(path))
        for _, nxt in neighbors(current, width, height, blocked):
            new_cost = cost + 1
            if new_cost < g_score.get(nxt, float("inf")):
                g_score[nxt] = new_cost
                parents[nxt] = current
                heappush(heap, (new_cost + manhattan(nxt, goal), new_cost, next(tie), nxt))
    return None
