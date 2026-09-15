"""Episode list/detail/delete endpoint tests (repo boundary mocked)."""

from datetime import UTC, datetime

import pytest

from app.service import episodes as svc

META = {
    "id": "ep1",
    "scenario_id": "sc1",
    "scenario_name": "Highway rush hour",
    "town": "Town10HD",
    "weather": "ClearNoon",
    "traffic_density": "high",
    "fps": 30,
    "requested_frames": 2,
    "captured_frames": 2,
    "sensors": ["rgb", "lidar"],
    "frames_by_sensor": {"rgb": 2, "lidar": 2},
    "status": "completed",
    "capture_source": "synthetic-seed",
    "error": None,
    "annotations": [],
    "started_at": "2026-01-01T00:00:00+00:00",
    "finished_at": "2026-01-01T00:00:05+00:00",
}


def _obj(key: str, size: int) -> dict:
    return {"Key": key, "Size": size, "LastModified": datetime(2026, 1, 1, tzinfo=UTC)}


@pytest.mark.asyncio
async def test_list_episodes(client, monkeypatch):
    objs = [
        _obj("episodes/ep1/metadata.json", 100),
        _obj("episodes/ep1/rgb/000000.png", 10),
        _obj("episodes/ep1/lidar/000000.ply", 20),
    ]
    monkeypatch.setattr(svc, "list_all_episode_objects", lambda: objs)
    monkeypatch.setattr(svc, "get_episode_metadata", lambda eid: META)

    response = await client.get("/episodes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "ep1"
    assert body[0]["capture_source"] == "synthetic-seed"
    assert body[0]["size_bytes"] == 130
    assert body[0]["total_objects"] == 3


@pytest.mark.asyncio
async def test_episode_detail(client, monkeypatch):
    monkeypatch.setattr(svc, "get_episode_metadata", lambda eid: META)
    monkeypatch.setattr(
        svc, "list_episode_objects", lambda eid: [_obj("episodes/ep1/rgb/000000.png", 10)]
    )
    response = await client.get("/episodes/ep1")
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["id"] == "ep1"
    assert body["total_objects"] == 1
    assert body["size_bytes"] == 10


@pytest.mark.asyncio
async def test_episode_detail_404(client, monkeypatch):
    monkeypatch.setattr(svc, "get_episode_metadata", lambda eid: None)
    response = await client.get("/episodes/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_episode(client, monkeypatch):
    monkeypatch.setattr(
        svc, "list_episode_objects", lambda eid: [_obj("episodes/ep1/rgb/000000.png", 10)]
    )
    monkeypatch.setattr(svc, "repo_delete_episode", lambda eid: 1)
    response = await client.delete("/episodes/ep1")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "id": "ep1", "objects": 1}


@pytest.mark.asyncio
async def test_delete_missing_episode_404(client, monkeypatch):
    monkeypatch.setattr(svc, "list_episode_objects", lambda eid: [])
    response = await client.delete("/episodes/missing")
    assert response.status_code == 404
