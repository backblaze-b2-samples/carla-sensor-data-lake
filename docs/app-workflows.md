<!-- last_verified: 2026-08-06 -->
# App Workflows

User journeys inside the application.

## Manage Scenarios

- User navigates to `/scenarios` — a table of reusable CARLA capture configs
- **New scenario** (`/scenarios/new`): a form with selectors for finite fields (town, weather preset, fps, traffic density) and a checkbox rig for sensors; free text for name/description; a numeric frame count. Each finite field shows its suggested safe default as guidance (Town10HD, ClearNoon, medium, 10 fps, 200 frames, full rig) rather than an autofill button
- On submit the scenario is stored as `scenarios/<id>.json` in B2 and the user lands on its detail page
- **Detail** (`/scenarios/[id]`): the full config, a **Run** action, an **Edit** link, a **Delete** action, and the episodes captured from this scenario
- **Edit** (`/scenarios/[id]/edit`): the same form, pre-filled with the real scenario; saving replaces the config (created_at preserved)
- **Delete**: a confirm dialog; deleting removes only the scenario config — captured episodes are untouched
- See: [Scenarios](features/scenarios.md)

## Run a Scenario (capture an episode)

- On a scenario's detail page the user clicks **Run**
- The API drives the real CARLA server in synchronous mode and streams every sensor frame to B2 as it is produced, then writes the episode `metadata.json`
- On success: a toast reports the frame count and the user is taken to the new episode
- If CARLA is not installed on the host or the server is unreachable, a clear "Run unavailable" toast explains the platform requirement — no fake capture is produced. This is expected on a machine without the CARLA server (e.g. the macOS dev machine); seed synthetic demo data with `scripts/seed_lake.py` to explore the browse/serve side
- See: [Simulation runner](features/simulation-runner.md)

## Explore an Episode

- User navigates to `/episodes` — a table of captured episodes (scenario, town/weather, frames, size, source badge, status)
- **Detail** (`/episodes/[id]`): metadata + bbox annotations, a frames-by-sensor breakdown, a "Serve this dataset" card (copy the PyTorch command, copy a sample frame's presigned URL), and a **sensor-frame browser scoped to `episodes/<id>/`** with per-frame preview/download
- **Delete**: a confirm dialog; deleting removes every object under `episodes/<id>/` (prefix-scoped)
- See: [Episode explorer](features/episode-explorer.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT). A determinate progress bar tracks the bytes leaving the browser; once they are all sent the row switches to "Verifying upload..." with an *indeterminate* sweeping bar while the API HEADs and magic-byte-sniffs the stored object. That phase has no percentage to report, and a bar parked at a full 100% read as finished-but-stuck
- On success: toast notification, green checkmark, and a "View in Files" link through to the browser
- On failure: red status icon with error message
- User can clear completed uploads
- The queue lives in an app-wide provider: navigating to another page keeps the upload running, shows an "Uploading N files" indicator in the header, and keeps the duplicate-upload guard armed
- Reloading or closing mid-upload asks for confirmation first; if the upload dies anyway, the next load says which file didn't finish
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads the 100 most recent objects from the API (sorted most recent first). While it loads, the page says so on screen and escalates the wording if the wait runs long — a full bucket listing measured 2.8s-21s cold
- If that limit was hit, a notice states how many objects the bucket actually holds — the page never claims to show everything
- Files displayed in tree view with folders and type-specific icons
- Folders auto-expand on load until the *majority* of the listed files are reachable without clicking, so the page's own "click a file" instruction is always actionable. Stopping at the first visible file was not enough: one stray top-level object left the other 99 sealed in collapsed folders while the page claimed to show 100
- Clicking a file row opens its preview; the per-row actions menu (preview / download / delete) is always visible, on every viewport
- Arriving at `/files?preview=<key>` expands that file's folders and opens its preview directly. This is how the ⌘K palette and the dashboard's recent-uploads rows hand off a *specific* file; the param is consumed on arrival so it doesn't re-fire later
- **Preview**: opens dialog with image/PDF preview + metadata panel, and the file's Download / Delete actions — the advertised "click a file" path offers everything the row menu does. The loading state holds until the media paints; a failure offers "Open in a new tab". The preview URL is signed with `Content-Disposition: inline` so PDFs render in place
- **Download**: shows a pending state on the row plus a toast while the presigned URL is fetched, then starts the download via an anchor click (which, unlike a popup, still works if the click's user activation expired during a slow presign). Failures are reported; the click can never silently do nothing
- **Delete**: the confirmation dialog stays open showing "Deleting..." until the request settles, then the row disappears with the toast (optimistic cache update) and the list reconciles with the server. The dialog is held deliberately — Radix closes on action click by default, which dismissed the only pending state and left the row looking untouched while the delete was still in flight
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Parallel API calls load: lake stats, ingest activity, and recent episodes
- While stats load, the page states it in words above the cards rather than showing silent skeletons
- Stats cards show: total episodes, total sensor frames, storage footprint, scenario count
- The ingest chart shows frames written to B2 per day over the last 7 days
- The breakdown card shows frames-by-sensor, episodes-by-weather, and episodes-by-town as proportional bars
- The recent-episodes table shows the 5 newest episodes; each row links to its episode detail
- Empty state: "No episodes yet" / "No ingest yet" pointing at Run or the seed script
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
