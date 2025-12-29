"""
Cache management for grid search service using Redis.
Praisin' the FSM! 🍝⚓
"""
import pickle
import hashlib
from typing import List, Dict, Any, Optional
from models import Draw
from shared.logging_service import get_backend_logger

# Set up backend path
from utils.path_setup import setup_backend_path
setup_backend_path()

logger = get_backend_logger()

# Redis key prefix for grid search cache
CACHE_KEY_PREFIX = "grid_search:"
# Default TTL: 7 days (in seconds)
DEFAULT_TTL = 7 * 24 * 60 * 60


class GridSearchCache:
    """Handles caching of grid search results using Redis"""
    
    def __init__(self, ttl: int = DEFAULT_TTL):
        """
        Initialize grid search cache
        
        Args:
            ttl: Time to live for cache entries in seconds (default: 7 days)
        """
        self.ttl = ttl
        self._redis = None
    
    @property
    def redis(self):
        """Lazy load Redis client"""
        if self._redis is None:
            # Get Redis client without decode_responses for binary pickle data
            import os
            import redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            # Use decode_responses=False for binary data (pickle)
            self._redis = redis.from_url(redis_url, decode_responses=False)
        return self._redis
    
    def get_cache_key(self, draws: List[Draw], grid_params: List[Dict[str, Any]]) -> str:
        """Generate cache key for grid search results"""
        # Create hash from draw dates and grid parameters
        draw_dates = ','.join(str(d.date) for d in draws[-50:])  # Use last 50 draws for cache key
        
        # Validate grid_params format and convert to sorted string for consistent hashing
        validated_params = []
        for idx, p in enumerate(grid_params):
            if not isinstance(p, dict):
                error_msg = (
                    f"Invalid grid_params format at index {idx}: expected dict, got {type(p).__name__}. "
                    f"Value: {str(p)[:200]}. This indicates a bug in _create_grid_parameters."
                )
                logger.error(
                    "Arrr! Invalid grid_params format in _get_cache_key!",
                    context={
                        "index": idx,
                        "expected_type": "dict",
                        "actual_type": type(p).__name__,
                        "value": str(p)[:200],
                        "grid_params_length": len(grid_params)
                    }
                )
                raise ValueError(error_msg)
            validated_params.append(tuple(sorted(p.items())))
        
        params_str = str(sorted(validated_params))
        key_string = f"{draw_dates}_{params_str}"
        cache_key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{CACHE_KEY_PREFIX}{cache_key_hash}"
    
    def load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load grid search results from Redis cache"""
        try:
            cached_data_bytes = self.redis.get(cache_key)
            if cached_data_bytes is None:
                return None
            
            cached_data = pickle.loads(cached_data_bytes)
            
            # Handle old cache format (list) - invalidate it
            if isinstance(cached_data, list):
                logger.warning(
                    "Arrr! Found old cache format (list), invalidating cache",
                    context={"cache_key": cache_key}
                )
                self.redis.delete(cache_key)
                return None
            
            # Validate cache format
            if not isinstance(cached_data, dict) or 'best_parameters' not in cached_data:
                logger.warning(
                    "Arrr! Invalid cache format, invalidating cache",
                    context={"cache_key": cache_key, "cache_type": type(cached_data).__name__}
                )
                self.redis.delete(cache_key)
                return None
            
            logger.info(
                "Arrr! Loaded grid search results from Redis cache, praisin' the FSM!",
                context={
                    "cache_key": cache_key,
                    "cached_results": len(cached_data.get('all_results', []))
                }
            )
            return cached_data
        except Exception as e:
            logger.warning(
                "Arrr! Failed to load from Redis cache, will recompute",
                context={"cache_key": cache_key, "error": str(e)}
            )
            return None
    
    def save_to_cache(self, cache_key: str, results: Dict[str, Any]):
        """Save grid search results to Redis cache"""
        try:
            cached_data_bytes = pickle.dumps(results)
            self.redis.setex(cache_key, self.ttl, cached_data_bytes)
            logger.info(
                "Arrr! Saved grid search results to Redis cache, praisin' the FSM!",
                context={
                    "cache_key": cache_key,
                    "results_count": len(results.get('all_results', [])),
                    "ttl_seconds": self.ttl
                }
            )
        except Exception as e:
            logger.error(
                "Arrr! Failed to save to Redis cache",
                context={"cache_key": cache_key, "error": str(e)}
            )

