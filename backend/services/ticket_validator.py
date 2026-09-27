"""Single ticket law for Lotto lines — validation, identity, and hit counting."""

from __future__ import annotations

from typing import Iterable, Sequence

from config import LINES_PER_DRAW

MAIN_NUMBER_MIN = 1
MAIN_NUMBER_MAX = 37
STRONG_NUMBER_MIN = 1
STRONG_NUMBER_MAX = 7


class TicketValidationError(ValueError):
    """Raised when a line or portfolio violates Lotto ticket rules."""


def line_identity(numbers: Sequence[int], strong: int) -> tuple[tuple[int, ...], int]:
    """Canonical identity: sorted main numbers plus strong."""
    return (tuple(sorted(int(n) for n in numbers)), int(strong))


def validate_line(numbers: Sequence[int], strong: int) -> None:
    if strong is None:
        raise TicketValidationError("Strong number is required")
    if not (STRONG_NUMBER_MIN <= int(strong) <= STRONG_NUMBER_MAX):
        raise TicketValidationError(
            f"Strong number must be {STRONG_NUMBER_MIN}..{STRONG_NUMBER_MAX}, got {strong}"
        )
    if numbers is None or len(numbers) != 6:
        raise TicketValidationError(f"Line must have exactly 6 main numbers, got {len(numbers or [])}")
    ints = [int(n) for n in numbers]
    if len(set(ints)) != 6:
        raise TicketValidationError(f"Main numbers must be unique, got {numbers}")
    for n in ints:
        if not (MAIN_NUMBER_MIN <= n <= MAIN_NUMBER_MAX):
            raise TicketValidationError(
                f"Main numbers must be {MAIN_NUMBER_MIN}..{MAIN_NUMBER_MAX}, got {n}"
            )


def count_hits(predicted_numbers: Sequence[int], actual_numbers: Sequence[int]) -> int:
    """Set intersection — a duplicated pick cannot count twice."""
    return len(set(predicted_numbers) & set(actual_numbers))


def validate_portfolio(lines: Iterable[dict], *, expected_lines: int = LINES_PER_DRAW) -> None:
    """Require ``expected_lines`` distinct valid lines."""
    seen: set[tuple[tuple[int, ...], int]] = set()
    count = 0
    for line in lines:
        numbers = line.get("numbers")
        strong = line.get("strong")
        if strong is None:
            strong = line.get("strong_number")
        validate_line(numbers, strong)
        ident = line_identity(numbers, strong)
        if ident in seen:
            raise TicketValidationError(f"Duplicate line in portfolio: {ident}")
        seen.add(ident)
        count += 1
    if count != expected_lines:
        raise TicketValidationError(
            f"Portfolio must contain exactly {expected_lines} lines, got {count}"
        )


def normalize_portfolio_lines(
    raw_combos: list[dict],
    default_strong: int,
) -> list[dict]:
    """Build validated line dicts with ``numbers`` and ``strong`` keys."""
    lines: list[dict] = []
    for combo in raw_combos:
        strong = combo.get("strong", default_strong)
        lines.append({"numbers": list(combo["numbers"]), "strong": int(strong)})
    validate_portfolio(lines)
    return lines
