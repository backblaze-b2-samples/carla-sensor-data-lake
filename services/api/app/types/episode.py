"""Episode models — the derived, immutable capture artifact.

An episode is produced by running a scenario. Its `metadata.json` lives at
`episodes/<id>/metadata.json`; sensor frames live under
`episodes/<id>/<sensor>/`. Episodes are read + delete in the UI (no edit —
captured frames are immutable).
"""

from datetime import datetime

from pydantic import BaseModel

# How an episode's frames were produced. "carla" = a real simulation run;
# "synthetic-seed" = demo data written by scripts/seed_lake.py so the
# browse/serve features are demonstrable without a CARLA host. The UI badges the
# difference so seed data is never mistaken for a real capture.
CAPTURE_SOURCES = ["carla", "synthetic-seed"]


class BBoxAnnotation(BaseModel):
    """One 2D bounding box on a captured RGB frame (illustrative annotations)."""

    frame: int
    label: str
    x: int
    y: int
    width: int
    height: int


class EpisodeMetadata(BaseModel):
    """The full per-episode record, persisted as episodes/<id>/metadata.json."""

    id: str
    scenario_id: str | None = None
    scenario_name: str | None = None
    town: str
    weather: str
    traffic_density: str
    fps: int
    requested_frames: int
    captured_frames: int
    sensors: list[str]
    frames_by_sensor: dict[str, int] = {}
    status: str  # "completed" | "failed" | "running"
    capture_source: str = "carla"
    error: str | None = None
    annotations: list[BBoxAnnotation] = []
    started_at: datetime
    finished_at: datetime | None = None


class EpisodeSummary(BaseModel):
    """Lightweight row for the episodes list. Sizes are computed live from B2."""

    id: str
    scenario_id: str | None = None
    scenario_name: str | None = None
    town: str
    weather: str
    status: str
    capture_source: str = "carla"
    captured_frames: int
    total_objects: int
    size_bytes: int
    size_human: str
    created_at: datetime


class EpisodeDetail(BaseModel):
    """Episode detail: the persisted metadata plus live-computed storage totals."""

    metadata: EpisodeMetadata
    total_objects: int
    size_bytes: int
    size_human: str
