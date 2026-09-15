# Build plan — `carla-sensor-data-lake`

Scaffolded from `vibe-coding-starter-kit` (fresh clone at
`.claude/scratch/vcsk-49a6eaa9-4294-424a-892c-6af1fe0d6abb/`). This plan is the
contract for both the `sample-builder` and `sample-reviewer` subagents.

## 1. Purpose

`carla-sensor-data-lake` is a **synthetic autonomous-driving data lake** built on
Backblaze B2. AV-perception and robotics teams generate large, diverse multi-sensor
driving datasets from the open-source **CARLA** simulator — RGB camera, semantic
segmentation, LiDAR point clouds, depth maps, and per-tick vehicle telemetry — without
costly real-world data collection. A scenario config (town, weather, traffic density,
sensor rig, frame count) is stored in B2; running it drives the real CARLA server,
which streams every sensor frame to B2 as it is produced (continuous high-volume
ingest); episode metadata + annotations are written at episode end; and the resulting
dataset is browsed, served via presigned URLs, and streamed straight into a PyTorch
`DataLoader` for training. B2 is the storage layer for the whole lake, accessed over
the **S3-compatible API** with a custom user agent and standard `B2_*` env vars — no
second API key, B2 credentials only.

Audience: autonomous-vehicle researchers, perception-model engineers, robotics/sim
teams who need scalable synthetic sensor datasets on cheap object storage.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is a B2-backed data app with a Next.js 16 web tier and a layered
FastAPI backend — exactly the shape a data-lake manager needs. The delta is therefore
**mostly ADD + ADAPT + rename**; very little is stripped. The starter is the ceiling.

### KEEP (as-is — do not strip, rename, or rebuild)
- **UI kit / design system**: `apps/web/src/components/ui/*` (shadcn primitives),
  design tokens in `apps/web/src/app/globals.css`, the `/design` reference page.
  New screens compose these; restyle only through `globals.css` tokens.
- **Bucket explorer (NON-NEGOTIABLE keep)**: `/files` route, `apps/web/src/app/files/`,
  `apps/web/src/components/files/*` (`file-browser`, `file-tree-row`,
  `file-metadata-panel`, `file-preview*`). Full-bucket browse stays. There is **no
  tension** removing it here — a raw view of the whole lake is genuinely useful.
- **Upload**: `/upload` route + `apps/web/src/components/upload/*`, lightly reframed in
  copy as "manual ingest into the lake" (import an external sensor file or a scenario
  JSON). Part of the starter's B2 scaffolding and the sidebar/agent-docs contract —
  kept to stay green, not rebuilt.
- **Layout/nav**: `app-sidebar`, `header`, `command-palette`, `health-banner`,
  `theme-provider`. Add "Scenarios" and "Episodes" sidebar entries; keep Dashboard,
  Upload, Files, Settings, Design.
- **Backend skeleton + invariants**: the `types → config → repo → service → runtime`
  layering; `repo/b2_client.py`, `repo/b2_object.py`, `repo/b2_upload.py`,
  `repo/list_cache.py`, `repo/counter.py`; `runtime/health.py`, `runtime/metrics.py`,
  `runtime/ratelimit.py`. No boto3 outside `repo/`; app Python files < 300 lines.
- **Tooling/gates**: `scripts/*`, `pnpm verify` chain, CI, OpenAPI contract check,
  `check:agent-docs`, agent-doc shims (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/copilot).
- `packages/shared` types package structure.

### TRIM (remove / stop shipping)
- Starter identity everywhere → rename (see §6). No "vibe coding" strings survive.
- The dashboard's upload-only framing: the illustrative "uploads over time" chart and
  "recent uploads" semantics are **rewritten** (see ADAPT) into lake metrics, not kept
  verbatim.
- Starter's own completed exec-plans under `docs/exec-plans/completed/*` that document
  *the starter's* construction (2026-02/07/08 dated entries) — optional cleanup; leave
  `_template`/structure intact. Do **not** break `docs/exec-plans/active/` structure.
- Do **not** hard-remove anything else; the starter is lean and mostly reused.

