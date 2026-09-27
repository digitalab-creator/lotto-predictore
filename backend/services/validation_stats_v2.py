"""Pure stats for the sealed go/no-go test. The unit of chance is one draw."""

from __future__ import annotations

import random
from typing import Sequence

from config import (
    VALIDATION_DEVELOP_FRACTION,
    VALIDATION_FDR_ALPHA,
    VALIDATION_MIN_EXPECTED_HITS,
    VALIDATION_SELECT_FRACTION,
)
from services.exact_coverage import ANY_PRIZE_PROBABILITY
from services.walk_forward_stats import quantile


class HoldoutAlreadyRan(RuntimeError):
    """The sealed slice was scored once. A second look is not a new experiment."""


class ValidationSplitError(ValueError):
    """The history is too short to keep develop, select, and holdout slices."""


def split_bounds(
    n: int,
    *,
    develop: float = VALIDATION_DEVELOP_FRACTION,
    select: float = VALIDATION_SELECT_FRACTION,
) -> tuple[int, int]:
    """Return (select_start, holdout_start) indexes into a date-ordered draw list."""
    if n < 10:
        raise ValidationSplitError(f"Need at least 10 regime draws to split, have {n}")
    select_start = int(n * develop)
    holdout_start = int(n * (develop + select))
    if select_start < 1 or holdout_start <= select_start or holdout_start >= n:
        raise ValidationSplitError(
            f"Empty split for n={n}: select_start={select_start}, holdout_start={holdout_start}"
        )
    return select_start, holdout_start


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def halves_above_baseline(rates: Sequence[float], baseline: float = ANY_PRIZE_PROBABILITY) -> tuple[float, float, bool]:
    """Both chronological halves must beat the fair-ticket rate before a lock is allowed."""
    if len(rates) < 2:
        return 0.0, 0.0, False
    mid = len(rates) // 2
    first = mean(rates[:mid])
    second = mean(rates[mid:])
    return first, second, first > baseline and second > baseline


def cluster_bootstrap_ci(
    draw_rates: Sequence[float],
    *,
    samples: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Point mean and percentile CI. Each resample draws whole draws, never lines."""
    if not draw_rates:
        raise ValueError("Bootstrap needs at least one draw")
    point = mean(draw_rates)
    rng = random.Random(seed)
    n = len(draw_rates)
    means: list[float] = []
    for _ in range(samples):
        total = 0.0
        for _pick in range(n):
            total += draw_rates[rng.randrange(n)]
        means.append(total / n)
    low = quantile(means, alpha / 2)
    high = quantile(means, 1 - alpha / 2)
    return point, low, high


def bootstrap_pvalue_above(
    draw_rates: Sequence[float],
    baseline: float,
    *,
    samples: int,
    seed: int,
) -> float:
    """Share of resampled draw-means that are not above the baseline."""
    if not draw_rates:
        return 1.0
    rng = random.Random(seed)
    n = len(draw_rates)
    at_or_below = 0
    for _ in range(samples):
        total = 0.0
        for _pick in range(n):
            total += draw_rates[rng.randrange(n)]
        if (total / n) <= baseline:
            at_or_below += 1
    return (at_or_below + 1) / (samples + 1)


def paired_signflip_pvalue(
    model_rates: Sequence[float],
    random_rates: Sequence[float],
    *,
    samples: int,
    seed: int,
) -> float:
    """Two-sided sign-flip test of the paired per-draw difference."""
    if len(model_rates) != len(random_rates) or not model_rates:
        return 1.0
    diffs = [m - r for m, r in zip(model_rates, random_rates)]
    observed = abs(sum(diffs))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(samples):
        total = 0.0
        for diff in diffs:
            total += diff if rng.random() < 0.5 else -diff
        if abs(total) >= observed:
            extreme += 1
    return (extreme + 1) / (samples + 1)


def benjamini_hochberg(pvalues: Sequence[float]) -> list[float]:
    """Adjusted p-values. Empty input stays empty."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [1.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        index = order[rank - 1]
        running = min(running, pvalues[index] * m / rank)
        adjusted[index] = running
    return adjusted


def decide_verdict(*, ci_low: float, ci_high: float, point: float, baseline: float) -> str:
    """Pass only when the whole 95% interval sits above the fair-ticket rate."""
    if ci_low > baseline:
        return "pass"
    if point <= baseline or (ci_low <= baseline <= ci_high):
        return "fail"
    return "fail"


def tier_call(
    *,
    expected_hits: float,
    ci_low: float,
    theoretical: float,
    adjusted_p: float | None,
    primary: bool,
) -> str:
    if expected_hits < VALIDATION_MIN_EXPECTED_HITS:
        return "insufficient data"
    if ci_low <= theoretical:
        return "no"
    if primary:
        return "yes"
    if adjusted_p is None or adjusted_p >= VALIDATION_FDR_ALPHA:
        return "no"
    return "yes"
