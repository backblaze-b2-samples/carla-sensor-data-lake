<!-- last_verified: 2026-09-15 -->
# Feature: Episode explorer

## Purpose
Browse a captured episode: its metadata and bbox annotations, a breakdown of frames by sensor, and a **sensor-frame browser scoped to that episode's `episodes/<id>/` prefix** — plus presigned-URL preview of individual frames. Episodes are immutable: read + delete only, no edit.

## Used By
- UI: `/episodes` (list), `/episodes/[id]` (detail with scoped explorer)
- API: `GET /episodes`, `GET /episodes/{episode_id}`, `DELETE /episodes/{episode_id}`, plus `GET /files?prefix=episodes/<id>/` for the scoped frame listing and `GET /files-by-key/preview` for previews

## Core Functions
- `apps/web/src/components/episodes/episodes-list.tsx` / `episodes-table.tsx` — list
- `apps/web/src/components/episodes/episode-detail.tsx` — metadata + annotations panel, serving affordances, scoped frame browser
- `apps/web/src/components/files/file-browser.tsx` — reused **prefix-locked** (`prefix` + `stripPrefix` props) for the scoped explorer; the whole-bucket `/files` view is unchanged
- `apps/web/src/lib/file-tree.ts` — `buildFileTree(files, stripPrefix)` roots the tree below the episode prefix while keeping real keys for actions
- `services/api/app/runtime/episodes.py` — route handlers
- `services/api/app/service/episodes.py` — list (one bucket scan, grouped by id + joined to metadata), detail, prefix-scoped delete
- `services/api/app/repo/episode_store.py` — list/read/delete under `episodes/` (delete scoped strictly to one `episodes/<id>/` prefix)

## Inputs
- episode_id: path param
- prefix: the scoped browser lists only `episodes/<id>/`

## Outputs
- `EpisodeSummary[]` (list), `EpisodeDetail` (metadata + live-computed size/object count)
- Delete removes every object under `episodes/<id>/` (`DeleteObjects`), returns the count

## Flow
- List: one `ListObjectsV2` under `episodes/`, grouped by id, joined to each `metadata.json`, newest first
- Detail: read `metadata.json` + list the episode's objects for size/count; render metadata, frames-by-sensor, annotations, serving card, and the scoped frame browser
- Preview: click a frame → presigned inline URL via `/files-by-key/preview`
- Delete: confirm → `DELETE /episodes/{id}` (prefix-scoped, never a broad wipe)

## Edge Cases
- Missing episode → `404`
- An episode id containing `/`, `..`, or `\` is rejected before any delete (prefix-escape guard)
- Seeded episodes carry `capture_source: "synthetic-seed"` and are badged as such

## UX States
- Empty: "No episodes yet" pointing at Run or the seed script
- Loading: skeletons
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_episodes.py`
- Required cases: list groups objects + joins metadata, detail, detail 404, prefix-scoped delete, delete missing → 404
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Simulation runner](simulation-runner.md)
- [Dataset serving](dataset-serving.md)
- [File Browser](file-browser.md)
