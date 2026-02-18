import torch
import numpy as np
import random
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Draw
from pathlib import Path

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import Algorithm, register_algorithm
from collections import Counter
from config import (
    SEQUENCE_CLASSIFIER_MODEL_PATH,
    SEQUENCE_CLASSIFIER_MODEL_SEQ20_PATH,
    SEQUENCE_CLASSIFIER_MODEL_POSITION_PATH,
    SEQUENCE_CLASSIFIER_MODEL_DIR,
    NUM_COMBINATIONS_TO_RECOMMEND,
    LOTTO_NUMBERS_COUNT,
    LSTM_DEFAULT_SEQ_LEN,
    LSTM_DEFAULT_THRESHOLD,
    LSTM_GRID_SEARCH_THRESHOLD
)
from ..core.lstm_model import load_meta
from ..core.lstm_training import train_lotto_lstm, finetune_lotto_lstm, predict_next_numbers, get_latest_draw_date

logger = get_backend_logger()


def _train_or_load_model(
    draws: List[Draw],
    model_path: str,
    meta_path: str,
    seq_len: int,
    epochs: int,
    lr: float,
    batch_size: int,
    finetune_epochs: int = None,
    db: Session = None
):
    """
    Helper function to train, finetune, or load an LSTM model.
    Returns True if model is ready, False otherwise.
    """
    latest_db_date = None
    if db is not None:
        latest_db_date = get_latest_draw_date(db)
    
    meta = load_meta(meta_path)
    meta_date = meta["latest_date"] if meta else None
    
    if not os.path.exists(model_path) or not meta_date:
        model = train_lotto_lstm(
            draws, 
            seq_len=seq_len, 
            epochs=epochs, 
            lr=lr, 
            batch_size=batch_size, 
            model_path=model_path, 
            meta_path=meta_path
        )
        if model is None or not os.path.exists(model_path):
            return False
    elif latest_db_date and str(latest_db_date) > meta_date:
        finetune_epochs = finetune_epochs or (epochs // 3)
        model = finetune_lotto_lstm(
            draws, 
            seq_len=seq_len, 
            epochs=finetune_epochs, 
            lr=lr/2, 
            batch_size=batch_size//2, 
            model_path=model_path, 
            meta_path=meta_path
        )
        if model is None:
            return False
    
    return True


def _generate_combos(
    draws: List[Draw],
    model_path: str,
    seq_len: int,
    version: str,
    top_n: int,
    num_for_analysis: int,
    num_to_recommend: int,
    threshold: float = LSTM_DEFAULT_THRESHOLD,
    hidden_size: int = 64,
    num_layers: int = 2,
    repeat_count: int = None
) -> List[Dict[str, Any]]:
    """
    Helper function to generate prediction combinations.
    Returns list of combo dictionaries.
    """
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
        logger.error(f"Arrr! LSTM prediction failed: {e}")
        return []
    
    strong_counter = Counter(draw.strong_number for draw in draws)
    top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
    
    params = {
        "seq_len": seq_len,
        "model_version": version,
        "top_n": top_n,
        "num_for_analysis": num_for_analysis,
        "num_to_recommend": num_to_recommend
    }
    
    combo = {"numbers": numbers, "strong": top_strong, "params": params}
    
    if repeat_count is None:
        repeat_count = num_to_recommend or NUM_COMBINATIONS_TO_RECOMMEND
    
    return [combo] * repeat_count if combo else []


@register_algorithm
class SequenceClassificationLSTMAlgorithm(Algorithm):
    version = "sequence_lstm_classifier"
    description = "Sequence classification LSTM model. Learns temporal patterns."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db=None) -> List[Dict[str, Any]]:
        try:
            logger.info("Arrr! LSTM run method called!")
            seq_len = LSTM_DEFAULT_SEQ_LEN
            model_path = str(SEQUENCE_CLASSIFIER_MODEL_PATH)
            meta_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_meta.json')
            
            # Special handling for default model (uses default paths)
            latest_db_date = None
            if db is not None:
                latest_db_date = get_latest_draw_date(db)
            meta = load_meta()
            meta_date = meta["latest_date"] if meta else None
            logger.debug(f"Arrr! [FSM DEBUG] Latest DB date: {latest_db_date}, Meta date: {meta_date}", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            
            if not os.path.exists(model_path) or not meta_date:
                logger.info("Arrr! [FSM DEBUG] No model or meta found, trainin' from scratch! Praisin' the FSM!")
                model = train_lotto_lstm(draws, seq_len=seq_len)
                if model is None or not os.path.exists(model_path):
                    logger.error("Arrr! LSTM training returned None!")
                    return []
            elif latest_db_date and str(latest_db_date) > meta_date:
                logger.info(f"Arrr! [FSM DEBUG] DB newer than model, fine-tunin'! Praisin' the FSM!", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
                model = finetune_lotto_lstm(draws, seq_len=seq_len)
                if model is None:
                    logger.error("Arrr! LSTM fine-tuning returned None!")
                    return []
            else:
                logger.info(f"Arrr! [FSM DEBUG] Model up-to-date, runnin' inference! Praisin' the FSM!", context={"latest_db_date": latest_db_date, "meta_date": meta_date})
            
            return _generate_combos(
                draws=draws,
                model_path=model_path,
                seq_len=seq_len,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_H32_L1_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h32_l1"
    description = "LSTM: hidden_size=32, num_layers=1, seq_len=10, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            logger.info("Arrr! LSTM H32_L1 run method called!")
            seq_len = LSTM_DEFAULT_SEQ_LEN
            hidden_size = 32
            num_layers = 1
            lr = 0.001
            batch_size = 16
            model_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_h32_l1.pt')
            meta_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_h32_l1_meta.json')
            
            if not _train_or_load_model(draws, model_path, meta_path, seq_len, 30, lr, batch_size, 10, db):
                return []
            
            return _generate_combos(
                draws=draws,
                model_path=model_path,
                seq_len=seq_len,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                hidden_size=hidden_size,
                num_layers=num_layers
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM H32_L1 run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_H128_L2_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2"
    description = "LSTM: hidden_size=128, num_layers=2, seq_len=10, lr=0.0005, batch_size=8. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            logger.info("Arrr! LSTM H128_L2 run method called!")
            seq_len = LSTM_DEFAULT_SEQ_LEN
            hidden_size = 128
            num_layers = 2
            lr = 0.0005
            batch_size = 8
            model_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_h128_l2.pt')
            meta_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_h128_l2_meta.json')
            
            if not _train_or_load_model(draws, model_path, meta_path, seq_len, 40, lr, batch_size, 15, db):
                return []
            
            return _generate_combos(
                draws=draws,
                model_path=model_path,
                seq_len=seq_len,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                hidden_size=hidden_size,
                num_layers=num_layers
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM H128_L2 run method failed: {e}")
            return []

@register_algorithm
class SequenceClassificationLSTM_SEQ20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_seq20"
    description = "LSTM: hidden_size=64, num_layers=2, seq_len=20, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None) -> List[Dict[str, Any]]:
        try:
            logger.info("Arrr! LSTM SEQ20 run method called!")
            seq_len = 20
            hidden_size = 64
            num_layers = 2
            lr = 0.001
            batch_size = 16
            model_path = str(SEQUENCE_CLASSIFIER_MODEL_SEQ20_PATH)
            meta_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / 'sequence_classifier_model_seq20_meta.json')
            
            if not _train_or_load_model(draws, model_path, meta_path, seq_len, 30, lr, batch_size, 10, db):
                return []
            
            return _generate_combos(
                draws=draws,
                model_path=model_path,
                seq_len=seq_len,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                hidden_size=hidden_size,
                num_layers=num_layers,
                threshold=LSTM_DEFAULT_THRESHOLD
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM SEQ20 run method failed: {e}")
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
            logger.info("Arrr! LSTM H128_L2_E20 (inference-only, single test draw) run method called!")
            seq_len = 10
            hidden_size = 128
            num_layers = 2
            lr = 0.001
            batch_size = 8
            epochs = 20
            threshold = LSTM_GRID_SEARCH_THRESHOLD
            model_path = str(SEQUENCE_CLASSIFIER_MODEL_POSITION_PATH)
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
                    logger.error(f"Arrr! [FSM DEBUG] Prediction failed: {e}")
                    numbers = []
                strong_counter = Counter(draw.strong_number for draw in draws)
                top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
                combos.append({"numbers": numbers, "strong": top_strong, "params": static_params.copy()})
            return combos
        except Exception as e:
            logger.error(f"Arrr! LSTM H128_L2_E20 (inference-only, single test draw) run method failed: {e}")
            return [] 