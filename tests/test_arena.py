import pytest

from botarena.arena.generator import ArenaConfig, generate_map, reachable_cells
from botarena.core.models import ArenaMap, is_inside, neighbors


def test_inside_bounds():
    assert is_inside(0, 0)
    assert is_inside(11, 11)
    assert not is_inside(-1, 5)
    assert not is_inside(12, 0)


def test_invalid_wall_outside():
    with pytest.raises(ValueError, match="вне границ"):
        ArenaMap(12, 12, frozenset({(12, 1)}), frozenset(), ((0, 0), (11, 11)))


def test_duplicate_starts():
    with pytest.raises(ValueError, match="различные"):
        ArenaMap(12, 12, frozenset(), frozenset(), ((0, 0), (0, 0)))


def test_resource_on_wall():
    with pytest.raises(ValueError, match="Ресурс"):
        ArenaMap(12, 12, frozenset({(1, 1)}), frozenset({(1, 1)}), ((0, 0), (11, 11)))


def test_neighbors_block_wall():
    options = neighbors((1, 1), 3, 3, {(1, 0), (0, 1)})
    assert {p for _, p in options} == {(1, 2), (2, 1)}


@pytest.mark.parametrize("density", (0.1, 0.2, 0.3))
def test_generated_map_reachable(density):
    arena = generate_map(ArenaConfig(map_seed=42, obstacle_density=density))
    assert (arena.width, arena.height) == (12, 12)
    assert len(arena.resources) == 10
    reachable = reachable_cells(arena.starts[0], arena.width, arena.height, arena.walls)
    assert arena.starts[1] in reachable
    assert arena.resources <= reachable


def test_generator_seed_reproducible():
    cfg = ArenaConfig(map_seed=123, obstacle_density=.3)
    assert generate_map(cfg) == generate_map(cfg)
    assert generate_map(cfg).map_id == generate_map(cfg).map_id


def test_impossible_configuration():
    with pytest.raises(ValueError, match="нет места"):
        generate_map(ArenaConfig(width=2, height=2, obstacle_density=0.5, resource_count=2))
