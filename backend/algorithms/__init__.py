from logger import logger

# Import base registry
from .base import ALGORITHM_REGISTRY, register_algorithm, get_registered_algorithms

# Import all algorithm modules
from . import statistical
from . import strong_number
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
