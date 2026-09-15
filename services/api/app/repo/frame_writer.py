"""Continuous streaming writer: one PutObject per sensor frame.

Called from the CARLA sensor callbacks (service/carla_runner.py) as frames are
produced, so the lake fills continuously during a run rather than in one batch at
the end. Deliberately does NOT invalidate the listing cache per frame — a run can
emit thousands of frames; the cache is invalidated once when the episode's
metadata is written (episode_store.put_episode_metadata). boto3 stays in repo/.
"""

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.episode_store import _safe_id


def frame_key(episode_id: str, sensor: str, frame_name: str) -> str:
    """episodes/<id>/<sensor>/<frame_name> — the canonical frame object key."""
    return f"episodes/{_safe_id(episode_id)}/{sensor}/{frame_name}"


def write_frame(
    episode_id: str,
    sensor: str,
    frame_name: str,
    data: bytes,
    content_type: str,
) -> str:
    """Stream one sensor frame to B2. Returns the object key.

    Raises RuntimeError on S3 failure so the runner can mark the episode failed.
    """
    client = get_s3_client()
    key = frame_key(episode_id, sensor, frame_name)
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 write frame '{key}' failed: {e}") from e
    return key
