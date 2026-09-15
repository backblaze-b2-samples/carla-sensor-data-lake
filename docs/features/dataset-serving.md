<!-- last_verified: 2026-09-15 -->
# Feature: Dataset serving

## Purpose
Serve captured frames straight from B2 via short-lived presigned URLs — for UI preview, for copy-and-inspect, and for streaming into a PyTorch `DataLoader` during training — so a private bucket trains models with no local copy of the dataset.

## Used By
- UI: `/episodes/[id]` — the "Serve this dataset" card (copy the PyTorch command, copy a sample frame's presigned URL) and per-frame Download in the scoped browser
- API: `GET /files-by-key/preview`, `GET /files-by-key/download` (presigned URLs)
- Standalone: `services/api/examples/carla_b2_dataset.py`

## Core Functions
- `apps/web/src/components/episodes/episode-detail.tsx` — serving affordances
- `services/api/app/repo/b2_client.py` — `get_presigned_url` (S3 `generate_presigned_url`)
- `services/api/examples/carla_b2_dataset.py` — a PyTorch `Dataset`/`DataLoader` that lists an episode's frames, presigns each, and streams them; auto-detects CUDA → MPS → CPU

## Inputs
- episode_id / frame key
- B2 env vars (`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`)

## Outputs
- Presigned GET URLs (time-limited)
- Batched image tensors from the example `DataLoader`

## Flow (PyTorch example)
```bash
pip install torch torchvision            # NOT a base dependency — install yourself
python services/api/examples/carla_b2_dataset.py --episode <episode_id>
```
- Lists `episodes/<id>/rgb/` via boto3 (its own client carries the same `b2ai-carla-sensor-data-lake` user agent)
- Presigns each frame, fetches the bytes over HTTPS, decodes with Pillow → CHW float tensor
- `DataLoader` batches them; the device is auto-selected (CUDA → MPS → CPU, default CPU)

## Edge Cases
- No frames for the episode → the example exits with a clear message
- `torch` not installed → the example fails at import with the documented `pip install` remedy (it is intentionally not a base dep)
- Presigned URLs expire — regenerate for long-running jobs (the example uses a 1-hour TTL)

## Verification
- Test files: covered indirectly by `services/api/tests/test_presign_disposition.py` (presign behavior); the example is a standalone script, excluded from `pnpm verify`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green; the example runs on a host with `torch` + real B2 credentials + a seeded/captured episode

## Related Docs
- [Episode explorer](episode-explorer.md)
- [README.md](../../README.md)
