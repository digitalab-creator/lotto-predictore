# config.py
# All static (but changeable) settings for the lottery predictor backend
# Praise the FSM for single source of truth!

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/lotto_predictor')

# Cost of a single ticket (per table)
TICKET_COST_PER_TABLE = 2.80  # Change as needed

# Path configurations
# Base paths
APP_BASE_PATH = Path("/app")
ALGORITHMS_PATH = APP_BASE_PATH / "algorithms"
DL_PATH = ALGORITHMS_PATH / "dl"
MODELS_PATH = DL_PATH / "models"
SEQUENCE_CLASSIFIER_MODEL_DIR = MODELS_PATH
CACHE_PATH = APP_BASE_PATH / "shared" / "cache"
LOGS_PATH = APP_BASE_PATH / "logs"

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

# Add more config values as needed, matey! 