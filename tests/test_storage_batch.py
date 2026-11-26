import csv
import json

from botarena.arena.generator import ArenaConfig, generate_map
from botarena.bots.strategies import create_strategy
from botarena.core.engine import Game
from botarena.storage.io import write_batch_csv, write_match_json
from botarena.tournament.batch import batch_rows


def test_match_json_has_full_arena_and_events(tmp_path):
    arena = generate_map(ArenaConfig(map_seed=12))
    result = Game(arena, create_strategy("greedy"), create_strategy("astar"),
                  strategy_a="greedy", strategy_b="astar").run()
    filename = write_match_json(result, tmp_path / "match.json")
    data = json.loads(filename.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["map"]["map_id"] == arena.map_id
    assert len(data["map"]["resources"]) == 10
    assert len(data["events"]) == 2 * result.rounds_played


def test_match_deterministic():
    arena = generate_map(ArenaConfig(map_seed=10, obstacle_density=.2))
    def run():
        game = Game(arena, create_strategy("random", 200), create_strategy("astar", 300),
                    strategy_a="random", strategy_b="astar", seed_a=200, seed_b=300)
        return game.run()
    assert run() == run()


def test_swapped_pairs_use_same_map_and_seeds(tmp_path):
    rows = list(batch_rows(maps_per_density=1, densities=(0.1,), first_seed=9))
    assert len(rows) == 6
    assert len({r["map_id"] for r in rows}) == 1
    assert rows[0]["strategy_a"] == rows[1]["strategy_b"]
    assert rows[0]["strategy_b"] == rows[1]["strategy_a"]
    file = write_batch_csv(rows, tmp_path / "batch.csv")
    with file.open(encoding="utf-8-sig", newline="") as f:
        reread = list(csv.DictReader(f))
    assert len(reread) == 6
    assert reread[0]["map_id"] == reread[1]["map_id"]


def test_render_ascii_contains_bots_and_map():
    from botarena.cli import render_ascii
    arena = generate_map(ArenaConfig(map_seed=2))
    game = Game(arena, create_strategy("random"), create_strategy("astar"))
    board = render_ascii(game)
    assert "A" in board and "B" in board and "#" in board and "*" in board
    assert "Раунд 0/100" in board
