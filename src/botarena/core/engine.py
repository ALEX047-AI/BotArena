"""Детерминированное выполнение игрового матча без UI-зависимостей."""

from __future__ import annotations

from botarena.core.models import (Action, ArenaMap, BOT_IDS, Controller, GameEvent,
                                  MatchResult, Observation, moved, is_inside)


class Game:
    def __init__(self, arena: ArenaMap, controller_a: Controller, controller_b: Controller,
                 *, max_rounds: int = 100, strategy_a: str = "A",
                 strategy_b: str = "B", seed_a: int | None = None,
                 seed_b: int | None = None) -> None:
        if max_rounds < 1:
            raise ValueError("Число раундов должно быть положительным")
        self.arena = arena
        self.controllers = {"A": controller_a, "B": controller_b}
        self.strategies = (strategy_a, strategy_b)
        self.seeds = (seed_a, seed_b)
        self.max_rounds = max_rounds
        self.positions = {"A": arena.starts[0], "B": arena.starts[1]}
        self.scores = {"A": 0, "B": 0}
        self.remaining_resources = set(arena.resources)
        self.round_index = 0
        self.events: list[GameEvent] = []
        self.finished = len(self.remaining_resources) == 0
        self.end_reason = "ALL_COLLECTED" if self.finished else ""

    def observation(self, bot_id: str) -> Observation:
        if bot_id not in BOT_IDS:
            raise ValueError("Неизвестный бот")
        opponent = "B" if bot_id == "A" else "A"
        return Observation(
            round_index=self.round_index,
            max_rounds=self.max_rounds,
            self_id=bot_id,
            self_position=self.positions[bot_id],
            opponent_position=self.positions[opponent],
            score_a=self.scores["A"], score_b=self.scores["B"],
            width=self.arena.width, height=self.arena.height,
            walls=self.arena.walls,
            resources=frozenset(self.remaining_resources),
        )

    def _turn(self, bot_id: str) -> GameEvent:
        before = self.positions[bot_id]
        opponent = "B" if bot_id == "A" else "A"
        proposed: object = Action.WAIT
        error = None
        try:
            proposed = self.controllers[bot_id].decide(self.observation(bot_id))
        except Exception as exc:
            # На данном этапе только доверенные локальные контроллеры.
            error = f"{type(exc).__name__}: {exc}"
            event = GameEvent(self.round_index, bot_id, "<исключение>",
                              Action.WAIT.value, before, before, "BOT_ERROR", error=error)
            self.events.append(event)
            return event

        raw = proposed.value if isinstance(proposed, Action) else proposed
        requested = str(raw) if isinstance(raw, str) else f"<{type(raw).__name__}>"
        try:
            action = Action(raw) if isinstance(raw, str) else None
        except ValueError:
            action = None
        if action is None:
            outcome = "INVALID_ACTION"
            after = before
            applied = Action.WAIT
        elif action == Action.WAIT:
            outcome = "WAIT"
            after = before
            applied = action
        else:
            target = moved(before, action)
            if (not is_inside(*target, self.arena.width, self.arena.height)
                    or target in self.arena.walls or target == self.positions[opponent]):
                outcome = "INVALID_ACTION"
                after = before
                applied = Action.WAIT
            else:
                outcome = "MOVED"
                after = target
                applied = action
                self.positions[bot_id] = target
        collected = False
        if outcome == "MOVED" and after in self.remaining_resources:
            self.remaining_resources.remove(after)
            self.scores[bot_id] += 1
            collected = True
            outcome = "COLLECTED"
        event = GameEvent(self.round_index, bot_id, requested, applied.value,
                          before, after, outcome, collected, error)
        self.events.append(event)
        return event

    def step_round(self) -> tuple[GameEvent, ...]:
        if self.finished:
            return ()
        order = BOT_IDS if self.round_index % 2 == 0 else tuple(reversed(BOT_IDS))
        round_events = tuple(self._turn(bot_id) for bot_id in order)
        self.round_index += 1
        if not self.remaining_resources:
            self.finished = True
            self.end_reason = "ALL_COLLECTED"
        elif self.round_index >= self.max_rounds:
            self.finished = True
            self.end_reason = "ROUND_LIMIT"
        return round_events

    def run(self) -> MatchResult:
        while not self.finished:
            self.step_round()
        return self.result()

    def result(self) -> MatchResult:
        if not self.finished:
            raise RuntimeError("Матч ещё не закончен")
        score_a, score_b = self.scores["A"], self.scores["B"]
        winner = ("A" if score_a > score_b else "B" if score_b > score_a else None)
        return MatchResult(
            arena=self.arena, strategy_a=self.strategies[0], strategy_b=self.strategies[1],
            seed_a=self.seeds[0], seed_b=self.seeds[1],
            max_rounds=self.max_rounds, rounds_played=self.round_index,
            scores=(score_a, score_b),
            final_positions=(self.positions["A"], self.positions["B"]),
            winner=winner, end_reason=self.end_reason, events=tuple(self.events))
