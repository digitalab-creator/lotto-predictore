"""
Base combination generator - shared logic for all weekly combination generation endpoints.
Praise the FSM for clean, shared code!
"""

from sqlalchemy.orm import Session
from services.core.cron_tracker import CronTracker
from models import Draw, Prediction, Model, GeneratedCombination
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from utils.model_utils import normalize_model_name, denormalize_model_name
from logger import logger
from datetime import datetime
import time
from typing import List, Dict, Any, Tuple, Optional


def get_db_session():
    """Get database session generator"""
    from db.base import SessionLocal
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    return next(get_db())


def load_draws_with_filter(db: Session) -> Tuple[List[Draw], int, float]:
    """
    Load draws filtering out strong_number == 8.
    
    Returns:
        Tuple of (draws, filtered_count, load_time)
    """
    draws_start = time.time()
    draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
    filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
    draws_time = time.time() - draws_start
    
    return draws, filtered_count, draws_time


def generate_combinations(
    db: Session,
    main_algo_name: str,
    strong_algo_name: str,
    draws: List[Draw],
    top_n: int,
    num_to_recommend: int,
    version: str,
    cron_job: Any,
    start_time: float
) -> Tuple[List[dict], Any, float]:
    """
    Generate combinations using specified algorithms.
    
    Returns:
        Tuple of (combos, strong_number, generation_time)
    """
    generation_start = time.time()
    main_algo_cls = ALGORITHM_REGISTRY[main_algo_name]
    strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_algo_name]
    
    all_draws = draws
    combos = main_algo_cls().run(all_draws, top_n=top_n, num_to_recommend=num_to_recommend)
    strong_algo = strong_algo_cls()
    strong_number = strong_algo.predict(all_draws)
    
    generation_time = time.time() - generation_start
    
    return combos, strong_number, generation_time


def validate_combos_result(combos: Any, main_algo_name: str, version: str, cron_job: Any, start_time: float, optimized_params: Optional[Dict] = None) -> Optional[str]:
    """
    Validate algorithm result and return error message if invalid.
    
    Returns:
        Error message string if invalid, None if valid
    """
    # Optimized version has different validation
    if version == "optimized_weekly_generation":
        if not isinstance(combos, list) or not combos:
            error_msg = f"Algorithm {main_algo_name} returned invalid result"
            logger.error(
                "Arrr! Algorithm returned invalid result in optimized mode!",
                context={
                    "algorithm": main_algo_name,
                    "result_type": type(combos),
                    "result_length": len(combos) if isinstance(combos, list) else "N/A",
                    "optimized_params": optimized_params
                }
            )
            return error_msg
    else:
        # Standard and Fast versions have two-step validation
        if not isinstance(combos, list):
            error_msg = f"Algorithm {main_algo_name} returned invalid result type: {type(combos)}"
            logger.error(
                "Arrr! Algorithm returned invalid result type!",
                context={
                    "algorithm": main_algo_name,
                    "result_type": type(combos),
                    "result_value": str(combos)[:200],
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            return error_msg
        
        if not combos:
            error_msg = f"Algorithm {main_algo_name} returned empty result"
            logger.error(
                "Arrr! Algorithm returned empty result!",
                context={
                    "algorithm": main_algo_name,
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            return error_msg
    
    return None


def get_model_objects(db: Session, main_algo_name: str, strong_algo_name: str) -> Tuple[Optional[Model], Optional[Model]]:
    """Get main and strong model objects from database"""
    main_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(main_algo_name), 'main')).first()
    strong_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(strong_algo_name), 'strong')).first()
    return main_model, strong_model


def store_combinations_in_db(
    db: Session,
    combos: List[dict],
    strong_number: Any,
    prediction_id: int,
    version: str,
    now: datetime
) -> int:
    """
    Store combinations in database.
    
    Returns:
        Number of valid combinations processed
    """
    valid_combos_processed = 0
    for idx, combo in enumerate(combos):
        # Validate combo format and extract numbers safely
        if not isinstance(combo, dict):
            logger.error(
                f"Arrr! Invalid combo format at index {idx}: not a dict",
                context={
                    "combo_type": type(combo),
                    "combo_value": str(combo)[:100],
                    "prediction_id": prediction_id
                }
            )
            continue
        
        # Try to extract numbers from different possible formats
        numbers = None
        if "numbers" in combo:
            numbers = combo["numbers"]
        elif "strong" in combo and isinstance(combo.get("strong"), (list, tuple)):
            numbers = combo["strong"]
        else:
            logger.error(
                f"Arrr! Combo at index {idx} missing 'numbers' key",
                context={
                    "combo_keys": list(combo.keys()),
                    "combo_value": str(combo)[:100],
                    "prediction_id": prediction_id
                }
            )
            continue
        
        # Validate numbers format
        if not isinstance(numbers, (list, tuple)) or len(numbers) != 6:
            logger.error(
                f"Arrr! Invalid numbers format at index {idx}",
                context={
                    "numbers_type": type(numbers),
                    "numbers_value": numbers,
                    "numbers_length": len(numbers) if isinstance(numbers, (list, tuple)) else "N/A",
                    "prediction_id": prediction_id
                }
            )
            continue
        
        # Ensure all numbers are integers
        try:
            numbers = [int(n) for n in numbers]
        except (ValueError, TypeError) as e:
            logger.error(
                f"Arrr! Error converting numbers to int at index {idx}",
                context={
                    "error": str(e),
                    "numbers": numbers,
                    "prediction_id": prediction_id
                }
            )
            continue
        
        # Check for duplicate numbers within the combination
        if len(numbers) != len(set(numbers)):
            logger.warning(
                f"Arrr! Skipping combo at index {idx} - contains duplicate numbers",
                context={
                    "numbers": numbers,
                    "duplicates": [n for n in numbers if numbers.count(n) > 1],
                    "prediction_id": prediction_id
                }
            )
            continue
        
        generated = GeneratedCombination(
            prediction_id=prediction_id,
            numbers=numbers,
            strong_number=strong_number,
            position=valid_combos_processed+1,
            version=version,
            generated_at=now
        )
        db.add(generated)
        valid_combos_processed += 1
        
        # Log message varies by version
        combo_msg = f"Stored {'OPTIMIZED' if version == 'optimized_weekly_generation' else 'FAST' if version == 'fast_weekly_generation' else ''} combo {valid_combos_processed}: {numbers} + {strong_number}".strip()
        
        logger.info(
            combo_msg,
            context={
                "prediction_id": prediction_id,
                "numbers": numbers,
                "strong_number": strong_number,
                "position": valid_combos_processed
            }
        )
    
    return valid_combos_processed

