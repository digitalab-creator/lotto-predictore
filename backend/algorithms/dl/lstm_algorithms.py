import random
from datetime import date
from typing import Any, Dict, List

from models import Draw
from sqlalchemy.orm import Session

from utils.path_setup import setup_backend_path

setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import Algorithm, register_algorithm
from .lstm_run_helpers import (
    build_lstm_portfolio_combos,
    default_strong_from_draws,
    resolve_cutoff,
    train_variant_if_missing,
)

logger = get_backend_logger()


def _run_cutoff_variant(
    draws: List[Draw],
    *,
    profile: str,
    seq_len: int,
    hidden_size: int,
    num_layers: int,
    epochs: int,
    lr: float,
    batch_size: int,
    version: str,
    top_n: int,
    num_for_analysis: int | None,
    num_to_recommend: int | None,
    as_of_date: date | None,
    rng: random.Random | None,
    use_topk: bool = False,
) -> List[Dict[str, Any]]:
    training_cutoff = resolve_cutoff(draws, as_of_date)
    model_path = train_variant_if_missing(
        draws=draws,
        profile=profile,
        training_cutoff=training_cutoff,
        seq_len=seq_len,
        hidden_size=hidden_size,
        num_layers=num_layers,
        epochs=epochs,
        lr=lr,
        batch_size=batch_size,
    )
    params = {
        "seq_len": seq_len,
        "model_version": version,
        "training_cutoff": str(training_cutoff),
        "top_n": top_n,
        "num_for_analysis": num_for_analysis,
        "num_to_recommend": num_to_recommend,
    }
    return build_lstm_portfolio_combos(
        draws,
        model_path=model_path,
        seq_len=seq_len,
        hidden_size=hidden_size,
        num_layers=num_layers,
        num_to_recommend=num_to_recommend,
        rng=rng,
        params=params,
        strong_for_line=lambda _nums: default_strong_from_draws(draws),
        use_topk=use_topk,
    )


@register_algorithm
class SequenceClassificationLSTMAlgorithm(Algorithm):
    version = "sequence_lstm_classifier"
    description = "Sequence classification LSTM model. Learns temporal patterns."

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = None,
        db=None,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            logger.info("Arrr! LSTM run method called!")
            return _run_cutoff_variant(
                draws,
                profile="sequence_classifier_model",
                seq_len=10,
                hidden_size=64,
                num_layers=2,
                epochs=30,
                lr=0.001,
                batch_size=16,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                as_of_date=as_of_date,
                rng=rng,
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM run method failed: {e}")
            return []


@register_algorithm
class SequenceClassificationLSTM_H32_L1_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h32_l1"
    description = "LSTM: hidden_size=32, num_layers=1, seq_len=10, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = None,
        db: Session = None,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            return _run_cutoff_variant(
                draws,
                profile="sequence_classifier_model_h32_l1",
                seq_len=10,
                hidden_size=32,
                num_layers=1,
                epochs=30,
                lr=0.001,
                batch_size=16,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                as_of_date=as_of_date,
                rng=rng,
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM H32_L1 run method failed: {e}")
            return []


@register_algorithm
class SequenceClassificationLSTM_H128_L2_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2"
    description = "LSTM: hidden_size=128, num_layers=2, seq_len=10, lr=0.0005, batch_size=8. Praisin' the FSM!"

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = None,
        db: Session = None,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            return _run_cutoff_variant(
                draws,
                profile="sequence_classifier_model_h128_l2",
                seq_len=10,
                hidden_size=128,
                num_layers=2,
                epochs=40,
                lr=0.0005,
                batch_size=8,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                as_of_date=as_of_date,
                rng=rng,
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM H128_L2 run method failed: {e}")
            return []


@register_algorithm
class SequenceClassificationLSTM_SEQ20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_seq20"
    description = "LSTM: hidden_size=64, num_layers=2, seq_len=20, lr=0.001, batch_size=16. Praisin' the FSM!"

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = None,
        db: Session = None,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            return _run_cutoff_variant(
                draws,
                profile="sequence_classifier_model_seq20",
                seq_len=20,
                hidden_size=64,
                num_layers=2,
                epochs=30,
                lr=0.001,
                batch_size=16,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                as_of_date=as_of_date,
                rng=rng,
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM SEQ20 run method failed: {e}")
            return []


@register_algorithm
class SequenceClassificationLSTM_H128_L2_E20_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_h128_l2_e20"
    description = (
        "LSTM: hidden_size=128, num_layers=2, seq_len=10, inference with diversified thresholds. "
        "Praisin' the FSM!"
    )

    def run(
        self,
        draws: List[Draw],
        top_n: int = 3,
        num_for_analysis: int = None,
        num_to_recommend: int = 8,
        db: Session = None,
        as_of_date: date | None = None,
        rng: random.Random | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            return _run_cutoff_variant(
                draws,
                profile="sequence_classifier_model_position",
                seq_len=10,
                hidden_size=128,
                num_layers=2,
                epochs=20,
                lr=0.001,
                batch_size=8,
                version=self.version,
                top_n=top_n,
                num_for_analysis=num_for_analysis,
                num_to_recommend=num_to_recommend,
                as_of_date=as_of_date,
                rng=rng,
            )
        except Exception as e:
            logger.error(f"Arrr! LSTM H128_L2_E20 run method failed: {e}")
            return []
