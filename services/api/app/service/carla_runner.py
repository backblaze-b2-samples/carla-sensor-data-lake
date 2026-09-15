"""Drive the REAL CARLA simulator and stream every sensor frame to B2.

This is the sample's primary feature, using the genuine vendor engine — never a
substitute generator. The `carla` PyPI wheel has **no macOS/arm64 build and no
Python 3.12 support** (Linux/Windows, CPython <= 3.10 only), so `import carla` is
**lazy and guarded**: on any host without the client library or without a
reachable CARLA server, `run_scenario` raises a typed `CarlaUnavailableError`
naming the supported platform, and the POST never 500s. The lake's
manage/browse/serve side works on any host against data already in B2.

See docs/features/simulation-runner.md for the prerequisites (a Linux/GPU host,
`pip install -r services/api/requirements-carla.txt`, and a running CARLA server).
"""

import contextlib
import logging
import queue
from datetime import UTC, datetime

from app.config import settings
from app.repo import put_episode_metadata, write_frame
from app.service import sensors
from app.types import Scenario
from app.types.episode import EpisodeMetadata

logger = logging.getLogger(__name__)

# Ticks discarded before capture so spawned traffic settles into motion.
_WARMUP_TICKS = 10
# Per-sensor wait for a tick's data in synchronous mode.
_SENSOR_TIMEOUT = 2.0


class CarlaUnavailableError(Exception):
    """CARLA client library is not installed here, or the server is unreachable."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class CarlaRunError(Exception):
    """A run reached CARLA but failed mid-capture; the episode is marked failed."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _import_carla():
    """Import the vendor engine or raise an actionable CarlaUnavailableError."""
    try:
        # Intentionally lazy: the `carla` wheel is platform-gated (see module docstring).
        import carla

        return carla
    except Exception as e:  # ImportError on unsupported platforms, and anything else
        raise CarlaUnavailableError(
            "CARLA Python API is not installed on this host. The `carla` wheel "
            "supports Linux/Windows on CPython <= 3.10 only (no macOS/arm64, no "
            "3.12). Install it on a supported Linux/GPU host "
            "(`pip install -r services/api/requirements-carla.txt`) and run "
            "against a live CARLA server. See docs/features/simulation-runner.md."
        ) from e


def _connect(carla):
    try:
        client = carla.Client(settings.carla_host, settings.carla_port)
        client.set_timeout(settings.carla_timeout)
        client.get_server_version()
        return client
    except Exception as e:
        raise CarlaUnavailableError(
            f"CARLA server unreachable at {settings.carla_host}:{settings.carla_port}. "
            "Start a CARLA server and set CARLA_HOST/CARLA_PORT. "
            f"({e})"
        ) from e


