"""Simulation-run endpoint tests.

The key regression: on a host without the platform-restricted `carla` wheel (the
macOS/Python-3.12 dev machine and CI), POST /scenarios/{id}/run must return a
clear 503 — never a 500 and never a silent fake. `carla` is not installed in the
test venv, so `carla_runner._import_carla()` raises `CarlaUnavailableError`, which
the router maps to 503 before any B2 or network call happens.
"""

import pytest

from app.service import scenarios as scen_svc

RAW = {
    "id": "abc123",
    "name": "Test scenario",
    "description": "",
    "town": "Town10HD",
    "weather": "ClearNoon",
    "traffic_density": "medium",
    "fps": 10,
    "frame_count": 10,
    "sensors": ["rgb"],
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_run_without_carla_returns_503_not_500(client, monkeypatch):
    monkeypatch.setattr(scen_svc, "repo_get_scenario", lambda sid: RAW)
    response = await client.post("/scenarios/abc123/run")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "CARLA" in detail
    assert "supported" in detail.lower() or "install" in detail.lower()


@pytest.mark.asyncio
async def test_run_missing_scenario_404(client, monkeypatch):
    monkeypatch.setattr(scen_svc, "repo_get_scenario", lambda sid: None)
    response = await client.post("/scenarios/missing/run")
    assert response.status_code == 404
