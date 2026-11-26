"""Три эталонные стратегии; вся логика отделена от графики."""

from __future__ import annotations

from random import Random

from botarena.bots.pathfinding import astar_path, manhattan
from botarena.core.models import Action, MOVE_ORDER, Observation


def _target_action(observation: Observation, target: tuple[int, int]) -> Action:
    for action, position in observation.legal_moves():
        if position == target:
            return action
    return Action.WAIT


class RandomStrategy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = Random(seed)

    def decide(self, observation: Observation) -> Action:
        moves = [action for action, _ in observation.legal_moves()]
        return self.rng.choice(moves) if moves else Action.WAIT


class GreedyStrategy:
    """Ближайшая цель по Манхэттену и только улучшающий шаг."""

    def decide(self, observation: Observation) -> Action:
        if not observation.resources:
            return Action.WAIT
        target = min(observation.resources,
                     key=lambda p: (manhattan(observation.self_position, p), p[1], p[0]))
        current_distance = manhattan(observation.self_position, target)
        moves = observation.legal_moves()
        if not moves:
            return Action.WAIT
        action, next_pos = min(moves, key=lambda item: (
            manhattan(item[1], target), MOVE_ORDER.index(item[0])))
        return action if manhattan(next_pos, target) < current_distance else Action.WAIT


class AStarStrategy:
    def decide(self, observation: Observation) -> Action:
        blocked = observation.walls | {observation.opponent_position}
        available: list[tuple[int, int, int, tuple[tuple[int, int], ...]]] = []
        for target in observation.resources:
            path = astar_path(observation.self_position, target,
                              width=observation.width, height=observation.height,
                              blocked=blocked)
            if path is not None:
                available.append((len(path), target[1], target[0], path))
        if not available:
            return Action.WAIT
        _, _, _, route = min(available)
        return _target_action(observation, route[1]) if len(route) > 1 else Action.WAIT


def create_strategy(name: str, seed: int = 0) -> RandomStrategy | GreedyStrategy | AStarStrategy:
    if name == "random":
        return RandomStrategy(seed)
    if name == "greedy":
        return GreedyStrategy()
    if name == "astar":
        return AStarStrategy()
    raise ValueError(f"Неизвестная стратегия: {name}")
