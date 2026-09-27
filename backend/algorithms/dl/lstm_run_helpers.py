"""Shared LSTM production / walk-forward helpers (cutoff-scoped weights, 8 distinct lines)."""

from __future__ import annotations

import random
from collections import Counter
from datetime import date
from itertools import combinations
from typing import Any, Callable, List

import torch

from config import NUM_COMBINATIONS_TO_RECOMMEND
from models import Draw
from shared.logging_service import get_backend_logger

from .lstm_model import LottoLSTM, draws_to_sequences
from .lstm_training import predict_next_numbers
from .lstm_weight_paths import (
    require_cutoff_model_path,
    training_cutoff_date,
    variant_meta_path,
    variant_model_path,
)

logger = get_backend_logger()


def train_variant_if_missing(
    *,
    draws: List[Draw],
    profile: str,
    training_cutoff: date,
    seq_len: int,
    hidden_size: int,
    num_layers: int,
    epochs: int,
    lr: float,
    batch_size: int,
) -> str:
    model_path = variant_model_path(profile, training_cutoff)
    meta_path = variant_meta_path(profile, training_cutoff)
    require_cutoff_model_path(model_path)
    if model_path.exists():
        return str(model_path)

    if len(draws) <= seq_len:
        raise ValueError("Not enough draws to train LSTM for this cutoff")

    num_numbers = 37
    X, y = draws_to_sequences(draws, seq_len, num_numbers)
    model = LottoLSTM(
        num_numbers=num_numbers,
        seq_len=seq_len,
        hidden_size=hidden_size,
        num_layers=num_layers,
    )
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for _ in range(epochs):
        permutation = torch.randperm(X.size(0))
        for i in range(0, X.size(0), batch_size):
            indices = permutation[i : i + batch_size]
            batch_x, batch_y = X[indices], y[indices]
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    from .lstm_model import save_meta

    save_meta(str(training_cutoff), str(meta_path))
    logger.info(
        "Arrr! [FSM LSTM] Trained cutoff-scoped weights",
        context={"profile": profile, "cutoff": str(training_cutoff), "path": str(model_path)},
    )
    return str(model_path)


def _topk_combo_portfolio(
    draws: List[Draw],
    model_path: str,
    *,
    seq_len: int,
    hidden_size: int,
    num_layers: int,
    num_to_recommend: int,
    rng: random.Random,
) -> list[list[int]]:
    require_cutoff_model_path(model_path)
    model = LottoLSTM(
        num_numbers=37,
        seq_len=seq_len,
        hidden_size=hidden_size,
        num_layers=num_layers,
    )
    model.load_state_dict(torch.load(model_path))
    model.eval()
    seq = draws[-seq_len:]
    x_seq = []
    for d in seq:
        onehot = [0] * 37
        for n in d.numbers:
            onehot[int(n) - 1] = 1
        x_seq.append(onehot)
    x_tensor = torch.tensor([x_seq], dtype=torch.float32)
    with torch.no_grad():
        output = model(x_tensor)[0].cpu().numpy()
    top_n_numbers = output.argsort()[-12:][::-1]
    scored: list[tuple[float, tuple[int, ...]]] = []
    for combo in combinations(top_n_numbers, 6):
        score = sum(output[i] for i in combo)
        scored.append((float(score), tuple(sorted(int(i) for i in combo))))
    scored.sort(reverse=True, key=lambda x: x[0])
    lines: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for _, combo in scored:
        if combo in seen:
            continue
        seen.add(combo)
        lines.append([i + 1 for i in combo])
        if len(lines) >= num_to_recommend:
            break
    if len(lines) < num_to_recommend:
        for attempt in range(num_to_recommend * 4):
            torch.manual_seed(rng.randint(1, 2_000_000_000))
            numbers = predict_next_numbers(
                draws,
                seq_len=seq_len,
                threshold=0.15 + (attempt % 5) * 0.05,
                model_path=model_path,
                hidden_size=hidden_size,
                num_layers=num_layers,
            )
            key = tuple(sorted(numbers))
            if key in seen:
                continue
            seen.add(key)
            lines.append(list(numbers))
            if len(lines) >= num_to_recommend:
                break
    return lines


def build_lstm_portfolio_combos(
    draws: List[Draw],
    *,
    model_path: str,
    seq_len: int,
    hidden_size: int,
    num_layers: int,
    num_to_recommend: int | None,
    rng: random.Random | None,
    params: dict[str, Any],
    strong_for_line: Callable[[List[int]], int],
    use_topk: bool = False,
) -> list[dict[str, Any]]:
    num_to_recommend = num_to_recommend or NUM_COMBINATIONS_TO_RECOMMEND
    rng = rng or random.Random(42)
    require_cutoff_model_path(model_path)

    if use_topk:
        number_lines = _topk_combo_portfolio(
            draws,
            model_path,
            seq_len=seq_len,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_to_recommend=num_to_recommend,
            rng=rng,
        )
    else:
        number_lines = []
        seen: set[tuple[int, ...]] = set()
        for attempt in range(num_to_recommend * 6):
            torch.manual_seed(rng.randint(1, 2_000_000_000))
            numbers = predict_next_numbers(
                draws,
                seq_len=seq_len,
                threshold=0.15 + (attempt % 6) * 0.05,
                model_path=model_path,
                hidden_size=hidden_size,
                num_layers=num_layers,
            )
            key = tuple(sorted(numbers))
            if key in seen:
                continue
            seen.add(key)
            number_lines.append(numbers)
            if len(number_lines) >= num_to_recommend:
                break

    if len(number_lines) < num_to_recommend:
        raise ValueError(
            f"LSTM produced only {len(number_lines)} distinct lines, need {num_to_recommend}"
        )

    combos: list[dict[str, Any]] = []
    for numbers in number_lines:
        combos.append(
            {
                "numbers": numbers,
                "strong": int(strong_for_line(numbers)),
                "params": dict(params),
            }
        )
    return combos


def default_strong_from_draws(draws: List[Draw]) -> int:
    strong_counter = Counter(draw.strong_number for draw in draws)
    return int(strong_counter.most_common(1)[0][0]) if strong_counter else 1


def resolve_cutoff(draws: List[Draw], as_of_date: date | None) -> date:
    return training_cutoff_date(draws, as_of_date)
