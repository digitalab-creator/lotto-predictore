import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Dict, Any
from models import Draw
from algorithms.base import Algorithm, register_algorithm
from collections import Counter
import os
import json
from datetime import date
from sqlalchemy.orm import Session
from shared.logging_service import get_backend_logger
import random
import numpy as np
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import TICKET_COST_PER_TABLE, PRIZE_TABLE, NUM_COMBINATIONS_TO_RECOMMEND
from db import SessionLocal
import itertools
from services.simulation_engine import calculate_roi_with_tax
import hashlib
import pickle

# Get the logger instance
dh_log = get_backend_logger()

dh_log.info("Arrr! sequence_classifier.py imported!")

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model.pt')
META_PATH = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_meta.json')

# --- Model Definition ---
class LottoLSTM(nn.Module):
    def __init__(self, num_numbers=37, seq_len=10, hidden_size=64, num_layers=2):
        super().__init__()
        self.num_numbers = num_numbers
        self.seq_len = seq_len
        self.lstm = nn.LSTM(input_size=num_numbers, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_numbers)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # Take last output
        out = self.fc(out)
        out = self.sigmoid(out)
        return out

# --- Metadata Helpers ---
def save_meta(latest_date: str, meta_path=META_PATH):
    with open(meta_path, 'w') as f:
        json.dump({'latest_date': latest_date}, f)

def load_meta(meta_path=META_PATH):
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, 'r') as f:
        return json.load(f)

# --- Data Preparation ---
def draws_to_sequences(draws: List[Draw], seq_len=10, num_numbers=37):
    # Each input: seq_len draws, each as one-hot vector of 37
    # Each output: binary vector of 37 (which numbers appear in next draw)
    X, y = [], []
    for i in range(len(draws) - seq_len):
        seq = draws[i:i+seq_len]
        target = draws[i+seq_len]
        x_seq = []
        for d in seq:
            onehot = [0]*num_numbers
            for n in d.numbers:
                onehot[n-1] = 1
            x_seq.append(onehot)
        target_vec = [0]*num_numbers
        for n in target.numbers:
            target_vec[n-1] = 1
        X.append(x_seq)
        y.append(target_vec)
    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

# --- Training Function ---
def train_lotto_lstm(draws: List[Draw], seq_len=10, epochs=30, lr=0.001, batch_size=16, model_path=MODEL_PATH, meta_path=META_PATH):
    num_numbers = 37
    X, y = draws_to_sequences(draws, seq_len, num_numbers)
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    try:
        for epoch in range(epochs):
            model.train()
            permutation = torch.randperm(X.size(0))
            for i in range(0, X.size(0), batch_size):
                indices = permutation[i:i+batch_size]
                batch_x, batch_y = X[indices], y[indices]
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
            dh_log.debug(f"Arrr! [FSM DEBUG] Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", context={"epoch": epoch+1, "loss": float(loss.item())})
        torch.save(model.state_dict(), model_path)
        # File sync to ensure data is written to disk
        try:
            with open(model_path, 'rb+') as f:
                f.flush()
                os.fsync(f.fileno())
            dh_log.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
        except Exception as e:
            dh_log.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
        # Integrity check: try to load the state_dict back
        try:
            _ = torch.load(model_path)
            dh_log.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
        except Exception as e:
            dh_log.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
        # Save latest date
        latest_date = str(draws[-1].date)
        save_meta(latest_date, meta_path)
        dh_log.info(f"Arrr! [FSM DEBUG] Model saved to {model_path} with latest_date {latest_date}", context={"model_path": model_path, "latest_date": latest_date})
        return model
    except Exception as e:
        dh_log.error(f"Arrr! LSTM training failed: {e}")
        return None

