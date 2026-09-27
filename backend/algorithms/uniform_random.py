"""Uniform random portfolios — walk-forward control and no-edge production fallback."""

from __future__ import annotations

import random
from typing import Any, List

from config import LINES_PER_DRAW, NUM_COMBINATIONS_TO_RECOMMEND
from models import Draw
from services.ticket_validator import line_identity

from .base import Algorithm, register_algorithm


def _distinct_random_portfolio(rng: random.Random, lines: int) -> list[dict[str, Any]]:
    seen: set[tuple[tuple[int, ...], int]] = set()
    portfolio: list[dict[str, Any]] = []
    attempts = 0
    max_attempts = lines * 500
    while len(portfolio) < lines and attempts < max_attempts:
        attempts += 1
        numbers = sorted(rng.sample(range(1, 38), 6))
        strong = rng.randint(1, 7)
        ident = line_identity(numbers, strong)
        if ident in seen:
            continue
        seen.add(ident)
        portfolio.append(
            {
                "numbers": numbers,
                "strong": strong,
                "params": {"generator": "uniform_random"},
            }
        )
    if len(portfolio) != lines:
        raise RuntimeError("Could not build a distinct random portfolio")
    return portfolio


@register_algorithm
class UniformRandomAlgorithm(Algorithm):
    version = "uniform_random"
    description = "Eight distinct uniformly random valid lines (walk-forward control)."

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int | None = None,
        num_to_recommend: int | None = None,
        **kwargs: Any,
    ) -> List[dict[str, Any]]:
        lines = num_to_recommend or NUM_COMBINATIONS_TO_RECOMMEND
        rng = kwargs.get("rng") or random
        if not isinstance(rng, random.Random):
            rng = random.Random(kwargs.get("seed", 42))
        return _distinct_random_portfolio(rng, lines)


@register_algorithm
class DiversifiedRandomAlgorithm(UniformRandomAlgorithm):
    """Production pack when the scoreboard shows no predictive edge."""

    version = "diversified_random"
    description = "Diversified random lines when walk-forward shows no edge vs chance."
