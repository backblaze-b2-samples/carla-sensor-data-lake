import logging

from fastapi import APIRouter, HTTPException

from app.service.lake import get_ingest_activity, get_lake_stats
from app.types import DailyFrameCount, LakeStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/lake/stats", response_model=LakeStats)
def lake_stats_endpoint():
    return get_lake_stats()


@router.get("/lake/ingest", response_model=list[DailyFrameCount])
def lake_ingest_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_ingest_activity(days=days)
