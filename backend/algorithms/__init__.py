from logger import logger

# Import base registry
from .base import ALGORITHM_REGISTRY, register_algorithm, get_registered_algorithms

# Import all algorithm modules
from . import top_n_frequent
from . import top_n_overall
from . import positionwise_scored
from . import delta_system
from . import repeated_pattern
from . import recency_weighted
from . import random_from_top_pool
from . import balanced_spread
from . import pattern_learning
from . import skip_distance
from . import strong_number
from . import uniform_random
from . import dl

# Try to import DL module, but don't fail if it's not available
try:
    from . import dl
except ImportError as e:
    logger.error(f"Failed to import DL module: {str(e)}", context={"error": str(e)})

def register_algorithms():
    """Register all algorithms with the registry"""
    # All algorithms are registered via decorators when imported
    pass
