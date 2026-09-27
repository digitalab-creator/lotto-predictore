"""Run a registered main+strong pair on a training window (shared by production and walk-forward)."""

from __future__ import annotations

import inspect
import random
from datetime import date
from typing import Any

from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
from models import Draw
from services.ticket_validator import TicketValidationError, normalize_portfolio_lines


def _top_n_for_algo(algo_name: str) -> int:
    if algo_name == "top_6_overall_frequent_v2":
        return 10
    return 3


def _accepts_kwarg(callable_obj, name: str) -> bool:
    sig = inspect.signature(callable_obj)
    if name in sig.parameters:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def run_strategy_on_draws(
    *,
    train_draws: list[Draw],
    main_algo: str,
    strong_algo: str,
    as_of_date: date,
    rng: random.Random,
    db: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Fit on ``train_draws`` and return validated portfolio lines plus params metadata.
    Raises TicketValidationError when the algorithm output is not a legal 8-line pack.
    """
    if main_algo not in ALGORITHM_REGISTRY:
        raise ValueError(f"Unknown main algorithm: {main_algo}")
    if strong_algo not in STRONG_NUMBER_REGISTRY:
        raise ValueError(f"Unknown strong algorithm: {strong_algo}")

    main_cls = ALGORITHM_REGISTRY[main_algo]
    strong_cls = STRONG_NUMBER_REGISTRY[strong_algo]
    top_n = _top_n_for_algo(main_algo)

    main_instance = main_cls()
    run_sig = inspect.signature(main_instance.run)
    run_kwargs: dict[str, Any] = {
        "top_n": top_n,
        "num_for_analysis": NUM_COMBINATIONS_FOR_ANALYSIS,
        "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND,
    }
    if _accepts_kwarg(main_instance.run, "as_of_date"):
        run_kwargs["as_of_date"] = as_of_date
    if _accepts_kwarg(main_instance.run, "rng"):
        run_kwargs["rng"] = rng
    if "draws" in run_sig.parameters:
        run_kwargs["draws"] = train_draws
    if db is not None and "db" in run_sig.parameters:
        run_kwargs["db"] = db
    if getattr(main_instance, "version", None) == "sequence_lstm_classifier_gridsearch":
        if "use_cache" in run_sig.parameters:
            run_kwargs["use_cache"] = False

    positional_names = [
        p.name
        for p in run_sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        and p.name not in ("self",)
    ]
    if positional_names and positional_names[0] == "draws":
        raw_combos = main_instance.run(
            train_draws, **{k: v for k, v in run_kwargs.items() if k != "draws"}
        )
    else:
        raw_combos = main_instance.run(**run_kwargs)

    if not raw_combos:
        raise TicketValidationError(f"Algorithm {main_algo} returned no combinations")

    strong_instance = strong_cls()
    predict_extra: dict[str, Any] = {}
    if _accepts_kwarg(strong_instance.predict, "as_of_date"):
        predict_extra["as_of_date"] = as_of_date
    if _accepts_kwarg(strong_instance.predict, "rng"):
        predict_extra["rng"] = rng
    default_strong = strong_instance.predict(train_draws, **predict_extra)

    if raw_combos and isinstance(raw_combos[0], dict) and "numbers" in raw_combos[0]:
        if raw_combos[0].get("strong") is None:
            for combo in raw_combos:
                if combo.get("strong") is None:
                    combo["strong"] = default_strong

    lines = normalize_portfolio_lines(raw_combos, default_strong)
    params = {}
    if raw_combos and isinstance(raw_combos[0], dict):
        params = dict(raw_combos[0].get("params") or {})
    params.update({"top_n": top_n, "main_algo": main_algo, "strong_algo": strong_algo})
    return lines, params
