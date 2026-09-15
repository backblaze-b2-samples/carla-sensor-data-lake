import logging

from fastapi import APIRouter, HTTPException

from app.service.episodes import (
    EpisodeNotFoundError,
    delete_episode,
    get_episode,
    list_all_episodes,
)
from app.types import EpisodeDetail, EpisodeSummary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/episodes", response_model=list[EpisodeSummary])
def list_episodes_endpoint():
    return list_all_episodes()


@router.get("/episodes/{episode_id}", response_model=EpisodeDetail)
def get_episode_endpoint(episode_id: str):
    try:
        return get_episode(episode_id)
    except EpisodeNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/episodes/{episode_id}")
def delete_episode_endpoint(episode_id: str):
    try:
        count = delete_episode(episode_id)
    except EpisodeNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete episode") from None
    return {"deleted": True, "id": episode_id, "objects": count}
