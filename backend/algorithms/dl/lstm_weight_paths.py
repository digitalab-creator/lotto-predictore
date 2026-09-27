"""Training-cutoff keyed LSTM weight paths — walk-forward must not reuse unscoped weights."""

from __future__ import annotations

import datetime
from pathlib import Path

from config import SEQUENCE_CLASSIFIER_MODEL_DIR

CUTOFF_TOKEN = "_cutoff_"


def training_cutoff_date(
    draws,
    as_of_date: datetime.date | None = None,
) -> datetime.date:
    if as_of_date is not None:
        return as_of_date
    if not draws:
        raise ValueError("Cannot derive training cutoff from empty draws")
    return draws[-1].date


def cutoff_slug(training_cutoff: datetime.date) -> str:
    return training_cutoff.strftime("%Y%m%d")


def path_has_training_cutoff(path: str | Path) -> bool:
    return CUTOFF_TOKEN in Path(path).name


def require_cutoff_model_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not path_has_training_cutoff(resolved):
        raise ValueError(
            f"LSTM weight path missing training cutoff marker '{CUTOFF_TOKEN}': {resolved.name}"
        )
    return resolved


def _lr_token(lr: float) -> str:
    return str(lr).replace(".", "p")


def grid_search_model_path(
    *,
    hidden_size: int,
    num_layers: int,
    seq_len: int,
    lr: float,
    batch_size: int,
    training_cutoff: datetime.date,
) -> Path:
    name = (
        f"sequence_classifier_grid_h{hidden_size}_l{num_layers}_s{seq_len}"
        f"_lr{_lr_token(lr)}_b{batch_size}{CUTOFF_TOKEN}{cutoff_slug(training_cutoff)}.pt"
    )
    return SEQUENCE_CLASSIFIER_MODEL_DIR / name


def variant_model_path(profile: str, training_cutoff: datetime.date) -> Path:
    name = f"{profile}{CUTOFF_TOKEN}{cutoff_slug(training_cutoff)}.pt"
    return SEQUENCE_CLASSIFIER_MODEL_DIR / name


def variant_meta_path(profile: str, training_cutoff: datetime.date) -> Path:
    name = f"{profile}{CUTOFF_TOKEN}{cutoff_slug(training_cutoff)}_meta.json"
    return SEQUENCE_CLASSIFIER_MODEL_DIR / name
