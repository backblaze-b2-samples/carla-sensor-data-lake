"""S3 CRUD for scenario config JSON under the `scenarios/` prefix.

Scenarios are stored as `scenarios/<id>.json` — B2 is the sole store, no
database. boto3/botocore stays confined to this repo/ layer; the cached S3
client is reused from `b2_client` for connection pooling.
"""

import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

SCENARIO_PREFIX = "scenarios/"


def _key(scenario_id: str) -> str:
    return f"{SCENARIO_PREFIX}{scenario_id}.json"


def put_scenario(scenario_id: str, data: dict) -> None:
    """Create or replace a scenario config. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    body = json.dumps(data, default=str, indent=2).encode("utf-8")
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=_key(scenario_id),
            Body=body,
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put scenario '{scenario_id}' failed: {e}") from e
    _invalidate_list_cache()


def get_scenario(scenario_id: str) -> dict | None:
    """Read one scenario config. Returns None if missing."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=_key(scenario_id)
        )
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get scenario '{scenario_id}' failed: {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get scenario '{scenario_id}' failed: {e}") from e


def list_scenarios() -> list[dict]:
    """Every stored scenario config, newest first by created_at when present."""
    client = get_s3_client()
    ids: list[str] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": SCENARIO_PREFIX}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    ids.append(key[len(SCENARIO_PREFIX) : -len(".json")])
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list scenarios failed: {e}") from e

    scenarios = [s for sid in ids if (s := get_scenario(sid)) is not None]
    scenarios.sort(key=lambda s: str(s.get("created_at", "")), reverse=True)
    return scenarios


def delete_scenario(scenario_id: str) -> None:
    """Delete one scenario config. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=_key(scenario_id))
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete scenario '{scenario_id}' failed: {e}") from e
    _invalidate_list_cache()
