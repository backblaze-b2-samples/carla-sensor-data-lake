"""Data-lake dashboard aggregation tests (repo boundary mocked)."""

from datetime import UTC, datetime

import pytest

from app.service import lake as svc


def _obj(key: str, size: int) -> dict:
    return {"Key": key, "Size": size, "LastModified": datetime(2026, 1, 1, tzinfo=UTC)}


@pytest.mark.asyncio
async def test_lake_stats_counts_frames_not_metadata(client, monkeypatch):
    objs = [
        _obj("episodes/ep1/metadata.json", 50),
        _obj("episodes/ep1/rgb/000000.png", 10),
        _obj("episodes/ep1/rgb/000001.png", 10),
        _obj("episodes/ep1/lidar/000000.ply", 30),
    ]
    monkeypatch.setattr(svc, "list_all_episode_objects", lambda: objs)
    monkeypatch.setattr(svc, "get_episode_metadata", lambda eid: {"weather": "ClearNoon", "town": "Town10HD"})
    monkeypatch.setattr(svc, "list_scenarios", lambda: [{"id": "s1"}, {"id": "s2"}])

    response = await client.get("/lake/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_episodes"] == 1
    assert body["total_frames"] == 3  # metadata.json is not a frame
    assert body["total_scenarios"] == 2
    assert body["total_size_bytes"] == 100
    sensors = {s["sensor"]: s["frames"] for s in body["frames_by_sensor"]}
    assert sensors == {"lidar": 1, "rgb": 2}
    assert body["episodes_by_weather"] == [{"label": "ClearNoon", "episodes": 1}]
    assert body["episodes_by_town"] == [{"label": "Town10HD", "episodes": 1}]


@pytest.mark.asyncio
async def test_lake_ingest_returns_one_bucket_per_day(client, monkeypatch):
    monkeypatch.setattr(
        svc, "list_all_episode_objects", lambda: [_obj("episodes/ep1/rgb/000000.png", 10)]
    )
    response = await client.get("/lake/ingest?days=7")
    assert response.status_code == 200
    assert len(response.json()) == 7


@pytest.mark.asyncio
async def test_lake_ingest_rejects_bad_days(client):
    response = await client.get("/lake/ingest?days=0")
    assert response.status_code == 400
