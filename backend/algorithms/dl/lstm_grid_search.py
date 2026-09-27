import hashlib
import itertools
import os
import pickle
import random
from datetime import date
from typing import Any, Dict, List

import numpy as np
import torch
from models import Draw
from sqlalchemy.orm import Session

from utils.path_setup import setup_backend_path

setup_backend_path()

from algorithms.base import Algorithm, register_algorithm
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import NUM_COMBINATIONS_TO_RECOMMEND, SEQUENCE_CLASSIFIER_MODEL_DIR
from services.simulation_engine import calculate_roi_with_tax
from services.simulation_helpers.simulation_prize import (
    calculate_prize,
    draw_has_prize_data,
    draw_ticket_cost,
)
from shared.logging_service import get_backend_logger

from .lstm_model import LottoLSTM, draws_to_sequences
from .lstm_run_helpers import build_lstm_portfolio_combos, resolve_cutoff
from .lstm_weight_paths import (
    cutoff_slug,
    grid_search_model_path,
    path_has_training_cutoff,
    require_cutoff_model_path,
)

logger = get_backend_logger()


@register_algorithm
class SequenceClassificationLSTM_GridSearch_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_gridsearch"
    description = "Grid search over LSTM hyperparameters, returns best results. Praisin' the FSM!"

    _best_params_cache: dict[str, Any] = {}

    def _get_cache_key(self, draws: List[Draw], training_cutoff: date) -> str:
        key = ",".join(str(d.date) for d in draws) + f"|{cutoff_slug(training_cutoff)}"
        return hashlib.md5(key.encode()).hexdigest()

    def _load_best_params_from_disk(self, cache_key: str):
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        return None

    def _save_best_params_to_disk(self, cache_key: str, best_params: dict) -> None:
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        with open(cache_path, "wb") as f:
            pickle.dump(best_params, f)

    def _train_grid_candidate(
        self,
        train_draws: List[Draw],
        params: dict[str, Any],
        training_cutoff: date,
    ) -> str:
        model_path = grid_search_model_path(
            hidden_size=params["hidden_size"],
            num_layers=params["num_layers"],
            seq_len=params["seq_len"],
            lr=params["lr"],
            batch_size=params["batch_size"],
            training_cutoff=training_cutoff,
        )
        require_cutoff_model_path(model_path)
        if model_path.exists():
            try:
                probe = LottoLSTM(
                    num_numbers=37,
                    seq_len=params["seq_len"],
                    hidden_size=params["hidden_size"],
                    num_layers=params["num_layers"],
                )
                probe.load_state_dict(torch.load(model_path))
                dummy_input = torch.zeros((1, params["seq_len"], 37))
                probe.eval()
                with torch.no_grad():
                    _ = probe(dummy_input)
                return str(model_path)
            except Exception as exc:
                logger.warning(
                    "Arrr! [FSM GRID] Stale cutoff model, retrainin'",
                    context={"path": str(model_path), "error": str(exc)},
                )
                model_path.unlink(missing_ok=True)

        model = LottoLSTM(
            num_numbers=37,
            seq_len=params["seq_len"],
            hidden_size=params["hidden_size"],
            num_layers=params["num_layers"],
        )
        X, y = draws_to_sequences(train_draws, seq_len=params["seq_len"], num_numbers=37)
        criterion = torch.nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=params["lr"])
        for _ in range(params["epochs"]):
            model.train()
            permutation = torch.randperm(X.size(0))
            for i in range(0, X.size(0), params["batch_size"]):
                indices = permutation[i : i + params["batch_size"]]
                batch_x, batch_y = X[indices], y[indices]
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
        model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), model_path)
        return str(model_path)

    def _predict_numbers_patched(
        self,
        draws: List[Draw],
        params: dict[str, Any],
        model_path: str,
        threshold: float = 0.2,
    ) -> List[int]:
        model = LottoLSTM(
            num_numbers=37,
            seq_len=params["seq_len"],
            hidden_size=params["hidden_size"],
            num_layers=params["num_layers"],
        )
        require_cutoff_model_path(model_path)
        model.load_state_dict(torch.load(model_path))
        model.eval()
        seq = draws[-params["seq_len"] :]
        x_seq = []
        for d in seq:
            onehot = [0] * 37
            for n in d.numbers:
                onehot[int(n) - 1] = 1
            x_seq.append(onehot)
        x_tensor = torch.tensor([x_seq], dtype=torch.float32)
        with torch.no_grad():
            output = model(x_tensor)[0]
        pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
        numbers = [i + 1 for i in pred]
        if len(numbers) > 6:
            top6 = output.topk(6).indices.tolist()
            numbers = [i + 1 for i in top6]
        elif len(numbers) < 6:
            from collections import Counter

            all_numbers = [n for d in draws for n in d.numbers]
            freq = Counter(all_numbers)
            for n, _ in freq.most_common():
                if n not in numbers:
                    numbers.append(n)
                if len(numbers) == 6:
                    break
        return sorted(numbers)

    def _hyperparameter_search(
        self,
        draws: List[Draw],
        training_cutoff: date,
        hyperparams_grid: dict[str, list],
        test_count: int,
    ) -> dict[str, Any] | None:
        train_draws = draws[:-test_count]
        test_draws = [d for d in draws[-test_count:] if draw_has_prize_data(d)]
        if not test_draws:
            return None
        best_result = None
        best_roi = float("-inf")
        param_names = list(hyperparams_grid.keys())
        for values in itertools.product(*hyperparams_grid.values()):
            params = dict(zip(param_names, values))
            model_path = self._train_grid_candidate(train_draws, params, training_cutoff)
            for strong_name, strong_cls in STRONG_NUMBER_REGISTRY.items():
                strong_algo = strong_cls()
                all_prizes = 0
                total_cost = 0.0
                prizes_list: list[float] = []
                for i, test_draw in enumerate(test_draws):
                    available_draws = train_draws + test_draws[:i]
                    for j in range(8):
                        torch.manual_seed(j)
                        np.random.seed(j)
                        random.seed(j)
                        numbers = self._predict_numbers_patched(
                            available_draws, params, model_path, threshold=0.2
                        )
                        strong = strong_algo.predict(available_draws, numbers=numbers)
                        hits = sum(n in test_draw.numbers for n in numbers)
                        strong_hit = int(strong) == int(test_draw.strong_number)
                        prize = calculate_prize(test_draw, hits, strong_hit)
                        if prize is None:
                            continue
                        all_prizes += prize
                        prizes_list.append(float(prize))
                        total_cost += draw_ticket_cost(test_draw)
                roi = calculate_roi_with_tax(prizes_list, total_cost)
                result = {
                    "params": params,
                    "model_path": model_path,
                    "strong_algo": strong_name,
                    "roi": roi,
                    "total_prize": all_prizes,
                    "total_cost": total_cost,
                    "test_count": len(test_draws),
                    "training_cutoff": str(training_cutoff),
                }
                if roi > best_roi:
                    best_roi = roi
                    best_result = result
        return best_result

    def _fit_final_model(self, draws: List[Draw], best_params: dict[str, Any], training_cutoff: date) -> str:
        params = best_params["params"]
        model_path = grid_search_model_path(
            hidden_size=params["hidden_size"],
            num_layers=params["num_layers"],
            seq_len=params["seq_len"],
            lr=params["lr"],
            batch_size=params["batch_size"],
            training_cutoff=training_cutoff,
        )
        require_cutoff_model_path(model_path)
        model = LottoLSTM(
            num_numbers=37,
            seq_len=params["seq_len"],
            hidden_size=params["hidden_size"],
            num_layers=params["num_layers"],
        )
        X, y = draws_to_sequences(draws, seq_len=params["seq_len"], num_numbers=37)
        criterion = torch.nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=params["lr"])
        for _ in range(params["epochs"]):
            model.train()
            permutation = torch.randperm(X.size(0))
            for i in range(0, X.size(0), params["batch_size"]):
                indices = permutation[i : i + params["batch_size"]]
                batch_x, batch_y = X[indices], y[indices]
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
        model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), model_path)
        return str(model_path)

    def _produce_combos(
        self,
        draws: List[Draw],
        best_params: dict[str, Any],
        training_cutoff: date,
        top_n: int,
        num_for_analysis: int | None,
        num_to_recommend: int | None,
        rng: random.Random | None,
    ) -> List[Dict[str, Any]]:
        model_path = self._fit_final_model(draws, best_params, training_cutoff)
        strong_cls = STRONG_NUMBER_REGISTRY[best_params["strong_algo"]]
        strong_algo = strong_cls()
        params = {
            "seq_len": best_params["params"]["seq_len"],
            "model_version": self.version,
            "training_cutoff": str(training_cutoff),
            "top_n": top_n,
            "num_for_analysis": num_for_analysis,
            "num_to_recommend": num_to_recommend,
            "grid_params": best_params["params"],
        }
        return build_lstm_portfolio_combos(
            draws,
            model_path=model_path,
            seq_len=best_params["params"]["seq_len"],
            hidden_size=best_params["params"]["hidden_size"],
            num_layers=best_params["params"]["num_layers"],
            num_to_recommend=num_to_recommend,
            rng=rng,
            params=params,
            strong_for_line=lambda nums: int(strong_algo.predict(draws, numbers=nums)),
            use_topk=True,
        )

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = None,
        db: Session = None,
        use_cache: bool = True,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        logger.info("Arrr! LSTM Grid Search run method called! Praisin' the FSM!")
        hyperparams_grid = {
            "hidden_size": [64, 128, 256],
            "num_layers": [1, 2, 3],
            "seq_len": [10, 20],
            "lr": [0.001, 0.0005, 0.0003],
            "batch_size": [8, 16],
            "epochs": [20],
        }
        test_count = 12
        if len(draws) < max(hyperparams_grid["seq_len"]) + test_count:
            logger.error("Arrr! [FSM GRID] Not enough draws for grid search evaluation!")
            return []
        training_cutoff = resolve_cutoff(draws, as_of_date)
        tune_draws = draws[:-test_count]
        cache_key = self._get_cache_key(tune_draws, training_cutoff)
        best_params = None
        if use_cache:
            best_params = self._best_params_cache.get(cache_key) or self._load_best_params_from_disk(
                cache_key
            )
            if best_params and not path_has_training_cutoff(best_params.get("model_path", "")):
                logger.warning("Arrr! [FSM GRID] Ignoring cached params with legacy weight path")
                best_params = None
        if not best_params:
            logger.info("Arrr! [FSM GRID] Runnin' hyperparameter search inside training window")
            best_params = self._hyperparameter_search(draws, training_cutoff, hyperparams_grid, test_count)
            if not best_params:
                return []
            if use_cache:
                self._best_params_cache[cache_key] = best_params
                self._save_best_params_to_disk(cache_key, best_params)
        return self._produce_combos(
            draws,
            best_params,
            training_cutoff,
            top_n,
            num_for_analysis,
            num_to_recommend,
            rng,
        )
