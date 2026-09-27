"""Exact eight-line coverage wheel report for production and APIs."""

from __future__ import annotations

import random
from typing import Any

from config import LINES_PER_DRAW
from services.coverage_optimizer import load_cached_lines, optimize_coverage
from services.exact_coverage import (
    ANY_PRIZE_PROBABILITY,
    exact_portfolio_report,
    independent_pack_any_prize,
    one_in,
    portfolio_metrics,
)
from services.pais_draw_rules import CURRENT_REGIME_START
from services.random_portfolio import distinct_random_portfolio

_RANDOM_BASELINE_SAMPLES = 48
_RANDOM_BASELINE_SEED = 42
_cached_baseline: dict[str, Any] | None = None


def _mean_random_unique_baseline(
    *,
    lines: int = LINES_PER_DRAW,
    samples: int = _RANDOM_BASELINE_SAMPLES,
    seed: int = _RANDOM_BASELINE_SEED,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Monte Carlo mean for eight distinct uniform random tickets (not independent duplicates)."""
    global _cached_baseline
    if use_cache and _cached_baseline is not None:
        return dict(_cached_baseline)
    rng = random.Random(seed)
    sums = {
        "p_any_prize": 0.0,
        "p_4_plus": 0.0,
        "p_5_plus": 0.0,
        "p_6_plus": 0.0,
        "expected_winning_lines_per_draw": 0.0,
    }
    for _ in range(samples):
        pack = distinct_random_portfolio(rng, lines)
        report = exact_portfolio_report(pack)
        sums["p_any_prize"] += report["p_any_prize"]
        sums["p_4_plus"] += report["p_4_plus"]
        sums["p_5_plus"] += report["p_5_plus"]
        sums["p_6_plus"] += report["p_6_plus"]
        sums["expected_winning_lines_per_draw"] += report["expected_winning_lines_per_draw"]
    mean = {key: value / samples for key, value in sums.items()}
    mean["method"] = "monte_carlo_distinct_uniform"
    mean["samples"] = samples
    mean["seed"] = seed
    mean["independent_8_p_any"] = independent_pack_any_prize(lines)
    mean["single_ticket_p_any"] = ANY_PRIZE_PROBABILITY
    if use_cache:
        _cached_baseline = dict(mean)
    return mean


def _tier_guard_vs_baseline(
    wheel: dict[str, float],
    baseline: dict[str, float],
    *,
    abs_floor: float = 0.001,
    rel_floor: float = 0.99,
) -> dict[str, Any]:
    """Check the wheel did not sacrifice high tiers for P(any)."""
    checks: dict[str, Any] = {}
    ok = True
    for key in ("p_4_plus", "p_5_plus", "p_6_plus"):
        base = float(baseline[key])
        actual = float(wheel[key])
        min_allowed = max(base - abs_floor, base * rel_floor)
        passed = actual >= min_allowed
        checks[key] = {
            "wheel": actual,
            "baseline_random_8": base,
            "min_allowed": min_allowed,
            "delta": actual - base,
            "ok": passed,
        }
        if not passed:
            ok = False
    return {"ok": ok, "tiers": checks}


def build_wheel_report(db: Any, *, lines: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Exact portfolio math for the live wheel vs random-eight baseline."""
    if lines is None:
        lines = load_cached_lines(db)
    if not lines:
        return {
            "ready": False,
            "regime_start": CURRENT_REGIME_START.isoformat(),
            "note": "No cached wheel. Run scripts/run_validation_v2.py coverage.",
        }

    from models.validation_v2 import CoveragePortfolio

    coverage_row = (
        db.query(CoveragePortfolio)
        .filter(CoveragePortfolio.regime_start == CURRENT_REGIME_START)
        .order_by(CoveragePortfolio.id.desc())
        .first()
    )
    exact = None
    baseline = None
    if coverage_row is not None and isinstance(coverage_row.report, dict):
        exact = coverage_row.report
        stored = coverage_row.report.get("baseline_random_unique_8")
        if isinstance(stored, dict):
            baseline = stored
    if exact is None:
        exact = exact_portfolio_report(lines)
    wheel_metrics = portfolio_metrics(lines)
    if baseline is None:
        tier_base = (exact or {}).get("tier_baseline_random_8")
        if isinstance(tier_base, dict):
            baseline = {
                "p_any_prize": float(tier_base.get("p_any_prize", independent_pack_any_prize(LINES_PER_DRAW))),
                "p_4_plus": float(tier_base["p_4_plus"]),
                "p_5_plus": float(tier_base["p_5_plus"]),
                "p_6_plus": float(tier_base["p_6_plus"]),
                "expected_winning_lines_per_draw": len(lines) * ANY_PRIZE_PROBABILITY,
                "method": "optimizer_tier_baseline",
                "independent_8_p_any": independent_pack_any_prize(LINES_PER_DRAW),
                "single_ticket_p_any": ANY_PRIZE_PROBABILITY,
            }
        else:
            proxy_metrics = portfolio_metrics(
                distinct_random_portfolio(random.Random(_RANDOM_BASELINE_SEED), LINES_PER_DRAW)
            )
            baseline = {
                "p_any_prize": independent_pack_any_prize(LINES_PER_DRAW),
                "p_4_plus": proxy_metrics["p_4_plus"],
                "p_5_plus": proxy_metrics["p_5_plus"],
                "p_6_plus": proxy_metrics["p_6_plus"],
                "expected_winning_lines_per_draw": len(lines) * ANY_PRIZE_PROBABILITY,
                "method": "independent_8_approximation",
                "note": "Re-run scripts/run_validation_v2.py coverage for Monte Carlo baseline.",
                "independent_8_p_any": independent_pack_any_prize(LINES_PER_DRAW),
                "single_ticket_p_any": ANY_PRIZE_PROBABILITY,
            }
    guard = _tier_guard_vs_baseline(wheel_metrics, baseline)

    return {
        "ready": True,
        "production_mode": "coverage_wheel",
        "regime_start": CURRENT_REGIME_START.isoformat(),
        "line_count": len(lines),
        "lines": lines,
        "exact": exact,
        "baseline_random_unique_8": baseline,
        "comparison": {
            "p_any_prize": {
                "wheel": exact["p_any_prize"],
                "random_unique_8_mean": baseline["p_any_prize"],
                "lift_vs_random_unique": exact["p_any_prize"] / baseline["p_any_prize"]
                if baseline["p_any_prize"]
                else None,
                "wheel_one_in": one_in(exact["p_any_prize"]),
                "random_unique_one_in": one_in(baseline["p_any_prize"]),
                "independent_8_same_ticket": independent_pack_any_prize(len(lines)),
            },
            "expected_winning_lines_per_draw": {
                "wheel": exact.get("expected_winning_lines_per_draw", wheel_metrics["p_any_prize"] * len(lines)),
                "random_unique_8_mean": baseline.get(
                    "expected_winning_lines_per_draw", len(lines) * ANY_PRIZE_PROBABILITY
                ),
            },
            "high_tier_guard": guard,
        },
        "disclaimer": (
            "Portfolio coverage changes correlation between lines; it does not make one ticket "
            "more likely to win or create positive expected monetary value."
        ),
    }


def refresh_wheel_with_tier_guard(db: Any, **optimize_kwargs: Any) -> dict[str, Any]:
    """Re-run the local search and persist when tier guard passes."""
    packed = optimize_coverage(**optimize_kwargs)
    report = build_wheel_report(db, lines=packed["lines"])
    if not report.get("ready"):
        return report
    if not report["comparison"]["high_tier_guard"]["ok"]:
        report["stored"] = False
        report["warning"] = "Optimized pack failed high-tier guard; not saved."
        return report
    from services.coverage_optimizer import save_coverage_portfolio

    row = save_coverage_portfolio(db, packed)
    report["stored"] = True
    report["coverage_portfolio_id"] = row.id
    return report
