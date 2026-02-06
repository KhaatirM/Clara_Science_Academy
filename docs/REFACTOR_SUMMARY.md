# Refactor Summary: Clean Architecture

This doc describes the structural changes made so **app.py** stays glue-only (config, blueprints, extensions) and business logic lives in dedicated modules.

---

## 1. Services layer (`services/`)

Business logic was moved out of `app.py` into:

| Module | Purpose |
|--------|--------|
| **`services/grade_calculation.py`** | Report-card grade calculation by grade level (1–2, 3, 4–8). Subject lists are hardcoded; consider a `SubjectRequirements` table later. |
| **`services/notifications.py`** | Create notifications (single user, class, all students, all teachers). |
| **`services/activity_log.py`** | `log_activity()` and `get_user_activity_log()` for auditing. |

**Imports:** Existing code can keep using `from app import create_notification`, `log_activity`, `get_grade_for_student`, etc.; `app.py` re-exports from `services`. New code can import directly from `services` if you prefer.

---

## 2. Database one-off fixes (`database_utils.py`)

- **`run_production_database_fix()`** adds missing columns on **PostgreSQL** when needed.
- It is **not** run on every startup. Prefer **Flask-Migrate** for schema changes:
  ```bash
  flask db migrate -m "Add column X"
  flask db upgrade
  ```
- To run the one-off fix on startup (e.g. on Render), set:
  ```bash
  RUN_PRODUCTION_DB_FIX=1
  ```
- For local or one-time use, you can call it from a script:
  ```python
  from database_utils import run_production_database_fix
  # ... create app and push context ...
  run_production_database_fix()
  ```

---

## 3. CSRF

- **Config:** `WTF_CSRF_CHECK_DEFAULT = False` so existing forms keep working.
- **Recommendation:** When you’re ready, set `WTF_CSRF_CHECK_DEFAULT = True` in `config.py`, ensure all forms include the CSRF token (e.g. `{{ csrf_token() }}` or `form.hidden_tag()`), and use `@csrf.exempt` only for specific API or webhook routes.

---

## 4. What stays in `app.py`

- Creating the Flask app and loading config
- Initializing extensions (db, login_manager, csrf, migrate)
- Registering blueprints
- User loader and thin `before_request` / error handlers
- Template filters (e.g. `from_json`, `display_grade`)

No grade calculation, notification creation, or activity logging lives in `app.py` anymore.

---

## 5. Optional next steps (from Gemini-style review)

- **Subject requirements:** Move hardcoded subject lists (e.g. for grades 1–2, 3, 4–8) into a `SubjectRequirements` (or similar) table so new subjects don’t require code changes.
- **Tabbed UIs:** Replace multiple assignment/admin pages with a single “command center” page per role using tabs (e.g. one assignment detail page with Stats / History / Submissions tabs).
- **Notification digest:** Batch notifications (e.g. daily or per-event) instead of one per grade/assignment to reduce noise.
- **Migrations only:** Remove any remaining `ALTER TABLE` from app startup and rely solely on `flask db upgrade` for schema changes.

---

## 5a. Implemented (Gemini checklist)

- **Subject requirements:** `SubjectRequirement` model and `services/grade_calculation.py` use it when populated; one-time seed via `maintenance_scripts/populate_subject_requirements.py`.
- **Assignment Command Center:** One tabbed page at `/management/assignment/<id>/center` (Overview / Grade / Statistics / History). Linked from View Assignment and Grade Statistics.
- **Notification digest:** `create_digest_notifications()` and `create_grade_update_digest()` in `services/notifications.py`; use after bulk grade save. Re-exported from `services` and `app`.
- **Migrations only:** No `ALTER TABLE` on app startup.

---

## 6. Consistent filters (UX)

Use the same filter controls (date range, role, search) across Student, Teacher, and Admin views. Prefer a shared partial (e.g. `templates/shared/_filter_bar.html`) with params like `date_from`, `date_to`, `role`, `q`. Activity log and assignment lists can adopt this in a future pass.