### ADD (new for carla-sensor-data-lake)
**Primary entity = Scenario** (a reusable CARLA config). New web screens:
- `/scenarios` — list (data-table), **create/edit** form (modeled on
  `settings/settings-form.tsx`), **detail** view (config + its episodes), **run**
  action, **delete** (modeled on `settings/danger-zone.tsx`).
- `/episodes` — list of produced episodes; **episode detail** with the
  **sample-specific scoped asset explorer** (the mandatory scoped explorer): a
  sensor-frame browser scoped to the `episodes/<id>/` prefix (reuse `file-tree`/
  `file-browser` primitives, prefix-locked), plus a metadata/annotations panel
  (weather, town, frame count, bbox annotations) and frame preview via presigned URL.
- Dataset **serving** UI affordance: "copy presigned URL" / "PyTorch snippet" on an
  episode.

New backend:
- `repo/scenario_store.py` — S3 CRUD for scenario JSON under `scenarios/`.
- `repo/episode_store.py` — S3 list/read/delete for episodes + metadata under
  `episodes/` (delete scoped strictly to one `episodes/<id>/` prefix).
- `repo/frame_writer.py` — the continuous streaming writer: per-frame `PutObject`
  under `episodes/<id>/<sensor>/<frame>` as frames are produced.
- `repo/presign.py` (or extend an existing repo module) — `generate_presigned_url` for
  serving/preview.
- `service/carla_runner.py` — drives the **real CARLA** Python API in synchronous
  mode: connect to server, load town/weather/traffic, attach the sensor rig, tick,
  route each sensor callback → `frame_writer` → B2, write `metadata.json` at end.
  **Lazy/guarded `import carla`** (see §3 build constraint). Split sensor-specific
  encoding into `service/sensors.py` if `carla_runner.py` nears 300 lines.
- `service/dataset.py` — dataset index (by episode id / scenario / weather) + presigned
  URL serving; pure boto3 via repo layer.
- `runtime/scenarios.py`, `runtime/episodes.py`, `runtime/simulate.py` routers.
- `types/scenario.py`, `types/episode.py` — Pydantic models; mirror in
  `packages/shared/src/types.ts` and register routes in `lib/api-client.ts`
  (`API_CLIENT_ROUTES`), `lib/queries.ts`, and re-export `docs/api/openapi.json`.
- `config/settings.py`: add `CARLA_HOST` (default `localhost`), `CARLA_PORT` (default
  `2000`), `CARLA_TIMEOUT`. These are **not** secrets.
- Standalone example (NOT in base deps): `services/api/examples/carla_b2_dataset.py` —
  a PyTorch `Dataset`/`DataLoader` that streams frames from B2 via presigned URLs;
  documented `pip install torch` separately. Defaults to CPU, autodetects CUDA→MPS→CPU.

### ADAPT (rewrite in place)
- **Dashboard** (`/` + `apps/web/src/components/dashboard/*`): replace upload metrics
  with **lake metrics** — total episodes, total frames, storage footprint (bytes),
  frames-by-sensor-type, episodes-by-weather/town, ingest throughput. Flow through
  `runtime → service → repo` and TanStack Query hooks in `lib/queries.ts` (no bare
  `useEffect + fetch`). Update `docs/features/dashboard.md` in the same change.

## 3. B2 surface (S3 operations) + build constraints

All storage is the **S3-compatible API only** (boto3), custom user agent on every
client, standard `B2_*` env vars. **No b2-native API.** Operations exercised:
- `PutObject` — scenario config JSON; each sensor frame during streaming ingest;
  per-tick vehicle-state JSON; episode `metadata.json`.
- `ListObjectsV2` (delimiter/prefix) — list scenarios; list episodes; list frames by
  `episodes/<id>/<sensor>/` (scoped explorer) and whole-bucket (Files).
- `GetObject` / `HeadObject` — read scenario config, episode metadata, frame preview,
  object size/metadata.
