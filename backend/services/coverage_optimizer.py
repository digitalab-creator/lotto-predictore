"""Find an 8-line pack with a higher exact P(any prize) than a random pack.

The search is local. The probability of the pack it keeps is exact.
The number does not depend on past draws, so the result is cached.
"""

from __future__ import annotations

import random
from typing import Any

from services.exact_coverage import exact_portfolio_report, portfolio_metrics, portfolio_p_any
from services.random_portfolio import distinct_random_portfolio
from services.pais_draw_rules import CURRENT_REGIME_START
from services.ticket_validator import line_identity, validate_portfolio

_NEIGHBOR_ATTEMPTS = 40
_BASELINE_SAMPLES = 32
_BASELINE_SEED = 91
_TIER_ABS_FLOOR = 0.001
_TIER_REL_FLOOR = 0.99


def _random_baseline_metrics(rng: random.Random, lines: int = 8) -> dict[str, float]:
    sums = {"p_any_prize": 0.0, "p_4_plus": 0.0, "p_5_plus": 0.0, "p_6_plus": 0.0}
    for _ in range(_BASELINE_SAMPLES):
        pack = distinct_random_portfolio(rng, lines)
        metrics = portfolio_metrics(pack)
        for key in sums:
            sums[key] += metrics[key]
    return {key: value / _BASELINE_SAMPLES for key, value in sums.items()}


def _tier_guard_ok(trial: dict[str, float], baseline: dict[str, float]) -> bool:
    for key in ("p_4_plus", "p_5_plus", "p_6_plus"):
        base = baseline[key]
        min_allowed = max(base - _TIER_ABS_FLOOR, base * _TIER_REL_FLOOR)
        if trial[key] < min_allowed:
            return False
    return True


def spread_seed_lines() -> list[dict[str, Any]]:
    """Eight distinct lines spread across 1–37. A starting wheel, not a claim of best."""
    lines: list[dict[str, Any]] = []
    seen: set[tuple[tuple[int, ...], int]] = set()
    for index in range(8):
        numbers = sorted(((index * 5 + step * 7) % 37) + 1 for step in range(6))
        strong = (index % 7) + 1
        ident = line_identity(numbers, strong)
        if ident in seen:
            strong = ((index + 3) % 7) + 1
            ident = line_identity(numbers, strong)
        seen.add(ident)
        lines.append({"numbers": numbers, "strong": strong})
    validate_portfolio(lines)
    return lines


def _mutate(lines: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]] | None:
    """Swap one main number on one line. Return None when the swap is not a new legal pack."""
    trial = [{"numbers": list(line["numbers"]), "strong": int(line["strong"])} for line in lines]
    index = rng.randrange(len(trial))
    current = set(trial[index]["numbers"])
    missing = [n for n in range(1, 38) if n not in current]
    if not missing:
        return None
    drop = rng.choice(trial[index]["numbers"])
    trial[index]["numbers"] = sorted((current - {drop}) | {rng.choice(missing)})
    try:
        validate_portfolio(trial)
    except ValueError:
        return None
    return trial


def optimize_coverage(
    *,
    iterations: int = 20,
    neighbors: int = 8,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Hill-climb exact P(any prize) without sacrificing P(4+)/P(5+)/P(6+) vs random eight."""
    rng = rng or random.Random(17)
    baseline_rng = random.Random(_BASELINE_SEED)
    tier_baseline = _random_baseline_metrics(baseline_rng)
    lines = spread_seed_lines()
    best_metrics = portfolio_metrics(lines)
    best_p = best_metrics["p_any_prize"]
    for _ in range(iterations):
        improved = False
        for _neighbor in range(neighbors):
            trial = None
            for _attempt in range(_NEIGHBOR_ATTEMPTS):
                trial = _mutate(lines, rng)
                if trial is not None:
                    break
            if trial is None:
                continue
            trial_metrics = portfolio_metrics(trial)
            trial_p = trial_metrics["p_any_prize"]
            if trial_p > best_p and _tier_guard_ok(trial_metrics, tier_baseline):
                lines = trial
                best_metrics = trial_metrics
                best_p = trial_p
                improved = True
                break
        if not improved:
            break
    from services.wheel_report import _mean_random_unique_baseline

    report = exact_portfolio_report(lines)
    report["regime_start"] = CURRENT_REGIME_START.isoformat()
    report["search"] = "local_hill_climb_tier_guarded"
    report["tier_baseline_random_8"] = tier_baseline
    report["baseline_random_unique_8"] = _mean_random_unique_baseline(use_cache=False)
    return {"lines": lines, "p_any_prize": best_p, "report": report}


def load_cached_lines(db: Any) -> list[dict[str, Any]] | None:
    from models.validation_v2 import CoveragePortfolio

    row = (
        db.query(CoveragePortfolio)
        .filter(CoveragePortfolio.regime_start == CURRENT_REGIME_START)
        .order_by(CoveragePortfolio.id.desc())
        .first()
    )
    if row is None:
        return None
    return list(row.lines)


def save_coverage_portfolio(db: Any, packed: dict[str, Any]) -> Any:
    from models.validation_v2 import CoveragePortfolio

    row = CoveragePortfolio(
        regime_start=CURRENT_REGIME_START,
        lines=packed["lines"],
        p_any=packed["p_any_prize"],
        report=packed["report"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
