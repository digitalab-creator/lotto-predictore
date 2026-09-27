"""Uniform random portfolios — walk-forward control and no-edge production fallback."""

from __future__ import annotations

import random
from typing import Any, List

from config import NUM_COMBINATIONS_TO_RECOMMEND
from models import Draw
from services.random_portfolio import distinct_random_portfolio

from .base import Algorithm, register_algorithm


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
        return distinct_random_portfolio(rng, lines)


@register_algorithm
class DiversifiedRandomAlgorithm(UniformRandomAlgorithm):
    """Kept registered so old scoreboards can name it. It is not a go/no-go candidate."""

    version = "diversified_random"
    description = "Same generator as uniform_random. Not used as proof of an edge."