- `generate_presigned_url` — serve frames to the PyTorch `DataLoader`; UI previews.
- `DeleteObject` / `DeleteObjects` — delete a scenario; delete an episode (scoped to
  exactly one `episodes/<id>/` prefix — never a broad wipe).

**B2 prefix layout**
```
scenarios/<scenario_id>.json
episodes/<episode_id>/metadata.json
episodes/<episode_id>/rgb/<frame>.png
episodes/<episode_id>/segmentation/<frame>.png
episodes/<episode_id>/depth/<frame>.npy
episodes/<episode_id>/lidar/<frame>.ply
episodes/<episode_id>/vehicle_state/<frame>.json
```

**Env-var normalization (`/b2-doctor` must pass):** the starter's `.env.example` uses
`B2_KEY_ID` and `B2_ENDPOINT`. This sample MUST use the standardized set:
`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`,
`B2_PUBLIC_URL_BASE` (endpoint derived from region). Apply `/b2-doctor` and update
`.env.example`, `config/settings.py`, and any `repo/b2_client.py` references + docs.

**CRITICAL build constraint — the `carla` wheel:** the `carla` PyPI package has **no
macOS/arm64 wheel and no Python 3.12 support** (Linux/Windows, CPython ≤3.10 only).
The starter runs Python 3.12 on the team's macOS dev machine. Therefore:
- `carla` MUST NOT be in `services/api/requirements.txt` / `requirements.lock` /
  `pyproject.toml` base deps — putting it there breaks `pnpm run setup`, the venv
  install, and every `verify` gate on macOS.
- Declare it as documented, optional, install-on-a-supported-host: e.g. an extra
  (`pip install carla==0.9.15` on a Linux GPU box) documented in README + the
  simulation feature doc as a prerequisite alongside "a running CARLA server."
- `import carla` is **lazy/guarded** inside `service/carla_runner.py`; the `run`
  endpoint returns a clear, typed error ("CARLA not installed on this host / CARLA
  server unreachable at CARLA_HOST:CARLA_PORT") when the module or server is absent —
  never a silent fake and never a substitute engine.
- This is still the **real vendor engine** (CARLA), guarded only because its wheel is
  platform-restricted. Reviewer: do NOT flag the guarded import as "not using the real
  engine" — the guard is the correct, documented handling, mirroring other heavy-native
  samples in this repo. The lake's manage/browse/serve side (scenarios CRUD, episode
  browse, presigned serving) works on any host against data already in B2.

`torch` is likewise NOT a base dep — the DataLoader lives in `examples/` with its own
documented `pip install`.

## 4. Key features (seed README + `docs/features/*`)

1. **Scenario configs** — create/edit/delete reusable CARLA scenario configs (town,
   weather preset, traffic density, sensor rig, fps, frame count) stored as JSON in the
   B2 `scenarios/` prefix. `deployment: local` (no external provider). *Primary entity.*
2. **CARLA simulation runner** — launch a scenario → drives the **real CARLA server**
   via the `carla` Python API in synchronous mode, capturing multi-sensor streams and
   streaming each frame to B2 as produced. `deployment: local`; external provider: none
   (CARLA server is user-hosted); env var for a key: **none** (B2 creds only);
   estimated cost of one full demo run: **$0** (no paid API — B2 storage/egress only).
   CPU/GPU note: the CARLA *server* needs a GPU (documented prereq); the app's
   client/writer process is CPU-only and holds no in-process torch model, so the
   CUDA→MPS→CPU autodetect rule applies only to the standalone PyTorch DataLoader
   example (which defaults CPU, autodetects CUDA→MPS→CPU).
3. **Episode explorer (scoped asset explorer)** — per-episode view: metadata +
   annotations (weather, town, frame count, bbox) and a sensor-scoped frame browser
   locked to the `episodes/<id>/` prefix, with presigned-URL preview.
4. **Dataset serving → PyTorch** — presigned-URL serving of frames straight from B2,
   plus a standalone `carla_b2_dataset.py` PyTorch `DataLoader` example for training.
5. **Data-lake dashboard** — total episodes, total frames, storage footprint, frames
   by sensor, episodes by weather/town, ingest throughput.

