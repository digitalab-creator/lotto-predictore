# Combinations module - all weekly combination generation endpoints
# Praise the FSM for clean organization!

from .optimized_combinations import router as optimized_combinations_router
from .fast_combinations import router as fast_combinations_router
from .standard_combinations import router as standard_combinations_router
from .grid_search_analysis_route import router as grid_search_analysis_router

__all__ = [
    'optimized_combinations_router',
    'fast_combinations_router',
    'standard_combinations_router',
    'grid_search_analysis_router'
]

