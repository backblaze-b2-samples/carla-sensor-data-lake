// Finite-value option sets for the Scenario form. These mirror the server-side
// constants in services/api/app/types/scenario.py — keep them in sync (the API
// re-validates every value, so a drift surfaces as a 422 rather than bad data).

export const TOWNS = [
  "Town01",
  "Town02",
  "Town03",
  "Town04",
  "Town05",
  "Town06",
  "Town07",
  "Town10HD",
] as const;

export const WEATHER_PRESETS = [
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
] as const;

export const TRAFFIC_DENSITIES = ["low", "medium", "high"] as const;

export const FPS_OPTIONS = [10, 20, 30] as const;

export const SENSORS = [
  { value: "rgb", label: "RGB camera" },
  { value: "segmentation", label: "Semantic segmentation" },
  { value: "depth", label: "Depth map" },
  { value: "lidar", label: "LiDAR point cloud" },
  { value: "vehicle_state", label: "Vehicle telemetry" },
] as const;

export const SENSOR_LABELS: Record<string, string> = Object.fromEntries(
  SENSORS.map((s) => [s.value, s.label]),
);

// Safe defaults surfaced as placeholder / description guidance on the create
// form (never an autofill button) — a sound first test run.
export const SCENARIO_DEFAULTS = {
  town: "Town10HD" as (typeof TOWNS)[number],
  weather: "ClearNoon" as (typeof WEATHER_PRESETS)[number],
  traffic_density: "medium" as (typeof TRAFFIC_DENSITIES)[number],
  fps: 10 as (typeof FPS_OPTIONS)[number],
  frame_count: 200,
  sensors: ["rgb", "segmentation", "depth", "lidar", "vehicle_state"],
};
