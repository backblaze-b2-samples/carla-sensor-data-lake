import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.service.carla_runner import (
    CarlaRunError,
    CarlaUnavailableError,
    run_scenario,
)
from app.service.scenarios import ScenarioNotFoundError, get_scenario
from app.types import EpisodeMetadata

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scenarios/{scenario_id}/run", response_model=EpisodeMetadata)
def run_scenario_endpoint(scenario_id: str):
    """Drive the real CARLA server for a scenario, streaming frames to B2.

    Returns 503 (not 500) with an actionable message when CARLA is not installed
    on this host or its server is unreachable — the guarded, documented handling
    for the platform-restricted `carla` wheel (see service/carla_runner.py). The
    run is synchronous; a production deployment would enqueue it as a job.
    """
    try:
        scenario = get_scenario(scenario_id)
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None

    episode_id = uuid.uuid4().hex[:12]
    try:
        return run_scenario(episode_id, scenario)
    except CarlaUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.detail) from None
    except CarlaRunError as e:
        raise HTTPException(
            status_code=502, detail=f"CARLA run failed mid-capture: {e.detail}"
        ) from None
