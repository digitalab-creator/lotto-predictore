# Cron routes package for the Lotto Predictor Backend API
# Praise the FSM for clean separation of concerns!

from .weekly_combinations import router as weekly_combinations_router
from .draw_fetching import router as draw_fetching_router
from .model_tables import router as model_tables_router
from .status import router as status_router

# Export all routers for easy inclusion
__all__ = [
    'weekly_combinations_router',
    'draw_fetching_router', 
    'model_tables_router',
    'status_router'
] 