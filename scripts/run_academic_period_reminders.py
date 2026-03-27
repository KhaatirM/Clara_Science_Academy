"""
Run from cron (e.g. Render daily) or locally:

    python scripts/run_academic_period_reminders.py

Uses SCHOOL_TIMEZONE / America/New_York for the calendar day check.
Set PUBLIC_BASE_URL so email links are absolute (optional).
"""
import sys
import os

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from utils.academic_period_reminders import run_academic_period_reminders


def main():
    app = create_app()
    with app.app_context():
        result = run_academic_period_reminders()
        print(result)


if __name__ == '__main__':
    main()
