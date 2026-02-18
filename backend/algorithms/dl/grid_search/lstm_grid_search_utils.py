"""Utility functions for LSTM grid search"""
import torch
from shared.logging_service import get_backend_logger

logger = get_backend_logger()


def get_device():
    """Detect and return the best available device (GPU or CPU)"""
    if torch.cuda.is_available():
        device = torch.device('cuda')
        logger.info(
            f"Arrr! [FSM GPU] CUDA available! Using GPU: {torch.cuda.get_device_name(0)}",
            context={"cuda_version": torch.version.cuda, "device_count": torch.cuda.device_count()}
        )
        return device
    else:
        device = torch.device('cpu')
        logger.debug("Arrr! [FSM GPU] CUDA not available, using CPU")
        return device

