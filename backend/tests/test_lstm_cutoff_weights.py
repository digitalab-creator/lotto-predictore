"""Phase 6 — LSTM cutoff weights and no future-draw training leakage."""

import datetime

import pytest

from algorithms.dl.lstm_model import draws_to_sequences
from algorithms.dl.lstm_weight_paths import (
    grid_search_model_path,
    path_has_training_cutoff,
    require_cutoff_model_path,
)


class _FakeDraw:
    def __init__(self, day: int, numbers: list[int]):
        self.date = datetime.date(2020, 1, day)
        self.numbers = numbers


def test_path_without_cutoff_is_refused():
    legacy = "sequence_classifier_grid_h64_l1_s10_lr0.001_b8.pt"
    assert path_has_training_cutoff(legacy) is False
    with pytest.raises(ValueError, match="missing training cutoff"):
        require_cutoff_model_path(legacy)


def test_cutoff_keyed_grid_path_is_loadable():
    cutoff = datetime.date(2026, 1, 15)
    path = grid_search_model_path(
        hidden_size=64,
        num_layers=1,
        seq_len=10,
        lr=0.001,
        batch_size=8,
        training_cutoff=cutoff,
    )
    assert path_has_training_cutoff(path)
    assert require_cutoff_model_path(path) == path
    assert "20260115" in path.name


def test_draws_to_sequences_never_targets_draw_outside_window():
    draws = [_FakeDraw(i, [1, 2, 3, 4, 5, 6]) for i in range(1, 11)]
    seq_len = 3
    train_only = draws[:8]
    X_train, _ = draws_to_sequences(train_only, seq_len=seq_len)
    X_all, _ = draws_to_sequences(draws, seq_len=seq_len)
    assert X_train.size(0) == len(train_only) - seq_len
    assert X_all.size(0) == len(draws) - seq_len
    assert X_train.size(0) < X_all.size(0)
