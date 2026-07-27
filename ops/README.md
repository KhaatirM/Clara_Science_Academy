# Ops utilities (Render shell)

Run from the **repo root** so imports resolve:

```bash
python ops/shutdown_maintenance.py
python ops/verify_database_connection.py
python ops/audit_staff_google_sync.py
```

- `shutdown_maintenance.py` — force-clear stuck maintenance mode
- `render_db_guard.py` — require Postgres for Google sync jobs
- `audit_*` / `backfill_*` / `merge_*` — rare admin repair jobs
