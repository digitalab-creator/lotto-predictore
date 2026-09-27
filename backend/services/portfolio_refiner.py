"""Refine algorithm output into an 8-line portfolio (Phase 5)."""

from __future__ import annotations

import itertools
import random
from typing import Any

from config import LINES_PER_DRAW
from services.ticket_validator import (
    TicketValidationError,
    line_identity,
    validate_line,
    validate_portfolio,
)

MAIN_MIN = 1
MAIN_MAX = 37
STRONG_MIN = 1
STRONG_MAX = 7

CROWD_BIRTHDAYS = frozenset(range(1, 32))
CROWD_LOW = frozenset(range(1, 7))


def _subset_key(numbers: list[int], size: int) -> frozenset[int]:
    return frozenset(numbers) if size == 6 else frozenset(itertools.combinations(numbers, size))


def _crowd_labels(numbers: list[int], strong: int) -> list[str]:
    labels: list[str] = []
    ints = [int(n) for n in numbers]
    if all(n in CROWD_BIRTHDAYS for n in ints):
        labels.append("prize_sharing_risk:birthdays_only")
    if all(n in CROWD_LOW for n in ints):
        labels.append("prize_sharing_risk:low_range_1_6")
    if all(n % 5 == 0 for n in ints):
        labels.append("prize_sharing_risk:multiples_pattern")
    if strong in (1, 7):
        labels.append("prize_sharing_risk:popular_strong")
    return labels


def _coverage_score(lines: list[dict]) -> tuple[int, int]:
    mains = set()
    strongs = set()
    for ln in lines:
        mains.update(int(n) for n in ln["numbers"])
        strongs.add(int(ln["strong"]))
    return len(mains), len(strongs)


def _try_replace_line(
    lines: list[dict],
    index: int,
    rng: random.Random,
    *,
    forbidden_4: set[frozenset],
    forbidden_5: set[frozenset],
) -> bool:
    """Replace one line with a random valid line that reduces subset collisions."""
    attempts = 0
    while attempts < 400:
        attempts += 1
        numbers = sorted(rng.sample(range(MAIN_MIN, MAIN_MAX + 1), 6))
        strong = rng.randint(STRONG_MIN, STRONG_MAX)
        ident = line_identity(numbers, strong)
        if any(line_identity(ln["numbers"], ln["strong"]) == ident for j, ln in enumerate(lines) if j != index):
            continue
        f4 = {frozenset(c) for c in itertools.combinations(numbers, 4)}
        f5 = {frozenset(c) for c in itertools.combinations(numbers, 5)}
        if f4 & forbidden_4 or f5 & forbidden_5:
            continue
        lines[index] = {
            "numbers": numbers,
            "strong": strong,
            "labels": _crowd_labels(numbers, strong),
        }
        return True
    return False


def _dedupe_subsets(lines: list[dict], rng: random.Random) -> None:
    """Drop repeated 4- and 5-number subsets across the portfolio."""
    for size in (5, 4):
        seen: dict[frozenset, int] = {}
        for idx, ln in enumerate(lines):
            nums = [int(n) for n in ln["numbers"]]
            for combo in itertools.combinations(nums, size):
                key = frozenset(combo)
                if key in seen:
                    other = seen[key]
                    forbidden_4: set[frozenset] = set()
                    forbidden_5: set[frozenset] = set()
                    for j, other_ln in enumerate(lines):
                        if j == idx:
                            continue
                        on = [int(n) for n in other_ln["numbers"]]
                        forbidden_4.update(frozenset(c) for c in itertools.combinations(on, 4))
                        forbidden_5.update(frozenset(c) for c in itertools.combinations(on, 5))
                    if not _try_replace_line(lines, idx, rng, forbidden_4=forbidden_4, forbidden_5=forbidden_5):
                        _try_replace_line(lines, other, rng, forbidden_4=forbidden_4, forbidden_5=forbidden_5)
                else:
                    seen[key] = idx


def _improve_coverage(lines: list[dict], rng: random.Random) -> None:
    """Swap one number on the weakest-coverage line to cover missing mains / strongs."""
    mains, strongs = _coverage_score(lines)
    missing_main = [n for n in range(MAIN_MIN, MAIN_MAX + 1) if n not in {int(x) for ln in lines for x in ln["numbers"]}]
    missing_strong = [s for s in range(STRONG_MIN, STRONG_MAX + 1) if s not in {int(ln["strong"]) for ln in lines}]
    if not missing_main and len(strongs) >= STRONG_MAX:
        return
    idx = rng.randrange(len(lines))
    ln = lines[idx]
    nums = [int(n) for n in ln["numbers"]]
    if missing_main:
        replace_at = rng.randrange(6)
        candidate = rng.choice(missing_main)
        nums[replace_at] = candidate
        nums = sorted(set(nums))
        while len(nums) < 6:
            extra = rng.randint(MAIN_MIN, MAIN_MAX)
            if extra not in nums:
                nums.append(extra)
        nums = sorted(nums[:6])
    strong = int(ln["strong"])
    if missing_strong:
        strong = rng.choice(missing_strong)
    try:
        validate_line(nums, strong)
        ident = line_identity(nums, strong)
        if any(line_identity(l["numbers"], l["strong"]) == ident for l in lines):
            return
        lines[idx] = {"numbers": nums, "strong": strong, "labels": _crowd_labels(nums, strong)}
    except TicketValidationError:
        return


def refine_portfolio(
    raw_lines: list[dict],
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """
    Take validated algorithm lines and return exactly eight distinct lines with
    subset de-duplication, coverage spread, and crowd-risk labels.
    """
    rng = rng or random.Random()
    lines: list[dict[str, Any]] = []
    for combo in raw_lines:
        numbers = [int(n) for n in combo["numbers"]]
        strong = int(combo.get("strong") or combo.get("strong_number"))
        validate_line(numbers, strong)
        lines.append(
            {
                "numbers": numbers,
                "strong": strong,
                "labels": list(combo.get("labels") or []) + _crowd_labels(numbers, strong),
            }
        )
    if len(lines) != LINES_PER_DRAW:
        raise TicketValidationError(
            f"Portfolio refiner expected {LINES_PER_DRAW} input lines, got {len(lines)}"
        )
    _dedupe_subsets(lines, rng)
    for _ in range(3):
        _improve_coverage(lines, rng)
    validate_portfolio(lines)
    return lines
