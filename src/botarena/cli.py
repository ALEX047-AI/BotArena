"""Консольный интерфейс BotArena: один матч и серия сравнений."""

from __future__ import annotations

import argparse
import time

from botarena.arena.generator import ArenaConfig, generate_map
from botarena.bots.strategies import create_strategy
from botarena.core.engine import Game
from botarena.storage.io import write_batch_csv, write_match_json
from botarena.tournament.batch import batch_rows

STRATEGIES = ("random", "greedy", "astar")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BotArena: сравнение стратегий автономных ботов")
    commands = parser.add_subparsers(dest="command", required=True)
    match = commands.add_parser("match", help="Один локальный матч без графики")
    match.add_argument("--a", choices=STRATEGIES, default="greedy", help="Стратегия A")
    match.add_argument("--b", choices=STRATEGIES, default="astar", help="Стратегия B")
    match.add_argument("--seed", type=int, default=42, help="Seed карты")
    match.add_argument("--seed-a", type=int, default=101)
    match.add_argument("--seed-b", type=int, default=202)
    match.add_argument("--density", type=float, default=0.1)
    match.add_argument("--rounds", type=int, default=100)
    match.add_argument("--json", default=None, help="Путь к JSON-протоколу")
    match.add_argument("--view", action="store_true", help="Просматривать матч в терминале")
    match.add_argument("--delay", type=float, default=0.1, help="Задержка между раундами (сек)")

    batch = commands.add_parser("batch", help="Серия сравнений в CSV")
    batch.add_argument("--maps", type=int, default=3, help="Карт на каждую плотность")
    batch.add_argument("--first-seed", type=int, default=1000)
    batch.add_argument("--rounds", type=int, default=100)
    batch.add_argument("--csv", default="results/experiment.csv")
    return parser


def render_ascii(game: Game) -> str:
    """Текстовый снимок игрового поля для демонстрации без Pygame."""
    rows = []
    for y in range(game.arena.height):
        chars = []
        for x in range(game.arena.width):
            point = (x, y)
            if point == game.positions["A"]:
                chars.append("A")
            elif point == game.positions["B"]:
                chars.append("B")
            elif point in game.arena.walls:
                chars.append("#")
            elif point in game.remaining_resources:
                chars.append("*")
            else:
                chars.append(".")
        rows.append(" ".join(chars))
    rows.append(f"Раунд {game.round_index}/{game.max_rounds} | A: {game.scores['A']}  B: {game.scores['B']}")
    rows.append("A/B — боты, # — стена, * — ресурс, . — свободная клетка")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "match":
        arena = generate_map(ArenaConfig(map_seed=args.seed, obstacle_density=args.density))
        game = Game(arena, create_strategy(args.a, args.seed_a),
                    create_strategy(args.b, args.seed_b),
                    max_rounds=args.rounds, strategy_a=args.a, strategy_b=args.b,
                    seed_a=args.seed_a, seed_b=args.seed_b)
        if args.view:
            if args.delay < 0:
                raise ValueError("Задержка не может быть отрицательной")
            print(render_ascii(game))
            while not game.finished:
                game.step_round()
                time.sleep(args.delay)
                print("\x1b[2J\x1b[H" + render_ascii(game), flush=True)
            result = game.result()
        else:
            result = game.run()
        print(f"Карта: {arena.map_id} | Раундов: {result.rounds_played}")
        print(f"A ({args.a}): {result.scores[0]} | B ({args.b}): {result.scores[1]}")
        print("Победитель:", result.winner or "ничья", "| Причина:", result.end_reason)
        if args.json:
            print("Протокол:", write_match_json(result, args.json))
        return 0
    rows = list(batch_rows(maps_per_density=args.maps,
                           first_seed=args.first_seed, max_rounds=args.rounds))
    print(f"Сыграно матчей: {len(rows)}")
    print("CSV:", write_batch_csv(rows, args.csv))
    return 0
