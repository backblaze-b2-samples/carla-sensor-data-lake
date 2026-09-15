import logging

# Sync `def` handlers on purpose: the call chain is blocking boto3, and Starlette
# runs sync handlers in its threadpool (see runtime/files.py for the rationale).
from fastapi import APIRouter, HTTPException

from app.service.scenarios import (
    ScenarioNotFoundError,
    create_scenario,
    delete_scenario,
    get_scenario,
    list_all_scenarios,
    update_scenario,
)
from app.types import Scenario, ScenarioInput

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the file routes, these are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md). Scope reads and
# writes to a per-user prefix before adding auth to a multi-tenant clone.


@router.get("/scenarios", response_model=list[Scenario])
def list_scenarios_endpoint():
    return list_all_scenarios()


@router.post("/scenarios", response_model=Scenario, status_code=201)
def create_scenario_endpoint(payload: ScenarioInput):
    try:
        return create_scenario(payload)
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to store scenario") from None


@router.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario_endpoint(scenario_id: str):
    try:
        return get_scenario(scenario_id)
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.put("/scenarios/{scenario_id}", response_model=Scenario)
def update_scenario_endpoint(scenario_id: str, payload: ScenarioInput):
    try:
        return update_scenario(scenario_id, payload)
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to store scenario") from None


@router.delete("/scenarios/{scenario_id}")
def delete_scenario_endpoint(scenario_id: str):
    try:
        delete_scenario(scenario_id)
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete scenario") from None
    return {"deleted": True, "id": scenario_id}
