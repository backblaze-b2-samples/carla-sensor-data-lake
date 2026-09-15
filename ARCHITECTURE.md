<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Scenarios: list, create/edit form, detail, run, delete (primary entity)
  - Episodes: list and per-episode detail with a scoped sensor-frame browser
  - Data-lake dashboard (episodes, frames, storage, sensor/weather/town breakdowns, ingest)
  - Full-bucket file browser + manual upload
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for scenario CRUD + run, episode read/delete, lake aggregation, files
  - B2 S3 integration via boto3 (scenario JSON, per-frame streaming, presigned serving)
  - CARLA simulation runner (lazy/guarded `import carla`; drives the real engine)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (Scenario, Episode, LakeStats, …)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, UploadStats, etc.)
    config/                Settings loaded from environment
    repo/                  B2 S3 client (data access layer)
    service/               Business logic (upload, files, metadata)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. Each service's versioned config sits at its own root —
  `railway.json` and `services/api/railway.json` — the default path Railway
  discovers, so a one-click template deploy inherits the same build, start, and
  health behavior with nothing to configure by hand. The human-approved
  staging/production contract lives in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store (no database)
  - `scenarios/<id>.json` — scenario configs
  - `episodes/<id>/metadata.json` — episode metadata + annotations
  - `episodes/<id>/<sensor>/<frame>` — per-frame sensor data (rgb/segmentation `.png`, depth `.npy`, lidar `.ply`, vehicle_state `.json`)
  - Listing/metadata via S3 `list_objects_v2` / `head_object`; serving via `generate_presigned_url`

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Scenario CRUD**: Browser -> `GET/POST/PUT/DELETE /scenarios[/{id}]` -> service -> `repo/scenario_store.py` reads/writes `scenarios/<id>.json`
- **Run (capture)**: Browser -> `POST /scenarios/{id}/run` -> `service/carla_runner.py` (guarded `import carla`) drives the real CARLA server in synchronous mode -> each sensor callback -> `repo/frame_writer.py` streams a `PutObject` per frame -> `metadata.json` written at end. No `carla`/server -> `503` with an actionable message (nothing written)
- **Episode browse**: Browser -> `GET /episodes` / `GET /episodes/{id}` -> service -> `repo/episode_store.py`; the scoped frame explorer reuses `GET /files?prefix=episodes/<id>/`
- **Episode delete**: Browser -> `DELETE /episodes/{id}` -> service -> repo `DeleteObjects` scoped strictly to `episodes/<id>/`
- **Dashboard**: Browser -> `GET /lake/stats` / `GET /lake/ingest` -> `service/lake.py` aggregates one `ListObjectsV2` under `episodes/`
- **Serve/Download**: Browser -> `GET /files-by-key/preview|download` -> repo generates a presigned URL -> browser (or the PyTorch DataLoader) fetches from B2
- **Upload (manual ingest)**: Browser -> `POST /upload/presign` -> Browser PUTs bytes **directly to B2** -> `POST /upload/verify`

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layered API handler: `services/api/app/runtime/scenarios.py`
- Service orchestration: `services/api/app/service/scenarios.py`
- Simulation engine (guarded): `services/api/app/service/carla_runner.py` + `service/sensors.py`
- B2 data access (repo layer): `services/api/app/repo/scenario_store.py`, `repo/episode_store.py`, `repo/frame_writer.py`, `repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`scenario.py`, `episode.py`, `lake.py`, `files.py`, …)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Scenarios](docs/features/scenarios.md)
- [Simulation runner](docs/features/simulation-runner.md)
- [Episode explorer](docs/features/episode-explorer.md)
- [Dataset serving](docs/features/dataset-serving.md)
- [Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md)
- [File Upload](docs/features/file-upload.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
