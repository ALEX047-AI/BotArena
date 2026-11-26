"""Генератор детерминированных карт с доступными ресурсами."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random

from botarena.core.models import ArenaMap, Position, neighbors


@dataclass(frozen=True)
class ArenaConfig:
    width: int = 12
    height: int = 12
    map_seed: int = 42
    obstacle_density: float = 0.10
    resource_count: int = 10

    def __post_init__(self) -> None:
        if self.width < 2 or self.height < 2:
            raise ValueError("Размеры должны быть не меньше 2")
        if not 0 <= self.obstacle_density < 1:
            raise ValueError("Плотность стен должна быть от 0 (включительно) до 1")
        if self.resource_count < 0:
            raise ValueError("Количество ресурсов не может быть отрицательным")


def reachable_cells(start: Position, width: int, height: int,
                    walls: frozenset[Position]) -> frozenset[Position]:
    """Обход в ширину по свободным клеткам."""
    if start in walls:
        return frozenset()
    seen = {start}
    queue = deque([start])
    while queue:
        position = queue.popleft()
        for _, target in neighbors(position, width, height, walls):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return frozenset(seen)


def generate_map(config: ArenaConfig, max_attempts: int = 5000) -> ArenaMap:
    """Генерирует карту. Одинаковые параметры дают идентичную карту.

    Оба старта должны соединяться, каждый ресурс — быть достижимым из обоих.
    Невыполнимые конфигурации отклоняются явно.
    """
    rng = Random(config.map_seed)
    starts = ((0, 0), (config.width - 1, config.height - 1))
    cells = [(x, y) for y in range(config.height) for x in range(config.width)]
    candidates = [p for p in cells if p not in starts]
    wall_count = round(len(cells) * config.obstacle_density)
    if wall_count + config.resource_count > len(candidates):
        raise ValueError("Для указанного количества стен и ресурсов нет места")
    for _ in range(max_attempts):
        walls = frozenset(rng.sample(candidates, wall_count))
        reachable = reachable_cells(starts[0], config.width, config.height, walls)
        available = [p for p in cells if p in reachable and p not in starts]
        if starts[1] not in reachable or len(available) < config.resource_count:
            continue
        resources = frozenset(rng.sample(available, config.resource_count))
        return ArenaMap(config.width, config.height, walls, resources, starts,
                        config.map_seed, config.obstacle_density)
    raise ValueError("Не удалось сгенерировать достижимую карту; измените параметры")