# --- Fine-tuning Function ---
def finetune_lotto_lstm(draws: List[Draw], seq_len=10, epochs=10, lr=0.0005, batch_size=8, model_path=MODEL_PATH, meta_path=META_PATH):
    num_numbers = 37
    X, y = draws_to_sequences(draws, seq_len, num_numbers)
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path))
        dh_log.info(f"Arrr! [FSM DEBUG] Loaded model from {model_path} for fine-tuning")
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    for epoch in range(epochs):
        model.train()
        permutation = torch.randperm(X.size(0))
        for i in range(0, X.size(0), batch_size):
            indices = permutation[i:i+batch_size]
            batch_x, batch_y = X[indices], y[indices]
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
        dh_log.debug(f"Arrr! [FSM DEBUG] Fine-tune Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", context={"epoch": epoch+1, "loss": float(loss.item())})
    torch.save(model.state_dict(), model_path)
    # File sync to ensure data is written to disk
    try:
        with open(model_path, 'rb+') as f:
            f.flush()
            os.fsync(f.fileno())
        dh_log.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
    except Exception as e:
        dh_log.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
    # Integrity check: try to load the state_dict back
    try:
        _ = torch.load(model_path)
        dh_log.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
    except Exception as e:
        dh_log.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
    # Save latest date
    latest_date = str(draws[-1].date)
    save_meta(latest_date, meta_path)
    dh_log.info(f"Arrr! [FSM DEBUG] Fine-tuned model saved to {model_path} with latest_date {latest_date}", context={"model_path": model_path, "latest_date": latest_date})
    return model

# --- Inference Function ---
def predict_next_numbers(draws: List[Draw], seq_len=10, threshold=0.5, model_path=MODEL_PATH, hidden_size=64, num_layers=2) -> List[int]:
    num_numbers = 37
    if len(draws) < seq_len:
        dh_log.error("Arrr! Not enough draws for sequence prediction!", context={"draws_len": len(draws), "seq_len": seq_len})
        raise ValueError("Not enough draws for sequence prediction")
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len, hidden_size=hidden_size, num_layers=num_layers)
    if not os.path.exists(model_path):
        dh_log.error(f"Arrr! Model file not found: {model_path}", context={"model_path": model_path})
        raise FileNotFoundError(f"Model file not found: {model_path}")
    model.load_state_dict(torch.load(model_path))
    model.eval()
    # Prepare input
    seq = draws[-seq_len:]
    x_seq = []
    for d in seq:
        onehot = [0]*num_numbers
        for n in d.numbers:
            onehot[n-1] = 1
        x_seq.append(onehot)
    x_tensor = torch.tensor([x_seq], dtype=torch.float32)
    with torch.no_grad():
        output = model(x_tensor)[0]
    # Arrr! Print the full output vector for FSM debug
    dh_log.debug(f"Arrr! [FSM DEBUG] Model raw output vector: {output.tolist()}", context={"output": output.tolist()})
    pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
    numbers = [i+1 for i in pred]
    # If no numbers, try a lower threshold for debug
    if len(numbers) == 0 and threshold > 0.2:
        dh_log.debug(f"Arrr! [FSM DEBUG] No numbers above threshold {threshold}, tryin' lower threshold 0.2!", context={"output": output.tolist()})
        pred = (output > 0.2).nonzero(as_tuple=True)[0].tolist()
        numbers = [i+1 for i in pred]
        dh_log.debug(f"Arrr! [FSM DEBUG] Numbers above 0.2: {numbers}", context={"numbers": numbers})
    dh_log.debug(f"Arrr! [FSM DEBUG] Model inference complete! Predicted numbers: {numbers}", context={"output": output.tolist(), "numbers": numbers})
    if len(numbers) > 6:
        top6 = output.topk(6).indices.tolist()
        numbers = [i+1 for i in top6]
        dh_log.debug(f"Arrr! [FSM DEBUG] More than 6 numbers predicted, takin' top 6: {numbers}", context={"top6": top6})
    elif len(numbers) < 6:
        all_numbers = [n for d in draws for n in d.numbers]
        freq = Counter(all_numbers)
        for n, _ in freq.most_common():
            if n not in numbers:
                numbers.append(n)
            if len(numbers) == 6:
                break
        dh_log.debug(f"Arrr! [FSM DEBUG] Less than 6 numbers, padded with most common: {numbers}", context={"numbers": numbers})
    return sorted(numbers)

# --- Utility: Get Latest Draw Date from DB ---
def get_latest_draw_date(db: Session) -> str:
    from sqlalchemy import desc
    latest = db.query(Draw).order_by(desc(Draw.date)).first()
    return str(latest.date) if latest else None

