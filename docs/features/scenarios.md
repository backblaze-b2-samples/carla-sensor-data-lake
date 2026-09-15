<!-- last_verified: 2026-09-15 -->
# Feature: Scenarios

## Purpose
Create, edit, delete, and run reusable CARLA capture configs — the primary entity of the lake. A scenario captures everything needed to reproduce a capture: town, weather preset, traffic density, sensor rig, capture rate, and frame count.

## Used By
- UI: `/scenarios` (list), `/scenarios/new` (create), `/scenarios/[id]` (detail + run + delete), `/scenarios/[id]/edit` (edit)
- API: `GET /scenarios`, `POST /scenarios`, `GET /scenarios/{scenario_id}`, `PUT /scenarios/{scenario_id}`, `DELETE /scenarios/{scenario_id}` (run is documented in [simulation-runner.md](simulation-runner.md))

## Core Functions
- `apps/web/src/components/scenarios/scenario-form.tsx` — shared create/edit form (selectors for finite fields, safe-default hints)
- `apps/web/src/components/scenarios/scenarios-list.tsx` — list table
- `apps/web/src/components/scenarios/scenario-detail.tsx` — detail view, run/edit/delete actions, this scenario's episodes
- `apps/web/src/lib/scenario-config.ts` — town/weather/traffic/fps/sensor option sets + safe defaults (mirrors the server constants)
- `services/api/app/runtime/scenarios.py` — route handlers
- `services/api/app/service/scenarios.py` — CRUD business logic (id generation, timestamps)
- `services/api/app/repo/scenario_store.py` — S3 CRUD under `scenarios/`
- `services/api/app/types/scenario.py` — Pydantic models + finite-field validators

## Canonical Files
- Form exemplar: `apps/web/src/components/settings/settings-form.tsx`
- CRUD store: `services/api/app/repo/scenario_store.py`

## Inputs
- name: string (2–80 chars)
- description: string (≤ 500 chars)
- town: enum — Town01–Town07, Town10HD
- weather: enum — CARLA `WeatherParameters` preset names
- traffic_density: enum — low / medium / high
- fps: enum — 10 / 20 / 30
- frame_count: int (1–10000)
- sensors: string[] — subset of rgb / segmentation / depth / lidar / vehicle_state

## Outputs
- `Scenario` JSON persisted at `scenarios/<id>.json` in B2 (side effect: `PutObject`)
- Delete removes that object (`DeleteObject`)

## Flow
- Create: form → `POST /scenarios` → server assigns id + timestamps → `scenarios/<id>.json` written → redirect to detail
- Edit: form pre-filled from the stored scenario → `PUT /scenarios/{id}` (full replace; `created_at` preserved, `updated_at` bumped)
- Delete: confirm dialog → `DELETE /scenarios/{id}` (episodes already captured are unaffected)
- Run: see [simulation-runner.md](simulation-runner.md)

## Edge Cases
- Unknown town/weather/sensor/fps → `422` from the Pydantic validators
- Missing scenario on get/update/delete → `404`
- Sensors are de-duplicated and normalised to the canonical rig order on save

## UX States
- Empty: "No scenarios yet" with a New scenario CTA
- Loading: skeleton rows
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_scenarios.py`
- Required cases: create (+ sensor normalisation), reject bad town/sensor, list, get 404, update preserves created_at, delete
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [docs/app-workflows.md](../app-workflows.md)
- [Simulation runner](simulation-runner.md)
