"""Distinct uniform tickets. The null model for the go/no-go test."""

from __future__ import annotations

import random
from typing import Any

from services.ticket_validator import line_identity


def distinct_random_portfolio(rng: random.Random, lines: int) -> list[dict[str, Any]]:
    """``lines`` different legal tickets. Each main set and strong is uniform."""
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