# --- Algorithm Integration ---
@register_algorithm
class SequenceClassificationLSTMAlgorithm(Algorithm):
    version = "sequence_lstm_classifier"
    description = "Sequence classification LSTM model. Learns temporal patterns."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log.info("Arrr! LSTM run method called!")
            seq_len = 10
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta()
            meta_date = meta["latest_date"] if meta else None
            dh_log.debug(f"Arrr! [FSM DEBUG] Latest DB date: {latest_db_date}, Meta date: {meta_date}", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            if not os.path.exists(MODEL_PATH) or not meta_date:
                dh_log.info("Arrr! [FSM DEBUG] No model or meta found, trainin' from scratch! Praisin' the FSM!")
                model = train_lotto_lstm(draws, seq_len=seq_len)
                if model is None:
                    dh_log.error("Arrr! LSTM training returned None!")
                    return []
                if not os.path.exists(MODEL_PATH):
                    dh_log.error(f"Arrr! Model file still not found after training: {MODEL_PATH}")
                    return []
            elif latest_db_date and latest_db_date > meta_date:
                dh_log.info(f"Arrr! [FSM DEBUG] DB newer than model, fine-tunin'! Praisin' the FSM!", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
                model = finetune_lotto_lstm(draws, seq_len=seq_len)
                if model is None:
                    dh_log.error("Arrr! LSTM fine-tuning returned None!")
                    return []
            else:
                dh_log.info(f"Arrr! [FSM DEBUG] Model up-to-date, runnin' inference! Praisin' the FSM!", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            try:
                numbers = predict_next_numbers(draws, seq_len=seq_len)
            except Exception as e:
                dh_log.error(f"Arrr! LSTM prediction failed: {e}")
                return []
            strong_counter = Counter(draw.strong_number for draw in draws)
            top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
            params = {
                "seq_len": seq_len,
                "model_version": self.version,
                "top_n": top_n,
                "num_for_analysis": num_for_analysis,
                "num_to_recommend": num_to_recommend
            }
            combos = [{"numbers": numbers, "strong": top_strong, "params": params}]
            if num_to_recommend is None:
                num_to_recommend = 8
            dh_log.debug(f"Arrr! LSTM combos generated: {combos}", context={"combos": combos})
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log.error(f"Arrr! LSTM run method failed: {e}")
            return []

# --- Grid Search Variants ---
@register_algorithm
class SequenceClassificationLSTM_H32_L1_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h32_l1"
    description = "LSTM: hidden_size=32, num_layers=1, seq_len=10, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log.info("Arrr! LSTM H32_L1 run method called!")
            seq_len = 10
            hidden_size = 32
            num_layers = 1
            lr = 0.001
            batch_size = 16
            model_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_h32_l1.pt')
            meta_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_h32_l1_meta.json')
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta(meta_path)
            meta_date = meta["latest_date"] if meta else None
            if not os.path.exists(model_path) or not meta_date:
                model = train_lotto_lstm(draws, seq_len=seq_len, epochs=30, lr=lr, batch_size=batch_size, model_path=model_path, meta_path=meta_path)
                if model is None or not os.path.exists(model_path):
                    return []
            elif latest_db_date and latest_db_date > meta_date:
                model = finetune_lotto_lstm(draws, seq_len=seq_len, epochs=10, lr=lr/2, batch_size=batch_size//2, model_path=model_path, meta_path=meta_path)
                if model is None:
                    return []
            numbers = predict_next_numbers(draws, seq_len=seq_len, model_path=model_path)
            strong_counter = Counter(draw.strong_number for draw in draws)
            top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
            params = {
                "seq_len": seq_len,
                "model_version": self.version,
                "top_n": top_n,
                "num_for_analysis": num_for_analysis,
                "num_to_recommend": num_to_recommend
            }
            combos = [{"numbers": numbers, "strong": top_strong, "params": params}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log.error(f"Arrr! LSTM H32_L1 run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_H128_L2_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2"
    description = "LSTM: hidden_size=128, num_layers=2, seq_len=10, lr=0.0005, batch_size=8. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log.info("Arrr! LSTM H128_L2 run method called!")
            seq_len = 10
            hidden_size = 128
            num_layers = 2
            lr = 0.0005
            batch_size = 8
            model_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_h128_l2.pt')
            meta_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_h128_l2_meta.json')
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta(meta_path)
            meta_date = meta["latest_date"] if meta else None
            if not os.path.exists(model_path) or not meta_date:
                model = train_lotto_lstm(draws, seq_len=seq_len, epochs=40, lr=lr, batch_size=batch_size, model_path=model_path, meta_path=meta_path)
                if model is None or not os.path.exists(model_path):
                    return []
            elif latest_db_date and latest_db_date > meta_date:
                model = finetune_lotto_lstm(draws, seq_len=seq_len, epochs=15, lr=lr/2, batch_size=batch_size//2, model_path=model_path, meta_path=meta_path)
                if model is None:
                    return []
            numbers = predict_next_numbers(draws, seq_len=seq_len, model_path=model_path)
            strong_counter = Counter(draw.strong_number for draw in draws)
            top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
            params = {
                "seq_len": seq_len,
                "model_version": self.version,
                "top_n": top_n,
                "num_for_analysis": num_for_analysis,
                "num_to_recommend": num_to_recommend
            }
            combos = [{"numbers": numbers, "strong": top_strong, "params": params}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log.error(f"Arrr! LSTM H128_L2 run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_SEQ20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_seq20"
    description = "LSTM: hidden_size=64, num_layers=2, seq_len=20, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log.info("Arrr! LSTM SEQ20 run method called!")
            seq_len = 20
            hidden_size = 64
            num_layers = 2
            lr = 0.001
            batch_size = 16
            model_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_seq20.pt')
            meta_path = os.path.join(os.path.dirname(__file__), 'sequence_classifier_model_seq20_meta.json')
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta(meta_path)
            meta_date = meta["latest_date"] if meta else None
            if not os.path.exists(model_path) or not meta_date:
                model = train_lotto_lstm(draws, seq_len=seq_len, epochs=30, lr=lr, batch_size=batch_size, model_path=model_path, meta_path=meta_path)
                if model is None or not os.path.exists(model_path):
                    return []
            elif latest_db_date and latest_db_date > meta_date:
                model = finetune_lotto_lstm(draws, seq_len=seq_len, epochs=10, lr=lr/2, batch_size=batch_size//2, model_path=model_path, meta_path=meta_path)
                if model is None:
                    return []
            numbers = predict_next_numbers(draws, seq_len=seq_len, model_path=model_path)
            strong_counter = Counter(draw.strong_number for draw in draws)
            top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
            params = {
                "seq_len": seq_len,
                "model_version": self.version,
                "top_n": top_n,
                "num_for_analysis": num_for_analysis,
                "num_to_recommend": num_to_recommend
            }
            combos = [{"numbers": numbers, "strong": top_strong, "params": params}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log.error(f"Arrr! LSTM SEQ20 run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_H128_L2_E20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2_e20"
    description = "LSTM: hidden_size=128, num_layers=2, seq_len=10, lr=0.001, batch_size=8, epochs=20. Inference-only, returns combos for a single test draw. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = 8, db: Session = None) -> List[Dict[str, Any]]:
        try:
            # Set random seeds for reproducibility
            random.seed(42)
            np.random.seed(42)
            torch.manual_seed(42)
            dh_log.info("Arrr! LSTM H128_L2_E20 (inference-only, single test draw) run method called!")
            seq_len = 10
            hidden_size = 128
            num_layers = 2
            lr = 0.001
            batch_size = 8
            epochs = 20
            threshold = 0.2
            model_path = os.path.join(os.path.dirname(__file__), '../scripts/sequence_classifier_grid_h128_l2_s10_lr0.001_b8.pt')
            combos = []
            static_params = {
                "hidden_size": hidden_size,
                "num_layers": num_layers,
                "seq_len": seq_len,
                "lr": lr,
                "batch_size": batch_size,
                "epochs": epochs,
                "threshold": threshold
            }
            for _ in range(num_to_recommend or 8):
                try:
                    numbers = predict_next_numbers(
                        draws,
                        seq_len=seq_len,
                        threshold=threshold,
                        model_path=model_path,
                        hidden_size=hidden_size,
                        num_layers=num_layers
                    )
                except Exception as e:
                    dh_log.error(f"Arrr! [FSM DEBUG] Prediction failed: {e}")
                    numbers = []
                strong_counter = Counter(draw.strong_number for draw in draws)
                top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
                combos.append({"numbers": numbers, "strong": top_strong, "params": static_params.copy()})
            return combos
        except Exception as e:
            dh_log.error(f"Arrr! LSTM H128_L2_E20 (inference-only, single test draw) run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_GridSearch_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_gridsearch"
    description = "Grid search over LSTM hyperparameters, returns best results. Praisin' the FSM!"

    _best_params_cache = {}

    def _get_cache_key(self, draws):
        # Use a hash of the draw dates as a cache key
        key = ','.join(str(d.date) for d in draws)
        return hashlib.md5(key.encode()).hexdigest()

    def _load_best_params_from_disk(self, cache_key):
        cache_path = os.path.join(os.path.dirname(__file__), f"gridsearch_best_{cache_key}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_best_params_to_disk(self, cache_key, best_params):
        cache_path = os.path.join(os.path.dirname(__file__), f"gridsearch_best_{cache_key}.pkl")
        with open(cache_path, 'wb') as f:
            pickle.dump(best_params, f)

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        dh_log.info("Arrr! LSTM Grid Search run method called! Praisin' the FSM!")
        hyperparams_grid = {
            'hidden_size': [64, 128, 256],
            'num_layers': [1, 2, 3],
            'seq_len': [10, 20],
            'lr': [0.001, 0.0005, 0.0003],
            'batch_size': [8, 16],
            'epochs': [20],
        }
        test_count = 12
        if len(draws) < max(hyperparams_grid['seq_len']) + test_count:
            dh_log.error(f"Arrr! [FSM GRID] Not enough draws for grid search evaluation!")
            return []
        train_draws = draws[:-test_count]
        test_draws = draws[-test_count:]
        cache_key = self._get_cache_key(train_draws)
        best_params = None
        if use_cache:
            best_params = self._best_params_cache.get(cache_key) or self._load_best_params_from_disk(cache_key)
        if not best_params:
            dh_log.info(f"Arrr! [FSM GRID] No cached best params, runnin' grid search! Praisin' the FSM!")
            results = []
            param_names = list(hyperparams_grid.keys())
            best_result = None
            best_roi = float('-inf')
            for values in itertools.product(*hyperparams_grid.values()):
                params = dict(zip(param_names, values))
                model_path = os.path.join(os.path.dirname(__file__), f"sequence_classifier_grid_h{params['hidden_size']}_l{params['num_layers']}_s{params['seq_len']}_lr{params['lr']}_b{params['batch_size']}.pt")
                dh_log.info(f"Arrr! [FSM GRID] Trainin' with params: {params}")
                model = LottoLSTM(num_numbers=37, seq_len=params['seq_len'], hidden_size=params['hidden_size'], num_layers=params['num_layers'])
                need_train = True
                if os.path.exists(model_path):
                    try:
                        state_dict = torch.load(model_path)
                        model.load_state_dict(state_dict)
                        dummy_input = torch.zeros((1, params['seq_len'], 37))
                        model.eval()
                        with torch.no_grad():
                            _ = model(dummy_input)
                        dh_log.info(f"Arrr! [FSM GRID] Loaded existing model for {params}")
                        need_train = False
                    except Exception as e:
                        dh_log.warning(f"Arrr! [FSM GRID] Model file mismatch or unusable, will retrain: {e}")
                        try:
                            os.remove(model_path)
                            dh_log.info(f"Arrr! [FSM GRID] Deleted mismatched model file: {model_path}")
                        except Exception as del_e:
                            dh_log.error(f"Arrr! [FSM GRID] Failed to delete model file: {model_path}, error: {del_e}")
                        if os.path.exists(model_path):
                            dh_log.error(f"Arrr! [FSM GRID] Model file still exists after delete attempt: {model_path}")
                        need_train = True
                if need_train:
                    X, y = draws_to_sequences(train_draws, seq_len=params['seq_len'], num_numbers=37)
                    criterion = torch.nn.BCELoss()
                    optimizer = torch.optim.Adam(model.parameters(), lr=params['lr'])
                    for epoch in range(params['epochs']):
                        model.train()
                        permutation = torch.randperm(X.size(0))
                        for i in range(0, X.size(0), params['batch_size']):
                            indices = permutation[i:i+params['batch_size']]
                            batch_x, batch_y = X[indices], y[indices]
                            optimizer.zero_grad()
                            outputs = model(batch_x)
                            loss = criterion(outputs, batch_y)
                            loss.backward()
                            optimizer.step()
                    torch.save(model.state_dict(), model_path)
                    # File sync to ensure data is written to disk
                    try:
                        with open(model_path, 'rb+') as f:
                            f.flush()
                            os.fsync(f.fileno())
                        dh_log.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
                    except Exception as e:
                        dh_log.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
                    # Integrity check: try to load the state_dict back
                    try:
                        _ = torch.load(model_path)
                        dh_log.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
                    except Exception as e:
                        dh_log.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
                def predict_next_numbers_patched(draws, seq_len=10, threshold=0.5, model_path=None):
                    model = LottoLSTM(
                        num_numbers=37,
                        seq_len=seq_len,
                        hidden_size=params['hidden_size'],
                        num_layers=params['num_layers']
                    )
                    if not os.path.exists(model_path):
                        raise FileNotFoundError(f"Model file not found: {model_path}")
                    model.load_state_dict(torch.load(model_path))
                    model.eval()
                    seq = draws[-seq_len:]
                    x_seq = []
                    for d in seq:
                        onehot = [0]*37
                        for n in d.numbers:
                            onehot[n-1] = 1
                        x_seq.append(onehot)
                    x_tensor = torch.tensor([x_seq], dtype=torch.float32)
                    with torch.no_grad():
                        output = model(x_tensor)[0]
                    pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
                    numbers = [i+1 for i in pred]
                    if len(numbers) > 6:
                        top6 = output.topk(6).indices.tolist()
                        numbers = [i+1 for i in top6]
                    elif len(numbers) < 6:
                        all_numbers = [n for d in draws for n in d.numbers]
                        from collections import Counter
                        freq = Counter(all_numbers)
                        for n, _ in freq.most_common():
                            if n not in numbers:
                                numbers.append(n)
                            if len(numbers) == 6:
                                break
                    return sorted(numbers)
                for strong_name, strong_cls in STRONG_NUMBER_REGISTRY.items():
                    if len(train_draws) < params['seq_len'] + 1:
                        dh_log.error(f"Arrr! [FSM GRID] Not enough draws for evaluation!")
                        continue
                    strong_algo = strong_cls()
                    all_prizes = 0
                    total_tickets = 0
                    NUM_TABLES_PER_DRAW = 8
                    prizes_list = []
                    for i, test_draw in enumerate(test_draws):
                        available_draws = train_draws + test_draws[:i]
                        combos = []
                        for j in range(NUM_TABLES_PER_DRAW):
                            torch.manual_seed(j)
                            np.random.seed(j)
                            random.seed(j)
                            numbers = predict_next_numbers_patched(available_draws, seq_len=params['seq_len'], threshold=0.2, model_path=model_path)
                            strong = strong_algo.predict(available_draws, numbers=numbers)
                            combos.append({"numbers": numbers, "strong": strong})
                        for combo in combos:
                            hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                            strong_hit = (combo["strong"] == test_draw.strong_number)
                            prize = PRIZE_TABLE.get((hits, strong_hit), 0)
                            all_prizes += prize
                            total_tickets += 1
                            prizes_list.append(prize)
                    total_cost = total_tickets * TICKET_COST_PER_TABLE
                    roi = calculate_roi_with_tax(prizes_list, total_cost)
                    result = {
                        'params': params,
                        'model_path': model_path,
                        'strong_algo': strong_name,
                        'roi': roi,
                        'total_prize': all_prizes,
                        'total_cost': total_cost,
                        'test_count': test_count
                    }
                    results.append(result)
                    dh_log.info(f"Arrr! [FSM GRID] Model result: {result}")
                    if result['roi'] > best_roi:
                        best_roi = result['roi']
                        best_result = result
            # Instead of returning only the best/top3, return all results for saving
            if use_cache:
                # Save best params to cache
                self._best_params_cache[cache_key] = best_result
                self._save_best_params_to_disk(cache_key, best_result)
            return results
        else:
            dh_log.debug(f"Arrr! [FSM GRID] Using cached best params! Praisin' the FSM! Params: {best_params}", context={"params": best_params})
            model_path = best_params['model_path']
            strong_cls = STRONG_NUMBER_REGISTRY[best_params['strong_algo']]
            model = LottoLSTM(num_numbers=37, seq_len=best_params['params']['seq_len'], hidden_size=best_params['params']['hidden_size'], num_layers=best_params['params']['num_layers'])
            model.load_state_dict(torch.load(model_path))
            model.eval()
            # Get model output probabilities for the next draw
            seq = draws[-best_params['params']['seq_len']:]
            x_seq = []
            for d in seq:
                onehot = [0]*37
                for n in d.numbers:
                    try:
                        onehot[int(n)-1] = 1  # ensure n is int
                    except Exception as e:
                        dh_log.error(f"Arrr! [FSM GRID] Error converting number to int: {n}, error: {e}")
                        raise
                x_seq.append(onehot)
            x_tensor = torch.tensor([x_seq], dtype=torch.float32)
            with torch.no_grad():
                output = model(x_tensor)[0].cpu().numpy()
            dh_log.debug(f"Arrr! [FSM GRID] Model output shape: {output.shape}, dtype: {output.dtype}")
            # Get the top 12 numbers by probability
            top_n_numbers = output.argsort()[-12:][::-1]
            dh_log.debug(f"Arrr! [FSM GRID] Top 12 numbers: {top_n_numbers}")
            # Generate all 6-number combinations from the top 12
            from itertools import combinations
            combo_candidates = list(combinations(top_n_numbers, 6))
            dh_log.debug(f"Arrr! [FSM GRID] Generated {len(combo_candidates)} combo candidates")
            # Score each combo by the sum of probabilities
            scored_combos = []
            for combo in combo_candidates:
                score = sum(output[i] for i in combo)
                scored_combos.append((score, combo))
            # Sort combos by score, descending
            scored_combos.sort(reverse=True, key=lambda x: x[0])
            # Take the top 8 unique combos
            unique_combos = []
            seen = set()
            for score, combo in scored_combos:
                sorted_combo = tuple(sorted(combo))
                if sorted_combo not in seen:
                    seen.add(sorted_combo)
                    unique_combos.append(sorted_combo)
                if len(unique_combos) == (num_to_recommend or NUM_COMBINATIONS_TO_RECOMMEND):
                    break
            dh_log.debug(f"Arrr! [FSM GRID] Unique combos count: {len(unique_combos)}")
            # Convert combos to the required format, ensure native ints and always include params
            combos = []
            strong_algo = strong_cls()
            for combo in unique_combos:
                try:
                    numbers = [int(i)+1 for i in combo]  # ensure native int
                    strong = strong_algo.predict(draws, numbers=numbers)
                    params = {
                        "seq_len": best_params['params']['seq_len'],
                        "model_version": self.version,
                        "top_n": top_n,
                        "num_for_analysis": num_for_analysis,
                        "num_to_recommend": num_to_recommend
                    }
                    combos.append({
                        "numbers": [int(n) for n in numbers],
                        "strong": int(strong) if hasattr(strong, '__int__') else strong,
                        "params": params
                    })
                except Exception as e:
                    dh_log.error(f"Arrr! [FSM GRID] Error generating combo: {combo}, error: {e}")
            if not combos:
                dh_log.warning(f"[FSM DEBUG] No combos generated, fallback to last test draws! Praisin' the FSM!")
                try:
                    combos = [{
                        "numbers": [int(n) for n in sorted(test_draws[-1].numbers)],
                        "strong": int(getattr(test_draws[-1], 'strong_number', 1)),
                        "params": best_params['params'].copy()
                    }]
                except Exception as e:
                    dh_log.error(f"Arrr! [FSM GRID] Fallback combo generation failed: {e}")
                    combos = []
            dh_log.info(f"Arrr! [FSM GRID] Final combos returned: {combos}")
            return combos

# Arrr! More grid search variants can be added here. Praise the FSM!

# Praise the FSM for deep learning magic! 