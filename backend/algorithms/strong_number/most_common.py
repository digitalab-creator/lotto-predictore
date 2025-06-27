from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm
import sys
import os

# Import cache service from shared directory
from shared.cache_service import get_strong_number_cache
from shared.logging_service import get_backend_logger

@register_strong_algorithm
class MostCommonStrongNumber(StrongNumberAlgorithm):
    version = "most_common"
    description = "Pick the most common strong number from history."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        logger = get_backend_logger()
        
        logger.debug(
            f"MostCommonStrongNumber predict called with {len(draws)} draws",
            context={
                "num_draws": len(draws),
                "first_3_draws": draws[:3] if draws else []
            }
        )
        
        # Get cache service
        cache = get_strong_number_cache()
        
        # Generate cache key from draws data
        if not draws:
            cache_key_data = "empty_draws"
        else:
            # Use first draw date, last draw date, and total count for cache key
            first_date = draws[0].date.isoformat()
            last_date = draws[-1].date.isoformat()
            cache_key_data = f"{first_date}_{last_date}_{len(draws)}"
        
        # Try to get from cache
        counter = cache.get(cache_key_data)
        
        if counter is None:
            # Calculate and cache
            strong_numbers = [draw.strong_number for draw in draws]
            # Debug: log the types of strong_number values
            strong_number_types = [(num, type(num)) for num in strong_numbers[:5]]
            logger.debug(
                f"Strong number types: {strong_number_types}",
                context={
                    "strong_number_types": strong_number_types,
                    "strong_numbers_sample": strong_numbers[:5]
                }
            )
            
            counter = Counter(strong_numbers)
            cache.set(counter, cache_key_data)
            
            logger.info(
                f"Calculated and cached new counter: {dict(counter)}",
                context={
                    "cache_key": cache_key_data,
                    "counter": dict(counter)
                }
            )
        else:
            logger.debug(
                f"Using cached counter for strong number calculation",
                context={"cache_key": cache_key_data}
            )
        
        if not counter:
            logger.warning(
                "Counter is empty, fallback to 1",
                context={"cache_key": cache_key_data}
            )
            strong_number = 1  # fallback
        else:
            candidates = [num for num, _ in counter.most_common()]
            logger.info(
                f"Found candidates from counter: {candidates}",
                context={
                    "candidates": candidates,
                    "counter": dict(counter)
                }
            )
            strong_number = candidates[0]
        
        self._validate_strong_number(strong_number)
        return strong_number 