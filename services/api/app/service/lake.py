"""Data-lake dashboard aggregation (episodes, frames, storage, throughput)."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.repo import (
    get_episode_metadata,
    list_all_episode_objects,
    list_scenarios,
)
from app.types import DailyFrameCount, GroupCount, LakeStats, SensorCount
from app.types.formatting import humanize_bytes


def _is_frame(parts: list[str]) -> bool:
    # episodes/<id>/<sensor>/<frame> -> a real frame; metadata.json is 3 parts.
    return len(parts) >= 4 and bool(parts[3])


def get_lake_stats() -> LakeStats:
    objects = list_all_episode_objects()
    frames_by_sensor: dict[str, int] = defaultdict(int)
    total_frames = 0
    total_size = 0
    episode_ids: set[str] = set()

    for obj in objects:
        total_size += obj["Size"]
        parts = obj["Key"].split("/")
        if len(parts) >= 2 and parts[1]:
            episode_ids.add(parts[1])
        if _is_frame(parts):
            frames_by_sensor[parts[2]] += 1
            total_frames += 1

    by_weather: dict[str, int] = defaultdict(int)
    by_town: dict[str, int] = defaultdict(int)
    for eid in episode_ids:
        meta = get_episode_metadata(eid)
        if meta:
            by_weather[meta.get("weather", "unknown")] += 1
            by_town[meta.get("town", "unknown")] += 1

    return LakeStats(
        total_episodes=len(episode_ids),
        total_frames=total_frames,
        total_scenarios=len(list_scenarios()),
        total_size_bytes=total_size,
        total_size_human=humanize_bytes(total_size),
        frames_by_sensor=[
            SensorCount(sensor=s, frames=n)
            for s, n in sorted(frames_by_sensor.items())
        ],
        episodes_by_weather=[
            GroupCount(label=lbl, episodes=n)
            for lbl, n in sorted(by_weather.items())
        ],
        episodes_by_town=[
            GroupCount(label=lbl, episodes=n) for lbl, n in sorted(by_town.items())
        ],
    )


def get_ingest_activity(days: int = 7) -> list[DailyFrameCount]:
    """Frames ingested per day over the last N days (ingest throughput)."""
    objects = list_all_episode_objects()
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)

    counts: dict[str, int] = defaultdict(int)
    for obj in objects:
        if not _is_frame(obj["Key"].split("/")):
            continue
        day = obj["LastModified"].date()
        if day >= cutoff:
            counts[day.isoformat()] += 1

    return [
        DailyFrameCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            frames=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
