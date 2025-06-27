import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
from typing import List
from sqlalchemy.orm import Session
from models import Draw
from pathlib import Path

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from .lstm_model import LottoLSTM, draws_to_sequences, save_meta, load_meta

logger = get_backend_logger()

# --- Training Function ---
def train_lotto_lstm(draws: List[Draw], seq_len=10, epochs=30, lr=0.001, batch_size=16, model_path=None, meta_path=None):
    from .lstm_model import MODEL_PATH, META_PATH
    if model_path is None:
        model_path = MODEL_PATH
    if meta_path is None:
        meta_path = META_PATH
        
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
            logger.debug(f"Arrr! [FSM DEBUG] Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", context={"epoch": epoch+1, "loss": float(loss.item())})
        torch.save(model.state_dict(), model_path)
        # File sync to ensure data is written to disk
        try:
            with open(model_path, 'rb+') as f:
                f.flush()
                os.fsync(f.fileno())
            logger.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
        except Exception as e:
            logger.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
        # Integrity check: try to load the state_dict back
        try:
            _ = torch.load(model_path)
            logger.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
        except Exception as e:
            logger.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
        # Save latest date
        latest_date = str(draws[-1].date)
        save_meta(latest_date, meta_path)
        logger.info(f"Arrr! [FSM DEBUG] Model saved to {model_path} with latest_date {latest_date}", context={"model_path": model_path, "latest_date": latest_date})
        return model
    except Exception as e:
        logger.error(f"Arrr! LSTM training failed: {e}")
        return None

# --- Fine-tuning Function ---
def finetune_lotto_lstm(draws: List[Draw], seq_len=10, epochs=10, lr=0.0005, batch_size=8, model_path=None, meta_path=None):
    from .lstm_model import MODEL_PATH, META_PATH
    if model_path is None:
        model_path = MODEL_PATH
    if meta_path is None:
        meta_path = META_PATH
        
    num_numbers = 37
    X, y = draws_to_sequences(draws, seq_len, num_numbers)
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path))
        logger.info(f"Arrr! [FSM DEBUG] Loaded model from {model_path} for fine-tuning")
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
        logger.debug(f"Arrr! [FSM DEBUG] Fine-tune Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}", context={"epoch": epoch+1, "loss": float(loss.item())})
    torch.save(model.state_dict(), model_path)
    # File sync to ensure data is written to disk
    try:
        with open(model_path, 'rb+') as f:
            f.flush()
            os.fsync(f.fileno())
        logger.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
    except Exception as e:
        logger.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
    # Integrity check: try to load the state_dict back
    try:
        _ = torch.load(model_path)
        logger.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
    except Exception as e:
        logger.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
    # Save latest date
    latest_date = str(draws[-1].date)
    save_meta(latest_date, meta_path)
    logger.info(f"Arrr! [FSM DEBUG] Fine-tuned model saved to {model_path} with latest_date {latest_date}", context={"model_path": model_path, "latest_date": latest_date})
    return model

# --- Inference Function ---
def predict_next_numbers(draws: List[Draw], seq_len=10, threshold=0.5, model_path=None, hidden_size=64, num_layers=2) -> List[int]:
    from .lstm_model import MODEL_PATH
    if model_path is None:
        model_path = MODEL_PATH
        
    num_numbers = 37
    if len(draws) < seq_len:
        logger.error("Arrr! Not enough draws for sequence prediction!", context={"draws_len": len(draws), "seq_len": seq_len})
        raise ValueError("Not enough draws for sequence prediction")
    model = LottoLSTM(num_numbers=num_numbers, seq_len=seq_len, hidden_size=hidden_size, num_layers=num_layers)
    if not os.path.exists(model_path):
        logger.error(f"Arrr! Model file not found: {model_path}", context={"model_path": model_path})
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

# --- Database Helper ---
def get_latest_draw_date(db: Session):
    if db is None:
        return None
    
    # Import cache service
    from shared.cache_service import get_database_cache
    cache = get_database_cache()
    
    # Generate cache key based on database session info
    # We'll use a simple key since this is a global query
    cache_key = "latest_draw_date"
    
    # Try to get from cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(
            "Arrr! Latest draw date retrieved from cache",
            context={"cached_date": str(cached_result)}
        )
        return cached_result
    
    try:
        from models import Draw
        latest_draw = db.query(Draw).order_by(Draw.date.desc()).first()
        result = latest_draw.date if latest_draw else None
        
        # Cache the result
        if result is not None:
            cache.set(result, cache_key)
            logger.debug(
                "Arrr! Latest draw date cached successfully",
                context={"cached_date": str(result)}
            )
        
        return result
    except Exception as e:
        logger.error(
            "Arrr! Error getting latest draw date",
            context={"error": str(e)}
        )
        return None 