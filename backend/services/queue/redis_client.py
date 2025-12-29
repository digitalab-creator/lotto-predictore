"""Redis connection manager for queue system"""
import os
import redis
from typing import Optional
from logger import logger

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            _redis_client.ping()
            logger.info("Arrr! Redis connection established, praisin' the FSM!", context={"redis_url": redis_url})
        except Exception as e:
            logger.error(
                "Arrr! Failed to connect to Redis!",
                context={"error": str(e), "redis_url": redis_url}
            )
            raise
    
    return _redis_client


def close_redis_client():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Arrr! Redis connection closed!")


