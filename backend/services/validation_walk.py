"""Walk forward one draw at a time. The strategy sees only earlier draws."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from services.draw_prize import calculate_prize, draw_has_prize_data, draw_ticket_cost
from services.exact_coverage import TIER_ORDER, tier_name
from services.ticket_validator import TicketValidationError, count_hits, validate_portfolio
from services.random_portfolio import distinct_random_portfolio


class LeakError(RuntimeError):
    """Training rows included the draw being scored, or a later one."""


ProduceLines = Callable[[list[Any]], list[dict[str, Any]]]


@dataclass
class DrawStep:
    draw_id: int | None
    draw_date: date
    lines: list[dict[str, Any]]
    ticket_wins: int
    line_count: int
    tier_counts: dict[str, int]
    mean_main_hits: float
    payout: float | None
    cost: float | None
    random_ticket_rate: float | None = None
    expected_payout: float | None = None

    @property
    def ticket_rate(self) -> float:
        if self.line_count == 0:
            return 0.0
        return self.ticket_wins / self.line_count


@dataclass
class WalkResult:
    steps: list[DrawStep] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


def assert_train_before(train: list[Any], target: Any) -> None:
    target_date = target.date
    for row in train:
        if row.date >= target_date:
            raise LeakError(
                f"Training draw {row.date.isoformat()} is not strictly before {target_date.isoformat()}"
            )


def score_lines(lines: list[dict[str, Any]], draw: Any) -> DrawStep:
    """Score a frozen pack against one draw. Prize shekels only when Pais stored them."""
    validate_portfolio(lines)
    tier_counts = {name: 0 for name in TIER_ORDER}
    wins = 0
    hit_sum = 0
    has_prize = draw_has_prize_data(draw)
    payout = 0.0
    cost = 0.0
    for line in lines:
        hits = count_hits(line["numbers"], draw.numbers)
        strong_hit = int(line["strong"]) == int(draw.strong_number)
        hit_sum += hits
        name = tier_name(hits, strong_hit)
        if name is not None:
            tier_counts[name] += 1
            wins += 1
        if has_prize:
            prize = calculate_prize(draw, hits, strong_hit)
            if prize is None:
                continue
            payout += float(prize)
            cost += draw_ticket_cost(draw)
    return DrawStep(
        draw_id=getattr(draw, "id", None),
        draw_date=draw.date,
        lines=[{"numbers": list(line["numbers"]), "strong": int(line["strong"])} for line in lines],
        ticket_wins=wins,
        line_count=len(lines),
        tier_counts=tier_counts,
        mean_main_hits=hit_sum / len(lines),
        payout=payout if has_prize and cost else None,
        cost=cost if has_prize and cost else None,
    )


def walk_forward(
    draws: list[Any],
    *,
    start: int,
    end: int,
    produce_lines: ProduceLines,
) -> WalkResult:
    """Score draws[start:end]. ``produce_lines`` receives draws[:i] only."""
    result = WalkResult()
    for index in range(start, end):
        target = draws[index]
        train = draws[:index]
        try:
            assert_train_before(train, target)
            lines = produce_lines(train)
            result.steps.append(score_lines(lines, target))
        except (LeakError, TicketValidationError, ValueError, RuntimeError) as exc:
            result.errors.append({"draw_date": str(target.date), "error": str(exc)})
    return result


def paired_random_rates(
    step: DrawStep,
    draw: Any,
    *,
    portfolios: int,
    rng: random.Random,
) -> float:
    """Mean per-ticket any-prize rate of fresh uniform packs on this same draw."""
    if portfolios < 1:
        raise ValueError("portfolios must be positive")
    actual = list(draw.numbers)
    total_wins = 0
    for _ in range(portfolios):
        pack = distinct_random_portfolio(rng, step.line_count)
        for line in pack:
            if count_hits(line["numbers"], actual) >= 3:
                total_wins += 1
    return total_wins / (portfolios * step.line_count)
