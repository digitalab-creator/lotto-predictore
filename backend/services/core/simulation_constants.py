"""
Constants for simulation engine.
Praisin' the FSM! 🍝⚓
"""

# Thread pool configuration
MAX_WORKERS = 4  # Match CPU count for parallel processing

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
MAX_RETRY_TIME_SECONDS = 300
DEFAULT_BACKOFF_BASE = 2  # Exponential backoff base

# Database timeout configuration
LSTM_TIMEOUT_SECONDS = 300  # 5 minutes for LSTM models
DEFAULT_TIMEOUT_SECONDS = 30  # Default timeout

# Minimum data requirements
MIN_TRAINING_DRAWS = 10  # Minimum draws needed for training

