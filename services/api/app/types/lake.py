"""Data-lake dashboard aggregate models."""

from pydantic import BaseModel


class SensorCount(BaseModel):
    sensor: str
    frames: int


class GroupCount(BaseModel):
    """Episodes grouped by a categorical dimension (weather, town)."""

    label: str
    episodes: int


class DailyFrameCount(BaseModel):
    """Frames ingested into the lake on a given day (ingest throughput)."""

    date: str
    frames: int


class LakeStats(BaseModel):
    total_episodes: int
    total_frames: int
    total_scenarios: int
    total_size_bytes: int
    total_size_human: str
    frames_by_sensor: list[SensorCount]
    episodes_by_weather: list[GroupCount]
    episodes_by_town: list[GroupCount]
