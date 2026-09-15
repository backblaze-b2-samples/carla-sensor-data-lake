"""Scenario CRUD endpoint tests (repo boundary mocked — hermetic)."""

import pytest

from app.service import scenarios as svc

VALID = {
    "name": "Test scenario",
    "description": "A scenario",
    "town": "Town10HD",
    "weather": "ClearNoon",
    "traffic_density": "medium",
    "fps": 10,
    "frame_count": 50,
    "sensors": ["vehicle_state", "rgb", "lidar"],
}
_NOW = "2026-01-01T00:00:00+00:00"


def _stored(**overrides) -> dict:
    return {**VALID, "id": "abc123", "created_at": _NOW, "updated_at": _NOW, **overrides}


@pytest.mark.asyncio
async def test_create_scenario(client, monkeypatch):
    saved: dict = {}
    monkeypatch.setattr(svc, "repo_put_scenario", lambda sid, data: saved.update({sid: data}))

    response = await client.post("/scenarios", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test scenario"
    assert body["id"]
    # Sensors are normalised to the canonical rig order regardless of input order.
    assert body["sensors"] == ["rgb", "lidar", "vehicle_state"]
    assert saved  # actually persisted through the repo


@pytest.mark.asyncio
async def test_create_scenario_rejects_unknown_town(client):
    response = await client.post("/scenarios", json={**VALID, "town": "Atlantis"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_scenario_rejects_unknown_sensor(client):
    response = await client.post("/scenarios", json={**VALID, "sensors": ["radar"]})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_scenarios(client, monkeypatch):
    monkeypatch.setattr(svc, "repo_list_scenarios", lambda: [_stored()])
    response = await client.get("/scenarios")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "abc123"


@pytest.mark.asyncio
async def test_get_scenario_404(client, monkeypatch):
    monkeypatch.setattr(svc, "repo_get_scenario", lambda sid: None)
    response = await client.get("/scenarios/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_scenario_preserves_created_at(client, monkeypatch):
    monkeypatch.setattr(svc, "repo_get_scenario", lambda sid: _stored())
    monkeypatch.setattr(svc, "repo_put_scenario", lambda sid, data: None)
    response = await client.put("/scenarios/abc123", json={**VALID, "name": "Renamed"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["created_at"].startswith("2026-01-01")


@pytest.mark.asyncio
async def test_delete_scenario(client, monkeypatch):
    monkeypatch.setattr(svc, "repo_get_scenario", lambda sid: _stored())
    monkeypatch.setattr(svc, "repo_delete_scenario", lambda sid: None)
    response = await client.delete("/scenarios/abc123")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "id": "abc123"}
