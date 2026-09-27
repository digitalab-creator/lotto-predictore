"""The proof machine: era cut, exact odds, no leakage, one holdout."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from services.draw_prize import ticket_cost_sql_literal
from services.exact_coverage import (
    ANY_PRIZE_PROBABILITY,
    MAIN_SPACE,
    TOTAL_OUTCOMES,
    exact_portfolio_report,
    independent_pack_any_prize,
    one_in,
    tier_probability,
)
from services.game_regime import split_regime
from services.pais_draw_rules import CURRENT_REGIME_START
from services.random_portfolio import distinct_random_portfolio
from services.ticket_validator import TicketValidationError, validate_portfolio
from services.validation_stats_v2 import (
    HoldoutAlreadyRan,
    benjamini_hochberg,
    cluster_bootstrap_ci,
    decide_verdict,
    halves_above_baseline,
    split_bounds,
    tier_call,
)
from services.validation_walk import LeakError, assert_train_before, walk_forward
import random


def _draw(day: date, strong: int = 1, numbers=None):
    return SimpleNamespace(
        date=day,
        numbers=numbers or [1, 2, 3, 4, 5, 6],
        strong_number=strong,
        id=day.toordinal(),
        source=None,
        prize_3=None,
    )


def _eight_lines():
    lines = []
    for index in range(8):
        numbers = sorted(((index * 5 + step * 7) % 37) + 1 for step in range(6))
        lines.append({"numbers": numbers, "strong": (index % 7) + 1})
    validate_portfolio(lines)
    return lines


def test_old_regime_block_is_dropped_together():
    """Strong 1–7 from the old era leaves with the strong-8 row. The cut is the date."""
    old_start = date(2010, 1, 5)
    old = [_draw(old_start + timedelta(days=i), strong=1 + (i % 7)) for i in range(6)]
    old.append(_draw(date(2011, 3, 1), strong=8))
    kept = _draw(CURRENT_REGIME_START, strong=4, numbers=[2, 4, 6, 8, 10, 12])
    legal, illegal = split_regime(old + [kept])
    assert illegal == []
    assert [row.date for row in legal] == [CURRENT_REGIME_START]


def test_ticket_cost_sql_literal_is_three_shekels():
    assert ticket_cost_sql_literal() == "3.00"


def test_closed_form_matches_published_odds():
    assert abs(ANY_PRIZE_PROBABILITY * 100 - 4.1751) < 0.0001
    assert one_in(tier_probability(6, True)) == pytest.approx(TOTAL_OUTCOMES)
    assert one_in(tier_probability(6, False)) == pytest.approx(2_712_248)
    assert round(one_in(tier_probability(3, False)), 2) == 30.17
    eight = independent_pack_any_prize(8)
    assert round(eight * 100, 2) == 28.91


def test_one_ticket_enumeration_matches_closed_form():
    report = exact_portfolio_report([{"numbers": [1, 2, 3, 4, 5, 6], "strong": 1}])
    assert report["any_prize_main_outcomes"] == 97062
    assert report["p_any_prize"] == pytest.approx(ANY_PRIZE_PROBABILITY)
    assert report["tiers"]["6_strong"]["probability"] == pytest.approx(1 / TOTAL_OUTCOMES)
    assert report["expected_winning_lines_per_draw"] == pytest.approx(ANY_PRIZE_PROBABILITY)


def test_duplicate_pack_is_rejected():
    line = {"numbers": [1, 2, 3, 4, 5, 6], "strong": 1}
    with pytest.raises(TicketValidationError):
        validate_portfolio([line] * 8)


def test_walk_rejects_a_strategy_that_sees_the_target():
    draws = [_draw(date(2024, 1, 1) + timedelta(days=i)) for i in range(4)]
    with pytest.raises(LeakError):
        assert_train_before(draws, draws[2])

    def produce(train):
        assert all(row.date < draws[len(train)].date for row in train)
        return _eight_lines()

    walked = walk_forward(draws, start=2, end=4, produce_lines=produce)
    assert len(walked.steps) == 2
    assert walked.errors == []


def test_duplicate_strategy_lines_are_errors_not_scores():
    draws = [_draw(date(2024, 1, 1) + timedelta(days=i)) for i in range(3)]

    def produce(_train):
        line = {"numbers": [1, 2, 3, 4, 5, 6], "strong": 1}
        return [line] * 8

    walked = walk_forward(draws, start=1, end=2, produce_lines=produce)
    assert walked.steps == []
    assert walked.errors


def test_select_window_cannot_see_holdout_draws():
    start = date(2024, 1, 1)
    draws = [_draw(start + timedelta(days=i)) for i in range(20)]
    select_start, holdout_start = split_bounds(len(draws))
    holdout_dates = {row.date for row in draws[holdout_start:]}
    seen = []

    def produce(train):
        seen.append({row.date for row in train})
        return _eight_lines()

    walk_forward(draws, start=select_start, end=holdout_start, produce_lines=produce)
    assert seen
    for train_dates in seen:
        assert train_dates.isdisjoint(holdout_dates)


def test_bootstrap_resamples_draws_not_exploded_lines():
    draw_rates = [0.0, 0.0, 1.0, 1.0]
    _point, draw_low, draw_high = cluster_bootstrap_ci(draw_rates, samples=400, seed=1)
    line_rates = [rate for rate in draw_rates for _ in range(8)]
    _point_l, line_low, line_high = cluster_bootstrap_ci(line_rates, samples=400, seed=1)
    assert (draw_high - draw_low) > (line_high - line_low)


def test_second_holdout_is_refused():
    class _Query:
        def count(self):
            return 1

    class _Db:
        def query(self, _model):
            return _Query()

    from services.validation_engine_v2 import ValidationEngineV2

    with pytest.raises(HoldoutAlreadyRan):
        ValidationEngineV2(_Db()).run_holdout()


def test_halves_must_both_beat_baseline_before_promotion():
    _first, _second, ok = halves_above_baseline([0.05, 0.02, 0.05, 0.02])
    assert ok is False
    _first, _second, ok = halves_above_baseline([0.08, 0.08, 0.09, 0.09])
    assert ok is True


def test_verdict_and_rare_tier_label():
    assert decide_verdict(ci_low=0.05, ci_high=0.06, point=0.055, baseline=ANY_PRIZE_PROBABILITY) == "pass"
    assert decide_verdict(ci_low=0.03, ci_high=0.05, point=0.045, baseline=ANY_PRIZE_PROBABILITY) == "fail"
    assert tier_call(expected_hits=0.01, ci_low=0.9, theoretical=0.0001, adjusted_p=0.01, primary=False) == (
        "insufficient data"
    )


def test_benjamini_hochberg_does_not_leave_a_raw_p_untouched_when_many_tests():
    adjusted = benjamini_hochberg([0.01, 0.04, 0.2])
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[1] == pytest.approx(0.06)


def test_uniform_portfolio_is_eight_distinct_lines():
    lines = distinct_random_portfolio(random.Random(1), 8)
    validate_portfolio(lines)
    assert MAIN_SPACE == 2_324_784


def test_tier_guard_rejects_sacrificing_high_tiers():
    from services.wheel_report import _tier_guard_vs_baseline

    baseline = {"p_4_plus": 0.01, "p_5_plus": 0.001, "p_6_plus": 0.0001}
    ok_wheel = {"p_4_plus": 0.0105, "p_5_plus": 0.00101, "p_6_plus": 0.0001}
    bad_wheel = {"p_4_plus": 0.008, "p_5_plus": 0.001, "p_6_plus": 0.0001}
    assert _tier_guard_vs_baseline(ok_wheel, baseline)["ok"] is True
    assert _tier_guard_vs_baseline(bad_wheel, baseline)["ok"] is False


def test_spread_wheel_has_higher_p_any_than_single_ticket():
    from services.coverage_optimizer import spread_seed_lines
    from services.exact_coverage import portfolio_p_any

    lines = spread_seed_lines()
    assert portfolio_p_any(lines) > ANY_PRIZE_PROBABILITY
