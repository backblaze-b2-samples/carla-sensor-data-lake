"""Scenario config models — the primary entity.

A Scenario is a reusable CARLA capture config (town, weather, traffic, sensor
rig, fps, frame count). It is persisted as JSON in B2 under `scenarios/` and is
the input to a simulation run. Finite-value fields are validated at the boundary
so the API rejects a bad town/weather/sensor before it ever reaches CARLA.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# CARLA ships these maps by default. Town10HD is the high-detail default used by
# the create-form safe defaults (see docs/features/scenarios.md).
TOWNS = [
    "Town01",
    "Town02",
    "Town03",
    "Town04",
    "Town05",
    "Town06",
    "Town07",
    "Town10HD",
]

# Names of `carla.WeatherParameters` presets. carla_runner resolves each via
# getattr with a ClearNoon fallback, so an older server missing a night preset
# degrades gracefully rather than crashing the run.
WEATHER_PRESETS = [
    "ClearNoon",
    "CloudyNoon",
    "WetNoon",
    "WetCloudyNoon",
    "MidRainyNoon",
    "HardRainNoon",
    "SoftRainNoon",
    "ClearSunset",
    "CloudySunset",
    "WetSunset",
    "WetCloudySunset",
    "MidRainSunset",
    "HardRainSunset",
    "SoftRainSunset",
    "ClearNight",
    "HardRainNight",
]

TRAFFIC_DENSITIES = ["low", "medium", "high"]

FPS_OPTIONS = [10, 20, 30]

# The sensor rig. Each maps to a CARLA sensor blueprint in service/sensors.py and
# to a B2 sub-prefix under episodes/<id>/<sensor>/.
SENSORS = ["rgb", "segmentation", "depth", "lidar", "vehicle_state"]


class ScenarioInput(BaseModel):
    """Create/edit payload for a Scenario (edit fully replaces the config)."""

    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    town: str
    weather: str
    traffic_density: str
    fps: int
    frame_count: int = Field(ge=1, le=10000)
    sensors: list[str] = Field(min_length=1)

    @field_validator("town")
    @classmethod
    def _valid_town(cls, v: str) -> str:
        if v not in TOWNS:
            raise ValueError(f"town must be one of {TOWNS}")
        return v

    @field_validator("weather")
    @classmethod
    def _valid_weather(cls, v: str) -> str:
        if v not in WEATHER_PRESETS:
            raise ValueError(f"weather must be one of {WEATHER_PRESETS}")
        return v

    @field_validator("traffic_density")
    @classmethod
    def _valid_traffic(cls, v: str) -> str:
        if v not in TRAFFIC_DENSITIES:
            raise ValueError(f"traffic_density must be one of {TRAFFIC_DENSITIES}")
        return v

    @field_validator("fps")
    @classmethod
    def _valid_fps(cls, v: int) -> int:
        if v not in FPS_OPTIONS:
            raise ValueError(f"fps must be one of {FPS_OPTIONS}")
        return v

    @field_validator("sensors")
    @classmethod
    def _valid_sensors(cls, v: list[str]) -> list[str]:
        unknown = [s for s in v if s not in SENSORS]
        if unknown:
            raise ValueError(f"unknown sensors {unknown}; valid: {SENSORS}")
        # De-dupe while preserving the canonical order.
        return [s for s in SENSORS if s in v]


class Scenario(ScenarioInput):
    """A stored Scenario: the input config plus server-assigned identity."""

    id: str
    created_at: datetime
    updated_at: datetime
