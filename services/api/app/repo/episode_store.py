"""S3 list/read/delete for episodes under the `episodes/` prefix.

Layout (see docs/features/episode-explorer.md):
    episodes/<id>/metadata.json
    episodes/<id>/<sensor>/<frame>

Deletes are scoped strictly to a single `episodes/<id>/` prefix — never a broad
wipe. boto3/botocore stays confined to this repo/ layer.
"""

import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

EPISODE_PREFIX = "episodes/"


def _safe_id(episode_id: str) -> str:
    """Reject ids that could escape the episode's own prefix.

    Delete is destructive and prefix-scoped, so an id with a slash or traversal
    segment could widen the blast radius — refuse it outright.
    """
    if not episode_id or "/" in episode_id or ".." in episode_id or "\\" in episode_id:
        raise ValueError(f"invalid episode id: {episode_id!r}")
    return episode_id


def _prefix(episode_id: str) -> str:
    return f"{EPISODE_PREFIX}{_safe_id(episode_id)}/"


def _metadata_key(episode_id: str) -> str:
    return f"{_prefix(episode_id)}metadata.json"


def put_episode_metadata(episode_id: str, data: dict) -> None:
    """Write episodes/<id>/metadata.json. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    body = json.dumps(data, default=str, indent=2).encode("utf-8")
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=_metadata_key(episode_id),
            Body=body,
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put episode meta '{episode_id}' failed: {e}") from e
    _invalidate_list_cache()


def get_episode_metadata(episode_id: str) -> dict | None:
    """Read one episode's metadata.json. Returns None if missing."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=_metadata_key(episode_id)
        )
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get episode meta '{episode_id}' failed: {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get episode meta '{episode_id}' failed: {e}") from e


def list_episode_ids() -> list[str]:
    """Distinct episode ids via a delimited listing of `episodes/`."""
    client = get_s3_client()
    ids: list[str] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": EPISODE_PREFIX,
        "Delimiter": "/",
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for cp in response.get("CommonPrefixes", []):
                pfx = cp.get("Prefix", "")
                ids.append(pfx[len(EPISODE_PREFIX) : -1])  # strip prefix + trailing /
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list episodes failed: {e}") from e
    return [i for i in ids if i]


def list_episode_objects(episode_id: str) -> list[dict]:
    """Every object under episodes/<id>/ (raw Key/Size/LastModified dicts)."""
    return _list_under(_prefix(episode_id))


def list_all_episode_objects() -> list[dict]:
    """Every object under episodes/ — used by the lake dashboard aggregation."""
    return _list_under(EPISODE_PREFIX)


def _list_under(prefix: str) -> list[dict]:
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": prefix,
        "MaxKeys": 1000,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list '{prefix}' failed: {e}") from e
    return contents


def delete_episode(episode_id: str) -> int:
    """Delete every object under episodes/<id>/. Returns the count deleted.

    Strictly scoped to one episode's prefix (see `_safe_id`). Raises
    RuntimeError on S3 failure.
    """
    client = get_s3_client()
    prefix = _prefix(episode_id)
    objects = _list_under(prefix)
    if not objects:
        return 0
    deleted = 0
    try:
        for start in range(0, len(objects), 1000):
            batch = objects[start : start + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": o["Key"]} for o in batch]},
            )
            deleted += len(batch)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete episode '{episode_id}' failed: {e}") from e
    _invalidate_list_cache()
    return deleted
