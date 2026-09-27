"""Unit tests for ticket law (Phase 3)."""

import pytest

from services.ticket_validator import (
    TicketValidationError,
    count_hits,
    line_identity,
    validate_line,
    validate_portfolio,
)


def test_count_hits_uses_set_intersection_no_double_count():
    predicted = [1, 2, 3, 4, 5, 6]
    actual = [1, 1, 2, 3, 10, 11]
    assert count_hits(predicted, actual) == 3


def test_validate_line_rejects_duplicate_main_numbers():
    with pytest.raises(TicketValidationError):
        validate_line([1, 1, 2, 3, 4, 5], 4)


def test_validate_portfolio_requires_eight_distinct_lines():
    lines = [
        {"numbers": [1, 2, 3, 4, 5, 6], "strong": 1},
        {"numbers": [1, 2, 3, 4, 5, 6], "strong": 2},
    ]
    with pytest.raises(TicketValidationError):
        validate_portfolio(lines)

    good = [
        {"numbers": [1, 2, 3, 4, 5, 6], "strong": 1},
        {"numbers": [7, 8, 9, 10, 11, 12], "strong": 2},
        {"numbers": [13, 14, 15, 16, 17, 18], "strong": 3},
        {"numbers": [19, 20, 21, 22, 23, 24], "strong": 4},
        {"numbers": [25, 26, 27, 28, 29, 30], "strong": 5},
        {"numbers": [31, 32, 33, 34, 35, 36], "strong": 6},
        {"numbers": [1, 3, 5, 7, 9, 11], "strong": 7},
        {"numbers": [2, 4, 6, 8, 10, 12], "strong": 1},
    ]
    validate_portfolio(good)
    assert line_identity([6, 5, 4, 3, 2, 1], 4) == ((1, 2, 3, 4, 5, 6), 4)
