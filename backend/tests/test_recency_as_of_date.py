"""Recency algorithms require as_of_date (Phase 3)."""

from datetime import date

import pytest

from algorithms.recency_weighted import RecencyWeightedFrequencyAlgorithm
from algorithms.strong_number.recency_weighted import RecencyWeightedStrongNumber
from types import SimpleNamespace


def _draw(d: date, numbers, strong):
    return SimpleNamespace(date=d, numbers=numbers, strong_number=strong)


def test_recency_main_requires_as_of_date():
    draws = [_draw(date(2024, 1, 1), [1, 2, 3, 4, 5, 6], 1)]
    with pytest.raises(ValueError, match="as_of_date"):
        RecencyWeightedFrequencyAlgorithm().run(draws)


def test_recency_main_uses_as_of_date_not_today():
    draws = [
        _draw(date(2020, 1, 1), [10, 11, 12, 13, 14, 15], 1),
        _draw(date(2024, 6, 1), [1, 2, 3, 4, 5, 6], 2),
    ]
    as_of = date(2024, 6, 15)
    combos = RecencyWeightedFrequencyAlgorithm().run(
        draws, top_n=3, num_for_analysis=8, num_to_recommend=8, as_of_date=as_of
    )
    assert len(combos) == 8


def test_recency_strong_requires_as_of_date():
    draws = [_draw(date(2024, 1, 1), [1, 2, 3, 4, 5, 6], 3)]
    with pytest.raises(ValueError, match="as_of_date"):
        RecencyWeightedStrongNumber().predict(draws)
