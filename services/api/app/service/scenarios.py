"""Scenario CRUD business logic. B2 is the sole store (repo/scenario_store)."""

import logging
import uuid
from datetime import UTC, datetime

from app.repo import (
    delete_scenario as repo_delete_scenario,
)
from app.repo import (
    get_scenario as repo_get_scenario,
)
from app.repo import (
    list_scenarios as repo_list_scenarios,
)
from app.repo import (
    put_scenario as repo_put_scenario,
)
from app.types import Scenario, ScenarioInput

logger = logging.getLogger(__name__)


class ScenarioNotFoundError(Exception):
    def __init__(self, detail: str = "Scenario not found"):
        self.detail = detail
        super().__init__(detail)


def create_scenario(data: ScenarioInput) -> Scenario:
    now = datetime.now(UTC)
    scenario = Scenario(
        id=uuid.uuid4().hex[:12],
        created_at=now,
        updated_at=now,
        **data.model_dump(),
    )
    repo_put_scenario(scenario.id, scenario.model_dump(mode="json"))
    logger.info("Scenario created: id=%s", scenario.id)
    return scenario


def list_all_scenarios() -> list[Scenario]:
    return [Scenario(**raw) for raw in repo_list_scenarios()]


def get_scenario(scenario_id: str) -> Scenario:
    raw = repo_get_scenario(scenario_id)
    if raw is None:
        raise ScenarioNotFoundError()
    return Scenario(**raw)


def update_scenario(scenario_id: str, data: ScenarioInput) -> Scenario:
    existing = repo_get_scenario(scenario_id)
    if existing is None:
        raise ScenarioNotFoundError()
    scenario = Scenario(
        id=scenario_id,
        created_at=existing.get("created_at", datetime.now(UTC)),
        updated_at=datetime.now(UTC),
        **data.model_dump(),
    )
    repo_put_scenario(scenario_id, scenario.model_dump(mode="json"))
    logger.info("Scenario updated: id=%s", scenario_id)
    return scenario


def delete_scenario(scenario_id: str) -> None:
    if repo_get_scenario(scenario_id) is None:
        raise ScenarioNotFoundError()
    repo_delete_scenario(scenario_id)
    logger.info("Scenario deleted: id=%s", scenario_id)
