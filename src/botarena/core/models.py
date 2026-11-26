"""Сущности BotArena и неизменяемый контракт наблюдения."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol

Position = tuple[int, int]
BOT_IDS = ("A", "B")
RULES_VERSION = "0.1"
SCHEMA_VERSION = 1


class Action(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    WAIT = "WAIT"


# Порядок направлений используется при разрешении равенств.
MOVE_ORDER = (Action.UP, Action.LEFT, Action.DOWN, Action.RIGHT)
DELTAS: dict[Action, Position] = {
    Action.UP: (0, -1),
    Action.LEFT: (-1, 0),
    Action.DOWN: (0, 1),
    Action.RIGHT: (1, 0),
}


def is_inside(x: int, y: int, width: int = 12, height: int = 12) -> bool:
    """Проверяет целочисленные координаты относительно размеров арены."""
    return 0 <= x < width and 0 <= y < height


def moved(position: Position, action: Action) -> Position:
    dx, dy = DELTAS[action]
    return position[0] + dx, position[1] + dy


def neighbors(position: Position, width: int, height: int,
              blocked: frozenset[Position] | set[Position]) -> tuple[tuple[Action, Position], ...]:
    """Доступные соседние клетки в фиксированном порядке."""
    options = []
    for action in MOVE_ORDER:
        target = moved(position, action)
        if is_inside(*target, width, height) and target not in blocked:
            options.append((action, target))
    return tuple(options)


def _sorted_points(points: frozenset[Position] | set[Position]) -> list[list[int]]:
    return [[x, y] for x, y in sorted(points, key=lambda p: (p[1], p[0]))]


@dataclass(frozen=True)
class ArenaMap:
    width: int
    height: int
    walls: frozenset[Position]
    resources: frozenset[Position]
    starts: tuple[Position, Position]
    map_seed: int = 0
    obstacle_density: float = 0.0

    def __post_init__(self) -> None:
        # Не даём вызывающему коду передать изменяемый set.
        object.__setattr__(self, "walls", frozenset(self.walls))
        object.__setattr__(self, "resources", frozenset(self.resources))
        if self.width < 2 or self.height < 2:
            raise ValueError("Минимальный размер арены — 2×2")
        if len(self.starts) != 2 or self.starts[0] == self.starts[1]:
            raise ValueError("Нужны две различные стартовые клетки")
        for name, cells in (("Стены", self.walls), ("Ресурсы", self.resources),
                            ("Старты", self.starts)):
            if any(not is_inside(*point, self.width, self.height) for point in cells):
                raise ValueError(f"{name}: клетка вне границ")
        if self.walls & self.resources:
            raise ValueError("Ресурс не может находиться в стене")
        if any(start in self.walls or start in self.resources for start in self.starts):
            raise ValueError("Стартовая клетка должна быть свободной")

    @property
    def map_id(self) -> str:
        data = {
            "width": self.width,
            "height": self.height,
            "starts": [list(p) for p in self.starts],
            "walls": _sorted_points(self.walls),
            "resources": _sorted_points(self.resources),
        }
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Observation:
    """Снимок состояния. Контроллер не получает ссылку на изменяемый Game."""
    round_index: int
    max_rounds: int
    self_id: str
    self_position: Position
    opponent_position: Position
    score_a: int
    score_b: int
    width: int
    height: int
    walls: frozenset[Position]
    resources: frozenset[Position]

    @property
    def scores(self) -> dict[str, int]:
        """Возвращает отдельный словарь, не связанный с состоянием матча."""
        return {"A": self.score_a, "B": self.score_b}

    def legal_moves(self) -> tuple[tuple[Action, Position], ...]:
        blocked = self.walls | {self.opponent_position}
        return neighbors(self.self_position, self.width, self.height, blocked)


class Controller(Protocol):
    def decide(self, observation: Observation) -> Action | str: ...


@dataclass(frozen=True)
class GameEvent:
    round_index: int
    actor: str
    requested_action: str
    applied_action: str
    before: Position
    after: Position
    outcome: str
    collected_resource: bool = False
    error: str | None = None


@dataclass(frozen=True)
class MatchResult:
    arena: ArenaMap
    strategy_a: str
    strategy_b: str
    seed_a: int | None
    seed_b: int | None
    max_rounds: int
    rounds_played: int
    scores: tuple[int, int]
    final_positions: tuple[Position, Position]
    winner: str | None
    end_reason: str
    events: tuple[GameEvent, ...]

    @property
    def invalid_actions(self) -> int:
        return sum(e.outcome == "INVALID_ACTION" for e in self.events)

    @property
    def bot_errors(self) -> int:
        return sum(e.outcome == "BOT_ERROR" for e in self.events)
