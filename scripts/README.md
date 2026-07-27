# Scripts

Deploy / scheduled jobs run from the **repo root**:

| Script | Purpose |
|--------|---------|
| `build_spa.sh` | Render build: install Node and build `static/spa/` |
| `startup.py` | Release migrate / boot helpers (`render.yaml` releaseCommand) |
| `sync_all_to_google.py` | Full Google Directory sync (cron) |
| `run_sync.py` | Google Classroom grades/assignments poll |

Emergency / repair tools live in [`ops/`](../ops/README.md) (e.g. `python ops/shutdown_maintenance.py`).
