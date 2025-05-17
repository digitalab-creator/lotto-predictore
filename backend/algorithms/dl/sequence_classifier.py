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
from services.logger import dh_log

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
            dh_log(f"Arrr! [FSM DEBUG] Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", level="DEBUG", context={"epoch": epoch+1, "loss": float(loss.item())})
        torch.save(model.state_dict(), model_path)
        # Save latest date
        latest_date = str(draws[-1].date)
        save_meta(latest_date, meta_path)
        dh_log(f"Arrr! [FSM DEBUG] Model saved to {model_path} with latest_date {latest_date}", level="INFO", context={"model_path": model_path, "latest_date": latest_date})
        return model
    except Exception as e:
        dh_log(f"Arrr! LSTM training failed: {e}", level="ERROR")
        return None

# --- Fine-tuning Function ---
def finetune_lotto_lstm(draws: List[Draw], seq_len=10, epochs=10, lr=0.0005, batch_size=8, model_path=MODEL_PATH, meta_path=META_PATH):
    num_numbers = 37
    X, y = draws_to_sequences(draws, seq_len, num_numbers)
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path))
        dh_log(f"Arrr! [FSM DEBUG] Loaded model from {model_path} for fine-tuning", level="INFO", context={"model_path": model_path})
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
        dh_log(f"Arrr! [FSM DEBUG] Fine-tune Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", level="DEBUG", context={"epoch": epoch+1, "loss": float(loss.item())})
    torch.save(model.state_dict(), model_path)
    # Save latest date
    latest_date = str(draws[-1].date)
    save_meta(latest_date, meta_path)
    dh_log(f"Arrr! [FSM DEBUG] Fine-tuned model saved to {model_path} with latest_date {latest_date}", level="INFO", context={"model_path": model_path, "latest_date": latest_date})
    return model

# --- Inference Function ---
def predict_next_numbers(draws: List[Draw], seq_len=10, threshold=0.5, model_path=MODEL_PATH) -> List[int]:
    num_numbers = 37
    if len(draws) < seq_len:
        dh_log("Arrr! Not enough draws for sequence prediction!", level="ERROR", context={"draws_len": len(draws), "seq_len": seq_len})
        raise ValueError("Not enough draws for sequence prediction")
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len)
    if not os.path.exists(model_path):
        dh_log(f"Arrr! Model file not found: {model_path}", level="ERROR", context={"model_path": model_path})
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
    dh_log(f"Arrr! [FSM DEBUG] Model raw output vector: {output.tolist()}", level="DEBUG", context={"output": output.tolist()})
    pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
    numbers = [i+1 for i in pred]
    # If no numbers, try a lower threshold for debug
    if len(numbers) == 0 and threshold > 0.2:
        dh_log(f"Arrr! [FSM DEBUG] No numbers above threshold {threshold}, tryin' lower threshold 0.2!", level="DEBUG", context={"output": output.tolist()})
        pred = (output > 0.2).nonzero(as_tuple=True)[0].tolist()
        numbers = [i+1 for i in pred]
        dh_log(f"Arrr! [FSM DEBUG] Numbers above 0.2: {numbers}", level="DEBUG", context={"numbers": numbers})
    dh_log(f"Arrr! [FSM DEBUG] Model inference complete! Predicted numbers: {numbers}", level="DEBUG", context={"output": output.tolist(), "numbers": numbers})
    if len(numbers) > 6:
        top6 = output.topk(6).indices.tolist()
        numbers = [i+1 for i in top6]
        dh_log(f"Arrr! [FSM DEBUG] More than 6 numbers predicted, takin' top 6: {numbers}", level="DEBUG", context={"top6": top6})
    elif len(numbers) < 6:
        all_numbers = [n for d in draws for n in d.numbers]
        freq = Counter(all_numbers)
        for n, _ in freq.most_common():
            if n not in numbers:
                numbers.append(n)
            if len(numbers) == 6:
                break
        dh_log(f"Arrr! [FSM DEBUG] Less than 6 numbers, padded with most common: {numbers}", level="DEBUG", context={"numbers": numbers})
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
            dh_log("Arrr! LSTM run method called!", level="INFO")
            seq_len = 10
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta()
            meta_date = meta["latest_date"] if meta else None
            dh_log(f"Arrr! [FSM DEBUG] Latest DB date: {latest_db_date}, Meta date: {meta_date}", level="DEBUG", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            if not os.path.exists(MODEL_PATH) or not meta_date:
                dh_log("Arrr! [FSM DEBUG] No model or meta found, trainin' from scratch! Praisin' the FSM!", level="INFO")
                model = train_lotto_lstm(draws, seq_len=seq_len)
                if model is None:
                    dh_log("Arrr! LSTM training returned None!", level="ERROR")
                    return []
                if not os.path.exists(MODEL_PATH):
                    dh_log(f"Arrr! Model file still not found after training: {MODEL_PATH}", level="ERROR")
                    return []
            elif latest_db_date and latest_db_date > meta_date:
                dh_log(f"Arrr! [FSM DEBUG] DB newer than model, fine-tunin'! Praisin' the FSM!", level="INFO", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
                model = finetune_lotto_lstm(draws, seq_len=seq_len)
                if model is None:
                    dh_log("Arrr! LSTM fine-tuning returned None!", level="ERROR")
                    return []
            else:
                dh_log(f"Arrr! [FSM DEBUG] Model up-to-date, runnin' inference! Praisin' the FSM!", level="INFO", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            try:
                numbers = predict_next_numbers(draws, seq_len=seq_len)
            except Exception as e:
                dh_log(f"Arrr! LSTM prediction failed: {e}", level="ERROR")
                return []
            strong_counter = Counter(draw.strong_number for draw in draws)
            top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
            combos = [{"numbers": numbers, "strong": top_strong}]
            if num_to_recommend is None:
                num_to_recommend = 8
            dh_log(f"Arrr! LSTM combos generated: {combos}", level="DEBUG", context={"combos": combos})
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log(f"Arrr! LSTM run method failed: {e}", level="ERROR")
            return []

# --- Grid Search Variants ---
@register_algorithm
class SequenceClassificationLSTM_H32_L1_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h32_l1"
    description = "LSTM: hidden_size=32, num_layers=1, seq_len=10, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log("Arrr! LSTM H32_L1 run method called!", level="INFO")
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
            combos = [{"numbers": numbers, "strong": top_strong}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log(f"Arrr! LSTM H32_L1 run method failed: {e}", level="ERROR")
            return []

@register_algorithm
class SequenceClassificationLSTM_H128_L2_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2"
    description = "LSTM: hidden_size=128, num_layers=2, seq_len=10, lr=0.0005, batch_size=8. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log("Arrr! LSTM H128_L2 run method called!", level="INFO")
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
            combos = [{"numbers": numbers, "strong": top_strong}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log(f"Arrr! LSTM H128_L2 run method failed: {e}", level="ERROR")
            return []

@register_algorithm
class SequenceClassificationLSTM_SEQ20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_seq20"
    description = "LSTM: hidden_size=64, num_layers=2, seq_len=20, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            dh_log("Arrr! LSTM SEQ20 run method called!", level="INFO")
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
            combos = [{"numbers": numbers, "strong": top_strong}]
            if num_to_recommend is None:
                num_to_recommend = 8
            return combos * num_to_recommend if combos else []
        except Exception as e:
            dh_log(f"Arrr! LSTM SEQ20 run method failed: {e}", level="ERROR")
            return []

# Arrr! More grid search variants can be added here. Praise the FSM!

# Praise the FSM for deep learning magic! 