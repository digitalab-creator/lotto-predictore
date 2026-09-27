"""Decision table for the sealed holdout. One primary cell, eight descriptive tiers."""

from __future__ import annotations

from typing import Any, Sequence

from config import VALIDATION_BOOTSTRAP_SAMPLES, VALIDATION_MIN_EXPECTED_HITS, VALIDATION_PRIMARY_METRIC
from services.exact_coverage import (
    ANY_PRIZE_PROBABILITY,
    TIER_HITS,
    TIER_ORDER,
    main_hit_ways,
    one_in,
    tier_probability,
)
from services.exact_coverage import MAIN_SPACE
from services.pais_draw_rules import STRONG_MAX
from services.validation_stats_v2 import (
    bootstrap_pvalue_above,
    cluster_bootstrap_ci,
    decide_verdict,
    mean,
    paired_signflip_pvalue,
    benjamini_hochberg,
    tier_call,
)
from services.validation_walk import DrawStep


def _row(
    *,
    prize: str,
    theoretical: float,
    draw_rates: Sequence[float],
    expected_hits: float,
    samples: int,
    seed: int,
    adjusted_p: float | None,
    primary: bool,
) -> dict[str, Any]:
    point, low, high = cluster_bootstrap_ci(draw_rates, samples=samples, seed=seed)
    return {
        "prize": prize,
        "theoretical_rate": theoretical,
        "theoretical_one_in": one_in(theoretical),
        "app_oos_rate": point,
        "app_oos_one_in": one_in(point),
        "lift": (point / theoretical) if theoretical else None,
        "ci95": [low, high],
        "expected_hits_if_fair": expected_hits,
        "call": tier_call(
            expected_hits=expected_hits,
            ci_low=low,
            theoretical=theoretical,
            adjusted_p=adjusted_p,
            primary=primary,
        ),
    }


def expected_ticket_payout(draw: Any) -> float | None:
    """Shekels a fair ticket expects on this draw's published prize table."""
    from services.draw_prize import draw_has_prize_data

    if not draw_has_prize_data(draw):
        return None
    total = 0.0
    for hits in range(3, 7):
        p_main = main_hit_ways(hits) / MAIN_SPACE
        plus = float(getattr(draw, f"prize_{hits}_strong") or 0)
        plain = float(getattr(draw, f"prize_{hits}") or 0)
        total += p_main * ((1 / STRONG_MAX) * plus + ((STRONG_MAX - 1) / STRONG_MAX) * plain)
    return total


def build_holdout_report(
    steps: Sequence[DrawStep],
    *,
    strategy_id: str,
    samples: int = VALIDATION_BOOTSTRAP_SAMPLES,
) -> dict[str, Any]:
    if not steps:
        raise ValueError("Holdout report needs scored draws")
    line_count = steps[0].line_count
    n_draws = len(steps)
    n_tickets = n_draws * line_count
    any_rates = [step.ticket_rate for step in steps]
    point, low, high = cluster_bootstrap_ci(any_rates, samples=samples, seed=1)
    random_rates = [step.random_ticket_rate for step in steps if step.random_ticket_rate is not None]
    paired_p = None
    if len(random_rates) == len(steps):
        paired_p = paired_signflip_pvalue(
            any_rates,
            [step.random_ticket_rate for step in steps],
            samples=samples,
            seed=2,
        )
    verdict = decide_verdict(ci_low=low, ci_high=high, point=point, baseline=ANY_PRIZE_PROBABILITY)

    tier_stats = []
    pvalues = []
    eligible_indexes = []
    for name in TIER_ORDER:
        hits_k, strong_hit = TIER_HITS[name]
        theoretical = tier_probability(hits_k, strong_hit)
        rates = [step.tier_counts[name] / step.line_count for step in steps]
        expected = n_tickets * theoretical
        pvalue = bootstrap_pvalue_above(rates, theoretical, samples=samples, seed=3 + hits_k)
        tier_stats.append((name, theoretical, rates, expected, pvalue))
        if expected >= VALIDATION_MIN_EXPECTED_HITS:
            eligible_indexes.append(len(tier_stats) - 1)
            pvalues.append(pvalue)
    adjusted = benjamini_hochberg(pvalues)
    adjusted_by_index = {index: adjusted[pos] for pos, index in enumerate(eligible_indexes)}

    rows = []
    for index, (name, theoretical, rates, expected, _pvalue) in enumerate(tier_stats):
        rows.append(
            _row(
                prize=name,
                theoretical=theoretical,
                draw_rates=rates,
                expected_hits=expected,
                samples=samples,
                seed=10 + index,
                adjusted_p=adjusted_by_index.get(index),
                primary=False,
            )
        )
    any_row = _row(
        prize="any",
        theoretical=ANY_PRIZE_PROBABILITY,
        draw_rates=any_rates,
        expected_hits=n_tickets * ANY_PRIZE_PROBABILITY,
        samples=samples,
        seed=1,
        adjusted_p=None,
        primary=True,
    )
    any_row["call"] = "yes" if verdict == "pass" else "no"
    rows.append(any_row)

    prize_steps = [step for step in steps if step.payout is not None and step.cost]
    roi = None
    if prize_steps:
        payout = sum(step.payout or 0 for step in prize_steps)
        cost = sum(step.cost or 0 for step in prize_steps)
        fair_payout = sum(step.expected_payout or 0.0 for step in prize_steps)
        roi = {
            "draws_with_prize_table": len(prize_steps),
            "draws_missing_prize_table": n_draws - len(prize_steps),
            "payout_ils": payout,
            "fair_expected_payout_ils": fair_payout,
            "cost_ils": cost,
            "roi": (payout - cost) / cost if cost else None,
            "fair_roi": (fair_payout - cost) / cost if cost else None,
            "label": "secondary",
        }
    return {
        "evidence_valid": True,
        "verdict": verdict,
        "primary_metric": VALIDATION_PRIMARY_METRIC,
        "strategy_id": strategy_id,
        "draws": n_draws,
        "tickets": n_tickets,
        "mean_main_hits": mean([step.mean_main_hits for step in steps]),
        "paired_random_pvalue": paired_p,
        "random_portfolio_mean_rate": mean(random_rates) if random_rates else None,
        "table": rows,
        "roi": roi,
        "note": "Pass means the any-prize interval sits above a fair ticket. It is not a promise of profit.",
    }
