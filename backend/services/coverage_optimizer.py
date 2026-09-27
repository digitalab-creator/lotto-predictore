"""Find an 8-line pack with a higher exact P(any prize) than a random pack.

The search is local. The probability of the pack it keeps is exact.
The number does not depend on past draws, so the result is cached.
"""

from __future__ import annotations

import random
from typing import Any

from services.exact_coverage import exact_portfolio_report, portfolio_p_any
from services.pais_draw_rules import CURRENT_REGIME_START
from services.ticket_validator import line_identity, validate_portfolio

_NEIGHBOR_ATTEMPTS = 40


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
    """Hill-climb exact P(any prize). Each accepted pack is strictly better."""
    rng = rng or random.Random(17)
    lines = spread_seed_lines()
    best_p = portfolio_p_any(lines)
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
            trial_p = portfolio_p_any(trial)
            if trial_p > best_p:
                lines = trial
                best_p = trial_p
                improved = True
                break
        if not improved:
            break
    report = exact_portfolio_report(lines)
    report["regime_start"] = CURRENT_REGIME_START.isoformat()
    report["search"] = "local_hill_climb"
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
