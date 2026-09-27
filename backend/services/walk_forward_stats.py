"""Pure stats helpers for walk-forward summaries (unit-testable)."""

from __future__ import annotations

import math
import statistics
from typing import Sequence


def make_strategy_id(main_algo: str, strong_algo: str) -> str:
    return f"{main_algo}+{strong_algo}"


def parse_strategy_id(strategy_id: str) -> tuple[str, str]:
    main, strong = strategy_id.rsplit("+", 1)
    return main, strong


def percentile_rank(value: float, sample: Sequence[float]) -> float:
    if not sample:
        return 50.0
    below_or_equal = sum(1 for x in sample if x <= value)
    return 100.0 * below_or_equal / len(sample)


def quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return float(ordered[low])
    weight = pos - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def bootstrap_roi_from_steps(
    step_nets: Sequence[float],
    step_costs: Sequence[float],
    *,
    samples: int,
    rng_seed: int,
) -> list[float]:
    import random

    if not step_nets or not step_costs or len(step_nets) != len(step_costs):
        return []
    rng = random.Random(rng_seed)
    n = len(step_nets)
    rois: list[float] = []
    for _ in range(samples):
        total_net = 0.0
        total_cost = 0.0
        for _ in range(n):
            idx = rng.randrange(n)
            total_net += step_nets[idx]
            total_cost += step_costs[idx]
        rois.append(total_net / total_cost if total_cost else 0.0)
    return rois


def summarize_draw_series(
    step_nets: Sequence[float],
    step_costs: Sequence[float],
    line_payouts: Sequence[float],
    hit_flags_3plus: Sequence[bool],
    strong_hit_flags: Sequence[bool],
) -> dict[str, float]:
    total_net = sum(step_nets)
    total_cost = sum(step_costs)
    roi = total_net / total_cost if total_cost else 0.0

    mean_payout = statistics.mean(line_payouts) if line_payouts else 0.0
    median_payout = statistics.median(line_payouts) if line_payouts else 0.0
    hit_rate = sum(1 for h in hit_flags_3plus if h) / len(hit_flags_3plus) if hit_flags_3plus else 0.0
    strong_acc = sum(1 for h in strong_hit_flags if h) / len(strong_hit_flags) if strong_hit_flags else 0.0

    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for net in step_nets:
        cumulative += net
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)

    variance_net = statistics.pvariance(step_nets) if len(step_nets) > 1 else 0.0

    return {
        "roi": roi,
        "mean_payout_per_line": mean_payout,
        "median_payout_per_line": median_payout,
        "hit_rate_3plus": hit_rate,
        "strong_accuracy": strong_acc,
        "max_drawdown": max_dd,
        "variance_net": variance_net,
        "independent_draw_count": float(len(step_nets)),
    }


def has_predictive_edge(
    independent_draw_count: int,
    random_percentile: float,
    *,
    min_draws: int,
    band_low: float,
    band_high: float,
) -> bool:
    if independent_draw_count < min_draws:
        return False
    if band_low <= random_percentile <= band_high:
        return False
    return random_percentile > band_high
