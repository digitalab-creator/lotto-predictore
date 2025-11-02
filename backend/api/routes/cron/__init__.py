# Cron routes package for the Lotto Predictor Backend API
# Praise the FSM for clean separation of concerns!

from .combinations import (
    optimized_combinations_router,
    fast_combinations_router,
    standard_combinations_router,
    grid_search_analysis_router
)
from .draw_fetching import router as draw_fetching_router
from .model_tables import router as model_tables_router
from .status import router as status_router

# Export all routers for easy inclusion
__all__ = [
    'optimized_combinations_router',
    'fast_combinations_router',
    'standard_combinations_router',
    'grid_search_analysis_router',
    'draw_fetching_router', 
    'model_tables_router',
    'status_router'
] 