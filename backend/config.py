# config.py
# All static (but changeable) settings for the lottery predictor backend
# Praise the FSM for single source of truth!

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_backend_dir():
    """Get the backend directory path dynamically."""
    return Path(__file__).parent

# Base directory paths
BACKEND_DIR = get_backend_dir()
APP_BASE_PATH = Path("/app")
ALGORITHMS_PATH = APP_BASE_PATH / "algorithms"
DL_PATH = ALGORITHMS_PATH / "dl"
MODELS_PATH = DL_PATH / "models"
SEQUENCE_CLASSIFIER_MODEL_DIR = MODELS_PATH
CACHE_PATH = APP_BASE_PATH / "shared" / "cache"
LOGS_PATH = APP_BASE_PATH / "logs"

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/lotto_predictor')

# Cost of a single ticket (per table)
TICKET_COST_PER_TABLE = 2.80  # Change as needed

# Path configurations
# Model file paths
SEQUENCE_CLASSIFIER_MODEL_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model.pt"
SEQUENCE_CLASSIFIER_MODEL_SEQ20_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model_seq20.pt"
SEQUENCE_CLASSIFIER_MODEL_POSITION_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model_position.pt"

# Cache file paths
STRONG_NUMBER_CACHE_PATH = CACHE_PATH / "strong_number_cache.json"

# Log file paths
BACKEND_LOG_PATH = LOGS_PATH / "backend_service" / "backend_service.log"

# Number of combinations to use for analysis/simulation (e.g., in ROI calculations)
NUM_COMBINATIONS_FOR_ANALYSIS = 8

# Number of combinations to recommend to the user for the next draw
NUM_COMBINATIONS_TO_RECOMMEND = 8

# LSTM Model Constants
LOTTO_NUMBERS_COUNT = 37  # Total numbers in the lottery (1-37)
LSTM_DEFAULT_SEQ_LEN = 10  # Default sequence length for LSTM
LSTM_DEFAULT_THRESHOLD = 0.5  # Default prediction threshold
LSTM_GRID_SEARCH_THRESHOLD = 0.2  # Threshold used in grid search
LSTM_GRID_SEARCH_TEST_COUNT = 12  # Number of test draws for grid search evaluation
LSTM_TABLES_PER_DRAW = 8  # Number of ticket combinations per draw in evaluation

# Prize table (average, adjust as needed)
# Key: (hits, strong_hit) -> value: average prize in NIS
PRIZE_TABLE = {
    (6, True): 6_000_000,   # 6 correct + strong
    (6, False): 250_000,    # 6 correct, no strong
    (5, True): 20_000,      # 5 correct + strong
    (5, False): 1_500,      # 5 correct, no strong
    (4, True): 500,         # 4 correct + strong
    (4, False): 60,         # 4 correct, no strong
    (3, True): 30,          # 3 correct + strong
    (3, False): 0,          # 3 correct, no strong
    (2, True): 10,          # 2 correct + strong
    (2, False): 0,          # 2 correct, no strong
}

# Logging configuration
LOG_ROTATION_MAX_BYTES = int(9.5 * 1024 * 1024)  # 9.5MB
LOG_ROTATION_BACKUP_COUNT = 100  # Keep up to 100 backup files
LOG_RETENTION_DAYS = 14  # Keep logs for 14 days before cleanup

# Add more config values as needed, matey! 