**External API provider:** none. The description says "no second API key, B2
credentials only," CARLA is on-device/user-hosted, and no "Suggested stack" mentions
Genblaze — so there is **no Genblaze routing** and **no remote AI provider** in this
sample.

**Primary-entity lifecycle (Scenario):** UI exposes **all** verbs —
create ✅ / read ✅ / edit ✅ / delete ✅ / run ✅. `omitted_ui_verbs`: **none**.
(Episode is a derived, immutable artifact, not the primary entity: it has read +
delete in the UI; "create" is the outcome of `run`, and "edit" is intentionally N/A —
captured sensor frames are immutable — so no Episode edit form is built. This is a
non-primary-entity note, not an omitted primary verb.)

**Form UX conventions (create/edit Scenario):**
- Selectors for finite-value fields (both create & edit): town (`Select`:
  Town01–Town10HD), weather preset (`Select`: ClearNoon / CloudyNoon / WetNoon /
  MidRainyNoon / HardRainNoon / ClearSunset / WetCloudySunset / HardRainNight …),
  traffic density (`RadioGroup`/segmented: low / medium / high), fps (`Select`:
  10 / 20 / 30), sensor rig (checkbox group of the sensor types). Free text only for
  name/description; numeric input for frame count.
- Create-form safe defaults surfaced as placeholder / `FormDescription` guidance (not
  an autofill button) for a sound test run: Town10HD, ClearNoon, medium traffic,
  10 fps, 200 frames, rig = RGB + segmentation + depth + LiDAR + vehicle-state.
- Edit form opens pre-filled with the real scenario. Exemplar:
  `apps/web/src/components/settings/settings-form.tsx`.

## 5. Doc transforms

- **Rewrite**: `README.md` (purpose, quickstart, CARLA prereqs, B2 setup, prefix
  layout, DataLoader usage), `ARCHITECTURE.md` (scenario→run→stream→serve data flow),
  `PRODUCT.md`, `docs/app-workflows.md`, `docs/features/dashboard.md`.
- **Keep (light edits)**: `docs/features/file-browser.md` (bucket explorer),
  `docs/features/file-upload.md` (reframed manual ingest), `docs/SECURITY.md`,
  `docs/RELIABILITY.md`, `docs/verification.md`, `docs/frontend-conventions.md`,
  `docs/dev-workflows.md`.
- **Repurpose**: `docs/features/metadata-extraction.md` → episode metadata/annotations,
  or delete if fully superseded by the new `episode-explorer.md`.
- **New feature docs (stub from `_template.md`)**: `docs/features/scenarios.md`,
  `docs/features/simulation-runner.md`, `docs/features/episode-explorer.md`,
  `docs/features/dataset-serving.md`.
- `settings.md` stays (Settings screen kept).

## 6. Rename table

| From (`vibe-coding-starter-kit`) | To (`carla-sensor-data-lake`) |
|---|---|
| kebab slug `vibe-coding-starter-kit` | `carla-sensor-data-lake` |
| pnpm package scope `@vibe-coding-starter-kit/web` | `@carla-sensor-data-lake/web` |
| snake / python `vibe_coding_starter_kit` | `carla_sensor_data_lake` |
| Title / display name `APP_NAME` (`app-config.ts`) | `CARLA Sensor Data Lake` |
| FastAPI `API_TITLE`/description (derives from `APP_NAME`) | derived — one display name, no drift |
| B2 attribution token — `user_agent_extra` **and** `utm_content` (single token) | `carla-sensor-data-lake` |
| Railway/Vercel service names, image tags, workflow slugs | `carla-sensor-data-lake-*` |
| README/docs prose references to the starter | CARLA data-lake wording |

Enforcement to respect: `check:agent-docs` branding rule (one display name across
frontend `APP_NAME` + FastAPI title), the single B2 attribution token across
`user_agent_extra` + `utm_content`, and no hardcoded display name in frontend source
outside `app-config.ts`.

---
Proceeding straight to Phase 2 (build). No approval gate.
