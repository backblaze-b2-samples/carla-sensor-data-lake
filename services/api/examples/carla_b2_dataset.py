"""Stream a CARLA episode's RGB frames straight from Backblaze B2 into PyTorch.

Standalone example — NOT part of the app, NOT installed by `pnpm run setup`, and
NOT covered by `pnpm verify`. `torch` is intentionally kept out of the base deps
(no macOS/arm64 concerns, just weight): install it yourself to run this.

    pip install -r services/api/requirements.txt   # boto3, Pillow (already present)
    pip install torch torchvision                   # CPU wheels are fine
    python services/api/examples/carla_b2_dataset.py --episode <episode_id>

Credentials come from the same standardized env vars the app uses
(B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME, B2_REGION). Frames are
fetched via short-lived presigned GET URLs, so the bucket can stay private.

Device selection auto-detects CUDA -> Apple MPS -> CPU (defaults to CPU) so the
same script runs on a laptop or a GPU box unchanged.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from urllib.request import urlopen

import boto3
from botocore.config import Config
from PIL import Image
from torch.utils.data import DataLoader, Dataset

USER_AGENT = "b2ai-carla-sensor-data-lake"


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _s3_client():
    region = os.environ["B2_REGION"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://s3.{region}.backblazeb2.com",
        region_name=region,
        aws_access_key_id=os.environ["B2_APPLICATION_KEY_ID"],
        aws_secret_access_key=os.environ["B2_APPLICATION_KEY"],
        # Same custom user agent as the app — one B2 attribution identity.
        config=Config(signature_version="s3v4", user_agent_extra=USER_AGENT),
    )


def pick_device() -> str:
    """First available of CUDA -> Apple MPS -> CPU (defaults to CPU)."""
    import torch

    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


class CarlaEpisodeDataset(Dataset):
    """RGB frames of one episode, streamed from B2 via presigned URLs.

    Only object keys are held in memory; each frame's bytes are fetched lazily in
    __getitem__, so an episode far larger than RAM still trains.
    """

    def __init__(self, episode_id: str, sensor: str = "rgb", expires_in: int = 3600):
        self.bucket = os.environ["B2_BUCKET_NAME"]
        self.client = _s3_client()
        self.expires_in = expires_in
        prefix = f"episodes/{episode_id}/{sensor}/"
        self.keys = self._list_keys(prefix)
        if not self.keys:
            raise SystemExit(f"No frames found under s3://{self.bucket}/{prefix}")

    def _list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        kwargs = {"Bucket": self.bucket, "Prefix": prefix}
        while True:
            response = self.client.list_objects_v2(**kwargs)
            keys.extend(obj["Key"] for obj in response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
        return sorted(keys)

    def __len__(self) -> int:
        return len(self.keys)

    def __getitem__(self, index: int):
        import torch

        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self.keys[index]},
            ExpiresIn=self.expires_in,
        )
        with urlopen(url) as response:  # B2 presigned https URL
            image = Image.open(io.BytesIO(response.read())).convert("RGB")
        # HWC uint8 -> CHW float tensor in [0, 1].
        tensor = torch.frombuffer(image.tobytes(), dtype=torch.uint8)
        tensor = tensor.view(image.height, image.width, 3).permute(2, 0, 1).float() / 255.0
        return tensor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True, help="Episode id to stream")
    parser.add_argument("--sensor", default="rgb")
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    device = pick_device()
    _out(f"Using device: {device}")

    dataset = CarlaEpisodeDataset(args.episode, sensor=args.sensor)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    _out(f"Episode {args.episode}: {len(dataset)} {args.sensor} frames")

    for batch_index, batch in enumerate(loader):
        batch = batch.to(device)
        _out(f"batch {batch_index}: {tuple(batch.shape)} on {batch.device}")
        if batch_index == 0:
            break  # this example just proves the stream; wire in your model here.


if __name__ == "__main__":
    main()
