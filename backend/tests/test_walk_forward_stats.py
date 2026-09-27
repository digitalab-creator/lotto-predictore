"""Unit tests for walk-forward stats and production strategy selection rules."""

from types import SimpleNamespace

from config import NO_EDGE_LABEL
from services.strategy_selection import choose_production_strategy
from services.walk_forward_stats import (
    bootstrap_roi_from_steps,
    has_predictive_edge,
    make_strategy_id,
    parse_strategy_id,
    percentile_rank,
    summarize_draw_series,
)


def test_strategy_id_roundtrip():
    sid = make_strategy_id("balanced_spread_fixed_ranges", "most_common")
    assert parse_strategy_id(sid) == ("balanced_spread_fixed_ranges", "most_common")


def test_percentile_rank_monotonic():
    sample = [0.0, 0.1, 0.2, 0.3, 0.4]
    assert percentile_rank(0.0, sample) == 20.0
    assert percentile_rank(0.4, sample) == 100.0


def test_has_predictive_edge_requires_high_percentile_and_n():
    assert has_predictive_edge(299, 99.0, min_draws=300, band_low=5, band_high=95) is False
    assert has_predictive_edge(300, 50.0, min_draws=300, band_low=5, band_high=95) is False
    assert has_predictive_edge(300, 96.0, min_draws=300, band_low=5, band_high=95) is True


def test_summarize_draw_series_roi():
    stats = summarize_draw_series(
        step_nets=[10.0, -5.0],
        step_costs=[24.0, 24.0],
        line_payouts=[5.0, 0.0],
        hit_flags_3plus=[True, False],
        strong_hit_flags=[True, False],
    )
    assert stats["independent_draw_count"] == 2.0
    assert round(stats["roi"], 4) == round(5.0 / 48.0, 4)


def test_bootstrap_roi_from_steps_non_empty():
    rois = bootstrap_roi_from_steps([1.0, -1.0], [24.0, 24.0], samples=20, rng_seed=1)
    assert len(rois) == 20


def test_choose_production_strategy_no_edge_in_band():
    class FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self._rows

        def first(self):
            return None

    class FakeDb:
        def query(self, model):
            row = SimpleNamespace(
                strategy_id="recency_weighted_linear+most_common",
                random_percentile=50.0,
                independent_draw_count=400,
                has_predictive_edge=False,
            )
            return FakeQuery([row])

    main, strong, meta = choose_production_strategy(FakeDb())
    assert main == "coverage_optimizer"
    assert strong == "exact"
    assert meta.get("no_edge") is True
    assert meta.get("detail") == NO_EDGE_LABEL
    assert meta.get("use_coverage") is True