def run_scenario(episode_id: str, scenario: Scenario) -> EpisodeMetadata:
    """Run one scenario end-to-end, streaming frames to B2 as they are produced.

    Raises CarlaUnavailableError (nothing written) if the engine/server is
    absent, or CarlaRunError (a `failed` episode persisted) on a mid-run error.
    """
    carla = _import_carla()
    client = _connect(carla)
    started = datetime.now(UTC)
    world = client.load_world(scenario.town)
    original = world.get_settings()
    traffic_manager = client.get_trafficmanager()
    actors: list = []
    sensor_actors: dict = {}
    frames_by_sensor = {s: 0 for s in scenario.sensors}
    annotations: list[dict] = []

    try:
        tuned = world.get_settings()
        tuned.synchronous_mode = True
        tuned.fixed_delta_seconds = 1.0 / scenario.fps
        world.apply_settings(tuned)
        traffic_manager.set_synchronous_mode(True)

        weather = getattr(
            carla.WeatherParameters, scenario.weather, carla.WeatherParameters.ClearNoon
        )
        world.set_weather(weather)

        ego = _spawn_ego(carla, world, traffic_manager)
        actors.append(ego)
        actors.extend(
            sensors.spawn_traffic(carla, world, traffic_manager, scenario.traffic_density)
        )

        rig = [s for s in scenario.sensors if s != "vehicle_state"]
        sensor_actors = sensors.spawn_sensor_rig(carla, world, ego, rig)
        queues = {name: queue.Queue() for name in sensor_actors}
        for name, actor in sensor_actors.items():
            actor.listen(lambda data, n=name: queues[n].put(data))

        for _ in range(_WARMUP_TICKS):
            world.tick()

        captured = _capture_loop(
            carla, world, ego, scenario, episode_id, queues,
            sensor_actors, frames_by_sensor, annotations,
        )
        metadata = _metadata(
            episode_id, scenario, captured, frames_by_sensor, annotations,
            "completed", None, started,
        )
    except CarlaUnavailableError:
        raise
    except Exception as e:
        logger.exception("CARLA run failed for episode %s", episode_id)
        metadata = _metadata(
            episode_id, scenario, sum(frames_by_sensor.values()) // max(len(scenario.sensors), 1),
            frames_by_sensor, annotations, "failed", str(e), started,
        )
        put_episode_metadata(episode_id, metadata.model_dump(mode="json"))
        raise CarlaRunError(str(e)) from e
    finally:
        _cleanup(world, original, traffic_manager, actors, sensor_actors)

    put_episode_metadata(episode_id, metadata.model_dump(mode="json"))
    logger.info("CARLA run complete: episode=%s frames=%s", episode_id, metadata.captured_frames)
    return metadata


def _spawn_ego(carla, world, traffic_manager):
    blueprints = world.get_blueprint_library()
    ego_bp = blueprints.filter("vehicle.tesla.model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    ego = world.spawn_actor(ego_bp, spawn_points[0])
    ego.set_autopilot(True, traffic_manager.get_port())
    return ego


def _capture_loop(
    carla, world, ego, scenario, episode_id, queues,
    sensor_actors, frames_by_sensor, annotations,
) -> int:
    captured = 0
    for frame_i in range(scenario.frame_count):
        world.tick()
        for name, q in queues.items():
            data = q.get(timeout=_SENSOR_TIMEOUT)
            payload, ext, content_type = sensors.encode_frame(carla, name, data)
            write_frame(episode_id, name, f"{frame_i:06d}.{ext}", payload, content_type)
            frames_by_sensor[name] += 1
        if "vehicle_state" in scenario.sensors:
            payload, ext, content_type = sensors.encode_vehicle_state(ego, frame_i)
            write_frame(episode_id, "vehicle_state", f"{frame_i:06d}.{ext}", payload, content_type)
            frames_by_sensor["vehicle_state"] += 1
        # Sample annotations about once a second so the panel has a few frames.
        if "rgb" in sensor_actors and frame_i % max(scenario.fps, 1) == 0:
            annotations.extend(
                sensors.sample_annotations(carla, sensor_actors["rgb"], world, frame_i)
            )
        captured += 1
    return captured


def _cleanup(world, original, traffic_manager, actors, sensor_actors):
    # Best-effort teardown: a failure here must not mask the run's real outcome.
    for actor in list(sensor_actors.values()):
        with contextlib.suppress(Exception):
            actor.stop()
    for actor in list(sensor_actors.values()) + list(reversed(actors)):
        with contextlib.suppress(Exception):
            actor.destroy()
    with contextlib.suppress(Exception):
        traffic_manager.set_synchronous_mode(False)
        world.apply_settings(original)


def _metadata(
    episode_id, scenario, captured, frames_by_sensor, annotations, status, error, started,
) -> EpisodeMetadata:
    return EpisodeMetadata(
        id=episode_id,
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        town=scenario.town,
        weather=scenario.weather,
        traffic_density=scenario.traffic_density,
        fps=scenario.fps,
        requested_frames=scenario.frame_count,
        captured_frames=captured,
        sensors=scenario.sensors,
        frames_by_sensor=frames_by_sensor,
        status=status,
        capture_source="carla",
        error=error,
        annotations=annotations,
        started_at=started,
        finished_at=datetime.now(UTC),
    )
