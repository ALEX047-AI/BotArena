"""Парные сравнения стратегий с перестановкой сторон на одинаковой карте."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from botarena import __version__
from botarena.arena.generator import ArenaConfig, generate_map
from botarena.bots.strategies import create_strategy
from botarena.core.engine import Game
from botarena.core.models import RULES_VERSION

STRATEGY_PAIRS = (("random", "greedy"), ("random", "astar"), ("greedy", "astar"))


def _strategy_seed(name: str, map_seed: int) -> int:
    # Независимый поток, устойчивый к перестановке сторон и хеш-рандомизации Python.
    kind = {"random": 1, "greedy": 2, "astar": 3}[name]
    return map_seed * 1009 + kind * 65537


def batch_rows(*, maps_per_density: int = 3,
               densities: Sequence[float] = (0.1, 0.2, 0.3),
               first_seed: int = 1000, max_rounds: int = 100) -> Iterator[dict]:
    if maps_per_density < 1:
        raise ValueError("Количество карт должно быть положительным")
    for density in densities:
        for index in range(maps_per_density):
            seed = first_seed + index  # Сопоставимые идентификаторы seed между уровнями
            arena = generate_map(ArenaConfig(map_seed=seed, obstacle_density=density))
            for first, second in STRATEGY_PAIRS:
                for side in (0, 1):
                    a, b = ((first, second) if side == 0 else (second, first))
                    seed_a, seed_b = _strategy_seed(a, seed), _strategy_seed(b, seed)
                    game = Game(arena, create_strategy(a, seed_a), create_strategy(b, seed_b),
                                max_rounds=max_rounds, strategy_a=a, strategy_b=b,
                                seed_a=seed_a, seed_b=seed_b)
                    result = game.run()
                    yield {
                        "map_seed": seed,
                        "map_id": arena.map_id,
                        "obstacle_density": density,
                        "side_assignment": f"{first}-{second}:{side}",
                        "strategy_a": a, "strategy_b": b,
                        "seed_a": seed_a, "seed_b": seed_b,
                        "score_a": result.scores[0], "score_b": result.scores[1],
                        "winner": result.winner if result.winner is not None else "DRAW",
                        "rounds_played": result.rounds_played,
                        "end_reason": result.end_reason,
                        "invalid_actions": result.invalid_actions,
                        "bot_errors": result.bot_errors,
                        "rules_version": RULES_VERSION,
                        "program_version": __version__,
                    }
