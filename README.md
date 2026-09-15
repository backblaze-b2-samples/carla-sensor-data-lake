<!-- last_verified: 2026-09-15 -->
# CARLA Sensor Data Lake

A **synthetic autonomous-driving data lake** built on **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake)**. Generate large, diverse multi-sensor driving datasets from the open-source [CARLA](https://carla.org) simulator — RGB camera, semantic segmentation, LiDAR point clouds, depth maps, and per-tick vehicle telemetry — without costly real-world data collection, and store, browse, and serve them straight from cheap object storage.

A scenario config (town, weather, traffic density, sensor rig, frame count) is stored in B2; running it drives the real CARLA server, which **streams every sensor frame to B2 as it is produced**; episode metadata and annotations are written at episode end; and the resulting dataset is browsed, served via presigned URLs, and streamed straight into a PyTorch `DataLoader` for training. B2 is the storage layer for the whole lake, accessed over the **S3-compatible API** — no second API key, B2 credentials only.

**Who it's for:** autonomous-vehicle researchers, perception-model engineers, and robotics/sim teams who need scalable synthetic sensor datasets on cheap object storage.

**What you get out of the box:**
- **Scenarios** — create / edit / delete / run reusable CARLA capture configs (the primary entity), stored as JSON in B2
- **Simulation runner** — drives the real CARLA server in synchronous mode and streams multi-sensor frames to B2 as they are captured
- **Episode explorer** — per-episode metadata + bbox annotations and a sensor-frame browser scoped to that episode's B2 prefix, with presigned-URL preview
- **Dataset serving** — presigned-URL serving of frames plus a standalone PyTorch `DataLoader` example for training
- **Data-lake dashboard** — episodes, frames, storage footprint, frames-by-sensor, episodes-by-weather/town, and ingest throughput
- Full-bucket file browser + upload, a FastAPI backend with strict layered architecture, and agent-optimized docs

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.12, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake)**. A CARLA server is only needed to *run* a scenario (see [Running against CARLA](#running-against-carla)); everything else — manage, browse, and serve datasets — works on any host against data already in B2.

```bash
git clone https://github.com/backblaze-b2-samples/carla-sensor-data-lake.git
cd carla-sensor-data-lake
pnpm run setup
```

`pnpm run setup` copies `.env.example` to `.env` (only if missing), installs workspace dependencies, creates `services/api/.venv`, and installs the API's committed Python 3.12 resolution from `services/api/requirements.lock`. It never installs `carla` or `torch` — those are optional, platform-restricted extras (see below). It is safe to rerun.

> Use the `pnpm run` form: `setup` (like `doctor`) is a built-in pnpm command before pnpm 11, so bare `pnpm setup` would run pnpm's own command instead of this script.

**Add your B2 credentials.** Open `.env`, then in the [Backblaze B2 console](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake):

1. **Create a bucket** and paste its values into `.env`:
   - **Bucket Unique Name** → `B2_BUCKET_NAME`
   - The region in the bucket's endpoint (e.g. `us-west-004` from `s3.us-west-004.backblazeb2.com`) → `B2_REGION` *(the S3 endpoint is derived from it)*
2. **Create an application key** with `Read and Write` permission:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(shown once — paste it now)*

**Seed some demo data (optional, recommended).** So the dashboard, episodes list, and frame explorer have content without a CARLA host, write a couple of synthetic scenarios and episodes to B2:

```bash
services/api/.venv/bin/python services/api/scripts/seed_lake.py --apply
```

Seeded episodes are clearly marked `synthetic-seed` in the UI so they're never mistaken for a real CARLA capture.

**Run it.**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000` (interactive API docs at `/docs`). `pnpm dev` runs the `pnpm run doctor` preflight first, which catches the common setup gotchas (wrong Node/Python version, missing venv, placeholder `.env`, ports in use).

## How it works

```
Scenario (JSON in B2)  ──run──▶  CARLA server (real engine)  ──stream──▶  B2 (per-frame PutObject)
                                                                              │
Dashboard ◀── aggregate ── Episode metadata + frames in B2 ◀── metadata.json ┘
                                                    │
                            Episode explorer / presigned URLs / PyTorch DataLoader
```

All storage is the **S3-compatible API only** (`boto3`), isolated in `services/api/app/repo/`, with a custom user agent (`b2ai-carla-sensor-data-lake`) on every client. Operations exercised: `PutObject` (scenario JSON, each sensor frame, episode metadata), `ListObjectsV2` (scenarios, episodes, scoped frame listings), `GetObject`/`HeadObject`, `generate_presigned_url` (serving/preview), and prefix-scoped `DeleteObject`/`DeleteObjects`.

### B2 prefix layout

```
scenarios/<scenario_id>.json
episodes/<episode_id>/metadata.json
episodes/<episode_id>/rgb/<frame>.png
episodes/<episode_id>/segmentation/<frame>.png
episodes/<episode_id>/depth/<frame>.npy
episodes/<episode_id>/lidar/<frame>.ply
episodes/<episode_id>/vehicle_state/<frame>.json
```

## Running against CARLA

Capturing a real episode needs the CARLA simulator. The `carla` PyPI wheel is **platform-restricted** — it supports Linux/Windows on **CPython <= 3.10 only** (no macOS/arm64, no Python 3.12), so it is deliberately **not** a base dependency and is never installed by `pnpm run setup`. The app imports `carla` lazily and, on a host without it or without a reachable server, the run endpoint returns a clear `503` naming the requirement — never a fake capture.

To actually run scenarios, on a supported Linux/GPU host with a running [CARLA server](https://carla.org/2020/06/09/release-0.9.9/):

```bash
python3.10 -m venv .venv-carla && . .venv-carla/bin/activate
pip install -r services/api/requirements.txt -r services/api/requirements-carla.txt
# point the app at your CARLA server (defaults: localhost:2000)
export CARLA_HOST=localhost CARLA_PORT=2000
```

Then click **Run** on a scenario (or `POST /scenarios/{id}/run`). See [docs/features/simulation-runner.md](docs/features/simulation-runner.md) for the full prerequisites.

## Training on the lake (PyTorch)

Frames are served straight from B2 via short-lived presigned URLs, so a private bucket streams into training with no local copy. A standalone example (`torch` is **not** a base dependency — install it yourself):

```bash
pip install torch torchvision
python services/api/examples/carla_b2_dataset.py --episode <episode_id>
```

The example auto-detects the device (CUDA → Apple MPS → CPU, defaulting to CPU). See [docs/features/dataset-serving.md](docs/features/dataset-serving.md).

## Why Backblaze B2?

[Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake) is the object storage this app is built around — a deliberate default, not just a demo backend:

- **S3-compatible API.** B2 speaks the S3 API, so the `boto3` calls you already use for AWS S3 work unchanged. All storage is isolated in `services/api/app/repo/` — nothing is locked to a proprietary client.
- **Built for data-heavy AI workloads.** A sensor data lake grows fast — hundreds of frames per episode across five sensor streams. B2 runs at a fraction of hyperscaler pricing with generous free egress to many CDN and compute partners, exactly what streaming datasets into training wants.
- **Free to start.** A [free B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake) is enough to run everything here.

## When to use

Use this when you need scalable synthetic multi-sensor driving datasets on cheap object storage: generate diverse CARLA scenarios, capture episodes at scale, and stream them into perception-model training — without building the storage, browse, and serving plumbing yourself.

## When not to use

This is a template/sample, not a hosted SaaS. It provides no managed hosting, user accounts, authentication, tenant isolation, or billing. The API is unauthenticated and bucket-wide by design (single-tenant demo stance). You own the product-specific security, operations, and compliance decisions for anything you adapt to production.

## Core Features

- [Scenarios](docs/features/scenarios.md) — create / edit / delete / run reusable CARLA capture configs (primary entity)
- [Simulation runner](docs/features/simulation-runner.md) — drive the real CARLA server and stream frames to B2
- [Episode explorer](docs/features/episode-explorer.md) — per-episode metadata, annotations, and a scoped sensor-frame browser
- [Dataset serving](docs/features/dataset-serving.md) — presigned-URL serving and the PyTorch `DataLoader` example
- [Dashboard](docs/features/dashboard.md) — lake metrics: episodes, frames, storage, sensor/weather/town breakdowns, ingest throughput
- [File Browser](docs/features/file-browser.md) — full-bucket list, preview, download, delete
- [File Upload](docs/features/file-upload.md) — manual ingest of an external sensor file or scenario JSON
- [Metadata Extraction](docs/features/metadata-extraction.md) — image dimensions, EXIF, PDF info, checksums (Files detail view)

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts, TanStack Query
- Python 3.12+, FastAPI, boto3, Pydantic v2, Pillow, PyPDF2
- CARLA 0.9.x (optional, user-hosted) + PyTorch (optional, for the DataLoader example)
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

The commands you reach for day to day:

| Command | What it does |
|---------|-------------|
| `pnpm run setup` | One-time cold start: copy `.env.example` → `.env` (only if missing), install workspace deps, create the backend venv, install locked API deps |
| `pnpm dev` | Start frontend + backend (runs the `pnpm run doctor` preflight first) |
| `pnpm wait-ready` | Block until the running web + API answer, print one line, exit 0/1 — use instead of sleeping before driving the app |
| `pnpm verify` | Credential-free pre-PR suite — runs `check:agent-docs`, `verify:api`, then `verify:web` |
| `pnpm verify:full` | `pnpm verify` plus Playwright E2E; needs a live local stack, real `.env`, free port 3000, and Chromium |
| `pnpm test:verify` | Run throwaway verification specs from `apps/web/e2e/verify/` against the app, with the shared browser fixtures |
| `pnpm contract:export` / `pnpm contract:check` | Export / verify the FastAPI OpenAPI contract in `docs/api/openapi.json` |

`pnpm verify` is the gate to run before opening a PR. It needs `services/api/.venv`
from `pnpm run setup`, but no B2 credentials or browser, and it breaks down into
`pnpm verify:api` (backend lint, tests, structure), `pnpm verify:web` (frontend
lint, unit tests, typecheck + build), and `pnpm check:agent-docs` (agent-doc drift).

For the full command reference (`dev:web`, `dev:api`, `lint`, `test:*`,
`check:structure`, `test:e2e`, live B2 tests), see
[docs/dev-workflows.md](docs/dev-workflows.md#commands). For worktree/parallel-run
notes, port-fallback behavior, and slow-run recovery, see
[docs/verification.md](docs/verification.md).

## Deploying to Vercel

Deploys as **one Vercel project** — the Next.js web app and FastAPI API build
from the same repo and share one origin (web at `/`, API under `/api`), so
there's **no CORS and no second URL to wire up**. The simulation runner is not
exercised on Vercel (CARLA is user-hosted); the deployed app manages, browses,
and serves data already in B2.

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fcarla-sensor-data-lake&project-name=carla-sensor-data-lake&repository-name=carla-sensor-data-lake&demo-title=CARLA%20Sensor%20Data%20Lake&demo-description=Synthetic%20autonomous-driving%20multi-sensor%20data%20lake%20on%20Backblaze%20B2%20object%20storage.&env=B2_APPLICATION_KEY_ID,B2_APPLICATION_KEY,B2_BUCKET_NAME,B2_REGION&envDescription=B2%20credentials%2C%20bucket%2C%20and%20region&envLink=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fcarla-sensor-data-lake%2Fblob%2Fmain%2Finfra%2Fvercel%2FREADME.md)

Full setup — variable reference, the two-Projects alternative, security,
preview/production, `/health` checks, and rollback — is in the
[Vercel delivery contract](infra/vercel/README.md).

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (scenarios, simulation, episodes, dataset serving, dashboard, files) |
| [docs/design-system.md](docs/design-system.md) | Design tokens, primitives, AI elements, loader, error/empty states |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows, command index, releases |
| [docs/verification.md](docs/verification.md) | What each gate checks, and failure recovery |
| [docs/frontend-conventions.md](docs/frontend-conventions.md) | Frontend conventions, screens, data fetching |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/api/openapi.json](docs/api/openapi.json) | Checked contract for the local FastAPI API |
| [infra/vercel/README.md](infra/vercel/README.md) | Vercel deployment contract |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## FAQ

**What is CARLA Sensor Data Lake?**
A full-stack template (Next.js 16 + FastAPI) that turns the open-source [CARLA](https://carla.org) simulator into a synthetic autonomous-driving data lake on [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-carla-sensor-data-lake): define scenarios, run them to capture multi-sensor episodes, and browse and serve the datasets straight from B2.

**Do I need a GPU or CARLA installed to try it?**
No. The manage/browse/serve side runs on any host against data already in B2 — seed synthetic demo data with `scripts/seed_lake.py`. Capturing a *real* episode needs a CARLA server on a supported Linux/GPU host (see [Running against CARLA](#running-against-carla)); without it, the Run action returns a clear message instead of failing.

**Why isn't `carla` (or `torch`) installed by setup?**
The `carla` wheel supports Linux/Windows on CPython <= 3.10 only (no macOS/arm64, no 3.12), so adding it to the base deps would break setup and verify on a typical dev machine. It's a documented optional extra (`requirements-carla.txt`), lazily imported and guarded. `torch` is likewise optional and used only by the standalone DataLoader example.

**Is it free?**
Yes. The code is MIT-licensed, and Backblaze B2 offers a free account to get started. A full CARLA run costs $0 in API fees (B2 storage/egress only) — there is no external AI provider and no second API key.

**Do I have to use Backblaze B2?**
It integrates B2 through the S3-compatible API, and B2 is the storage the app is built around. You supply your own bucket and application key during setup.

**Does it include authentication or multi-tenant isolation?**
No. The API is unauthenticated and bucket-wide by design. Add whatever your application requires on top of the scaffold.

**Where do I get help or report bugs?**
Report repository defects through [GitHub Issues](https://github.com/backblaze-b2-samples/carla-sensor-data-lake/issues). For B2 account, billing, service, or API help, use [Backblaze Support](https://www.backblaze.com/help).

## Maintenance and support

Backblaze maintains this open-source template/sample to help developers get
started with B2. Production use is possible with caution and requires your own
validation. Report repository defects and feature requests through
[GitHub Issues](https://github.com/backblaze-b2-samples/carla-sensor-data-lake/issues);
for B2 account, billing, service, or API help, use
[Backblaze Support](https://www.backblaze.com/help). This template/sample is
not covered by the Backblaze service level agreement, and no SLA is provided
for the repository software; any B2 service or support commitments are governed
separately by the applicable Backblaze terms and support plan.

## Contributing

Start with [AGENTS.md](AGENTS.md). It's the map — everything else is discoverable from there. For local commit hooks, follow [the pre-commit workflow](docs/verification.md#pre-commit).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related projects

**Claude Agent B2 Skill** — manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup). Repo: [claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage).
