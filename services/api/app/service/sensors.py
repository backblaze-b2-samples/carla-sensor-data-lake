"""CARLA sensor rig construction + per-frame encoding.

Split out of ``carla_runner`` to keep both files under the 300-line ceiling and
to isolate the sensor-specific encoding. **Every `carla`/`numpy` import is lazy
(inside a function)** so this module imports cleanly on hosts without the CARLA
wheel (macOS/arm64, Python 3.12) — the whole app would otherwise fail to import.

Encoders return `(payload_bytes, extension, content_type)` and never touch B2;
``carla_runner`` routes the bytes to ``repo.frame_writer`` (the only writer).
"""

from __future__ import annotations

import io
import json
from typing import Any

# Approximate NPC vehicle counts per traffic-density preset.
TRAFFIC_COUNTS = {"low": 20, "medium": 50, "high": 120}

# Camera resolution kept modest so a frame is a few hundred KB, not multiple MB —
# a data lake fills fast at 200 frames x 5 sensors.
_CAMERA_WIDTH = 800
_CAMERA_HEIGHT = 600
_LIDAR_RANGE = 100.0


def spawn_sensor_rig(carla: Any, world: Any, ego: Any, sensors: list[str]) -> dict:
    """Attach the requested sensors to the ego vehicle. Returns name -> actor."""
    bp_lib = world.get_blueprint_library()
    actors: dict = {}
    cam_tf = carla.Transform(carla.Location(x=1.5, z=2.4))
    lidar_tf = carla.Transform(carla.Location(x=0.0, z=2.4))

    if "rgb" in sensors:
        actors["rgb"] = _spawn_camera(
            carla, world, bp_lib, ego, cam_tf, "sensor.camera.rgb"
        )
    if "segmentation" in sensors:
        actors["segmentation"] = _spawn_camera(
            carla, world, bp_lib, ego, cam_tf, "sensor.camera.semantic_segmentation"
        )
    if "depth" in sensors:
        actors["depth"] = _spawn_camera(
            carla, world, bp_lib, ego, cam_tf, "sensor.camera.depth"
        )
    if "lidar" in sensors:
        lidar_bp = bp_lib.find("sensor.lidar.ray_cast")
        lidar_bp.set_attribute("range", str(_LIDAR_RANGE))
        lidar_bp.set_attribute("rotation_frequency", "20")
        lidar_bp.set_attribute("points_per_second", "500000")
        actors["lidar"] = world.spawn_actor(lidar_bp, lidar_tf, attach_to=ego)

    return actors


def _spawn_camera(carla, world, bp_lib, ego, transform, blueprint_id):
    bp = bp_lib.find(blueprint_id)
    bp.set_attribute("image_size_x", str(_CAMERA_WIDTH))
    bp.set_attribute("image_size_y", str(_CAMERA_HEIGHT))
    return world.spawn_actor(bp, transform, attach_to=ego)


def spawn_traffic(carla, world, traffic_manager, density: str) -> list:
    """Spawn NPC vehicles on autopilot. Returns the spawned actor list."""
    count = TRAFFIC_COUNTS.get(density, 50)
    bp_lib = world.get_blueprint_library()
    vehicle_bps = bp_lib.filter("vehicle.*")
    spawn_points = world.get_map().get_spawn_points()
    import random

    random.shuffle(spawn_points)
    tm_port = traffic_manager.get_port()
    actors: list = []
    for i in range(min(count, len(spawn_points))):
        bp = random.choice(vehicle_bps)
        npc = world.try_spawn_actor(bp, spawn_points[i])
        if npc is not None:
            npc.set_autopilot(True, tm_port)
            actors.append(npc)
    return actors


def encode_frame(carla, sensor: str, data: Any) -> tuple[bytes, str, str]:
    """Encode one sensor measurement to storable bytes.

    rgb/segmentation -> PNG, depth -> float32 .npy (metres), lidar -> ASCII PLY.
    """
    if sensor == "rgb":
        return _encode_rgb(carla, data)
    if sensor == "segmentation":
        return _encode_segmentation(carla, data)
    if sensor == "depth":
        return _encode_depth(data)
    if sensor == "lidar":
        return _encode_lidar(data)
    raise ValueError(f"no encoder for sensor {sensor!r}")


def _bgra_to_rgb_array(image):
    import numpy as np

    buffer = np.frombuffer(image.raw_data, dtype=np.uint8)
    reshaped = buffer.reshape((image.height, image.width, 4))
    # CARLA delivers BGRA; drop alpha and reverse to RGB.
    return reshaped[:, :, :3][:, :, ::-1]


def _png_bytes(rgb_array) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.fromarray(rgb_array, "RGB").save(out, format="PNG")
    return out.getvalue()


def _encode_rgb(carla, image) -> tuple[bytes, str, str]:
    return _png_bytes(_bgra_to_rgb_array(image)), "png", "image/png"


