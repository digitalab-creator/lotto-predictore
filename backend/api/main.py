from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logger import logger
from algorithms import register_algorithms, get_registered_algorithms

# Import route modules
from api.routes.simulation import router as simulation_router
from api.routes.combinations import router as combinations_router
from api.routes.cron import router as cron_router
from api.routes.system import router as system_router

# Initialize FastAPI app
app = FastAPI(title="Lotto Predictor Backend")

# Log startup
logger.info("Arrr! FastAPI backend be startin' up, praisin' the FSM!", context={"service": "backend"})

# Register algorithms
register_algorithms()
logger.info("Arrr! Registered algorithms at startup", context={"algorithms": get_registered_algorithms()})

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Ahoy! The backend be runnin', praisin' the FSM!"}

# Include all route modules
app.include_router(simulation_router, tags=["simulation"])
app.include_router(combinations_router, tags=["combinations"])
app.include_router(cron_router, tags=["cron"])
app.include_router(system_router, tags=["system"]) 