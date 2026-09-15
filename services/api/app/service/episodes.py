"""Episode read/delete business logic (episodes are immutable — no edit)."""

import logging
from collections import defaultdict

from app.repo import (
    delete_episode as repo_delete_episode,
)
from app.repo import (
    get_episode_metadata,
    list_all_episode_objects,
    list_episode_objects,
)
from app.types import EpisodeDetail, EpisodeMetadata, EpisodeSummary
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


class EpisodeNotFoundError(Exception):
    def __init__(self, detail: str = "Episode not found"):
        self.detail = detail
        super().__init__(detail)


def _episode_id_of(key: str) -> str | None:
    parts = key.split("/")  # episodes/<id>/...
    return parts[1] if len(parts) >= 2 and parts[1] else None


def list_all_episodes() -> list[EpisodeSummary]:
    """One bucket listing under episodes/, grouped by id, joined to metadata."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for obj in list_all_episode_objects():
        eid = _episode_id_of(obj["Key"])
        if eid:
            grouped[eid].append(obj)

    summaries: list[EpisodeSummary] = []
    for eid, objects in grouped.items():
        meta = get_episode_metadata(eid)
        if meta is None:
            continue  # a partial prefix with no metadata.json — skip from the list
        size = sum(o["Size"] for o in objects)
        summaries.append(
            EpisodeSummary(
                id=eid,
                scenario_id=meta.get("scenario_id"),
                scenario_name=meta.get("scenario_name"),
                town=meta.get("town", ""),
                weather=meta.get("weather", ""),
                status=meta.get("status", "completed"),
                capture_source=meta.get("capture_source", "carla"),
                captured_frames=meta.get("captured_frames", 0),
                total_objects=len(objects),
                size_bytes=size,
                size_human=humanize_bytes(size),
                created_at=meta["started_at"],
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def get_episode(episode_id: str) -> EpisodeDetail:
    meta = get_episode_metadata(episode_id)
    if meta is None:
        raise EpisodeNotFoundError()
    objects = list_episode_objects(episode_id)
    size = sum(o["Size"] for o in objects)
    return EpisodeDetail(
        metadata=EpisodeMetadata(**meta),
        total_objects=len(objects),
        size_bytes=size,
        size_human=humanize_bytes(size),
    )


def delete_episode(episode_id: str) -> int:
    """Delete one episode's whole prefix. Raises EpisodeNotFoundError if empty."""
    objects = list_episode_objects(episode_id)
    if not objects:
        raise EpisodeNotFoundError()
    deleted = repo_delete_episode(episode_id)
    logger.info("Episode deleted: id=%s objects=%s", episode_id, deleted)
    return deleted
