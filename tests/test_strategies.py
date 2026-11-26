from collections import deque

from botarena.bots.pathfinding import astar_path
from botarena.bots.strategies import AStarStrategy, GreedyStrategy, RandomStrategy
from botarena.core.models import Action, Observation, neighbors


def obs(*, position=(0, 0), opponent=(3, 3), walls=(), resources=((2, 0),)):
    return Observation(0, 100, "A", position, opponent, 0, 0, 4, 4,
                       frozenset(walls), frozenset(resources))


def test_random_makes_only_legal_moves():
    bot = RandomStrategy(seed=12)
    observation = obs(walls={(0, 1)}, resources={(3, 2)})
    assert {bot.decide(observation) for _ in range(20)} == {Action.RIGHT}


def test_greedy_direct_step():
    assert GreedyStrategy().decide(obs()) == Action.RIGHT


def test_greedy_stuck_when_no_improving_step():
    observation = obs(position=(0, 0), walls={(1, 0)}, resources={(2, 0)})
    assert GreedyStrategy().decide(observation) == Action.WAIT


def test_astar_avoids_wall():
    observation = obs(position=(0, 0), walls={(1, 0)}, resources={(2, 0)})
    assert AStarStrategy().decide(observation) == Action.DOWN


def test_astar_unreachable():
    observation = obs(position=(0, 0), walls={(1, 0), (0, 1)})
    assert AStarStrategy().decide(observation) == Action.WAIT


def bfs_length(start, goal, blocked, width, height):
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        pos, distance = queue.popleft()
        if pos == goal:
            return distance
        for _, nxt in neighbors(pos, width, height, blocked):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, distance+1))
    return None


def test_astar_matches_bfs_on_small_walls():
    for walls in (frozenset(), frozenset({(1, 0)}), frozenset({(1, 1), (1, 2)})):
        start, goal = (0, 0), (3, 3)
        path = astar_path(start, goal, width=4, height=4, blocked=walls)
        length = bfs_length(start, goal, walls, 4, 4)
        assert (len(path)-1 if path else None) == length


def test_random_is_reproducible():
    o = obs(position=(1, 1))
    x, y = RandomStrategy(100), RandomStrategy(100)
    assert [x.decide(o) for _ in range(20)] == [y.decide(o) for _ in range(20)]
