import pytest

from botarena.core.engine import Game
from botarena.core.models import Action, ArenaMap


class Fixed:
    def __init__(self, action):
        self.action = action

    def decide(self, observation):
        return self.action


class Crash:
    def decide(self, observation):
        raise RuntimeError("учебная ошибка")


class Spy:
    def __init__(self):
        self.seen = []

    def decide(self, observation):
        self.seen.append((observation.round_index, observation.self_id,
                          observation.score_a, observation.score_b))
        return Action.WAIT


def arena(walls=(), resources=((1, 0),), starts=((0, 0), (3, 3))):
    return ArenaMap(4, 4, frozenset(walls), frozenset(resources), starts)


def test_collect_once_and_finish():
    game = Game(arena(), Fixed(Action.RIGHT), Fixed(Action.WAIT))
    events = game.step_round()
    assert game.scores == {"A": 1, "B": 0}
    assert game.finished
    assert game.result().winner == "A"
    assert events[0].outcome == "COLLECTED"
    assert sum(e.collected_resource for e in game.events) == 1
    assert game.step_round() == ()


def test_wall_and_oob_invalid():
    for blocked, action in (({(1, 0)}, Action.RIGHT), (set(), Action.LEFT)):
        game = Game(arena(walls=blocked, resources={(2, 2)}), Fixed(action), Fixed(Action.WAIT), max_rounds=1)
        result = game.run()
        assert result.events[0].outcome == "INVALID_ACTION"
        assert result.final_positions[0] == (0, 0)


def test_enemy_cell_invalid():
    game = Game(arena(starts=((0, 0), (1, 0)), resources={(2, 2)}),
                Fixed(Action.RIGHT), Fixed(Action.WAIT), max_rounds=1)
    assert game.run().events[0].outcome == "INVALID_ACTION"


def test_invalid_type_consumes_action():
    game = Game(arena(), Fixed(42), Fixed(Action.WAIT), max_rounds=1)
    result = game.run()
    assert result.invalid_actions == 1
    assert result.rounds_played == 1


def test_bot_error_waits():
    result = Game(arena(), Crash(), Fixed(Action.WAIT), max_rounds=1).run()
    assert result.bot_errors == 1
    assert result.events[0].outcome == "BOT_ERROR"
    assert result.final_positions[0] == (0, 0)


def test_wait_and_round_limit():
    result = Game(arena(), Fixed(Action.WAIT), Fixed(Action.WAIT), max_rounds=3).run()
    assert result.end_reason == "ROUND_LIMIT"
    assert result.rounds_played == 3
    assert len(result.events) == 6
    assert result.winner is None
    assert all(e.outcome == "WAIT" for e in result.events)


def test_round_order_alternates_and_new_observation():
    a, b = Spy(), Spy()
    game = Game(arena(), a, b, max_rounds=2)
    game.run()
    assert [event.actor for event in game.events] == ["A", "B", "B", "A"]
    assert a.seen[0][0] == 0 and a.seen[1][0] == 1


def test_zero_resources_ends_before_round():
    result = Game(arena(resources=()), Fixed(Action.WAIT), Fixed(Action.WAIT)).run()
    assert result.rounds_played == 0
    assert result.end_reason == "ALL_COLLECTED"


def test_strategy_cannot_mutate_resource_snapshot():
    class Malicious:
        def decide(self, obs):
            obs.resources.add((2, 2))
            return Action.UP
    result = Game(arena(), Malicious(), Fixed(Action.WAIT), max_rounds=1).run()
    assert result.bot_errors == 1


def test_resource_collected_only_once_with_reentry():
    class RoundTrip:
        def decide(self, observation):
            return [Action.RIGHT, Action.LEFT, Action.RIGHT][observation.round_index]
    game = Game(arena(resources={(1, 0), (2, 2)}), RoundTrip(), Fixed(Action.WAIT), max_rounds=3)
    result = game.run()
    assert result.scores[0] == 1
    assert sum(event.collected_resource for event in result.events) == 1


def test_default_round_limit_is_100():
    result = Game(arena(), Fixed(Action.WAIT), Fixed(Action.WAIT)).run()
    assert result.rounds_played == 100
    assert result.end_reason == "ROUND_LIMIT"


def test_second_bot_sees_first_bot_new_position():
    class Record:
        observed = None
        def decide(self, observation):
            self.observed = observation.opponent_position
            return Action.WAIT
    b = Record()
    game = Game(arena(resources={(2, 2)}), Fixed(Action.RIGHT), b, max_rounds=1)
    game.run()
    assert b.observed == (1, 0)
