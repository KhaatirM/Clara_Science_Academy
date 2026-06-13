# End-to-end browser tests (Playwright)

Automated UI tests for school-year closure, management filters, and role access during phased lockouts.

## Setup

```bash
pip install -r tests/e2e/requirements-e2e.txt
playwright install chromium
```

Start the app (in another terminal):

```bash
python app.py
```

## Run

```bash
python tests/e2e/run_closure_e2e.py
```

Optional environment variables:

| Variable | Default |
|----------|---------|
| `E2E_BASE_URL` | `http://127.0.0.1:5000` |
| `E2E_PASSWORD` | *(required — set in your environment)* |
| `E2E_DIRECTOR_USER` | `vmuhammad` |
| `E2E_TEACHER_USER` | `jabdullah` |
| `E2E_STUDENT_USER` | `jhope` |

The runner resets test-user passwords, ensures **2025-2026** is active, cancels any in-flight closure, then schedules a new closure and **cancels** it at the end (no finalize).

## What is covered

- Calendar: **End-of-year closure** link present
- Report cards: closure scheduler **not** on that tab
- Classes / Assignments & Grades: nothing listed until a school year is selected
- Schedule closure → advance to teacher window → student submit blocked
- Advance to admin window → teacher grade POST blocked
- Cancel closure (cleanup)
