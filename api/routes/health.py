"""
Health route — GET /api/health
Returns system status, uptime, model info, and supported chains.
"""
import time
from fastapi import APIRouter
from api.schemas import HealthResponse

router = APIRouter()

# Module-level state
PREDICTION_COUNTER = 0
START_TIME = time.time()


def increment_prediction_counter():
    global PREDICTION_COUNTER
    PREDICTION_COUNTER += 1


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Returns platform status, uptime, model registry, and supported chains.",
)
def get_health():
    from src.utils import load_yaml
    chains = list(load_yaml("config/chains.yaml").keys())

    return HealthResponse(
        status="healthy",
        timestamp=int(time.time()),
        version="2.0.0",
        predictions_served=PREDICTION_COUNTER,
        active_models=[
            "RandomForest / XGBoost Tabular Ensemble",
            "SimpleGNN (GraphSAGE) Network Risk",
            "Autoencoder Anomaly Detector",
        ],
        chains_supported=chains,
        uptime_seconds=round(time.time() - START_TIME, 1),
    )
