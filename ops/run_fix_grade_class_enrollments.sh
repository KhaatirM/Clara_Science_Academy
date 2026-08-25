#!/usr/bin/env bash
# Align student core-class enrollments to each student's current grade level.
#
# Run on Render Shell (production DB):
#   bash ops/run_fix_grade_class_enrollments.sh              # preview only
#   bash ops/run_fix_grade_class_enrollments.sh --apply      # preview, then apply
#   bash ops/run_fix_grade_class_enrollments.sh --apply --student-id 42
#
# Optional env:
#   FLASK_ENV=production   (default)
#   SCHOOL_YEAR_ID=3       pass --school-year-id when no year is marked active
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export FLASK_ENV="${FLASK_ENV:-production}"

EXTRA=()
APPLY=0
for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    APPLY=1
  else
    EXTRA+=("$arg")
  fi
done

if [[ -n "${SCHOOL_YEAR_ID:-}" ]]; then
  EXTRA+=(--school-year-id "$SCHOOL_YEAR_ID")
fi

echo "=== Grade/class enrollment fix — dry run ==="
python ops/fix_student_core_enrollments_and_temp_creds.py --dry-run "${EXTRA[@]}"

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "No changes written. Re-run with --apply to commit enrollment fixes."
  exit 0
fi

echo
echo "=== Applying enrollment fixes ==="
python ops/fix_student_core_enrollments_and_temp_creds.py "${EXTRA[@]}"
echo "Done."
