<!-- last_verified: 2026-09-15 -->
# Feature: Simulation runner

## Purpose
Run a scenario against the **real CARLA server** in synchronous mode, capturing multi-sensor streams and writing each frame to B2 as it is produced (continuous high-volume ingest), then write the episode's `metadata.json` at the end.

## Prerequisites (real capture)
The `carla` PyPI wheel is platform-restricted: **Linux/Windows, CPython <= 3.10 only** — no macOS/arm64, no Python 3.12. It is therefore NOT a base dependency and is never installed by `pnpm run setup`. To run a real capture, on a supported Linux/GPU host with a running CARLA server:

```bash
python3.10 -m venv .venv-carla && . .venv-carla/bin/activate
pip install -r services/api/requirements.txt -r services/api/requirements-carla.txt
export CARLA_HOST=localhost CARLA_PORT=2000   # point at your CARLA server
```

On any host **without** `carla` installed or without a reachable server, the run endpoint returns `503` with an actionable message — never a fake capture and never a substitute engine. This is the correct, documented handling for the platform-restricted wheel.

## Used By
- UI: `/scenarios/[id]` — the **Run** button
- API: `POST /scenarios/{scenario_id}/run`

## Core Functions
- `services/api/app/runtime/simulate.py` — route handler; maps `CarlaUnavailableError` → 503, `CarlaRunError` → 502
- `services/api/app/service/carla_runner.py` — lazy/guarded `import carla`, connect, load town/weather/traffic, spawn ego + sensor rig, synchronous tick loop, write metadata
- `services/api/app/service/sensors.py` — sensor rig construction + per-frame encoding (rgb/segmentation → PNG, depth → `.npy`, lidar → `.ply`, vehicle_state → JSON) and bbox-annotation projection
- `services/api/app/repo/frame_writer.py` — the continuous streaming writer (`PutObject` per frame)
- `services/api/app/repo/episode_store.py` — writes `episodes/<id>/metadata.json`

## Inputs
- scenario_id: path param → the stored `Scenario`
- `CARLA_HOST` / `CARLA_PORT` / `CARLA_TIMEOUT`: env (non-secret; localhost defaults)

## Outputs
- Per-frame objects under `episodes/<id>/<sensor>/` (streamed during the run)
- `episodes/<id>/metadata.json` with `capture_source: "carla"`, frame counts, and bbox annotations
- Response: `EpisodeMetadata`

## Flow
- `import carla` (guarded) → connect to `CARLA_HOST:CARLA_PORT` → `load_world(town)` → synchronous mode at `1/fps`
- Set weather, spawn ego (autopilot) + traffic (density → NPC count), attach the sensor rig
- Warm-up ticks, then for each frame: `world.tick()` → drain each sensor queue → encode → `frame_writer.write_frame` → B2; read vehicle telemetry; sample bbox annotations periodically
- On completion: write `metadata.json` (status `completed`), restore async mode, destroy actors

## Edge Cases
- `carla` not importable / server unreachable → `CarlaUnavailableError` → **503**, nothing written
- Mid-run failure → episode persisted with status `failed`, `CarlaRunError` → **502**
- The run is synchronous; a production deployment would enqueue it as a background job

## UX States
- Pending: "Running..." on the Run button + a loading toast
- Success: toast + redirect to the new episode
- Unavailable (503): a "Run unavailable" toast with the platform message — expected on the dev machine

## Verification
- Test files: `services/api/tests/test_simulate.py`
- Required cases: run without `carla` returns 503 (not 500); missing scenario returns 404
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green on macOS without `carla` installed

## Related Docs
- [Scenarios](scenarios.md)
- [Episode explorer](episode-explorer.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