def _encode_segmentation(carla, image) -> tuple[bytes, str, str]:
    # Colourise semantic labels with CARLA's CityScapes palette before saving.
    image.convert(carla.ColorConverter.CityScapesPalette)
    return _png_bytes(_bgra_to_rgb_array(image)), "png", "image/png"


def _encode_depth(image) -> tuple[bytes, str, str]:
    import numpy as np

    buffer = np.frombuffer(image.raw_data, dtype=np.uint8)
    bgra = buffer.reshape((image.height, image.width, 4)).astype(np.float32)
    r, g, b = bgra[:, :, 2], bgra[:, :, 1], bgra[:, :, 0]
    # CARLA's depth codec -> normalised [0,1] -> metres (far plane 1000 m).
    normalized = (r + g * 256.0 + b * 256.0 * 256.0) / (256.0**3 - 1.0)
    depth_metres = (normalized * 1000.0).astype(np.float32)
    out = io.BytesIO()
    np.save(out, depth_metres)
    return out.getvalue(), "npy", "application/octet-stream"


def _encode_lidar(measurement) -> tuple[bytes, str, str]:
    import numpy as np

    points = np.frombuffer(measurement.raw_data, dtype=np.float32).reshape((-1, 4))
    header = (
        "ply\nformat ascii 1.0\n"
        f"element vertex {len(points)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property float intensity\nend_header\n"
    )
    body = "\n".join(f"{x:.4f} {y:.4f} {z:.4f} {i:.4f}" for x, y, z, i in points)
    return (header + body + "\n").encode("utf-8"), "ply", "text/plain"


def sample_annotations(
    carla: Any, camera: Any, world: Any, frame_index: int, max_boxes: int = 10
) -> list[dict]:
    """Project nearby vehicles' 3D boxes onto the RGB image plane.

    Standard CARLA client-side bounding-box projection: build the camera
    intrinsics from its FOV, transform each box vertex into camera space, and
    keep vertices in front of the camera. Returns BBoxAnnotation-shaped dicts.
    """
    import numpy as np

    fov = 90.0
    focal = _CAMERA_WIDTH / (2.0 * np.tan(fov * np.pi / 360.0))
    k = np.identity(3)
    k[0, 0] = k[1, 1] = focal
    k[0, 2] = _CAMERA_WIDTH / 2.0
    k[1, 2] = _CAMERA_HEIGHT / 2.0
    world_2_cam = np.array(camera.get_transform().get_inverse_matrix())
    cam_loc = camera.get_transform().location

    out: list[dict] = []
    for vehicle in world.get_actors().filter("vehicle.*"):
        if camera.parent is not None and vehicle.id == camera.parent.id:
            continue
        if vehicle.get_transform().location.distance(cam_loc) > 60.0:
            continue
        us: list[float] = []
        vs: list[float] = []
        for vert in vehicle.bounding_box.get_world_vertices(vehicle.get_transform()):
            point = world_2_cam @ np.array([vert.x, vert.y, vert.z, 1.0])
            cam_point = np.array([point[1], -point[2], point[0]])
            if cam_point[2] <= 0.0:
                continue
            projected = k @ cam_point
            us.append(projected[0] / projected[2])
            vs.append(projected[1] / projected[2])
        if not us:
            continue
        x0 = max(0, int(min(us)))
        y0 = max(0, int(min(vs)))
        x1 = min(_CAMERA_WIDTH, int(max(us)))
        y1 = min(_CAMERA_HEIGHT, int(max(vs)))
        if x1 <= x0 or y1 <= y0:
            continue
        out.append(
            {
                "frame": frame_index,
                "label": str(vehicle.type_id),
                "x": x0,
                "y": y0,
                "width": x1 - x0,
                "height": y1 - y0,
            }
        )
        if len(out) >= max_boxes:
            break
    return out


def encode_vehicle_state(ego, frame_index: int) -> tuple[bytes, str, str]:
    """Per-tick ego telemetry as JSON (transform, velocity, control)."""
    tf = ego.get_transform()
    vel = ego.get_velocity()
    ctrl = ego.get_control()
    speed_mps = (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5
    state = {
        "frame": frame_index,
        "location": {"x": tf.location.x, "y": tf.location.y, "z": tf.location.z},
        "rotation": {
            "pitch": tf.rotation.pitch,
            "yaw": tf.rotation.yaw,
            "roll": tf.rotation.roll,
        },
        "velocity_mps": {"x": vel.x, "y": vel.y, "z": vel.z},
        "speed_mps": speed_mps,
        "control": {
            "throttle": ctrl.throttle,
            "steer": ctrl.steer,
            "brake": ctrl.brake,
        },
    }
    return json.dumps(state, indent=2).encode("utf-8"), "json", "application/json"
