import torch
import torch.nn as nn
import json
import os
from pathlib import Path
from typing import List
from models import Draw

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from config import (
    SEQUENCE_CLASSIFIER_MODEL_PATH,
    SEQUENCE_CLASSIFIER_MODEL_DIR,
    LOTTO_NUMBERS_COUNT
)

logger = get_backend_logger()

MODEL_PATH = str(SEQUENCE_CLASSIFIER_MODEL_PATH)
META_PATH = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_meta.json')

# --- Model Definition ---
class LottoLSTM(nn.Module):
    def __init__(self, num_numbers=LOTTO_NUMBERS_COUNT, seq_len=10, hidden_size=64, num_layers=2):
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
def draws_to_sequences(draws: List[Draw], seq_len=10, num_numbers=LOTTO_NUMBERS_COUNT):
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