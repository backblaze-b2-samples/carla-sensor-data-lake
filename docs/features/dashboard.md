<!-- last_verified: 2026-09-15 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the data lake: how many episodes and sensor frames it holds, its storage footprint, how frames break down by sensor, how episodes break down by weather and town, and ingest throughput over time.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /lake/stats`, `GET /lake/ingest`, `GET /episodes`

## Core Functions
- `apps/web/src/components/dashboard/lake-stats-cards.tsx` — 4 stat cards (episodes, sensor frames, storage footprint, scenarios)
- `apps/web/src/components/dashboard/ingest-chart.tsx` — bar chart of frames ingested per day (last 7 days)
- `apps/web/src/components/dashboard/recent-episodes.tsx` — the 5 newest episodes
- `apps/web/src/components/dashboard/lake-breakdown.tsx` — frames-by-sensor, episodes-by-weather, episodes-by-town
- `apps/web/src/lib/api-client.ts` — `getLakeStats()`, `getIngestActivity()`, `getEpisodes()`
- `services/api/app/runtime/lake.py` — `GET /lake/stats`, `GET /lake/ingest`
- `services/api/app/service/lake.py` — aggregation over the `episodes/` prefix
- `services/api/app/repo/episode_store.py` — `list_all_episode_objects()` data access

## Canonical Files
- Aggregation logic: `services/api/app/service/lake.py`

## Inputs
- None (dashboard loads data automatically)
- `GET /lake/ingest?days=N` accepts a day window (1–90, default 7)

## Outputs
- `GET /lake/stats` → `LakeStats` (total_episodes, total_frames, total_scenarios, total_size_bytes/human, frames_by_sensor, episodes_by_weather, episodes_by_town)
- `GET /lake/ingest?days=7` → `DailyFrameCount[]` (frames written per day)
- `GET /episodes` → `EpisodeSummary[]` (recent episodes table shows the newest 5)

## Flow
- Page loads → parallel API calls (lake stats, ingest activity, episodes)
- Stats aggregate a single `ListObjectsV2` under `episodes/`: frames are objects two levels below the episode id (metadata.json is excluded); episode weather/town come from each `metadata.json`
- Cards show totals; the ingest chart shows server-aggregated frames-per-day; the breakdown card shows proportional bars for sensor/weather/town; the recent-episodes table links each row to its episode detail

## Edge Cases
- API unavailable → inline error states with retry
- Empty lake → empty chart/table/breakdown messages (no false zeros while loading)
- Large lake → listing paginates with `ContinuationToken`; metadata is read once per episode

## UX States
- Loading: an on-screen "Loading lake stats…" notice + skeletons for cards, chart, and breakdown
- Empty: "No episodes yet" / "No ingest yet" pointing at Run or the seed script
- Loaded: populated cards, chart, breakdown, recent-episodes table

## Verification
- Test files: `services/api/tests/test_lake.py`, `services/api/tests/test_episodes.py`
- Required cases: frames counted (metadata excluded), sensor/weather/town grouping, scenario count, ingest day window, bad `days` rejected
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [Episode explorer](episode-explorer.md)
