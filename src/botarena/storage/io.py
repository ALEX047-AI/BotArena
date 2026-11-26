"""Версионированный JSON-протокол и CSV сводки."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from botarena import __version__
from botarena.core.models import MatchResult, RULES_VERSION, SCHEMA_VERSION


def result_to_dict(result: MatchResult) -> dict:
    arena = result.arena
    def point(p: tuple[int, int]) -> list[int]:
        return [p[0], p[1]]
    return {
        "schema_version": SCHEMA_VERSION,
        "program_version": __version__,
        "rules_version": RULES_VERSION,
        "map": {
            "map_id": arena.map_id,
            "width": arena.width, "height": arena.height,
            "map_seed": arena.map_seed,
            "obstacle_density": arena.obstacle_density,
            "starts": [point(p) for p in arena.starts],
            "walls": [point(p) for p in sorted(arena.walls)],
            "resources": [point(p) for p in sorted(arena.resources)],
        },
        "match": {
            "strategy_a": result.strategy_a,
            "strategy_b": result.strategy_b,
            "seed_a": result.seed_a,
            "seed_b": result.seed_b,
            "max_rounds": result.max_rounds,
            "rounds_played": result.rounds_played,
            "final_positions": [point(p) for p in result.final_positions],
            "scores": {"A": result.scores[0], "B": result.scores[1]},
            "winner": result.winner,
            "end_reason": result.end_reason,
            "invalid_actions": result.invalid_actions,
            "bot_errors": result.bot_errors,
        },
        "events": [
            {
                "round_index": event.round_index,
                "actor": event.actor,
                "requested_action": event.requested_action,
                "applied_action": event.applied_action,
                "before": point(event.before),
                "after": point(event.after),
                "outcome": event.outcome,
                "collected_resource": event.collected_resource,
                "error": event.error,
            } for event in result.events
        ],
    }


def write_match_json(result: MatchResult, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2),
                      encoding="utf-8")
    return target


CSV_FIELDS = (
    "map_seed", "map_id", "obstacle_density", "side_assignment",
    "strategy_a", "strategy_b", "seed_a", "seed_b",
    "score_a", "score_b", "winner", "rounds_played", "end_reason",
    "invalid_actions", "bot_errors", "rules_version", "program_version",
)


def write_batch_csv(rows: Iterable[dict], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target
