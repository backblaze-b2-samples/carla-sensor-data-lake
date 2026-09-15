"""Seed the B2 lake with synthetic scenarios + episodes for local demos.

This writes DEMO data so the dashboard, episodes list, and scoped frame explorer
are populated without a CARLA host. Frames are small synthetic placeholders — the
episodes are clearly marked `capture_source: "synthetic-seed"` (the UI badges
them), so seed data is never mistaken for a real capture. A real capture comes
from POST /scenarios/{id}/run against a live CARLA server (service/carla_runner).

Dependency-free beyond the base venv (Pillow, boto3) — no numpy/carla needed.

    python services/api/scripts/seed_lake.py            # dry run (lists what it would write)
    python services/api/scripts/seed_lake.py --apply    # actually write to B2
    python services/api/scripts/seed_lake.py --apply --episodes 2 --frames 3
"""

from __future__ import annotations

import argparse
import io
import struct
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.repo import put_episode_metadata, put_scenario, write_frame  # noqa: E402
from app.types import Scenario  # noqa: E402
from app.types.scenario import SENSORS  # noqa: E402


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


_W, _H = 160, 120

_SEED_SCENARIOS = [
    ("Highway rush hour", "Town10HD", "ClearNoon", "high", 30, 200),
    ("Wet city loop", "Town05", "MidRainyNoon", "medium", 20, 150),
    ("Dusk suburban", "Town03", "ClearSunset", "low", 10, 100),
]


def _png(color: tuple[int, int, int]) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (_W, _H), color).save(out, format="PNG")
    return out.getvalue()


def _npy(rows: int, cols: int, value: float) -> bytes:
    """A valid .npy (v1.0) float32 array — hand-rolled to avoid a numpy dep."""
    magic = b"\x93NUMPY\x01\x00"
    header = f"{{'descr': '<f4', 'fortran_order': False, 'shape': ({rows}, {cols}), }}"
    padding = (64 - (len(magic) + 2 + len(header) + 1) % 64) % 64
    header = header + " " * padding + "\n"
    body = struct.pack(f"<{rows * cols}f", *([value] * (rows * cols)))
    return magic + struct.pack("<H", len(header)) + header.encode("latin1") + body


def _ply(points: int, jitter: int) -> bytes:
    header = (
        "ply\nformat ascii 1.0\n"
        f"element vertex {points}\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property float intensity\nend_header\n"
    )
    body = "\n".join(
        f"{(i % 20) - 10 + jitter:.4f} {(i % 13) - 6:.4f} {(i % 7) * 0.5:.4f} {0.5:.4f}"
        for i in range(points)
    )
    return (header + body + "\n").encode("utf-8")


def _vehicle_state(frame: int) -> bytes:
    import json

    return json.dumps(
        {
            "frame": frame,
            "location": {"x": 10.0 + frame, "y": -3.2, "z": 0.03},
            "rotation": {"pitch": 0.0, "yaw": 88.0, "roll": 0.0},
            "velocity_mps": {"x": 8.0, "y": 0.1, "z": 0.0},
            "speed_mps": 8.0,
            "control": {"throttle": 0.6, "steer": 0.02, "brake": 0.0},
        },
        indent=2,
    ).encode("utf-8")


def _write_scenarios(apply: bool) -> list[Scenario]:
    now = datetime.now(UTC)
    scenarios: list[Scenario] = []
    for i, (name, town, weather, density, fps, frames) in enumerate(_SEED_SCENARIOS):
        scenario = Scenario(
            id=uuid.uuid4().hex[:12],
            name=name,
            description="Synthetic seed scenario for local demos.",
            town=town,
            weather=weather,
            traffic_density=density,
            fps=fps,
            frame_count=frames,
            sensors=SENSORS,
            created_at=now - timedelta(minutes=i),
            updated_at=now - timedelta(minutes=i),
        )
        _out(f"  scenario: {scenario.id}  {name}")
        if apply:
            put_scenario(scenario.id, scenario.model_dump(mode="json"))
        scenarios.append(scenario)
    return scenarios


def _write_episode(scenario: Scenario, frames: int, apply: bool, age_min: int) -> None:
    episode_id = uuid.uuid4().hex[:12]
    started = datetime.now(UTC) - timedelta(minutes=age_min)
    frames_by_sensor = {s: 0 for s in scenario.sensors}
    _out(f"  episode:  {episode_id}  from {scenario.name} ({frames} frames/sensor)")

    for frame_i in range(frames):
        payloads = {
            "rgb": (_png((60 + frame_i * 5, 90, 140)), "png", "image/png"),
            "segmentation": (_png((frame_i * 9 % 255, 200, 80)), "png", "image/png"),
            "depth": (_npy(32, 32, 12.5 + frame_i), "npy", "application/octet-stream"),
            "lidar": (_ply(64, frame_i), "ply", "text/plain"),
            "vehicle_state": (_vehicle_state(frame_i), "json", "application/json"),
        }
        for sensor in scenario.sensors:
            data, ext, ctype = payloads[sensor]
            frames_by_sensor[sensor] += 1
            if apply:
                write_frame(episode_id, sensor, f"{frame_i:06d}.{ext}", data, ctype)

    annotations = [
        {"frame": 0, "label": "vehicle.tesla.model3", "x": 40, "y": 55, "width": 60, "height": 40},
        {"frame": 0, "label": "vehicle.audi.a2", "x": 110, "y": 60, "width": 45, "height": 30},
    ]
    metadata = {
        "id": episode_id,
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "town": scenario.town,
        "weather": scenario.weather,
        "traffic_density": scenario.traffic_density,
        "fps": scenario.fps,
        "requested_frames": frames,
        "captured_frames": frames,
        "sensors": scenario.sensors,
        "frames_by_sensor": frames_by_sensor,
        "status": "completed",
        "capture_source": "synthetic-seed",
        "error": None,
        "annotations": annotations,
        "started_at": started.isoformat(),
        "finished_at": (started + timedelta(seconds=frames / scenario.fps)).isoformat(),
    }
    if apply:
        put_episode_metadata(episode_id, metadata)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write to B2 (else dry run)")
    parser.add_argument("--episodes", type=int, default=2, help="Synthetic episodes to write")
    parser.add_argument("--frames", type=int, default=2, help="Frames per sensor per episode")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    _out(f"Seeding CARLA Sensor Data Lake ({mode})")
    scenarios = _write_scenarios(args.apply)
    for i in range(args.episodes):
        _write_episode(scenarios[i % len(scenarios)], args.frames, args.apply, age_min=i * 5)

    if not args.apply:
        _out("\nDry run — re-run with --apply to write these objects to B2.")
    else:
        _out("\nDone. Open the dashboard, /episodes, and /scenarios to see the lake.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
