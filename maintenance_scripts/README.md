# Maintenance Scripts

One-off migrations and data scripts. Run with Flask app context.

## One-time data: Subject requirements

Populates the `subject_requirement` table so report-card grade calculation uses DB-driven subjects (see `services/grade_calculation.py`). Run **once** after the table exists:

```bash
flask shell
>>> from maintenance_scripts.populate_subject_requirements import run
>>> run()
```

Or: `python -c "from app import create_app; from maintenance_scripts.populate_subject_requirements import run; app = create_app(); app.app_context().push(); run()"`

If the table is missing, create it with Flask-Migrate (`flask db migrate` / `flask db upgrade`) or ensure `SubjectRequirement` is in `models.py` and run `db.create_all()` in a context first.
