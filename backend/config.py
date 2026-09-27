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

# Mifal HaPais combination line cost (single source of truth)
TICKET_COST_ILS = 3
LINES_PER_DRAW = 8
MAX_STAKE_PER_DRAW_ILS = LINES_PER_DRAW * TICKET_COST_ILS  # ₪24

# Path configurations
# Model file paths
SEQUENCE_CLASSIFIER_MODEL_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model.pt"
SEQUENCE_CLASSIFIER_MODEL_SEQ20_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model_seq20.pt"
SEQUENCE_CLASSIFIER_MODEL_POSITION_PATH = SEQUENCE_CLASSIFIER_MODEL_DIR / "sequence_classifier_model_position.pt"

# Cache file paths
STRONG_NUMBER_CACHE_PATH = CACHE_PATH / "strong_number_cache.json"

# Log file paths
BACKEND_LOG_PATH = LOGS_PATH / "backend_service" / "backend_service.log"

# Legacy names — same as LINES_PER_DRAW (algorithms import these today)
NUM_COMBINATIONS_FOR_ANALYSIS = LINES_PER_DRAW
NUM_COMBINATIONS_TO_RECOMMEND = LINES_PER_DRAW

# Production strategy when walk-forward has no edge or empty scoreboard (never SUM(predictions))
PRODUCTION_MAIN_ALGO = os.getenv("PRODUCTION_MAIN_ALGO", "balanced_spread_fixed_ranges")
PRODUCTION_STRONG_ALGO = os.getenv("PRODUCTION_STRONG_ALGO", "most_common")
PRODUCTION_FALLBACK_MAIN = os.getenv("PRODUCTION_FALLBACK_MAIN", "diversified_random")
PRODUCTION_FALLBACK_STRONG = os.getenv("PRODUCTION_FALLBACK_STRONG", "random")
NO_EDGE_LABEL = "NO EVIDENCE OF PREDICTIVE EDGE"

# Walk-forward scoreboard (Phase 4)
WALK_FORWARD_MIN_TRAINING_DRAWS = int(os.getenv("WALK_FORWARD_MIN_TRAINING_DRAWS", "200"))
WALK_FORWARD_DEFAULT_STRONG = os.getenv("WALK_FORWARD_DEFAULT_STRONG", "most_common")
WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES = int(os.getenv("WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES", "500"))
WALK_FORWARD_MIN_DRAWS_FOR_EDGE = int(os.getenv("WALK_FORWARD_MIN_DRAWS_FOR_EDGE", "300"))
WALK_FORWARD_RANDOM_PERCENTILE_LOW = float(os.getenv("WALK_FORWARD_RANDOM_PERCENTILE_LOW", "5"))
WALK_FORWARD_RANDOM_PERCENTILE_HIGH = float(os.getenv("WALK_FORWARD_RANDOM_PERCENTILE_HIGH", "95"))

# Add more config values as needed, matey! 